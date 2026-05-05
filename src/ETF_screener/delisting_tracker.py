"""Helpers for tracking missing tickers before promoting them to blacklist."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper()


def _parse_day(raw: object | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw).split(" ")[0], "%Y-%m-%d").date()
    except ValueError:
        return None


class DelistingTracker:
    """Persist missing-ticker state and promote old misses into the blacklist."""

    def __init__(
        self,
        blacklist_file: str | Path = "config/blacklist.json",
        missing_file: str | Path | None = None,
    ) -> None:
        self.blacklist_file = Path(blacklist_file)
        self.missing_file = (
            Path(missing_file)
            if missing_file is not None
            else self.blacklist_file.with_name("delisting_state.json")
        )

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception:
            return {}
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _save_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def load_blacklist(self) -> dict[str, dict[str, Any]]:
        raw = self._load_json(self.blacklist_file)
        return {
            _normalize_ticker(ticker): (
                value if isinstance(value, dict) else {"status": str(value)}
            )
            for ticker, value in raw.items()
            if _normalize_ticker(ticker)
        }

    def load_missing_state(self) -> dict[str, dict[str, Any]]:
        raw = self._load_json(self.missing_file)
        return {
            _normalize_ticker(ticker): (
                value if isinstance(value, dict) else {"reason": str(value)}
            )
            for ticker, value in raw.items()
            if _normalize_ticker(ticker)
        }

    def is_blacklisted(self, ticker: str) -> bool:
        return _normalize_ticker(ticker) in self.load_blacklist()

    def filter_blacklisted(self, tickers: list[str] | tuple[str, ...]) -> list[str]:
        blacklist = self.load_blacklist()
        return [
            t
            for t in (_normalize_ticker(t) for t in tickers)
            if t and t not in blacklist
        ]

    def mark_missing(
        self,
        ticker: str,
        reason: str = "No data found during refresh",
        observed_on: date | None = None,
    ) -> dict[str, Any]:
        ticker_key = _normalize_ticker(ticker)
        if not ticker_key or self.is_blacklisted(ticker_key):
            return {}

        today = observed_on or date.today()
        state = self.load_missing_state()
        entry = state.get(ticker_key, {})
        first_missing = _parse_day(entry.get("first_missing")) or today
        missing_days = max(0, (today - first_missing).days)
        payload = {
            "status": "missing",
            "reason": reason,
            "first_missing": first_missing.isoformat(),
            "last_missing": today.isoformat(),
            "missing_days": missing_days,
        }
        state[ticker_key] = payload
        self._save_json(self.missing_file, state)
        return payload

    def clear_missing(self, ticker: str) -> None:
        ticker_key = _normalize_ticker(ticker)
        if not ticker_key:
            return
        state = self.load_missing_state()
        if ticker_key in state:
            del state[ticker_key]
            self._save_json(self.missing_file, state)

    def promote_aged_missing(
        self,
        threshold_days: int = 14,
        today: date | None = None,
    ) -> list[str]:
        current_day = today or date.today()
        state = self.load_missing_state()
        blacklist = self.load_blacklist()
        promoted: list[str] = []
        changed = False

        for ticker, entry in list(state.items()):
            first_missing = _parse_day(entry.get("first_missing")) or _parse_day(
                entry.get("last_missing")
            )
            if first_missing is None:
                continue
            age_days = max(0, (current_day - first_missing).days)
            if age_days < threshold_days:
                continue

            if ticker not in blacklist:
                blacklist[ticker] = {
                    "status": "invalid",
                    "reason": entry.get("reason", "No data found during refresh"),
                    "first_missing": first_missing.isoformat(),
                    "missing_days": age_days,
                    "promoted_on": current_day.isoformat(),
                }
                promoted.append(ticker)
                changed = True

            del state[ticker]
            changed = True

        if changed:
            self._save_json(self.blacklist_file, blacklist)
            self._save_json(self.missing_file, state)

        return promoted
