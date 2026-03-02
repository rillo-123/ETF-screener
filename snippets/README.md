# ETF Snippets - Quick Analysis Scripts

User-created analysis scripts using the `Snippet` helper class for ad-hoc database exploration and filtering.

These scripts provide quick access to common analysis patterns without needing to write full CLI commands or notebook cells.

## Quick Start

Each script can be run directly:

```powershell
python snippets/overbought.py
python snippets/oversold.py
python snippets/rsi_ema.py
python snippets/oversold_period.py
python snippets/overbought_period.py
python snippets/ema_cross.py
```

**No need to run `etfs refresh` first!** By default, snippets automatically fetch missing data from yfinance on-demand, cache it, and calculate indicators. Just run a snippet and it works.

### Command-Line Parameters

Most snippets accept parameters to customize behavior:

```powershell
# Overbought - change threshold
python snippets/overbought.py --threshold 75      # Stricter: RSI > 75
python snippets/overbought.py --threshold 65      # Relaxed: RSI > 65

# Oversold - change threshold
python snippets/oversold.py --threshold 25        # Stricter: RSI < 25
python snippets/oversold.py --threshold 40        # Relaxed: RSI < 40

# Oversold in period - customize lookback and threshold
python snippets/oversold_period.py --days 60 --threshold 25
python snippets/oversold_period.py --days 7 --threshold 30

# Overbought in period - customize lookback and threshold
python snippets/overbought_period.py --days 90 --threshold 75
python snippets/overbought_period.py --days 14 --threshold 65

# EMA Crossover - check days since cross
python snippets/ema_cross.py --days 120
```

Or import patterns in your own scripts:

```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    results = snippet.filter_overbought(rsi_threshold=70)
    for ticker, rsi in results:
        print(f"{ticker}: RSI={rsi:.1f}")
```

## Available Examples

### `example_overbought.py`
Find all ETFs with RSI > 70 (overbought conditions).

**Use case**: Identify potential pullback opportunities or reversals

**Output**:
```
✓ Found 15 ETFs with RSI > 70

Ticker     RSI
EXS1.DE    75.3
EUNG.DE    72.1
EONS.DE    71.5
...
```

### `example_oversold.py`
Find all ETFs with RSI < 30 (oversold conditions).

**Use case**: Identify potential bounce opportunities

**Output**:
```
✓ Found 8 ETFs with RSI < 30

Ticker     RSI
XASC.DE    28.2
NNRG.DE    25.5
...
```

### `example_rsi_ema.py`
Combine multiple filters: RSI > 70 AND Price > EMA50 (overbought in uptrend).

**Use case**: Find strong moves that haven't exhausted yet

**Output**:
```
✓ Found 12 ETFs with RSI > 70 AND Price > EMA50

Ticker     Price     EMA50     RSI
EXS1.DE    125.45    121.32    75.3
EUNG.DE    98.76     96.54     72.1
...
```

### `example_oversold_period.py`
Find tickers that were oversold at ANY point in the last 30 days (or custom period).

**Use case**: Identify tickers with temporary weakness + recovery potential

**Output**:
```
✓ Found 24 ETFs that were oversold in last 30 days

Ticker      Times Oversold      Date(s)
XASC.DE     4x                  2026-02-08, 2026-02-09, 2026-02-10, ... (4 total)
NNRG.DE     2x                  2026-02-05, 2026-02-07
...
```

### `example_overbought_period.py`
Find tickers that were overbought at ANY point in the last 30 days (or custom period).

**Use case**: Identify tickers with sustained strength + pullback opportunities

**Output**:
```
✓ Found 18 ETFs that were overbought in last 30 days

Ticker      Times Overbought   Date(s)
EXS1.DE     6x                  2026-02-03, 2026-02-04, 2026-02-05, ... (6 total)
EUNG.DE     3x                  2026-02-08, 2026-02-09, 2026-02-10
...
```

### `example_auto_fetch.py`
Demo of automatic data fetching on-demand.

**Use case**: Show how snippets work without running refresh first

**Output**:
```
============================================================
Auto-fetch mode: True
============================================================

EXS1.DE         ✓ Price= 125.45  RSI= 72.3  (30 days)
EUNG.DE         ✓ Price=  98.76  RSI= 65.1  (28 days)
EONS.DE         ✓ Price= 145.23  RSI= 78.9  (30 days)

============================================================
✓ All tickers cached (subsequent runs will be instant)
============================================================
```

## `Snippet` Class API

The `Snippet` helper class abstracts database iteration and provides common filters:

### Automatic Data Fetching (Lazy-Loading)

By default, `Snippet` automatically fetches data from yfinance if it's not cached in the database:

```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    # First access: fetches from yfinance, calculates indicators, caches in DB
    df = snippet.get_data("EXS1.DE")
    
    # Second access: returns cached data instantly
    df = snippet.get_data("EXS1.DE")
```

**Disable auto-fetch** to use only cached data:

```python
with Snippet(auto_fetch=False) as snippet:
    # Only returns data if it exists in database
    df = snippet.get_data("EXS1.DE")
```

### Basic Usage

```python
from ETF_screener.snippets import Snippet

# Create context (auto-connects to database)
with Snippet() as snippet:
    # Your analysis here
    pass
# Database closed automatically
```

### Methods

#### `iterate_tickers()`
Iterator over all tickers in database.

```python
for ticker in snippet.iterate_tickers():
    print(ticker)
```

#### `get_data(ticker, days=60)`
Fetch latest N days of data with indicators pre-calculated.

```python
df = snippet.get_data("EXS1.DE", days=60)
print(df[["Date", "Close", "RSI", "EMA_50"]])
```

#### `filter_overbought(rsi_threshold=70)`
Find all tickers with RSI above threshold, sorted descending.

```python
results = snippet.filter_overbought(rsi_threshold=70)
# Returns: List of (ticker, rsi) tuples
for ticker, rsi in results:
    print(f"{ticker}: RSI={rsi:.1f}")
```

#### `filter_oversold(rsi_threshold=30)`
Find all tickers with RSI below threshold, sorted ascending.

```python
results = snippet.filter_oversold(rsi_threshold=30)
# Returns: List of (ticker, rsi) tuples
```

#### `filter_by_ema(above_ema=True)`
Filter by price relative to EMA50.

```python
uptrend = snippet.filter_by_ema(above_ema=True)   # Price > EMA50
downtrend = snippet.filter_by_ema(above_ema=False)  # Price < EMA50
```

#### `filter_by_supertrend(color="green")`
Filter by Supertrend indicator (uses daily timeframe).

```python
bullish = snippet.filter_by_supertrend(color="green")   # Price > Supertrend
bearish = snippet.filter_by_supertrend(color="red")     # Price < Supertrend
```

#### `find_oversold_in_period(days_lookback=30, rsi_threshold=30)`
Find tickers that were oversold at ANY POINT in the lookback period.

Returns dates when each ticker hit oversold conditions:
```python
results = snippet.find_oversold_in_period(days_lookback=30, rsi_threshold=30)
# Returns: {'EXS1.DE': ['2026-01-15', '2026-01-16'], 'EUNG.DE': ['2026-02-10'], ...}
```

#### `find_overbought_in_period(days_lookback=30, rsi_threshold=70)`
Find tickers that were overbought at ANY POINT in the lookback period.

Returns dates when each ticker hit overbought conditions:
```python
results = snippet.find_overbought_in_period(days_lookback=30, rsi_threshold=70)
# Returns: {'EXS1.DE': ['2026-02-05', '2026-02-06', '2026-02-07'], ...}
```

## Common Patterns

### Pattern 1: Simple Filter (Overbought)

```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    overbought = snippet.filter_overbought(rsi_threshold=70)
    print(f"Found {len(overbought)} overbought ETFs")
    for ticker, rsi in overbought:
        print(f"{ticker}: {rsi:.1f}")
```

### Pattern 2: Manual Iteration (Full Control)

```python
from ETF_screener.snippets import Snippet
import pandas as pd

with Snippet() as snippet:
    results = []
    
    for ticker in snippet.iterate_tickers():
        df = snippet.get_data(ticker)
        if df.empty or "RSI" not in df.columns:
            continue
        
        latest = df.iloc[-1]
        if latest["RSI"] > 70:
            results.append({
                "Ticker": ticker,
                "Price": latest["Close"],
                "RSI": latest["RSI"]
            })
    
    df_results = pd.DataFrame(results).sort_values("RSI", ascending=False)
    print(df_results)
```

### Pattern 3: Multiple Conditions (Combine Filters)

```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    results = []
    
    for ticker in snippet.iterate_tickers():
        df = snippet.get_data(ticker)
        if df.empty:
            continue
        
        latest = df.iloc[-1]
        
        # Combine conditions: RSI > 70 AND Price > EMA50 AND Supertrend=GREEN
        if (latest["RSI"] > 70 and 
            latest["Close"] > latest["EMA_50"] and
            latest["Close"] > latest["Supertrend"]):
            results.append(ticker)
    
    print(f"Found {len(results)} strong bullish setups")
    for ticker in results:
        print(f"  {ticker}")
```

### Pattern 4: Get Ticker Details

```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    df = snippet.get_data("EXS1.DE", days=30)
    latest = df.iloc[-1]
    
    print(f"EXS1.DE (latest data):")
    print(f"  Price: {latest['Close']:.2f}")
    print(f"  RSI: {latest['RSI']:.1f}")
    print(f"  EMA50: {latest['EMA_50']:.2f}")
    print(f"  Supertrend: {latest['Supertrend']:.2f}")
    print(f"  Signal: {latest['Signal']:.0f}")
```

### Pattern 5: Historical Oversold/Overbought Over Period

Find tickers that hit extreme RSI values at ANY point in the last N days:

```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    # Find all tickers that were oversold in last 30 days
    oversold = snippet.find_oversold_in_period(days_lookback=30, rsi_threshold=30)
    
    print(f"Tickers with oversold conditions in last 30 days:")
    for ticker, dates in oversold.items():
        print(f"  {ticker}: {len(dates)} times on {dates[-1]}")  # Last occurrence date
```

## Creating Your Own Snippets

1. Copy one of the example scripts
2. Modify the filter logic to match your criteria
3. Run it: `python snippets/my_analysis.py`

Example template:

```python
#!/usr/bin/env python3
"""
My Custom Analysis Snippet

Description: What this script analyzes
"""

from ETF_screener.snippets import Snippet

def main():
    with Snippet() as snippet:
        # Your analysis here
        results = snippet.filter_overbought(rsi_threshold=70)
        
        print(f"\n✓ Found {len(results)} results\n")
        for ticker, rsi in results:
            print(f"{ticker}: RSI={rsi:.1f}")

if __name__ == "__main__":
    main()
```

## Notes

- All snippets automatically use the database at `data/etfs.db`
- DataFrames include all indicators: `Close`, `Volume`, `EMA_50`, `Supertrend`, `RSI`, `Signal`
- RSI is 14-period by default
- Supertrend uses daily timeframe with 3.0 multiplier
- Snippets process ~2000+ tickers (may take 30-60 seconds for full iterations)
