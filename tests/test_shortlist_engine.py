import json

import numpy as np
import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.shortlist_engine import ETFShortlistEngine
from ETF_screener.storage import ParquetStorage


def _make_ohlcv(seed: int, slope: float, n: int = 140) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end="2024-04-30", periods=n, freq="B")
    trend = np.linspace(0.0, slope * (n - 1), n)
    close = 100 + trend + rng.normal(0, 0.6, n)
    close = np.maximum(close, 5.0)
    open_ = close + rng.normal(0, 0.3, n)
    high = np.maximum(open_, close) + rng.uniform(0.1, 0.8, n)
    low = np.minimum(open_, close) - rng.uniform(0.1, 0.8, n)
    volume = rng.integers(400_000, 900_000, n)
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume.astype(int),
        }
    )


def _prepare_engine(tmp_path):
    db_path = tmp_path / "etfs.db"
    meta_path = tmp_path / "etfs.json"
    parquet_dir = tmp_path / "parquet"

    metadata = {
        "CORE.DE": {
            "status": "active",
            "name": "iShares Core MSCI World UCITS ETF",
        },
        "LEVD.DE": {
            "status": "active",
            "name": "L+G DAX Daily 2X Long",
        },
    }
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")

    db = ETFDatabase(db_path=str(db_path))
    db.insert_dataframe(_make_ohlcv(seed=1, slope=0.18), "CORE.DE")
    db.insert_dataframe(_make_ohlcv(seed=2, slope=0.12), "LEVD.DE")

    engine = ETFShortlistEngine(
        db_path=str(db_path),
        metadata_path=str(meta_path),
        storage=ParquetStorage(data_dir=str(parquet_dir)),
    )
    return db, engine


def test_shortlist_engine_builds_and_ranks_artifacts(tmp_path):
    db, engine = _prepare_engine(tmp_path)

    df = engine.get_shortlist(limit=10, refresh=True, max_workers=2)

    assert list(df["ticker"]) == ["CORE.DE", "LEVD.DE"]
    assert float(df.iloc[0]["final_score"]) > float(df.iloc[1]["final_score"])
    assert df.iloc[0]["label"] in {"Buy", "Watch"}
    assert db.get_latest_shortlist_date() == db.get_latest_market_date()


def test_shortlist_engine_reuses_fresh_snapshot(tmp_path, monkeypatch):
    _, engine = _prepare_engine(tmp_path)
    first = engine.get_shortlist(limit=10, refresh=True, max_workers=2)

    monkeypatch.setattr(
        engine,
        "build_shortlist",
        lambda max_workers=None: (_ for _ in ()).throw(
            AssertionError("build_shortlist should not run when artifacts are fresh")
        ),
    )

    second = engine.get_shortlist(limit=10, refresh=False, max_workers=2)

    assert second["ticker"].tolist() == first["ticker"].tolist()
