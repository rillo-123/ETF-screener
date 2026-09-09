import os
import time

import pytest

from ETF_screener import cache_policy, config_loader


def test_cache_expiration_is_a_miss(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cache_policy, "get_paths", lambda: {"cache_policy": {"max_age_days": 1}}
    )
    path = tmp_path / "entry.pkl"
    path.write_bytes(b"cached")
    assert cache_policy.cache_is_fresh(path)
    os.utime(path, (1, 1))
    assert not cache_policy.cache_is_fresh(path)


def test_price_write_failure_preserves_existing_history(tmp_path, monkeypatch):
    import pandas as pd
    from ETF_screener.storage import ParquetStorage

    storage = ParquetStorage(str(tmp_path))
    original = pd.DataFrame({"Close": [10.0]})
    storage.save_etf_data(original, "AAA")

    def broken_write(*args, **kwargs):
        raise OSError("USB disconnected")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", broken_write)
    with pytest.raises(OSError, match="USB disconnected"):
        storage.save_etf_data(pd.DataFrame({"Close": [20.0]}), "AAA")
    pd.testing.assert_frame_equal(storage.load_etf_data("AAA"), original)


def test_nasdaq_focus_is_shared_and_explicit_override_wins(tmp_path, monkeypatch):
    import json
    from ETF_screener import market_data_service as service

    focus = tmp_path / "focus.json"
    focus.write_text(json.dumps({"tickers": ["AAA", "BBB"]}))
    monkeypatch.setattr(service, "get_paths", lambda: {"nasdaq_focus_file": str(focus)})
    assert service.filter_low_vitality_nasdaq_tickers(None, None, ["AAA", "CCC"]) == [
        "AAA"
    ]
    refresher = object.__new__(service.MarketDataRefresher)
    refresher.etfs_file = tmp_path / "nasdaq.json"
    refresher.tracked_tickers_override = None
    monkeypatch.setattr(refresher, "_load_blacklist", lambda: {"BBB"})
    assert refresher._load_tracked_tickers() == ["AAA"]
    refresher.tracked_tickers_override = ["CCC"]
    assert refresher._load_tracked_tickers() == ["CCC"]


def test_nasdaq_catalogue_overrides_legacy_metadata_source(monkeypatch):
    import pandas as pd
    from unittest.mock import MagicMock
    from ETF_screener.dashboard import app_fast as dashboard

    monkeypatch.setattr(dashboard, "_cached_dashboard_tickers", lambda *args: ("AAA",))
    monkeypatch.setattr(dashboard, "_cached_etf_metadata_map", lambda: {})
    monkeypatch.setattr(dashboard, "_load_metadata_file_map", lambda path: {"AAA": {}})
    monkeypatch.setattr(dashboard, "load_nasdaq_focus", lambda: {"AAA"})
    monkeypatch.setattr(dashboard, "ETFDatabase", MagicMock())
    monkeypatch.setattr(
        dashboard.pd,
        "read_sql_query",
        lambda *args: pd.DataFrame(
            [{"ticker": "AAA", "name": "Alpha", "source": "config/etfs.json"}]
        ),
    )
    dashboard._cached_dashboard_universe.cache_clear()
    try:
        assert (
            dashboard._cached_dashboard_universe("test", None)[0]["exchange"]
            == "nasdaq"
        )
    finally:
        dashboard._cached_dashboard_universe.cache_clear()


def test_cache_limits_preserve_prices_and_unrelated_files(tmp_path, monkeypatch):
    root = tmp_path / "cache"
    root.mkdir()
    paths = {
        "data": {"cache": str(root)},
        "cache_policy": {"max_bytes": 15, "max_files": 2, "max_age_days": 14},
    }
    monkeypatch.setattr(cache_policy, "get_paths", lambda: paths)
    for name in ["old.pkl", "middle.pkl", "new.pkl", "abc_data.parquet", "notes.txt"]:
        (root / name).write_bytes(b"x" * 10)
    os.utime(root / "old.pkl", (1, 1))
    os.utime(root / "middle.pkl", (time.time() - 10, time.time() - 10))
    result = cache_policy.trim_cache()
    assert result["freed_bytes"] == 20
    assert (root / "new.pkl").exists()
    assert (root / "abc_data.parquet").exists()
    assert (root / "notes.txt").exists()


def test_external_override_requires_marker_on_every_access(tmp_path, monkeypatch):
    config = tmp_path / "config"
    config.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (config / "paths.json").write_text('{"data":{"cache":"data/cache"}}')
    import json

    (config / "paths.local.json").write_text(
        json.dumps(
            {
                "external_storage_root": str(external),
                "data": {"cache": str(external / "cache")},
            }
        )
    )
    monkeypatch.setattr(config_loader, "CONFIG_DIR", config)
    monkeypatch.setattr(config_loader, "_paths_cache", None)
    monkeypatch.delenv("ETF_SCREENER_IGNORE_LOCAL_PATHS")
    with pytest.raises(RuntimeError, match="Connect the Kingston"):
        config_loader.get_paths()
    marker = external / ".etf-screener-storage"
    marker.touch()
    assert config_loader.get_paths()["data"]["cache"] == str(external / "cache")
    marker.unlink()
    with pytest.raises(RuntimeError, match="No replacement store"):
        config_loader.get_paths()
