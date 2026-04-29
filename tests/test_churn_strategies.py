import pandas as pd

from ETF_screener.scripts.churn_strategies import (
    find_recent_entry_days,
    parse_dsl_content,
)


def test_parse_dsl_content_extracts_max_days_and_blocks():
    content = """
MAX_DAYS: 7
BEGIN CONTEXT
FILTER: close > ema_200
END
BEGIN QUALIFY
FILTER: rsi_14 > 50
END
BEGIN TRIGGER
FILTER: close > ema_20 and close_d1 <= ema_20_d1
END
BEGIN INVALIDATE
FILTER: close < ema_50
END
"""

    parsed = parse_dsl_content(content)

    assert parsed["max_days"] == 7
    assert parsed["trigger"] == "(close > ema_20 and close_d1 <= ema_20_d1)"
    assert "(close > ema_200)" in parsed["filter"]
    assert "(rsi_14 > 50)" in parsed["filter"]
    assert parsed["exit"] == "(close < ema_50)"


def test_find_recent_entry_days_returns_surviving_age():
    df = pd.DataFrame(
        {
            "close": [9.0, 10.0, 11.0, 12.0, 13.0],
            "close_d1": [8.0, 9.0, 10.0, 11.0, 12.0],
            "ema_20": [10.0, 10.0, 10.0, 10.0, 10.0],
            "ema_20_d1": [10.0, 10.0, 10.0, 10.0, 10.0],
            "exit_condition": [False, False, False, False, False],
        }
    )
    strategy_spec = {
        "trigger": "(close > ema_20 and close_d1 <= ema_20_d1)",
        "filter": "(close > ema_20)",
        "exit": "(close < ema_20)",
    }

    assert find_recent_entry_days(df, strategy_spec, max_days=4) == 2
    assert find_recent_entry_days(df, strategy_spec, max_days=1) is None


def test_find_recent_entry_days_rejects_post_trigger_exit():
    df = pd.DataFrame(
        {
            "close": [9.0, 10.0, 11.0, 12.0, 13.0],
            "close_d1": [8.0, 9.0, 10.0, 11.0, 12.0],
            "ema_20": [10.0, 10.0, 10.0, 10.0, 10.0],
            "ema_20_d1": [10.0, 10.0, 10.0, 10.0, 10.0],
            "exit_condition": [False, False, False, True, False],
        }
    )
    strategy_spec = {
        "trigger": "(close > ema_20 and close_d1 <= ema_20_d1)",
        "filter": "(close > ema_20)",
        "exit": "(close < ema_20)",
    }

    assert find_recent_entry_days(df, strategy_spec, max_days=4) is None
