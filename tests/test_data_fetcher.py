"""Tests for data_fetcher module."""

import os
import threading
from concurrent.futures import CancelledError
from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from ETF_screener.data_fetcher import FinnhubFetcher, _FinnhubRequestGate
from ETF_screener.market_data_provider import MarketDataPermissionError


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class RecordingSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class TestFinnhubFetcher:
    """Test Finnhub data fetcher."""

    def test_fetcher_initialization_with_api_key(self):
        """Test that fetcher initializes with provided API key."""
        fetcher = FinnhubFetcher(api_key="test_key_123")
        assert fetcher.api_key == "test_key_123"

    def test_fetcher_initialization_without_api_key_raises_error(self):
        """Test that fetcher raises error without API key."""
        # Mock the environment to ensure FINNHUB_API_KEY is not set
        with patch.dict(os.environ, {}, clear=False):
            # Remove FINNHUB_API_KEY if it exists
            os.environ.pop("FINNHUB_API_KEY", None)
            with pytest.raises(ValueError, match="Finnhub API key not provided"):
                FinnhubFetcher(api_key=None)

    def test_base_url_is_set(self):
        """Test that base URL is correctly set."""
        fetcher = FinnhubFetcher(api_key="test_key")
        assert fetcher.base_url == "https://finnhub.io/api/v1"

    def test_incremental_candles_are_normalized_and_key_uses_header(self):
        session = RecordingSession(
            FakeResponse(
                {
                    "s": "ok",
                    "t": [1787875200],
                    "o": [100.0],
                    "h": [102.0],
                    "l": [99.0],
                    "c": [101.0],
                    "v": [123_456],
                }
            )
        )
        fetcher = FinnhubFetcher(api_key="secret", session=session)
        _FinnhubRequestGate.reset_for_tests()

        frame = fetcher.fetch_historical_data(
            "AAPL",
            start_date=date(2026, 8, 27),
            end_date=date(2026, 8, 29),
        )

        assert frame.columns.tolist() == [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Dividends",
        ]
        assert frame["Dividends"].tolist() == [0.0]
        _, request = session.calls[0]
        assert request["headers"] == {"X-Finnhub-Token": "secret"}
        assert "token" not in request["params"]
        assert request["params"]["resolution"] == "D"
        assert request["params"]["from"] == int(
            pd.Timestamp("2026-08-27", tz="UTC").timestamp()
        )

    def test_permission_error_explains_historical_candle_plan(self):
        session = RecordingSession(FakeResponse({}, status_code=403))
        _FinnhubRequestGate.reset_for_tests()

        with pytest.raises(MarketDataPermissionError, match="Premium"):
            FinnhubFetcher(api_key="free-key", session=session).fetch_historical_data(
                "AAPL"
            )

    def test_pre_cancelled_request_never_reaches_finnhub(self):
        session = RecordingSession(FakeResponse({"s": "no_data"}))
        cancel_event = threading.Event()
        cancel_event.set()
        _FinnhubRequestGate.reset_for_tests()

        with pytest.raises(CancelledError):
            FinnhubFetcher(api_key="key", session=session).fetch_historical_data(
                "AAPL", cancel_event=cancel_event
            )

        assert session.calls == []
