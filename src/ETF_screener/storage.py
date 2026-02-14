"""Data storage utilities for parquet files."""

from pathlib import Path

import pandas as pd


class ParquetStorage:
    """Handle parquet data storage and retrieval."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize storage.

        Args:
            data_dir: Directory to store parquet files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def save_etf_data(self, df: pd.DataFrame, symbol: str) -> Path:
        """
        Save ETF data to parquet file.

        Args:
            df: DataFrame with ETF data
            symbol: ETF symbol

        Returns:
            Path to saved parquet file
        """
        file_path = self.data_dir / f"{symbol.lower()}_data.parquet"
        df.to_parquet(file_path, compression="snappy", index=False)
        print(f"Saved {symbol} data to {file_path}")
        return file_path

    def load_etf_data(self, symbol: str) -> pd.DataFrame:
        """
        Load ETF data from parquet file.

        Args:
            symbol: ETF symbol

        Returns:
            DataFrame with ETF data or empty DataFrame if file not found
        """
        file_path = self.data_dir / f"{symbol.lower()}_data.parquet"
        if file_path.exists():
            df = pd.read_parquet(file_path)
            print(f"Loaded {symbol} data from {file_path}")
            return df
        else:
            print(f"No parquet file found for {symbol}")
            return pd.DataFrame()

    def save_multiple_etfs(self, etf_dict: dict[str, pd.DataFrame]) -> dict:
        """
        Save multiple ETFs to parquet files.

        Args:
            etf_dict: Dictionary mapping symbol to DataFrame

        Returns:
            Dictionary mapping symbol to file path
        """
        results = {}
        for symbol, df in etf_dict.items():
            results[symbol] = self.save_etf_data(df, symbol)
        return results

    def list_available_etfs(self) -> list[str]:
        """
        List all available ETFs in storage.

        Returns:
            List of ETF symbols
        """
        symbols = []
        for parquet_file in self.data_dir.glob("*_data.parquet"):
            symbol = parquet_file.stem.replace("_data", "").upper()
            symbols.append(symbol)
        return sorted(symbols)
