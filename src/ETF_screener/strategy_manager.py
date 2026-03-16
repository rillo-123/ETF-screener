import pandas as pd
import hashlib
import json
from pathlib import Path
from typing import Callable, Any, Dict, List
from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import calculate_ema, calculate_rsi, calculate_supertrend

class CachedStrategyManager:
    """Manages strategy execution with memory caching for indicator calculations."""

    _memory_cache = {}  # Class-level cache shared across instances but local to process

    def __init__(self, db: ETFDatabase, cache_dir: str = "data/cache"):
        self.db = db
        # We keep cache_dir for backward compatibility but won't use it for primary reads/writes
        self.cache_dir = Path(cache_dir)

    def _get_cache_key(self, ticker: str, indicator_name: str, params: Dict[str, Any], df_len: int) -> str:
        """Generate a unique cache key based on ticker, parameters, and data length."""
        param_str = json.dumps(params, sort_keys=True)
        return f"{ticker}_{indicator_name}_{param_str}_{df_len}"

    def get_indicator(self, df: pd.DataFrame, ticker: str, func: Callable, name: str, **kwargs) -> pd.Series:
        """
        Get indicator values, using memory cache if available.
        """
        cache_key = self._get_cache_key(ticker, name, kwargs, len(df))

        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # Standard column names
        price_col = 'Close' if 'Close' in df.columns else 'close'
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        if name in ["Supertrend", "ADX", "stoch_all"] or func.__name__ in ["calculate_supertrend", "calculate_adx", "calculate_stochastic"]:
            # Some indicators return multiple values and require OHLC
            res = func(df[high_col], df[low_col], df[price_col], **kwargs)
            result = res[0] if isinstance(res, tuple) else res
        elif "series" in kwargs:
            # For functions like calculate_linreg_slope that take a pre-calculated series
            series = kwargs.pop("series")
            result = func(series, **kwargs)
        else:
            # Standard single-column indicators (EMA, RSI, MACD)
            res = func(df[price_col], **kwargs)
            # If the result is a tuple (like MACD), we cache the whole thing
            result = res
        
        # Save to memory cache
        self._memory_cache[cache_key] = result
        return result

    def prepare_data(self, ticker: str, indicators_setup: List[Dict[str, Any]], days: int = 365) -> pd.DataFrame:
        """
        Fetches data and attaches all requested indicators using the cache.
        
        Example indicators_setup:
        [
            {'name': 'ema_20', 'func': calculate_ema, 'params': {'period': 20}},
            {'name': 'rsi_14', 'func': calculate_rsi, 'params': {'period': 14}}
        ]
        """
        df = self.db.get_ticker_data(ticker, days=days)
        if df.empty:
            return df

        for setup in indicators_setup:
            col_name = setup['name']
            df[col_name] = self.get_indicator(
                df, ticker, setup['func'], setup['name'], **setup['params']
            )
        
        return df

from typing import List
