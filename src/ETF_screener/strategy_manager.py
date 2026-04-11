import json
from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, List

import pandas as pd
from ETF_screener.database import ETFDatabase


class CachedStrategyManager:
    """Manages strategy execution with memory caching for indicator calculations."""

    _memory_cache: ClassVar[dict[str, Any]] = (
        {}
    )  # Class-level cache shared across instances but local to process

    def __init__(self, db: ETFDatabase, cache_dir: str = "data/cache"):
        self.db = db
        # We keep cache_dir for backward compatibility but won't use it for primary reads/writes
        self.cache_dir = Path(cache_dir)

    def _get_cache_key(
        self, ticker: str, indicator_name: str, params: dict[str, Any], df_len: int
    ) -> str:
        """Generate a unique cache key based on ticker, parameters, and data length."""
        # Filter out objects that are not directly JSON-serializable, like Pandas objects
        serializable_params = {
            k: v
            for k, v in params.items()
            if not isinstance(v, (pd.Series, pd.DataFrame))
        }
        param_str = json.dumps(serializable_params, sort_keys=True)
        return f"{ticker}_{indicator_name}_{param_str}_{df_len}"

    def get_indicator(
        self, df: pd.DataFrame, ticker: str, func: Callable, name: str, **kwargs
    ) -> pd.Series:
        """
        Get indicator values, using disk and then memory cache if available.
        """
        cache_key = self._get_cache_key(ticker, name, kwargs, len(df))

        # 1. Check Memory Cache
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # 2. Check Disk Cache
        disk_cache_file = self.cache_dir / f"{cache_key}.parquet"
        if disk_cache_file.exists():
            try:
                result = pd.read_parquet(disk_cache_file).iloc[:, 0]
                self._memory_cache[cache_key] = result
                return result
            except Exception:
                pass  # Fallback to calculation if disk read fails

        # Standard column names
        price_col = "Close" if "Close" in df.columns else "close"
        high_col = "High" if "High" in df.columns else "high"
        low_col = "Low" if "Low" in df.columns else "low"

        if name in ["Supertrend", "ADX", "stoch_all"] or func.__name__ in [
            "calculate_supertrend",
            "calculate_adx",
            "calculate_stochastic",
        ]:
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

        # 3. Save to memory and disk cache
        self._memory_cache[cache_key] = result

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            if isinstance(result, pd.Series):
                pd.DataFrame(result).to_parquet(disk_cache_file)
            elif isinstance(result, tuple):
                # For tuples (like MACD), store as multi-column dataframe
                pd.DataFrame({f"col_{i}": s for i, s in enumerate(result)}).to_parquet(
                    disk_cache_file
                )
        except Exception:
            pass  # Continue even if disk write fails

        return result

    def prepare_data(
        self, ticker: str, indicators_setup: List[Dict[str, Any]], days: int = 365
    ) -> pd.DataFrame:
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
            col_name = setup["name"]
            df[col_name] = self.get_indicator(
                df, ticker, setup["func"], setup["name"], **setup["params"]
            )

        return df
