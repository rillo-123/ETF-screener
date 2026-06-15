from pathlib import Path

from ETF_screener.dsl_parser import parse_strategy_structure_profile


def _strategy_text(name: str) -> str:
    return (Path("strategies") / f"{name}.dsl").read_text(encoding="utf-8")


def test_structure_profile_scores_ema_breakout_fanout_as_trend_heavy():
    profile = parse_strategy_structure_profile(_strategy_text("ema_breakout_fanout"))

    axes = profile["structure_axes"]
    assert axes["trend_context"] >= 8
    assert axes["confirmation_depth"] >= 7
    assert axes["exit_discipline"] >= 6
    assert "trend_gated" in profile["structure_tags"]
    assert profile["structure_score"] == round(
        sum(axes.values()) / len(axes), 2
    )


def test_structure_profile_scores_anchored_vwap_reclaim_as_precise_and_time_bounded():
    profile = parse_strategy_structure_profile(
        _strategy_text("anchored_vwap_reclaim")
    )

    axes = profile["structure_axes"]
    assert axes["trigger_precision"] >= 7
    assert axes["risk_control"] >= 7
    assert axes["time_discipline"] >= 8
    assert "has_time_stop" in profile["structure_tags"]


def test_structure_profile_missing_max_days_still_keeps_time_discipline_positive():
    fanout_profile = parse_strategy_structure_profile(
        _strategy_text("ema_breakout_fanout")
    )
    rsi_profile = parse_strategy_structure_profile(_strategy_text("rsi_risk_mitigated"))

    fanout_axes = fanout_profile["structure_axes"]
    rsi_axes = rsi_profile["structure_axes"]
    assert rsi_axes["time_discipline"] > 0
    assert rsi_axes["exit_discipline"] >= 6
    assert rsi_axes["risk_control"] >= 5
    assert rsi_axes["trend_context"] < fanout_axes["trend_context"]


def test_structure_profile_returns_zeroed_profile_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        "ETF_screener.dsl_parser.parse_strategy_blocks",
        lambda _content: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    profile = parse_strategy_structure_profile("TRIGGER: close > ema_20")

    assert profile["structure_score"] == 0.0
    assert all(value == 0.0 for value in profile["structure_axes"].values())
    assert profile["structure_tags"] == ["profile_unavailable"]
