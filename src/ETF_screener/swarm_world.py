"""Build and cache a rectangular ticker world for the Swarm dashboard tab."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Optional

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.shortlist_engine import ETFShortlistEngine


class SwarmWorldEngine:
    """Project shortlist artifacts into a stable rectangular swarm world."""

    ARTIFACT_VERSION = "swarm_v3_grid"
    WORLD_WIDTH = 1600.0
    WORLD_HEIGHT = 920.0

    def __init__(
        self,
        db_path: str | None = None,
        shortlist_engine: Optional[ETFShortlistEngine] = None,
    ):
        self.db = ETFDatabase(db_path=db_path)
        self.shortlist_engine = shortlist_engine or ETFShortlistEngine(db_path=db_path)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
            if pd.isna(result):
                return default
            return result
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            if value is None or pd.isna(value):
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_components(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _stable_fraction(text: str, salt: str = "") -> float:
        digest = hashlib.sha256(f"{salt}:{text}".encode("utf-8")).hexdigest()
        return int(digest[:12], 16) / float((16**12) - 1)

    @classmethod
    def _clamp(cls, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _freshness_score(self, recent_entry_days: Any) -> float:
        if recent_entry_days is None or pd.isna(recent_entry_days):
            return 22.0
        age = max(0.0, float(recent_entry_days))
        return self._clamp(100.0 - (age * 7.5), 0.0, 100.0)

    def _momentum_score(self, components: dict[str, Any]) -> float:
        slope_pct = self._safe_float(components.get("ema_50_slope_pct"))
        base = 50.0 + (slope_pct * 16.0)
        base += 12.0 * self._safe_float(components.get("close_above_ema_50"))
        base += 12.0 * self._safe_float(components.get("close_above_supertrend"))
        base += 8.0 * self._safe_float(components.get("macd_above_signal"))
        return self._clamp(base, 0.0, 100.0)

    def _energy_score(
        self, row: pd.Series, components: dict[str, Any]
    ) -> tuple[float, float, float]:
        final_score = self._safe_float(row.get("final_score"))
        technical_score = self._safe_float(row.get("technical_score"))
        product_score = self._safe_float(row.get("product_score"))
        freshness_score = self._freshness_score(row.get("recent_entry_days"))
        momentum_score = self._momentum_score(components)

        label = str(row.get("label") or "Watch")
        label_bonus = {"Buy": 8.0, "Watch": 2.0, "Skip": -6.0}.get(label, 0.0)

        energy = (
            (0.42 * final_score)
            + (0.24 * technical_score)
            + (0.12 * product_score)
            + (0.12 * freshness_score)
            + (0.10 * momentum_score)
            + label_bonus
        )
        return (
            self._clamp(energy, 5.0, 100.0),
            momentum_score,
            freshness_score,
        )

    @staticmethod
    def _color_for_label(label: str) -> str:
        if label == "Buy":
            return "#10b981"
        if label == "Watch":
            return "#f59e0b"
        return "#f43f5e"

    def _radius_for_row(
        self,
        row: pd.Series,
        min_log_volume: float,
        max_log_volume: float,
    ) -> float:
        volume = max(1.0, self._safe_float(row.get("volume"), 1.0))
        log_volume = math.log10(volume)
        if max_log_volume > min_log_volume:
            volume_norm = (log_volume - min_log_volume) / (
                max_log_volume - min_log_volume
            )
        else:
            volume_norm = 0.5

        label = str(row.get("label") or "Watch")
        label_bonus = {"Buy": 2.0, "Watch": 1.0, "Skip": 0.2}.get(label, 0.5)
        return round(4.0 + (volume_norm * 5.0) + label_bonus, 2)

    def _prepare_nodes(self, shortlist_df: pd.DataFrame) -> list[dict[str, Any]]:
        if shortlist_df.empty:
            return []

        volume_logs = [
            math.log10(max(1.0, self._safe_float(row.get("volume"), 1.0)))
            for _, row in shortlist_df.iterrows()
        ]
        min_log_volume = min(volume_logs) if volume_logs else 0.0
        max_log_volume = max(volume_logs) if volume_logs else 1.0

        nodes: list[dict[str, Any]] = []
        for _, row in shortlist_df.iterrows():
            components = self._parse_components(row.get("components_json"))
            energy, momentum_score, freshness_score = self._energy_score(
                row, components
            )
            final_score = self._safe_float(row.get("final_score"))
            technical_score = self._safe_float(row.get("technical_score"))
            row_payload = {
                "ticker": str(row.get("ticker") or "").upper(),
                "as_of_date": str(row.get("as_of_date") or ""),
                "name": str(row.get("name") or row.get("ticker") or ""),
                "issuer": str(row.get("issuer") or ""),
                "asset_class": str(row.get("asset_class") or ""),
                "region": str(row.get("region") or ""),
                "label": str(row.get("label") or "Watch"),
                "volume": self._safe_int(row.get("volume"), 0),
                "recent_entry_days": (
                    self._safe_int(row.get("recent_entry_days"))
                    if row.get("recent_entry_days") is not None
                    and not pd.isna(row.get("recent_entry_days"))
                    else None
                ),
                "product_score": round(self._safe_float(row.get("product_score")), 2),
                "exposure_score": round(self._safe_float(row.get("exposure_score")), 2),
                "technical_score": round(technical_score, 2),
                "final_score": round(final_score, 2),
                "energy": round(energy, 2),
                "momentum_score": round(momentum_score, 2),
                "freshness_score": round(freshness_score, 2),
                "radius": self._radius_for_row(row, min_log_volume, max_log_volume),
                "color": self._color_for_label(str(row.get("label") or "Watch")),
                "components": components,
                "world_version": self.ARTIFACT_VERSION,
            }
            nodes.append(row_payload)

        return nodes

    @classmethod
    def grid_dimensions(cls, node_count: int) -> tuple[int, int]:
        """Return square-ish grid columns and rows for the ticker count."""
        clean_count = max(1, int(node_count or 1))
        columns = max(
            1, math.ceil(math.sqrt(clean_count * (cls.WORLD_WIDTH / cls.WORLD_HEIGHT)))
        )
        rows = max(1, math.ceil(clean_count / columns))
        return columns, rows

    @classmethod
    def grid_cell_size(cls, columns: int, rows: int) -> tuple[float, float]:
        clean_columns = max(1, int(columns or 1))
        clean_rows = max(1, int(rows or 1))
        return cls.WORLD_WIDTH / clean_columns, cls.WORLD_HEIGHT / clean_rows

    def _position_nodes(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not nodes:
            return nodes

        columns, rows = self.grid_dimensions(len(nodes))
        cell_width, cell_height = self.grid_cell_size(columns, rows)
        available_cells = [(row, col) for row in range(rows) for col in range(columns)]
        available_cells.sort(
            key=lambda cell: self._stable_fraction(f"{cell[0]}:{cell[1]}", "grid-cell")
        )

        used_cells: set[tuple[int, int]] = set()
        for idx, node in enumerate(nodes):
            ticker = node["ticker"]
            row, col = available_cells[
                int(self._stable_fraction(ticker, "ticker-grid") * len(available_cells))
                % len(available_cells)
            ]
            if (row, col) in used_cells:
                row, col = next(
                    cell for cell in available_cells if cell not in used_cells
                )
            used_cells.add((row, col))
            node["row"] = row
            node["col"] = col
            node["x"] = round((col + 0.5) * cell_width, 2)
            node["y"] = round((row + 0.5) * cell_height, 2)
            node["vx"] = 0.0
            node["vy"] = 0.0
            node["charge"] = round(
                0.8 + (self._safe_float(node.get("energy")) / 100.0) * 2.2, 4
            )
            node["is_dummy"] = False

        return nodes

    def build_world(self, refresh_shortlist: bool = False) -> pd.DataFrame:
        shortlist_df = self.shortlist_engine.get_shortlist(
            limit=None, refresh=refresh_shortlist
        )
        if shortlist_df.empty:
            return pd.DataFrame()

        nodes = self._position_nodes(self._prepare_nodes(shortlist_df))
        self.db.upsert_swarm_world_artifacts(
            [
                {
                    **node,
                    "components_json": json.dumps(node.get("components", {})),
                }
                for node in nodes
            ]
        )
        return self.db.get_swarm_world(limit=None)

    def get_world(
        self,
        limit: int | None = None,
        label: str | None = None,
        refresh: bool = False,
    ) -> pd.DataFrame:
        shortlist_date = self.db.get_latest_shortlist_date()
        world_date = self.db.get_latest_swarm_world_date()
        cached_world = self.db.get_swarm_world(limit=1)
        cached_version = (
            str(cached_world.iloc[0].get("world_version"))
            if not cached_world.empty and "world_version" in cached_world.columns
            else None
        )

        if (
            refresh
            or not world_date
            or world_date != shortlist_date
            or cached_version != self.ARTIFACT_VERSION
        ):
            self.build_world(refresh_shortlist=refresh)

        return self.db.get_swarm_world(limit=limit, label=label)
