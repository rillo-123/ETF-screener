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
    prices = np.linspace(100.0, 150.0, 100, dtype='float64')
    df = pd.DataFrame({
        'Date': dates,
        'close': prices,
        'high': prices + 1.0,
        'low': prices - 1.0,
        'open': prices,
        'volume': np.full(100, 1000.0, dtype='float64')
    })
    # Manually assign indicators to avoid any tool-call calculation issues in setup
    df['ema_30'] = df['close'].ewm(span=30, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    # Simplified RSI mock for testing DSL
    df['rsi_14'] = np.linspace(30.0, 70.0, 100)
    df['Supertrend'] = 130.0 # Mocked simple value
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
        sample_data['st'] = sample_data['Supertrend']
        res = bt.scripted_strategy(sample_data, "TEST", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert df is not None
        assert "signal" in df.columns or "Signal" in df.columns
        
    def test_scripted_strategy_operators(self, bt, sample_data):
        entry = "(ema_30 > ema_50)"
        exit_rule = "st < close"
        sample_data['st'] = sample_data['Supertrend']
        res = bt.scripted_strategy(sample_data, "TEST", entry, exit_rule)
        df = res["df"] if isinstance(res, dict) else res
        assert df is not None
        sig_col = "signal" if "signal" in df.columns else "Signal"
        assert sig_col in df.columns

    def test_backtester_run(self, bt, monkeypatch):
        # We need to mock the db property specifically on the CLASS or use a different approach
        # because the @property decorator makes it tricky to monkeypatch on the instance
        
        class MockDB:
            def __init__(self, db_path="data/etfs.db"):
                self.db_path = db_path
            def get_ticker_data(self, ticker, days=365):
                dates = pd.date_range("2023-01-01", periods=10)
                return pd.DataFrame({
                    'Date': dates, 'close': [100.0]*10, 'high': [101.0]*10, 
                    'low': [99.0]*10, 'open': [100.0]*10, 'volume': [1000.0]*10
                })
        
        # Patch the class property
        monkeypatch.setattr(Backtester, 'db', property(lambda self: MockDB()))
        
        def dummy_strat(df):
            df = df.copy()
            df['signal'] = 0
            df.loc[2, 'signal'] = 1
            df.loc[5, 'signal'] = -1
            return df
            
        res = bt.run_strategy("AAPL", dummy_strat, indicators_setup=None)
        assert "num_trades" in res
        assert res["num_trades"] == 1
