
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from ETF_screener.dashboard.app_fast import app
from ETF_screener.database import ETFDatabase

client = TestClient(app)

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
    # If the DB has data, we should get some records
    if len(data["matches"]) > 0:
        assert "ticker" in data["matches"][0]
        assert "close" in data["matches"][0]

def test_get_chart_valid_ticker():
    """Verify we can get chart data and that the figure contains expected visual data."""
    # Using a common ticker like 'DTE.DE'
    response = client.get("/api/chart/DTE.DE?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "figure" in data
    
    # Parse the inner figure string
    import json
    fig = json.loads(data["figure"])
    
    # Structural checks
    assert "data" in fig, "Plotly figure missing data traces"
    assert "layout" in fig, "Plotly figure missing layout"
    
    # Data quality checks (Ensuring it's not just an empty canvas)
    # Most Candlestick or Scatter plots will have a 'y' array
    trace_has_data = any(len(trace.get("y", [])) > 0 or len(trace.get("close", [])) > 0 for trace in fig["data"])
    assert trace_has_data, "Chart traces are present but contain no data points"
    
    # Check if Supertrend traces are present (identifiable by name or metadata)
    # The plotter uses "ST Support" and "ST Resistance" names
    st_present = any("ST " in str(trace.get("name", "")) for trace in fig["data"])
    # We don't strictly assert this yet as some tickers might have insufficient data for indicators, 
    # but we print it for test visibility.
    print(f"\nSupertrend indicator found: {st_present}")

def test_on_demand_fetch_persists():
    """Verify that fetching a new ticker via API actually saves it to the database."""
    ticker = "SAP.DE" # Choose a ticker likely not in the short-running test DB
    
    # 1. Fetch via API
    response = client.get(f"/api/chart/{ticker}?days=30")
    assert response.status_code == 200
    
    # 2. Verify directly in DB
    from ETF_screener.dashboard.app_fast import get_db
    db = get_db()
    assert db.ticker_exists(ticker), f"Ticker {ticker} was fetched but not found in DB"


def test_database_path_consistency():
    """Verify the dashboard is hitting the same database file as the rest of the app."""
    from ETF_screener.dashboard.app_fast import get_db
    db = get_db()
    # Check if the path is explicitly set to data/etfs.db
    assert str(db.db_path).replace("\\", "/").endswith("data/etfs.db")
