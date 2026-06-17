import json
from pathlib import Path

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.query_service import ETFQueryService
from ETF_screener.storage import ParquetStorage


def _make_history_frame(
    symbol: str, start: str = "2026-01-01", periods: int = 6
) -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=periods, freq="D")
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": [10 + idx for idx in range(periods)],
            "High": [11 + idx for idx in range(periods)],
            "Low": [9 + idx for idx in range(periods)],
            "Close": [10.5 + idx for idx in range(periods)],
            "Volume": [1000 * (idx + 1) for idx in range(periods)],
            "Dividends": [0.0] * periods,
            "EMA_50": [10.2 + idx for idx in range(periods)],
            "Supertrend": [9.8 + idx for idx in range(periods)],
            "Signal": [0, 0, 1, 0, 0, 1][:periods],
        }
    )


def _make_service(tmp_path: Path) -> ETFQueryService:
    storage = ParquetStorage(data_dir=str(tmp_path / "parquet"))
    db = ETFDatabase(db_path=str(tmp_path / "etfs.db"))
    return ETFQueryService(db=db, storage=storage)


def test_query_price_history_reads_parquet_and_applies_tail_and_columns(tmp_path):
    service = _make_service(tmp_path)
    frame = _make_history_frame("AAA.DE", periods=6)
    service.storage.save_etf_data(frame, "AAA.DE")

    result = service.query_price_history(
        ticker="AAA.DE",
        days=3,
        columns="date,close,volume",
        limit=5,
    )

    assert result["dataset"] == "price_history"
    assert result["source"] == "parquet"
    assert result["columns"] == ["date", "close", "volume"]
    assert result["row_count"] == 3
    assert result["returned_rows"] == 3
    assert [row["close"] for row in result["rows"]] == [13.5, 14.5, 15.5]


def test_query_price_history_falls_back_to_database_range(tmp_path):
    service = _make_service(tmp_path)
    frame = _make_history_frame("BBB.DE", periods=4)
    service.db.insert_dataframe(frame, "BBB.DE")

    result = service.query_price_history(
        ticker="BBB.DE",
        start_date="2026-01-02",
        end_date="2026-01-03",
        columns="date,open,close",
    )

    assert result["source"] == "database_fallback"
    assert result["row_count"] == 2
    assert [row["open"] for row in result["rows"]] == [11, 12]
    assert str(result["summary"]["earliest_date"]).startswith("2026-01-02")
    assert str(result["summary"]["latest_date"]).startswith("2026-01-03")


def test_query_shortlist_filters_and_sorts_snapshot_rows(tmp_path):
    service = _make_service(tmp_path)
    service.db.upsert_shortlist_artifacts(
        [
            {
                "ticker": "CCC.DE",
                "as_of_date": "2026-06-15",
                "name": "Gamma ETF",
                "region": "Europe",
                "close": 101.0,
                "volume": 500000,
                "recent_entry_days": 2,
                "product_score": 7.0,
                "exposure_score": 6.0,
                "technical_score": 8.0,
                "final_score": 8.4,
                "label": "Buy",
                "reasons_json": "[]",
                "components_json": "{}",
                "artifact_version": "v1",
            },
            {
                "ticker": "DDD.DE",
                "as_of_date": "2026-06-15",
                "name": "Delta ETF",
                "region": "USA",
                "close": 99.0,
                "volume": 800000,
                "recent_entry_days": 4,
                "product_score": 6.0,
                "exposure_score": 5.0,
                "technical_score": 7.0,
                "final_score": 6.2,
                "label": "Watch",
                "reasons_json": "[]",
                "components_json": "{}",
                "artifact_version": "v1",
            },
        ]
    )

    result = service.query_shortlist(
        label="All",
        sort_by="volume",
        columns="ticker,label,volume",
        limit=10,
    )

    assert result["dataset"] == "shortlist"
    assert result["row_count"] == 2
    assert result["columns"] == ["ticker", "label", "volume"]
    assert [row["ticker"] for row in result["rows"]] == ["DDD.DE", "CCC.DE"]
    assert result["summary"]["buy_count"] == 1
    assert result["summary"]["watch_count"] == 1


def test_query_signal_scan_returns_recent_trend_forming_match(tmp_path, monkeypatch):
    service = _make_service(tmp_path)
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    frame = pd.DataFrame(
        {
            "Date": dates,
            "Open": [100.0 + (idx * 0.2) for idx in range(30)],
            "High": [100.4 + (idx * 0.2) for idx in range(30)],
            "Low": [99.6 + (idx * 0.2) for idx in range(30)],
            "Close": ([99.4] * 25) + [99.8, 100.4, 101.1, 101.8, 102.3],
            "Volume": [1000] * 24 + [1200, 1300, 1500, 1700, 1900, 2100],
            "Dividends": [0.0] * 30,
            "EMA_50": [100.0 + (idx * 0.03) for idx in range(30)],
            "Supertrend": ([100.2] * 26) + [99.7, 100.0, 100.3, 100.7],
            "Signal": [0] * 30,
        }
    )
    service.storage.save_etf_data(frame, "AAA.DE")
    monkeypatch.setattr(service, "_load_universe_tickers", lambda _source: ["AAA.DE"])

    result = service.query_signal_scan(
        source="xetra",
        signal="trend_forming",
        signal_age_max=5,
        min_reliability=6.0,
    )

    assert result["dataset"] == "signal_scan"
    assert result["summary"]["matched_tickers"] == 1
    assert result["rows"][0]["ticker"] == "AAA.DE"
    assert result["rows"][0]["signal_age_days"] <= 5
    assert "recent_ema50_reclaim" in result["rows"][0]["matched_rules"]


def test_query_signal_scan_returns_downtrend_turnaround_and_rejects_bulltrap(
    tmp_path, monkeypatch
):
    service = _make_service(tmp_path)
    dates = pd.date_range("2026-01-01", periods=70, freq="D")
    turnaround_frame = pd.DataFrame(
        {
            "Date": dates,
            "Open": ([130.0 - (idx * 0.7) for idx in range(66)])
            + [87.8, 89.2, 90.4, 91.7],
            "High": ([130.5 - (idx * 0.7) for idx in range(66)])
            + [88.4, 89.9, 91.4, 92.8],
            "Low": ([129.3 - (idx * 0.7) for idx in range(66)])
            + [87.2, 88.8, 90.0, 91.2],
            "Close": ([130.0 - (idx * 0.7) for idx in range(66)])
            + [88.0, 89.5, 91.0, 92.4],
            "Volume": ([1100] * 66) + [1450, 1900, 2200, 2600],
            "Dividends": [0.0] * 70,
            "EMA_50": ([125.0 - (idx * 0.6) for idx in range(66)])
            + [89.0, 88.9, 89.1, 89.5],
            "EMA_200": [116.0] * 66 + [111.8, 111.5, 111.2, 110.9],
            "Supertrend": ([132.0 - (idx * 0.65) for idx in range(66)])
            + [89.2, 89.0, 89.4, 89.9],
            "Signal": [0] * 70,
        }
    )
    bulltrap_frame = pd.DataFrame(
        {
            "Date": dates,
            "Open": ([130.0 - (idx * 0.7) for idx in range(65)])
            + [90.0, 92.0, 93.0, 92.2, 91.3],
            "High": ([130.4 - (idx * 0.7) for idx in range(65)])
            + [90.5, 94.5, 94.0, 92.8, 91.8],
            "Low": ([129.2 - (idx * 0.7) for idx in range(65)])
            + [89.5, 91.8, 91.9, 90.6, 90.2],
            "Close": ([130.0 - (idx * 0.7) for idx in range(65)])
            + [89.8, 94.0, 92.3, 90.9, 90.4],
            "Volume": ([1100] * 65) + [1200, 2500, 2000, 1700, 1500],
            "Dividends": [0.0] * 70,
            "EMA_50": ([125.0 - (idx * 0.6) for idx in range(65)])
            + [92.6, 92.5, 92.4, 92.3, 92.2],
            "EMA_200": [116.0] * 65 + [112.0, 111.8, 111.6, 111.4, 111.2],
            "Supertrend": ([132.0 - (idx * 0.65) for idx in range(65)])
            + [93.5, 93.3, 93.1, 92.9, 92.7],
            "Signal": [0] * 70,
        }
    )
    service.storage.save_etf_data(turnaround_frame, "TURN.DE")
    service.storage.save_etf_data(bulltrap_frame, "TRAP.DE")
    monkeypatch.setattr(
        service, "_load_universe_tickers", lambda _source: ["TURN.DE", "TRAP.DE"]
    )

    result = service.query_signal_scan(
        source="xetra",
        signal="downtrend_turnaround",
        signal_age_max=5,
        min_reliability=6.8,
        columns="ticker,signal_state,reclaim_hold_days,matched_rules",
    )

    assert result["dataset"] == "signal_scan"
    assert result["summary"]["matched_tickers"] == 1
    assert result["rows"][0]["ticker"] == "TURN.DE"
    assert result["rows"][0]["signal_state"] == "turnaround"
    assert "prior_downtrend_confirmed" in result["rows"][0]["matched_rules"]
    assert result["rows"][0]["reclaim_hold_days"] >= 3


def test_query_signal_scan_adds_historical_calibration_context(tmp_path, monkeypatch):
    service = _make_service(tmp_path)
    current_row = {
        "ticker": "AAA.DE",
        "reliability_score": 7.0,
        "signal_age_days": 1,
        "signal_state": "forming",
        "last_date": "2026-06-15T00:00:00",
        "close": 105.0,
        "ema_50": 101.0,
        "ema_200": 99.0,
        "supertrend": 100.0,
        "volume": 2500,
        "extension_pct": 3.96,
        "ema_50_slope_pct": 0.42,
        "matched_rules": [
            "close_above_ema50",
            "ema50_rising",
            "supertrend_bullish",
            "recent_ema50_reclaim",
            "volume_confirmed",
        ],
        "warning_flags": [],
        "data_source": "parquet",
    }
    bucket = service._signal_pattern_bucket("trend_forming", current_row)
    history_events = [
        {
            "ticker": f"HIST{idx}.DE",
            "signal": "trend_forming",
            "event_index": idx,
            "event_date": f"2026-05-{idx + 1:02d}T00:00:00",
            "pattern_bucket": bucket,
            "rule_reliability_score": 6.8,
            "signal_age_days": 1,
            "forward_return_5d": 2.5,
            "forward_return_10d": 4.8,
            "forward_return_20d": 7.5 if idx < 10 else -0.5,
            "adverse_excursion_10d": -2.2,
            "success_20d": idx < 10,
            "failure_10d": idx == 11,
        }
        for idx in range(12)
    ]

    def fake_analyze(
        ticker: str, signal: str, signal_age_max: int
    ) -> dict[str, object]:
        if ticker == "AAA.DE":
            return {
                "current": dict(current_row),
                "history_events": list(history_events),
            }
        return {"current": None, "history_events": []}

    monkeypatch.setattr(service, "_load_universe_tickers", lambda _source: ["AAA.DE"])
    monkeypatch.setattr(service, "_analyze_signal_ticker", fake_analyze)

    result = service.query_signal_scan(
        source="xetra",
        signal="trend_forming",
        signal_age_max=5,
        min_reliability=6.0,
        columns="ticker,reliability_score,calibrated_reliability_score,historical_success_rate_20d,historical_failure_rate_10d,historical_sample_size,historical_match_basis",
    )

    assert result["summary"]["matched_tickers"] == 1
    assert result["summary"]["historical_signal_events"] == 12
    row = result["rows"][0]
    assert row["ticker"] == "AAA.DE"
    assert row["historical_sample_size"] == 12
    assert row["historical_match_basis"] == "pattern_bucket"
    assert row["historical_success_rate_20d"] == 0.833
    assert row["historical_failure_rate_10d"] == 0.083
    assert row["calibrated_reliability_score"] > row["reliability_score"]


def test_load_universe_tickers_filters_low_vitality_nasdaq_names(tmp_path, monkeypatch):
    service = _make_service(tmp_path)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=60, freq="B")
    lively = pd.DataFrame(
        {
            "Date": dates,
            "Open": [24.8] * len(dates),
            "High": [25.4] * len(dates),
            "Low": [24.4] * len(dates),
            "Close": [25.0] * len(dates),
            "Volume": [500_000] * len(dates),
        }
    )
    weak = pd.DataFrame(
        {
            "Date": dates,
            "Open": [1.2] * len(dates),
            "High": [1.3] * len(dates),
            "Low": [1.1] * len(dates),
            "Close": [1.2] * len(dates),
            "Volume": [15_000] * len(dates),
        }
    )
    service.db.insert_dataframe(lively, "GOOD")
    service.db.insert_dataframe(weak, "THIN")

    metadata_path = tmp_path / "nasdaq.json"
    metadata_path.write_text(
        json.dumps(
            {
                "GOOD": {"name": "Good Nasdaq"},
                "THIN": {"name": "Thin Nasdaq"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        service,
        "_market_source_config",
        lambda _source: (metadata_path, "active"),
    )

    tickers = service._load_universe_tickers("nasdaq")

    assert tickers == ["GOOD"]
