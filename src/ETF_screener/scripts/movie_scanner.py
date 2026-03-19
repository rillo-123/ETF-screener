import pandas as pd
import os
import argparse
from pathlib import Path
from ETF_screener.backtester import Backtester
from ETF_screener.scripts.churn_strategies import load_dsl_file

def movie_scanner(strat_path: str, ticker_filter: str = None, limit_days: int = 50):
    backtester = Backtester()
    
    # 1. Load strategies
    strategies = []
    path = Path(strat_path)
    if path.is_file():
        entry, exit_ = load_dsl_file(path)
        strategies.append({"name": path.stem, "entry": entry, "exit": exit_})
    elif path.is_dir():
        for dsl_file in path.glob("*.dsl"):
            if "strat_cache" in dsl_file.parts: continue
            entry, exit_ = load_dsl_file(dsl_file)
            strategies.append({"name": dsl_file.stem, "entry": entry, "exit": exit_})

    # 2. Get tickers
    conn = backtester.db._get_connection()
    query = "SELECT DISTINCT ticker FROM etf_data"
    if ticker_filter:
        if '%' in ticker_filter or '_' in ticker_filter:
            query += f" WHERE ticker LIKE '{ticker_filter}'"
        else:
            query += f" WHERE ticker LIKE '{ticker_filter}%'"
    tickers = pd.read_sql_query(query, conn)['ticker'].tolist()

    print(f"\n--- REVERSE MOVIE SCANNER ---")
    print(f"Scanning {len(tickers)} tickers through {len(strategies)} strategies...")
    print(f"Looking back up to {limit_days} days...\n")
    print(f"{'DAY':<5} | {'TICKER':<10} | {'STRATEGY':<20} | {'SIGNAL'}")
    print("-" * 60)

    # 3. Churn through time backwards
    # To keep it efficient, we run the strategy once per ticker/strat pair
    # then look at the signal column from the end.
    
    found_any = False
    # Outer loop is day offset (0 = today, 1 = yesterday, etc.)
    for day_offset in range(limit_days):
        signals_today = []
        
        for strat in strategies:
            # We use parallel backtest logic if needed, but for simplicity here we do it sequential
            # to allow the "scrolling" effect in terminal
            for ticker in tickers:
                res = backtester.run_strategy(
                    ticker=ticker, 
                    strategy_func=backtester.scripted_strategy,
                    days=500,
                    strategy_kwargs={"entry_script": strat["entry"], "exit_script": strat["exit"]}
                )
                
                if res and "df" in res:
                    df = res["df"]
                    # Calculate index from the end
                    idx = len(df) - 1 - day_offset
                    if idx >= 0:
                        signal = df.iloc[idx].get('signal', 0)
                        if signal == 1: # Only Entry signals
                            date_str = df.iloc[idx]['Date'].strftime('%Y-%m-%d')
                            print(f"T-{day_offset:<3} | {ticker:<10} | {strat['name']:<20} | BUY ({date_str})")
                            found_any = True

    if not found_any:
        print("No signals found in the specified window.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strat_path", type=str, default="strategies/")
    parser.add_argument("--filter", type=str, help="Ticker filter")
    parser.add_argument("--days", type=int, default=10, help="How many days to look back")
    args = parser.parse_args()
    
    movie_scanner(args.strat_path, args.filter, args.days)
