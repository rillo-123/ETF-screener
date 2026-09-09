"""Financially material checks for the separate historical rating evaluator."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ETF_screener.dslx import (
    CandleSeries,
    LiquidityClause,
    _liquidity_clause_matches,
    _match_pattern,
)

spec = importlib.util.spec_from_file_location(
    "dslx_quality_research", Path(__file__).parents[1] / "scripts/rate_dslx_quality.py"
)
research = importlib.util.module_from_spec(spec)
spec.loader.exec_module(research)


def prices(n=300):
    close = 100 + np.arange(n) * 0.05 + np.sin(np.arange(n) / 3) * 4
    return pd.DataFrame(
        {
            "Date": pd.bdate_range("2023-01-01", periods=n),
            "Open": close - 0.2,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": 100000 + np.arange(n) * 500,
        }
    )


def test_research_fills_next_real_open_and_marks_open_positions():
    frame = prices(4)
    frame["Open"] = [10.0, 20.0, 30.0, 40.0]
    frame["Close"] = [15.0, 25.0, 35.0, 45.0]
    base = research.simulate(
        frame, [True, False, False, False], [False, False, True, False], cost=0
    )
    assert base["equity"] == [1.0, 1.25, 1.75, 2.0]
    assert base["trades"][0]["net_pct"] == pytest.approx(100)
    assert base["trades"][0]["entry"] == "2023-01-03"
    assert base["trades"][0]["exit"] == "2023-01-05"
    marked = research.simulate(
        frame, [True, False, False, False], [False] * 4, cost=0.0015
    )
    assert marked["trades"][0]["status"] == "open_mark"
    assert marked["equity"][-1] == pytest.approx(45 / (20 * 1.0015) * 0.9985)
    no_future_fill = research.simulate(frame, [False, False, False, True], [False] * 4)
    assert not no_future_fill["trades"]


def test_research_liquidity_matches_prefix_rules():
    frame = prices()
    clauses = (
        LiquidityClause("avg_turnover", 20, ">=", 10000000),
        LiquidityClause("median_turnover", 20, ">=", 10000000),
        LiquidityClause("active_sessions", 20, ">=", 20),
    )
    mask = research.eligibility(frame, clauses)
    assert not mask[: research.WARMUP].any()
    for i in range(research.WARMUP, len(frame)):
        assert mask[i] == all(
            _liquidity_clause_matches(frame.iloc[: i + 1], c) for c in clauses
        )


def test_research_array_candles_preserve_dslx_and_historical_endpoints():
    frame = prices()
    fast = research.ResearchSeries(frame, style="heikin_ashi")
    ordinary = CandleSeries(frame, style="heikin_ashi")
    specs = research.load_specs(Path("strategies/dslx"))
    for item in specs.values():
        st = item["strategy"]
        for i in (257, 278, 299):
            assert (
                _match_pattern(st, st.entry_struct, fast, i)[0]
                == _match_pattern(st, st.entry_struct, ordinary, i)[0]
            )
            prefix = CandleSeries(frame.iloc[: i + 1], style="heikin_ashi")
            assert (
                _match_pattern(st, st.entry_struct, fast, i)[0]
                == _match_pattern(st, st.entry_struct, prefix, i)[0]
            )


def test_research_period_split_purges_crossing_and_unfinished_outcomes():
    observations = [
        {
            "ticker": "AAA",
            "date": "2024-12-01",
            "ratios": {"20": 1.1},
            "outcome_dates": {"20": "2024-12-30"},
        },
        {
            "ticker": "AAA",
            "date": "2024-12-20",
            "ratios": {"20": 2.0},
            "outcome_dates": {"20": "2025-01-20"},
        },
        {
            "ticker": "AAA",
            "date": "2025-01-20",
            "ratios": {"20": 1.2},
            "outcome_dates": {"20": "2025-02-20"},
        },
        {
            "ticker": "AAA",
            "date": "2026-09-04",
            "ratios": {"20": None},
            "outcome_dates": {"20": None},
        },
    ]
    early = research.observation_summary(observations, end="2025-01-01")
    late = research.observation_summary(observations, start="2025-01-01")
    assert early["n"] == 1
    assert early["mean_net_pct"] == pytest.approx(research.net_pct(1.1))
    assert late["n"] == 1
    assert late["mean_net_pct"] == pytest.approx(research.net_pct(1.2))
