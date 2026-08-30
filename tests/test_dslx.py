import pandas as pd
import pytest

from ETF_screener.dslx import (
    CandleSeries, DSLXInterpreter, DSLXProgramInterpreter,
    DSLXSyntaxError, backtest_signals, parse_program, parse_strategy,
)


def _candles() -> pd.DataFrame:
    close = [10.0 + index for index in range(30)]
    return pd.DataFrame({
        "Open": [value - 0.5 for value in close],
        "High": [value + 0.8 for value in close],
        "Low": [value - 0.9 for value in close],
        "Close": close, "Volume": [1000.0] * 30,
    })


def _strategy(name, entry, exit_condition="pass", *, declarations="", entry_price=""):
    exit_part = "exitstruct { pass }" if exit_condition == "pass" else (
        f"candle exit_signal {{ when => {exit_condition} }} exitstruct {{ exit_signal }}"
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
    interpreter = DSLXInterpreter(_strategy(
        "trend", "close > ema(20) && rsi(14) > 50", "close < ema(20)",
        declarations="execution { entry: next_open, exit: close }",
    ))
    assert interpreter.strategy.entry_execution == "next_open"
    assert interpreter.strategy.exit_execution == "close"
    assert interpreter.matches_entry(_candles()) is True
    assert interpreter.matches_exit(_candles()) is False


@pytest.mark.parametrize("keyword", ["entry", "exit", "match"])
def test_dslx_rejects_legacy_strategy_lambda_rules(keyword):
    with pytest.raises(DSLXSyntaxError, match="no longer supported"):
        parse_strategy(f"strategy old {{ {keyword} when candle => candle.is_green }}")


def test_dslx_requires_both_structs_and_supports_a_no_op_exit():
    with pytest.raises(DSLXSyntaxError, match="needs an entrystruct"):
        parse_strategy("strategy bad { candle green { when => is_green } exitstruct { pass } }")
    with pytest.raises(DSLXSyntaxError, match="needs an exitstruct"):
        parse_strategy("strategy bad { candle green { when => is_green } entrystruct { green } }")
    assert DSLXInterpreter(_strategy("hold", "is_green")).matches_exit(_candles()) is False


def test_dslx_backtests_structured_patterns_and_no_op_exit():
    signals = backtest_signals(_strategy("green", "is_green") + "let matches = green.run() matches.show()", _candles())
    assert bool(signals["entry_condition"].iloc[-1]) is True
    assert signals["exit_condition"].sum() == 0
    assert signals["signal"].sum() == 1


def test_dslx_structured_exit_can_reference_open_position_and_set_fill_price():
    frame = pd.DataFrame({
        "Open": [100.0, 101.0, 102.0], "High": [101.0, 104.0, 106.0],
        "Low": [99.0, 100.0, 101.0], "Close": [100.0, 102.0, 104.0],
        "Volume": [1_000.0] * 3,
    })
    signals = backtest_signals(_strategy(
        "target", "close == 100", "high >= position.entry_price * 1.03",
        entry_price=" at entry_signal.close",
    ), frame)
    assert signals["signal"].tolist() == [1, -1, 0]
    assert signals["entry_fill_price"].iloc[0] == pytest.approx(100.0)
    assert signals["exit_fill_price"].iloc[1] == pytest.approx(103.0)


def test_dslx_named_candle_structs_define_consecutive_pattern_order():
    candles = pd.DataFrame({
        "Open": [10.0, 9.0, 11.0], "High": [11.0, 12.0, 14.0],
        "Low": [8.0, 8.5, 10.0], "Close": [9.0, 11.0, 13.0],
        "Volume": [1_000.0, 2_000.0, 3_000.0],
    })
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
    assert [row["name"] for row in matches.show()[0]["candles"]] == ["setup", "recovery", "breakout"]


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
        parse_strategy(source.replace("entrystruct { breakout }", "entrystruct { breakout setup }"))


def test_dslx_structs_produce_historical_entry_and_exit_signals():
    frame = pd.DataFrame({
        "Open": [10.0, 9.0, 11.0, 14.0], "High": [11.0, 12.0, 14.0, 14.0],
        "Low": [8.0, 8.5, 10.0, 11.0], "Close": [9.0, 11.0, 13.0, 12.0],
        "Volume": [1_000.0] * 4,
    })
    signals = backtest_signals("""
      strategy pattern_trade {
        candle setup { when => is_red }
        candle recovery { when => is_green }
        candle breakout { when => is_green && close > recovery.high }
        candle exit_setup { when => is_green }
        candle breakdown { when => is_red && close < exit_setup.close }
        entrystruct { setup recovery breakout at breakout.close }
        exitstruct { exit_setup breakdown }
      }
    """, frame)
    assert signals["entry_condition"].tolist() == [False, False, True, False]
    assert signals["exit_condition"].tolist() == [False, False, False, True]
    assert signals["signal"].tolist() == [0, 0, 1, -1]


def test_dslx_named_candles_support_windows_indicators_and_geometry():
    interpreter = DSLXInterpreter(_strategy(
        "green_sequence",
        'window(3).all(c => c.close > c.open) && !is_doji && ema("high", 20).slope > 0',
    ))
    assert interpreter.matches_entry(_candles()) is True
    assert interpreter.matches_entry(_candles().iloc[:2]) is False
    frame = pd.DataFrame({
        "Open": [10.0, 10.0, 10.0], "High": [12.0, 12.0, 11.0],
        "Low": [8.0, 8.0, 9.0], "Close": [10.0, 11.0, 11.0], "Volume": [1_000.0] * 3,
    })
    assert DSLXInterpreter(_strategy("body", 'ema("close", 2).within_body')).matches_entry(frame)
    assert not DSLXInterpreter(
        _strategy("outside_body", 'ema("close", 2).not_within_body')
    ).matches_entry(frame)
    assert DSLXInterpreter(
        _strategy("outside_body", 'ema("high", 2).not_within_body')
    ).matches_entry(frame)
    assert DSLXInterpreter(_strategy("band", 'ema("high", "low", 2).contains')).matches_entry(frame.assign(Close=[10.0] * 3))
    candle = CandleSeries(frame.assign(Open=[12.0] * 3, Close=[10.0] * 3)).last
    assert candle.color == "red" and candle.body_length == 2.0


def test_dslx_normalized_atr_filter_rejects_flatlining_prices():
    flat = pd.DataFrame({
        "Open": [100.0] * 30,
        "High": [100.1] * 30,
        "Low": [99.9] * 30,
        "Close": [100.0] * 30,
        "Volume": [10_000.0] * 30,
    })
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
    results = DSLXProgramInterpreter(source.replace("combined.show()", "matches.show()")).run(
        selected={}, universes={"universe.xetra": {"LIQ.DE": liquid, "THIN.DE": thin}},
    )
    assert len(results["matches"]) == 10
    assert {match.ticker for match in results["matches"]} == {"LIQ.DE"}


def test_dslx_rejects_invalid_liquidity_and_unsafe_expression_names():
    with pytest.raises(DSLXSyntaxError, match="requires 'from"):
        parse_program("universe bad { require liquidity { avg_turnover(20) >= 1 } }")
    with pytest.raises(DSLXSyntaxError, match="liquidity supports"):
        parse_program("universe bad { from universe.xetra require liquidity { spread(20) >= 1 } }")
    with pytest.raises(DSLXSyntaxError, match="references unknown name"):
        DSLXInterpreter(_strategy("bad", "__import__('os')"))
