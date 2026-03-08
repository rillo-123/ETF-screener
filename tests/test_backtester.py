import pytest
import pandas as pd
import numpy as np
from ETF_screener.backtester import Backtester, rsi_strategy, ema_cross_strategy, scripted_strategy
from ETF_screener.indicators import calculate_ema, calculate_rsi

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
        df = ema_cross_strategy(sample_data, fast=10, slow=30)
        assert "signal" in df.columns or "Signal" in df.columns
        # Should have signals
        sig_col = "signal" if "signal" in df.columns else "Signal"
        assert set(df[sig_col].unique()).issubset({0, 1, -1})

    def test_rsi_strategy(self, sample_data):
        df = rsi_strategy(sample_data, rsi_period=14, oversold=30, overbought=70)
        assert "signal" in df.columns or "Signal" in df.columns
        assert len(df) == len(sample_data)

    def test_scripted_strategy_dsl(self, sample_data):
        entry = "(ema_30 > ema_50)"
        exit_rule = "close < Supertrend"
        df = scripted_strategy(sample_data, entry, exit_rule)
        assert "signal" in df.columns or "Signal" in df.columns
        
    def test_scripted_strategy_operators(self, sample_data):
        entry = "(ema_30 -gt ema_50)"
        exit_rule = "close -lt Supertrend"
        df = scripted_strategy(sample_data, entry, exit_rule)
        sig_col = "signal" if "signal" in df.columns else "Signal"
        assert 1 in df[sig_col].values

    def test_backtester_run(self, monkeypatch):
        # Mock database and data fetcher
        class MockDB:
            def get_ticker_data(self, ticker, days):
                dates = pd.date_range("2023-01-01", periods=10)
                return pd.DataFrame({
                    'Date': dates, 'close': [100.0]*10, 'high': [101.0]*10, 
                    'low': [99.0]*10, 'open': [100.0]*10, 'volume': [1000.0]*10
                })
        
        bt = Backtester()
        monkeypatch.setattr(bt, 'db', MockDB())
        
        def dummy_strat(df):
            df['signal'] = 0
            df.loc[df.index[2], 'signal'] = 1
            df.loc[df.index[5], 'signal'] = -1
            return df
            
        res = bt.run_strategy("AAPL", dummy_strat)
        assert "num_trades" in res
        assert res["num_trades"] == 1
