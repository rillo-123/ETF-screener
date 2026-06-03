"""FastAPI dashboard application."""

# mypy: ignore-errors

import inspect
import asyncio
import hashlib
import os
import random
import re
import json
import logging as _logging_mod
import math
import uuid
from collections import deque
from functools import lru_cache
from datetime import date, datetime, timezone
from io import StringIO
import pandas as pd
from typing import Any, Optional
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ETF_screener.database import ETFDatabase
from ETF_screener.backtester import Backtester
from ETF_screener.config_loader import get_paths
from ETF_screener.dsl_parser import parse_strategy_scripts
from ETF_screener.logging_setup import setup_logging, get_log_file
from ETF_screener.market_data_service import MarketDataRefresher
from ETF_screener.shortlist_engine import ETFShortlistEngine
from ETF_screener.swarm_world import SwarmWorldEngine
from ETF_screener.scripts.churn_strategies import (
    evaluate_strategies,
    find_recent_entry_days,
    filter_tickers_by_exchange_and_list,
    parse_dsl_content,
)

try:
    from ETF_screener.plotter_plotly import InteractivePlotter as _InteractivePlotter
except ModuleNotFoundError as exc:
    # Keep the dashboard API importable when Plotly is not installed. Chart
    # endpoints will surface a clearer error if they are invoked.
    if exc.name != "plotly" and not str(exc.name).startswith("plotly"):
        raise
    _InteractivePlotter = None

InteractivePlotter: Any | None = _InteractivePlotter

app = FastAPI(title="ETF Discovery Lab API")

# Initialise logging as early as possible so that all subsequent imports and
# uvicorn log records are captured in the timestamped debug file.
logger = setup_logging()

SWARM_DNA_SCHEMA_VERSION = "swarm_agent_dna_v2"
SWARM_DNA_CONFIG_PATH = Path("config") / "swarm_agent_dna.json"
CUSTOM_TICKER_LIST_SCHEMA_VERSION = "custom_ticker_lists_v3"
CUSTOM_TICKER_LIST_CONFIG_PATH = Path("config") / "custom_ticker_list.json"
CUSTOM_TICKER_LIST_DEFAULT_NAME = "My List"
XETRA_METADATA_PATH = Path("config") / "xetra.json"
SWEDEN_METADATA_PATH = Path("config") / "sweden.json"
LEGACY_ETFS_METADATA_PATH = Path("config") / "etfs.json"
BLACKLIST_PATH = Path("config") / "blacklist.json"
SCREEN_EXPORTS_DIR = Path("data") / "exports"
BACKTEST_EXPORTS_DIR = Path("data") / "backtests"
BACKTEST_METRICS = [
    {"key": "quality_score", "label": "Quality Score", "kind": "score"},
    {"key": "return_pct", "label": "Return (%)", "kind": "percent"},
    {"key": "win_rate_pct", "label": "Win Rate (%)", "kind": "percent"},
    {"key": "sharpe", "label": "Sharpe", "kind": "ratio"},
    {"key": "profit_factor", "label": "Profit Factor", "kind": "ratio"},
    {"key": "max_dd_pct", "label": "Max Drawdown (%)", "kind": "percent"},
    {"key": "trades", "label": "Trades", "kind": "count"},
    {"key": "days_since_entry", "label": "Days Since Entry", "kind": "days"},
]
_JOB_PROGRESS_LOCK = Lock()
_JOB_PROGRESS_STATE: dict[str, object] = {
    "job": None,
    "phase": "idle",
    "label": "Idle",
    "detail": "",
    "pct": 0.0,
    "active": False,
    "updated_at": None,
    "error": None,
    "payload": None,
}
_BACKTEST_EVENT_LOCK = Lock()
_BACKTEST_EVENT_RUNS: dict[str, dict[str, object]] = {}
_BACKTEST_EVENT_MAX_RUNS = 8
_BACKTEST_EVENT_MAX_EVENTS = 2000


def _safe_float(val, default=None):
    """Return val as float, or default if it is NaN/inf/None."""
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _load_metadata_file_map(path: Path) -> dict[str, dict[str, object]]:
    """Load a ticker-to-metadata map from a config JSON file."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception:
        return {}

    normalized: dict[str, dict[str, object]] = {}
    if isinstance(raw, dict):
        for ticker, info in raw.items():
            if isinstance(info, dict):
                payload = dict(info)
            else:
                payload = {"name": str(info)}
            payload.setdefault("name", str(ticker))
            normalized[str(ticker).upper()] = payload
    return normalized


def _set_job_progress(
    job: str | None,
    phase: str,
    pct: float = 0.0,
    label: str | None = None,
    detail: str | None = None,
    active: bool = True,
    error: str | None = None,
    payload: object | None = None,
) -> None:
    with _JOB_PROGRESS_LOCK:
        _JOB_PROGRESS_STATE.update(
            {
                "job": job,
                "phase": phase,
                "label": label or str(job or "Job").replace("-", " ").title(),
                "detail": detail or "",
                "pct": max(0.0, min(100.0, float(pct))),
                "active": active,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "error": error,
                "payload": payload,
            }
        )


def _clear_job_progress(job: str | None = None) -> None:
    with _JOB_PROGRESS_LOCK:
        if job is None or _JOB_PROGRESS_STATE.get("job") == job:
            _JOB_PROGRESS_STATE.update(
                {
                    "job": None,
                    "phase": "idle",
                    "label": "Idle",
                    "detail": "",
                    "pct": 0.0,
                    "active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "error": None,
                    "payload": None,
                }
            )


def _update_job_progress(state: dict[str, object]) -> None:
    """Apply a callback payload from long-running dashboard work."""
    if not isinstance(state, dict):
        return
    job = str(state.get("job") or "dashboard")
    phase = str(state.get("phase") or "working")
    pct = _safe_float(state.get("pct"), 0.0) or 0.0
    label = str(state.get("label") or "").strip() or None
    detail = str(state.get("detail") or "").strip() or None
    active = bool(state.get("active", True))
    error = state.get("error")
    payload = state.get("payload")
    _set_job_progress(
        job,
        phase,
        pct=float(pct),
        label=label,
        detail=detail,
        active=active,
        error=str(error) if error else None,
        payload=payload,
    )


def _new_backtest_race_run(strategy_names: list[str]) -> str:
    """Create a thread-safe event buffer for one backtest race run."""
    run_id = uuid.uuid4().hex
    with _BACKTEST_EVENT_LOCK:
        _BACKTEST_EVENT_RUNS[run_id] = {
            "run_id": run_id,
            "strategies": list(strategy_names),
            "events": deque(maxlen=_BACKTEST_EVENT_MAX_EVENTS),
            "next_seq": 1,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if len(_BACKTEST_EVENT_RUNS) > _BACKTEST_EVENT_MAX_RUNS:
            oldest = sorted(
                _BACKTEST_EVENT_RUNS.values(),
                key=lambda item: str(item.get("created_at") or ""),
            )[0]
            _BACKTEST_EVENT_RUNS.pop(str(oldest["run_id"]), None)
    return run_id


def _work_item_key(
    *,
    run_id: str,
    strategy_name: str,
    ticker: object | None = None,
    market_data_version: object | None = None,
    params: object | None = None,
) -> str:
    payload = {
        "strategy": str(strategy_name or ""),
        "ticker": str(ticker or ""),
        "market_data_version": str(market_data_version or ""),
        "params": params or {},
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _append_backtest_race_event(
    run_id: str,
    event_type: str,
    *,
    lane: str | None = None,
    payload: dict[str, object] | None = None,
    active: bool | None = None,
) -> dict[str, object] | None:
    """Append a sequenced race event for worker/lane consumers."""
    with _BACKTEST_EVENT_LOCK:
        run = _BACKTEST_EVENT_RUNS.get(run_id)
        if not run:
            return None
        seq = int(run.get("next_seq") or 1)
        run["next_seq"] = seq + 1
        if active is not None:
            run["active"] = bool(active)
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        event = {
            "run_id": run_id,
            "seq": seq,
            "type": str(event_type),
            "lane": lane or "",
            "payload": payload or {},
            "ts": run["updated_at"],
        }
        events = run.get("events")
        if isinstance(events, deque):
            events.append(event)
        return event


def _get_backtest_race_events(
    run_id: str | None = None,
    *,
    after_seq: int = 0,
    limit: int = 200,
) -> dict[str, object]:
    with _BACKTEST_EVENT_LOCK:
        selected_run_id = run_id
        if not selected_run_id and _BACKTEST_EVENT_RUNS:
            latest = sorted(
                _BACKTEST_EVENT_RUNS.values(),
                key=lambda item: str(item.get("created_at") or ""),
            )[-1]
            selected_run_id = str(latest["run_id"])
        run = _BACKTEST_EVENT_RUNS.get(str(selected_run_id or ""))
        if not run:
            return {
                "run_id": selected_run_id or "",
                "active": False,
                "events": [],
                "next_seq": int(after_seq) + 1,
                "latest_seq": int(after_seq),
            }
        safe_after = max(0, int(after_seq or 0))
        safe_limit = max(1, min(int(limit or 200), 1000))
        events = [
            dict(event)
            for event in list(run.get("events") or [])
            if int(event.get("seq") or 0) > safe_after
        ][:safe_limit]
        latest_seq = int(run.get("next_seq") or 1) - 1
        return {
            "run_id": str(run["run_id"]),
            "active": bool(run.get("active")),
            "strategies": list(run.get("strategies") or []),
            "events": events,
            "next_seq": (int(events[-1]["seq"]) + 1) if events else safe_after + 1,
            "latest_seq": latest_seq,
        }


def _rank_matches(matches: list[dict]) -> list[dict]:
    """Composite breakdown-quality score, sorted descending.

    Components (min-max normalised across result set):
      Volume       40 % — higher = more conviction
      EMA 50 slope 35 % — more negative = stronger downtrend (inverted)
      Day change % 25 % — more negative = more decisive bar  (inverted)
    """
    if not matches:
        return matches

    def _minmax(vals: list[float], invert: bool = False) -> list[float]:
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return [0.5] * len(vals)
        ns = [(v - mn) / (mx - mn) for v in vals]
        return [1.0 - n if invert else n for n in ns]

    vols = [m["volume"] for m in matches]
    slopes = [m.get("ema_50_slope") or 0.0 for m in matches]
    changes = [m.get("change_pct") or 0.0 for m in matches]

    vol_s = _minmax(vols)
    slope_s = _minmax(slopes, invert=True)
    change_s = _minmax(changes, invert=True)

    for i, m in enumerate(matches):
        m["score"] = round(0.40 * vol_s[i] + 0.35 * slope_s[i] + 0.25 * change_s[i], 3)

    return sorted(matches, key=lambda x: x["score"], reverse=True)


def _format_basic_screen_matches(df: pd.DataFrame) -> list[dict]:
    """Normalize simple screen rows to the shape the dashboard expects."""
    matches = []
    for _, row in df.iterrows():
        matches.append(
            {
                "ticker": row.get("ticker", "UNKNOWN"),
                "close": _safe_float(row.get("close", row.get("Close", 0)), 0.0),
                "volume": _safe_float(row.get("volume", row.get("Volume", 0)), 0.0),
                "status": "Trending",
                "return_pct": 0.0,
                "change_pct": 0.0,
                "supertrend": _safe_float(
                    row.get("supertrend", row.get("Supertrend", 0)), 0.0
                ),
                "st_lower": _safe_float(
                    row.get("st_lower", row.get("ST_Lower", 0)), 0.0
                ),
            }
        )
    return matches


# Setup templates and static files
# We can keep the same template files as Flask (Jinja2 is compatible)
templates = Jinja2Templates(directory="src/ETF_screener/dashboard/templates")
app.mount(
    "/static",
    StaticFiles(directory="src/ETF_screener/dashboard/static"),
    name="static",
)


def get_strategies():
    """Load all .dsl strategies from the strategies directory."""
    strategies = []
    strat_dir = Path("strategies")
    if strat_dir.exists():
        for dsl_file in strat_dir.glob("*.dsl"):
            strategies.append(dsl_file.stem)
    return sorted(strategies)


def load_strategy_content(name):
    """Load the content of a strategy file."""
    strat_path = Path("strategies") / f"{name}.dsl"
    if strat_path.exists():
        return strat_path.read_text(encoding="utf-8")
    return ""


def _finite_number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def _backtest_ticker_exchange_bucket(ticker: object) -> str:
    symbol = str(ticker or "").upper()
    if symbol.endswith((".ST", ".SS")):
        return "sweden"
    if symbol.endswith((".DE", ".F", ".DU", ".HM", ".SG", ".BE", ".MU")):
        return "xetra"
    return "unknown"


def _backtest_row_from_series(row: pd.Series) -> dict[str, object]:
    ticker = str(row.get("Ticker", ""))
    return {
        "ticker": ticker,
        "strategy": str(row.get("Strategy", "")),
        "exchange": _backtest_ticker_exchange_bucket(ticker),
        "quality_score": round(_finite_number(row.get("Quality Score")), 2),
        "return_pct": round(_finite_number(row.get("Return (%)")), 2),
        "win_rate_pct": round(_finite_number(row.get("Win Rate (%)")), 2),
        "profit_factor": round(_finite_number(row.get("Profit Factor")), 2),
        "sharpe": round(_finite_number(row.get("Sharpe")), 2),
        "max_dd_pct": round(_finite_number(row.get("Max DD (%)")), 2),
        "trades": int(_finite_number(row.get("Trades"), 0.0)),
        "days_since_entry": int(_finite_number(row.get("Days Since Entry"), 999.0)),
    }


def _backtest_ticker_result_from_series(
    row: pd.Series,
    *,
    completed: int,
    total: int,
) -> dict[str, object]:
    return {
        "ticker": str(row.get("Ticker", "")),
        "completed": int(completed),
        "total": int(total),
        "return_pct": round(_finite_number(row.get("Return (%)")), 2),
        "win_rate_pct": round(_finite_number(row.get("Win Rate (%)")), 2),
        "profit_factor": round(_finite_number(row.get("Profit Factor")), 2),
        "sharpe": round(_finite_number(row.get("Sharpe")), 2),
        "max_dd_pct": round(_finite_number(row.get("Max DD (%)")), 2),
        "trades": int(_finite_number(row.get("Trades"), 0.0)),
        "quality_score": round(_finite_number(row.get("Quality Score")), 2),
        "days_since_entry": int(_finite_number(row.get("Days Since Entry"), 999.0)),
    }


def _trade_rows_for_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if "Trades" not in df.columns:
        return df
    trade_mask = pd.to_numeric(df["Trades"], errors="coerce").fillna(0) > 0
    trade_rows = df.loc[trade_mask].copy()
    return trade_rows if not trade_rows.empty else df


def _trade_count_for_summary(df: pd.DataFrame) -> int:
    if df is None or df.empty or "Trades" not in df.columns:
        return 0
    trade_mask = pd.to_numeric(df["Trades"], errors="coerce").fillna(0) > 0
    trade_rows = df.loc[trade_mask].copy()
    trades = pd.to_numeric(trade_rows["Trades"], errors="coerce").fillna(0)
    return int(max(0, round(float(trades.sum()))))


def _backtest_strategy_summary_from_frame(
    strategy_name: str,
    df: pd.DataFrame,
    *,
    index: int,
    status: str = "done",
    progress_pct: float = 100.0,
    detail: str = "",
) -> dict[str, object]:
    count = int(len(df))
    ticker_count = (
        int(df["Ticker"].nunique()) if not df.empty and "Ticker" in df.columns else 0
    )
    if df.empty:
        trade_rows = df
    elif "Trades" in df.columns:
        trade_mask = pd.to_numeric(df["Trades"], errors="coerce").fillna(0) > 0
        trade_rows = df.loc[trade_mask].copy()
    else:
        trade_rows = df.copy()
    scored_tickers = (
        int(trade_rows["Ticker"].nunique())
        if not trade_rows.empty and "Ticker" in trade_rows.columns
        else int(len(trade_rows))
    )
    no_trade_tickers = max(0, ticker_count - scored_tickers)

    quality_series = (
        trade_rows["Quality Score"]
        if not trade_rows.empty and "Quality Score" in trade_rows.columns
        else pd.Series(dtype=float)
    )
    return_series = (
        trade_rows["Return (%)"]
        if not trade_rows.empty and "Return (%)" in trade_rows.columns
        else pd.Series(dtype=float)
    )
    sharpe_series = (
        trade_rows["Sharpe"]
        if not trade_rows.empty and "Sharpe" in trade_rows.columns
        else pd.Series(dtype=float)
    )
    win_rate_series = (
        trade_rows["Win Rate (%)"]
        if not trade_rows.empty and "Win Rate (%)" in trade_rows.columns
        else pd.Series(dtype=float)
    )
    profit_factor_series = (
        trade_rows["Profit Factor"]
        if not trade_rows.empty and "Profit Factor" in trade_rows.columns
        else pd.Series(dtype=float)
    )
    max_dd_series = (
        trade_rows["Max DD (%)"]
        if not trade_rows.empty and "Max DD (%)" in trade_rows.columns
        else pd.Series(dtype=float)
    )

    best_quality = _finite_number(
        quality_series.max() if not quality_series.empty else 0.0
    )
    avg_quality = _finite_number(
        quality_series.mean() if not quality_series.empty else 0.0
    )
    avg_return = _finite_number(
        return_series.mean() if not return_series.empty else 0.0
    )
    avg_sharpe = _finite_number(
        sharpe_series.mean() if not sharpe_series.empty else 0.0
    )
    avg_win_rate = _finite_number(
        win_rate_series.mean() if not win_rate_series.empty else 0.0
    )
    avg_profit_factor = _finite_number(
        profit_factor_series.mean() if not profit_factor_series.empty else 0.0
    )
    avg_max_dd = _finite_number(
        max_dd_series.mean() if not max_dd_series.empty else 0.0
    )
    best_ticker = ""
    best_return = _finite_number(
        return_series.max() if not return_series.empty else 0.0
    )
    if (
        not trade_rows.empty
        and "Ticker" in trade_rows.columns
        and "Return (%)" in trade_rows.columns
    ):
        best_idx = pd.to_numeric(trade_rows["Return (%)"], errors="coerce").idxmax()
        if pd.notna(best_idx):
            best_ticker = str(trade_rows.loc[best_idx, "Ticker"])

    return {
        "strategy": strategy_name,
        "index": int(index),
        "status": status,
        "progress_pct": round(max(0.0, min(100.0, float(progress_pct))), 2),
        "detail": detail,
        "count": count,
        "ticker_count": ticker_count,
        "processed_tickers": ticker_count,
        "scored_tickers": scored_tickers,
        "no_trade_tickers": no_trade_tickers,
        "error_tickers": 0,
        "completed_tickers": ticker_count,
        "total_tickers": ticker_count,
        "last_ticker": "",
        "best_ticker": best_ticker,
        "best_return_pct": round(best_return, 2),
        "trades": _trade_count_for_summary(df),
        "quality_score": round(best_quality, 2),
        "avg_quality_score": round(avg_quality, 2),
        "return_pct": round(avg_return, 2),
        "sharpe": round(avg_sharpe, 2),
        "win_rate_pct": round(avg_win_rate, 2),
        "profit_factor": round(avg_profit_factor, 2),
        "max_dd_pct": round(avg_max_dd, 2),
        "speed_score": round(avg_quality, 2),
    }


def _empty_backtest_live_stats() -> dict[str, object]:
    return {
        "completed": 0,
        "total": 0,
        "scored": 0,
        "no_trade": 0,
        "errors": 0,
        "return_sum": 0.0,
        "quality_sum": 0.0,
        "sharpe_sum": 0.0,
        "win_rate_sum": 0.0,
        "profit_factor_sum": 0.0,
        "max_dd_sum": 0.0,
        "trades_sum": 0.0,
        "best_return": None,
        "best_ticker": "",
        "last_ticker": "",
    }


def _backtest_live_quality_score(
    return_pct: float,
    win_rate_pct: float,
    sharpe: float,
    max_dd_pct: float,
    trades: float,
) -> float:
    return _finite_number(
        return_pct
        * (win_rate_pct / 100.0)
        * (sharpe + 1.0)
        / ((1.0 + trades / 100.0) * (1.0 + max_dd_pct / 10.0))
    )


def _apply_backtest_live_ticker_result(
    lane: dict[str, object],
    stats: dict[str, object],
    ticker_result: object,
) -> None:
    if not isinstance(ticker_result, dict):
        return

    completed = int(_finite_number(ticker_result.get("completed"), 0.0))
    total = int(_finite_number(ticker_result.get("total"), 0.0))
    ticker = str(ticker_result.get("ticker") or "").strip()
    stats["completed"] = max(int(stats.get("completed") or 0), completed)
    stats["total"] = max(int(stats.get("total") or 0), total)
    if ticker:
        stats["last_ticker"] = ticker

    processed = int(stats.get("completed") or 0)
    total_tickers = int(stats.get("total") or 0)
    scored = int(stats.get("scored") or 0)
    no_trade = int(stats.get("no_trade") or 0)
    errors = int(stats.get("errors") or 0)

    def _update_lane_counters() -> None:
        lane.update(
            {
                "ticker_count": total_tickers,
                "processed_tickers": processed,
                "completed_tickers": processed,
                "total_tickers": total_tickers,
                "scored_tickers": scored,
                "no_trade_tickers": no_trade,
                "error_tickers": errors,
                "count": scored,
                "last_ticker": ticker or str(stats.get("last_ticker") or ""),
            }
        )

    if ticker_result.get("error"):
        stats["errors"] = errors + 1
        errors = int(stats.get("errors") or 0)
        _update_lane_counters()
        return

    return_pct = _finite_number(ticker_result.get("return_pct"), 0.0)
    win_rate_pct = _finite_number(ticker_result.get("win_rate_pct"), 0.0)
    profit_factor = _finite_number(ticker_result.get("profit_factor"), 0.0)
    sharpe = _finite_number(ticker_result.get("sharpe"), 0.0)
    max_dd_pct = _finite_number(ticker_result.get("max_dd_pct"), 0.0)
    trades = _finite_number(ticker_result.get("trades"), 0.0)
    if trades <= 0:
        stats["no_trade"] = no_trade + 1
        no_trade = int(stats.get("no_trade") or 0)
        _update_lane_counters()
        return

    scored = int(stats.get("scored") or 0) + 1
    quality_score = _finite_number(ticker_result.get("quality_score"), math.nan)
    if not math.isfinite(quality_score):
        quality_score = _backtest_live_quality_score(
            return_pct, win_rate_pct, sharpe, max_dd_pct, trades
        )

    stats["scored"] = scored
    stats["return_sum"] = float(stats.get("return_sum") or 0.0) + return_pct
    stats["quality_sum"] = float(stats.get("quality_sum") or 0.0) + quality_score
    stats["sharpe_sum"] = float(stats.get("sharpe_sum") or 0.0) + sharpe
    stats["win_rate_sum"] = float(stats.get("win_rate_sum") or 0.0) + win_rate_pct
    stats["profit_factor_sum"] = (
        float(stats.get("profit_factor_sum") or 0.0) + profit_factor
    )
    stats["max_dd_sum"] = float(stats.get("max_dd_sum") or 0.0) + max_dd_pct
    stats["trades_sum"] = float(stats.get("trades_sum") or 0.0) + trades

    best_return = stats.get("best_return")
    if best_return is None or return_pct > float(best_return):
        stats["best_return"] = return_pct
        stats["best_ticker"] = ticker

    lane.update(
        {
            "count": scored,
            "ticker_count": total_tickers,
            "processed_tickers": processed,
            "completed_tickers": processed,
            "total_tickers": total_tickers,
            "scored_tickers": scored,
            "no_trade_tickers": no_trade,
            "error_tickers": errors,
            "last_ticker": ticker,
            "best_ticker": str(stats.get("best_ticker") or ""),
            "best_return_pct": round(_finite_number(stats.get("best_return")), 2),
            "return_pct": round(float(stats["return_sum"]) / scored, 2),
            "quality_score": round(float(stats["quality_sum"]) / scored, 2),
            "avg_quality_score": round(float(stats["quality_sum"]) / scored, 2),
            "sharpe": round(float(stats["sharpe_sum"]) / scored, 2),
            "win_rate_pct": round(float(stats["win_rate_sum"]) / scored, 2),
            "profit_factor": round(float(stats["profit_factor_sum"]) / scored, 2),
            "max_dd_pct": round(float(stats["max_dd_sum"]) / scored, 2),
            "trades": int(max(0, round(float(stats["trades_sum"])))),
            "speed_score": round(float(stats["quality_sum"]) / scored, 2),
        }
    )


def _backtest_race_payload(
    strategy_names: list[str],
    strategy_summaries: list[dict[str, object]],
    *,
    run_id: str | None = None,
    active_strategy: str | None,
    completed: int,
    total: int,
    pct: float,
    phase: str,
    detail: str,
    work_completed: int | None = None,
    work_total: int | None = None,
    ticker_count: int | None = None,
) -> dict[str, object]:
    return {
        "run_id": run_id or "",
        "selected_strategies": list(strategy_names),
        "active_strategy": active_strategy or "",
        "completed": int(completed),
        "total": int(total),
        "work_completed": int(work_completed if work_completed is not None else 0),
        "work_total": int(work_total if work_total is not None else 0),
        "ticker_count": int(ticker_count if ticker_count is not None else 0),
        "strategy_count": int(len(strategy_names)),
        "pct": round(max(0.0, min(100.0, float(pct))), 2),
        "phase": phase,
        "detail": detail,
        "lanes": [
            {
                **lane,
            }
            for lane in strategy_summaries
        ],
    }


def _evaluate_strategy_frame(**kwargs) -> pd.DataFrame:
    signature = inspect.signature(evaluate_strategies)
    accepts_kwargs = any(
        param.kind == inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    )
    filtered = (
        kwargs
        if accepts_kwargs
        else {k: v for k, v in kwargs.items() if k in signature.parameters}
    )
    return evaluate_strategies(**filtered)


def _parse_strategy_selection(strategies: Optional[str]) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[\s,;]+", str(strategies or ""))
        if item.strip()
    ]


def _backtest_matrix_worker_plan(total_strategies: int) -> tuple[int, int]:
    """Bound nested backtest parallelism so "all strategies" stays stable."""
    safe_total = max(1, int(total_strategies))
    cpu_budget = max(1, min(os.cpu_count() or 4, 8))
    strategy_concurrency = min(safe_total, max(1, min(4, cpu_budget)))
    if safe_total == 1:
        ticker_workers = min(4, cpu_budget)
    else:
        ticker_workers = max(
            1,
            min(4, cpu_budget // max(1, strategy_concurrency)),
        )
    return strategy_concurrency, ticker_workers


@lru_cache(maxsize=4)
def _cached_dashboard_tickers(
    db_path: str, latest_market_date: str | None
) -> tuple[str, ...]:
    """Cache the home-page ticker list until market data advances."""
    blacklist = _cached_blacklist_tickers()
    with ETFDatabase(db_path=db_path) as db:
        conn = db._get_connection()
        tickers = pd.read_sql_query(
            "SELECT DISTINCT ticker FROM etf_data ORDER BY ticker", conn
        )["ticker"].tolist()
        if not tickers:
            for etf_path in (
                XETRA_METADATA_PATH,
                SWEDEN_METADATA_PATH,
                LEGACY_ETFS_METADATA_PATH,
            ):
                tickers = sorted(_load_metadata_file_map(etf_path).keys())
                if tickers:
                    break
        return tuple(
            str(ticker) for ticker in tickers if str(ticker).upper() not in blacklist
        )


@lru_cache(maxsize=4)
def _cached_dashboard_universe(
    db_path: str, latest_market_date: str | None
) -> tuple[dict[str, object], ...]:
    """Cache the list-builder ticker universe with metadata until market data advances."""
    tickers = _cached_dashboard_tickers(db_path, latest_market_date)
    metadata_map = _cached_etf_metadata_map()
    db_metadata: dict[str, dict[str, object]] = {}

    if tickers:
        with ETFDatabase(db_path=db_path) as db:
            conn = db._get_connection()
            metadata_df = pd.read_sql_query(
                "SELECT ticker, name, issuer, asset_class, region, source FROM etf_metadata",
                conn,
            )
        db_metadata = {
            str(row.get("ticker", "")).upper(): {
                "name": row.get("name"),
                "issuer": row.get("issuer"),
                "asset_class": row.get("asset_class"),
                "region": row.get("region"),
                "source": row.get("source"),
            }
            for _, row in metadata_df.iterrows()
            if str(row.get("ticker", "")).strip()
        }

    items: list[dict[str, object]] = []
    for ticker in tickers:
        upper_ticker = str(ticker).upper()
        db_info = db_metadata.get(upper_ticker, {})
        fallback_info = metadata_map.get(upper_ticker, {})
        source_hint = str(
            db_info.get("source") or fallback_info.get("source") or ""
        ).lower()
        exchange = _backtest_ticker_exchange_bucket(upper_ticker)
        if "sweden" in source_hint:
            exchange = "sweden"
        elif "xetra" in source_hint or "etfs.json" in source_hint:
            exchange = "xetra"

        name = (
            str(
                db_info.get("name") or fallback_info.get("name") or upper_ticker
            ).strip()
            or upper_ticker
        )
        items.append(
            {
                "ticker": upper_ticker,
                "name": name,
                "label": name,
                "issuer": str(
                    db_info.get("issuer") or fallback_info.get("issuer") or ""
                ).strip(),
                "asset_class": str(
                    db_info.get("asset_class") or fallback_info.get("asset_class") or ""
                ).strip(),
                "region": str(
                    db_info.get("region") or fallback_info.get("region") or ""
                ).strip(),
                "exchange": exchange,
            }
        )
    return tuple(items)


@lru_cache(maxsize=1)
def _cached_etf_metadata_map() -> dict[str, dict[str, object]]:
    """Load metadata from config/xetra.json, config/sweden.json, and config/etfs.json."""
    normalized: dict[str, dict[str, object]] = {}
    for etf_path in (
        XETRA_METADATA_PATH,
        SWEDEN_METADATA_PATH,
        LEGACY_ETFS_METADATA_PATH,
    ):
        normalized.update(_load_metadata_file_map(etf_path))
    return normalized


@lru_cache(maxsize=1)
def _cached_blacklist_tickers() -> set[str]:
    """Load the configured blacklist once for dashboard universe filtering."""
    if not BLACKLIST_PATH.exists():
        return set()
    try:
        with open(BLACKLIST_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception:
        return set()

    if isinstance(raw, dict):
        return {str(ticker).upper() for ticker in raw.keys()}
    if isinstance(raw, list):
        return {str(ticker).upper() for ticker in raw}
    return set()


@lru_cache(maxsize=8)
def _cached_screen_universe(
    db_path: str, latest_market_date: str | None
) -> tuple[str, ...]:
    """Cache the expensive ticker-universe query until market data advances."""
    blacklist = _cached_blacklist_tickers()
    with ETFDatabase(db_path=db_path) as db:
        conn = db._get_connection()
        universe_query = """
            WITH ranked AS (
                SELECT
                    ticker,
                    date,
                    volume,
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
                FROM etf_data
            ),
            agg AS (
                SELECT
                    ticker,
                    MAX(date) AS last_date,
                    COUNT(*) AS total_rows,
                    SUM(CASE WHEN volume > 0 THEN 1 ELSE 0 END) AS nonzero_volume_rows,
                    SUM(CASE WHEN rn <= 30 THEN 1 ELSE 0 END) AS recent_rows,
                    SUM(CASE WHEN rn <= 30 AND volume = 0 THEN 1 ELSE 0 END) AS recent_zero_volume_rows
                FROM ranked
                GROUP BY ticker
            )
            SELECT ticker
            FROM agg
            WHERE total_rows >= 50
              AND nonzero_volume_rows >= 10
              AND recent_rows >= 10
              AND recent_zero_volume_rows < 2
              AND last_date >= date('now', '-180 day')
        """
        universe_df = pd.read_sql_query(universe_query, conn)
        return tuple(
            sorted(
                str(ticker).upper()
                for ticker in universe_df["ticker"].tolist()
                if str(ticker).upper() not in blacklist
            )
        )


@lru_cache(maxsize=8)
def _cached_backtest_universe(
    db_path: str, latest_market_date: str | None
) -> tuple[str, ...]:
    """Cache the raw backtest ticker universe until market data advances."""
    blacklist = _cached_blacklist_tickers()
    with ETFDatabase(db_path=db_path) as db:
        conn = db._get_connection()
        tickers = pd.read_sql_query(
            "SELECT DISTINCT ticker FROM etf_data ORDER BY ticker", conn
        )["ticker"].tolist()
    return tuple(
        str(ticker).upper()
        for ticker in tickers
        if str(ticker).upper() not in blacklist
    )


def _screen_exports_dir() -> Path:
    SCREEN_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCREEN_EXPORTS_DIR


def _backtest_exports_dir() -> Path:
    BACKTEST_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKTEST_EXPORTS_DIR


def _build_backtest_export_frame(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Ticker",
        "Strategy",
        "Return (%)",
        "Win Rate (%)",
        "Profit Factor",
        "Sharpe",
        "Max DD (%)",
        "Trades",
        "Days Since Entry",
        "Quality Score",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)
    frame = df.copy()
    if "df" in frame.columns:
        frame = frame.drop(columns=["df"])
    ordered = [column for column in columns if column in frame.columns]
    extras = [column for column in frame.columns if column not in ordered]
    return frame[ordered + extras]


def _write_backtest_results_csv(
    df: pd.DataFrame,
    *,
    label: str = "backtest",
) -> Path:
    export_dir = _backtest_exports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^A-Za-z0-9._-]+", "_", label or "backtest").strip("_")
    csv_path = export_dir / f"{safe_label or 'backtest'}_{timestamp}.csv"
    frame = _build_backtest_export_frame(df)
    frame.to_csv(csv_path, index=False, float_format="%.2f")
    return csv_path


def _build_top_matches_export_frame(
    matches: list[dict[str, object]],
    *,
    strategy_name: str = "",
    scan_scope: str = "",
    exchange: str = "",
    ticker_list: str = "",
) -> pd.DataFrame:
    """Convert screen matches into a stable CSV layout."""
    rows: list[dict[str, object]] = []
    for idx, match in enumerate(matches, start=1):
        rows.append(
            {
                "rank": idx,
                "ticker": str(match.get("ticker") or "").upper(),
                "status": str(match.get("status") or ""),
                "close": _safe_float(match.get("close"), 0.0),
                "volume": _safe_float(match.get("volume"), 0.0),
                "return_pct": _safe_float(match.get("return_pct"), 0.0),
                "change_pct": _safe_float(match.get("change_pct"), 0.0),
                "ema_50_slope": _safe_float(match.get("ema_50_slope"), 0.0),
                "days_since_entry": int(match.get("days_since_entry") or 0),
                "score": _safe_float(match.get("score"), 0.0),
                "strategy": strategy_name,
                "scan_scope": scan_scope,
                "exchange": exchange,
                "ticker_list": ticker_list,
            }
        )
    return pd.DataFrame(rows)


def _write_top_matches_csv(
    matches: list[dict[str, object]],
    *,
    strategy_name: str = "",
    scan_scope: str = "",
    exchange: str = "",
    ticker_list: str = "",
) -> Path:
    export_dir = _screen_exports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_strategy = (
        re.sub(r"[^A-Za-z0-9._-]+", "_", strategy_name or "screen").strip("_")
        or "screen"
    )
    csv_path = export_dir / f"top_matches_{safe_strategy}_{timestamp}.csv"
    frame = _build_top_matches_export_frame(
        matches,
        strategy_name=strategy_name,
        scan_scope=scan_scope,
        exchange=exchange,
        ticker_list=ticker_list,
    )
    frame.to_csv(csv_path, index=False)
    return csv_path


def _normalize_market_source(value: object | None) -> str:
    cleaned = str(value or "xetra").strip().lower()
    if cleaned in {"sweden", "stockholm", "stockholms", "se", "ss", "st"}:
        return "sweden"
    if cleaned in {"list", "chosen", "chosen_list", "custom"}:
        return "list"
    if cleaned in {"all_lists", "alllists", "all list", "all lists"}:
        return "all_lists"
    if cleaned in {"debug", "demo", "dummy", "synthetic"}:
        return "debug"
    if cleaned in {"xetra", "germany", "de", "exchange", "all"}:
        return "xetra"
    return "xetra"


def _market_source_config(source: object | None) -> tuple[Path, str]:
    normalized = _normalize_market_source(source)
    if normalized == "sweden":
        return SWEDEN_METADATA_PATH, "active"
    if normalized == "list":
        return CUSTOM_TICKER_LIST_CONFIG_PATH, "active"
    if normalized == "all_lists":
        return CUSTOM_TICKER_LIST_CONFIG_PATH, "all"
    return XETRA_METADATA_PATH, "active"


def _swarm_scope_tickers(
    db,
    *,
    scan_scope: Optional[str] = None,
    exchange: Optional[str] = None,
    ticker_list: Optional[str] = None,
) -> list[str]:
    """Resolve the current Swarm selector into a concrete ticker list."""
    try:
        normalized_scope = _normalize_market_source(scan_scope or exchange or "xetra")
        latest_market_date = _latest_market_date_for(db)
        universe = list(_cached_screen_universe(_db_path_for(db), latest_market_date))
        return filter_tickers_by_exchange_and_list(
            universe,
            exchange=exchange,
            ticker_list=ticker_list,
            scan_scope=normalized_scope,
        )
    except Exception as exc:
        logger.warning(
            "Swarm scope resolution fell back to scope-only filtering: %s", exc
        )
        return []


def _ticker_matches_swarm_scope(ticker: object, scope: str) -> bool:
    upper = str(ticker or "").upper()
    if not upper:
        return False
    normalized = _normalize_market_source(scope)
    if normalized == "sweden":
        return upper.endswith(".ST") or upper.endswith(".SE") or upper.endswith(".SS")
    if normalized == "xetra":
        return upper.endswith(".DE") or upper.endswith(".F") or "." not in upper
    return True


def _swarm_is_debug_scope(
    scan_scope: object | None = None, exchange: object | None = None
) -> bool:
    return _normalize_market_source(scan_scope or exchange or "xetra") == "debug"


def _swarm_debug_asset_count(value: object | None, default: int = 24) -> int:
    try:
        cleaned = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        cleaned = default
    return max(1, min(cleaned, 400))


def _swarm_debug_seed(*parts: object) -> int:
    payload = "|".join(str(part or "") for part in parts)
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16], 16)


def _swarm_debug_close_for_radius(target_radius: float) -> float:
    safe_radius = max(1.35, min(float(target_radius), 8.5))
    return 10 ** ((safe_radius - 1.35) / 0.95)


def _swarm_debug_shortlist_frame(
    asset_count: int,
    *,
    scan_scope: object | None = None,
    exchange: object | None = None,
    ticker_list: object | None = None,
) -> pd.DataFrame:
    rng = random.Random(
        _swarm_debug_seed(asset_count, scan_scope, exchange, ticker_list, "world")
    )
    as_of_date = pd.Timestamp.utcnow().normalize().strftime("%Y-%m-%d")
    labels = ["Buy", "Watch", "Skip"]
    rows: list[dict[str, object]] = []

    for index in range(asset_count):
        ticker = f"DUMMY-{index + 1:03d}"
        target_radius = 1.9 + (rng.random() * 1.45) + ((index % 5) * 0.04)
        close = round(_swarm_debug_close_for_radius(target_radius), 4)
        volume = int(rng.uniform(50_000, 8_500_000))
        recent_entry_days = rng.choice([None, 1, 2, 4, 7, 12, 18])
        label = rng.choices(labels, weights=[0.36, 0.44, 0.20], k=1)[0]
        technical_score = round(rng.uniform(14.0, 96.0), 2)
        product_score = round(rng.uniform(12.0, 95.0), 2)
        exposure_score = round(rng.uniform(10.0, 92.0), 2)
        final_score = round(
            min(
                99.0,
                max(
                    1.0,
                    (technical_score * 0.42)
                    + (product_score * 0.31)
                    + (exposure_score * 0.27),
                ),
            ),
            2,
        )
        slope = round(rng.uniform(-5.5, 5.5), 3)
        components = {
            "ema_50_slope_pct": slope,
            "close_above_ema_50": int(rng.random() > 0.42),
            "close_above_supertrend": int(rng.random() > 0.48),
            "macd_above_signal": int(rng.random() > 0.5),
        }
        rows.append(
            {
                "ticker": ticker,
                "as_of_date": as_of_date,
                "name": f"Synthetic Asset {index + 1:03d}",
                "issuer": "Debug Lab",
                "asset_class": "Synthetic",
                "region": "Debug",
                "label": label,
                "close": close,
                "volume": volume,
                "recent_entry_days": recent_entry_days,
                "product_score": product_score,
                "exposure_score": exposure_score,
                "technical_score": technical_score,
                "final_score": final_score,
                "components_json": json.dumps(components),
            }
        )
    return pd.DataFrame(rows)


def _swarm_debug_nodes(
    engine: SwarmWorldEngine,
    asset_count: int,
    *,
    scan_scope: object | None = None,
    exchange: object | None = None,
    ticker_list: object | None = None,
) -> list[dict[str, object]]:
    shortlist_df = _swarm_debug_shortlist_frame(
        asset_count,
        scan_scope=scan_scope,
        exchange=exchange,
        ticker_list=ticker_list,
    )
    prepared = engine._prepare_rows(shortlist_df)
    for row in prepared:
        row["components_json"] = json.dumps(row.get("components", {}))
    return prepared


def _swarm_debug_history_payload(
    nodes: list[dict[str, object]],
    safe_days: int,
    *,
    scan_scope: object | None = None,
    exchange: object | None = None,
    ticker_list: object | None = None,
) -> dict[str, object]:
    date_index = pd.bdate_range(
        end=pd.Timestamp.utcnow().normalize(),
        periods=max(1, int(safe_days or 1)),
    )
    latest_date = str(date_index[-1].date())
    history: dict[str, dict[str, list]] = {}

    for row in nodes:
        ticker = str(row.get("ticker") or "").upper()
        if not ticker:
            continue
        rng = random.Random(
            _swarm_debug_seed(
                ticker,
                safe_days,
                scan_scope,
                exchange,
                ticker_list,
                "history",
            )
        )
        base_value = max(
            0.5,
            float(row.get("value") or row.get("close") or rng.uniform(5.0, 140.0)),
        )
        closes = [round(base_value, 6) for _ in range(len(date_index))]
        dividends = [0.0 for _ in range(len(date_index))]
        history[ticker] = {
            "closes": closes,
            "dividends": dividends,
        }

    return {
        "days": safe_days,
        "requested_tickers": len(nodes),
        "count": len(history),
        "as_of_date": latest_date,
        "history": history,
    }


# Database access function (FastAPI style)
def get_db():
    return ETFDatabase(db_path=get_paths()["data"]["etf_db"])


def _latest_market_date_for(db) -> str | None:
    """Return the latest market date when the DB implementation exposes it."""
    getter = getattr(db, "get_latest_market_date", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            return None
    return None


def _db_path_for(db) -> str:
    """Return a usable database path for real and fake DB implementations."""
    db_path = getattr(db, "db_path", None)
    if db_path is not None:
        return str(db_path)
    return str(get_paths()["data"]["etf_db"])


def _is_stale_date(raw_date: object, threshold_days: int = 0) -> bool:
    if not raw_date:
        return True
    try:
        latest_day = pd.to_datetime(raw_date).date()
    except Exception:
        return True
    return (date.today() - latest_day).days > max(0, int(threshold_days))


SCREEN_RESULT_CACHE_VERSION = "screen_result_v1"


def _screen_cache_dir() -> Path:
    cache_root = Path(get_paths()["data"]["cache"])
    cache_dir = cache_root / "screen_requests"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _screen_request_signature(
    *,
    strategy_name: str,
    strategy_text: str,
    latest_market_date: str | None,
    scan_scope: str | None,
    exchange: str | None,
    ticker_list: str | None,
    tickers: list[str],
    fallback_mode: bool,
) -> str:
    universe_blob = "|".join(str(ticker).upper() for ticker in tickers)
    payload = {
        "cache_version": SCREEN_RESULT_CACHE_VERSION,
        "strategy_name": strategy_name,
        "strategy_text_sha": hashlib.sha256(strategy_text.encode("utf-8")).hexdigest(),
        "latest_market_date": latest_market_date or "",
        "scan_scope": str(scan_scope or "").strip().lower(),
        "exchange": str(exchange or "").strip().lower(),
        "ticker_list_sha": hashlib.sha256(
            str(ticker_list or "").encode("utf-8")
        ).hexdigest(),
        "universe_sha": hashlib.sha256(universe_blob.encode("utf-8")).hexdigest(),
        "fallback_mode": bool(fallback_mode),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=16)
def _load_cached_screen_result(cache_key: str, _cache_mtime_ns: int) -> dict | None:
    cache_path = _screen_cache_dir() / f"{cache_key}.pkl"
    if not cache_path.exists():
        return None
    try:
        cached = pd.read_pickle(cache_path)
    except Exception:
        return None
    return cached if isinstance(cached, dict) else None


def _save_cached_screen_result(cache_key: str, payload: dict) -> None:
    cache_path = _screen_cache_dir() / f"{cache_key}.pkl"
    try:
        pd.to_pickle(payload, cache_path)
    except Exception:
        try:
            if cache_path.exists():
                cache_path.unlink()
        except Exception:
            pass


def _validate_swarm_dna_payload(payload: object) -> dict:
    """Validate the browser-generated Swarm DNA payload before writing config."""
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Swarm DNA payload must be an object"
        )

    if payload.get("schema_version") != SWARM_DNA_SCHEMA_VERSION:
        raise HTTPException(
            status_code=400,
            detail=f"schema_version must be {SWARM_DNA_SCHEMA_VERSION}",
        )

    top_agents = payload.get("top_agents")
    if not isinstance(top_agents, list) or not top_agents:
        raise HTTPException(
            status_code=400, detail="top_agents must be a non-empty list"
        )
    if len(top_agents) > 50:
        raise HTTPException(status_code=400, detail="top_agents is unexpectedly large")

    for idx, agent in enumerate(top_agents):
        if not isinstance(agent, dict):
            raise HTTPException(
                status_code=400, detail=f"top_agents[{idx}] must be an object"
            )
        dna = agent.get("dna")
        if not isinstance(dna, dict):
            raise HTTPException(
                status_code=400, detail=f"top_agents[{idx}].dna is required"
            )
        if dna.get("schema_version") != SWARM_DNA_SCHEMA_VERSION:
            raise HTTPException(
                status_code=400,
                detail=f"top_agents[{idx}].dna.schema_version must be {SWARM_DNA_SCHEMA_VERSION}",
            )
        modules = dna.get("behavior_modules")
        if not isinstance(modules, list):
            raise HTTPException(
                status_code=400,
                detail=f"top_agents[{idx}].dna.behavior_modules must be a list",
            )

        for module_idx, module in enumerate(modules):
            if not isinstance(module, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"top_agents[{idx}].dna.behavior_modules[{module_idx}] must be an object",
                )
            module_type = str(module.get("type", ""))
            if module_type in {"ema_cross_up", "ema_cross_down"}:
                if "fast_period" not in module or "slow_period" not in module:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"top_agents[{idx}].dna.behavior_modules[{module_idx}] "
                            "must include fast_period and slow_period"
                        ),
                    )

    validated = json.loads(json.dumps(payload, allow_nan=False))
    validated["saved_at"] = datetime.now(timezone.utc).isoformat()
    validated["saved_by"] = "dashboard_swarm_auto_save"
    return validated


def _normalize_custom_ticker_list_value(value: object) -> list[str]:
    """Return a stable, uppercase, de-duplicated ticker list from raw JSON input."""
    if isinstance(value, dict):
        value = value.get("tickers", [])

    if value is None:
        raw_items: list[object] = []
    elif isinstance(value, str):
        raw_items = re.split(r"[\s,;]+", value)
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = []

    tickers: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        ticker = str(item or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        tickers.append(ticker)
    return tickers


def _normalize_custom_ticker_list_name(value: object) -> str:
    """Return a stable display name for the saved custom list."""
    name = str(value or "").strip()
    return name or CUSTOM_TICKER_LIST_DEFAULT_NAME


def _normalize_custom_ticker_list_entry(
    value: object,
    fallback_name: str | None = None,
) -> dict[str, object] | None:
    """Normalize a single named ticker list entry."""
    name = _normalize_custom_ticker_list_name(fallback_name)
    tickers_source: object = []
    if isinstance(value, dict):
        name = _normalize_custom_ticker_list_name(
            value.get("name")
            or value.get("list_name")
            or value.get("label")
            or fallback_name
        )
        tickers_source = value.get("tickers", [])
    else:
        tickers_source = value

    tickers = _normalize_custom_ticker_list_value(tickers_source)
    if not tickers and not name:
        return None
    return {
        "name": name,
        "tickers": tickers,
        "count": len(tickers),
    }


def _normalize_custom_ticker_lists_payload(payload: object) -> dict:
    """Normalize the stored custom-list collection to a consistent structure."""
    entries: list[dict[str, object]] = []
    active_name = CUSTOM_TICKER_LIST_DEFAULT_NAME
    updated_at = None

    if isinstance(payload, dict):
        updated_at = payload.get("updated_at")
        active_list_name = None
        active_list_value = payload.get("active_list")
        if isinstance(active_list_value, dict):
            active_list_name = active_list_value.get("name")
        active_name = _normalize_custom_ticker_list_name(
            payload.get("active_name") or active_list_name or payload.get("name")
        )
        raw_lists = payload.get("lists")
        if isinstance(raw_lists, list):
            for raw_entry in raw_lists:
                entry = _normalize_custom_ticker_list_entry(raw_entry)
                if entry and entry["name"] not in {item["name"] for item in entries}:
                    entries.append(entry)
        else:
            entry = _normalize_custom_ticker_list_entry(
                payload,
                fallback_name=active_name,
            )
            if entry:
                entries.append(entry)
    elif isinstance(payload, (list, tuple, set, str)):
        entry = _normalize_custom_ticker_list_entry(payload, fallback_name=active_name)
        if entry:
            entries.append(entry)

    if not entries:
        entries.append(
            {
                "name": CUSTOM_TICKER_LIST_DEFAULT_NAME,
                "tickers": [],
                "count": 0,
            }
        )

    deduped: list[dict[str, object]] = []
    seen_names: set[str] = set()
    for entry in entries:
        name = _normalize_custom_ticker_list_name(entry.get("name"))
        if name in seen_names:
            continue
        seen_names.add(name)
        deduped.append(
            {
                "name": name,
                "tickers": _normalize_custom_ticker_list_value(
                    entry.get("tickers", [])
                ),
                "count": len(
                    _normalize_custom_ticker_list_value(entry.get("tickers", []))
                ),
            }
        )

    active = next(
        (entry for entry in deduped if entry["name"] == active_name), deduped[0]
    )
    total_unique: list[str] = []
    seen_tickers: set[str] = set()
    for entry in deduped:
        for ticker in entry["tickers"]:
            if ticker in seen_tickers:
                continue
            seen_tickers.add(ticker)
            total_unique.append(ticker)

    return {
        "schema_version": CUSTOM_TICKER_LIST_SCHEMA_VERSION,
        "updated_at": updated_at,
        "active_name": active["name"],
        "name": active["name"],
        "tickers": list(active["tickers"]),
        "count": len(active["tickers"]),
        "active_list": dict(active),
        "lists": deduped,
        "list_count": len(deduped),
        "total_count": len(total_unique),
    }


def _load_custom_ticker_list_payload() -> dict:
    """Load the persisted custom ticker list JSON from config."""
    if not CUSTOM_TICKER_LIST_CONFIG_PATH.exists():
        return _normalize_custom_ticker_lists_payload({})

    try:
        with open(CUSTOM_TICKER_LIST_CONFIG_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        logger.warning("Failed to read custom ticker list JSON: %s", exc, exc_info=True)
        fallback = _normalize_custom_ticker_lists_payload({})
        fallback["error"] = "could_not_read"
        return fallback

    return _normalize_custom_ticker_lists_payload(payload)


def _save_custom_ticker_list_payload(payload: object) -> dict:
    """Persist the custom ticker list JSON to config."""
    normalized_collection = _normalize_custom_ticker_lists_payload(payload)
    CUSTOM_TICKER_LIST_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    saved_payload = {
        "schema_version": CUSTOM_TICKER_LIST_SCHEMA_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "active_name": normalized_collection["active_name"],
        "name": normalized_collection["active_name"],
        "count": normalized_collection["count"],
        "tickers": normalized_collection["tickers"],
        "active_list": normalized_collection["active_list"],
        "lists": normalized_collection["lists"],
        "list_count": normalized_collection["list_count"],
        "total_count": normalized_collection["total_count"],
    }
    CUSTOM_TICKER_LIST_CONFIG_PATH.write_text(
        json.dumps(saved_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return saved_payload


@app.get("/api/job-progress")
async def job_progress():
    """Return the latest dashboard job progress snapshot."""
    with _JOB_PROGRESS_LOCK:
        return dict(_JOB_PROGRESS_STATE)


@app.get("/api/backtest/events")
async def backtest_events(
    run_id: Optional[str] = None,
    after_seq: int = 0,
    limit: int = 200,
):
    """Return sequenced race events for a backtest run."""
    return _get_backtest_race_events(run_id, after_seq=after_seq, limit=limit)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Suppress noisy favicon 404s until a real icon is added."""
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page."""
    db = get_db()
    try:
        latest_market_date = _latest_market_date_for(db)
        tickers = list(_cached_dashboard_tickers(_db_path_for(db), latest_market_date))
    except Exception:
        tickers = []

    strategies = get_strategies()
    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"tickers": tickers, "strategies": strategies},
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/api/strategies")
async def list_strategies():
    """Get list of available strategies."""
    return get_strategies()


@app.get("/api/strategy/{name}")
async def get_strategy(name: str):
    """Get strategy content."""
    content = load_strategy_content(name)
    if not content:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"name": name, "content": content}


@app.get("/api/ticker-universe")
async def ticker_universe():
    """Return the cached ticker universe with names for the list builder."""
    db = get_db()
    try:
        latest_market_date = _latest_market_date_for(db)
        items = list(_cached_dashboard_universe(_db_path_for(db), latest_market_date))
    except Exception as exc:
        logger.warning(
            "Ticker universe endpoint fell back to empty payload: %s",
            exc,
            exc_info=True,
        )
        items = []

    return {
        "count": len(items),
        "items": items,
        "latest_market_date": _latest_market_date_for(db),
    }


@app.get("/api/custom-ticker-list")
async def get_custom_ticker_list():
    """Return the persisted custom ticker list for the list builder."""
    return _load_custom_ticker_list_payload()


@app.post("/api/custom-ticker-list")
async def save_custom_ticker_list(request: Request):
    """Persist a user-built ticker list to config/custom_ticker_list.json."""
    try:
        payload = await request.json()
    except Exception as exc:
        logger.warning("Invalid custom ticker list JSON: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail="invalid json")

    try:
        saved = _save_custom_ticker_list_payload(payload)
    except Exception as exc:
        logger.error("Custom ticker list save failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "success",
        "schema_version": saved["schema_version"],
        "active_name": saved["active_name"],
        "name": saved["name"],
        "count": saved["count"],
        "updated_at": saved["updated_at"],
        "tickers": saved["tickers"],
        "lists": saved["lists"],
        "list_count": saved["list_count"],
        "total_count": saved["total_count"],
        "path": str(CUSTOM_TICKER_LIST_CONFIG_PATH).replace("\\", "/"),
    }


@app.get("/api/market-status")
def market_status(stale_after_days: int = 0, source: Optional[str] = None):
    """Return freshness information about the underlying market data cache."""
    metadata_path, collection_mode = _market_source_config(source)
    refresher = MarketDataRefresher(
        db_path=str(get_db().db_path),
        etfs_file=str(metadata_path),
        collection_mode=collection_mode,
    )
    try:
        return refresher.get_status(stale_after_days=stale_after_days)
    except Exception as e:
        logger.error("Market status endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/market-data/refresh")
def refresh_market_data(
    force: bool = True,
    stale_after_days: int = 0,
    depth: int = 400,
    max_workers: int = 8,
    source: Optional[str] = None,
):
    """Refresh stale market data, then rebuild shortlist artifacts."""
    safe_depth = max(60, min(int(depth), 1500))
    safe_workers = max(1, min(int(max_workers), 16))
    safe_stale_after_days = max(0, min(int(stale_after_days), 30))
    metadata_path, collection_mode = _market_source_config(source)
    logger.info(
        "Dashboard market refresh requested: source=%s force=%s stale_after_days=%s depth=%s max_workers=%s",
        source or "default",
        force,
        safe_stale_after_days,
        safe_depth,
        safe_workers,
    )
    refresher = MarketDataRefresher(
        db_path=str(get_db().db_path),
        etfs_file=str(metadata_path),
        collection_mode=collection_mode,
    )
    try:
        refresh_kwargs = {
            "depth": safe_depth,
            "stale_after_days": safe_stale_after_days,
            "force": force,
            "max_workers": safe_workers,
            "rebuild_shortlist": True,
        }
        if (
            "progress_callback"
            in inspect.signature(refresher.refresh_market_data).parameters
        ):
            refresh_kwargs["progress_callback"] = _update_job_progress
        _set_job_progress(
            "market-refresh",
            "starting",
            pct=2.0,
            label="Market Refresh",
            detail="Preparing market refresh",
            active=True,
        )
        result = refresher.refresh_market_data(**refresh_kwargs)
        logger.info(
            "Dashboard market refresh finished: requested=%s refreshed=%s failed=%s shortlist_rebuilt=%s latest_market_date=%s",
            result.get("requested"),
            result.get("refreshed"),
            result.get("failed"),
            result.get("shortlist_rebuilt"),
            result.get("latest_market_date"),
        )
        return result
    except Exception as e:
        _set_job_progress(
            "market-refresh",
            "failed",
            pct=100.0,
            label="Market Refresh",
            detail=str(e),
            active=False,
            error=str(e),
        )
        logger.error("Market refresh endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _clear_job_progress("market-refresh")


def _refresh_market_data_for_gui(
    source: Optional[str] = None,
) -> dict[str, object] | None:
    """Top up market data for GUI-driven actions when a user asks for it."""
    metadata_path, collection_mode = _market_source_config(source)
    logger.info(
        "Dashboard GUI refresh starting: source=%s metadata=%s collection_mode=%s",
        source or "default",
        metadata_path,
        collection_mode,
    )
    refresher = MarketDataRefresher(
        db_path=str(get_db().db_path),
        etfs_file=str(metadata_path),
        collection_mode=collection_mode,
    )
    try:
        refresh_kwargs = {
            "depth": 400,
            "stale_after_days": 0,
            "force": False,
            "max_workers": 8,
            "rebuild_shortlist": True,
        }
        if (
            "progress_callback"
            in inspect.signature(refresher.refresh_market_data).parameters
        ):
            refresh_kwargs["progress_callback"] = _update_job_progress
        _set_job_progress(
            "market-refresh",
            "starting",
            pct=2.0,
            label="Market Refresh",
            detail="Preparing market refresh",
            active=True,
        )
        result = refresher.refresh_market_data(**refresh_kwargs)
        logger.info(
            "Dashboard GUI refresh finished: requested=%s refreshed=%s failed=%s shortlist_rebuilt=%s",
            result.get("requested"),
            result.get("refreshed"),
            result.get("failed"),
            result.get("shortlist_rebuilt"),
        )
        return result
    except Exception as e:
        logger.warning("GUI market refresh failed: %s", e, exc_info=True)
        return None
    finally:
        _clear_job_progress("market-refresh")


@app.get("/api/shortlist")
async def shortlist(
    limit: int = 50,
    label: Optional[str] = None,
    refresh: bool = False,
):
    """Return the cached ETF shortlist, rebuilding it only when needed."""
    safe_limit = max(1, min(int(limit), 250))
    safe_label = label.title() if label else None
    if safe_label not in {None, "Buy", "Watch", "Skip"}:
        raise HTTPException(status_code=400, detail="label must be Buy, Watch, or Skip")

    engine = ETFShortlistEngine(db_path=str(get_db().db_path))
    try:
        df = engine.get_shortlist(limit=safe_limit, label=safe_label, refresh=refresh)
    except Exception as e:
        logger.error("Shortlist endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    rows = []
    for _, row in df.iterrows():
        reasons_raw = row.get("reasons_json", "[]")
        components_raw = row.get("components_json", "{}")
        try:
            reasons = json.loads(reasons_raw) if reasons_raw else []
        except Exception:
            reasons = []
        try:
            components = json.loads(components_raw) if components_raw else {}
        except Exception:
            components = {}

        rows.append(
            {
                "ticker": row["ticker"],
                "name": row.get("name", row["ticker"]),
                "label": row.get("label", "Watch"),
                "issuer": row.get("issuer", ""),
                "asset_class": row.get("asset_class", ""),
                "region": row.get("region", ""),
                "close": round(float(row.get("close", 0.0) or 0.0), 4),
                "volume": int(row.get("volume", 0) or 0),
                "recent_entry_days": (
                    int(row["recent_entry_days"])
                    if pd.notna(row.get("recent_entry_days"))
                    else None
                ),
                "product_score": round(float(row.get("product_score", 0.0) or 0.0), 2),
                "exposure_score": round(
                    float(row.get("exposure_score", 0.0) or 0.0), 2
                ),
                "technical_score": round(
                    float(row.get("technical_score", 0.0) or 0.0), 2
                ),
                "final_score": round(float(row.get("final_score", 0.0) or 0.0), 2),
                "reasons": reasons,
                "components": components,
                "as_of_date": row.get("as_of_date"),
                "updated_at": row.get("updated_at"),
            }
        )

    label_counts = {
        grade: sum(1 for item in rows if item["label"] == grade)
        for grade in ["Buy", "Watch", "Skip"]
    }

    return {
        "as_of_date": rows[0]["as_of_date"] if rows else None,
        "count": len(rows),
        "labels": label_counts,
        "rows": rows,
    }


@app.get("/api/swarm-world")
async def swarm_world(
    limit: Optional[int] = None,
    label: Optional[str] = None,
    refresh: bool = False,
    scan_scope: Optional[str] = None,
    exchange: Optional[str] = None,
    ticker_list: Optional[str] = None,
    debug_assets: Optional[int] = None,
):
    """Return the cached swarm world artifact for the exploratory tab."""
    safe_limit = None if limit is None else max(1, min(int(limit), 5000))
    safe_label = label.title() if label else None
    if safe_label not in {None, "Buy", "Watch", "Skip"}:
        raise HTTPException(status_code=400, detail="label must be Buy, Watch, or Skip")

    engine = SwarmWorldEngine(db_path=str(get_db().db_path))
    debug_scope = _swarm_is_debug_scope(scan_scope, exchange)

    if debug_scope:
        debug_count = _swarm_debug_asset_count(debug_assets)
        debug_nodes = _swarm_debug_nodes(
            engine,
            debug_count,
            scan_scope=scan_scope,
            exchange=exchange,
            ticker_list=ticker_list,
        )
        df = pd.DataFrame(debug_nodes)
    else:
        try:
            df = engine.get_world(limit=safe_limit, label=safe_label, refresh=refresh)
        except Exception as e:
            logger.error("Swarm world endpoint failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

        db = get_db()
        selected_tickers = _swarm_scope_tickers(
            db,
            scan_scope=scan_scope,
            exchange=exchange,
            ticker_list=ticker_list,
        )
        normalized_scope = _normalize_market_source(scan_scope or exchange or "xetra")
        if selected_tickers:
            selected = {str(ticker).upper() for ticker in selected_tickers}
            df = df[df["ticker"].astype(str).str.upper().isin(selected)].reset_index(
                drop=True
            )
        elif normalized_scope in {"list", "all_lists"}:
            df = df.iloc[0:0]
        elif normalized_scope in {"xetra", "sweden"}:
            df = df[
                df["ticker"].map(
                    lambda ticker: _ticker_matches_swarm_scope(ticker, normalized_scope)
                )
            ].reset_index(drop=True)

    nodes = []
    for _, row in df.iterrows():
        components_raw = row.get("components_json", "{}")
        try:
            components = json.loads(components_raw) if components_raw else {}
        except Exception:
            components = {}

        nodes.append(
            {
                "ticker": row["ticker"],
                "name": row.get("name", row["ticker"]),
                "issuer": row.get("issuer", ""),
                "asset_class": row.get("asset_class", ""),
                "region": row.get("region", ""),
                "label": row.get("label", "Watch"),
                "close": round(float(row.get("close", 0.0) or 0.0), 4),
                "volume": int(row.get("volume", 0) or 0),
                "recent_entry_days": (
                    int(row["recent_entry_days"])
                    if pd.notna(row.get("recent_entry_days"))
                    else None
                ),
                "product_score": round(float(row.get("product_score", 0.0) or 0.0), 2),
                "exposure_score": round(
                    float(row.get("exposure_score", 0.0) or 0.0), 2
                ),
                "technical_score": round(
                    float(row.get("technical_score", 0.0) or 0.0), 2
                ),
                "final_score": round(float(row.get("final_score", 0.0) or 0.0), 2),
                "energy": round(float(row.get("energy", 0.0) or 0.0), 2),
                "value": round(
                    float(row.get("value", row.get("close", 0.0)) or 0.0), 4
                ),
                "mass": round(float(row.get("mass", 0.0) or 0.0), 3),
                "momentum_score": round(
                    float(row.get("momentum_score", 0.0) or 0.0), 2
                ),
                "freshness_score": round(
                    float(row.get("freshness_score", 0.0) or 0.0), 2
                ),
                "row": int(row.get("grid_row", row.get("row", 0)) or 0),
                "col": int(row.get("grid_col", row.get("col", 0)) or 0),
                "x": round(float(row.get("x", 0.0) or 0.0), 2),
                "y": round(float(row.get("y", 0.0) or 0.0), 2),
                "z": round(float(row.get("z", 0.0) or 0.0), 2),
                "vx": round(float(row.get("vx", 0.0) or 0.0), 4),
                "vy": round(float(row.get("vy", 0.0) or 0.0), 4),
                "charge": round(float(row.get("charge", 1.0) or 1.0), 4),
                "radius": round(float(row.get("radius", 0.0) or 0.0), 2),
                "sphere_radius": round(float(row.get("sphere_radius", 0.0) or 0.0), 3),
                "sphere_x": round(
                    float(row.get("sphere_x", row.get("x", 0.0)) or 0.0), 4
                ),
                "sphere_y": round(
                    float(row.get("sphere_y", row.get("y", 0.0)) or 0.0), 4
                ),
                "sphere_z": round(
                    float(row.get("sphere_z", row.get("z", 0.0)) or 0.0), 4
                ),
                "latitude": round(float(row.get("latitude", 0.0) or 0.0), 6),
                "longitude": round(float(row.get("longitude", 0.0) or 0.0), 6),
                "color": row.get("color", "#64748b"),
                "components": components,
                "world_version": row.get("world_version"),
                "is_dummy": bool(row.get("is_dummy", debug_scope)),
                "as_of_date": row.get("as_of_date"),
                "updated_at": row.get("updated_at"),
            }
        )

    label_counts = {
        grade: sum(1 for item in nodes if item["label"] == grade)
        for grade in ["Buy", "Watch", "Skip"]
    }

    sphere_radius = (
        float(nodes[0].get("sphere_radius", getattr(engine, "MIN_WORLD_RADIUS", 120.0)))
        if nodes
        else float(getattr(engine, "MIN_WORLD_RADIUS", 120.0))
    )
    surface_area = 4.0 * math.pi * (sphere_radius**2)

    return {
        "world": {
            "layout": "sphere",
            "radius": round(sphere_radius, 4),
            "diameter": round(sphere_radius * 2.0, 4),
            "surface_area": round(surface_area, 4),
            "asset_count": len(nodes),
            "version": getattr(engine, "ARTIFACT_VERSION", "swarm_v1"),
        },
        "as_of_date": nodes[0]["as_of_date"] if nodes else None,
        "updated_at": nodes[0]["updated_at"] if nodes else None,
        "count": len(nodes),
        "labels": label_counts,
        "nodes": nodes,
    }


@app.get("/api/swarm-history")
async def swarm_history(
    days: int = 420,
    limit: Optional[int] = 5000,
    scan_scope: Optional[str] = None,
    exchange: Optional[str] = None,
    ticker_list: Optional[str] = None,
    debug_assets: Optional[int] = None,
):
    """Return compact cached close-price history for current swarm tickers."""
    safe_days = max(2, min(int(days), 1500))
    safe_limit = max(1, min(int(limit or 5000), 5000))
    db = get_db()
    engine = SwarmWorldEngine(db_path=str(db.db_path))
    debug_scope = _swarm_is_debug_scope(scan_scope, exchange)

    if debug_scope:
        debug_count = _swarm_debug_asset_count(debug_assets)
        debug_nodes = _swarm_debug_nodes(
            engine,
            debug_count,
            scan_scope=scan_scope,
            exchange=exchange,
            ticker_list=ticker_list,
        )
        return _swarm_debug_history_payload(
            debug_nodes,
            safe_days,
            scan_scope=scan_scope,
            exchange=exchange,
            ticker_list=ticker_list,
        )

    try:
        world_df = engine.get_world(limit=safe_limit, refresh=False)
    except Exception as e:
        logger.error("Swarm history world lookup failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    selected_tickers = _swarm_scope_tickers(
        db,
        scan_scope=scan_scope,
        exchange=exchange,
        ticker_list=ticker_list,
    )
    normalized_scope = _normalize_market_source(scan_scope or exchange or "xetra")
    tickers = [
        str(ticker).upper()
        for ticker in world_df.get("ticker", pd.Series(dtype=str)).dropna().tolist()
    ]
    if selected_tickers:
        selected = {str(ticker).upper() for ticker in selected_tickers}
        tickers = [ticker for ticker in tickers if ticker in selected]
    elif normalized_scope in {"list", "all_lists"}:
        tickers = []
    elif normalized_scope in {"xetra", "sweden"}:
        tickers = [
            ticker
            for ticker in tickers
            if _ticker_matches_swarm_scope(ticker, normalized_scope)
        ]
    if not tickers:
        return {
            "days": safe_days,
            "requested_tickers": 0,
            "count": 0,
            "as_of_date": None,
            "history": {},
        }

    conn = db._get_connection()
    etf_data_columns = {
        str(row[1]) for row in conn.execute("PRAGMA table_info(etf_data)").fetchall()
    }
    dividends_expr = (
        "COALESCE(dividends, 0) AS dividends"
        if "dividends" in etf_data_columns
        else "0.0 AS dividends"
    )
    chunk_size = 750
    history: dict[str, dict[str, list]] = {}
    latest_date: str | None = None
    for start in range(0, len(tickers), chunk_size):
        chunk = tickers[start : start + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        query = f"""
            SELECT ticker, date, close, dividends
            FROM (
                SELECT
                    ticker,
                    date,
                    close,
                    {dividends_expr},
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
                FROM etf_data
                WHERE ticker IN ({placeholders})
                  AND close IS NOT NULL
            )
            WHERE rn <= ?
            ORDER BY ticker, date
        """  # nosec B608 - placeholders are generated, values are parameterized
        frame = pd.read_sql_query(query, conn, params=[*chunk, safe_days])
        if frame.empty:
            continue
        frame["ticker"] = frame["ticker"].astype(str).str.upper()
        frame["date"] = frame["date"].astype(str)
        chunk_latest = str(frame["date"].max())
        latest_date = (
            chunk_latest if latest_date is None else max(latest_date, chunk_latest)
        )
        for ticker, group in frame.groupby("ticker", sort=False):
            clean_group = group.dropna(subset=["close"]).sort_values("date")
            closes = [
                round(float(value), 6)
                for value in clean_group["close"].tolist()
                if pd.notna(value)
            ]
            dividends = [
                round(float(value or 0.0), 6)
                for value in clean_group.get("dividends", pd.Series(dtype=float))
                .fillna(0.0)
                .tolist()
            ]
            if closes:
                history[str(ticker)] = {
                    "closes": closes,
                    "dividends": dividends[-len(closes) :],
                }

    return {
        "days": safe_days,
        "requested_tickers": len(tickers),
        "count": len(history),
        "as_of_date": latest_date,
        "history": history,
    }


@app.post("/api/swarm-dna/save")
async def save_swarm_dna(request: Request):
    """Persist the latest completed Swarm top-agent DNA into config."""
    try:
        raw_payload = await request.json()
        payload = _validate_swarm_dna_payload(raw_payload)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid json")
    except Exception as e:
        logger.error("Swarm DNA validation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    try:
        SWARM_DNA_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        SWARM_DNA_CONFIG_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        logger.error("Swarm DNA save failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        "path": str(SWARM_DNA_CONFIG_PATH).replace("\\", "/"),
        "agent_count": len(payload.get("top_agents", [])),
        "saved_at": payload["saved_at"],
    }


@app.post("/api/strategy/save")
async def save_strategy(request: Request):
    """Save a strategy to the strategies directory."""
    data = await request.json()
    name = data.get("name")
    content = data.get("content")

    if not name or not content:
        raise HTTPException(status_code=400, detail="Name and content required")

    # Sanitize name
    name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Invalid strategy name")

    strat_path = Path("strategies") / f"{name}.dsl"
    try:
        strat_path.parent.mkdir(parents=True, exist_ok=True)
        strat_path.write_text(content, encoding="utf-8")
        return {"status": "success", "message": f"Saved to {strat_path.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/screen")
async def screen(
    strategy: Optional[str] = None,
    dsl_content: Optional[str] = None,
    refresh: bool = False,
    scan_scope: Optional[str] = None,
    exchange: Optional[str] = None,
    ticker_list: Optional[str] = None,
):
    """Run a dynamic screen based on selected strategies or provided DSL."""
    logger.info("=== SCREEN ENDPOINT START ===")
    logger.info(
        "Params: strategy=%s, dsl_content=%s",
        strategy,
        "PROVIDED" if dsl_content else "NONE",
    )
    db = get_db()
    latest_market_date = _latest_market_date_for(db)
    db_path = _db_path_for(db)

    _set_job_progress(
        "screen",
        "starting",
        pct=0.0,
        label="Screen",
        detail="Preparing screen...",
        active=True,
    )

    try:
        if refresh:
            _refresh_market_data_for_gui(source=scan_scope or exchange)
            latest_market_date = _latest_market_date_for(db)

        # Priority: 1. Provided DSL content (from Lab), 2. Named strategy (from dropdown)
        content = ""
        if dsl_content:
            content = dsl_content
            logger.info("Using provided DSL, length: %d chars", len(content))
        elif strategy:
            content = load_strategy_content(strategy)
            logger.info(
                "Loaded strategy '%s', length: %d chars",
                strategy,
                len(content) if content else 0,
            )

        if not content:
            cache_key = _screen_request_signature(
                strategy_name="",
                strategy_text="",
                latest_market_date=latest_market_date,
                scan_scope=scan_scope,
                exchange=exchange,
                ticker_list=ticker_list,
                tickers=[],
                fallback_mode=True,
            )
            cache_path = _screen_cache_dir() / f"{cache_key}.pkl"
            if not refresh and cache_path.exists():
                cached_mtime_ns = cache_path.stat().st_mtime_ns
                cached_payload = _load_cached_screen_result(cache_key, cached_mtime_ns)
                if cached_payload is not None:
                    _set_job_progress(
                        "screen",
                        "done",
                        pct=100.0,
                        label="Screen",
                        detail="Loaded cached results",
                        active=False,
                    )
                    return cached_payload

            logger.info("No strategy/DSL, using fallback basic trend screen")
            # Fallback to simple trend screen if no strategy found/selected
            conn = db._get_connection()
            query = """
                SELECT ticker, close, volume, supertrend, st_lower
                FROM etf_data 
                WHERE date = (SELECT MAX(date) FROM etf_data)
                AND close > st_lower
                ORDER BY volume DESC
                LIMIT 50
            """
            df = pd.read_sql_query(query, conn)
            matches = _format_basic_screen_matches(df)
            payload = {
                "matches": matches,
                "errors": [],
                "total_errors": 0,
                "total_candidates": len(matches),
            }
            _save_cached_screen_result(cache_key, payload)
            _set_job_progress(
                "screen",
                "done",
                pct=100.0,
                label="Screen",
                detail=f"{len(matches)} matches found",
                active=False,
            )
            return payload

        strategy_spec = parse_dsl_content(content)
        final_entry = strategy_spec["entry"]
        final_exit = strategy_spec["exit"]
        logger.info(
            "Strategy parsed. Entry script length: %d, Exit script length: %d, max_days=%s",
            len(final_entry),
            len(final_exit),
            strategy_spec.get("max_days"),
        )

        tickers = list(_cached_screen_universe(db_path, latest_market_date))
        tickers = filter_tickers_by_exchange_and_list(
            tickers,
            exchange=exchange,
            ticker_list=ticker_list,
            scan_scope=scan_scope,
        )
        logger.info("Ticker universe built: %d tickers to screen", len(tickers))
        if not tickers:
            _set_job_progress(
                "screen",
                "done",
                pct=100.0,
                label="Screen",
                detail="No tickers selected",
                active=False,
            )
            return {
                "matches": [],
                "errors": [],
                "total_errors": 0,
                "total_candidates": 0,
            }
        cache_key = _screen_request_signature(
            strategy_name=strategy
            or (strategy_spec.get("name") if isinstance(strategy_spec, dict) else ""),
            strategy_text=content,
            latest_market_date=latest_market_date,
            scan_scope=scan_scope,
            exchange=exchange,
            ticker_list=ticker_list,
            tickers=tickers,
            fallback_mode=False,
        )
        cache_path = _screen_cache_dir() / f"{cache_key}.pkl"
        if not refresh and cache_path.exists():
            cached_mtime_ns = cache_path.stat().st_mtime_ns
            cached_payload = _load_cached_screen_result(cache_key, cached_mtime_ns)
            if cached_payload is not None:
                _set_job_progress(
                    "screen",
                    "done",
                    pct=100.0,
                    label="Screen",
                    detail="Loaded cached results",
                    active=False,
                )
                return cached_payload
        # Run backtest for current status
        bt = Backtester()
        logger.info("Starting parallel backtest for %d tickers", len(tickers))
        run_kwargs = {
            "days": 200,
            "strategy_kwargs": {"entry_script": final_entry, "exit_script": final_exit},
        }
        if "max_workers" in inspect.signature(bt.run_parallel_backtest).parameters:
            run_kwargs["max_workers"] = 8
        if "show_progress" in inspect.signature(bt.run_parallel_backtest).parameters:
            run_kwargs["show_progress"] = True
        if (
            "task_timeout_seconds"
            in inspect.signature(bt.run_parallel_backtest).parameters
        ):
            run_kwargs["task_timeout_seconds"] = 45
        if (
            "progress_callback"
            in inspect.signature(bt.run_parallel_backtest).parameters
        ):
            run_kwargs["progress_callback"] = _update_job_progress
        results = await asyncio.to_thread(
            bt.run_parallel_backtest,
            tickers,
            bt.scripted_strategy,
            **run_kwargs,
        )
        logger.info(
            "Backtest complete, processing %d results", len(results) if results else 0
        )

        # Filter for currently active signals. Strategies with MAX_DAYS opt into
        # movie-scan style recency; otherwise we preserve the stricter latest-bar behavior.
        matches = []
        errors = []
        for idx, res in enumerate(results):
            if not res:
                continue

            ticker = res.get("ticker", "UNKNOWN")
            if "error" in res:
                logger.debug("Backtest error for %s: %s", ticker, res["error"])
                errors.append({"ticker": ticker, "error": res["error"]})
                continue

            df = res.get("df")
            if df is None or df.empty:
                logger.debug("No data for %s", ticker)
                errors.append(
                    {"ticker": ticker, "error": "No data or empty strategy result"}
                )
                continue

            # Align with CLI behavior: a match is an active entry signal on the latest bar.
            try:
                last_row = df.iloc[-1]
                latest_signal = last_row.get("signal", last_row.get("Signal", 0))
                strategy_max_days = strategy_spec.get("max_days")
                recent_days = None
                if strategy_max_days is not None:
                    recent_days = find_recent_entry_days(
                        df,
                        strategy_spec,
                        max_days=int(strategy_max_days),
                    )
                    is_match = recent_days is not None
                else:
                    is_match = latest_signal == 1
                    if is_match:
                        recent_days = 0

                # Additional metadata for the UI
                prev_row = df.iloc[-2] if len(df) > 1 else last_row

                if is_match:
                    # Handle possible column name variations (database vs dataframe)
                    close_val = _safe_float(
                        (
                            last_row["close"]
                            if "close" in last_row
                            else last_row.get("Close", 0)
                        ),
                        0.0,
                    )
                    vol_val = _safe_float(
                        (
                            last_row["volume"]
                            if "volume" in last_row
                            else last_row.get("Volume", 0)
                        ),
                        0.0,
                    )
                    prev_close = _safe_float(
                        (
                            prev_row["close"]
                            if "close" in prev_row
                            else prev_row.get("Close", 0)
                        ),
                        0.0,
                    )
                    change_pct = _safe_float(
                        ((close_val / prev_close) - 1) * 100 if prev_close else 0, 0.0
                    )
                    ema_50_slope_val = _safe_float(last_row.get("ema_50_slope"), 0.0)

                    matches.append(
                        {
                            "ticker": ticker,
                            "close": close_val,
                            "volume": vol_val,
                            "status": (
                                "Entry Signal"
                                if int(recent_days or 0) == 0
                                else f"Recent Entry ({int(recent_days)}d)"
                            ),
                            "return_pct": _safe_float(
                                res.get("total_return_pct", 0), 0.0
                            ),
                            "change_pct": change_pct,
                            "ema_50_slope": ema_50_slope_val,
                            "days_since_entry": int(recent_days or 0),
                        }
                    )
                    logger.info(
                        "Match found: %s (days_since_entry=%s, max_days=%s)",
                        ticker,
                        recent_days,
                        strategy_max_days,
                    )
            except Exception as e:
                logger.error(
                    "Error processing ticker %s: %s", ticker, str(e), exc_info=True
                )
                errors.append({"ticker": ticker, "error": str(e)})

        # Rank by composite breakdown-quality score
        matches = _rank_matches(matches)
        logger.info(
            "Screen complete. Matches: %d, Errors: %d", len(matches), len(errors)
        )
        _set_job_progress(
            "screen",
            "done",
            pct=100.0,
            label="Screen",
            detail=f"{len(matches)} matches found",
            active=False,
        )

        # Return matched ETFs along with errors for the UI
        payload = {
            "matches": matches,
            "errors": errors[:50],  # Limit errors returned to UI
            "total_errors": len(errors),
            "total_candidates": len(tickers),
        }
        _save_cached_screen_result(cache_key, payload)
        return payload

    except KeyboardInterrupt:
        logger.warning("Screen run interrupted by KeyboardInterrupt", exc_info=True)
        _set_job_progress(
            "screen",
            "failed",
            pct=100.0,
            label="Screen",
            detail="Screen run interrupted",
            active=False,
            error="Screen run interrupted",
        )
        return JSONResponse(
            status_code=503,
            content={
                "matches": [],
                "errors": [{"ticker": "SYSTEM", "error": "Screen run interrupted"}],
                "total_errors": 1,
                "total_candidates": 0,
            },
        )
    except Exception as e:
        logger.error("Screen endpoint failed: %s", str(e), exc_info=True)
        _set_job_progress(
            "screen",
            "failed",
            pct=100.0,
            label="Screen",
            detail=str(e),
            active=False,
            error=str(e),
        )
        return JSONResponse(
            status_code=500,
            content={
                "matches": [],
                "errors": [{"ticker": "SYSTEM", "error": str(e)}],
                "total_errors": 1,
                "total_candidates": 0,
            },
        )


@app.post("/api/screen/export")
async def export_screen_results(request: Request):
    """Write the current top matches to CSV and return it as a download."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}")

    matches = payload.get("matches")
    if not isinstance(matches, list) or not matches:
        raise HTTPException(status_code=400, detail="matches must be a non-empty array")

    normalized_matches: list[dict[str, object]] = []
    for item in matches:
        if isinstance(item, dict):
            normalized_matches.append(item)

    if not normalized_matches:
        raise HTTPException(status_code=400, detail="matches must contain objects")

    strategy_name = str(
        payload.get("strategy_name") or payload.get("strategy") or "Top Matches"
    ).strip()
    scan_scope = str(payload.get("scan_scope") or "").strip()
    exchange = str(payload.get("exchange") or "").strip()
    ticker_list = str(payload.get("ticker_list") or "").strip()

    csv_path = _write_top_matches_csv(
        normalized_matches,
        strategy_name=strategy_name,
        scan_scope=scan_scope,
        exchange=exchange,
        ticker_list=ticker_list,
    )
    frame = _build_top_matches_export_frame(
        normalized_matches,
        strategy_name=strategy_name,
        scan_scope=scan_scope,
        exchange=exchange,
        ticker_list=ticker_list,
    )
    csv_buffer = StringIO()
    frame.to_csv(csv_buffer, index=False)
    csv_text = csv_buffer.getvalue()

    download_name = csv_path.name
    logger.info("Top matches exported to %s", csv_path)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "X-Export-Path": str(csv_path),
        },
    )


@app.get("/api/backtest")
async def backtest_view(
    strategy: Optional[str] = None,
    dsl_content: Optional[str] = None,
    limit: int = 25,
    signal_days: Optional[int] = None,
    since_days: Optional[int] = None,
    refresh: bool = False,
    scan_scope: Optional[str] = None,
    exchange: Optional[str] = None,
    ticker_list: Optional[str] = None,
):
    """Evaluate a saved strategy and return ranked quality metrics for the UI."""
    strategy_name = (strategy or "").strip()
    dsl_text = (dsl_content or "").strip()
    source_type = "editor" if dsl_text else "saved"
    signal_window_days = signal_days if signal_days is not None else since_days

    if not strategy_name and not dsl_text:
        _set_job_progress(
            "backtest",
            "done",
            pct=100.0,
            label="Backtest",
            detail="No strategy selected",
            active=False,
        )
        return {
            "strategy_name": "",
            "source_type": source_type,
            "summary": {
                "count": 0,
                "best_quality": 0.0,
                "avg_return": 0.0,
                "avg_sharpe": 0.0,
            },
            "rows": [],
            "chart": {"data": [], "layout": {}},
        }

    strat_path = Path("strategies") / f"{strategy_name}.dsl"
    if not dsl_text and not strat_path.exists():
        raise HTTPException(status_code=404, detail="Strategy not found")

    _set_job_progress(
        "backtest",
        "starting",
        pct=0.0,
        label="Backtest",
        detail="Preparing backtest...",
        active=True,
    )

    try:
        if refresh:
            _refresh_market_data_for_gui(source=scan_scope or exchange)

        evaluate_kwargs = {
            "strategy_path": (strat_path.as_posix() if not dsl_text else None),
            "dsl_content": dsl_text or None,
            "strategy_name": (strategy_name or "Editor Draft"),
        }
        if signal_window_days is not None:
            evaluate_kwargs["since_days"] = signal_window_days
        if scan_scope is not None:
            evaluate_kwargs["scan_scope"] = scan_scope
        if exchange is not None:
            evaluate_kwargs["exchange"] = exchange
        if ticker_list is not None:
            evaluate_kwargs["ticker_list"] = ticker_list
        if "progress_callback" in inspect.signature(evaluate_strategies).parameters:
            evaluate_kwargs["progress_callback"] = _update_job_progress
        df = await asyncio.to_thread(evaluate_strategies, **evaluate_kwargs)
    except ValueError as e:
        logger.error("Backtest validation failed for %s: %s", strategy_name, e)
        _set_job_progress(
            "backtest",
            "failed",
            pct=100.0,
            label="Backtest",
            detail=str(e),
            active=False,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Backtest endpoint failed for %s: %s", strategy_name, e, exc_info=True
        )
        _set_job_progress(
            "backtest",
            "failed",
            pct=100.0,
            label="Backtest",
            detail=str(e),
            active=False,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))

    if df.empty:
        csv_path = _write_backtest_results_csv(
            df,
            label=f"backtest_{strategy_name or 'editor_draft'}",
        )
        _set_job_progress(
            "backtest",
            "done",
            pct=100.0,
            label="Backtest",
            detail="No scored results",
            active=False,
        )
        return {
            "strategy_name": strategy_name or "Editor Draft",
            "source_type": source_type,
            "csv_path": str(csv_path),
            "summary": {
                "count": 0,
                "best_quality": 0.0,
                "avg_return": 0.0,
                "avg_sharpe": 0.0,
            },
            "rows": [],
            "chart": {"data": [], "layout": {}},
        }

    safe_limit = max(1, min(int(limit), 100))
    view = df.head(safe_limit).copy()
    csv_path = _write_backtest_results_csv(
        df,
        label=f"backtest_{strategy_name or 'editor_draft'}",
    )
    rows = []
    for _, row in view.iterrows():
        rows.append(
            {
                "ticker": row["Ticker"],
                "strategy": row["Strategy"],
                "quality_score": round(float(row.get("Quality Score", 0.0)), 2),
                "return_pct": round(float(row.get("Return (%)", 0.0)), 2),
                "win_rate_pct": round(float(row.get("Win Rate (%)", 0.0)), 2),
                "profit_factor": round(float(row.get("Profit Factor", 0.0)), 2),
                "sharpe": round(float(row.get("Sharpe", 0.0)), 2),
                "max_dd_pct": round(float(row.get("Max DD (%)", 0.0)), 2),
                "trades": int(row.get("Trades", 0) or 0),
                "days_since_entry": int(row.get("Days Since Entry", 999) or 999),
            }
        )

    chart_rows = rows[: min(len(rows), 10)]
    chart = {
        "data": [
            {
                "type": "bar",
                "x": [row["ticker"] for row in chart_rows],
                "y": [row["quality_score"] for row in chart_rows],
                "marker": {
                    "color": [row["return_pct"] for row in chart_rows],
                    "colorscale": "RdYlGn",
                    "colorbar": {"title": "Return %"},
                },
                "hovertemplate": "Ticker: %{x}<br>Quality: %{y:.2f}<br>Return: %{marker.color:.2f}%<extra></extra>",
            }
        ],
        "layout": {
            "title": {"text": "Top Quality Scores", "font": {"size": 16}},
            "paper_bgcolor": "#ffffff",
            "plot_bgcolor": "#ffffff",
            "margin": {"l": 50, "r": 20, "t": 40, "b": 60},
            "xaxis": {"title": "Ticker", "tickangle": -25, "automargin": True},
            "yaxis": {"title": "Quality Score"},
        },
    }

    _set_job_progress(
        "backtest",
        "done",
        pct=100.0,
        label="Backtest",
        detail=f"{len(df)} rows scored",
        active=False,
    )

    return {
        "strategy_name": strategy_name or "Editor Draft",
        "source_type": source_type,
        "csv_path": str(csv_path),
        "summary": {
            "count": int(len(df)),
            "best_quality": round(float(df["Quality Score"].max()), 2),
            "avg_return": round(
                float(_trade_rows_for_summary(df)["Return (%)"].mean()), 2
            ),
            "avg_sharpe": round(float(_trade_rows_for_summary(df)["Sharpe"].mean()), 2),
            "trades": _trade_count_for_summary(df),
        },
        "rows": rows,
        "chart": chart,
    }


@app.get("/api/backtest/matrix")
async def backtest_matrix_view(
    strategies: Optional[str] = None,
    all_strategies: bool = False,
    limit: int = 1000,
    signal_days: Optional[int] = None,
    since_days: Optional[int] = None,
    refresh: bool = False,
    scan_scope: Optional[str] = None,
    exchange: Optional[str] = None,
    ticker_list: Optional[str] = None,
):
    """Evaluate multiple saved strategies and return rows for flexible 2D plotting."""
    requested = _parse_strategy_selection(strategies)
    available = get_strategies()
    if all_strategies or any(item.lower() == "all" for item in requested):
        strategy_names = available
    else:
        strategy_names = requested

    strategy_names = list(dict.fromkeys(strategy_names))
    if not strategy_names:
        return {
            "source_type": "saved_matrix",
            "strategies": [],
            "metrics": BACKTEST_METRICS,
            "summary": {
                "count": 0,
                "strategy_count": 0,
                "ticker_count": 0,
                "best_quality": 0.0,
                "avg_return": 0.0,
                "avg_sharpe": 0.0,
            },
            "rows": [],
        }

    missing = [
        name
        for name in strategy_names
        if not (Path("strategies") / f"{name}.dsl").exists()
    ]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy not found: {', '.join(missing[:5])}",
        )

    signal_window_days = signal_days if signal_days is not None else since_days
    frames: list[pd.DataFrame] = []
    total_strategies = len(strategy_names)
    db = get_db()
    latest_market_date = db.get_latest_market_date()
    ticker_universe = filter_tickers_by_exchange_and_list(
        list(_cached_backtest_universe(_db_path_for(db), latest_market_date)),
        exchange=exchange,
        ticker_list=ticker_list,
        scan_scope=scan_scope,
    )
    estimated_ticker_count = len(ticker_universe)
    total_work_items = total_strategies * estimated_ticker_count
    strategy_concurrency, ticker_workers = _backtest_matrix_worker_plan(
        total_strategies
    )
    logger.info(
        "Backtest matrix worker plan: strategies=%d strategy_concurrency=%d ticker_workers=%d estimated_tickers=%d",
        total_strategies,
        strategy_concurrency,
        ticker_workers,
        estimated_ticker_count,
    )
    strategy_worker_semaphore = asyncio.Semaphore(strategy_concurrency)
    run_id = _new_backtest_race_run(strategy_names)
    _append_backtest_race_event(
        run_id,
        "run_started",
        payload={
            "strategies": list(strategy_names),
            "strategy_count": total_strategies,
            "ticker_count": estimated_ticker_count,
            "work_total": total_work_items,
            "work_completed": 0,
            "scan_scope": scan_scope or "",
            "exchange": exchange or "",
            "ticker_list_count": len(_parse_strategy_selection(ticker_list)),
        },
        active=True,
    )
    strategy_summaries = [
        {
            "strategy": name,
            "index": idx,
            "status": "queued",
            "progress_pct": 0.0,
            "detail": "Queued",
            "count": 0,
            "ticker_count": estimated_ticker_count,
            "processed_tickers": 0,
            "scored_tickers": 0,
            "no_trade_tickers": 0,
            "error_tickers": 0,
            "completed_tickers": 0,
            "total_tickers": estimated_ticker_count,
            "last_ticker": "",
            "best_ticker": "",
            "best_return_pct": 0.0,
            "quality_score": 0.0,
            "avg_quality_score": 0.0,
            "return_pct": 0.0,
            "sharpe": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_dd_pct": 0.0,
            "speed_score": 0.0,
        }
        for idx, name in enumerate(strategy_names, start=1)
    ]
    live_strategy_stats = [_empty_backtest_live_stats() for _ in strategy_names]

    def _publish_race_state(
        *,
        active_strategy: str | None,
        current_index: int,
        current_pct: float,
        phase: str,
        detail: str,
        active: bool = True,
        error: str | None = None,
    ) -> None:
        completed_total = sum(
            1
            for lane in strategy_summaries
            if str(lane.get("status")) in {"done", "failed"}
        )
        all_done = completed_total >= total_strategies
        any_failed = any(
            str(lane.get("status")) == "failed" for lane in strategy_summaries
        )
        lane_progress_sum = sum(
            max(0.0, min(100.0, _finite_number(lane.get("progress_pct"), 0.0)))
            for lane in strategy_summaries
        )
        known_work_total = sum(
            max(0, int(_finite_number(lane.get("total_tickers"), 0.0)))
            for lane in strategy_summaries
        )
        if known_work_total <= 0:
            known_work_total = total_work_items
        completed_work_items = 0
        for lane in strategy_summaries:
            lane_total = max(0, int(_finite_number(lane.get("total_tickers"), 0.0)))
            lane_completed = max(
                0, int(_finite_number(lane.get("completed_tickers"), 0.0))
            )
            if str(lane.get("status")) in {"done", "failed"} and lane_total > 0:
                lane_completed = lane_total
            completed_work_items += min(lane_completed, lane_total or lane_completed)
        if not all_done and 0 <= current_index < len(strategy_summaries):
            current_lane_pct = max(0.0, min(100.0, float(current_pct)))
            existing_lane_pct = max(
                0.0,
                min(
                    100.0,
                    _finite_number(
                        strategy_summaries[current_index].get("progress_pct"), 0.0
                    ),
                ),
            )
            lane_progress_sum += max(0.0, current_lane_pct - existing_lane_pct)
            lane_total = max(
                0,
                int(
                    _finite_number(
                        strategy_summaries[current_index].get("total_tickers"),
                        float(estimated_ticker_count),
                    )
                ),
            )
            existing_completed = max(
                0,
                int(
                    _finite_number(
                        strategy_summaries[current_index].get("completed_tickers"), 0.0
                    )
                ),
            )
            current_completed = int(
                round((current_lane_pct / 100.0) * max(1, lane_total))
            )
            completed_work_items += max(0, current_completed - existing_completed)
        overall_pct = (
            (completed_work_items / max(1, known_work_total)) * 100.0
            if known_work_total > 0
            else lane_progress_sum / max(1, total_strategies)
        )
        if all_done:
            job_phase = "failed" if any_failed or phase == "failed" else "done"
        elif phase == "failed" and total_strategies <= 1:
            job_phase = "failed"
        else:
            job_phase = "running"
        job_active = (active or not all_done) and job_phase not in {"done", "failed"}
        display_work_total = known_work_total or total_work_items
        work_detail = (
            f"{completed_work_items}/{display_work_total} ticker-strategy checks"
            if display_work_total > 0
            else detail
        )
        race_payload = _backtest_race_payload(
            strategy_names,
            strategy_summaries,
            run_id=run_id,
            active_strategy=active_strategy,
            completed=completed_total,
            total=total_strategies,
            pct=overall_pct,
            phase=job_phase,
            detail=work_detail if job_phase == "running" else detail,
            work_completed=completed_work_items,
            work_total=display_work_total,
            ticker_count=estimated_ticker_count,
        )
        _set_job_progress(
            "backtest",
            job_phase,
            pct=overall_pct,
            label="Backtest Matrix",
            detail=work_detail if job_phase == "running" else detail,
            active=job_active,
            error=error,
            payload={"backtest_race": race_payload},
        )

    _publish_race_state(
        active_strategy=None,
        current_index=0,
        current_pct=0.0,
        phase="starting",
        detail=f"Preparing {total_strategies} strategies...",
        active=True,
    )

    try:
        if refresh:
            _refresh_market_data_for_gui(source=scan_scope or exchange)
        strategy_state_lock = Lock()

        async def _run_strategy_worker(index: int, strategy_name: str):
            async with strategy_worker_semaphore:
                current_index = index - 1
                start_detail = f"{strategy_name} ({index}/{total_strategies})"
                loaded_from_eval_cache = False
                _append_backtest_race_event(
                    run_id,
                    "lane_started",
                    lane=strategy_name,
                    payload={
                        "strategy": strategy_name,
                        "index": index,
                        "work_items": "ticker_universe",
                    },
                    active=True,
                )
                with strategy_state_lock:
                    strategy_summaries[current_index].update(
                        {
                            "status": "running",
                            "progress_pct": 0.0,
                            "detail": start_detail,
                        }
                    )
                _publish_race_state(
                    active_strategy=strategy_name,
                    current_index=current_index,
                    current_pct=0.0,
                    phase="running",
                    detail=start_detail,
                    active=True,
                )

                def _strategy_progress_callback(
                    state: dict[str, object],
                    *,
                    _index=current_index,
                    _strategy_name=strategy_name,
                ) -> None:
                    if not isinstance(state, dict):
                        return
                    phase = str(state.get("phase") or "running")
                    active = bool(state.get("active", True))
                    detail = (
                        str(state.get("detail") or "").strip()
                        or f"{_strategy_name} running"
                    )
                    pct_value = _safe_float(state.get("pct"), 0.0) or 0.0
                    payload = state.get("payload")
                    ticker_result = (
                        payload.get("ticker_result")
                        if isinstance(payload, dict)
                        else None
                    )
                    nonlocal loaded_from_eval_cache
                    if (
                        phase == "done"
                        and not active
                        and not isinstance(ticker_result, dict)
                    ):
                        loaded_from_eval_cache = True
                    with strategy_state_lock:
                        if isinstance(payload, dict):
                            _apply_backtest_live_ticker_result(
                                strategy_summaries[_index],
                                live_strategy_stats[_index],
                                ticker_result,
                            )
                        strategy_summaries[_index]["status"] = (
                            "done" if phase == "done" or not active else "running"
                        )
                        strategy_summaries[_index]["progress_pct"] = round(
                            max(0.0, min(100.0, float(pct_value))), 2
                        )
                        completed_tickers = int(
                            strategy_summaries[_index].get("completed_tickers") or 0
                        )
                        total_tickers = int(
                            strategy_summaries[_index].get("total_tickers") or 0
                        )
                        last_ticker = str(
                            strategy_summaries[_index].get("last_ticker") or ""
                        )
                        if last_ticker and total_tickers:
                            strategy_summaries[_index][
                                "detail"
                            ] = f"{completed_tickers}/{total_tickers} tickers, last {last_ticker}"
                        else:
                            strategy_summaries[_index]["detail"] = detail
                        lane_snapshot = dict(strategy_summaries[_index])
                    if isinstance(ticker_result, dict):
                        ticker = str(ticker_result.get("ticker") or "").strip()
                        trades = _finite_number(ticker_result.get("trades"), 0.0)
                        event_payload = {
                            **ticker_result,
                            "strategy": _strategy_name,
                            "progress_pct": round(
                                max(0.0, min(100.0, float(pct_value))), 2
                            ),
                            "scored": not bool(ticker_result.get("error"))
                            and float(trades) > 0,
                            "no_trade": not bool(ticker_result.get("error"))
                            and float(trades) <= 0,
                            "cache_hit": False,
                            "work_key": _work_item_key(
                                run_id=run_id,
                                strategy_name=_strategy_name,
                                ticker=ticker,
                                params={
                                    "signal_days": signal_window_days,
                                    "scan_scope": scan_scope,
                                    "exchange": exchange,
                                },
                            ),
                            "lane": lane_snapshot,
                        }
                        _append_backtest_race_event(
                            run_id,
                            "ticker_done",
                            lane=_strategy_name,
                            payload=event_payload,
                            active=True,
                        )
                    elif phase == "done" and not active:
                        _append_backtest_race_event(
                            run_id,
                            "lane_cached",
                            lane=_strategy_name,
                            payload={
                                "strategy": _strategy_name,
                                "detail": detail,
                                "progress_pct": round(
                                    max(0.0, min(100.0, float(pct_value))), 2
                                ),
                                "cache_hit": True,
                                "work_key": _work_item_key(
                                    run_id=run_id,
                                    strategy_name=_strategy_name,
                                    params={
                                        "signal_days": signal_window_days,
                                        "scan_scope": scan_scope,
                                        "exchange": exchange,
                                    },
                                ),
                            },
                            active=True,
                        )
                    _publish_race_state(
                        active_strategy=_strategy_name,
                        current_index=_index,
                        current_pct=float(pct_value),
                        phase=phase,
                        detail=str(strategy_summaries[_index].get("detail") or detail),
                        active=active,
                    )

                strat_path = Path("strategies") / f"{strategy_name}.dsl"
                evaluate_kwargs = {
                    "strategy_path": strat_path.as_posix(),
                    "strategy_name": strategy_name,
                    "dsl_content": None,
                    "progress_callback": _strategy_progress_callback,
                    "since_days": signal_window_days,
                    "scan_scope": scan_scope,
                    "exchange": exchange,
                    "ticker_list": ticker_list,
                    "max_workers": ticker_workers,
                }
                try:
                    df = await asyncio.to_thread(
                        _evaluate_strategy_frame, **evaluate_kwargs
                    )
                except Exception as exc:
                    logger.error(
                        "Backtest worker failed for %s: %s",
                        strategy_name,
                        exc,
                        exc_info=True,
                    )
                    with strategy_state_lock:
                        strategy_summaries[current_index].update(
                            {
                                "status": "failed",
                                "detail": str(exc),
                                "progress_pct": 100.0,
                            }
                        )
                    _publish_race_state(
                        active_strategy=strategy_name,
                        current_index=current_index,
                        current_pct=100.0,
                        phase="failed",
                        detail=str(exc),
                        active=False,
                        error=str(exc),
                    )
                    return current_index, pd.DataFrame(), exc

                if loaded_from_eval_cache and not df.empty:
                    total_cached_rows = int(len(df))
                    for completed, (_, row) in enumerate(df.iterrows(), start=1):
                        ticker_result = _backtest_ticker_result_from_series(
                            row,
                            completed=completed,
                            total=total_cached_rows,
                        )
                        pct_value = 5.0 + (
                            (completed / max(1, total_cached_rows)) * 88.0
                        )
                        with strategy_state_lock:
                            _apply_backtest_live_ticker_result(
                                strategy_summaries[current_index],
                                live_strategy_stats[current_index],
                                ticker_result,
                            )
                            strategy_summaries[current_index]["status"] = "running"
                            strategy_summaries[current_index]["progress_pct"] = round(
                                max(0.0, min(100.0, float(pct_value))), 2
                            )
                            strategy_summaries[current_index][
                                "detail"
                            ] = f"{completed}/{total_cached_rows} cached rows, last {ticker_result['ticker']}"
                            lane_snapshot = dict(strategy_summaries[current_index])
                        _append_backtest_race_event(
                            run_id,
                            "ticker_done",
                            lane=strategy_name,
                            payload={
                                **ticker_result,
                                "strategy": strategy_name,
                                "progress_pct": round(
                                    max(0.0, min(100.0, float(pct_value))), 2
                                ),
                                "scored": not bool(ticker_result.get("error"))
                                and _finite_number(ticker_result.get("trades"), 0.0)
                                > 0,
                                "no_trade": not bool(ticker_result.get("error"))
                                and _finite_number(ticker_result.get("trades"), 0.0)
                                <= 0,
                                "cache_hit": True,
                                "work_key": _work_item_key(
                                    run_id=run_id,
                                    strategy_name=strategy_name,
                                    ticker=ticker_result.get("ticker"),
                                    params={
                                        "signal_days": signal_window_days,
                                        "scan_scope": scan_scope,
                                        "exchange": exchange,
                                    },
                                ),
                                "lane": lane_snapshot,
                            },
                            active=True,
                        )
                        _publish_race_state(
                            active_strategy=strategy_name,
                            current_index=current_index,
                            current_pct=float(pct_value),
                            phase="running",
                            detail=strategy_summaries[current_index]["detail"],
                            active=True,
                        )

                strategy_summary = _backtest_strategy_summary_from_frame(
                    strategy_name,
                    df,
                    index=index,
                    status="done",
                    progress_pct=100.0,
                    detail=(
                        f"{len(df)} rows scored" if not df.empty else "No scored rows"
                    ),
                )
                with strategy_state_lock:
                    completed_tickers = int(
                        strategy_summaries[current_index].get("completed_tickers") or 0
                    )
                    processed_tickers = int(
                        strategy_summaries[current_index].get("processed_tickers") or 0
                    )
                    scored_tickers = int(
                        strategy_summaries[current_index].get("scored_tickers") or 0
                    )
                    no_trade_tickers = int(
                        strategy_summaries[current_index].get("no_trade_tickers") or 0
                    )
                    error_tickers = int(
                        strategy_summaries[current_index].get("error_tickers") or 0
                    )
                    total_tickers = int(
                        strategy_summaries[current_index].get("total_tickers") or 0
                    )
                    best_ticker = str(
                        strategy_summaries[current_index].get("best_ticker") or ""
                    )
                    best_return_pct = _finite_number(
                        strategy_summaries[current_index].get("best_return_pct"), 0.0
                    )
                    strategy_summaries[current_index].update(strategy_summary)
                    if completed_tickers <= 0:
                        completed_tickers = int(
                            strategy_summary.get("completed_tickers") or 0
                        )
                    if processed_tickers <= 0:
                        processed_tickers = int(
                            strategy_summary.get("processed_tickers")
                            or completed_tickers
                        )
                    if scored_tickers <= 0:
                        scored_tickers = int(
                            strategy_summary.get("scored_tickers") or 0
                        )
                    if no_trade_tickers <= 0:
                        no_trade_tickers = int(
                            strategy_summary.get("no_trade_tickers") or 0
                        )
                    if error_tickers <= 0:
                        error_tickers = int(strategy_summary.get("error_tickers") or 0)
                    if total_tickers <= 0:
                        total_tickers = int(strategy_summary.get("total_tickers") or 0)
                    if not best_ticker:
                        best_ticker = str(strategy_summary.get("best_ticker") or "")
                    if best_return_pct == 0.0:
                        best_return_pct = _finite_number(
                            strategy_summary.get("best_return_pct"), 0.0
                        )
                    strategy_summaries[current_index][
                        "completed_tickers"
                    ] = completed_tickers
                    strategy_summaries[current_index][
                        "processed_tickers"
                    ] = processed_tickers
                    strategy_summaries[current_index]["scored_tickers"] = scored_tickers
                    strategy_summaries[current_index][
                        "no_trade_tickers"
                    ] = no_trade_tickers
                    strategy_summaries[current_index]["error_tickers"] = error_tickers
                    strategy_summaries[current_index]["total_tickers"] = total_tickers
                    strategy_summaries[current_index]["best_ticker"] = best_ticker
                    strategy_summaries[current_index]["best_return_pct"] = round(
                        best_return_pct, 2
                    )
                    strategy_summaries[current_index]["status"] = "done"
                    strategy_summaries[current_index]["progress_pct"] = 100.0
                    strategy_summaries[current_index]["detail"] = (
                        f"{len(df)} rows scored" if not df.empty else "No scored rows"
                    )
                _publish_race_state(
                    active_strategy=strategy_name,
                    current_index=current_index,
                    current_pct=100.0,
                    phase="done",
                    detail=strategy_summaries[current_index]["detail"],
                    active=False,
                )
                _append_backtest_race_event(
                    run_id,
                    "lane_done",
                    lane=strategy_name,
                    payload={
                        "strategy": strategy_name,
                        "index": index,
                        "rows_scored": int(len(df)),
                        "ticker_count": int(
                            strategy_summaries[current_index].get("total_tickers") or 0
                        ),
                        "completed_tickers": int(
                            strategy_summaries[current_index].get("completed_tickers")
                            or 0
                        ),
                        "processed_tickers": int(
                            strategy_summaries[current_index].get("processed_tickers")
                            or 0
                        ),
                        "scored_tickers": int(
                            strategy_summaries[current_index].get("scored_tickers") or 0
                        ),
                        "no_trade_tickers": int(
                            strategy_summaries[current_index].get("no_trade_tickers")
                            or 0
                        ),
                        "error_tickers": int(
                            strategy_summaries[current_index].get("error_tickers") or 0
                        ),
                        "lane": dict(strategy_summaries[current_index]),
                    },
                    active=True,
                )
                return current_index, df, None

        tasks = [
            asyncio.create_task(_run_strategy_worker(index, strategy_name))
            for index, strategy_name in enumerate(strategy_names, start=1)
        ]
        results = await asyncio.gather(*tasks)
        first_error: Exception | None = None
        first_error_status = 500
        for _, df, err in results:
            if err is not None:
                if first_error is None:
                    first_error = err
                    first_error_status = 400 if isinstance(err, ValueError) else 500
                continue
            if not df.empty:
                frames.append(df)
        if first_error is not None:
            raise HTTPException(status_code=first_error_status, detail=str(first_error))
    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Backtest matrix validation failed: %s", e)
        _set_job_progress(
            "backtest",
            "failed",
            pct=100.0,
            label="Backtest Matrix",
            detail=str(e),
            active=False,
            error=str(e),
        )
        _publish_race_state(
            active_strategy=None,
            current_index=max(0, total_strategies - 1),
            current_pct=100.0,
            phase="failed",
            detail=str(e),
            active=False,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Backtest matrix endpoint failed: %s", e, exc_info=True)
        _set_job_progress(
            "backtest",
            "failed",
            pct=100.0,
            label="Backtest Matrix",
            detail=str(e),
            active=False,
            error=str(e),
        )
        _publish_race_state(
            active_strategy=None,
            current_index=max(0, total_strategies - 1),
            current_pct=100.0,
            phase="failed",
            detail=str(e),
            active=False,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))

    if frames:
        df = pd.concat(frames, ignore_index=True)
        if "Quality Score" in df.columns:
            df = df.sort_values(by="Quality Score", ascending=False)
    else:
        df = pd.DataFrame()

    safe_limit = max(1, min(int(limit), 5000))
    view = df.head(safe_limit).copy() if not df.empty else df
    rows = [_backtest_row_from_series(row) for _, row in view.iterrows()]
    csv_label = (
        "backtest_matrix_"
        + "_".join(strategy_names[:3])
        + (f"_plus_{len(strategy_names) - 3}" if len(strategy_names) > 3 else "")
    )
    csv_path = _write_backtest_results_csv(df, label=csv_label)

    _set_job_progress(
        "backtest",
        "done",
        pct=100.0,
        label="Backtest Matrix",
        detail=f"{len(df)} rows scored",
        active=False,
        payload={
            "backtest_race": _backtest_race_payload(
                strategy_names,
                strategy_summaries,
                run_id=run_id,
                active_strategy=strategy_names[-1] if strategy_names else None,
                completed=total_strategies,
                total=total_strategies,
                pct=100.0,
                phase="done",
                detail=f"{len(df)} rows scored",
            )
        },
    )
    _append_backtest_race_event(
        run_id,
        "run_done",
        payload={
            "rows_scored": int(len(df)),
            "strategy_count": int(len(strategy_names)),
            "ticker_count": int(df["Ticker"].nunique()) if not df.empty else 0,
        },
        active=False,
    )

    return {
        "source_type": "saved_matrix",
        "run_id": run_id,
        "csv_path": str(csv_path),
        "strategies": strategy_names,
        "strategy_summaries": strategy_summaries,
        "race": _backtest_race_payload(
            strategy_names,
            strategy_summaries,
            run_id=run_id,
            active_strategy=strategy_names[-1] if strategy_names else None,
            completed=total_strategies,
            total=total_strategies,
            pct=100.0,
            phase="done",
            detail=f"{len(df)} rows scored",
        ),
        "metrics": BACKTEST_METRICS,
        "universe": {
            "scan_scope": scan_scope or "",
            "exchange": exchange or "",
            "ticker_list_count": len(_parse_strategy_selection(ticker_list)),
        },
        "summary": {
            "count": int(len(df)),
            "returned": int(len(rows)),
            "strategy_count": int(len(strategy_names)),
            "ticker_count": int(df["Ticker"].nunique()) if not df.empty else 0,
            "best_quality": round(
                _finite_number(df["Quality Score"].max() if not df.empty else 0.0), 2
            ),
            "avg_return": round(
                _finite_number(
                    _trade_rows_for_summary(df)["Return (%)"].mean()
                    if not df.empty
                    else 0.0
                ),
                2,
            ),
            "avg_sharpe": round(
                _finite_number(
                    _trade_rows_for_summary(df)["Sharpe"].mean()
                    if not df.empty
                    else 0.0
                ),
                2,
            ),
            "trades": _trade_count_for_summary(df),
        },
        "rows": rows,
    }


@app.get("/api/chart/{ticker}")
async def get_chart(
    ticker: str,
    days: int = 365 * 2,
    strategy: Optional[str] = None,
    dsl_content: Optional[str] = None,
):
    """Generate and return an interactive chart for a ticker. Fetches if missing."""
    db = get_db()
    ticker = ticker.upper()
    blacklist = _cached_blacklist_tickers()
    is_blacklisted = ticker in blacklist

    # 1. Try to get data from database
    conn = db._get_connection()
    safe_days = max(1, min(days, 3650))
    query = f"SELECT * FROM etf_data WHERE ticker = ? ORDER BY date DESC LIMIT {safe_days}"  # nosec B608 - safe_days is int-clamped
    df = pd.read_sql_query(query, conn, params=(ticker,))

    latest_cached_day = None
    if not df.empty:
        latest_col = "date" if "date" in df.columns else "Date"
        try:
            latest_cached_day = pd.to_datetime(df[latest_col].max()).date()
        except Exception:
            latest_cached_day = None

    # 2. If data is missing, too sparse, or stale, fetch it.
    # Keep at least 100 bars so indicator warmup stays reliable for EMA50 and ATR.
    if not is_blacklisted and (
        df.empty or len(df) < 100 or _is_stale_date(latest_cached_day, threshold_days=0)
    ):
        logger.info(
            "Cache refresh for %s (count=%d, latest=%s). Fetching from Yahoo Finance...",
            ticker,
            len(df),
            latest_cached_day,
        )
        try:
            refresher = MarketDataRefresher(db_path=str(db.db_path))
            processed_df = refresher.refresh_ticker_data(
                ticker=ticker,
                depth=max(safe_days, 365),
                min_existing_rows=max(100, min(safe_days, 365)),
            )

            has_st = (
                not processed_df["Supertrend"].isna().all()
                if "Supertrend" in processed_df.columns
                else False
            )
            logger.info(
                "Ticker refresh complete for %s. Rows=%d, Supertrend calculated=%s",
                ticker,
                len(processed_df),
                has_st,
            )

            df = processed_df.sort_values("Date").tail(days)
        except Exception as e:
            logger.warning("Failed to fetch %s on demand: %s", ticker, e)
            # Instead of crashing let's return a specific error that the UI can catch
            raise HTTPException(
                status_code=404, detail=f"Data fetch failed for {ticker}: {str(e)}"
            )
    elif is_blacklisted and df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker {ticker} is blacklisted and has no cached data",
        )

    if df.empty:
        raise HTTPException(
            status_code=404, detail=f"No data found for ticker {ticker}"
        )

    df = df.sort_values("date" if "date" in df.columns else "Date")
    # Match the plotter's expected column names (normalized)
    rename_cols = {
        "date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "ema_50": "EMA_50",
        "supertrend": "Supertrend",
        "st_upper": "ST_Upper",
        "st_lower": "ST_Lower",
        "signal": "Signal",
    }
    # Direct rename to ensure uppercase matching for plotter
    df = df.rename(columns=rename_cols)

    # Check if we have the critical columns after normalization
    required = ["Date", "Close", "Open", "High", "Low"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        logger.warning(
            "Normalizing column names from DB for %s. Missing: %s. Available: %s",
            ticker,
            missing,
            df.columns.tolist(),
        )
        # Check if we have 'open_price' instead of 'open' (some legacy code used 'open_price')
        if "open_price" in df.columns and "Open" not in df.columns:
            df = df.rename(columns={"open_price": "Open"})
            missing = [c for c in required if c not in df.columns]

    if missing:
        # If still missing, we might have a data integrity issue
        logger.error(
            "CRITICAL: %s is missing required columns %s for plotting.", ticker, missing
        )
        raise HTTPException(
            status_code=500,
            detail=f"Database schema mismatch for {ticker}. Missing {missing}",
        )

    strategy_content = ""
    if dsl_content:
        strategy_content = dsl_content
    elif strategy:
        strategy_content = load_strategy_content(strategy)

    if strategy_content:
        entry_script, exit_script = parse_strategy_scripts(strategy_content)
        if entry_script:
            bt = Backtester()
            try:
                strat_res = bt.scripted_strategy(
                    df.copy(),
                    ticker=ticker,
                    entry_script=entry_script,
                    exit_script=exit_script,
                )
                if (
                    isinstance(strat_res, dict)
                    and strat_res.get("df") is not None
                    and not strat_res["df"].empty
                ):
                    df = strat_res["df"]
            except Exception:
                logger.debug(
                    "Could not enrich chart data with strategy indicators for %s",
                    ticker,
                )

    def _fallback_plot_payload(frame: pd.DataFrame) -> dict:
        """Build a minimal chart payload when Plotly is unavailable."""
        local_df = frame.copy()
        local_df["Date"] = pd.to_datetime(local_df["Date"], errors="coerce")
        dates = [d.isoformat() if pd.notna(d) else None for d in local_df["Date"]]
        close = (
            pd.to_numeric(local_df.get("Close"), errors="coerce").fillna(0.0).tolist()
        )
        data = [
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Close",
                "x": dates,
                "y": close,
            }
        ]

        for candidate in ("Supertrend", "supertrend", "st", "ST_Lower", "st_lower"):
            if candidate in local_df.columns:
                series = pd.to_numeric(local_df[candidate], errors="coerce")
                series = series.ffill().bfill().fillna(0.0)
                data.append(
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "name": "ST",
                        "x": dates,
                        "y": series.tolist(),
                        "line": {"color": "#10b981", "width": 2},
                    }
                )
                break

        return {
            "data": data,
            "layout": {
                "title": {"text": f"{ticker} Chart"},
                "xaxis": {"title": {"text": "Date"}},
                "yaxis": {"title": {"text": "Price"}},
                "template": "plotly_white",
            },
        }

    try:
        if InteractivePlotter is None:
            figure = _fallback_plot_payload(df)
            fig_json = json.dumps(figure, default=str)
            return {
                "ticker": ticker,
                "strategy_name": strategy or "Custom Strategy",
                "figure": fig_json,
                "data": figure.get("data", []),
                "layout": figure.get("layout", {}),
            }

        plotter = InteractivePlotter()
        fig = plotter.create_plot(df, ticker, strategy_content=strategy_content)
        # Fastapi JSONResponse or direct dict return will handle this.
        # But we need to ensure it's a DICT, not a JSON string,
        # because the frontend is now expecting the un-wrapped object.

        fig_json = fig.to_json()
        fig_dict = json.loads(fig_json)
        return {
            "ticker": ticker,
            "strategy_name": strategy or "Custom Strategy",
            "figure": fig_json,
            "data": fig_dict.get("data", []),
            "layout": fig_dict.get("layout", {}),
        }
    except Exception as e:

        logger.exception("Plotter failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=f"Plot generation failed: {str(e)}")


@app.get("/api/screen/basic")
async def screen_basic():
    """Run the basic trend screen without the DSL/backtester pipeline."""
    db = get_db()
    conn = db._get_connection()
    query = """
        SELECT ticker, close, volume, supertrend, st_lower
        FROM etf_data 
        WHERE date = (SELECT MAX(date) FROM etf_data)
        AND close > st_lower
        ORDER BY volume DESC
        LIMIT 50
    """
    try:
        df = pd.read_sql_query(query, conn)
        matches = _format_basic_screen_matches(df)
        return {
            "matches": matches,
            "errors": [],
            "total_errors": 0,
            "total_candidates": len(matches),
        }
    except Exception:
        logger.exception("Basic screen failed")
        return {
            "matches": [],
            "errors": [{"ticker": "SYSTEM", "error": "Basic screen failed"}],
            "total_errors": 1,
            "total_candidates": 0,
        }


# ---------------------------------------------------------------------------
# Browser log relay — receives console.log/warn/error calls from the frontend
# and writes them into the same server-side log file.
# ---------------------------------------------------------------------------


@app.post("/api/log")
async def browser_log(request: Request):
    """Accept JSON log records from the browser and write them to the server log."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "detail": "invalid json"}

    level_map = {
        "debug": _logging_mod.DEBUG,
        "info": _logging_mod.INFO,
        "warn": _logging_mod.WARNING,
        "warning": _logging_mod.WARNING,
        "error": _logging_mod.ERROR,
    }
    browser_logger = _logging_mod.getLogger("browser")
    level = level_map.get(str(body.get("level", "info")).lower(), _logging_mod.INFO)
    message = str(body.get("message", ""))
    stack = body.get("stack")
    url = body.get("url", "")
    line = body.get("line", "")

    full_msg = message
    if url or line:
        full_msg += f"  [{url}:{line}]"
    if stack:
        full_msg += f"\n{stack}"

    browser_logger.log(level, full_msg)
    return {"status": "ok", "log_file": str(get_log_file())}


@app.post("/api/log/console")
async def save_console_logs(request: Request):
    """Receive batched console logs from the browser and save them to a console_TIME.log file."""
    import datetime
    from pathlib import Path

    try:
        body = await request.json()
        logs = body.get("logs", [])
    except Exception as e:
        logger.error("Failed to parse console logs request: %s", str(e))
        return {"status": "error", "detail": "invalid json"}

    if not logs:
        return {"status": "ok", "count": 0}

    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create console log file with timestamp
        now = datetime.datetime.now()
        console_log_file = logs_dir / f"console_{now.strftime('%Y%m%d_%H%M%S')}.log"

        # Write logs
        with open(console_log_file, "a", encoding="utf-8") as f:
            for log_entry in logs:
                timestamp = log_entry.get("timestamp", "")
                level = log_entry.get("level", "LOG")
                message = log_entry.get("message", "")
                f.write(f"[{timestamp}] {level}: {message}\n")

        logger.info(
            "Console logs saved: %d entries to %s", len(logs), console_log_file.name
        )

        # Apply retention policy: keep only 3 most recent console logs
        cleanup_old_logs(logs_dir, "console_", max_keep=3)

        return {"status": "ok", "count": len(logs), "file": str(console_log_file.name)}
    except Exception as e:
        logger.error("Error saving console logs: %s", str(e), exc_info=True)
        return {"status": "error", "detail": str(e)}


def cleanup_old_logs(logs_dir: Path, prefix: str, max_keep: int = 3):
    """Keep only the max_keep most recent log files with the given prefix."""
    import os

    try:
        log_files = sorted(
            [f for f in logs_dir.glob(f"{prefix}*.log")],
            key=lambda x: os.path.getctime(x),
            reverse=True,
        )

        # Remove all but the most recent max_keep files
        for old_file in log_files[max_keep:]:
            try:
                old_file.unlink()
                logger.info("Deleted old log file: %s", old_file.name)
            except Exception as e:
                logger.warning("Could not delete %s: %s", old_file.name, str(e))
    except Exception as e:
        logger.warning("Error during log cleanup for %s: %s", prefix, str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app_fast:app", host="127.0.0.1", port=5000, reload=True)
