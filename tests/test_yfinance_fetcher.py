import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest
from yfinance.exceptions import YFRateLimitError

from ETF_screener import yfinance_fetcher
from ETF_screener.yfinance_fetcher import YFinanceFetcher, _YahooRequestGate


@pytest.fixture(autouse=True)
def reset_yahoo_request_gate():
    _YahooRequestGate.reset_for_tests()
    yield
    _YahooRequestGate.reset_for_tests()


def _history_frame():
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-08-28"]),
            "Open": [100.0],
            "High": [101.0],
            "Low": [99.0],
            "Close": [100.5],
            "Volume": [100_000],
        }
    ).set_index("Date")


def test_yahoo_request_gate_spaces_concurrent_history_calls(monkeypatch):
    monkeypatch.setattr(yfinance_fetcher, "YAHOO_MIN_REQUEST_INTERVAL_SECONDS", 0.03)
    _YahooRequestGate.reset_for_tests()
    call_times = []

    class FakeTicker:
        def __init__(self, _symbol):
            pass

        def history(self, **_kwargs):
            call_times.append(time.monotonic())
            return _history_frame()

    monkeypatch.setattr(yfinance_fetcher.yf, "Ticker", FakeTicker)
    fetcher = YFinanceFetcher()
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda symbol: fetcher.fetch_historical_data(symbol), ["AAA", "BBB"]))

    assert len(call_times) == 2
    assert abs(call_times[1] - call_times[0]) >= 0.025


def test_yahoo_rate_limit_opens_shared_circuit_without_ticker_retries(monkeypatch):
    monkeypatch.setattr(yfinance_fetcher, "YAHOO_MIN_REQUEST_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(yfinance_fetcher, "YAHOO_RATE_LIMIT_BASE_BACKOFF_SECONDS", 0.03)
    monkeypatch.setattr(yfinance_fetcher, "YAHOO_RATE_LIMIT_MAX_BACKOFF_SECONDS", 0.03)
    monkeypatch.setattr(yfinance_fetcher.random, "uniform", lambda *_args: 0.0)
    _YahooRequestGate.reset_for_tests()
    calls = 0

    class RateLimitedTicker:
        def __init__(self, _symbol):
            pass

        def history(self, **_kwargs):
            nonlocal calls
            calls += 1
            raise YFRateLimitError()

    monkeypatch.setattr(yfinance_fetcher.yf, "Ticker", RateLimitedTicker)
    started = time.monotonic()
    with pytest.raises(YFRateLimitError):
        YFinanceFetcher().fetch_historical_data("AAA")

    assert calls == 1
    assert _YahooRequestGate._blocked_until >= started + 0.02
