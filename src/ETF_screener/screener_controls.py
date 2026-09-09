"""Control-based screener utilities for recent technical-event scans."""

from __future__ import annotations

import math
import os
import hashlib
import re
import logging
import pickle  # nosec B403
import sqlite3
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from threading import Lock
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable

import pandas as pd

from ETF_screener.cache_policy import cache_is_fresh, trim_cache
from ETF_screener.config_loader import get_paths
from ETF_screener.indicators import (
    calculate_macd,
    calculate_rsi,
    calculate_stoch_rsi,
    calculate_supertrend,
)

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 30
MIN_EVENT_AGE_DAYS = 0
DEFAULT_HISTORY_DAYS = 365
# EMA periods are expressed in trading bars, while the history query uses
# calendar days. Four calendar days per period provides roughly three times
# the trading-bar period for EMA 200 without retaining open-ended history.
INDICATOR_WARMUP_CALENDAR_DAYS_PER_PERIOD = 4
MIN_INDICATOR_WARMUP_DAYS = 120
MAX_SCREEN_DATA_STALENESS_DAYS = 3
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
DEFAULT_EMA_RELATIONSHIP_CROSS_MODE = "cross_up"
DEFAULT_EMA_RELATIONSHIP_ALLOWANCE = 0.1
DEFAULT_VOLUME_SPIKE_PERIOD = 20
DEFAULT_VOLUME_SPIKE_MULTIPLIER = 2.0
DEFAULT_HA_EMA_VOLUME_EMA1_PERIOD = 20
DEFAULT_HA_EMA_VOLUME_EMA1_SOURCE = "close"
DEFAULT_HA_EMA_VOLUME_EMA2_PERIOD = 50
DEFAULT_HA_EMA_VOLUME_EMA2_SOURCE = "close"
DEFAULT_HA_EMA_VOLUME_START_FIELD = "open"
DEFAULT_HA_EMA_VOLUME_START_LINE = "ema2"
DEFAULT_HA_EMA_VOLUME_START_RELATION = "above"
DEFAULT_HA_EMA_VOLUME_END_FIELD = "close"
DEFAULT_HA_EMA_VOLUME_END_LINE = "ema1"
DEFAULT_HA_EMA_VOLUME_END_RELATION = "above"
DEFAULT_HA_EMA_VOLUME_CONDITIONS = [
    {"field": "open", "enabled": False, "zone": "above_ema1"},
    {"field": "high", "enabled": False, "zone": "above_ema1"},
    {"field": "low", "enabled": False, "zone": "below_ema2"},
    {"field": "close", "enabled": True, "zone": "above_ema1"},
]
DEFAULT_HA_EMA_VOLUME_PERIOD = 20
DEFAULT_HA_EMA_VOLUME_MULTIPLIER = 2.5
DEFAULT_HA_EMA_VOLUME_EVENT_AGE = 30
DEFAULT_HA_EMA_VOLUME_CANDLE_COLOR = "green"
DEFAULT_PRICE_EMA_PERIOD = 20
DEFAULT_PRICE_EMA_SOURCE = "close"
DEFAULT_PRICE_EMA_CROSS_MODE = "cross_up"
DEFAULT_PRICE_EMA_EVENT_AGE = 30
DEFAULT_EMA_FLATTEN_PERIOD = 20
DEFAULT_EMA_FLATTEN_LOOKBACK = 5
DEFAULT_EMA_FLATTEN_TOLERANCE = 0.1
DEFAULT_EMA_FLATTEN_MODE = "either"
DEFAULT_EMA_FLATTEN_EVENT_AGE = 30
DEFAULT_TIMELINE_ORDER = ["rsi", "macd", "stoch", "supertrend", "ema_relationship"]
TIMELINE_RULE_KEYS = [
    *DEFAULT_TIMELINE_ORDER,
    "volume_spike",
    "price_ema",
    "ema_flatten",
    "ha_ema_volume",
]
INDICATOR_HISTORY_CACHE_MAXSIZE = 6
INDICATOR_HISTORY_DISK_CACHE = os.path.join(
    get_paths()["data"]["cache"], "screen-indicators"
)

DEFAULT_SCREEN_FILTERS: dict[str, Any] = {
    "lookback_days": DEFAULT_LOOKBACK_DAYS,
    "volume_range": {"min": 0.0, "max": DEFAULT_VOLUME_MAX},
    "macd_event_enabled": True,
    "rsi_event_enabled": True,
    "rsi_filter_enabled": False,
    "rsi_filter_min": DEFAULT_RSI_CROSS_VALUE,
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
    "ema_relationship_fast_slope": DEFAULT_EMA_RELATIONSHIP_SLOPE,
    "ema_relationship_slow_slope": DEFAULT_EMA_RELATIONSHIP_SLOPE,
    "ema_relationship_cross_mode": DEFAULT_EMA_RELATIONSHIP_CROSS_MODE,
    "ema_relationship_allowance": DEFAULT_EMA_RELATIONSHIP_ALLOWANCE,
    "ema_relationship_age": 30,
    "price_ema_event_enabled": False,
    "price_ema_period": DEFAULT_PRICE_EMA_PERIOD,
    "price_ema_source": DEFAULT_PRICE_EMA_SOURCE,
    "price_ema_sources": [DEFAULT_PRICE_EMA_SOURCE],
    "price_ema_cross_mode": DEFAULT_PRICE_EMA_CROSS_MODE,
    "price_ema_event_age": DEFAULT_PRICE_EMA_EVENT_AGE,
    "ema_flatten_enabled": False,
    "ema_flatten_period": DEFAULT_EMA_FLATTEN_PERIOD,
    "ema_flatten_lookback": DEFAULT_EMA_FLATTEN_LOOKBACK,
    "ema_flatten_tolerance": DEFAULT_EMA_FLATTEN_TOLERANCE,
    "ema_flatten_mode": DEFAULT_EMA_FLATTEN_MODE,
    "ema_flatten_event_age": DEFAULT_EMA_FLATTEN_EVENT_AGE,
    "volume_spike_enabled": False,
    "volume_spike_period": DEFAULT_VOLUME_SPIKE_PERIOD,
    "volume_spike_multiplier": DEFAULT_VOLUME_SPIKE_MULTIPLIER,
    "volume_spike_age": 5,
    "ha_ema_volume_enabled": False,
    "ha_ema_volume_ema1_period": DEFAULT_HA_EMA_VOLUME_EMA1_PERIOD,
    "ha_ema_volume_ema1_source": DEFAULT_HA_EMA_VOLUME_EMA1_SOURCE,
    "ha_ema_volume_ema2_period": DEFAULT_HA_EMA_VOLUME_EMA2_PERIOD,
    "ha_ema_volume_ema2_source": DEFAULT_HA_EMA_VOLUME_EMA2_SOURCE,
    "ha_ema_volume_start_field": DEFAULT_HA_EMA_VOLUME_START_FIELD,
    "ha_ema_volume_start_line": DEFAULT_HA_EMA_VOLUME_START_LINE,
    "ha_ema_volume_start_relation": DEFAULT_HA_EMA_VOLUME_START_RELATION,
    "ha_ema_volume_end_field": DEFAULT_HA_EMA_VOLUME_END_FIELD,
    "ha_ema_volume_end_line": DEFAULT_HA_EMA_VOLUME_END_LINE,
    "ha_ema_volume_end_relation": DEFAULT_HA_EMA_VOLUME_END_RELATION,
    "ha_ema_volume_conditions": [
        dict(item) for item in DEFAULT_HA_EMA_VOLUME_CONDITIONS
    ],
    "ha_ema_volume_candle_color": DEFAULT_HA_EMA_VOLUME_CANDLE_COLOR,
    "ha_ema_volume_period": DEFAULT_HA_EMA_VOLUME_PERIOD,
    "ha_ema_volume_multiplier": DEFAULT_HA_EMA_VOLUME_MULTIPLIER,
    "ha_ema_volume_event_age": DEFAULT_HA_EMA_VOLUME_EVENT_AGE,
    "ema_slope_20": "any",
    "ema_slope_50": "any",
    "ema_slope_200": "any",
    "ema_slope_lookback": 5,
    "ema_slope_flat_tolerance": 0.1,
    "ema_slope_period_1": 20,
    "ema_slope_period_2": 50,
    "ema_slope_period_3": 200,
    "ema_slope_1": "any",
    "ema_slope_2": "any",
    "ema_slope_3": "any",
    "timeline_order": list(DEFAULT_TIMELINE_ORDER),
}

_INDICATOR_HISTORY_CACHE: OrderedDict[
    tuple[str, str, int, int, tuple[str, ...]],
    pd.DataFrame,
] = OrderedDict()
_INDICATOR_HISTORY_CACHE_LOCK = Lock()


def _coerce_float(
    value: object, default: float, *, minimum: float, maximum: float
) -> float:
    try:
        numeric = float(str(value))
    except (TypeError, ValueError):
        numeric = default
    if not math.isfinite(numeric):
        numeric = default
    return max(minimum, min(maximum, numeric))


def _finite_or_none(value: object) -> float | None:
    try:
        numeric = float(str(value))
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _coerce_int(value: object, default: int, *, minimum: int, maximum: int) -> int:
    try:
        numeric = int(float(str(value)))
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
    raw: dict[str, Any] = payload if isinstance(payload, dict) else {}
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
    return _coerce_int(
        value, default, minimum=MIN_EVENT_AGE_DAYS, maximum=lookback_days
    )


def _legacy_window_midpoint(
    payload: object, *, lookback_days: int, default: int
) -> int:
    raw: dict[str, Any] = payload if isinstance(payload, dict) else {}
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


@dataclass(frozen=True)
class RsiEvent:
    """One RSI threshold crossing in a screen timeline."""

    level: float
    mode: str
    max_age_days: int
    event_id: str | None = None

    @classmethod
    def from_payload(
        cls,
        payload: object,
        *,
        lookback_days: int,
        default_age: int,
    ) -> "RsiEvent":
        """Build an event from either the API shape or the legacy UI shape."""
        raw = payload if isinstance(payload, dict) else {}
        mode = (
            str(
                raw.get("rsi_cross_mode", raw.get("cross_mode", DEFAULT_RSI_CROSS_MODE))
                or DEFAULT_RSI_CROSS_MODE
            )
            .strip()
            .lower()
        )
        if mode not in {"cross_up", "cross_down"}:
            mode = DEFAULT_RSI_CROSS_MODE

        age = _normalize_event_age(
            raw.get("rsi_event_age", raw.get("event_age")),
            lookback_days=lookback_days,
            default=_legacy_window_midpoint(
                raw.get("rsi_cross_window"),
                lookback_days=lookback_days,
                default=default_age,
            ),
        )
        level = _coerce_float(
            raw.get("rsi_cross_value", raw.get("cross_value")),
            DEFAULT_RSI_CROSS_VALUE,
            minimum=0.0,
            maximum=100.0,
        )
        raw_id = raw.get("rsi_event_id") or raw.get("id")
        return cls(
            level=level,
            mode=mode,
            max_age_days=age,
            event_id=str(raw_id) if raw_id else None,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RsiEvent":
        """Build an event from an already-normalized filter dictionary."""
        return cls(
            level=float(payload["rsi_cross_value"]),
            mode=str(payload["rsi_cross_mode"]),
            max_age_days=int(payload["rsi_event_age"]),
            event_id=(
                str(payload["rsi_event_id"]) if payload.get("rsi_event_id") else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event at the API and persistence boundary."""
        result: dict[str, Any] = {
            "rsi_cross_value": self.level,
            "rsi_cross_mode": self.mode,
            "rsi_event_age": self.max_age_days,
        }
        if self.event_id:
            result["rsi_event_id"] = self.event_id
        return result


@dataclass(frozen=True)
class RsiEventSequence:
    """Chronologically matchable collection of distinct RSI events."""

    events: tuple[RsiEvent, ...]

    def find_ages(
        self, rsi: pd.Series, dates: pd.Series, *, lookback_days: int
    ) -> list[int] | None:
        """Return event ages, or ``None`` when the configured sequence is absent."""
        if not self.events:
            return None

        latest_date = pd.Timestamp(dates.iloc[-1]).normalize()
        cutoff = latest_date - pd.Timedelta(days=lookback_days)
        candidates: list[list[pd.Timestamp]] = []
        for event in self.events:
            mask = _rsi_cross_mask(rsi, level=event.level, mode=event.mode).fillna(
                False
            )
            event_dates = pd.to_datetime(
                dates[mask & (dates >= cutoff)], errors="coerce"
            )
            minimum_date = latest_date - pd.Timedelta(days=event.max_age_days)
            candidates.append(
                [
                    event_date.normalize()
                    for event_date in event_dates
                    if event_date.normalize() >= minimum_date
                ]
            )

        ages: list[int] = []
        previous_date: pd.Timestamp | None = None
        for event_dates in candidates:
            candidate_date = next(
                (
                    event_date
                    for event_date in event_dates
                    if previous_date is None or event_date > previous_date
                ),
                None,
            )
            if candidate_date is None:
                return None
            ages.append(int((latest_date - candidate_date).days))
            previous_date = candidate_date
        return ages


def _normalize_ha_ema_volume_conditions(
    raw: dict[str, Any],
) -> list[dict[str, Any]]:
    """Normalize the four optional HA OHLC zone conditions."""
    import json

    value = raw.get("ha_ema_volume_conditions")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            value = None
    by_field = {
        str(item.get("field", "")).lower(): item
        for item in (value if isinstance(value, list) else [])
        if isinstance(item, dict)
    }
    conditions = []
    for default in DEFAULT_HA_EMA_VOLUME_CONDITIONS:
        field = str(default["field"])
        item = by_field.get(field, default)
        zone = str(item.get("zone", default["zone"])).lower()
        if zone not in {"above_ema1", "between_ema1_ema2", "below_ema2"}:
            zone = str(default["zone"])
        conditions.append(
            {
                "field": field,
                "enabled": _coerce_bool(item.get("enabled"), bool(default["enabled"])),
                "zone": zone,
            }
        )
    return conditions


def _validate_ha_ema_volume_conditions(
    conditions: list[dict[str, Any]],
) -> list[str]:
    """Return contradictions implied by OHLC ordering and selected zones."""
    ranks = {"below_ema2": 0, "between_ema1_ema2": 1, "above_ema1": 2}
    active = {
        item["field"]: ranks[item["zone"]] for item in conditions if item.get("enabled")
    }
    contradictions = []
    ordered_pairs = [
        ("low", "open"),
        ("low", "close"),
        ("low", "high"),
        ("open", "high"),
        ("close", "high"),
    ]
    for lower_field, upper_field in ordered_pairs:
        if (
            lower_field in active
            and upper_field in active
            and active[lower_field] > active[upper_field]
        ):
            contradictions.append(
                f"{lower_field.title()} cannot be in a higher zone than {upper_field.title()}."
            )
    return contradictions


def normalize_screen_filters(payload: object | None = None) -> dict[str, Any]:
    """Return a stable control payload for the recent-event screener."""
    raw: dict[str, Any] = payload if isinstance(payload, dict) else {}
    timeline_source: list[Any] = (
        list(raw["timeline_order"])
        if isinstance(raw.get("timeline_order"), list)
        else list(DEFAULT_TIMELINE_ORDER)
    )
    lookback_days = _coerce_int(
        raw.get("lookback_days"),
        DEFAULT_LOOKBACK_DAYS,
        minimum=30,
        maximum=365,
    )
    defaults = DEFAULT_SCREEN_FILTERS
    raw_rsi_events = raw.get("rsi_events")
    if not isinstance(raw_rsi_events, list) or not raw_rsi_events:
        raw_rsi_events = [raw]
    normalized_rsi_events: list[dict[str, Any]] = []
    for event in raw_rsi_events[:3]:
        event_payload = event if isinstance(event, dict) else raw
        normalized_rsi_events.append(
            RsiEvent.from_payload(
                event_payload,
                lookback_days=lookback_days,
                default_age=int(DEFAULT_SCREEN_FILTERS["rsi_event_age"]),
            ).to_dict()
        )

    raw_price_ema_sources = raw.get("price_ema_sources")
    if isinstance(raw_price_ema_sources, list):
        selected_price_ema_sources = [
            str(source).strip().lower() for source in raw_price_ema_sources
        ]
    else:
        selected_price_ema_sources = [
            str(raw.get("price_ema_source") or DEFAULT_PRICE_EMA_SOURCE).strip().lower()
        ]
    selected_price_ema_sources = list(
        dict.fromkeys(
            source
            for source in selected_price_ema_sources
            if source in {"open", "high", "low", "close"}
        )
    ) or [DEFAULT_PRICE_EMA_SOURCE]
    raw_price_ema_events = raw.get("price_ema_events")
    if not isinstance(raw_price_ema_events, list) or not raw_price_ema_events:
        raw_price_ema_events = [
            {**raw, "price_ema_source": source} for source in selected_price_ema_sources
        ]
    normalized_price_ema_events: list[dict[str, Any]] = []
    for index, event in enumerate(raw_price_ema_events[:3]):
        payload = event if isinstance(event, dict) else {}
        normalized_price_ema_events.append(
            {
                "price_ema_source": str(
                    payload.get("price_ema_source") or DEFAULT_PRICE_EMA_SOURCE
                )
                .strip()
                .lower(),
                "price_ema_period": _coerce_int(
                    payload.get("price_ema_period"),
                    DEFAULT_PRICE_EMA_PERIOD,
                    minimum=2,
                    maximum=500,
                ),
                "price_ema_cross_mode": str(
                    payload.get("price_ema_cross_mode") or DEFAULT_PRICE_EMA_CROSS_MODE
                )
                .strip()
                .lower(),
                "price_ema_event_age": _normalize_event_age(
                    payload.get("price_ema_event_age"),
                    lookback_days=lookback_days,
                    default=DEFAULT_PRICE_EMA_EVENT_AGE,
                ),
                "price_ema_event_id": str(
                    payload.get("price_ema_event_id")
                    or payload.get("id")
                    or ("price_ema" if index == 0 else f"price_ema_{index + 1}")
                ),
            }
        )

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
        "rsi_filter_enabled": _coerce_bool(raw.get("rsi_filter_enabled"), False),
        "rsi_filter_min": _coerce_float(
            raw.get("rsi_filter_min"),
            DEFAULT_RSI_CROSS_VALUE,
            minimum=0.0,
            maximum=100.0,
        ),
        "stoch_event_enabled": _coerce_bool(
            raw.get("stoch_event_enabled"),
            True,
        ),
        "rsi_cross_value": float(normalized_rsi_events[0]["rsi_cross_value"]),
        "rsi_cross_mode": str(normalized_rsi_events[0]["rsi_cross_mode"]),
        "rsi_events": normalized_rsi_events,
        "stoch_cross_value": _coerce_float(
            raw.get("stoch_cross_value"),
            DEFAULT_STOCH_CROSS_VALUE,
            minimum=0.0,
            maximum=100.0,
        ),
        "stoch_cross_mode": str(raw.get("stoch_cross_mode") or DEFAULT_STOCH_CROSS_MODE)
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
        "rsi_event_age": int(normalized_rsi_events[0]["rsi_event_age"]),
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
        "ema_relationship_enabled": _coerce_bool(
            raw.get("ema_relationship_enabled"), DEFAULT_EMA_RELATIONSHIP_ENABLED
        ),
        "ema_relationship_fast": _coerce_int(
            raw.get("ema_relationship_fast"),
            DEFAULT_EMA_RELATIONSHIP_FAST,
            minimum=2,
            maximum=200,
        ),
        "ema_relationship_slow": _coerce_int(
            raw.get("ema_relationship_slow"),
            DEFAULT_EMA_RELATIONSHIP_SLOW,
            minimum=3,
            maximum=400,
        ),
        "ema_relationship_slope": str(
            raw.get("ema_relationship_slope") or DEFAULT_EMA_RELATIONSHIP_SLOPE
        )
        .strip()
        .lower(),
        "ema_relationship_fast_slope": str(
            raw.get("ema_relationship_fast_slope")
            or raw.get("ema_relationship_slope")
            or DEFAULT_EMA_RELATIONSHIP_SLOPE
        )
        .strip()
        .lower(),
        "ema_relationship_slow_slope": str(
            raw.get("ema_relationship_slow_slope")
            or raw.get("ema_relationship_slope")
            or DEFAULT_EMA_RELATIONSHIP_SLOPE
        )
        .strip()
        .lower(),
        "ema_relationship_cross_mode": str(
            raw.get("ema_relationship_cross_mode")
            or DEFAULT_EMA_RELATIONSHIP_CROSS_MODE
        )
        .strip()
        .lower(),
        "ema_relationship_allowance": _coerce_float(
            raw.get("ema_relationship_allowance"),
            DEFAULT_EMA_RELATIONSHIP_ALLOWANCE,
            minimum=0.0,
            maximum=5.0,
        ),
        "ema_relationship_age": _normalize_event_age(
            raw.get("ema_relationship_age"), lookback_days=lookback_days, default=30
        ),
        "price_ema_event_enabled": _coerce_bool(
            raw.get("price_ema_event_enabled"), False
        ),
        "price_ema_period": _coerce_int(
            raw.get("price_ema_period"),
            DEFAULT_PRICE_EMA_PERIOD,
            minimum=2,
            maximum=500,
        ),
        "price_ema_source": str(raw.get("price_ema_source") or DEFAULT_PRICE_EMA_SOURCE)
        .strip()
        .lower(),
        "price_ema_sources": selected_price_ema_sources,
        "price_ema_cross_mode": str(
            raw.get("price_ema_cross_mode") or DEFAULT_PRICE_EMA_CROSS_MODE
        )
        .strip()
        .lower(),
        "price_ema_event_age": _normalize_event_age(
            raw.get("price_ema_event_age"),
            lookback_days=lookback_days,
            default=DEFAULT_PRICE_EMA_EVENT_AGE,
        ),
        "price_ema_events": normalized_price_ema_events,
        "ema_flatten_enabled": _coerce_bool(raw.get("ema_flatten_enabled"), False),
        "ema_flatten_period": _coerce_int(
            raw.get("ema_flatten_period"),
            DEFAULT_EMA_FLATTEN_PERIOD,
            minimum=2,
            maximum=500,
        ),
        "ema_flatten_lookback": _coerce_int(
            raw.get("ema_flatten_lookback"),
            DEFAULT_EMA_FLATTEN_LOOKBACK,
            minimum=1,
            maximum=30,
        ),
        "ema_flatten_tolerance": _coerce_float(
            raw.get("ema_flatten_tolerance"),
            DEFAULT_EMA_FLATTEN_TOLERANCE,
            minimum=0.0,
            maximum=5.0,
        ),
        "ema_flatten_mode": str(raw.get("ema_flatten_mode") or DEFAULT_EMA_FLATTEN_MODE)
        .strip()
        .lower(),
        "ema_flatten_event_age": _normalize_event_age(
            raw.get("ema_flatten_event_age"),
            lookback_days=lookback_days,
            default=DEFAULT_EMA_FLATTEN_EVENT_AGE,
        ),
        "volume_spike_enabled": _coerce_bool(raw.get("volume_spike_enabled"), False),
        "volume_spike_period": _coerce_int(
            raw.get("volume_spike_period"),
            DEFAULT_VOLUME_SPIKE_PERIOD,
            minimum=2,
            maximum=100,
        ),
        "volume_spike_multiplier": _coerce_float(
            raw.get("volume_spike_multiplier"),
            DEFAULT_VOLUME_SPIKE_MULTIPLIER,
            minimum=1.1,
            maximum=10.0,
        ),
        "volume_spike_age": _normalize_event_age(
            raw.get("volume_spike_age"), lookback_days=lookback_days, default=5
        ),
        "ha_ema_volume_enabled": _coerce_bool(raw.get("ha_ema_volume_enabled"), False),
        "ha_ema_volume_ema1_period": _coerce_int(
            raw.get("ha_ema_volume_ema1_period"),
            DEFAULT_HA_EMA_VOLUME_EMA1_PERIOD,
            minimum=2,
            maximum=500,
        ),
        "ha_ema_volume_ema1_source": str(
            raw.get("ha_ema_volume_ema1_source") or DEFAULT_HA_EMA_VOLUME_EMA1_SOURCE
        )
        .strip()
        .lower(),
        "ha_ema_volume_ema2_period": _coerce_int(
            raw.get("ha_ema_volume_ema2_period"),
            DEFAULT_HA_EMA_VOLUME_EMA2_PERIOD,
            minimum=2,
            maximum=500,
        ),
        "ha_ema_volume_ema2_source": str(
            raw.get("ha_ema_volume_ema2_source") or DEFAULT_HA_EMA_VOLUME_EMA2_SOURCE
        )
        .strip()
        .lower(),
        "ha_ema_volume_start_field": str(
            raw.get("ha_ema_volume_start_field") or DEFAULT_HA_EMA_VOLUME_START_FIELD
        )
        .strip()
        .lower(),
        "ha_ema_volume_start_line": str(
            raw.get("ha_ema_volume_start_line") or DEFAULT_HA_EMA_VOLUME_START_LINE
        )
        .strip()
        .lower(),
        "ha_ema_volume_start_relation": str(
            raw.get("ha_ema_volume_start_relation")
            or DEFAULT_HA_EMA_VOLUME_START_RELATION
        )
        .strip()
        .lower(),
        "ha_ema_volume_end_field": str(
            raw.get("ha_ema_volume_end_field") or DEFAULT_HA_EMA_VOLUME_END_FIELD
        )
        .strip()
        .lower(),
        "ha_ema_volume_end_line": str(
            raw.get("ha_ema_volume_end_line") or DEFAULT_HA_EMA_VOLUME_END_LINE
        )
        .strip()
        .lower(),
        "ha_ema_volume_end_relation": str(
            raw.get("ha_ema_volume_end_relation") or DEFAULT_HA_EMA_VOLUME_END_RELATION
        )
        .strip()
        .lower(),
        "ha_ema_volume_conditions": _normalize_ha_ema_volume_conditions(raw),
        "ha_ema_volume_candle_color": (
            str(
                raw.get("ha_ema_volume_candle_color")
                or DEFAULT_HA_EMA_VOLUME_CANDLE_COLOR
            )
            .strip()
            .lower()
            if str(
                raw.get("ha_ema_volume_candle_color")
                or DEFAULT_HA_EMA_VOLUME_CANDLE_COLOR
            )
            .strip()
            .lower()
            in {"any", "green", "red"}
            else DEFAULT_HA_EMA_VOLUME_CANDLE_COLOR
        ),
        "ha_ema_volume_period": _coerce_int(
            raw.get("ha_ema_volume_period"),
            DEFAULT_HA_EMA_VOLUME_PERIOD,
            minimum=2,
            maximum=100,
        ),
        "ha_ema_volume_multiplier": _coerce_float(
            raw.get("ha_ema_volume_multiplier"),
            DEFAULT_HA_EMA_VOLUME_MULTIPLIER,
            minimum=1.1,
            maximum=10.0,
        ),
        "ha_ema_volume_event_age": _normalize_event_age(
            raw.get("ha_ema_volume_event_age"),
            lookback_days=lookback_days,
            default=DEFAULT_HA_EMA_VOLUME_EVENT_AGE,
        ),
        "ema_slope_20": str(raw.get("ema_slope_20") or "any").strip().lower(),
        "ema_slope_50": str(raw.get("ema_slope_50") or "any").strip().lower(),
        "ema_slope_200": str(raw.get("ema_slope_200") or "any").strip().lower(),
        "ema_slope_lookback": _coerce_int(
            raw.get("ema_slope_lookback"), 5, minimum=1, maximum=30
        ),
        "ema_slope_flat_tolerance": _coerce_float(
            raw.get("ema_slope_flat_tolerance"), 0.1, minimum=0.0, maximum=5.0
        ),
        "ema_slope_period_1": _coerce_int(
            raw.get("ema_slope_period_1"), 20, minimum=2, maximum=500
        ),
        "ema_slope_period_2": _coerce_int(
            raw.get("ema_slope_period_2"), 50, minimum=2, maximum=500
        ),
        "ema_slope_period_3": _coerce_int(
            raw.get("ema_slope_period_3"), 200, minimum=2, maximum=500
        ),
        "ema_slope_1": str(raw.get("ema_slope_1") or raw.get("ema_slope_20") or "any")
        .strip()
        .lower(),
        "ema_slope_2": str(raw.get("ema_slope_2") or raw.get("ema_slope_50") or "any")
        .strip()
        .lower(),
        "ema_slope_3": str(raw.get("ema_slope_3") or raw.get("ema_slope_200") or "any")
        .strip()
        .lower(),
        "timeline_order": [
            key
            for key in timeline_source
            if str(key) in TIMELINE_RULE_KEYS
            or re.fullmatch(
                r"(?:rsi|macd|stoch|supertrend|ema_relationship|price_ema|volume_spike|ema_flatten)_[2-3]",
                str(key),
            )
        ],
    }
    filters["timeline_order"] = list(timeline_source)
    chart_ta: Any = raw.get("chart_ta") if isinstance(raw.get("chart_ta"), dict) else {}
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
    for key in ("ema_relationship_fast_slope", "ema_relationship_slow_slope"):
        if filters[key] not in {"any", "positive", "negative"}:
            filters[key] = DEFAULT_EMA_RELATIONSHIP_SLOPE
    if filters["ema_relationship_cross_mode"] not in {"cross_up", "cross_down"}:
        filters["ema_relationship_cross_mode"] = DEFAULT_EMA_RELATIONSHIP_CROSS_MODE
    if filters["price_ema_cross_mode"] not in {"cross_up", "cross_down"}:
        filters["price_ema_cross_mode"] = DEFAULT_PRICE_EMA_CROSS_MODE
    if filters["price_ema_source"] not in {"open", "high", "low", "close"}:
        filters["price_ema_source"] = DEFAULT_PRICE_EMA_SOURCE
    if filters["ema_flatten_mode"] not in {"top", "bottom", "either"}:
        filters["ema_flatten_mode"] = DEFAULT_EMA_FLATTEN_MODE
    fast_period = _coerce_int(
        filters["ema_relationship_fast"],
        DEFAULT_EMA_RELATIONSHIP_FAST,
        minimum=2,
        maximum=200,
    )
    slow_period = _coerce_int(
        filters["ema_relationship_slow"],
        DEFAULT_EMA_RELATIONSHIP_SLOW,
        minimum=3,
        maximum=400,
    )
    if fast_period >= slow_period:
        filters["ema_relationship_fast"], filters["ema_relationship_slow"] = (
            slow_period,
            fast_period,
        )
    for key in ("ema_slope_20", "ema_slope_50", "ema_slope_200"):
        if filters[key] not in {"any", "positive", "flat", "negative"}:
            filters[key] = "any"
    for key in ("ema_slope_1", "ema_slope_2", "ema_slope_3"):
        if filters[key] not in {"any", "positive", "flat", "negative"}:
            filters[key] = "any"

    return filters


def _required_screen_history_days(filters: dict[str, Any]) -> int:
    """Return the bounded calendar-day history needed by the TA controls."""
    periods: list[int] = [
        14,  # RSI
        26,  # MACD's slow leg
        int(filters.get("volume_spike_period", DEFAULT_VOLUME_SPIKE_PERIOD)),
        int(filters.get("ema_slope_period_1", 20)),
        int(filters.get("ema_slope_period_2", 50)),
        int(filters.get("ema_slope_period_3", 200)),
    ]
    if bool(filters.get("ema_relationship_enabled")):
        periods.extend(
            [
                int(
                    filters.get("ema_relationship_fast", DEFAULT_EMA_RELATIONSHIP_FAST)
                ),
                int(
                    filters.get("ema_relationship_slow", DEFAULT_EMA_RELATIONSHIP_SLOW)
                ),
            ]
        )
    if bool(filters.get("price_ema_event_enabled")):
        periods.append(int(filters.get("price_ema_period", DEFAULT_PRICE_EMA_PERIOD)))
        periods.extend(
            int(event["price_ema_period"])
            for event in filters.get("price_ema_events", [])
            if isinstance(event, dict) and "price_ema_period" in event
        )
    if bool(filters.get("ema_flatten_enabled")):
        periods.append(
            int(filters.get("ema_flatten_period", DEFAULT_EMA_FLATTEN_PERIOD))
        )
    if bool(filters.get("ha_ema_volume_enabled")):
        periods.extend(
            [
                int(
                    filters.get(
                        "ha_ema_volume_ema1_period", DEFAULT_HA_EMA_VOLUME_EMA1_PERIOD
                    )
                ),
                int(
                    filters.get(
                        "ha_ema_volume_ema2_period", DEFAULT_HA_EMA_VOLUME_EMA2_PERIOD
                    )
                ),
                int(filters.get("ha_ema_volume_period", DEFAULT_HA_EMA_VOLUME_PERIOD)),
            ]
        )

    max_period = max(periods, default=DEFAULT_EMA_RELATIONSHIP_SLOW)
    warmup_days = max(
        MIN_INDICATOR_WARMUP_DAYS,
        max_period * INDICATOR_WARMUP_CALENDAR_DAYS_PER_PERIOD,
    )
    return max(
        DEFAULT_HISTORY_DAYS,
        int(filters.get("lookback_days", DEFAULT_LOOKBACK_DAYS)) + warmup_days,
    )


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
        return date.fromisoformat(str(pd.Timestamp(str(value)).date()))
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
    normalized_tickers = [
        str(ticker).upper() for ticker in tickers if str(ticker).strip()
    ]
    if not normalized_tickers:
        return pd.DataFrame()

    latest_date = _resolve_latest_date(latest_market_date)
    since_date = (
        latest_date - timedelta(days=max(history_days, DEFAULT_HISTORY_DAYS))
    ).isoformat()
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
    history = (
        history.dropna(subset=["date"])
        .sort_values(["ticker", "date"])
        .reset_index(drop=True)
    )
    return history


def _indicator_history_cache_key(
    db_path: str,
    tickers: list[str],
    *,
    latest_market_date: object | None,
    history_days: int,
) -> tuple[str, str, int, int, tuple[str, ...]]:
    normalized_tickers = tuple(
        sorted({str(ticker).upper() for ticker in tickers if str(ticker).strip()})
    )
    latest_date = _resolve_latest_date(latest_market_date).isoformat()
    try:
        database_mtime_ns = int(os.stat(db_path).st_mtime_ns)
    except OSError:
        database_mtime_ns = 0
    return (
        str(db_path),
        latest_date,
        int(history_days),
        database_mtime_ns,
        normalized_tickers,
    )


def _get_cached_indicator_history(
    cache_key: tuple[str, str, int, int, tuple[str, ...]],
) -> pd.DataFrame | None:
    with _INDICATOR_HISTORY_CACHE_LOCK:
        cached = _INDICATOR_HISTORY_CACHE.get(cache_key)
        if cached is not None:
            _INDICATOR_HISTORY_CACHE.move_to_end(cache_key)
            return cached
    cache_name = hashlib.sha256(repr(cache_key).encode("utf-8")).hexdigest() + ".pkl"
    if not cache_is_fresh(Path(INDICATOR_HISTORY_DISK_CACHE) / cache_name):
        return None
    try:
        with open(
            os.path.join(INDICATOR_HISTORY_DISK_CACHE, cache_name), "rb"
        ) as handle:  # noqa: PTH123
            cached = pickle.load(handle)  # noqa: S301
        if isinstance(cached, pd.DataFrame) and not cached.empty:
            _store_cached_indicator_history(cache_key, cached)
            return cached
    except (FileNotFoundError, OSError, pickle.PickleError, EOFError, ImportError):
        pass
    return None


def _store_cached_indicator_history(
    cache_key: tuple[str, str, int, int, tuple[str, ...]],
    history: pd.DataFrame,
) -> None:
    with _INDICATOR_HISTORY_CACHE_LOCK:
        _INDICATOR_HISTORY_CACHE[cache_key] = history
        _INDICATOR_HISTORY_CACHE.move_to_end(cache_key)
        while len(_INDICATOR_HISTORY_CACHE) > INDICATOR_HISTORY_CACHE_MAXSIZE:
            _INDICATOR_HISTORY_CACHE.popitem(last=False)


def _enrich_indicator_group(group: tuple[str, pd.DataFrame]) -> pd.DataFrame:
    """Calculate the fixed screen indicators for one ticker."""
    ticker, frame = group
    scoped = frame.sort_values("date").reset_index(drop=True).copy()
    scoped["ticker"] = str(ticker).upper()
    scoped["close"] = pd.to_numeric(scoped["close"], errors="coerce")
    scoped["volume"] = pd.to_numeric(scoped["volume"], errors="coerce").fillna(0.0)
    close = scoped["close"]
    high = pd.to_numeric(scoped["high"] if "high" in scoped else close, errors="coerce")
    low = pd.to_numeric(scoped["low"] if "low" in scoped else close, errors="coerce")
    scoped["high"] = high
    scoped["low"] = low
    scoped["rsi"] = calculate_rsi(close, period=14)
    scoped["macd"], scoped["macd_signal"], _ = calculate_macd(close)
    scoped["stoch_k"], scoped["stoch_d"] = calculate_stoch_rsi(
        close, rsi_period=14, stoch_period=14, k_period=3, d_period=3
    )
    return scoped[
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
        ]
    ]


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

    groups = list(history.groupby("ticker", sort=False))
    worker_count = min(12, max(4, os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        enriched_frames = list(executor.map(_enrich_indicator_group, groups))

    enriched_history = (
        pd.concat(enriched_frames, ignore_index=True)
        if enriched_frames
        else pd.DataFrame()
    )
    if not enriched_history.empty:
        _store_cached_indicator_history(cache_key, enriched_history)
        try:
            os.makedirs(INDICATOR_HISTORY_DISK_CACHE, exist_ok=True)
            cache_name = (
                hashlib.sha256(repr(cache_key).encode("utf-8")).hexdigest() + ".pkl"
            )
            temp_path = os.path.join(INDICATOR_HISTORY_DISK_CACHE, cache_name + ".tmp")
            final_path = os.path.join(INDICATOR_HISTORY_DISK_CACHE, cache_name)
            with open(temp_path, "wb") as handle:  # noqa: PTH123
                pickle.dump(enriched_history, handle, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(temp_path, final_path)
            trim_cache()
        except OSError:
            pass
    return enriched_history, False


def _crossed_above(lhs: pd.Series, rhs: pd.Series) -> pd.Series:
    return (lhs > rhs) & (lhs.shift(1) <= rhs.shift(1))


def _crossed_below(lhs: pd.Series, rhs: pd.Series) -> pd.Series:
    return (lhs < rhs) & (lhs.shift(1) >= rhs.shift(1))


def _crossed_above_value(series: pd.Series, value: float) -> pd.Series:
    return (series > value) & (series.shift(1) <= value)


def _crossed_below_value(series: pd.Series, value: float) -> pd.Series:
    return (series < value) & (series.shift(1) >= value)


def _latest_event_age_days(
    mask: pd.Series, dates: pd.Series, *, lookback_days: int
) -> int | None:
    if mask.empty or dates.empty:
        return None
    latest_date = pd.Timestamp(dates.iloc[-1]).normalize()
    cutoff = latest_date - pd.Timedelta(days=lookback_days)
    scoped = mask.fillna(False) & (dates >= cutoff)
    if not bool(scoped.any()):
        return None
    event_date = pd.Timestamp(dates[scoped].iloc[-1]).normalize()
    return int((latest_date - event_date).days)


def _rsi_event_sequence_ages(
    rsi: pd.Series,
    dates: pd.Series,
    events: list[dict[str, Any]],
    *,
    lookback_days: int,
) -> list[int] | None:
    """Return distinct RSI event ages in the configured sequence order.

    The sequence is chronological: the first step is the oldest crossing and
    each later step must be a distinct crossing after it. Each step's age is
    still an independent upper-bound window ending today.
    """
    sequence = RsiEventSequence(tuple(RsiEvent.from_dict(event) for event in events))
    return sequence.find_ages(rsi, dates, lookback_days=lookback_days)


def _ema_slope_state(
    close: pd.Series, *, period: int, lookback: int, flat_tolerance: float
) -> str:
    ema = pd.to_numeric(close, errors="coerce").ewm(span=period, adjust=False).mean()
    if len(ema) <= lookback:
        return "unknown"
    current = _finite_or_none(ema.iloc[-1])
    previous = _finite_or_none(ema.iloc[-1 - lookback])
    if current is None or previous is None or previous == 0:
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
    fast_slope_direction: str = DEFAULT_EMA_RELATIONSHIP_SLOPE,
    slow_slope_direction: str = DEFAULT_EMA_RELATIONSHIP_SLOPE,
    cross_mode: str = DEFAULT_EMA_RELATIONSHIP_CROSS_MODE,
) -> tuple[pd.Series, pd.Series, str, str]:
    fast = (
        pd.to_numeric(close, errors="coerce").ewm(span=fast_period, adjust=False).mean()
    )
    slow = (
        pd.to_numeric(close, errors="coerce").ewm(span=slow_period, adjust=False).mean()
    )
    states = pd.Series("unknown", index=close.index, dtype="object")
    valid = fast.notna() & slow.notna()
    states.loc[valid & fast.gt(slow)] = "fast above slow"
    states.loc[valid & fast.lt(slow)] = "fast below slow"

    cross_up = _crossed_above(fast, slow)
    cross_down = _crossed_below(fast, slow)
    normalized_cross_mode = (
        str(cross_mode or DEFAULT_EMA_RELATIONSHIP_CROSS_MODE).strip().lower()
    )
    cross = cross_up if normalized_cross_mode == "cross_up" else cross_down
    slope_lookback = 5
    fast_change = fast.pct_change(slope_lookback) * 100.0
    slow_change = slow.pct_change(slope_lookback) * 100.0
    fast_direction = str(fast_slope_direction or DEFAULT_EMA_RELATIONSHIP_SLOPE).lower()
    slow_direction = str(slow_slope_direction or DEFAULT_EMA_RELATIONSHIP_SLOPE).lower()
    fast_matches = (
        pd.Series(True, index=close.index)
        if fast_direction == "any"
        else (
            fast_change.gt(0.1)
            if fast_direction == "positive"
            else (
                fast_change.lt(-0.1)
                if fast_direction == "negative"
                else fast_change.abs().le(0.1)
            )
        )
    )
    slow_matches = (
        pd.Series(True, index=close.index)
        if slow_direction == "any"
        else (
            slow_change.gt(0.1)
            if slow_direction == "positive"
            else (
                slow_change.lt(-0.1)
                if slow_direction == "negative"
                else slow_change.abs().le(0.1)
            )
        )
    )
    fast_slope = (
        "unknown"
        if fast_change.empty or pd.isna(fast_change.iloc[-1])
        else (
            "positive"
            if fast_change.iloc[-1] > 0.1
            else "negative" if fast_change.iloc[-1] < -0.1 else "flat"
        )
    )
    slow_slope = (
        "unknown"
        if slow_change.empty or pd.isna(slow_change.iloc[-1])
        else (
            "positive"
            if slow_change.iloc[-1] > 0.1
            else "negative" if slow_change.iloc[-1] < -0.1 else "flat"
        )
    )
    slope_matches = fast_matches & slow_matches
    mask = cross & slope_matches
    return mask.fillna(False), states, fast_slope, slow_slope


def _price_ema_cross_mask(
    close: pd.Series,
    *,
    period: int,
    mode: str = DEFAULT_PRICE_EMA_CROSS_MODE,
) -> pd.Series:
    """Detect price crossing a single EMA, in the requested direction."""
    price = pd.to_numeric(close, errors="coerce")
    ema = price.ewm(span=period, adjust=False).mean()
    normalized_mode = str(mode or DEFAULT_PRICE_EMA_CROSS_MODE).strip().lower()
    return (
        _crossed_above(price, ema)
        if normalized_mode == "cross_up"
        else _crossed_below(price, ema)
    ).fillna(False)


def _ema_flatten_mask(
    close: pd.Series,
    *,
    period: int,
    lookback: int = DEFAULT_EMA_FLATTEN_LOOKBACK,
    tolerance: float = DEFAULT_EMA_FLATTEN_TOLERANCE,
    mode: str = DEFAULT_EMA_FLATTEN_MODE,
) -> tuple[pd.Series, pd.Series]:
    """Detect an EMA entering a flat slope and classify the turn as top/bottom."""
    ema = pd.to_numeric(close, errors="coerce").ewm(span=period, adjust=False).mean()
    change = ema.pct_change(lookback) * 100.0
    current_flat = change.abs().le(tolerance)
    previous_change = change.shift(1)
    top = current_flat & previous_change.gt(tolerance)
    bottom = current_flat & previous_change.lt(-tolerance)
    # Keep the event active while the EMA remains flat. This makes the
    # screen useful for a current flattening setup instead of only matching
    # the first bar that entered the flat band.
    states = pd.Series("unknown", index=close.index, dtype="object")
    states.loc[top] = "top"
    states.loc[bottom] = "bottom"
    states = states.replace("unknown", pd.NA).ffill().fillna("unknown")
    normalized_mode = str(mode or DEFAULT_EMA_FLATTEN_MODE).strip().lower()
    mask = current_flat & (
        states.eq("top")
        if normalized_mode == "top"
        else (
            states.eq("bottom")
            if normalized_mode == "bottom"
            else states.isin({"top", "bottom"})
        )
    )
    return mask.fillna(False), states


def _ema_flatten_label(period: int, mode: str) -> str:
    return f"EMA {period} flatten ({str(mode).strip().lower()})"


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
    current = green.fillna(False).astype(bool)
    previous = current.shift(1, fill_value=False)
    if normalized_mode == "green_to_red":
        return previous & ~current
    return ~previous & current


def _supertrend_cross_label(mode: str) -> str:
    return (
        "Supertrend green to red"
        if str(mode).strip().lower() == "green_to_red"
        else "Supertrend red to green"
    )


def _volume_spike_mask(
    volume: pd.Series, *, period: int, multiplier: float
) -> tuple[pd.Series, pd.Series]:
    """Detect a fresh cross above a volume EMA multiple and return its ratio."""
    baseline = volume.ewm(span=period, adjust=False, min_periods=period).mean()
    ratio = volume.divide(baseline.replace(0, pd.NA))
    threshold = ratio >= multiplier
    crossed = threshold & ~threshold.shift(1, fill_value=False)
    return crossed.fillna(False), ratio


def _volume_spike_label(period: int, multiplier: float) -> str:
    return f"Volume spike {multiplier:.1f}x EMA {period}"


def _heikin_ashi_ohlc(
    frame: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Return Heikin-Ashi OHLC values for event evaluation."""
    raw_close = pd.to_numeric(frame["close"], errors="coerce")
    # Some screener queries only return close plus derived indicators. Keep
    # the event evaluator usable for those frames instead of raising a
    # per-ticker KeyError when an alternate OHLC source is selected.
    raw_open = pd.to_numeric(frame.get("open", raw_close), errors="coerce")
    raw_high = pd.to_numeric(frame.get("high", raw_close), errors="coerce")
    raw_low = pd.to_numeric(frame.get("low", raw_close), errors="coerce")
    ha_close = (raw_open + raw_high + raw_low + raw_close) / 4.0
    ha_open = ((raw_open + raw_close) / 2.0).copy()
    for index in range(1, len(ha_open)):
        ha_open.iloc[index] = (ha_open.iloc[index - 1] + ha_close.iloc[index - 1]) / 2.0
    ha_high = pd.concat([raw_high, ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([raw_low, ha_open, ha_close], axis=1).min(axis=1)
    return ha_open, ha_high, ha_low, ha_close


def _ha_ema_volume_mask(
    frame: pd.DataFrame,
    volume: pd.Series,
    *,
    ema1_period: int,
    ema1_source: str,
    ema2_period: int,
    ema2_source: str,
    start_field: str,
    start_line: str,
    start_relation: str,
    end_field: str,
    end_line: str,
    end_relation: str,
    volume_period: int,
    volume_multiplier: float,
    conditions: list[dict[str, Any]] | None = None,
    candle_color: str = DEFAULT_HA_EMA_VOLUME_CANDLE_COLOR,
) -> tuple[pd.Series, pd.Series]:
    """Match selected same-candle HA OHLC zones plus a volume spike."""
    ha_open, ha_high, ha_low, ha_close = _heikin_ashi_ohlc(frame)
    ha_fields = {"open": ha_open, "high": ha_high, "low": ha_low, "close": ha_close}
    # The condition rows evaluate Heikin-Ashi OHLC, so their EMA sources must
    # use the same HA series. Mixing HA candles with raw-price EMAs makes a
    # candle appear contained by the chart while still passing the screener.
    ema1_source_series = ha_fields.get(str(ema1_source).lower(), frame["close"])
    ema2_source_series = ha_fields.get(str(ema2_source).lower(), frame["close"])
    ema1 = (
        pd.to_numeric(ema1_source_series, errors="coerce")
        .ewm(span=ema1_period, adjust=False, min_periods=ema1_period)
        .mean()
    )
    ema2 = (
        pd.to_numeric(ema2_source_series, errors="coerce")
        .ewm(span=ema2_period, adjust=False, min_periods=ema2_period)
        .mean()
    )
    ema_lines = {"ema1": ema1, "ema2": ema2}
    if conditions is not None:
        contradictions = _validate_ha_ema_volume_conditions(conditions)
        if contradictions:
            raise ValueError("Invalid HA OHLC conditions: " + " ".join(contradictions))
        condition_matches = pd.Series(True, index=frame.index)
        for condition in conditions:
            if not condition.get("enabled"):
                continue
            value = ha_fields[str(condition["field"])]
            zone = str(condition["zone"])
            if zone == "above_ema1":
                condition_matches &= value > ema1
            elif zone == "below_ema2":
                condition_matches &= value < ema2
            else:
                condition_matches &= value > pd.concat([ema1, ema2], axis=1).min(axis=1)
                condition_matches &= value < pd.concat([ema1, ema2], axis=1).max(axis=1)
    else:
        start_value = ha_fields.get(str(start_field).lower(), ha_open)
        end_value = ha_fields.get(str(end_field).lower(), ha_close)
        start_line_value = ema_lines.get(str(start_line).lower(), ema2)
        end_line_value = ema_lines.get(str(end_line).lower(), ema1)
        condition_matches = (
            start_value > start_line_value
            if str(start_relation).lower() == "above"
            else start_value < start_line_value
        )
        condition_matches &= (
            end_value > end_line_value
            if str(end_relation).lower() == "above"
            else end_value < end_line_value
        )
    volume_baseline = volume.ewm(
        span=volume_period, adjust=False, min_periods=volume_period
    ).mean()
    volume_ratio = volume.divide(volume_baseline.replace(0, pd.NA))
    color = str(candle_color or "any").strip().lower()
    color_matches = pd.Series(True, index=frame.index)
    if color == "green":
        color_matches = ha_close > ha_open
    elif color == "red":
        color_matches = ha_close < ha_open
    matched = condition_matches & color_matches & (volume_ratio >= volume_multiplier)
    return matched.fillna(False), volume_ratio


def _ha_ema_volume_label(
    ema1_period: int,
    ema1_source: str,
    ema2_period: int,
    ema2_source: str,
    start_field: str,
    start_line: str,
    start_relation: str,
    end_field: str,
    end_line: str,
    end_relation: str,
    volume_period: int,
    multiplier: float,
) -> str:
    return f"HA {str(start_field).title()} {str(start_relation).lower()} {str(start_line).upper()} and HA {str(end_field).title()} {str(end_relation).lower()} {str(end_line).upper()} + Volume {multiplier:.1f}x EMA {volume_period}"


def screen_with_controls(
    *,
    db_path: str,
    tickers: list[str],
    latest_market_date: object | None,
    filters: object | None = None,
    metadata_map: dict[str, dict[str, Any]] | None = None,
    cancel_event=None,
) -> dict[str, Any]:
    """Scan the selected universe using recent MACD/RSI/StochRSI event controls."""
    normalized_filters = normalize_screen_filters(filters)
    condition_errors = (
        _validate_ha_ema_volume_conditions(
            normalized_filters["ha_ema_volume_conditions"]
        )
        if normalized_filters["ha_ema_volume_enabled"]
        else []
    )
    if condition_errors:
        return {
            "matches": [],
            "errors": [{"ticker": "SYSTEM", "error": " ".join(condition_errors)}],
            "total_errors": 1,
            "total_candidates": 0,
            "candidate_pool": [],
            "filters": normalized_filters,
            "indicator_cache_hit": False,
        }
    lookback_days = int(normalized_filters["lookback_days"])
    required_history_days = _required_screen_history_days(normalized_filters)
    history, indicator_cache_hit = load_recent_indicator_history(
        db_path,
        tickers,
        latest_market_date=latest_market_date,
        history_days=required_history_days,
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

    matches: list[dict[str, Any]] = []
    candidate_pool: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    grouped = {
        str(ticker).upper(): group.copy()
        for ticker, group in history.groupby("ticker", sort=False)
    }
    requested_tickers = [
        str(ticker).upper() for ticker in tickers if str(ticker).strip()
    ]
    expected_latest_date = (
        _resolve_latest_date(latest_market_date)
        if latest_market_date is not None
        else None
    )
    observed_latest_dates = [
        pd.Timestamp(frame["date"].iloc[-1]).date()
        for ticker in requested_tickers
        if (frame := grouped.get(ticker)) is not None
        and not frame.empty
        and "date" in frame
        and pd.notna(frame["date"].iloc[-1])
    ]
    if observed_latest_dates:
        # The database contains several markets with different trading
        # calendars and refresh times. Compare freshness within this scan's
        # selected universe rather than against another market's latest row.
        expected_latest_date = max(observed_latest_dates)

    for ticker in requested_tickers:
        if cancel_event is not None and cancel_event.is_set():
            break
        frame = grouped.get(ticker)
        if frame is None or frame.empty:
            continue
        try:
            frame = frame.sort_values("date").reset_index(drop=True)
            close = pd.to_numeric(frame["close"], errors="coerce")
            price_ema_sources = {
                source: pd.to_numeric(frame[source], errors="coerce")
                for source in ("open", "high", "low", "close")
                if source in frame
            }
            volume = pd.to_numeric(frame["volume"], errors="coerce").fillna(0.0)
            dates = pd.to_datetime(frame["date"], errors="coerce")
            if len(frame) < 40 or close.isna().all() or dates.isna().all():
                continue
            if expected_latest_date is not None:
                ticker_latest_date = dates.iloc[-1].date()
                if (
                    expected_latest_date - ticker_latest_date
                ).days > MAX_SCREEN_DATA_STALENESS_DAYS:
                    logger.debug(
                        "Skipping stale ticker %s: latest=%s expected=%s",
                        ticker,
                        ticker_latest_date,
                        expected_latest_date,
                    )
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
            avg_volume_20 = (
                _finite_or_none(volume.tail(20).mean()) if len(volume) else 0.0
            )
            if current_close is None or current_rsi is None:
                continue
            if bool(normalized_filters["rsi_filter_enabled"]):
                if current_rsi < float(normalized_filters["rsi_filter_min"]):
                    continue
            if avg_volume_20 is None:
                avg_volume_20 = 0.0

            volume_range = normalized_filters["volume_range"]
            volume_matches = (
                float(volume_range["min"])
                <= avg_volume_20
                <= float(volume_range["max"])
            )

            slope_lookback = int(normalized_filters["ema_slope_lookback"])
            slope_tolerance = float(normalized_filters["ema_slope_flat_tolerance"])
            ema_slope_periods = [
                int(normalized_filters[f"ema_slope_period_{index}"])
                for index in (1, 2, 3)
            ]
            ema_slope_states = {
                period: _ema_slope_state(
                    close,
                    period=period,
                    lookback=slope_lookback,
                    flat_tolerance=slope_tolerance,
                )
                for period in ema_slope_periods
            }
            slope_matches = not any(
                normalized_filters[f"ema_slope_{index}"]
                not in {"any", ema_slope_states[period]}
                for index, period in enumerate(ema_slope_periods, start=1)
            )

            macd_mode = str(normalized_filters["macd_cross_mode"])
            macd_enabled = bool(normalized_filters["macd_event_enabled"])
            rsi_mode = str(normalized_filters["rsi_cross_mode"])
            rsi_enabled = bool(normalized_filters["rsi_event_enabled"])
            rsi_level = float(normalized_filters["rsi_cross_value"])
            rsi_events = [
                dict(event)
                for event in normalized_filters.get("rsi_events", [])
                if isinstance(event, dict)
            ]
            if rsi_enabled and not rsi_events:
                rsi_events = [
                    {
                        "rsi_cross_value": rsi_level,
                        "rsi_cross_mode": rsi_mode,
                        "rsi_event_age": int(normalized_filters["rsi_event_age"]),
                    }
                ]
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
            rsi_ages = (
                _rsi_event_sequence_ages(
                    rsi,
                    dates,
                    rsi_events,
                    lookback_days=lookback_days,
                )
                if rsi_enabled
                else None
            )
            rsi_age = rsi_ages[0] if rsi_ages else None
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
            supertrend_age = None
            if supertrend_enabled:
                chart_ta: Any = (
                    normalized_filters.get("chart_ta")
                    if isinstance(normalized_filters.get("chart_ta"), dict)
                    else {}
                )
                st_period = _coerce_int(
                    chart_ta.get("supertrend_period"), 10, minimum=2, maximum=100
                )
                st_multiplier = _coerce_float(
                    chart_ta.get("supertrend_multiplier"),
                    3.0,
                    minimum=0.5,
                    maximum=10.0,
                )
                st_high = pd.to_numeric(
                    frame["high"] if "high" in frame else close, errors="coerce"
                )
                st_low = pd.to_numeric(
                    frame["low"] if "low" in frame else close, errors="coerce"
                )
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
            ema_relationship_enabled = bool(
                normalized_filters["ema_relationship_enabled"]
            )
            ema_fast_period = int(normalized_filters["ema_relationship_fast"])
            ema_slow_period = int(normalized_filters["ema_relationship_slow"])
            (
                ema_relationship_mask,
                ema_relationship_states,
                ema_fast_slope_state,
                ema_slow_slope_state,
            ) = _ema_cross_event_mask(
                close,
                fast_period=ema_fast_period,
                slow_period=ema_slow_period,
                fast_slope_direction=str(
                    normalized_filters["ema_relationship_fast_slope"]
                ),
                slow_slope_direction=str(
                    normalized_filters["ema_relationship_slow_slope"]
                ),
                cross_mode=str(normalized_filters["ema_relationship_cross_mode"]),
            )
            ema_relationship_age = _latest_event_age_days(
                ema_relationship_mask, dates, lookback_days=lookback_days
            )
            ema_relationship_state = str(ema_relationship_states.iloc[-1])
            price_ema_enabled = bool(normalized_filters["price_ema_event_enabled"])
            price_ema_period = int(normalized_filters["price_ema_period"])
            price_ema_source = str(normalized_filters["price_ema_source"])
            price_ema_mode = str(normalized_filters["price_ema_cross_mode"])
            price_ema_event_results: list[dict[str, Any]] = []
            for event in normalized_filters.get("price_ema_events", []):
                event_source = str(event["price_ema_source"])
                event_period = int(event["price_ema_period"])
                event_mode = str(event["price_ema_cross_mode"])
                event_price = price_ema_sources.get(event_source, close)
                event_ema = event_price.ewm(span=event_period, adjust=False).mean()
                event_mask = _price_ema_cross_mask(
                    event_price, period=event_period, mode=event_mode
                )
                event_age = _latest_event_age_days(
                    event_mask, dates, lookback_days=lookback_days
                )
                price_ema_event_results.append(
                    {
                        **event,
                        "price_ema_age": event_age,
                        "price_ema_state": (
                            f"{event_source} above EMA"
                            if event_price.iloc[-1] > event_ema.iloc[-1]
                            else f"{event_source} below EMA"
                        ),
                    }
                )
            primary_price_ema = (
                price_ema_event_results[0]
                if price_ema_event_results
                else {
                    "price_ema_source": price_ema_source,
                    "price_ema_period": price_ema_period,
                    "price_ema_cross_mode": price_ema_mode,
                    "price_ema_event_age": int(
                        normalized_filters["price_ema_event_age"]
                    ),
                    "price_ema_age": None,
                    "price_ema_state": "unknown",
                }
            )
            price_ema_source = str(primary_price_ema["price_ema_source"])
            price_ema_period = int(primary_price_ema["price_ema_period"])
            price_ema_mode = str(primary_price_ema["price_ema_cross_mode"])
            price_ema_age = primary_price_ema["price_ema_age"]
            price_ema_state = str(primary_price_ema["price_ema_state"])
            ema_flatten_enabled = bool(normalized_filters["ema_flatten_enabled"])
            ema_flatten_period = int(normalized_filters["ema_flatten_period"])
            ema_flatten_lookback = int(normalized_filters["ema_flatten_lookback"])
            ema_flatten_tolerance = float(normalized_filters["ema_flatten_tolerance"])
            ema_flatten_mode = str(normalized_filters["ema_flatten_mode"])
            ema_flatten_mask, ema_flatten_states = _ema_flatten_mask(
                close,
                period=ema_flatten_period,
                lookback=ema_flatten_lookback,
                tolerance=ema_flatten_tolerance,
                mode=ema_flatten_mode,
            )
            ema_flatten_age = _latest_event_age_days(
                ema_flatten_mask, dates, lookback_days=lookback_days
            )
            flatten_event_states = ema_flatten_states[ema_flatten_mask]
            ema_flatten_state = str(
                flatten_event_states.iloc[-1]
                if not flatten_event_states.empty
                else ema_flatten_states.iloc[-1]
            )
            volume_spike_period = int(normalized_filters["volume_spike_period"])
            volume_spike_multiplier = float(
                normalized_filters["volume_spike_multiplier"]
            )
            volume_spike_mask, volume_spike_ratio = _volume_spike_mask(
                volume,
                period=volume_spike_period,
                multiplier=volume_spike_multiplier,
            )
            volume_spike_age = _latest_event_age_days(
                volume_spike_mask, dates, lookback_days=lookback_days
            )
            volume_spike_ratio_current = _finite_or_none(volume_spike_ratio.iloc[-1])
            ha_ema_volume_enabled = bool(normalized_filters["ha_ema_volume_enabled"])
            ha_ema_volume_ema1_period = int(
                normalized_filters["ha_ema_volume_ema1_period"]
            )
            ha_ema_volume_ema1_source = str(
                normalized_filters["ha_ema_volume_ema1_source"]
            )
            ha_ema_volume_ema2_period = int(
                normalized_filters["ha_ema_volume_ema2_period"]
            )
            ha_ema_volume_ema2_source = str(
                normalized_filters["ha_ema_volume_ema2_source"]
            )
            ha_ema_volume_start_field = str(
                normalized_filters["ha_ema_volume_start_field"]
            )
            ha_ema_volume_start_line = str(
                normalized_filters["ha_ema_volume_start_line"]
            )
            ha_ema_volume_start_relation = str(
                normalized_filters["ha_ema_volume_start_relation"]
            )
            ha_ema_volume_end_field = str(normalized_filters["ha_ema_volume_end_field"])
            ha_ema_volume_end_line = str(normalized_filters["ha_ema_volume_end_line"])
            ha_ema_volume_end_relation = str(
                normalized_filters["ha_ema_volume_end_relation"]
            )
            ha_ema_volume_period = int(normalized_filters["ha_ema_volume_period"])
            ha_ema_volume_multiplier = float(
                normalized_filters["ha_ema_volume_multiplier"]
            )
            ha_ema_volume_mask, ha_ema_volume_ratio = _ha_ema_volume_mask(
                frame,
                volume,
                ema1_period=ha_ema_volume_ema1_period,
                ema1_source=ha_ema_volume_ema1_source,
                ema2_period=ha_ema_volume_ema2_period,
                ema2_source=ha_ema_volume_ema2_source,
                start_field=ha_ema_volume_start_field,
                start_line=ha_ema_volume_start_line,
                start_relation=ha_ema_volume_start_relation,
                end_field=ha_ema_volume_end_field,
                end_line=ha_ema_volume_end_line,
                end_relation=ha_ema_volume_end_relation,
                volume_period=ha_ema_volume_period,
                volume_multiplier=ha_ema_volume_multiplier,
                conditions=normalized_filters["ha_ema_volume_conditions"],
                candle_color=str(normalized_filters["ha_ema_volume_candle_color"]),
            )
            ha_ema_volume_age = _latest_event_age_days(
                ha_ema_volume_mask, dates, lookback_days=lookback_days
            )
            ha_ema_volume_ratio_current = _finite_or_none(ha_ema_volume_ratio.iloc[-1])

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
                    "ema_slope_20_state": ema_slope_states.get(20, "unknown"),
                    "ema_slope_50_state": ema_slope_states.get(50, "unknown"),
                    "ema_slope_200_state": ema_slope_states.get(200, "unknown"),
                    "ema_slope_periods": ema_slope_periods,
                    **{
                        f"ema_slope_{index}_state": ema_slope_states[period]
                        for index, period in enumerate(ema_slope_periods, start=1)
                    },
                    "macd_cross_days_ago": macd_age,
                    "rsi_cross_days_ago": rsi_age,
                    "rsi_cross_days_ago_all": rsi_ages,
                    "stoch_cross_days_ago": stoch_age,
                    "supertrend_cross_days_ago": supertrend_age,
                    "ema_relationship_state": ema_relationship_state,
                    "ema_relationship_fast_slope": ema_fast_slope_state,
                    "ema_relationship_slow_slope": ema_slow_slope_state,
                    "ema_relationship_days_ago": ema_relationship_age,
                    "price_ema_days_ago": price_ema_age,
                    "price_ema_state": price_ema_state,
                    "ema_flatten_days_ago": ema_flatten_age,
                    "ema_flatten_state": ema_flatten_state,
                    "volume_spike_days_ago": volume_spike_age,
                    "volume_spike_ratio": (
                        round(volume_spike_ratio_current, 2)
                        if volume_spike_ratio_current is not None
                        else None
                    ),
                    "ha_ema_volume_days_ago": ha_ema_volume_age,
                    "ha_ema_volume_ratio": (
                        round(ha_ema_volume_ratio_current, 2)
                        if ha_ema_volume_ratio_current is not None
                        else None
                    ),
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
            if rsi_enabled and not rsi_ages:
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
            if price_ema_enabled and any(
                not _event_matches_target(
                    result["price_ema_age"],
                    int(result["price_ema_event_age"]),
                )
                for result in price_ema_event_results
            ):
                continue
            if ema_flatten_enabled and not _event_matches_target(
                ema_flatten_age,
                int(normalized_filters["ema_flatten_event_age"]),
            ):
                continue
            if bool(
                normalized_filters["volume_spike_enabled"]
            ) and not _event_matches_target(
                volume_spike_age,
                int(normalized_filters["volume_spike_age"]),
            ):
                continue
            if ha_ema_volume_enabled and not _event_matches_target(
                ha_ema_volume_age,
                int(normalized_filters["ha_ema_volume_event_age"]),
            ):
                continue

            event_pairs: list[tuple[str, int]] = []
            if rsi_enabled:
                event_pairs.extend(
                    (
                        _rsi_cross_label(
                            str(event["rsi_cross_mode"]),
                            float(event["rsi_cross_value"]),
                        ),
                        int(age),
                    )
                    for event, age in zip(rsi_events, rsi_ages or [])
                )
            if macd_enabled:
                event_pairs.append(("MACD", int(macd_age or 0)))
            if stoch_enabled:
                event_pairs.append(("StochRSI", int(stoch_age or 0)))
            if supertrend_enabled:
                event_pairs.append(("Supertrend", int(supertrend_age or 0)))
            if ema_relationship_enabled:
                event_pairs.append(
                    (
                        f"EMA {ema_fast_period}/{ema_slow_period} cross",
                        int(ema_relationship_age or 0),
                    )
                )
            if price_ema_enabled:
                event_pairs.extend(
                    (
                        f"{str(result['price_ema_source']).title()} {str(result['price_ema_cross_mode']).replace('_', ' ')} EMA {int(result['price_ema_period'])}",
                        int(result["price_ema_age"] or 0),
                    )
                    for result in price_ema_event_results
                )
            if ema_flatten_enabled:
                event_pairs.append(
                    (
                        _ema_flatten_label(ema_flatten_period, ema_flatten_state),
                        int(ema_flatten_age or 0),
                    )
                )
            if bool(normalized_filters["volume_spike_enabled"]):
                event_pairs.append(
                    (
                        _volume_spike_label(
                            volume_spike_period, volume_spike_multiplier
                        ),
                        int(volume_spike_age or 0),
                    )
                )
            if ha_ema_volume_enabled:
                event_pairs.append(
                    (
                        _ha_ema_volume_label(
                            ha_ema_volume_ema1_period,
                            ha_ema_volume_ema1_source,
                            ha_ema_volume_ema2_period,
                            ha_ema_volume_ema2_source,
                            ha_ema_volume_start_field,
                            ha_ema_volume_start_line,
                            ha_ema_volume_start_relation,
                            ha_ema_volume_end_field,
                            ha_ema_volume_end_line,
                            ha_ema_volume_end_relation,
                            ha_ema_volume_period,
                            ha_ema_volume_multiplier,
                        ),
                        int(ha_ema_volume_age or 0),
                    )
                )
            ordered_events = sorted(event_pairs, key=lambda item: item[1], reverse=True)
            sequence = (
                " -> ".join(label for label, _ in ordered_events) or "Volume only"
            )
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
                    "rsi_events": rsi_events,
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
                    "ema_relationship_fast_slope": ema_fast_slope_state,
                    "ema_relationship_slow_slope": ema_slow_slope_state,
                    "ema_relationship_cross_mode": str(
                        normalized_filters["ema_relationship_cross_mode"]
                    ),
                    "price_ema_event_enabled": price_ema_enabled,
                    "price_ema_period": price_ema_period,
                    "price_ema_source": price_ema_source,
                    "price_ema_cross_mode": price_ema_mode,
                    "price_ema_days_ago": price_ema_age,
                    "price_ema_state": price_ema_state,
                    "price_ema_events": price_ema_event_results,
                    "ema_flatten_enabled": ema_flatten_enabled,
                    "ema_flatten_period": ema_flatten_period,
                    "ema_flatten_lookback": ema_flatten_lookback,
                    "ema_flatten_tolerance": ema_flatten_tolerance,
                    "ema_flatten_mode": ema_flatten_mode,
                    "ema_flatten_days_ago": ema_flatten_age,
                    "ema_flatten_state": ema_flatten_state,
                    "volume_spike_enabled": bool(
                        normalized_filters["volume_spike_enabled"]
                    ),
                    "volume_spike_period": volume_spike_period,
                    "volume_spike_multiplier": volume_spike_multiplier,
                    "volume_spike_days_ago": volume_spike_age,
                    "volume_spike_ratio": (
                        round(volume_spike_ratio_current, 2)
                        if volume_spike_ratio_current is not None
                        else None
                    ),
                    "ha_ema_volume_enabled": ha_ema_volume_enabled,
                    "ha_ema_volume_ema1_period": ha_ema_volume_ema1_period,
                    "ha_ema_volume_ema1_source": ha_ema_volume_ema1_source,
                    "ha_ema_volume_ema2_period": ha_ema_volume_ema2_period,
                    "ha_ema_volume_ema2_source": ha_ema_volume_ema2_source,
                    "ha_ema_volume_start_field": ha_ema_volume_start_field,
                    "ha_ema_volume_start_line": ha_ema_volume_start_line,
                    "ha_ema_volume_start_relation": ha_ema_volume_start_relation,
                    "ha_ema_volume_end_field": ha_ema_volume_end_field,
                    "ha_ema_volume_end_line": ha_ema_volume_end_line,
                    "ha_ema_volume_end_relation": ha_ema_volume_end_relation,
                    "ha_ema_volume_period": ha_ema_volume_period,
                    "ha_ema_volume_multiplier": ha_ema_volume_multiplier,
                    "ha_ema_volume_days_ago": ha_ema_volume_age,
                    "ha_ema_volume_ratio": (
                        round(ha_ema_volume_ratio_current, 2)
                        if ha_ema_volume_ratio_current is not None
                        else None
                    ),
                    "macd_cross_mode": macd_mode,
                    "macd_cross_days_ago": macd_age,
                    "rsi_cross_days_ago": rsi_age,
                    "rsi_cross_days_ago_all": rsi_ages,
                    "stoch_cross_days_ago": stoch_age,
                    "event_sequence": sequence,
                    "status": "Sequence aligned" if event_pairs else "Volume aligned",
                    "score": score,
                    "reasons": (
                        [f"RSI now {current_rsi:.1f}"]
                        + [f"Avg volume 20d {avg_volume_20:,.0f}"]
                        + (
                            [
                                f"{_rsi_cross_label(str(event['rsi_cross_mode']), float(event['rsi_cross_value']))} {int(age)}d ago"
                                for event, age in zip(rsi_events, rsi_ages or [])
                            ]
                            if rsi_enabled
                            else []
                        )
                        + (
                            [
                                f"{_macd_cross_label(macd_mode)} {int(macd_age or 0)}d ago"
                            ]
                            if macd_enabled
                            else []
                        )
                        + (
                            [
                                f"{_stoch_cross_label(stoch_mode, stoch_level, stoch_region)} {int(stoch_age or 0)}d ago"
                            ]
                            if stoch_enabled
                            else []
                        )
                        + (
                            [
                                f"{_supertrend_cross_label(supertrend_mode)} {int(supertrend_age or 0)}d ago"
                            ]
                            if supertrend_enabled
                            else []
                        )
                        + (
                            [
                                f"EMA {ema_fast_period}/{ema_slow_period} cross {int(ema_relationship_age or 0)}d ago"
                            ]
                            if ema_relationship_enabled
                            else []
                        )
                        + (
                            [
                                f"{str(result['price_ema_source']).title()} {str(result['price_ema_cross_mode']).replace('_', ' ')} EMA {int(result['price_ema_period'])} {int(result['price_ema_age'] or 0)}d ago"
                                for result in price_ema_event_results
                            ]
                            if price_ema_enabled
                            else []
                        )
                        + (
                            [
                                f"{_ema_flatten_label(ema_flatten_period, ema_flatten_state)} {int(ema_flatten_age or 0)}d ago"
                            ]
                            if ema_flatten_enabled
                            else []
                        )
                        + (
                            [
                                f"{_volume_spike_label(volume_spike_period, volume_spike_multiplier)} {int(volume_spike_age or 0)}d ago"
                            ]
                            if bool(normalized_filters["volume_spike_enabled"])
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
