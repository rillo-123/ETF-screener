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

    def _build_strategy_layer_ribbons(self, strategy_content: str | None) -> list[dict]:
        """Build dynamic ribbon layers from DSL comments/sections."""
        if not strategy_content:
            return []

        layer_exprs = {1: [], 2: [], 3: [], 4: []}
        current_layer = None
        default_map = {"TRIGGER": 3, "ENTRY": 3, "FILTER": 2, "EXIT": 4}

        def _keyword_to_layer(keyword: str | None) -> int | None:
            if not keyword:
                return None
            k = keyword.strip().lower()
            m = re.match(r'^layer\s*([1-4])$', k)
            if m:
                return int(m.group(1))
            m = re.match(r'^layer[_-]?([1-4])$', k)
            if m:
                return int(m.group(1))
            m = re.match(r'^l([1-4])$', k)
            if m:
                return int(m.group(1))
            alias = {
                "context": 1,
                "setup": 2,
                "trigger": 3,
                "risk": 4,
            }
            if k in alias:
                return alias[k]

            # Descriptive identifiers (e.g. CONTEXT_REGIME, SETUP_PULLBACK).
            # We map by semantic prefix to keep future naming flexible.
            if k.startswith("context"):
                return 1
            if k.startswith("setup"):
                return 2
            if k.startswith("trigger"):
                return 3
            if k.startswith("risk"):
                return 4
            return None

        for raw in strategy_content.splitlines():
            line = raw.strip()
            if not line:
                continue

            # Block syntax support:
            # 1) BEGIN <keyword>
            # 2) <keyword> BEGIN
            begin_prefix = re.match(r'^begin\s+(.+)$', line, re.IGNORECASE)
            if begin_prefix:
                current_layer = _keyword_to_layer(begin_prefix.group(1))
                continue

            begin_suffix = re.match(r'^(.+?)\s+begin\b', line, re.IGNORECASE)
            if begin_suffix:
                current_layer = _keyword_to_layer(begin_suffix.group(1))
                continue

            if re.match(r'^end\b', line, re.IGNORECASE):
                current_layer = None
                continue

            if re.match(r'^begin\b', line, re.IGNORECASE):
                continue

            layer_match = re.match(r'^#\s*layer\s*([1-4])\b', line, re.IGNORECASE)
            if layer_match:
                current_layer = int(layer_match.group(1))
                continue

            if line.startswith("#"):
                continue

            section = re.match(r'^(TRIGGER|FILTER|ENTRY|EXIT):\s*(.+)$', line, re.IGNORECASE)
            if not section:
                continue

            section_name = section.group(1).upper()
            expr = section.group(2).strip()
            if not expr:
                continue

            layer_idx = current_layer if current_layer in layer_exprs else default_map.get(section_name, 2)
            layer_exprs[layer_idx].append(f"({expr})")

        layer_style = {
            1: {"label": "Layer 1 Context", "color": "#2563eb", "alpha": 0.60},
            2: {"label": "Layer 2 Setup", "color": "#f59e0b", "alpha": 0.60},
            3: {"label": "Layer 3 Trigger", "color": "#16a34a", "alpha": 0.70},
            4: {"label": "Layer 4 Risk", "color": "#dc2626", "alpha": 0.60},
        }

        ribbons = []
        for i in (1, 2, 3, 4):
            if not layer_exprs[i]:
                continue
            ribbons.append({
                "label": layer_style[i]["label"],
                "layers": [{
                    "condition": " AND ".join(layer_exprs[i]),
                    "color": layer_style[i]["color"],
                    "alpha": layer_style[i]["alpha"],
                }],
            })

        # Add a synthesized readiness ribbon when the full entry chain exists.
        # This gives one concise go/no-go visual for layered strategies.
        if layer_exprs[1] and layer_exprs[2] and layer_exprs[3]:
            entry_ready_cond = " AND ".join([
                f"({' AND '.join(layer_exprs[1])})",
                f"({' AND '.join(layer_exprs[2])})",
                f"({' AND '.join(layer_exprs[3])})",
            ])
            ribbons.append({
                "label": "Entry Ready (L1+L2+L3)",
                "layers": [{
                    "condition": entry_ready_cond,
                    "color": "#06b6d4",
                    "alpha": 0.85,
                }],
            })
        return ribbons

    def _extract_ema_periods(self, strategy_content: str | None) -> list[int]:
        """Extract EMA periods referenced in DSL content (e.g. ema_50, ema_200)."""
        if not strategy_content:
            return []
        periods = {int(m.group(1)) for m in re.finditer(r'\bema_(\d+)\b', strategy_content.lower())}
        return sorted(periods)

    def _shift_expr_symbols(self, expr: str, delay: int) -> str:
        reserved = {"and", "or", "not", "true", "false", "cross_up", "cross_down", "was_true"}

        def repl(m):
            word = m.group(1)
            if word in reserved:
                return word
            if re.fullmatch(r'\d+(?:\.\d+)?', word):
                return word
            if f"_d{delay}" in word:
                return word
            return f"{word}_d{delay}"

        return re.sub(r'([a-z][a-z0-9_]*)\b', repl, expr)

    def _prepare_eval_columns(self, eval_df: pd.DataFrame, condition: str) -> pd.DataFrame:
        words = set(re.findall(r'[a-z][a-z0-9_]*', condition))

        for w in words:
            delay_match = re.search(r'_d(\d+)$', w)
            if delay_match:
                base = re.sub(r'_d\d+$', '', w)
                delay = int(delay_match.group(1))
                if base in eval_df.columns and w not in eval_df.columns:
                    eval_df[w] = eval_df[base].shift(delay)
                continue

            if w.endswith('_slope'):
                base = w[:-6]
                if base in eval_df.columns and w not in eval_df.columns:
                    eval_df[w] = eval_df[base].diff().fillna(0)

        if 'st_10_4_is_green' in words and 'st_10_4_is_green' not in eval_df.columns:
            if 'close' in eval_df.columns and 'st_lower' in eval_df.columns:
                eval_df['st_10_4_is_green'] = (eval_df['close'] > eval_df['st_lower']).astype(float)

        return eval_df

    def _to_eval_condition(self, condition: str) -> str:
        s = condition.lower()

        def wt_repl(m):
            expr = m.group(1).strip()
            delay = int(m.group(2).strip())
            return f"({self._shift_expr_symbols(expr, delay)})"

        s = re.sub(r'was_true\s*\(([^,]+),\s*(\d+)\s*\)', wt_repl, s)

        def cross_up_repl(m):
            a = m.group(1).strip()
            b = m.group(2).strip()
            ad = self._shift_expr_symbols(a, 1)
            bd = self._shift_expr_symbols(b, 1)
            return f"(({a}) > ({b}) & ({ad}) <= ({bd}))"

        def cross_down_repl(m):
            a = m.group(1).strip()
            b = m.group(2).strip()
            ad = self._shift_expr_symbols(a, 1)
            bd = self._shift_expr_symbols(b, 1)
            return f"(({a}) < ({b}) & ({ad}) >= ({bd}))"

        s = re.sub(r'cross_up\s*\(([^,]+),\s*([^)]+)\)', cross_up_repl, s)
        s = re.sub(r'cross_down\s*\(([^,]+),\s*([^)]+)\)', cross_down_repl, s)

        s = re.sub(r'\band\b', ' & ', s)
        s = re.sub(r'\bor\b', ' | ', s)
        s = re.sub(r'([a-z0-9._]+(?:\s*[<>!=]+\s*[a-z0-9._]+)+)', r'(\1)', s)
        s = re.sub(r'\b(\d+(?:\.\d+)?)([km])\b', lambda m: str(int(float(m.group(1)) * (1000 if m.group(2) == 'k' else 1000000)),), s)
        return s

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

    def create_plot(self, df: pd.DataFrame, symbol: str, strategy_content: str | None = None) -> go.Figure:
        """
        Internal implementation that generates and returns the Plotly Figure object.
        Separated from file operations to allow direct use in web APIs.
        """
        df = df.copy()
        # Ensure Date is datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        
        # Determine available ribbons.
        # Strategy-focused mode: if we have layer ribbons from DSL, show those only.
        layer_ribbons = self._build_strategy_layer_ribbons(strategy_content)
        if layer_ribbons:
            ribbon_settings = layer_ribbons
        else:
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

        # Add only EMA curves that are explicitly referenced by the active strategy.
        ema_periods = self._extract_ema_periods(strategy_content)
        ema_colors = ["#f59e0b", "#3b82f6", "#10b981", "#ef4444", "#8b5cf6", "#14b8a6"]
        for idx, period in enumerate(ema_periods):
            lower_col = f"ema_{period}"
            upper_col = f"EMA_{period}"
            ema_col = lower_col if lower_col in df.columns else (upper_col if upper_col in df.columns else None)
            if not ema_col:
                continue
            fig.add_trace(
                go.Scatter(
                    x=df['Date'],
                    y=df[ema_col],
                    name=f"EMA {period}",
                    line=dict(color=ema_colors[idx % len(ema_colors)], width=1.2, dash='dot')
                ),
                row=1,
                col=1,
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

            eval_df = df.copy()
            for c in eval_df.columns:
                if pd.api.types.is_numeric_dtype(eval_df[c]):
                    eval_df[c] = eval_df[c].ffill()
            eval_df.columns = [c.lower() for c in eval_df.columns]
            eval_df = eval_df.loc[:, ~eval_df.columns.duplicated()]
            
            for layer in layers:
                color = layer.get("color", "gray")
                alpha = layer.get("alpha", 0.8)
                condition = layer.get("condition", "False")
                
                try:
                    clean_cond = self._to_eval_condition(condition)
                    eval_df = self._prepare_eval_columns(eval_df, clean_cond)
                    mask = eval_df.eval(clean_cond, engine='python')
                    
                    if isinstance(mask, pd.Series) and mask.any():
                        mask = mask.astype(float).interpolate(limit=2).fillna(0).astype(bool)
                        fig.add_trace(
                            go.Scatter(
                                x=df['Date'], 
                                y=np.where(mask, 1, np.nan),
                                mode='lines',
                                line=dict(width=30, color=color),
                                opacity=alpha,
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
