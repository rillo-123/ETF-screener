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


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to dataframe.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with added indicator columns
    """
    df_copy = df.copy()

    # EMA 50
    df_copy["EMA_50"] = calculate_ema(df_copy["Close"], period=50)

    # Supertrend
    st, ub, lb = calculate_supertrend(
        df_copy["High"], df_copy["Low"], df_copy["Close"], period=10, multiplier=3.0
    )
    df_copy["Supertrend"] = st
    df_copy["ST_Upper"] = ub
    df_copy["ST_Lower"] = lb

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
