# Conftest for pytest configuration
import os
import pytest

# Unit tests must not read/write a developer's removable-drive configuration.
os.environ["ETF_SCREENER_IGNORE_LOCAL_PATHS"] = "1"


@pytest.fixture(autouse=True)
def isolated_derived_cache(monkeypatch, tmp_path):
    from ETF_screener.config_loader import get_paths

    monkeypatch.setitem(get_paths()["data"], "cache", str(tmp_path / "cache"))
    from ETF_screener import screener_controls

    monkeypatch.setattr(
        screener_controls,
        "INDICATOR_HISTORY_DISK_CACHE",
        str(tmp_path / "cache" / "screen-indicators"),
    )
