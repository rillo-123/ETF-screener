# Normalized EMA Slope

## Purpose

The screener needs a way to describe the slope of a moving average that is comparable across securities with very different prices and currencies.

A raw EMA slope such as:

```text
(EMA_today - EMA_previous) / days
```

has units such as USD/day, SEK/day, or EUR/day. This makes values difficult to compare between securities.

Instead, normalize the change by the EMA's own value.

## Definition

For an EMA with period `p`, measure its change over a slope window of `w` trading days:

```text
slope(ema(p), w)
```

Define:

```text
slope = ((EMA[t] / EMA[t-w]) - 1) / w
```

or, expressed as percent per trading day:

```text
slopePercent = 100 * ((EMA[t] / EMA[t-w]) - 1) / w
```

Example:

```text
EMA[t-20] = 100
EMA[t]    = 102

slope = 100 * ((102 / 100) - 1) / 20
      = 0.10 % / trading day
```

## Units

The ratio:

```text
EMA[t] / EMA[t-w]
```

is dimensionless because both values have the same price unit.

Therefore the slope is independent of whether the security trades in USD, SEK, EUR, etc., and independent of the absolute share price.

However, after dividing by the number of trading days, the complete slope technically has dimensions of:

```text
1 / trading-day
```

It is conveniently represented as:

```text
% / trading day
```

## Two Independent Parameters

There are two important parameters:

```text
slope(ema(p), w)
          ↑   ↑
          │   └── slope measurement window
          └────── EMA smoothing period
```

They control different things.

### EMA period `p`

Controls how quickly the underlying EMA responds to price changes.

For example:

```text
ema(20)   -> fast
ema(50)   -> medium
ema(200)  -> very slow
```

EMA200 has substantial inertia. If its slope is strongly negative, it generally cannot become strongly positive after only one or two trading days.

### Slope window `w`

Controls how far back we look when estimating the EMA's current direction.

For example:

```text
slope(ema(200), 5)
slope(ema(200), 20)
slope(ema(200), 60)
```

These measure the same EMA but answer somewhat different questions about its recent direction.

A short window responds quickly but is noisier. A long window is smoother but responds more slowly to a change in trend.

## Parameter Surface

The two parameters naturally form a two-dimensional parameter space:

```text
X = EMA period p
Y = slope window w
Z = resulting slope
```

This can be visualized as a 3D surface.

More importantly, during strategy research the Z axis could instead represent a performance metric such as subsequent return, win rate, Sharpe-like score, or another strategy quality measure.

That would allow `(p, w)` combinations to be searched rather than assuming conventional values such as EMA200 and a 20-day slope window.

## DSL

A natural DSL representation is:

```text
slope(ema(200), 20)
```

with the function returning normalized EMA slope in `% / trading day`.

Strategy expressions could therefore look like:

```text
slope(ema(200), 20) > 0.05
```

meaning that the EMA200 has been increasing at an average normalized rate greater than approximately `0.05%` per trading day over the last 20 trading days.

## Scheduler Application

The same measurement can help determine how frequently a security needs to be downloaded and reevaluated.

For example, if a strategy requires a positive EMA200 slope:

```text
strongly negative EMA200 slope
    -> security is far from qualifying
    -> schedule next evaluation farther into the future

slightly negative EMA200 slope
    -> security may qualify relatively soon
    -> check again sooner

positive EMA200 slope
    -> security passes the slow filter
    -> evaluate frequently
```

Because EMA200 has considerable inertia, this can substantially reduce unnecessary market-data requests while preserving frequent evaluation of securities that are close to producing a strategy hit.

The scheduler should ultimately be based on distance from strategy eligibility rather than arbitrary fixed polling intervals.

## Implementation status

Implemented in DSLX as `slope(fn(a, b, ...), window)` or
`slope(expression, window)`, returning percent per candle using the formula above.
Any supported numeric DSL expression is evaluated at the current candle and
again at the historical candle. This includes EMA, SMA, RSI, ATR, volume EMA,
Stochastic RSI K/D, rolling-window functions, raw prices and arithmetic
combinations such as `slope(ema(20) / ema(50), 10)`. Existing `.slope` retains its absolute one-candle meaning. The numeric
helper is `ETF_screener.slope.normalized_slope(current, previous, window)`.
Missing endpoint history and zero denominators produce no strategy match.
The interpreter reuses cached indicator series and anchors each measurement to
the evaluated candle, without using future values.

The generalized unit is % per candle: % per trading day for daily strategies,
% per week for weekly strategies. Normalization removes constant unit scaling;
it does not make all indicators or volatility levels economically equivalent.

Scheduler integration and parameter-surface research remain future work. A
negative slope alone does not guarantee a minimum time until eligibility, so
skipping future checks would be a separate scheduling policy with potential
missed signals, not a result-preserving calculation optimization.


Moving-average source selection also supports dot notation:
`slope(ema(200).close, 20)`, `slope(ema(20).high, 5)` and
`slope(sma(50).low, 10)`. The selectors `.open`, `.high`, `.low`, `.close`
choose the input price series. Existing string-source syntax remains supported.
