# DSLX: collection-oriented language design

## Purpose

This is a proposal for **DSLX**, the next generation of the screening and
strategy DSL. The name distinguishes this collection-oriented language from the
existing expression DSL, allowing both to coexist during a gradual migration.
It treats a market data scope as nested, typed collections instead of evaluating
only a flat expression against one ticker dataframe.

The central question becomes:

> Which tickers in this universe satisfy a condition formed from their ordered
> candle history, and how should the matching tickers be ranked?

The same condition must work in both places:

- **Screener:** evaluate it at the latest finalized candle for every ticker.
- **Backtest:** evaluate it at each historical finalized candle, without access
  to data that was unavailable at that point.

This is inspired by LINQ's composable collection operations, not by a chart-first
language such as Pine Script.

## Domain model

```text
Universe
  └── TickerList
        └── Ticker
              └── CandleSeries (one series per timeframe)
                    └── Candle
```

### Universe

A `Universe` is an ordered collection of eligible `Ticker` objects. Examples
include the Xetra universe, Nasdaq universe, an explicit user list, or the
current backtest scope.

### Ticker

A `Ticker` represents one instrument and owns candle series by timeframe.

```dsl
ticker.symbol
ticker.name
ticker.candles("1d")
```

`ticker.candles` may be an allowed shorthand when the query has a declared
default timeframe.

### CandleSeries

A `CandleSeries` is an immutable, chronological series for exactly one ticker
and one timeframe. Its timestamps are unique and its order is always oldest to
newest.

```dsl
ticker.candles("1d").last
ticker.candles("1d").ending_at(candle)
```

### Candle

A finalized candle is an immutable value object.

```dsl
candle.timeframe
candle.timestamp
candle.open
candle.high
candle.low
candle.close
candle.volume
candle.age
```

At its selected timeframe, a candle is DSLX's atomic market observation and
decision point. It represents a time interval in the underlying market, but a
rule evaluates it as one focal event. Every directly visible characteristic and
every derived value is anchored to that event.

`age` is relative to the query's evaluation endpoint: `0` is the endpoint
candle, `1` is the preceding trading bar, and so on.

A live, still-forming bar is a separate provisional snapshot. It must not be
silently treated as a finalized `Candle`.

### Candle geometry

Every visual part of a candle is also available as a numeric property. These
properties are calculated from the candle's exposed OHLC values, so they work
for regular candles and for Heikin-Ashi candles represented by transformed
OHLC values.

| Property | Meaning |
| --- | --- |
| `color` | `"green"`, `"red"`, or `"doji"` |
| `is_green`, `is_red`, `is_doji` | Explicit colour/state predicates |
| `total_length` (or `range`) | `high - low`, including wicks |
| `body_length` | `abs(close - open)` |
| `upper_wick_length` | `high - max(open, close)` |
| `lower_wick_length` | `min(open, close) - low` |
| `body_ratio` | `body_length / total_length` |
| `upper_wick_ratio` | `upper_wick_length / total_length` |
| `lower_wick_ratio` | `lower_wick_length / total_length` |

The three ratios are fractions in the range `0..1` and sum to `1` for a
non-zero-length candle. A zero-length candle returns `0` for every ratio,
which keeps comparisons deterministic.

```dsl
# Green Heikin-Ashi candle with a dominant lower wick
candle.color == "green"
AND candle.lower_wick_ratio > 0.50
AND candle.body_ratio < 0.30
```

### Derived values and indicators

OHLCV fields are properties because they are values belonging to one candle.
An indicator takes configuration and is therefore a method/function:

```dsl
candle.ema(20)
candle.rsi(14)
candle.atr(14)
candle.sma("close", 50)
```

Although an indicator is written on a candle for convenience, it is calculated
from the candle's owning `CandleSeries`, ending at that candle. Thus
`candle.ema(20)` never uses later bars.

An indicator has no standalone identity in a rule: `candle.rsi(14)` means the
RSI known at this particular candle's close. This makes the candle the common
time anchor for all OHLC, visual, volume, and technical-analysis conditions.

## Collection types and guarantees

Not every list has the same temporal guarantees. The runtime should retain that
information in its types instead of relying on strategy authors to remember it.

| Type | Ordering | Consecutive trading bars | Typical producer |
| --- | --- | --- | --- |
| `Universe` / `TickerList` | stable ticker order | n/a | source selection |
| `CandleSeries` | chronological | yes | `ticker.candles("1d")` |
| `CandleWindow` | chronological | yes | `candle.window(5)` |
| `FilteredCandles` | chronological | not guaranteed | `series.where(...)` |
| `ValueSequence` | follows source unless sorted | depends on source | `series.select(...)` |

"Consecutive" means adjacent available trading bars at the series timeframe.
For daily data, Friday followed by Monday is consecutive. A detected missing
expected trading bar is a data-quality gap, not a reason to reinterpret calendar
days as bars.

## Temporal navigation

All navigation is relative to a focal candle and points backward in time:

```dsl
candle.previous(1)            # the preceding completed bar
candle.previous(2)
candle.window(3)              # [previous(2), previous(1), candle]
candle.window(20).high.max()
```

`window(n)` produces a `CandleWindow`: an ordered, contiguous slice ending at
the focal candle. It fails or returns no match when there is insufficient valid
history, depending on the final null/insufficient-history policy.

Filtering is intentionally different:

```dsl
ticker.candles.where(c => c.close > c.open)
```

This preserves chronological order but may skip bars, so it returns
`FilteredCandles`, not a `CandleWindow`. It must not be used as a hidden
substitute for "three consecutive green candles".

## Query operations

Collection operations are LINQ-like and composable:

```dsl
where(predicate)
select(projection)
any(predicate)
all(predicate)
count(predicate)
order_by(key)
order_by_desc(key)
take(n)
first
last
```

Operations document what they preserve:

- `where(...)` preserves order but may lose consecutiveness.
- `window(n)` creates a consecutive window.
- `take(n)` preserves the guarantees of its input.
- `order_by(...)` establishes the requested sort order; it is no longer
  chronological unless sorting by timestamp.
- `select(...)` produces derived values rather than candles.

## Examples

### Three consecutive green candles

```dsl
universe
  .where(t =>
    t.candles.last.window(3).all(c => c.close > c.open)
  )
```

`window(3)` is crucial: filtering for green candles and taking three would not
require the bars to be adjacent.

### Rising three-bar close sequence

```dsl
universe
  .where(t => {
    let bars = t.candles.last.window(3)
    bars[0].close < bars[1].close < bars[2].close
  })
```

Window indexing is always oldest to newest.

### Breakout with a volume confirmation

```dsl
universe
  .where(t => {
    let c = t.candles.last
    c.close > c.previous(1).window(20).high.max()
    AND c.volume > c.previous(1).window(20).volume.average() * 1.5
  })
```

The prior-bar anchor deliberately excludes the current candle from the
20-bar breakout and average-volume reference windows.

### Screen and rank

```dsl
universe
  .where(t => {
    let c = t.candles.last
    c.close > c.ema(200)
    AND c.rsi(14) > 50
    AND c.window(3).all(bar => bar.close > bar.open)
  })
  .order_by_desc(t => t.candles.last.rsi(14))
  .take(25)
  .select(t => {
    ticker: t.symbol,
    close: t.candles.last.close,
    rsi_14: t.candles.last.rsi(14)
  })
```

### A named reusable predicate

```dsl
predicate bullish_three_bar_setup(ticker) =
  ticker.candles.last.window(3).all(c => c.close > c.open)
  AND ticker.candles.last.close > ticker.candles.last.ema(20)

universe
  .where(t => bullish_three_bar_setup(t))
  .order_by_desc(t => t.candles.last.rsi(14))
```

The predicate can be evaluated at the current endpoint for a screener or at
each historical endpoint for a backtest.

## Entry and exit constructs

DSLX should make trade lifecycle rules explicit rather than treating entry and
exit as unrelated boolean strings. An entry or exit can be either a one-candle
predicate or an ordered candle pattern.

### One-candle rules

```dsl
strategy trend_following {
  entry when candle => candle.close > candle.ema(20)
  exit  when candle => candle.close < candle.ema(20)
}
```

Here `candle` is a local variable bound to the current endpoint `Candle`
object. It is not a global candle, and it is evaluated only on finalized candles
unless a strategy explicitly opts into provisional-bar evaluation.

### Consecutive multi-candle patterns

An ordered list is a pattern over a consecutive `CandleWindow`. Each item is
matched against exactly one bar; the first item matches the oldest bar and the
last item matches the endpoint candle.

```dsl
strategy three_bar_reversal {
  entry sequence consecutive [
    candle => candle.close < candle.open,                 # oldest: red candle
    candle => candle.close > candle.open,                  # then green
    candle => candle.close > candle.open AND candle.close > candle.ema(20)
                                                           # trigger: green breakout
  ]

  exit when candle => candle.close < candle.ema(20)
}
```

This is equivalent in spirit to:

```dsl
let bars = candle.window(3)
bars[0].is_red
AND bars[1].is_green
AND bars[2].is_green
AND bars[2].close > bars[2].ema(20)
```

but the `sequence` form expresses intent directly and guarantees that the bars
are ordered and adjacent. It must never be implemented by filtering matching
candles and taking the last three.

### Named pattern steps

Steps can be named when later conditions need to compare them:

```dsl
entry sequence consecutive [
  pullback: candle => candle.close < candle.open,
  reclaim:  candle => candle.close > candle.open AND candle.close > pullback.high,
  trigger:  candle => candle.close > reclaim.high
                       AND candle.volume > candle.previous(1).volume
]
```

Each list item receives a distinct immutable `Candle` object from the matched
window. `pullback`, `reclaim`, and `trigger` name those distinct objects, so a
later step may compare itself with an earlier named candle. It may inspect its
own history or an earlier named step, but it cannot inspect a later step.

### Non-consecutive event patterns

Patterns are consecutive by default. If a strategy genuinely permits intervening
bars, that relaxation should be visible in the source:

```dsl
entry sequence within 10 bars [
  oversold: candle => candle.rsi(14) < 30,
  recovery: candle => candle.rsi(14) > 40
]
```

The runtime returns the matched candles and their bar distances, so reports can
explain the match. This construct is intentionally distinct from `consecutive`.

### Execution semantics

Pattern matching and trade execution are different events:

1. The final pattern step matches on the close of endpoint candle `t`.
2. By default, the resulting entry or exit order fills at the next executable
   candle's open (`t + 1`).
3. An explicit policy may instead request a close fill, limit order, or
   provisional-bar evaluation; those policies must be named in the strategy.
4. Exit rules are evaluated only while a position is open. Entry rules are
   evaluated only while no position is open, unless the strategy explicitly
   supports scaling or reversal.

For example:

```dsl
strategy three_bar_reversal {
  execution { entry: next_open, exit: next_open }

  entry sequence consecutive [
    candle => candle.is_red,
    candle => candle.is_green,
    candle => candle.is_green AND candle.close > candle.ema(20)
  ]

  exit when candle => candle.close < candle.ema(20)
}
```

Keeping the execution policy explicit avoids an otherwise common source of
optimistic backtests: assuming that a signal known only at a candle close could
also have traded at that same close.

## Evaluation rules

1. The evaluator receives one explicit endpoint candle per ticker.
2. A candle expression may inspect only its endpoint candle and earlier bars in
   the same series, unless a future-looking construct is explicitly introduced
   for research and prohibited in backtests.
3. Indicator values are calculated as-of the endpoint candle.
4. A screen applies a ticker predicate to every ticker in the selected universe.
5. A backtest replays that same predicate over each historical endpoint.
6. Finalized candles and windows are immutable during evaluation.

These rules make look-ahead bias difficult to express accidentally.

## Implementation direction

Python is suitable for the runtime and data model:

```text
Universe, TickerList, Ticker, CandleSeries, Candle, CandleWindow
```

The DSL should be parsed into an AST and evaluated by those types. Strategy text
must not be passed to unrestricted Python `eval`.

For performance, the public objects can be thin semantic wrappers around pandas,
NumPy, and precomputed indicator series. The execution engine should compile
common collection predicates into vectorized masks and only materialize small
windows when a sequence operation requires it. This keeps the language readable
while remaining practical for thousands of tickers.

## Open decisions

- Exact surface syntax for lambdas, local bindings, and object projections.
- How insufficient history and data-quality gaps are represented (`false`,
  `null`, or an explicit `unknown`).
- Multi-timeframe alignment rules, such as using a finalized weekly candle while
  evaluating a daily endpoint.
- Which indicators are built in versus user-definable.
- Whether ranking/projection belongs in the initial DSL release or follows after
  ticker predicates and windows are stable.
