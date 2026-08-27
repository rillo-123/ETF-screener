import pandas as pd
import pytest

from ETF_screener.dslx import (
    CandleSeries,
    DSLXEvaluationError,
    DSLXInterpreter,
    DSLXProgramInterpreter,
    DSLXSyntaxError,
    MatchList,
    backtest_signals,
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


def test_dslx_requires_an_explicit_exit_and_accepts_pass_as_a_no_op():
    with pytest.raises(DSLXSyntaxError, match="needs an exit rule"):
        parse_strategy("strategy incomplete { entry when candle => candle.is_green }")

    interpreter = DSLXInterpreter(
        "strategy hold { entry when candle => candle.is_green exit when candle => pass }"
    )
    assert interpreter.matches_exit(_candles()) is False


def test_dslx_backtest_signals_are_historical_and_preserve_no_op_exits():
    signals = backtest_signals(
        """
        strategy green {
          entry when candle => candle.is_green
          exit when candle => pass
        }
        let matches = green.run()
        matches.show()
        """,
        _candles(),
    )

    assert bool(signals["entry_condition"].iloc[-1]) is True
    assert signals["exit_condition"].sum() == 0
    assert signals["signal"].sum() == 1
    assert signals["signal"].iloc[-1] == 0


def test_dslx_exit_rules_can_reference_the_open_position_entry_price():
    frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 104.0, 106.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.0, 102.0, 104.0],
            "Volume": [1_000.0, 1_000.0, 1_000.0],
        }
    )
    signals = backtest_signals(
        """
        strategy fixed_target {
          candles timeframe "1d" as regular
          entry at candle.close when candle => candle.close == 100
          exit when candle => candle.high >= position.entry_price * 1.03
        }
        """,
        frame,
    )

    assert signals["signal"].tolist() == [1, -1, 0]
    assert signals["entry_fill_price"].iloc[0] == pytest.approx(100.0)
    assert signals["exit_condition"].tolist() == [False, True, False]
    assert signals["exit_fill_price"].iloc[1] == pytest.approx(103.0)


def test_dslx_window_predicates_are_consecutive_and_safe():
    interpreter = DSLXInterpreter(
        """
        strategy green_sequence {
          entry when candle => candle.window(3).all(c => c.close > c.open)
          exit when candle => pass
        }
        """
    )

    assert interpreter.matches_entry(_candles()) is True
    assert interpreter.matches_entry(_candles().iloc[:2]) is False


def test_dslx_compares_adjacent_candles_with_arbitrary_previous_offsets():
    candles = pd.DataFrame(
        {
            "Open": [10.0, 9.0, 11.0],
            "High": [11.0, 12.0, 14.0],
            "Low": [8.0, 8.0, 10.0],
            "Close": [9.0, 11.0, 13.0],
            "Volume": [1_000.0, 2_000.0, 3_000.0],
        }
    )
    interpreter = DSLXInterpreter(
        """
        strategy two_candle_reversal {
          candles timeframe "1d" as regular
          entry when candle => candle.is_green
            AND candle.previous(1).is_green
            AND candle.close > candle.previous(1).high
            AND candle.previous(2).is_red
          exit when candle => pass
        }
        """
    )

    assert interpreter.matches_entry(candles) is True
    assert interpreter.matches_entry(candles.iloc[:2]) is False


def test_dslx_named_candle_structs_define_consecutive_pattern_order():
    candles = pd.DataFrame(
        {
            "Open": [10.0, 9.0, 11.0],
            "High": [11.0, 12.0, 14.0],
            "Low": [8.0, 8.5, 10.0],
            "Close": [9.0, 11.0, 13.0],
            "Volume": [1_000.0, 2_000.0, 3_000.0],
        }
    )
    source = """
        strategy consecutive_breakout {
          candle breakout {
            when => is_green && close > recovery.high
          }
          candle setup {
            when => is_red
          }
          candle recovery {
            when => is_green && low > setup.low
          }
          candle breakdown {
            when => is_red
          }
          entrystruct {
            setup
            recovery
            breakout
            at breakout.close
          }
          exitstruct {
            breakdown
          }
        }
    """
    interpreter = DSLXInterpreter(source)

    assert interpreter.matches_entry(candles) is True
    assert interpreter.matches_entry(candles.iloc[:2]) is False
    matches = interpreter.run({"PATTERN": candles})
    assert [name for name, _candle in matches[0].pattern] == [
        "setup", "recovery", "breakout"
    ]
    assert [item["name"] for item in matches.show()[0]["candles"]] == [
        "setup", "recovery", "breakout"
    ]


def test_dslx_struct_references_are_validated_before_evaluation():
    missing_member = """
        strategy invalid {
          candle setup { when => is_red }
          candle breakout { when => close > setup.high }
          candle exit_candle { when => is_red }
          entrystruct { breakout }
          exitstruct { exit_candle }
        }
    """
    with pytest.raises(DSLXSyntaxError, match="not a member of this structure"):
        parse_strategy(missing_member)

    forward_reference = missing_member.replace(
        "entrystruct { breakout }", "entrystruct { breakout setup }"
    )
    with pytest.raises(DSLXSyntaxError, match="cannot reference later candle 'setup'"):
        parse_strategy(forward_reference)


def test_dslx_structs_produce_historical_entry_and_exit_signals():
    frame = pd.DataFrame(
        {
            "Open": [10.0, 9.0, 11.0, 14.0],
            "High": [11.0, 12.0, 14.0, 14.0],
            "Low": [8.0, 8.5, 10.0, 11.0],
            "Close": [9.0, 11.0, 13.0, 12.0],
            "Volume": [1_000.0] * 4,
        }
    )
    signals = backtest_signals(
        """
        strategy pattern_trade {
          candle setup { when => is_red }
          candle recovery { when => is_green }
          candle breakout { when => is_green && close > recovery.high }
          candle exit_setup { when => is_green }
          candle breakdown { when => is_red && close < exit_setup.close }
          entrystruct { setup recovery breakout at breakout.close }
          exitstruct { exit_setup breakdown }
        }
        """,
        frame,
    )

    assert signals["entry_condition"].tolist() == [False, False, True, False]
    assert signals["exit_condition"].tolist() == [False, False, False, True]
    assert signals["signal"].tolist() == [0, 0, 1, -1]
    assert signals["entry_fill_price"].iloc[2] == pytest.approx(13.0)


def test_dslx_accepts_c_style_logical_operators():
    interpreter = DSLXInterpreter(
        """
        strategy c_style_operators {
          entry when candle => candle.is_green && !candle.is_doji || candle.is_red
          exit when candle => pass
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
          exit when candle => pass
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
          exit when candle => pass
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
          exit when candle => pass
        }
        """
    )

    assert interpreter.matches_entry(_candles()) is True


def test_dslx_indicator_candle_region_predicates_follow_visible_candle_parts():
    body = DSLXInterpreter(
        """
        strategy ema_in_body {
          entry when candle => candle.ema("close", 2).within_body
          exit when candle => pass
        }
        """
    )
    upper_wick = DSLXInterpreter(
        """
        strategy ema_in_upper_wick {
          entry when candle => candle.ema("close", 2).within_upper_wick
          exit when candle => pass
        }
        """
    )
    lower_wick = DSLXInterpreter(
        """
        strategy ema_in_lower_wick {
          entry when candle => candle.ema("close", 2).within_lower_wick
          exit when candle => pass
        }
        """
    )
    frame = pd.DataFrame(
        {
            "Open": [10.0, 10.0, 10.0],
            "High": [12.0, 12.0, 12.0],
            "Low": [8.0, 8.0, 8.0],
            "Close": [10.0, 11.0, 11.0],
            "Volume": [1_000.0] * 3,
        }
    )

    # EMA(2) ends inside the final 10-to-11 body.
    assert body.matches_entry(frame) is True
    assert upper_wick.matches_entry(frame) is False
    assert lower_wick.matches_entry(frame) is False

    upper_frame = frame.assign(Close=[10.0, 12.0, 12.0])
    # EMA(2) ends just above the final body, leaving it in the upper wick.
    upper_frame.loc[2, "Close"] = 11.0
    assert upper_wick.matches_entry(upper_frame) is True

    lower_frame = frame.assign(Close=[10.0, 8.0, 9.0])
    assert lower_wick.matches_entry(lower_frame) is True


def test_dslx_candle_within_ema_band_requires_the_full_candle_inside():
    interpreter = DSLXInterpreter(
        """
        strategy contained_by_ema_band {
          entry when candle => candle.within_ema_band(2)
          exit when candle => pass
        }
        """
    )
    contained = pd.DataFrame(
        {
            "Open": [10.0, 10.0, 10.0],
            "High": [12.0, 12.0, 11.0],
            "Low": [8.0, 8.0, 9.0],
            "Close": [10.0, 10.0, 10.0],
            "Volume": [1_000.0] * 3,
        }
    )

    assert interpreter.matches_entry(contained) is True
    assert interpreter.matches_entry(contained.assign(High=[12.0, 12.0, 13.0])) is False
    assert interpreter.matches_entry(contained.assign(Low=[8.0, 8.0, 7.0])) is False


def test_dslx_ema_band_contains_is_a_concise_alias_for_candle_containment():
    interpreter = DSLXInterpreter(
        """
        strategy contained_by_ema_band {
          entry when candle => candle.ema("high", "low", 2).contains
          exit when candle => pass
        }
        """
    )
    contained = pd.DataFrame(
        {
            "Open": [10.0, 10.0, 10.0],
            "High": [12.0, 12.0, 11.0],
            "Low": [8.0, 8.0, 9.0],
            "Close": [10.0, 10.0, 10.0],
            "Volume": [1_000.0] * 3,
        }
    )

    assert interpreter.matches_entry(contained) is True
    assert interpreter.matches_entry(contained.assign(High=[12.0, 12.0, 13.0])) is False


def test_dslx_parses_candle_centred_strategy_declarations():
    strategy = parse_strategy(
        """
        strategy ha_breakout {
          source universe.selected
          candles timeframe "1d" as heikin_ashi
          scan within 10 candles
          match when candle => candle.is_green && candle.rsi(14) > 50
          exit when candle => pass
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
        "strategy green { scan latest match when candle => candle.is_green exit when candle => pass }"
    )

    matches = interpreter.run(
        {"AAA": latest, "BBB": latest.assign(Open=latest["Close"] + 1)}
    )

    assert len(matches) == 1
    assert matches[0].strategy == "green"
    assert matches[0].ticker == "AAA"
    assert matches[0].age == 0
    assert (matches + MatchList()).show()[0]["strategy"] == "green"
    assert (matches + MatchList()).show()[0]["rsi"] == pytest.approx(100.0)


def test_dslx_program_parses_strategy_execution_and_display():
    program = parse_program(
        """
        strategy green { source universe.selected scan latest match when candle => candle.is_green exit when candle => pass }
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
        strategy green { source universe.selected scan latest match when candle => candle.is_green exit when candle => pass }
        let matches = green.run()
        matches.show()
        """
    )
    results = interpreter.run(selected={"AAA": _candles()})

    assert list(results) == ["matches"]
    assert results["matches"][0].ticker == "AAA"


def test_dslx_program_filters_a_named_universe_before_running_strategy():
    liquid = _candles().assign(Volume=100_000.0)
    thin = _candles().assign(Volume=[0.0] * 10 + [100.0] * 20)
    interpreter = DSLXProgramInterpreter(
        """
        universe xetra_liquid {
          from universe.xetra
          require liquidity {
            avg_turnover(20) >= 1_000_000
            median_turnover(20) >= 1_000_000
            active_sessions(20) >= 15
            active_sessions(5) >= 3
          }
        }
        strategy green {
          source universe.xetra_liquid
          scan latest
          match when candle => candle.is_green
          exit when candle => pass
        }
        let matches = green.run()
        matches.show()
        """
    )

    results = interpreter.run(
        selected={},
        universes={"universe.xetra": {"LIQ.DE": liquid, "THIN.DE": thin}},
    )

    assert [match.ticker for match in results["matches"]] == ["LIQ.DE"]
    definition = interpreter.program.universes[0]
    assert definition.name == "xetra_liquid"
    assert definition.source == "universe.xetra"
    assert definition.liquidity[0].metric == "avg_turnover"


def test_dslx_named_universe_rejects_invalid_liquidity_declarations():
    with pytest.raises(DSLXSyntaxError, match="requires 'from"):
        parse_program(
            "universe bad { require liquidity { avg_turnover(20) >= 1 } }"
        )
    with pytest.raises(DSLXSyntaxError, match="liquidity supports"):
        parse_program(
            "universe bad { from universe.xetra require liquidity { spread(20) >= 1 } }"
        )


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
        "strategy bad { entry when candle => __import__('os') exit when candle => pass }"
    )
    with pytest.raises(DSLXEvaluationError, match="Unknown name"):
        interpreter.matches_entry(_candles())
