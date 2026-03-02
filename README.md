# ETF-screener

Technical analysis tool for identifying swing trading opportunities in large XETRA ETFs using Finnhub API.

## Features

- 📊 **Finnhub Integration** - Fetch real-time and historical XETRA exchange data
- 📈 **Technical Indicators**:
  - EMA 50 (Exponential Moving Average)
  - Supertrend Indicator
  - Automated buy/sell signals
- 💾 **Parquet Storage** - Efficient data persistence with Apache Arrow
- 📉 **Visualization** - Professional charts with matplotlib
- 🔍 **Swing Trading Focus** - Designed for analyzing large-cap ETFs
- ⚡ **CLI Interface** - Simple command-line tools for data fetching and analysis

## Quick Start

### Setup

```powershell
.\ensure-venv.ps1
pip install -r requirements.txt
```

### Get Finnhub API Key

1. Sign up at [finnhub.io](https://finnhub.io)
2. Get your free API key
3. Set environment variable:
   ```powershell
   $env:FINNHUB_API_KEY = "your_api_key_here"
   ```

### Fetch and Analyze ETF Data

```powershell
# Fetch data for single ETF (1 year history)
ETF_screener fetch EXS1 --days 365

# Fetch multiple ETFs
ETF_screener fetch EXS1 EUNG EONS

# Specify custom data and plot directories
ETF_screener fetch EXS1 EUNG --data-dir "./etf_data" --plot-dir "./etf_charts"

# Use different data source (default: yfinance)
ETF_screener fetch EXS1.DE --source yfinance
```

### List Saved ETFs

```powershell
ETF_screener list
ETF_screener list --data-dir custom_data_dir
```

## CLI Usage Guide

### Discovery Commands

Discover and validate ETF tickers:

```powershell
# Discover a few specific tickers
etfs discover EXS1.DE EUNG.DE XESC.DE

# Discover ALL XETRA ETFs from justETFs (slow but comprehensive ~5-10 min)
etfs discover-all --workers 5

# Extract ETFs from Deutsche Börse CSV (from reference/ directory)
etfs extract

# Custom output locations (stored in config/ by default)
etfs discover-all --etfs-file config/etfs.json --blacklist-file config/blacklist.json
```

### Screener Commands

Screen ETFs by volume and technical criteria:

```powershell
# Screen all ETFs in database with default settings (10M min volume, last 10 days)
etfs screener

# Screen for specific technical setups
etfs screener --supt green                 # Only GREEN Supertrend (price > supertrend)
etfs screener --supt red                   # Only RED Supertrend (price < supertrend)
etfs screener --supt red --red-streak 10   # Reversal scanner (10+ consecutive RED days)
etfs screener --swing                      # Pullback scanner (price dipped to EMA50 in uptrend)

# Use conditional volume filters (supports K/M notation)
etfs screener --volume-gte 500k            # Volume greater than or equal to 500,000
etfs screener --volume-lt 1M               # Volume less than 1 million
etfs screener --close-gt 100               # Price greater than 100

# Screen specific ETFs with custom volume threshold
etfs screener EXS1.DE EUNG.DE XESC.DE --aVol 50k --days 20

# Use human-friendly volume notation everywhere
etfs screener --aVol 100K --days 20      # 100 thousand shares
etfs screener --aVol 1.5M --days 20      # 1.5 million shares
etfs screener --aVol 50000 --days 20     # Raw number

# Get top 20 ETFs instead of default 10
etfs screener --nofEtfs 20 --aVol 100K

# Output in different formats
etfs screener --format default             # Full view: volume, prices, EMA50, supertrend
etfs screener --format compact             # Minimal view: ticker, volume only
etfs screener --format detailed            # Extended view: min volume + all indicators
etfs screener --format swing               # Special view for pullback setups

# Keep only recent data (prune older records)
etfs screener --aVol 50K --keep-days 90   # Prune data older than 90 days
```

### Output Formats

The screener supports multiple output formats via `output_formats.json`:

**Default Format** (comprehensive):
```
Ticker   Avg Vol      Max Vol      Open       Close      Latest     EMA50      Supertrend   Days
EUNL.DE  378.1K       1.2M         123.45     124.56     124.56     120.00     125.00       20
VDIV.DE  289.4K       950.0K       45.67      46.78      46.78      44.50      47.00        20
```

**Compact Format** (minimal):
```
Ticker     Avg Volume      Max Volume      Days
EUNL.DE    378.1K          1.2M            20
VDIV.DE    289.4K          950.0K          20
```

**Detailed Format** (extended):
```
Shows all fields including min volume and all technical indicators
```

### Volume Notation

The `--aVol` parameter supports friendly notation:

```powershell
etfs screener --aVol 100       # 100 shares
etfs screener --aVol 100K      # 100,000 shares
etfs screener --aVol 1M        # 1,000,000 shares
etfs screener --aVol 1.5M      # 1,500,000 shares
```

### Configuration

CLI flags are defined in `commands.json` for easy customization:

```json
{
  "screener": {
    "flags": {
      "--nofEtfs": {"default": 10},
      "--aVol": {"default": "10M"},
      "--days": {"default": 10}
    }
  }
}
```

Modify defaults without touching Python code!

### Common Scenarios

**Quick volume screening (5-10 seconds):**
```powershell
etfs screener --aVol 50K --days 10 --format compact
```

**Deep analysis with technical indicators:**
```powershell
etfs screener EXS1.DE EUNG.DE --aVol 30K --days 30 --format default
```

**Find high-liquidity ETFs:**
```powershell
etfs screener --aVol 500K --nofEtfs 20 --format compact
```

**Maintenance - clean old data:**
```powershell
etfs screener --keep-days 180  # Prune records older than 6 months
```

### Database Refresh & Management

The `refresh` command incrementally fills/extends your SQLite database from the CSV file.

**Implicit vs Explicit Refresh:**
- **Explicit:** Use `etfs refresh --depth 365` for batch operations and bulk data loading
- **Implicit:** Snippets automatically fetch missing data on-demand (lazy-loading)

Choose based on your workflow:

- Use `refresh` for daily/bulk maintenance and ETF discovery workflows
- Use snippets for exploratory analysis without setup overhead

### Automated Refresh

The project includes an auto-refresh system designed to run at logon (via Task Scheduler).

- **`auto-refresh.ps1`**: The main PowerShell script that runs a shallow refresh (last 30 days) and generates a swing trading hotlist.
- **`auto-refresh.bat`**: A launcher for the PowerShell script.
- **Progress Tracking**: The script displays a live progress bar in a terminal window and logs detailed output to `logs/auto-refresh.log`.

**Key concept**: `--depth` specifies how many days of history to keep, counting *back from today*.
- `--depth 365` = fetch/maintain data from 365 days ago until today
- `--depth 90` = fetch/maintain data from 90 days ago until today

**Smart incremental updates:**
- **New tickers**: Fetches full depth from scratch (365 days ago → today)
- **Existing with partial data**: Extends history to reach target depth
- **Already complete**: Skips (no duplicate fetches)
- **Blacklisted**: Skipped by default (optional override)

```powershell
# Standard refresh - maintains 1 year of data (only fills gaps before oldest)
etfs refresh --depth 365

# Light refresh - maintains last 90 days
etfs refresh --depth 90

# Deep history - maintains 2 years of data
etfs refresh --depth 730

# Re-validate blacklisted tickers (e.g., if some were delisted but now active)
etfs refresh --depth 365 --include-blacklist

# Force full re-fetch of everything (slow, useful for maintenance)
etfs refresh --depth 365 --force

# From custom CSV location
etfs refresh --depth 365 --csv-file path/to/your/etfs.csv

# Using specific validated ETF list
etfs refresh --depth 365 --etfs-file data/my_etfs.json
```

**Example workflow (incremental daily updates):**
```powershell
# Day 1: Initial load - fetch data from 365 days ago to today
etfs refresh --depth 365
# Result: Tickers fetched with data spanning 365 days

# Day 2: Quick update (only adds 1 new day of data)
etfs refresh --depth 365
# Result: For each ticker, checks if it has 365 days. If oldest is >365 days ago, extends back.
# ✓ New: 2000
# ↻ Extended: 0
# ✗ Failed: 5
# ⊘ Skipped: 100
# 📊 Total: 2105/2105

# Day 3+: Regular updates (most tickers already at full depth)
etfs refresh --depth 365
# Result: Only tickers that don't span full 365 days are updated
# ✓ New: 0
# ↻ Extended: 0
# ✗ Failed: 5
# ⊘ Skipped: 2100 (already have 365 days)
# 📊 Total: 2105/2105
```

### Swing Trading Workflows

**Find swing-ready setups (price near EMA50 in uptrend):**
```powershell
etfs screener --swing --aVol 100K --days 30

# With tighter pullback requirement (2% from high)
etfs screener --swing --swing-pull 2.0 --aVol 100K

# Looser pullback (5% from high)
etfs screener --swing --swing-pull 5.0 --aVol 100K
```

**Filter by Supertrend color:**
```powershell
# Only GREEN Supertrend (price > supertrend = uptrend)
etfs screener --supt green --days 20 --aVol 50K

# Only RED Supertrend (price < supertrend = downtrend)
etfs screener --supt red --days 20 --aVol 50K

# RED Supertrend with minimum reversal signal (10+ RED days)
etfs screener --supt red --red-streak 10 --days 20 --aVol 50K
```

**Weekly Supertrend analysis (longer-term trend):**
```powershell
etfs screener --supt green --timeframe 1W --days 30

# Adjust sensitivity with st-multiplier (default 3.0)
etfs screener --supt green --timeframe 1W --st-multiplier 2.5 --days 30
```

**Conditional filtering:**
```powershell
# Price greater than 100
etfs screener --close-gt 100 --aVol 50K

# EMA value less than 50
etfs screener --ema-lt 50 --aVol 50K

# Volume greater than 500K shares
etfs screener --volume-gte 500000 --days 10

# Multiple conditions (AND logic)
etfs screener --close-gte 50 --close-lte 150 --ema-gt 40 --aVol 100K
```

**Detailed swing analysis:**
```powershell
etfs screener --swing --swing-pull 2.0 --format detailed --aVol 100K --st-multiplier 3.0
```

### Discovery & Validation Workflows

**Initial setup - discover and validate all XETRA ETFs:**
```powershell
# Extract from Deutsche Börse CSV
etfs extract

# Or discover from complete list (slower, ~5-10 minutes)
etfs discover-all --workers 10

# Custom ETF validation
etfs discover EXS1.DE EUNG.DE EONS.DE --etfs-file data/my_etfs.json
```

**Update discovery to new output location:**
```powershell
etfs discover-all --etfs-file data/new_etfs.json --blacklist-file data/new_blacklist.json --workers 5
```

### End-to-End Workflows

**Complete fresh start:**
```powershell
# 1. Extract and validate all ETFs from CSV
etfs extract

# 2. Refresh database with 1 year of history
etfs refresh --depth 365

# 3. Screen for high-volume ETFs
etfs screener --aVol 100K --days 20 --format compact

# 4. Analyze swing setups with detailed output
etfs screener --swing --aVol 50K --format detailed
```

**Daily trading preparation:**
```powershell
# 1. Quick refresh (last 30 days only - fast)
etfs refresh --depth 30

# 2. Find current swing opportunities
etfs screener --swing --aVol 50K --swing-pull 2.0 --days 20

# 3. Check uptrend confirmation (GREEN Supertrend)
etfs screener --supt green --aVol 50K --format detailed

# 4. Weekly perspective
etfs screener --supt green --timeframe 1W --aVol 50K
```

**Weekly analysis (find strong trends):**
```powershell
# 1. Full data refresh
etfs refresh --depth 365

# 2. Screen high-liquidity ETFs
etfs screener --aVol 500K --format compact --days 20

# 3. Find GREEN weekly trends
etfs screener --supt green --timeframe 1W --aVol 100K --format detailed

# 4. Identify reversal candidates (RED 10+ days)
etfs screener --supt red --red-streak 10 --aVol 50K --format default
```

**Maintenance - prune old data and refresh:**
```powershell
# Keep only last 6 months
etfs screener --keep-days 180

# Refresh with current data
etfs refresh --depth 180

# Screen with pruned data
etfs screener --aVol 50K --format compact
```

### Performance Tips

**Fast screening (existing data only):**
```powershell
# Use pre-cached data, no fetching
etfs screener --aVol 50K --days 10 --format compact
# Takes <5 seconds
```

**Faster refresh (shallow history):**
```powershell
# Fetch only 30 days instead of 365
etfs refresh --depth 30
# Takes ~2-3 minutes for 2000+ ETFs
```

**Parallel worker optimization:**
```powershell
# More workers = faster but higher API load
etfs discover-all --workers 10  # Fast but aggressive

# Conservative, lower load
etfs discover-all --workers 3   # Slower but gentler
```

## Output Files

Data and plots are automatically saved:

```
data/
├── exs1_data.parquet          # Historical OHLCV + indicators
├── eung_data.parquet
├── etfs.json                  # Discovered valid ETF tickers
├── blacklist.json             # Invalid/delisted ETFs
├── etfs.db                    # SQLite database
└── test_results_*.txt         # Test logs

plots/
├── exs1_analysis.png          # Full technical analysis chart
├── eung_analysis.png
└── ...
```

## Parquet Data Format

Each parquet file contains:

- **Date** - Trading date
- **Open** - Opening price
- **High** - High price
- **Low** - Low price
- **Close** - Closing price
- **Volume** - Trading volume
- **EMA_50** - 50-period exponential moving average
- **Supertrend** - Supertrend indicator value
- **ST_Upper** - Upper band of supertrend
- **ST_Lower** - Lower band of supertrend
- **Signal** - Trading signal: 1 (buy), -1 (sell), 0 (neutral)

## Python Snippets

Quick analysis scripts for ad-hoc database exploration without needing CLI commands or notebook setup.

These are standalone Python scripts you can run directly or use as templates for your own analysis.

**Key feature:** Snippets automatically fetch missing data from yfinance on-demand, calculate indicators, and cache it. No need to run `etfs refresh` first!

### Quick Start

```powershell
# Find all overbought ETFs (RSI > 70)
python snippets/example_overbought.py

# Find all oversold ETFs (RSI < 30)
python snippets/example_oversold.py

# Find overbought ETFs still in uptrend (RSI > 70 AND Price > EMA50)
python snippets/example_rsi_ema.py

# Find tickers that were oversold in last 30 days
python snippets/example_oversold_period.py

# Demo auto-fetch behavior
python snippets/example_auto_fetch.py
```

**No refresh needed!** Snippets handle data fetching automatically.

### Available Examples

**`snippets/example_overbought.py`** - Find overbought conditions
```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    overbought = snippet.filter_overbought(rsi_threshold=70)
    for ticker, rsi in overbought:
        print(f"{ticker}: RSI={rsi:.1f}")
```

**`snippets/example_oversold.py`** - Find oversold conditions
```python
with Snippet() as snippet:
    oversold = snippet.filter_oversold(rsi_threshold=30)
    for ticker, rsi in oversold:
        print(f"{ticker}: RSI={rsi:.1f}")
```

**`snippets/example_rsi_ema.py`** - Combine multiple filters
```python
with Snippet() as snippet:
    # RSI > 70 AND Price > EMA50 (strong uptrend)
    for ticker in snippet.iterate_tickers():
        df = snippet.get_data(ticker)
        latest = df.iloc[-1]
        if latest['RSI'] > 70 and latest['Close'] > latest['EMA_50']:
            print(f"{ticker}: RSI={latest['RSI']:.1f}")
```

### Snippet Helper Class

The `Snippet` class provides convenient methods for database iteration and filtering:

- `iterate_tickers()` - Iterator over all database tickers
- `get_data(ticker, days=60)` - Fetch latest N days with indicators pre-calculated
- `filter_overbought(rsi_threshold=70)` - Find RSI > threshold
- `filter_oversold(rsi_threshold=30)` - Find RSI < threshold
- `filter_by_ema(above_ema=True)` - Filter by price vs EMA50
- `filter_by_supertrend(color="green")` - Filter by trend direction
- `find_oversold_in_period()` - Find tickers that were oversold at any point in period
- `find_overbought_in_period()` - Find tickers that were overbought at any point in period

**Auto-fetch feature:** By default, `get_data()` automatically fetches from yfinance if data is missing or insufficient:

```python
from ETF_screener.snippets import Snippet

with Snippet() as snippet:
    # First call: fetches from yfinance, caches it
    df = snippet.get_data("EXS1.DE")
    
    # Disable auto-fetch if you only want cached data
    with Snippet(auto_fetch=False) as snippet_cached:
        df = snippet_cached.get_data("EXS1.DE")  # Returns cached only
```

See [snippets/README.md](snippets/README.md) for full API and pattern examples.

## Python API Reference

### ETFScreener (Volume Screening)

```python
from ETF_screener import ETFScreener, ETFDatabase

# Initialize database and screener
db = ETFDatabase(db_path="data/etfs.db")
screener = ETFScreener(db=db)

# Screen by volume
results = screener.screen_by_volume(
    min_days=10,
    min_avg_volume=50000,
    max_results=10
)

# Print with custom format
screener.print_results(results, format_name="default")
```

### ETFDatabase (SQLite)

```python
from ETF_screener import ETFDatabase
import pandas as pd

db = ETFDatabase(db_path="data/etfs.db")

# Insert DataFrame with price and indicator data
df = pd.DataFrame({...})
db.insert_dataframe(df, ticker="EXS1.DE")

# Query by volume
high_vol = db.query_by_volume(min_volume=50000, min_days=20)

# Check if ticker exists
if db.ticker_exists("EXS1.DE"):
    latest_date = db.get_latest_date("EXS1.DE")

# Prune old data (>365 days)
deleted = db.prune_old_data(days_to_keep=365)

db.close()
```

### YFinanceFetcher (Real Data)

```python
from ETF_screener import YFinanceFetcher

fetcher = YFinanceFetcher()

# Fetch single ETF
df = fetcher.fetch_historical_data("EXS1.DE", days=365)

# Fetch multiple ETFs
data = fetcher.fetch_multiple_etfs(["EXS1.DE", "EUNG.DE"], days=365)
```

### FinnhubFetcher (Legacy)

```python
from ETF_screener import FinnhubFetcher

fetcher = FinnhubFetcher(api_key="your_api_key")

# Fetch single ETF
df = fetcher.fetch_historical_data("EXS1", days=365)

# Fetch multiple ETFs
data = fetcher.fetch_multiple_etfs(["EXS1", "EUNG", "EONS"], days=365)
```

### Technical Indicators

```python
from ETF_screener import add_indicators

# Your DataFrame must have: Date, Open, High, Low, Close, Volume
df_with_indicators = add_indicators(df)

print(df_with_indicators[["Date", "Close", "EMA_50", "Supertrend", "Signal"]])
```

### Data Storage

```python
from ETF_screener import ParquetStorage

storage = ParquetStorage(data_dir="data")

# Save ETF data
storage.save_etf_data(df, "EXS1")

# Load ETF data
df = storage.load_etf_data("EXS1")

# List all saved ETFs
etfs = storage.list_available_etfs()
```

### Plotting

```python
from ETF_screener import PortfolioPlotter

plotter = PortfolioPlotter(output_dir="plots")

# Plot single ETF analysis
plotter.plot_etf_analysis(df_with_indicators, "EXS1")

# Plot multiple ETFs
etf_data = {"EXS1": df1, "EUNG": df2}
plotter.plot_multiple_etfs(etf_data)
```

## Example Workflow

```python
from ETF_screener import (
    FinnhubFetcher,
    add_indicators,
    ParquetStorage,
    PortfolioPlotter
)

# Initialize components
fetcher = FinnhubFetcher(api_key="your_key")
storage = ParquetStorage(data_dir="data")
plotter = PortfolioPlotter(output_dir="plots")

# Fetch data
symbols = ["EXS1", "EUNG", "EONS"]
etf_data = fetcher.fetch_multiple_etfs(symbols, days=365)

# Calculate indicators
for symbol, df in etf_data.items():
    etf_data[symbol] = add_indicators(df)

# Save and plot
storage.save_multiple_etfs(etf_data)
plotter.plot_multiple_etfs(etf_data)

# Analyze signals
for symbol, df in etf_data.items():
    buy_signals = (df["Signal"] == 1).sum()
    sell_signals = (df["Signal"] == -1).sum()
    print(f"{symbol}: {buy_signals} buy, {sell_signals} sell signals")
```

## XETRA ETF Examples

Popular large-cap XETRA ETFs for swing trading:

| Symbol | Name | Focus |
|--------|------|-------|
| EXS1 | iShares EURO STOXX 50 UCITS ETF | European Large-Cap |
| EUNG | iShares MSCI World UCITS ETF | Global Broad Market |
| EONS | Xtrackers Euro Stoxx 50 UCITS ETF | European Blue Chips |

## Testing

```powershell
.\run_all_tests.ps1
```

Or run specific tests:

```powershell
pytest tests/test_indicators.py -v
pytest tests/test_storage.py -v
pytest tests/test_data_fetcher.py -v
pytest tests/test_plotter.py -v
```

## Development

### Code Quality

```powershell
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

### Tools

- **Code formatter**: black
- **Import sorter**: isort
- **Linter**: flake8
- **Type checker**: mypy

## Module Overview

- **data_fetcher.py** - Finnhub API integration for fetching XETRA data
- **indicators.py** - Technical analysis calculations (EMA 50, Supertrend, signals)
- **storage.py** - Parquet file persistence for efficient data storage
- **plotter.py** - Visualization with matplotlib for technical analysis charts
- **main.py** - CLI interface for fetching and analyzing ETF data

## Requirements

- Python 3.8+
- pandas >= 2.0.0
- matplotlib >= 3.8.0
- pyarrow >= 14.0.0
- requests >= 2.32.3
- numpy >= 1.24.0

## License

MIT

## Disclaimer

This tool is for educational and research purposes. Trading involves significant risk. Always conduct thorough due diligence and consider consulting with a financial advisor before making trading decisions.

