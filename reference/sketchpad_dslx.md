# DSLX sketchpad: candle matching

## The central model

DSLX is not primarily a general-purpose query language. It is a **candle match
language**.

The runtime visits each eligible, finalized candle for every ticker in the
selected universe. It evaluates one complete predicate against that candle. If
the predicate is true, it emits a `Match` containing both the ticker and the
candle that was visible when the signal occurred.

```text
for each ticker in universe
  for each eligible finalized candle in ticker
    if every condition matches that candle
      emit Match(ticker, candle)
```

This makes the candle—not a list or a dataframe—the unit of evaluation. A
ticker can have more than one match, which is why the internal result is a
`MatchList`, rather than a `List<Ticker>`.

A candle is an atomic market observation at the selected timeframe: for a
daily scan it represents one trading day; for an hourly scan it represents one
hour. It occupies an interval in real time, but DSLX treats it as the single
focal event at which a decision is made. `open`, `high`, `low`, `close`,
volume, colour, body, and wicks describe what is directly visible at that
event.

Technical-analysis values have no independent identity in DSLX. An EMA, RSI,
ATR, or slope is meaningful only **at a particular focal candle** and is
computed from information available at or before that candle. In other words,
`candle.rsi(14)` means “the 14-period RSI known when this candle closed,” not
“an RSI series floating separately from candles.” This keeps every comparison
anchored to one observable market event and prevents future data from leaking
into a historical match.

For a normal screener, the eligible set is usually only the latest finalized
candle. A historical scan or backtest can select many endpoint candles. The
rule itself remains exactly the same in either case.

## Proposed declarative shape

The language should say what candle series to inspect and what a matching
candle looks like. It should not require users to allocate objects, create a
list, or write nested loops.

```dsl
strategy ha_breakout {
  source universe.etfs
  candles timeframe "1d" as heikin_ashi
  scan latest                         // use `within 30 candles` for history

  match when candle =>
    candle.open > candle.ema("low", 20)
    && candle.open < candle.ema("high", 20)
    && candle.close > candle.ema("high", 20)
    && candle.is_green
    && candle.rsi(14) > 50
    && candle.ema("close", 200).slope > 0
    && candle.rsi(14).slope > 0
    && candle.volume > candle.volume_ema(20) * 1.5
    && candle.ema("close", 20) >= 10
}
```

### Universe sources and GUI selection

`source` defines the universe for that strategy. `universe.selected` is the
explicit bridge to the GUI: it uses whichever universe the user has selected
when the strategy is run (for example Xetra, Nasdaq, Sweden, or a saved ticker
list).

```dsl
source universe.selected       // honour the user's current GUI selection
```

A concrete source is self-contained and overrides the GUI selection. It is
therefore reproducible when the same strategy is run from another screen,
scheduled job, or backtest.

```dsl
source universe.nasdaq         // always scan the Nasdaq universe
source universe.xetra          // always scan the Xetra universe
source universe.sweden         // always scan the Sweden universe
source universe.etfs           // all configured ETF universes
```

The precedence rule is simple: the strategy's concrete source wins;
`universe.selected` is the only source that intentionally inherits GUI state.
The host should alert the user if `universe.selected` is used without a current
GUI selection.

### Named liquidity universes

Liquidity is an eligibility property of an instrument, not a signal on the
candle that happens to match a strategy. Define it once at program level, then
use the resulting named universe from one or more strategies:

```dsl
universe xetra_liquid {
  from universe.xetra
  require liquidity {
    avg_turnover(20) >= 1_000_000
    median_turnover(20) >= 500_000
    active_sessions(20) >= 15
    active_sessions(5) >= 3
  }
}

strategy ha_breakout {
  source universe.xetra_liquid
  candles timeframe "1d" as heikin_ashi
  scan latest

  match when candle => candle.is_green && candle.rsi(14) > 50
}
```

`turnover` is `close × volume` in the listing currency. The host evaluates all
`require liquidity` clauses from finalized OHLCV history before it evaluates a
strategy. A ticker must satisfy every clause. This deliberately avoids putting
an instrument-quality rule inside `match when`, which must remain a predicate
about one focal candle.

`as heikin_ashi` means that `open`, `high`, `low`, `close`, colour, body, and
wicks all refer to the transformed candle that is drawn. There is no mix of
regular OHLC values and Heikin-Ashi visual properties within the rule.

The expression after `match when` is one boolean predicate. All `&&` clauses
therefore apply to the **same candle**. Methods such as `previous(1)` and
`window(3)` are the explicit way to inspect earlier candles.

### Adjacent candle patterns

Define named candle objects independently, then place them in an
`entrystruct` or `exitstruct` to give them consecutive time positions. The
definition order has no time meaning. Struct order is oldest to newest, and
the final member is the most recent candle at the scan endpoint:

```dsl
candle setup {
  when => is_red
}

candle recovery {
  when => is_green && low > setup.low
}

candle breakout {
  when => is_green && close > recovery.high
}

entrystruct {
  setup
  recovery
  breakout
  at breakout.close
}
```

For a match ending at candle `t`, that struct binds `setup` to `t-2`,
`recovery` to `t-1`, and `breakout` to `t`. Every member must match its bound
candle. Named objects may reference themselves or earlier members of the same
struct. A missing member or a later/forward reference is rejected while the
program is parsed; DSLX never inserts hidden candles automatically.

The legacy `candle.previous(n)` form remains supported for compatibility and
`window(n)` remains useful when one uniform condition applies to a range:

```dsl
entry when candle => candle.window(3).all(c => c.is_green)
```

If the requested prior candle or window is outside available history, the
strategy simply does not match at that point.

### Position-aware exits

Exit rules can inspect the price at which the current simulated position was
opened. This lets a strategy express a fixed profit target directly:

```dsl
entry at candle.close when candle => candle.is_green
exit when candle => candle.high >= position.entry_price * 1.03
```

`position.entry_price` is available only in an exit rule while a position is
open. `entry at candle.close` explicitly declares the entry fill price; omit
`at ...` to retain the default close price. The price expression can use any
property of the entry candle, such as `candle.open`, `candle.close`, or an EMA.
It uses the strategy's simulated entry price before transaction costs;
the backtester still applies its configured slippage and commission to fills.

## Result model

```text
Match
  strategy               # strategy definition that emitted this match
  ticker
  candle                 # the exact matched HA candle
  timeframe
  timestamp
  age                    # 0 for the scan endpoint
  values / diagnostics   # optional values used for explanation and ranking

MatchList
  one Match per qualifying ticker/candle pair
```

The screener UI may project a `MatchList` to one row per ticker, normally using
its newest match. A backtest keeps every match because the timestamp and
matched candle are part of its trading history.

When the GUI presents matches, it should render `match.strategy` as a small
strategy badge. A one-match row has one badge. If the UI groups several matches
into one ticker row, it shows one badge for each distinct originating strategy;
it must not arbitrarily pick one and discard the others. Hovering or opening a
row should identify the strategy, timeframe, matched timestamp, and focal
candle values that caused each badge.

## Running, combining, and showing match lists

A strategy declaration is a reusable, pure definition. It does not show a UI
or mutate a global result list while it runs. Calling `run()` evaluates the
strategy against its declared source and returns a `MatchList`.

```dsl
let list1 = ha_breakout.run()
let list2 = lower_wick_reversal.run()

let big_list = list1 + list2
big_list.show()
```

`show()` is a host-output method: in the dashboard it opens or replaces the
results view; in a command-line host it can render a table. It does not change
the matches, so it is deliberately outside the `strategy { ... }` block.

`+` combines match lists in left-to-right order. It retains strategy provenance,
so if the same ticker and candle match two different strategies, the combined
list contains two matches and the UI can explain both. It does not silently
deduplicate by ticker. Explicit display operations can later choose to group or
deduplicate the list, for example `big_list.group_by_ticker().show()`.

The language convention is lower snake case, matching candle properties such
as `is_green` and `upper_wick_ratio`; therefore use `big_list.show()`, rather
than C#-style `bigList.Show()`.

## Why this is preferable to the imperative sketch

The following is the runtime's job, not DSLX source:

```text
new Candle()
new Universe()
new List<Ticker>()
foreach ticker
  foreach candle
    if conditions
      add ticker
```

It also hides two key requirements: which candles are eligible, and which
candle generated the signal. The declarative form makes both explicit while
remaining centered on the candle the trader sees.

## Open implementation questions

- Whether `scan latest` is the default, or must always be declared.
- Exact indicator API: source-aware `candle.ema("high", 20)` is clearer than
  names such as `ema_high(20)`, because it retains the focal candle as the
  owner of the value.
- Whether `.slope` means one-bar absolute change, percentage change, or a
  configurable regression slope. It should be defined once and used uniformly.
- How matches are ranked and de-duplicated when a screener needs one result per
  ticker.
