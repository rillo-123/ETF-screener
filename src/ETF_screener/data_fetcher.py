"""Finnhub historical market-data provider."""

import os
import threading
import time
from concurrent.futures import CancelledError
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import requests

from ETF_screener.market_data_provider import (
    MarketDataPermissionError,
    MarketDataRateLimitError,
)

FINNHUB_MIN_REQUEST_INTERVAL_SECONDS = max(
    0.0, float(os.getenv("ETF_SCREENER_FINNHUB_REQUEST_INTERVAL", "1.0"))
)
FINNHUB_RATE_LIMIT_BACKOFF_SECONDS = max(
    1.0, float(os.getenv("ETF_SCREENER_FINNHUB_RATE_BACKOFF", "60"))
)


class _FinnhubRequestGate:
    """Process-wide pacing for a plan whose exact quota may vary."""

    _lock = threading.Lock()
    _next_request_at = 0.0
    _blocked_until = 0.0

    @classmethod
    def wait(cls, cancel_event=None) -> None:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError("Finnhub request cancelled")
            with cls._lock:
                now = time.monotonic()
                ready_at = max(cls._next_request_at, cls._blocked_until)
                if ready_at <= now:
                    cls._next_request_at = now + FINNHUB_MIN_REQUEST_INTERVAL_SECONDS
                    return
                delay = min(ready_at - now, 1.0)
            if cancel_event is not None:
                if cancel_event.wait(delay):
                    raise CancelledError("Finnhub request cancelled")
            else:
                time.sleep(delay)

    @classmethod
    def record_rate_limit(cls, retry_after: float | None = None) -> None:
        delay = max(FINNHUB_RATE_LIMIT_BACKOFF_SECONDS, retry_after or 0.0)
        with cls._lock:
            cls._blocked_until = max(cls._blocked_until, time.monotonic() + delay)

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._lock:
            cls._next_request_at = 0.0
            cls._blocked_until = 0.0


class FinnhubFetcher:
    """Fetch historical data from Finnhub API."""

    name = "Finnhub"

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        session: requests.Session | None = None,
        base_url: str = "https://finnhub.io/api/v1",
    ):
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
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    @staticmethod
    def _timestamp(value: datetime | date | str) -> int:
        stamp = pd.Timestamp(value)
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize(timezone.utc)
        else:
            stamp = stamp.tz_convert(timezone.utc)
        return int(stamp.timestamp())

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

        Args:
            symbol: Stock/ETF symbol (e.g., 'EXS1' for XETRA)
            days: Number of days of historical data to fetch (default 365)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        resolutions = {"1d": "D", "1wk": "W", "1mo": "M"}
        try:
            resolution = resolutions[interval.lower()]
        except KeyError as exc:
            raise ValueError(
                f"Finnhub does not support interval '{interval}' in this adapter"
            ) from exc

        resolved_end = end_date or datetime.now(timezone.utc)
        resolved_start = start_date or (
            pd.Timestamp(resolved_end) - timedelta(days=days)
        )
        end_time = self._timestamp(resolved_end)
        start_time = self._timestamp(resolved_start)

        params: dict[str, str | int] = {
            "symbol": symbol,
            "resolution": resolution,
            "from": start_time,
            "to": end_time,
        }

        _FinnhubRequestGate.wait(cancel_event)
        response = self.session.get(
            f"{self.base_url}/stock/candle",
            params=params,
            headers={"X-Finnhub-Token": self.api_key},
            timeout=20,
        )
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError("Finnhub request cancelled")
        if response.status_code == 429:
            raw_retry_after = response.headers.get("Retry-After")
            try:
                retry_after = float(raw_retry_after) if raw_retry_after else None
            except ValueError:
                retry_after = None
            _FinnhubRequestGate.record_rate_limit(retry_after)
            raise MarketDataRateLimitError(
                "Finnhub rate limit reached; requests have been paused"
            )
        if response.status_code in {401, 403}:
            raise MarketDataPermissionError(
                "Finnhub rejected the API key or plan. Historical stock candles "
                "may require Premium access."
            )
        response.raise_for_status()

        data = response.json()

        if data.get("s") == "no_data":
            raise ValueError(f"No data found for symbol: {symbol}")
        if data.get("s") != "ok":
            raise RuntimeError(
                f"Finnhub returned an unexpected candle status: {data.get('s')!r}"
            )

        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(data["t"], unit="s"),
                "Open": data["o"],
                "High": data["h"],
                "Low": data["l"],
                "Close": data["c"],
                "Volume": data["v"],
                "Dividends": 0.0,
            }
        )

        return df.sort_values("Date").reset_index(drop=True)

    def fetch_multiple_etfs(
        self,
        symbols: list[str],
        days: int = 365,
        quiet: bool = False,
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch data for multiple ETFs.

        Args:
            symbols: List of ETF symbols
            days: Number of days of historical data to fetch

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        results: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            try:
                if not quiet:
                    print(f"Fetching data for {symbol}...")
                results[symbol] = self.fetch_historical_data(
                    symbol, days, interval=interval
                )
            except Exception as e:
                if not quiet:
                    print(f"Error fetching {symbol}: {str(e)}")
        return results
