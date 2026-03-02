import argparse
import pandas as pd
import numpy as np
from ETF_screener.snippets import Snippet

# Configuration
EMA_PERIOD = 30           # Lookback period for the Exponential Moving Average
MIN_AVG_VOLUME = 100_000 # Minimum 20-day average volume to filter out illiquid ETFs
AVG_VOL_DAYS = 20        # Window for volume averaging

# Slope threshold: % change in price per day (e.g., 0.1% = 0.001)
# This 'Angle' normalizes the slope across different price points.
MIN_ANGLE = 0.001 

def find_ema_slope(days_back=120):
    """
    Find ETFs where the EMA is sloping upwards (Rate of Change).
    This script calculates the 1st derivative (Slope) of a single EMA 
    and normalizes it as an 'Angle' relative to the share price.
    """
    print(f"Analyzing EMA {EMA_PERIOD} Slope...")
    print(f"Min Vol: {MIN_AVG_VOLUME:,} | Lookback: {days_back}d")
    
    with Snippet() as s:
        def process_ticker(ticker, df):
            if df.empty or len(df) < max(EMA_PERIOD, 10):
                return None
            
            # --- Volume Filter ---
            # Ensures we only analyze tradeable ETFs with sufficient liquidity
            if 'Volume' in df.columns:
                avg_vol = df['Volume'].tail(AVG_VOL_DAYS).mean()
                if avg_vol < MIN_AVG_VOLUME:
                    return None
            else:
                avg_vol = 0

            # 1. Calculate EMA
            # Using Exponential Moving Average to give more weight to recent price action
            df = df.sort_values('Date') if 'Date' in df.columns else df
            df['EMA'] = df['Close'].ewm(span=EMA_PERIOD, adjust=False).mean()
            
            # 2. Calculate the Slope (1st Derivative)
            # This represents the daily absolute change of the EMA line.
            # We apply a 3-day rolling mean to smooth out single-day volatility 'noise'.
            df['Slope'] = df['EMA'].diff(1).rolling(window=3).mean()
            
            latest = df.iloc[-1]
            current_slope = latest['Slope']

            # Filter out any negative slopes (downtrends)
            if pd.isna(current_slope) or current_slope <= 0:
                return None

            # 3. Calculate 'Angle' (Relative Slope)
            # Normalizing the slope by price allows us to compare a $4000 ETF (like LCUJ)
            # with a $5 ETF (like IBB1) on a level playing field.
            # (Slope / Current Price) * 100 = % increase of the EMA per day.
            angle = (current_slope / latest['Close']) * 100

            if angle < MIN_ANGLE:
                return None

            return {
                'ticker': ticker,
                'price': latest['Close'],
                'ema': latest['EMA'],
                'slope': current_slope,
                'angle': angle,
                'avg_vol': avg_vol
            }

        # Run parallel scan
        results = s.map_parallel(process_ticker, days=days_back, desc="Measuring Slopes")

        # Sort by Angle (steepest relative slope first)
        results.sort(key=lambda x: x['angle'], reverse=True)
        
        if not results:
            print(f"No ETFs found with a positive EMA slope.")
            return

        cols = f"{'Ticker':<10} | {'Price':<8} | {'EMA':<8} | {'Slope (abs)':<12} | {'Angle (%)':<10}"
        print(f"\n{cols}")
        print("-" * len(cols))
        for res in results:
            print(f"{res['ticker']:<10} | {res['price']:>8.2f} | {res['ema']:>8.2f} | {res['slope']:>12.5f} | {res['angle']:>9.4f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find ETFs where the EMA is sloping upwards.")
    parser.add_argument("--days", type=int, default=120, help="Lookback period (default: 120)")
    args = parser.parse_args()
    find_ema_slope(days_back=args.days)
