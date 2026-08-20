"""Composable asset filters for simple rule-based screening."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import calculate_rsi
from ETF_screener.query_service import ETFQueryService
from ETF_screener.storage import ParquetStorage

LIQUIDITY_THRESHOLD = 250_000.0
OVERSOLD_RSI_THRESHOLD = 30.0
OVERBOUGHT_RSI_THRESHOLD = 70.0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_date_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except Exception:
            return str(value)
    return str(value)


class AssetFilterService:
    """Apply named filters to a chosen market universe."""

    FILTER_METADATA: dict[str, dict[str, Any]] = {
        "high_liquidity": {
            "label": "High Liquidity",
            "description": "20-day average volume is at or above the liquidity floor.",
        },
        "oversold": {
            "label": "Oversold",
            "description": "Latest RSI(14) is below the oversold threshold.",
        },
        "overbought": {
            "label": "Overbought",
            "description": "Latest RSI(14) is above the overbought threshold.",
        },
    }

    def __init__(
        self,
        *,
        db: ETFDatabase | None = None,
        storage: ParquetStorage | None = None,
        query_service: ETFQueryService | None = None,
    ) -> None:
        self.query_service = query_service or ETFQueryService(db=db, storage=storage)

    def list_filters(self) -> list[dict[str, Any]]:
        """Return the currently supported named filters."""
        return [
            {"key": key, **meta}
            for key, meta in sorted(
                self.FILTER_METADATA.items(), key=lambda item: item[0]
            )
        ]

    def get_filtered_assets(
        self,
        source: str,
        filters: str | Iterable[str],
        *,
        mode: str = "all",
    ) -> dict[str, Any]:
        """Return assets that match one or more named filters."""
        requested_filters = self._normalize_filters(filters)
        normalized_mode = self._normalize_mode(mode)
        normalized_source = self.query_service._normalize_source(source)
        tickers = self.query_service._load_universe_tickers(normalized_source)
        rows: list[dict[str, Any]] = []

        for ticker in tickers:
            raw_frame, data_source = self.query_service._load_price_history_frame(
                ticker
            )
            if raw_frame.empty:
                continue
            frame = self.query_service._normalize_price_history_frame(raw_frame)
            if frame.empty:
                continue
            evaluated = self._evaluate_ticker(
                ticker=ticker,
                frame=frame,
                data_source=data_source,
                filters=requested_filters,
            )
            matched = evaluated["matched_filters"]
            if normalized_mode == "all" and len(matched) != len(requested_filters):
                continue
            if normalized_mode == "any" and not matched:
                continue
            rows.append(evaluated)

        rows.sort(key=lambda row: (-len(row["matched_filters"]), str(row["ticker"])))
        return {
            "source": normalized_source,
            "mode": normalized_mode,
            "filters": requested_filters,
            "row_count": len(rows),
            "scanned_tickers": len(tickers),
            "rows": rows,
        }

    def _normalize_filters(self, filters: str | Iterable[str]) -> list[str]:
        if isinstance(filters, str):
            raw_items = [filters]
        else:
            raw_items = list(filters)
        normalized: list[str] = []
        for item in raw_items:
            key = str(item or "").strip().lower()
            if not key:
                continue
            if key not in self.FILTER_METADATA:
                raise ValueError(f"Unsupported asset filter: {item}")
            if key not in normalized:
                normalized.append(key)
        if not normalized:
            raise ValueError("At least one asset filter is required")
        return normalized

    def _normalize_mode(self, mode: str) -> str:
        cleaned = str(mode or "all").strip().lower()
        if cleaned not in {"all", "any"}:
            raise ValueError(f"Unsupported filter mode: {mode}")
        return cleaned

    def _evaluate_ticker(
        self,
        *,
        ticker: str,
        frame: pd.DataFrame,
        data_source: str,
        filters: list[str],
    ) -> dict[str, Any]:
        latest = frame.iloc[-1]
        filter_results: dict[str, dict[str, Any]] = {}
        matched_filters: list[str] = []
        avg_volume_20 = self._latest_avg_volume_20(frame)
        latest_rsi_14 = self._latest_rsi_14(frame)
        latest_close = _safe_float(latest.get("close"))
        latest_volume = _safe_float(latest.get("volume"))

        for filter_name in filters:
            if filter_name == "high_liquidity":
                result = {
                    "matched": bool(
                        avg_volume_20 is not None
                        and avg_volume_20 >= LIQUIDITY_THRESHOLD
                    ),
                    "metric": "avg_volume_20",
                    "value": (
                        round(avg_volume_20, 2) if avg_volume_20 is not None else None
                    ),
                    "threshold": LIQUIDITY_THRESHOLD,
                }
            elif filter_name == "oversold":
                result = {
                    "matched": bool(
                        latest_rsi_14 is not None
                        and latest_rsi_14 < OVERSOLD_RSI_THRESHOLD
                    ),
                    "metric": "rsi_14",
                    "value": (
                        round(latest_rsi_14, 2) if latest_rsi_14 is not None else None
                    ),
                    "threshold": OVERSOLD_RSI_THRESHOLD,
                }
            else:
                result = {
                    "matched": bool(
                        latest_rsi_14 is not None
                        and latest_rsi_14 > OVERBOUGHT_RSI_THRESHOLD
                    ),
                    "metric": "rsi_14",
                    "value": (
                        round(latest_rsi_14, 2) if latest_rsi_14 is not None else None
                    ),
                    "threshold": OVERBOUGHT_RSI_THRESHOLD,
                }
            filter_results[filter_name] = result
            if result["matched"]:
                matched_filters.append(filter_name)

        return {
            "ticker": ticker,
            "last_date": _safe_date_text(latest.get("date")),
            "close": latest_close,
            "volume": latest_volume,
            "avg_volume_20": (
                round(avg_volume_20, 2) if avg_volume_20 is not None else None
            ),
            "rsi_14": round(latest_rsi_14, 2) if latest_rsi_14 is not None else None,
            "matched_filters": matched_filters,
            "filter_results": filter_results,
            "data_source": data_source,
        }

    def _latest_avg_volume_20(self, frame: pd.DataFrame) -> float | None:
        volume_series = pd.to_numeric(frame.get("volume"), errors="coerce").dropna()
        if volume_series.empty:
            return None
        return _safe_float(volume_series.tail(20).mean())

    def _latest_rsi_14(self, frame: pd.DataFrame) -> float | None:
        for column in frame.columns:
            lowered = str(column).strip().lower()
            if lowered in {"rsi", "rsi_14"}:
                series = pd.to_numeric(frame[column], errors="coerce").dropna()
                if not series.empty:
                    return _safe_float(series.iloc[-1])

        close_series = pd.to_numeric(frame.get("close"), errors="coerce").dropna()
        if close_series.empty:
            return None
        rsi_series = calculate_rsi(close_series, period=14)
        if len(rsi_series) == 0:
            return None
        return _safe_float(rsi_series.iloc[-1])


def get_filtered_assets(
    source: str,
    filters: str | Iterable[str],
    *,
    mode: str = "all",
    db: ETFDatabase | None = None,
    storage: ParquetStorage | None = None,
    query_service: ETFQueryService | None = None,
) -> dict[str, Any]:
    """Convenience wrapper for simple asset-filter calls."""
    service = AssetFilterService(
        db=db,
        storage=storage,
        query_service=query_service,
    )
    return service.get_filtered_assets(source, filters, mode=mode)
