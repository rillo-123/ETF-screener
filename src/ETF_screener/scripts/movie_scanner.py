from ETF_screener.config_loader import get_paths
import pandas as pd
import os
import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from ETF_screener.backtester import Backtester
from ETF_screener.plotter import PortfolioPlotter
from ETF_screener.strategy_manager import CachedStrategyManager
from ETF_screener.scripts.churn_strategies import (
    find_recent_entry_days,
    load_dsl_file,
)


def load_settings():
    settings_path = Path("config/scanner_settings.json")
    if settings_path.exists():
        with open(settings_path, "r") as f:
            settings = json.load(f)
            if "signal_window_days" not in settings and "scan_days" in settings:
                settings["signal_window_days"] = settings["scan_days"]
            return settings
    return {"scan_path": "strategies/", "signal_window_days": 50, "warmup_buffer": 20}


def load_blacklist():
    """Load blacklist from config/blacklist.json."""
    blacklist_path = Path("config/blacklist.json")
    if blacklist_path.exists():
        with open(blacklist_path, "r") as f:
            return json.load(f)
    return {}


def get_strategy_warmup_days(strategies):
    """Deduce the indicator warmup required by the strategy model."""
    max_period = 0
    for s in strategies:
        # Join entry, exit, trigger and filter to find all symbols
        full_script = f"{s['entry']} {s['exit']} {s.get('trigger') or ''} {s.get('filter') or ''}".lower()

        # 1. Special case for standard indicators with known periods
        if "macd" in full_script and max_period < 26:
            max_period = 26
        if "adx" in full_script and max_period < 14:
            max_period = 14
        if "st" in full_script or "supertrend" in full_script:
            if max_period < 10:
                max_period = 10

        # 2. Extract dynamic numbers from indicators like ema_50, rsi_14, etc.
        # This matches any number after an underscore
        periods = re.findall(r"_\d+", full_script)
        for p in periods:
            try:
                val = int(p.strip("_"))
                if val > max_period:
                    max_period = val
            except ValueError:
                continue

    # If no indicators found, use 14 as safety baseline.
    return max_period if max_period > 0 else 14


def resolve_strategy_signal_window(strategy: dict, configured_signal_days: int) -> int:
    """Return the signal window for a strategy.

    The DSL-provided MAX_DAYS is the source of truth for signal age when it is
    present. The configured scan window only acts as the default cap.
    """
    configured_signal_days = max(1, int(configured_signal_days or 1))
    strategy_max_days = strategy.get("max_days")
    if strategy_max_days is None:
        return configured_signal_days
    return min(configured_signal_days, int(strategy_max_days))


def movie_scanner(
    strat_path: str | None = None,
    ticker_filter: str | None = None,
    limit_days: int | None = None,
    open_result: bool = False,
    plot_limit: int = 0,
):
    settings = load_settings()
    blacklist = load_blacklist()

    # Use settings if arguments are not provided
    strat_path = strat_path or settings.get("scan_path")
    signal_days = int(
        limit_days
        if limit_days is not None
        else settings.get("signal_window_days", settings.get("scan_days", 50))
    )
    signal_days = max(1, signal_days)
    warmup_buffer = int(settings.get("warmup_buffer", 20))

    backtester = Backtester()
    shared_manager = CachedStrategyManager(backtester.db)
    plotter = PortfolioPlotter() if plot_limit != 0 else None

    # Track plotting count
    plotted_count = 0

    # 1. Load strategies
    strategies = []
    path = Path(strat_path)
    if path.is_file():
        res = load_dsl_file(path)
        if not res.get("has_valid_exit", False):
            print(f"Skipping {path.stem}: strategy has no exit criterion.")
            return
        strategies.append(
            {
                "name": path.stem,
                "entry": res["entry"],
                "exit": res["exit"],
                "trigger": res["trigger"],
                "filter": res["filter"],
                "max_days": res.get("max_days"),
            }
        )
    elif path.is_dir():
        for dsl_file in path.glob("*.dsl"):
            if "strat_cache" in dsl_file.parts:
                continue
            res = load_dsl_file(dsl_file)
            if not res.get("has_valid_exit", False):
                print(f"Skipping {dsl_file.stem}: strategy has no exit criterion.")
                continue
            strategies.append(
                {
                    "name": dsl_file.stem,
                    "entry": res["entry"],
                    "exit": res["exit"],
                    "trigger": res["trigger"],
                    "filter": res["filter"],
                    "max_days": res.get("max_days"),
                }
            )

    # Deduce the indicator warmup needed for the strategy model.
    strategy_warmup_days = get_strategy_warmup_days(strategies)
    effective_warmup_days = max(strategy_warmup_days, warmup_buffer)
    # Total data fetch = warmup + the signal window + a small safety pad.
    total_fetch_days = signal_days + effective_warmup_days + 10

    # 2. Get tickers
    conn = backtester.db._get_connection()
    query = "SELECT DISTINCT ticker FROM etf_data"
    if ticker_filter:
        if "%" in ticker_filter or "_" in ticker_filter:
            query += f' WHERE ticker LIKE "{ticker_filter}"'
        else:
            query += f' WHERE ticker LIKE "{ticker_filter}%"'
    all_tickers = pd.read_sql_query(query, conn)["ticker"].tolist()

    # Filter out blacklisted tickers
    tickers = [t for t in all_tickers if t.upper() not in blacklist]

    if len(tickers) < len(all_tickers):
        print(f"Filtered out {len(all_tickers) - len(tickers)} blacklisted tickers.")

    print("\n--- STRATEGY SCANNER (SIGNAL WINDOW) ---")
    print(f"Scanning {len(tickers)} tickers through {len(strategies)} strategies...")
    print(f"Signal window: {signal_days} days (DSL max_days default)")
    print(
        f"Strategy warmup: {strategy_warmup_days} days "
        f"(buffer: {warmup_buffer}, effective: {effective_warmup_days})\n"
    )
    print(f"{'TICKER':<10} | {'STRATEGY':<20} | {'DAYS AGO'}")
    print("-" * 50)

    found_any = False

    def process_ticker(ticker):
        results = []

        # Load ribbon settings to ensure all indicators used in ribbons are calculated
        ribbon_indicators = []
        try:
            with open("config/ribbon_settings.json", "r") as f:
                ribbon_data = json.load(f)
                for ribbon in ribbon_data.get("ribbons", []):
                    for layer in ribbon.get("layers", []):
                        cond = layer.get("condition", "").lower()
                        # Simple regex to find words that look like indicators
                        for word in re.findall(r"[a-z][a-z_0-9]*", cond):
                            if word not in [
                                "and",
                                "or",
                                "close",
                                "open",
                                "high",
                                "low",
                                "volume",
                                "date",
                            ]:
                                ribbon_indicators.append(word)
        except Exception:
            pass

        for strat in strategies:
            strategy_window = resolve_strategy_signal_window(strat, signal_days)

            res = backtester.run_strategy(
                ticker=ticker,
                strategy_func=backtester.scripted_strategy,
                days=total_fetch_days,
                strategy_kwargs={
                    "entry_script": strat["entry"],
                    "exit_script": strat["exit"],
                    "manager": shared_manager,
                    "additional_indicators": ribbon_indicators,
                },
            )

            if res and "df" in res:
                df = res["df"]
                if df.empty:
                    continue

                # REJECTION 1: Data must be fresh.
                # If the latest date is older than 4 calendar days, ignore this ticker entirely.
                # This prevents "1 days ago (2026-03-04)" when today is March 21.
                latest_date = pd.to_datetime(df.iloc[-1]["Date"])
                days_stale = (datetime.now() - latest_date).days
                if days_stale > 4:
                    continue

                recent_days = find_recent_entry_days(
                    df,
                    strat,
                    max_days=int(strategy_window),
                )
                if recent_days is None:
                    continue

                idx = len(df) - 1 - int(recent_days)
                if idx < 0:
                    continue

                date_str = df.iloc[idx]["Date"].strftime("%Y-%m-%d")
                days_str = (
                    "TODAY" if int(recent_days) == 0 else f"{int(recent_days)} days ago"
                )

                # Store as tuple (days_ago, ticker, line_text, df) for easy sorting and plotting
                results.append(
                    (
                        int(recent_days),
                        ticker,
                        f"{ticker:<10} | {strat['name']:<20} | {days_str:<12} ({date_str})",
                        df,
                    )
                )
        return results

    # 3. Process with ThreadPool for speed
    max_workers = os.cpu_count() or 4
    all_hits = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Wrap with tqdm for progress
        futures = list(
            tqdm(
                executor.map(process_ticker, tickers),
                total=len(tickers),
                desc="Parallel Scan",
                unit="ticker",
            )
        )

        for result_list in futures:
            for hit_tuple in result_list:
                all_hits.append(hit_tuple)
                found_any = True

    # 4. Sort by days ago (ascending) then ticker
    all_hits.sort(key=lambda x: (x[0], x[1]))

    # 5. Output Results and Plot
    csv_rows = []

    # NEW: Clean out old plots before generating new ones
    if plotter and plot_limit != 0:
        plot_dir = Path("plots")
        if plot_dir.exists():
            for f in plot_dir.glob("*.png"):
                try:
                    f.unlink()
                except Exception:
                    pass
            for f in plot_dir.glob("*.svg"):
                try:
                    f.unlink()
                except Exception:
                    pass
            print("Cleaned up old plots.")

    # Print excerpt (top 10) to terminal and handle plotting
    for i, (days_ago, ticker, line, df_hit) in enumerate(all_hits):
        if i < 10:
            print(line)
        elif i == 10:
            print(f"... and {len(all_hits) - 10} more (see CSV for full results)")

        # Plotting logic (sequential now that we've found the hits)
        if plotter and (plot_limit == -1 or i < plot_limit):
            try:
                plotter.plot_etf_analysis(df_hit, ticker)
                plotted_count += 1
            except Exception as pe:
                print(f"Error plotting {ticker}: {pe}")

        # Prepare CSV data
        date_match = re.search(r"\((\d{4}-\d{2}-\d{2})\)", line)
        date_str = date_match.group(1) if date_match else ""

        parts = [p.strip() for p in line.split("|")]
        strat_name = parts[1]

        csv_rows.append(
            {
                "Ticker": ticker,
                "Strategy": strat_name,
                "DaysAgo": days_ago,
                "Date": date_str,
            }
        )

    if plotter and plotted_count > 0:
        print(f"\nGenerated {plotted_count} plots.")

    if csv_rows:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(
            f"{get_paths()['data']['movie_scans']}/movie_scan_{timestamp}.csv"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(csv_rows).to_csv(output_file, index=False)
        print(f"\nFull results saved to {output_file}")

        # Keep only the 3 most recent movie scan files
        try:
            history_files = sorted(
                Path(get_paths()["data"]["movie_scans"]).glob("movie_scan_*.csv"),
                key=os.path.getmtime,
                reverse=True,
            )
            if len(history_files) > 3:
                for old_file in history_files[3:]:
                    old_file.unlink()
                print(f"Cleaned up {len(history_files) - 3} old scan CSV files.")
        except Exception as e:
            print(f"Warning: Could not cleanup old CSVs: {e}")

        if open_result:
            os.startfile(output_file.absolute())  # type: ignore[attr-defined]

    if not found_any:
        print("No signals found in the signal window.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strat_path", type=str, help="Path to strategy file or directory"
    )
    parser.add_argument("--filter", type=str, help="Ticker filter")
    parser.add_argument(
        "--signal-window-days",
        "--lookback",
        dest="signal_days",
        type=int,
        help="How far back from today to search for the signal transition",
    )
    parser.add_argument("--open", action="store_true", help="Open the result CSV")
    parser.add_argument(
        "--plot",
        type=int,
        default=0,
        help="Generate plots for scan hits (number or -1 for all)",
    )
    args = parser.parse_args()

    movie_scanner(args.strat_path, args.filter, args.signal_days, args.open, args.plot)
