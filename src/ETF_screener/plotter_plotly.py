"""Interactive Plotly-based plotting utilities for ETF analysis."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RibbonLayoutConfig:
    """Parameterized layout settings for ribbon-heavy charts."""

    price_panel_px: int
    volume_panel_px: int
    target_lane_px: int
    min_lane_px: int
    max_total_height_px: int


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
                    return json.load(f)  # type: ignore[no-any-return]
            except Exception as e:
                logger.warning("Could not load ribbon settings: %s", e)
        return {"ribbons": []}

    def _layout_numeric_setting(self, key: str, default: float) -> float:
        """Read numeric chart layout setting from config/ribbon_settings.json."""
        layout_cfg = (
            self.ribbon_config.get("layout", {})
            if isinstance(self.ribbon_config, dict)
            else {}
        )
        raw = layout_cfg.get(key, default)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return float(default)

    def _dsl_layer_style(self, layer_key: str, defaults: dict) -> dict:
        """Read configurable DSL layer style (label/color/alpha/height) from settings."""
        if not isinstance(self.ribbon_config, dict):
            return defaults

        styles_cfg = self.ribbon_config.get("dsl_layer_styles", {})
        layer_cfg = (
            styles_cfg.get(layer_key, {}) if isinstance(styles_cfg, dict) else {}
        )

        out = {
            "label": str(layer_cfg.get("label", defaults["label"])),
            "color": str(layer_cfg.get("color", defaults["color"])),
            "alpha": defaults["alpha"],
            "height_multiplier": defaults.get("height_multiplier", 1.0),
        }
        try:
            out["alpha"] = float(layer_cfg.get("alpha", defaults["alpha"]))
        except (TypeError, ValueError):
            out["alpha"] = float(defaults["alpha"])
        try:
            hm = float(
                layer_cfg.get(
                    "height_multiplier", defaults.get("height_multiplier", 1.0)
                )
            )
            out["height_multiplier"] = max(0.5, min(2.5, hm))
        except (TypeError, ValueError):
            out["height_multiplier"] = float(defaults.get("height_multiplier", 1.0))
        return out

    def _aggregate_fill_condition(self) -> str:
        """Read aggregate fill condition expression from config/ribbon_settings.json."""
        if not isinstance(self.ribbon_config, dict):
            return "context and trigger"

        aggregate_cfg = self.ribbon_config.get("aggregate", {})
        raw = aggregate_cfg.get(
            "fill_condition", aggregate_cfg.get("fill_mode", "context_and_trigger")
        )
        return self._aggregate_fill_condition_alias(str(raw))

    def _eval_rule_when(self, when_expr: str, block_presence: dict[str, bool]) -> bool:
        """Evaluate a rule `when` expression using IsContext/IsSetup/IsTrigger/IsRisk flags."""
        expr = str(when_expr or "").strip()
        if not expr:
            return False

        normalized = expr.lower().replace("&&", " and ").replace("||", " or ")
        normalized = normalized.replace("!", " not ")
        normalized = normalized.replace("_and_", " and ").replace("_or_", " or ")

        token_map = {
            "iscontext": block_presence.get("context", False),
            "issetup": block_presence.get("setup", False),
            "istrigger": block_presence.get("trigger", False),
            "isrisk": block_presence.get("risk", False),
        }
        for token, value in token_map.items():
            normalized = re.sub(
                rf"\b{token}\b", "True" if value else "False", normalized
            )

        try:
            return bool(eval(normalized, {"__builtins__": {}}, {}))
        except Exception:
            return False

    def _resolve_aggregate_expression(self, block_presence: dict[str, bool]) -> str:
        """Resolve aggregate fill expression, optionally via config-defined conditional rules."""
        if not isinstance(self.ribbon_config, dict):
            return "context and trigger"

        aggregate_cfg = self.ribbon_config.get("aggregate", {})
        rules = aggregate_cfg.get("rules", []) if isinstance(aggregate_cfg, dict) else []
        if isinstance(rules, list):
            for rule in rules:
                if not isinstance(rule, dict):
                    continue

                when_expr = str(rule.get("when", "")).strip()
                if not when_expr:
                    continue

                if not self._eval_rule_when(when_expr, block_presence):
                    continue

                raw_expr = rule.get(
                    "aggregate", rule.get("fill_condition", rule.get("expression", ""))
                )
                candidate = str(raw_expr or "").strip()
                if candidate:
                    return self._aggregate_fill_condition_alias(candidate)

        return self._aggregate_fill_condition()

    def _aggregate_fill_condition_alias(self, condition: str) -> str:
        """Normalize aliases for aggregate expressions to canonical expression strings."""
        cond = str(condition).strip().lower()
        alias_map = {
            "strict": "context and trigger",
            "context_and_trigger": "context and trigger",
            "context+trigger": "context and trigger",
            "context_trigger": "context and trigger",
            "permissive": "in_position",
            "signal_state": "in_position",
            "in_position": "in_position",
        }
        return alias_map.get(cond, cond)

    def _get_ribbon_layout(self, num_ribbons: int) -> dict:
        """Compute scalable panel/lane layout so all ribbons keep the same size."""
        cfg = RibbonLayoutConfig(
            price_panel_px=int(self._layout_numeric_setting("price_panel_px", 460)),
            volume_panel_px=int(self._layout_numeric_setting("volume_panel_px", 130)),
            target_lane_px=int(self._layout_numeric_setting("ribbon_lane_px", 20)),
            min_lane_px=int(self._layout_numeric_setting("ribbon_min_lane_px", 6)),
            max_total_height_px=int(
                self._layout_numeric_setting("max_plot_height_px", 2600)
            ),
        )

        lane_count = 1 + max(0, num_ribbons)  # aggregated lane + ribbon lanes
        fixed_px = cfg.price_panel_px + cfg.volume_panel_px
        available_for_lanes = max(
            cfg.max_total_height_px - fixed_px, lane_count * cfg.min_lane_px
        )
        lane_px = max(
            cfg.min_lane_px, min(cfg.target_lane_px, available_for_lanes // lane_count)
        )

        total_height_px = fixed_px + (lane_px * lane_count)
        raw_heights = [cfg.price_panel_px, cfg.volume_panel_px] + [lane_px] * lane_count
        normalizer = float(sum(raw_heights)) if raw_heights else 1.0
        row_heights = [h / normalizer for h in raw_heights]

        # Keep stroke proportional to lane height but safely visible.
        lane_line_width = max(8, int(lane_px * 0.95))

        return {
            "row_heights": row_heights,
            "figure_height_px": int(total_height_px),
            "lane_line_width": lane_line_width,
        }

    def _build_strategy_layer_ribbons(self, strategy_content: str | None) -> list[dict]:
        """Build dynamic ribbon layers from DSL block names — block name is the single source of truth for labels."""
        if not strategy_content:
            return []

        # Canonical aliases map a block name to a layer slot and a preferred style key.
        _CANONICAL_ALIAS = {
            "context": (1, "context"),
            "setup": (2, "setup"),
            "trigger": (3, "trigger"),
            "risk": (4, "risk"),
            "entry": (3, "trigger"),
            "exit": (4, "risk"),
        }
        # Prefix fallback (e.g. CONTEXT_REGIME → context)
        _CANONICAL_PREFIX_ORDER = [
            "context",
            "setup",
            "trigger",
            "risk",
            "entry",
            "exit",
        ]

        # Alternating palette for extra/unrecognised blocks.
        _EXTRA_COLORS = [
            "#7c3aed",
            "#0891b2",
            "#b45309",
            "#be185d",
            "#065f46",
            "#1e40af",
        ]

        default_map = {"TRIGGER": 3, "ENTRY": 3, "FILTER": 2, "EXIT": 4}

        # Ordered list of (block_name_raw, layer_slot) pairs encountered in the file.
        # We preserve encounter order so ribbons appear top→bottom in DSL order.
        block_order: list[tuple[str, int]] = []
        block_exprs: dict[str, list[str]] = {}  # raw_block_name → conditions
        current_block: str | None = None
        current_layer: int | None = None

        def _resolve_block(raw_name: str) -> tuple[int, str]:
            """Return (layer_slot, style_key) for a block name."""
            k = raw_name.strip().lower()
            # Exact match
            m = re.match(r"^layer\s*([1-4])$", k) or re.match(r"^l([1-4])$", k)
            if m:
                return (
                    int(m.group(1)),
                    list(_CANONICAL_ALIAS.keys())[int(m.group(1)) - 1],
                )
            if k in _CANONICAL_ALIAS:
                return _CANONICAL_ALIAS[k]
            for prefix in _CANONICAL_PREFIX_ORDER:
                if k.startswith(prefix):
                    return _CANONICAL_ALIAS[prefix]
            return 2, ""  # unknown → treat as setup slot

        for raw in strategy_content.splitlines():
            line = raw.strip()
            if not line:
                continue

            begin_prefix = re.match(r"^begin\s+(.+)$", line, re.IGNORECASE)
            begin_suffix = re.match(r"^(.+?)\s+begin\b", line, re.IGNORECASE)

            if begin_prefix:
                raw_name = begin_prefix.group(1).strip()
                current_block = raw_name
                current_layer, _ = _resolve_block(raw_name)
                if raw_name not in block_exprs:
                    block_exprs[raw_name] = []
                    block_order.append((raw_name, current_layer))
                continue

            if begin_suffix:
                raw_name = begin_suffix.group(1).strip()
                current_block = raw_name
                current_layer, _ = _resolve_block(raw_name)
                if raw_name not in block_exprs:
                    block_exprs[raw_name] = []
                    block_order.append((raw_name, current_layer))
                continue

            if re.match(r"^end\b", line, re.IGNORECASE):
                current_block = None
                current_layer = None
                continue

            if re.match(r"^begin\b", line, re.IGNORECASE):
                continue

            layer_match = re.match(r"^#\s*layer\s*([1-4])\b", line, re.IGNORECASE)
            if layer_match:
                current_layer = int(layer_match.group(1))
                continue

            if line.startswith("#"):
                continue

            section = re.match(
                r"^(TRIGGER|FILTER|ENTRY|EXIT):\s*(.+)$", line, re.IGNORECASE
            )
            if not section:
                continue

            expr = section.group(2).strip()
            if not expr:
                continue

            if current_block:
                block_exprs[current_block].append(f"({expr})")
            else:
                # No explicit block — fall back to section keyword → layer slot.
                slot = (
                    current_layer
                    if current_layer
                    else default_map.get(section.group(1).upper(), 2)
                )
                fallback_name = {1: "Context", 2: "Setup", 3: "Trigger", 4: "Risk"}.get(
                    slot, "Block"
                )
                if fallback_name not in block_exprs:
                    block_exprs[fallback_name] = []
                    block_order.append((fallback_name, slot))
                block_exprs[fallback_name].append(f"({expr})")

        # Build palette: canonical blocks get their configured color; extras get alternating colors.
        layer_style_cache = {
            1: self._dsl_layer_style(
                "context", {"label": "Context", "color": "#2563eb", "alpha": 0.60}
            ),
            2: self._dsl_layer_style(
                "setup", {"label": "Setup", "color": "#f59e0b", "alpha": 0.60}
            ),
            3: self._dsl_layer_style(
                "trigger", {"label": "Trigger", "color": "#16a34a", "alpha": 0.70}
            ),
            4: self._dsl_layer_style(
                "risk", {"label": "Risk", "color": "#dc2626", "alpha": 0.60}
            ),
        }
        extra_idx = 0
        seen_slots: set[int] = set()

        ribbons = []
        for block_name, slot in block_order:
            exprs = block_exprs.get(block_name, [])
            if not exprs:
                continue
            # Use canonical style for first occurrence of each slot; alternate color for subsequent.
            if slot not in seen_slots:
                style = layer_style_cache.get(slot, {"color": "#6b7280", "alpha": 0.6})
                color = style["color"]
                alpha = style.get("alpha", 0.6)
                seen_slots.add(slot)
            else:
                color = _EXTRA_COLORS[extra_idx % len(_EXTRA_COLORS)]
                alpha = 0.65
                extra_idx += 1

            ribbons.append(
                {
                    "label": block_name.title(),  # DSL block name is the label — single source of truth
                    "condition": " AND ".join(exprs),
                    "color": color,
                    "alpha": alpha,
                }
            )

        return ribbons

    def _extract_ema_periods(self, strategy_content: str | None) -> list[int]:
        """Extract EMA periods referenced in DSL content (e.g. ema_50, ema_200)."""
        if not strategy_content:
            return []
        periods = {
            int(m.group(1))
            for m in re.finditer(r"\bema_(\d+)\b", strategy_content.lower())
        }
        return sorted(periods)

    def _extract_supertrend_specs(
        self, strategy_content: str | None
    ) -> list[tuple[int, str]]:
        """Extract Supertrend specs referenced in DSL content (e.g. st_10_4, st_10_4_is_green)."""
        if not strategy_content:
            return []

        specs: set[tuple[int, str]] = set()
        pattern = r"\b(?:st|supertrend)_(\d+)_(\d+(?:\.\d+)?)(?:_is_(?:green|red))?\b"
        for m in re.finditer(pattern, strategy_content.lower()):
            period = int(m.group(1))
            mult_raw = m.group(2)
            try:
                mult_num = float(mult_raw)
                mult = (
                    str(int(mult_num))
                    if mult_num.is_integer()
                    else str(mult_num).rstrip("0").rstrip(".")
                )
            except (TypeError, ValueError):
                mult = mult_raw
            specs.add((period, mult))

        return sorted(specs)

    def _compact_ribbon_label(self, label: str) -> str:
        # Label comes directly from the DSL block name — return as-is.
        return label

    def _compact_ribbon_label_color(self, label: str) -> str:
        if isinstance(self.ribbon_config, dict):
            styles_cfg = self.ribbon_config.get("dsl_layer_styles", {})
            if isinstance(styles_cfg, dict):
                for cfg in styles_cfg.values():
                    if not isinstance(cfg, dict):
                        continue
                    cfg_label = str(cfg.get("label", "")).strip()
                    cfg_color = cfg.get("color")
                    if (
                        cfg_label
                        and cfg_label == label
                        and isinstance(cfg_color, str)
                        and cfg_color.strip()
                    ):
                        return cfg_color.strip()

        color_map = {
            "Layer 1 Context": "#3b82f6",
            "Layer 2 Setup": "#d97706",
            "Layer 3 Trigger": "#15803d",
            "Layer 4 Risk": "#b91c1c",
        }
        return color_map.get(label, "#6b7280")

    def _isolated_true_mask(self, mask: np.ndarray) -> np.ndarray:
        """Return a boolean mask of active points that do not touch an active neighbor."""
        mask_bool = np.asarray(mask, dtype=bool)
        if mask_bool.size == 0:
            return mask_bool

        prev_active = np.roll(mask_bool, 1)
        next_active = np.roll(mask_bool, -1)
        prev_active[0] = False
        next_active[-1] = False
        return mask_bool & ~prev_active & ~next_active

    def _draw_ribbon_mask_trace(
        self,
        fig,
        x_values,
        mask,
        row: int,
        color: str,
        lane_width: int,
        name: str,
        hovertemplate: str | None,
        show_markers: bool = False,
        alpha: float = 1.0,
    ) -> None:
        """Draw a ribbon overlay as one discrete bar per data point, aligned to candlestick x positions."""
        _ = show_markers
        lane_min, lane_max = 0.9, 1.1
        lane_span = lane_max - lane_min
        bucket_ms = self._time_bucket_width_ms(x_values)
        mask_arr = np.asarray(mask, dtype=bool)
        fig.add_trace(
            go.Bar(
                x=x_values,
                y=np.where(mask_arr, lane_span, 0.0),
                base=lane_min,
                width=bucket_ms,
                marker=dict(color=color, line=dict(width=0)),
                opacity=alpha,
                showlegend=False,
                name=name,
                hovertemplate=hovertemplate,
            ),
            row=row,
            col=1,
        )

    def _time_bucket_width_ms(self, x_values) -> float:
        """Estimate a sensible bar width from the visible time spacing."""
        try:
            dt = pd.to_datetime(pd.Series(x_values)).dropna().sort_values()
        except Exception:
            return 24 * 60 * 60 * 1000

        if len(dt) < 2:
            return 24 * 60 * 60 * 1000

        diffs = dt.diff().dropna()
        if diffs.empty:
            return 24 * 60 * 60 * 1000

        median_ms = float(diffs.median().total_seconds() * 1000.0)
        return max(6 * 60 * 60 * 1000, median_ms)

    def _shift_expr_symbols(self, expr: str, delay: int) -> str:
        reserved = {
            "and",
            "or",
            "not",
            "true",
            "false",
            "cross_up",
            "cross_down",
            "was_true",
        }

        def repl(m):
            word = m.group(1)
            if word in reserved:
                return word
            if re.fullmatch(r"\d+(?:\.\d+)?", word):
                return word
            if f"_d{delay}" in word:
                return word
            return f"{word}_d{delay}"

        return re.sub(r"([a-z][a-z0-9_]*)\b", repl, expr)

    def _prepare_eval_columns(
        self, eval_df: pd.DataFrame, condition: str
    ) -> pd.DataFrame:
        words = set(re.findall(r"[a-z][a-z0-9_]*", condition))

        def _ensure_st_green_column(col_name: str) -> None:
            if not col_name.endswith("_is_green"):
                return
            # Do NOT trust a pre-existing column: it may be a stale float stored in
            # the DB (e.g. st_10_4_is_green=1.0 even while price is below the ST
            # upper band).  Always recompute from the live ST line when possible.
            if "close" not in eval_df.columns:
                return

            base_st = col_name[:-9]  # strip '_is_green'
            if base_st in eval_df.columns:
                eval_df[col_name] = (
                    (eval_df["close"] > eval_df[base_st]).fillna(False).astype(bool)
                )
                return

            if base_st.startswith("st_"):
                alt = f"supertrend_{base_st[3:]}"
                if alt in eval_df.columns:
                    eval_df[col_name] = (
                        (eval_df["close"] > eval_df[alt]).fillna(False).astype(bool)
                    )
                    return
            if base_st.startswith("supertrend_"):
                alt = f"st_{base_st[11:]}"
                if alt in eval_df.columns:
                    eval_df[col_name] = (
                        (eval_df["close"] > eval_df[alt]).fillna(False).astype(bool)
                    )
                    return

            if "supertrend" in eval_df.columns:
                eval_df[col_name] = (
                    (eval_df["close"] > eval_df["supertrend"])
                    .fillna(False)
                    .astype(bool)
                )
                return
            if "st_lower" in eval_df.columns:
                # Last-resort fallback for legacy data frames missing supertrend line.
                eval_df[col_name] = (
                    (eval_df["close"] > eval_df["st_lower"]).fillna(False).astype(bool)
                )

        for w in words:
            delay_match = re.search(r"_d(\d+)$", w)
            if delay_match:
                base = re.sub(r"_d\d+$", "", w)
                delay = int(delay_match.group(1))
                _ensure_st_green_column(base)
                if base in eval_df.columns and w not in eval_df.columns:
                    shifted = eval_df[base].shift(delay)
                    if base.endswith("_is_green"):
                        shifted = shifted.eq(True)
                    eval_df[w] = shifted
                continue

            if w.endswith("_slope"):
                base = w[:-6]
                if base in eval_df.columns and w not in eval_df.columns:
                    eval_df[w] = eval_df[base].diff().fillna(0)

        for w in words:
            _ensure_st_green_column(w)
            if w in eval_df.columns and w.endswith("_is_green"):
                eval_df[w] = eval_df[w].eq(True)

        return eval_df

    def _to_eval_condition(self, condition: str) -> str:
        s = condition.lower()

        def wt_repl(m):
            expr = m.group(1).strip()
            delay = int(m.group(2).strip())
            return f"({self._shift_expr_symbols(expr, delay)})"

        s = re.sub(r"was_true\s*\(([^,]+),\s*(\d+)\s*\)", wt_repl, s)

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

        s = re.sub(r"cross_up\s*\(([^,]+),\s*([^)]+)\)", cross_up_repl, s)
        s = re.sub(r"cross_down\s*\(([^,]+),\s*([^)]+)\)", cross_down_repl, s)

        s = re.sub(r"\band\b", " & ", s)
        s = re.sub(r"\bor\b", " | ", s)
        s = re.sub(r"([a-z0-9._]+(?:\s*[<>!=]+\s*[a-z0-9._]+)+)", r"(\1)", s)
        s = re.sub(
            r"\b(\d+(?:\.\d+)?)([km])\b",
            lambda m: str(
                int(float(m.group(1)) * (1000 if m.group(2) == "k" else 1000000)),
            ),
            s,
        )
        return s

    def create_plot(
        self, df: pd.DataFrame, symbol: str, strategy_content: str | None = None
    ) -> go.Figure:
        """
        Internal implementation that generates and returns the Plotly Figure object.
        Separated from file operations to allow direct use in web APIs.
        """
        df = df.copy()
        # Ensure Date is datetime
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])

        # Determine available ribbons.
        # Strategy-focused mode: when DSL is provided, use only DSL-derived ribbons.
        if strategy_content and strategy_content.strip():
            ribbon_settings = self._build_strategy_layer_ribbons(strategy_content)
            # Do not pre-filter DSL ribbons by currently present columns.
            # Some expressions (e.g. was_true(st_10_4_is_green, 10)) require
            # derived helper columns materialized later during eval prep.
            active_ribbons = ribbon_settings
        else:
            ribbon_settings = self.ribbon_config.get("ribbons", [])
            active_ribbons = []
            available_cols = [c.lower() for c in df.columns]

            for rib in ribbon_settings:
                ribbon_condition = str(rib.get("condition", "")).lower().strip()
                layers = rib.get("layers", [])
                ribbon_is_possible = False
                conditions_to_check = (
                    [ribbon_condition]
                    if ribbon_condition
                    else [str(layer.get("condition", "")).lower() for layer in layers]
                )
                for condition in conditions_to_check:
                    words = re.findall(r"[a-z_][a-z0-9_]*", condition)
                    if any(word in available_cols for word in words):
                        ribbon_is_possible = True
                        break
                if ribbon_is_possible or "supertrend" in rib.get("label", "").lower():
                    active_ribbons.append(rib)

        num_ribbons = len(active_ribbons)
        layout_spec = self._get_ribbon_layout(num_ribbons)
        row_heights = layout_spec["row_heights"]
        lane_line_width = layout_spec["lane_line_width"]

        # We start with a clean subplot setup
        # Reverting to shared_xaxes=True but we will FIX the layout naming issue
        fig = make_subplots(
            rows=3 + num_ribbons,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.0,
            row_heights=row_heights,
            subplot_titles=[f"{symbol} Analysis", "Volume", "Buy/Sell Conditions"]
            + [""] * num_ribbons,
        )

        # Drop empty subplot-title annotations so ribbon lanes don't reserve extra headroom.
        if getattr(fig.layout, "annotations", None):
            fig.layout.annotations = tuple(
                a for a in fig.layout.annotations if str(getattr(a, "text", "")).strip()
            )

        fig.update_layout(height=layout_spec["figure_height_px"])

        # Fixed left gutter anchor so legend and ribbon labels are visually justified.
        # Tunable in config/ribbon_settings.json under layout.left_gutter_x.
        left_gutter_x = self._layout_numeric_setting("left_gutter_x", -0.22)

        # 1. Price Chart (Candlestick)
        fig.add_trace(
            go.Candlestick(
                x=df["Date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="Price",
                increasing_line_color="#16a34a",
                decreasing_line_color="#dc2626",
                increasing_fillcolor="#16a34a",
                decreasing_fillcolor="#dc2626",
            ),
            row=1,
            col=1,
        )

        # Add only EMA curves that are explicitly referenced by the active strategy.
        ema_periods = self._extract_ema_periods(strategy_content)
        ema_colors = ["#f59e0b", "#3b82f6", "#10b981", "#ef4444", "#8b5cf6", "#14b8a6"]
        for idx, period in enumerate(ema_periods):
            lower_col = f"ema_{period}"
            upper_col = f"EMA_{period}"
            ema_col = (
                lower_col
                if lower_col in df.columns
                else (upper_col if upper_col in df.columns else None)
            )
            if not ema_col:
                continue
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df[ema_col],
                    name=f"EMA {period}",
                    line=dict(color=ema_colors[idx % len(ema_colors)], width=1.2),
                ),
                row=1,
                col=1,
            )

        # Supertrend Price Overlay — single color-changing line, only when referenced by DSL.
        supertrend_specs = self._extract_supertrend_specs(strategy_content)
        if (
            "ST_Lower" in df.columns
            and "ST_Upper" in df.columns
            and (supertrend_specs if strategy_content else True)
        ):
            st_lower = df["ST_Lower"].values.astype(float)
            st_upper = df["ST_Upper"].values.astype(float)
            # Green regime: ST_Lower is populated; red regime: ST_Upper is populated.
            is_green_regime = ~np.isnan(st_lower)
            st_active = np.where(is_green_regime, st_lower, st_upper)

            # Split into contiguous same-color runs and draw one trace per run.
            # Adjacent runs share their boundary index so the line appears continuous.
            transitions = np.where(np.diff(is_green_regime.astype(int)) != 0)[0] + 1
            run_starts = np.concatenate([[0], transitions])
            run_ends = np.concatenate([transitions, [len(is_green_regime)]])

            first_st_trace = True
            for run_start, run_end in zip(run_starts, run_ends):
                green = bool(is_green_regime[run_start])
                color = "#16a34a" if green else "#dc2626"
                # Include one bridge point (start of next run) for visual continuity.
                slice_end = int(min(run_end + 1, len(df)))
                fig.add_trace(
                    go.Scatter(
                        x=df["Date"].iloc[run_start:slice_end],
                        y=st_active[run_start:slice_end],
                        name="Supertrend",
                        legendgroup="supertrend",
                        showlegend=first_st_trace,
                        mode="lines",
                        line=dict(color=color, width=1.5),
                        connectgaps=False,
                    ),
                    row=1,
                    col=1,
                )
                first_st_trace = False

        # 2. Volume Chart
        colors = [
            "red" if df["Close"].iloc[i] < df["Open"].iloc[i] else "green"
            for i in range(len(df))
        ]
        fig.add_trace(
            go.Bar(
                x=df["Date"],
                y=df["Volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

        # 3. Indicator Ribbons (layer lanes)
        ribbon_lane_activity: list[np.ndarray] = []
        context_lane_mask = np.zeros(len(df), dtype=bool)
        trigger_lane_mask = np.zeros(len(df), dtype=bool)
        has_context_lane = False
        has_trigger_lane = False
        has_setup_lane = False
        has_risk_lane = False
        for i, rib in enumerate(active_ribbons):
            row = 3 + i
            label = rib.get("label", "Indicator")
            layers = rib.get("layers", [])
            ribbon_condition = str(rib.get("condition", "")).strip()
            is_trigger_lane = "trigger" in label.lower()
            lane_width = lane_line_width

            # Paint a neutral base so lanes remain contiguous even when condition masks are false.
            fig.add_trace(
                go.Bar(
                    x=df["Date"],
                    y=np.full(len(df), 0.2),
                    base=0.9,
                    width=self._time_bucket_width_ms(df["Date"]),
                    marker=dict(color="#d1d5db", line=dict(width=0)),
                    opacity=0.4,
                    showlegend=False,
                    name=f"{label} base",
                ),
                row=row,
                col=1,
            )

            eval_df = df.copy()
            for c in eval_df.columns:
                if pd.api.types.is_numeric_dtype(eval_df[c]):
                    eval_df[c] = eval_df[c].ffill()
            eval_df.columns = [c.lower() for c in eval_df.columns]
            eval_df = eval_df.loc[:, ~eval_df.columns.duplicated()]
            ribbon_any_mask = pd.Series(False, index=eval_df.index)

            overlay_specs = []
            if ribbon_condition:
                overlay_specs.append(
                    {
                        "condition": ribbon_condition,
                        "color": rib.get(
                            "color",
                            layers[0].get("color", "gray") if layers else "gray",
                        ),
                        "alpha": rib.get(
                            "alpha", layers[0].get("alpha", 0.8) if layers else 0.8
                        ),
                    }
                )
            else:
                overlay_specs.extend(layers)

            for overlay in overlay_specs:
                color = overlay.get("color", "gray")
                alpha = overlay.get("alpha", 0.8)
                condition = overlay.get("condition", "False")

                try:
                    clean_cond = self._to_eval_condition(condition)
                    eval_df = self._prepare_eval_columns(eval_df, clean_cond)
                    mask = eval_df.eval(clean_cond, engine="python")

                    if isinstance(mask, pd.Series) and mask.any():
                        mask = mask.fillna(False).astype(bool)
                        ribbon_any_mask = ribbon_any_mask | mask
                        self._draw_ribbon_mask_trace(
                            fig=fig,
                            x_values=df["Date"],
                            mask=mask,
                            row=row,
                            color=color,
                            lane_width=lane_width,
                            name=f"{label} - {color}",
                            hovertemplate=None,
                            show_markers=is_trigger_lane,
                            alpha=alpha,
                        )
                except Exception:
                    continue

            ribbon_lane_activity.append(ribbon_any_mask.to_numpy(dtype=bool))
            lane_mask_np = ribbon_any_mask.to_numpy(dtype=bool)
            if "context" in label.lower() and len(lane_mask_np) == len(df):
                context_lane_mask = context_lane_mask | lane_mask_np
                has_context_lane = True
            if "setup" in label.lower() and len(lane_mask_np) == len(df):
                has_setup_lane = True
            if "trigger" in label.lower() and len(lane_mask_np) == len(df):
                trigger_lane_mask = trigger_lane_mask | lane_mask_np
                has_trigger_lane = True
            if "risk" in label.lower() and len(lane_mask_np) == len(df):
                has_risk_lane = True

            fig.update_yaxes(showticklabels=False, range=[0.9, 1.1], row=row, col=1)

            # Add a horizontal label just left of each ribbon lane.
            yaxis_name = "yaxis" if row == 1 else f"yaxis{row}"
            y_domain = fig.layout[yaxis_name].domain
            y_mid = (y_domain[0] + y_domain[1]) / 2
            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=left_gutter_x,
                y=y_mid,
                xanchor="left",
                yanchor="middle",
                xshift=0,
                text=f"<b>{self._compact_ribbon_label(label)}</b>",
                showarrow=False,
                font=dict(size=10, color=rib.get("color", "#6b7280")),
                align="left",
            )

        # Bottom-most lane: Aggregated state ribbon (single lane)
        aggregated_row = 3 + num_ribbons
        df_state = df.copy()
        df_state["aggregated_state"] = 0

        if "Signal" in df_state.columns or "signal" in df_state.columns:
            signal_col = "signal" if "signal" in df_state.columns else "Signal"
            in_position = False
            states = []
            for sig in df_state[signal_col].fillna(0).astype(int):
                if sig == 1:
                    in_position = True
                elif sig == -1:
                    in_position = False
                states.append(1 if in_position else 0)
            df_state["aggregated_state"] = states
        elif (
            "entry_condition" in df_state.columns
            or "exit_condition" in df_state.columns
        ):
            in_position = False
            states = []
            for i in range(len(df_state)):
                is_entry = (
                    bool(df_state["entry_condition"].iloc[i])
                    if "entry_condition" in df_state.columns
                    else False
                )
                is_exit = (
                    bool(df_state["exit_condition"].iloc[i])
                    if "exit_condition" in df_state.columns
                    else False
                )
                if is_entry:
                    in_position = True
                if is_exit:
                    in_position = False
                states.append(1 if in_position else 0)
            df_state["aggregated_state"] = states

        # Base lane — full-height grey bar covering the whole lane.
        agg_lane_min, agg_lane_max = 0.9, 1.1
        agg_lane_span = agg_lane_max - agg_lane_min
        fig.add_trace(
            go.Bar(
                x=df_state["Date"],
                y=np.full(len(df_state), agg_lane_span),
                base=agg_lane_min,
                width=self._time_bucket_width_ms(df_state["Date"]),
                marker=dict(color="#d1d5db", line=dict(width=0)),
                opacity=0.4,
                showlegend=False,
                name="Aggregated base",
            ),
            row=aggregated_row,
            col=1,
        )

        in_position_mask = (
            df_state["aggregated_state"].fillna(0).astype(int) == 1
        ).to_numpy(dtype=bool)
        lane_masks = {
            "context": context_lane_mask,
            "trigger": trigger_lane_mask,
            "setup": np.zeros(len(df_state), dtype=bool),
            "risk": np.zeros(len(df_state), dtype=bool),
            "in_position": in_position_mask,
        }

        # Capture setup/risk too so custom fill_condition can reference them.
        for i, rib in enumerate(active_ribbons):
            label = rib.get("label", "").lower()
            if i < len(ribbon_lane_activity) and len(ribbon_lane_activity[i]) == len(
                df_state
            ):
                mask_np = ribbon_lane_activity[i]
                if "setup" in label:
                    lane_masks["setup"] = lane_masks["setup"] | mask_np
                if "risk" in label:
                    lane_masks["risk"] = lane_masks["risk"] | mask_np

        block_presence = {
            "context": has_context_lane,
            "setup": has_setup_lane,
            "trigger": has_trigger_lane,
            "risk": has_risk_lane,
        }
        fill_condition = self._resolve_aggregate_expression(block_presence)
        if fill_condition == "context and trigger":
            agg_mask_np = (
                context_lane_mask & trigger_lane_mask
                if has_context_lane and has_trigger_lane
                else np.zeros(len(df_state), dtype=bool)
            )
        else:
            normalized_expr = fill_condition.replace("_and_", " and ").replace(
                "_or_", " or "
            )
            normalized_expr = re.sub(r"\band\b", "&", normalized_expr)
            normalized_expr = re.sub(r"\bor\b", "|", normalized_expr)
            normalized_expr = re.sub(r"\bnot\b", "~", normalized_expr)
            normalized_expr = re.sub(r"\s+", " ", normalized_expr).strip()

            try:
                agg_mask_np = eval(
                    normalized_expr, {"__builtins__": {}}, lane_masks
                )  # nosec B307 - sandboxed: empty builtins, only numpy arrays in namespace
                if isinstance(agg_mask_np, np.ndarray):
                    agg_mask_np = agg_mask_np.astype(bool)
                else:
                    agg_mask_np = np.zeros(len(df_state), dtype=bool)
            except Exception:
                if has_context_lane and has_trigger_lane:
                    agg_mask_np = context_lane_mask & trigger_lane_mask
                else:
                    agg_mask_np = np.zeros(len(df_state), dtype=bool)

        agg_fill_label = fill_condition
        bucket_ms = self._time_bucket_width_ms(df_state["Date"])
        fig.add_trace(
            go.Bar(
                x=df_state["Date"],
                y=np.where(agg_mask_np, agg_lane_span, 0.0),
                base=agg_lane_min,
                width=bucket_ms,
                marker=dict(color="#16a34a", line=dict(width=0)),
                opacity=1.0,
                showlegend=False,
                name="Aggregated",
                hovertemplate=f"Aggregated Fill: {agg_fill_label}<br>Date: %{{x}}<extra></extra>",
            ),
            row=aggregated_row,
            col=1,
        )
        fig.update_yaxes(
            showticklabels=False, range=[0.9, 1.1], row=aggregated_row, col=1
        )

        # Add label for aggregated lane
        agg_yaxis_name = "yaxis" if aggregated_row == 1 else f"yaxis{aggregated_row}"
        agg_domain = fig.layout[agg_yaxis_name].domain
        agg_mid = (agg_domain[0] + agg_domain[1]) / 2
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=left_gutter_x,
            y=agg_mid,
            xanchor="left",
            yanchor="middle",
            xshift=0,
            text="<b>Aggregated</b>",
            showarrow=False,
            font=dict(size=10, color="#0f766e"),
            align="left",
        )

        # 4. Global configurations for all x-axes
        bottom_row = 3 + num_ribbons

        # Completely re-write the end of the method with dictionary-level precision
        fig_dict = fig.to_dict()
        layout = fig_dict["layout"]

        # Shared x-axis: show date tick labels only on the bottom pane.
        bottom_axis_key = "xaxis" if bottom_row == 1 else f"xaxis{bottom_row}"

        # Enforce axis visibility and formatting on EVERY possible x-axis key in the layout
        for key in list(layout.keys()):
            if key.startswith("xaxis"):
                is_bottom = key == bottom_axis_key
                layout[key]["showticklabels"] = is_bottom
                layout[key]["visible"] = True
                layout[key]["type"] = "date"
                layout[key]["tickformat"] = "%b %Y"
                layout[key]["gridcolor"] = "lightgray"
                layout[key]["ticks"] = "outside" if is_bottom else ""
                layout[key]["showline"] = is_bottom
                layout[key]["zeroline"] = False

        # Force professional global layout
        layout["template"] = "plotly_white"
        layout["xaxis_rangeslider_visible"] = False
        layout["hovermode"] = "x unified"
        # Tunable in config/ribbon_settings.json under layout.left_margin.
        left_margin = int(self._layout_numeric_setting("left_margin", 300))
        layout["margin"] = dict(l=left_margin, r=20, t=50, b=80)
        layout["legend"] = dict(
            x=left_gutter_x,
            y=1.0,
            xanchor="left",
            yanchor="top",
            orientation="v",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#d1d5db",
            borderwidth=1,
        )
        # Style the modebar (keep default horizontal orientation so it
        # renders at the top-right, clear of the left-gutter legend).
        layout["modebar"] = dict(
            bgcolor="rgba(255,255,255,0.9)",
            color="#374151",
            activecolor="#2563eb",
        )

        return go.Figure(fig_dict)

    def plot_etf_analysis(self, df: pd.DataFrame, symbol: str) -> Path:
        fig = self.create_plot(df, symbol)
        output_path = self.output_dir / f"{symbol.lower()}_interactive.html"
        # Inject a tiny style block so the modebar gets a visible border frame
        # in the standalone HTML output (mirrors the legend's bordercolor).
        post_script = (
            "var s=document.createElement('style');"
            "s.textContent='.modebar-container{"
            "border:1px solid #d1d5db;"
            "border-radius:4px;"
            "padding:2px;"
            "}';"
            "document.head.appendChild(s);"
        )
        fig.write_html(str(output_path), post_script=post_script)
        return output_path
