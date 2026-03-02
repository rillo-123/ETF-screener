import argparse
import pandas as pd
from ETF_screener.snippets import Snippet
from ETF_screener.indicators import add_indicators

from ETF_screener.indicators import add_indicators

# Configuration - Change these to easily adjust the scan
EMA_FAST = 30
EMA_SLOW = 50
MIN_AVG_VOLUME = 100_000

def find_ema_crosses(days_back=120):
    """Find ETFs where EMA_FAST > EMA_SLOW and calculate how long ago the cross happened."""
    print(f"Searching for {EMA_FAST} > {EMA_SLOW} EMA crosses (Min Vol: {MIN_AVG_VOLUME:,})...")
    
    with Snippet() as s:
        def process_ticker(ticker, df):
            if df.empty or len(df) < 5:
                return None
            
            # Volume Check
            if 'Volume' in df.columns:
                avg_vol = df['Volume'].tail(20).mean()
                if avg_vol < MIN_AVG_VOLUME:
                    return None
            
            # Calculate EMAs
            df = df.sort_values('Date') if 'Date' in df.columns else df
            df[f'EMA_{EMA_FAST}'] = df['Close'].ewm(span=EMA_FAST, adjust=False).mean()
            df[f'EMA_{EMA_SLOW}'] = df['Close'].ewm(span=EMA_SLOW, adjust=False).mean()
            
            latest = df.iloc[-1]
            if not (latest[f'EMA_{EMA_FAST}'] > latest[f'EMA_{EMA_SLOW}']):
                return None
            
            # Find the cross-over point
            cross_index = -1
            for i in range(len(df) - 2, 0, -1):
                if df.iloc[i][f'EMA_{EMA_FAST}'] <= df.iloc[i][f'EMA_{EMA_SLOW}']:
                    cross_index = i + 1
                    break
            
            if cross_index != -1:
                return {
                    'ticker': ticker,
                    'price': latest['Close'],
                    'diff': latest[f'EMA_{EMA_FAST}'] - latest[f'EMA_{EMA_SLOW}'],
                    'days_ago': len(df) - 1 - cross_index
                }
            return None

        # Use the parallel map helper
        results = s.map_parallel(process_ticker, days=days_back, desc="Finding Crosses")

        # Sort by days ago (most recent first)
        results.sort(key=lambda x: x['days_ago'])
        
        if not results:
            print("No ETFs currently in a bullish EMA cross.")
            return

        cols = f"{'Ticker':<10} | {'Price':<8} | {'Gap':<8} | {'Days Since Cross'}"
        print(f"\n{cols}")
        print("-" * len(cols))
        for res in results:
            print(f"{res['ticker']:<10} | {res['price']:>8.2f} | {res['diff']:>8.2f} | {res['days_ago']:>12}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find ETFs with EMA30 > EMA50 trend.")
    parser.add_argument("--days", type=int, default=120, help="Lookback period for data (default: 120)")
    args = parser.parse_args()
    
    find_ema_crosses(days_back=args.days)
