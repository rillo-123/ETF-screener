"""Curated ETF facts that complement Yahoo Finance market data.

Yahoo is used for changing market data (prices, volume and history).  This
module deliberately owns the slowly changing product facts that Yahoo often
does not expose consistently for UCITS ETFs.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CATALOGUE_PATH = Path("config") / "ucits_catalogue.json"
FILTER_FIELDS = {
    "asset_class",
    "issuer",
    "distribution_policy",
    "replication",
    "fund_domicile",
    "currency",
}


class CatalogueError(ValueError):
    """Raised when the local catalogue has an invalid shape."""


def _normalise_fund(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CatalogueError("Each catalogue fund must be an object")
    ticker = str(raw.get("ticker", "")).strip().upper()
    name = str(raw.get("name", "")).strip()
    isin = str(raw.get("isin", "")).strip().upper()
    if not ticker or not name or len(isin) != 12:
        raise CatalogueError("Each fund requires ticker, name, and a 12-character ISIN")
    fund = {key: raw.get(key) for key in raw}
    fund["ticker"] = ticker
    fund["name"] = name
    fund["isin"] = isin
    try:
        ter_pct = float(raw["ter_pct"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogueError(f"{ticker} requires a numeric ter_pct") from exc
    if ter_pct < 0:
        raise CatalogueError(f"{ticker} has a negative ter_pct")
    fund["ter_pct"] = ter_pct
    return fund


@lru_cache(maxsize=4)
def load_catalogue(
    path: str = str(DEFAULT_CATALOGUE_PATH),
) -> tuple[dict[str, Any], ...]:
    """Load and validate the curated catalogue once per source file."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogueError(f"Could not read catalogue at {path}") from exc
    funds = payload.get("funds") if isinstance(payload, dict) else None
    if not isinstance(funds, list):
        raise CatalogueError("Catalogue requires a funds list")
    normalised = tuple(_normalise_fund(fund) for fund in funds)
    tickers = [fund["ticker"] for fund in normalised]
    if len(tickers) != len(set(tickers)):
        raise CatalogueError("Catalogue tickers must be unique")
    return normalised


def filter_catalogue(
    funds: Iterable[dict[str, Any]],
    *,
    search: str | None = None,
    max_ter_pct: float | None = None,
    **filters: str | None,
) -> list[dict[str, Any]]:
    """Return product facts matching transparent catalogue filters."""
    unknown = set(filters) - FILTER_FIELDS
    if unknown:
        raise CatalogueError(f"Unsupported filters: {', '.join(sorted(unknown))}")
    needle = (search or "").strip().casefold()
    result = []
    for fund in funds:
        haystack = " ".join(
            str(fund.get(key, "")) for key in ("ticker", "name", "isin", "exposure")
        ).casefold()
        if needle and needle not in haystack:
            continue
        if max_ter_pct is not None and float(fund["ter_pct"]) > max_ter_pct:
            continue
        if any(
            value is not None
            and str(fund.get(field, "")).casefold() != value.strip().casefold()
            for field, value in filters.items()
        ):
            continue
        result.append(dict(fund))
    return sorted(result, key=lambda fund: (float(fund["ter_pct"]), fund["ticker"]))


def compare_catalogue(
    funds: Iterable[dict[str, Any]], tickers: Iterable[str]
) -> list[dict[str, Any]]:
    """Return selected funds in requested order, rejecting unknown tickers."""
    by_ticker = {str(fund["ticker"]).upper(): fund for fund in funds}
    selected = [
        str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()
    ]
    if not selected:
        raise CatalogueError("Select at least one ticker to compare")
    unknown = [ticker for ticker in selected if ticker not in by_ticker]
    if unknown:
        raise CatalogueError(f"Unknown catalogue ticker(s): {', '.join(unknown)}")
    return [dict(by_ticker[ticker]) for ticker in selected]
