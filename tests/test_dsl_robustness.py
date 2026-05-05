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

    @pytest.mark.parametrize(
        "entry_rule",
        [
            "within(close < ema_20, 2, 3)",
            "between(close < ema_20, 2, 3)",
        ],
    )
    def test_interval_helpers_trigger_on_expected_bar(self, bt, entry_rule):
        """Test interval-based lookbacks expand into the expected bar window."""
        df = pd.DataFrame(
            {
                "Date": pd.date_range(start="2024-01-01", periods=5),
                "open": [12, 12, 9, 12, 12],
                "high": [13, 13, 10, 13, 13],
                "low": [11, 11, 8, 11, 11],
                "close": [12, 12, 9, 12, 12],
                "volume": [1000, 1000, 1000, 1000, 1000],
                "ema_20": [10, 10, 10, 10, 10],
            }
        )

        res = bt.scripted_strategy(df, "TEST_INTERVAL", entry_rule, "False")
        out = res["df"] if isinstance(res, dict) else res

        assert out["signal"].tolist() == [0, 0, 0, 0, 1]

    def test_between_now_alias_matches_numeric_zero(self, bt):
        """Test that 'now' is accepted as the current bar offset."""
        df = pd.DataFrame(
            {
                "Date": pd.date_range(start="2024-01-01", periods=4),
                "open": [12, 12, 12, 9],
                "high": [13, 13, 13, 10],
                "low": [11, 11, 11, 8],
                "close": [12, 12, 12, 9],
                "volume": [1000, 1000, 1000, 1000],
                "ema_20": [10, 10, 10, 10],
            }
        )

        now_res = bt.scripted_strategy(
            df, "TEST_NOW", "between(close < ema_20, 3, now)", "False"
        )
        zero_res = bt.scripted_strategy(
            df, "TEST_ZERO", "between(close < ema_20, 0, 3)", "False"
        )

        now_df = now_res["df"] if isinstance(now_res, dict) else now_res
        zero_df = zero_res["df"] if isinstance(zero_res, dict) else zero_res

        assert now_df["signal"].tolist() == zero_df["signal"].tolist()
