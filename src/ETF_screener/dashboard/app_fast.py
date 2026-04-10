import json
import logging as _logging_mod
import math
import pandas as pd
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates

from ETF_screener.database import ETFDatabase
from ETF_screener.plotter_plotly import InteractivePlotter
from ETF_screener.yfinance_fetcher import YFinanceFetcher
from ETF_screener.indicators import add_indicators
from ETF_screener.backtester import Backtester
from ETF_screener.logging_setup import setup_logging, get_log_file

app = FastAPI(title="ETF Discovery Lab API")
fetcher = YFinanceFetcher()  # For on-demand fetching

# Initialise logging as early as possible so that all subsequent imports and
# uvicorn log records are captured in the timestamped debug file.
logger = setup_logging()


def _safe_float(val, default=None):
    """Return val as float, or default if it is NaN/inf/None."""
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _rank_matches(matches: list[dict]) -> list[dict]:
    """Composite breakdown-quality score, sorted descending.

    Components (min-max normalised across result set):
      Volume       40 % — higher = more conviction
      EMA 50 slope 35 % — more negative = stronger downtrend (inverted)
      Day change % 25 % — more negative = more decisive bar  (inverted)
    """
    if not matches:
        return matches

    def _minmax(vals: list[float], invert: bool = False) -> list[float]:
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return [0.5] * len(vals)
        ns = [(v - mn) / (mx - mn) for v in vals]
        return [1.0 - n if invert else n for n in ns]

    vols = [m["volume"] for m in matches]
    slopes = [m.get("ema_50_slope") or 0.0 for m in matches]
    changes = [m.get("change_pct") or 0.0 for m in matches]

    vol_s = _minmax(vols)
    slope_s = _minmax(slopes, invert=True)
    change_s = _minmax(changes, invert=True)

    for i, m in enumerate(matches):
        m["score"] = round(0.40 * vol_s[i] + 0.35 * slope_s[i] + 0.25 * change_s[i], 3)

    return sorted(matches, key=lambda x: x["score"], reverse=True)


def _format_basic_screen_matches(df: pd.DataFrame) -> list[dict]:
    """Normalize simple screen rows to the shape the dashboard expects."""
    matches = []
    for _, row in df.iterrows():
        matches.append(
            {
                "ticker": row.get("ticker", "UNKNOWN"),
                "close": _safe_float(row.get("close", row.get("Close", 0)), 0.0),
                "volume": _safe_float(row.get("volume", row.get("Volume", 0)), 0.0),
                "status": "Trending",
                "return_pct": 0.0,
                "change_pct": 0.0,
                "supertrend": _safe_float(
                    row.get("supertrend", row.get("Supertrend", 0)), 0.0
                ),
                "st_lower": _safe_float(
                    row.get("st_lower", row.get("ST_Lower", 0)), 0.0
                ),
            }
        )
    return matches


# Setup templates and static files
# We can keep the same template files as Flask (Jinja2 is compatible)
templates = Jinja2Templates(directory="src/ETF_screener/dashboard/templates")


def get_strategies():
    """Load all .dsl strategies from the strategies directory."""
    strategies = []
    strat_dir = Path("strategies")
    if strat_dir.exists():
        for dsl_file in strat_dir.glob("*.dsl"):
            strategies.append(dsl_file.stem)
    return sorted(strategies)


def load_strategy_content(name):
    """Load the content of a strategy file."""
    strat_path = Path("strategies") / f"{name}.dsl"
    if strat_path.exists():
        return strat_path.read_text(encoding="utf-8")
    return ""


def parse_strategy_scripts(content: str) -> tuple[str, str]:
    """Parse layered DSL into entry/exit expressions."""
    import re

    trigger_terms = re.findall(
        r"^TRIGGER:\s*(.*)", content, re.IGNORECASE | re.MULTILINE
    )
    filter_terms = re.findall(r"^FILTER:\s*(.*)", content, re.IGNORECASE | re.MULTILINE)
    entry_terms = re.findall(r"^ENTRY:\s*(.*)", content, re.IGNORECASE | re.MULTILINE)
    exit_terms = re.findall(r"^EXIT:\s*(.*)", content, re.IGNORECASE | re.MULTILINE)

    entry_parts = [
        f"({t.strip()})"
        for t in (trigger_terms + filter_terms + entry_terms)
        if t.strip()
    ]
    exit_parts = [f"({t.strip()})" for t in exit_terms if t.strip()]

    final_entry = " and ".join(entry_parts)
    final_exit = " or ".join(exit_parts) if exit_parts else "False"
    return final_entry, final_exit


# Database access function (FastAPI style)
def get_db():
    return ETFDatabase(db_path="data/etfs.db")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Suppress noisy favicon 404s until a real icon is added."""
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page."""
    db = get_db()
    conn = db._get_connection()
    try:
        # Get all distinct tickers from DB OR from etfs.json if DB is fresh
        tickers = pd.read_sql_query(
            "SELECT DISTINCT ticker FROM etf_data ORDER BY ticker", conn
        )["ticker"].tolist()
        if not tickers:
            # Fallback to etfs.json if DB is empty
            etf_path = Path("config/etfs.json")
            if etf_path.exists():
                with open(etf_path, "r") as f:
                    tickers = json.load(f).get("tickers", [])
    except Exception:
        tickers = []

    strategies = get_strategies()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"tickers": tickers, "strategies": strategies},
    )


@app.get("/api/strategies")
async def list_strategies():
    """Get list of available strategies."""
    return get_strategies()


@app.get("/api/strategy/{name}")
async def get_strategy(name: str):
    """Get strategy content."""
    content = load_strategy_content(name)
    if not content:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"name": name, "content": content}


@app.post("/api/strategy/save")
async def save_strategy(request: Request):
    """Save a strategy to the strategies directory."""
    data = await request.json()
    name = data.get("name")
    content = data.get("content")

    if not name or not content:
        raise HTTPException(status_code=400, detail="Name and content required")

    # Sanitize name
    name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Invalid strategy name")

    strat_path = Path("strategies") / f"{name}.dsl"
    try:
        strat_path.parent.mkdir(parents=True, exist_ok=True)
        strat_path.write_text(content, encoding="utf-8")
        return {"status": "success", "message": f"Saved to {strat_path.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/screen")
async def screen(strategy: Optional[str] = None, dsl_content: Optional[str] = None):
    """Run a dynamic screen based on selected strategies or provided DSL."""
    logger.info("=== SCREEN ENDPOINT START ===")
    logger.info(
        "Params: strategy=%s, dsl_content=%s",
        strategy,
        "PROVIDED" if dsl_content else "NONE",
    )
    db = get_db()

    try:
        # Priority: 1. Provided DSL content (from Lab), 2. Named strategy (from dropdown)
        content = ""
        if dsl_content:
            content = dsl_content
            logger.info("Using provided DSL, length: %d chars", len(content))
        elif strategy:
            content = load_strategy_content(strategy)
            logger.info(
                "Loaded strategy '%s', length: %d chars",
                strategy,
                len(content) if content else 0,
            )

        if not content:
            logger.info("No strategy/DSL, using fallback basic trend screen")
            # Fallback to simple trend screen if no strategy found/selected
            conn = db._get_connection()
            query = """
                SELECT ticker, close, volume, supertrend, st_lower
                FROM etf_data 
                WHERE date = (SELECT MAX(date) FROM etf_data)
                AND close > st_lower
                ORDER BY volume DESC
                LIMIT 50
            """
            df = pd.read_sql_query(query, conn)
            matches = _format_basic_screen_matches(df)
            return {
                "matches": matches,
                "errors": [],
                "total_errors": 0,
                "total_candidates": len(matches),
            }

        final_entry, final_exit = parse_strategy_scripts(content)
        logger.info(
            "Strategy parsed. Entry script length: %d, Exit script length: %d",
            len(final_entry),
            len(final_exit),
        )

        # Build a cleaner ticker universe so the backtester doesn't waste workers on stale symbols.
        conn = db._get_connection()
        universe_query = """
            WITH ranked AS (
                SELECT
                    ticker,
                    date,
                    volume,
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
                FROM etf_data
            ),
            agg AS (
                SELECT
                    ticker,
                    MAX(date) AS last_date,
                    COUNT(*) AS total_rows,
                    SUM(CASE WHEN volume > 0 THEN 1 ELSE 0 END) AS nonzero_volume_rows,
                    SUM(CASE WHEN rn <= 30 THEN 1 ELSE 0 END) AS recent_rows,
                    SUM(CASE WHEN rn <= 30 AND volume = 0 THEN 1 ELSE 0 END) AS recent_zero_volume_rows
                FROM ranked
                GROUP BY ticker
            )
            SELECT ticker
            FROM agg
            WHERE total_rows >= 50
              AND nonzero_volume_rows >= 10
              AND recent_rows >= 10
              AND recent_zero_volume_rows < 2
              AND last_date >= date('now', '-180 day')
        """
        universe_df = pd.read_sql_query(universe_query, conn)
        tickers = universe_df["ticker"].tolist()
        logger.info("Ticker universe built: %d tickers to screen", len(tickers))
        # Run backtest for current status
        bt = Backtester()
        logger.info("Starting parallel backtest for %d tickers", len(tickers))
        results = bt.run_parallel_backtest(
            tickers,
            bt.scripted_strategy,
            days=200,
            strategy_kwargs={"entry_script": final_entry, "exit_script": final_exit},
        )
        logger.info(
            "Backtest complete, processing %d results", len(results) if results else 0
        )

        # Filter for currently active signals (in a position or just triggered)
        matches = []
        errors = []
        for idx, res in enumerate(results):
            if not res:
                continue

            ticker = res.get("ticker", "UNKNOWN")
            if "error" in res:
                logger.debug("Backtest error for %s: %s", ticker, res["error"])
                errors.append({"ticker": ticker, "error": res["error"]})
                continue

            df = res.get("df")
            if df is None or df.empty:
                logger.debug("No data for %s", ticker)
                errors.append(
                    {"ticker": ticker, "error": "No data or empty strategy result"}
                )
                continue

            # Align with CLI behavior: a match is an active entry signal on the latest bar.
            try:
                last_row = df.iloc[-1]
                latest_signal = last_row.get("signal", last_row.get("Signal", 0))
                has_latest_entry = latest_signal == 1

                # Additional metadata for the UI
                prev_row = df.iloc[-2] if len(df) > 1 else last_row

                if has_latest_entry:
                    # Handle possible column name variations (database vs dataframe)
                    close_val = _safe_float(
                        (
                            last_row["close"]
                            if "close" in last_row
                            else last_row.get("Close", 0)
                        ),
                        0.0,
                    )
                    vol_val = _safe_float(
                        (
                            last_row["volume"]
                            if "volume" in last_row
                            else last_row.get("Volume", 0)
                        ),
                        0.0,
                    )
                    prev_close = _safe_float(
                        (
                            prev_row["close"]
                            if "close" in prev_row
                            else prev_row.get("Close", 0)
                        ),
                        0.0,
                    )
                    change_pct = _safe_float(
                        ((close_val / prev_close) - 1) * 100 if prev_close else 0, 0.0
                    )
                    ema_50_slope_val = _safe_float(last_row.get("ema_50_slope"), 0.0)

                    matches.append(
                        {
                            "ticker": ticker,
                            "close": close_val,
                            "volume": vol_val,
                            "status": "Entry Signal",
                            "return_pct": _safe_float(
                                res.get("total_return_pct", 0), 0.0
                            ),
                            "change_pct": change_pct,
                            "ema_50_slope": ema_50_slope_val,
                        }
                    )
                    logger.info("Match found: %s (signal on latest bar)", ticker)
            except Exception as e:
                logger.error(
                    "Error processing ticker %s: %s", ticker, str(e), exc_info=True
                )
                errors.append({"ticker": ticker, "error": str(e)})

        # Rank by composite breakdown-quality score
        matches = _rank_matches(matches)
        logger.info(
            "Screen complete. Matches: %d, Errors: %d", len(matches), len(errors)
        )

        # Return matched ETFs along with errors for the UI
        return {
            "matches": matches,
            "errors": errors[:50],  # Limit errors returned to UI
            "total_errors": len(errors),
            "total_candidates": len(tickers),
        }

    except KeyboardInterrupt:
        logger.warning("Screen run interrupted by KeyboardInterrupt", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "matches": [],
                "errors": [{"ticker": "SYSTEM", "error": "Screen run interrupted"}],
                "total_errors": 1,
                "total_candidates": 0,
            },
        )
    except Exception as e:
        logger.error("Screen endpoint failed: %s", str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "matches": [],
                "errors": [{"ticker": "SYSTEM", "error": str(e)}],
                "total_errors": 1,
                "total_candidates": 0,
            },
        )


@app.get("/api/chart/{ticker}")
async def get_chart(
    ticker: str,
    days: int = 365 * 2,
    strategy: Optional[str] = None,
    dsl_content: Optional[str] = None,
):
    """Generate and return an interactive chart for a ticker. Fetches if missing."""
    db = get_db()
    ticker = ticker.upper()

    # 1. Try to get data from database
    conn = db._get_connection()
    safe_days = max(1, min(days, 3650))
    query = f"SELECT * FROM etf_data WHERE ticker = ? ORDER BY date DESC LIMIT {safe_days}"  # nosec B608 - safe_days is int-clamped
    df = pd.read_sql_query(query, conn, params=(ticker,))

    # 2. If data is missing or too sparse (less than 100 days for indicators), fetch it!
    # Increased minimum requirement to 100 days to ensure enough lookback for EMA50 and ATR
    if df.empty or len(df) < 100:
        logger.info(
            "Cache miss for %s (or insufficient data, count=%d). Fetching from Yahoo Finance...",
            ticker,
            len(df),
        )
        try:
            # Fetch fresh data - Updated to use correct method name: fetch_historical_data
            # Force at least 365 days of data for high resolution indicators
            fetched_df = fetcher.fetch_historical_data(ticker, days=max(days, 365))
            if not fetched_df.empty:
                logger.info(
                    "Fetched %d rows for %s. Processing indicators...",
                    len(fetched_df),
                    ticker,
                )
                # Add indicators before storing
                processed_df = add_indicators(fetched_df)

                # Check if supertrend was calculated
                has_st = (
                    not processed_df["Supertrend"].isna().all()
                    if "Supertrend" in processed_df.columns
                    else False
                )
                logger.info(
                    "Indicator processing complete for %s. Supertrend calculated: %s",
                    ticker,
                    has_st,
                )

                # Store in DB for next time
                for _, row in processed_df.iterrows():
                    db.insert_etf_data(
                        ticker=ticker,
                        date=row["Date"].strftime("%Y-%m-%d"),
                        open_price=row["Open"],
                        high=row["High"],
                        low=row["Low"],
                        close=row["Close"],
                        volume=int(row["Volume"]),
                        ema_50=row.get("EMA_50"),
                        supertrend=row.get("Supertrend"),
                        st_upper=row.get("ST_Upper"),
                        st_lower=row.get("ST_Lower"),
                    )

                # Use the new data for the plot
                df = processed_df.sort_values("Date").tail(days)
        except Exception as e:
            logger.warning("Failed to fetch %s on demand: %s", ticker, e)
            # Instead of crashing let's return a specific error that the UI can catch
            raise HTTPException(
                status_code=404, detail=f"Data fetch failed for {ticker}: {str(e)}"
            )

    if df.empty:
        raise HTTPException(
            status_code=404, detail=f"No data found for ticker {ticker}"
        )

    df = df.sort_values("date" if "date" in df.columns else "Date")
    # Match the plotter's expected column names (normalized)
    rename_cols = {
        "date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "ema_50": "EMA_50",
        "supertrend": "Supertrend",
        "st_upper": "ST_Upper",
        "st_lower": "ST_Lower",
        "signal": "Signal",
    }
    # Direct rename to ensure uppercase matching for plotter
    df = df.rename(columns=rename_cols)

    # Check if we have the critical columns after normalization
    required = ["Date", "Close", "Open", "High", "Low"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        logger.warning(
            "Normalizing column names from DB for %s. Missing: %s. Available: %s",
            ticker,
            missing,
            df.columns.tolist(),
        )
        # Check if we have 'open_price' instead of 'open' (some legacy code used 'open_price')
        if "open_price" in df.columns and "Open" not in df.columns:
            df = df.rename(columns={"open_price": "Open"})
            missing = [c for c in required if c not in df.columns]

    if missing:
        # If still missing, we might have a data integrity issue
        logger.error(
            "CRITICAL: %s is missing required columns %s for plotting.", ticker, missing
        )
        raise HTTPException(
            status_code=500,
            detail=f"Database schema mismatch for {ticker}. Missing {missing}",
        )

    strategy_content = ""
    if dsl_content:
        strategy_content = dsl_content
    elif strategy:
        strategy_content = load_strategy_content(strategy)

    if strategy_content:
        entry_script, exit_script = parse_strategy_scripts(strategy_content)
        if entry_script:
            bt = Backtester()
            try:
                strat_res = bt.scripted_strategy(
                    df.copy(),
                    ticker=ticker,
                    entry_script=entry_script,
                    exit_script=exit_script,
                )
                if (
                    isinstance(strat_res, dict)
                    and strat_res.get("df") is not None
                    and not strat_res["df"].empty
                ):
                    df = strat_res["df"]
            except Exception:
                logger.debug(
                    "Could not enrich chart data with strategy indicators for %s",
                    ticker,
                )

    plotter = InteractivePlotter()
    try:
        fig = plotter.create_plot(df, ticker, strategy_content=strategy_content)
        # Fastapi JSONResponse or direct dict return will handle this.
        # But we need to ensure it's a DICT, not a JSON string,
        # because the frontend is now expecting the un-wrapped object.
        import json

        fig_json = fig.to_json()
        fig_dict = json.loads(fig_json)
        return {
            "ticker": ticker,
            "figure": fig_json,
            "data": fig_dict.get("data", []),
            "layout": fig_dict.get("layout", {}),
        }
    except Exception as e:

        logger.exception("Plotter failed for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=f"Plot generation failed: {str(e)}")


@app.get("/api/screen/basic")
async def screen_basic():
    """Run the basic trend screen without the DSL/backtester pipeline."""
    db = get_db()
    conn = db._get_connection()
    query = """
        SELECT ticker, close, volume, supertrend, st_lower
        FROM etf_data 
        WHERE date = (SELECT MAX(date) FROM etf_data)
        AND close > st_lower
        ORDER BY volume DESC
        LIMIT 50
    """
    try:
        df = pd.read_sql_query(query, conn)
        matches = _format_basic_screen_matches(df)
        return {
            "matches": matches,
            "errors": [],
            "total_errors": 0,
            "total_candidates": len(matches),
        }
    except Exception:
        logger.exception("Basic screen failed")
        return {
            "matches": [],
            "errors": [{"ticker": "SYSTEM", "error": "Basic screen failed"}],
            "total_errors": 1,
            "total_candidates": 0,
        }


# ---------------------------------------------------------------------------
# Browser log relay — receives console.log/warn/error calls from the frontend
# and writes them into the same server-side log file.
# ---------------------------------------------------------------------------


@app.post("/api/log")
async def browser_log(request: Request):
    """Accept JSON log records from the browser and write them to the server log."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "detail": "invalid json"}

    level_map = {
        "debug": _logging_mod.DEBUG,
        "info": _logging_mod.INFO,
        "warn": _logging_mod.WARNING,
        "warning": _logging_mod.WARNING,
        "error": _logging_mod.ERROR,
    }
    browser_logger = _logging_mod.getLogger("browser")
    level = level_map.get(str(body.get("level", "info")).lower(), _logging_mod.INFO)
    message = str(body.get("message", ""))
    stack = body.get("stack")
    url = body.get("url", "")
    line = body.get("line", "")

    full_msg = message
    if url or line:
        full_msg += f"  [{url}:{line}]"
    if stack:
        full_msg += f"\n{stack}"

    browser_logger.log(level, full_msg)
    return {"status": "ok", "log_file": str(get_log_file())}


@app.post("/api/log/console")
async def save_console_logs(request: Request):
    """Receive batched console logs from the browser and save them to a console_TIME.log file."""
    import datetime
    from pathlib import Path

    try:
        body = await request.json()
        logs = body.get("logs", [])
    except Exception as e:
        logger.error("Failed to parse console logs request: %s", str(e))
        return {"status": "error", "detail": "invalid json"}

    if not logs:
        return {"status": "ok", "count": 0}

    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create console log file with timestamp
        now = datetime.datetime.now()
        console_log_file = logs_dir / f"console_{now.strftime('%Y%m%d_%H%M%S')}.log"

        # Write logs
        with open(console_log_file, "a", encoding="utf-8") as f:
            for log_entry in logs:
                timestamp = log_entry.get("timestamp", "")
                level = log_entry.get("level", "LOG")
                message = log_entry.get("message", "")
                f.write(f"[{timestamp}] {level}: {message}\n")

        logger.info(
            "Console logs saved: %d entries to %s", len(logs), console_log_file.name
        )

        # Apply retention policy: keep only 3 most recent console logs
        cleanup_old_logs(logs_dir, "console_", max_keep=3)

        return {"status": "ok", "count": len(logs), "file": str(console_log_file.name)}
    except Exception as e:
        logger.error("Error saving console logs: %s", str(e), exc_info=True)
        return {"status": "error", "detail": str(e)}


def cleanup_old_logs(logs_dir: Path, prefix: str, max_keep: int = 3):
    """Keep only the max_keep most recent log files with the given prefix."""
    import os

    try:
        log_files = sorted(
            [f for f in logs_dir.glob(f"{prefix}*.log")],
            key=lambda x: os.path.getctime(x),
            reverse=True,
        )

        # Remove all but the most recent max_keep files
        for old_file in log_files[max_keep:]:
            try:
                old_file.unlink()
                logger.info("Deleted old log file: %s", old_file.name)
            except Exception as e:
                logger.warning("Could not delete %s: %s", old_file.name, str(e))
    except Exception as e:
        logger.warning("Error during log cleanup for %s: %s", prefix, str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app_fast:app", host="127.0.0.1", port=5000, reload=True)
