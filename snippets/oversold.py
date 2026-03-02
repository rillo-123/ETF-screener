#!/usr/bin/env python3
"""
Example: Find Oversold ETFs (RSI < threshold)

Use case: Identify potential bounce opportunities

Usage:
    python example_oversold.py                          # Default: RSI < 30
    python example_oversold.py --threshold 25          # Strict: RSI < 25
    python example_oversold.py --threshold 35          # Relaxed: RSI < 35
"""

import sys
sys.path.insert(0, 'src')

import argparse
from ETF_screener.snippets import Snippet


def main():
    parser = argparse.ArgumentParser(description="Find oversold ETFs")
    parser.add_argument("--threshold", type=float, default=30, help="RSI threshold (default: 30)")
    
    args = parser.parse_args()
    
    with Snippet() as snippet:
        # Find all oversold tickers
        oversold = snippet.filter_oversold(rsi_threshold=args.threshold)
        
        if not oversold:
            print(f"No ETFs found with RSI < {args.threshold}")
            return
        
        print(f"\n✓ Found {len(oversold)} ETFs with RSI < {args.threshold}\n")
        print("Ticker     RSI")
        print("-" * 20)
        
        for ticker, rsi in oversold:
            print(f"{ticker:<10} {rsi:.1f}")


if __name__ == "__main__":
    main()
