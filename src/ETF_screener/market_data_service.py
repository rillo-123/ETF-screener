"""Market data freshness helpers for the dashboard."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import add_indicators
from ETF_screener.shortlist_engine import ETFShortlistEngine
from ETF_screener.storage import ParquetStorage
from ETF_screener.yfinance_fetcher import YFinanceFetcher


class MarketDataRefresher:
    """Track and refresh the underlying ETF market data cache."""

    INDICATOR_WARMUP_DAYS = 90

    def __init__(
        self,
        db_path: str | None = None,
        etfs_file: str = "config/etfs.json",
        blacklist_file: str = "config/blacklist.json",
        fetcher: Optional[YFinanceFetcher] = None,
        storage: Optional[ParquetStorage] = None,
    ):
        self.db = ETFDatabase(db_path=db_path)
        self.etfs_file = Path(etfs_file)
        self.blacklist_file = Path(blacklist_file)
        self.fetcher = fetcher or YFinanceFetcher()
        self.storage = storage or ParquetStorage()

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

    def _load_tracked_tickers(self) -> list[str]:
        blacklist = self._load_blacklist()
        tickers: set[str] = set()
        if self.etfs_file.exists():
            with open(self.etfs_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
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
            return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

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
        normalized = normalized[["Date", "Open", "High", "Low", "Close", "Volume", "Dividends"]]
        normalized = normalized.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
        normalized["Volume"] = pd.to_numeric(normalized["Volume"], errors="coerce").fillna(0)
        normalized["Dividends"] = pd.to_numeric(normalized["Dividends"], errors="coerce").fillna(0)
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
            fetch_start = latest_day - timedelta(days=max(5, int(warmup_days)))
            fetched = self.fetcher.fetch_historical_data(
                ticker,
                start_date=fetch_start,
                end_date=datetime.now(),
            )
            fresh_slice = self._normalize_price_frame(fetched)
            merged = self._normalize_price_frame(pd.concat([existing, fresh_slice], ignore_index=True))

        if merged.empty:
            raise ValueError(f"No rows returned for {ticker}")

        enriched = add_indicators(merged)
        return ticker, enriched

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
            "latest_shortlist_date": shortlist_day.isoformat() if shortlist_day else None,
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
    ) -> dict[str, Any]:
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
        refreshed = 0
        failed = 0
        errors: list[dict[str, str]] = []

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
                    refreshed += 1
                except Exception as exc:
                    failed += 1
                    errors.append({"ticker": ticker, "error": str(exc)})

        shortlist_rebuilt = False
        if rebuild_shortlist:
            engine = ETFShortlistEngine(
                db_path=str(self.db.db_path),
                metadata_path=str(self.etfs_file),
                storage=self.storage,
            )
            engine.build_shortlist(max_workers=max_workers)
            shortlist_rebuilt = True

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
        return status
