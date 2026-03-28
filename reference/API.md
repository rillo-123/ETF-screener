# ETF Screener Python API

Chainable, fluent Python API for screening European Xetra ETFs with advanced technical indicators.

## Installation

```python
from ETF_screener import Screener
```

## Quick Start

```python
from ETF_screener import Screener

# Find GREEN ETFs (1W timeframe, price above Supertrend)
results = (Screener(min_volume=10000)
    .filter_supertrend('green', timeframe='1W', multiplier=1.0)
    .execute())

print(results)  # DataFrame with matching ETFs
```

## API Reference

### Screener Class

Main entry point for ETF screening.

#### Constructor

```python
Screener(
    min_volume: int = 10_000_000,  # Minimum average volume
    days: int = 10,                 # Days to analyze
    data_dir: str = "data",         # Directory with etfs.json
    db: Optional[ETFDatabase] = None
)
```

### Filter Methods (Chainable)

All filter methods return `self` for method chaining.

#### `filter_supertrend(color, timeframe='1D', period=10, multiplier=3.0)`

Filter by Supertrend indicator (trend following, ATR-based).

**Parameters:**
- `color`: `'green'` (price > Supertrend) or `'red'` (price < Supertrend)
- `timeframe`: `'1D'` (daily) or `'1W'` (weekly)
- `period`: ATR period (default 10)
- `multiplier`: Band width multiplier (default 3.0, typical range 1.0-3.5)

**Examples:**
```python
# Weekly uptrend with default bands
.filter_supertrend('green', timeframe='1W')

# Daily downtrend with tight bands
.filter_supertrend('red', timeframe='1D', multiplier=1.5)

# Custom ATR period
.filter_supertrend('green', period=14, multiplier=2.0)
```

#### `filter_close(gt=None, gte=None, lt=None, lte=None, eq=None, ne=None)`

Filter by close price.

**Parameters:**
- `gt`: Close price > value
- `gte`: Close price >= value  
- `lt`: Close price < value
- `lte`: Close price <= value
- `eq`: Close price == value (within 0.0001 tolerance)
- `ne`: Close price != value

**Examples:**
```python
# Close between 50-100
.filter_close(gte=50, lte=100)

# Close above 150
.filter_close(gt=150)

# Price range
.filter_close(gte=20, lte=50)
```

#### `filter_ema(gt=None, gte=None, lt=None, lte=None, eq=None, ne=None)`

Filter by EMA50 (50-day Exponential Moving Average).

**Examples:**
```python
# EMA between 30-90
.filter_ema(gte=30, lte=90)

# EMA below 50
.filter_ema(lt=50)
```

#### `filter_pullback(gt=None, gte=None, lt=None, lte=None, eq=None, ne=None)`

Filter by pullback % from recent high (typically 10-day lookback).

**Examples:**
```python
# Pullback between 2-5%
.filter_pullback(gte=2, lte=5)

# Strong pullback > 10%
.filter_pullback(gt=10)
```

#### `filter_volume(gt=None, gte=None, lt=None, lte=None, eq=None, ne=None)`

Filter by average volume.

**Examples:**
```python
# Volume between 100K-1M
.filter_volume(gte=100000, lte=1000000)

# High liquidity (> 500K shares/day)
.filter_volume(gt=500000)
```

#### `filter_red_streak(min_days: int)`

Find ETFs in RED (downtrend) for minimum consecutive days.

Used with `filter_supertrend('red')` to identify reversal candidates.

**Parameters:**
- `min_days`: Minimum consecutive RED days (e.g., 10 for strong downtrend)

**Examples:**
```python
# ETFs RED for 10+ weeks (reversal candidates)
.filter_supertrend('red', timeframe='1W')
.filter_red_streak(min_days=10)

# Daily downtrends lasting 20+ days
.filter_supertrend('red', timeframe='1D')
.filter_red_streak(min_days=20)
```

#### `filter_swing(min_pullback=2.0, max_ema_distance=5.0)`

Find swing-ready setups: price dipped toward EMA50 in uptrend.

**Parameters:**
- `min_pullback`: Minimum pullback % from recent high (default 2.0)
- `max_ema_distance`: Maximum distance % from EMA50 (default 5.0)

**Examples:**
```python
# Standard swing setup
.filter_swing()

# Tighter pullback requirement
.filter_swing(min_pullback=3.0, max_ema_distance=3.0)
```

### Execute

#### `execute() -> Optional[pd.DataFrame]`

Run all filters and return matching ETFs as DataFrame.

Returns `None` if no matches found.

**DataFrame Columns:**
- `ticker`: ETF symbol
- `avg_volume`: Average volume (shares/day)
- `max_volume`, `min_volume`, `days_count`: Volume stats
- `open`, `close`, `latest_price`: Price data
- `ema_50`: EMA50 value
- `supertrend`: Current Supertrend level
- `streak_days`: Consecutive RED/GREEN days (if Supertrend filter used)
- `streak_status`: Current trend status ("RED" or "GREEN")

**Example:**
```python
results = screener.execute()

if results is not None:
    print(f"Found {len(results)} matches")
    print(results[['ticker', 'close', 'ema_50']].head())
else:
    print("No matches found")
```

## Usage Examples

### Example 1: Simple Green Filter

Find ETFs in uptrend (weekly, relaxed sensitivity):

```python
from ETF_screener import Screener

results = (Screener(min_volume=10000)
    .filter_supertrend('green', timeframe='1W', multiplier=1.0)
    .execute())

print(f"Found {len(results)} GREEN ETFs")
```

### Example 2: Price Range + Trend

Find ETFs between 50-100 in uptrend:

```python
results = (Screener(min_volume=10000)
    .filter_supertrend('green', timeframe='1W')
    .filter_close(gte=50, lte=100)
    .execute())
```

### Example 3: Swing Setup

Find swing-ready setups with decent liquidity:

```python
results = (Screener(min_volume=50000)
    .filter_swing(min_pullback=2.0)
    .filter_supertrend('green', timeframe='1D')
    .execute())
```

### Example 4: Reversal Candidates

Find ETFs that have been RED for 10+ weeks (likely bottoming):

```python
results = (Screener(min_volume=10000)
    .filter_supertrend('red', timeframe='1W', multiplier=3.0)
    .filter_red_streak(min_days=10)
    .execute())

if results is not None:
    strong_downtrends = results[results['streak_days'] >= 15]
    print(f"Strong downtrends: {len(strong_downtrends)} ETFs")
```

### Example 5: Complex Chain

Multiple conditions with AND logic:

```python
results = (Screener(min_volume=20000)
    .filter_supertrend('green', timeframe='1W', multiplier=1.5)
    .filter_close(gte=50, lte=150)       # Price range
    .filter_ema(gte=40, lte=100)         # EMA range
    .filter_pullback(gte=1, lte=5)       # Recent pullback
    .execute())
```

### Example 6: Using Results

```python
results = (Screener(min_volume=10000)
    .filter_supertrend('green', timeframe='1W')
    .execute())

if results is not None:
    # Sort by volume
    results = results.sort_values('avg_volume', ascending=False)
    
    # Display top tickers
    print(results[['ticker', 'close', 'ema_50', 'avg_volume']].head(10))
    
    # Save to CSV
    results.to_csv('green_etfs.csv', index=False)
```

## Operator Reference

All comparison methods use these operators:

| Operator | Meaning | Example |
|----------|---------|---------|
| `gt` | Greater than (>) | `filter_close(gt=100)` |
| `gte` | Greater or equal (>=) | `filter_ema(gte=50)` |
| `lt` | Less than (<) | `filter_volume(lt=1000000)` |
| `lte` | Less or equal (<=) | `filter_close(lte=150)` |
| `eq` | Equal (==) | `filter_close(eq=75.5)` |
| `ne` | Not equal (!=) | `filter_ema(ne=0)` |

## Context Manager Usage

```python
with Screener(min_volume=10000) as screener:
    results = (screener
        .filter_supertrend('green')
        .execute())
    
    print(results)
# Database connection automatically closed
```

Or manually:

```python
screener = Screener(min_volume=10000)
results = screener.filter_supertrend('green').execute()
screener.close()
```

## Performance Tips

1. **Increase min_volume** - Fewer candidates to analyze
2. **Use weekly instead of daily** - Faster, more stable signals
3. **Apply most restrictive filters first** - Reduces computation

```python
# Efficient: volume first, then most specific filters
results = (Screener(min_volume=100000)  # High volume threshold
    .filter_supertrend('green', timeframe='1W')
    .filter_close(gte=50, lte=100)
    .filter_ema(lt=80)
    .execute())
```

## Return Value

`execute()` returns a pandas DataFrame or `None`:

- **Success**: DataFrame with matching ETFs (1+ row)
- **No matches**: `None`

Check before using:

```python
results = screener.execute()

if results is not None:
    print(f"Found {len(results)} matches")
else:
    print("No ETFs matched criteria")
```

## Integration with CLI

The Python API uses the same underlying engine as the CLI:

```bash
# CLI equivalent:
etfs screener --aVol 10K --supt green --timeframe 1W --st-multiplier 1.0 --close-gte 50 --close-lte 100

# Python API equivalent:
Screener(min_volume=10000) \
    .filter_supertrend('green', timeframe='1W', multiplier=1.0) \
    .filter_close(gte=50, lte=100) \
    .execute()
```

## Notes

- All filters use **AND logic** when combined (all must pass)
- Multiple conditions on same field are combined (e.g., `close(gte=50, lte=100)` = "50 ≤ close ≤ 100")
- Supertrend parameters (period, multiplier) affect sensitivity:
  - Lower multiplier = tighter bands, more signals
  - Higher multiplier = wider bands, fewer false signals
  - Weekly naturally stickier than daily

## See Also

- [CLI Documentation](README.md)
- Screener Configuration example: `test_api.py`
