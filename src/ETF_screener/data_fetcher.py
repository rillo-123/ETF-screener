"""Fetch ETF data from Finnhub API."""

import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests


class FinnhubFetcher:
    """Fetch historical data from Finnhub API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Finnhub fetcher.

        Args:
            api_key: Finnhub API key. If not provided, reads from FINNHUB_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Finnhub API key not provided. Set FINNHUB_API_KEY environment variable."
            )
        self.base_url = "https://finnhub.io/api/v1"

    def fetch_historical_data(
        self, symbol: str, days: int = 365
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for an ETF.

        Args:
            symbol: Stock/ETF symbol (e.g., 'EXS1' for XETRA)
            days: Number of days of historical data to fetch (default 365)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())

        params = {
            "symbol": symbol,
            "resolution": "D",  # Daily resolution
            "from": start_time,
            "to": end_time,
            "token": self.api_key,
        }

        response = requests.get(f"{self.base_url}/stock/candle", params=params)
        response.raise_for_status()

        data = response.json()

        if data.get("s") == "no_data":
            raise ValueError(f"No data found for symbol: {symbol}")

        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(data["t"], unit="s"),
                "Open": data["o"],
                "High": data["h"],
                "Low": data["l"],
                "Close": data["c"],
                "Volume": data["v"],
            }
        )

        return df.sort_values("Date").reset_index(drop=True)

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
