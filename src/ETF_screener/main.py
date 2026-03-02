"""Entry point for ETF screener CLI."""



import argparse

import io

import json

import sys

from pathlib import Path

from typing import Optional



# Fix CSV handling and Unicode output on Windows

if sys.stdout.encoding and sys.stdout.encoding.lower() == 'utf-8':

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

else:

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=sys.stdout.encoding or 'utf-8', errors='replace')



import pandas as pd

from tqdm import tqdm



from ETF_screener.data_fetcher import FinnhubFetcher

from ETF_screener.database import ETFDatabase

from ETF_screener.etf_discovery import ETFDiscovery

from ETF_screener.indicators import add_indicators, calculate_consecutive_streak

from ETF_screener.hotlist import generate_hotlist

from ETF_screener.plotter import PortfolioPlotter

from ETF_screener.screener import ETFScreener

from ETF_screener.storage import ParquetStorage

from ETF_screener.xetra_extractor import XETRETFExtractor

from ETF_screener.yfinance_fetcher import YFinanceFetcher





def parse_volume(volume_str: str) -> int:

    """

    Parse volume string with K/M suffixes.



    Examples:

        "100K" -> 100000

        "1.5M" -> 1500000

        "50000" -> 50000



    Args:

        volume_str: Volume string with optional K/M suffix



    Returns:

        Volume as integer



    Raises:

        ValueError: If format is invalid

    """

    volume_str = volume_str.strip().upper()

    

    if volume_str.endswith("K"):

        try:

            return int(float(volume_str[:-1]) * 1_000)

        except ValueError:

            raise ValueError(f"Invalid volume format: {volume_str}")

    

    elif volume_str.endswith("M"):

        try:

            return int(float(volume_str[:-1]) * 1_000_000)

        except ValueError:

            raise ValueError(f"Invalid volume format: {volume_str}")

    

    else:

        try:

            return int(volume_str)

        except ValueError:

            raise ValueError(f"Invalid volume format: {volume_str}")





def evaluate_condition(value: float, operator: str, threshold: float) -> bool:

    """

    Evaluate a numeric condition.



    Args:

        value: Value to check

        operator: Operator ('gt', 'gte', 'lt', 'lte', 'eq', 'ne')

        threshold: Threshold value to compare against



    Returns:

        True if condition is met, False otherwise

    """

    if pd.isna(value):

        return False

    

    value = float(value)

    threshold = float(threshold)

    

    if operator == "gt":

        return value > threshold

    elif operator == "gte":

        return value >= threshold

    elif operator == "lt":

        return value < threshold

    elif operator == "lte":

        return value <= threshold

    elif operator == "eq":

        return abs(value - threshold) < 0.0001  # Float equality with tolerance

    elif operator == "ne":

        return abs(value - threshold) >= 0.0001

    else:

        return False





def fetch_and_analyze(

    symbols: list[str],

    days: int = 365,

    api_key: Optional[str] = None,

    data_dir: str = "data",

    plot_dir: str = "plots",

    use_db: bool = True,

    source: str = "yfinance",

) -> None:

    """

    Fetch ETF data, calculate indicators, save to storage, and generate plots.



    Args:

        symbols: List of ETF symbols to fetch

        days: Number of days of historical data

        api_key: Finnhub API key (only for Finnhub source)

        data_dir: Directory to store parquet files

        plot_dir: Directory to store plots

        use_db: Store data in SQLite database

        source: Data source ('yfinance' or 'finnhub')

    """

    try:

        # Initialize fetcher based on source

        if source.lower() == "finnhub":

            print("Initializing Finnhub fetcher...")

            fetcher = FinnhubFetcher(api_key=api_key)

        else:

            print("Initializing Yahoo Finance fetcher...")

            fetcher = YFinanceFetcher()



        # Fetch data for all symbols

        print(f"Fetching data for {len(symbols)} ETFs (past {days} days)...")

        etf_data = fetcher.fetch_multiple_etfs(symbols, days=days)



        if not etf_data:

            print("No data fetched. Exiting.")

            return



        # Add indicators

        print("Calculating indicators (EMA 50, Supertrend)...")

        for symbol, df in etf_data.items():

            etf_data[symbol] = add_indicators(df)



        # Save to database if enabled

        if use_db:

            print("Storing data in SQLite database...")

            db = ETFDatabase()

            for symbol, df in etf_data.items():

                db.insert_dataframe(df, symbol)

            db.close()



        # Save to parquet

        print("Saving data to parquet files...")

        storage = ParquetStorage(data_dir=data_dir)

        storage.save_multiple_etfs(etf_data)



        # Generate plots

        print("Generating analysis plots...")

        plotter = PortfolioPlotter(output_dir=plot_dir)

        plotter.plot_multiple_etfs(etf_data)



        print("\n[OK] Analysis complete!")

        print(f"  Data saved to: {data_dir}")

        print(f"  Plots saved to: {plot_dir}")



        # Print summary

        print("\nSignal Summary:")

        for symbol, df in etf_data.items():

            buy_signals = (df["Signal"] == 1).sum()

            sell_signals = (df["Signal"] == -1).sum()

            latest_price = df["Close"].iloc[-1]

            latest_ema = df["EMA_50"].iloc[-1]



            print(f"\n{symbol}:")

            print(f"  Latest Price: {latest_price:.2f}")

            print(f"  EMA 50: {latest_ema:.2f}")

            print(f"  Buy Signals: {buy_signals}")

            print(f"  Sell Signals: {sell_signals}")



    except Exception as e:

        print(f"Error: {str(e)}", file=sys.stderr)

        sys.exit(1)





def list_saved_etfs(data_dir: str = "data") -> None:
    """
    List all saved ETFs in parquet storage and show database statistics.

    Args:
        data_dir: Directory containing parquet files
    """
    # Show Database Stats first
    try:
        db = ETFDatabase()
        db_tickers = db.get_tickers()
        print(f"\n[DATABASE] Database Statistics:")
        print(f"  - Total Tickers: {len(db_tickers)}")
        print(f"  - DB Path: {db.db_path}\n")
        db.close()
    except Exception as e:
        print(f"[ERROR] Could not read database stats: {e}")

    # Show Parquet Files (Legacy format)
    storage = ParquetStorage(data_dir=data_dir)
    etfs = storage.list_available_etfs()

    if etfs:
        print(f"Available Parquet Files in {data_dir}:")
        for symbol in etfs:
            df = storage.load_etf_data(symbol)
            if df is not None and not df.empty:
                print(f"  {symbol}: {len(df)} rows, {df['Date'].min().date()} to {df['Date'].max().date()}")
    else:
        print(f"No ETF Parquet files found in {data_dir}")





def screen_etfs(

    symbols: Optional[list[str]] = None,

    nof_etfs: Optional[int] = None,

    min_avg_volume: int = 10_000_000,

    days: int = 10,

    days_to_keep: int = 365,

    api_key: Optional[str] = None,

    format_name: str = "default",

    data_dir: str = "data",

    filter_swing: bool = False,

    swing_pullback: float = 2.0,

    supertrend_filter: Optional[str] = None,

    timeframe: str = "1D",

    st_period: int = 10,

    st_multiplier: float = 3.0,

    red_streak_min: int = 0,

    conditions: Optional[dict] = None,

) -> None:

    """

    Screen ETFs by volume criteria. Fetches from online if not in cache (DB).

    Stores fetched data in DB as cache for future runs. Returns ALL matching ETFs.



    Args:

        symbols: List of ETF symbols to screen (if None, screens all from etfs.json)

        nof_etfs: Ignored - returns ALL ETFs matching criteria

        min_avg_volume: Minimum average volume in shares

        days: Number of days to analyze

        days_to_keep: Unused - data persisted in DB as cache

        api_key: Finnhub API key

        format_name: Output format (default, compact, detailed, swing)

        data_dir: Directory containing etfs.json file

        filter_swing: Filter for swing setups (price dipped to EMA50 in uptrend)

        swing_pullback: Minimum pullback % for swing filter

        supertrend_filter: Filter by Supertrend color ('green': price > supertrend, 'red': price < supertrend)

        timeframe: Timeframe for Supertrend ("1D" or "1W", default "1D")

        st_period: Supertrend ATR period (default 10)

        st_multiplier: Supertrend multiplier (default 3.0)

        red_streak_min: Minimum consecutive RED days to include (0 = all, 10+ = likely reversal)

        conditions: Dict of conditional filters {field: [(operator, threshold), ...]}

    """

    try:

        db = ETFDatabase()

        

        if symbols:

            # Screen specific symbols

            print(f"Processing {len(symbols)} symbols (minimum 50 days for accurate EMA50)...\n")

            to_fetch = []

            

            for symbol in symbols:

                if not db.ticker_exists(symbol):

                    to_fetch.append(symbol)

                else:

                    print(f"  [OK] {symbol} found in cache")

            

            if to_fetch:

                print(f"\nFetching {len(to_fetch)} missing from Yahoo Finance...")

                fetcher = YFinanceFetcher()

                etf_data = fetcher.fetch_multiple_etfs(to_fetch, days=max(50, days))

                

                if etf_data:

                    print("Calculating indicators...")

                    for symbol, df in etf_data.items():

                        etf_data[symbol] = add_indicators(df)

                    

                    print("Storing in cache...")

                    for symbol, df in etf_data.items():

                        db.insert_dataframe(df, symbol)

                        print(f"  [OK] {symbol} cached")

        else:

            # Load all ETFs from config/etfs.json (preferred) or data/etfs.json (fallback)
            etfs_file = Path("config/etfs.json")
            if not etfs_file.exists():
                etfs_file = Path(data_dir) / "etfs.json"

            if not etfs_file.exists():

                print(f"Error: {etfs_file} not found. Run 'etfs discover' first.")

                db.close()

                return

            

            try:

                with open(etfs_file) as f:

                    etfs_data = json.load(f)

                    available_symbols = list(etfs_data.keys())

                

                print(f"Scanning {len(available_symbols)} ETFs from etfs.json...")

                

                # Check which are already cached

                to_fetch = []

                cached_count = 0

                for symbol in available_symbols:

                    if not db.ticker_exists(symbol):

                        to_fetch.append(symbol)

                    else:

                        cached_count += 1

                

                print(f"  Found in cache: {cached_count}")

                print(f"  Need to fetch: {len(to_fetch)}")

                

                if to_fetch:

                    print(f"\nFetching {len(to_fetch)} ETFs (minimum 50 days for accurate EMA50)...")

                    fetcher = YFinanceFetcher()

                    etf_data = fetcher.fetch_multiple_etfs(to_fetch, days=max(50, days))

                    

                    if etf_data:

                        print(f"\nCalculating indicators for {len(etf_data)} ETFs...")

                        for symbol, df in etf_data.items():

                            etf_data[symbol] = add_indicators(df)

                        

                        print("Storing in cache...")

                        for symbol, df in etf_data.items():

                            db.insert_dataframe(df, symbol)

                        print(f"  [OK] Cached {len(etf_data)} new ETFs\n")

                    

            except Exception as e:

                print(f"Error: {e}")

                db.close()

                return

        

        screener = ETFScreener(db=db, api_key=api_key)

        print(f"Screening ALL ETFs (last {days} days, avg volume >= {min_avg_volume:,})...\n")



        # Return ALL results matching criteria (no limit)

        results = screener.screen_by_volume(

            min_days=days,

            min_avg_volume=min_avg_volume,

            max_results=None,

            fetch_missing=False,

        )



        # Apply swing filter if requested

        if filter_swing and not results.empty:

            print(f"Filtering for swing setups (pullback >= {swing_pullback}%, price > Supertrend)...\n")

            results = screener.filter_swing_setups(

                results,

                db=db,

                min_pullback=swing_pullback,

                max_distance_from_ema=5.0,

                require_green_supertrend=True,

                st_period=st_period,

                st_multiplier=st_multiplier,

                timeframe=timeframe,

            )



        # Apply supertrend color filter if requested
        if supertrend_filter and not results.empty:
            filtered_results = []
            updates_to_cache = {}
            
            # Identify if we can use cached values
            is_default_params = (timeframe == "1D" and st_period == 10 and st_multiplier == 3.0)
            
            for _, row in tqdm(results.iterrows(), total=len(results), desc="Checking Supertrend"):
                ticker = row["ticker"]
                try:
                    # Check if Supertrend is already in results (from db.query_by_volume)
                    # and if we are using default parameters that match the cache
                    if is_default_params and "supertrend" in row and pd.notna(row["supertrend"]):
                        latest_close = row["latest_price"]
                        latest_st = row["supertrend"]
                        
                        # Apply filter quickly using cached values
                        matches = False
                        if supertrend_filter == "green" and latest_close > latest_st:
                            matches = True
                        elif supertrend_filter == "red" and latest_close <= latest_st:
                            matches = True
                            
                        if matches:
                            # We still need the streak, which requires historical data
                            # Fast Streak: only need a short lookback if we already trust the cache
                            hist_df = db.get_ticker_data(ticker, days=30) 
                            if not hist_df.empty:
                                streak_days, streak_status = calculate_consecutive_streak(hist_df)
                                
                                # If red filter, check extra conditions
                                if supertrend_filter == "red" and streak_days < red_streak_min:
                                    continue
                                    
                                row_copy = row.copy()
                                row_copy["streak_days"] = streak_days
                                row_copy["streak_status"] = streak_status
                                filtered_results.append(row_copy)
                            continue
                        else:
                            # If it doesn't match the filter based on cache, skip immediately
                            continue

                    # Fallback to full fetch and calculation if parameters differ or data missing
                    # Ensure we have enough data for Indicators (EMA 50 requires at least 50 bars)
                    lookback_days = 200 if timeframe == "1W" else 150
                    hist_df = db.get_ticker_data(ticker, days=lookback_days)
                    if hist_df.empty or len(hist_df) < 10:
                        continue
                    
                    # Recalculate with new parameters and timeframe
                    hist_df = add_indicators(hist_df, st_period=st_period, st_multiplier=st_multiplier, timeframe=timeframe)
                    latest = hist_df.iloc[-1]
                    
                    # Store in update queue
                    if timeframe == "1D" and st_period == 10 and st_multiplier == 3.0:
                        updates_to_cache[ticker] = hist_df
                    
                    # Calculate RED/GREEN streak
                    streak_days, streak_status = calculate_consecutive_streak(hist_df)
                    
                    # Apply filter
                    if supertrend_filter == "green" and latest["Close"] > latest["Supertrend"]:
                        row_copy = row.copy()
                        row_copy["streak_days"] = streak_days
                        row_copy["streak_status"] = streak_status
                        filtered_results.append(row_copy)

                    elif supertrend_filter == "red" and latest["Close"] <= latest["Supertrend"]:
                        row_copy = row.copy()
                        row_copy["streak_days"] = streak_days
                        row_copy["streak_status"] = streak_status
                        # Filter by red streak if specified
                        if streak_days >= red_streak_min:
                            filtered_results.append(row_copy)
                        
                except Exception:
                    continue
            
            # Batch update the database for any newly calculated indicators
            if updates_to_cache:
                print(f"Updating cache for {len(updates_to_cache)} ETFs...")
                for t, df_to_cache in updates_to_cache.items():
                    db.insert_dataframe(df_to_cache, t)
            
            results = pd.DataFrame(filtered_results) if filtered_results else pd.DataFrame()

            

            if supertrend_filter == "green":

                print(f"Filtering for GREEN Supertrend ({timeframe}, mult={st_multiplier})...\n")

            elif supertrend_filter == "red":

                if red_streak_min > 0:

                    print(f"Filtering for RED Supertrend ({timeframe}, mult={st_multiplier}) with RED streak >= {red_streak_min} days...\n")

                else:

                    print(f"Filtering for RED Supertrend ({timeframe}, mult={st_multiplier})...\n")



        # Apply conditional filters if specified

        if conditions and not results.empty:

            for field, ops_list in conditions.items():

                if not ops_list:

                    continue

                

                filtered_results = []

                for _, row in tqdm(results.iterrows(), total=len(results), desc=f"Filtering {field}"):

                    # If indicators aren't already in the row (from supertrend filter), fetch them

                    if field not in row or pd.isna(row[field]):

                        try:

                            ticker = row["ticker"]

                            hist_df = db.get_ticker_data(ticker, days=90)

                            if hist_df.empty or len(hist_df) < 10:

                                continue

                            hist_df = add_indicators(hist_df, st_period=st_period, st_multiplier=st_multiplier, timeframe=timeframe)

                            latest = hist_df.iloc[-1]

                            row = row.copy()

                            row["close"] = latest["Close"]

                            row["ema"] = latest["EMA_50"]

                            row["supertrend"] = latest["Supertrend"]

                            # Check if pullback_pct exists (from swing filter)

                            if "Pullback_Pct" in latest:

                                row["pullback"] = latest["Pullback_Pct"]

                            if "avg_vol" in row or "Avg Vol" in row:

                                row["volume"] = row.get("avg_vol", row.get("Avg Vol", 0))

                        except Exception:

                            continue

                    

                    # Apply all conditions for this field

                    passes_all = True

                    for operator, threshold in ops_list:

                        # Map field names to available columns (case-insensitive, with fallbacks)

                        field_value = None

                        if field == "close":

                            field_value = row.get("close") or row.get("Close")

                        elif field == "ema":

                            field_value = row.get("ema") or row.get("EMA_50") or row.get("ema_50")

                        elif field == "pullback":

                            field_value = row.get("pullback") or row.get("Pullback_Pct")

                        elif field == "volume":

                            field_value = row.get("volume") or row.get("Avg Vol") or row.get("avg_vol") or row.get("avg_volume")

                        

                        if field_value is None or not evaluate_condition(field_value, operator, threshold):

                            passes_all = False

                            break

                    

                    if passes_all:

                        filtered_results.append(row)

                

                results = pd.DataFrame(filtered_results) if filtered_results else pd.DataFrame()

                

                # Print what was filtered

                ops_str = " and ".join([f"{op} {val}" for op, val in ops_list])

                print(f"Filtering {field} ({ops_str})...\n")



        screener.print_results(results, format_name=format_name)



        if results.empty:

            print("\n[WARNING] No ETFs matched the criteria. Try lower --aVol threshold.")



        db.close()



    except Exception as e:

        print(f"Error: {str(e)}", file=sys.stderr)

        sys.exit(1)





def discover_etfs(

    tickers: Optional[list[str]] = None,

    etfs_file: str = "config/etfs.json",

    blacklist_file: str = "config/blacklist.json",

) -> None:

    """

    Discover and validate ETF tickers on Yahoo Finance.



    Args:

        tickers: List of tickers to validate. If None, uses predefined list.

        etfs_file: JSON file to save working ETFs

        blacklist_file: JSON file to save blacklisted ETFs

    """

    try:

        discovery = ETFDiscovery(etfs_file=etfs_file, blacklist_file=blacklist_file)

        results = discovery.discover(tickers=tickers, verbose=True)



        print("\n[DATA] Discovery Summary:")

        print(f"  Working: {len(results['working'])} ETFs")

        print(f"  Blacklisted: {len(results['blacklisted'])} ETFs")

        

        if results['working']:

            print("\n[OK] Working ETFs:")

            for ticker in sorted(results['working'].keys()):

                print(f"  - {ticker}")

        

        if results['blacklisted']:

            print("\n[X] Blacklisted ETFs:")

            for ticker in sorted(results['blacklisted'].keys()):

                print(f"  - {ticker}")



    except Exception as e:

        print(f"Error: {str(e)}", file=sys.stderr)

        sys.exit(1)





def extract_xetra_etfs(

    csv_file: str = "reference/t7-xetr-allTradableInstruments.csv",

    etfs_file: str = "config/etfs.json",

    blacklist_file: str = "config/blacklist.json",

) -> None:

    """

    Extract and validate XETRA ETF tickers from Deutsche Brse CSV.



    Args:

        csv_file: Path to Deutsche Brse CSV file

        etfs_file: JSON file to save working ETFs

        blacklist_file: JSON file to save blacklisted ETFs

    """

    try:

        extractor = XETRETFExtractor(

            csv_file=csv_file,

            etfs_file=etfs_file,

            blacklist_file=blacklist_file,

        )

        results = extractor.discover_and_validate(verbose=True)



        print("\n[DATA] Extraction Summary:")

        print(f"  CSV File: {csv_file}")

        print(f"  Working: {len(results['working'])} ETFs")

        print(f"  Blacklisted: {len(results['blacklisted'])} ETFs")



        if results['working']:

            print("\n[OK] Top 20 Working ETFs:")

            for ticker in sorted(results['working'].keys())[:20]:

                print(f"  - {ticker}")

            if len(results['working']) > 20:

                print(f"  ... and {len(results['working']) - 20} more")



    except Exception as e:

        print(f"Error: {str(e)}", file=sys.stderr)

        sys.exit(1)





def discover_all_etfs(

    etfs_file: str = "config/etfs.json",

    blacklist_file: str = "config/blacklist.json",

    max_workers: int = 5,

) -> None:

    """

    Discover ALL XETRA ETFs from justETFs and validate in parallel.



    Args:

        etfs_file: JSON file to save working ETFs

        blacklist_file: JSON file to save blacklisted ETFs

        max_workers: Number of parallel validation workers

    """

    try:

        discovery = ETFDiscovery(etfs_file=etfs_file, blacklist_file=blacklist_file)

        print("[START] Starting full XETRA ETF discovery from justETFs...\n")

        results = discovery.discover_parallel(tickers=None, max_workers=max_workers, verbose=True)



        print("\n[DATA] Discovery Complete!")

        print(f"  [OK] Working: {len(results['working'])} ETFs")

        print(f"  [X] Blacklisted: {len(results['blacklisted'])} ETFs")

        print("\n  Saved to:")

        print(f"    - {etfs_file} (use for screener)")

        print(f"    - {blacklist_file} (review delisted)")



    except Exception as e:

        print(f"Error: {str(e)}", file=sys.stderr)

        sys.exit(1)





def refresh_database(

    depth: int = 365,

    csv_file: str = "reference/t7-xetr-allTradableInstruments.csv",

    etfs_file: str = "config/etfs.json",

    blacklist_file: str = "config/blacklist.json",

    force: bool = False,

    include_blacklist: bool = False,

) -> None:

    """

    Refresh SQLite database by fetching/extending data for tickers from CSV.



    Incrementally fills gaps in historical data. Only fetches what's missing.



    Args:

        depth: Target number of days to maintain, counting back from today (e.g., 365 = today back 365 days)

        csv_file: Path to Deutsche Brse CSV file

        etfs_file: JSON file with validated ETFs

        blacklist_file: JSON file with blacklisted ETFs

        force: Re-fetch all tickers even if cached (default: False)

        include_blacklist: Include blacklisted tickers (default: False)

    """

    try:

        print(f" Starting database refresh (depth: {depth} days)...\n")



        # Extract tickers from CSV

        print(f"[READ] Reading ETF tickers from {csv_file}...")

        extractor = XETRETFExtractor(

            csv_file=csv_file,

            etfs_file=etfs_file,

            blacklist_file=blacklist_file,

        )

        tickers = extractor.extract_etf_tickers()

        

        if not tickers:

            print("[ERROR] No tickers found in CSV. Exiting.")

            return



        # Load blacklist

        blacklist = extractor.blacklist if hasattr(extractor, 'blacklist') else {}

        

        # Filter out blacklisted tickers (unless --include-blacklist)

        if not include_blacklist:

            tickers = [t for t in tickers if t not in blacklist]

            print(f"[OK] Found {len(tickers)} tickers in CSV (filtered out {len(extractor.extract_etf_tickers()) - len(tickers)} blacklisted)\n")

        else:

            print(f"[OK] Found {len(tickers)} tickers in CSV (including blacklisted)\n")



        # Initialize database

        db = ETFDatabase()

        fetcher = YFinanceFetcher()



        # Fetch and store data

        print(f"[DATA] Processing {len(tickers)} ETFs (target {depth} days)...\n")

        

        successful = 0

        failed = 0

        skipped = 0

        updated = 0



        for ticker in tqdm(tickers, desc="Processing", ncols=80):

            try:

                # Determine action

                ticker_exists = db.ticker_exists(ticker)

                

                if force:

                    # Force: re-fetch everything

                    action = "refetch"

                elif not ticker_exists:

                    # New: fetch from scratch

                    action = "new"

                else:

                    # Existing: check if we need to extend depth

                    oldest_date = db.get_oldest_date(ticker)

                    if oldest_date:

                        from datetime import datetime, timedelta

                        oldest = datetime.strptime(oldest_date, "%Y-%m-%d")

                        today = datetime.now()

                        days_in_db = (today - oldest).days

                        

                        if days_in_db < depth:

                            action = "extend"

                        else:

                            action = "skip"

                    else:

                        action = "skip"

                

                if action == "skip":

                    skipped += 1

                    continue

                

                # Fetch data
                df = fetcher.fetch_historical_data(ticker, days=depth)

                if df.empty:
                    tqdm.write(f"[ERROR] No data found for {ticker}")
                    # Blacklist if it's a new or problematic ticker to speed up future refreshes
                    extractor.add_to_blacklist(ticker, reason="No data found during refresh")
                    failed += 1
                    continue

                

                # Add indicators

                df = add_indicators(df)

                

                # Store in database (INSERT OR REPLACE handles updates)

                db.insert_dataframe(df, ticker)

                

                if action == "new":

                    successful += 1

                elif action == "extend":

                    updated += 1

                else:  # refetch

                    successful += 1

                    

            except Exception as e:

                failed += 1



        db.close()



        # Print summary

        print(f"\n[OK] Database refresh complete!")

        print(f"  [OK] New: {successful}")

        print(f"   Extended: {updated}")

        print(f"  [X] Failed: {failed}")

        print(f"   Skipped: {skipped}")

        print(f"   Total: {successful + updated + failed + skipped}/{len(tickers)}")



    except Exception as e:

        print(f"Error: {str(e)}", file=sys.stderr)

        sys.exit(1)





def main() -> None:

    """Main CLI entry point."""

    parser = argparse.ArgumentParser(

        prog="etfs",

        description="ETF Screener - Swing trading analysis for XETRA ETFs with technical indicators",

        epilog="""

======================== QUICK START GUIDE ========================



[START] FIRST TIME SETUP:

   1. Extract ETF list:          etfs extract

   2. Refresh database:           etfs refresh --depth 365

   3. Screen for opportunities:   etfs screener --aVol 50K --days 10 --swing



[DAILY] DAILY WORKFLOW:

   * Quick refresh:               etfs refresh --depth 30

   * Find swing setups:           etfs screener --swing --aVol 50K

   * Check uptrends:              etfs screener --supt green --aVol 50K



[FIND] DISCOVERY:

   * Validate specific ETFs:      etfs discover EXS1.DE EUNG.DE

   * Discover all (5-10 min):     etfs discover-all --workers 5



[DATA] SCREENING EXAMPLES:

   * Screen by volume:            etfs screener --aVol 100K --days 10

   * Swing-ready setups:          etfs screener --swing --swing-pull 2.0 --aVol 50K

   * Weekly trends (GREEN):       etfs screener --supt green --timeframe 1W --aVol 100K

   * Reversal candidates (RED):   etfs screener --supt red --red-streak 10 --aVol 50K



[SAVE] DATA MANAGEMENT:

   * Fetch specific ETFs:         etfs fetch EXS1.DE EUNG.DE --days 365

   * List cached data:            etfs list

   * Database rebuild:            etfs refresh --depth 365 --force



[VIEW] OUTPUT FORMATS:

   * Compact (volume only):       etfs screener --format compact

   * Default (indicators):        etfs screener --format default

   * Detailed (full data):        etfs screener --format detailed



[HELP] For detailed help on a command: etfs <command> --help



====================================================================

        """,

        formatter_class=argparse.RawDescriptionHelpFormatter,

    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")



    # Fetch command

    fetch_parser = subparsers.add_parser(

        "fetch", 

        help="Fetch & analyze ETF data: parquet + plots",

        description="Download historical data, calculate indicators, save data & generate charts"

    )

    fetch_parser.add_argument(

        "symbols",

        nargs="+",

        help="ETF symbols to fetch (e.g., EXS1.DE EUNG.DE)",

    )

    fetch_parser.add_argument(

        "--days",

        type=int,

        default=365,

        help="Number of days of historical data (default: 365)",

    )

    fetch_parser.add_argument(

        "--source",

        choices=["yfinance", "finnhub"],

        default="yfinance",

        help="Data source (default: yfinance)",

    )

    fetch_parser.add_argument(

        "--api-key",

        help="Finnhub API key (only for --source finnhub)",

    )

    fetch_parser.add_argument(

        "--data-dir",

        default="data",

        help="Directory to store parquet files (default: data)",

    )

    fetch_parser.add_argument(

        "--plot-dir",

        default="plots",

        help="Directory to store plots (default: plots)",

    )



    # List command

    list_parser = subparsers.add_parser(

        "list", 

        help="View cached ETF data",

        description="Show all ETFs in database with data range"

    )

    list_parser.add_argument(

        "--data-dir",

        default="data",

        help="Directory containing parquet files (default: data)",

    )



    # Screener command

    screener_parser = subparsers.add_parser(

        "screener", 

        help="Find ETFs matching criteria: volume, trends, signals",

        description="Screen cached ETF data by volume, technical indicators, and trend patterns"

    )

    screener_parser.add_argument(

        "symbols",

        nargs="*",

        help="ETF symbols to screen (e.g., EXS1.DE EUNG.DE). If empty, screens all in database.",

    )

    screener_parser.add_argument(

        "--nofEtfs",

        type=int,

        default=None,

        help="Number of top ETFs to return (default from output_formats.json config, or 10)",

    )

    screener_parser.add_argument(

        "--aVol",

        type=parse_volume,

        default=0,

        help="Minimum average volume (default: 0). Use K for thousands, M for millions (e.g., 100K, 1.5M)",

    )

    screener_parser.add_argument(

        "--days",

        type=int,

        default=5,

        help="Number of days to analyze (default: 5)",

    )

    screener_parser.add_argument(

        "--keep-days",

        type=int,

        default=365,

        help="Keep data for this many days; prune older (default: 365)",

    )

    screener_parser.add_argument(

        "--api-key",

        help="Finnhub API key (or set FINNHUB_API_KEY env var)",

    )

    screener_parser.add_argument(

        "--format",

        choices=["default", "compact", "detailed"],

        default="default",

        help="Output format template (default: default)",

    )

    screener_parser.add_argument(

        "--compact",

        action="store_true",

        help="Use compact output format (shorthand for --format compact)",

    )

    screener_parser.add_argument(

        "--detailed",

        action="store_true",

        help="Use detailed output format (shorthand for --format detailed)",

    )

    screener_parser.add_argument(

        "--default",

        action="store_true",

        help="Use default output format (shorthand for --format default)",

    )

    screener_parser.add_argument(

        "--swing",

        action="store_true",

        help="Filter for swing-ready setups (price dipped to EMA50 in uptrend)",

    )

    screener_parser.add_argument(

        "--swing-pull",

        type=float,

        default=2.0,

        help="Minimum pullback %% from recent high for swing filter (default: 2.0)",

    )

    screener_parser.add_argument(

        "--supt",

        choices=["green", "red"],

        help="Filter by Supertrend color (green: price > supertrend, red: price < supertrend)",

    )

    screener_parser.add_argument(

        "--data-dir",

        default="data",

        help="Directory containing etfs.json (default: data)",

    )

    screener_parser.add_argument(

        "--timeframe",

        choices=["1D", "1W"],

        default="1D",

        help="Timeframe for Supertrend calculation ('1D' daily or '1W' weekly, default: 1D)",

    )

    screener_parser.add_argument(

        "--st-period",

        type=int,

        default=10,

        help="Supertrend ATR period (default: 10)",

    )

    screener_parser.add_argument(

        "--st-multiplier",

        type=float,

        default=3.0,

        help="Supertrend multiplier (default: 3.0, try 2.0-3.5 to adjust sensitivity)",

    )

    screener_parser.add_argument(

        "--red-streak",

        type=int,

        default=0,

        help="Minimum consecutive RED days for reversal candidates (0 = all, 10+ = strong signal, use with --supt red)",

    )

    

    # Conditional operators: close, ema, pullback, volume
    for field in ["close", "ema", "pullback", "volume"]:
        # Choose type based on field
        data_type = float
        if field == "volume":
            data_type = parse_volume
            
        for op in ["gt", "gte", "lt", "lte", "eq", "ne"]:
            arg_name = f"--{field}-{op}"
            screener_parser.add_argument(
                arg_name,
                type=data_type,
                help=f"Filter {field} {op} value (e.g., --{field}-{op} 50)",
            )



    # Discover command

    discover_parser = subparsers.add_parser(

        "discover",

        help="Validate ETF tickers: test if they trade",

        description="Check if ETF tickers are valid and tradeable on XETRA"

    )

    discover_parser.add_argument(

        "symbols",

        nargs="*",

        help="ETF symbols to validate. If empty, validates predefined XETRA list.",

    )

    discover_parser.add_argument(

        "--etfs-file",

        default="config/etfs.json",

        help="JSON file to save validated ETFs (default: config/etfs.json)",

    )

    discover_parser.add_argument(

        "--blacklist-file",

        default="config/blacklist.json",

        help="JSON file to save blacklisted/invalid ETFs (default: config/blacklist.json)",

    )



    # Discover all command

    discover_all_parser = subparsers.add_parser(

        "discover-all", 

        help="Find all ~3000 XETRA ETFs (5-10 min)",

        description="Comprehensive discovery of all XETRA ETFs from justETFs database"

    )

    discover_all_parser.add_argument(

        "--etfs-file",

        default="config/etfs.json",

        help="JSON file to save validated ETFs (default: config/etfs.json)",

    )

    discover_all_parser.add_argument(

        "--blacklist-file",

        default="config/blacklist.json",

        help="JSON file to save blacklisted/invalid ETFs (default: config/blacklist.json)",

    )

    discover_all_parser.add_argument(

        "--workers",

        type=int,

        default=5,

        help="Number of parallel workers (default: 5, use 1-10)",

    )



    # Refresh command

    refresh_parser = subparsers.add_parser(

        "refresh",

        help="Update database: fetch missing historical data",

        description="Incrementally fill database with historical data for all XETRA ETFs"

    )

    refresh_parser.add_argument(

        "--depth",

        type=int,

        default=365,

        help="Target number of days of historical data (default: 365). Extends existing data to reach this depth.",

    )

    refresh_parser.add_argument(

        "--csv-file",

        default="reference/t7-xetr-allTradableInstruments.csv",

        help="Path to Deutsche Brse CSV file (default: reference/t7-xetr-allTradableInstruments.csv)",

    )

    refresh_parser.add_argument(

        "--etfs-file",

        default="config/etfs.json",

        help="JSON file with validated ETFs (default: config/etfs.json)",

    )

    refresh_parser.add_argument(

        "--blacklist-file",

        default="config/blacklist.json",

        help="JSON file with blacklisted ETFs (default: config/blacklist.json)",

    )

    refresh_parser.add_argument(

        "--force",

        action="store_true",

        help="Re-fetch all tickers even if already cached (full refresh)",

    )

    refresh_parser.add_argument(

        "--include-blacklist",

        action="store_true",

        help="Include blacklisted tickers (useful for re-validation)",

    )



    # Extract command

    extract_parser = subparsers.add_parser(

        "extract",

        help="Parse Deutsche Brse CSV: validate ETF list",

        description="Extract and validate XETRA ETF tickers from official CSV file"

    )

    extract_parser.add_argument(

        "--csv-file",

        default="reference/t7-xetr-allTradableInstruments.csv",

        help="Path to Deutsche Brse CSV file",

    )

    extract_parser.add_argument(

        "--etfs-file",

        default="config/etfs.json",

        help="JSON file to save validated ETFs (default: config/etfs.json)",

    )

    extract_parser.add_argument(

        "--blacklist-file",

        default="config/blacklist.json",

        help="JSON file to save blacklisted/invalid ETFs (default: config/blacklist.json)",

    )



    # Hotlist command

    hotlist_parser = subparsers.add_parser(

        "hotlist",

        help="Generate swing trading hotlist (daily prospects)",

        description="Create a timestamped report of ETFs with green supertrend and swing setups"

    )

    hotlist_parser.add_argument(

        "--aVol",

        type=parse_volume,

        default=10_000_000,

        help="Minimum average volume (default: 10M). Use K for thousands, M for millions (e.g., 100K, 1.5M)",

    )

    hotlist_parser.add_argument(

        "--days",

        type=int,

        default=10,

        help="Number of days to analyze (default: 10)",

    )

    hotlist_parser.add_argument(

        "--output",

        default="logs",

        help="Directory to save hotlist report (default: logs)",

    )

    hotlist_parser.add_argument(

        "--swing-pull",

        type=float,

        default=2.0,

        help="Minimum pullback %% from recent high (default: 2.0)",

    )

    hotlist_parser.add_argument(

        "--ema-distance",

        type=float,

        default=5.0,

        help="Maximum distance %% from EMA50 (default: 5.0)",

    )

    hotlist_parser.add_argument(

        "--timeframe",

        choices=["1D", "1W"],

        default="1D",

        help="Timeframe for analysis ('1D' daily or '1W' weekly, default: 1D)",

    )

    hotlist_parser.add_argument(

        "--st-period",

        type=int,

        default=10,

        help="Supertrend ATR period (default: 10)",

    )

    hotlist_parser.add_argument(

        "--st-multiplier",

        type=float,

        default=3.0,

        help="Supertrend multiplier (default: 3.0)",

    )




    args = parser.parse_args()



    if args.command == "fetch":

        fetch_and_analyze(

            args.symbols,

            days=args.days,

            api_key=args.api_key,

            data_dir=args.data_dir,

            plot_dir=args.plot_dir,

            source=args.source,

        )

    elif args.command == "list":

        list_saved_etfs(data_dir=args.data_dir)

    elif args.command == "screener":

        # Determine format from convenience flags or --format argument

        format_name = args.format

        if args.compact:

            format_name = "compact"

        elif args.detailed:

            format_name = "detailed"

        elif args.default:

            format_name = "default"

        elif args.swing:

            format_name = "swing"

        

        # Extract conditional filters from args

        conditions = {}

        min_avg_volume = args.aVol

        for field in ["close", "ema", "pullback", "volume"]:

            field_conditions = []

            for op in ["gt", "gte", "lt", "lte", "eq", "ne"]:

                attr_name = f"{field}_{op}" if field != "pullback" else f"pb_{op}"

                if hasattr(args, attr_name) and getattr(args, attr_name) is not None:

                    val = getattr(args, attr_name)

                    field_conditions.append((op, val))

                    # If volume condition is provided, use it to update min_avg_volume

                    if field == "volume" and op in ["gt", "gte"]:

                        min_avg_volume = min(min_avg_volume, val)

            if field_conditions:

                conditions[field] = field_conditions

        

        screen_etfs(

            symbols=args.symbols if args.symbols else None,

            nof_etfs=args.nofEtfs,

            min_avg_volume=min_avg_volume,

            days=args.days,

            days_to_keep=args.keep_days,

            api_key=args.api_key,

            format_name=format_name,

            data_dir=args.data_dir,

            filter_swing=args.swing,

            swing_pullback=args.swing_pull,

            supertrend_filter=args.supt,

            timeframe=args.timeframe,

            st_period=args.st_period,

            st_multiplier=args.st_multiplier,

            red_streak_min=args.red_streak,

            conditions=conditions if conditions else None,

        )

    elif args.command == "discover":

        discover_etfs(

            tickers=args.symbols if args.symbols else None,

            etfs_file=args.etfs_file,

            blacklist_file=args.blacklist_file,

        )

    elif args.command == "discover-all":

        discover_all_etfs(

            etfs_file=args.etfs_file,

            blacklist_file=args.blacklist_file,

            max_workers=args.workers,

        )

    elif args.command == "refresh":

        refresh_database(

            depth=args.depth,

            csv_file=args.csv_file,

            etfs_file=args.etfs_file,

            blacklist_file=args.blacklist_file,

            force=args.force,

            include_blacklist=args.include_blacklist,

        )

    elif args.command == "extract":

        extract_xetra_etfs(

            csv_file=args.csv_file,

            etfs_file=args.etfs_file,

            blacklist_file=args.blacklist_file,

        )

    elif args.command == "hotlist":

        generate_hotlist(

            min_avg_volume=args.aVol,

            days=args.days,

            output_dir=args.output,

            min_pullback=args.swing_pull,

            max_distance_from_ema=args.ema_distance,

            st_period=args.st_period,

            st_multiplier=args.st_multiplier,

            timeframe=args.timeframe,

        )

    else:

        parser.print_help()





if __name__ == "__main__":

    main()

