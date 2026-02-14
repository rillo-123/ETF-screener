"""Tests for storage module."""

import pandas as pd
import pytest
import tempfile
from pathlib import Path

from ETF_screener.storage import ParquetStorage


class TestParquetStorage:
    """Test parquet storage functionality."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

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
                "Volume": [1000000 + i * 1000 for i in range(60)],
            }
        )

    def test_storage_initialization(self, temp_storage_dir):
        """Test storage initialization creates directory."""
        storage = ParquetStorage(data_dir=temp_storage_dir)
        assert Path(temp_storage_dir).exists()

    def test_save_etf_data(self, temp_storage_dir, sample_data):
        """Test saving ETF data to parquet."""
        storage = ParquetStorage(data_dir=temp_storage_dir)
        path = storage.save_etf_data(sample_data, "TEST")

        assert path.exists()
        assert path.suffix == ".parquet"
        assert path.name == "test_data.parquet"

    def test_load_etf_data(self, temp_storage_dir, sample_data):
        """Test loading ETF data from parquet."""
        storage = ParquetStorage(data_dir=temp_storage_dir)
        storage.save_etf_data(sample_data, "TEST")

        loaded_data = storage.load_etf_data("TEST")

        assert not loaded_data.empty
        assert len(loaded_data) == len(sample_data)
        pd.testing.assert_frame_equal(
            loaded_data.reset_index(drop=True),
            sample_data.reset_index(drop=True),
        )

    def test_load_nonexistent_etf(self, temp_storage_dir):
        """Test loading nonexistent ETF returns empty dataframe."""
        storage = ParquetStorage(data_dir=temp_storage_dir)
        loaded_data = storage.load_etf_data("NONEXISTENT")

        assert loaded_data.empty

    def test_save_multiple_etfs(self, temp_storage_dir, sample_data):
        """Test saving multiple ETFs."""
        storage = ParquetStorage(data_dir=temp_storage_dir)
        etf_dict = {"ETFA": sample_data, "ETFB": sample_data}

        results = storage.save_multiple_etfs(etf_dict)

        assert len(results) == 2
        assert all(path.exists() for path in results.values())

    def test_list_available_etfs(self, temp_storage_dir, sample_data):
        """Test listing available ETFs."""
        storage = ParquetStorage(data_dir=temp_storage_dir)
        storage.save_multiple_etfs({"ETF1": sample_data, "ETF2": sample_data})

        etfs = storage.list_available_etfs()

        assert len(etfs) == 2
        assert "ETF1" in etfs
        assert "ETF2" in etfs
        assert etfs == sorted(etfs)  # Should be sorted
