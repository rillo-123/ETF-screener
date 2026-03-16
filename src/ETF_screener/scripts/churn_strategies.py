from ETF_screener.backtester import Backtester, rsi_strategy, ema_cross_strategy, ema_supertrend_strategy
from ETF_screener.indicators import calculate_ema, calculate_rsi, calculate_supertrend, calculate_adx
from ETF_screener.plotter import PortfolioPlotter
from tqdm import tqdm
import pandas as pd
import os
import argparse
import re
import datetime
from pathlib import Path

def load_dsl_file(file_path):
    """Parse a .dsl file for ENTRY and EXIT blocks."""
    with open(file_path, 'r') as f:
        content = f.read()
    entry = re.search(r'ENTRY:\s*(.*)', content)
    exit_ = re.search(r'EXIT:\s*(.*)', content)
    return entry.group(1).strip() if entry else None, exit_.group(1).strip() if exit_ else None

def churn_db(entry_script: str = None, exit_script: str = None, ticker_filter: str = None, strategy_path: str = None, plot_top: int = 20, force_refresh: bool = False):
    backtester = Backtester()
    plotter = PortfolioPlotter()
    
    # Phase 0: Clean plots directory only if force_refresh is True
    if force_refresh:
        print("Cleaning plots directory: plots...")
        for file in Path("plots").glob("*.svg"):
            try:
                file.unlink()
            except PermissionError:
                print(f"Skipping locked file: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")
    
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
    # Fetch data only once per ticker to speed up multiple strategy runs
    print(f"Churning {len(tickers)} tickers through {len(strategies)} strategies (Total {len(tickers)*len(strategies)} runs)...")
    
    # Pre-loading data or using a shared cache could speed this up, 
    # but the backtester already uses a CachedStrategyManager.
    
    for strat in strategies:
        print(f"Running Strategy: {strat['name']}")
        results = backtester.run_parallel_backtest(
            tickers, 
            strat['func'], 
            days=500, # Reduced from 730 to 500 (~2 years) for faster discovery
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
                    "Max DD (%)": res.get('max_drawdown_pct', 0),
                    "Trades": res.get('num_trades', 0),
                    "df": res.get('df')
                })
    
    # Convert to DataFrame and sort by Score
    summary_df = pd.DataFrame(all_results)
    if not summary_df.empty:
        summary_df['Quality Score'] = (
            summary_df['Return (%)'] * 
            (summary_df['Win Rate (%)'] / 100) * 
            (summary_df['Sharpe'] + 1) / 
            ((1 + summary_df['Trades'] / 100.0) * (1 + summary_df['Max DD (%)'] / 10.0))
        )
        summary_df = summary_df.sort_values(by="Quality Score", ascending=False)
        
        print("\nTop 10 Strategy/ETF Combinations:")
        # Display with 2 decimals, excluding the bulky 'df' column
        cols_to_print = [c for c in summary_df.columns if c != 'df']
        print(summary_df[cols_to_print].head(10).to_string(index=False, float_format=lambda x: "{:.2f}".format(x)))
        
        # Plot top performers
        if plot_top > 0:
            print(f"\nPlotting top {plot_top} performers...")
            # Use a fresh import to avoid any scoping issues inside the loop
            from ETF_screener.plotter import PortfolioPlotter as PFPlot
            p = PFPlot()
            
            # Prepare rich manifest data for the dashboard
            rich_manifest = []
            
            for i in range(min(plot_top, len(summary_df))):
                row = summary_df.iloc[i]
                ticker = row['Ticker']
                strategy_name = row['Strategy']
                # Find the original result to get the DF
                found = False
                for res in all_results:
                    if res.get('Ticker') == ticker and res.get('Strategy') == strategy_name and 'df' in res:
                        # Define the filename first
                        plot_filename = f"{ticker}_{strategy_name}_analysis.svg".lower()

                        # Ensure the directory exists
                        plot_path = Path("plots") / plot_filename
                        
                        # Phase 1: Skip if already exists (unless we want to force refresh)
                        if plot_path.exists() and not force_refresh:
                            print(f"Skipping {plot_filename} (Already exists)")
                        else:
                            print(f"Generating plot for {ticker} ({strategy_name})...")
                            p.plot_etf_analysis(res['df'].copy(), f"{ticker}_{strategy_name}")
                        
                        rich_manifest.append({
                            "file": plot_filename,
                            "ticker": str(ticker),
                            "strategy": str(strategy_name),
                            "return_pct": float(row['Return (%)']),
                            "win_rate": float(row['Win Rate (%)']),
                            "profit_factor": float(row['Profit Factor']),
                            "sharpe": float(row['Sharpe']),
                            "max_dd": float(row.get('Max DD (%)', 0)),
                            "trades": int(row['Trades'])
                        })
                        found = True
                        break
                if not found:
                    print(f"Warning: Could not find data to plot for {ticker} / {strategy_name}")
            
            # Save the rich manifest to help the SVG chooser
            try:
                import json
                manifest_path = Path("plots") / "plot_manifest.json"
                manifest_json = json.dumps(rich_manifest, indent=2)
                manifest_path.write_text(manifest_json)
                
                # Manually trigger the HTML update logic from plotter since we aren't calling plot_multiple_etfs
                target_ui = Path("plots/index.html")
                root_ui = Path("browser.html")
                if root_ui.exists():
                    import shutil
                    import re
                    shutil.copy2(root_ui, target_ui)
                    
                if target_ui.exists():
                    content = target_ui.read_text(encoding='utf-8')
                    # Use backticks for a multiline template string in JS
                    # This is much safer for JSON injection
                    pattern = r"const rawManifest = `.*?`;"
                    # Backslashes and backticks need to be escaped inside the template string
                    escaped_json = manifest_json.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
                    new_manifest_line = f"const rawManifest = `{escaped_json}`;"
                    
                    # Clean up any potential failed injections (single quote or multi-line)
                    content = re.sub(r"const rawManifest = '.*?';", new_manifest_line, content, flags=re.DOTALL)
                    content = re.sub(r"const rawManifest = `.*?`;", new_manifest_line, content, flags=re.DOTALL)
                    
                    target_ui.write_text(content, encoding='utf-8')
                    print(f"Injected {len(rich_manifest)} items into dashboard.")
            except Exception as e:
                print(f"Warning: Could not save rich manifest: {e}")
        
        # Save to CSV with 2 decimal precision (keeps full precision in memory/code)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"data/discovery_results_{timestamp}.csv"
        
        # Exclude the bulky 'df' column from CSV output for better compatibility with Spreadsheet tools
        cols_to_save = [c for c in summary_df.columns if c != 'df']
        
        # Keep only profitable results and limit to 100 rows for easier viewing
        clean_df = summary_df[summary_df['Return (%)'] > 0].head(100)
        
        clean_df[cols_to_save].to_csv(output_name, index=False, float_format="%.2f")
        
        # Also maintain a symlink-like constant copy for the PS1 script if needed
        clean_df[cols_to_save].to_csv("data/multi_strategy_results.csv", index=False, float_format="%.2f")
        
        # Also save to "custom_script_results.csv" for run_custom_backtest.ps1 compatibility
        if not strategy_path:
            clean_df[cols_to_save].to_csv("data/custom_script_results.csv", index=False, float_format="%.2f")
            
        print(f"\nFull results saved to {output_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", type=str, help="Entry condition (DSL)")
    parser.add_argument("--exit", type=str, help="Exit condition (DSL)")
    parser.add_argument("--filter", type=str, help="Ticker filter")
    parser.add_argument("--strat_path", type=str, help="Path to .dsl file or directory")
    parser.add_argument("--plot", type=int, default=20, help="Number of top performers to plot")
    parser.add_argument("--force", action="store_true", help="Force refresh (cleans plots/ folder)")
    args = parser.parse_args()
    
    churn_db(entry_script=args.entry, exit_script=args.exit, ticker_filter=args.filter, strategy_path=args.strat_path, plot_top=args.plot, force_refresh=args.force)

