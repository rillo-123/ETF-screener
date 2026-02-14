"""Tests for data_fetcher module."""

import os
from unittest.mock import patch

import pytest

from ETF_screener.data_fetcher import FinnhubFetcher


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
