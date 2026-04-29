# ETF_screener package

__version__ = "0.1.0"

from ETF_screener.data_fetcher import FinnhubFetcher
from ETF_screener.database import ETFDatabase
from ETF_screener.etf_discovery import ETFDiscovery
from ETF_screener.indicators import add_indicators, calculate_ema, calculate_supertrend
from ETF_screener.screener import ETFScreener
from ETF_screener.screener_api import Screener
from ETF_screener.storage import ParquetStorage
from ETF_screener.xetra_extractor import XETRETFExtractor
from ETF_screener.yfinance_fetcher import YFinanceFetcher

try:
    from ETF_screener.plotter_plotly import InteractivePlotter
except ModuleNotFoundError as exc:
    # Keep the package importable in environments that do not have Plotly
    # installed. Most of the non-visual pipeline and tests do not need it.
    if exc.name != "plotly" and not str(exc.name).startswith("plotly"):
        raise
    InteractivePlotter = None

__all__ = [
    "FinnhubFetcher",
    "YFinanceFetcher",
    "ETFDatabase",
    "ETFDiscovery",
    "XETRETFExtractor",
    "add_indicators",
    "calculate_ema",
    "calculate_supertrend",
    "InteractivePlotter",
    "ETFScreener",
    "Screener",
    "ParquetStorage",
]
