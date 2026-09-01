"""Provider-neutral contracts and construction for historical market data."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional, Protocol, runtime_checkable

import pandas as pd


class MarketDataProviderError(RuntimeError):
    """Base exception raised by a remote market-data provider."""


class MarketDataRateLimitError(MarketDataProviderError):
    """Raised when a provider rejects a request because of its rate limit."""


class MarketDataPermissionError(MarketDataProviderError):
    """Raised when the configured plan cannot access an endpoint."""


@runtime_checkable
class MarketDataProvider(Protocol):
    """Minimum contract required by cache refresh and screening workflows."""

    name: str

    def fetch_historical_data(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[datetime | date | str] = None,
        end_date: Optional[datetime | date | str] = None,
        interval: str = "1d",
        cancel_event=None,
    ) -> pd.DataFrame:
        """Return normalized Date/OHLCV data, optionally including Dividends."""

    def fetch_multiple_etfs(
        self,
        symbols: list[str],
        days: int = 365,
        quiet: bool = False,
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """Fetch a collection of symbols for CLI/batch workflows."""


def normalize_market_data_provider_name(provider: str | None) -> str:
    """Return the canonical provider name or reject an unknown adapter."""
    value = str(
        provider or os.getenv("ETF_SCREENER_MARKET_DATA_PROVIDER", "yahoo")
    ).strip().lower()
    aliases = {
        "yahoo": "yahoo",
        "yfinance": "yahoo",
        "finnhub": "finnhub",
    }
    try:
        return aliases[value]
    except KeyError as exc:
        supported = ", ".join(sorted(set(aliases.values())))
        raise ValueError(
            f"Unknown market-data provider '{value}'. Supported: {supported}"
        ) from exc


def create_market_data_provider(
    provider: str | None = None,
    *,
    api_key: str | None = None,
) -> MarketDataProvider:
    """Build the configured provider without coupling callers to adapters."""
    provider_name = normalize_market_data_provider_name(provider)
    if provider_name == "finnhub":
        from ETF_screener.data_fetcher import FinnhubFetcher

        return FinnhubFetcher(api_key=api_key)

    from ETF_screener.yfinance_fetcher import YFinanceFetcher

    return YFinanceFetcher()


def configured_market_data_provider_name() -> str:
    """Expose the selected provider without constructing a network client."""
    return normalize_market_data_provider_name(None)
