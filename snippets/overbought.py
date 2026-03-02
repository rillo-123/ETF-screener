#!/usr/bin/env python3
"""
Example: Find Overbought ETFs (RSI > threshold)

Use case: Identify potential pullback opportunities or reversals

Usage:
    python example_overbought.py                          # Default: RSI > 70
    python example_overbought.py --threshold 75          # Strict: RSI > 75
    python example_overbought.py --threshold 65          # Relaxed: RSI > 65
"""

import sys
sys.path.insert(0, 'src')

import argparse
from ETF_screener.snippets import Snippet


def main():
    parser = argparse.ArgumentParser(description="Find overbought ETFs")
    parser.add_argument("--threshold", type=float, default=70, help="RSI threshold (default: 70)")
    
    args = parser.parse_args()
    
    with Snippet() as snippet:
        # Find all overbought tickers
        overbought = snippet.filter_overbought(rsi_threshold=args.threshold)
        
        if not overbought:
            print(f"No ETFs found with RSI > {args.threshold}")
            return
        
        print(f"\n✓ Found {len(overbought)} ETFs with RSI > {args.threshold}\n")
        print("Ticker     RSI")
        print("-" * 20)
        
        for ticker, rsi in overbought:
            print(f"{ticker:<10} {rsi:.1f}")


if __name__ == "__main__":
    main()
