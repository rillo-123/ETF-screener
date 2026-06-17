"""Build config/nasdaq.json from the official Nasdaq Trader symbol directory."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
INCLUDE_TOKENS = (
    "COMMON STOCK",
    "COMMON SHARES",
    "ORDINARY SHARE",
    "ORDINARY SHARES",
    "AMERICAN DEPOSITARY SHARES",
    "ADS",
)
EXCLUDE_TOKENS = (
    "WARRANT",
    "UNIT",
    "RIGHT",
    "PREFERRED",
    "NOTES",
    "BOND",
    "DEPOSITARY SHARE",
    "ACQUISITION",
    "BLANK CHECK",
)


def _fetch_source_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _clean_name(security_name: str, symbol: str) -> str:
    base = str(security_name or "").split(" - ", 1)[0].strip()
    return base or str(symbol or "").strip().upper()


def _include_row(row: dict[str, str]) -> bool:
    symbol = str(row.get("Symbol") or "").strip().upper()
    if not symbol or symbol.startswith("FILE CREATION TIME"):
        return False

    if str(row.get("Test Issue") or "").strip().upper() != "N":
        return False
    if str(row.get("ETF") or "").strip().upper() == "Y":
        return False
    if str(row.get("NextShares") or "").strip().upper() == "Y":
        return False

    financial_status = str(row.get("Financial Status") or "").strip().upper()
    if financial_status not in {"", "N"}:
        return False

    security_name = str(row.get("Security Name") or "").strip()
    upper_name = security_name.upper()
    if not any(token in upper_name for token in INCLUDE_TOKENS):
        return False
    if any(token in upper_name for token in EXCLUDE_TOKENS):
        return False
    return True


def build_universe(text: str) -> dict[str, dict[str, object]]:
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    payload: dict[str, dict[str, object]] = {}
    for row in reader:
        if not _include_row(row):
            continue
        symbol = str(row.get("Symbol") or "").strip().upper()
        security_name = str(row.get("Security Name") or "").strip()
        payload[symbol] = {
            "status": "active",
            "name": _clean_name(security_name, symbol),
            "security_name": security_name,
            "symbol": symbol,
            "yahoo_symbol": symbol,
            "exchange": "Nasdaq / United States",
            "country": "United States",
            "market": "NASDAQ",
            "currency": "USD",
            "asset_class": "SHARES",
            "market_category": str(row.get("Market Category") or "").strip(),
            "financial_status": str(row.get("Financial Status") or "").strip() or "N",
            "round_lot_size": str(row.get("Round Lot Size") or "").strip(),
            "source": SOURCE_URL,
        }
    return dict(sorted(payload.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="config/nasdaq.json",
        help="Output path for the generated universe JSON",
    )
    args = parser.parse_args()

    text = _fetch_source_text(SOURCE_URL)
    payload = build_universe(text)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} Nasdaq symbols to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
