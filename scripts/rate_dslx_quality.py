"""Reproducible, read-only Nasdaq DSLX research; artifacts live on Kingston.

Run with --output F:/ETF-screener-data/research/<new-run-name>. Strategies and
input Parquet files are frozen first. Existing output files are never replaced.
This evaluates current selected-universe daily strategies, not arbitrary DSLX
execution instructions. All fills are normalized to next real session open.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pandas as pd

from ETF_screener.config_loader import get_paths
from ETF_screener.dslx import (
    CandleSeries, InsufficientHistory, _expression_names, _liquidity_clause_matches,
    _match_pattern, parse_program,
)

HORIZONS = (5, 20, 60)
COST = 0.0015  # all-in proportional friction per side
STRESS_COST = 0.0035
WARMUP = 257  # 252 prior candles before the longest six-candle pattern
LATE_START = "2025-01-01"
AS_OF = "2026-09-04"


def dump_json(path: Path, payload) -> None:
    def convert(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    text = json.dumps(payload, default=convert, allow_nan=False, indent=2)
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write(text)
    else:
        path.write_text(text, encoding="utf-8")


class ResearchSeries(CandleSeries):
    """Same candle semantics, with validated OHLCV array lookup for research."""

    def __init__(self, frame, **kwargs):
        super().__init__(frame, **kwargs)
        self.arrays = {name: self.frame[col].to_numpy() for name, col in self.columns.items()}

    def value(self, index, field):
        value = self.arrays[field.lower()][index]
        if pd.isna(value):
            raise InsufficientHistory(f"{field} unavailable")
        return float(value)


def load_specs(directory: Path):
    specs = {}
    seen = {}
    for path in sorted(directory.glob("*.dslx")):
        source = path.read_text(encoding="utf-8-sig")
        program = parse_program(source)
        if len(program.strategies) != 1:
            raise ValueError(f"{path.name}: expected one strategy")
        st = program.strategies[0]
        if st.timeframe != "1d" or not st.entry_struct:
            raise ValueError(f"{path.name}: unsupported timeframe or entry pattern")
        if any("position" in _expression_names(d.condition) for d in st.candle_definitions):
            raise ValueError(f"{path.name}: position-dependent rules require a different evaluator")
        if len(program.universes) > 1 or any(u.source != "universe.selected" for u in program.universes):
            raise ValueError(f"{path.name}: unsupported universe chain")
        expected_source = f"universe.{program.universes[0].name}" if program.universes else "universe.selected"
        if st.source != expected_source:
            raise ValueError(f"{path.name}: unsupported source")
        clauses = tuple(c for u in program.universes for c in u.liquidity)
        group = hashlib.sha256(repr(clauses).encode()).hexdigest()[:12]
        signature = repr((replace(st, name="", source=""), clauses))
        duplicate = seen.get(signature)
        seen.setdefault(signature, path.name)
        specs[path.name] = {
            "strategy": st, "clauses": clauses, "group": group,
            "duplicate_of": duplicate,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return specs


def eligibility(frame, clauses):
    result = pd.Series(True, index=frame.index)
    for c in clauses:
        turnover = frame.Close * frame.Volume
        if c.metric == "avg_turnover":
            values = turnover.rolling(c.sessions).mean()
        elif c.metric == "median_turnover":
            values = turnover.rolling(c.sessions).median()
        elif c.metric == "active_sessions":
            values = (frame.Volume > 0).astype(float).rolling(c.sessions).sum()
        else:
            raise ValueError(c.metric)
        operations = {">": values.gt, ">=": values.ge, "<": values.lt,
                      "<=": values.le, "==": values.eq, "!=": values.ne}
        result &= values.notna() & operations[c.operator](c.value)
    result.iloc[:WARMUP] = False
    return result.to_numpy()


def simulate(frame, entries, exits, cost=COST):
    """One unlevered sleeve per ticker, next-open fills, daily mark to market."""
    opens, closes = frame.Open.to_numpy(), frame.Close.to_numpy()
    dates = frame.Date.dt.strftime("%Y-%m-%d").tolist()
    cash, units = 1.0, 0.0
    pending_entry = pending_exit = False
    held = None
    trades, curve, exposure = [], [], []
    for i in range(len(frame)):
        exited = False
        if pending_exit:
            cash = units * opens[i] * (1 - cost)
            trades.append({"entry": held["entry"], "exit": dates[i],
                           "net_pct": (cash / held["capital"] - 1) * 100,
                           "bars": i - held["index"], "status": "closed"})
            units, held, pending_exit, exited = 0.0, None, False, True
        if pending_entry and held is None and not exited:
            held = {"entry": dates[i], "capital": cash, "index": i}
            units = cash / (opens[i] * (1 + cost))
            cash = 0.0
        pending_entry = False
        curve.append(cash + units * closes[i])
        exposure.append(held is not None)
        if held is not None:
            pending_exit = bool(exits[i])
        elif not exited:
            pending_entry = bool(entries[i])
    if held is not None:
        liquidation_value = units * closes[-1] * (1 - cost)
        trades.append({"entry": held["entry"], "exit": dates[-1],
                       "net_pct": (liquidation_value / held["capital"] - 1) * 100,
                       "bars": len(frame) - 1 - held["index"], "status": "open_mark"})
        curve[-1] = liquidation_value  # include estimated exit friction at report cutoff
    return {"trades": trades, "equity": curve, "exposure": exposure}


def evaluate_ticker(task):
    output, ticker = task
    output = Path(output)
    specs = load_specs(output / "strategies")
    frame = pd.read_parquet(output / "prices" / f"{ticker}.parquet")
    dates = frame.Date.dt.strftime("%Y-%m-%d").tolist()
    if len(frame) <= WARMUP:
        return ticker, {"dates": dates, "skipped": "insufficient warmup", "strategies": {}}
    series_by_style = {}
    masks, eligible, baseline = {}, {}, {}
    ha = ResearchSeries(frame, style="heikin_ashi")
    series_by_style["heikin_ashi"] = ha
    ema = ha._indicator_series("ema", "close", 200)
    trend = (ema.diff() >= 0).to_numpy()
    returns = {}
    outcome_dates = {}
    for horizon in HORIZONS:
        ratio = frame.Close.shift(-horizon) / frame.Open.shift(-1)
        returns[horizon] = ratio.to_numpy()
        outcome_dates[horizon] = frame.Date.shift(-horizon).dt.strftime("%Y-%m-%d").tolist()
    for spec in specs.values():
        group = spec["group"]
        if group in eligible:
            continue
        eligible[group] = eligibility(frame, spec["clauses"])
        baseline[group] = [
            [dates[i], int(trend[i]), *[
                float(returns[h][i]) if np.isfinite(returns[h][i]) else None for h in HORIZONS
            ]] for i in np.flatnonzero(eligible[group])
        ]
    result = {}
    for name, spec in specs.items():
        if spec["duplicate_of"]:
            continue
        st = spec["strategy"]
        series = series_by_style.setdefault(st.candle_style, ha) if st.candle_style == "heikin_ashi" else series_by_style.get(st.candle_style)
        if series is None:
            series = ResearchSeries(frame, style=st.candle_style)
            series_by_style[st.candle_style] = series
        key = (st.candle_style, st.candle_definitions, st.entry_struct, st.exit_struct)
        if key in masks:
            entry_mask, exit_mask = masks[key]
        else:
            entry_mask, exit_mask = np.zeros(len(frame), dtype=bool), np.zeros(len(frame), dtype=bool)
            for i in range(WARMUP, len(frame)):
                try:
                    entry_mask[i] = _match_pattern(st, st.entry_struct, series, i)[0]
                    exit_mask[i] = bool(st.exit_struct) and _match_pattern(st, st.exit_struct, series, i)[0]
                except InsufficientHistory:
                    pass
            masks[key] = entry_mask, exit_mask
        entries = entry_mask & eligible[spec["group"]]
        observations = []
        for i in np.flatnonzero(entries):
            observations.append({
                "ticker": ticker, "date": dates[i], "trend": int(trend[i]),
                "ratios": {str(h): float(returns[h][i]) if np.isfinite(returns[h][i]) else None for h in HORIZONS},
                "outcome_dates": {str(h): outcome_dates[h][i] if isinstance(outcome_dates[h][i], str) else None for h in HORIZONS},
            })
        result[name] = {"observations": observations,
                        "base": simulate(frame, entries, exit_mask),
                        "stress": simulate(frame, entries, exit_mask, STRESS_COST)}
    payload = {"dates": dates, "baseline": baseline, "strategies": result}
    dump_json(output / "ticker-results" / f"{ticker}.json.gz", payload)
    return ticker, payload


def net_pct(ratio, cost=COST):
    return (np.asarray(ratio) * (1 - cost) / (1 + cost) - 1) * 100


def drawdown(curve):
    values = np.asarray(curve, dtype=float)
    return float(np.min(values / np.maximum.accumulate(values) - 1) * 100)


def blocked_interval(monthly, seed=604):
    """Descriptive circular three-month block bootstrap, not a discovery test."""
    values = np.asarray(monthly, dtype=float)
    if len(values) < 6:
        return None
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(values), size=(2000, int(np.ceil(len(values) / 3))))
    indexes = ((starts[:, :, None] + np.arange(3)) % len(values)).reshape(2000, -1)[:, :len(values)]
    means = np.nanmean(values[indexes], axis=1)
    return [float(x) for x in np.nanquantile(means, [0.025, 0.975])]


def observation_summary(observations, start=None, end=None, horizon=20):
    rows = [o for o in observations if o["ratios"][str(horizon)] is not None
            and (start is None or o["date"] >= start)
            and (end is None or o["outcome_dates"][str(horizon)] < end)]
    if not rows:
        return {"n": 0}
    vals = net_pct([o["ratios"][str(horizon)] for o in rows])
    paired = [o for o in rows if o.get(f"excess_{horizon}") is not None]
    summary = {
        "n": len(rows), "tickers": len({o["ticker"] for o in rows}),
        "dates": len({o["date"] for o in rows}), "mean_net_pct": float(vals.mean()),
        "median_net_pct": float(np.median(vals)), "win_pct": float((vals > 0).mean() * 100),
        "mean_stress_pct": float(net_pct([o["ratios"][str(horizon)] for o in rows], STRESS_COST).mean()),
        "p05_net_pct": float(np.quantile(vals, .05)), "paired_n": len(paired),
    }
    if paired:
        df = pd.DataFrame(paired)
        excess = f"excess_{horizon}"
        daily = df.groupby("date")[excess].mean()
        monthly = daily.groupby(daily.index.str[:7]).mean()
        calendar = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M").astype(str)
        monthly = monthly.reindex(calendar)
        summary.update({"mean_excess_pp": float(df[excess].mean()),
                        "date_weighted_excess_pp": float(daily.mean()),
                        "month_weighted_excess_pp": float(monthly.mean()),
                        "positive_month_pct": float((monthly.dropna() > 0).mean() * 100),
                        "signal_months": int(monthly.notna().sum()),
                        "monthly_block_95_interval_pp": blocked_interval(monthly),
                        "monthly_excess_pp": {str(k): float(v) for k,v in monthly.dropna().items()}})
    return summary


def aggregate(output, specs, ticker_results, manifest):
    baseline = {}
    for ticker, payload in ticker_results.items():
        for group, rows in payload.get("baseline", {}).items():
            for row in rows:
                for j, h in enumerate(HORIZONS, 2):
                    if row[j] is None:
                        continue
                    key = (group, row[0], row[1], h)
                    total, count = baseline.get(key, (0.0, 0))
                    baseline[key] = total + row[j], count + 1
    all_dates = sorted({d for p in ticker_results.values() for d in p["dates"]})
    summary, all_observations, curves = [], {}, {}
    flagged = {r["ticker"] for r in manifest["coverage"] if r.get("extreme_daily_moves", 0)}
    for name, spec in specs.items():
        if spec["duplicate_of"]:
            continue
        observations, trades, equity, stress_equity, exposure = [], [], [], [], []
        for ticker, payload in ticker_results.items():
            r = payload["strategies"].get(name)
            if r is None:
                equity.append(pd.Series(1., index=all_dates))
                stress_equity.append(pd.Series(1., index=all_dates))
                exposure.append(pd.Series(0., index=all_dates))
                continue
            for obs in r["observations"]:
                for h in HORIZONS:
                    ratio = obs["ratios"][str(h)]
                    total, count = baseline.get((spec["group"], obs["date"], obs["trend"], h), (0, 0))
                    obs[f"excess_{h}"] = float(net_pct(ratio) - net_pct((total - ratio) / (count - 1))) if ratio is not None and count >= 11 else None
                observations.append(obs)
            trades.extend({"ticker": ticker, **t} for t in r["base"]["trades"])
            equity.append(pd.Series(r["base"]["equity"], index=payload["dates"]).reindex(all_dates).ffill().fillna(1))
            stress_equity.append(pd.Series(r["stress"]["equity"], index=payload["dates"]).reindex(all_dates).ffill().fillna(1))
            exposure.append(pd.Series(r["base"]["exposure"], index=payload["dates"], dtype=float).reindex(all_dates).ffill().fillna(0))
        portfolio = pd.concat(equity, axis=1).mean(axis=1)
        stress = pd.concat(stress_equity, axis=1).mean(axis=1)
        invested = pd.concat(exposure, axis=1).mean(axis=1)
        years = (pd.Timestamp(all_dates[-1]) - pd.Timestamp(all_dates[0])).days / 365.25
        late = observation_summary(observations, start=LATE_START)
        early = observation_summary(observations, end=LATE_START)
        enough = late.get("n", 0) >= 100 and late.get("tickers", 0) >= 30 and late.get("signal_months", 0) >= 12
        edge = late.get("month_weighted_excess_pp", float("-inf"))
        ci = late.get("monthly_block_95_interval_pp")
        if not spec["strategy"].exit_struct:
            rating = "Entry-only baseline"
        elif not enough:
            rating = "Insufficient evidence"
        elif edge <= 0:
            rating = "Weak versus matched peers"
        elif ci and ci[0] > 0 and early.get("month_weighted_excess_pp", 0) > 0:
            rating = "Promising historical candidate"
        else:
            rating = "Mixed / exploratory"
        closed = [t["net_pct"] for t in trades if t["status"] == "closed"]
        all_trade_vals = [t["net_pct"] for t in trades]
        late_curve = portfolio.loc[LATE_START:]
        prior_values = portfolio.loc[portfolio.index < LATE_START]
        late_base = float(prior_values.iloc[-1]) if len(prior_values) else 1.
        row = {
            "file": name, "rating": rating, "sha256": spec["sha256"],
            "signals": len(observations), "pending_20": sum(o["ratios"]["20"] is None for o in observations),
            "full": observation_summary(observations), "early": early, "late": late,
            "horizon_5": observation_summary(observations, start=LATE_START, horizon=5),
            "horizon_60": observation_summary(observations, start=LATE_START, horizon=60),
            "late_excluding_extreme_move_tickers": observation_summary([o for o in observations if o["ticker"] not in flagged], start=LATE_START),
            "yearly": {str(y): observation_summary(observations, start=f"{y}-01-01", end=f"{y+1}-01-01") for y in range(2022, 2027)},
            "closed_trades": len(closed), "open_marked_trades": len(trades) - len(closed),
            "mean_closed_trade_pct": float(np.mean(closed)) if closed else None,
            "mean_all_trade_pct": float(np.mean(all_trade_vals)) if all_trade_vals else None,
            "trade_win_pct_including_open_marks": float((np.array(all_trade_vals) > 0).mean() * 100) if trades else None,
            "mean_holding_sessions": float(np.mean([t["bars"] for t in trades])) if trades else None,
            "portfolio_return_pct": float((portfolio.iloc[-1] - 1) * 100),
            "portfolio_cagr_pct": float((portfolio.iloc[-1] ** (1 / years) - 1) * 100),
            "portfolio_max_drawdown_pct": drawdown(portfolio),
            "portfolio_stress_return_pct": float((stress.iloc[-1] - 1) * 100),
            "late_portfolio_return_pct": float((late_curve.iloc[-1] / late_base - 1) * 100),
            "late_portfolio_drawdown_pct": drawdown(np.r_[late_base, late_curve]),
            "mean_capital_fraction_exposed": float(invested.mean()),
        }
        summary.append(row)
        all_observations[name] = observations
        curves[name] = {"equity": portfolio.tolist(), "stress_equity": stress.tolist()}
        dump_json(output / f"trades-{Path(name).stem}.json.gz", trades)
    for name, spec in specs.items():
        if spec["duplicate_of"]:
            original = next(r for r in summary if r["file"] == spec["duplicate_of"])
            summary.append({**original, "file": name, "sha256": spec["sha256"], "duplicate_of": spec["duplicate_of"]})
    summary.sort(key=lambda r: (r["rating"] != "Entry-only baseline", r["late"].get("month_weighted_excess_pp", -999)), reverse=True)
    dump_json(output / "summary.json", {"manifest": manifest, "strategies": summary})
    dump_json(output / "observations.json.gz", all_observations)
    dump_json(output / "equity.json", {"dates": all_dates, "curves": curves})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    for folder in ("prices", "strategies", "ticker-results", "evaluator-source"):
        (args.output / folder).mkdir()
    for p in Path("strategies/dslx").glob("*.dslx"):
        shutil.copy2(p, args.output / "strategies" / p.name)
    for p in (Path(__file__), Path("src/ETF_screener/dslx.py"), Path("src/ETF_screener/slope.py")):
        shutil.copy2(p, args.output / "evaluator-source" / p.name)
    specs = load_specs(args.output / "strategies")
    config = json.loads(Path("config/nasdaq_focus.json").read_text(encoding="utf-8"))
    tickers = list(dict.fromkeys(config["tickers"]))[:args.limit]
    root = Path(get_paths()["data"]["parquet"])
    coverage, excluded = [], []
    for ticker in tickers:
        try:
            raw = (root / f"{ticker.lower()}_data.parquet").read_bytes()
            frame = pd.read_parquet(io.BytesIO(raw))
            frame = frame[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
            frame.Date = pd.to_datetime(frame.Date).dt.tz_localize(None).dt.normalize()
            frame = frame.loc[frame.Date <= AS_OF].reset_index(drop=True)
            if frame.empty or not frame.Date.is_unique or not frame.Date.is_monotonic_increasing:
                raise ValueError("Missing, duplicate or unsorted dates")
            if not np.isfinite(frame.iloc[:, 1:].to_numpy()).all() or (frame.iloc[:, 1:5] <= 0).any().any() or (frame.Volume < 0).any():
                raise ValueError("Invalid OHLCV values")
            if (frame.High + 1e-5 < frame[["Open", "Close", "Low"]].max(axis=1)).any() or (frame.Low - 1e-5 > frame[["Open", "Close", "High"]].min(axis=1)).any():
                raise ValueError("Invalid OHLC geometry")
            frame.to_parquet(args.output / "prices" / f"{ticker}.parquet", index=False)
            coverage.append({"ticker": ticker, "rows": len(frame), "start": str(frame.Date.iloc[0].date()),
                             "end": str(frame.Date.iloc[-1].date()), "input_sha256": hashlib.sha256(raw).hexdigest(),
                             "snapshot_sha256": hashlib.sha256((args.output / "prices" / f"{ticker}.parquet").read_bytes()).hexdigest(),
                             "extreme_daily_moves": int((frame.Close.pct_change().abs() > 1).sum())})
        except Exception as exc:
            excluded.append({"ticker": ticker, "error": str(exc)})
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "as_of": AS_OF,
                "universe": config, "requested_tickers": len(tickers), "coverage": coverage, "excluded": excluded,
                "warmup": WARMUP, "late_start": LATE_START, "horizons": HORIZONS,
                "cost_per_side": COST, "stress_cost_per_side": STRESS_COST,
                "selection_note": "Current liquid 400, not reconstructed historical membership; no independent out-of-sample claim",
                "price_note": "Cached OHLC, provider auto_adjust=False; price returns, cash dividends excluded",
                "rating_policy": "Later 20-session monthly matched excess; 100 observations, 30 tickers and 12 active months minimum for descriptive rating. Positive early and late excess plus positive block interval required for promising. No strategy is called validated."}
    dump_json(args.output / "manifest.json", manifest)
    print(f"Frozen {len(coverage)}/{len(tickers)} ticker histories and {len(specs)} strategies; excluded={excluded}", flush=True)
    started, results = time.monotonic(), {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks = [(str(args.output), row["ticker"]) for row in coverage]
        for i, (ticker, result) in enumerate(pool.map(evaluate_ticker, tasks), 1):
            results[ticker] = result
            print(f"{i}/{len(tasks)} {ticker} · elapsed {time.monotonic()-started:.0f}s", flush=True)
    summary = aggregate(args.output, specs, results, manifest)
    print(json.dumps([{k: r[k] for k in ("file", "rating", "signals")} for r in summary], indent=2))
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
