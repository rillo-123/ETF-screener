"""Build and cache a spherical asset world for the Swarm dashboard tab."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Optional

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.shortlist_engine import ETFShortlistEngine


class SwarmWorldEngine:
    """Project shortlist artifacts into a stable spherical asset world."""

    ARTIFACT_VERSION = "swarm_v6_sphere_tetra"
    MIN_WORLD_RADIUS = 20.0
    PACKING_DENSITY = 0.42

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
    def _clamp(_cls, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _normalize_vector(
        vector: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        x, y, z = vector
        length = math.sqrt((x * x) + (y * y) + (z * z))
        if length <= 1e-12:
            return (0.0, 1.0, 0.0)
        return (x / length, y / length, z / length)

    @staticmethod
    def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
        return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])

    @staticmethod
    def _scale(
        vector: tuple[float, float, float], factor: float
    ) -> tuple[float, float, float]:
        return (vector[0] * factor, vector[1] * factor, vector[2] * factor)

    @staticmethod
    def _subtract(
        a: tuple[float, float, float], b: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    @staticmethod
    def _add(
        a: tuple[float, float, float], b: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    @staticmethod
    def _fibonacci_vector(
        index: int, total: int, seed: str = ""
    ) -> tuple[float, float, float]:
        count = max(1, int(total or 1))
        idx = max(0, min(count - 1, int(index or 0)))
        phase = SwarmWorldEngine._stable_fraction(seed, "sphere-index") if seed else 0.0
        golden_angle = math.pi * (3 - math.sqrt(5))
        y = 1 - ((idx + 0.5) / count) * 2
        radius = math.sqrt(max(0.0, 1 - (y * y)))
        theta = (idx + phase) * golden_angle
        return SwarmWorldEngine._normalize_vector(
            (
                math.cos(theta) * radius,
                y,
                math.sin(theta) * radius,
            )
        )

    def _asset_value(self, row: pd.Series) -> float:
        close = self._safe_float(row.get("close"))
        if close > 0:
            return close
        final_score = self._safe_float(row.get("final_score"))
        return max(0.01, final_score if final_score > 0 else 1.0)

    def _asset_radius(self, value: float) -> float:
        log_value = math.log10(max(1.0, value))
        return round(self._clamp(1.35 + (log_value * 0.95), 1.35, 8.5), 3)

    def _asset_mass(self, value: float) -> float:
        log_value = math.log10(max(1.0, value))
        return round(self._clamp(0.9 + (log_value * 0.85), 0.9, 10.0), 3)

    def _asset_energy(self, row: pd.Series, components: dict[str, Any]) -> float:
        final_score = self._safe_float(row.get("final_score"))
        technical_score = self._safe_float(row.get("technical_score"))
        product_score = self._safe_float(row.get("product_score"))
        momentum_score = self._safe_float(components.get("ema_50_slope_pct")) * 14.0
        value_bonus = math.log10(max(1.0, self._asset_value(row))) * 6.0
        return self._clamp(
            (0.44 * final_score)
            + (0.24 * technical_score)
            + (0.14 * product_score)
            + momentum_score
            + value_bonus,
            5.0,
            100.0,
        )

    def _sphere_radius(self, nodes: list[dict[str, Any]]) -> float:
        if not nodes:
            return self.MIN_WORLD_RADIUS
        if len(nodes) == 4:
            max_radius = max(float(node["radius"]) for node in nodes)
            return round(max_radius * (math.sqrt(6.0) / 2.0), 3)
        area_sum = sum(math.pi * (float(node["radius"]) ** 2) for node in nodes)
        estimated = math.sqrt(area_sum / (4 * math.pi * self.PACKING_DENSITY))
        scaled = max(self.MIN_WORLD_RADIUS, estimated)
        scaled = max(scaled, math.sqrt(len(nodes)) * 3.0)
        return round(scaled, 3)

    @staticmethod
    def _tetrahedron_vectors() -> list[tuple[float, float, float]]:
        return [
            SwarmWorldEngine._normalize_vector((1.0, 1.0, 1.0)),
            SwarmWorldEngine._normalize_vector((-1.0, -1.0, 1.0)),
            SwarmWorldEngine._normalize_vector((-1.0, 1.0, -1.0)),
            SwarmWorldEngine._normalize_vector((1.0, -1.0, -1.0)),
        ]

    def _relax_positions(
        self,
        nodes: list[dict[str, Any]],
        sphere_radius: float,
        passes: int = 5,
    ) -> None:
        if len(nodes) < 2:
            return

        for _ in range(max(0, int(passes))):
            for idx, node in enumerate(nodes):
                current = (
                    float(node["sphere_x"]) / sphere_radius,
                    float(node["sphere_y"]) / sphere_radius,
                    float(node["sphere_z"]) / sphere_radius,
                )
                for offset in range(1, min(10, len(nodes))):
                    other = nodes[(idx + offset) % len(nodes)]
                    other_vec = (
                        float(other["sphere_x"]) / sphere_radius,
                        float(other["sphere_y"]) / sphere_radius,
                        float(other["sphere_z"]) / sphere_radius,
                    )
                    dot = self._clamp(self._dot(current, other_vec), -1.0, 1.0)
                    angle = math.acos(dot)
                    min_angle = (
                        (float(node["radius"]) + float(other["radius"]))
                        / max(1.0, sphere_radius)
                    ) * 1.04
                    if angle >= min_angle:
                        continue
                    tangent = self._subtract(other_vec, self._scale(current, dot))
                    tangent = self._normalize_vector(tangent)
                    push = ((min_angle - angle) / max(min_angle, 1e-6)) * 0.22
                    current = self._normalize_vector(
                        self._subtract(current, self._scale(tangent, push))
                    )
                    other_vec = self._normalize_vector(
                        self._add(other_vec, self._scale(tangent, push))
                    )
                    other["sphere_x"] = round(other_vec[0] * sphere_radius, 6)
                    other["sphere_y"] = round(other_vec[1] * sphere_radius, 6)
                    other["sphere_z"] = round(other_vec[2] * sphere_radius, 6)
                    other["latitude"] = round(
                        math.asin(self._clamp(other_vec[1], -1.0, 1.0)), 6
                    )
                    other["longitude"] = round(
                        math.atan2(other_vec[2], other_vec[0]), 6
                    )
                node["sphere_x"] = round(current[0] * sphere_radius, 6)
                node["sphere_y"] = round(current[1] * sphere_radius, 6)
                node["sphere_z"] = round(current[2] * sphere_radius, 6)
                node["latitude"] = round(
                    math.asin(self._clamp(current[1], -1.0, 1.0)), 6
                )
                node["longitude"] = round(math.atan2(current[2], current[0]), 6)

    def _prepare_rows(self, shortlist_df: pd.DataFrame) -> list[dict[str, Any]]:
        if shortlist_df.empty:
            return []

        rows = shortlist_df.copy()
        rows["__order"] = (
            rows["ticker"]
            .astype(str)
            .map(lambda ticker: self._stable_fraction(ticker.upper(), "sphere-order"))
        )
        rows = rows.sort_values(
            by=["__order", "final_score", "ticker"],
            ascending=[True, False, True],
        ).reset_index(drop=True)

        prepared: list[dict[str, Any]] = []
        for _, row in rows.iterrows():
            components = self._parse_components(row.get("components_json"))
            value = self._asset_value(row)
            radius = self._asset_radius(value)
            mass = self._asset_mass(value)
            energy = self._asset_energy(row, components)
            prepared.append(
                {
                    "ticker": str(row.get("ticker") or "").upper(),
                    "as_of_date": str(row.get("as_of_date") or ""),
                    "name": str(row.get("name") or row.get("ticker") or ""),
                    "issuer": str(row.get("issuer") or ""),
                    "asset_class": str(row.get("asset_class") or ""),
                    "region": str(row.get("region") or ""),
                    "label": str(row.get("label") or "Watch"),
                    "close": round(self._safe_float(row.get("close"), value), 4),
                    "value": round(value, 4),
                    "mass": mass,
                    "volume": self._safe_int(row.get("volume"), 0),
                    "recent_entry_days": (
                        self._safe_int(row.get("recent_entry_days"))
                        if row.get("recent_entry_days") is not None
                        and not pd.isna(row.get("recent_entry_days"))
                        else None
                    ),
                    "product_score": round(
                        self._safe_float(row.get("product_score")), 2
                    ),
                    "exposure_score": round(
                        self._safe_float(row.get("exposure_score")), 2
                    ),
                    "technical_score": round(
                        self._safe_float(row.get("technical_score")), 2
                    ),
                    "final_score": round(self._safe_float(row.get("final_score")), 2),
                    "energy": round(energy, 2),
                    "momentum_score": round(
                        self._safe_float(components.get("ema_50_slope_pct")) * 14.0, 2
                    ),
                    "freshness_score": round(
                        100.0
                        - (
                            max(
                                0.0, self._safe_float(row.get("recent_entry_days"), 0.0)
                            )
                            * 7.0
                        ),
                        2,
                    ),
                    "radius": radius,
                    "components": components,
                }
            )

        sphere_radius = self._sphere_radius(prepared)
        tetrahedron_mode = len(prepared) == 4
        tetra_vectors = self._tetrahedron_vectors() if tetrahedron_mode else []
        for idx, node in enumerate(prepared):
            direction = (
                tetra_vectors[idx]
                if tetrahedron_mode
                else self._fibonacci_vector(idx, len(prepared), node["ticker"])
            )
            node["sphere_radius"] = sphere_radius
            node["sphere_x"] = round(direction[0] * sphere_radius, 6)
            node["sphere_y"] = round(direction[1] * sphere_radius, 6)
            node["sphere_z"] = round(direction[2] * sphere_radius, 6)
            node["latitude"] = round(math.asin(self._clamp(direction[1], -1.0, 1.0)), 6)
            node["longitude"] = round(math.atan2(direction[2], direction[0]), 6)
            node["x"] = node["sphere_x"]
            node["y"] = node["sphere_y"]
            node["z"] = node["sphere_z"]
            node["grid_row"] = idx
            node["grid_col"] = 0
            node["color"] = "#f8fafc" if node["label"] == "Buy" else "#cbd5e1"
            node["world_version"] = self.ARTIFACT_VERSION

        if not tetrahedron_mode:
            self._relax_positions(prepared, sphere_radius)

        for idx, node in enumerate(prepared):
            node["sphere_radius"] = sphere_radius
            node["x"] = round(node["sphere_x"], 6)
            node["y"] = round(node["sphere_y"], 6)
            node["z"] = round(node["sphere_z"], 6)
            node["grid_row"] = idx
            node["grid_col"] = 0
            node["radius"] = round(node["radius"], 3)
            node["mass"] = round(node["mass"], 3)

        return prepared

    def build_world(self, refresh_shortlist: bool = False) -> pd.DataFrame:
        shortlist_df = self.shortlist_engine.get_shortlist(refresh=refresh_shortlist)
        if shortlist_df.empty:
            return pd.DataFrame()

        rows = self._prepare_rows(shortlist_df)
        self.db.upsert_swarm_world_artifacts(
            [
                {
                    **row,
                    "components_json": json.dumps(row.get("components", {})),
                }
                for row in rows
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
        cached_layout = (
            str(cached_world.iloc[0].get("layout"))
            if not cached_world.empty and "layout" in cached_world.columns
            else None
        )

        if (
            refresh
            or not world_date
            or world_date != shortlist_date
            or cached_version != self.ARTIFACT_VERSION
            or cached_layout == "grid"
        ):
            self.build_world(refresh_shortlist=refresh)

        return self.db.get_swarm_world(limit=limit, label=label)
