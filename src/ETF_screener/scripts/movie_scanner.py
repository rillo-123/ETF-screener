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
from ETF_screener.scripts.churn_strategies import load_dsl_file


def load_settings():
    settings_path = Path("config/scanner_settings.json")
    if settings_path.exists():
        with open(settings_path, "r") as f:
            return json.load(f)
    return {"scan_path": "strategies/", "scan_days": 50}


def load_blacklist():
    """Load blacklist from config/blacklist.json."""
    blacklist_path = Path("config/blacklist.json")
    if blacklist_path.exists():
        with open(blacklist_path, "r") as f:
            return json.load(f)
    return {}


def get_max_lookback(strategies):
    """Deduce the required data lookback from strategy indicators."""
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

    # If no indicators found, use 14 as safety baseline
    return max_period if max_period > 0 else 14


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
    limit_days = limit_days or settings.get("scan_days")

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
        strategies.append(
            {
                "name": path.stem,
                "entry": res["entry"],
                "exit": res["exit"],
                "trigger": res["trigger"],
                "filter": res["filter"],
            }
        )
    elif path.is_dir():
        for dsl_file in path.glob("*.dsl"):
            if "strat_cache" in dsl_file.parts:
                continue
            res = load_dsl_file(dsl_file)
            strategies.append(
                {
                    "name": dsl_file.stem,
                    "entry": res["entry"],
                    "exit": res["exit"],
                    "trigger": res["trigger"],
                    "filter": res["filter"],
                }
            )

    # Deduce the lookback needed for the indicator calculations
    strategy_lookback = get_max_lookback(strategies)
    # Total data fetch = warmup + the scan window
    total_fetch_days = strategy_lookback + limit_days + 10

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

    print("\n--- STRATEGY SCANNER (REVERSE) ---")
    print(f"Scanning {len(tickers)} tickers through {len(strategies)} strategies...")
    print(
        f"Lookback window: {limit_days} days (Calculated Warmup: {strategy_lookback} days)\n"
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
            # Task: Separation of Trigger and Filter.
            # If a trigger/filter pair exists, use ONLY the trigger for the backtester's entry.
            # This ensures 'signal == 1' represents the EXACT day of the event.
            # The 'filter' survival check later handles the trend/validation.
            active_trigger = (
                strat.get("trigger") if strat.get("trigger") else strat["entry"]
            )

            res = backtester.run_strategy(
                ticker=ticker,
                strategy_func=backtester.scripted_strategy,
                days=total_fetch_days,
                strategy_kwargs={
                    "entry_script": active_trigger,
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

                # Check backwards from the end for the first "signal" == 1 (Entry)
                for i in range(limit_days):
                    idx = len(df) - 1 - i
                    if idx < 0:
                        break

                    signal = df.iloc[idx].get("signal", 0)
                    if signal == 1:
                        # REJECTION 2: Signal must still be in an UPTREND if looking at historical entries.
                        # Check the latest bar to see if it would have been disqualified (EXIT condition).
                        # We use the same 'df' which already has the signal column computed.
                        # If the latest bar has signal == -1, or if we want to be stricter,
                        # we can check if the EXIT condition is currently true.
                        latest_bar = df.iloc[-1]

                        # Use the 'signal' column as a proxy for the strategy's own exit logic.
                        # If signal is -1 TODAY, it means the EXIT condition triggered TODAY.
                        # However, the user specifically mentioned "Price < EMA 50" (Down Trend).
                        # Since the strategy defines EXIT as 'cross_down(macd, macd_signal) or close < ema_50',
                        # a signal of -1 on the latest bar would catch this.
                        # But wait: what if the signal is 0 (neutral) but the trend is still broke?
                        # We should check if the LATEST state is 'Position=0' or 'Exited'.

                        # Accurate check: Is the position currently 0 if we were to walk the signals?
                        # Or simpler: Is the EXIT condition currently true on the LATEST bar?
                        # In backtester.scripted_strategy, b_r is the exit condition.
                        # It's harder to re-eval the DSL here, so we look at the 'signal' column.

                        # 3. EXCLUSION: If signal was 1 N days ago, but -1 since then, it's dead.
                        # However, we only kill it if the exit happens AFTER the window.
                        recent_exits = df.iloc[idx + 1 :]["signal"].tolist()
                        if -1 in recent_exits:
                            # If we are looking for historically successful entries, maybe we
                            # want to see them even if they eventually failed? No, this is a
                            # "movie scanner" for CURRENTLY active signals.
                            continue

                        # 4. SURVIVAL LOGIC: If the strategy has a FILTER block, it MUST be true
                        # for EVERY SINGLE DAY from the trigger (idx) until today.
                        if strat.get("filter"):
                            # Prepare a slice of the dataframe from the trigger day until the latest bar
                            df_slice = df.iloc[idx:].copy()

                            try:
                                # Process the filter string to be pandas-compatible (same as backtester)
                                def p(s):
                                    # Handle c_up/down
                                    s = re.sub(
                                        r"cross_up\(([^,]+),\s*([^)]+)\)",
                                        r"(\1 > \2 and \1_d1 <= \2_d1)",
                                        s,
                                    )
                                    s = re.sub(
                                        r"cross_down\(([^,]+),\s*([^)]+)\)",
                                        r"(\1 < \2 and \1_d1 >= \2_d1)",
                                        s,
                                    )

                                    # Handle d[N]
                                    def d_sub(m):
                                        return f"{m.group(1)}_d{m.group(2)}"

                                    s = re.sub(
                                        r"([a-z_][a-z0-9_]*)\.d\[(\d+)\]", d_sub, s
                                    )

                                    # Handle was_true
                                    def shift_cond(m):
                                        c = m.group(1)
                                        n = int(m.group(2))
                                        shifted = " or ".join(
                                            [f"{c}_d{i}" for i in range(1, n + 1)]
                                        )
                                        return f"({shifted})"

                                    s = re.sub(
                                        r"was_true\(([^,]+),\s*(\d+)\)", shift_cond, s
                                    )

                                    # Use 'and'/'or' keywords for pandas.eval() to avoid numexpr issues.
                                    # pandas.eval() expects bitwise (&, |) or it fails with 'BoolOp' error if using engine='python'.
                                    # Actually, engine='python' should support 'and' if it's a simple python eval,
                                    # but usually it's safer to use bitwise or simple string replacement.
                                    return (
                                        s.lower()
                                        .replace(" and ", " & ")
                                        .replace(" or ", " | ")
                                        .replace("-gt", ">")
                                        .replace("-lt", "<")
                                        .replace("-eq", "==")
                                        .replace("-ge", ">=")
                                        .replace("-le", "<=")
                                    )

                                f_s = p(strat["filter"])

                                # Map columns to match the evaluation (lowercase)
                                df_slice.columns = [c.lower() for c in df_slice.columns]

                                # Use engine='python', parser='python' to match backtester improvements
                                filter_mask = df_slice.eval(
                                    f_s, engine="python", parser="python"
                                )

                                # If the filter was False at any point in the "survival" window, disqualify.
                                if not filter_mask.all():
                                    continue
                            except Exception:
                                # Fallback: if evaluation fails, we keep the ticker but log a warning if needed
                                pass

                        # 5. EXCLUSION: The LATEST bar (now) MUST satisfy the DSL's ENTRY-level trend/stability.
                        # This prevents tickers that entered validly 3 days ago but are currently DOWN (Price < EMA 50)
                        # or have lost momentum (MACD < Signal).
                        latest_bar = df.iloc[-1]

                        # Use b_em (entry mask) to verify if entry conditions are currently TRUE.
                        # CRITICAL: For strategies with crossovers (cross_up), b_em will only be True
                        # on the day of the crossover. To allow entry signals from 1-5 days ago,
                        # we must check if the POSITION is still OPEN and the trend is still UP,
                        # rather than requiring a NEW crossover today.

                        # Is the position currently in an "OPEN" state?
                        # Since we check -1 since the signal above, we just need to verify
                        # that the LATEST bar doesn't violate the EXIT condition.
                        if "b_r" in res:
                            # If the EXIT condition (b_r) is TRUE today, disqualify.
                            if res["b_r"].iloc[-1]:
                                continue

                        # Also, regardless of the crossover, we firmly enforce the Trend/MACD stability:
                        price_col = "Close" if "Close" in latest_bar else "close"

                        # (A) 2% safety buffer for EMA 50 must still be respected today
                        # BUT: only if the strategy doesn't already have its own FILTER logic!
                        # If a strategy defines its own survivability, we trust it.
                        if not strat.get("filter"):
                            if "ema_50" in df.columns:
                                if latest_bar[price_col] < (
                                    latest_bar["ema_50"] * 1.02
                                ):
                                    continue

                        # (B) MACD must still be ABOVE the Signal line today (No "Red over Blue")
                        if "macd" in df.columns and "macd_signal" in df.columns:
                            # Use a tiny buffer to avoid precision issues
                            if latest_bar["macd"] < (
                                latest_bar["macd_signal"] - 0.00001
                            ):
                                continue

                        # (C) DEBUG: Extra check to see why tickers might be slipping through
                        # if ticker == "HYCN.DE":
                        #     print(f"DEBUG HYCN.DE: macd={latest_bar['macd']}, signal={latest_bar['macd_signal']}")

                        # If we passed all rejections, record this hit.
                        date_str = df.iloc[idx]["Date"].strftime("%Y-%m-%d")
                        days_str = "TODAY" if i == 0 else f"{i} days ago"

                        # Store as tuple (days_ago, ticker, line_text, df) for easy sorting and plotting
                        results.append(
                            (
                                i,
                                ticker,
                                f"{ticker:<10} | {strat['name']:<20} | {days_str:<12} ({date_str})",
                                df,
                            )
                        )
                        break
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
        output_file = Path(f"data/movie_scan_{timestamp}.csv")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(csv_rows).to_csv(output_file, index=False)
        print(f"\nFull results saved to {output_file}")

        # Keep only the 3 most recent movie scan files
        try:
            history_files = sorted(
                Path("data").glob("movie_scan_*.csv"),
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
            os.startfile(output_file.absolute())

    if not found_any:
        print("No signals found in the specified window.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strat_path", type=str, help="Path to strategy file or directory"
    )
    parser.add_argument("--filter", type=str, help="Ticker filter")
    parser.add_argument(
        "--lookback", type=int, help="How many days of data to analyze/lookback"
    )
    parser.add_argument("--open", action="store_true", help="Open the result CSV")
    parser.add_argument(
        "--plot",
        type=int,
        default=0,
        help="Generate plots for scan hits (number or -1 for all)",
    )
    args = parser.parse_args()

    movie_scanner(args.strat_path, args.filter, args.lookback, args.open, args.plot)
