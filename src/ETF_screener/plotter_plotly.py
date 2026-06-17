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

from ETF_screener.dsl_parser import parse_strategy_blocks, resolve_block

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
        rules = (
            aggregate_cfg.get("rules", []) if isinstance(aggregate_cfg, dict) else []
        )
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

    def _get_ribbon_layout(
        self, num_ribbons: int, num_strategy_panels: int = 0
    ) -> dict:
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
        strategy_panel_px = int(self._layout_numeric_setting("strategy_panel_px", 140))
        fixed_px = (
            cfg.price_panel_px
            + cfg.volume_panel_px
            + (max(0, num_strategy_panels) * strategy_panel_px)
        )
        available_for_lanes = max(
            cfg.max_total_height_px - fixed_px, lane_count * cfg.min_lane_px
        )
        lane_px = max(
            cfg.min_lane_px, min(cfg.target_lane_px, available_for_lanes // lane_count)
        )

        total_height_px = fixed_px + (lane_px * lane_count)
        raw_heights = (
            [cfg.price_panel_px, cfg.volume_panel_px]
            + [strategy_panel_px] * max(0, num_strategy_panels)
            + [lane_px] * lane_count
        )
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
        parsed_blocks = parse_strategy_blocks(strategy_content)
        if not parsed_blocks:
            return []

        # Alternating palette for extra/unrecognised blocks.
        _EXTRA_COLORS = [
            "#7c3aed",
            "#0891b2",
            "#b45309",
            "#be185d",
            "#065f46",
            "#1e40af",
        ]

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
        merged_setup_idx: int | None = None
        for block in parsed_blocks:
            block_name = block.name
            slot = block.layer
            exprs = list(block.expressions)
            _, style_key = resolve_block(block_name)
            if style_key == "setup":
                style = layer_style_cache[2]
                merged_condition = " AND ".join(exprs)
                if merged_setup_idx is None:
                    ribbons.append(
                        {
                            "label": "Setup",
                            "condition": merged_condition,
                            "color": style["color"],
                            "alpha": style.get("alpha", 0.6),
                        }
                    )
                    merged_setup_idx = len(ribbons) - 1
                else:
                    existing = str(
                        ribbons[merged_setup_idx].get("condition", "")
                    ).strip()
                    ribbons[merged_setup_idx]["condition"] = " AND ".join(
                        part for part in [existing, merged_condition] if part
                    )
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

    def _evaluate_ribbon_overlays(
        self, df: pd.DataFrame, ribbon: dict
    ) -> tuple[np.ndarray, list[dict]]:
        """Evaluate a ribbon into a lane mask plus concrete overlay traces."""
        label = str(ribbon.get("label", "Indicator"))
        display_label = self._compact_ribbon_label(label)
        layers = ribbon.get("layers", [])
        ribbon_condition = str(ribbon.get("condition", "")).strip()
        is_trigger_lane = "trigger" in label.lower()

        eval_df = df.copy()
        for column in eval_df.columns:
            if pd.api.types.is_numeric_dtype(eval_df[column]):
                eval_df[column] = eval_df[column].ffill()
        eval_df.columns = [column.lower() for column in eval_df.columns]
        eval_df = eval_df.loc[:, ~eval_df.columns.duplicated()]

        ribbon_any_mask = pd.Series(False, index=eval_df.index)
        overlay_specs = []
        if ribbon_condition:
            overlay_specs.append(
                {
                    "condition": ribbon_condition,
                    "color": ribbon.get(
                        "color", layers[0].get("color", "gray") if layers else "gray"
                    ),
                    "alpha": ribbon.get(
                        "alpha", layers[0].get("alpha", 0.8) if layers else 0.8
                    ),
                }
            )
        else:
            overlay_specs.extend(layers)

        overlay_draws: list[dict] = []
        for overlay in overlay_specs:
            color = overlay.get("color", "gray")
            alpha = overlay.get("alpha", 0.8)
            condition = overlay.get("condition", "False")

            try:
                clean_cond = self._to_eval_condition(condition)
                eval_df = self._prepare_eval_columns(eval_df, clean_cond)
                mask = eval_df.eval(clean_cond, engine="python")
            except Exception:
                continue

            if not isinstance(mask, pd.Series) or not mask.any():
                continue

            mask = mask.fillna(False).astype(bool)
            mask_np = mask.to_numpy(dtype=bool)
            ribbon_any_mask = ribbon_any_mask | mask
            overlay_draws.append(
                {
                    "mask": mask_np,
                    "color": color,
                    "alpha": alpha,
                    "name": f"{display_label} - {color}",
                    "hovertemplate": self._ribbon_hovertemplate(ribbon, color),
                    "show_markers": is_trigger_lane,
                }
            )

        return ribbon_any_mask.to_numpy(dtype=bool), overlay_draws

    def _evaluate_lane_expression(
        self, expression: str, lane_masks: dict[str, np.ndarray], length: int
    ) -> np.ndarray | None:
        """Evaluate an aggregate-style lane expression against numpy mask arrays."""
        normalized_expr = (
            str(expression or "").replace("_and_", " and ").replace("_or_", " or ")
        )
        normalized_expr = re.sub(r"\band\b", "&", normalized_expr)
        normalized_expr = re.sub(r"\bor\b", "|", normalized_expr)
        normalized_expr = re.sub(r"\bnot\b", "~", normalized_expr)
        normalized_expr = re.sub(r"\s+", " ", normalized_expr).strip()
        if not normalized_expr:
            return np.zeros(length, dtype=bool)

        try:
            result = eval(
                normalized_expr, {"__builtins__": {}}, lane_masks
            )  # nosec B307 - sandboxed: empty builtins, only numpy arrays in namespace
        except Exception:
            return None

        if isinstance(result, pd.Series):
            series_bool: np.ndarray = result.fillna(False).to_numpy(dtype=bool)
            return series_bool
        if isinstance(result, np.ndarray):
            return np.asarray(result, dtype=bool)  # type: ignore[no-any-return]
        if np.isscalar(result):
            return np.full(length, bool(result), dtype=bool)
        return None

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

    def _extract_anchored_vwap_names(self, strategy_content: str | None) -> list[str]:
        """Extract anchored VWAP tokens referenced in DSL content."""
        if not strategy_content:
            return []

        found: list[str] = []
        seen: set[str] = set()
        for match in re.finditer(
            r"\b((?:avwap|anchored_vwap)_(?:low|high)_\d+)\b",
            strategy_content.lower(),
        ):
            token = match.group(1)
            if token in seen:
                continue
            seen.add(token)
            found.append(token)
        return found

    def _extract_strategy_indicator_names(
        self, strategy_content: str | None
    ) -> list[str]:
        """Extract plot-worthy indicator names referenced by the DSL."""
        if not strategy_content:
            return []

        s = strategy_content.lower()
        found: list[str] = []
        seen: set[str] = set()

        def add(name: str) -> None:
            name = str(name).strip()
            if not name or name in seen:
                return
            seen.add(name)
            found.append(name)

        for period in re.findall(r"\bema_(\d+)\b", s):
            add(f"ema_{period}")

        for period in re.findall(r"\brsi_(\d+)\b", s):
            add(f"rsi_{period}")

        if re.search(r"\brsi\b", s):
            add("rsi")

        for rsi_period, ema_period in re.findall(r"\brsi_ema_(\d+)_(\d+)\b", s):
            add(f"rsi_ema_{rsi_period}_{ema_period}")

        for period, mult in re.findall(
            r"\b(?:st|supertrend)_(\d+)_(\d+(?:\.\d+)?)\b", s
        ):
            add(f"supertrend_{period}_{mult}")

        for match in re.finditer(
            r"\b((?:avwap|anchored_vwap)_(?:low|high)_\d+)\b",
            s,
        ):
            add(match.group(1))

        for token in (
            "macd",
            "macd_signal",
            "macd_hist",
            "stoch_k",
            "stoch_d",
            "stoch_rsi_k",
            "stoch_rsi_d",
            "tsi",
            "tsi_signal",
            "adx",
            "vol_ema_20",
        ):
            if re.search(rf"\b{re.escape(token)}\b", s):
                add(token)

        # Generic slope references are useful to visualize if the strategy uses them.
        for slope_match in re.finditer(r"\b([a-z][a-z0-9_]*_slope)\b", s):
            add(slope_match.group(1))

        return found

    def _find_column_case_insensitive(
        self, df: pd.DataFrame, column_name: str
    ) -> str | None:
        """Return the actual DataFrame column matching `column_name`, ignoring case."""
        if column_name in df.columns:
            return str(column_name)

        lower_name = str(column_name).lower()
        for col in df.columns:
            if str(col).lower() == lower_name:
                return str(col)
        return None

    def _pretty_indicator_label(self, column_name: str) -> str:
        """Convert an indicator column name into a readable legend label."""
        name = str(column_name).strip()
        if not name:
            return "Indicator"

        lower = name.lower()
        if lower.startswith("supertrend_"):
            parts = lower.split("_")
            if len(parts) >= 3:
                return f"Supertrend {parts[1]} {parts[2]}"
        if re.fullmatch(r"(?:avwap|anchored_vwap)_(low|high)_\d+", lower):
            parts = lower.split("_")
            return f"AVWAP {parts[-2].title()} {parts[-1]}"
        if lower.startswith("ema_"):
            suffix = lower[4:].replace("_", " ")
            return f"EMA {suffix}".strip()
        if lower == "rsi":
            return "RSI"
        if lower.startswith("rsi_ema_"):
            suffix = lower[8:].replace("_", " ")
            return f"RSI EMA {suffix}".strip()
        if lower.startswith("rsi_"):
            suffix = lower[4:].replace("_", " ")
            return f"RSI {suffix}".strip()
        if lower == "macd":
            return "MACD"
        if lower == "macd_signal":
            return "MACD Signal"
        if lower == "macd_hist":
            return "MACD Hist"
        if lower.startswith("stoch_rsi_"):
            suffix = lower[10:].replace("_", " ")
            return f"Stoch RSI {suffix}".strip()
        if lower.startswith("stoch_"):
            suffix = lower[6:].replace("_", " ")
            return f"Stoch {suffix}".strip()
        if lower == "tsi":
            return "TSI"
        if lower == "tsi_signal":
            return "TSI Signal"
        if lower == "adx":
            return "ADX"
        if lower == "vol_ema_20":
            return "Volume EMA 20"
        if lower.endswith("_slope"):
            return name.replace("_", " ").title()
        return name.replace("_", " ").title()

    def _classify_strategy_indicator(self, column_name: str, series: pd.Series) -> str:
        """Group indicator curves into reasonable subplot families."""
        lower = str(column_name).lower()
        if lower == "vol_ema_20":
            return "volume"
        if any(token in lower for token in ("rsi", "stoch", "adx")):
            return "oscillator"
        if any(token in lower for token in ("macd", "tsi", "_slope")):
            return "momentum"

        # Fallback by scale: bounded values fit better with oscillators, everything
        # else goes into a separate momentum panel so it does not crush the price pane.
        try:
            numeric = pd.to_numeric(series, errors="coerce").dropna()
        except Exception:
            return "momentum"

        if numeric.empty:
            return "momentum"

        max_abs = float(numeric.abs().max())
        if max_abs <= 120.0:
            return "oscillator"
        return "momentum"

    def _compact_ribbon_label(self, label: str) -> str:
        # Convert DSL block names into readable left-gutter labels.
        normalized = str(label).replace("_", " ").strip()
        if not normalized:
            return str(label)

        lowered = normalized.lower()
        if lowered == "risk" or "exit" in lowered:
            return "Exit"

        words = normalized.split()
        if not words:
            return str(label)
        return " ".join(word[:1].upper() + word[1:].lower() for word in words)

    def _condition_lines(self, condition: str, max_lines: int = 2) -> list[str]:
        """Return a short human-readable condition summary for labels/hover."""
        if not condition:
            return []

        parts = re.split(r"\s+AND\s+", str(condition).strip(), flags=re.IGNORECASE)
        cleaned = []
        for part in parts:
            line = part.strip()
            if line.startswith("(") and line.endswith(")"):
                line = line[1:-1].strip()
            line = line.replace("_d1", " (prev)")
            if line:
                cleaned.append(line)

        if len(cleaned) > max_lines:
            shown = cleaned[:max_lines]
            shown.append(f"+{len(cleaned) - max_lines} more")
            return shown
        return cleaned

    def _ribbon_annotation_text(self, ribbon: dict) -> str:
        """Build the left gutter label for a ribbon lane."""
        label = self._compact_ribbon_label(ribbon.get("label", "Indicator"))
        return f"<b>{label}</b>"

    def _ribbon_hovertemplate(self, ribbon: dict, color: str) -> str:
        """Build hover content that explains the current DSL block."""
        label = self._compact_ribbon_label(ribbon.get("label", "Indicator"))
        condition = str(ribbon.get("condition", "")).strip() or "n/a"
        condition = condition.replace("<", "&lt;").replace(">", "&gt;")
        color_name = str(color)
        return (
            f"Block: {label}<br>"
            f"State: {color_name}<br>"
            f"Condition: {condition}<br>"
            "Date: %{x}<extra></extra>"
        )

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
            "Layer 4 Exit": "#b91c1c",
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
        _lane_width: int,
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
            "within",
            "between",
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

    def _split_dsl_args(self, raw: str) -> list[str]:
        parts: list[str] = []
        depth = 0
        buf: list[str] = []
        for ch in raw:
            if ch == "," and depth == 0:
                item = "".join(buf).strip()
                if item:
                    parts.append(item)
                buf = []
                continue
            if ch == "(":
                depth += 1
            elif ch == ")" and depth > 0:
                depth -= 1
            buf.append(ch)
        item = "".join(buf).strip()
        if item:
            parts.append(item)
        return parts

    def _parse_interval_bound(self, token: str) -> int:
        cleaned = token.strip().lower()
        if cleaned == "now":
            return 0
        return max(0, int(cleaned))

    def _prepare_eval_columns(
        self, eval_df: pd.DataFrame, condition: str
    ) -> pd.DataFrame:
        words = set(re.findall(r"[a-z][a-z0-9_]*", condition))

        def _ensure_st_regime_column(col_name: str) -> None:
            if not (
                col_name.endswith("_is_green")
                or col_name.endswith("_is_red")
                or col_name.endswith("_is_flat")
                or col_name.endswith("_is_near_flat")
            ):
                return
            # Do NOT trust a pre-existing column: it may be a stale float stored in
            # the DB (e.g. st_10_4_is_green=1.0 even while price is below the ST
            # upper band).  Always recompute from the live ST line when possible.
            if "close" not in eval_df.columns:
                return

            match = re.fullmatch(
                r"((?:st|supertrend)(?:_\d+_\d+)?)_is_(green|red|flat|near_flat)",
                col_name,
            )
            if not match:
                return
            base_st, regime = match.groups()

            line = None
            if base_st in eval_df.columns:
                line = eval_df[base_st]
            if line is None and base_st.startswith("st_"):
                alt = f"supertrend_{base_st[3:]}"
                if alt in eval_df.columns:
                    line = eval_df[alt]
            if line is None and base_st.startswith("supertrend_"):
                alt = f"st_{base_st[11:]}"
                if alt in eval_df.columns:
                    line = eval_df[alt]
            if line is None and "supertrend" in eval_df.columns:
                line = eval_df["supertrend"]
            if line is None and "st_lower" in eval_df.columns:
                # Last-resort fallback for legacy data frames missing the supertrend line.
                line = eval_df["st_lower"]

            if line is None:
                return

            if regime == "green":
                eval_df[col_name] = ((eval_df["close"] > line).fillna(False)).astype(
                    bool
                )
            elif regime == "red":
                eval_df[col_name] = ((eval_df["close"] < line).fillna(False)).astype(
                    bool
                )
            elif regime == "flat":
                eval_df[col_name] = (
                    line.diff().abs().le(1e-9).fillna(False).astype(bool)
                )
            else:
                close_abs = eval_df["close"].abs().replace(0, np.nan)
                eval_df[col_name] = (
                    line.diff()
                    .abs()
                    .div(close_abs)
                    .le(0.001)
                    .fillna(False)
                    .astype(bool)
                )

        for w in words:
            delay_match = re.search(r"_d(\d+)$", w)
            if delay_match:
                base = re.sub(r"_d\d+$", "", w)
                delay = int(delay_match.group(1))
                _ensure_st_regime_column(base)
                if base in eval_df.columns and w not in eval_df.columns:
                    shifted = eval_df[base].shift(delay)
                    if base.endswith("_is_green") or base.endswith("_is_red"):
                        shifted = shifted.eq(True)
                    eval_df[w] = shifted
                continue

            slope_flip_match = re.fullmatch(r"(.+_slope)_cross_(up|down)", w)
            if slope_flip_match:
                slope_base, direction = slope_flip_match.groups()
                if slope_base not in eval_df.columns and slope_base.endswith("_slope"):
                    source_base = slope_base[:-6]
                    if source_base in eval_df.columns:
                        eval_df[slope_base] = eval_df[source_base].diff().fillna(0)
                if slope_base in eval_df.columns and w not in eval_df.columns:
                    slope_sign = pd.Series(
                        np.sign(eval_df[slope_base]), index=eval_df.index
                    )
                    prev_nonzero = slope_sign.replace(0, np.nan).ffill().shift(1)
                    if direction == "up":
                        eval_df[w] = (
                            ((slope_sign > 0) & (prev_nonzero < 0))
                            .fillna(False)
                            .astype(bool)
                        )
                    else:
                        eval_df[w] = (
                            ((slope_sign < 0) & (prev_nonzero > 0))
                            .fillna(False)
                            .astype(bool)
                        )
                continue

            if w.endswith("_slope"):
                base = w[:-6]
                if base in eval_df.columns and w not in eval_df.columns:
                    eval_df[w] = eval_df[base].diff().fillna(0)

        for w in words:
            _ensure_st_regime_column(w)
            if w in eval_df.columns and (
                w.endswith("_is_green")
                or w.endswith("_is_red")
                or w.endswith("_is_flat")
            ):
                eval_df[w] = eval_df[w].eq(True)

        return eval_df

    def _to_eval_condition(self, condition: str) -> str:
        s = condition.lower()

        def wt_repl(m):
            expr = m.group(1).strip()
            delay = int(m.group(2).strip())
            return f"({self._shift_expr_symbols(expr, delay)})"

        s = re.sub(r"was_true\s*\(([^,]+),\s*(\d+)\s*\)", wt_repl, s)

        def within_repl(m):
            content = m.group(0).split("(", 1)[1].rsplit(")", 1)[0]
            parts = self._split_dsl_args(content)
            if len(parts) < 2:
                return "False"
            expr = parts[0].strip()
            if len(parts) == 2:
                start, end = 0, self._parse_interval_bound(parts[1])
            else:
                start, end = sorted(
                    (
                        self._parse_interval_bound(parts[1]),
                        self._parse_interval_bound(parts[2]),
                    )
                )
            if end < start:
                return "False"
            terms = [
                (
                    f"({expr})"
                    if delay == 0
                    else f"({self._shift_expr_symbols(expr, delay)})"
                )
                for delay in range(start, end + 1)
            ]
            return f"({' | '.join(terms)})"

        s = re.sub(r"(?:within|between)\s*\((?:[^()]+|\([^()]*\))+\)", within_repl, s)

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

        strategy_indicator_names = self._extract_strategy_indicator_names(
            strategy_content
        )
        overlay_names = {
            *[
                f"ema_{period}"
                for period in self._extract_ema_periods(strategy_content)
            ],
            *[
                f"supertrend_{period}_{mult}"
                for period, mult in self._extract_supertrend_specs(strategy_content)
            ],
            *self._extract_anchored_vwap_names(strategy_content),
        }
        strategy_panel_groups: list[dict] = []
        panel_buckets: dict[str, list[dict]] = {
            "oscillator": [],
            "momentum": [],
            "volume": [],
        }
        if strategy_content and strategy_content.strip():
            seen_columns: set[str] = set()

            for indicator_name in strategy_indicator_names:
                if indicator_name in overlay_names:
                    continue
                column_name = self._find_column_case_insensitive(df, indicator_name)
                if not column_name:
                    # Some strategy helpers are derived at runtime and may not be
                    # stored under the exact DSL token. Skip quietly if absent.
                    continue
                if column_name in seen_columns:
                    continue

                series = df[column_name]
                if not pd.api.types.is_numeric_dtype(series):
                    continue
                if pd.api.types.is_bool_dtype(series):
                    continue

                family = self._classify_strategy_indicator(column_name, series)
                label = self._pretty_indicator_label(column_name)
                panel_buckets.setdefault(family, []).append(
                    {"column": column_name, "label": label}
                )
                seen_columns.add(column_name)

            for title, family in (
                ("Oscillators", "oscillator"),
                ("Momentum", "momentum"),
            ):
                items = panel_buckets.get(family, [])
                if items:
                    strategy_panel_groups.append({"title": title, "items": items})

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

        ribbon_render_data: list[dict] = []
        context_lane_mask = np.zeros(len(df), dtype=bool)
        trigger_lane_mask = np.zeros(len(df), dtype=bool)
        has_context_lane = False
        has_trigger_lane = False
        has_setup_lane = False
        has_risk_lane = False
        lane_masks = {
            "context": np.zeros(len(df), dtype=bool),
            "setup": np.zeros(len(df), dtype=bool),
            "trigger": np.zeros(len(df), dtype=bool),
            "risk": np.zeros(len(df), dtype=bool),
        }

        for ribbon in active_ribbons:
            lane_mask_np, overlay_draws = self._evaluate_ribbon_overlays(df, ribbon)
            label_lower = str(ribbon.get("label", "")).lower()
            is_context_lane = "context" in label_lower
            is_setup_lane = "setup" in label_lower
            is_trigger_lane = "trigger" in label_lower
            is_risk_lane = "risk" in label_lower or "exit" in label_lower

            if is_context_lane and len(lane_mask_np) == len(df):
                context_lane_mask = context_lane_mask | lane_mask_np
                lane_masks["context"] = lane_masks["context"] | lane_mask_np
                has_context_lane = True
            if is_setup_lane and len(lane_mask_np) == len(df):
                lane_masks["setup"] = lane_masks["setup"] | lane_mask_np
                has_setup_lane = True
            if is_trigger_lane and len(lane_mask_np) == len(df):
                trigger_lane_mask = trigger_lane_mask | lane_mask_np
                lane_masks["trigger"] = lane_masks["trigger"] | lane_mask_np
                has_trigger_lane = True
            if is_risk_lane and len(lane_mask_np) == len(df):
                lane_masks["risk"] = lane_masks["risk"] | lane_mask_np
                has_risk_lane = True

            ribbon_render_data.append(
                {
                    "ribbon": ribbon,
                    "label_lower": label_lower,
                    "lane_mask": lane_mask_np,
                    "overlay_draws": overlay_draws,
                    "is_risk_lane": is_risk_lane,
                }
            )

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
        lane_masks["in_position"] = (
            df_state["aggregated_state"].fillna(0).astype(int) == 1
        ).to_numpy(dtype=bool)

        block_presence = {
            "context": has_context_lane,
            "setup": has_setup_lane,
            "trigger": has_trigger_lane,
            "risk": has_risk_lane,
        }
        fill_condition = self._resolve_aggregate_expression(block_presence)
        fallback_mask = (
            context_lane_mask & lane_masks["setup"] & trigger_lane_mask
            if has_context_lane and has_setup_lane and has_trigger_lane
            else (
                context_lane_mask & trigger_lane_mask
                if has_context_lane and has_trigger_lane
                else np.zeros(len(df_state), dtype=bool)
            )
        )
        entry_ready_lane_masks = dict(lane_masks)
        entry_ready_lane_masks["risk"] = np.zeros(len(df_state), dtype=bool)
        entry_ready_mask_np = self._evaluate_lane_expression(
            fill_condition, entry_ready_lane_masks, len(df_state)
        )
        if entry_ready_mask_np is None:
            entry_ready_mask_np = fallback_mask

        agg_mask_np = self._evaluate_lane_expression(
            fill_condition, lane_masks, len(df_state)
        )
        if agg_mask_np is None:
            agg_mask_np = fallback_mask

        visible_ribbon_data = []
        for item in ribbon_render_data:
            lane_mask_np = item["lane_mask"]
            overlay_draws = item["overlay_draws"]
            if item["is_risk_lane"]:
                display_mask = lane_mask_np & entry_ready_mask_np
                display_overlays = []
                for overlay in overlay_draws:
                    gated_mask = overlay["mask"] & entry_ready_mask_np
                    if gated_mask.any():
                        display_overlays.append({**overlay, "mask": gated_mask})
                if not display_mask.any():
                    continue
            else:
                display_mask = lane_mask_np
                display_overlays = overlay_draws

            visible_ribbon_data.append(
                {
                    **item,
                    "display_mask": display_mask,
                    "display_overlays": display_overlays,
                }
            )

        num_ribbons = len(visible_ribbon_data)
        num_strategy_panels = len(strategy_panel_groups)
        layout_spec = self._get_ribbon_layout(num_ribbons, num_strategy_panels)
        row_heights = layout_spec["row_heights"]
        lane_line_width = layout_spec["lane_line_width"]

        strategy_row_start = 3
        ribbon_row_start = strategy_row_start + num_strategy_panels
        aggregated_row = ribbon_row_start + num_ribbons

        # We start with a clean subplot setup
        # Reverting to shared_xaxes=True but we will FIX the layout naming issue
        fig = make_subplots(
            rows=3 + num_strategy_panels + num_ribbons,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.0,
            row_heights=row_heights,
            subplot_titles=[f"{symbol} Analysis", "Volume"]
            + [panel["title"] for panel in strategy_panel_groups]
            + ["Buy/Sell Conditions"]
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
        left_gutter_x = self._layout_numeric_setting("left_gutter_x", -0.18)

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

        avwap_names = self._extract_anchored_vwap_names(strategy_content)
        avwap_colors = ["#0f766e", "#b45309", "#be123c", "#0369a1"]
        for idx, avwap_name in enumerate(avwap_names):
            avwap_col = self._find_column_case_insensitive(df, avwap_name)
            if not avwap_col:
                continue
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df[avwap_col],
                    name=self._pretty_indicator_label(avwap_col),
                    line=dict(
                        color=avwap_colors[idx % len(avwap_colors)],
                        width=1.4,
                        dash="dot",
                    ),
                ),
                row=1,
                col=1,
            )

        # Add other TA curves that the strategy directly references, grouped into
        # dedicated indicator panels so they remain readable.
        strategy_curve_palette = [
            "#7c3aed",
            "#0891b2",
            "#b45309",
            "#be185d",
            "#065f46",
            "#1e40af",
            "#4f46e5",
            "#059669",
        ]
        volume_overlay_specs = panel_buckets.get("volume", [])
        for panel_idx, panel in enumerate(strategy_panel_groups):
            row = strategy_row_start + panel_idx
            items = panel["items"]
            for item_idx, item in enumerate(items):
                col_name = item["column"]
                if col_name not in df.columns:
                    continue
                color = strategy_curve_palette[
                    (panel_idx + item_idx) % len(strategy_curve_palette)
                ]
                series = pd.to_numeric(df[col_name], errors="coerce")
                if series.dropna().empty:
                    continue

                fig.add_trace(
                    go.Scatter(
                        x=df["Date"],
                        y=series,
                        name=item["label"],
                        mode="lines",
                        line=dict(color=color, width=1.5),
                        connectgaps=False,
                    ),
                    row=row,
                    col=1,
                )

            if panel["title"].lower() == "oscillators":
                fig.update_yaxes(
                    range=[0, 100],
                    row=row,
                    col=1,
                )
                fig.add_hline(
                    y=70,
                    line=dict(color="#cbd5e1", width=1, dash="dot"),
                    row=row,
                    col=1,
                )
                fig.add_hline(
                    y=30,
                    line=dict(color="#cbd5e1", width=1, dash="dot"),
                    row=row,
                    col=1,
                )
            elif panel["title"].lower() == "momentum":
                fig.add_hline(
                    y=0,
                    line=dict(color="#cbd5e1", width=1, dash="dot"),
                    row=row,
                    col=1,
                )

        # Supertrend Price Overlay — always surface it when the chart data includes it.
        st_lower_col: str | None = next(
            (str(c) for c in df.columns if str(c).lower() == "st_lower"),
            None,
        )
        st_upper_col: str | None = next(
            (str(c) for c in df.columns if str(c).lower() == "st_upper"),
            None,
        )
        st_col: str | None = next(
            (str(c) for c in df.columns if str(c).lower() in {"supertrend", "st"}),
            None,
        )

        st_active = None
        is_green_regime = None

        if st_lower_col and st_upper_col:
            st_lower = pd.to_numeric(df[st_lower_col], errors="coerce").to_numpy(
                dtype=float
            )
            st_upper = pd.to_numeric(df[st_upper_col], errors="coerce").to_numpy(
                dtype=float
            )
            # Green regime: ST_Lower is populated; red regime: ST_Upper is populated.
            is_green_regime = ~np.isnan(st_lower)
            st_active = np.where(is_green_regime, st_lower, st_upper)
        elif st_col and "Close" in df.columns:
            st_active = pd.to_numeric(df[st_col], errors="coerce").to_numpy(dtype=float)
            close_values = pd.to_numeric(df["Close"], errors="coerce").to_numpy(
                dtype=float
            )
            valid = ~np.isnan(st_active) & ~np.isnan(close_values)
            is_green_regime = valid & (close_values > st_active)
        elif st_col and "close" in df.columns:
            st_active = pd.to_numeric(df[st_col], errors="coerce").to_numpy(dtype=float)
            close_values = pd.to_numeric(df["close"], errors="coerce").to_numpy(
                dtype=float
            )
            valid = ~np.isnan(st_active) & ~np.isnan(close_values)
            is_green_regime = valid & (close_values > st_active)

        if st_active is not None and is_green_regime is not None:
            valid_mask = ~np.isnan(st_active)

            # Split into contiguous same-color runs and draw one trace per run.
            # Adjacent runs share their boundary index so the line appears continuous.
            run_starts: list[int] = []
            run_ends: list[int] = []
            i = 0
            while i < len(st_active):
                if not valid_mask[i]:
                    i += 1
                    continue
                green = bool(is_green_regime[i])
                j = i + 1
                while (
                    j < len(st_active)
                    and valid_mask[j]
                    and bool(is_green_regime[j]) == green
                ):
                    j += 1
                run_starts.append(i)
                run_ends.append(j)
                i = j

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
                        line=dict(color=color, width=1.7),
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

        for item_idx, item in enumerate(volume_overlay_specs):
            col_name = item["column"]
            if col_name not in df.columns:
                continue
            series = pd.to_numeric(df[col_name], errors="coerce")
            if series.dropna().empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=series,
                    name=item["label"],
                    mode="lines",
                    line=dict(
                        color=strategy_curve_palette[
                            item_idx % len(strategy_curve_palette)
                        ],
                        width=1.4,
                    ),
                    connectgaps=False,
                ),
                row=2,
                col=1,
            )

        # 3. Indicator Ribbons (layer lanes)
        for i, item in enumerate(visible_ribbon_data):
            row = ribbon_row_start + i
            rib = item["ribbon"]
            label = rib.get("label", "Indicator")
            for overlay in item["display_overlays"]:
                self._draw_ribbon_mask_trace(
                    fig=fig,
                    x_values=df["Date"],
                    mask=overlay["mask"],
                    row=row,
                    color=overlay["color"],
                    _lane_width=lane_line_width,
                    name=overlay["name"],
                    hovertemplate=overlay["hovertemplate"],
                    show_markers=overlay["show_markers"],
                    alpha=overlay["alpha"],
                )

            fig.update_yaxes(
                showticklabels=False,
                range=[0.9, 1.1],
                showgrid=False,
                zeroline=False,
                row=row,
                col=1,
            )

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
                text=self._ribbon_annotation_text(rib),
                showarrow=False,
                font=dict(size=10, color=rib.get("color", "#6b7280")),
                align="left",
            )

        # Bottom-most lane: Aggregated state ribbon (single lane)
        agg_lane_min, agg_lane_max = 0.9, 1.1
        agg_lane_span = agg_lane_max - agg_lane_min

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
            showticklabels=False,
            range=[0.9, 1.1],
            showgrid=False,
            zeroline=False,
            row=aggregated_row,
            col=1,
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
        bottom_row = aggregated_row

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
                row_num = 1 if key == "xaxis" else int(key.replace("xaxis", ""))
                is_ribbon_axis = row_num >= ribbon_row_start
                layout[key]["showgrid"] = not is_ribbon_axis
                layout[key]["gridcolor"] = "lightgray"
                layout[key]["ticks"] = "outside" if is_bottom else ""
                layout[key]["showline"] = is_bottom
                layout[key]["zeroline"] = False

        # Force professional global layout
        layout["template"] = "plotly_white"
        layout["xaxis_rangeslider_visible"] = False
        layout["hovermode"] = "x unified"
        # Tunable in config/ribbon_settings.json under layout.left_margin.
        left_margin = int(self._layout_numeric_setting("left_margin", 160))
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
        fig.write_html(
            str(output_path),
            post_script=post_script,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "scrollZoom": True,
            },
        )
        return output_path
