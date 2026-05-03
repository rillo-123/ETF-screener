import pandas as pd

from ETF_screener.backtester import Backtester
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


def test_ema_breakout_fanout_strategy_requires_widening_gaps():
    bt = Backtester()
    strategy_path = "strategies/ema_breakout_fanout.dsl"
    with open(strategy_path, "r", encoding="utf-8") as handle:
        parsed = parse_dsl_content(handle.read())

    assert parsed["max_days"] == 20
    assert "cross_up(close, ema_30)" in parsed["trigger"]
    assert "(ema_30 - ema_50) > (ema_30_d1 - ema_50_d1)" in parsed["filter"]

    dates = pd.date_range(start="2024-01-01", periods=8)
    close = pd.Series([97.5, 97.8, 98.2, 98.8, 99.4, 100.0, 101.0, 102.0])

    df = pd.DataFrame(
        {
            "Date": dates,
            "close": close,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "volume": [100000.0] * 8,
            "ema_30": [98.0, 98.4, 98.8, 99.2, 99.7, 100.2, 100.8, 101.5],
            "ema_50": [97.0, 97.2, 97.4, 97.7, 98.0, 98.4, 98.8, 99.2],
            "ema_100": [96.0, 96.1, 96.2, 96.4, 96.6, 96.8, 97.0, 97.2],
            "ema_200": [94.0, 94.1, 94.2, 94.3, 94.4, 94.5, 94.6, 94.7],
        }
    )

    res = bt.scripted_strategy(df, "TEST", parsed["entry"], parsed["exit"])
    df_out = res["df"] if isinstance(res, dict) else res

    assert df_out is not None
    sig_col = "signal" if "signal" in df_out.columns else "Signal"
    assert sig_col in df_out.columns
    assert int(df_out[sig_col].fillna(0).sum()) >= 1
    assert df_out[sig_col].iloc[6] == 1


def test_epi_a_st_fanout_phase_flags_jan_20_2026():
    bt = Backtester()
    with open("strategies/epi_a_st_fanout_phase.dsl", "r", encoding="utf-8") as handle:
        parsed = parse_dsl_content(handle.read())

    df = pd.read_parquet("data/parquet/epi-a.st_data.parquet").rename(
        columns=lambda c: c.lower()
    )
    df["Date"] = pd.to_datetime(df["date"])

    res = bt.scripted_strategy(df, "EPI-A.ST", parsed["entry"], parsed["exit"])
    df_out = res["df"] if isinstance(res, dict) else res

    assert df_out is not None
    jan20 = df_out[df_out["Date"].dt.strftime("%Y-%m-%d") == "2026-01-20"].iloc[0]
    assert bool(jan20["entry_condition"]) is True
    assert int(jan20["signal"]) == 1


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
