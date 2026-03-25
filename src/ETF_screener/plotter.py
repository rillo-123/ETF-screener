"""Plotting utilities for ETF analysis."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import re
import json

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
        
        # Load ribbon settings
        self.ribbon_config = self._load_ribbon_settings()

    def _load_ribbon_settings(self) -> dict:
        """Load ribbon configuration from settings file."""
        import json
        config_path = Path("config/ribbon_settings.json")
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load ribbon settings: {e}")
        return {"ribbons": []}

    def plot_etf_analysis(
        self, df: pd.DataFrame, symbol: str, figsize: tuple = (14, 8), format: str = "svg"
    ) -> Path:
        """
        Create comprehensive ETF analysis plot.

        Args:
            df: DataFrame with OHLCV and indicator data
            symbol: ETF symbol
            figsize: Figure size tuple
            format: Output format ('svg' or 'png', default 'svg')

        Returns:
            Path to saved plot
        """
        # Resolve duplicate labels BEFORE any other operations
        df = df.copy()
        if df.columns.duplicated().any():
            # If we have duplicate column names, pandas gets confused during indexing
            # We explicitly keep only the first occurrence for each column name
            df = df.loc[:, ~df.columns.duplicated()].copy()

        # ... [Lines 42-43 already copied above]
        cols = []
        
        # Diagnostic: Print MACD series range
        is_oscillator = lambda c: any(x in c.lower() for x in ["rsi", "stoch", "macd", "adx"])
        
        macd_cols = [c for c in df.columns if "macd" in c.lower() and "hist" not in c.lower()]
        if macd_cols:
            m_s = df[macd_cols[0]].dropna()
            if not m_s.empty:
                if m_s.max() > 100 or m_s.min() < -100:
                    print(f"CRITICAL WARNING: {symbol} has extreme MACD values!")

        seen = set()
        for c in df.columns:
            c_str = str(c)
            # Standardize core columns
            if c_str.lower() in ['date', 'open', 'high', 'low', 'close', 'volume', 'signal']:
                new_col = c_str.capitalize()
            elif is_oscillator(c_str):
                # KEEP OSCILLATOR COLUMN NAMES ORIGINAL (no title case)
                new_col = c_str
            else:
                new_col = c_str
            
            # Final safety check against duplicates after capitalization
            if new_col in seen:
                continue
            cols.append(new_col)
            seen.add(new_col)
        
        # Don't trim df.iloc, just reassign columns if they match
        if len(cols) == len(df.columns):
            df.columns = cols
        
        # Identify special indicator columns for separate subplots
        # lambda is redefined below but used for clarity
        
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
        
        # Categorize oscillators (and trend) for dedicated ribbon subplots
        ribbon_settings = self.ribbon_config.get("ribbons", [])
        active_ribbons = []
        
        # Determine which ribbons we should actually plot based on available data
        # We now use a more robust check that looks at the conditions to see if required columns exist
        available_cols = [c.lower() for c in df.columns]
        for rib in ribbon_settings:
            # Check if any layer's condition can be evaluated with available columns
            layers = rib.get("layers", [])
            ribbon_is_possible = False
            for layer in layers:
                condition = layer.get("condition", "").lower()
                # Find all potential column names in the condition string
                words = re.findall(r'[a-z_][a-z0-9_]*', condition)
                # If any word in the condition is a column, we assume it's possible to plot it
                if any(word in available_cols for word in words):
                    ribbon_is_possible = True
                    break
            
            if ribbon_is_possible:
                active_ribbons.append(rib)
        
        # Total subplots is 2 (Price, Vol) + Ribbons
        num_subplots = 2 + len(active_ribbons)
        
        # Order: Price (4), Volume (1), Ribbons (0.3 each)
        height_ratios = [4, 1] + ([0.3] * len(active_ribbons))
        
        fig, axes = plt.subplots(
            num_subplots, 1, 
            figsize=(14, 4 + 1.2 + 0.3 * len(active_ribbons)), # Adjusted for tighter fit
            sharex=True, 
            gridspec_kw={'height_ratios': height_ratios, 'hspace': 0.05} # Even tighter spacing
        )
        
        if num_subplots == 2:
            ax1, ax_vol = axes[0], axes[1]
            ribbon_axes = []
        else:
            ax1 = axes[0]
            ax_vol = axes[1]
            ribbon_axes = axes[2:]

        # Plot 1: Price only (Close)
        price_col = "Close" if "Close" in df.columns else "close"
        ax1.plot(
            df["Date"], df[price_col], label="Close Price", color="black", linewidth=1.5
        )
        
        # Explicitly set y-limits to the robust range
        padding = p_range * 0.1 if p_range > 0 else 1.0
        ax1.set_ylim(p_min_robust - padding, p_max_robust + padding)
        
        # Signal markers
        sig_col = "Signal" if "Signal" in df.columns else "signal"
        buy_signals = df[df[sig_col] == 1]
        ax1.scatter(
            buy_signals["Date"],
            buy_signals[price_col],
            color="blue",
            marker="^",
            s=80,
            label="Trigger",
            zorder=5,
        )

        # Sell signals
        sell_signals = df[df[sig_col] == -1]
        ax1.scatter(
            sell_signals["Date"],
            sell_signals[price_col],
            color="red",
            marker="v",
            s=100,
            label="Sell Signal",
            zorder=5,
        )

        # Highlight profitable trade regions
        try:
            trade_df = df[df[sig_col].isin([1, -1])].copy()
            if not trade_df.empty:
                entry_idx = None
                for idx, row in trade_df.iterrows():
                    if row[sig_col] == 1:
                        entry_idx = idx
                    elif row[sig_col] == -1 and entry_idx is not None:
                        # Trade completed
                        exit_idx = idx
                        entry_price = df.loc[entry_idx, price_col]
                        exit_price = df.loc[exit_idx, price_col]
                        
                        color = "green" if exit_price > entry_price else "red"
                        # Fill between entry/exit dates
                        ax1.axvspan(df.loc[entry_idx, "Date"], df.loc[exit_idx, "Date"], 
                                   color=color, alpha=0.15, label="_nolegend_")
                        entry_idx = None
        except Exception as e:
            print(f"Warning: Could not highlight trade regions: {e}")

        ax1.set_ylabel("Price", fontsize=10)
        ax1.set_title(f"{symbol} - Technical Analysis", fontsize=12, fontweight="bold")
        ax1.legend(loc="upper left", fontsize=8)
        ax1.grid(True, alpha=0.2)

        # Plot Volume
        vol_col = "Volume" if "Volume" in df.columns else "volume"
        if vol_col in df.columns:
            ax_vol.bar(df["Date"], df[vol_col], color="gray", alpha=0.3)
            ax_vol.set_ylabel("Vol", fontsize=8)
            ax_vol.grid(True, alpha=0.2)
            # Remove y-ticks for volume to save space if needed
            ax_vol.get_yaxis().set_major_formatter(matplotlib.ticker.EngFormatter())

        # Plot Ribbon Panels
        for i, rib in enumerate(active_ribbons):
            osc_ax = ribbon_axes[i]
            label = rib.get("label", "Unknown")
            
            # Helper to find column case-insensitively
            def get_col(name):
                # Check for direct match first
                if name in df.columns: return name
                # Check lowercase
                for c in df.columns:
                    if str(c).lower() == name.lower():
                        return c
                return None

            # Helper to calculate condition mask
            def evaluate_simple_condition(expr, df_eval):
                try:
                    # Map expr to use df_eval columns
                    processed_expr = expr.lower()
                    
                    # 1. replace common operators
                    processed_expr = processed_expr.replace(" and ", " & ").replace(" or ", " | ")
                    
                    # 2. find all words and check if they are columns
                    words = re.findall(r'[a-z_][a-z0-9_]*', processed_expr)
                    for word in set(words):
                        actual_col = get_col(word)
                        if actual_col:
                            # Use backticks for pandas eval if name has spaces, but our names usually don't
                            processed_expr = re.sub(rf'\b{word}\b', f"`{actual_col}`", processed_expr)
                    
                    return df_eval.eval(processed_expr)
                except Exception as eval_e:
                    # Very simple fallback for "close > ema_50" or similar
                    return pd.Series([False] * len(df_eval), index=df_eval.index)

            # Create a local dict for eval that has lowercase keys pointing to actual columns
            eval_df = pd.DataFrame(index=df.index)
            for c in df.columns:
                if pd.api.types.is_numeric_dtype(df[c]):
                    eval_df[str(c).lower()] = df[c]
            
            for layer in rib.get("layers", []):
                condition = layer.get("condition", "")
                color = layer.get("color", "gray")
                alpha = layer.get("alpha", 0.6)
                
                try:
                    # Replace and/or with bitwise for eval and wrap comparisons
                    clean_cond = condition.lower()
                    
                    # Log what we are trying to evaluate
                    # print(f"DEBUG EVAL: Trying condition '{clean_cond}' for {label}")

                    # Replace common comparison with bitwise operators safely
                    clean_cond = clean_cond.replace(" and ", " & ").replace(" or ", " | ")
                    # Wrap segments to ensure precedence
                    clean_cond = re.sub(r'([a-z0-9._]+(?:\s*[<>!=]+\s*[a-z0-9._]+)+)', r'(\1)', clean_cond)
                    
                    # We use eval_df to ensure column lookup works case-insensitively
                    mask = eval_df.eval(clean_cond, engine='python')
                    
                    if isinstance(mask, (pd.Series, np.ndarray)):
                        # If it's a series, make it a numpy array for direct masking
                        mask_vals = getattr(mask, "values", mask)
                        mask_bool = np.asanyarray(mask_vals).astype(bool)
                        
                        if np.any(mask_bool):
                            # Use step='post' to match the data transitions correctly
                            osc_ax.fill_between(df["Date"], 0, 1, where=mask_bool, color=color, alpha=alpha, 
                                               step='post', transform=osc_ax.get_xaxis_transform())
                except Exception as eval_e:
                    # print(f"Ribbon eval error for '{condition}' in {label}: {eval_e}")
                    pass

            osc_ax.set_yticks([]) # No Y axis for ribbons
            osc_ax.set_ylabel(label, rotation=0, labelpad=30, verticalalignment='center', fontsize=9, fontweight="bold")
            osc_ax.set_ylim(0, 1)
            osc_ax.set_facecolor('#f0f0f0') # Light gray background for ribbons to see "missing" data
            osc_ax.grid(False) # Clean look for ribbons

        # Plot Volume
        ax_vol.bar(df["Date"], df["Volume"], color="steelblue", alpha=0.6)
        ax_vol.set_ylabel("Volume", fontsize=12)
        ax_vol.grid(True, alpha=0.3)

        # Format X-axis Dates (YYYY-MM-DD)
        all_axes = [ax1] + list(ribbon_axes) + [ax_vol]
        
        for ax in all_axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
            # Enable auto-formatting and show labels on ALL axes
            ax.tick_params(axis='x', labelbottom=True)
            plt.setp(ax.get_xticklabels(), visible=True, rotation=0, ha='center', fontsize=6)
            
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

        # Save figure as specified format
        ext = format.lower()
        output_path = self.output_dir / f"{symbol.lower()}_analysis.{ext}"
        
        plt.savefig(output_path, format=ext, bbox_inches="tight")
        plt.close()

        return output_path

    def plot_multiple_etfs(self, etf_dict: dict[str, pd.DataFrame], format: str = "svg") -> dict:
        """
        Create analysis plots for multiple ETFs.

        Args:
            etf_dict: Dictionary mapping symbol to DataFrame
            format: Output format ('svg' or 'png', default 'svg')

        Returns:
            Dictionary mapping symbol to plot path
        """
        results = {}
        for symbol, df in etf_dict.items():
            try:
                results[symbol] = self.plot_etf_analysis(df, symbol, format=format)
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
            plots = sorted([f.name for f in self.output_dir.glob(f"*.{format.lower()}") or []])
            
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

    def plot_price_only(self, df: pd.DataFrame, symbol: str, format: str = "svg") -> Path:
        """
        Create a simple price plot.

        Args:
            df: DataFrame with price data
            symbol: ETF symbol
            format: Output format ('svg' or 'png', default 'svg')

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

        ext = format.lower()
        output_path = self.output_dir / f"{symbol.lower()}_price.{ext}"
        plt.savefig(output_path, format=ext, bbox_inches="tight")
        print(f"Saved {ext.upper()} price plot to {output_path}")
        plt.close()

        return output_path
