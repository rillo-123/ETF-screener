"""Fetch ETF data from Yahoo Finance API."""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Optional

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
                start=start_date,
                end=end_date,
                interval="1d",
                auto_adjust=False,
                actions=True,
            )
        except Exception as e:
            logger.debug("yfinance error for %s: %s", symbol, e)
            return pd.DataFrame()
        if df.empty:
            return df
        df = df.reset_index()
        df.columns = df.columns.str.capitalize()
        if "Dividends" not in df.columns:
            df["Dividends"] = 0.0
        required = ["Date", "Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in required):
            return pd.DataFrame()
        return df[[*required, "Dividends"]].sort_values("Date").reset_index(drop=True)

    def fetch_historical_data(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[datetime | date | str] = None,
        end_date: Optional[datetime | date | str] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for an ETF.

        Tries the given symbol first. If it returns empty and the symbol ends
        with a recognised exchange suffix (e.g. .DE), retries with the
        Frankfurt suffix (.F) as a fallback before giving up.

        Args:
            symbol: Stock/ETF symbol (e.g., 'EXS1.DE' for XETRA)
            days: Number of days of historical data to fetch when no explicit
                start/end window is provided (default 365)
            start_date: Optional explicit inclusive start date for incremental fetches
            end_date: Optional explicit exclusive end date for incremental fetches

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume, Dividends
        """
        resolved_end = (
            pd.to_datetime(end_date).to_pydatetime() if end_date else datetime.now()
        )
        if start_date is not None:
            resolved_start = pd.to_datetime(start_date).to_pydatetime()
        else:
            resolved_start = resolved_end - timedelta(days=days)

        df = pd.DataFrame()
        attempts = 3
        for attempt in range(attempts):
            df = self._fetch_yf(symbol, resolved_start, resolved_end)
            if not df.empty:
                break
            if attempt < attempts - 1:
                time.sleep(0.5 * (attempt + 1))

        if df.empty:
            # Build a .F fallback symbol when the primary has a European suffix
            base = symbol.rsplit(".", 1)[0] if "." in symbol else None
            fallback = (
                f"{base}.F" if base and not symbol.upper().endswith(".F") else None
            )
            if fallback:
                logger.debug(
                    "No data for %s, retrying with fallback %s", symbol, fallback
                )
                for attempt in range(attempts):
                    df = self._fetch_yf(fallback, resolved_start, resolved_end)
                    if not df.empty:
                        break
                    if attempt < attempts - 1:
                        time.sleep(0.5 * (attempt + 1))

        if df.empty:
            logger.warning(
                f"No data found for symbol: {symbol} (tried .DE and .F if applicable)"
            )
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
                logger.warning(f"Skipping {symbol}: {str(e)}")
                if not quiet:
                    print(f"Error fetching {symbol}: {str(e)}")
        return results
