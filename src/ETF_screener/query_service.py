"""Shared query service for Parquet-backed ETF data exploration."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.market_data_service import (
    MarketDataRefresher,
    filter_low_vitality_nasdaq_tickers,
)
from ETF_screener.storage import ParquetStorage

SIGNAL_SCAN_DATASET = "signal_scan"
PRICE_HISTORY_DATASET = "price_history"
SHORTLIST_DATASET = "shortlist"
QUERY_DATASETS = (SIGNAL_SCAN_DATASET, PRICE_HISTORY_DATASET, SHORTLIST_DATASET)
DEFAULT_SIGNAL_SCAN_COLUMNS = (
    "ticker",
    "calibrated_reliability_score",
    "reliability_score",
    "historical_success_rate_20d",
    "historical_failure_rate_10d",
    "historical_sample_size",
    "signal_age_days",
    "close",
    "ema_50",
    "ema_200",
    "supertrend",
    "matched_rules",
    "warning_flags",
)
DEFAULT_PRICE_HISTORY_COLUMNS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "dividends",
    "ema_50",
    "supertrend",
    "signal",
)
DEFAULT_SHORTLIST_COLUMNS = (
    "ticker",
    "label",
    "final_score",
    "technical_score",
    "product_score",
    "exposure_score",
    "recent_entry_days",
    "close",
    "volume",
    "name",
    "region",
    "as_of_date",
)
SHORTLIST_SORT_OPTIONS = (
    "final_score",
    "technical_score",
    "product_score",
    "exposure_score",
    "volume",
    "recent_entry_days",
    "ticker",
    "label",
    "as_of_date",
)
SIGNAL_PRESETS = {
    "trend_forming": {
        "label": "Trend Forming",
        "default_age_max": 5,
        "default_min_reliability": 6.0,
        "description": "Recent bullish transition with enough confirmation to be actionable now.",
    },
    "trend_weakening": {
        "label": "Trend Weakening",
        "default_age_max": 3,
        "default_min_reliability": 6.0,
        "description": "Recent signs that an existing uptrend is losing support or flipping weaker.",
    },
    "downtrend_turnaround": {
        "label": "Downtrend Turnaround",
        "default_age_max": 5,
        "default_min_reliability": 6.8,
        "description": "A damaged chart that has only recently started repairing, with bull-trap filters applied.",
    },
}
_COLUMN_ALIASES = {
    "date": "date",
    "datetime": "date",
    "ticker": "ticker",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "dividends": "dividends",
    "dividend": "dividends",
    "ema50": "ema_50",
    "ema_50": "ema_50",
    "ema200": "ema_200",
    "ema_200": "ema_200",
    "supertrend": "supertrend",
    "signal": "signal",
}
HISTORICAL_FORWARD_WINDOWS = (5, 10, 20)
HISTORICAL_PATTERN_MIN_SAMPLE = 6
HISTORICAL_SIGNAL_MIN_SAMPLE = 12


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_safe_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if pd.isna(value) else value
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return _json_safe_cell(value.item())
        except Exception:
            pass
    return value


def _frame_to_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        rows.append({str(col): _json_safe_cell(row[col]) for col in frame.columns})
    return rows


class ETFQueryService:
    """Provide a stable query layer over Parquet and cached artifacts."""

    def __init__(
        self,
        *,
        db: ETFDatabase | None = None,
        storage: ParquetStorage | None = None,
    ) -> None:
        self.db = db or ETFDatabase()
        self.storage = storage or ParquetStorage()

    def query_catalog(self) -> dict[str, Any]:
        """Describe the currently supported query datasets and controls."""
        return {
            "datasets": [
                {
                    "key": SIGNAL_SCAN_DATASET,
                    "label": "Signal Scan",
                    "description": "Actionable tickers now, by chosen universe and named signal preset.",
                },
                {
                    "key": PRICE_HISTORY_DATASET,
                    "label": "Ticker History",
                    "description": "Parquet-backed OHLCV and indicator history for one ticker.",
                },
                {
                    "key": SHORTLIST_DATASET,
                    "label": "Shortlist Snapshot",
                    "description": "Cached shortlist artifacts with labels and ETF scoring.",
                },
            ],
            SIGNAL_SCAN_DATASET: {
                "default_columns": list(DEFAULT_SIGNAL_SCAN_COLUMNS),
                "signals": [
                    {
                        "key": key,
                        "label": value["label"],
                        "default_age_max": value["default_age_max"],
                        "default_min_reliability": value["default_min_reliability"],
                        "description": value["description"],
                    }
                    for key, value in SIGNAL_PRESETS.items()
                ],
                "sources": [
                    {"key": "xetra", "label": "Xetra"},
                    {"key": "nasdaq", "label": "Nasdaq"},
                    {"key": "sweden", "label": "Sweden"},
                    {"key": "list", "label": "My List"},
                    {"key": "all_lists", "label": "All Lists"},
                ],
                "default_limit": 50,
                "max_preview_rows": 500,
            },
            PRICE_HISTORY_DATASET: {
                "default_columns": list(DEFAULT_PRICE_HISTORY_COLUMNS),
                "default_days": 90,
                "max_preview_rows": 500,
            },
            SHORTLIST_DATASET: {
                "default_columns": list(DEFAULT_SHORTLIST_COLUMNS),
                "labels": ["All", "Buy", "Watch", "Skip"],
                "sort_options": list(SHORTLIST_SORT_OPTIONS),
                "default_limit": 50,
                "max_preview_rows": 500,
            },
        }

    def list_available_tickers(self) -> list[str]:
        """Return the union of tickers visible in Parquet storage and SQLite."""
        symbols = {
            str(item).upper()
            for item in list(self.storage.list_available_etfs())
            + list(self.db.get_tickers())
            if str(item).strip()
        }
        return sorted(symbols)

    def run_query(
        self,
        dataset: str,
        *,
        ticker: str | None = None,
        source: str | None = None,
        signal: str | None = None,
        min_reliability: float | None = None,
        signal_age_max: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        days: int | None = None,
        columns: str | Iterable[str] | None = None,
        limit: int | None = None,
        label: str | None = None,
        sort_by: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch a named dataset query."""
        normalized = str(dataset or "").strip().lower()
        if normalized == SIGNAL_SCAN_DATASET:
            return self.query_signal_scan(
                source=source or "xetra",
                signal=signal or "trend_forming",
                min_reliability=min_reliability,
                signal_age_max=signal_age_max,
                columns=columns,
                limit=limit,
            )
        if normalized == PRICE_HISTORY_DATASET:
            return self.query_price_history(
                ticker=ticker or "",
                start_date=start_date,
                end_date=end_date,
                days=days,
                columns=columns,
                limit=limit,
            )
        if normalized == SHORTLIST_DATASET:
            return self.query_shortlist(
                label=label,
                columns=columns,
                limit=limit,
                sort_by=sort_by,
            )
        raise ValueError(f"Unsupported query dataset: {dataset}")

    def query_signal_scan(
        self,
        *,
        source: str = "xetra",
        signal: str = "trend_forming",
        min_reliability: float | None = None,
        signal_age_max: int | None = None,
        columns: str | Iterable[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Return actionable tickers for a named live signal preset."""
        normalized_signal = str(signal or "").strip().lower()
        if normalized_signal not in SIGNAL_PRESETS:
            raise ValueError(f"Unsupported signal preset: {signal}")

        signal_meta = SIGNAL_PRESETS[normalized_signal]
        safe_limit = self._normalize_limit(limit, default=50)
        safe_age_max = max(0, int(signal_age_max or signal_meta["default_age_max"]))
        safe_min_reliability = float(
            min_reliability
            if min_reliability is not None
            else signal_meta["default_min_reliability"]
        )
        tickers = self._load_universe_tickers(source)
        matches: list[dict[str, Any]] = []
        historical_events: list[dict[str, Any]] = []

        worker_count = min(8, max(1, len(tickers)))
        with ThreadPoolExecutor(max_workers=worker_count or 1) as executor:
            futures = {
                executor.submit(
                    self._analyze_signal_ticker, ticker, normalized_signal, safe_age_max
                ): ticker
                for ticker in tickers
            }
            for future in as_completed(futures):
                analysis = future.result()
                historical_events.extend(analysis.get("history_events", []))
                row = analysis.get("current")
                if not row:
                    continue
                if float(row.get("reliability_score") or 0.0) < safe_min_reliability:
                    continue
                matches.append(row)

        history_profile = self._build_signal_history_profile(
            historical_events,
            signal=normalized_signal,
        )
        matches = [
            self._apply_historical_calibration(row, normalized_signal, history_profile)
            for row in matches
        ]
        matches = sorted(
            matches,
            key=lambda row: (
                -float(
                    row.get("calibrated_reliability_score")
                    or row.get("reliability_score")
                    or 0.0
                ),
                -float(row.get("reliability_score") or 0.0),
                -float(row.get("historical_success_rate_20d") or 0.0),
                int(row.get("signal_age_days") or 9999),
                str(row.get("ticker") or ""),
            ),
        )
        available_columns = (
            list(matches[0].keys()) if matches else list(DEFAULT_SIGNAL_SCAN_COLUMNS)
        )
        selected_columns = self._resolve_columns(
            columns,
            available_columns,
            default_columns=DEFAULT_SIGNAL_SCAN_COLUMNS,
        )
        preview_rows = matches[:safe_limit]
        if selected_columns:
            preview_rows = [
                {column: row.get(column) for column in selected_columns}
                for row in preview_rows
            ]
        latest_market_date = self.db.get_latest_market_date()

        return {
            "dataset": SIGNAL_SCAN_DATASET,
            "label": "Signal Scan",
            "source": str(source or "xetra").strip().lower() or "xetra",
            "params": {
                "signal": normalized_signal,
                "signal_age_max": safe_age_max,
                "min_reliability": round(safe_min_reliability, 2),
                "limit": safe_limit,
            },
            "columns": selected_columns,
            "available_columns": available_columns,
            "row_count": int(len(matches)),
            "returned_rows": int(len(preview_rows)),
            "rows": preview_rows,
            "summary": {
                "signal": normalized_signal,
                "signal_label": signal_meta["label"],
                "scanned_tickers": int(len(tickers)),
                "matched_tickers": int(len(matches)),
                "latest_market_date": latest_market_date,
                "historical_signal_events": int(
                    (history_profile.get("signal") or {}).get("sample_size") or 0
                ),
                "top_ticker": str(matches[0].get("ticker")) if matches else None,
                "top_score": (
                    round(
                        float(
                            matches[0].get("calibrated_reliability_score")
                            or matches[0].get("reliability_score")
                            or 0.0
                        ),
                        2,
                    )
                    if matches
                    else None
                ),
            },
        }

    def query_price_history(
        self,
        *,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
        days: int | None = None,
        columns: str | Iterable[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Query one ticker's historical Parquet-backed price data."""
        symbol = str(ticker or "").strip().upper()
        if not symbol:
            raise ValueError("Ticker is required for price_history queries")

        raw_frame, source = self._load_price_history_frame(symbol)
        if raw_frame.empty:
            return {
                "dataset": PRICE_HISTORY_DATASET,
                "label": "Ticker History",
                "ticker": symbol,
                "source": source,
                "params": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": int(days) if days is not None else None,
                    "limit": self._normalize_limit(limit),
                },
                "columns": [],
                "available_columns": [],
                "row_count": 0,
                "returned_rows": 0,
                "rows": [],
                "summary": {
                    "earliest_date": None,
                    "latest_date": None,
                    "latest_close": None,
                    "average_volume": None,
                },
            }

        frame = self._normalize_price_history_frame(raw_frame)
        if start_date:
            frame = frame.loc[frame["date"] >= pd.to_datetime(start_date)].copy()
        if end_date:
            frame = frame.loc[frame["date"] <= pd.to_datetime(end_date)].copy()
        if not start_date and not end_date:
            safe_days = max(1, int(days or 90))
            frame = frame.tail(safe_days).copy()

        frame = frame.sort_values("date").reset_index(drop=True)
        available_columns = list(frame.columns)
        selected_columns = self._resolve_columns(
            columns,
            available_columns,
            default_columns=DEFAULT_PRICE_HISTORY_COLUMNS,
        )
        preview_limit = self._normalize_limit(limit)
        preview = (
            frame.loc[:, selected_columns].tail(preview_limit).reset_index(drop=True)
        )

        return {
            "dataset": PRICE_HISTORY_DATASET,
            "label": "Ticker History",
            "ticker": symbol,
            "source": source,
            "params": {
                "start_date": start_date,
                "end_date": end_date,
                "days": int(days) if days is not None else None,
                "limit": preview_limit,
            },
            "columns": selected_columns,
            "available_columns": available_columns,
            "row_count": int(len(frame)),
            "returned_rows": int(len(preview)),
            "rows": _frame_to_rows(preview),
            "summary": {
                "earliest_date": (
                    _json_safe_cell(frame["date"].iloc[0]) if not frame.empty else None
                ),
                "latest_date": (
                    _json_safe_cell(frame["date"].iloc[-1]) if not frame.empty else None
                ),
                "latest_close": (
                    _safe_float(frame["close"].iloc[-1])
                    if "close" in frame.columns and not frame.empty
                    else None
                ),
                "average_volume": (
                    round(float(frame["volume"].dropna().mean()), 2)
                    if "volume" in frame.columns and not frame["volume"].dropna().empty
                    else None
                ),
            },
        }

    def query_shortlist(
        self,
        *,
        label: str | None = None,
        columns: str | Iterable[str] | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
    ) -> dict[str, Any]:
        """Query the cached shortlist artifact snapshot."""
        normalized_label = str(label or "").strip().title()
        shortlist_label = (
            normalized_label if normalized_label in {"Buy", "Watch", "Skip"} else None
        )
        frame = self.db.get_shortlist(limit=None, label=shortlist_label)
        if not frame.empty:
            sort_key = str(sort_by or "final_score").strip()
            if sort_key not in SHORTLIST_SORT_OPTIONS:
                sort_key = "final_score"
            ascending = sort_key in {"ticker", "label", "as_of_date"}
            if sort_key in frame.columns:
                frame = frame.sort_values(
                    sort_key, ascending=ascending, na_position="last"
                ).reset_index(drop=True)

        available_columns = list(frame.columns)
        selected_columns = self._resolve_columns(
            columns,
            available_columns,
            default_columns=DEFAULT_SHORTLIST_COLUMNS,
        )
        preview_limit = self._normalize_limit(limit, default=50)
        preview = (
            frame.loc[:, selected_columns].head(preview_limit).reset_index(drop=True)
            if selected_columns
            else frame.head(preview_limit).reset_index(drop=True)
        )

        return {
            "dataset": SHORTLIST_DATASET,
            "label": "Shortlist Snapshot",
            "source": "sqlite_artifacts",
            "params": {
                "label": shortlist_label or "All",
                "limit": preview_limit,
                "sort_by": str(sort_by or "final_score").strip() or "final_score",
            },
            "columns": selected_columns,
            "available_columns": available_columns,
            "row_count": int(len(frame)),
            "returned_rows": int(len(preview)),
            "rows": _frame_to_rows(preview),
            "summary": {
                "as_of_date": (
                    str(frame["as_of_date"].iloc[0])
                    if not frame.empty and "as_of_date" in frame.columns
                    else None
                ),
                "buy_count": (
                    int((frame["label"] == "Buy").sum())
                    if "label" in frame.columns
                    else 0
                ),
                "watch_count": (
                    int((frame["label"] == "Watch").sum())
                    if "label" in frame.columns
                    else 0
                ),
                "skip_count": (
                    int((frame["label"] == "Skip").sum())
                    if "label" in frame.columns
                    else 0
                ),
                "best_score": (
                    round(float(frame["final_score"].max()), 2)
                    if not frame.empty and "final_score" in frame.columns
                    else None
                ),
            },
        }

    def _load_price_history_frame(self, ticker: str) -> tuple[pd.DataFrame, str]:
        frame = self.storage.load_etf_data(ticker)
        if not frame.empty:
            return frame.copy(), "parquet"

        legacy_path = Path("data") / f"{ticker.lower()}_data.parquet"
        if legacy_path.exists():
            try:
                return pd.read_parquet(legacy_path).copy(), "legacy_parquet"
            except Exception:
                pass

        db_frame = self.db.get_etf_data(ticker)
        if not db_frame.empty:
            return db_frame.copy(), "database_fallback"
        return pd.DataFrame(), "parquet"

    def _load_universe_tickers(self, source: str) -> list[str]:
        normalized_source = self._normalize_source(source)
        metadata_path, collection_mode = self._market_source_config(normalized_source)
        refresher = MarketDataRefresher(
            db_path=str(self.db.db_path),
            etfs_file=str(metadata_path),
            collection_mode=collection_mode,
            storage=self.storage,
        )
        tickers = refresher._load_tracked_tickers()
        if normalized_source == "nasdaq":
            return filter_low_vitality_nasdaq_tickers(
                db_path=str(self.db.db_path),
                latest_market_date=self.db.get_latest_market_date(),
                tickers=tickers,
            )
        return tickers

    def _analyze_signal_ticker(
        self,
        ticker: str,
        signal: str,
        signal_age_max: int,
    ) -> dict[str, Any]:
        frame, source = self._load_price_history_frame(ticker)
        if frame.empty:
            return {"current": None, "history_events": []}
        normalized = (
            self._normalize_price_history_frame(frame).tail(220).reset_index(drop=True)
        )
        if len(normalized) < 25:
            return {"current": None, "history_events": []}
        current = self._evaluate_signal_frame(
            ticker, signal, normalized, source, signal_age_max
        )
        history_events = self._collect_historical_signal_events(
            ticker,
            signal,
            normalized,
            source,
            signal_age_max,
        )
        return {"current": current, "history_events": history_events}

    def _evaluate_signal_frame(
        self,
        ticker: str,
        signal: str,
        frame: pd.DataFrame,
        source: str,
        signal_age_max: int,
    ) -> dict[str, Any] | None:
        if signal == "trend_forming":
            return self._evaluate_trend_forming(ticker, frame, source, signal_age_max)
        if signal == "trend_weakening":
            return self._evaluate_trend_weakening(ticker, frame, source, signal_age_max)
        if signal == "downtrend_turnaround":
            return self._evaluate_downtrend_turnaround(
                ticker, frame, source, signal_age_max
            )
        return None

    def _evaluate_trend_forming(
        self,
        ticker: str,
        frame: pd.DataFrame,
        source: str,
        signal_age_max: int,
    ) -> dict[str, Any] | None:
        metrics = self._signal_metrics(frame)
        current = metrics["current"]
        event_ages = [
            age
            for age in [metrics["reclaim_age"], metrics["supertrend_flip_up_age"]]
            if age is not None
        ]
        signal_age = min(event_ages) if event_ages else None
        matched_rules: list[str] = []
        warning_flags: list[str] = []
        score = 0.0

        if current["close"] > current["ema_50"]:
            matched_rules.append("close_above_ema50")
            score += 2.0
        else:
            warning_flags.append("below_ema50")
        if metrics["ema_50_slope_pct"] > 0.12:
            matched_rules.append("ema50_rising")
            score += 2.0
        elif metrics["ema_50_slope_pct"] > 0:
            matched_rules.append("ema50_turning_up")
            score += 1.0
        else:
            warning_flags.append("ema50_flat_or_falling")
        if current["supertrend_ready"] and current["close"] > current["supertrend"]:
            matched_rules.append("supertrend_bullish")
            score += 2.0
        elif current["supertrend_ready"]:
            warning_flags.append("below_supertrend")
        if (
            metrics["reclaim_age"] is not None
            and metrics["reclaim_age"] <= signal_age_max
        ):
            matched_rules.append("recent_ema50_reclaim")
            score += 2.0
        if (
            metrics["supertrend_flip_up_age"] is not None
            and metrics["supertrend_flip_up_age"] <= signal_age_max
        ):
            matched_rules.append("recent_supertrend_flip")
            score += 1.5
        if metrics["volume_confirmed"]:
            matched_rules.append("volume_confirmed")
            score += 1.0
        if metrics["higher_low_bias"]:
            matched_rules.append("higher_low_bias")
            score += 1.0
        if metrics["extension_pct"] > 8.0:
            warning_flags.append("extended_above_ema50")
            score -= 1.5
        elif metrics["extension_pct"] > 5.0:
            warning_flags.append("slightly_extended")
            score -= 0.5
        if signal_age is None:
            warning_flags.append("no_recent_trigger")
            return None
        if signal_age > signal_age_max:
            return None
        if current["close"] <= current["ema_50"]:
            return None
        if current["supertrend_ready"] and current["close"] <= current["supertrend"]:
            return None

        reliability_score = round(max(0.0, min(score, 10.0)), 2)
        return {
            "ticker": ticker,
            "reliability_score": reliability_score,
            "signal_age_days": int(signal_age),
            "signal_state": "forming",
            "last_date": _json_safe_cell(frame["date"].iloc[-1]),
            "close": round(float(current["close"]), 4),
            "ema_50": round(float(current["ema_50"]), 4),
            "ema_200": (
                round(float(current["ema_200"]), 4)
                if current["ema_200_ready"]
                else None
            ),
            "supertrend": (
                round(float(current["supertrend"]), 4)
                if current["supertrend_ready"]
                else None
            ),
            "volume": _safe_int(current["volume"]),
            "extension_pct": round(metrics["extension_pct"], 2),
            "ema_50_slope_pct": round(metrics["ema_50_slope_pct"], 3),
            "matched_rules": matched_rules,
            "warning_flags": warning_flags,
            "data_source": source,
        }

    def _collect_historical_signal_events(
        self,
        ticker: str,
        signal: str,
        frame: pd.DataFrame,
        source: str,
        signal_age_max: int,
    ) -> list[dict[str, Any]]:
        candidate_indices = self._candidate_signal_indices(
            frame, signal, signal_age_max
        )
        if not candidate_indices:
            return []

        events: list[dict[str, Any]] = []
        last_event_index = -10_000
        for idx in candidate_indices:
            if idx - last_event_index <= signal_age_max:
                continue
            prefix = frame.iloc[: idx + 1].copy()
            row = self._evaluate_signal_frame(
                ticker, signal, prefix, source, signal_age_max
            )
            if not row:
                continue
            outcome = self._measure_signal_outcomes(frame, idx, signal)
            if outcome is None:
                continue
            last_event_index = idx
            events.append(
                {
                    "ticker": ticker,
                    "signal": signal,
                    "event_index": idx,
                    "event_date": _json_safe_cell(frame["date"].iloc[idx]),
                    "pattern_bucket": self._signal_pattern_bucket(signal, row),
                    "rule_reliability_score": round(
                        float(row.get("reliability_score") or 0.0), 2
                    ),
                    "signal_age_days": int(row.get("signal_age_days") or 0),
                    **outcome,
                }
            )
        return events

    def _candidate_signal_indices(
        self,
        frame: pd.DataFrame,
        signal: str,
        signal_age_max: int,
    ) -> list[int]:
        max_forward_window = max(HISTORICAL_FORWARD_WINDOWS)
        if len(frame) <= max_forward_window + 25:
            return []

        close = pd.to_numeric(frame.get("close"), errors="coerce")
        ema_50 = pd.to_numeric(frame.get("ema_50"), errors="coerce")
        supertrend = pd.to_numeric(frame.get("supertrend"), errors="coerce")
        above_ema = (close > ema_50).fillna(False)
        supertrend_ready = supertrend.notna()
        above_supertrend = (
            (close > supertrend).where(supertrend_ready, False).fillna(False)
        )

        prev_ema = above_ema.shift(1, fill_value=False).astype(bool)
        prev_supertrend = above_supertrend.shift(1, fill_value=False).astype(bool)
        cross_up_ema = [
            idx for idx, value in enumerate((above_ema & (~prev_ema)).tolist()) if value
        ]
        cross_down_ema = [
            idx for idx, value in enumerate(((~above_ema) & prev_ema).tolist()) if value
        ]
        cross_up_supertrend = [
            idx
            for idx, value in enumerate(
                (above_supertrend & (~prev_supertrend)).tolist()
            )
            if value
        ]
        cross_down_supertrend = [
            idx
            for idx, value in enumerate(
                ((~above_supertrend) & prev_supertrend).tolist()
            )
            if value
        ]

        if signal in {"trend_forming", "downtrend_turnaround"}:
            base_indices = sorted(set(cross_up_ema + cross_up_supertrend))
        else:
            base_indices = sorted(set(cross_down_ema + cross_down_supertrend))

        max_idx = len(frame) - 1 - max_forward_window
        candidates: set[int] = set()
        for base_idx in base_indices:
            if base_idx < 25 or base_idx > max_idx:
                continue
            for offset in range(max(1, signal_age_max) + 1):
                candidate_idx = base_idx + offset
                if candidate_idx > max_idx:
                    break
                candidates.add(candidate_idx)
        return sorted(candidates)

    def _measure_signal_outcomes(
        self,
        frame: pd.DataFrame,
        event_index: int,
        signal: str,
    ) -> dict[str, Any] | None:
        close_series = pd.to_numeric(frame.get("close"), errors="coerce")
        low_series = pd.to_numeric(frame.get("low"), errors="coerce")
        high_series = pd.to_numeric(frame.get("high"), errors="coerce")
        ema_50_series = pd.to_numeric(frame.get("ema_50"), errors="coerce")

        if event_index >= len(close_series):
            return None
        entry_close = _safe_float(close_series.iloc[event_index])
        if not entry_close:
            return None

        returns: dict[int, float | None] = {}
        for window in HISTORICAL_FORWARD_WINDOWS:
            target_idx = event_index + window
            if target_idx >= len(close_series):
                return None
            target_close = _safe_float(close_series.iloc[target_idx])
            returns[window] = (
                ((target_close - entry_close) / entry_close) * 100.0
                if target_close is not None
                else None
            )

        next_10 = frame.iloc[event_index + 1 : event_index + 11].copy()
        if len(next_10) < 10:
            return None

        if signal in {"trend_forming", "downtrend_turnaround"}:
            next_lows = pd.to_numeric(
                next_10.get("low", next_10.get("close")), errors="coerce"
            )
            min_low = _safe_float(next_lows.min())
            adverse_excursion = (
                ((min_low - entry_close) / entry_close) * 100.0
                if min_low is not None
                else None
            )
            failure_10d = bool(
                (returns[10] is not None and returns[10] <= -3.0)
                or (
                    not ema_50_series.iloc[event_index + 1 : event_index + 11].empty
                    and bool(
                        (
                            close_series.iloc[event_index + 1 : event_index + 11]
                            < ema_50_series.iloc[event_index + 1 : event_index + 11]
                        )
                        .fillna(False)
                        .any()
                    )
                )
                or (adverse_excursion is not None and adverse_excursion <= -6.0)
            )
            success_20d = bool(
                returns[20] is not None and returns[20] >= 4.0 and not failure_10d
            )
        else:
            next_highs = pd.to_numeric(
                next_10.get("high", next_10.get("close")), errors="coerce"
            )
            max_high = _safe_float(next_highs.max())
            adverse_excursion = (
                ((max_high - entry_close) / entry_close) * 100.0
                if max_high is not None
                else None
            )
            failure_10d = bool(
                (returns[10] is not None and returns[10] >= 3.0)
                or (
                    not ema_50_series.iloc[event_index + 1 : event_index + 11].empty
                    and bool(
                        (
                            close_series.iloc[event_index + 1 : event_index + 11]
                            > ema_50_series.iloc[event_index + 1 : event_index + 11]
                        )
                        .fillna(False)
                        .any()
                    )
                )
                or (adverse_excursion is not None and adverse_excursion >= 6.0)
            )
            success_20d = bool(
                returns[20] is not None and returns[20] <= -4.0 and not failure_10d
            )

        return {
            "forward_return_5d": round(float(returns[5] or 0.0), 2),
            "forward_return_10d": round(float(returns[10] or 0.0), 2),
            "forward_return_20d": round(float(returns[20] or 0.0), 2),
            "adverse_excursion_10d": round(float(adverse_excursion or 0.0), 2),
            "success_20d": success_20d,
            "failure_10d": failure_10d,
        }

    def _signal_pattern_bucket(self, signal: str, row: dict[str, Any]) -> str:
        matched_rules = {str(item) for item in row.get("matched_rules", [])}
        signal_age = int(row.get("signal_age_days") or 99)
        age_bucket = "fresh" if signal_age <= 2 else "aging"
        close_value = _safe_float(row.get("close"))
        ema_200_value = _safe_float(row.get("ema_200"))
        above_ema200 = bool(
            close_value is not None
            and ema_200_value is not None
            and close_value >= ema_200_value
        )
        ema200_bucket = "above200" if above_ema200 else "below200"

        if signal == "trend_forming":
            extension_pct = _safe_float(row.get("extension_pct")) or 0.0
            extension_bucket = "extended" if extension_pct > 5.0 else "tight"
            volume_bucket = "volume" if "volume_confirmed" in matched_rules else "quiet"
            slope_bucket = (
                "strong_slope"
                if "ema50_rising" in matched_rules
                else "turning_up" if "ema50_turning_up" in matched_rules else "flat"
            )
            return "|".join(
                [
                    signal,
                    age_bucket,
                    ema200_bucket,
                    volume_bucket,
                    extension_bucket,
                    slope_bucket,
                ]
            )

        if signal == "downtrend_turnaround":
            drawdown_pct = _safe_float(row.get("drawdown_120_pct")) or 0.0
            drawdown_bucket = (
                "deep_damage"
                if drawdown_pct <= -20.0
                else "damaged" if drawdown_pct <= -12.0 else "shallow_damage"
            )
            hold_bucket = (
                "held" if int(row.get("reclaim_hold_days") or 0) >= 3 else "brief_hold"
            )
            volume_bucket = "volume" if "volume_confirmed" in matched_rules else "quiet"
            return "|".join(
                [
                    signal,
                    age_bucket,
                    ema200_bucket,
                    drawdown_bucket,
                    hold_bucket,
                    volume_bucket,
                ]
            )

        downside_bucket = (
            "followthrough"
            if "downside_followthrough" in matched_rules
            else "early_loss"
        )
        slope_bucket = (
            "turning_down"
            if "ema50_turning_down" in matched_rules
            else "flattening" if "ema50_flattening" in matched_rules else "mixed"
        )
        return "|".join(
            [signal, age_bucket, ema200_bucket, downside_bucket, slope_bucket]
        )

    def _build_signal_history_profile(
        self,
        events: list[dict[str, Any]],
        *,
        signal: str,
    ) -> dict[str, Any]:
        relevant = [event for event in events if str(event.get("signal")) == signal]
        if not relevant:
            return {"signal": None, "by_bucket": {}}

        by_bucket: dict[str, list[dict[str, Any]]] = {}
        for event in relevant:
            bucket = str(event.get("pattern_bucket") or "")
            by_bucket.setdefault(bucket, []).append(event)

        return {
            "signal": self._aggregate_historical_stats(relevant),
            "by_bucket": {
                bucket: self._aggregate_historical_stats(bucket_events)
                for bucket, bucket_events in by_bucket.items()
            },
        }

    def _aggregate_historical_stats(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sample_size = len(events)
        if sample_size == 0:
            return {
                "sample_size": 0,
                "success_rate_20d": None,
                "failure_rate_10d": None,
                "median_return_20d": None,
                "median_return_10d": None,
                "median_adverse_excursion_10d": None,
            }

        return_20d = pd.Series(
            [_safe_float(event.get("forward_return_20d")) for event in events],
            dtype="float64",
        ).dropna()
        return_10d = pd.Series(
            [_safe_float(event.get("forward_return_10d")) for event in events],
            dtype="float64",
        ).dropna()
        adverse_10d = pd.Series(
            [_safe_float(event.get("adverse_excursion_10d")) for event in events],
            dtype="float64",
        ).dropna()
        return {
            "sample_size": sample_size,
            "success_rate_20d": round(
                sum(bool(event.get("success_20d")) for event in events) / sample_size, 3
            ),
            "failure_rate_10d": round(
                sum(bool(event.get("failure_10d")) for event in events) / sample_size, 3
            ),
            "median_return_20d": (
                round(float(return_20d.median()), 2) if not return_20d.empty else None
            ),
            "median_return_10d": (
                round(float(return_10d.median()), 2) if not return_10d.empty else None
            ),
            "median_adverse_excursion_10d": (
                round(float(adverse_10d.median()), 2) if not adverse_10d.empty else None
            ),
        }

    def _pick_historical_stats_for_row(
        self,
        row: dict[str, Any],
        signal: str,
        history_profile: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str]:
        pattern_bucket = self._signal_pattern_bucket(signal, row)
        bucket_stats = (history_profile.get("by_bucket") or {}).get(pattern_bucket)
        signal_stats = history_profile.get("signal")

        if (
            bucket_stats
            and int(bucket_stats.get("sample_size") or 0)
            >= HISTORICAL_PATTERN_MIN_SAMPLE
        ):
            return bucket_stats, "pattern_bucket"
        if (
            signal_stats
            and int(signal_stats.get("sample_size") or 0)
            >= HISTORICAL_SIGNAL_MIN_SAMPLE
        ):
            return signal_stats, "signal_fallback"
        if bucket_stats and int(bucket_stats.get("sample_size") or 0) > 0:
            return bucket_stats, "pattern_bucket_thin"
        if signal_stats and int(signal_stats.get("sample_size") or 0) > 0:
            return signal_stats, "signal_fallback_thin"
        return None, "no_history"

    def _apply_historical_calibration(
        self,
        row: dict[str, Any],
        signal: str,
        history_profile: dict[str, Any],
    ) -> dict[str, Any]:
        enriched = dict(row)
        raw_score = round(float(enriched.get("reliability_score") or 0.0), 2)
        stats, basis = self._pick_historical_stats_for_row(
            enriched, signal, history_profile
        )

        enriched["rule_reliability_score"] = raw_score
        enriched["historical_match_basis"] = basis
        if not stats:
            enriched["calibrated_reliability_score"] = raw_score
            enriched["historical_sample_size"] = 0
            enriched["historical_success_rate_20d"] = None
            enriched["historical_failure_rate_10d"] = None
            enriched["historical_median_return_20d"] = None
            enriched["historical_median_return_10d"] = None
            enriched["historical_confidence"] = "none"
            return enriched

        sample_size = int(stats.get("sample_size") or 0)
        success_rate = _safe_float(stats.get("success_rate_20d"))
        failure_rate = _safe_float(stats.get("failure_rate_10d"))
        median_return_20d = _safe_float(stats.get("median_return_20d"))

        confidence_scale = min(sample_size / 24.0, 1.0)
        adjustment = 0.0
        if success_rate is not None:
            if success_rate >= 0.65:
                adjustment += 0.7
            elif success_rate >= 0.55:
                adjustment += 0.35
            elif success_rate <= 0.4:
                adjustment -= 0.7
        if failure_rate is not None:
            if failure_rate <= 0.15:
                adjustment += 0.25
            elif failure_rate >= 0.35:
                adjustment -= 0.7
        if median_return_20d is not None:
            if signal in {"trend_forming", "downtrend_turnaround"}:
                if median_return_20d >= 6.0:
                    adjustment += 0.3
                elif median_return_20d <= 0.0:
                    adjustment -= 0.3
            else:
                if median_return_20d <= -6.0:
                    adjustment += 0.3
                elif median_return_20d >= 0.0:
                    adjustment -= 0.3

        calibrated_score = max(
            0.0, min(raw_score + (adjustment * confidence_scale), 10.0)
        )
        enriched["calibrated_reliability_score"] = round(calibrated_score, 2)
        enriched["historical_sample_size"] = sample_size
        enriched["historical_success_rate_20d"] = (
            round(success_rate, 3) if success_rate is not None else None
        )
        enriched["historical_failure_rate_10d"] = (
            round(failure_rate, 3) if failure_rate is not None else None
        )
        enriched["historical_median_return_20d"] = (
            round(median_return_20d, 2) if median_return_20d is not None else None
        )
        enriched["historical_median_return_10d"] = (
            round(float(stats.get("median_return_10d")), 2)
            if _safe_float(stats.get("median_return_10d")) is not None
            else None
        )
        enriched["historical_confidence"] = (
            "high"
            if sample_size >= 24
            else (
                "medium"
                if sample_size >= HISTORICAL_SIGNAL_MIN_SAMPLE
                else (
                    "low"
                    if sample_size >= HISTORICAL_PATTERN_MIN_SAMPLE
                    else "exploratory"
                )
            )
        )
        return enriched

    def _evaluate_trend_weakening(
        self,
        ticker: str,
        frame: pd.DataFrame,
        source: str,
        signal_age_max: int,
    ) -> dict[str, Any] | None:
        metrics = self._signal_metrics(frame)
        current = metrics["current"]
        event_ages = [
            age
            for age in [metrics["loss_age"], metrics["supertrend_flip_down_age"]]
            if age is not None
        ]
        signal_age = min(event_ages) if event_ages else None
        matched_rules: list[str] = []
        warning_flags: list[str] = []
        score = 0.0

        if current["close"] < current["ema_50"]:
            matched_rules.append("close_below_ema50")
            score += 2.5
        elif metrics["distance_to_ema_pct"] <= 1.5:
            matched_rules.append("close_near_ema50")
            score += 1.0
        if metrics["ema_50_slope_pct"] < -0.05:
            matched_rules.append("ema50_turning_down")
            score += 2.0
        elif metrics["ema_50_slope_pct"] <= 0.05:
            matched_rules.append("ema50_flattening")
            score += 1.0
        else:
            warning_flags.append("ema50_still_rising")
        if current["supertrend_ready"] and current["close"] < current["supertrend"]:
            matched_rules.append("below_supertrend")
            score += 2.0
        if metrics["loss_age"] is not None and metrics["loss_age"] <= signal_age_max:
            matched_rules.append("recent_ema50_loss")
            score += 2.0
        if (
            metrics["supertrend_flip_down_age"] is not None
            and metrics["supertrend_flip_down_age"] <= signal_age_max
        ):
            matched_rules.append("recent_supertrend_flip_down")
            score += 1.5
        if metrics["downside_followthrough"]:
            matched_rules.append("downside_followthrough")
            score += 1.0
        if current["close"] > current["ema_50"] and not (
            current["supertrend_ready"] and current["close"] < current["supertrend"]
        ):
            warning_flags.append("primary_trend_still_partly_intact")
        if signal_age is None:
            warning_flags.append("no_recent_loss_event")
            return None
        if signal_age > signal_age_max:
            return None

        reliability_score = round(max(0.0, min(score, 10.0)), 2)
        return {
            "ticker": ticker,
            "reliability_score": reliability_score,
            "signal_age_days": int(signal_age),
            "signal_state": "weakening",
            "last_date": _json_safe_cell(frame["date"].iloc[-1]),
            "close": round(float(current["close"]), 4),
            "ema_50": round(float(current["ema_50"]), 4),
            "ema_200": (
                round(float(current["ema_200"]), 4)
                if current["ema_200_ready"]
                else None
            ),
            "supertrend": (
                round(float(current["supertrend"]), 4)
                if current["supertrend_ready"]
                else None
            ),
            "volume": _safe_int(current["volume"]),
            "distance_to_ema_pct": round(metrics["distance_to_ema_pct"], 2),
            "ema_50_slope_pct": round(metrics["ema_50_slope_pct"], 3),
            "matched_rules": matched_rules,
            "warning_flags": warning_flags,
            "data_source": source,
        }

    def _evaluate_downtrend_turnaround(
        self,
        ticker: str,
        frame: pd.DataFrame,
        source: str,
        signal_age_max: int,
    ) -> dict[str, Any] | None:
        metrics = self._signal_metrics(frame)
        current = metrics["current"]
        event_ages = [
            age
            for age in [metrics["reclaim_age"], metrics["supertrend_flip_up_age"]]
            if age is not None
        ]
        signal_age = min(event_ages) if event_ages else None
        matched_rules: list[str] = []
        warning_flags: list[str] = []
        score = 0.0

        if metrics["prior_downtrend_confirmed"]:
            matched_rules.append("prior_downtrend_confirmed")
            score += 2.5
        else:
            warning_flags.append("no_clear_prior_downtrend")
            return None
        if metrics["drawdown_120_pct"] <= -15.0:
            matched_rules.append("deep_prior_drawdown")
            score += 1.5
        elif metrics["drawdown_120_pct"] <= -10.0:
            matched_rules.append("meaningful_prior_drawdown")
            score += 1.0
        if metrics["below_ema50_days_60"] >= 35:
            matched_rules.append("spent_weeks_below_ema50")
            score += 1.0
        if current["close"] > current["ema_50"]:
            matched_rules.append("close_above_ema50")
            score += 1.5
        else:
            warning_flags.append("below_ema50")
            return None
        if (
            metrics["reclaim_age"] is not None
            and metrics["reclaim_age"] <= signal_age_max
        ):
            matched_rules.append("recent_ema50_reclaim")
            score += 1.5
        if (
            metrics["supertrend_flip_up_age"] is not None
            and metrics["supertrend_flip_up_age"] <= signal_age_max
        ):
            matched_rules.append("recent_supertrend_flip")
            score += 1.0
        if metrics["ema_50_slope_pct"] > 0.1:
            matched_rules.append("ema50_turning_up")
            score += 1.5
        else:
            warning_flags.append("ema50_not_turning_up_enough")
        if metrics["reclaim_hold_days"] >= 3:
            matched_rules.append("reclaim_holding")
            score += 1.5
        elif metrics["reclaim_hold_days"] >= 2:
            matched_rules.append("reclaim_holding_briefly")
            score += 0.75
        else:
            warning_flags.append("insufficient_hold_after_reclaim")
            return None
        if current["supertrend_ready"]:
            if (
                current["close"] > current["supertrend"]
                and metrics["supertrend_hold_days"] >= 2
            ):
                matched_rules.append("supertrend_supporting")
                score += 1.0
            elif current["close"] <= current["supertrend"]:
                warning_flags.append("below_supertrend")
                return None
        if metrics["higher_low_bias"]:
            matched_rules.append("higher_low_bias")
            score += 0.75
        else:
            warning_flags.append("no_higher_low_yet")
        if metrics["volume_confirmed"]:
            matched_rules.append("volume_confirmed")
            score += 0.75
        if metrics["downside_followthrough"]:
            warning_flags.append("fresh_downside_followthrough")
            return None
        if metrics["extension_pct"] > 8.0:
            warning_flags.append("too_extended_after_reclaim")
            return None
        elif metrics["extension_pct"] > 5.0:
            warning_flags.append("slightly_extended")
            score -= 0.5
        if current["ema_200_ready"] and current["close"] > current["ema_200"]:
            matched_rules.append("back_above_ema200")
            score += 0.75
        elif current["ema_200_ready"] and metrics["distance_to_ema200_pct"] <= -10.0:
            warning_flags.append("still_far_below_ema200")
            score -= 0.75
        if signal_age is None:
            warning_flags.append("no_recent_reversal_trigger")
            return None
        if signal_age > signal_age_max:
            return None

        reliability_score = round(max(0.0, min(score, 10.0)), 2)
        if reliability_score < 6.0:
            return None
        return {
            "ticker": ticker,
            "reliability_score": reliability_score,
            "signal_age_days": int(signal_age),
            "signal_state": "turnaround",
            "last_date": _json_safe_cell(frame["date"].iloc[-1]),
            "close": round(float(current["close"]), 4),
            "ema_50": round(float(current["ema_50"]), 4),
            "ema_200": (
                round(float(current["ema_200"]), 4)
                if current["ema_200_ready"]
                else None
            ),
            "supertrend": (
                round(float(current["supertrend"]), 4)
                if current["supertrend_ready"]
                else None
            ),
            "volume": _safe_int(current["volume"]),
            "extension_pct": round(metrics["extension_pct"], 2),
            "drawdown_120_pct": round(metrics["drawdown_120_pct"], 2),
            "below_ema50_days_60": int(metrics["below_ema50_days_60"]),
            "reclaim_hold_days": int(metrics["reclaim_hold_days"]),
            "supertrend_hold_days": int(metrics["supertrend_hold_days"]),
            "ema_50_slope_pct": round(metrics["ema_50_slope_pct"], 3),
            "distance_to_ema200_pct": (
                round(metrics["distance_to_ema200_pct"], 2)
                if current["ema_200_ready"]
                else None
            ),
            "matched_rules": matched_rules,
            "warning_flags": warning_flags,
            "data_source": source,
        }

    def _signal_metrics(self, frame: pd.DataFrame) -> dict[str, Any]:
        working = frame.copy().reset_index(drop=True)
        working["ema_50"] = pd.to_numeric(working.get("ema_50"), errors="coerce")
        working["ema_200"] = pd.to_numeric(working.get("ema_200"), errors="coerce")
        working["close"] = pd.to_numeric(working.get("close"), errors="coerce")
        working["volume"] = pd.to_numeric(working.get("volume"), errors="coerce")
        working["supertrend"] = pd.to_numeric(
            working.get("supertrend"), errors="coerce"
        )
        if "ema_200" not in working.columns or working["ema_200"].dropna().empty:
            working["ema_200"] = working["close"].ewm(span=200, adjust=False).mean()
        current_idx = len(working) - 1
        above_ema = (working["close"] > working["ema_50"]).fillna(False)
        above_ema200 = (working["close"] > working["ema_200"]).fillna(False)
        supertrend_ready = working["supertrend"].notna()
        above_supertrend = (
            (working["close"] > working["supertrend"])
            .where(supertrend_ready, False)
            .fillna(False)
        )
        reclaim_age = self._latest_event_age(above_ema, turning_true=True)
        loss_age = self._latest_event_age(above_ema, turning_true=False)
        supertrend_flip_up_age = self._latest_event_age(
            above_supertrend, turning_true=True
        )
        supertrend_flip_down_age = self._latest_event_age(
            above_supertrend, turning_true=False
        )
        ema_now = (
            float(working["ema_50"].iloc[current_idx])
            if pd.notna(working["ema_50"].iloc[current_idx])
            else 0.0
        )
        ema_200_now = (
            float(working["ema_200"].iloc[current_idx])
            if pd.notna(working["ema_200"].iloc[current_idx])
            else 0.0
        )
        close_now = (
            float(working["close"].iloc[current_idx])
            if pd.notna(working["close"].iloc[current_idx])
            else 0.0
        )
        supertrend_now = (
            float(working["supertrend"].iloc[current_idx])
            if pd.notna(working["supertrend"].iloc[current_idx])
            else 0.0
        )
        slope_lookback = 5 if len(working) > 5 else max(1, len(working) - 1)
        ema_then = (
            float(working["ema_50"].iloc[current_idx - slope_lookback])
            if slope_lookback > 0
            and pd.notna(working["ema_50"].iloc[current_idx - slope_lookback])
            else ema_now
        )
        ema_50_slope_pct = (
            ((ema_now - ema_then) / ema_then * 100.0) if ema_then else 0.0
        )
        extension_pct = ((close_now - ema_now) / ema_now * 100.0) if ema_now else 0.0
        distance_to_ema_pct = abs(extension_pct)
        distance_to_ema200_pct = (
            ((close_now - ema_200_now) / ema_200_now * 100.0) if ema_200_now else 0.0
        )
        volume_now = (
            float(working["volume"].iloc[current_idx])
            if pd.notna(working["volume"].iloc[current_idx])
            else 0.0
        )
        volume_mean20 = (
            float(working["volume"].tail(20).dropna().mean())
            if not working["volume"].tail(20).dropna().empty
            else 0.0
        )
        recent_low = (
            float(working["close"].tail(5).min()) if len(working) >= 5 else close_now
        )
        prior_low = (
            float(working["close"].iloc[-10:-5].min())
            if len(working) >= 10
            else recent_low
        )
        downside_followthrough = (
            close_now < float(working["close"].iloc[max(0, current_idx - 4)])
            if len(working) >= 5
            else False
        )
        trailing_60 = working.tail(60)
        trailing_120 = working.tail(120)
        below_ema50_days_60 = (
            int((trailing_60["close"] < trailing_60["ema_50"]).fillna(False).sum())
            if not trailing_60.empty
            else 0
        )
        below_ema200_days_120 = (
            int((trailing_120["close"] < trailing_120["ema_200"]).fillna(False).sum())
            if not trailing_120.empty
            else 0
        )
        trailing_peak_120 = (
            float(trailing_120["close"].max()) if not trailing_120.empty else close_now
        )
        drawdown_120_pct = (
            ((close_now - trailing_peak_120) / trailing_peak_120 * 100.0)
            if trailing_peak_120
            else 0.0
        )
        reclaim_hold_days = self._trailing_true_run_length(above_ema)
        supertrend_hold_days = self._trailing_true_run_length(above_supertrend)
        prior_downtrend_confirmed = bool(
            (
                below_ema50_days_60 >= max(15, int(len(trailing_60) * 0.6))
                or below_ema200_days_120 >= max(20, int(len(trailing_120) * 0.6))
            )
            and drawdown_120_pct <= -10.0
            and (not above_ema200.iloc[current_idx] or distance_to_ema200_pct <= 2.0)
        )
        return {
            "reclaim_age": reclaim_age,
            "loss_age": loss_age,
            "supertrend_flip_up_age": supertrend_flip_up_age,
            "supertrend_flip_down_age": supertrend_flip_down_age,
            "ema_50_slope_pct": ema_50_slope_pct,
            "extension_pct": extension_pct,
            "distance_to_ema_pct": distance_to_ema_pct,
            "distance_to_ema200_pct": distance_to_ema200_pct,
            "volume_confirmed": bool(
                volume_mean20 and volume_now >= volume_mean20 * 1.05
            ),
            "higher_low_bias": recent_low >= prior_low and close_now >= ema_now,
            "downside_followthrough": bool(downside_followthrough),
            "below_ema50_days_60": below_ema50_days_60,
            "below_ema200_days_120": below_ema200_days_120,
            "drawdown_120_pct": drawdown_120_pct,
            "reclaim_hold_days": reclaim_hold_days,
            "supertrend_hold_days": supertrend_hold_days,
            "prior_downtrend_confirmed": prior_downtrend_confirmed,
            "current": {
                "close": close_now,
                "ema_50": ema_now,
                "ema_200": ema_200_now,
                "ema_200_ready": bool(pd.notna(working["ema_200"].iloc[current_idx])),
                "supertrend": supertrend_now,
                "supertrend_ready": bool(supertrend_ready.iloc[current_idx]),
                "volume": volume_now,
            },
        }

    def _latest_event_age(self, series: pd.Series, *, turning_true: bool) -> int | None:
        if series.empty:
            return None
        current_idx = len(series) - 1
        bool_series = series.astype(bool)
        previous = bool_series.shift(1, fill_value=False)
        if turning_true:
            mask = bool_series & (~previous.astype(bool))
        else:
            mask = (~bool_series) & previous.astype(bool)
        indices = [idx for idx, value in enumerate(mask.tolist()) if value]
        if not indices:
            return None
        return current_idx - indices[-1]

    def _trailing_true_run_length(self, series: pd.Series) -> int:
        if series.empty:
            return 0
        count = 0
        for value in reversed(series.astype(bool).tolist()):
            if not value:
                break
            count += 1
        return count

    def _normalize_price_history_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        rename_map: dict[str, str] = {}
        for column in normalized.columns:
            lower = str(column).strip().lower()
            if lower == "date":
                rename_map[column] = "date"
            elif lower == "open":
                rename_map[column] = "open"
            elif lower == "high":
                rename_map[column] = "high"
            elif lower == "low":
                rename_map[column] = "low"
            elif lower == "close":
                rename_map[column] = "close"
            elif lower == "volume":
                rename_map[column] = "volume"
            elif lower == "dividends":
                rename_map[column] = "dividends"
            elif lower in {"ema_50", "ema50"}:
                rename_map[column] = "ema_50"
            elif lower in {"ema_200", "ema200"}:
                rename_map[column] = "ema_200"
            elif lower == "supertrend":
                rename_map[column] = "supertrend"
            elif lower == "signal":
                rename_map[column] = "signal"
            elif lower == "ticker":
                rename_map[column] = "ticker"
            elif lower == "st_upper":
                rename_map[column] = "st_upper"
            elif lower == "st_lower":
                rename_map[column] = "st_lower"
        normalized = normalized.rename(columns=rename_map)

        if "Date" in normalized.columns and "date" not in normalized.columns:
            normalized = normalized.rename(columns={"Date": "date"})
        normalized["date"] = pd.to_datetime(
            normalized.get("date", normalized.get("Date")),
            errors="coerce",
        )
        normalized = (
            normalized.dropna(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )

        preferred = [
            "ticker",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "dividends",
            "ema_50",
            "ema_200",
            "supertrend",
            "st_upper",
            "st_lower",
            "signal",
        ]
        ordered = [name for name in preferred if name in normalized.columns]
        extras = [name for name in normalized.columns if name not in ordered]
        return normalized.loc[:, ordered + extras]

    def _resolve_columns(
        self,
        columns: str | Iterable[str] | None,
        available_columns: list[str],
        *,
        default_columns: Iterable[str],
    ) -> list[str]:
        if not available_columns:
            return []

        if columns is None:
            requested = list(default_columns)
        elif isinstance(columns, str):
            cleaned = str(columns).strip()
            if not cleaned or cleaned == "*":
                return list(available_columns)
            requested = [item.strip() for item in cleaned.split(",") if item.strip()]
        else:
            requested = [str(item).strip() for item in columns if str(item).strip()]

        resolved: list[str] = []
        available_lookup = {
            str(col).strip().lower(): str(col) for col in available_columns
        }
        for item in requested:
            key = _COLUMN_ALIASES.get(
                str(item).strip().lower(), str(item).strip().lower()
            )
            actual = available_lookup.get(key.lower())
            if actual and actual not in resolved:
                resolved.append(actual)
        if resolved:
            return resolved
        return [col for col in default_columns if col in available_columns] or list(
            available_columns
        )

    def _normalize_limit(self, limit: int | None, *, default: int = 120) -> int:
        return max(1, min(int(limit or default), 500))

    def _normalize_source(self, source: str | None) -> str:
        cleaned = str(source or "xetra").strip().lower()
        if cleaned in {"nasdaq", "us", "usa", "us_stocks", "us-stocks"}:
            return "nasdaq"
        if cleaned in {"sweden", "stockholm", "stockholms", "se", "ss", "st"}:
            return "sweden"
        if cleaned in {"list", "chosen", "chosen_list", "custom"}:
            return "list"
        if cleaned in {"all_lists", "alllists", "all list", "all lists"}:
            return "all_lists"
        return "xetra"

    def _market_source_config(self, source: str) -> tuple[Path, str]:
        normalized = self._normalize_source(source)
        if normalized == "nasdaq":
            return Path("config") / "nasdaq.json", "active"
        if normalized == "sweden":
            return Path("config") / "sweden.json", "active"
        if normalized == "list":
            return Path("config") / "custom_ticker_list.json", "active"
        if normalized == "all_lists":
            return Path("config") / "custom_ticker_list.json", "all"
        return Path("config") / "xetra.json", "active"


def render_query_result(
    result: dict[str, Any],
    *,
    output_format: str = "table",
) -> str:
    """Render a query response for CLI use."""
    normalized = str(output_format or "table").strip().lower()
    rows = result.get("rows", [])
    if normalized == "json":
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if normalized == "csv":
        frame = pd.DataFrame(rows)
        return frame.to_csv(index=False)
    if not rows:
        return "No rows returned."
    frame = pd.DataFrame(rows)
    return frame.to_string(index=False)
