import numpy as np
import pandas as pd
import pytest

from ETF_screener.dslx import (
    CandleSeries,
    DSLXEvaluationError,
    DSLXInterpreter,
    DSLXProgramInterpreter,
    DSLXSyntaxError,
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


def _strategy(name, entry, exit_condition="pass", *, declarations="", entry_price=""):
    exit_part = (
        "exitstruct { pass }"
        if exit_condition == "pass"
        else (
            f"candle exit_signal {{ when => {exit_condition} }} exitstruct {{ exit_signal }}"
        )
    )
    return f"""
      strategy {name} {{
        {declarations}
        candle entry_signal {{ when => {entry} }}
        entrystruct {{ entry_signal{entry_price} }}
        {exit_part}
      }}
    """


def test_dslx_uses_structural_candle_patterns_only():
    interpreter = DSLXInterpreter(
        _strategy(
            "trend",
            "close > ema(20) && rsi(14) > 50",
            "close < ema(20)",
            declarations="execution { entry: next_open, exit: close }",
        )
    )
    assert interpreter.strategy.entry_execution == "next_open"
    assert interpreter.strategy.exit_execution == "close"
    assert interpreter.matches_entry(_candles()) is True
    assert interpreter.matches_exit(_candles()) is False


def test_dslx_stoch_rsi_exposes_cached_k_d_lines_and_slopes():
    close = [100.0 + np.sin(index / 2.0) * 4.0 + index * 0.03 for index in range(100)]
    frame = pd.DataFrame(
        {
            "Open": [value - 0.2 for value in close],
            "High": [value + 0.7 for value in close],
            "Low": [value - 0.8 for value in close],
            "Close": close,
            "Volume": [10_000.0] * len(close),
        }
    )
    series = CandleSeries(frame)

    oscillator = series.last.stoch_rsi(14)
    explicit = series.last.stoch_rsi(14, 14, 3, 3)

    assert 0.0 <= oscillator.k <= 100.0
    assert 0.0 <= oscillator.d <= 100.0
    assert oscillator.k == pytest.approx(explicit.k)
    assert oscillator.d == pytest.approx(explicit.d)
    assert np.isfinite(oscillator.k.slope)
    assert np.isfinite(oscillator.d.slope)
    assert len(series._stoch_rsi_series_cache) == 1
    assert DSLXInterpreter(
        _strategy(
            "stoch_turn",
            "stoch_rsi(14).k >= 0 && stoch_rsi(14).d <= 100",
        )
    ).matches_entry(frame)


@pytest.mark.parametrize("arguments", [(), (14, 3), (0,), (14, 14, 3, 0)])
def test_dslx_stoch_rsi_rejects_invalid_period_arguments(arguments):
    with pytest.raises(DSLXEvaluationError, match="stoch_rsi"):
        CandleSeries(_candles()).last.stoch_rsi(*arguments)


@pytest.mark.parametrize("keyword", ["entry", "exit", "match"])
def test_dslx_rejects_legacy_strategy_lambda_rules(keyword):
    with pytest.raises(DSLXSyntaxError, match="no longer supported"):
        parse_strategy(f"strategy old {{ {keyword} when candle => candle.is_green }}")


def test_dslx_requires_both_structs_and_supports_a_no_op_exit():
    with pytest.raises(DSLXSyntaxError, match="needs an entrystruct"):
        parse_strategy(
            "strategy bad { candle green { when => is_green } exitstruct { pass } }"
        )
    with pytest.raises(DSLXSyntaxError, match="needs an exitstruct"):
        parse_strategy(
            "strategy bad { candle green { when => is_green } entrystruct { green } }"
        )
    assert (
        DSLXInterpreter(_strategy("hold", "is_green")).matches_exit(_candles()) is False
    )


def test_dslx_backtests_structured_patterns_and_no_op_exit():
    signals = backtest_signals(
        _strategy("green", "is_green") + "let matches = green.run() matches.show()",
        _candles(),
    )
    assert bool(signals["entry_condition"].iloc[-1]) is True
    assert signals["exit_condition"].sum() == 0
    assert signals["signal"].sum() == 1


def test_dslx_structured_exit_can_reference_open_position_and_set_fill_price():
    frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 104.0, 106.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.0, 102.0, 104.0],
            "Volume": [1_000.0] * 3,
        }
    )
    signals = backtest_signals(
        _strategy(
            "target",
            "close == 100",
            "high >= position.entry_price * 1.03",
            entry_price=" at entry_signal.close",
        ),
        frame,
    )
    assert signals["signal"].tolist() == [1, -1, 0]
    assert signals["entry_fill_price"].iloc[0] == pytest.approx(100.0)
    assert signals["exit_fill_price"].iloc[1] == pytest.approx(103.0)


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
      strategy breakout {
        candle setup { when => is_red }
        candle recovery { when => is_green && low > setup.low }
        candle breakout { when => is_green && close > recovery.high }
        candle breakdown { when => is_red }
        entrystruct { setup recovery breakout at breakout.close }
        exitstruct { breakdown }
      }
    """
    interpreter = DSLXInterpreter(source)
    assert interpreter.matches_entry(candles) is True
    assert interpreter.matches_entry(candles.iloc[:2]) is False
    matches = interpreter.run({"PATTERN": candles})
    assert [name for name, _ in matches[0].pattern] == ["setup", "recovery", "breakout"]
    assert [row["name"] for row in matches.show()[0]["candles"]] == [
        "setup",
        "recovery",
        "breakout",
    ]


def test_dslx_any_struct_member_consumes_one_unconstrained_candle():
    candles = pd.DataFrame(
        {
            "Open": [10.0, 12.0, 11.0, 14.0],
            "High": [11.0, 13.0, 14.0, 15.0],
            "Low": [8.0, 9.0, 10.0, 13.0],
            "Close": [9.0, 10.0, 13.0, 14.0],
            "Volume": [1_000.0] * 4,
        }
    )
    source = """
      strategy wildcard_breakout {
        candle setup { when => is_red }
        candle breakout { when => is_green && close > setup.high }
        entrystruct { setup any breakout at breakout.close }
        exitstruct { any }
      }
    """

    interpreter = DSLXInterpreter(source)
    assert interpreter.matches_entry(candles.iloc[:2]) is False
    assert interpreter.matches_entry(candles.iloc[:3]) is True
    match = interpreter.run({"WILDCARD": candles.iloc[:3]})[0]
    assert [name for name, _ in match.pattern] == ["setup", "any", "breakout"]

    signals = backtest_signals(source, candles)
    assert signals["entry_condition"].tolist() == [False, False, True, False]
    assert signals["exit_condition"].tolist() == [False, False, False, True]
    assert signals["signal"].tolist() == [0, 0, 1, -1]


def test_dslx_program_checks_for_cancellation_between_tickers():
    source = """
      strategy cancellable {
        candle green { when => is_green }
        entrystruct { green }
        exitstruct { pass }
      }
      let matches = cancellable.run()
      matches.show()
    """
    checks = 0

    def cancel_check():
        nonlocal checks
        checks += 1
        if checks >= 2:
            raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        DSLXProgramInterpreter(source).run(
            selected={"AAA": _candles(), "BBB": _candles()},
            cancel_check=cancel_check,
        )


def test_dslx_program_publishes_matches_and_ticker_progress_incrementally():
    source = """
      strategy streaming {
        candle green { when => is_green }
        entrystruct { green }
        exitstruct { pass }
      }
      let matches = streaming.run()
      matches.show()
    """
    frame = _candles().assign(Open=lambda value: value["Close"] - 1.0)
    streamed_matches = []
    progress = []

    result = DSLXProgramInterpreter(source).run(
        selected={"AAA": frame, "BBB": frame},
        match_callback=lambda match: streamed_matches.append(match.ticker),
        progress_callback=lambda ticker, completed, total: progress.append(
            (ticker, completed, total)
        ),
    )

    assert streamed_matches == ["AAA", "BBB"]
    assert progress == [("AAA", 1, 2), ("BBB", 2, 2)]
    assert [match.ticker for match in result["matches"]] == ["AAA", "BBB"]


def test_dslx_any_struct_member_can_repeat_but_cannot_be_named_or_referenced():
    repeated = parse_strategy("""
      strategy repeated_any {
        candle setup { when => is_red }
        candle breakout { when => is_green }
        entrystruct { setup any any breakout }
        exitstruct { pass }
      }
    """)
    assert repeated.entry_struct == ("setup", "any", "any", "breakout")

    with pytest.raises(DSLXSyntaxError, match="reserved for unconstrained"):
        parse_strategy("""
          strategy named_any {
            candle any { when => is_green }
            entrystruct { any }
            exitstruct { pass }
          }
        """)
    with pytest.raises(DSLXSyntaxError, match="unavailable candle 'any'"):
        parse_strategy("""
          strategy priced_any {
            candle setup { when => is_red }
            entrystruct { setup any at any.close }
            exitstruct { pass }
          }
        """)


def test_dslx_struct_references_are_validated_before_evaluation():
    source = """
      strategy invalid {
        candle setup { when => is_red }
        candle breakout { when => close > setup.high }
        candle exit_candle { when => is_red }
        entrystruct { breakout }
        exitstruct { exit_candle }
      }
    """
    with pytest.raises(DSLXSyntaxError, match="not a member of this structure"):
        parse_strategy(source)
    with pytest.raises(DSLXSyntaxError, match="cannot reference later candle 'setup'"):
        parse_strategy(
            source.replace("entrystruct { breakout }", "entrystruct { breakout setup }")
        )


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


def test_dslx_named_candles_support_windows_indicators_and_geometry():
    interpreter = DSLXInterpreter(
        _strategy(
            "green_sequence",
            'window(3).all(c => c.close > c.open) && !is_doji && ema("high", 20).slope > 0',
        )
    )
    assert interpreter.matches_entry(_candles()) is True
    assert interpreter.matches_entry(_candles().iloc[:2]) is False
    frame = pd.DataFrame(
        {
            "Open": [10.0, 10.0, 10.0],
            "High": [12.0, 12.0, 11.0],
            "Low": [8.0, 8.0, 9.0],
            "Close": [10.0, 11.0, 11.0],
            "Volume": [1_000.0] * 3,
        }
    )
    assert DSLXInterpreter(
        _strategy("body", 'ema("close", 2).body_intersects')
    ).matches_entry(frame)
    assert not DSLXInterpreter(
        _strategy("outside_body", '!ema("close", 2).body_intersects')
    ).matches_entry(frame)
    assert DSLXInterpreter(
        _strategy("outside_body", '!ema("high", 2).body_intersects')
    ).matches_entry(frame)
    assert DSLXInterpreter(
        _strategy("upper_wick", 'ema("high", 2).upper_wick_intersects')
    ).matches_entry(frame.assign(High=[12.0] * 3))
    assert DSLXInterpreter(
        _strategy("lower_wick", 'ema("low", 2).lower_wick_intersects')
    ).matches_entry(frame.assign(Low=[8.0] * 3))
    contained = frame.assign(Open=[10.0] * 3, Close=[10.0] * 3)
    assert DSLXInterpreter(
        _strategy("body_band", 'ema("high", 2, "low", 2).body_within')
    ).matches_entry(contained)
    assert DSLXInterpreter(
        _strategy("candle_band", 'ema("high", 2, "low", 2).candle_within')
    ).matches_entry(contained)
    candle = CandleSeries(frame.assign(Open=[12.0] * 3, Close=[10.0] * 3)).last
    assert candle.color == "red" and candle.body_length == 2.0


def test_dslx_ema_band_distinguishes_body_from_full_candle_and_supports_periods():
    frame = pd.DataFrame(
        {
            "Open": [9.0, 10.0, 10.0],
            "High": [12.0, 12.0, 13.0],
            "Low": [8.0, 8.0, 7.0],
            "Close": [11.0, 10.0, 10.0],
            "Volume": [1_000.0] * 3,
        }
    )

    assert DSLXInterpreter(
        _strategy("body_only", 'ema("high", 2, "low", 3).body_within')
    ).matches_entry(frame)
    assert not DSLXInterpreter(
        _strategy("with_wicks", 'ema("high", 2, "low", 3).candle_within')
    ).matches_entry(frame)


def test_dslx_candle_wick_presence_properties_cover_visual_categories():
    def candle(*, high: float, low: float):
        frame = pd.DataFrame(
            {
                "Open": [10.0],
                "High": [high],
                "Low": [low],
                "Close": [11.0],
                "Volume": [1_000.0],
            }
        )
        return CandleSeries(frame).last

    both = candle(high=12.0, low=9.0)
    only_upper = candle(high=12.0, low=10.0)
    only_lower = candle(high=11.0, low=9.0)
    wickless = candle(high=11.0, low=10.0)
    floating_dust = candle(high=11.0 + 1e-13, low=10.0)

    assert both.has_both_wicks
    assert both.has_upper_wick and both.has_lower_wick
    assert only_upper.has_only_upper_wick
    assert only_lower.has_only_lower_wick
    assert wickless.is_wickless
    assert floating_dust.is_wickless

    frame = pd.DataFrame(
        {
            "Open": [10.0] * 3,
            "High": [12.0] * 3,
            "Low": [9.0] * 3,
            "Close": [11.0] * 3,
            "Volume": [1_000.0] * 3,
        }
    )
    assert DSLXInterpreter(_strategy("both_wicks", "has_both_wicks")).matches_entry(
        frame
    )


def test_dslx_indicator_body_and_candle_over_under_are_strict():
    above = pd.DataFrame(
        {
            "Open": [10.0] * 3,
            "High": [12.0] * 3,
            "Low": [8.0] * 3,
            "Close": [11.0] * 3,
            "Volume": [1_000.0] * 3,
        }
    )
    below = pd.DataFrame(
        {
            "Open": [9.0] * 3,
            "High": [12.0] * 3,
            "Low": [8.0] * 3,
            "Close": [8.0] * 3,
            "Volume": [1_000.0] * 3,
        }
    )

    assert DSLXInterpreter(
        _strategy("body_over", 'ema("low", 2).body_over')
    ).matches_entry(above)
    assert not DSLXInterpreter(
        _strategy("candle_over", 'ema("low", 2).candle_over')
    ).matches_entry(above)
    assert DSLXInterpreter(
        _strategy("body_under", 'ema("high", 2).body_under')
    ).matches_entry(below)
    assert not DSLXInterpreter(
        _strategy("candle_under", 'ema("high", 2).candle_under')
    ).matches_entry(below)

    full_above = above.assign(Low=[8.0, 8.0, 9.0])
    full_below = below.assign(High=[12.0, 12.0, 11.0])
    assert DSLXInterpreter(
        _strategy("candle_over", 'ema("low", 2).candle_over')
    ).matches_entry(full_above)
    assert DSLXInterpreter(
        _strategy("candle_under", 'ema("high", 2).candle_under')
    ).matches_entry(full_below)

    touching_above = full_above.assign(Low=[9.0] * 3)
    touching_below = full_below.assign(High=[11.0] * 3)
    assert not DSLXInterpreter(
        _strategy("touching_over", 'ema("low", 2).candle_over')
    ).matches_entry(touching_above)
    assert not DSLXInterpreter(
        _strategy("touching_under", 'ema("high", 2).candle_under')
    ).matches_entry(touching_below)


def test_dslx_ema_band_boundaries_are_inclusive_and_argument_order_independent():
    frame = pd.DataFrame(
        {
            "Open": [8.0, 8.0, 8.0],
            "High": [12.0, 12.0, 12.0],
            "Low": [8.0, 8.0, 8.0],
            "Close": [12.0, 12.0, 12.0],
            "Volume": [1_000.0] * 3,
        }
    )

    assert DSLXInterpreter(
        _strategy("inclusive", 'ema("low", 2, "high", 2).candle_within')
    ).matches_entry(frame)


def test_dslx_ema_band_does_not_expose_legacy_contains():
    with pytest.raises(
        DSLXEvaluationError, match="'contains' is not available on EMABand"
    ):
        DSLXInterpreter(
            _strategy("legacy_contains", 'ema("high", 2, "low", 2).contains')
        ).matches_entry(_candles())


@pytest.mark.parametrize(
    "legacy_name",
    ["within_body", "not_within_body", "within_upper_wick", "within_lower_wick"],
)
def test_dslx_indicator_does_not_expose_reversed_region_names(legacy_name):
    with pytest.raises(DSLXEvaluationError, match=f"'{legacy_name}' is not available"):
        DSLXInterpreter(
            _strategy("legacy_region", f'ema("close", 2).{legacy_name}')
        ).matches_entry(_candles())


def test_dslx_normalized_atr_filter_rejects_flatlining_prices():
    flat = pd.DataFrame(
        {
            "Open": [100.0] * 30,
            "High": [100.1] * 30,
            "Low": [99.9] * 30,
            "Close": [100.0] * 30,
            "Volume": [10_000.0] * 30,
        }
    )
    moving = flat.assign(High=[102.0] * 30, Low=[98.0] * 30)
    strategy = DSLXInterpreter(_strategy("volatile", "atr(14) / close >= 0.01"))

    assert strategy.matches_entry(flat) is False
    assert strategy.matches_entry(moving) is True


def test_dslx_caches_source_and_indicator_series_per_ticker():
    series = CandleSeries(_candles())

    series.last.ema("close", 20)
    cached_ema = series._indicator_series_cache[("ema", "close", 20)]
    series.candle_at(20).ema("close", 20)
    series.last.rsi(14)

    assert series._indicator_series_cache[("ema", "close", 20)] is cached_ema
    assert set(series._indicator_series_cache) == {
        ("ema", "close", 20),
        ("rsi", "close", 14),
    }
    assert set(series._source_series_cache) == {"close"}


def test_dslx_evaluates_cheap_conjunction_terms_before_indicators(monkeypatch):
    def unexpected_atr(*_args, **_kwargs):
        raise AssertionError("ATR should not run after a cheap rejection")

    monkeypatch.setattr("ETF_screener.dslx.Candle.atr", unexpected_atr)
    strategy = DSLXInterpreter(_strategy("cheap_first", "atr(14) > 0 && close < 0"))

    assert strategy.matches_entry(_candles()) is False


def test_dslx_uses_short_indicator_lookbacks_to_reject_before_long_ones(monkeypatch):
    def unexpected_ema(*_args, **_kwargs):
        raise AssertionError("EMA(200) should not run after ATR(14) rejects")

    monkeypatch.setattr("ETF_screener.dslx.Candle.ema", unexpected_ema)
    frame = pd.concat([_candles()] * 8, ignore_index=True)
    strategy = DSLXInterpreter(
        _strategy("short_first", 'ema("close", 200) > 0 && atr(14) > 1_000')
    )

    assert strategy.matches_entry(frame) is False


def test_dslx_program_retains_composable_match_lists_and_named_universes():
    liquid = _candles().assign(Volume=100_000.0)
    thin = _candles().assign(Volume=[0.0] * 10 + [100.0] * 20)
    source = """
      universe xetra_liquid {
        from universe.xetra
        require liquidity { avg_turnover(20) >= 1_000_000 median_turnover(20) >= 1_000_000 active_sessions(20) >= 15 }
      }
      strategy green {
        source universe.xetra_liquid
        candles timeframe "1d" as heikin_ashi
        scan within 10 candles
        candle green { when => is_green && rsi(14) > 50 }
        entrystruct { green }
        exitstruct { pass }
      }
      let matches = green.run()
      let combined = matches + matches
      combined.show()
    """
    program = parse_program(source)
    assert program.strategies[0].timeframe == "1d"
    assert program.merges == (("combined", "matches", "matches"),)
    results = DSLXProgramInterpreter(
        source.replace("combined.show()", "matches.show()")
    ).run(
        selected={},
        universes={"universe.xetra": {"LIQ.DE": liquid, "THIN.DE": thin}},
    )
    assert len(results["matches"]) == 10
    assert {match.ticker for match in results["matches"]} == {"LIQ.DE"}


def test_dslx_rejects_invalid_liquidity_and_unsafe_expression_names():
    with pytest.raises(DSLXSyntaxError, match="requires 'from"):
        parse_program("universe bad { require liquidity { avg_turnover(20) >= 1 } }")
    with pytest.raises(DSLXSyntaxError, match="liquidity supports"):
        parse_program(
            "universe bad { from universe.xetra require liquidity { spread(20) >= 1 } }"
        )
    with pytest.raises(DSLXSyntaxError, match="references unknown name"):
        DSLXInterpreter(_strategy("bad", "__import__('os')"))


@pytest.mark.parametrize("name", ["ema", "sma", "rsi", "atr", "volume_ema"])
def test_normalized_slope_matches_indicator_history_and_scale(name):
    frame = _candles()
    candle = CandleSeries(frame).last
    indicator = getattr(candle, name)(5)
    previous = getattr(candle.previous(3), name)(5)
    expected = 100 * (indicator / previous - 1) / 3
    assert candle.slope(indicator, 3) == pytest.approx(expected)
    scaled = frame.copy()
    scaled[["Open", "High", "Low", "Close", "Volume"]] *= 100
    scaled_candle = CandleSeries(scaled).last
    assert scaled_candle.slope(getattr(scaled_candle, name)(5), 3) == pytest.approx(
        expected
    )
    assert indicator.slope == pytest.approx(
        indicator - getattr(candle.previous(), name)(5)
    )


def test_normalized_slope_dsl_and_no_lookahead():
    source = _strategy("normalized", "slope(ema(5), 3) > 0.05")
    frame = _candles()
    interpreter = DSLXInterpreter(source)
    assert interpreter.matches_entry(frame)
    assert interpreter.matches_entry(frame, endpoint=12) == interpreter.matches_entry(
        frame.iloc[:13]
    )
    changed_future = frame.copy()
    changed_future.loc[13:, ["Open", "High", "Low", "Close"]] *= 10000
    assert interpreter.matches_entry(
        changed_future, endpoint=12
    ) == interpreter.matches_entry(frame, endpoint=12)
    assert not interpreter.matches_entry(frame.iloc[:7])  # p + w candles required
    explicit = DSLXInterpreter(
        _strategy("explicit", "entry_signal.slope(entry_signal.ema(5), 3) > 0")
    )
    assert explicit.matches_entry(frame)


@pytest.mark.parametrize("window", [0, -1, 1.5, True])
def test_normalized_slope_rejects_invalid_window(window):
    candle = CandleSeries(_candles()).last
    with pytest.raises(DSLXEvaluationError, match="positive integer"):
        candle.slope(candle.ema(5), window)


def test_normalized_slope_undefined_is_no_match_and_scalar_required():
    frame = _candles()
    frame.loc[:, "Volume"] = 0
    assert not DSLXInterpreter(
        _strategy("zero", "slope(volume_ema(5), 3) >= 0")
    ).matches_entry(frame)
    candle = CandleSeries(frame).last
    with pytest.raises(DSLXEvaluationError, match="scalar indicator"):
        candle.slope(100, 3)
    with pytest.raises(DSLXEvaluationError, match="scalar indicator"):
        candle.slope(candle.ema(5) + 1, 3)


def test_normalized_slope_plan_example_and_negative_direction():
    from ETF_screener.slope import normalized_slope

    assert normalized_slope(102, 100, 20) == pytest.approx(0.10)
    assert normalized_slope(98, 100, 20) == pytest.approx(-0.10)
    assert normalized_slope(100, 100, 20) == 0
    assert np.isnan(normalized_slope(100, 0, 20))
    assert np.isnan(normalized_slope(float("inf"), 100, 20))


def test_normalized_stoch_rsi_slope_uses_line_history():
    frame = _candles()
    frame["Close"] = [100 + np.sin(i) * 5 for i in range(len(frame))]
    candle = CandleSeries(frame).last
    current = candle.stoch_rsi(3).k
    previous = candle.previous(2).stoch_rsi(3).k
    assert candle.slope(current, 2) == pytest.approx(100 * (current / previous - 1) / 2)


@pytest.mark.parametrize(
    "expression",
    [
        "ema(5) / ema(10)",
        'ema("high", 5) - ema("low", 10)',
        "window(3).close.average()",
        "previous(2).ema(5)",
        "close",
        "ema(5) + 1",
    ],
)
def test_generalized_slope_recomputes_expression_at_historical_candle(expression):
    from ETF_screener.dslx import _evaluate, _implicit_candle_environment

    frame = _candles()
    parsed = parse_strategy(_strategy("numeric", f"{expression} > 0"))
    numeric = parsed.candle_definitions[0].condition.left
    series = CandleSeries(frame)
    current = _evaluate(numeric, _implicit_candle_environment(series.last))
    previous = _evaluate(numeric, _implicit_candle_environment(series.last.previous(3)))
    expected = 100 * (current / previous - 1) / 3
    source = _strategy(
        "general",
        f"slope({expression}, 3) > {expected - 0.000001} && slope({expression}, 3) < {expected + 0.000001}",
    )
    assert DSLXInterpreter(source).matches_entry(frame)
    assert DSLXInterpreter(source).matches_entry(
        pd.concat([frame, frame * 1000], ignore_index=True), endpoint=29
    )


def test_generalized_slope_rejects_non_numeric_expression():
    for expression in ["is_green", 'ema("high", 5, "low", 5)']:
        with pytest.raises(DSLXEvaluationError, match="numeric expression"):
            DSLXInterpreter(
                _strategy("invalid", f"slope({expression}, 3) > 0")
            ).matches_entry(_candles())


@pytest.mark.parametrize("average", ["ema", "sma"])
@pytest.mark.parametrize("source", ["open", "high", "low", "close"])
def test_moving_average_dot_source_matches_string_source(average, source):
    frame = _candles()
    candle = CandleSeries(frame).last
    dotted = getattr(getattr(candle, average)(5), source)
    explicit = getattr(candle, average)(source, 5)
    assert dotted == pytest.approx(explicit)
    assert dotted.slope == pytest.approx(explicit.slope)
    assert dotted.body_intersects == explicit.body_intersects
    expression = (
        f'slope({average}(5).{source}, 3) == slope({average}("{source}", 5), 3)'
    )
    assert DSLXInterpreter(_strategy("sources", expression)).matches_entry(frame)
    interpreter = DSLXInterpreter(_strategy("sources", expression))
    assert interpreter.matches_entry(frame, endpoint=12) == interpreter.matches_entry(
        frame.iloc[:13]
    )


def test_non_moving_average_rejects_price_source_selector():
    with pytest.raises(DSLXEvaluationError, match="EMA or SMA"):
        DSLXInterpreter(_strategy("invalid", "rsi(5).close > 0")).matches_entry(
            _candles()
        )
