"""ETF screener for volume-based filtering."""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from ETF_screener.data_fetcher import FinnhubFetcher
from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import add_indicators

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


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
        self.formats = self._load_formats()

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

    def _load_formats(self) -> dict:
        """Load output format templates from JSON file."""
        format_file = Path(__file__).parent.parent.parent / "output_formats.json"
        if not format_file.exists():
            return {"default": {"columns": []}}
        try:
            with open(format_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load format file: {e}")
            return {"default": {"columns": []}}

    def format_value(self, value: any, format_type: str, color: str = "") -> str:
        """
        Format a value based on its type.

        Args:
            value: Value to format
            format_type: Format type (volume, price, int, str)
            color: ANSI color code to apply (e.g., GREEN, RED)

        Returns:
            Formatted string
        """
        if pd.isna(value):
            return "N/A"

        if format_type == "volume":
            formatted = self.format_volume(int(value))
        elif format_type == "price":
            formatted = f"{float(value):.2f}"
        elif format_type == "int":
            formatted = str(int(value))
        else:
            formatted = str(value)

        # Apply color if specified
        if color:
            formatted = f"{color}{formatted}{RESET}"

        return formatted

    def print_results(
        self, results: pd.DataFrame, format_name: str = "default"
    ) -> None:
        """
        Pretty print screener results using configured format.

        Args:
            results: Results DataFrame from screen_by_volume
            format_name: Format template name (default, compact, detailed)
        """
        if results.empty:
            print("❌ No ETFs found matching criteria")
            return

        # Get format template
        format_template = self.formats.get(format_name, self.formats.get("default"))
        if not format_template or not format_template.get("columns"):
            print("❌ Invalid format template")
            return

        columns = format_template["columns"]

        print(f"\n✅ Found {len(results)} ETFs:\n")

        # Build header
        header = "".join(
            f"{col['header']:<{col['width']}}" for col in columns
        )
        print(header)
        print("-" * len(header))

        # Print rows
        for _, row in results.iterrows():
            row_values = []
            for col in columns:
                field = col["field"]
                format_type = col["format"]
                width = col["width"]

                if field not in row:
                    value_str = "N/A"
                else:
                    value = row[field]
                    
                    # Determine color for supertrend based on price comparison
                    color = ""
                    if field == "supertrend" and "latest_price" in row:
                        price = row["latest_price"]
                        if not pd.isna(price) and not pd.isna(value):
                            price = float(price)
                            supertrend = float(value)
                            if price > supertrend:
                                color = GREEN  # Uptrend
                            else:
                                color = RED    # Downtrend
                    
                    value_str = self.format_value(value, format_type, color)

                row_values.append(f"{value_str:<{width}}")

            print("".join(row_values))

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
