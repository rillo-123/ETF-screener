"""Technical indicators for swing trading analysis."""

import pandas as pd


def calculate_ema(data: pd.Series, period: int = 50) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Args:
        data: Series of prices
        period: EMA period (default 50)

    Returns:
        Series with EMA values
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_supertrend(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Supertrend indicator.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default 10)
        multiplier: ATR multiplier for bands (default 3.0)

    Returns:
        Tuple of (supertrend, upperband, lowerband)
    """
    # Calculate ATR (Average True Range)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    # Calculate HL2 (High-Low Average)
    hl2 = (high + low) / 2

    # Calculate basic bands
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr

    # Calculate final bands
    final_ub = basic_ub.copy()
    final_lb = basic_lb.copy()

    for i in range(1, len(final_ub)):
        if pd.notna(basic_ub.iloc[i]) and pd.notna(final_ub.iloc[i - 1]):
            final_ub.iloc[i] = min(basic_ub.iloc[i], final_ub.iloc[i - 1]) if close.iloc[i - 1] > final_ub.iloc[i - 1] else basic_ub.iloc[i]
        if pd.notna(basic_lb.iloc[i]) and pd.notna(final_lb.iloc[i - 1]):
            final_lb.iloc[i] = max(basic_lb.iloc[i], final_lb.iloc[i - 1]) if close.iloc[i - 1] < final_lb.iloc[i - 1] else basic_lb.iloc[i]

    # Determine supertrend
    supertrend = pd.Series(index=close.index, dtype=float)
    supertrend_direction = pd.Series(index=close.index, dtype=int)

    for i in range(len(close)):
        if i == 0:
            supertrend.iloc[i] = final_ub.iloc[i] if pd.notna(final_ub.iloc[i]) else close.iloc[i]
            supertrend_direction.iloc[i] = -1
        else:
            if supertrend_direction.iloc[i - 1] == 1:
                if pd.notna(final_lb.iloc[i]) and close.iloc[i] <= final_lb.iloc[i]:
                    supertrend.iloc[i] = final_ub.iloc[i]
                    supertrend_direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = final_lb.iloc[i] if pd.notna(final_lb.iloc[i]) else close.iloc[i]
                    supertrend_direction.iloc[i] = 1
            else:
                if pd.notna(final_ub.iloc[i]) and close.iloc[i] >= final_ub.iloc[i]:
                    supertrend.iloc[i] = final_lb.iloc[i]
                    supertrend_direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = final_ub.iloc[i] if pd.notna(final_ub.iloc[i]) else close.iloc[i]
                    supertrend_direction.iloc[i] = -1

    return supertrend, final_ub, final_lb


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

    # Supertrend with configurable parameters
    st, ub, lb = calculate_supertrend(
        df_copy["High"], df_copy["Low"], df_copy["Close"], 
        period=st_period, multiplier=st_multiplier
    )
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
