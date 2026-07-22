"""Control-based screener utilities for recent technical-event scans."""

from __future__ import annotations

import math
import sqlite3
from collections import OrderedDict
from datetime import date, datetime, timedelta
from threading import Lock
from typing import Iterable

import pandas as pd

from ETF_screener.indicators import calculate_macd, calculate_rsi, calculate_stoch_rsi, calculate_supertrend

DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_HISTORY_DAYS = 365
DEFAULT_VOLUME_MAX = 20_000_000.0
DEFAULT_RSI_CROSS_VALUE = 50.0
DEFAULT_MACD_CROSS_MODE = "low_cross_buy"
DEFAULT_RSI_CROSS_MODE = "cross_up"
DEFAULT_STOCH_CROSS_VALUE = 20.0
DEFAULT_STOCH_CROSS_MODE = "cross_up"
DEFAULT_STOCH_CROSS_REGION = "below"
DEFAULT_SUPERTREND_EVENT_ENABLED = False
DEFAULT_SUPERTREND_CROSS_MODE = "red_to_green"
DEFAULT_EMA_RELATIONSHIP_ENABLED = False
DEFAULT_EMA_RELATIONSHIP_FAST = 10
DEFAULT_EMA_RELATIONSHIP_SLOW = 20
DEFAULT_EMA_RELATIONSHIP_SLOPE = "positive"
DEFAULT_EMA_RELATIONSHIP_ALLOWANCE = 0.1
INDICATOR_HISTORY_CACHE_MAXSIZE = 6

DEFAULT_SCREEN_FILTERS: dict[str, object] = {
    "lookback_days": DEFAULT_LOOKBACK_DAYS,
    "volume_range": {"min": 0.0, "max": DEFAULT_VOLUME_MAX},
    "macd_event_enabled": True,
    "rsi_event_enabled": True,
    "stoch_event_enabled": True,
    "rsi_cross_value": DEFAULT_RSI_CROSS_VALUE,
    "rsi_cross_mode": DEFAULT_RSI_CROSS_MODE,
    "stoch_cross_value": DEFAULT_STOCH_CROSS_VALUE,
    "stoch_cross_mode": DEFAULT_STOCH_CROSS_MODE,
    "stoch_cross_region": DEFAULT_STOCH_CROSS_REGION,
    "supertrend_event_enabled": DEFAULT_SUPERTREND_EVENT_ENABLED,
    "supertrend_cross_mode": DEFAULT_SUPERTREND_CROSS_MODE,
    "macd_cross_mode": DEFAULT_MACD_CROSS_MODE,
    "macd_event_age": 45,
    "rsi_event_age": 90,
    "stoch_event_age": 15,
    "supertrend_event_age": 30,
    "ema_relationship_enabled": DEFAULT_EMA_RELATIONSHIP_ENABLED,
    "ema_relationship_fast": DEFAULT_EMA_RELATIONSHIP_FAST,
    "ema_relationship_slow": DEFAULT_EMA_RELATIONSHIP_SLOW,
    "ema_relationship_slope": DEFAULT_EMA_RELATIONSHIP_SLOPE,
    "ema_relationship_allowance": DEFAULT_EMA_RELATIONSHIP_ALLOWANCE,
    "ema_relationship_age": 30,
    "ema_slope_20": "any",
    "ema_slope_50": "any",
    "ema_slope_200": "any",
    "ema_slope_lookback": 5,
    "ema_slope_flat_tolerance": 0.1,
}

_INDICATOR_HISTORY_CACHE: OrderedDict[
    tuple[str, str, int, tuple[str, ...]],
    pd.DataFrame,
] = OrderedDict()
_INDICATOR_HISTORY_CACHE_LOCK = Lock()


def _coerce_float(value: object, default: float, *, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    if not math.isfinite(numeric):
        numeric = default
    return max(minimum, min(maximum, numeric))


def _finite_or_none(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _coerce_int(value: object, default: int, *, minimum: int, maximum: int) -> int:
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        numeric = default
    return max(minimum, min(maximum, numeric))


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_range(
    payload: object,
    *,
    default_min: float,
    default_max: float,
    minimum: float,
    maximum: float,
) -> dict[str, float]:
    raw = payload if isinstance(payload, dict) else {}
    min_value = _coerce_float(
        raw.get("min"),
        default_min,
        minimum=minimum,
        maximum=maximum,
    )
    max_value = _coerce_float(
        raw.get("max"),
        default_max,
        minimum=minimum,
        maximum=maximum,
    )
    if min_value > max_value:
        min_value, max_value = max_value, min_value
    return {"min": min_value, "max": max_value}


def _normalize_event_age(value: object, *, lookback_days: int, default: int) -> int:
    return _coerce_int(value, default, minimum=0, maximum=lookback_days)


def _legacy_window_midpoint(payload: object, *, lookback_days: int, default: int) -> int:
    raw = payload if isinstance(payload, dict) else {}
    min_value = _coerce_int(raw.get("min"), 0, minimum=0, maximum=lookback_days)
    max_value = _coerce_int(
        raw.get("max"),
        lookback_days,
        minimum=0,
        maximum=lookback_days,
    )
    if min_value > max_value:
        min_value, max_value = max_value, min_value
    return int(round((min_value + max_value) / 2))


def normalize_screen_filters(payload: object | None = None) -> dict[str, object]:
    """Return a stable control payload for the recent-event screener."""
    raw = payload if isinstance(payload, dict) else {}
    lookback_days = _coerce_int(
        raw.get("lookback_days"),
        DEFAULT_LOOKBACK_DAYS,
        minimum=30,
        maximum=365,
    )
    defaults = DEFAULT_SCREEN_FILTERS
    filters = {
        "lookback_days": lookback_days,
        "volume_range": _normalize_range(
            raw.get("volume_range"),
            default_min=float(defaults["volume_range"]["min"]),  # type: ignore[index]
            default_max=float(defaults["volume_range"]["max"]),  # type: ignore[index]
            minimum=0.0,
            maximum=100_000_000.0,
        ),
        "macd_event_enabled": _coerce_bool(
            raw.get("macd_event_enabled"),
            True,
        ),
        "rsi_event_enabled": _coerce_bool(
            raw.get("rsi_event_enabled"),
            True,
        ),
        "stoch_event_enabled": _coerce_bool(
            raw.get("stoch_event_enabled"),
            True,
        ),
        "rsi_cross_value": _coerce_float(
            raw.get("rsi_cross_value"),
            DEFAULT_RSI_CROSS_VALUE,
            minimum=0.0,
            maximum=100.0,
        ),
        "rsi_cross_mode": str(raw.get("rsi_cross_mode") or DEFAULT_RSI_CROSS_MODE)
        .strip()
        .lower(),
        "stoch_cross_value": _coerce_float(
            raw.get("stoch_cross_value"),
            DEFAULT_STOCH_CROSS_VALUE,
            minimum=0.0,
            maximum=100.0,
        ),
        "stoch_cross_mode": str(
            raw.get("stoch_cross_mode") or DEFAULT_STOCH_CROSS_MODE
        )
        .strip()
        .lower(),
        "stoch_cross_region": str(
            raw.get("stoch_cross_region") or DEFAULT_STOCH_CROSS_REGION
        )
        .strip()
        .lower(),
        "supertrend_event_enabled": bool(
            raw.get("supertrend_event_enabled", DEFAULT_SUPERTREND_EVENT_ENABLED)
        ),
        "supertrend_cross_mode": str(
            raw.get("supertrend_cross_mode") or DEFAULT_SUPERTREND_CROSS_MODE
        )
        .strip()
        .lower(),
        "macd_cross_mode": str(raw.get("macd_cross_mode") or DEFAULT_MACD_CROSS_MODE)
        .strip()
        .lower(),
        "macd_event_age": _normalize_event_age(
            raw.get("macd_event_age"),
            lookback_days=lookback_days,
            default=_legacy_window_midpoint(
                raw.get("macd_cross_window"),
                lookback_days=lookback_days,
                default=int(DEFAULT_SCREEN_FILTERS["macd_event_age"]),
            ),
        ),
        "rsi_event_age": _normalize_event_age(
            raw.get("rsi_event_age"),
            lookback_days=lookback_days,
            default=_legacy_window_midpoint(
                raw.get("rsi_cross_window"),
                lookback_days=lookback_days,
                default=int(DEFAULT_SCREEN_FILTERS["rsi_event_age"]),
            ),
        ),
        "stoch_event_age": _normalize_event_age(
            raw.get("stoch_event_age"),
            lookback_days=lookback_days,
            default=_legacy_window_midpoint(
                raw.get("stoch_cross_window"),
                lookback_days=lookback_days,
                default=int(DEFAULT_SCREEN_FILTERS["stoch_event_age"]),
            ),
        ),
        "supertrend_event_age": _normalize_event_age(
            raw.get("supertrend_event_age"),
            lookback_days=lookback_days,
            default=int(DEFAULT_SCREEN_FILTERS["supertrend_event_age"]),
        ),
        "ema_relationship_enabled": _coerce_bool(raw.get("ema_relationship_enabled"), DEFAULT_EMA_RELATIONSHIP_ENABLED),
        "ema_relationship_fast": _coerce_int(raw.get("ema_relationship_fast"), DEFAULT_EMA_RELATIONSHIP_FAST, minimum=2, maximum=200),
        "ema_relationship_slow": _coerce_int(raw.get("ema_relationship_slow"), DEFAULT_EMA_RELATIONSHIP_SLOW, minimum=3, maximum=400),
        "ema_relationship_slope": str(raw.get("ema_relationship_slope") or DEFAULT_EMA_RELATIONSHIP_SLOPE).strip().lower(),
        "ema_relationship_allowance": _coerce_float(raw.get("ema_relationship_allowance"), DEFAULT_EMA_RELATIONSHIP_ALLOWANCE, minimum=0.0, maximum=5.0),
        "ema_relationship_age": _normalize_event_age(raw.get("ema_relationship_age"), lookback_days=lookback_days, default=30),
        "ema_slope_20": str(raw.get("ema_slope_20") or "any").strip().lower(),
        "ema_slope_50": str(raw.get("ema_slope_50") or "any").strip().lower(),
        "ema_slope_200": str(raw.get("ema_slope_200") or "any").strip().lower(),
        "ema_slope_lookback": _coerce_int(raw.get("ema_slope_lookback"), 5, minimum=1, maximum=30),
        "ema_slope_flat_tolerance": _coerce_float(raw.get("ema_slope_flat_tolerance"), 0.1, minimum=0.0, maximum=5.0),
    }
    chart_ta = raw.get("chart_ta")
    if isinstance(chart_ta, dict):
        filters["chart_ta"] = dict(chart_ta)
    if filters["macd_cross_mode"] not in {
        "low_cross_buy",
        "high_cross_sell",
        "bullish_cross",
        "bearish_cross",
    }:
        filters["macd_cross_mode"] = DEFAULT_MACD_CROSS_MODE
    if filters["rsi_cross_mode"] not in {"cross_up", "cross_down"}:
        filters["rsi_cross_mode"] = DEFAULT_RSI_CROSS_MODE
    if filters["stoch_cross_mode"] not in {"cross_up", "cross_down"}:
        filters["stoch_cross_mode"] = DEFAULT_STOCH_CROSS_MODE
    if filters["stoch_cross_region"] not in {"below", "above", "any"}:
        filters["stoch_cross_region"] = DEFAULT_STOCH_CROSS_REGION
    if filters["supertrend_cross_mode"] not in {"green_to_red", "red_to_green"}:
        filters["supertrend_cross_mode"] = DEFAULT_SUPERTREND_CROSS_MODE
    if filters["ema_relationship_slope"] not in {"any", "positive", "negative"}:
        filters["ema_relationship_slope"] = DEFAULT_EMA_RELATIONSHIP_SLOPE
    if filters["ema_relationship_fast"] >= filters["ema_relationship_slow"]:
        filters["ema_relationship_fast"], filters["ema_relationship_slow"] = (
            filters["ema_relationship_slow"], filters["ema_relationship_fast"]
        )
    for key in ("ema_slope_20", "ema_slope_50", "ema_slope_200"):
        if filters[key] not in {"any", "positive", "flat", "negative"}:
            filters[key] = "any"
    return filters


def _chunked(values: Iterable[str], size: int = 400) -> Iterable[list[str]]:
    bucket: list[str] = []
    for value in values:
        bucket.append(str(value))
        if len(bucket) >= size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


def _resolve_latest_date(value: object | None) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return pd.Timestamp(value).date()
    except Exception:
        return datetime.utcnow().date()


def load_recent_price_history(
    db_path: str,
    tickers: list[str],
    *,
    latest_market_date: object | None,
    history_days: int,
) -> pd.DataFrame:
    """Load enough recent OHLCV history to evaluate the control-based screener."""
    normalized_tickers = [str(ticker).upper() for ticker in tickers if str(ticker).strip()]
    if not normalized_tickers:
        return pd.DataFrame()

    latest_date = _resolve_latest_date(latest_market_date)
    since_date = (latest_date - timedelta(days=max(history_days, DEFAULT_HISTORY_DAYS))).isoformat()
    frames: list[pd.DataFrame] = []
    conn = sqlite3.connect(db_path)
    try:
        for batch in _chunked(normalized_tickers):
            placeholders = ",".join("?" for _ in batch)
            query = f"""
                SELECT ticker, date, open, high, low, close, volume
                FROM etf_data
                WHERE date >= ?
                  AND ticker IN ({placeholders})
                ORDER BY ticker, date
            """
            params = [since_date, *batch]
            frame = pd.read_sql_query(query, conn, params=params)
            if not frame.empty:
                frames.append(frame)
    finally:
        conn.close()

    if not frames:
        return pd.DataFrame()
    history = pd.concat(frames, ignore_index=True)
    if history.empty:
        return history
    history["ticker"] = history["ticker"].astype(str).str.upper()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history = history.dropna(subset=["date"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    return history


def _indicator_history_cache_key(
    db_path: str,
    tickers: list[str],
    *,
    latest_market_date: object | None,
    history_days: int,
) -> tuple[str, str, int, tuple[str, ...]]:
    normalized_tickers = tuple(
        sorted(
            {
                str(ticker).upper()
                for ticker in tickers
                if str(ticker).strip()
            }
        )
    )
    latest_date = _resolve_latest_date(latest_market_date).isoformat()
    return (str(db_path), latest_date, int(history_days), normalized_tickers)


def _get_cached_indicator_history(
    cache_key: tuple[str, str, int, tuple[str, ...]],
) -> pd.DataFrame | None:
    with _INDICATOR_HISTORY_CACHE_LOCK:
        cached = _INDICATOR_HISTORY_CACHE.get(cache_key)
        if cached is None:
            return None
        _INDICATOR_HISTORY_CACHE.move_to_end(cache_key)
        return cached


def _store_cached_indicator_history(
    cache_key: tuple[str, str, int, tuple[str, ...]],
    history: pd.DataFrame,
) -> None:
    with _INDICATOR_HISTORY_CACHE_LOCK:
        _INDICATOR_HISTORY_CACHE[cache_key] = history
        _INDICATOR_HISTORY_CACHE.move_to_end(cache_key)
        while len(_INDICATOR_HISTORY_CACHE) > INDICATOR_HISTORY_CACHE_MAXSIZE:
            _INDICATOR_HISTORY_CACHE.popitem(last=False)


def clear_indicator_history_cache() -> None:
    with _INDICATOR_HISTORY_CACHE_LOCK:
        _INDICATOR_HISTORY_CACHE.clear()


def load_recent_indicator_history(
    db_path: str,
    tickers: list[str],
    *,
    latest_market_date: object | None,
    history_days: int,
) -> tuple[pd.DataFrame, bool]:
    cache_key = _indicator_history_cache_key(
        db_path,
        tickers,
        latest_market_date=latest_market_date,
        history_days=history_days,
    )
    cached = _get_cached_indicator_history(cache_key)
    if cached is not None:
        return cached, True

    history = load_recent_price_history(
        db_path,
        tickers,
        latest_market_date=latest_market_date,
        history_days=history_days,
    )
    if history.empty:
        return history, False

    enriched_frames: list[pd.DataFrame] = []
    for ticker, frame in history.groupby("ticker", sort=False):
        scoped = frame.sort_values("date").reset_index(drop=True).copy()
        scoped["ticker"] = str(ticker).upper()
        scoped["close"] = pd.to_numeric(scoped["close"], errors="coerce")
        scoped["volume"] = pd.to_numeric(scoped["volume"], errors="coerce").fillna(0.0)
        close = scoped["close"]
        high = pd.to_numeric(scoped["high"] if "high" in scoped else close, errors="coerce")
        low = pd.to_numeric(scoped["low"] if "low" in scoped else close, errors="coerce")
        scoped["high"] = high
        scoped["low"] = low
        rsi = calculate_rsi(close, period=14)
        macd, macd_signal, _ = calculate_macd(close)
        stoch_k, stoch_d = calculate_stoch_rsi(
            close,
            rsi_period=14,
            stoch_period=14,
            k_period=3,
            d_period=3,
        )
        scoped["rsi"] = rsi
        scoped["macd"] = macd
        scoped["macd_signal"] = macd_signal
        scoped["stoch_k"] = stoch_k
        scoped["stoch_d"] = stoch_d
        supertrend, st_upper, st_lower = calculate_supertrend(
            pd.DataFrame({"high": high, "low": low, "close": close})
        )
        scoped["supertrend_green"] = supertrend.eq(st_lower).where(supertrend.notna())
        enriched_frames.append(
            scoped[
                [
                    "ticker",
                    "date",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "rsi",
                    "macd",
                    "macd_signal",
                    "stoch_k",
                    "stoch_d",
                    "supertrend_green",
                ]
            ]
        )

    enriched_history = (
        pd.concat(enriched_frames, ignore_index=True)
        if enriched_frames
        else pd.DataFrame()
    )
    if not enriched_history.empty:
        _store_cached_indicator_history(cache_key, enriched_history)
    return enriched_history, False


def _crossed_above(lhs: pd.Series, rhs: pd.Series) -> pd.Series:
    return (lhs > rhs) & (lhs.shift(1) <= rhs.shift(1))


def _crossed_below(lhs: pd.Series, rhs: pd.Series) -> pd.Series:
    return (lhs < rhs) & (lhs.shift(1) >= rhs.shift(1))


def _crossed_above_value(series: pd.Series, value: float) -> pd.Series:
    return (series > value) & (series.shift(1) <= value)


def _crossed_below_value(series: pd.Series, value: float) -> pd.Series:
    return (series < value) & (series.shift(1) >= value)


def _latest_event_age_days(mask: pd.Series, dates: pd.Series, *, lookback_days: int) -> int | None:
    if mask.empty or dates.empty:
        return None
    latest_date = pd.Timestamp(dates.iloc[-1]).normalize()
    cutoff = latest_date - pd.Timedelta(days=lookback_days)
    scoped = mask.fillna(False) & (dates >= cutoff)
    if not bool(scoped.any()):
        return None
    event_date = pd.Timestamp(dates[scoped].iloc[-1]).normalize()
    return int((latest_date - event_date).days)


def _ema_slope_state(
    close: pd.Series, *, period: int, lookback: int, flat_tolerance: float
) -> str:
    ema = pd.to_numeric(close, errors="coerce").ewm(span=period, adjust=False).mean()
    if len(ema) <= lookback:
        return "unknown"
    current = _finite_or_none(ema.iloc[-1])
    previous = _finite_or_none(ema.iloc[-1 - lookback])
    if current is None or previous in (None, 0):
        return "unknown"
    change_pct = ((current / previous) - 1.0) * 100.0
    if abs(change_pct) <= flat_tolerance:
        return "flat"
    return "positive" if change_pct > 0 else "negative"


def _event_matches_target(
    age_days: int | None,
    target_age: int,
) -> bool:
    if age_days is None:
        return False
    return int(age_days) <= int(target_age)


def _ema_cross_event_mask(
    close: pd.Series,
    *,
    fast_period: int,
    slow_period: int,
    divergence_allowance: float,
    slope_direction: str = DEFAULT_EMA_RELATIONSHIP_SLOPE,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast = pd.to_numeric(close, errors="coerce").ewm(span=fast_period, adjust=False).mean()
    slow = pd.to_numeric(close, errors="coerce").ewm(span=slow_period, adjust=False).mean()
    states = pd.Series("unknown", index=close.index, dtype="object")
    valid = fast.notna() & slow.notna()
    states.loc[valid & fast.gt(slow)] = "fast above slow"
    states.loc[valid & fast.lt(slow)] = "fast below slow"

    cross_up = _crossed_above(fast, slow)
    cross_down = _crossed_below(fast, slow)
    cross = (cross_up | cross_down).fillna(False)
    gap_pct = ((fast - slow) / slow.replace(0, pd.NA)).abs() * 100.0
    gap_change = gap_pct.diff()
    divergence = gap_change.ge(-float(divergence_allowance)).fillna(False)
    slope_lookback = 5
    pair_slope = (fast.pct_change(slope_lookback) + slow.pct_change(slope_lookback)) / 2.0 * 100.0
    direction = str(slope_direction or DEFAULT_EMA_RELATIONSHIP_SLOPE).strip().lower()
    slope_matches = (
        direction == "any"
        if direction == "any"
        else pair_slope.gt(0) if direction == "positive" else pair_slope.lt(0)
    )
    mask = cross & slope_matches
    return mask.fillna(False), states, divergence


def _macd_cross_mask(
    macd: pd.Series,
    macd_signal: pd.Series,
    *,
    mode: str,
) -> pd.Series:
    normalized_mode = str(mode or DEFAULT_MACD_CROSS_MODE).strip().lower()
    bullish = _crossed_above(macd, macd_signal)
    bearish = _crossed_below(macd, macd_signal)
    if normalized_mode == "low_cross_buy":
        return bullish & (macd < 0)
    if normalized_mode == "high_cross_sell":
        return bearish & (macd > 0)
    if normalized_mode == "bearish_cross":
        return bearish
    return bullish


def _macd_cross_label(mode: str) -> str:
    normalized_mode = str(mode or DEFAULT_MACD_CROSS_MODE).strip().lower()
    if normalized_mode == "high_cross_sell":
        return "MACD/Signal bearish cross above zero"
    if normalized_mode == "bearish_cross":
        return "MACD/Signal bearish cross in any region"
    if normalized_mode == "bullish_cross":
        return "MACD/Signal bullish cross in any region"
    return "MACD/Signal bullish cross below zero"


def _rsi_cross_mask(rsi: pd.Series, *, level: float, mode: str) -> pd.Series:
    normalized_mode = str(mode or DEFAULT_RSI_CROSS_MODE).strip().lower()
    if normalized_mode == "cross_down":
        return _crossed_below_value(rsi, level)
    return _crossed_above_value(rsi, level)


def _rsi_cross_label(mode: str, level: float) -> str:
    normalized_mode = str(mode or DEFAULT_RSI_CROSS_MODE).strip().lower()
    direction = "down through" if normalized_mode == "cross_down" else "up through"
    return f"RSI crossed {direction} {float(level):.0f}"


def _stoch_cross_mask(
    stoch_k: pd.Series,
    stoch_d: pd.Series,
    *,
    level: float,
    mode: str,
    region: str,
) -> pd.Series:
    normalized_mode = str(mode or DEFAULT_STOCH_CROSS_MODE).strip().lower()
    k_prev = stoch_k.shift(1)
    d_prev = stoch_d.shift(1)
    if normalized_mode == "cross_down":
        crossed = (k_prev >= d_prev) & (stoch_k < stoch_d)
    else:
        crossed = (k_prev <= d_prev) & (stoch_k > stoch_d)
    normalized_region = str(region or DEFAULT_STOCH_CROSS_REGION).strip().lower()
    if normalized_region == "below":
        crossed &= stoch_k <= level
        crossed &= stoch_d <= level
    elif normalized_region == "above":
        crossed &= stoch_k >= level
        crossed &= stoch_d >= level
    return crossed.fillna(False)


def _stoch_cross_label(mode: str, level: float, region: str) -> str:
    normalized_mode = str(mode or DEFAULT_STOCH_CROSS_MODE).strip().lower()
    direction = "down through" if normalized_mode == "cross_down" else "up through"
    region_label = {
        "below": "below",
        "above": "above",
        "any": "any region",
    }.get(str(region or "").strip().lower(), "below")
    return f"StochRSI {direction} between K/D {region_label} {float(level):.0f}"


def _supertrend_cross_mask(green: pd.Series, *, mode: str) -> pd.Series:
    normalized_mode = str(mode or DEFAULT_SUPERTREND_CROSS_MODE).strip().lower()
    previous = green.shift(1)
    if normalized_mode == "green_to_red":
        return (previous == True) & (green == False)
    return (previous == False) & (green == True)


def _supertrend_cross_label(mode: str) -> str:
    return "Supertrend green to red" if str(mode).strip().lower() == "green_to_red" else "Supertrend red to green"


def screen_with_controls(
    *,
    db_path: str,
    tickers: list[str],
    latest_market_date: object | None,
    filters: object | None = None,
    metadata_map: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    """Scan the selected universe using recent MACD/RSI/StochRSI event controls."""
    normalized_filters = normalize_screen_filters(filters)
    lookback_days = int(normalized_filters["lookback_days"])
    relationship_warmup_days = 0
    if bool(normalized_filters["ema_relationship_enabled"]):
        # History is calendar-day based while EMA periods are trading bars.
        # Five calendar days per slow-EMA period gives the EMA enough warm-up
        # data even for long periods and avoids relying on unstable startup values.
        relationship_warmup_days = (
            int(normalized_filters["ema_relationship_slow"]) * 5
            + 5
        )
    history, indicator_cache_hit = load_recent_indicator_history(
        db_path,
        tickers,
        latest_market_date=latest_market_date,
        history_days=max(
            DEFAULT_HISTORY_DAYS,
            lookback_days + 120,
            relationship_warmup_days + lookback_days,
        ),
    )
    metadata_map = metadata_map or {}
    if history.empty:
        return {
            "matches": [],
            "errors": [],
            "total_errors": 0,
            "total_candidates": 0,
            "filters": normalized_filters,
        }

    matches: list[dict[str, object]] = []
    candidate_pool: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []

    grouped = {
        str(ticker).upper(): group.copy()
        for ticker, group in history.groupby("ticker", sort=False)
    }
    requested_tickers = [str(ticker).upper() for ticker in tickers if str(ticker).strip()]

    for ticker in requested_tickers:
        frame = grouped.get(ticker)
        if frame is None or frame.empty:
            continue
        try:
            frame = frame.sort_values("date").reset_index(drop=True)
            close = pd.to_numeric(frame["close"], errors="coerce")
            volume = pd.to_numeric(frame["volume"], errors="coerce").fillna(0.0)
            dates = pd.to_datetime(frame["date"], errors="coerce")
            if len(frame) < 40 or close.isna().all() or dates.isna().all():
                continue

            rsi = pd.to_numeric(frame["rsi"], errors="coerce")
            macd = pd.to_numeric(frame["macd"], errors="coerce")
            macd_signal = pd.to_numeric(frame["macd_signal"], errors="coerce")
            stoch_k = pd.to_numeric(frame["stoch_k"], errors="coerce")

            current_close = _finite_or_none(close.iloc[-1])
            previous_close = (
                _finite_or_none(close.iloc[-2]) if len(close) > 1 else current_close
            )
            current_rsi = _finite_or_none(rsi.iloc[-1])
            avg_volume_20 = _finite_or_none(volume.tail(20).mean()) if len(volume) else 0.0
            if current_close is None or current_rsi is None:
                continue
            if avg_volume_20 is None:
                avg_volume_20 = 0.0

            volume_range = normalized_filters["volume_range"]
            volume_matches = float(volume_range["min"]) <= avg_volume_20 <= float(volume_range["max"])

            slope_lookback = int(normalized_filters["ema_slope_lookback"])
            slope_tolerance = float(normalized_filters["ema_slope_flat_tolerance"])
            ema_slope_states = {
                period: _ema_slope_state(
                    close,
                    period=period,
                    lookback=slope_lookback,
                    flat_tolerance=slope_tolerance,
                )
                for period in (20, 50, 200)
            }
            slope_matches = not any(
                normalized_filters[f"ema_slope_{period}"] not in {"any", ema_slope_states[period]}
                for period in (20, 50, 200)
            )

            macd_mode = str(normalized_filters["macd_cross_mode"])
            macd_enabled = bool(normalized_filters["macd_event_enabled"])
            rsi_mode = str(normalized_filters["rsi_cross_mode"])
            rsi_enabled = bool(normalized_filters["rsi_event_enabled"])
            rsi_level = float(normalized_filters["rsi_cross_value"])
            stoch_mode = str(normalized_filters["stoch_cross_mode"])
            stoch_region = str(normalized_filters["stoch_cross_region"])
            stoch_enabled = bool(normalized_filters["stoch_event_enabled"])
            stoch_level = float(normalized_filters["stoch_cross_value"])
            supertrend_enabled = bool(normalized_filters["supertrend_event_enabled"])
            supertrend_mode = str(normalized_filters["supertrend_cross_mode"])
            macd_age = _latest_event_age_days(
                _macd_cross_mask(macd, macd_signal, mode=macd_mode),
                dates,
                lookback_days=lookback_days,
            )
            rsi_age = _latest_event_age_days(
                _rsi_cross_mask(rsi, level=rsi_level, mode=rsi_mode),
                dates,
                lookback_days=lookback_days,
            )
            stoch_d = pd.to_numeric(frame["stoch_d"], errors="coerce")
            stoch_age = _latest_event_age_days(
                _stoch_cross_mask(
                    stoch_k,
                    stoch_d,
                    level=stoch_level,
                    mode=stoch_mode,
                    region=stoch_region,
                ),
                dates,
                lookback_days=lookback_days,
            )
            chart_ta = normalized_filters.get("chart_ta") if isinstance(normalized_filters.get("chart_ta"), dict) else {}
            st_period = _coerce_int(chart_ta.get("supertrend_period"), 10, minimum=2, maximum=100)
            st_multiplier = _coerce_float(chart_ta.get("supertrend_multiplier"), 3.0, minimum=0.5, maximum=10.0)
            st_high = pd.to_numeric(frame["high"] if "high" in frame else close, errors="coerce")
            st_low = pd.to_numeric(frame["low"] if "low" in frame else close, errors="coerce")
            st_line, _st_upper, st_lower = calculate_supertrend(
                pd.DataFrame({"high": st_high, "low": st_low, "close": close}),
                period=st_period,
                multiplier=st_multiplier,
            )
            supertrend_green = st_line.eq(st_lower).where(st_line.notna())
            supertrend_age = _latest_event_age_days(
                _supertrend_cross_mask(supertrend_green, mode=supertrend_mode),
                dates,
                lookback_days=lookback_days,
            )
            ema_relationship_enabled = bool(normalized_filters["ema_relationship_enabled"])
            ema_fast_period = int(normalized_filters["ema_relationship_fast"])
            ema_slow_period = int(normalized_filters["ema_relationship_slow"])
            ema_relationship_mask, ema_relationship_states, ema_divergence = _ema_cross_event_mask(
                close,
                fast_period=ema_fast_period,
                slow_period=ema_slow_period,
                divergence_allowance=float(normalized_filters["ema_relationship_allowance"]),
                slope_direction=str(normalized_filters["ema_relationship_slope"]),
            )
            ema_relationship_age = _latest_event_age_days(
                ema_relationship_mask, dates, lookback_days=lookback_days
            )
            ema_relationship_state = str(ema_relationship_states.iloc[-1])
            ema_relationship_is_diverging = bool(ema_divergence.iloc[-1])

            metadata = metadata_map.get(ticker, {})
            change_pct = (
                ((current_close / previous_close) - 1.0) * 100.0
                if previous_close
                else 0.0
            )
            candidate_pool.append(
                {
                    "ticker": ticker,
                    "name": str(metadata.get("name") or ticker).strip() or ticker,
                    "close": round(current_close, 4),
                    "volume": int(float(volume.iloc[-1] or 0.0)),
                    "recent_avg_volume": round(avg_volume_20, 2),
                    "change_pct": round(change_pct, 2),
                    "rsi": round(current_rsi, 2),
                    "ema_slope_20_state": ema_slope_states[20],
                    "ema_slope_50_state": ema_slope_states[50],
                    "ema_slope_200_state": ema_slope_states[200],
                    "macd_cross_days_ago": macd_age,
                    "rsi_cross_days_ago": rsi_age,
                    "stoch_cross_days_ago": stoch_age,
                    "supertrend_cross_days_ago": supertrend_age,
                    "ema_relationship_state": ema_relationship_state,
                    "ema_relationship_is_diverging": ema_relationship_is_diverging,
                    "ema_relationship_days_ago": ema_relationship_age,
                    "volume_matches": volume_matches,
                    "slope_matches": slope_matches,
                }
            )

            if not volume_matches or not slope_matches:
                continue

            if macd_enabled and not _event_matches_target(
                macd_age,
                int(normalized_filters["macd_event_age"]),
            ):
                continue
            if rsi_enabled and not _event_matches_target(
                rsi_age,
                int(normalized_filters["rsi_event_age"]),
            ):
                continue
            if stoch_enabled and not _event_matches_target(
                stoch_age,
                int(normalized_filters["stoch_event_age"]),
            ):
                continue
            if supertrend_enabled and not _event_matches_target(
                supertrend_age,
                int(normalized_filters["supertrend_event_age"]),
            ):
                continue
            if ema_relationship_enabled and not _event_matches_target(
                ema_relationship_age,
                int(normalized_filters["ema_relationship_age"]),
            ):
                continue
            if ema_relationship_enabled and not ema_relationship_is_diverging:
                continue

            event_pairs: list[tuple[str, int]] = []
            if rsi_enabled:
                event_pairs.append(("RSI", int(rsi_age or 0)))
            if macd_enabled:
                event_pairs.append(("MACD", int(macd_age or 0)))
            if stoch_enabled:
                event_pairs.append(("StochRSI", int(stoch_age or 0)))
            if supertrend_enabled:
                event_pairs.append(("Supertrend", int(supertrend_age or 0)))
            if ema_relationship_enabled:
                event_pairs.append((
                    f"EMA {ema_fast_period}/{ema_slow_period} cross",
                    int(ema_relationship_age or 0),
                ))
            ordered_events = sorted(event_pairs, key=lambda item: item[1], reverse=True)
            sequence = " -> ".join(label for label, _ in ordered_events) or "Volume only"
            total_age = sum(age for _, age in event_pairs)
            score = round(
                max(0.0, (lookback_days * 3.0) - total_age)
                + min(18.0, math.log10(max(avg_volume_20, 1.0)) * 3.0)
                + (
                    max(0.0, 18.0 - abs(current_rsi - rsi_level))
                    if rsi_enabled
                    else 0.0
                ),
                2,
            )
            matches.append(
                {
                    "ticker": ticker,
                    "name": str(metadata.get("name") or ticker).strip() or ticker,
                    "close": round(current_close, 4),
                    "volume": int(float(volume.iloc[-1] or 0.0)),
                    "recent_avg_volume": round(avg_volume_20, 2),
                    "change_pct": round(change_pct, 2),
                    "rsi": round(current_rsi, 2),
                    "macd_event_enabled": macd_enabled,
                    "rsi_event_enabled": rsi_enabled,
                    "stoch_event_enabled": stoch_enabled,
                    "rsi_cross_mode": rsi_mode,
                    "rsi_cross_value": rsi_level,
                    "stoch_cross_mode": stoch_mode,
                    "stoch_cross_value": stoch_level,
                    "stoch_cross_region": stoch_region,
                    "supertrend_event_enabled": supertrend_enabled,
                    "supertrend_cross_mode": supertrend_mode,
                    "supertrend_cross_days_ago": supertrend_age,
                    "ema_relationship_enabled": ema_relationship_enabled,
                    "ema_relationship_fast": ema_fast_period,
                    "ema_relationship_slow": ema_slow_period,
                    "ema_relationship_days_ago": ema_relationship_age,
                    "ema_relationship_state": ema_relationship_state,
                    "macd_cross_mode": macd_mode,
                    "macd_cross_days_ago": macd_age,
                    "rsi_cross_days_ago": rsi_age,
                    "stoch_cross_days_ago": stoch_age,
                    "event_sequence": sequence,
                    "status": "Sequence aligned" if event_pairs else "Volume aligned",
                    "score": score,
                    "reasons": (
                        [f"RSI now {current_rsi:.1f}"]
                        + [f"Avg volume 20d {avg_volume_20:,.0f}"]
                        + (
                            [f"{_rsi_cross_label(rsi_mode, rsi_level)} {int(rsi_age or 0)}d ago"]
                            if rsi_enabled
                            else []
                        )
                        + (
                            [f"{_macd_cross_label(macd_mode)} {int(macd_age or 0)}d ago"]
                            if macd_enabled
                            else []
                        )
                        + (
                            [f"{_stoch_cross_label(stoch_mode, stoch_level, stoch_region)} {int(stoch_age or 0)}d ago"]
                            if stoch_enabled
                            else []
                        )
                        + (
                            [f"{_supertrend_cross_label(supertrend_mode)} {int(supertrend_age or 0)}d ago"]
                            if supertrend_enabled
                            else []
                        )
                        + (
                            [f"EMA {ema_fast_period}/{ema_slow_period} cross {int(ema_relationship_age or 0)}d ago"]
                            if ema_relationship_enabled
                            else []
                        )
                        + [f"Sequence {sequence}"]
                    ),
                }
            )
        except Exception as exc:
            errors.append({"ticker": ticker, "error": str(exc)})

    matches.sort(
        key=lambda item: (
            -float(item.get("score") or 0.0),
            int(item.get("macd_cross_days_ago") or 9999),
            int(item.get("rsi_cross_days_ago") or 9999),
            int(item.get("stoch_cross_days_ago") or 9999),
            -float(item.get("recent_avg_volume") or 0.0),
            str(item.get("ticker") or ""),
        )
    )
    return {
        "matches": matches,
        "errors": errors,
        "total_errors": len(errors),
        "total_candidates": len(matches),
        "candidate_pool": candidate_pool,
        "filters": normalized_filters,
        "indicator_cache_hit": indicator_cache_hit,
    }
