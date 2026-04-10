import pytest
import pandas as pd
import numpy as np
from ETF_screener.backtester import Backtester, rsi_strategy, ema_cross_strategy
from ETF_screener.indicators import calculate_ema, calculate_rsi


@pytest.fixture
def bt():
    return Backtester()


@pytest.fixture
def sample_data():
    """Create 100 days of upward trending data then downward."""
    dates = pd.date_range(start="2023-01-01", periods=100)
    # Ensure raw numpy arrays are float64
    prices = np.linspace(100.0, 150.0, 100, dtype="float64")
    df = pd.DataFrame(
        {
            "Date": dates,
            "close": prices,
            "high": prices + 1.0,
            "low": prices - 1.0,
            "open": prices,
            "volume": np.full(100, 1000.0, dtype="float64"),
        }
    )
    # Manually assign indicators to avoid any tool-call calculation issues in setup
    df["ema_30"] = df["close"].ewm(span=30, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    # Simplified RSI mock for testing DSL
    df["rsi_14"] = np.linspace(30.0, 70.0, 100)
    df["Supertrend"] = 130.0  # Mocked simple value
    return df


class TestBacktester:
    def test_ema_cross_strategy(self, sample_data):
        df = ema_cross_strategy(sample_data, f=10, s=30)
        assert "signal" in df.columns or "Signal" in df.columns
        # Should have signals
        sig_col = "signal" if "signal" in df.columns else "Signal"
        assert set(df[sig_col].unique()).issubset({0, 1, -1})

    def test_rsi_strategy(self, sample_data):
        df = rsi_strategy(sample_data, p=14, os=30)
        assert "signal" in df.columns or "Signal" in df.columns
        assert len(df) == len(sample_data)

    def test_scripted_strategy_dsl(self, bt, sample_data):
        entry = "(ema_30 > ema_50)"
        exit_rule = "st < close"
        # The DSL expects 'st' to be available. In the real app, it calculates it.
        # In this test, we need to ensure the sample_data has the expected column names
        # or that the DSL aliases are working.
        sample_data["st"] = sample_data["Supertrend"]
        res = bt.scripted_strategy(sample_data, "TEST", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert df is not None
        assert "signal" in df.columns or "Signal" in df.columns

    def test_scripted_strategy_operators(self, bt, sample_data):
        entry = "(ema_30 > ema_50)"
        exit_rule = "st < close"
        sample_data["st"] = sample_data["Supertrend"]
        res = bt.scripted_strategy(sample_data, "TEST", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert df is not None
        sig_col = "signal" if "signal" in df.columns else "Signal"
        assert sig_col in df.columns

    def test_scripted_strategy_recomputes_stale_slope_columns(self, bt, sample_data):
        df_in = sample_data.copy()
        stale_value = -123.456
        df_in["ema_200_slope"] = stale_value

        entry = "(close > ema_200) and (ema_200_slope > 0)"
        exit_rule = "close < ema_200"

        res = bt.scripted_strategy(df_in, "TEST", entry, exit_rule)
        df_out = res["df"] if isinstance(res, dict) else res

        assert df_out is not None
        assert "ema_200" in df_out.columns
        assert "ema_200_slope" in df_out.columns

        # Regression guard: stale persisted slope columns must be replaced.
        assert not np.allclose(df_out["ema_200_slope"].to_numpy(), stale_value)

        expected_slope = df_out["ema_200"].diff().fillna(0)
        assert np.allclose(
            df_out["ema_200_slope"].to_numpy(), expected_slope.to_numpy()
        )

    def test_backtester_run(self, bt, monkeypatch):
        # We need to mock the db property specifically on the CLASS or use a different approach
        # because the @property decorator makes it tricky to monkeypatch on the instance

        class MockDB:
            def __init__(self, db_path="data/etfs.db"):
                self.db_path = db_path

            def get_ticker_data(self, ticker, days=365):
                dates = pd.date_range("2023-01-01", periods=10)
                return pd.DataFrame(
                    {
                        "Date": dates,
                        "close": [100.0] * 10,
                        "high": [101.0] * 10,
                        "low": [99.0] * 10,
                        "open": [100.0] * 10,
                        "volume": [1000.0] * 10,
                    }
                )

        # Patch the class property
        monkeypatch.setattr(Backtester, "db", property(lambda self: MockDB()))

        def dummy_strat(df):
            df = df.copy()
            df["signal"] = 0
            df.loc[2, "signal"] = 1
            df.loc[5, "signal"] = -1
            return df

        res = bt.run_strategy("AAPL", dummy_strat, indicators_setup=None)
        assert "num_trades" in res
        assert res["num_trades"] == 1

    def test_scripted_strategy_handles_st_breakdown_cross_logic(self, bt):
        dates = pd.date_range(start="2024-01-01", periods=8)
        close = np.array([102.0, 103.0, 104.0, 101.0, 99.0, 98.0, 97.5, 97.0])
        st_10_4 = np.array([100.0, 101.0, 102.0, 102.5, 102.0, 101.5, 101.0, 100.5])

        df = pd.DataFrame(
            {
                "Date": dates,
                "close": close,
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "volume": np.full(8, 100000.0),
                "st_10_4": st_10_4,
                "ema_20": np.array(
                    [101.0, 101.5, 102.0, 101.8, 101.0, 100.5, 100.0, 99.5]
                ),
                "ema_50": np.array(
                    [100.5, 100.8, 101.1, 101.0, 100.7, 100.3, 99.9, 99.6]
                ),
                "ema_50_slope": np.array([0.2, 0.2, 0.1, -0.1, -0.2, -0.2, -0.1, -0.1]),
                "adx": np.full(8, 25.0),
            }
        )

        entry = "cross_down(st_10_4_is_green, 0.5) OR (close < ema_20 AND close_d1 >= ema_20_d1) AND was_true(st_10_4_is_green, 10) AND close < ema_50 AND ema_50_slope < 0 AND adx > 18"
        exit_rule = "st_10_4_is_green == 1 OR close > ema_20"

        res = bt.scripted_strategy(df, "TEST", entry, exit_rule)

        assert isinstance(res, dict)
        assert "df" in res
        out = res["df"]
        assert "signal" in out.columns
        assert set(out["signal"].unique()).issubset({-1, 0, 1})
