"""Plotting utilities for ETF analysis."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

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
        # Resolve duplicate labels BEFORE any other operations
        df = df.copy()
        if df.columns.duplicated().any():
            # If we have duplicate column names, pandas gets confused during indexing
            # We explicitly keep only the first occurrence for each column name
            df = df.loc[:, ~df.columns.duplicated()].copy()

        # Ensure Case-Insensitive Column Access
        cols = []
        seen = set()
        for c in df.columns:
            c_str = str(c)
            # Standardize core columns
            if c_str.lower() in ['date', 'open', 'high', 'low', 'close', 'volume', 'signal']:
                new_col = c_str.capitalize()
            else:
                new_col = c_str
            
            # Final safety check against duplicates after capitalization
            if new_col in seen:
                continue
            cols.append(new_col)
            seen.add(new_col)
        
        df = df.iloc[:, :len(cols)] # Trim if needed
        df.columns = cols
        
        # Identify special indicator columns for separate subplots
        is_oscillator = lambda c: any(x in c.lower() for x in ["rsi", "stoch", "macd", "adx"])
        
        # Calculate robust price limits to handle outliers (like bad data points)
        price_col = "Close" if "Close" in df.columns else "close"
        # Ensure price_col exists in df
        if price_col not in df.columns:
            # Fallback to the first numeric column if Close/close is missing
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            price_col = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[0]

        # Debug print columns for diagnosis
        # print(f"Plotting {symbol}. Columns: {df.columns.tolist()}")

        # Use quantiles to establish the y-limits, ignoring the top/bottom 2% of extreme values
        # Add safety for column name cases
        price_col = "Close" if "Close" in df.columns else "close"
        if price_col not in df.columns and "Adj Close" in df.columns:
            price_col = "Adj Close"
            
        p_min_robust = df[price_col].quantile(0.01)
        p_max_robust = df[price_col].quantile(0.99)
        p_range = p_max_robust - p_min_robust
        
        # Filter indicators for those with meaningful variance to avoid straight lines ruining the scale
        valid_cols = []
        for c in df.columns:
            if c in ["Date", "Open", "High", "Low", "Close", "Volume", "Signal", "signal"]:
                continue
            # Also skip internal columns like _slope or _dN if they are not explicitly meant for plotting
            if any(x in c.lower() for x in ["_slope", "_lr_"]):
                continue

            if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().sum() > 0:
                # If it's effectively constant, skip it to avoid y-axis scaling issues
                # But allow oscillators even if variance is small (they have their own scale)
                if df[c].std() > 1e-8 or is_oscillator(c):
                    # Also skip indicators that are vastly outside the robust price range (e.g. metadata or bad data)
                    # EXCEPT for oscillators like MACD/RSI that naturally live in a different range (e.g. 0-100 or near 0)
                    if not is_oscillator(c):
                        c_mean = df[c].mean()
                        if c_mean < p_min_robust - 10 * p_range or c_mean > p_max_robust + 10 * p_range:
                            continue
                    valid_cols.append(c)

        # Prepare indicators for plotting
        price_indicators = [c for c in valid_cols if not is_oscillator(c)]
        
        # Categorize oscillators for dedicated subplots
        osc_groups = {
            "RSI": [c for c in valid_cols if "rsi" in c.lower() and "stoch" not in c.lower()],
            "MACD": [c for c in valid_cols if "macd" in c.lower()],
            "StochRSI": [c for c in valid_cols if "stoch" in c.lower() or "srsi" in c.lower() or "stochrsi" in c.lower()],
            "ADX": [c for c in valid_cols if "adx" in c.lower()]
        }
        
        # DEBUG: Ensure all stoch columns are identified correctly
        stoch_cols = [c for c in valid_cols if "stoch" in c.lower() or "srsi" in c.lower() or "stochrsi" in c.lower()]
        # print(f"DEBUG: Found StochRSI columns: {stoch_cols}")
        
        # Only keep groups that have at least one valid column
        active_groups = {}
        for k, v in osc_groups.items():
            valid_group_cols = [c for c in v if c in df.columns]
            if valid_group_cols:
                active_groups[k] = valid_group_cols
        
        num_subplots = 1 + 1 + len(active_groups)  # Price + Volume + Active Groups (Oscillators)
        # Order: Price (4), Volume (1), Oscillators (2.2 each)
        height_ratios = [4, 1] + ([2.2] * len(active_groups))
        
        fig, axes = plt.subplots(
            num_subplots, 1, 
            figsize=(14, 4 + 2 + 2.5 * len(active_groups)), # Adjusted total figure height
            sharex=True, 
            gridspec_kw={'height_ratios': height_ratios, 'hspace': 0.15} 
        )
        
        if num_subplots == 2:
            ax1, ax_vol = axes[0], axes[1]
            osc_ax_map = {}
        else:
            ax1 = axes[0]
            ax_vol = axes[1] # Volume moved to index 1 (under Price)
            # Indicators move to indices 2 and beyond
            osc_ax_map = {name: axes[i+2] for i, name in enumerate(active_groups.keys())}

        # Plot 1: Price with indicators (Moving Averages, Supertrend)
        ax1.plot(
            df["Date"], df["Close"], label="Close Price", color="black", linewidth=2
        )
        
        # Explicitly set y-limits to the robust range to fix the "straight line" outlier issue
        padding = p_range * 0.1 if p_range > 0 else 1.0
        ax1.set_ylim(p_min_robust - padding, p_max_robust + padding)
        
        # Plot valid price indicators
        for col in price_indicators:
            # Skip Supertrend (ST) lines to keep the chart clean, but keep moving averages (MA/EMA)
            if "st_" in col.lower() or "supertrend" in col.lower():
                continue
            ax1.plot(df["Date"], df[col], label=col, alpha=0.7)

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

        # Highlight profitable trade regions
        # Logic: Find a 1, find the next -1. If close at -1 > close at 1, color that region green.
        try:
            trade_df = df[df["Signal"].isin([1, -1])].copy()
            if not trade_df.empty:
                entry_idx = None
                for idx, row in trade_df.iterrows():
                    if row["Signal"] == 1:
                        entry_idx = idx
                    elif row["Signal"] == -1 and entry_idx is not None:
                        # Trade completed
                        exit_idx = idx
                        entry_price = df.loc[entry_idx, "Close"]
                        exit_price = df.loc[exit_idx, "Close"]
                        
                        color = "green" if exit_price > entry_price else "red"
                        # Fill between entry/exit dates with enhanced visibility
                        ax1.axvspan(df.loc[entry_idx, "Date"], df.loc[exit_idx, "Date"], 
                                   color=color, alpha=0.25, label="_nolegend_")
                        # Add a vertical line at entry and exit for sharpness
                        ax1.axvline(df.loc[entry_idx, "Date"], color="gray", linestyle="--", alpha=0.3, linewidth=1)
                        ax1.axvline(df.loc[exit_idx, "Date"], color="gray", linestyle="--", alpha=0.3, linewidth=1)
                        entry_idx = None
        except Exception as e:
            print(f"Warning: Could not highlight trade regions: {e}")

        ax1.set_ylabel("Price", fontsize=12)
        ax1.set_title(f"{symbol} - Technical Analysis", fontsize=14, fontweight="bold")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)

        # Plot Oscillator Subplots (RSI, StochRSI, MACD)
        for name, osc_ax in osc_ax_map.items():
            cols = active_groups[name]
            
            # Special handling for MACD to use histogram and colored lines
            if name == "MACD":
                hist_cols = [c for c in cols if "hist" in c.lower()]
                signal_cols = [c for c in cols if "signal" in c.lower()]
                macd_cols = [c for c in cols if (c.lower() == "macd" or ("macd" in c.lower() and "signal" not in c.lower() and "hist" not in c.lower()))]
                
                if hist_cols:
                    h_col = hist_cols[0]
                    # Create colors for histogram (green for positive, red for negative)
                    hist_data = df[h_col].fillna(0).values
                    colors = ['green' if x >= 0 else 'red' for x in hist_data]
                    # Calculate reasonable bar width based on date spacing (default to 0.8 days)
                    width = 0.8
                    if len(df) > 1:
                        avg_diff = (df["Date"].iloc[-1] - df["Date"].iloc[0]).total_seconds() / (len(df) * 86400)
                        width = max(0.2, min(0.9, avg_diff * 0.8))
                    
                    osc_ax.bar(df["Date"], df[h_col], width=width, color=colors, alpha=0.5, label="Hist")
                
                if macd_cols:
                    # Map any macd column to charcoal
                    osc_ax.plot(df["Date"], df[macd_cols[0]], label="MACD", color="#1c1c1c", linewidth=2.0)
                
                if signal_cols:
                    # Map any signal column to deep red
                    osc_ax.plot(df["Date"], df[signal_cols[0]], label="Signal", color="#d62728", linewidth=1.5)
                
                # If we missed any other MACD related columns
                other_cols = [c for c in cols if c not in hist_cols + signal_cols + macd_cols]
                for col in other_cols:
                    osc_ax.plot(df["Date"], df[col], label=col, alpha=0.7, linewidth=1.5)
            else:
                # Standard plotting for RSI/StochRSI
                for col in cols:
                    # Ensure numeric data for plotting
                    data_to_plot = pd.to_numeric(df[col], errors='coerce')
                    
                    # Custom styling for oscillators
                    color = None
                    linewidth = 1.0 
                    alpha = 1.0 # Increased from 0.95 for maximum visibility
                    
                    col_lower = col.lower()
                    zorder = 3 # Default zorder
                    if name == "StochRSI":
                        if "stoch_rsi_k" in col_lower or col_lower.endswith("_k") or col_lower.endswith("k"):
                            color = "#1f77b4" # Strong Blue for %K
                            linewidth = 2.4 # Increased significantly
                            zorder = 3
                        elif "stoch_rsi_d" in col_lower or col_lower.endswith("_d") or col_lower.endswith("d"):
                            color = "#e41a1c" # Strong Red for %D Signal
                            linewidth = 2.0 
                            zorder = 4 # Put Red Signal on TOP of Blue K
                        alpha = 1.0
                    elif name == "RSI":
                        color = "#7b1fa2" # Purple for RSI
                        linewidth = 2.0
                        zorder = 3
                    
                    osc_ax.plot(df["Date"], data_to_plot, label=col, alpha=alpha, linewidth=linewidth, color=color, zorder=zorder)
            
            # Add guides for specific indicators
            if name == "RSI":
                osc_ax.axhline(70, color="red", linestyle="--", alpha=0.3)
                osc_ax.axhline(30, color="green", linestyle="--", alpha=0.3)
                osc_ax.set_ylim(-5, 105) # Extra padding for visibility
            elif name == "StochRSI":
                osc_ax.axhline(80, color="red", linestyle="--", alpha=0.3)
                osc_ax.axhline(20, color="green", linestyle="--", alpha=0.3)
                # Fill the area between overbought/oversold for StochRSI
                osc_ax.axhspan(20, 80, color="gray", alpha=0.05)
                # Check if values are 0-1 or 0-100 to set appropriate limits
                max_val = df[cols].max().max()
                if max_val <= 1.1:
                    osc_ax.set_ylim(-0.05, 1.05)
                    # Convert guides to 0-1 if data is 0-1
                    for line in osc_ax.get_lines():
                        if line.get_ydata()[0] == 80: line.set_ydata([0.8, 0.8])
                        if line.get_ydata()[0] == 20: line.set_ydata([0.2, 0.2])
                else:
                    osc_ax.set_ylim(-5, 105)
            elif name == "MACD" and len(cols) > 0:
                # Add a zero line for MACD
                osc_ax.axhline(0, color="black", linestyle="-", alpha=0.2)
                
                # Robust scaling for MACD to avoid extreme compression
                m_data = df[cols].values
                m_min, m_max = np.nanquantile(m_data, [0.01, 0.99])
                m_range = m_max - m_min
                if m_range > 0:
                    osc_ax.set_ylim(m_min - 0.2*m_range, m_max + 0.2*m_range)
            
            osc_ax.set_ylabel(name, fontsize=10)
            osc_ax.grid(True, alpha=0.2)
            osc_ax.legend(loc="upper left", fontsize=8)

        # Plot Volume
        ax_vol.bar(df["Date"], df["Volume"], color="steelblue", alpha=0.6)
        ax_vol.set_ylabel("Volume", fontsize=12)
        ax_vol.grid(True, alpha=0.3)

        # Format X-axis Dates (YYYY-MM-DD)
        all_axes = [ax1] + list(osc_ax_map.values()) + [ax_vol]
        
        for ax in all_axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
            # Enable auto-formatting and then hide/show specifically
            ax.tick_params(axis='x', labelbottom=False)
            
        # Only show labels on the very last subplot (which is ax_vol)
        last_ax = all_axes[-1]
        last_ax.tick_params(axis='x', labelbottom=True)
        # Use horizontal labels to avoid overlap with panel below
        plt.setp(last_ax.get_xticklabels(), visible=True, rotation=0, ha='center', fontsize=8)

        # Add performance metrics to the plot
        total_return = 0
        if "Signal" in df.columns:
            # Simple check for return if it's available in the dataframe name or similar
            # If we don't have it passed, we can calculate a simple "buy and hold" or similar
            buy_count = (df["Signal"] == 1).sum()
            sell_count = (df["Signal"] == -1).sum()
            stats_text = f"Trades: {buy_count + sell_count}\nBuys: {buy_count}\nSells: {sell_count}"
            ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.5))

        # Use subplots_adjust instead of tight_layout to prevent compatible axes warnings
        # and provide consistent spacing for multiple indicator panels
        plt.subplots_adjust(hspace=0.4, top=0.92, bottom=0.08, left=0.1, right=0.95)

        # Save figure as both SVG (primary) and PNG (backup)
        output_path_svg = self.output_dir / f"{symbol.lower()}_analysis.svg"
        output_path_png = self.output_dir / f"{symbol.lower()}_analysis.png"
        
        plt.savefig(output_path_svg, format="svg", bbox_inches="tight")
        plt.savefig(output_path_png, format="png", dpi=300, bbox_inches="tight")
        
        print(f"Saved SVG plot to {output_path_svg}")
        plt.close()

        return output_path_svg

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
        
        # Automatically update the manifest for the dashboard viewer
        try:
            import json
            import shutil
            import re
            
            # Ensure the output directory exists
            self.output_dir.mkdir(exist_ok=True)
            
            # 1. Update the JSON manifest file first
            plots = sorted([f.name for f in self.output_dir.glob("*.svg") or []])
            
            # Check if there is already a rich manifest (from churn_strategies.py)
            manifest_file = self.output_dir / "plot_manifest.json"
            if manifest_file.exists():
                manifest_json = manifest_file.read_text(encoding='utf-8')
            else:
                manifest_json = json.dumps(plots)
                manifest_file.write_text(manifest_json, encoding='utf-8')
            
            # 2. Update/Sync index.html
            target_ui = self.output_dir / "index.html"
            root_ui = Path("browser.html")
            
            # Always refresh the HTML template from root if available
            if root_ui.exists():
                shutil.copy2(root_ui, target_ui)
                
            if target_ui.exists():
                # Inject the real manifest data directly into the index.html fallback
                content = target_ui.read_text(encoding='utf-8')
                # Use a more robust regex for the manifest injection
                pattern = r"const rawManifest = '.*?';"
                escaped_json = manifest_json.replace("'", "\\'")
                new_manifest_line = f"const rawManifest = '{escaped_json}';"
                
                if re.search(pattern, content):
                    updated_content = re.sub(pattern, new_manifest_line, content)
                    target_ui.write_text(updated_content, encoding='utf-8')
                
            print(f"Updated dashboard manifest with {len(plots)} items.")
        except Exception as e:
            print(f"Warning: Could not update plot manifest: {e}")
            print(f"Warning: Could not update plot manifest: {e}")
            
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

        output_path = self.output_dir / f"{symbol.lower()}_price.svg"
        plt.savefig(output_path, format="svg", bbox_inches="tight")
        print(f"Saved SVG price plot to {output_path}")
        plt.close()

        return output_path
