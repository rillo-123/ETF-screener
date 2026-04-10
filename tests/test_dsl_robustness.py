import pytest
import pandas as pd
import numpy as np
from ETF_screener.backtester import Backtester


@pytest.fixture
def bt():
    return Backtester()


@pytest.fixture
def trend_data():
    """Create data that clearly transitions for Supertrend testing."""
    dates = pd.date_range(start="2024-01-01", periods=50)
    # Price starts at 100, goes up to 120, then crashes to 90
    # Days 0-25: 100 -> 120
    # Days 26-50: 120 -> 90
    prices = np.concatenate(
        [np.linspace(100.0, 120.0, 25), np.linspace(119.0, 90.0, 25)]
    )

    df = pd.DataFrame(
        {
            "Date": dates,
            "open": prices,
            "high": prices + 2.0,
            "low": prices - 1.0,
            "close": prices,
            "volume": 1000,
        }
    )
    return df


class TestDSLRobustness:
    """Tests specifically targeting the 'TokenError' and 'Mangled Words' bugs."""

    def test_parametric_supertrend_alias(self, bt, trend_data):
        """Test st_10_4_is_green and st_10_4_is_red expansion."""
        # This tests both the dynamic regex and the comparison wrapper
        entry = "st_10_4_is_red"
        exit_rule = "st_10_4_is_green"

        # Should not crash with TokenError
        res = bt.scripted_strategy(trend_data, "TEST_ST", entry, exit_rule)
        if res is None:
            pytest.fail(
                "Strategy evaluation returned None, check console for transformed script."
            )
        df = res["df"] if isinstance(res, dict) else res

        assert "st_10_4" in df.columns
        assert "signal" in df.columns

    def test_was_true_with_aliases(self, bt, trend_data):
        """Test was_true(st_is_green, 5) expansion."""
        # This was causing the 'st_is_green_d5' mangling bug
        entry = "st_is_red and was_true(st_is_green, 5)"
        exit_rule = "st_is_green"

        # Should not crash
        res = bt.scripted_strategy(trend_data, "TEST_WAS_TRUE", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert "signal" in df.columns

    def test_cross_down_with_aliases(self, bt, trend_data):
        """Test cross_down(st_is_green, 0.5) expansion."""
        # This tests the most common trigger that was failing
        entry = "cross_down(st_is_green, 0.5)"
        exit_rule = "st_is_red"

        res = bt.scripted_strategy(trend_data, "TEST_CROSS", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert "signal" in df.columns

    def test_word_boundary_protection(self, bt, trend_data):
        """Ensure 'close' doesn't become 'c(lose'."""
        # We use a strategy that uses 'close' explicitly
        entry = "close < st_10_4"
        exit_rule = "close > st_10_4"

        # This specifically tests if 'close' survives the comparison wrapper regex
        res = bt.scripted_strategy(trend_data, "TEST_CLOSE", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert "signal" in df.columns

    def test_nested_complex_logic(self, bt, trend_data):
        """Test very complex logic strings to ensure parser stability."""
        entry = "(st_10_4_is_red and was_true(st_10_4_is_green, 10)) or (close < ema_50 and rsi_14 < 30)"
        exit_rule = "st_10_4_is_green"

        # Should handle nested parens and multiple indicators
        res = bt.scripted_strategy(trend_data, "TEST_COMPLEX", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert "signal" in df.columns
