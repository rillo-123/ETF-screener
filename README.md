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

# Custom output locations
etfs discover-all --etfs-file data/my_etfs.json --blacklist-file data/my_blacklist.json
```

### Screener Commands

Screen ETFs by volume and technical criteria:

```powershell
# Screen all ETFs in database with default settings (10M min volume, last 10 days)
etfs screener

# Screen specific ETFs with custom volume threshold
etfs screener EXS1.DE EUNG.DE XESC.DE --aVol 50000 --days 20

# Use human-friendly volume notation
etfs screener --aVol 100K --days 20      # 100 thousand shares
etfs screener --aVol 1.5M --days 20      # 1.5 million shares
etfs screener --aVol 50000 --days 20     # Raw number

# Get top 20 ETFs instead of default 10
etfs screener --nofEtfs 20 --aVol 100K

# Output in different formats
etfs screener --format default             # Full view: volume, prices, EMA50, supertrend
etfs screener --format compact             # Minimal view: ticker, volume only
etfs screener --format detailed            # Extended view: min volume + all indicators

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

