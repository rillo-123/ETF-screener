def fetch_and_analyze(
    symbols: list[str],
    days: int = 365,
    api_key: Optional[str] = None,
    data_dir: str = "data",
    plot_dir: str = "plots",
    use_db: bool = True,
    source: str = "yfinance",
    plot_format: str = "svg",
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
        plot_format: Output format for plots ('svg' or 'png')
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
        print(f"Generating analysis plots ({plot_format.upper()})...")
        plotter = PortfolioPlotter(output_dir=plot_dir)
        plotter.plot_multiple_etfs(etf_data, format=plot_format)

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





