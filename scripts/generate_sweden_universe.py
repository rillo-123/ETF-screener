"""Build the Swedish universe from Nasdaq Stockholm, First North, and Spotlight."""

from __future__ import annotations

import json
import re
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SWEDEN_JSON = ROOT / "config" / "sweden.json"
NASDAQ_URL = "https://api.nasdaq.com/api/nordic/screener/shares"
SPOTLIGHT_SEARCH_URL = "https://www.spotlightstockmarket.com/Umbraco/api/companyapi/CompanySimpleSearch"
SPOTLIGHT_PAGE = "https://www.spotlightstockmarket.com"


def _request(url: str, *, form: dict[str, str] | None = None) -> str:
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    if form is not None:
        payload = urlencode(form).encode("utf-8")
        request = Request(url, data=payload, headers=headers, method="POST")
    else:
        request = Request(url, headers=headers)
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _nasdaq_first_north() -> dict[str, dict[str, object]]:
    query = urlencode({"category": "FIRST_NORTH", "tableonly": "false", "market": "STO"})
    payload = json.loads(_request(f"{NASDAQ_URL}?{query}"))
    rows = payload.get("data", {}).get("instrumentListing", {}).get("rows", [])
    result = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol or str(row.get("assetClass") or "").upper() != "SHARES":
            continue
        result[f"{symbol}.ST"] = {
            "status": "active",
            "name": str(row.get("fullName") or symbol).strip(),
            "symbol": symbol,
            "yahoo_symbol": f"{symbol}.ST",
            "exchange": "Nasdaq First North Stockholm / Sweden",
            "country": "Sweden",
            "market": "FIRST_NORTH_STO",
            "currency": str(row.get("currency") or "SEK"),
            "asset_class": "SHARES",
            "isin": str(row.get("isin") or ""),
            "orderbook_id": str(row.get("orderbookId") or ""),
            "source": f"{NASDAQ_URL}?{query}",
        }
    return result


def _spotlight_urls() -> dict[str, str]:
    # The directory returns up to 135 rows per request. Prefix searches expose
    # the complete directory without relying on an undocumented page parameter.
    searches = [a + b for a in string.ascii_lowercase for b in string.ascii_lowercase]
    urls: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {
            pool.submit(
                _request,
                SPOTLIGHT_SEARCH_URL,
                form={"searchText": prefix, "lang": "en-US", "getAll": "true"},
            ): prefix
            for prefix in searches
        }
        for future in as_completed(futures):
            try:
                payload = json.loads(future.result())
            except Exception:
                continue
            for row in payload.get("results", []):
                url = str(row.get("url") or "").strip()
                match = re.search(r"InstrumentId=([^&\"']+)", url, re.IGNORECASE)
                if match:
                    urls[match.group(1)] = str(row.get("heading") or "").strip()
    return urls


def _spotlight() -> dict[str, dict[str, object]]:
    urls = _spotlight_urls()
    result: dict[str, dict[str, object]] = {}

    def fetch(item: tuple[str, str]) -> tuple[str, str, str] | None:
        instrument_id, name = item
        try:
            html = _request(f"{SPOTLIGHT_PAGE}/en/companies/irabout/?InstrumentId={instrument_id}")
        except Exception:
            return None
        match = re.search(r'"Symbol"\s*:\s*"([^"\\]+)"', html)
        symbol = match.group(1).strip().upper() if match else ""
        return instrument_id, name, symbol

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(fetch, item) for item in urls.items()]
        for future in as_completed(futures):
            row = future.result()
            if not row:
                continue
            instrument_id, name, symbol = row
            if not symbol or symbol in {"-", "N/A"}:
                continue
            yahoo_symbol = f"{symbol}.ST"
            result[yahoo_symbol] = {
                "status": "active",
                "name": name or symbol,
                "symbol": symbol,
                "yahoo_symbol": yahoo_symbol,
                "exchange": "Spotlight Stock Market / Sweden",
                "country": "Sweden",
                "market": "SPOTLIGHT_STO",
                "currency": "SEK",
                "asset_class": "SHARES",
                "instrument_id": instrument_id,
                "source": f"{SPOTLIGHT_PAGE}/en/market-overview/our-companies/",
            }
    return result


def main() -> int:
    existing = json.loads(SWEDEN_JSON.read_text(encoding="utf-8"))
    combined = dict(existing)
    combined.update(_nasdaq_first_north())
    combined.update(_spotlight())
    SWEDEN_JSON.write_text(json.dumps(dict(sorted(combined.items())), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(combined)} Swedish symbols to {SWEDEN_JSON}")
    print(f"Added {len(combined) - len(existing)} symbols from First North and Spotlight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
