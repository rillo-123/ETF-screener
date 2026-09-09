"""Resume the focused five-year Nasdaq download without strategy-specific copies.

Run from the repository root. --stage-dir allows downloading while a storage
migration is in progress; staged files are not active dashboard history yet.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from ETF_screener.config_loader import get_paths
from ETF_screener.database import ETFDatabase
from ETF_screener.indicators import add_indicators
from ETF_screener.market_data_provider import create_market_data_provider
from ETF_screener.storage import ParquetStorage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-dir")
    args = parser.parse_args()
    focus = json.loads(Path("config/nasdaq_focus.json").read_text(encoding="utf-8"))
    directory = Path(args.stage_dir or get_paths()["data"]["parquet"])
    directory.mkdir(parents=True, exist_ok=True)
    storage = ParquetStorage(str(directory))
    checkpoint = directory / "nasdaq-history-status.json"
    status = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    provider = create_market_data_provider()
    db = None if args.stage_dir else ETFDatabase()
    consecutive_failures = 0
    for index, ticker in enumerate(focus["tickers"], 1):
        previous = status.get(ticker, {})
        if (
            previous.get("status") == "downloaded"
            and not storage.load_etf_data(ticker).empty
        ):
            continue
        try:
            frame = provider.fetch_historical_data(ticker, days=1830)
            if frame.empty:
                raise ValueError("Provider returned no history")
            frame = (
                frame.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
            )
            if pd.to_datetime(frame["Date"]).max().date().isoformat() < focus["as_of"]:
                raise ValueError(
                    "Provider history is older than the selection snapshot"
                )
            if (
                not frame[["Open", "High", "Low", "Close", "Volume"]]
                .notna()
                .all()
                .all()
            ):
                raise ValueError("Incomplete OHLCV history")
            frame = add_indicators(frame)
            storage.save_etf_data(frame, ticker)
            if db is not None:
                db.insert_dataframe(frame, ticker)
            status[ticker] = {
                "status": "downloaded",
                "rows": len(frame),
                "start": str(frame.Date.min()),
                "end": str(frame.Date.max()),
            }
            consecutive_failures = 0
        except Exception as exc:
            status[ticker] = {"status": "failed", "error": str(exc)}
            consecutive_failures += 1
        temporary = checkpoint.with_suffix(".tmp")
        temporary.write_text(json.dumps(status, indent=2), encoding="utf-8")
        temporary.replace(checkpoint)
        print(f"{index}/{len(focus['tickers'])} {ticker}: {status[ticker]}", flush=True)
        if consecutive_failures >= 5:
            raise RuntimeError(
                "Five consecutive provider failures; progress saved for retry"
            )
    if any(
        status.get(ticker, {}).get("status") != "downloaded"
        for ticker in focus["tickers"]
    ):
        raise RuntimeError("Some symbols failed; rerun to retry only those symbols")


if __name__ == "__main__":
    main()
