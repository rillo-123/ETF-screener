#!/usr/bin/env python3
"""
Example: Find tickers that were oversold at ANY POINT in the last X days

Use case: Identify tickers that had temporary weakness over a period
(even if they've recovered since)

Usage:
    python example_oversold_period.py                                    # Defaults: 30 days, threshold 30
    python example_oversold_period.py --days 60 --threshold 25          # Custom parameters
    python example_oversold_period.py --days 90 --threshold 20
"""

import sys
sys.path.insert(0, 'src')

import argparse
from ETF_screener.snippets import Snippet


def main():
    parser = argparse.ArgumentParser(description="Find tickers oversold in period")
    parser.add_argument("--days", type=int, default=30, help="Days to look back (default: 30)")
    parser.add_argument("--threshold", type=float, default=30, help="RSI threshold for oversold (default: 30)")
    
    args = parser.parse_args()
    
    with Snippet() as snippet:
        results = snippet.find_oversold_in_period(days_lookback=args.days, rsi_threshold=args.threshold)
        
        if not results:
            print(f"No ETFs found with RSI < {args.threshold} in last {args.days} days")
            return
        
        print(f"\n✓ Found {len(results)} ETFs with RSI < {args.threshold} in last {args.days} days\n")
        print("Ticker      Times Oversold      Date(s)")
        print("-" * 70)
        
        # Sort by number of oversold days
        sorted_results = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)
        
        for ticker, dates in sorted_results:
            count = len(dates)
            dates_str = ", ".join(dates[-3:])  # Show last 3 dates
            if len(dates) > 3:
                dates_str += f", ... ({len(dates)} total)"
            print(f"{ticker:<11} {count:>2}x               {dates_str}")


if __name__ == "__main__":
    main()
