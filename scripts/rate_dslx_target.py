"""Measure +25% first-passage frequency within one calendar month of entry."""

import argparse
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rate_dslx_quality import COST, STRESS_COST, LATE_START, dump_json


def target_outcome(frame, entry_index, exit_date=None):
    """A next-open entry, with optional pre-existing strategy exit at an open."""
    if entry_index >= len(frame):
        return {"complete": False}
    date = frame.Date.iloc[entry_index]
    deadline = date + pd.DateOffset(months=1)
    complete = deadline <= frame.Date.iloc[-1]
    end = int(frame.Date.searchsorted(deadline, side="right"))
    entry = float(frame.Open.iloc[entry_index])
    target = entry * (1 + COST) * 1.25 / (1 - COST)
    stress_target = entry * (1 + STRESS_COST) * 1.25 / (1 - STRESS_COST)
    close_end = end
    exit_open = None
    if exit_date is not None:
        ix = int(frame.Date.searchsorted(pd.Timestamp(exit_date)))
        if ix < end:
            close_end = ix
            exit_open = float(frame.Open.iloc[ix])
    highs = frame.High.iloc[entry_index:close_end].to_numpy()
    closes = frame.Close.iloc[entry_index:close_end].to_numpy()
    high_candidates = np.r_[highs, exit_open] if exit_open is not None else highs
    high_max = float(np.max(high_candidates)) if len(high_candidates) else entry
    close_max = float(np.max(closes)) if len(closes) else entry
    hit = high_max >= target
    hit_offsets = np.flatnonzero(high_candidates >= target)
    return {
        "complete": bool(complete), "entry_date": str(date.date()),
        "deadline": str(deadline.date()), "intraday_net25": bool(hit),
        "close_net25": bool(close_max >= target),
        "intraday_gross25": bool(high_max >= entry * 1.25),
        "intraday_stress_net25": bool(high_max >= stress_target),
        "target_price": target,
        "peak_net_pct": (high_max / entry * (1 - COST) / (1 + COST) - 1) * 100,
        "first_hit_session": int(hit_offsets[0] + 1) if len(hit_offsets) else None,
    }


def cluster_interval(rows, field):
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["month"] = df.entry_date.str[:7]
    monthly = df.groupby("month")[field].agg(["sum", "count"])
    calendar = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M").astype(str)
    monthly = monthly.reindex(calendar).fillna(0)
    if len(monthly) < 6:
        return None
    rng = np.random.default_rng(625)
    starts = rng.integers(0, len(monthly), size=(2000, int(np.ceil(len(monthly) / 3))))
    ix = ((starts[:, :, None] + np.arange(3)) % len(monthly)).reshape(2000, -1)[:, :len(monthly)]
    totals = monthly["count"].to_numpy()[ix].sum(axis=1)
    hits = monthly["sum"].to_numpy()[ix].sum(axis=1)
    ratios = hits[totals > 0] / totals[totals > 0] * 100
    return [float(x) for x in np.quantile(ratios, [.025, .975])] if len(ratios) else None


def summarize(rows, start=None, end=None):
    selected = [r for r in rows if (start is None or r["entry_date"] >= start)]
    complete = [r for r in selected if r["complete"] and (end is None or r["deadline"] < end)]
    n = len(complete)
    result = {"n": n, "pending": sum(not r["complete"] for r in selected),
              "tickers": len({r["ticker"] for r in complete}),
              "entry_dates": len({r["entry_date"] for r in complete}),
              "active_months": len({r["entry_date"][:7] for r in complete})}
    if not n:
        return result
    for field in ("intraday_net25", "close_net25", "intraday_gross25", "intraday_stress_net25"):
        hits = sum(r[field] for r in complete)
        result[field] = {"hits": hits, "pct": hits / n * 100,
                         "block_95_interval_pct": cluster_interval(complete, field)}
    times = [r["first_hit_session"] for r in complete if r["intraday_net25"]]
    result["median_sessions_to_hit"] = float(np.median(times)) if times else None
    result["evidence"] = "Moderate historical sample" if n >= 100 and result["tickers"] >= 30 and result["active_months"] >= 12 and len(times) >= 20 else "Limited historical sample"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads((args.run / "summary.json").read_text(encoding="utf-8"))
    metadata = {r["file"]: r for r in original["strategies"]}
    observations, trades = {}, {}
    for number, path in enumerate(sorted((args.run / "ticker-results").glob("*.json.gz")), 1):
        ticker = path.name.removesuffix(".json.gz")
        frame = pd.read_parquet(args.run / "prices" / f"{ticker}.parquet")
        lookup = {str(d.date()): i for i, d in enumerate(frame.Date)}
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        cache = {}
        for name, result in payload["strategies"].items():
            dest = observations.setdefault(name, [])
            for obs in result["observations"]:
                index = lookup[obs["date"]] + 1
                if index >= len(frame):
                    # Keep the unfilled final signal explicitly pending.
                    dest.append({"ticker": ticker, "entry_date": obs["date"], "signal_date": obs["date"], "complete": False, "unfilled": True})
                    continue
                if index not in cache:
                    cache[index] = target_outcome(frame, index)
                dest.append({"ticker": ticker, "signal_date": obs["date"], **cache[index]})
            trade_dest = trades.setdefault(name, [])
            for trade in result["base"]["trades"]:
                index = lookup[trade["entry"]]
                exit_date = trade["exit"] if trade["status"] == "closed" else None
                trade_dest.append({"ticker": ticker, **target_outcome(frame, index, exit_date)})
        if number % 50 == 0:
            print(f"Calendar-month target evaluation: {number} tickers", flush=True)
    summary = []
    for name, rows in observations.items():
        r = {"file": name, "sha256": metadata[name]["sha256"],
             "full": summarize(rows), "early": summarize(rows, end=LATE_START),
             "late": summarize(rows, start=LATE_START),
             "actual_trades_full": summarize(trades[name]),
             "actual_trades_late": summarize(trades[name], start=LATE_START),
             "yearly": {str(y): summarize(rows, start=f"{y}-01-01", end=f"{y+1}-01-01") for y in range(2022, 2027)}}
        summary.append(r)
    for name, item in metadata.items():
        if item.get("duplicate_of"):
            original_row = next(r for r in summary if r["file"] == item["duplicate_of"])
            summary.append({**original_row, "file": name, "sha256": item["sha256"], "duplicate_of": item["duplicate_of"]})
    summary.sort(key=lambda r: r["late"].get("intraday_net25", {}).get("pct", -1), reverse=True)
    dump_json(args.run / "target25-summary.json", {"target_net_pct": 25, "window": "one calendar month from next-open entry", "cost_per_side": COST, "strategies": summary})
    dump_json(args.run / "target25-observations.json.gz", observations)
    dump_json(args.run / "target25-actual-trades.json.gz", trades)
    root = str(args.run.resolve()).replace("\\", "/")
    lines = ["# DSLX quality: probability of +25% within one month", "",
             f"Nasdaq US 400. Frozen prices through {original['manifest']['as_of']}; rules frozen on 2026-09-07.", "",
             "**Metric:** among entry signals with a complete calendar month of follow-up, the fraction "
             "whose price reaches a level allowing a **25% net gain** within that month. Entry is at the "
             "next session's actual open. Base all-in trading friction is 0.15% per side. The required "
             "raw price gain is therefore approximately 25.38%. A separate gross +25% column and closing-price "
             "check are included. These are historical hit rates, not calibrated future probabilities.", "",
             "A month runs from the entry date to the same calendar date in the following month "
             "(clamped to month-end when needed), including trading sessions on the deadline. A target "
             "touch uses the real daily high; the close check requires at least one daily close at or "
             "above target during the month. A daily high does not guarantee a real limit-order fill. "
             "Once a target is touched it counts even if the price later falls. The metric is not the "
             "return at the end of the month.", "",
             "The main table assesses each entry signal independently, ignoring the written exit so "
             "we can measure entry opportunity. The second table respects the written exit and the "
             "one-position-per-ticker rule. Pending entry signals and entries without a full month of "
             "price follow-up are excluded from probabilities and reported separately.", "",
             "## Main ranking: later-period entries, January 2025 onward", "",
             "| File | +25% net touch | Hits / complete signals | 95% block interval | Daily close +25% net | Gross +25% touch | Sample |",
             "| --- | ---: | ---: | --- | ---: | ---: | --- |"]
    for r in summary:
        s = r["late"]
        if not s["n"]:
            lines.append(f"| {Path(r['file']).stem} | — | 0 / 0 | — | — | — | No outcomes |")
            continue
        p = s["intraday_net25"]
        ci = p["block_95_interval_pct"]
        interval = f"{ci[0]:.1f}–{ci[1]:.1f}%" if ci else "—"
        sample = f"Duplicate: {Path(r['duplicate_of']).stem}" if r.get("duplicate_of") else s["evidence"]
        lines.append(f"| {Path(r['file']).stem} | **{p['pct']:.1f}%** | {p['hits']} / {s['n']} | {interval} | "
                     f"{s['close_net25']['pct']:.1f}% | {s['intraday_gross25']['pct']:.1f}% | {sample} |")
    lines += ["", "## Period stability and the written exits", "",
              "Actual-trade rates below use only the entries that would be taken while flat and require "
              "the target to be reached before the strategy's next-open exit. On an exit day only its "
              "opening price can qualify; a later intraday rally cannot. The denominator differs from "
              "the all-signal table, so the difference is not solely the effect of exits.", "",
              "| File | Full-period signal rate | Pre-2025 rate | Later rate | Later actual-trade rate before exit | Actual hits / trades | Pending signals |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in summary:
        if r.get("duplicate_of"):
            continue
        def pct(s):
            return f"{s['intraday_net25']['pct']:.1f}%" if s.get("n") else "—"
        actual = r["actual_trades_late"]
        lines.append(f"| {Path(r['file']).stem} | {pct(r['full'])} | {pct(r['early'])} | {pct(r['late'])} | "
                     f"{pct(actual)} | {actual.get('intraday_net25', {}).get('hits', 0)} / {actual['n']} | {r['full']['pending']} |")
    lines += ["", "## Interpretation", "",
              "- The 95% intervals resample three-calendar-month blocks 2,000 times with a fixed seed. "
              "All signals in sampled months stay together. Intervals are descriptive, not corrected "
              "for comparing many strategies; persistent ticker/sector dependence remains.",
              "- A moderate historical sample requires at least 100 later complete observations, 30 "
              "tickers, 12 active months and 20 successes. This is a reporting convention, not validation. "
              "A large rate from a small number of signals is not a reliable winner.",
              "- Current-universe selection/survivorship bias is substantial: these are today's liquid "
              "400, not all stocks that could have been traded historically. The later period is a "
              "historical check, not genuinely unseen testing. Cash dividends are excluded.",
              "- The target metric was chosen by the user while the initial broader review was running, "
              "before this target analysis. It replaces the 20-session mean-return ranking as the user's "
              "primary objective; it was not selected by searching outcome horizons for the best score.",
              "- Overlapping signals are counted separately. A higher target hit rate need not imply "
              "positive expectancy: loss sizes, stops, holding time and exits still matter. See the "
              "separate broad quality report for full-position returns, drawdown and capital use.",
              "- `simple_green` is an entry-only baseline with no exit rule; its actual-trade count is "
              "small after the initial purchases because it then keeps holding. Duplicated files add no evidence.",
              "", "## Artifacts", "",
              f"- [All probability metrics, period splits, yearly results and source hashes]({root}/target25-summary.json)",
              f"- [Individual signal target outcomes]({root}/target25-observations.json.gz)",
              f"- [Actual-trade target outcomes]({root}/target25-actual-trades.json.gz)",
              f"- [Frozen inputs and audit manifest]({root}/manifest.json)",
              "- Reproduce: `.venv/Scripts/python.exe scripts/rate_dslx_target.py RUN_DIRECTORY --report reference/dslx-target25-review.md`."]
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    unique = [r for r in summary if not r.get("duplicate_of") and r["late"].get("n")]
    fig, ax = plt.subplots(figsize=(11, 7))
    for i, r in enumerate(unique):
        p = r["late"]["intraday_net25"]
        color = "#177d68" if r["late"]["evidence"].startswith("Moderate") else "#ad8544"
        ax.barh(i, p["pct"], color=color)
        ci = p["block_95_interval_pct"]
        if ci:
            ax.plot(ci, [i, i], color="#253243", linewidth=1.4)
        ax.text(99, i, f"{p['hits']}/{r['late']['n']}", va="center", ha="right", fontsize=9)
    ax.set_yticks(range(len(unique)), [Path(r["file"]).stem.replace("ha_", "") for r in unique])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Historical probability of +25% net intraday touch within one calendar month (%)")
    ax.set_title("DSLX target-hit rates · Nasdaq US 400\nEntries from Jan 2025; complete follow-up only", loc="left", pad=18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=.15)
    ax.set_axisbelow(True)
    fig.text(.02, .015, "Green: moderate historical sample. Amber: limited sample. Lines: descriptive 95% block intervals. Current-universe bias applies.", fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(args.run / "target25-probability.png", dpi=160)
    print(json.dumps([{ "file": r["file"], "late": r["late"]} for r in summary], indent=2))
    print(args.report)


if __name__ == "__main__":
    main()
