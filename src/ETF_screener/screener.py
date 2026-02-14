"""ETF screener for volume-based filtering."""

from typing import Optional

import pandas as pd

from ETF_screener.data_fetcher import FinnhubFetcher
from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import add_indicators


class ETFScreener:
    """Screen and filter ETFs based on technical criteria."""

    def __init__(self, db: Optional[ETFDatabase] = None, api_key: Optional[str] = None):
        """
        Initialize screener.

        Args:
            db: Database instance
            api_key: Finnhub API key (optional)
        """
        self.db = db or ETFDatabase()
        self.fetcher = FinnhubFetcher(api_key=api_key) if api_key else None

    def screen_by_volume(
        self,
        min_days: int = 10,
        min_avg_volume: int = 10_000_000,
        max_results: Optional[int] = None,
        fetch_missing: bool = True,
    ) -> pd.DataFrame:
        """
        Screen ETFs by average volume in last N days.

        Args:
            min_days: Number of days to look back
            min_avg_volume: Minimum average volume threshold
            max_results: Limit results (top by volume)
            fetch_missing: Fetch missing ETF data from Finnhub

        Returns:
            DataFrame with screened ETFs
        """
        # Get candidates from database
        results = self.db.query_by_volume(
            min_days=min_days, min_volume=min_avg_volume, limit=None
        )

        if results.empty:
            return pd.DataFrame()

        # If fetch_missing enabled and no results, try fetching some popular ETFs
        if results.empty and fetch_missing:
            print(
                f"No ETFs found with avg volume >= {min_avg_volume:,}. "
                "Consider fetching more data with: etfs fetch <TICKER>"
            )
            return pd.DataFrame()

        # Limit results if specified
        if max_results:
            results = results.head(max_results)

        return results

    def format_volume(self, volume: int) -> str:
        """
        Format volume to human-readable string.

        Args:
            volume: Volume in shares

        Returns:
            Formatted string (M for millions, K for thousands)
        """
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.1f}K"
        else:
            return str(volume)

    def print_results(self, results: pd.DataFrame) -> None:
        """
        Pretty print screener results.

        Args:
            results: Results DataFrame from screen_by_volume
        """
        if results.empty:
            print("❌ No ETFs found matching criteria")
            return

        print(f"\n✅ Found {len(results)} ETFs:\n")
        print(f"{'Ticker':<10} {'Avg Volume':<15} {'Max Volume':<15} {'Days':<8}")
        print("-" * 50)

        for _, row in results.iterrows():
            ticker = row["ticker"]
            avg_vol = self.format_volume(int(row["avg_volume"]))
            max_vol = self.format_volume(int(row["max_volume"]))
            days = int(row["days_count"])

            print(f"{ticker:<10} {avg_vol:<15} {max_vol:<15} {days:<8}")

    def fetch_and_store(
        self, ticker: str, days: int = 365, recalculate_indicators: bool = True
    ) -> None:
        """
        Fetch ETF data from Finnhub and store in database.

        Args:
            ticker: ETF ticker symbol
            days: Number of days to fetch
            recalculate_indicators: Recalculate technical indicators
        """
        if not self.fetcher:
            raise ValueError("Finnhub API key required to fetch data")

        print(f"Fetching {ticker}...")
        df = self.fetcher.fetch_historical_data(ticker, days=days)

        if recalculate_indicators:
            df = add_indicators(df)

        self.db.insert_dataframe(df, ticker)
        print(f"✓ Stored {len(df)} records for {ticker}")
