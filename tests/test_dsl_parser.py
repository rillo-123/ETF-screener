from ETF_screener.dsl_parser import parse_strategy_blocks, parse_strategy_scripts


def test_parse_strategy_scripts_combines_entry_and_exit_sections():
    content = """
    # Comment
    BEGIN CONTEXT
    FILTER: close > ema_200
    END

    BEGIN TRIGGER
    TRIGGER: cross_up(macd, macd_signal)
    END

    EXIT: close < ema_50
    EXIT: cross_down(macd, macd_signal)
    """

    entry_script, exit_script = parse_strategy_scripts(content)

    assert entry_script == "(close > ema_200) and (cross_up(macd, macd_signal))"
    assert exit_script == "(close < ema_50) or (cross_down(macd, macd_signal))"


def test_parse_strategy_scripts_defaults_missing_exit_to_false():
    content = """
    BEGIN TRIGGER
    TRIGGER: volume > 100K
    END
    """

    entry_script, exit_script = parse_strategy_scripts(content)

    assert entry_script == "(volume > 100K)"
    assert exit_script == "False"


def test_supertrend_red_to_green_ema50_crossup_strategy_parses_as_expected():
    from pathlib import Path

    strategy_path = Path("strategies/supertrend_red_to_green_ema50_crossup.dsl")
    content = strategy_path.read_text(encoding="utf-8")

    entry_script, exit_script = parse_strategy_scripts(content)

    assert "ema_200_slope > 0" in entry_script
    assert "st_10_4 < ema_50" in entry_script
    assert "st_10_4_d4 < ema_50_d4" in entry_script
    assert "cross_up(st_10_4, ema_50)" in entry_script
    assert "cross_down(st_10_4, ema_50)" in exit_script
    assert "ema_200_slope <= 0" in exit_script


def test_supertrend_st_crossdown_ema50_slope_turnup_strategy_parses_as_expected():
    from pathlib import Path

    strategy_path = Path("strategies/supertrend_st_crossdown_ema50_slope_turnup.dsl")
    content = strategy_path.read_text(encoding="utf-8")

    entry_script, exit_script = parse_strategy_scripts(content)

    assert "ema_200_slope > 0" in entry_script
    assert "st_10_4 < ema_50" in entry_script
    assert "st_10_4_d6 >= ema_50_d6" in entry_script
    assert "ema_50_slope_cross_up" in entry_script
    assert "cross_up(st_10_4, ema_50)" in exit_script
    assert "ema_200_slope <= 0" in exit_script


def test_parse_strategy_blocks_preserves_block_order_and_fallback_sections():
    content = """
    FILTER: close > ema_200

    BEGIN TRIGGER_EVENT
    TRIGGER: macd > macd_signal
    END

    EXIT: close < ema_50
    """

    blocks = parse_strategy_blocks(content)

    assert [block.name for block in blocks] == [
        "Setup",
        "TRIGGER_EVENT",
        "Exit",
    ]
    assert [block.layer for block in blocks] == [2, 3, 4]
    assert blocks[0].expressions == ("(close > ema_200)",)
    assert blocks[1].expressions == ("(macd > macd_signal)",)
    assert blocks[2].expressions == ("(close < ema_50)",)
