import json
import sqlite3
from io import StringIO
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from ETF_screener.dashboard import app_fast
from ETF_screener.dashboard.app_fast import app
from ETF_screener.indicators import add_indicators

client = TestClient(app)


def _make_fake_ohlcv(ticker: str, n: int = 150) -> pd.DataFrame:
    """Return a deterministic synthetic OHLCV DataFrame for offline testing."""
    rng = np.random.default_rng(seed=42)
    dates = pd.date_range(end="2024-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    close = np.clip(close, 1, None)
    high = close * (1 + rng.uniform(0, 0.02, n))
    low = close * (1 - rng.uniform(0, 0.02, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    volume = rng.integers(100_000, 1_000_000, n)
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume.astype(float),
        }
    )


def test_tab_bar_visible():
    """Ensure the dashboard exposes the primary workflow tabs."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    dashboard_js = client.get("/static/js/dashboard.js")
    log_relay_js = client.get("/static/js/browser-log-relay.js")
    assert dashboard_js.status_code == 200
    assert log_relay_js.status_code == 200
    dashboard_source = html + dashboard_js.text + log_relay_js.text
    assert 'id="dashboard-tabs"' in html
    assert 'id="scan-source-toggle"' in html
    assert 'id="scan-source-xetra"' in html
    assert 'id="scan-source-sweden"' in html
    assert 'id="scan-source-list"' in html
    assert 'id="scan-source-all-lists"' in html
    assert 'id="swarm-scan-source-toggle"' in html
    assert 'id="swarm-scan-source-xetra"' in html
    assert 'id="swarm-scan-source-sweden"' in html
    assert 'id="swarm-scan-source-list"' in html
    assert 'id="swarm-scan-source-all-lists"' in html
    assert 'id="list-edit-btn"' in html
    assert ">Screener<" in html
    assert ">Shortlist<" in html
    assert ">Swarm<" in html
    assert ">Backtester<" in html
    assert ">Churner<" not in html
    assert ">Discovery<" not in html
    assert 'id="backtest-chart"' in html
    assert 'id="backtest-table-body"' in html
    assert "Signal Window" in html
    assert 'id="shortlist-grid"' in html
    assert 'id="swarm-canvas"' in html
    assert 'id="swarm-step-1-btn"' in html
    assert 'id="swarm-step-10-btn"' in html
    assert 'id="swarm-timeline-slider"' in html
    assert 'id="swarm-jump-cost-slider"' in html
    assert "Global asset scan" in html
    assert 'id="swarm-agents-per-node-slider"' in html
    assert 'id="swarm-zoom-slider"' in html
    assert 'id="swarm-world-visibility"' in html
    assert 'id="swarm-stop-btn"' in html
    assert 'id="swarm-agent-selected"' in html
    assert 'id="swarm-top-agents"' in html
    assert 'id="shortlist-filter-buy"' in html
    assert 'id="swarm-filter-buy"' in html
    assert 'id="shortlist-filter-watch"' in html
    assert 'id="shortlist-filter-skip"' in html
    assert 'id="market-refresh-btn"' in html
    assert 'id="export-matches-btn"' in html
    assert "/api/market-status?stale_after_days=0" in dashboard_source
    assert "force=true&stale_after_days=0" in dashboard_source
    assert "/api/swarm-history" in dashboard_source
    assert 'id="swarm-dna-save-status"' in html
    assert "/static/js/dashboard.js" in html
    assert "/static/js/browser-log-relay.js" in html
    assert "supertrend_continuation" in html
    assert "SWARM_DNA_SCHEMA_VERSION" in dashboard_source
    assert "SWARM_DNA_CONFIG_PATH" in dashboard_source
    assert "config/swarm_agent_dna.json" in dashboard_source
    assert "behaviorModules" in dashboard_source
    assert "ema_cross_up" in dashboard_source
    assert "emaFastPeriod" in dashboard_source
    assert "emaSlowPeriod" in dashboard_source
    assert "fast_period" in dashboard_source
    assert "slow_period" in dashboard_source
    assert "autoSaveSwarmTopAgentDna" in dashboard_source
    assert "/api/swarm-dna/save" in dashboard_source
    assert "interpretSwarmDnaRules" in dashboard_source
    assert "Investment rule interpretation" in dashboard_source
    assert "SWARM_ANNUAL_INFLATION_RATE" in dashboard_source
    assert "Export DNA" not in dashboard_source
    assert "spawnLimit" in dashboard_source
    assert "jumpCostSensitivity" in dashboard_source
    assert "swarmJumpCostMultiplier" in dashboard_source
    assert "getSwarmGlobalCandidateNodes" in dashboard_source
    assert "stableSwarmSphereVector" in dashboard_source
    assert "SWARM_SPHERE_REPULSION_SAMPLE" in dashboard_source
    assert "setSwarmZoom" in dashboard_source
    assert "DUMMY-R" not in dashboard_source
    assert "asset sphere" in dashboard_source
    assert "updateFixedSwarmNodeWorth" in dashboard_source
    assert "fixed ticker map" not in dashboard_source
    assert "childHeadStart" in dashboard_source
    assert "getSwarmAgentRadius" in dashboard_source
    assert "getSwarmTickerDrawRadius" in dashboard_source
    assert "SWARM_MAX_AGENTS = 5000" in dashboard_source
    assert "swarmCompletedAgents" in dashboard_source
    assert "stepSwarmDays" in dashboard_source
    assert "three.min.js" in dashboard_source
    assert "asset sphere" in dashboard_source
    assert "getSwarmScopeQueryParams" in dashboard_source
    assert "setSwarmDebugAssetCount" in dashboard_source
    assert "debug_assets" in dashboard_source
    assert "exportTopMatches" in dashboard_source
    assert "getSwarmAgentHeading" in dashboard_source
    assert "startSwarmPlayback" in dashboard_source
    assert "ensureSwarmAnimationLoop" in dashboard_source
    assert "swarmLoadingPromise" in dashboard_source
    assert "Saved Strategy" in html
    assert "Editor Draft" in html
    assert 'id="list-modal"' in html
    assert 'id="list-modal-grid"' in html
    assert 'id="list-modal-search"' in html
    assert 'id="list-modal-list-select"' in html
    assert 'id="list-modal-name"' in html


def test_api_status():
    """Verify the root endpoint loads."""
    response = client.get("/")
    assert response.status_code == 200


def test_screen_endpoint():
    """Verify the screen endpoint returns data from the DB."""
    response = client.get("/api/screen")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "matches" in data
    assert isinstance(data["matches"], list)
    if len(data["matches"]) > 0:
        assert "ticker" in data["matches"][0]
        assert "close" in data["matches"][0]


def test_screen_endpoint_refreshes_on_gui_request(monkeypatch):
    captured = {"called": False}

    def fake_refresh(source=None, **kwargs):
        captured["called"] = True
        captured["source"] = source
        return {"refreshed": 1}

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._refresh_market_data_for_gui",
        fake_refresh,
    )

    response = client.get("/api/screen?refresh=true")
    assert response.status_code == 200
    assert captured["called"] is True
    assert captured["source"] is None


def test_cached_screen_universe_uses_db_backed_tickers_only(monkeypatch):
    app_fast._cached_screen_universe.cache_clear()

    class FakeDb:
        def _get_connection(self):
            return object()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, _tb):
            return False

    def fake_read_sql_query(query, conn):
        return pd.DataFrame({"ticker": ["AAA.DE", "BBB.DE", "CCC.ST"]})

    def fail_if_metadata_loaded():
        raise AssertionError("screen universe should not depend on metadata keys")

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.ETFDatabase", lambda db_path=None: FakeDb()
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.pd.read_sql_query", fake_read_sql_query
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._cached_blacklist_tickers", lambda: {"BBB.DE"}
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._cached_etf_metadata_map",
        fail_if_metadata_loaded,
    )

    result = app_fast._cached_screen_universe("fake-db", "2026-04-01")

    assert result == ("AAA.DE", "CCC.ST")


def test_screen_endpoint_honors_scan_scope_list(monkeypatch, tmp_path):
    captured = {}
    cache_dir = None

    class FakeDb:
        db_path = "fake-db"

        def get_latest_market_date(self):
            return "2026-04-01"

    class FakeBacktester:
        def __init__(self):
            self.db = FakeDb()
            self.db_path = "fake-db"
            self.scripted_strategy = lambda *args, **kwargs: None

        def run_parallel_backtest(self, tickers, *args, **kwargs):
            captured["backtest_tickers"] = list(tickers)
            return []

    def fake_get_db():
        return FakeDb()

    def fake_universe(db_path, latest_market_date):
        captured["universe_args"] = (db_path, latest_market_date)
        return ("AAA.DE", "BBB.ST", "CCC.DE")

    def fake_filter(tickers, exchange=None, ticker_list=None, scan_scope=None):
        captured["filter_args"] = {
            "tickers": list(tickers),
            "exchange": exchange,
            "ticker_list": ticker_list,
            "scan_scope": scan_scope,
        }
        return ["BBB.ST"] if scan_scope == "list" else list(tickers)

    def fake_cache_dir():
        nonlocal cache_dir
        if cache_dir is None:
            cache_dir = tmp_path / "screen_requests_scope"
            cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    monkeypatch.setattr("ETF_screener.dashboard.app_fast.get_db", fake_get_db)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._cached_screen_universe", fake_universe
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.filter_tickers_by_exchange_and_list",
        fake_filter,
    )
    monkeypatch.setattr("ETF_screener.dashboard.app_fast.Backtester", FakeBacktester)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._screen_cache_dir", fake_cache_dir
    )

    response = client.get(
        "/api/screen?scan_scope=list&ticker_list=BBB.ST&dsl_content=TRIGGER:%20close%20%3E%20ema_50"
    )
    assert response.status_code == 200
    assert captured["filter_args"]["scan_scope"] == "list"
    assert captured["filter_args"]["ticker_list"] == "BBB.ST"
    assert captured["backtest_tickers"] == ["BBB.ST"]


def test_screen_export_endpoint_writes_csv(monkeypatch, tmp_path):
    export_dir = tmp_path / "exports"

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.SCREEN_EXPORTS_DIR", export_dir
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._write_top_matches_csv",
        lambda *args, **kwargs: export_dir / "top_matches_demo.csv",
    )

    response = client.post(
        "/api/screen/export",
        json={
            "strategy_name": "demo",
            "scan_scope": "xetra",
            "matches": [
                {
                    "ticker": "AAA.DE",
                    "status": "Entry Signal",
                    "close": 12.34,
                    "volume": 123456,
                    "return_pct": 4.5,
                    "change_pct": 1.2,
                    "ema_50_slope": 0.33,
                    "days_since_entry": 0,
                    "score": 0.88,
                },
                {
                    "ticker": "BBB.DE",
                    "status": "Recent Entry (2d)",
                    "close": 23.45,
                    "volume": 234567,
                    "return_pct": 6.7,
                    "change_pct": -0.4,
                    "ema_50_slope": 0.21,
                    "days_since_entry": 2,
                    "score": 0.76,
                },
            ],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment;" in response.headers["content-disposition"]
    exported = pd.read_csv(StringIO(response.text))
    assert exported["ticker"].tolist() == ["AAA.DE", "BBB.DE"]
    assert exported["rank"].tolist() == [1, 2]


def test_screen_endpoint_reuses_cached_result(monkeypatch, tmp_path):
    calls = {"run_parallel_backtest": 0}

    class FakeDb:
        db_path = "fake-db"

        def get_latest_market_date(self):
            return "2026-04-01"

        def _get_connection(self):
            raise AssertionError("fallback DB connection should not be used here")

    class FakeBacktester:
        def __init__(self, *args, **kwargs):
            self.db_path = "fake-db"
            self._db = FakeDb()
            self.scripted_strategy = lambda *args, **kwargs: None

        @property
        def db(self):
            return self._db

        def run_parallel_backtest(self, tickers, *args, **kwargs):
            calls["run_parallel_backtest"] += 1
            df = pd.DataFrame(
                {
                    "close": [9.0, 10.0, 11.0, 12.0, 13.0],
                    "close_d1": [8.0, 9.0, 10.0, 11.0, 12.0],
                    "ema_20": [10.0] * 5,
                    "ema_20_d1": [10.0] * 5,
                    "signal": [0, 0, 1, 0, 0],
                    "exit_condition": [False] * 5,
                }
            )
            return [
                {
                    "ticker": tickers[0],
                    "df": df,
                    "total_return_pct": 2.5,
                    "win_rate_pct": 50.0,
                    "profit_factor": 1.1,
                    "sharpe_ratio": 0.7,
                    "max_drawdown_pct": 1.5,
                    "num_trades": 1,
                }
            ]

    def fake_get_db():
        return FakeDb()

    def fake_universe(db_path, latest_market_date):
        return ("AAA.DE",)

    def fake_filter(tickers, exchange=None, ticker_list=None, scan_scope=None):
        return list(tickers)

    def fake_cache_dir():
        cache_dir = tmp_path / "screen_requests"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    monkeypatch.setattr("ETF_screener.dashboard.app_fast.get_db", fake_get_db)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._cached_screen_universe", fake_universe
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.filter_tickers_by_exchange_and_list",
        fake_filter,
    )
    monkeypatch.setattr("ETF_screener.dashboard.app_fast.Backtester", FakeBacktester)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._screen_cache_dir", fake_cache_dir
    )

    params = "dsl_content=TRIGGER:%20close%20%3E%20ema_20"
    first = client.get(f"/api/screen?{params}")
    second = client.get(f"/api/screen?{params}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["run_parallel_backtest"] == 1
    assert first.json() == second.json()


def test_backtest_endpoint_honors_scan_scope_list(monkeypatch):
    captured = {}

    def fake_evaluate_strategies(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame()

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.evaluate_strategies", fake_evaluate_strategies
    )

    response = client.get(
        "/api/backtest?scan_scope=list&ticker_list=BBB.ST&dsl_content=TRIGGER:%20close%20%3E%20ema_50"
    )
    assert response.status_code == 200
    assert captured["scan_scope"] == "list"
    assert captured["ticker_list"] == "BBB.ST"


def test_custom_ticker_list_api_roundtrip(monkeypatch, tmp_path):
    config_path = tmp_path / "custom_ticker_list.json"
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.CUSTOM_TICKER_LIST_CONFIG_PATH",
        config_path,
    )

    response = client.get("/api/custom-ticker-list")
    assert response.status_code == 200
    data = response.json()
    assert data["tickers"] == []
    assert data["count"] == 0
    assert data["name"] == "My List"
    assert data["active_name"] == "My List"
    assert data["lists"] == [{"name": "My List", "tickers": [], "count": 0}]

    save_response = client.post(
        "/api/custom-ticker-list",
        json={"name": "Growth Basket", "tickers": ["msft", "aapl", "msft", "  nvda  "]},
    )
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["count"] == 3
    assert saved["name"] == "Growth Basket"
    assert saved["active_name"] == "Growth Basket"
    assert saved["tickers"] == ["MSFT", "AAPL", "NVDA"]
    assert saved["lists"] == [
        {"name": "Growth Basket", "tickers": ["MSFT", "AAPL", "NVDA"], "count": 3}
    ]
    assert config_path.exists()

    with open(config_path, "r", encoding="utf-8") as handle:
        persisted = json.load(handle)
    assert persisted["name"] == "Growth Basket"
    assert persisted["tickers"] == ["MSFT", "AAPL", "NVDA"]


def test_ticker_universe_api():
    response = client.get("/api/ticker-universe")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        first = data["items"][0]
        assert "ticker" in first
        assert "name" in first
        assert "label" in first
        assert "exchange" in first


def test_market_status_endpoint(monkeypatch):
    captured = {}

    class FakeRefresher:
        def __init__(
            self, db_path=None, etfs_file=None, collection_mode=None, **kwargs
        ):
            self.db_path = db_path
            captured["etfs_file"] = etfs_file
            captured["collection_mode"] = collection_mode

        def get_status(self, stale_after_days=3):
            captured["stale_after_days"] = stale_after_days
            return {
                "today": "2026-04-23",
                "latest_market_date": "2026-04-15",
                "latest_shortlist_date": "2026-04-15",
                "latest_shortlist_updated_at": "2026-04-23 19:27:36",
                "days_stale": 8,
                "is_stale": True,
                "tracked_tickers": 10,
                "missing_tickers": 2,
                "stale_tickers": 8,
                "missing_examples": ["AAA.DE"],
                "stale_examples": ["BBB.DE"],
            }

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.MarketDataRefresher",
        FakeRefresher,
    )

    response = client.get("/api/market-status?source=sweden")
    assert response.status_code == 200
    data = response.json()
    assert data["days_stale"] == 8
    assert data["is_stale"] is True
    assert data["latest_market_date"] == "2026-04-15"
    assert captured["stale_after_days"] == 0
    assert str(captured["etfs_file"]).endswith("sweden.json")
    assert captured["collection_mode"] == "active"


def test_market_refresh_endpoint(monkeypatch):
    captured = {}

    class FakeRefresher:
        def __init__(
            self, db_path=None, etfs_file=None, collection_mode=None, **kwargs
        ):
            self.db_path = db_path
            captured["etfs_file"] = etfs_file
            captured["collection_mode"] = collection_mode

        def refresh_market_data(
            self,
            depth=400,
            stale_after_days=3,
            force=False,
            max_workers=8,
            rebuild_shortlist=True,
            warmup_days=90,
        ):
            captured.update(
                {
                    "depth": depth,
                    "stale_after_days": stale_after_days,
                    "force": force,
                    "max_workers": max_workers,
                    "rebuild_shortlist": rebuild_shortlist,
                }
            )
            return {
                "today": "2026-04-23",
                "latest_market_date": "2026-04-23",
                "latest_shortlist_date": "2026-04-23",
                "latest_shortlist_updated_at": "2026-04-23 21:00:00",
                "days_stale": 0,
                "is_stale": False,
                "tracked_tickers": 10,
                "missing_tickers": 0,
                "stale_tickers": 0,
                "requested": 8,
                "refreshed": 8,
                "failed": 0,
                "shortlist_rebuilt": True,
                "errors": [],
            }

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.MarketDataRefresher",
        FakeRefresher,
    )

    response = client.post("/api/market-data/refresh?source=sweden")
    assert response.status_code == 200
    data = response.json()
    assert data["refreshed"] == 8
    assert data["shortlist_rebuilt"] is True
    assert data["latest_market_date"] == "2026-04-23"
    assert captured["force"] is True
    assert captured["stale_after_days"] == 0
    assert captured["rebuild_shortlist"] is True
    assert str(captured["etfs_file"]).endswith("sweden.json")
    assert captured["collection_mode"] == "active"


def test_swarm_world_endpoint(monkeypatch):
    fake_df = pd.DataFrame(
        [
            {
                "ticker": "EUNL.DE",
                "name": "iShares Core MSCI World UCITS ETF",
                "issuer": "iShares",
                "asset_class": "Equity",
                "region": "Global",
                "label": "Buy",
                "volume": 750000,
                "recent_entry_days": 2,
                "product_score": 84.0,
                "exposure_score": 80.0,
                "technical_score": 72.0,
                "final_score": 78.4,
                "energy": 82.5,
                "momentum_score": 77.1,
                "freshness_score": 85.0,
                "grid_row": 2,
                "grid_col": 4,
                "x": 1220.4,
                "y": 210.0,
                "z": 88.0,
                "radius": 9.5,
                "value": 239.84,
                "mass": 5.61,
                "sphere_radius": 244.0,
                "sphere_x": 88.0,
                "sphere_y": 130.0,
                "sphere_z": 194.0,
                "latitude": 0.42,
                "longitude": 1.12,
                "color": "#10b981",
                "world_version": "swarm_v6_sphere_tetra",
                "components_json": '{"style": "Core Broad Market"}',
                "as_of_date": "2026-04-23",
                "updated_at": "2026-04-23 22:10:00",
            },
            {
                "ticker": "XACT.ST",
                "name": "Swedish World ETF",
                "issuer": "Xact",
                "asset_class": "Equity",
                "region": "Sweden",
                "label": "Watch",
                "volume": 510000,
                "recent_entry_days": 4,
                "product_score": 71.0,
                "exposure_score": 69.0,
                "technical_score": 64.0,
                "final_score": 67.4,
                "energy": 77.1,
                "momentum_score": 68.2,
                "freshness_score": 82.0,
                "grid_row": 3,
                "grid_col": 1,
                "x": 980.0,
                "y": 360.0,
                "z": -14.0,
                "radius": 8.4,
                "value": 175.22,
                "mass": 5.02,
                "sphere_radius": 244.0,
                "sphere_x": -72.0,
                "sphere_y": 186.0,
                "sphere_z": -140.0,
                "latitude": 0.84,
                "longitude": -0.64,
                "color": "#38bdf8",
                "world_version": "swarm_v6_sphere_tetra",
                "components_json": '{"style": "Nordic Equity"}',
                "as_of_date": "2026-04-23",
                "updated_at": "2026-04-23 22:10:00",
            },
        ]
    )

    class FakeSwarmEngine:
        def __init__(self, db_path=None):
            self.db_path = db_path
            self.WORLD_WIDTH = 1600.0
            self.WORLD_HEIGHT = 920.0
            self.ARTIFACT_VERSION = "swarm_v6_sphere_tetra"

        def get_world(self, limit=None, label=None, refresh=False):
            return fake_df

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.SwarmWorldEngine",
        FakeSwarmEngine,
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._swarm_scope_tickers",
        lambda db, scan_scope=None, exchange=None, ticker_list=None: (
            ["EUNL.DE"]
            if (scan_scope or exchange or "xetra") in {"xetra", None, "exchange"}
            else ["XACT.ST"]
        ),
    )

    response = client.get("/api/swarm-world")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["world"]["layout"] == "sphere"
    assert data["world"]["radius"] > 0
    assert data["world"]["asset_count"] == 1
    assert data["nodes"][0]["ticker"] == "EUNL.DE"
    assert data["nodes"][0]["energy"] == 82.5
    assert data["nodes"][0]["value"] == 239.84
    assert data["nodes"][0]["mass"] == 5.61
    assert data["nodes"][0]["sphere_radius"] == 244.0
    assert data["nodes"][0]["sphere_x"] == 88.0
    assert data["nodes"][0]["sphere_y"] == 130.0
    assert data["nodes"][0]["sphere_z"] == 194.0
    assert data["nodes"][0]["is_dummy"] is False
    assert data["nodes"][0]["world_version"] == "swarm_v6_sphere_tetra"

    sweden_response = client.get("/api/swarm-world?scan_scope=sweden")
    assert sweden_response.status_code == 200
    sweden_data = sweden_response.json()
    assert sweden_data["count"] == 1
    assert sweden_data["nodes"][0]["ticker"] == "XACT.ST"


def test_swarm_history_endpoint_returns_cached_close_history(monkeypatch):
    fake_df = pd.DataFrame(
        [
            {"ticker": "AAA.DE"},
            {"ticker": "BBB.DE"},
        ]
    )
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("""
        CREATE TABLE etf_data (
            ticker TEXT,
            date TEXT,
            close REAL,
            dividends REAL
        )
        """)
    conn.executemany(
        "INSERT INTO etf_data (ticker, date, close, dividends) VALUES (?, ?, ?, ?)",
        [
            ("AAA.DE", "2026-04-20", 10.0, 0.0),
            ("AAA.DE", "2026-04-21", 10.5, 0.0),
            ("AAA.DE", "2026-04-22", 11.0, 0.25),
            ("BBB.DE", "2026-04-21", 20.0, 0.0),
            ("BBB.DE", "2026-04-22", 19.5, 0.0),
        ],
    )
    conn.commit()

    class FakeDB:
        db_path = ":memory:"

        def _get_connection(self):
            return conn

    class FakeSwarmEngine:
        def __init__(self, db_path=None):
            self.db_path = db_path

        def get_world(self, limit=None, label=None, refresh=False):
            return fake_df.head(limit)

    monkeypatch.setattr("ETF_screener.dashboard.app_fast.get_db", lambda: FakeDB())
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.SwarmWorldEngine",
        FakeSwarmEngine,
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._swarm_scope_tickers",
        lambda db, scan_scope=None, exchange=None, ticker_list=None: [
            "AAA.DE",
            "BBB.DE",
        ],
    )

    response = client.get("/api/swarm-history?days=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 2
    assert data["requested_tickers"] == 2
    assert data["count"] == 2
    assert data["as_of_date"] == "2026-04-22"
    assert data["history"]["AAA.DE"]["dates"] == ["2026-04-21", "2026-04-22"]
    assert data["history"]["AAA.DE"]["closes"] == [10.5, 11.0]
    assert data["history"]["AAA.DE"]["dividends"] == [0.0, 0.25]
    assert data["history"]["BBB.DE"]["closes"] == [20.0, 19.5]
    assert data["history"]["BBB.DE"]["dividends"] == [0.0, 0.0]


def test_swarm_debug_scope_generates_dummy_assets(monkeypatch, tmp_path):
    class FakeDB:
        db_path = str(tmp_path / "debug.db")

    monkeypatch.setattr("ETF_screener.dashboard.app_fast.get_db", lambda: FakeDB())

    world_response = client.get("/api/swarm-world?scan_scope=debug&debug_assets=5")
    assert world_response.status_code == 200
    world = world_response.json()
    assert world["world"]["layout"] == "sphere"
    assert world["world"]["asset_count"] == 5
    assert world["count"] == 5
    assert len(world["nodes"]) == 5
    assert all(str(node["ticker"]).startswith("DUMMY-") for node in world["nodes"])
    assert all(node["is_dummy"] is True for node in world["nodes"])
    radii = [float(node["radius"]) for node in world["nodes"]]
    assert min(radii) >= 1.7
    assert max(radii) <= 3.7
    assert max(radii) - min(radii) >= 0.25

    history_response = client.get(
        "/api/swarm-history?scan_scope=debug&debug_assets=5&days=4"
    )
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["requested_tickers"] == 5
    assert history["count"] == 5
    assert history["days"] == 4
    assert len(history["history"]) == 5
    assert all(str(ticker).startswith("DUMMY-") for ticker in history["history"])
    for payload in history["history"].values():
        closes = payload["closes"]
        dividends = payload["dividends"]
        assert len(closes) == 4
        assert len(dividends) == 4
        assert len(set(round(close, 6) for close in closes)) == 1
        assert all(dividend == 0.0 for dividend in dividends)


def test_swarm_dna_save_endpoint_writes_config(monkeypatch, tmp_path):
    target_path = tmp_path / "config" / "swarm_agent_dna.json"
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.SWARM_DNA_CONFIG_PATH",
        target_path,
    )

    payload = {
        "schema_version": "swarm_agent_dna_v2",
        "created_at": "2026-04-26T12:00:00.000Z",
        "world_version": "swarm_v6_sphere_tetra",
        "as_of_date": "2026-04-24",
        "simulation": {
            "steps": 250,
            "max_steps": 250,
            "filter": "All",
            "visible_node_count": 12,
            "starting_energy": 10000,
            "jump_cost_multiplier": 2,
            "history_days": 420,
            "history_ticker_count": 12,
        },
        "top_agents": [
            {
                "rank": 1,
                "id": "AAA.DE-1-test",
                "generation": 3,
                "energy": 12500,
                "profit": 2500,
                "age": 42,
                "target_ticker": "AAA.DE",
                "learned_ticker_count": 4,
                "dna": {
                    "schema_version": "swarm_agent_dna_v2",
                    "ema_fast_period": 30,
                    "ema_slow_period": 50,
                    "rsi_period": 14,
                    "rsi_low": 35,
                    "rsi_high": 70,
                    "behavior_modules": [
                        {
                            "type": "ema_cross_up",
                            "fast_period": 30,
                            "slow_period": 50,
                            "stay_weight": 0.2,
                            "jump_weight": 1.1,
                        },
                        {
                            "type": "ema_cross_down",
                            "fast_period": 30,
                            "slow_period": 50,
                            "stay_weight": -0.8,
                            "jump_weight": 0.4,
                        },
                    ],
                    "mutation_rate": 0.04,
                    "spawn_limit": 15000,
                    "jump_cost_sensitivity": 1.2,
                    "exploration_bias": 0.3,
                    "metabolism": 1.0,
                    "speed": 1.0,
                },
                "rules": [
                    "Hold winners while EMA 30 stays constructive against EMA 50; jump only when a global ticker setup clears friction.",
                    "Treat dividends as part of total return and judge each step against the 2.5% annual inflation hurdle.",
                ],
            }
        ],
    }

    response = client.post("/api/swarm-dna/save", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["agent_count"] == 1
    assert data["path"].replace("\\", "/").endswith("config/swarm_agent_dna.json")

    saved = json.loads(target_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == "swarm_agent_dna_v2"
    assert saved["saved_by"] == "dashboard_swarm_auto_save"
    assert saved["saved_at"]
    assert "dividends as part of total return" in saved["top_agents"][0]["rules"][1]
    assert saved["top_agents"][0]["dna"]["ema_fast_period"] == 30
    assert saved["top_agents"][0]["dna"]["behavior_modules"][0]["slow_period"] == 50


def test_backtest_endpoint_returns_ranked_metrics(monkeypatch, tmp_path):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    (strategies_dir / "demo.dsl").write_text(
        "TRIGGER: close > ema_20\nEXIT: close < ema_20\n", encoding="utf-8"
    )

    fake_df = pd.DataFrame(
        [
            {
                "Ticker": "AAA.DE",
                "Strategy": "demo",
                "Quality Score": 12.34,
                "Return (%)": 18.5,
                "Win Rate (%)": 62.0,
                "Profit Factor": 1.8,
                "Sharpe": 1.4,
                "Max DD (%)": 8.1,
                "Trades": 7,
                "Days Since Entry": 3,
            }
        ]
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.evaluate_strategies",
        lambda strategy_path=None, dsl_content=None, strategy_name=None: fake_df,
    )

    response = client.get("/api/backtest?strategy=demo")
    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == "demo"
    assert data["source_type"] == "saved"
    assert data["summary"]["count"] == 1
    assert data["summary"]["avg_sharpe"] == 1.4
    assert data["rows"][0]["ticker"] == "AAA.DE"
    assert data["rows"][0]["quality_score"] == 12.34
    assert data["chart"]["data"][0]["type"] == "bar"


def test_backtest_endpoint_prefers_editor_dsl(monkeypatch, tmp_path):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    (strategies_dir / "saved.dsl").write_text(
        "TRIGGER: close > ema_20\nEXIT: close < ema_20\n", encoding="utf-8"
    )

    fake_df = pd.DataFrame(
        [
            {
                "Ticker": "BBB.DE",
                "Strategy": "Editor Draft",
                "Quality Score": 9.87,
                "Return (%)": 6.5,
                "Win Rate (%)": 55.0,
                "Profit Factor": 1.4,
                "Sharpe": 1.1,
                "Max DD (%)": 4.2,
                "Trades": 5,
                "Days Since Entry": 8,
            }
        ]
    )
    captured = {}

    def fake_evaluate(strategy_path=None, dsl_content=None, strategy_name=None):
        captured["strategy_path"] = strategy_path
        captured["dsl_content"] = dsl_content
        captured["strategy_name"] = strategy_name
        return fake_df

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.evaluate_strategies",
        fake_evaluate,
    )

    response = client.get(
        "/api/backtest?strategy=saved&dsl_content=TRIGGER%3A%20close%20%3E%20ema_50"
    )
    assert response.status_code == 200
    data = response.json()
    assert captured["dsl_content"] == "TRIGGER: close > ema_50"
    assert captured["strategy_path"] is None
    assert captured["strategy_name"] == "saved"
    assert data["strategy_name"] == "saved"
    assert data["source_type"] == "editor"
    assert data["rows"][0]["ticker"] == "BBB.DE"


def test_backtest_endpoint_forwards_signal_days(monkeypatch, tmp_path):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    (strategies_dir / "age.dsl").write_text(
        "MAX_DAYS: 12\nTRIGGER: close > ema_20\nEXIT: close < ema_20\n",
        encoding="utf-8",
    )

    fake_df = pd.DataFrame(
        [
            {
                "Ticker": "CCC.DE",
                "Strategy": "age",
                "Quality Score": 7.77,
                "Return (%)": 4.4,
                "Win Rate (%)": 58.0,
                "Profit Factor": 1.2,
                "Sharpe": 0.9,
                "Max DD (%)": 3.1,
                "Trades": 4,
                "Days Since Entry": 5,
            }
        ]
    )
    captured = {}

    def fake_evaluate(
        strategy_path=None, dsl_content=None, strategy_name=None, since_days=None
    ):
        captured["strategy_path"] = strategy_path
        captured["dsl_content"] = dsl_content
        captured["strategy_name"] = strategy_name
        captured["since_days"] = since_days
        return fake_df

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.evaluate_strategies",
        fake_evaluate,
    )

    response = client.get("/api/backtest?strategy=age&signal_days=30")
    assert response.status_code == 200
    data = response.json()
    assert captured["since_days"] == 30
    assert captured["strategy_path"].replace("\\", "/").endswith("strategies/age.dsl")
    assert data["rows"][0]["ticker"] == "CCC.DE"


def test_backtest_endpoint_refreshes_on_gui_request(monkeypatch, tmp_path):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    (strategies_dir / "gui.dsl").write_text(
        "TRIGGER: close > ema_20\nEXIT: close < ema_20\n",
        encoding="utf-8",
    )

    fake_df = pd.DataFrame(
        [
            {
                "Ticker": "EEE.DE",
                "Strategy": "gui",
                "Quality Score": 5.55,
                "Return (%)": 2.2,
                "Win Rate (%)": 49.0,
                "Profit Factor": 1.0,
                "Sharpe": 0.6,
                "Max DD (%)": 2.1,
                "Trades": 2,
                "Days Since Entry": 1,
            }
        ]
    )
    captured = {"refreshed": False}

    def fake_refresh(source=None, **kwargs):
        captured["refreshed"] = True
        captured["source"] = source
        return {"refreshed": 1}

    def fake_evaluate(
        strategy_path=None, dsl_content=None, strategy_name=None, since_days=None
    ):
        return fake_df

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast._refresh_market_data_for_gui",
        fake_refresh,
    )
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.evaluate_strategies",
        fake_evaluate,
    )

    response = client.get("/api/backtest?strategy=gui&refresh=true")
    assert response.status_code == 200
    assert captured["refreshed"] is True
    assert captured["source"] is None


def test_backtest_endpoint_still_accepts_since_days_alias(monkeypatch, tmp_path):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    (strategies_dir / "alias.dsl").write_text(
        "MAX_DAYS: 12\nTRIGGER: close > ema_20\nEXIT: close < ema_20\n",
        encoding="utf-8",
    )

    fake_df = pd.DataFrame(
        [
            {
                "Ticker": "DDD.DE",
                "Strategy": "alias",
                "Quality Score": 6.66,
                "Return (%)": 3.3,
                "Win Rate (%)": 51.0,
                "Profit Factor": 1.1,
                "Sharpe": 0.7,
                "Max DD (%)": 2.9,
                "Trades": 3,
                "Days Since Entry": 4,
            }
        ]
    )
    captured = {}

    def fake_evaluate(
        strategy_path=None, dsl_content=None, strategy_name=None, since_days=None
    ):
        captured["since_days"] = since_days
        return fake_df

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.evaluate_strategies",
        fake_evaluate,
    )

    response = client.get("/api/backtest?strategy=alias&since_days=14")
    assert response.status_code == 200
    assert captured["since_days"] == 14


def test_backtest_endpoint_returns_empty_without_strategy():
    response = client.get("/api/backtest")
    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == ""
    assert data["source_type"] == "saved"
    assert data["summary"]["count"] == 0
    assert data["summary"]["avg_sharpe"] == 0.0
    assert data["rows"] == []
    assert data["chart"] == {"data": [], "layout": {}}


def test_get_chart_valid_ticker():
    """Verify we can get chart data and that the figure contains expected visual data."""
    with patch(
        "ETF_screener.dashboard.app_fast.MarketDataRefresher.refresh_ticker_data",
        return_value=add_indicators(_make_fake_ohlcv("DTE.DE")),
    ):
        response = client.get("/api/chart/DTE.DE?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "figure" in data

    fig = json.loads(data["figure"])
    assert "data" in fig
    assert "layout" in fig

    trace_has_data = any(
        len(trace.get("y", [])) > 0 or len(trace.get("close", [])) > 0
        for trace in fig["data"]
    )
    assert trace_has_data, "Chart traces are present but contain no data points"

    st_present = any("ST " in str(trace.get("name", "")) for trace in fig["data"])
    print(f"\nSupertrend indicator found: {st_present}")


def test_on_demand_fetch_persists():
    """Verify that fetching a new ticker via API actually saves it to the database."""
    ticker = "SAP.DE"
    enriched = add_indicators(_make_fake_ohlcv(ticker))

    def fake_refresh(self, ticker, depth=400, warmup_days=90, min_existing_rows=100):
        self.db.insert_dataframe(enriched, ticker)
        self.storage.save_etf_data(enriched, ticker)
        return enriched

    with patch(
        "ETF_screener.dashboard.app_fast.MarketDataRefresher.refresh_ticker_data",
        fake_refresh,
    ):
        response = client.get(f"/api/chart/{ticker}?days=30")
    assert response.status_code == 200

    from ETF_screener.dashboard.app_fast import get_db

    db = get_db()
    assert db.ticker_exists(ticker), f"Ticker {ticker} was fetched but not found in DB"


def test_database_path_consistency():
    """Verify the dashboard is hitting the same database file as the rest of the app."""
    from ETF_screener.dashboard.app_fast import get_db

    db = get_db()
    expected_path = "data/etf_db/etfs.db"
    assert (
        str(db.db_path).replace("\\", "/").endswith(expected_path)
    ), f"Expected DB path to end with {expected_path}, got {db.db_path}"


def _make_recent_entry_result(age: int = 2) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.date_range(end="2024-01-05", periods=5, freq="B"),
            "close": [9.0, 10.0, 11.0, 12.0, 13.0],
            "close_d1": [8.0, 9.0, 10.0, 11.0, 12.0],
            "ema_20": [10.0, 10.0, 10.0, 10.0, 10.0],
            "ema_20_d1": [10.0, 10.0, 10.0, 10.0, 10.0],
            "volume": [1000.0, 1100.0, 1200.0, 1300.0, 1400.0],
            "signal": [0, 0, 1 if age == 2 else 0, 0, 0],
            "exit_condition": [False, False, False, False, False],
        }
    )


def test_screen_endpoint_uses_max_days_from_dsl(monkeypatch):
    class FakeDB:
        def _get_connection(self):
            return object()

    class FakeBacktester:
        def __init__(self):
            self.scripted_strategy = object()

        def run_parallel_backtest(
            self,
            tickers,
            strategy_func,
            days=365,
            strategy_kwargs=None,
        ):
            return [
                {
                    "ticker": "AAA.DE",
                    "df": _make_recent_entry_result(age=2),
                    "total_return_pct": 7.5,
                }
            ]

    monkeypatch.setattr("ETF_screener.dashboard.app_fast.get_db", lambda: FakeDB())
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.pd.read_sql_query",
        lambda query, conn: pd.DataFrame({"ticker": ["AAA.DE"]}),
    )
    monkeypatch.setattr("ETF_screener.dashboard.app_fast.Backtester", FakeBacktester)

    dsl = """
MAX_DAYS: 3
BEGIN SETUP
FILTER: close > ema_20
END
BEGIN TRIGGER
FILTER: close > ema_20 and close_d1 <= ema_20_d1
END
BEGIN EXIT
EXIT: close < ema_20
END
"""

    response = client.get("/api/screen", params={"dsl_content": dsl})
    assert response.status_code == 200
    data = response.json()

    assert data["matches"][0]["ticker"] == "AAA.DE"
    assert data["matches"][0]["days_since_entry"] == 2
    assert data["matches"][0]["status"] == "Recent Entry (2d)"


def test_screen_endpoint_stays_latest_only_without_max_days(monkeypatch):
    class FakeDB:
        def _get_connection(self):
            return object()

    class FakeBacktester:
        def __init__(self):
            self.scripted_strategy = object()

        def run_parallel_backtest(
            self,
            tickers,
            strategy_func,
            days=365,
            strategy_kwargs=None,
        ):
            return [
                {
                    "ticker": "AAA.DE",
                    "df": _make_recent_entry_result(age=2),
                    "total_return_pct": 7.5,
                }
            ]

    monkeypatch.setattr("ETF_screener.dashboard.app_fast.get_db", lambda: FakeDB())
    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.pd.read_sql_query",
        lambda query, conn: pd.DataFrame({"ticker": ["AAA.DE"]}),
    )
    monkeypatch.setattr("ETF_screener.dashboard.app_fast.Backtester", FakeBacktester)

    dsl = """
BEGIN SETUP
FILTER: close > ema_20
END
BEGIN TRIGGER
FILTER: close > ema_20 and close_d1 <= ema_20_d1
END
BEGIN EXIT
EXIT: close < ema_20
END
"""

    response = client.get("/api/screen", params={"dsl_content": dsl})
    assert response.status_code == 200
    data = response.json()

    assert data["matches"] == []


def test_shortlist_endpoint_returns_cached_rows(monkeypatch):
    fake_df = pd.DataFrame(
        [
            {
                "ticker": "EUNL.DE",
                "name": "iShares Core MSCI World UCITS ETF",
                "label": "Buy",
                "issuer": "iShares",
                "asset_class": "Equity",
                "region": "Global",
                "close": 102.55,
                "volume": 750000,
                "recent_entry_days": 3,
                "product_score": 84.0,
                "exposure_score": 80.0,
                "technical_score": 72.0,
                "final_score": 78.4,
                "reasons_json": '["Trusted issuer: iShares", "Price above EMA 50"]',
                "components_json": '{"style": "Core Broad Market"}',
                "as_of_date": "2024-04-30",
                "updated_at": "2026-04-23 21:00:00",
            }
        ]
    )

    class FakeEngine:
        def __init__(self, db_path=None):
            self.db_path = db_path

        def get_shortlist(self, limit=50, label=None, refresh=False):
            return fake_df

    monkeypatch.setattr(
        "ETF_screener.dashboard.app_fast.ETFShortlistEngine",
        FakeEngine,
    )

    response = client.get("/api/shortlist?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["labels"]["Buy"] == 1
    assert data["rows"][0]["ticker"] == "EUNL.DE"
    assert data["rows"][0]["reasons"] == [
        "Trusted issuer: iShares",
        "Price above EMA 50",
    ]
