"""Entry point for ETF screener CLI."""

import argparse
import sys
from typing import Optional

from ETF_screener.data_fetcher import FinnhubFetcher
from ETF_screener.database import ETFDatabase
from ETF_screener.etf_discovery import ETFDiscovery
from ETF_screener.indicators import add_indicators
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

        print("\n✓ Analysis complete!")
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
    List all saved ETFs in parquet storage.

    Args:
        data_dir: Directory containing parquet files
    """
    storage = ParquetStorage(data_dir=data_dir)
    etfs = storage.list_available_etfs()

    if etfs:
        print(f"Available ETFs in {data_dir}:")
        for symbol in etfs:
            df = storage.load_etf_data(symbol)
            if not df.empty:
                print(f"  {symbol}: {len(df)} rows, {df['Date'].min()} to {df['Date'].max()}")
    else:
        print(f"No ETF data found in {data_dir}")


def screen_etfs(
    symbols: Optional[list[str]] = None,
    nof_etfs: int = 10,
    min_avg_volume: int = 10_000_000,
    days: int = 10,
    days_to_keep: int = 365,
    api_key: Optional[str] = None,
) -> None:
    """
    Screen ETFs by volume criteria. Auto-fetches missing data and prunes stale records.

    Args:
        symbols: List of ETF symbols to screen (if None, screens all in database)
        nof_etfs: Number of ETFs to return
        min_avg_volume: Minimum average volume in shares
        days: Number of days to look back
        days_to_keep: Number of days to keep in database (prune older)
        api_key: Finnhub API key
    """
    try:
        db = ETFDatabase()
        
        # Prune data older than days_to_keep
        deleted = db.prune_old_data(days_to_keep=days_to_keep)
        if deleted > 0:
            print(f"Pruned {deleted} records older than {days_to_keep} days")
        
        # If symbols provided, fetch missing ones
        if symbols:
            print(f"Checking database for {len(symbols)} symbols...")
            missing_symbols = []
            
            for symbol in symbols:
                if not db.ticker_exists(symbol):
                    missing_symbols.append(symbol)
                else:
                    latest_date = db.get_latest_date(symbol)
                    print(f"  ✓ {symbol} found (latest: {latest_date})")
            
            if missing_symbols:
                print(f"Fetching {len(missing_symbols)} missing symbols from Yahoo Finance...")
                fetcher = YFinanceFetcher()
                etf_data = fetcher.fetch_multiple_etfs(missing_symbols, days=days_to_keep)
                
                if etf_data:
                    print("Calculating indicators...")
                    for symbol, df in etf_data.items():
                        etf_data[symbol] = add_indicators(df)
                    
                    print("Storing in database...")
                    for symbol, df in etf_data.items():
                        db.insert_dataframe(df, symbol)
                        print(f"  ✓ {symbol} stored")
        
        screener = ETFScreener(db=db, api_key=api_key)
        print(f"\nScreening ETFs (last {days} days, avg volume >= {min_avg_volume:,})...")

        results = screener.screen_by_volume(
            min_days=days,
            min_avg_volume=min_avg_volume,
            max_results=nof_etfs,
            fetch_missing=False,
        )

        screener.print_results(results)

        if results.empty:
            if symbols:
                print(
                    f"\n⚠️  No {symbols} matched the volume criteria."
                    f" Try lower --aVol threshold."
                )
            else:
                print(
                    "\n💡 Tip: Run with symbols to fetch and analyze:"
                    "\n  etfs screener EXS1.DE EUNG.DE XESC.DE --aVol 1000 --days 20"
                )

        db.close()

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def discover_etfs(
    tickers: Optional[list[str]] = None,
    etfs_file: str = "data/etfs.json",
    blacklist_file: str = "data/blacklist.json",
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

        print("\n📊 Discovery Summary:")
        print(f"  Working: {len(results['working'])} ETFs")
        print(f"  Blacklisted: {len(results['blacklisted'])} ETFs")
        
        if results['working']:
            print("\n✓ Working ETFs:")
            for ticker in sorted(results['working'].keys()):
                print(f"  • {ticker}")
        
        if results['blacklisted']:
            print("\n✗ Blacklisted ETFs:")
            for ticker in sorted(results['blacklisted'].keys()):
                print(f"  • {ticker}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def extract_xetra_etfs(
    csv_file: str = "reference/t7-xetr-allTradableInstruments.csv",
    etfs_file: str = "data/etfs.json",
    blacklist_file: str = "data/blacklist.json",
) -> None:
    """
    Extract and validate XETRA ETF tickers from Deutsche Börse CSV.

    Args:
        csv_file: Path to Deutsche Börse CSV file
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

        print("\n📊 Extraction Summary:")
        print(f"  CSV File: {csv_file}")
        print(f"  Working: {len(results['working'])} ETFs")
        print(f"  Blacklisted: {len(results['blacklisted'])} ETFs")

        if results['working']:
            print("\n✓ Top 20 Working ETFs:")
            for ticker in sorted(results['working'].keys())[:20]:
                print(f"  • {ticker}")
            if len(results['working']) > 20:
                print(f"  ... and {len(results['working']) - 20} more")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def discover_all_etfs(
    etfs_file: str = "data/etfs.json",
    blacklist_file: str = "data/blacklist.json",
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
        print("🚀 Starting full XETRA ETF discovery from justETFs...\n")
        results = discovery.discover_parallel(tickers=None, max_workers=max_workers, verbose=True)

        print("\n📊 Discovery Complete!")
        print(f"  ✓ Working: {len(results['working'])} ETFs")
        print(f"  ✗ Blacklisted: {len(results['blacklisted'])} ETFs")
        print("\n  Saved to:")
        print(f"    • {etfs_file} (use for screener)")
        print(f"    • {blacklist_file} (review delisted)")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ETF Screener - Analyze large ETFs for swing trading"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Fetch command
    fetch_parser = subparsers.add_parser(
        "fetch", help="Fetch and analyze ETF data"
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
        "list", help="List saved ETFs"
    )
    list_parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing parquet files (default: data)",
    )

    # Screener command
    screener_parser = subparsers.add_parser(
        "screener", help="Screen ETFs by volume criteria"
    )
    screener_parser.add_argument(
        "symbols",
        nargs="*",
        help="ETF symbols to screen (e.g., EXS1.DE EUNG.DE). If empty, screens all in database.",
    )
    screener_parser.add_argument(
        "--nofEtfs",
        type=int,
        default=10,
        help="Number of top ETFs to return (default: 10)",
    )
    screener_parser.add_argument(
        "--aVol",
        type=parse_volume,
        default=10_000_000,
        help="Minimum average volume (default: 10M). Use K for thousands, M for millions (e.g., 100K, 1.5M)",
    )
    screener_parser.add_argument(
        "--days",
        type=int,
        default=10,
        help="Number of days to analyze (default: 10)",
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

    # Discover command
    discover_parser = subparsers.add_parser(
        "discover", help="Discover and validate ETF tickers"
    )
    discover_parser.add_argument(
        "symbols",
        nargs="*",
        help="ETF symbols to validate. If empty, validates predefined XETRA list.",
    )
    discover_parser.add_argument(
        "--etfs-file",
        default="data/etfs.json",
        help="JSON file to save validated ETFs (default: data/etfs.json)",
    )
    discover_parser.add_argument(
        "--blacklist-file",
        default="data/blacklist.json",
        help="JSON file to save blacklisted/invalid ETFs (default: data/blacklist.json)",
    )

    # Discover all command
    discover_all_parser = subparsers.add_parser(
        "discover-all", help="Discover ALL 2950+ XETRA ETFs from justETFs (this takes time!)"
    )
    discover_all_parser.add_argument(
        "--etfs-file",
        default="data/etfs.json",
        help="JSON file to save validated ETFs (default: data/etfs.json)",
    )
    discover_all_parser.add_argument(
        "--blacklist-file",
        default="data/blacklist.json",
        help="JSON file to save blacklisted/invalid ETFs (default: data/blacklist.json)",
    )
    discover_all_parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5, use 1-10)",
    )

    # Extract command
    extract_parser = subparsers.add_parser(
        "extract", help="Extract XETRA ETFs from Deutsche Börse CSV"
    )
    extract_parser.add_argument(
        "--csv-file",
        default="reference/t7-xetr-allTradableInstruments.csv",
        help="Path to Deutsche Börse CSV file",
    )
    extract_parser.add_argument(
        "--etfs-file",
        default="data/etfs.json",
        help="JSON file to save validated ETFs (default: data/etfs.json)",
    )
    extract_parser.add_argument(
        "--blacklist-file",
        default="data/blacklist.json",
        help="JSON file to save blacklisted/invalid ETFs (default: data/blacklist.json)",
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
        screen_etfs(
            symbols=args.symbols if args.symbols else None,
            nof_etfs=args.nofEtfs,
            min_avg_volume=args.aVol,
            days=args.days,
            days_to_keep=args.keep_days,
            api_key=args.api_key,
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
    elif args.command == "extract":
        extract_xetra_etfs(
            csv_file=args.csv_file,
            etfs_file=args.etfs_file,
            blacklist_file=args.blacklist_file,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
