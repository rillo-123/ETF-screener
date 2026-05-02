import pandas as pd

from ETF_screener.scripts.churn_strategies import (
    evaluate_strategies,
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


def test_evaluate_strategies_reuses_cached_result(monkeypatch, tmp_path):
    calls = {"run_parallel_backtest": 0}

    class FakeDb:
        def get_latest_market_date(self):
            return "2026-04-01"

    class FakeBacktester:
        def __init__(self, *args, **kwargs):
            self.db_path = "fake-db"
            self._db = FakeDb()
            self.scripted_strategy = lambda *args, **kwargs: None

        @property
        def db(self):
            return self._db

        def run_parallel_backtest(self, *args, **kwargs):
            calls["run_parallel_backtest"] += 1
            df = pd.DataFrame(
                {
                    "close": [9.0, 10.0, 11.0, 12.0, 13.0],
                    "close_d1": [8.0, 9.0, 10.0, 11.0, 12.0],
                    "ema_20": [10.0] * 5,
                    "ema_20_d1": [10.0] * 5,
                    "signal": [0, 0, 1, 0, 0],
                    "exit_condition": [False] * 5,
                }
            )
            return [
                {
                    "ticker": "AAA.DE",
                    "df": df,
                    "total_return_pct": 2.5,
                    "win_rate_pct": 50.0,
                    "profit_factor": 1.1,
                    "sharpe_ratio": 0.7,
                    "max_drawdown_pct": 1.5,
                    "num_trades": 1,
                }
            ]

    def fake_cache_dir():
        cache_dir = tmp_path / "strategy_eval"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    monkeypatch.setattr(
        "ETF_screener.scripts.churn_strategies.Backtester", FakeBacktester
    )
    monkeypatch.setattr(
        "ETF_screener.scripts.churn_strategies._strategy_eval_cache_dir",
        fake_cache_dir,
    )
    monkeypatch.setattr(
        "ETF_screener.scripts.churn_strategies._cached_strategy_tickers",
        lambda *args, **kwargs: ("AAA.DE",),
    )

    kwargs = {
        "dsl_content": "TRIGGER: close > ema_20\nEXIT: close < ema_20",
        "strategy_name": "CacheTest",
    }

    first = evaluate_strategies(**kwargs)
    second = evaluate_strategies(**kwargs)

    assert calls["run_parallel_backtest"] == 1
    assert not first.empty
    assert not second.empty
    assert first.drop(columns=["df"]).equals(second.drop(columns=["df"]))
