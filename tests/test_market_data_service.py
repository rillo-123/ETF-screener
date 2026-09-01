import json
import threading
from datetime import date, timedelta
from concurrent.futures import Future

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.delisting_tracker import DelistingTracker
from ETF_screener.indicators import add_indicators
from ETF_screener.market_data_service import (
    MarketDataRefresher,
    filter_low_vitality_nasdaq_tickers,
)
from ETF_screener.storage import ParquetStorage


def test_market_data_refresher_status_marks_stale_data(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8"
    )

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


def test_market_data_refresh_honors_a_preexisting_cancellation(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8"
    )
    cancel_event = threading.Event()
    cancel_event.set()
    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    result = refresher.refresh_market_data(
        force=True,
        rebuild_shortlist=False,
        cancel_event=cancel_event,
    )

    assert result["cancelled"] is True
    assert result["refreshed"] == 0


def test_missing_only_refresh_ignores_existing_stale_tickers(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(
        json.dumps(
            {
                "STALE.DE": {"name": "Already cached"},
                "MISSING.DE": {"name": "Needs discovery"},
            }
        ),
        encoding="utf-8",
    )
    db = ETFDatabase(db_path=str(db_path))
    db.insert_dataframe(
        pd.DataFrame(
            {
                "Date": pd.to_datetime([date.today() - timedelta(days=30)]),
                "Open": [100.0],
                "High": [101.0],
                "Low": [99.0],
                "Close": [100.5],
                "Volume": [100_000],
            }
        ),
        "STALE.DE",
    )
    calls = []

    class RecordingFetcher:
        name = "Recording"

        def fetch_historical_data(self, symbol, **_kwargs):
            calls.append(symbol)
            return pd.DataFrame(
                {
                    "Date": pd.to_datetime([date.today()]),
                    "Open": [50.0],
                    "High": [51.0],
                    "Low": [49.0],
                    "Close": [50.5],
                    "Volume": [200_000],
                }
            )

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        fetcher=RecordingFetcher(),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    result = refresher.refresh_market_data(
        stale_after_days=0,
        max_workers=1,
        rebuild_shortlist=False,
        missing_only=True,
    )

    assert calls == ["MISSING.DE"]
    assert result["requested"] == 1
    assert result["refreshed"] == 1


def test_delisting_tracker_promotes_missing_tickers_after_14_days(tmp_path):
    blacklist_path = tmp_path / "blacklist.json"
    missing_path = tmp_path / "delisting_state.json"
    blacklist_path.write_text(json.dumps({}), encoding="utf-8")
    missing_path.write_text(json.dumps({}), encoding="utf-8")

    tracker = DelistingTracker(
        blacklist_file=str(blacklist_path),
        missing_file=str(missing_path),
    )

    tracker.mark_missing(
        "AAA.DE",
        reason="No data found during refresh",
        observed_on=date.today() - timedelta(days=15),
    )
    promoted = tracker.promote_aged_missing(
        threshold_days=14,
        today=date.today(),
    )

    blacklist = tracker.load_blacklist()
    missing = tracker.load_missing_state()

    assert promoted == ["AAA.DE"]
    assert "AAA.DE" in blacklist
    assert blacklist["AAA.DE"]["status"] == "invalid"
    assert blacklist["AAA.DE"]["reason"] == "No data found during refresh"
    assert missing == {}


def test_delisting_tracker_repairs_legacy_eager_blacklist_entries(tmp_path):
    blacklist_path = tmp_path / "blacklist.json"
    missing_path = tmp_path / "delisting_state.json"
    blacklist_path.write_text(
        json.dumps(
            {
                "DEPTH.DE": {"status": "invalid", "reason": "Max depth reached"},
                "GAP.DE": {
                    "status": "invalid",
                    "reason": "No data found during refresh",
                    "first_missing": "2026-08-20",
                    "missing_days": 0,
                    "promoted_on": "2026-08-20",
                },
                "DELISTED.DE": {
                    "status": "invalid",
                    "reason": "Stale data (likely delisted)",
                    "first_missing": "2026-07-01",
                    "missing_days": 20,
                    "promoted_on": "2026-07-21",
                },
            }
        ),
        encoding="utf-8",
    )
    tracker = DelistingTracker(
        blacklist_file=blacklist_path,
        missing_file=missing_path,
    )

    repaired = tracker.repair_legacy_blacklist()

    assert repaired == {"removed_max_depth": 1, "restored_missing": 1}
    assert set(tracker.load_blacklist()) == {"DELISTED.DE"}
    missing = tracker.load_missing_state()
    assert missing["GAP.DE"]["status"] == "missing"
    assert missing["GAP.DE"]["first_missing"] == "2026-08-20"


def test_market_data_refresher_refreshes_and_rebuilds_shortlist(tmp_path, monkeypatch):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8"
    )

    class FakeFetcher:
        def fetch_historical_data(
            self, symbol, days=365, start_date=None, end_date=None
        ):
            del end_date
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
            del metadata_path
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
    latest_business_day = pd.bdate_range(end=pd.Timestamp(date.today()), periods=1)[
        0
    ].date()

    assert result["refreshed"] == 1
    assert result["failed"] == 0
    assert result["latest_market_date"] == latest_business_day.isoformat()
    assert built["called"] is True
    assert db.get_latest_market_date() == latest_business_day.isoformat()
    stored = db.get_etf_data("AAA.DE")
    assert "dividends" in stored.columns
    assert stored["dividends"].sum() == 0.15


def test_market_data_refresher_respects_cautious_worker_limit_for_sweden(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "sweden.json"
    etfs_path.write_text(
        json.dumps(
            {
                "AAA.ST": {"name": "Alpha Sweden ETF"},
                "BBB.ST": {"name": "Beta Sweden ETF"},
            }
        ),
        encoding="utf-8",
    )

    class FakeFetcher:
        def fetch_historical_data(
            self, symbol, days=365, start_date=None, end_date=None
        ):
            del end_date
            dates = pd.date_range(end=pd.Timestamp(date.today()), periods=5, freq="B")
            return pd.DataFrame(
                {
                    "Date": dates,
                    "Open": [100, 101, 102, 103, 104],
                    "High": [101, 102, 103, 104, 105],
                    "Low": [99, 100, 101, 102, 103],
                    "Close": [100, 101, 102, 103, 104],
                    "Dividends": [0, 0, 0, 0, 0],
                    "Volume": [100000, 100000, 100000, 100000, 100000],
                }
            )

    captured = {"max_workers": None}

    class FakeExecutor:
        def __init__(self, max_workers=None):
            captured["max_workers"] = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, _tb):
            del exc_type
            del exc
            return False

        def submit(self, fn, *args, **kwargs):
            future = Future()
            future.set_result(fn(*args, **kwargs))
            return future

    monkeypatch.setattr(
        "ETF_screener.market_data_service.ThreadPoolExecutor", FakeExecutor
    )
    monkeypatch.setattr(
        "ETF_screener.market_data_service.as_completed",
        lambda futures: list(futures),
    )

    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        fetcher=FakeFetcher(),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    result = refresher.refresh_market_data(
        force=True,
        max_workers=1,
        rebuild_shortlist=False,
    )

    assert captured["max_workers"] == 1
    assert result["refreshed"] == 2
    assert result["failed"] == 0


def test_market_data_refresher_prioritizes_newest_cached_tickers(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "xetra.json"
    blacklist_path = tmp_path / "blacklist.json"
    blacklist_path.write_text(json.dumps({}), encoding="utf-8")
    etfs_path.write_text(
        json.dumps(
            {
                "OLDER.DE": {"status": "active"},
                "NEWER.DE": {"status": "active"},
                "MISSING.DE": {"status": "active"},
            }
        ),
        encoding="utf-8",
    )
    db = ETFDatabase(db_path=str(db_path))
    expected_day = MarketDataRefresher._expected_market_day()
    for ticker, age in (("OLDER.DE", 8), ("NEWER.DE", 2)):
        candle_day = expected_day - timedelta(days=age)
        db.insert_dataframe(
            pd.DataFrame(
                {
                    "Date": pd.to_datetime([candle_day]),
                    "Open": [100.0],
                    "High": [101.0],
                    "Low": [99.0],
                    "Close": [100.5],
                    "Volume": [100_000],
                }
            ),
            ticker,
        )

    submitted = []

    class RecordingExecutor:
        def __init__(self, max_workers=None):
            del max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        def submit(self, fn, ticker, *args):
            submitted.append(ticker)
            future = Future()
            future.set_exception(ValueError("No rows returned"))
            return future

    monkeypatch.setattr(
        "ETF_screener.market_data_service.ThreadPoolExecutor", RecordingExecutor
    )
    monkeypatch.setattr(
        "ETF_screener.market_data_service.as_completed", lambda futures: list(futures)
    )
    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        blacklist_file=str(blacklist_path),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    refresher.refresh_market_data(
        stale_after_days=0,
        max_workers=1,
        rebuild_shortlist=False,
    )

    assert submitted == ["NEWER.DE", "OLDER.DE", "MISSING.DE"]


def test_market_data_refresher_zero_day_threshold_tops_up_yesterday(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8"
    )

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
        def fetch_historical_data(
            self, symbol, days=365, start_date=None, end_date=None
        ):
            del end_date
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

    expected_market_day = MarketDataRefresher._expected_market_day()
    if expected_market_day == date.today():
        assert calls == ["AAA.DE"]
        assert result["requested"] == 1
        assert result["refreshed"] == 1
        assert result["latest_market_date"] == date.today().isoformat()
    else:
        assert calls == []
        assert result["requested"] == 0
        assert result["refreshed"] == 0
        assert result["latest_market_date"] in {
            expected_market_day.isoformat(),
            date.today().isoformat(),
            (date.today() - timedelta(days=1)).isoformat(),
        }


def test_market_data_refresher_fetches_only_missing_tail_for_stale_ticker(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8"
    )

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
        def fetch_historical_data(
            self, symbol, days=365, start_date=None, end_date=None
        ):
            del end_date
            calls.append(
                {
                    "symbol": symbol,
                    "days": days,
                    "start_date": (
                        pd.to_datetime(start_date).date() if start_date else None
                    ),
                }
            )
            fresh_dates = pd.date_range(
                start=pd.Timestamp(start_date), end=pd.Timestamp(date.today()), freq="B"
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

    refreshed_df = refresher.refresh_ticker_data("AAA.DE", depth=400)
    latest_business_day = pd.bdate_range(end=pd.Timestamp(date.today()), periods=1)[
        0
    ].date()

    assert calls, "Expected an incremental fetch call"
    latest_existing_day = existing_df["Date"].max().date()
    assert calls[0]["start_date"] == latest_existing_day + timedelta(days=1)
    assert refreshed_df["Date"].max().date() == latest_business_day
    assert len(refreshed_df) > len(existing_df)


def test_market_data_refresher_adapts_to_five_missing_sessions():
    expected_day = MarketDataRefresher._expected_market_day()
    missing_dates = pd.bdate_range(end=pd.Timestamp(expected_day), periods=5)
    latest_existing = pd.bdate_range(
        end=missing_dates[0] - pd.Timedelta(days=1), periods=1
    )[0]
    existing_dates = pd.bdate_range(end=latest_existing, periods=20)
    existing = pd.DataFrame(
        {
            "Date": existing_dates,
            "Open": [100.0] * len(existing_dates),
            "High": [101.0] * len(existing_dates),
            "Low": [99.0] * len(existing_dates),
            "Close": [100.5] * len(existing_dates),
            "Volume": [100_000] * len(existing_dates),
        }
    )
    calls = []

    class FakeFetcher:
        def fetch_historical_data(
            self, symbol, days=365, start_date=None, end_date=None
        ):
            calls.append((symbol, days, pd.Timestamp(start_date).date(), end_date))
            return pd.DataFrame(
                {
                    "Date": missing_dates,
                    "Open": [101.0] * 5,
                    "High": [102.0] * 5,
                    "Low": [100.0] * 5,
                    "Close": [101.5] * 5,
                    "Volume": [110_000] * 5,
                }
            )

    refresher = object.__new__(MarketDataRefresher)
    refresher.fetcher = FakeFetcher()
    refresher._load_existing_price_frame = lambda _ticker: existing.copy()

    _ticker, refreshed = refresher._build_refresh_frame(
        "AAA", depth=400, warmup_days=90
    )

    assert calls[0][2] == latest_existing.date() + timedelta(days=1)
    assert refreshed["Date"].max().date() == expected_day
    assert len(refreshed) == len(existing) + 5


def test_market_data_refresher_preserves_timezone_aware_fresh_rows(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "etfs.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF"}}), encoding="utf-8"
    )

    existing_dates = pd.date_range(
        end=pd.Timestamp(date.today() - timedelta(days=2)), periods=5, freq="B"
    )
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
        def fetch_historical_data(
            self, symbol, days=365, start_date=None, end_date=None
        ):
            del end_date
            fresh_dates = pd.date_range(
                start=pd.Timestamp(
                    date.today() - timedelta(days=2), tz="Europe/Berlin"
                ),
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
    latest_business_day = pd.bdate_range(end=pd.Timestamp(date.today()), periods=1)[
        0
    ].date()

    assert refreshed_df["Date"].max().date() == latest_business_day
    assert db.get_latest_date("AAA.DE") == latest_business_day.isoformat()


def test_filter_low_vitality_nasdaq_tickers_keeps_only_actionable_symbols(tmp_path):
    db_path = tmp_path / "etfs.db"
    db = ETFDatabase(db_path=str(db_path))
    dates = pd.date_range(end=pd.Timestamp(date.today()), periods=60, freq="B")

    lively = pd.DataFrame(
        {
            "Date": dates,
            "Open": [14.8] * len(dates),
            "High": [15.4] * len(dates),
            "Low": [14.5] * len(dates),
            "Close": [15.0] * len(dates),
            "Volume": [400_000] * len(dates),
        }
    )
    weak = pd.DataFrame(
        {
            "Date": dates,
            "Open": [1.0] * len(dates),
            "High": [1.1] * len(dates),
            "Low": [0.9] * len(dates),
            "Close": [1.0] * len(dates),
            "Volume": [20_000] * len(dates),
        }
    )
    db.insert_dataframe(lively, "LIVN")
    db.insert_dataframe(weak, "WEAK")

    filtered = filter_low_vitality_nasdaq_tickers(
        db_path=str(db_path),
        latest_market_date=db.get_latest_market_date(),
        tickers=["LIVN", "WEAK", "AAA.DE"],
    )

    assert filtered == ["LIVN", "AAA.DE"]


def test_market_data_refresher_quarantines_empty_responses_before_blacklisting(
    tmp_path,
):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "xetra.json"
    blacklist_path = tmp_path / "blacklist.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF", "status": "active"}}),
        encoding="utf-8",
    )
    blacklist_path.write_text(json.dumps({}), encoding="utf-8")

    class EmptyFetcher:
        calls = 0

        def fetch_historical_data(
            self, symbol, days=365, start_date=None, end_date=None
        ):
            del symbol, days, start_date, end_date
            self.calls += 1
            return pd.DataFrame()

    fetcher = EmptyFetcher()
    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        blacklist_file=str(blacklist_path),
        fetcher=fetcher,
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    result = refresher.refresh_market_data(
        force=True,
        max_workers=1,
        rebuild_shortlist=False,
    )

    assert result["failed"] == 1
    assert refresher.delisting_tracker.load_blacklist() == {}
    missing = refresher.delisting_tracker.load_missing_state()
    assert missing["AAA.DE"]["missing_days"] == 0

    retry = refresher.refresh_market_data(
        force=False,
        max_workers=1,
        rebuild_shortlist=False,
    )

    assert retry["requested"] == 0
    assert retry["deferred_missing"] == 1
    assert fetcher.calls == 1


def test_market_data_refresh_prunes_rolling_window_when_already_fresh(tmp_path):
    db_path = tmp_path / "etfs.db"
    etfs_path = tmp_path / "xetra.json"
    etfs_path.write_text(
        json.dumps({"AAA.DE": {"name": "Alpha ETF", "status": "active"}}),
        encoding="utf-8",
    )
    expected_day = MarketDataRefresher._expected_market_day()
    old_day = expected_day - timedelta(days=60)
    db = ETFDatabase(db_path=str(db_path))
    db.insert_dataframe(
        pd.DataFrame(
            {
                "Date": pd.to_datetime([old_day, expected_day]),
                "Open": [90.0, 100.0],
                "High": [91.0, 101.0],
                "Low": [89.0, 99.0],
                "Close": [90.5, 100.5],
                "Volume": [100_000, 100_000],
            }
        ),
        "AAA.DE",
    )
    refresher = MarketDataRefresher(
        db_path=str(db_path),
        etfs_file=str(etfs_path),
        storage=ParquetStorage(data_dir=str(tmp_path / "parquet")),
    )

    result = refresher.refresh_market_data(
        stale_after_days=0,
        rebuild_shortlist=False,
        retention_days=30,
    )

    assert result["requested"] == 0
    assert result["pruned"] == 1
    retained = db.get_etf_data("AAA.DE")
    assert retained["Date"].dt.date.tolist() == [expected_day]


def test_database_rejects_nonpositive_retention_window(tmp_path):
    db = ETFDatabase(db_path=str(tmp_path / "etfs.db"))

    try:
        db.prune_old_data(days_to_keep=0)
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("Expected an invalid retention window to fail")


def test_market_data_normalization_discards_incomplete_candles():
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-08-27", "2026-08-28"]),
            "Open": [100.0, None],
            "High": [101.0, None],
            "Low": [99.0, None],
            "Close": [100.5, None],
            "Volume": [100_000, 120_000],
        }
    )

    normalized = MarketDataRefresher._normalize_price_frame(frame)

    assert normalized["Date"].dt.date.tolist() == [date(2026, 8, 27)]


def test_database_prunes_incomplete_candles(tmp_path):
    db = ETFDatabase(db_path=str(tmp_path / "etfs.db"))
    conn = db._get_connection()
    conn.execute(
        """
        INSERT INTO etf_data (ticker, date, open, high, low, close, volume)
        VALUES ('AAA.DE', '2026-08-27', 100, 101, 99, 100.5, 100000),
               ('AAA.DE', '2026-08-28', NULL, NULL, NULL, NULL, 120000)
        """
    )
    conn.commit()

    deleted = db.prune_incomplete_data()

    assert deleted == 1
    assert db.get_latest_date("AAA.DE") == "2026-08-27"
