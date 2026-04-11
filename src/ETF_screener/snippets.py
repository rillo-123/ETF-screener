"""Helper module for quick data analysis snippets.

Provides utility functions for iterating through database and filtering ETFs.

Example:
    from snippets import Snippet

    snippet = Snippet()

    # Find all tickers with RSI > 70
    for ticker in snippet.iterate_tickers():
        df = snippet.get_data(ticker)
        rsi = df['RSI'].iloc[-1]
        if rsi > 70:
            print(f"{ticker}: RSI={rsi:.1f}")
"""

from typing import Iterator, Callable, Any
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import add_indicators
from ETF_screener.yfinance_fetcher import YFinanceFetcher


class Snippet:
    """Helper class for writing quick analysis snippets.

    By default, automatically fetches data from yfinance on cache miss,
    stores it in the database, and returns it with indicators calculated.

    This enables lazy-loading - no need to run 'etfs refresh' beforehand.
    Just query what you need and it will be fetched if missing.

    Set auto_fetch=False to use only cached database data.
    """

    def __init__(self, db_path: str = "data/etfs.db", auto_fetch: bool = True):
        """Initialize with database connection.

        Args:
            db_path: Path to SQLite database
            auto_fetch: If True, automatically fetch from yfinance on cache miss (default True)
        """
        self.db = ETFDatabase(db_path=db_path)
        self.auto_fetch = auto_fetch
        self.fetcher = YFinanceFetcher() if auto_fetch else None

    def iterate_tickers(self) -> Iterator[str]:
        """Iterate through all tickers in database (with progress bar).

        Yields:
            Ticker symbol
        """
        tickers = self.db.get_tickers()
        for ticker in tqdm(tickers, desc="Processing ETFs", leave=False, ncols=80):
            yield ticker

    def get_data(self, ticker: str, days: int = 60) -> pd.DataFrame:
        """Get historical data for a ticker.

        If auto_fetch is True and data is not in database or insufficient,
        automatically fetches from yfinance and caches it.

        Args:
            ticker: ETF ticker symbol
            days: Number of days to fetch

        Returns:
            DataFrame with OHLCV and indicators
        """
        # Try to get from database first
        df = self.db.get_ticker_data(ticker, days=days)

        # If auto_fetch enabled and data is empty or insufficient, fetch from yfinance
        if (
            self.auto_fetch
            and self.fetcher is not None
            and (df.empty or len(df) < days * 0.8)
        ):  # 80% threshold
            try:
                df = self.fetcher.fetch_historical_data(ticker, days=days)
                if not df.empty:
                    # Add indicators before caching
                    df = add_indicators(df)
                    # Store in database for future use
                    self.db.insert_dataframe(df, ticker)
            except Exception:
                # If fetch fails, return what we have from DB (if anything)
                pass

        return df

    def get_all_data(self, days: int = 60) -> dict[str, pd.DataFrame]:
        """Get data for all tickers.

        Args:
            days: Number of days to fetch for each ticker

        Returns:
            Dictionary mapping ticker to DataFrame
        """
        result = {}
        tickers = self.db.get_tickers()

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {
                executor.submit(self.get_data, ticker, days): ticker
                for ticker in tickers
            }
            for future in tqdm(
                as_completed(future_to_ticker),
                total=len(tickers),
                desc="Loading all tickers",
                ncols=80,
            ):
                ticker = future_to_ticker[future]
                try:
                    df = future.result()
                    if not df.empty:
                        result[ticker] = df
                except Exception:
                    pass
        return result

    def map_parallel(
        self,
        func: Callable[[str, pd.DataFrame], Any],
        days: int = 60,
        desc: str = "Processing",
    ) -> list[Any]:
        """Run a function over all tickers in parallel.

        Args:
            func: Function that takes (ticker, dataframe) and returns a result
            days: Number of days of data to provide to the function
            desc: Progress bar description

        Returns:
            List of non-None results from the function
        """
        results = []
        tickers = list(
            self.db.get_tickers()
        )  # Materialize to list to ensure length is known

        def _worker(ticker_symbol):
            try:
                # We use a fresh database connection per thread to avoid SQLite locking/threading issues
                from ETF_screener.database import ETFDatabase

                thread_db = ETFDatabase(db_path=self.db.db_path)

                # Fetch data manually for the thread
                df = thread_db.get_ticker_data(ticker_symbol, days=days)

                # Auto-fetch if missing (optional enhancement, but keep simple for now)
                if df.empty:
                    # For now just return empty, auto-fetch in threads is complex with yfinance
                    return None

                return func(ticker_symbol, df)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {
                executor.submit(_worker, ticker): ticker for ticker in tickers
            }
            for future in tqdm(
                as_completed(future_to_ticker), total=len(tickers), desc=desc, ncols=80
            ):
                try:
                    res = future.result()
                    if res is not None:
                        results.append(res)
                except Exception:
                    pass
        return results

    def filter_overbought(self, rsi_threshold: float = 70) -> list[tuple[str, float]]:
        """Find all tickers with RSI > threshold.

        Args:
            rsi_threshold: RSI threshold (default 70 = overbought)

        Returns:
            List of (ticker, rsi_value) tuples
        """
        results = []
        tickers = list(self.iterate_tickers())

        for ticker in tqdm(tickers, desc="Scanning overbought", ncols=80):
            try:
                df = self.get_data(ticker)
                if df.empty or "RSI" not in df.columns:
                    continue
                rsi = df["RSI"].iloc[-1]
                if not pd.isna(rsi) and rsi > rsi_threshold:
                    results.append((ticker, rsi))
            except Exception:
                continue
        return sorted(results, key=lambda x: x[1], reverse=True)

    def filter_oversold(self, rsi_threshold: float = 30) -> list[tuple[str, float]]:
        """Find all tickers with RSI < threshold.

        Args:
            rsi_threshold: RSI threshold (default 30 = oversold)

        Returns:
            List of (ticker, rsi_value) tuples
        """
        results = []
        tickers = list(self.iterate_tickers())

        for ticker in tqdm(tickers, desc="Scanning oversold", ncols=80):
            try:
                df = self.get_data(ticker)
                if df.empty or "RSI" not in df.columns:
                    continue
                rsi = df["RSI"].iloc[-1]
                if not pd.isna(rsi) and rsi < rsi_threshold:
                    results.append((ticker, rsi))
            except Exception:
                continue
        return sorted(results, key=lambda x: x[1])

    def filter_by_ema(self, above_ema: bool = True) -> list[str]:
        """Find tickers above/below EMA50.

        Args:
            above_ema: True for price > EMA50, False for price < EMA50

        Returns:
            List of ticker symbols
        """
        results = []
        tickers = list(self.iterate_tickers())
        condition = "above" if above_ema else "below"

        for ticker in tqdm(tickers, desc=f"Filtering EMA ({condition})", ncols=80):
            try:
                df = self.get_data(ticker)
                if df.empty or "EMA_50" not in df.columns:
                    continue
                latest = df.iloc[-1]
                if above_ema and latest["Close"] > latest["EMA_50"]:
                    results.append(ticker)
                elif not above_ema and latest["Close"] < latest["EMA_50"]:
                    results.append(ticker)
            except Exception:
                continue
        return results

    def filter_by_supertrend(self, color: str = "green") -> list[str]:
        """Find tickers by Supertrend color.

        Args:
            color: 'green' (price > supertrend) or 'red' (price < supertrend)

        Returns:
            List of ticker symbols
        """
        results = []
        tickers = list(self.iterate_tickers())

        for ticker in tqdm(tickers, desc=f"Filtering Supertrend ({color})", ncols=80):
            try:
                df = self.get_data(ticker)
                if df.empty or "Supertrend" not in df.columns:
                    continue
                latest = df.iloc[-1]
                if color.lower() == "green" and latest["Close"] > latest["Supertrend"]:
                    results.append(ticker)
                elif color.lower() == "red" and latest["Close"] < latest["Supertrend"]:
                    results.append(ticker)
            except Exception:
                continue
        return results

    def find_oversold_in_period(
        self, days_lookback: int = 30, rsi_threshold: float = 30
    ) -> dict[str, list]:
        """Find tickers that were oversold at any point in the lookback period.

        Args:
            days_lookback: Number of days to look back (default 30 days)
            rsi_threshold: RSI threshold for oversold (default 30)

        Returns:
            Dictionary mapping ticker to list of dates when oversold
            Example: {'EXS1.DE': ['2026-01-15', '2026-01-16'], ...}
        """
        results = {}
        tickers = list(self.iterate_tickers())

        for ticker in tqdm(tickers, desc=f"Scanning {days_lookback}d period", ncols=80):
            try:
                df = self.get_data(ticker, days=days_lookback)
                if df.empty or "RSI" not in df.columns:
                    continue

                # Find all rows where RSI < threshold
                oversold_mask = df["RSI"] < rsi_threshold
                oversold_dates = df[oversold_mask]["Date"].astype(str).tolist()

                if oversold_dates:
                    results[ticker] = oversold_dates
            except Exception:
                continue
        return results

    def find_overbought_in_period(
        self, days_lookback: int = 30, rsi_threshold: float = 70
    ) -> dict[str, list]:
        """Find tickers that were overbought at any point in the lookback period.

        Args:
            days_lookback: Number of days to look back (default 30 days)
            rsi_threshold: RSI threshold for overbought (default 70)

        Returns:
            Dictionary mapping ticker to list of dates when overbought
            Example: {'EXS1.DE': ['2026-02-10', '2026-02-11'], ...}
        """
        results = {}
        tickers = list(self.iterate_tickers())

        for ticker in tqdm(tickers, desc=f"Scanning {days_lookback}d period", ncols=80):
            try:
                df = self.get_data(ticker, days=days_lookback)
                if df.empty or "RSI" not in df.columns:
                    continue

                # Find all rows where RSI > threshold
                overbought_mask = df["RSI"] > rsi_threshold
                overbought_dates = df[overbought_mask]["Date"].astype(str).tolist()

                if overbought_dates:
                    results[ticker] = overbought_dates
            except Exception:
                continue
        return results

    def close(self) -> None:
        """Close database connection and cleanup resources."""
        self.db.close()
        if self.fetcher:
            self.fetcher = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.close()
