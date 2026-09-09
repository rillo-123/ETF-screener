"""Render a completed rate_dslx_quality.py run into Markdown and a static chart."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def number(value, digits=2, signed=False):
    if value is None:
        return "—"
    return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads((args.run / "summary.json").read_text(encoding="utf-8"))
    rows, manifest = payload["strategies"], payload["manifest"]
    coverage = manifest["coverage"]
    unique = [r for r in rows if not r.get("duplicate_of")]
    ranked = [r for r in unique if r["rating"] != "Entry-only baseline"]
    enough = sum(c["rows"] > manifest["warmup"] for c in coverage)
    earliest = min(c["start"] for c in coverage)
    flagged = [c["ticker"] for c in coverage if c["extreme_daily_moves"]]
    skipped = [c["ticker"] for c in coverage if c["rows"] <= manifest["warmup"]]
    path = str(args.run.resolve()).replace("\\", "/")
    lines = [
        "# DSLX strategy quality — Nasdaq US 400",
        "",
        f"Research snapshot: {manifest['created_utc'][:10]}. Prices through **{manifest['as_of']}**.",
        "",
        "These ratings describe historical evidence in today's selected Nasdaq universe. "
        "They are not a forecast or proof that a strategy will make money. Entry selection "
        "and the written exit behavior are shown separately. No strategy is classified as validated.",
        "",
        "## Scope and execution",
        "",
        f"- {len(rows)} files, {len(unique)} distinct parsed configurations, including an entry-only baseline.",
        f"- {len(coverage)} frozen ticker histories; {sum(c['rows'] for c in coverage):,} rows, "
        f"from {earliest} through {manifest['as_of']}. {enough} tickers have enough warm-up history.",
        "- Rules were frozen before this run. Every strategy uses the same 257-candle warm-up: "
        "252 prior candles before the longest six-candle entry pattern. Shorter patterns use the same start.",
        "- Signals use the saved daily Heikin-Ashi conditions. All research entry/exit fills use the "
        "next session's actual OHLC open, with one position per ticker. Explicit synthetic `at candle.close` "
        "fills are intentionally replaced for an executable comparison; this does not reproduce dashboard P&L.",
        "- Base trading friction: 0.15% per side, all-in proportional commission/slippage assumption. "
        "Stress friction: 0.35% per side. No leverage, borrow costs, taxes or FX conversion. Cash earns zero.",
        "- Cached provider OHLC is used as stored (`auto_adjust=False`). Returns exclude cash dividends; "
        "corporate-action treatment has not been independently audited. No new Yahoo downloads were made.",
        "- Liquidity rules use rolling historical windows at each signal date. Existing positions still "
        "evaluate exits even when a ticker subsequently fails liquidity requirements.",
        "",
        "## Entry ranking",
        "",
        "The primary outcome is net return from the next real open to the close of holding session 20. "
        "Five- and 60-session outcomes are supporting sensitivity checks. All signals count, including "
        "overlapping signals; these are entry observations, not independent trades or a portfolio return.",
        "",
        "For each signal, the matched baseline is the equal-weight return of *other* current-universe "
        "stocks on the same date, passing the same historical liquidity rules and having the same "
        "nonnegative/negative Heikin-Ashi EMA200 slope state. At least ten peers with a completed "
        "outcome are required. The signal stock is removed from its own baseline. This controls for date "
        "and broad trend state, but not sector, volatility, size or every source of risk.",
        "",
        "Early period: outcomes completed before 2025-01-01. Later period: signals on/after 2025-01-01. "
        "Early signals whose outcomes cross the split are excluded from the early comparison. "
        "The later period is a historical robustness check, **not genuinely unseen out-of-sample data**: "
        "these rules and today's universe were created with knowledge of recent markets.",
        "",
        "The ranking orders later-period *month-weighted matched excess*: average excess across signals "
        "within each day, then days within each active month, then months equally. This reduces the "
        "influence of crowded signal dates. The 95% interval uses 2,000 circular three-calendar-month "
        "block-bootstrap draws, with a fixed seed. It is descriptive, not corrected for testing multiple "
        "strategies; it does not remove persistent issuer/sector dependence.",
        "",
        "| File | Historical rating | Later outcomes | Tickers | Mean net 20d % | Monthly matched excess, pp | Descriptive 95% interval, pp |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in rows:
        late = r["late"]
        ci = late.get("monthly_block_95_interval_pp")
        interval = f"[{number(ci[0], signed=True)}, {number(ci[1], signed=True)}]" if ci else "—"
        rating = f"Duplicate of {Path(r['duplicate_of']).stem}" if r.get("duplicate_of") else r["rating"]
        lines.append(f"| {Path(r['file']).stem} | {rating} | {late.get('n', 0)} | {late.get('tickers', 0)} | "
                     f"{number(late.get('mean_net_pct'), signed=True)} | "
                     f"{number(late.get('month_weighted_excess_pp'), signed=True)} | {interval} |")
    lines += [
        "",
        "Descriptive labels were defined before this run: fewer than 100 later outcomes, 30 tickers or "
        "12 active months is **insufficient evidence**. With that minimum, nonpositive later matched "
        "excess is **weak versus matched peers**. Positive early and late excess with a positive lower "
        "bootstrap bound is a **promising historical candidate**; other positive cases are **mixed / exploratory**. "
        "These minimums are screening conventions, not statistical guarantees. Labels rate entry selection; "
        "the exit/portfolio table below is required before judging the complete strategy.",
        "",
        "## Stability and entry risk",
        "",
        "| File | Early excess pp | Later excess pp | Later 5d excess pp | Later 60d excess pp | Later win % | Later 5th-percentile net % | Excluding flagged stocks, excess pp |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in unique:
        fields = [r["early"].get("month_weighted_excess_pp"), r["late"].get("month_weighted_excess_pp"),
                  r["horizon_5"].get("month_weighted_excess_pp"), r["horizon_60"].get("month_weighted_excess_pp"),
                  r["late"].get("win_pct"), r["late"].get("p05_net_pct"),
                  r["late_excluding_extreme_move_tickers"].get("month_weighted_excess_pp")]
        lines.append(f"| {Path(r['file']).stem} | " + " | ".join(number(v) for v in fields) + " |")
    lines += [
        "",
        "## Written exits and capital use",
        "",
        "Each of the 400 stocks receives an equal initial cash sleeve. Each sleeve compounds its "
        "own trades and is fully invested only while its strategy holds a position; money is not "
        "redistributed between sleeves. Ineligible/new stocks remain cash. This is a transparent "
        "unlevered model, not an optimized portfolio. Results include the initial warm-up period in "
        "cash. Unequal exposure matters: a mostly inactive strategy can have a small drawdown merely "
        "because most of its capital stays in cash.",
        "",
        "Unfinished positions are marked at the final real close with estimated exit costs, not discarded. "
        "The all-position mean includes those marks. Per-position means are equally weighted and are "
        "not annualized. The stress case uses the same signal/exit dates with higher friction.",
        "",
        "| File | Closed | Open marked | Mean position net % | Mean holding sessions | Full sleeve portfolio return % | Max drawdown % | Stress return % | Mean invested % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in unique:
        lines.append(f"| {Path(r['file']).stem} | {r['closed_trades']} | {r['open_marked_trades']} | "
                     f"{number(r['mean_all_trade_pct'])} | {number(r['mean_holding_sessions'], 1)} | "
                     f"{number(r['portfolio_return_pct'])} | {number(r['portfolio_max_drawdown_pct'])} | "
                     f"{number(r['portfolio_stress_return_pct'])} | {number(r['mean_capital_fraction_exposed'] * 100)} |")
    lines += [
        "",
        "`simple_green` has no exit rule; its marked positions represent an entry-only buy-and-hold-like "
        "baseline, not a complete trading strategy. Identical files share results; duplicated tests do "
        "not add evidence. Ranking by the largest raw return alone would reward market exposure and "
        "extreme winners as well as useful signals.",
        "",
        "## Coverage and limitations",
        "",
        "- This is the **current liquid Nasdaq 400**, selected using recent trading activity. Delisted "
        "stocks, former constituents and stocks that became illiquid are not reconstructed. "
        "Selection/survivorship bias applies to both strategies and matched peers.",
        "- Signals overlap, stocks share market/sector risk, and multiple share classes can represent "
        "the same issuer. Counts are not independent sample sizes. The 2025–2026 diagnostic period "
        "covers fewer than two years and cannot establish performance across all market regimes.",
        "- Point-in-time liquidity and next-open execution remove specific look-ahead problems, "
        "but do not establish a realistic market-impact model or repair provider history.",
        f"- Insufficient warm-up ({len(skipped)}): {', '.join(skipped)}.",
        f"- Stocks with at least one absolute daily close-to-close move over 100% ({len(flagged)}): " + ", ".join(flagged) + ". They remain in the main results; the sensitivity column excludes their signals. "
        "The peers remain the same in that sensitivity check, so it is an influence diagnostic, not a cleaned-data backtest.",
        "- Five- and 60-session checks use different completed-observation subsets. Missing future "
        "outcomes are omitted and pending counts are retained in JSON. No indicator or strategy "
        "parameter was tuned using these results.",
        "",
        "## Reproduction and artifacts",
        "",
        f"- [Full metrics and manifest]({path}/summary.json)",
        f"- [Frozen input coverage and hashes]({path}/manifest.json)",
        f"- [Detailed signal observations, compressed JSON]({path}/observations.json.gz)",
        f"- [Portfolio curves]({path}/equity.json)",
        f"- Frozen strategy files, price snapshots, evaluator source and per-ticker results are in `{path}`.",
        "- Evaluator: `scripts/rate_dslx_quality.py`; renderer: `scripts/report_dslx_quality.py`.",
        "- To run on current inputs, choose a new output directory: "
        "`.venv/Scripts/python.exe scripts/rate_dslx_quality.py --output F:/ETF-screener-data/research/NEW-RUN --workers 2`.",
        "",
        "## Method references",
        "",
        "Synthetic Heikin-Ashi prices are unsuitable as assumed executable fills; see "
        "[TradingView's explanation](https://www.tradingview.com/support/solutions/43000481029-strategy-produces-unrealistic-results-on-non-standard-chart-types-heikin-ashi-renko-etc/).",
        "",
        "Choosing winners from many backtests creates selection/overfitting risk; see "
        "[Bailey et al., The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). "
        "This report does not estimate that probability or claim its intervals correct for strategy selection.",
    ]
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    valid = [r for r in ranked if r["late"].get("month_weighted_excess_pp") is not None]
    labels = [Path(r["file"]).stem.replace("ha_", "") for r in valid]
    values = np.array([r["late"]["month_weighted_excess_pp"] for r in valid])
    fig, ax = plt.subplots(figsize=(11, max(5, .55 * len(valid) + 2)))
    colors = ["#137d63" if v > 0 else "#b94d56" for v in values]
    ax.barh(np.arange(len(valid)), values, color=colors, alpha=.85)
    for i, r in enumerate(valid):
        interval = r["late"].get("monthly_block_95_interval_pp")
        if interval:
            ax.plot(interval, [i, i], color="#263343", linewidth=1.4)
            ax.plot([interval[0], interval[1]], [i, i], "|", color="#263343", markersize=9)
    ax.set_yticks(np.arange(len(valid)), labels)
    ax.invert_yaxis()
    ax.axvline(0, color="#697581", linewidth=.8)
    ax.set_xlabel("Net 20-session excess over matched peers (percentage points; months equally weighted)")
    ax.set_title("DSLX entry quality · Nasdaq US 400\nLater period: Jan 2025–Sep 2026; descriptive 95% block intervals", loc="left", pad=18)
    ax.grid(axis="x", alpha=.18)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(.02, .015, "Current-universe selection bias applies. Historical diagnostics, not validated future returns. Duplicates and entry-only baseline omitted.", fontsize=8, color="#52606d")
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(args.run / "entry-quality.png", dpi=160)
    plt.close(fig)
    print(args.report)
    print(args.run / "entry-quality.png")


if __name__ == "__main__":
    main()
