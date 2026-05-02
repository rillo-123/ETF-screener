import json
from datetime import date, timedelta

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import add_indicators
from ETF_screener.market_data_service import MarketDataRefresher
from ETF_screener.storage import ParquetStorage


def test_market_data_refresher_status_marks_stale_data(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8")

    db = ETFDatabase(db_path=str(db_path))
    stale_day = (date.today() - timedelta(days=8)).isoformat()
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime([stale_day]),
            "Open": [100.0],
            "High": [101.0],
            "Low": [99.0],
            "Close": [100.5],
            "Volume": [100000],
            "EMA_50": [99.0],
            "Supertrend": [98.5],
            "ST_Upper": [None],
            "ST_Lower": [98.5],
            "Signal": [0],
        }
    )
    db.insert_dataframe(df, "AAA.DE")

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )
    status = refresher.get_status(stale_after_days=3)

    assert status["latest_market_date"] == stale_day
    assert status["days_stale"] >= 8
    assert status["is_stale"] is True
    assert status["tracked_tickers"] == 1
    assert status["fresh_tickers"] == 0


def test_market_data_refresher_excludes_blacklisted_tickers(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    blacklist_path = tmp_path / "blacklist.json"
    etfs_path.write_text(
        json.dumps(
            {
                "AAA.DE": {"name": "Alpha ETF", "status": "active"},
                "BBB.DE": {"name": "Broken ETF", "status": "active"},
                "CCC.DE": {"name": "Inactive ETF", "status": "inactive"},
            }
        ),
        encoding="utf-8",
    )
    blacklist_path.write_text(
        json.dumps({"BBB.DE": {"status": "invalid"}}),
        encoding="utf-8",
    )

    today = date.today().isoformat()
    db = ETFDatabase(db_path=str(db_path))
    db.insert_dataframe(
        pd.DataFrame(
            {
                "Date": pd.to_datetime([today]),
                "Open": [100.0],
                "High": [101.0],
                "Low": [99.0],
                "Close": [100.5],
                "Volume": [100000],
            }
        ),
        "AAA.DE",
    )

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        blacklist_file=str(blacklist_path),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )
    status = refresher.get_status(stale_after_days=0)

    assert status["tracked_tickers"] == 1
    assert status["fresh_tickers"] == 1
    assert status["blacklisted_tickers"] == 1
    assert status["missing_examples"] == []
    assert status["is_stale"] is False


def test_market_data_refresher_refreshes_and_rebuilds_shortlist(tmp_path, monkeypatch):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8")

    class FakeFetcher:
        def fetch_historical_data(self, symbol, days=365, start_date=None, end_date=None):
            dates = pd.date_range(end=pd.Timestamp(date.today()), periods=5, freq="B")
            return pd.DataFrame(
                {
                    "Date": dates,
                    "Open": [100, 101, 102, 103, 104],
                    "High": [101, 102, 103, 104, 105],
                    "Low": [99, 100, 101, 102, 103],
                    "Close": [100, 101, 102, 103, 104],
                    "Dividends": [0, 0, 0.15, 0, 0],
                    "Volume": [100000, 100000, 100000, 100000, 100000],
                }
            )

    built = {"called": False}

    class FakeShortlistEngine:
        def __init__(self, db_path=None, metadata_path=None, storage=None):
            self.db_path = db_path

        def build_shortlist(self, max_workers=None):
            built["called"] = True
            return pd.DataFrame()

    monkeypatch.setattr(
        "ETF_screener.market_data_service.ETFShortlistEngine",
        FakeShortlistEngine,
    )

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        fetcher=FakeFetcher(),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    result = refresher.refresh_market_data(force=True, max_workers=1)
    db = ETFDatabase(db_path=str(db_path))
    latest_business_day = pd.bdate_range(end=pd.Timestamp(date.today()), periods=1)[0].date()

    assert result["refreshed"] == 1
    assert result["failed"] == 0
    assert result["latest_market_date"] == latest_business_day.isoformat()
    assert built["called"] is True
    assert db.get_latest_market_date() == latest_business_day.isoformat()
    stored = db.get_etf_data("AAA.DE")
    assert "dividends" in stored.columns
    assert stored["dividends"].sum() == 0.15


def test_market_data_refresher_zero_day_threshold_tops_up_yesterday(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8")

    yesterday = date.today() - timedelta(days=1)
    db = ETFDatabase(db_path=str(db_path))
    db.insert_dataframe(
        pd.DataFrame(
            {
                "Date": pd.to_datetime([yesterday]),
                "Open": [100.0],
                "High": [101.0],
                "Low": [99.0],
                "Close": [100.5],
                "Volume": [100000],
            }
        ),
        "AAA.DE",
    )

    calls = []

    class FakeFetcher:
        def fetch_historical_data(self, symbol, days=365, start_date=None, end_date=None):
            calls.append(symbol)
            return pd.DataFrame(
                {
                    "Date": pd.to_datetime([date.today()]),
                    "Open": [101.0],
                    "High": [102.0],
                    "Low": [100.0],
                    "Close": [101.5],
                    "Volume": [100000],
                }
            )

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        fetcher=FakeFetcher(),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    result = refresher.refresh_market_data(
        force=False,
        stale_after_days=0,
        max_workers=1,
        rebuild_shortlist=False,
    )

    assert calls == ["AAA.DE"]
    assert result["requested"] == 1
    assert result["refreshed"] == 1
    assert result["latest_market_date"] == date.today().isoformat()


def test_market_data_refresher_uses_delta_window_for_stale_ticker(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8")

    stale_end = date.today() - timedelta(days=8)
    existing_dates = pd.date_range(end=pd.Timestamp(stale_end), periods=120, freq="B")
    existing_df = add_indicators(
        pd.DataFrame(
            {
                "Date": existing_dates,
                "Open": range(100, 220),
                "High": range(101, 221),
                "Low": range(99, 219),
                "Close": range(100, 220),
                "Volume": [100000] * 120,
            }
        )
    )

    db = ETFDatabase(db_path=str(db_path))
    storage = ParquetStorage(data_dir=str(tmp_path / "parquet"))
    db.insert_dataframe(existing_df, "AAA.DE")
    storage.save_etf_data(existing_df, "AAA.DE")

    calls = []

    class FakeFetcher:
        def fetch_historical_data(self, symbol, days=365, start_date=None, end_date=None):
            calls.append(
                {
                    "symbol": symbol,
                    "days": days,
                    "start_date": pd.to_datetime(start_date).date() if start_date else None,
                }
            )
            fresh_dates = pd.date_range(start=pd.Timestamp(start_date), end=pd.Timestamp(date.today()), freq="B")
            return pd.DataFrame(
                {
                    "Date": fresh_dates,
                    "Open": [200.0 + i for i in range(len(fresh_dates))],
                    "High": [201.0 + i for i in range(len(fresh_dates))],
                    "Low": [199.0 + i for i in range(len(fresh_dates))],
                    "Close": [200.5 + i for i in range(len(fresh_dates))],
                    "Volume": [150000] * len(fresh_dates),
                }
            )

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        fetcher=FakeFetcher(),
        storage=storage,
    )

    refreshed_df = refresher.refresh_ticker_data("AAA.DE", depth=400)
    latest_business_day = pd.bdate_range(end=pd.Timestamp(date.today()), periods=1)[0].date()

    assert calls, "Expected an incremental fetch call"
    latest_existing_day = existing_df["Date"].max().date()
    assert calls[0]["start_date"] == latest_existing_day - timedelta(days=refresher.INDICATOR_WARMUP_DAYS)
    assert refreshed_df["Date"].max().date() == latest_business_day
    assert len(refreshed_df) > len(existing_df)


def test_market_data_refresher_preserves_timezone_aware_fresh_rows(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8")

    existing_dates = pd.date_range(end=pd.Timestamp(date.today() - timedelta(days=2)), periods=5, freq="B")
    existing_df = pd.DataFrame(
        {
            "Date": existing_dates,
            "Open": [100, 101, 102, 103, 104],
            "High": [101, 102, 103, 104, 105],
            "Low": [99, 100, 101, 102, 103],
            "Close": [100, 101, 102, 103, 104],
            "Volume": [100000] * 5,
        }
    )

    db = ETFDatabase(db_path=str(db_path))
    storage = ParquetStorage(data_dir=str(tmp_path / "parquet"))
    db.insert_dataframe(existing_df, "AAA.DE")
    storage.save_etf_data(existing_df, "AAA.DE")

    class FakeFetcher:
        def fetch_historical_data(self, symbol, days=365, start_date=None, end_date=None):
            fresh_dates = pd.date_range(
                start=pd.Timestamp(date.today() - timedelta(days=2), tz="Europe/Berlin"),
                end=pd.Timestamp(date.today(), tz="Europe/Berlin"),
                freq="B",
            )
            return pd.DataFrame(
                {
                    "Date": fresh_dates,
                    "Open": [200.0 + i for i in range(len(fresh_dates))],
                    "High": [201.0 + i for i in range(len(fresh_dates))],
                    "Low": [199.0 + i for i in range(len(fresh_dates))],
                    "Close": [200.5 + i for i in range(len(fresh_dates))],
                    "Volume": [150000] * len(fresh_dates),
                }
            )

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        fetcher=FakeFetcher(),
        storage=storage,
    )

    refreshed_df = refresher.refresh_ticker_data("AAA.DE", depth=30, warmup_days=10)
    latest_business_day = pd.bdate_range(end=pd.Timestamp(date.today()), periods=1)[0].date()

    assert refreshed_df["Date"].max().date() == latest_business_day
    assert db.get_latest_date("AAA.DE") == latest_business_day.isoformat()
