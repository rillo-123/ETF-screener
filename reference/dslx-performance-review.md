# DSLX historical performance review

2026-09-06 — Exploratory results for the saved **Sweden Finance** list, 42 tickers.
No strategy has enough independent evidence here to be called a proven winner.

## Method

- Read existing SQLite history without refreshing or modifying it. All 42 tickers
  had data: 247 rows from 2025-09-08 through 2026-09-04, except NOBA (233 rows
  starting 2025-09-26).
- Require 200 prior candles before the beginning of each entry pattern. Usable
  one-candle signals start June 30; six-candle signals start July 7. Signals with
  a complete 20-session outcome end August 6 on the common calendar.
- Detect the written entry pattern on finalized Heikin-Ashi candles. Buy at the
  **next session's actual open** and measure the actual close of holding session
  20. Count all signals, including overlapping ones. Exclude unfinished outcomes
  and report their count separately.
- Model 0.1% adverse slippage and 5 quote-currency units commission per side,
  using 10,000 units initial notional per observation. These are assumptions,
  not verified broker costs. A flat-price round trip costs about 0.30%.
- Evaluate liquidity only on the historical data available at the signal date.
- Separately simulate one position per ticker using the written exit condition,
  filled at the next actual open. Do not add stops or targets. Report unresolved
  positions separately.
- This standardizes execution for a setup comparison; it deliberately does not
  reproduce the current dashboard's synthetic `at candle.close` fill behavior.

## Entry-quality observations

These are net returns **per signal over 20 sessions**, not portfolio returns.
Observations overlap; tickers and A/B share classes are correlated. All evidence
ratings remain low. Pending outcomes are excluded from the averages.

| File | Completed outcomes | Tickers | Mean net | Median net | Pending | Assessment |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| ha_breakout | 14 | 12 | +5.37% | +2.76% | 12 | First candidate for a broader test |
| ha_breakout_liquid_filtered | 14 | 12 | +5.37% | +2.76% | 12 | Same observed outcomes as breakout |
| ha_breakout_liquid_filtered_struct | 14 | 12 | +5.37% | +2.76% | 12 | Duplicate of liquid_filtered |
| ha_breakout_loose | 4 | 4 | +8.24% | +6.14% | 5 | Highest mean, far too few observations |
| ha_breakout_average | 3 | 3 | +2.48% | +2.24% | 2 | Insufficient evidence |
| ha_breakout_other | 3 | 3 | +2.48% | +2.24% | 2 | Duplicate of average |
| ha_breakout_early_days | 1 | 1 | +3.41% | +3.41% | 0 | Insufficient evidence |
| ha_red_to_green | 6 | 6 | +2.26% | +1.76% | 6 | Insufficient evidence |
| ha_three_strong_men | 52 | 22 | +1.45% | +0.11% | 33 | Weak against its context baseline here |
| ha_breakout_strict | 0 | 0 | — | — | 0 | No qualifying setups in this window |
| ha_dipfinder | 0 | 0 | — | — | 0 | No qualifying setups in this window |
| simple_green | 690 | 42 | +2.82% | +1.81% | 453 | Entry baseline; no exit rule |

For context, entering on every eligible date under the three-strong-men
liquidity/warm-up settings averaged +4.08%. That is a different date/ticker mix,
so the difference is not a matched excess-return estimate or statistical proof.
The corresponding baseline for ha_breakout was +4.39%. The simple_green baseline
has different liquidity requirements and is not a directly matched control.

## Written exits: completed trades only

These cannot be compared directly with the forward-return table: the horizons
and observations differ, and still-open positions are excluded. Negative
closed-trade averages alone do not establish that the exit is bad.

| File or identical-result group | Closed trades | Mean net per closed trade | Still open |
| --- | ---: | ---: | ---: |
| ha_breakout / both liquid_filtered files | 6 each | -0.93% | 14 each |
| ha_breakout_loose | 2 | -0.02% | 5 |
| ha_breakout_average / ha_breakout_other | 2 each | -3.08% | 3 each |
| ha_breakout_early_days | 0 | — | 1 |
| ha_red_to_green | 6 | -1.72% | 4 |
| ha_three_strong_men | 17 | -2.89% | 19 |
| ha_breakout_strict / ha_dipfinder | 0 | — | 0 |
| simple_green | 0 | — | 42 |

## Duplicates and identity

All 12 files parsed successfully. Comparing parsed rules while ignoring
strategy/universe labels found two exact duplicate pairs:

- `ha_breakout_average.dslx` and `ha_breakout_other.dslx`.
- `ha_breakout_liquid_filtered.dslx` and `ha_breakout_liquid_filtered_struct.dslx`.

There are 10 distinct parsed configurations. The original ha_breakout uses
stricter crossing inequalities than the liquid_filtered pair; identical results
in this sample do not make those rules exact duplicates. Several files reuse
internal strategy names, so future results should include the filename and
source-content hash. No strategy was changed, renamed, or deleted.

## Execution issues found in the existing backtester

`backtest_signals()` can emit a same-row entry at a Heikin-Ashi average price even
though the parsed execution setting defaults to `next_open`. The trade simulator
consumes that fill directly. In a synthetic reproduction, the final row had
actual open 120 and close 125, but the emitted entry price was 122.5 on that same
row, despite no next row being available.

Heikin-Ashi prices are synthetic. TradingView also explains why fills should use
actual market OHLC: [realistic backtests on Heikin-Ashi charts](https://www.tradingview.com/blog/en/new-features-pine-script-realistic-backtests-heikin-ashi-built-ins-for-symbol-info-39050/).

The existing DSLX backtest also filters a ticker using the full frame's final
liquidity window before evaluating its history. That is inappropriate for a
point-in-time historical eligibility comparison. This review used prefix-based
eligibility instead. Neither issue was changed in application code in this review.

## Classification to use

Keep **performance status** and **evidence strength** separate:

1. **Insufficient evidence:** no reliable sample or incomplete execution checks.
2. **Exploratory candidate:** encouraging observations needing independent validation.
3. **Weak in tested sample:** weaker observed performance against a comparable
   baseline, with the scope and uncertainty attached.
4. **Validated candidate:** positive net expectancy on genuinely unseen periods,
   a matched baseline comparison, acceptable drawdown, reasonable cost sensitivity,
   and stability across independent periods/instruments. None currently qualifies.

Track duplicates and entry-only baselines separately. Report entry outcomes,
full trade outcomes including marked-to-market open positions, sample counts,
independent dates/issuers, date range, universe, drawdown, costs, and source hash.
An arbitrary trade-count threshold alone does not establish confidence.

The next useful experiment needs several years of history plus indicator warm-up,
chronological validation periods, and rules frozen before inspecting validation
results. Today's saved list is not reconstructed historical membership. This
review has not eliminated selection/survivorship effects or independently audited
price adjustment and dividend treatment. It is not an out-of-sample test.

## Local reproduction artifacts

- [Detailed observations, coverage, and strategy hashes](../data/backtests/dslx_preliminary_classification.json).
- [Exact evaluator](../data/backtests/dslx_preliminary_evaluator.py). From the repo
  root: `.venv/Scripts/python.exe data/backtests/dslx_preliminary_evaluator.py`.

These data artifacts are local and may be ignored by Git. The evaluator is scoped
to the current single-strategy, selected-universe files and their breakdown exits;
it is not a replacement for the general backtester. Rerunning uses the then-current
saved list, strategy files, and SQLite history.
