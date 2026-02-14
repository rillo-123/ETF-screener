"""Fetch ETF data from Yahoo Finance API."""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf


class YFinanceFetcher:
    """Fetch historical data from Yahoo Finance."""

    def __init__(self):
        """Initialize Yahoo Finance fetcher."""
        self.name = "Yahoo Finance"

    def fetch_historical_data(
        self, symbol: str, days: int = 365
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for an ETF.

        Args:
            symbol: Stock/ETF symbol (e.g., 'EXS1.DE' for XETRA)
            days: Number of days of historical data to fetch (default 365)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        print(f"  Downloading {symbol}...")
        ticker = yf.Ticker(symbol)
        
        # Fetch daily data
        df = ticker.history(start=start_date, end=end_date, interval="1d")

        if df.empty:
            raise ValueError(f"No data found for symbol: {symbol}")

        # Reset index to get Date as column
        df = df.reset_index()
        
        # Rename columns to match expected format
        df.columns = df.columns.str.capitalize()
        
        # Ensure we have the right columns
        required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Sort by date
        df = df[required_cols].sort_values("Date").reset_index(drop=True)

        return df

    def fetch_multiple_etfs(self, symbols: list[str], days: int = 365) -> dict:
        """
        Fetch data for multiple ETFs.

        Args:
            symbols: List of ETF symbols
            days: Number of days of historical data to fetch

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        results = {}
        for symbol in symbols:
            try:
                print(f"Fetching data for {symbol}...")
                results[symbol] = self.fetch_historical_data(symbol, days)
            except Exception as e:
                print(f"Error fetching {symbol}: {str(e)}")
        return results
