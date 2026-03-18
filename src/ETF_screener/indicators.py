"""Technical indicators for swing trading analysis."""

import pandas as pd
import numpy as np
from typing import Any, Union, Tuple, List, Optional


def clean_price_data(series: pd.Series, max_pct_change: float = 0.5) -> pd.Series:
    """
    Remove extreme outliers from price data by replacing them with the previous value.
    This effectively 'mutes' single-day spikes or 'level shifts' (incorrect cents vs euro).

    Args:
        series: Price series (e.g., Close)
        max_pct_change: Percentage threshold for identifying spikes (default 50%)

    Returns:
        Cleaned series with spikes and incorrect unit shifts smoothed out.
    """
    s = series.copy()
    
    # Identifies the START of a spike/shift.
    # If change from previous is > threshold (e.g. 50%)
    # or if we have a massive immediate divergence from the rolling median.
    window = 10
    rolling_median = s.rolling(window=window, center=True).median().fillna(method='bfill').fillna(method='ffill')

    for i in range(1, len(s)):
        prev_val = s.iloc[i-1]
        curr_val = s.iloc[i]
        
        # Guard against division by zero if data is sparse
        if prev_val == 0 or np.isnan(prev_val):
            continue
            
        # 1. Check for immediate % change (e.g. price jumps from 10 to 1000)
        pct_change = abs(curr_val / prev_val - 1)
        
        # 2. Check for absolute divergence from local median (for "broken" months)
        median_val = rolling_median.iloc[i]
        median_div = abs(curr_val / median_val - 1) if median_val != 0 else 0

        if pct_change > max_pct_change or median_div > max_pct_change * 2:
            s.iloc[i] = prev_val
            
    return s


def calculate_rsi(data: Any, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    """
    if isinstance(data, pd.DataFrame):
        price_col = None
        for col in ['Close', 'close', 'Adj Close']:
            if col in data.columns:
                price_col = col
                break
        series = clean_price_data(data[price_col] if price_col else data.iloc[:,0])
    else:
        series = clean_price_data(data)

    # Convert everything to a clean 1D Series to bypass MultiIndex hell
    s = series.iloc[:, 0] if hasattr(series, 'iloc') and len(series.shape) > 1 else series
    s = pd.Series(s.values.flatten(), index=s.index)

    # Calculate price changes
    delta = s.diff()
    
    # Separate gains and losses
    gains = delta.clip(lower=0)
    losses = delta.clip(upper=0).abs()
    
    # Use Wilder's EWM for RSI calculation matching TradingView/Investing.com
    # alpha = 1 / period
    avg_gains = gains.ewm(alpha=1/period, adjust=False).mean()
    avg_losses = losses.ewm(alpha=1/period, adjust=False).mean()
    
    # Case: First valid points for Wilder's (SMA of first 'period' gains)
    # Most traders expect the first 'period' bars to be SMA then EWM
    # But for simplicity, EWM with adjust=False is usually standard enough.
    
    # RS and RSI
    rs = avg_gains / avg_losses.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    # Fix first 'period' bars to be NaN as we don't have enough data
    rsi.iloc[:period] = np.nan
    
    # Fill cases:
    # 1. Both gains and losses are zero -> neutral (50)
    # 2. Loss is zero but gain > 0 -> Strong (100)
    # 3. Rest is calculated
    rsi = rsi.fillna(50.0)
    rsi.loc[(avg_losses == 0) & (avg_gains > 0)] = 100.0
    
    # If we had a DataFrame/No-MultiIndex input, return a framed RSI for consistency
    if isinstance(data, pd.DataFrame) and not isinstance(data.columns, pd.MultiIndex):
        # Result is already a Series with the original Index, just name it
        return rsi.rename('RSI')
            
    return rsi


def calculate_rsi_ema(data: Any, rsi_period: int = 14, ema_period: int = 10) -> pd.Series:
    """
    Calculate an EMA of the RSI (RSI Signal Line).
    """
    rsi = calculate_rsi(data, rsi_period)
    return rsi.ewm(span=ema_period, adjust=False).mean()


def calculate_adx(high: Any, low: Any = None, close: Any = None, period: int = 14) -> pd.Series:
    """
    Calculate Average Directional Index (ADX) - Trend Strength.
    Values 0-100: > 25 = Strong Trend, < 20 = Weak Trend.
    """
    if isinstance(high, pd.DataFrame):
        df = high
        h = df['High'] if 'High' in df.columns else df['high']
        l = df['Low'] if 'Low' in df.columns else df['low']
        c = df['Close'] if 'Close' in df.columns else df['close']
    else:
        h, l, c = high, low, close

    tr1 = h - l
    tr2 = (h - c.shift()).abs()
    tr3 = (l - c.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Simple TR smoothing for ADX approximation
    atr = tr.rolling(window=period).mean()
    
    up_move = h - h.shift()
    down_move = l.shift() - l
    
    plus_dm = pd.Series(0.0, index=h.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    
    minus_dm = pd.Series(0.0, index=l.index)
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


def calculate_ema(data: Any, period: int = 50) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    """
    if isinstance(data, pd.DataFrame):
        price_col = None
        for col in ['Close', 'close', 'Adj Close']:
            if col in data.columns:
                price_col = col
                break
        series = clean_price_data(data[price_col] if price_col else data.iloc[:,0])
    else:
        series = clean_price_data(data)
        
    return series.ewm(span=period, adjust=False).mean()


def calculate_macd(data: Any, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD, Signal Line, and Histogram.
    """
    if isinstance(data, pd.DataFrame):
        price_col = None
        for col in ['Close', 'close', 'Adj Close']:
            if col in data.columns:
                price_col = col
                break
        series = data[price_col] if price_col else data.iloc[:,0]
    else:
        series = data
        
    # Ensure we use raw values to avoid Series/Index alignment issues in EWM
    s = pd.Series(series.values.flatten(), index=series.index)
    
    # Standard MACD (12, 26, 9)
    fast_ema = s.ewm(span=fast, adjust=False).mean()
    slow_ema = s.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    
    # Signal line is 9-day EMA of the MACD line
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_stochastic(high: Any, low: Any = None, close: Any = None, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator (%K and %D).
    """
    if isinstance(high, pd.DataFrame):
        df = high
        h = df['High'] if 'High' in df.columns else df['high']
        l = df['Low'] if 'Low' in df.columns else df['low']
        c = df['Close'] if 'Close' in df.columns else df['close']
    else:
        h, l = high, low
        c = close

    low_min = l.rolling(window=k_period).min()
    high_max = h.rolling(window=k_period).max()
    
    k_line = 100 * (c - low_min) / (high_max - low_min)
    d_line = k_line.rolling(window=d_period).mean()
    
    return k_line, d_line


def calculate_stoch_rsi(data: Any, rsi_period: int = 14, stoch_period: int = 14, k_period: int = 3, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic RSI.
    
    Returns:
        Tuple of (StochRSI %K, StochRSI %D)
    """
    rsi = calculate_rsi(data, rsi_period)
    
    # Calculate StochRSI
    rsi_min = rsi.rolling(window=stoch_period).min()
    rsi_max = rsi.rolling(window=stoch_period).max()
    
    # Avoid division by zero
    diff = rsi_max - rsi_min
    raw_stoch_rsi = 100 * (rsi - rsi_min) / diff
    
    # Simple smoothing to get %K and %D
    # TradingView style: k = SMA(Stoch, 3), d = SMA(K, 3)
    k_line = raw_stoch_rsi.rolling(window=k_period).mean()
    d_line = k_line.rolling(window=d_period).mean()
    
    # Clip and handle NaNs
    k_line = k_line.clip(0, 100).fillna(50.0)
    d_line = d_line.clip(0, 100).fillna(50.0)
    
    return k_line, d_line


def calculate_supertrend(
    high: Any, low: Any = None, close: Any = None, period: int = 10, multiplier: float = 3.0
) -> Union[Tuple[pd.Series, pd.Series, pd.Series], pd.Series]:
    """
    Calculate Supertrend indicator.
    Accepts (high, low, close) as individual Series OR a single DataFrame.
    """
    if isinstance(high, pd.DataFrame):
        df = high
        h = df['High'] if 'High' in df.columns else df['high']
        l = df['Low'] if 'Low' in df.columns else df['low']
        c = df['Close'] if 'Close' in df.columns else df['close']
    else:
        h, l, c = high, low, close

    # Calculate ATR (Average True Range)
    tr1 = h - l
    tr2 = (h - c.shift()).abs()
    tr3 = (l - c.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    # Calculate HL2 (High-Low Average)
    hl2 = (h + l) / 2

    # Calculate basic bands
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr

    # Calculate final bands and supertrend direction
    final_ub = basic_ub.copy()
    final_lb = basic_lb.copy()
    
    supertrend = pd.Series(index=c.index, dtype=float)
    supertrend_direction = pd.Series(index=c.index, dtype=int)
    
    # Wait for ATR to be available
    start_idx = period
    if start_idx >= len(c):
        return supertrend if not isinstance(high, pd.DataFrame) else (supertrend, final_ub, final_lb)

    # Initialize first valid bar
    supertrend_direction.iloc[start_idx] = 1 # Initial guess
    supertrend.iloc[start_idx] = basic_ub.iloc[start_idx]

    for i in range(start_idx + 1, len(c)):
        # Final Upper Band
        if basic_ub.iloc[i] < final_ub.iloc[i-1] or c.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
            
        # Final Lower Band
        if basic_lb.iloc[i] > final_lb.iloc[i-1] or c.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
            
        # Strategy Direction logic
        if supertrend_direction.iloc[i-1] == 1:
            if c.iloc[i] > final_ub.iloc[i]:
                supertrend_direction.iloc[i] = 1
                supertrend.iloc[i] = final_lb.iloc[i]
            else:
                supertrend_direction.iloc[i] = -1
                supertrend.iloc[i] = final_ub.iloc[i]
        else:
            if c.iloc[i] < final_lb.iloc[i]:
                supertrend_direction.iloc[i] = -1
                supertrend.iloc[i] = final_ub.iloc[i]
            else:
                supertrend_direction.iloc[i] = 1
                supertrend.iloc[i] = final_lb.iloc[i]

    return supertrend if not isinstance(high, pd.DataFrame) else (supertrend, final_ub, final_lb)


def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample daily OHLCV data to weekly.

    Args:
        df: DataFrame with Date column and OHLCV data

    Returns:
        Weekly resampled DataFrame
    """
    df_copy = df.copy()
    
    # Ensure Date is datetime and set as index
    if 'Date' in df_copy.columns:
        df_copy['Date'] = pd.to_datetime(df_copy['Date'])
        df_copy = df_copy.set_index('Date')
    
    # Resample to weekly (Sunday close)
    df_weekly = df_copy.resample('W').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    
    # Reset index to Date column
    df_weekly = df_weekly.reset_index()
    return df_weekly


def calculate_linreg_slope(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate the slope of a linear regression line over a rolling period.
    This provides a 'best fit' slope that is much less sensitive to noise than diff().
    """
    import numpy as np
    
    def get_slope(y):
        if len(y) < period:
            return 0.0
        # Check for NaNs
        if np.isnan(y).any():
            return 0.0
        x = np.arange(len(y))
        slope, _ = np.polyfit(x, y, 1)
        return slope

    return series.rolling(window=period).apply(get_slope, raw=True)


def calculate_consecutive_streak(df: pd.DataFrame) -> tuple[int, str]:
    """
    Calculate consecutive RED/GREEN days from the current bar backwards.
    
    Args:
        df: DataFrame with Close and Supertrend columns
        
    Returns:
        Tuple of (streak_count, streak_direction) where direction is "RED" or "GREEN"
    """
    if len(df) == 0 or "Close" not in df.columns or "Supertrend" not in df.columns:
        return 0, "UNKNOWN"
    
    streak = 0
    # Current status (most recent bar)
    latest_close = df["Close"].iloc[-1]
    latest_st = df["Supertrend"].iloc[-1]
    
    if pd.isna(latest_st):
        return 0, "UNKNOWN"
    
    # Determine if RED or GREEN
    current_status = "GREEN" if latest_close > latest_st else "RED"
    
    # Count backwards from most recent bar
    for i in range(len(df) - 1, -1, -1):
        close = df["Close"].iloc[i]
        st = df["Supertrend"].iloc[i]
        
        if pd.isna(st):
            break
        
        status = "GREEN" if close > st else "RED"
        
        if status == current_status:
            streak += 1
        else:
            break
    
    return streak, current_status


def add_indicators(
    df: pd.DataFrame, 
    st_period: int = 10, 
    st_multiplier: float = 3.0,
    timeframe: str = "1D"
) -> pd.DataFrame:
    """
    Add technical indicators to dataframe.

    Args:
        df: DataFrame with OHLCV data (Date column required for 1W)
        st_period: Supertrend ATR period (default 10)
        st_multiplier: Supertrend multiplier (default 3.0)
        timeframe: Timeframe for calculation ("1D" or "1W", default "1D")

    Returns:
        DataFrame with added indicator columns
    """
    df_copy = df.copy()
    
    # Resample to weekly if requested
    if timeframe.upper() == "1W":
        df_copy = resample_to_weekly(df_copy)

    # EMA 50
    df_copy["EMA_50"] = calculate_ema(df_copy["Close"], period=50)

    # RSI 14
    df_copy["RSI"] = calculate_rsi(df_copy["Close"], period=14)

    # Supertrend with configurable parameters
    st_res = calculate_supertrend(
        df_copy, 
        period=st_period, multiplier=st_multiplier
    )
    if isinstance(st_res, tuple):
        st, ub, lb = st_res
    else:
        st = st_res; ub = lb = None
        
    df_copy["Supertrend"] = st
    df_copy["ST_Upper"] = ub
    df_copy["ST_Lower"] = lb

    # Swing setup detection: price near EMA50 but in uptrend
    # Look back 10 days for max price to detect pullback
    lookback = 10
    df_copy["Recent_High"] = df_copy["Close"].rolling(window=lookback).max()
    
    # Pullback percentage: how far below recent high
    df_copy["Pullback_Pct"] = ((df_copy["Recent_High"] - df_copy["Close"]) / df_copy["Recent_High"] * 100).round(2)
    
    # Distance from EMA50 (negative = below, positive = above)
    df_copy["EMA_Distance_Pct"] = ((df_copy["Close"] - df_copy["EMA_50"]) / df_copy["EMA_50"] * 100).round(2)
    
    # In uptrend: price > EMA50 (allows small dips)
    df_copy["In_Uptrend"] = (df_copy["Close"] > df_copy["EMA_50"]).astype(int)

    # Buy/Sell signals based on Supertrend and EMA50
    signals = []

    for i in range(len(df_copy)):
        if i == 0:
            signals.append(0)
        else:
            signal = 0
            # Buy signal: price crosses above supertrend and is above EMA50
            if (
                df_copy["Close"].iloc[i - 1] <= df_copy["Supertrend"].iloc[i - 1]
                and df_copy["Close"].iloc[i] > df_copy["Supertrend"].iloc[i]
                and df_copy["Close"].iloc[i] > df_copy["EMA_50"].iloc[i]
            ):
                signal = 1  # Buy signal

            # Sell signal: price crosses below supertrend
            elif (
                df_copy["Close"].iloc[i - 1] >= df_copy["Supertrend"].iloc[i - 1]
                and df_copy["Close"].iloc[i] < df_copy["Supertrend"].iloc[i]
            ):
                signal = -1  # Sell signal

            signals.append(signal)

    df_copy["Signal"] = signals
    return df_copy
