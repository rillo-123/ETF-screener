"""Tests for plotter module."""

import numpy as np
import pandas as pd
import pytest
import tempfile
from pathlib import Path

from ETF_screener.plotter import PortfolioPlotter


class TestPortfolioPlotter:
    """Test plotting functionality."""

    @pytest.fixture
    def temp_plot_dir(self):
        """Create temporary plot directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_data_with_indicators(self):
        """Create sample data with indicators."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        prices_series = pd.Series(prices)

        return pd.DataFrame(
            {
                "Date": dates,
                "Open": prices - 0.5,
                "High": prices + 1,
                "Low": prices - 1,
                "Close": prices_series,
                "Volume": np.random.randint(1000000, 5000000, 100),
                "EMA_50": prices_series.rolling(50).mean(),
                "Supertrend": prices_series,
                "ST_Upper": prices_series + 2,
                "ST_Lower": prices_series - 2,
                "Signal": np.zeros(100),
            }
        )

    def test_plotter_initialization(self, temp_plot_dir):
        """Test plotter initialization creates directory."""
        _ = PortfolioPlotter(output_dir=temp_plot_dir)
        assert Path(temp_plot_dir).exists()

    def test_plot_etf_analysis(self, temp_plot_dir, sample_data_with_indicators):
        """Test generating analysis plot."""
        plotter = PortfolioPlotter(output_dir=temp_plot_dir)
        path = plotter.plot_etf_analysis(sample_data_with_indicators, "TEST")

        assert path.exists()
        assert path.suffix == ".png"
        assert "test_analysis" in path.name

    def test_plot_price_only(self, temp_plot_dir, sample_data_with_indicators):
        """Test generating price-only plot."""
        plotter = PortfolioPlotter(output_dir=temp_plot_dir)
        path = plotter.plot_price_only(sample_data_with_indicators, "TEST")

        assert path.exists()
        assert path.suffix == ".png"
        assert "test_price" in path.name

    def test_plot_multiple_etfs(self, temp_plot_dir, sample_data_with_indicators):
        """Test plotting multiple ETFs."""
        plotter = PortfolioPlotter(output_dir=temp_plot_dir)
        etf_dict = {"ETFA": sample_data_with_indicators, "ETFB": sample_data_with_indicators}

        results = plotter.plot_multiple_etfs(etf_dict)

        assert len(results) == 2
        assert all(isinstance(path, Path) for path in results.values())

    def test_plot_with_signals(self, temp_plot_dir, sample_data_with_indicators):
        """Test that signals are properly plotted."""
        # Add some buy and sell signals
        sample_data_with_indicators["Signal"].iloc[20] = 1  # Buy
        sample_data_with_indicators["Signal"].iloc[50] = -1  # Sell

        plotter = PortfolioPlotter(output_dir=temp_plot_dir)
        path = plotter.plot_etf_analysis(sample_data_with_indicators, "SIGNALTEST")

        assert path.exists()
