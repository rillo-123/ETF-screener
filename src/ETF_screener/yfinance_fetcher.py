"""Fetch ETF data from Yahoo Finance API."""

import logging
import os
import random
import threading
import time
from concurrent.futures import CancelledError
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from tqdm import tqdm


class _FallbackYFRateLimitError(RuntimeError):
    def __init__(self):
        super().__init__("Too Many Requests. Rate limited. Try after a while.")


YFRateLimitError: type[Exception] = getattr(
    getattr(yf, "exceptions", None),
    "YFRateLimitError",
    _FallbackYFRateLimitError,
)


logger = logging.getLogger(__name__)

YAHOO_MIN_REQUEST_INTERVAL_SECONDS = max(
    0.0, float(os.getenv("ETF_SCREENER_YAHOO_REQUEST_INTERVAL", "1.0"))
)
YAHOO_RATE_LIMIT_BASE_BACKOFF_SECONDS = max(
    1.0, float(os.getenv("ETF_SCREENER_YAHOO_RATE_BACKOFF", "30"))
)
YAHOO_RATE_LIMIT_MAX_BACKOFF_SECONDS = max(
    YAHOO_RATE_LIMIT_BASE_BACKOFF_SECONDS,
    float(os.getenv("ETF_SCREENER_YAHOO_RATE_MAX_BACKOFF", "900")),
)


class _YahooRequestGate:
    """Process-wide pacing and circuit breaking for Yahoo requests."""

    _lock = threading.Lock()
    _next_request_at = 0.0
    _blocked_until = 0.0
    _rate_limit_strikes = 0

    @classmethod
    def wait(cls, cancel_event=None) -> None:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError("Yahoo request cancelled")
            with cls._lock:
                now = time.monotonic()
                ready_at = max(cls._next_request_at, cls._blocked_until)
                if ready_at <= now:
                    cls._next_request_at = now + YAHOO_MIN_REQUEST_INTERVAL_SECONDS
                    return
                delay = min(ready_at - now, 1.0)
            if cancel_event is not None:
                if cancel_event.wait(delay):
                    raise CancelledError("Yahoo request cancelled")
            else:
                time.sleep(delay)

    @classmethod
    def record_rate_limit(cls) -> float:
        with cls._lock:
            cls._rate_limit_strikes += 1
            base_delay = min(
                YAHOO_RATE_LIMIT_BASE_BACKOFF_SECONDS
                * (2 ** (cls._rate_limit_strikes - 1)),
                YAHOO_RATE_LIMIT_MAX_BACKOFF_SECONDS,
            )
            delay = min(
                base_delay + random.uniform(0.0, min(5.0, base_delay * 0.1)),
                YAHOO_RATE_LIMIT_MAX_BACKOFF_SECONDS,
            )
            cls._blocked_until = max(cls._blocked_until, time.monotonic() + delay)
            return float(delay)

    @classmethod
    def record_success(cls) -> None:
        with cls._lock:
            cls._rate_limit_strikes = 0

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._lock:
            cls._next_request_at = 0.0
            cls._blocked_until = 0.0
            cls._rate_limit_strikes = 0


class YFinanceFetcher:
    """Fetch historical data from Yahoo Finance."""

    def __init__(self):
        """Initialize Yahoo Finance fetcher."""
        self.name = "Yahoo Finance"

    def _fetch_yf(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        cancel_event=None,
    ) -> pd.DataFrame:
        """Raw yfinance fetch, returns normalized DataFrame or empty DataFrame."""
        _YahooRequestGate.wait(cancel_event)
        try:
            df = yf.Ticker(symbol).history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=False,
                actions=True,
            )
        except YFRateLimitError:
            delay = _YahooRequestGate.record_rate_limit()
            logger.warning(
                "Yahoo rate limit reached for %s; pausing requests for %.1f seconds",
                symbol,
                delay,
            )
            raise
        except Exception as e:
            if "too many requests" in str(e).lower() or "429" in str(e):
                delay = _YahooRequestGate.record_rate_limit()
                logger.warning(
                    "Yahoo rate limit reached for %s; pausing requests for %.1f seconds",
                    symbol,
                    delay,
                )
                raise YFRateLimitError() from e
            logger.debug("yfinance error for %s: %s", symbol, e)
            return pd.DataFrame()
        _YahooRequestGate.record_success()
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
        interval: str = "1d",
        cancel_event=None,
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
        attempts = 2
        for attempt in range(attempts):
            df = self._fetch_yf(
                symbol,
                resolved_start,
                resolved_end,
                interval=interval,
                cancel_event=cancel_event,
            )
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
                    df = self._fetch_yf(
                        fallback,
                        resolved_start,
                        resolved_end,
                        interval=interval,
                        cancel_event=cancel_event,
                    )
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
        self,
        symbols: list[str],
        days: int = 365,
        quiet: bool = False,
        interval: str = "1d",
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
                results[symbol] = self.fetch_historical_data(
                    symbol, days, interval=interval
                )
            except Exception as e:
                logger.warning(f"Skipping {symbol}: {str(e)}")
                if not quiet:
                    print(f"Error fetching {symbol}: {str(e)}")
        return results
