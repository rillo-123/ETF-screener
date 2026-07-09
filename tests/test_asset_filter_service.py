from pathlib import Path

import pandas as pd
import pytest

from ETF_screener.asset_filter_service import AssetFilterService, get_filtered_assets
from ETF_screener.database import ETFDatabase
from ETF_screener.query_service import ETFQueryService
from ETF_screener.storage import ParquetStorage


def _make_filter_frame(
    *,
    start: str = "2026-01-01",
    periods: int = 25,
    latest_rsi: float,
    volume: int,
) -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=periods, freq="D")
    closes = [100.0 + (idx * 0.25) for idx in range(periods)]
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": [value - 0.2 for value in closes],
            "High": [value + 0.4 for value in closes],
            "Low": [value - 0.5 for value in closes],
            "Close": closes,
            "Volume": [volume] * periods,
            "Dividends": [0.0] * periods,
            "RSI": ([50.0] * (periods - 1)) + [latest_rsi],
        }
    )


def _make_service(tmp_path: Path) -> AssetFilterService:
    storage = ParquetStorage(data_dir=str(tmp_path / "parquet"))
    db = ETFDatabase(db_path=str(tmp_path / "etfs.db"))
    query_service = ETFQueryService(db=db, storage=storage)
    return AssetFilterService(query_service=query_service)


def test_get_filtered_assets_supports_all_mode_composition(tmp_path, monkeypatch):
    service = _make_service(tmp_path)
    service.query_service.storage.save_etf_data(
        _make_filter_frame(latest_rsi=25.0, volume=300_000),
        "BOTH.DE",
    )
    service.query_service.storage.save_etf_data(
        _make_filter_frame(latest_rsi=45.0, volume=320_000),
        "LIQ.DE",
    )
    service.query_service.storage.save_etf_data(
        _make_filter_frame(latest_rsi=24.0, volume=50_000),
        "OS.DE",
    )
    monkeypatch.setattr(
        service.query_service,
        "_load_universe_tickers",
        lambda _source: ["BOTH.DE", "LIQ.DE", "OS.DE"],
    )

    result = service.get_filtered_assets(
        "xetra",
        ["high_liquidity", "oversold"],
        mode="all",
    )

    assert result["source"] == "xetra"
    assert result["mode"] == "all"
    assert result["filters"] == ["high_liquidity", "oversold"]
    assert result["row_count"] == 1
    assert result["rows"][0]["ticker"] == "BOTH.DE"
    assert result["rows"][0]["matched_filters"] == ["high_liquidity", "oversold"]
    assert result["rows"][0]["filter_results"]["high_liquidity"]["matched"] is True
    assert result["rows"][0]["filter_results"]["oversold"]["matched"] is True


def test_get_filtered_assets_supports_any_mode(tmp_path, monkeypatch):
    service = _make_service(tmp_path)
    service.query_service.storage.save_etf_data(
        _make_filter_frame(latest_rsi=25.0, volume=300_000),
        "BOTH.DE",
    )
    service.query_service.storage.save_etf_data(
        _make_filter_frame(latest_rsi=45.0, volume=320_000),
        "LIQ.DE",
    )
    service.query_service.storage.save_etf_data(
        _make_filter_frame(latest_rsi=24.0, volume=50_000),
        "OS.DE",
    )
    monkeypatch.setattr(
        service.query_service,
        "_load_universe_tickers",
        lambda _source: ["BOTH.DE", "LIQ.DE", "OS.DE"],
    )

    result = get_filtered_assets(
        "xetra",
        ["high_liquidity", "oversold"],
        mode="any",
        query_service=service.query_service,
    )

    assert result["row_count"] == 3
    assert {row["ticker"] for row in result["rows"]} == {"BOTH.DE", "LIQ.DE", "OS.DE"}


def test_get_filtered_assets_rejects_unknown_filter(tmp_path):
    service = _make_service(tmp_path)

    with pytest.raises(ValueError, match="Unsupported asset filter"):
        service.get_filtered_assets("xetra", ["not_a_real_filter"])

