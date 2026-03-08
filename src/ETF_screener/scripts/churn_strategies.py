from ETF_screener.backtester import Backtester, rsi_strategy, ema_cross_strategy, ema_supertrend_strategy
from ETF_screener.indicators import calculate_ema, calculate_rsi, calculate_supertrend, calculate_adx
from tqdm import tqdm
import pandas as pd
import os
import argparse
import re
from pathlib import Path

def load_dsl_file(file_path):
    """Parse a .dsl file for ENTRY and EXIT blocks."""
    with open(file_path, 'r') as f:
        content = f.read()
    entry = re.search(r'ENTRY:\s*(.*)', content)
    exit_ = re.search(r'EXIT:\s*(.*)', content)
    return entry.group(1).strip() if entry else None, exit_.group(1).strip() if exit_ else None

def churn_db(entry_script: str = None, exit_script: str = None, ticker_filter: str = None, strategy_path: str = None):
    backtester = Backtester()
    # Get all tickers from DB
    conn = backtester.db._get_connection()
    query = "SELECT DISTINCT ticker FROM etf_data"
    
    if ticker_filter:
        # Smart Filter: If it contains % or _, use as-is. Otherwise, add a trailing % for prefix matching.
        if '%' in ticker_filter or '_' in ticker_filter:
            query += f" WHERE ticker LIKE '{ticker_filter}'"
        else:
            query += f" WHERE ticker LIKE '{ticker_filter}%'"
    
    tickers = pd.read_sql_query(query, conn)['ticker'].tolist()
    
    strategies = []
    
    # Mode 1: Path to a .dsl file or a directory of .dsl files
    if strategy_path:
        path = Path(strategy_path)
        if path.is_file():
            entry, exit_ = load_dsl_file(path)
            strategies.append({"name": path.stem, "func": backtester.scripted_strategy, "kwargs": {"entry_script": entry, "exit_script": exit_}})
        elif path.is_dir():
            for dsl_file in path.glob("*.dsl"):
                entry, exit_ = load_dsl_file(dsl_file)
                strategies.append({"name": dsl_file.stem, "func": backtester.scripted_strategy, "kwargs": {"entry_script": entry, "exit_script": exit_}})
    
    # Mode 2: Direct CLI strings
    elif entry_script and exit_script:
        strategies.append({"name": "CLI_Custom", "func": backtester.scripted_strategy, "kwargs": {"entry_script": entry_script, "exit_script": exit_script}})
    
    if not strategies:
        print("No strategies found to run.")
        return

    all_results = []
    print(f"Churning {len(tickers)} tickers through {len(strategies)} strategies...")
    
    for strat in strategies:
        print(f"Running Strategy: {strat['name']}")
        results = backtester.run_parallel_backtest(
            tickers, 
            strat['func'], 
            days=730, 
            strategy_kwargs=strat.get('kwargs')
        )
        for res in results:
            if res and "error" not in res:
                all_results.append({
                    "Ticker": res['ticker'],
                    "Strategy": strat['name'],
                    "Return (%)": res['total_return_pct'],
                    "Win Rate (%)": res['win_rate_pct'],
                    "Profit Factor": res['profit_factor'],
                    "Sharpe": res.get('sharpe_ratio', 0),
                    "Trades": res.get('num_trades', 0)
                })
    
    # Convert to DataFrame and sort by best performance
    summary_df = pd.DataFrame(all_results)
    if not summary_df.empty:
        # Quality Score: Return * WinRate * (Sharpe + 1) / (1 + trades/100)
        summary_df['Quality Score'] = (
            summary_df['Return (%)'] * 
            (summary_df['Win Rate (%)'] / 100) * 
            (summary_df['Sharpe'] + 1) / 
            (1 + summary_df['Trades'] / 100.0)
        )
        summary_df = summary_df.sort_values(by="Quality Score", ascending=False)
        
        print("\nTop 10 Strategy/ETF Combinations:")
        # Display with 2 decimals
        print(summary_df.head(10).to_string(index=False, float_format=lambda x: "{:.2f}".format(x)))
        
        # Save to CSV with 2 decimal precision (keeps full precision in memory/code)
        output_name = "data/multi_strategy_results.csv"
        summary_df.to_csv(output_name, index=False, float_format="%.2f")
        
        # Also save to "custom_script_results.csv" for run_custom_backtest.ps1 compatibility
        if not strategy_path:
            summary_df.to_csv("data/custom_script_results.csv", index=False, float_format="%.2f")
            
        print(f"\nFull results saved to {output_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", type=str, help="Entry condition (DSL)")
    parser.add_argument("--exit", type=str, help="Exit condition (DSL)")
    parser.add_argument("--filter", type=str, help="Ticker filter")
    parser.add_argument("--strat_path", type=str, help="Path to .dsl file or directory")
    args = parser.parse_args()
    
    churn_db(entry_script=args.entry, exit_script=args.exit, ticker_filter=args.filter, strategy_path=args.strat_path)

