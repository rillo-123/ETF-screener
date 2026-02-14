"""Plotting utilities for ETF analysis."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

# Use non-interactive backend to avoid GUI requirements
matplotlib.use("Agg")


class PortfolioPlotter:
    """Plot ETF data with technical indicators."""

    def __init__(self, output_dir: str = "plots"):
        """
        Initialize plotter.

        Args:
            output_dir: Directory to save plot images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def plot_etf_analysis(
        self, df: pd.DataFrame, symbol: str, figsize: tuple = (14, 8)
    ) -> Path:
        """
        Create comprehensive ETF analysis plot.

        Args:
            df: DataFrame with OHLCV and indicator data
            symbol: ETF symbol
            figsize: Figure size tuple

        Returns:
            Path to saved plot
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)

        # Plot 1: Price with indicators
        ax1.plot(
            df["Date"], df["Close"], label="Close Price", color="black", linewidth=2
        )
        ax1.plot(df["Date"], df["EMA_50"], label="EMA 50", color="blue", linewidth=1)
        ax1.fill_between(
            df["Date"],
            df["ST_Upper"],
            df["ST_Lower"],
            alpha=0.2,
            color="gray",
            label="Supertrend Band",
        )
        ax1.plot(
            df["Date"], df["Supertrend"], label="Supertrend", color="red", linewidth=1
        )

        # Buy signals
        buy_signals = df[df["Signal"] == 1]
        ax1.scatter(
            buy_signals["Date"],
            buy_signals["Close"],
            color="green",
            marker="^",
            s=100,
            label="Buy Signal",
            zorder=5,
        )

        # Sell signals
        sell_signals = df[df["Signal"] == -1]
        ax1.scatter(
            sell_signals["Date"],
            sell_signals["Close"],
            color="red",
            marker="v",
            s=100,
            label="Sell Signal",
            zorder=5,
        )

        ax1.set_ylabel("Price", fontsize=12)
        ax1.set_title(f"{symbol} - Technical Analysis", fontsize=14, fontweight="bold")
        ax1.legend(loc="best")
        ax1.grid(True, alpha=0.3)

        # Plot 2: Volume
        ax2.bar(df["Date"], df["Volume"], color="steelblue", alpha=0.6)
        ax2.set_ylabel("Volume", fontsize=12)
        ax2.set_xlabel("Date", fontsize=12)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save figure
        output_path = self.output_dir / f"{symbol.lower()}_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Saved plot to {output_path}")
        plt.close()

        return output_path

    def plot_multiple_etfs(self, etf_dict: dict[str, pd.DataFrame]) -> dict:
        """
        Create analysis plots for multiple ETFs.

        Args:
            etf_dict: Dictionary mapping symbol to DataFrame

        Returns:
            Dictionary mapping symbol to plot path
        """
        results = {}
        for symbol, df in etf_dict.items():
            try:
                results[symbol] = self.plot_etf_analysis(df, symbol)
            except Exception as e:
                print(f"Error plotting {symbol}: {str(e)}")
        return results

    def plot_price_only(self, df: pd.DataFrame, symbol: str) -> Path:
        """
        Create a simple price plot.

        Args:
            df: DataFrame with price data
            symbol: ETF symbol

        Returns:
            Path to saved plot
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(df["Date"], df["Close"], label="Close Price", linewidth=2)
        ax.set_ylabel("Price", fontsize=12)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_title(f"{symbol} - Price Chart", fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        output_path = self.output_dir / f"{symbol.lower()}_price.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"Saved price plot to {output_path}")
        plt.close()

        return output_path
