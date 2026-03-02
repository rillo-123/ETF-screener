#!/usr/bin/env python3
"""
Example: Auto-fetch demonstration

Shows how Snippet automatically fetches data from yfinance on-demand
without needing to run 'etfs refresh' first.

Usage:
    python example_auto_fetch.py                    # Normal (auto-fetch enabled)
    python example_auto_fetch.py --no-fetch        # Cache-only mode
"""

import sys
sys.path.insert(0, 'src')

import argparse
from ETF_screener.snippets import Snippet


def main():
    parser = argparse.ArgumentParser(description="Demo auto-fetch behavior")
    parser.add_argument("--no-fetch", action="store_true", help="Disable auto-fetch (cache-only)")
    
    args = parser.parse_args()
    auto_fetch = not args.no_fetch
    
    print(f"\n{'=' * 60}")
    print(f"Auto-fetch mode: {auto_fetch}")
    print(f"{'=' * 60}\n")
    
    tickers = ["EXS1.DE", "EUNG.DE", "EONS.DE"]
    
    with Snippet(auto_fetch=auto_fetch) as snippet:
        for ticker in tickers:
            try:
                df = snippet.get_data(ticker, days=30)
                
                if df.empty:
                    print(f"{ticker:<15} ✗ No data (not in cache)")
                    continue
                
                latest = df.iloc[-1]
                rsi = latest.get('RSI', None)
                price = latest.get('Close', None)
                
                if rsi and price:
                    print(f"{ticker:<15} ✓ Price={price:>7.2f}  RSI={rsi:>5.1f}  ({len(df)} days)")
                else:
                    print(f"{ticker:<15} ✓ Data available ({len(df)} days)")
            except Exception as e:
                print(f"{ticker:<15} ✗ Error: {str(e)[:40]}")
    
    print(f"\n{'=' * 60}")
    if auto_fetch:
        print("✓ All tickers cached (subsequent runs will be instant)")
    else:
        print("✓ Cache-only mode - no data was fetched")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
