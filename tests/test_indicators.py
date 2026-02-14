"""Tests for indicators module."""

import numpy as np
import pandas as pd
import pytest

from ETF_screener.indicators import (
    add_indicators,
    calculate_ema,
    calculate_supertrend,
)


class TestIndicators:
    """Test technical indicator calculations."""

    @pytest.fixture
    def sample_data(self):
        """Create sample price data."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        # Create synthetic price data with trend
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        return pd.DataFrame(
            {
                "Date": dates,
                "Open": prices - 0.5,
                "High": prices + 1,
                "Low": prices - 1,
                "Close": prices,
                "Volume": np.random.randint(1000000, 5000000, 100),
            }
        )

    def test_calculate_ema(self, sample_data):
        """Test EMA calculation."""
        ema = calculate_ema(sample_data["Close"], period=20)
        assert len(ema) == len(sample_data)
        assert ema.notna().sum() > 0
        # EMA should not be constant for varying prices
        assert not (ema == ema.iloc[0]).all()

    def test_calculate_supertrend(self, sample_data):
        """Test Supertrend calculation."""
        st, ub, lb = calculate_supertrend(
            sample_data["High"],
            sample_data["Low"],
            sample_data["Close"],
            period=10,
            multiplier=3.0,
        )
        assert len(st) == len(sample_data)
        assert len(ub) == len(sample_data)
        assert len(lb) == len(sample_data)
        # Upper band should be above lower band (for non-NaN values)
        valid_mask = ub.notna() & lb.notna()
        assert (ub[valid_mask] >= lb[valid_mask]).all()

    def test_add_indicators(self, sample_data):
        """Test adding all indicators to dataframe."""
        result = add_indicators(sample_data)

        # Check that all columns are present
        expected_cols = [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "EMA_50",
            "Supertrend",
            "ST_Upper",
            "ST_Lower",
            "Signal",
        ]
        for col in expected_cols:
            assert col in result.columns

        # Check data integrity
        assert len(result) == len(sample_data)
        assert result["Close"].equals(sample_data["Close"])

    def test_add_indicators_signals(self, sample_data):
        """Test that signals are generated correctly."""
        result = add_indicators(sample_data)

        # Signals should be 0, 1, or -1
        assert set(result["Signal"].unique()).issubset({-1, 0, 1})

    def test_ema_convergence(self, sample_data):
        """Test EMA convergence to mean price."""
        # For constant prices, EMA should converge to that price
        constant_prices = pd.Series([100.0] * 100)
        ema = calculate_ema(constant_prices, period=50)
        # After convergence, EMA should be very close to 100
        assert abs(ema.iloc[-1] - 100.0) < 1.0
