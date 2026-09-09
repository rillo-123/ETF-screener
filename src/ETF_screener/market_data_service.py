"""Market data freshness helpers for the dashboard."""

from __future__ import annotations

import json
import inspect
import logging
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from concurrent.futures import as_completed as as_completed  # noqa: F401
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ETF_screener.config_loader import get_paths
from ETF_screener.database import ETFDatabase
from ETF_screener.delisting_tracker import DelistingTracker
from ETF_screener.indicators import add_indicators
from ETF_screener.market_data_provider import (
    MarketDataProvider,
    create_market_data_provider,
)
from ETF_screener.shortlist_engine import ETFShortlistEngine
from ETF_screener.storage import ParquetStorage

logger = logging.getLogger(__name__)

NASDAQ_VITALITY_MIN_RECENT_AVG_VOLUME = 150_000
NASDAQ_VITALITY_MIN_RECENT_AVG_DOLLAR_VOLUME = 1_500_000.0
NASDAQ_VITALITY_MIN_RECENT_AVG_CLOSE = 3.0


def load_nasdaq_focus() -> set[str] | None:
    """Return the optional, explicitly selected Nasdaq maintenance universe."""
    path = get_paths().get("nasdaq_focus_file")
    if not path:
        return None
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return {str(ticker).upper() for ticker in payload["tickers"]}


@lru_cache(maxsize=8)
def _cached_nasdaq_vitality_tickers(
    db_path: str,
    latest_market_date: str | None,
    candidate_tickers: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Return Nasdaq-style symbols with enough recent trading vitality."""
    del latest_market_date
    normalized_candidates = tuple(
        dict.fromkeys(
            str(ticker).upper()
            for ticker in candidate_tickers
            if str(ticker).strip() and "." not in str(ticker)
        )
    )
    candidate_filter = ""
    query_params: list[object] = []
    if normalized_candidates:
        placeholders = ",".join("?" for _ in normalized_candidates)
        candidate_filter = f" AND ticker IN ({placeholders})"
        query_params.extend(normalized_candidates)
    query = f"""
        WITH ranked AS (
            SELECT
                ticker,
                date,
                close,
                volume,
                ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
            FROM etf_data
            WHERE ticker NOT LIKE '%.%'
              {candidate_filter}
        ),
        agg AS (
            SELECT
                ticker,
                MAX(date) AS last_date,
                COUNT(*) AS total_rows,
                SUM(CASE WHEN volume > 0 THEN 1 ELSE 0 END) AS nonzero_volume_rows,
                SUM(CASE WHEN rn <= 30 THEN 1 ELSE 0 END) AS recent_rows,
                SUM(CASE WHEN rn <= 30 AND volume = 0 THEN 1 ELSE 0 END) AS recent_zero_volume_rows,
                AVG(CASE WHEN rn <= 20 THEN volume END) AS recent_avg_volume,
                AVG(CASE WHEN rn <= 20 THEN close END) AS recent_avg_close,
                AVG(CASE WHEN rn <= 20 THEN close * volume END) AS recent_avg_dollar_volume
            FROM ranked
            GROUP BY ticker
        )
        SELECT ticker
        FROM agg
        WHERE total_rows >= 50
          AND nonzero_volume_rows >= 20
          AND recent_rows >= 10
          AND recent_zero_volume_rows < 2
          AND recent_avg_volume >= ?
          AND recent_avg_close >= ?
          AND recent_avg_dollar_volume >= ?
          AND last_date >= date('now', '-45 day')
        ORDER BY ticker
    """
    query_params.extend(
        [
            NASDAQ_VITALITY_MIN_RECENT_AVG_VOLUME,
            NASDAQ_VITALITY_MIN_RECENT_AVG_CLOSE,
            NASDAQ_VITALITY_MIN_RECENT_AVG_DOLLAR_VOLUME,
        ]
    )
    with ETFDatabase(db_path=db_path) as db:
        frame = pd.read_sql_query(
            query,
            db._get_connection(),
            params=query_params,
        )
    return tuple(str(ticker).upper() for ticker in frame.get("ticker", []).tolist())


def filter_low_vitality_nasdaq_tickers(
    db_path: str | None,
    latest_market_date: str | None,
    tickers: list[str] | tuple[str, ...],
) -> list[str]:
    """Filter Nasdaq-style symbols down to more actionable names."""
    focus = load_nasdaq_focus()
    if focus is not None:
        tickers = [ticker for ticker in tickers if str(ticker).upper() in focus]
    normalized = [str(ticker).upper() for ticker in tickers if str(ticker).strip()]
    if not db_path:
        return normalized
    undotted_candidates = tuple(
        dict.fromkeys(ticker for ticker in normalized if "." not in ticker)
    )
    # SQLite's default bind limit is commonly 999. Focused Nasdaq universes fit
    # comfortably below it; fall back to the all-Nasdaq query for larger lists.
    bounded_candidates = undotted_candidates if len(undotted_candidates) <= 900 else ()
    eligible = set(
        _cached_nasdaq_vitality_tickers(
            str(db_path), latest_market_date, bounded_candidates
        )
    )
    filtered: list[str] = []
    for upper in normalized:
        if not upper:
            continue
        if "." in upper or upper in eligible:
            filtered.append(upper)
    return filtered


class MarketDataRefresher:
    """Track and refresh the underlying ETF market data cache."""

    INDICATOR_WARMUP_DAYS = 90
    DEFAULT_RETENTION_DAYS = int(get_paths().get("history_retention_days", 365))

    def __init__(
        self,
        db_path: str | None = None,
        etfs_file: str = "config/xetra.json",
        blacklist_file: str = "config/blacklist.json",
        fetcher: Optional[MarketDataProvider] = None,
        storage: Optional[ParquetStorage] = None,
        collection_mode: str = "active",
        tracked_tickers_override: object | None = None,
        provider: str | None = None,
        provider_api_key: str | None = None,
    ):
        self.db = ETFDatabase(db_path=db_path)
        self.etfs_file = Path(etfs_file)
        self.blacklist_file = Path(blacklist_file)
        self.delisting_tracker = DelistingTracker(blacklist_file=self.blacklist_file)
        self.fetcher = fetcher or create_market_data_provider(
            provider,
            api_key=provider_api_key,
        )
        self.storage = storage or ParquetStorage()
        self.collection_mode = (
            "all" if str(collection_mode).strip().lower() == "all" else "active"
        )
        self.tracked_tickers_override = tracked_tickers_override

    @staticmethod
    def _parse_day(raw: str | None) -> Optional[date]:
        if not raw:
            return None
        try:
            return datetime.strptime(str(raw).split(" ")[0], "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _expected_market_day(today: date | None = None) -> date:
        """Return the latest weekday that can reasonably have a market candle."""
        expected = today or date.today()
        while expected.weekday() >= 5:
            expected -= timedelta(days=1)
        return expected

    def _load_blacklist(self) -> set[str]:
        if not self.blacklist_file.exists():
            return set()
        try:
            with open(self.blacklist_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception:
            return set()

        if isinstance(raw, dict):
            return {str(ticker).upper() for ticker in raw.keys()}
        if isinstance(raw, list):
            return {str(ticker).upper() for ticker in raw}
        return set()

    @staticmethod
    def _normalize_ticker_values(raw: object) -> list[str]:
        if raw is None:
            return []
        if isinstance(raw, dict):
            values = list(raw.keys())
        elif isinstance(raw, (list, tuple, set)):
            values = list(raw)
        elif isinstance(raw, str):
            values = [
                item for item in raw.replace(";", ",").replace("\n", ",").split(",")
            ]
        else:
            values = [raw]
        tickers: list[str] = []
        for item in values:
            ticker = str(item).strip().upper()
            if ticker:
                tickers.append(ticker)
        return tickers

    def _load_tracked_tickers(self) -> list[str]:
        blacklist = self._load_blacklist()
        if self.tracked_tickers_override is not None:
            return sorted(
                ticker
                for ticker in self._normalize_ticker_values(
                    self.tracked_tickers_override
                )
                if ticker not in blacklist
            )
        focus_path = get_paths().get("nasdaq_focus_file")
        if self.etfs_file.name == "nasdaq.json" and focus_path:
            with open(focus_path, encoding="utf-8") as handle:
                focus = json.load(handle)
            return sorted(
                t
                for t in self._normalize_ticker_values(focus["tickers"])
                if t not in blacklist
            )
        tickers: set[str] = set()
        if self.etfs_file.exists():
            with open(self.etfs_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                if isinstance(raw.get("lists"), list):
                    lists = raw.get("lists", [])
                    if self.collection_mode == "all":
                        for entry in lists:
                            if isinstance(entry, dict):
                                tickers.update(
                                    self._normalize_ticker_values(
                                        entry.get("tickers", [])
                                    )
                                )
                            else:
                                tickers.update(self._normalize_ticker_values(entry))
                    else:
                        active_name = str(
                            raw.get("active_name") or raw.get("name") or ""
                        ).strip()
                        active_entry = None
                        if active_name:
                            for entry in lists:
                                if not isinstance(entry, dict):
                                    continue
                                entry_name = str(entry.get("name") or "").strip()
                                if entry_name == active_name:
                                    active_entry = entry
                                    break
                        if active_entry is None and isinstance(
                            raw.get("active_list"), dict
                        ):
                            active_entry = raw.get("active_list")
                        if active_entry is not None:
                            tickers.update(
                                self._normalize_ticker_values(
                                    active_entry.get("tickers", [])
                                )
                            )
                        else:
                            tickers.update(
                                self._normalize_ticker_values(raw.get("tickers", []))
                            )
                    return sorted(
                        ticker for ticker in tickers if ticker not in blacklist
                    )
                if isinstance(raw.get("tickers"), list):
                    tickers.update(str(ticker).upper() for ticker in raw["tickers"])
                else:
                    for ticker, metadata in raw.items():
                        status = (
                            str(metadata.get("status", "active")).lower()
                            if isinstance(metadata, dict)
                            else "active"
                        )
                        if status not in {
                            "invalid",
                            "blacklisted",
                            "delisted",
                            "inactive",
                        }:
                            tickers.add(str(ticker).upper())
            elif isinstance(raw, list):
                tickers.update(str(ticker).upper() for ticker in raw)
        else:
            tickers.update(str(ticker).upper() for ticker in self.db.get_tickers())

        return sorted(ticker for ticker in tickers if ticker not in blacklist)

    @staticmethod
    def _normalize_price_frame(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(
                columns=["Date", "Open", "High", "Low", "Close", "Volume"]
            )

        normalized = df.copy()
        normalized = normalized.rename(
            columns={
                "date": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "dividends": "Dividends",
                "volume": "Volume",
            }
        )

        for column in ["Date", "Open", "High", "Low", "Close", "Volume", "Dividends"]:
            if column not in normalized.columns:
                normalized[column] = None if column == "Date" else 0

        def _coerce_date(value):
            if pd.isna(value):
                return pd.NaT
            ts = pd.Timestamp(value)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            return ts.normalize()

        normalized["Date"] = normalized["Date"].map(_coerce_date)
        normalized = normalized.dropna(subset=["Date"])
        normalized = normalized[
            ["Date", "Open", "High", "Low", "Close", "Volume", "Dividends"]
        ]
        for column in ["Open", "High", "Low", "Close"]:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        # Providers sometimes expose an unfinished session with volume but no
        # price body. It is not a finalized candle and must never become the
        # latest bar used by liquidity or TA predicates.
        normalized = normalized.dropna(subset=["Open", "High", "Low", "Close"])
        normalized = normalized.sort_values("Date").drop_duplicates(
            subset=["Date"], keep="last"
        )
        normalized["Volume"] = pd.to_numeric(
            normalized["Volume"], errors="coerce"
        ).fillna(0)
        normalized["Dividends"] = pd.to_numeric(
            normalized["Dividends"], errors="coerce"
        ).fillna(0)
        return normalized.reset_index(drop=True)

    def _load_existing_price_frame(self, ticker: str) -> pd.DataFrame:
        existing = self.storage.load_etf_data(ticker)
        if existing is None or existing.empty:
            with ETFDatabase(db_path=str(self.db.db_path)) as lookup_db:
                existing = lookup_db.get_etf_data(ticker)
        return self._normalize_price_frame(existing)

    def _build_refresh_frame(
        self,
        ticker: str,
        depth: int,
        warmup_days: int,
        min_existing_rows: int = 100,
        cancel_event=None,
        backfill: bool = False,
    ) -> tuple[str, pd.DataFrame]:
        # Normal refreshes extend the latest date; explicit history requests
        # merge a longer provider window into the existing canonical history.
        del warmup_days, min_existing_rows
        existing = self._load_existing_price_frame(ticker)
        latest_day = None
        if not existing.empty:
            latest_day = pd.to_datetime(existing["Date"].max()).date()

        fetch_supports_cancel = (
            "cancel_event"
            in inspect.signature(self.fetcher.fetch_historical_data).parameters
        )
        fetch_kwargs: dict[str, Any]

        if existing.empty or backfill:
            fetch_kwargs = {"days": depth}
            if fetch_supports_cancel:
                fetch_kwargs["cancel_event"] = cancel_event
            fetched = self.fetcher.fetch_historical_data(ticker, **fetch_kwargs)
            fresh_slice = self._normalize_price_frame(fetched)
            if fresh_slice.empty:
                raise ValueError(f"No rows returned for {ticker}")
            if existing.empty:
                merged = fresh_slice
            else:
                merged = self._normalize_price_frame(
                    pd.concat([existing, fresh_slice], ignore_index=True)
                )
        else:
            if latest_day is None:
                raise RuntimeError("Expected a latest market date when refreshing")
            expected_day = self._expected_market_day()
            if latest_day >= expected_day:
                return ticker, add_indicators(existing)

            # The cache is authoritative. Request the adaptive missing tail,
            # beginning on the calendar day after the latest stored candle.
            # The provider naturally omits weekends and exchange closures.
            fetch_start = latest_day + timedelta(days=1)
            fetch_kwargs = {
                "start_date": fetch_start,
                "end_date": datetime.now(),
            }
            if fetch_supports_cancel:
                fetch_kwargs["cancel_event"] = cancel_event
            fetched = self.fetcher.fetch_historical_data(ticker, **fetch_kwargs)
            fresh_slice = self._normalize_price_frame(fetched)
            merged = self._normalize_price_frame(
                pd.concat([existing, fresh_slice], ignore_index=True)
            )

        if merged.empty:
            raise ValueError(f"No rows returned for {ticker}")

        enriched = add_indicators(merged)
        return ticker, enriched

    @staticmethod
    def _emit_progress(
        progress_callback,
        *,
        job: str,
        phase: str,
        pct: float,
        detail: str = "",
        label: str | None = None,
        active: bool = True,
        error: str | None = None,
    ) -> None:
        if progress_callback is None:
            return
        try:
            progress_callback(
                {
                    "job": job,
                    "phase": phase,
                    "pct": pct,
                    "detail": detail,
                    "label": label or "Market Refresh",
                    "active": active,
                    "error": error,
                }
            )
        except Exception:
            pass

    def get_status(self, stale_after_days: int = 3) -> dict[str, Any]:
        tracked = self._load_tracked_tickers()
        blacklist = self._load_blacklist()
        latest_by_ticker = self.db.get_ticker_latest_dates()

        calendar_today = date.today()
        today = self._expected_market_day(calendar_today)
        threshold_days = max(0, int(stale_after_days))
        market_day = self._parse_day(self.db.get_latest_market_date())
        shortlist_day = self._parse_day(self.db.get_latest_shortlist_date())
        shortlist_updated_at = self.db.get_latest_shortlist_updated_at()
        stale_cutoff = today - timedelta(days=threshold_days)

        missing = [ticker for ticker in tracked if ticker not in latest_by_ticker]
        stale = [
            ticker
            for ticker in tracked
            if ticker in latest_by_ticker
            and (self._parse_day(latest_by_ticker[ticker]) or date.min) < stale_cutoff
        ]
        days_stale = (calendar_today - market_day).days if market_day else None
        market_days_stale = (today - market_day).days if market_day else None
        fresh_tickers = max(0, len(tracked) - len(missing) - len(stale))

        return {
            "provider": str(getattr(self.fetcher, "name", type(self.fetcher).__name__)),
            "today": today.isoformat(),
            "latest_market_date": market_day.isoformat() if market_day else None,
            "latest_shortlist_date": (
                shortlist_day.isoformat() if shortlist_day else None
            ),
            "latest_shortlist_updated_at": shortlist_updated_at,
            "days_stale": days_stale,
            "market_days_stale": market_days_stale,
            "is_stale": (
                market_days_stale is None
                or market_days_stale > threshold_days
                or bool(missing)
                or bool(stale)
            ),
            "tracked_tickers": len(tracked),
            "fresh_tickers": fresh_tickers,
            "missing_tickers": len(missing),
            "stale_tickers": len(stale),
            "blacklisted_tickers": len(blacklist),
            "missing_examples": missing[:10],
            "stale_examples": stale[:10],
        }

    def refresh_ticker_data(
        self,
        ticker: str,
        depth: int = 400,
        warmup_days: int = INDICATOR_WARMUP_DAYS,
        min_existing_rows: int = 100,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> pd.DataFrame:
        symbol, df = self._build_refresh_frame(
            ticker=ticker,
            depth=depth,
            warmup_days=warmup_days,
            min_existing_rows=min_existing_rows,
        )
        self.db.insert_dataframe(df, symbol)
        self.storage.save_etf_data(df, symbol)
        self.db.prune_incomplete_data()
        self.db.prune_old_data(days_to_keep=retention_days)
        return df

    def refresh_market_data(
        self,
        depth: int = 400,
        stale_after_days: int = 3,
        force: bool = False,
        max_workers: int = 2,
        rebuild_shortlist: bool = True,
        warmup_days: int = INDICATOR_WARMUP_DAYS,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        progress_callback=None,
        cancel_event=None,
        missing_only: bool = False,
        history_years: int = 0,
    ) -> dict[str, Any]:
        if history_years not in (0, 1, 3, 5, 10):
            raise ValueError("History must be 0, 1, 3, 5 or 10 years")
        backfill = history_years > 0
        if backfill:
            depth = history_years * 366
            force = True
            missing_only = False
            retention_days = max(retention_days, depth)
        job = "market-refresh"

        def is_cancelled() -> bool:
            return bool(cancel_event is not None and cancel_event.is_set())

        source_name = self.etfs_file.name.lower()
        logger.info(
            "Market refresh started: source=%s force=%s stale_after_days=%s depth=%s max_workers=%s rebuild_shortlist=%s missing_only=%s",
            source_name,
            force,
            stale_after_days,
            depth,
            max_workers,
            rebuild_shortlist,
            missing_only,
        )
        promoted = self.delisting_tracker.promote_aged_missing(threshold_days=14)
        if promoted:
            logger.info("Promoted %d missing tickers to blacklist", len(promoted))
        self._emit_progress(
            progress_callback,
            job=job,
            phase="planning",
            pct=2.0,
            detail="Scanning tracked tickers",
            label="Market Refresh",
            active=True,
        )
        tracked = self._load_tracked_tickers()
        latest_by_ticker = self.db.get_ticker_latest_dates()
        missing_state = self.delisting_tracker.load_missing_state()
        today = self._expected_market_day()
        observation_day = date.today()
        threshold_days = max(0, int(stale_after_days))
        stale_cutoff = today - timedelta(days=threshold_days)

        to_refresh = []
        deferred_missing = 0
        for ticker in tracked:
            if is_cancelled():
                break
            latest = self._parse_day(latest_by_ticker.get(ticker))
            if missing_only and latest is not None:
                continue
            if not (force or latest is None or latest < stale_cutoff):
                continue
            last_missing = self._parse_day(
                str(missing_state.get(ticker, {}).get("last_missing") or "")
            )
            if (
                not force
                and last_missing is not None
                and (observation_day - last_missing).days < 1
            ):
                deferred_missing += 1
                continue
            to_refresh.append(ticker)

        # Treat refresh work as a useful-data queue: update symbols with the
        # newest existing candles first and leave never-seen symbols until last.
        # This prevents obsolete catalogue entries from delaying usable TA data.
        to_refresh.sort(
            key=lambda ticker: (
                self._parse_day(latest_by_ticker.get(ticker)) is not None,
                self._parse_day(latest_by_ticker.get(ticker)) or date.min,
            ),
            reverse=True,
        )

        if is_cancelled():
            self._emit_progress(
                progress_callback,
                job=job,
                phase="cancelled",
                pct=2.0,
                detail="Market refresh stopped",
                label="Market Refresh",
                active=False,
            )
            status = self.get_status(stale_after_days=stale_after_days)
            status.update(
                {
                    "requested": len(to_refresh),
                    "refreshed": 0,
                    "failed": 0,
                    "shortlist_rebuilt": False,
                    "pruned": 0,
                    "pruned_incomplete": 0,
                    "deferred_missing": deferred_missing,
                    "errors": [],
                    "cancelled": True,
                }
            )
            return status

        if not to_refresh:
            logger.info("Market refresh planning complete: nothing to refresh")
            pruned_incomplete = self.db.prune_incomplete_data()
            pruned = self.db.prune_old_data(days_to_keep=retention_days)
            logger.info(
                "Market data retention complete: pruned=%d retention_days=%d",
                pruned,
                retention_days,
            )
            self._emit_progress(
                progress_callback,
                job=job,
                phase="done",
                pct=100.0,
                detail="Market data already fresh",
                label="Market Refresh",
                active=False,
            )
            status = self.get_status(stale_after_days=stale_after_days)
            status.update(
                {
                    "requested": 0,
                    "refreshed": 0,
                    "failed": 0,
                    "shortlist_rebuilt": False,
                    "pruned": pruned,
                    "pruned_incomplete": pruned_incomplete,
                    "deferred_missing": deferred_missing,
                }
            )
            return status

        worker_count = min(max(1, int(max_workers)), 2)
        sequential_refresh = False
        if source_name in {"sweden.json", "nasdaq.json"}:
            # A small worker pool plus the shared request gate prevents large
            # universes from producing a Yahoo request burst.
            worker_count = min(worker_count, max(1, len(to_refresh)))
        elif source_name == "custom_ticker_list.json" and len(to_refresh) <= 100:
            worker_count = min(worker_count, 2)
            sequential_refresh = True
        refreshed = 0
        failed = 0
        errors: list[dict[str, str]] = []
        total = len(to_refresh)
        completed = 0
        logger.info(
            "Market refresh planning complete: tracked=%d queued=%d worker_mode=%s worker_count=%d",
            len(tracked),
            total,
            "sequential" if sequential_refresh else "parallel",
            worker_count,
        )

        self._emit_progress(
            progress_callback,
            job=job,
            phase="refreshing",
            pct=5.0,
            detail=(
                f"Downloading {history_years}-year history for {total} tickers"
                if backfill
                else f"Refreshing {total} tickers"
            ),
            label="Market Refresh",
            active=True,
        )
        logger.info("Market refresh phase: refreshing %d tickers", total)

        if sequential_refresh:
            logger.info("Market refresh worker mode: sequential")
            for ticker in to_refresh:
                if is_cancelled():
                    break
                try:
                    symbol, df = self._build_refresh_frame(
                        ticker,
                        depth,
                        warmup_days,
                        cancel_event=cancel_event,
                        **({"backfill": True} if backfill else {}),
                    )
                    if df is None or df.empty:
                        raise ValueError("No rows returned")
                    self.db.insert_dataframe(df, symbol)
                    self.storage.save_etf_data(df, symbol)
                    self.delisting_tracker.clear_missing(ticker)
                    refreshed += 1
                except Exception as exc:
                    failed += 1
                    message = str(exc)
                    if "No data found" in message or "No rows returned" in message:
                        self.delisting_tracker.mark_missing(ticker, reason=message)
                        # Provider gaps can be transient. Keep the symbol in the
                        # missing queue until the normal 14-day quarantine expires.
                        self.delisting_tracker.promote_aged_missing(threshold_days=14)
                    errors.append({"ticker": ticker, "error": str(exc)})
                finally:
                    completed += 1
                    progress_pct = 5.0 + (completed / max(1, total)) * 75.0
                    self._emit_progress(
                        progress_callback,
                        job=job,
                        phase="refreshing",
                        pct=progress_pct,
                        detail=f"{completed}/{total} tickers processed · {ticker} · {failed} failed",
                        label="Market Refresh",
                        active=True,
                    )
                    if completed < total:
                        time.sleep(0.1)
        else:
            logger.info(
                "Market refresh worker mode: parallel (%d workers)", worker_count
            )
            executor = ThreadPoolExecutor(max_workers=worker_count)
            futures = {}
            try:
                for ticker in to_refresh:
                    if is_cancelled():
                        break
                    future = executor.submit(
                        self._build_refresh_frame,
                        ticker,
                        depth,
                        warmup_days,
                        100,
                        cancel_event,
                        **({"backfill": True} if backfill else {}),
                    )
                    futures[future] = ticker
                pending = set(futures)
                while pending and not is_cancelled():
                    done, pending = wait(
                        pending,
                        timeout=0.25,
                        return_when=FIRST_COMPLETED,
                    )
                    for future in done:
                        ticker = futures[future]
                        try:
                            symbol, df = future.result()
                            if df is None or df.empty:
                                raise ValueError("No rows returned")
                            self.db.insert_dataframe(df, symbol)
                            self.storage.save_etf_data(df, symbol)
                            self.delisting_tracker.clear_missing(ticker)
                            refreshed += 1
                        except Exception as exc:
                            failed += 1
                            message = str(exc)
                            if (
                                "No data found" in message
                                or "No rows returned" in message
                            ):
                                self.delisting_tracker.mark_missing(
                                    ticker, reason=message
                                )
                                # Empty provider responses enter the missing queue;
                                # only persistent misses become blacklist entries.
                                self.delisting_tracker.promote_aged_missing(
                                    threshold_days=14
                                )
                            errors.append({"ticker": ticker, "error": str(exc)})
                        finally:
                            completed += 1
                            progress_pct = 5.0 + (completed / max(1, total)) * 75.0
                            self._emit_progress(
                                progress_callback,
                                job=job,
                                phase="refreshing",
                                pct=progress_pct,
                                detail=f"{completed}/{total} tickers processed · {ticker} · {failed} failed",
                                label="Market Refresh",
                                active=True,
                            )
            finally:
                for future in futures:
                    if not future.done():
                        future.cancel()
                if hasattr(executor, "shutdown"):
                    executor.shutdown(wait=False, cancel_futures=True)

        if is_cancelled():
            logger.info(
                "Market refresh cancelled after %d/%d tickers", completed, total
            )
            self._emit_progress(
                progress_callback,
                job=job,
                phase="cancelled",
                pct=5.0 + (completed / max(1, total)) * 75.0,
                detail=f"Stopped after {completed}/{total} tickers",
                label="Market Refresh",
                active=False,
            )
            status = self.get_status(stale_after_days=stale_after_days)
            status.update(
                {
                    "requested": len(to_refresh),
                    "refreshed": refreshed,
                    "failed": failed,
                    "shortlist_rebuilt": False,
                    "pruned": 0,
                    "pruned_incomplete": 0,
                    "deferred_missing": deferred_missing,
                    "errors": errors[:25],
                    "cancelled": True,
                }
            )
            return status

        pruned_incomplete = self.db.prune_incomplete_data()
        pruned = self.db.prune_old_data(days_to_keep=retention_days)
        logger.info(
            "Market data retention complete: pruned=%d retention_days=%d",
            pruned,
            retention_days,
        )

        shortlist_rebuilt = False
        if rebuild_shortlist:
            logger.info("Market refresh phase: rebuilding shortlist artifacts")
            self._emit_progress(
                progress_callback,
                job=job,
                phase="rebuilding-shortlist",
                pct=88.0,
                detail="Rebuilding shortlist artifacts",
                label="Market Refresh",
                active=True,
            )
            engine = ETFShortlistEngine(
                db_path=str(self.db.db_path),
                metadata_path=str(self.etfs_file),
                storage=self.storage,
            )
            engine.build_shortlist(max_workers=max_workers)
            shortlist_rebuilt = True
            self._emit_progress(
                progress_callback,
                job=job,
                phase="rebuilding-shortlist",
                pct=96.0,
                detail="Shortlist rebuilt",
                label="Market Refresh",
                active=True,
            )
            logger.info("Market refresh phase complete: shortlist rebuilt")

        status = self.get_status(stale_after_days=stale_after_days)
        status.update(
            {
                "requested": len(to_refresh),
                "refreshed": refreshed,
                "failed": failed,
                "shortlist_rebuilt": shortlist_rebuilt,
                "pruned": pruned,
                "pruned_incomplete": pruned_incomplete,
                "deferred_missing": deferred_missing,
                "errors": errors[:25],
            }
        )
        logger.info(
            "Market refresh finished: requested=%d refreshed=%d failed=%d shortlist_rebuilt=%s latest_market_date=%s",
            status["requested"],
            refreshed,
            failed,
            shortlist_rebuilt,
            status.get("latest_market_date"),
        )
        self._emit_progress(
            progress_callback,
            job=job,
            phase="done",
            pct=100.0,
            detail=f"{refreshed} refreshed, {failed} failed",
            label="Market Refresh",
            active=False,
        )
        return status
