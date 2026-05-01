from ETF_screener.scripts.movie_scanner import (
    get_strategy_warmup_days,
    resolve_strategy_signal_window,
)


def test_get_strategy_warmup_days_uses_indicator_periods_not_signal_age():
    strategies = [
        {
            "entry": "close > ema_20 and close > ema_200",
            "exit": "close < ema_50",
            "trigger": "cross_up(st_10_4_is_green, 0.5)",
            "filter": None,
            "max_days": 7,
        }
    ]

    assert get_strategy_warmup_days(strategies) == 200


def test_resolve_strategy_signal_window_prefers_dsl_max_days():
    strategy = {"max_days": 7}

    assert resolve_strategy_signal_window(strategy, configured_signal_days=50) == 7


def test_resolve_strategy_signal_window_uses_config_when_strategy_has_no_cap():
    strategy = {"max_days": None}

    assert resolve_strategy_signal_window(strategy, configured_signal_days=50) == 50

