import os
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from ETF_screener.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_stoch_rsi,
    clean_price_data,
)
from ETF_screener.plotter import PortfolioPlotter


def test_jupi_spike_fix():
    print("Fetching data for JUPI.DE (known for 17,000% yfinance spikes)...")
    ticker = "JUPI.DE"
    # Ensure a wide enough window to catch the Nov 2025 spikes
    end_date = datetime.now()
    start_date = end_date - timedelta(days=250)

    df = yf.download(ticker, start=start_date, end=end_date)
    if df.empty:
        print("Failed to fetch data.")
        return

    print(f"Index: {df.index.names}")
    print(f"Columns before reset: {df.columns}")
    df = df.reset_index()
    print(f"Columns after reset: {df.columns}")

    # Flatten multi-index if needed
    if isinstance(df.columns, pd.MultiIndex):
        print("Handling MultiIndex columns...")
        # yfinance now uses (Price, Ticker) - we want Price
        df.columns = [c[0] for c in df.columns]
        print(f"Columns after flattening: {df.columns}")

    df.columns = df.columns.astype(str).str.capitalize()
    print(f"Calculated columns: {df.columns}")

    # Check if 'Close' exists (case insensitive)
    close_col = next((c for c in df.columns if c.lower() == "close"), None)
    if not close_col:
        print(f"ERROR: Could not find 'Close' column. Available: {list(df.columns)}")
        return

    print(f"Found close column: {close_col}")

    print(f"Initial raw data shape: {df.shape}")

    # Apply standard cleaning (which we just improved)
    # The jump is approx 170x (17,000%)
    print("Applying level-shift cleaning...")
    # NOTE: The cleaner modifies in-place if we loop, so we copy.
    df["Close"] = clean_price_data(df["Close"])
    df["High"] = clean_price_data(df["High"])
    df["Low"] = clean_price_data(df["Low"])
    df["Open"] = clean_price_data(df["Open"])

    print("Calculating indicators on cleaned data...")
    df["RSI"] = calculate_rsi(df)
    macd_line, signal_line, hist = calculate_macd(df)
    df["MACD"] = macd_line
    df["MACD_Signal"] = signal_line
    df["MACD_Hist"] = hist

    stoch_k, stoch_d = calculate_stoch_rsi(df)
    df["Stoch_RSI_K"] = stoch_k
    df["Stoch_RSI_D"] = stoch_d

    # Add dummy signal column to satisfy plotter
    df["Signal"] = 0

    print("Generating plot to plots/jupi_clean_test.svg...")
    plotter = PortfolioPlotter(output_dir="plots")
    plotter.plot_etf_analysis(df, ticker)

    print("Success! Check plots/jupi_clean_test.svg for clean indicators.")


if __name__ == "__main__":
    if not os.path.exists("plots"):
        os.makedirs("plots")
    test_jupi_spike_fix()
