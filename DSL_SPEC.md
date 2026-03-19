# ETF Strategy DSL Specification

This document defines the Domain Specific Language (DSL) used for defining trading strategies in `.dsl` files.

## File Structure
A `.dsl` file must contain at least two blocks: `ENTRY:` and `EXIT:`. Comments start with `#`.

```dsl
# Example Strategy
ENTRY: cross_up(macd, macd_signal) AND (close > ema_50)
EXIT:  cross_down(macd, macd_signal) OR (close < ema_50)
```

## Core Components

### 1. Variables (Indicators & Price)
You can use any of the following base variables. Many support automatic period configuration via suffixes.

| Variable | Description | Example |
| :--- | :--- | :--- |
| `close`, `open`, `high`, `low`, `volume` | Standard OHLCV price data | `close > open` |
| `ema_[N]` | Exponential Moving Average of period N | `ema_50`, `ema_200` |
| `rsi_[N]` | Relative Strength Index of period N | `rsi_14 < 30` |
| `macd`, `macd_signal`, `macd_hist` | MACD components (12, 26, 9) | `macd > 0` |
| `stoch_k`, `stoch_d` | Full Stochastic (14, 3) | `stoch_k > 80` |
| `st`, `supertrend` | Supertrend (10, 3.0) | `close > st` |
| `adx` | Average Directional Index (14) | `adx > 25` |

### 2. Suffixes & Modifiers

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

### 4. Suffix Units
Numeric values in conditions can use K (thousands) or M (millions).
- **Example**: `volume > 1M` (Volume greater than 1,000,000)

### 5. Operators
- **Logical**: `AND`, `OR` (case-insensitive)
- **Comparison**: `>`, `<`, `>=`, `<=`, `==`, `!=`

---

## Technical Details
The DSL is parsed in [src/ETF_screener/backtester.py](src/ETF_screener/backtester.py) and evaluated using `pandas.eval()`. 
1. `cross_up` and `cross_down` are expanded into logical expressions.
2. `was_true` is expanded by injecting `_dN` delays into symbols.
3. Symbols are dynamically matched and calculated via `CachedStrategyManager`.
4. Indicators are automatically calculated and added to the dataframe before evaluation.
