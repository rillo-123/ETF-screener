"""Interactive Plotly-based plotting utilities for ETF analysis."""

import json
import re
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

logger = logging.getLogger(__name__)

class InteractivePlotter:
    """Plot ETF data with technical indicators using Plotly for interactivity."""

    def __init__(self, output_dir: str = "plots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.ribbon_config = self._load_ribbon_settings()

    def _load_ribbon_settings(self) -> dict:
        config_path = Path("config/ribbon_settings.json")
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not load ribbon settings: %s", e)
        return {"ribbons": []}

    def plot_etf_analysis(self, df: pd.DataFrame, symbol: str) -> Path:
        df = df.copy()
        # Ensure Date is datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        
        # Determine available ribbons
        ribbon_settings = self.ribbon_config.get("ribbons", [])
        active_ribbons = []
        available_cols = [c.lower() for c in df.columns]
        
        for rib in ribbon_settings:
            layers = rib.get("layers", [])
            ribbon_is_possible = False
            for layer in layers:
                condition = layer.get("condition", "").lower()
                words = re.findall(r'[a-z_][a-z0-9_]*', condition)
                if any(word in available_cols for word in words):
                    ribbon_is_possible = True
                    break
            if ribbon_is_possible or "supertrend" in rib.get("label", "").lower():
                active_ribbons.append(rib)

        num_ribbons = len(active_ribbons)
        # 1 (Price) + 1 (Volume) + N (Ribbons)
        # Ratios: Price=0.5, Volume=0.1, Ribbons=0.05 each
        row_heights = [0.5, 0.1] + [0.05] * num_ribbons
        
        fig = make_subplots(
            rows=2 + num_ribbons, 
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.02,
            row_heights=row_heights,
            subplot_titles=[f"{symbol} Analysis", "Volume"] + [""] * num_ribbons
        )

        # 1. Price Chart (Candlestick or Line)
        fig.add_trace(
            go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(color='black', width=1.5)),
            row=1, col=1
        )
        
        # Supertrend Price Overlay
        if "ST_Lower" in df.columns and "ST_Upper" in df.columns:
            # Mask for green segments (Support)
            green_mask = df["Close"] > df["ST_Lower"]
            support = np.where(green_mask, df["ST_Lower"], np.nan)
            resistance = np.where(~green_mask, df["ST_Upper"], np.nan)
            
            fig.add_trace(
                go.Scatter(x=df['Date'], y=support, name='ST Support', 
                          line=dict(color='green', width=1.5), connectgaps=False),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=df['Date'], y=resistance, name='ST Resistance', 
                          line=dict(color='red', width=1.5), connectgaps=False),
                row=1, col=1
            )
        
        # Add EMA 50 if it exists
        if 'EMA_50' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Date'], y=df['EMA_50'], name='EMA 50', line=dict(color='orange', width=1, dash='dot')),
                row=1, col=1
            )

        # Add Trigger Signals
        if 'Signal' in df.columns:
            buys = df[df['Signal'] == 1]
            sells = df[df['Signal'] == -1]
            
            fig.add_trace(
                go.Scatter(x=buys['Date'], y=buys['Close'], mode='markers', name='Buy',
                          marker=dict(symbol='triangle-up', size=12, color='blue')),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=sells['Date'], y=sells['Close'], mode='markers', name='Sell',
                          marker=dict(symbol='triangle-down', size=12, color='red')),
                row=1, col=1
            )

        # 2. Volume
        fig.add_trace(
            go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color='lightgray'),
            row=2, col=1
        )

        # 3. Ribbons
        for i, rib in enumerate(active_ribbons):
            row = 3 + i
            label = rib.get("label")
            
            # Prepare eval df for this ribbon
            eval_df = df.copy()
            for c in eval_df.columns:
                if pd.api.types.is_numeric_dtype(eval_df[c]):
                    # Interpolate/ffill to remove whitespace/gaps
                    eval_df[c] = eval_df[c].ffill()
            
            eval_df.columns = [c.lower() for c in eval_df.columns]

            for layer in rib.get("layers", []):
                condition = layer.get("condition", "").lower()
                color = layer.get("color")
                
                # Cleanup condition for eval
                clean_cond = condition.replace(" and ", " & ").replace(" or ", " | ")
                clean_cond = re.sub(r'([a-z0-9._]+(?:\s*[<>!=]+\s*[a-z0-9._]+)+)', r'(\1)', clean_cond)
                
                try:
                    mask = eval_df.eval(clean_cond, engine='python')
                    if isinstance(mask, pd.Series) and mask.any():
                        # Fill gaps in the mask itself if they are small (1-2 days)
                        # but keep it boolean
                        mask = mask.astype(float).interpolate(limit=2).fillna(0).astype(bool)

                        # Use Scatter with fill to create ribbons
                        fig.add_trace(
                            go.Scatter(
                                x=df['Date'], 
                                y=np.where(mask, 1, np.nan),
                                mode='lines',
                                line=dict(width=30, color=color),
                                showlegend=False,
                                connectgaps=True, # Allow Plotly to bridge small data gaps
                                name=f"{label} - {color}"
                            ),
                            row=row, col=1
                        )
                except:
                    continue
            
            fig.update_yaxes(showticklabels=False, range=[0, 1.5], row=row, col=1)

        return output_path

    def create_plot(self, df: pd.DataFrame, symbol: str) -> go.Figure:
        """
        Internal implementation that generates and returns the Plotly Figure object.
        Separated from file operations to allow direct use in web APIs.
        """
        df = df.copy()
        # Ensure Date is datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        
        # Determine available ribbons
        ribbon_settings = self.ribbon_config.get("ribbons", [])
        active_ribbons = []
        available_cols = [c.lower() for c in df.columns]
        
        for rib in ribbon_settings:
            layers = rib.get("layers", [])
            ribbon_is_possible = False
            for layer in layers:
                condition = layer.get("condition", "").lower()
                words = re.findall(r'[a-z_][a-z0-9_]*', condition)
                if any(word in available_cols for word in words):
                    ribbon_is_possible = True
                    break
            if ribbon_is_possible or "supertrend" in rib.get("label", "").lower():
                active_ribbons.append(rib)

        num_ribbons = len(active_ribbons)
        # 1 (Price) + 1 (Volume) + N (Ribbons)
        row_heights = [0.5, 0.1] + [0.05] * num_ribbons
        
        # We start with a clean subplot setup
        # Reverting to shared_xaxes=True but we will FIX the layout naming issue
        fig = make_subplots(
            rows=2 + num_ribbons, 
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03,
            row_heights=row_heights,
            subplot_titles=[f"{symbol} Analysis", "Volume"] + [""] * num_ribbons
        )

        # 1. Price Chart (Candlestick or Line)
        fig.add_trace(
            go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(color='black', width=1.5)),
            row=1, col=1
        )
        
        # Supertrend Price Overlay
        if "ST_Lower" in df.columns and "ST_Upper" in df.columns:
            # Mask for green segments (Support)
            green_mask = df["Close"] > df["ST_Lower"]
            support = np.where(green_mask, df["ST_Lower"], np.nan)
            resistance = np.where(~green_mask, df["ST_Upper"], np.nan)
            
            fig.add_trace(
                go.Scatter(x=df['Date'], y=support, name='ST Support', 
                          line=dict(color='green', width=1.5), connectgaps=False),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=df['Date'], y=resistance, name='ST Resistance', 
                          line=dict(color='red', width=1.5), connectgaps=False),
                row=1, col=1
            )
        
        # Add EMA 50 if it exists
        if 'EMA_50' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['Date'], y=df['EMA_50'], name='EMA 50', line=dict(color='orange', width=1, dash='dot')),
                row=1, col=1
            )

        # Add Trigger Signals
        if 'Signal' in df.columns:
            # Handle mixed case if needed from DB but usually normalized by app_fast now
            signal_col = 'Signal'
            buys = df[df[signal_col] == 1]
            sells = df[df[signal_col] == -1]
            if not buys.empty and 'Low' in df.columns:
                fig.add_trace(
                    go.Scatter(x=buys['Date'], y=buys['Low']*0.98, mode='markers', name='Buy Signal',
                               marker=dict(symbol='triangle-up', size=12, color='green')),
                    row=1, col=1
                )
            if not sells.empty and 'High' in df.columns:
                fig.add_trace(
                    go.Scatter(x=sells['Date'], y=sells['High']*1.02, mode='markers', name='Sell Signal',
                               marker=dict(symbol='triangle-down', size=12, color='red')),
                    row=1, col=1
                )

        # 2. Volume Chart
        colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green' for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color=colors, opacity=0.7),
            row=2, col=1
        )

        # 3. Indicator Ribbons
        for i, rib in enumerate(active_ribbons):
            row = 3 + i
            label = rib.get("label", "Indicator")
            layers = rib.get("layers", [])
            
            for layer in layers:
                color = layer.get("color", "gray")
                condition = layer.get("condition", "False")
                
                try:
                    # Replace variable names for evaluation
                    safe_cond = condition.replace("close", "df['Close']").replace("supertrend", "df['Supertrend']")
                    safe_cond = safe_cond.replace("st_upper", "df['ST_Upper']").replace("st_lower", "df['ST_Lower']")
                    mask = eval(safe_cond)
                    
                    if mask.any():
                        fig.add_trace(
                            go.Scatter(
                                x=df['Date'], 
                                y=np.where(mask, 1, np.nan),
                                mode='lines',
                                line=dict(width=30, color=color),
                                showlegend=False,
                                connectgaps=True,
                                name=f"{label} - {color}"
                            ),
                            row=row, col=1
                        )
                except:
                    continue
            
            fig.update_yaxes(showticklabels=False, range=[0, 1.5], row=row, col=1)

        # 4. Global configurations for all x-axes
        bottom_row = 2 + num_ribbons
        
        # Completely re-write the end of the method with dictionary-level precision
        fig_dict = fig.to_dict()
        layout = fig_dict['layout']
        
        # Enforce axis visibility and formatting on EVERY possible x-axis key in the layout
        for key in list(layout.keys()):
            if key.startswith('xaxis'):
                layout[key]['showticklabels'] = True
                layout[key]['visible'] = True
                layout[key]['type'] = 'date'
                layout[key]['tickformat'] = '%b %Y'
                layout[key]['gridcolor'] = 'lightgray'

        # Force professional global layout
        layout['template'] = 'plotly_white'
        layout['xaxis_rangeslider_visible'] = False
        layout['hovermode'] = 'x unified'
        layout['margin'] = dict(l=60, r=20, t=50, b=80) 
        
        return go.Figure(fig_dict)

    def plot_etf_analysis(self, df: pd.DataFrame, symbol: str) -> Path:
        fig = self.create_plot(df, symbol)
        output_path = self.output_dir / f"{symbol.lower()}_interactive.html"
        fig.write_html(str(output_path))
        return output_path
