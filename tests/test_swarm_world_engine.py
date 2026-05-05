import math

import pandas as pd

from ETF_screener.swarm_world import SwarmWorldEngine


def test_swarm_world_engine_builds_stable_spherical_world(tmp_path):
    fake_shortlist = pd.DataFrame(
        [
            {
                "ticker": "AAA.DE",
                "as_of_date": "2026-04-23",
                "name": "Core World ETF",
                "issuer": "iShares",
                "asset_class": "Equity",
                "region": "Global",
                "label": "Buy",
                "close": 12.5,
                "volume": 850000,
                "recent_entry_days": 1,
                "product_score": 88.0,
                "exposure_score": 82.0,
                "technical_score": 79.0,
                "final_score": 83.4,
                "components_json": '{"ema_50_slope_pct": 1.2, "close_above_ema_50": 1, "close_above_supertrend": 1, "macd_above_signal": 1}',
            },
            {
                "ticker": "BBB.DE",
                "as_of_date": "2026-04-23",
                "name": "Europe Dividend ETF",
                "issuer": "Vanguard",
                "asset_class": "Equity",
                "region": "Europe",
                "label": "Watch",
                "close": 120.0,
                "volume": 420000,
                "recent_entry_days": 6,
                "product_score": 74.0,
                "exposure_score": 68.0,
                "technical_score": 61.0,
                "final_score": 66.8,
                "components_json": '{"ema_50_slope_pct": 0.5, "close_above_ema_50": 1, "close_above_supertrend": 0, "macd_above_signal": 1}',
            },
            {
                "ticker": "CCC.DE",
                "as_of_date": "2026-04-23",
                "name": "Inverse Tactical ETF",
                "issuer": "Other",
                "asset_class": "Equity",
                "region": "Other",
                "label": "Skip",
                "close": 950.0,
                "volume": 95000,
                "recent_entry_days": None,
                "product_score": 22.0,
                "exposure_score": 18.0,
                "technical_score": 28.0,
                "final_score": 24.4,
                "components_json": '{"ema_50_slope_pct": -1.1, "close_above_ema_50": 0, "close_above_supertrend": 0, "macd_above_signal": 0}',
            },
        ]
    )

    class FakeShortlistEngine:
        def get_shortlist(self, limit=None, refresh=False):
            return fake_shortlist

    engine = SwarmWorldEngine(
        db_path=str(tmp_path / "etfs.db"),
        shortlist_engine=FakeShortlistEngine(),
    )

    built = engine.build_world()
    cached = engine.get_world(limit=None)

    assert len(built) == 3
    assert len(cached) == 3
    assert set(built["world_version"]) == {engine.ARTIFACT_VERSION}
    assert set(built["world_version"]) == {engine.ARTIFACT_VERSION}
    assert built["radius"].gt(0).all()
    assert built["mass"].gt(0).all()
    assert built["sphere_radius"].nunique() == 1
    sphere_radius = float(built.iloc[0]["sphere_radius"])
    assert sphere_radius > 0

    for _, row in built.iterrows():
        vector_length = math.sqrt(
            (row["sphere_x"] ** 2) + (row["sphere_y"] ** 2) + (row["sphere_z"] ** 2)
        )
        assert math.isclose(vector_length, sphere_radius, rel_tol=0.02)
        assert -math.pi / 2 <= float(row["latitude"]) <= math.pi / 2
        assert -math.pi <= float(row["longitude"]) <= math.pi

    ordered = built.sort_values("value").reset_index(drop=True)
    assert (
        ordered.loc[0, "radius"] < ordered.loc[1, "radius"] < ordered.loc[2, "radius"]
    )
    assert ordered.loc[0, "mass"] < ordered.loc[1, "mass"] < ordered.loc[2, "mass"]

    def angular_distance(a, b):
        dot = (
            (a["sphere_x"] * b["sphere_x"])
            + (a["sphere_y"] * b["sphere_y"])
            + (a["sphere_z"] * b["sphere_z"])
        ) / (sphere_radius**2)
        dot = max(-1.0, min(1.0, float(dot)))
        return math.acos(dot)

    for idx, left in built.iterrows():
        for jdx, right in built.iterrows():
            if jdx <= idx:
                continue
            min_angle = ((left["radius"] + right["radius"]) / sphere_radius) * 0.9
            assert angular_distance(left, right) >= min_angle


def test_swarm_world_engine_places_four_equal_assets_as_tetrahedron(tmp_path):
    fake_shortlist = pd.DataFrame(
        [
            {
                "ticker": "AAA.DE",
                "as_of_date": "2026-04-23",
                "name": "Asset A",
                "issuer": "Issuer",
                "asset_class": "Equity",
                "region": "Global",
                "label": "Buy",
                "close": 100.0,
                "volume": 1000,
                "recent_entry_days": 1,
                "product_score": 80.0,
                "exposure_score": 80.0,
                "technical_score": 80.0,
                "final_score": 80.0,
                "components_json": '{"ema_50_slope_pct": 0.0}',
            },
            {
                "ticker": "BBB.DE",
                "as_of_date": "2026-04-23",
                "name": "Asset B",
                "issuer": "Issuer",
                "asset_class": "Equity",
                "region": "Global",
                "label": "Buy",
                "close": 100.0,
                "volume": 1000,
                "recent_entry_days": 1,
                "product_score": 80.0,
                "exposure_score": 80.0,
                "technical_score": 80.0,
                "final_score": 80.0,
                "components_json": '{"ema_50_slope_pct": 0.0}',
            },
            {
                "ticker": "CCC.DE",
                "as_of_date": "2026-04-23",
                "name": "Asset C",
                "issuer": "Issuer",
                "asset_class": "Equity",
                "region": "Global",
                "label": "Buy",
                "close": 100.0,
                "volume": 1000,
                "recent_entry_days": 1,
                "product_score": 80.0,
                "exposure_score": 80.0,
                "technical_score": 80.0,
                "final_score": 80.0,
                "components_json": '{"ema_50_slope_pct": 0.0}',
            },
            {
                "ticker": "DDD.DE",
                "as_of_date": "2026-04-23",
                "name": "Asset D",
                "issuer": "Issuer",
                "asset_class": "Equity",
                "region": "Global",
                "label": "Buy",
                "close": 100.0,
                "volume": 1000,
                "recent_entry_days": 1,
                "product_score": 80.0,
                "exposure_score": 80.0,
                "technical_score": 80.0,
                "final_score": 80.0,
                "components_json": '{"ema_50_slope_pct": 0.0}',
            },
        ]
    )

    class FakeShortlistEngine:
        def get_shortlist(self, limit=None, refresh=False):
            return fake_shortlist

    engine = SwarmWorldEngine(
        db_path=str(tmp_path / "etfs.db"),
        shortlist_engine=FakeShortlistEngine(),
    )

    built = engine.build_world()
    assert len(built) == 4
    assert set(built["world_version"]) == {engine.ARTIFACT_VERSION}

    radii = built["radius"].tolist()
    assert len({round(radius, 6) for radius in radii}) == 1
    asset_radius = float(radii[0])
    sphere_radius = float(built.iloc[0]["sphere_radius"])

    expected_sphere_radius = round(asset_radius * math.sqrt(6.0) / 2.0, 3)
    assert math.isclose(sphere_radius, expected_sphere_radius, rel_tol=0.001)

    def distance(a, b):
        return math.sqrt(
            ((a["sphere_x"] - b["sphere_x"]) ** 2)
            + ((a["sphere_y"] - b["sphere_y"]) ** 2)
            + ((a["sphere_z"] - b["sphere_z"]) ** 2)
        )

    def dot(a, b):
        return (
            (a["sphere_x"] * b["sphere_x"])
            + (a["sphere_y"] * b["sphere_y"])
            + (a["sphere_z"] * b["sphere_z"])
        ) / (sphere_radius**2)

    for _, row in built.iterrows():
        length = math.sqrt(
            (row["sphere_x"] ** 2) + (row["sphere_y"] ** 2) + (row["sphere_z"] ** 2)
        )
        assert math.isclose(length, sphere_radius, rel_tol=0.02)

    for idx, left in built.iterrows():
        for jdx, right in built.iterrows():
            if jdx <= idx:
                continue
            assert math.isclose(distance(left, right), 2 * asset_radius, rel_tol=0.02)
            assert math.isclose(dot(left, right), -1 / 3, rel_tol=0.02)
