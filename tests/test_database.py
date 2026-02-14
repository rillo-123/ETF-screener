"""Tests for database module."""

import pandas as pd
import pytest
import tempfile
from pathlib import Path

from ETF_screener.database import ETFDatabase


class TestETFDatabase:
    """Test SQLite database functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ETFDatabase(db_path=str(db_path))
            yield db
            db.close()  # Ensure connection is closed before cleanup

    @pytest.fixture
    def sample_data(self):
        """Create sample ETF data."""
        return pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", periods=60, freq="D"),
                "Open": [100 + i * 0.1 for i in range(60)],
                "High": [101 + i * 0.1 for i in range(60)],
                "Low": [99 + i * 0.1 for i in range(60)],
                "Close": [100.5 + i * 0.1 for i in range(60)],
                "Volume": [10_000_000 + i * 100_000 for i in range(60)],
                "EMA_50": [100.0] * 60,
                "Supertrend": [100.0] * 60,
                "ST_Upper": [101.0] * 60,
                "ST_Lower": [99.0] * 60,
                "Signal": [0] * 60,
            }
        )

    def test_database_initialization(self, temp_db):
        """Test database initializes with schema."""
        assert temp_db.db_path.exists()

    def test_insert_dataframe(self, temp_db, sample_data):
        """Test inserting DataFrame."""
        temp_db.insert_dataframe(sample_data, "TEST")
        
        result = temp_db.get_etf_data("TEST")
        assert len(result) == 60
        assert "TEST" not in result.columns  # ticker not in result

    def test_ticker_exists(self, temp_db, sample_data):
        """Test checking if ticker exists."""
        assert not temp_db.ticker_exists("TEST")
        
        temp_db.insert_dataframe(sample_data, "TEST")
        assert temp_db.ticker_exists("TEST")

    def test_get_tickers(self, temp_db, sample_data):
        """Test getting all tickers."""
        temp_db.insert_dataframe(sample_data, "ETFA")
        temp_db.insert_dataframe(sample_data, "ETFB")
        
        tickers = temp_db.get_tickers()
        assert "ETFA" in tickers
        assert "ETFB" in tickers
        assert len(tickers) == 2

    def test_get_latest_date(self, temp_db, sample_data):
        """Test getting latest date."""
        temp_db.insert_dataframe(sample_data, "TEST")
        
        latest = temp_db.get_latest_date("TEST")
        assert latest is not None
        # Latest date should be 59 days after first date (2024-01-01 + 59 days = 2024-02-29)
        assert latest == sample_data["Date"].max().strftime("%Y-%m-%d")

    def test_query_by_volume(self, temp_db):
        """Test volume-based querying."""
        # Create sample data with recent dates
        recent_data = pd.DataFrame(
            {
                "Date": pd.date_range(end="today", periods=15, freq="D"),  # Last 15 days to today
                "Open": [100 + i * 0.1 for i in range(15)],
                "High": [101 + i * 0.1 for i in range(15)],
                "Low": [99 + i * 0.1 for i in range(15)],
                "Close": [100.5 + i * 0.1 for i in range(15)],
                "Volume": [10_000_000 + i * 100_000 for i in range(15)],
                "EMA_50": [100.0] * 15,
                "Supertrend": [100.0] * 15,
                "ST_Upper": [101.0] * 15,
                "ST_Lower": [99.0] * 15,
                "Signal": [0] * 15,
            }
        )
        
        temp_db.insert_dataframe(recent_data, "HIGHVOL")
        results = temp_db.query_by_volume(min_days=10, min_volume=10_000_000, limit=10)
        
        assert not results.empty
        assert "HIGHVOL" in results["ticker"].values
        assert results["avg_volume"].iloc[0] > 10_000_000

    def test_context_manager(self, temp_db):
        """Test context manager."""
        with temp_db as db:
            assert db.ticker_exists("NONEXISTENT") is False
