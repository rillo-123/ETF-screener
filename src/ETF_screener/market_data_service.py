"""Market data freshness helpers for the dashboard."""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.delisting_tracker import DelistingTracker
from ETF_screener.indicators import add_indicators
from ETF_screener.shortlist_engine import ETFShortlistEngine
from ETF_screener.storage import ParquetStorage
from ETF_screener.yfinance_fetcher import YFinanceFetcher

logger = logging.getLogger(__name__)


class MarketDataRefresher:
    """Track and refresh the underlying ETF market data cache."""

    INDICATOR_WARMUP_DAYS = 90

    def __init__(
        self,
        db_path: str | None = None,
        etfs_file: str = "config/xetra.json",
        blacklist_file: str = "config/blacklist.json",
        fetcher: Optional[YFinanceFetcher] = None,
        storage: Optional[ParquetStorage] = None,
        collection_mode: str = "active",
    ):
        self.db = ETFDatabase(db_path=db_path)
        self.etfs_file = Path(etfs_file)
        self.blacklist_file = Path(blacklist_file)
        self.delisting_tracker = DelistingTracker(blacklist_file=self.blacklist_file)
        self.fetcher = fetcher or YFinanceFetcher()
        self.storage = storage or ParquetStorage()
        self.collection_mode = (
            "all" if str(collection_mode).strip().lower() == "all" else "active"
        )

    @staticmethod
    def _parse_day(raw: str | None) -> Optional[date]:
        if not raw:
            return None
        try:
            return datetime.strptime(str(raw).split(" ")[0], "%Y-%m-%d").date()
        except ValueError:
            return None

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
    ) -> tuple[str, pd.DataFrame]:
        existing = self._load_existing_price_frame(ticker)
        latest_day = None
        if not existing.empty:
            latest_day = pd.to_datetime(existing["Date"].max()).date()

        if existing.empty or len(existing) < min_existing_rows:
            fetched = self.fetcher.fetch_historical_data(ticker, days=depth)
            merged = self._normalize_price_frame(fetched)
        else:
            if latest_day is None:
                raise RuntimeError("Expected a latest market date when refreshing")
            fetch_start = latest_day - timedelta(days=max(5, int(warmup_days)))
            fetched = self.fetcher.fetch_historical_data(
                ticker,
                start_date=fetch_start,
                end_date=datetime.now(),
            )
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

        today = date.today()
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
        days_stale = (today - market_day).days if market_day else None
        fresh_tickers = max(0, len(tracked) - len(missing) - len(stale))

        return {
            "today": today.isoformat(),
            "latest_market_date": market_day.isoformat() if market_day else None,
            "latest_shortlist_date": (
                shortlist_day.isoformat() if shortlist_day else None
            ),
            "latest_shortlist_updated_at": shortlist_updated_at,
            "days_stale": days_stale,
            "is_stale": (
                days_stale is None
                or days_stale > threshold_days
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
    ) -> pd.DataFrame:
        symbol, df = self._build_refresh_frame(
            ticker=ticker,
            depth=depth,
            warmup_days=warmup_days,
            min_existing_rows=min_existing_rows,
        )
        self.db.insert_dataframe(df, symbol)
        self.storage.save_etf_data(df, symbol)
        return df

    def refresh_market_data(
        self,
        depth: int = 400,
        stale_after_days: int = 3,
        force: bool = False,
        max_workers: int = 8,
        rebuild_shortlist: bool = True,
        warmup_days: int = INDICATOR_WARMUP_DAYS,
        progress_callback=None,
    ) -> dict[str, Any]:
        job = "market-refresh"
        source_name = self.etfs_file.name.lower()
        logger.info(
            "Market refresh started: source=%s force=%s stale_after_days=%s depth=%s max_workers=%s rebuild_shortlist=%s",
            source_name,
            force,
            stale_after_days,
            depth,
            max_workers,
            rebuild_shortlist,
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
        today = date.today()
        threshold_days = max(0, int(stale_after_days))
        stale_cutoff = today - timedelta(days=threshold_days)

        to_refresh = []
        for ticker in tracked:
            latest = self._parse_day(latest_by_ticker.get(ticker))
            if force or latest is None or latest < stale_cutoff:
                to_refresh.append(ticker)

        if not to_refresh:
            logger.info("Market refresh planning complete: nothing to refresh")
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
                }
            )
            return status

        worker_count = min(max(1, int(max_workers)), max(2, os.cpu_count() or 4, 8))
        sequential_refresh = False
        if source_name == "sweden.json":
            # Sweden tickers are numerous enough that the default worker pool
            # is a better tradeoff than the old single-worker throttle.
            worker_count = max(worker_count, min(8, len(to_refresh)))
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
            detail=f"Refreshing {total} tickers",
            label="Market Refresh",
            active=True,
        )
        logger.info("Market refresh phase: refreshing %d tickers", total)

        if sequential_refresh:
            logger.info("Market refresh worker mode: sequential")
            for ticker in to_refresh:
                try:
                    symbol, df = self._build_refresh_frame(
                        ticker,
                        depth,
                        warmup_days,
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
                        detail=f"{completed}/{total} tickers processed",
                        label="Market Refresh",
                        active=True,
                    )
                    if completed < total:
                        time.sleep(0.1)
        else:
            logger.info("Market refresh worker mode: parallel (%d workers)", worker_count)
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(
                        self._build_refresh_frame,
                        ticker,
                        depth,
                        warmup_days,
                    ): ticker
                    for ticker in to_refresh
                }
                for future in as_completed(futures):
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
                        if "No data found" in message or "No rows returned" in message:
                            self.delisting_tracker.mark_missing(ticker, reason=message)
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
                            detail=f"{completed}/{total} tickers processed",
                            label="Market Refresh",
                            active=True,
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
