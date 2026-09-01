"""Tests for provider-neutral market-data construction."""

import pytest

from ETF_screener.data_fetcher import FinnhubFetcher
from ETF_screener.market_data_provider import (
    create_market_data_provider,
    normalize_market_data_provider_name,
)
from ETF_screener.yfinance_fetcher import YFinanceFetcher


def test_provider_factory_defaults_to_yahoo(monkeypatch):
    monkeypatch.delenv("ETF_SCREENER_MARKET_DATA_PROVIDER", raising=False)

    assert isinstance(create_market_data_provider(), YFinanceFetcher)


def test_provider_factory_selects_finnhub_from_environment(monkeypatch):
    monkeypatch.setenv("ETF_SCREENER_MARKET_DATA_PROVIDER", "finnhub")
    monkeypatch.setenv("FINNHUB_API_KEY", "configured-key")

    provider = create_market_data_provider()

    assert isinstance(provider, FinnhubFetcher)
    assert provider.api_key == "configured-key"


def test_provider_factory_accepts_yfinance_alias_and_rejects_unknown():
    assert normalize_market_data_provider_name("yfinance") == "yahoo"
    with pytest.raises(ValueError, match="Unknown market-data provider 'mystery'"):
        create_market_data_provider("mystery")
