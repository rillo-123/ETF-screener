"""Parse Deutsche Börse XETRA tradeable assets CSV and extract ETF tickers."""

import csv
import json
from pathlib import Path
from typing import Optional

from yfinance import Ticker


class XETRETFExtractor:
    """Extract and validate XETRA ETF tickers from Deutsche Börse CSV."""

    def __init__(
        self,
        csv_file: str = "reference/t7-xetr-allTradableInstruments.csv",
        etfs_file: str = "etfs.json",
        blacklist_file: str = "blacklist.json",
    ):
        """Initialize extractor."""
        self.csv_file = Path(csv_file)
        self.etfs_file = Path(etfs_file)
        self.blacklist_file = Path(blacklist_file)
        self.working_etfs = self._load_json(self.etfs_file) or {}
        self.blacklist = self._load_json(self.blacklist_file) or {}

    @staticmethod
    def _load_json(file_path: Path) -> Optional[dict]:
        """Load JSON file if it exists."""
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
        return None

    def _save_json(self, data: dict, file_path: Path) -> None:
        """Save data to JSON file."""
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def extract_etf_tickers(self) -> list[str]:
        """
        Extract ETF tickers from Deutsche Börse CSV.

        Returns:
            List of ETF tickers with .DE suffix for yfinance
        """
        etf_tickers = []

        if not self.csv_file.exists():
            print(f"CSV file not found: {self.csv_file}")
            return etf_tickers

        print(f"Parsing {self.csv_file}...")

        try:
            with open(self.csv_file, "r", encoding="utf-8-sig") as f:
                # Skip metadata rows until we find the actual header
                # The file starts with "Market:;XETR" and "Date Last Update:;..."
                lines = f.readlines()
                
                # Find the header row (starts with "Product Status")
                header_index = 0
                for i, line in enumerate(lines):
                    if "Product Status" in line:
                        header_index = i
                        break
                
                # Reset file pointer and skip to header
                f.seek(0)
                for _ in range(header_index):
                    f.readline()
                
                # Now read CSV from the actual header
                reader = csv.DictReader(f, delimiter=";")
                
                for row in reader:
                    # Filter by instrument type - looking for "ETF" or "ETC"
                    # Check multiple possible column names for instrument type
                    instr_type = (
                        row.get("Instrument Type", "")
                        or row.get("Security Sub Type", "")
                    ).strip().upper()
                    
                    mnemonic = row.get("Mnemonic", "").strip()
                    
                    # Look for ETF, ETC (Exchange Traded Commodity), or ETP (Exchange Traded Product)
                    if mnemonic and any(
                        etf_type in instr_type 
                        for etf_type in ["ETF", "ETC", "ETP"]
                    ):
                        # Add .DE suffix for XETRA (yfinance requirement)
                        ticker_with_suffix = f"{mnemonic}.DE"
                        etf_tickers.append(ticker_with_suffix)

        except Exception as e:
            print(f"Error parsing CSV: {e}")

        print(f"Found {len(etf_tickers)} ETF tickers in CSV")
        return etf_tickers

    def validate_ticker(self, ticker: str) -> bool:
        """
        Check if ticker has data on Yahoo Finance.

        Args:
            ticker: ETF ticker symbol

        Returns:
            True if data available, False otherwise
        """
        try:
            t = Ticker(ticker)
            hist = t.history(period="1d")
            if hist is not None and not hist.empty:
                return True
            return False
        except Exception:
            return False

    def discover_and_validate(
        self, max_workers: int = 5, verbose: bool = True
    ) -> dict:
        """
        Extract ETFs from CSV and validate against Yahoo Finance.

        Args:
            max_workers: Number of parallel validation workers
            verbose: Print progress

        Returns:
            Dict with 'working' and 'blacklisted' keys
        """
        # Extract tickers from CSV
        tickers = self.extract_etf_tickers()

        if verbose:
            print(f"\nValidating {len(tickers)} ETF tickers on Yahoo Finance...\n")

        validated_count = 0
        blacklisted_count = 0

        for i, ticker in enumerate(tickers, 1):
            # Skip if already processed
            if ticker in self.working_etfs or ticker in self.blacklist:
                continue

            if verbose:
                print(f"[{i}/{len(tickers)}] Testing {ticker}...", end=" ")

            if self.validate_ticker(ticker):
                if verbose:
                    print("✓")
                self.working_etfs[ticker] = {"status": "active"}
                validated_count += 1
            else:
                if verbose:
                    print("✗")
                self.blacklist[ticker] = {"status": "invalid"}
                blacklisted_count += 1

            # Save progress every 50 tickers
            if (i % 50) == 0:
                self._save_json(self.working_etfs, self.etfs_file)
                self._save_json(self.blacklist, self.blacklist_file)
                if verbose:
                    print(f"\n  [Progress saved: {len(self.working_etfs)} working, {len(self.blacklist)} blacklisted]\n")

        # Save final results
        self._save_json(self.working_etfs, self.etfs_file)
        self._save_json(self.blacklist, self.blacklist_file)

        if verbose:
            print("\n✓ Discovery complete!")
            print(f"  {self.etfs_file}: {len(self.working_etfs)} working ETFs")
            print(f"  {self.blacklist_file}: {len(self.blacklist)} blacklisted")

        return {
            "working": self.working_etfs,
            "blacklisted": self.blacklist,
        }

    def get_working_tickers(self) -> list[str]:
        """Get list of validated working ticker symbols."""
        return sorted(list(self.working_etfs.keys()))
