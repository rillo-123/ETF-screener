import glob
from ETF_screener.config_loader import get_paths
import json
import logging as _logging_mod
import math
from datetime import date, datetime, timezone
import pandas as pd
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ETF_screener.database import ETFDatabase
from ETF_screener.backtester import Backtester
from ETF_screener.dsl_parser import parse_strategy_scripts
from ETF_screener.logging_setup import setup_logging, get_log_file
from ETF_screener.market_data_service import MarketDataRefresher
from ETF_screener.shortlist_engine import ETFShortlistEngine
from ETF_screener.swarm_world import SwarmWorldEngine
from ETF_screener.scripts.churn_strategies import (
    evaluate_strategies,
    find_recent_entry_days,
    parse_dsl_content,
)

try:
    from ETF_screener.plotter_plotly import InteractivePlotter
except ModuleNotFoundError as exc:
    # Keep the dashboard API importable when Plotly is not installed. Chart
    # endpoints will surface a clearer error if they are invoked.
    if exc.name != "plotly" and not str(exc.name).startswith("plotly"):
        raise
    InteractivePlotter = None

app = FastAPI(title="ETF Discovery Lab API")

# Initialise logging as early as possible so that all subsequent imports and
# uvicorn log records are captured in the timestamped debug file.
logger = setup_logging()

SWARM_DNA_SCHEMA_VERSION = "swarm_agent_dna_v2"
SWARM_DNA_CONFIG_PATH = Path("config") / "swarm_agent_dna.json"


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
app.mount(
    "/static",
    StaticFiles(directory="src/ETF_screener/dashboard/static"),
    name="static",
)


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


# Database access function (FastAPI style)
def get_db():
    return ETFDatabase(db_path=get_paths()["data"]["etf_db"])


def _is_stale_date(raw_date: object, threshold_days: int = 0) -> bool:
    if not raw_date:
        return True
    try:
        latest_day = pd.to_datetime(raw_date).date()
    except Exception:
        return True
    return (date.today() - latest_day).days > max(0, int(threshold_days))


def _validate_swarm_dna_payload(payload: object) -> dict:
    """Validate the browser-generated Swarm DNA payload before writing config."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Swarm DNA payload must be an object")

    if payload.get("schema_version") != SWARM_DNA_SCHEMA_VERSION:
        raise HTTPException(
            status_code=400,
            detail=f"schema_version must be {SWARM_DNA_SCHEMA_VERSION}",
        )

    top_agents = payload.get("top_agents")
    if not isinstance(top_agents, list) or not top_agents:
        raise HTTPException(status_code=400, detail="top_agents must be a non-empty list")
    if len(top_agents) > 50:
        raise HTTPException(status_code=400, detail="top_agents is unexpectedly large")

    for idx, agent in enumerate(top_agents):
        if not isinstance(agent, dict):
            raise HTTPException(status_code=400, detail=f"top_agents[{idx}] must be an object")
        dna = agent.get("dna")
        if not isinstance(dna, dict):
            raise HTTPException(status_code=400, detail=f"top_agents[{idx}].dna is required")
        if dna.get("schema_version") != SWARM_DNA_SCHEMA_VERSION:
            raise HTTPException(
                status_code=400,
                detail=f"top_agents[{idx}].dna.schema_version must be {SWARM_DNA_SCHEMA_VERSION}",
            )
        modules = dna.get("behavior_modules")
        if not isinstance(modules, list):
            raise HTTPException(
                status_code=400,
                detail=f"top_agents[{idx}].dna.behavior_modules must be a list",
            )

        for module_idx, module in enumerate(modules):
            if not isinstance(module, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"top_agents[{idx}].dna.behavior_modules[{module_idx}] must be an object",
                )
            module_type = str(module.get("type", ""))
            if module_type in {"ema_cross_up", "ema_cross_down"}:
                if "fast_period" not in module or "slow_period" not in module:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"top_agents[{idx}].dna.behavior_modules[{module_idx}] "
                            "must include fast_period and slow_period"
                        ),
                    )

    validated = json.loads(json.dumps(payload, allow_nan=False))
    validated["saved_at"] = datetime.now(timezone.utc).isoformat()
    validated["saved_by"] = "dashboard_swarm_auto_save"
    return validated


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
    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"tickers": tickers, "strategies": strategies},
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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


@app.get("/api/market-status")
def market_status(stale_after_days: int = 0):
    """Return freshness information about the underlying market data cache."""
    refresher = MarketDataRefresher(db_path=str(get_db().db_path))
    try:
        return refresher.get_status(stale_after_days=stale_after_days)
    except Exception as e:
        logger.error("Market status endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/market-data/refresh")
def refresh_market_data(
    force: bool = True,
    stale_after_days: int = 0,
    depth: int = 400,
    max_workers: int = 8,
):
    """Refresh stale market data, then rebuild shortlist artifacts."""
    safe_depth = max(60, min(int(depth), 1500))
    safe_workers = max(1, min(int(max_workers), 16))
    safe_stale_after_days = max(0, min(int(stale_after_days), 30))
    refresher = MarketDataRefresher(db_path=str(get_db().db_path))
    try:
        return refresher.refresh_market_data(
            depth=safe_depth,
            stale_after_days=safe_stale_after_days,
            force=force,
            max_workers=safe_workers,
            rebuild_shortlist=True,
        )
    except Exception as e:
        logger.error("Market refresh endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _refresh_market_data_for_gui() -> dict[str, object] | None:
    """Top up market data for GUI-driven actions when a user asks for it."""
    refresher = MarketDataRefresher(db_path=str(get_db().db_path))
    try:
        return refresher.refresh_market_data(
            depth=400,
            stale_after_days=0,
            force=False,
            max_workers=8,
            rebuild_shortlist=True,
        )
    except Exception as e:
        logger.warning("GUI market refresh failed: %s", e, exc_info=True)
        return None


@app.get("/api/shortlist")
async def shortlist(
    limit: int = 50,
    label: Optional[str] = None,
    refresh: bool = False,
):
    """Return the cached ETF shortlist, rebuilding it only when needed."""
    safe_limit = max(1, min(int(limit), 250))
    safe_label = label.title() if label else None
    if safe_label not in {None, "Buy", "Watch", "Skip"}:
        raise HTTPException(status_code=400, detail="label must be Buy, Watch, or Skip")

    engine = ETFShortlistEngine(db_path=str(get_db().db_path))
    try:
        df = engine.get_shortlist(limit=safe_limit, label=safe_label, refresh=refresh)
    except Exception as e:
        logger.error("Shortlist endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    rows = []
    for _, row in df.iterrows():
        reasons_raw = row.get("reasons_json", "[]")
        components_raw = row.get("components_json", "{}")
        try:
            reasons = json.loads(reasons_raw) if reasons_raw else []
        except Exception:
            reasons = []
        try:
            components = json.loads(components_raw) if components_raw else {}
        except Exception:
            components = {}

        rows.append(
            {
                "ticker": row["ticker"],
                "name": row.get("name", row["ticker"]),
                "label": row.get("label", "Watch"),
                "issuer": row.get("issuer", ""),
                "asset_class": row.get("asset_class", ""),
                "region": row.get("region", ""),
                "close": round(float(row.get("close", 0.0) or 0.0), 4),
                "volume": int(row.get("volume", 0) or 0),
                "recent_entry_days": (
                    int(row["recent_entry_days"])
                    if pd.notna(row.get("recent_entry_days"))
                    else None
                ),
                "product_score": round(float(row.get("product_score", 0.0) or 0.0), 2),
                "exposure_score": round(
                    float(row.get("exposure_score", 0.0) or 0.0), 2
                ),
                "technical_score": round(
                    float(row.get("technical_score", 0.0) or 0.0), 2
                ),
                "final_score": round(float(row.get("final_score", 0.0) or 0.0), 2),
                "reasons": reasons,
                "components": components,
                "as_of_date": row.get("as_of_date"),
                "updated_at": row.get("updated_at"),
            }
        )

    label_counts = {
        grade: sum(1 for item in rows if item["label"] == grade)
        for grade in ["Buy", "Watch", "Skip"]
    }

    return {
        "as_of_date": rows[0]["as_of_date"] if rows else None,
        "count": len(rows),
        "labels": label_counts,
        "rows": rows,
    }


@app.get("/api/swarm-world")
async def swarm_world(
    limit: Optional[int] = None,
    label: Optional[str] = None,
    refresh: bool = False,
):
    """Return the cached swarm world artifact for the exploratory tab."""
    safe_limit = None if limit is None else max(1, min(int(limit), 5000))
    safe_label = label.title() if label else None
    if safe_label not in {None, "Buy", "Watch", "Skip"}:
        raise HTTPException(status_code=400, detail="label must be Buy, Watch, or Skip")

    engine = SwarmWorldEngine(db_path=str(get_db().db_path))
    try:
        df = engine.get_world(limit=safe_limit, label=safe_label, refresh=refresh)
    except Exception as e:
        logger.error("Swarm world endpoint failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    nodes = []
    for _, row in df.iterrows():
        components_raw = row.get("components_json", "{}")
        try:
            components = json.loads(components_raw) if components_raw else {}
        except Exception:
            components = {}

        nodes.append(
            {
                "ticker": row["ticker"],
                "name": row.get("name", row["ticker"]),
                "issuer": row.get("issuer", ""),
                "asset_class": row.get("asset_class", ""),
                "region": row.get("region", ""),
                "label": row.get("label", "Watch"),
                "volume": int(row.get("volume", 0) or 0),
                "recent_entry_days": (
                    int(row["recent_entry_days"])
                    if pd.notna(row.get("recent_entry_days"))
                    else None
                ),
                "product_score": round(float(row.get("product_score", 0.0) or 0.0), 2),
                "exposure_score": round(float(row.get("exposure_score", 0.0) or 0.0), 2),
                "technical_score": round(float(row.get("technical_score", 0.0) or 0.0), 2),
                "final_score": round(float(row.get("final_score", 0.0) or 0.0), 2),
                "energy": round(float(row.get("energy", 0.0) or 0.0), 2),
                "momentum_score": round(float(row.get("momentum_score", 0.0) or 0.0), 2),
                "freshness_score": round(float(row.get("freshness_score", 0.0) or 0.0), 2),
                "row": int(row.get("grid_row", row.get("row", 0)) or 0),
                "col": int(row.get("grid_col", row.get("col", 0)) or 0),
                "x": round(float(row.get("x", 0.0) or 0.0), 2),
                "y": round(float(row.get("y", 0.0) or 0.0), 2),
                "vx": round(float(row.get("vx", 0.0) or 0.0), 4),
                "vy": round(float(row.get("vy", 0.0) or 0.0), 4),
                "charge": round(float(row.get("charge", 1.0) or 1.0), 4),
                "radius": round(float(row.get("radius", 0.0) or 0.0), 2),
                "color": row.get("color", "#64748b"),
                "components": components,
                "world_version": row.get("world_version"),
                "is_dummy": False,
                "as_of_date": row.get("as_of_date"),
                "updated_at": row.get("updated_at"),
            }
        )

    label_counts = {
        grade: sum(1 for item in nodes if item["label"] == grade)
        for grade in ["Buy", "Watch", "Skip"]
    }

    world_width = float(getattr(engine, "WORLD_WIDTH", 1600.0))
    world_height = float(getattr(engine, "WORLD_HEIGHT", 920.0))
    if nodes:
        columns = max(int(node.get("col", 0)) for node in nodes) + 1
        rows = max(int(node.get("row", 0)) for node in nodes) + 1
    else:
        columns = 1
        rows = 1
    if hasattr(engine, "grid_dimensions") and nodes:
        columns, rows = engine.grid_dimensions(len(nodes))
    cell_width = world_width / max(1, columns)
    cell_height = world_height / max(1, rows)

    return {
        "world": {
            "width": world_width,
            "height": world_height,
            "layout": "grid",
            "columns": columns,
            "rows": rows,
            "cell_width": round(cell_width, 4),
            "cell_height": round(cell_height, 4),
            "version": getattr(engine, "ARTIFACT_VERSION", "swarm_v1"),
        },
        "as_of_date": nodes[0]["as_of_date"] if nodes else None,
        "updated_at": nodes[0]["updated_at"] if nodes else None,
        "count": len(nodes),
        "labels": label_counts,
        "nodes": nodes,
    }


@app.get("/api/swarm-history")
async def swarm_history(days: int = 420, limit: Optional[int] = 5000):
    """Return compact cached close-price history for current swarm tickers."""
    safe_days = max(2, min(int(days), 1500))
    safe_limit = max(1, min(int(limit or 5000), 5000))
    db = get_db()
    engine = SwarmWorldEngine(db_path=str(db.db_path))

    try:
        world_df = engine.get_world(limit=safe_limit, refresh=False)
    except Exception as e:
        logger.error("Swarm history world lookup failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    tickers = [
        str(ticker).upper()
        for ticker in world_df.get("ticker", pd.Series(dtype=str)).dropna().tolist()
    ]
    if not tickers:
        return {
            "days": safe_days,
            "requested_tickers": 0,
            "count": 0,
            "as_of_date": None,
            "history": {},
        }

    frames = []
    conn = db._get_connection()
    etf_data_columns = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(etf_data)").fetchall()
    }
    dividends_expr = "COALESCE(dividends, 0) AS dividends" if "dividends" in etf_data_columns else "0.0 AS dividends"
    chunk_size = 750
    for start in range(0, len(tickers), chunk_size):
        chunk = tickers[start : start + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        query = f"""
            SELECT ticker, date, close, dividends
            FROM (
                SELECT
                    ticker,
                    date,
                    close,
                    {dividends_expr},
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
                FROM etf_data
                WHERE ticker IN ({placeholders})
                  AND close IS NOT NULL
            )
            WHERE rn <= ?
            ORDER BY ticker, date
        """  # nosec B608 - placeholders are generated, values are parameterized
        frames.append(pd.read_sql_query(query, conn, params=[*chunk, safe_days]))

    history_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    history: dict[str, dict[str, list]] = {}
    latest_date = None
    if not history_df.empty:
        history_df["ticker"] = history_df["ticker"].astype(str).str.upper()
        history_df["date"] = history_df["date"].astype(str)
        latest_date = str(history_df["date"].max())
        for ticker, group in history_df.groupby("ticker", sort=False):
            clean_group = group.dropna(subset=["close"]).sort_values("date")
            closes = [
                round(float(value), 6)
                for value in clean_group["close"].tolist()
                if pd.notna(value)
            ]
            dividends = [
                round(float(value or 0.0), 6)
                for value in clean_group.get("dividends", pd.Series(dtype=float)).fillna(0.0).tolist()
            ]
            if closes:
                history[str(ticker)] = {
                    "dates": clean_group["date"].tolist()[-len(closes) :],
                    "closes": closes,
                    "dividends": dividends[-len(closes) :],
                }

    return {
        "days": safe_days,
        "requested_tickers": len(tickers),
        "count": len(history),
        "as_of_date": latest_date,
        "history": history,
    }


@app.post("/api/swarm-dna/save")
async def save_swarm_dna(request: Request):
    """Persist the latest completed Swarm top-agent DNA into config."""
    try:
        raw_payload = await request.json()
        payload = _validate_swarm_dna_payload(raw_payload)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid json")
    except Exception as e:
        logger.error("Swarm DNA validation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    try:
        SWARM_DNA_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        SWARM_DNA_CONFIG_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        logger.error("Swarm DNA save failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        "path": str(SWARM_DNA_CONFIG_PATH).replace("\\", "/"),
        "agent_count": len(payload.get("top_agents", [])),
        "saved_at": payload["saved_at"],
    }


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
async def screen(
    strategy: Optional[str] = None,
    dsl_content: Optional[str] = None,
    refresh: bool = False,
):
    """Run a dynamic screen based on selected strategies or provided DSL."""
    logger.info("=== SCREEN ENDPOINT START ===")
    logger.info(
        "Params: strategy=%s, dsl_content=%s",
        strategy,
        "PROVIDED" if dsl_content else "NONE",
    )
    db = get_db()

    try:
        if refresh:
            _refresh_market_data_for_gui()

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

        strategy_spec = parse_dsl_content(content)
        final_entry = strategy_spec["entry"]
        final_exit = strategy_spec["exit"]
        logger.info(
            "Strategy parsed. Entry script length: %d, Exit script length: %d, max_days=%s",
            len(final_entry),
            len(final_exit),
            strategy_spec.get("max_days"),
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

        # Filter for currently active signals. Strategies with MAX_DAYS opt into
        # movie-scan style recency; otherwise we preserve the stricter latest-bar behavior.
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
                strategy_max_days = strategy_spec.get("max_days")
                recent_days = None
                if strategy_max_days is not None:
                    recent_days = find_recent_entry_days(
                        df,
                        strategy_spec,
                        max_days=int(strategy_max_days),
                    )
                    is_match = recent_days is not None
                else:
                    is_match = latest_signal == 1
                    if is_match:
                        recent_days = 0

                # Additional metadata for the UI
                prev_row = df.iloc[-2] if len(df) > 1 else last_row

                if is_match:
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
                            "status": (
                                "Entry Signal"
                                if int(recent_days or 0) == 0
                                else f"Recent Entry ({int(recent_days)}d)"
                            ),
                            "return_pct": _safe_float(
                                res.get("total_return_pct", 0), 0.0
                            ),
                            "change_pct": change_pct,
                            "ema_50_slope": ema_50_slope_val,
                            "days_since_entry": int(recent_days or 0),
                        }
                    )
                    logger.info(
                        "Match found: %s (days_since_entry=%s, max_days=%s)",
                        ticker,
                        recent_days,
                        strategy_max_days,
                    )
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


@app.get("/api/backtest")
async def backtest_view(
    strategy: Optional[str] = None,
    dsl_content: Optional[str] = None,
    limit: int = 25,
    signal_days: Optional[int] = None,
    since_days: Optional[int] = None,
    refresh: bool = False,
):
    """Evaluate a saved strategy and return ranked quality metrics for the UI."""
    strategy_name = (strategy or "").strip()
    dsl_text = (dsl_content or "").strip()
    source_type = "editor" if dsl_text else "saved"
    signal_window_days = signal_days if signal_days is not None else since_days

    if not strategy_name and not dsl_text:
        return {
            "strategy_name": "",
            "source_type": source_type,
            "summary": {
                "count": 0,
                "best_quality": 0.0,
                "avg_return": 0.0,
                "avg_sharpe": 0.0,
            },
            "rows": [],
            "chart": {"data": [], "layout": {}},
        }

    strat_path = Path("strategies") / f"{strategy_name}.dsl"
    if not dsl_text and not strat_path.exists():
        raise HTTPException(status_code=404, detail="Strategy not found")

    try:
        if refresh:
            _refresh_market_data_for_gui()

        evaluate_kwargs = {
            "strategy_path": (strat_path.as_posix() if not dsl_text else None),
            "dsl_content": dsl_text or None,
            "strategy_name": (strategy_name or "Editor Draft"),
        }
        if signal_window_days is not None:
            evaluate_kwargs["since_days"] = signal_window_days
        df = evaluate_strategies(**evaluate_kwargs)
    except Exception as e:
        logger.error("Backtest endpoint failed for %s: %s", strategy_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    if df.empty:
        return {
            "strategy_name": strategy_name or "Editor Draft",
            "source_type": source_type,
            "summary": {
                "count": 0,
                "best_quality": 0.0,
                "avg_return": 0.0,
                "avg_sharpe": 0.0,
            },
            "rows": [],
            "chart": {"data": [], "layout": {}},
        }

    safe_limit = max(1, min(int(limit), 100))
    view = df.head(safe_limit).copy()
    rows = []
    for _, row in view.iterrows():
        rows.append(
            {
                "ticker": row["Ticker"],
                "strategy": row["Strategy"],
                "quality_score": round(float(row.get("Quality Score", 0.0)), 2),
                "return_pct": round(float(row.get("Return (%)", 0.0)), 2),
                "win_rate_pct": round(float(row.get("Win Rate (%)", 0.0)), 2),
                "profit_factor": round(float(row.get("Profit Factor", 0.0)), 2),
                "sharpe": round(float(row.get("Sharpe", 0.0)), 2),
                "max_dd_pct": round(float(row.get("Max DD (%)", 0.0)), 2),
                "trades": int(row.get("Trades", 0) or 0),
                "days_since_entry": int(row.get("Days Since Entry", 999) or 999),
            }
        )

    chart_rows = rows[: min(len(rows), 10)]
    chart = {
        "data": [
            {
                "type": "bar",
                "x": [row["ticker"] for row in chart_rows],
                "y": [row["quality_score"] for row in chart_rows],
                "marker": {
                    "color": [row["return_pct"] for row in chart_rows],
                    "colorscale": "RdYlGn",
                    "colorbar": {"title": "Return %"},
                },
                "hovertemplate": "Ticker: %{x}<br>Quality: %{y:.2f}<br>Return: %{marker.color:.2f}%<extra></extra>",
            }
        ],
        "layout": {
            "title": {"text": "Top Quality Scores", "font": {"size": 16}},
            "paper_bgcolor": "#ffffff",
            "plot_bgcolor": "#ffffff",
            "margin": {"l": 50, "r": 20, "t": 40, "b": 60},
            "xaxis": {"title": "Ticker", "tickangle": -25, "automargin": True},
            "yaxis": {"title": "Quality Score"},
        },
    }

    return {
        "strategy_name": strategy_name or "Editor Draft",
        "source_type": source_type,
        "summary": {
            "count": int(len(df)),
            "best_quality": round(float(df["Quality Score"].max()), 2),
            "avg_return": round(float(df["Return (%)"].mean()), 2),
            "avg_sharpe": round(float(df["Sharpe"].mean()), 2),
        },
        "rows": rows,
        "chart": chart,
    }


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

    latest_cached_day = None
    if not df.empty:
        latest_col = "date" if "date" in df.columns else "Date"
        try:
            latest_cached_day = pd.to_datetime(df[latest_col].max()).date()
        except Exception:
            latest_cached_day = None

    # 2. If data is missing, too sparse, or stale, fetch it.
    # Keep at least 100 bars so indicator warmup stays reliable for EMA50 and ATR.
    if df.empty or len(df) < 100 or _is_stale_date(latest_cached_day, threshold_days=0):
        logger.info(
            "Cache refresh for %s (count=%d, latest=%s). Fetching from Yahoo Finance...",
            ticker,
            len(df),
            latest_cached_day,
        )
        try:
            refresher = MarketDataRefresher(db_path=str(db.db_path))
            processed_df = refresher.refresh_ticker_data(
                ticker=ticker,
                depth=max(safe_days, 365),
                min_existing_rows=max(100, min(safe_days, 365)),
            )

            has_st = (
                not processed_df["Supertrend"].isna().all()
                if "Supertrend" in processed_df.columns
                else False
            )
            logger.info(
                "Ticker refresh complete for %s. Rows=%d, Supertrend calculated=%s",
                ticker,
                len(processed_df),
                has_st,
            )

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

    def _fallback_plot_payload(frame: pd.DataFrame) -> dict:
        """Build a minimal chart payload when Plotly is unavailable."""
        local_df = frame.copy()
        local_df["Date"] = pd.to_datetime(local_df["Date"], errors="coerce")
        dates = [d.isoformat() if pd.notna(d) else None for d in local_df["Date"]]
        close = (
            pd.to_numeric(local_df.get("Close"), errors="coerce")
            .fillna(0.0)
            .tolist()
        )
        data = [
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Close",
                "x": dates,
                "y": close,
            }
        ]

        for candidate in ("Supertrend", "supertrend", "st", "ST_Lower", "st_lower"):
            if candidate in local_df.columns:
                series = pd.to_numeric(local_df[candidate], errors="coerce")
                series = series.ffill().bfill().fillna(0.0)
                data.append(
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "name": "ST",
                        "x": dates,
                        "y": series.tolist(),
                        "line": {"color": "#10b981", "width": 2},
                    }
                )
                break

        return {
            "data": data,
            "layout": {
                "title": {"text": f"{ticker} Chart"},
                "xaxis": {"title": {"text": "Date"}},
                "yaxis": {"title": {"text": "Price"}},
                "template": "plotly_white",
            },
        }

    try:
        if InteractivePlotter is None:
            figure = _fallback_plot_payload(df)
            fig_json = json.dumps(figure, default=str)
            return {
                "ticker": ticker,
                "strategy_name": strategy or "Custom Strategy",
                "figure": fig_json,
                "data": figure.get("data", []),
                "layout": figure.get("layout", {}),
            }

        plotter = InteractivePlotter()
        fig = plotter.create_plot(df, ticker, strategy_content=strategy_content)
        # Fastapi JSONResponse or direct dict return will handle this.
        # But we need to ensure it's a DICT, not a JSON string,
        # because the frontend is now expecting the un-wrapped object.

        fig_json = fig.to_json()
        fig_dict = json.loads(fig_json)
        return {
            "ticker": ticker,
            "strategy_name": strategy or "Custom Strategy",
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
