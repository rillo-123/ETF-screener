import pandas as pd
import pytest

from ETF_screener.dslx import (
    CandleSeries,
    DSLXEvaluationError,
    DSLXInterpreter,
    DSLXProgramInterpreter,
    DSLXSyntaxError,
    MatchList,
    parse_program,
    parse_strategy,
)


def _candles() -> pd.DataFrame:
    close = [10.0 + index for index in range(30)]
    return pd.DataFrame(
        {
            "Open": [value - 0.5 for value in close],
            "High": [value + 0.8 for value in close],
            "Low": [value - 0.9 for value in close],
            "Close": close,
            "Volume": [1000.0] * 30,
        }
    )


def test_dslx_strategy_evaluates_documented_when_rules():
    interpreter = DSLXInterpreter(
        """
        strategy trend_following {
          execution { entry: next_open, exit: close }
          entry when candle => candle.close > candle.ema(20) AND candle.rsi(14) > 50
          exit when candle => candle.close < candle.ema(20)
        }
        """
    )

    assert interpreter.strategy.name == "trend_following"
    assert interpreter.strategy.entry_execution == "next_open"
    assert interpreter.strategy.exit_execution == "close"
    assert interpreter.matches_entry(_candles()) is True
    assert interpreter.matches_exit(_candles()) is False


def test_dslx_window_predicates_are_consecutive_and_safe():
    interpreter = DSLXInterpreter(
        """
        strategy green_sequence {
          entry when candle => candle.window(3).all(c => c.close > c.open)
        }
        """
    )

    assert interpreter.matches_entry(_candles()) is True
    assert interpreter.matches_entry(_candles().iloc[:2]) is False


def test_dslx_accepts_c_style_logical_operators():
    interpreter = DSLXInterpreter(
        """
        strategy c_style_operators {
          entry when candle => candle.is_green && !candle.is_doji || candle.is_red
        }
        """
    )

    assert interpreter.matches_entry(_candles()) is True


def test_dslx_supports_previous_window_aggregates_and_chained_comparisons():
    interpreter = DSLXInterpreter(
        """
        strategy breakout {
          entry when candle => candle.close > candle.previous(1).window(20).high.max()
            AND 40 < candle.rsi(14) < 101
        }
        """
    )

    assert interpreter.matches_entry(_candles()) is True


def test_candle_exposes_complete_visible_geometry():
    candle = CandleSeries(
        pd.DataFrame(
            {
                "Open": [12.0],
                "High": [15.0],
                "Low": [9.0],
                "Close": [10.0],
                "Volume": [1000.0],
            }
        )
    ).last

    assert candle.color == "red"
    assert candle.is_red is True
    assert candle.is_green is False
    assert candle.is_doji is False
    assert candle.total_length == candle.range == 6.0
    assert candle.body_length == 2.0
    assert candle.upper_wick_length == 3.0
    assert candle.lower_wick_length == 1.0
    assert candle.body_ratio == pytest.approx(2 / 6)
    assert candle.upper_wick_ratio == pytest.approx(3 / 6)
    assert candle.lower_wick_ratio == pytest.approx(1 / 6)


def test_dslx_can_filter_on_candle_geometry_and_doji():
    interpreter = DSLXInterpreter(
        """
        strategy long_lower_wick {
          entry when candle => candle.color == "green"
            AND candle.lower_wick_ratio > 0.4
            AND candle.body_ratio < 0.4
        }
        """
    )
    frame = pd.DataFrame(
        {
            "Open": [12.0], "High": [13.0], "Low": [8.0], "Close": [13.0],
            "Volume": [1000.0],
        }
    )

    assert interpreter.matches_entry(frame) is True
    doji = CandleSeries(frame.assign(Close=12.0)).last
    assert doji.color == "doji"
    assert doji.is_doji is True
    assert doji.body_ratio == 0.0


def test_dslx_supports_source_aware_indicators_and_indicator_slope():
    interpreter = DSLXInterpreter(
        """
        strategy source_aware {
          entry when candle => candle.ema("high", 20).slope > 0
            && candle.rsi(14).slope >= 0
            && candle.volume >= candle.volume_ema(20)
        }
        """
    )

    assert interpreter.matches_entry(_candles()) is True


def test_dslx_parses_candle_centred_strategy_declarations():
    strategy = parse_strategy(
        """
        strategy ha_breakout {
          source universe.selected
          candles timeframe "1d" as heikin_ashi
          scan within 10 candles
          match when candle => candle.is_green && candle.rsi(14) > 50
        }
        """
    )

    assert strategy.source == "universe.selected"
    assert strategy.timeframe == "1d"
    assert strategy.candle_style == "heikin_ashi"
    assert strategy.scan == "within:10"


def test_dslx_run_returns_composable_provenance_carrying_match_lists():
    latest = _candles()
    latest.loc[29, "Open"] = latest.loc[29, "Close"] - 1
    interpreter = DSLXInterpreter(
        "strategy green { scan latest match when candle => candle.is_green }"
    )

    matches = interpreter.run(
        {"AAA": latest, "BBB": latest.assign(Open=latest["Close"] + 1)}
    )

    assert len(matches) == 1
    assert matches[0].strategy == "green"
    assert matches[0].ticker == "AAA"
    assert matches[0].age == 0
    assert (matches + MatchList()).show()[0]["strategy"] == "green"


def test_dslx_program_parses_strategy_execution_and_display():
    program = parse_program(
        """
        strategy green { source universe.selected scan latest match when candle => candle.is_green }
        let matches = green.run()
        let combined = matches + matches
        combined.show()
        """
    )

    assert program.strategies[0].name == "green"
    assert program.runs == (("matches", "green"),)
    assert program.merges == (("combined", "matches", "matches"),)
    assert program.shows == ("combined",)


def test_dslx_program_runs_selected_universe_and_returns_shown_list():
    interpreter = DSLXProgramInterpreter(
        """
        strategy green { source universe.selected scan latest match when candle => candle.is_green }
        let matches = green.run()
        matches.show()
        """
    )
    results = interpreter.run(selected={"AAA": _candles()})

    assert list(results) == ["matches"]
    assert results["matches"][0].ticker == "AAA"


def test_heikin_ashi_candle_series_exposes_transformed_visual_geometry():
    frame = pd.DataFrame(
        {
            "Open": [10.0, 12.0], "High": [13.0, 15.0], "Low": [9.0, 11.0],
            "Close": [12.0, 14.0], "Volume": [1000.0, 1000.0],
        }
    )
    candle = CandleSeries(frame, style="heikin_ashi").last

    assert candle.open == pytest.approx(11.0)
    assert candle.close == pytest.approx(13.0)
    assert candle.color == "green"


def test_dslx_rejects_unknown_sections_and_python_syntax():
    with pytest.raises(DSLXSyntaxError, match="Unknown strategy section"):
        parse_strategy("strategy bad { import when candle => true }")
    interpreter = DSLXInterpreter(
        "strategy bad { entry when candle => __import__('os') }"
    )
    with pytest.raises(DSLXEvaluationError, match="Unknown name"):
        interpreter.matches_entry(_candles())
