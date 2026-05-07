import pandas as pd

from ETF_screener.strategy_manager import CachedStrategyManager


def test_indicator_memory_cache_is_bounded(monkeypatch):
    class FakeDb:
        def get_ticker_data(self, ticker, days=365):
            return pd.DataFrame({"Close": [1.0, 2.0, 3.0]})

    def fake_indicator(series, period=1):
        return series + period

    monkeypatch.setattr(
        "ETF_screener.strategy_manager.pd.DataFrame.to_parquet",
        lambda self, *args, **kwargs: None,
    )
    monkeypatch.setattr(CachedStrategyManager, "_memory_cache_limit", 3)
    CachedStrategyManager._memory_cache.clear()

    manager = CachedStrategyManager(FakeDb())

    first_key = None
    last_key = None
    for idx in range(5):
        ticker = f"T{idx}"
        manager.get_indicator(pd.DataFrame({"Close": [1.0, 2.0, 3.0]}), ticker, fake_indicator, "ema", period=idx)
        current_key = manager._get_cache_key(ticker, "ema", {"period": idx}, 3)
        if idx == 0:
            first_key = current_key
        last_key = current_key

    assert len(CachedStrategyManager._memory_cache) == 3
    assert first_key not in CachedStrategyManager._memory_cache
    assert last_key in CachedStrategyManager._memory_cache
