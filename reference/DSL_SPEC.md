# ETF Strategy DSL Specification

This document defines the Domain Specific Language (DSL) used for defining trading strategies in `.dsl` files.

## File Structure
A `.dsl` file can use the legacy `ENTRY:`/`EXIT:` format or the modern `TRIGGER:`/`FILTER:`/`EXIT:` format (recommended for scanners).

### Layered Block Format (Keyword Blocks, recommended)
```dsl
BEGIN CONTEXT_REGIME
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

BEGIN SETUP_PULLBACK
FILTER: close > ema_50
END

BEGIN TRIGGER_EVENT
TRIGGER: macd > macd_signal AND macd_d1 <= macd_signal_d1
END

BEGIN RISK_GUARD
FILTER: volume > 150K
EXIT: close < ema_50
END
```

Keywords currently mapped to visual layers:
- `CONTEXT*` -> Layer 1
- `SETUP*` -> Layer 2
- `TRIGGER*` -> Layer 3
- `RISK*` -> Layer 4

Identifier style guideline:
- Prefer uppercase identifiers.
- Use underscores, no spaces (e.g. `CONTEXT_REGIME`).

Supported aliases:
- `layer 1`, `layer 2`, `layer 3`, `layer 4`
- `layer_1`, `layer_2`, `layer_3`, `layer_4`
- `l1`, `l2`, `l3`, `l4`

Backward compatibility:
- `LAYER n BEGIN ... END` still works.
- Optional global `BEGIN ... END` wrappers are still accepted.

### Layered Block Format (Pascal-style, still supported)
```dsl
BEGIN

LAYER 1 BEGIN
FILTER: close > ema_200
FILTER: ema_200_slope > 0
END

LAYER 2 BEGIN
FILTER: close > ema_50
END

LAYER 3 BEGIN
TRIGGER: cross_up(macd, macd_signal)
END

LAYER 4 BEGIN
FILTER: volume > 150K
EXIT:   close < ema_50
END

END
```

Notes:
- `BEGIN`/`END` wrappers are optional and currently used for structure/readability.
- Block keywords assign rules to visual ribbons for Layer 1-4.
- `TRIGGER`, `FILTER`, `ENTRY`, and `EXIT` semantics remain unchanged.

### Recommended Format (Modern)
```dsl
# Hardened Trend Strategy
TRIGGER: cross_up(macd, macd_signal) 
FILTER:  close > ema_50 AND volume > 100K
EXIT:    cross_down(macd, macd_signal) OR close < ema_50
```

### Scanner Format (Function-style indicators)
The dashboard scanner also accepts a compact format intended for quick
universe scans. `candle_age LTE N` limits the match to the latest N candles,
including today. `candle_age EQ N` selects signals exactly N candles ago.
`period_1d` explicitly selects one-day candles. Put one
condition per line and join conditions with `AND` or `OR`.

```dsl
candle_age LTE 5
period_1d
rsi(14) GT 70
AND
volume GT vol_ema_20
```

This finds instruments whose 14-period RSI is above 70 and whose latest
volume is above its 20-period volume EMA.

Other examples:

```dsl
# Strong momentum above the 50-day trend
candle_age LTE 10
period_1d
close GT ema_50
AND
rsi(14) GT 50
```

```dsl
# High absolute volume with improving momentum
candle_age LTE 3
period_1d
volume GT 1M
AND
rsi(14) GT 50
AND
rsi_14 GT rsi_14_d1
```

In scanner conditions, the word operators `GT`, `GTE`, `LT`, `LTE`, `EQ`, and
`NE` are equivalent to `>`, `>=`, `<`, `<=`, `==`, and `!=`. The shorter
aliases `GE` and `LE` remain supported as alternatives to `GTE` and `LTE`.

### Legacy Format
```dsl
ENTRY: cross_up(macd, macd_signal) AND (close > ema_50)
EXIT:  cross_down(macd, macd_signal) OR (close < ema_50)
```

Entry and exit are evaluated in sequence. The entry condition is searched
within the `candle_age` window and establishes the entry candle. The exit
condition is then evaluated only on later candles while that position is
open. `candle_age` has no meaning in the exit box and should not be placed
there; it is an entry-signal search limit, not an exit timer.

For example:

```dsl
# Entry box
candle_age LTE 5
period_1d
rsi(14) GT 50
AND
ema_close(200)_slope GT 0

# Exit box
ha_close LT ema_close(20)
```

## Core Components

### 1. Scanner expressions

The compact scanner form is the preferred format for the dashboard. It is one
condition per line, with `AND` or `OR` on its own line (or inline inside a
condition). The dashboard accepts both function-style names and their
normalized column-style names.

#### Metadata

| Expression | Meaning |
| :--- | :--- |
| `candle_age LTE N` | Match a signal in the latest N candles, including the current candle. |
| `candle_age EQ N` | Match a signal exactly N candles ago. |
| `period_1d` | Explicitly select daily candles. |

`LTE` is normally what you want for “within the last N candles”; `EQ` means
exactly that candle age. Metadata lines are not indicator conditions.

#### Price and volume fields

| Expression | Description | Example |
| :--- | :--- | :--- |
| `open`, `high`, `low`, `close`, `volume` | Raw daily OHLCV fields | `close GT open` |
| `ha_open`, `ha_high`, `ha_low`, `ha_close` | Heikin-Ashi OHLC fields | `ha_close GT ha_open` |
| `volume` | Latest trading volume | `volume GT 1M` |

Candle colour is explicit; EMA conditions do not imply a candle colour:

```dsl
# Green Heikin-Ashi candle
ha_close GT ha_open

# Red Heikin-Ashi candle
ha_close LT ha_open

# Green or red regular candle
close GT open
close LT open
```

For example, a bullish rule that requires a green Heikin-Ashi candle is:

```dsl
ha_close GT ema_high(20)
AND
ha_open GT ema_low(20)
AND
ha_close GT ha_open
```

#### Moving averages

Function-style syntax is recommended because it makes the source field clear:

| Expression | Normalized form | Meaning |
| :--- | :--- | :--- |
| `ema_20` | same | 20-period EMA of close |
| `ema_open(20)` | `ema_open_20` | 20-period EMA of open |
| `ema_high(20)` | `ema_high_20` | 20-period EMA of high |
| `ema_low(20)` | `ema_low_20` | 20-period EMA of low |
| `ema_close(20)` | `ema_close_20` | 20-period EMA of close |
| `ema_20` | same | Close-EMA form |

`ema_20_high` is not the canonical spelling. Use `ema_high(20)` (or
`ema_high_20` when using the normalized form).

#### Momentum and trend indicators

| Expression | Description | Example |
| :--- | :--- | :--- |
| `rsi(N)` / `rsi_N` | RSI with period N | `rsi(14) GT 50` |
| `rsi_ema_R_E` | EMA of RSI period R with EMA period E | `rsi_ema_14_10 GT 50` |
| `macd` | MACD line, default 12/26/9 | `macd GT 0` |
| `macd_signal` | MACD signal line | `macd GT macd_signal` |
| `macd_hist` | MACD histogram | `macd_hist GT 0` |
| `stoch_k`, `stoch_d` | Stochastic K/D, default 14/3 | `stoch_k LT 20` |
| `stoch_rsi_k`, `stoch_rsi_d` | StochRSI K/D, default 14/14/3/3 | `stoch_rsi_k GT 80` |
| `adx` | ADX, default period 14 | `adx GT 25` |
| `tsi`, `tsi_signal` | TSI and signal line | `tsi GT tsi_signal` |
| `vol_ema_N` | Volume EMA; `vol_ema_20` is currently supported | `volume GT vol_ema_20` |

#### Supertrend

| Expression | Meaning |
| :--- | :--- |
| `st` / `supertrend` | Default Supertrend, period 10 and multiplier 3.0 |
| `st_N_M` / `supertrend_N_M` | Supertrend with period N and multiplier M, e.g. `st_10_3` |
| `st_is_green` | Price is above the default Supertrend |
| `st_is_red` | Price is below the default Supertrend |
| `st_N_M_is_green` / `_is_red` | Parameterized Supertrend regime helper |

#### Anchored VWAP

| Expression | Meaning |
| :--- | :--- |
| `avwap_low_N` | Anchored VWAP from the rolling N-bar swing low |
| `avwap_high_N` | Anchored VWAP from the rolling N-bar swing high |
| `anchored_vwap_low_N` / `anchored_vwap_high_N` | Verbose aliases |

### 2. Modifiers and history

| Variable | Description | Example |
| :--- | :--- | :--- |
| `close`, `open`, `high`, `low`, `volume` | Standard OHLCV price data | `close > open` |
| `ema_[N]` | Exponential Moving Average of period N | `ema_50`, `ema_200` |
| `avwap_low_[N]` | Anchored VWAP from the lowest low in the last N bars | `avwap_low_20` |
| `avwap_high_[N]` | Anchored VWAP from the highest high in the last N bars | `avwap_high_20` |
| `rsi_[N]` / `rsi(N)` | Relative Strength Index of period N | `rsi(14) GT 50` |
| `macd`, `macd_signal`, `macd_hist` | MACD components (12, 26, 9) | `macd > 0` |
| `stoch_k`, `stoch_d` | Full Stochastic (14, 3) | `stoch_k > 80` |
| `st`, `supertrend` | Supertrend (10, 3.0) | `close > st` |
| `st_is_green` | Boolean alias for `close > supertrend` | `TRIGGER: st_is_green` |
| `st_is_red` | Boolean alias for `close < supertrend` | `TRIGGER: st_is_red` |
| `adx` | Average Directional Index (14) | `adx > 25` |

Volume indicators:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `volume` | Latest trading volume | `volume GT 1M` |
| `vol_ema_[N]` | Exponential moving average of volume over N periods | `volume GT vol_ema_20` |

Anchored VWAP notes:
- `avwap_low_[N]` re-anchors to the most recent rolling N-bar swing low.
- `avwap_high_[N]` re-anchors to the most recent rolling N-bar swing high.
- `anchored_vwap_low_[N]` and `anchored_vwap_high_[N]` are accepted as verbose aliases.

#### `_slope`
Calculates the rate of change. For indicators like `rsi` or `macd`, it uses a 7-day linear regression. For others, it uses `diff()`.
- **Example**: `ema_50_slope > 0` (Trend is up)

#### `_d[N]` (Delays/History)
Used to access historical values from N bars ago.
- **Example**: `close_d1` (Previous close), `rsi_14_d2` (RSI from 2 days ago)

### 3. Functions

| Function | Description | Implementation |
| :--- | :--- | :--- |
| `cross_up(a, b)` | True if `a` crosses above `b` | `(a > b AND a_d1 <= b_d1)` |
| `cross_down(a, b)` | True if `a` crosses below `b` | `(a < b AND a_d1 >= b_d1)` |
| `was_true(cond, N)` | True if `cond` was true N bars ago | `cond` with all variables shifted by `_dN` |
| `within(cond, N)` | True if `cond` is true now or in the previous N bars | `within(rsi(14) GT 50, 5)` |
| `within(cond, A, B)` | True if `cond` is true between A and B bars ago | `within(close GT ema_50, 2, 5)` |
| `between(cond, N)` | Alias for `within(cond, N)` | `between(macd GT 0, 3)` |

### 4. Suffix Units
Numeric values in conditions can use K (thousands) or M (millions).
- **Example**: `volume > 1M` (Volume greater than 1,000,000)

### 5. Operators
- **Logical**: `AND`, `OR` (case-insensitive)
- **Comparison symbols**: `>`, `<`, `>=`, `<=`, `==`, `!=`
- **Comparison words**: `GT`, `LT`, `GTE`/`GE`, `LTE`/`LE`, `EQ`, `NE`
- **Numeric units**: `K` for thousands and `M` for millions, e.g. `volume GT 1M`

---

## Technical Details
The DSL is parsed in [src/ETF_screener/backtester.py](src/ETF_screener/backtester.py) and evaluated using `pandas.eval()`. 
1. `cross_up` and `cross_down` are expanded into logical expressions.
2. `was_true` is expanded by injecting `_dN` delays into symbols.
3. Symbols are dynamically matched and calculated via `CachedStrategyManager`.
4. Indicators are automatically calculated and added to the dataframe before evaluation.
