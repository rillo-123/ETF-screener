#!/usr/bin/env python3
"""
Example: RSI > 70 AND Price > EMA50

Use case: Find strong uptrend moves that haven't exhausted yet
(Overbought but still in uptrend - high probability continuation)
"""

import sys
sys.path.insert(0, 'src')

import pandas as pd
from ETF_screener.snippets import Snippet


def main():
    results = []
    
    with Snippet() as snippet:
        # Manual iteration for combined filtering
        for ticker in snippet.iterate_tickers():
            try:
                df = snippet.get_data(ticker)
                
                if df.empty or 'RSI' not in df.columns or 'EMA_50' not in df.columns:
                    continue
                
                latest = df.iloc[-1]
                rsi = latest['RSI']
                price = latest['Close']
                ema = latest['EMA_50']
                
                # Both conditions must be true
                if (not pd.isna(rsi) and rsi > 70 and 
                    not pd.isna(price) and not pd.isna(ema) and price > ema):
                    results.append({
                        'Ticker': ticker,
                        'Price': f"{price:.2f}",
                        'EMA50': f"{ema:.2f}",
                        'RSI': f"{rsi:.1f}"
                    })
            except Exception:
                pass
    
    if not results:
        print("No ETFs found with RSI > 70 AND Price > EMA50")
        return
    
    # Sort by RSI descending
    df_results = pd.DataFrame(results)
    df_results['RSI_num'] = df_results['RSI'].astype(float)
    df_results = df_results.sort_values('RSI_num', ascending=False).drop('RSI_num', axis=1)
    
    print(f"\n✓ Found {len(results)} ETFs with RSI > 70 AND Price > EMA50\n")
    print(df_results.to_string(index=False))


if __name__ == "__main__":
    main()
