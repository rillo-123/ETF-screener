import json
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from ETF_screener.dashboard.app_fast import app

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
    """Ensure the dashboard exposes only the two primary tabs."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="dashboard-tabs"' in html
    assert ">Screener<" in html
    assert ">Backtester<" in html
    assert ">Churner<" not in html
    assert ">Discovery<" not in html
    assert 'id="backtest-chart"' in html
    assert 'id="backtest-table-body"' in html
    assert "Saved Strategy" in html
    assert "Editor Draft" in html


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
        "ETF_screener.dashboard.app_fast.fetcher.fetch_historical_data",
        return_value=_make_fake_ohlcv("DTE.DE"),
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

    with patch(
        "ETF_screener.dashboard.app_fast.fetcher.fetch_historical_data",
        return_value=_make_fake_ohlcv(ticker),
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
    assert str(db.db_path).replace("\\", "/").endswith(expected_path), (
        f"Expected DB path to end with {expected_path}, got {db.db_path}"
    )
