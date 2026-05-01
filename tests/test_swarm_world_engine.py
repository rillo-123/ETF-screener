import pandas as pd

from ETF_screener.swarm_world import SwarmWorldEngine


def test_swarm_world_engine_builds_stable_rectangular_world(tmp_path):
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
    columns, rows = engine.grid_dimensions(len(fake_shortlist))
    cell_width, cell_height = engine.grid_cell_size(columns, rows)
    assert columns > 0
    assert rows > 0
    assert built["x"].between(0, engine.WORLD_WIDTH).all()
    assert built["y"].between(0, engine.WORLD_HEIGHT).all()
    assert built["radius"].gt(0).all()
    assert set(built["world_version"]) == {engine.ARTIFACT_VERSION}
    assert set(built["world_version"]) == {"swarm_v3_grid"}
    assert built[["grid_row", "grid_col"]].drop_duplicates().shape[0] == len(built)
    assert built["grid_row"].between(0, rows - 1).all()
    assert built["grid_col"].between(0, columns - 1).all()
    for _, row in built.iterrows():
        assert row["x"] == round((row["grid_col"] + 0.5) * cell_width, 2)
        assert row["y"] == round((row["grid_row"] + 0.5) * cell_height, 2)

    energies = built.set_index("ticker")["energy"].to_dict()
    assert energies["AAA.DE"] > energies["BBB.DE"] > energies["CCC.DE"]
