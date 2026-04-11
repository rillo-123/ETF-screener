"""Fetch ETF data from Yahoo Finance API."""

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from tqdm import tqdm

logger = logging.getLogger(__name__)


class YFinanceFetcher:
    """Fetch historical data from Yahoo Finance."""

    def __init__(self):
        """Initialize Yahoo Finance fetcher."""
        self.name = "Yahoo Finance"

    def _fetch_yf(
        self, symbol: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Raw yfinance fetch, returns normalized DataFrame or empty DataFrame."""
        try:
            df = yf.Ticker(symbol).history(
                start=start_date, end=end_date, interval="1d"
            )
        except Exception as e:
            logger.debug("yfinance error for %s: %s", symbol, e)
            return pd.DataFrame()
        if df.empty:
            return df
        df = df.reset_index()
        df.columns = df.columns.str.capitalize()
        required = ["Date", "Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in required):
            return pd.DataFrame()
        return df[required].sort_values("Date").reset_index(drop=True)

    def fetch_historical_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for an ETF.

        Tries the given symbol first. If it returns empty and the symbol ends
        with a recognised exchange suffix (e.g. .DE), retries with the
        Frankfurt suffix (.F) as a fallback before giving up.

        Args:
            symbol: Stock/ETF symbol (e.g., 'EXS1.DE' for XETRA)
            days: Number of days of historical data to fetch (default 365)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        df = self._fetch_yf(symbol, start_date, end_date)

        if df.empty:
            # Build a .F fallback symbol when the primary has a European suffix
            base = symbol.rsplit(".", 1)[0] if "." in symbol else None
            fallback = (
                f"{base}.F" if base and not symbol.upper().endswith(".F") else None
            )
            if fallback:
                logger.info(
                    "No data for %s, retrying with fallback %s", symbol, fallback
                )
                df = self._fetch_yf(fallback, start_date, end_date)

        if df.empty:
            raise ValueError(f"No data found for symbol: {symbol}")

        return df

    def fetch_multiple_etfs(
        self, symbols: list[str], days: int = 365, quiet: bool = False
    ) -> dict:
        """
        Fetch data for multiple ETFs.

        Args:
            symbols: List of ETF symbols
            days: Number of days of historical data to fetch
            quiet: Disable progress bar and error printing

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        results = {}
        for symbol in tqdm(symbols, desc="Downloading ETFs", unit="ETF", disable=quiet):
            try:
                results[symbol] = self.fetch_historical_data(symbol, days)
            except Exception as e:
                if not quiet:
                    print(f"Error fetching {symbol}: {str(e)}")
        return results
