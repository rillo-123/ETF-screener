import hashlib
import json

from ETF_screener.config_loader import get_paths
from ETF_screener.backtester import (
    Backtester,
)
import pandas as pd
import os
import argparse
import re
import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

BLACKLIST_PATH = Path("config") / "blacklist.json"
STRATEGY_EVAL_CACHE_VERSION = "strategy_eval_v2"


@lru_cache(maxsize=1)
def _cached_blacklist_tickers() -> set[str]:
    if not BLACKLIST_PATH.exists():
        return set()
    try:
        with open(BLACKLIST_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception:
        return set()

    if isinstance(raw, dict):
        return {str(ticker).upper() for ticker in raw.keys()}
    if isinstance(raw, list):
        return {str(ticker).upper() for ticker in raw}
    return set()


def _strategy_eval_cache_dir() -> Path:
    cache_root = Path(get_paths()["data"]["cache"])
    cache_dir = cache_root / "strategy_eval"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _strategy_request_signature(
    *,
    strategy_path: str | None,
    entry_script: str | None,
    exit_script: str | None,
    dsl_content: str | None,
    strategy_name: str | None,
    since_days: int | None,
    exchange: str | None,
    ticker_list: str | None,
    scan_scope: str | None,
    latest_market_date: str | None,
    tickers: list[str] | tuple[str, ...],
) -> str:
    """Build a stable signature for strategy evaluation cache hits."""
    strategy_text = ""
    if dsl_content:
        strategy_text = dsl_content
    elif strategy_path:
        path = Path(strategy_path)
        if path.is_file():
            try:
                strategy_text = path.read_text(encoding="utf-8")
            except Exception:
                strategy_text = str(path)
        elif path.exists():
            try:
                parts = []
                for child in sorted(path.glob("*.dsl")):
                    try:
                        parts.append(child.read_text(encoding="utf-8"))
                    except Exception:
                        parts.append(child.name)
                strategy_text = "\n".join(parts)
            except Exception:
                strategy_text = str(path)
    elif entry_script or exit_script:
        strategy_text = f"{entry_script or ''}\n---EXIT---\n{exit_script or ''}"

    universe_blob = "|".join(str(ticker).upper() for ticker in tickers)
    payload = {
        "cache_version": STRATEGY_EVAL_CACHE_VERSION,
        "strategy_name": strategy_name or "",
        "strategy_text_sha": hashlib.sha256(strategy_text.encode("utf-8")).hexdigest(),
        "since_days": since_days,
        "exchange": str(exchange or "").strip().lower(),
        "ticker_list_sha": hashlib.sha256(str(ticker_list or "").encode("utf-8")).hexdigest(),
        "scan_scope": str(scan_scope or "").strip().lower(),
        "latest_market_date": latest_market_date or "",
        "universe_sha": hashlib.sha256(universe_blob.encode("utf-8")).hexdigest(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=16)
def _load_cached_strategy_eval(
    cache_key: str, _cache_mtime_ns: int
) -> pd.DataFrame | None:
    cache_path = _strategy_eval_cache_dir() / f"{cache_key}.pkl"
    if not cache_path.exists():
        return None
    try:
        cached = pd.read_pickle(cache_path)
    except Exception:
        return None
    if isinstance(cached, pd.DataFrame):
        return cached
    return None


def _save_cached_strategy_eval(cache_key: str, df: pd.DataFrame) -> None:
    cache_path = _strategy_eval_cache_dir() / f"{cache_key}.pkl"
    try:
        df.to_pickle(cache_path)
    except Exception:
        try:
            if cache_path.exists():
                cache_path.unlink()
        except Exception:
            pass


def parse_dsl_content(content: str | None) -> dict:
    """Parse DSL content into runnable scripts plus strategy metadata.

    Entry is composed from positive conditions in CONTEXT/SETUP/QUALIFY/TRIGGER.
    Exit is composed from EXIT lines plus INVALIDATE/RISK conditions.
    """
    content = content or ""

    canonical_alias: Dict[str, str] = {
        "context": "context",
        "setup": "setup",
        "qualify": "setup",
        "trigger": "trigger",
        "entry": "trigger",
        "risk": "risk",
        "invalidate": "risk",
        "exit": "risk",
    }
    canonical_prefixes: List[str] = [
        "context",
        "setup",
        "qualify",
        "trigger",
        "risk",
        "invalidate",
        "entry",
        "exit",
    ]

    def resolve_block(raw_name: str | None) -> str:
        if not raw_name:
            return "global"
        k = raw_name.strip().lower()
        if k in canonical_alias:
            return canonical_alias[k]
        for prefix in canonical_prefixes:
            if k.startswith(prefix):
                return canonical_alias[prefix]
        return "setup"

    scoped_terms = {
        "context": [],
        "setup": [],
        "trigger": [],
        "risk": [],
        "global": [],
    }
    explicit_exits: list[str] = []

    current_block_raw: str | None = None
    max_days: int | None = None
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue

        directive = re.match(
            r"^(MAX_DAYS|MAX_SIGNAL_AGE_DAYS|SIGNAL_MAX_DAYS|SINCE_DAYS)\s*:\s*(\d+)\s*$",
            line,
            re.IGNORECASE,
        )
        if directive:
            max_days = int(directive.group(2))
            continue

        if line.startswith("#"):
            continue

        begin_prefix = re.match(r"^begin\s+(.+)$", line, re.IGNORECASE)
        begin_suffix = re.match(r"^(.+?)\s+begin\b", line, re.IGNORECASE)
        if begin_prefix:
            current_block_raw = begin_prefix.group(1).strip()
            continue
        if begin_suffix:
            current_block_raw = begin_suffix.group(1).strip()
            continue
        if re.match(r"^end\b", line, re.IGNORECASE):
            current_block_raw = None
            continue

        section = re.match(r"^(TRIGGER|FILTER|ENTRY|EXIT):\s*(.+)$", line, re.IGNORECASE)
        if not section:
            continue

        section_name = section.group(1).upper()
        expr = section.group(2).strip()
        if not expr:
            continue

        canonical_block = resolve_block(current_block_raw)
        wrapped = f"({expr})"

        if section_name == "EXIT":
            explicit_exits.append(wrapped)
            continue

        if canonical_block == "risk":
            # INVALIDATE/RISK positive conditions should disqualify, so treat as exits.
            explicit_exits.append(wrapped)
            continue

        if canonical_block in scoped_terms:
            scoped_terms[canonical_block].append(wrapped)
        else:
            scoped_terms["setup"].append(wrapped)

    entry_parts = (
        scoped_terms["context"]
        + scoped_terms["setup"]
        + scoped_terms["trigger"]
        + scoped_terms["global"]
    )
    filter_parts = (
        scoped_terms["context"] + scoped_terms["setup"] + scoped_terms["global"]
    )
    final_entry = " and ".join(entry_parts) if entry_parts else "False"
    filter_entry = " and ".join(filter_parts) if filter_parts else None
    trigger_entry = (
        " and ".join(scoped_terms["trigger"]) if scoped_terms["trigger"] else None
    )
    final_exit = " or ".join(explicit_exits) if explicit_exits else "False"
    has_valid_exit = final_exit != "False"

    return {
        "trigger": trigger_entry,
        "filter": filter_entry,
        "entry": final_entry,
        "exit": final_exit,
        "has_valid_exit": has_valid_exit,
        "max_days": max_days,
    }


def load_dsl_file(file_path):
    """Load and parse a .dsl file with block-aware semantics."""
    with open(file_path, "r", encoding="utf-8") as f:
        return parse_dsl_content(f.read())


def _prepare_scan_expression(expr: str) -> str:
    """Convert DSL-style expressions into a pandas.eval-friendly form."""
    s = str(expr or "").strip()
    if not s:
        return "False"
    if s.lower() in {"true", "false"}:
        return s.title()

    s = re.sub(
        r"cross_up\(([^,]+),\s*([^)]+)\)",
        r"(\1 > \2 and \1_d1 <= \2_d1)",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"cross_down\(([^,]+),\s*([^)]+)\)",
        r"(\1 < \2 and \1_d1 >= \2_d1)",
        s,
        flags=re.IGNORECASE,
    )

    def d_sub(match):
        return f"{match.group(1)}_d{match.group(2)}"

    s = re.sub(r"([a-z_][a-z0-9_]*)\.d\[(\d+)\]", d_sub, s, flags=re.IGNORECASE)

    def shift_cond(match):
        condition = match.group(1).strip()
        lookback = int(match.group(2))
        shifted = " or ".join([f"{condition}_d{i}" for i in range(1, lookback + 1)])
        return f"({shifted})"

    s = re.sub(
        r"was_true\(([^,]+),\s*(\d+)\)",
        shift_cond,
        s,
        flags=re.IGNORECASE,
    )

    return (
        s.lower()
        .replace(" and ", " & ")
        .replace(" or ", " | ")
        .replace("-gt", ">")
        .replace("-lt", "<")
        .replace("-eq", "==")
        .replace("-ge", ">=")
        .replace("-le", "<=")
    )


def _evaluate_strategy_mask(df: pd.DataFrame, expr: str | None) -> pd.Series:
    """Evaluate a DSL expression against a strategy dataframe."""
    if df is None or df.empty:
        return pd.Series(dtype=bool)

    normalized = str(expr or "").strip()
    if not normalized:
        return pd.Series(True, index=df.index, dtype=bool)
    if normalized.lower() == "false":
        return pd.Series(False, index=df.index, dtype=bool)
    if normalized.lower() == "true":
        return pd.Series(True, index=df.index, dtype=bool)

    eval_df = df.copy()
    eval_df.columns = [str(column).lower() for column in eval_df.columns]
    eval_df = eval_df.loc[:, ~eval_df.columns.duplicated()]
    prepared = _prepare_scan_expression(normalized)
    result = eval_df.eval(prepared, engine="python")
    if not isinstance(result, pd.Series):
        return pd.Series([bool(result)] * len(eval_df), index=eval_df.index, dtype=bool)
    return result.fillna(False).astype(bool)


def find_recent_entry_days(
    df: pd.DataFrame | None,
    strategy_spec: dict,
    max_days: int | None = None,
) -> int | None:
    """Return the age in bars of the most recent still-valid entry candidate."""
    if df is None or df.empty:
        return None

    trigger_expr = strategy_spec.get("trigger") or strategy_spec.get("entry")
    filter_expr = strategy_spec.get("filter")
    if not trigger_expr:
        return None

    trigger_mask = _evaluate_strategy_mask(df, trigger_expr)
    filter_mask = _evaluate_strategy_mask(df, filter_expr)

    if "exit_condition" in df.columns:
        exit_mask = df["exit_condition"].fillna(False).astype(bool)
    else:
        exit_mask = _evaluate_strategy_mask(df, strategy_spec.get("exit"))

    scan_limit = len(df) if max_days is None else min(int(max_days) + 1, len(df))
    for age in range(scan_limit):
        idx = len(df) - 1 - age
        if idx < 0:
            break
        if not bool(trigger_mask.iloc[idx]):
            continue
        if bool(exit_mask.iloc[idx]):
            continue
        if idx + 1 < len(df) and bool(exit_mask.iloc[idx + 1 :].any()):
            continue
        if not bool(filter_mask.iloc[idx:].all()):
            continue
        return age

    return None


def _load_strategy_specs(
    backtester: Backtester,
    strategy_path: str | None = None,
    entry_script: str | None = None,
    exit_script: str | None = None,
    dsl_content: str | None = None,
    strategy_name: str | None = None,
):
    """Build runnable strategy specs from a saved DSL path or direct scripts."""
    strategies = []

    if strategy_path:
        path = Path(strategy_path)
        if path.is_file():
            res = load_dsl_file(path)
            if res.get("has_valid_exit", False):
                strategies.append(
                    {
                        "name": path.stem,
                        "func": backtester.scripted_strategy,
                        "kwargs": {
                            "entry_script": res["entry"],
                            "exit_script": res["exit"],
                        },
                        "trigger": res.get("trigger"),
                        "filter": res.get("filter"),
                        "exit": res.get("exit"),
                        "max_days": res.get("max_days"),
                    }
                )
        elif path.is_dir():
            for dsl_file in path.glob("*.dsl"):
                if "strat_cache" in dsl_file.parts:
                    continue
                res = load_dsl_file(dsl_file)
                if not res.get("has_valid_exit", False):
                    continue
                strategies.append(
                    {
                        "name": dsl_file.stem,
                        "func": backtester.scripted_strategy,
                        "kwargs": {
                            "entry_script": res["entry"],
                            "exit_script": res["exit"],
                        },
                        "trigger": res.get("trigger"),
                        "filter": res.get("filter"),
                        "exit": res.get("exit"),
                        "max_days": res.get("max_days"),
                    }
                )
    elif dsl_content:
        res = parse_dsl_content(dsl_content)
        if res["entry"] and res["entry"] != "False":
            strategies.append(
                {
                    "name": strategy_name or "Editor Draft",
                    "func": backtester.scripted_strategy,
                    "kwargs": {
                        "entry_script": res["entry"],
                        "exit_script": res["exit"],
                    },
                    "trigger": res.get("trigger"),
                    "filter": res.get("filter"),
                    "exit": res.get("exit"),
                    "max_days": res.get("max_days"),
                }
            )
    elif entry_script and exit_script:
        strategies.append(
            {
                "name": "CLI_Custom",
                "func": backtester.scripted_strategy,
                "kwargs": {"entry_script": entry_script, "exit_script": exit_script},
                "trigger": None,
                "filter": None,
                "entry": entry_script,
                "exit": exit_script,
                "max_days": None,
            }
        )

    return strategies


@lru_cache(maxsize=8)
def _cached_strategy_tickers(db_path: str, latest_market_date: str | None, ticker_filter: str | None) -> tuple[str, ...]:
    """Cache the strategy-screen ticker universe until market data advances."""
    db = Backtester(db_path=db_path).db
    conn = db._get_connection()
    query = "SELECT DISTINCT ticker FROM etf_data"

    if ticker_filter:
        if "%" in ticker_filter or "_" in ticker_filter:
            query += f" WHERE ticker LIKE '{ticker_filter}'"
        else:
            query += f" WHERE ticker LIKE '{ticker_filter}%'"

    tickers = pd.read_sql_query(query, conn)["ticker"].tolist()
    return tuple(str(ticker) for ticker in tickers)


def filter_tickers_by_exchange_and_list(
    tickers: list[str] | tuple[str, ...],
    exchange: str | None = None,
    ticker_list: str | None = None,
    scan_scope: str | None = None,
) -> list[str]:
    """Filter a ticker universe by exchange bucket or an explicit user-defined list."""
    blacklist = _cached_blacklist_tickers()
    exchange_key = str(exchange or "all").strip().lower()
    if exchange_key in {"", "all"}:
        exchange_key = "all"
    elif exchange_key in {"xetra", "de", "germany"}:
        exchange_key = "xetra"
    elif exchange_key in {"sweden", "swe", "stockholm", "se", "ss", "st"}:
        exchange_key = "sweden"

    scope_key = str(scan_scope or "exchange").strip().lower()
    if scope_key in {"custom", "list", "selected", "chosen"}:
        scope_key = "list"
    elif scope_key in {"all_lists", "alllists", "all list", "all lists"}:
        scope_key = "all_lists"
    elif scope_key in {"xetra", "de", "germany"}:
        scope_key = "xetra"
        exchange_key = "xetra"
    elif scope_key in {"sweden", "swe", "stockholm", "se", "ss", "st"}:
        scope_key = "sweden"
        exchange_key = "sweden"
    else:
        scope_key = "exchange"

    explicit_list = []
    if ticker_list:
        # Accept comma, newline, or whitespace separated lists.
        explicit_list = [
            str(item).strip().upper()
            for item in re.split(r"[\s,;]+", str(ticker_list))
            if str(item).strip()
        ]
    explicit_set = set(explicit_list)

    def matches_exchange(ticker: str) -> bool:
        upper = str(ticker or "").upper()
        if not upper:
            return False
        if scope_key in {"list", "all_lists"}:
            return True
        if exchange_key == "all":
            return True
        if exchange_key == "xetra":
            return upper.endswith(".DE") or upper.endswith(".F") or "." not in upper
        if exchange_key == "sweden":
            return upper.endswith(".ST") or upper.endswith(".SE") or upper.endswith(".SS")
        return True

    filtered = [
        str(ticker).upper()
        for ticker in tickers
        if matches_exchange(ticker) and str(ticker).upper() not in blacklist
    ]
    if scope_key in {"list", "all_lists"} and explicit_set:
        filtered = [ticker for ticker in filtered if ticker in explicit_set]
    elif scope_key in {"list", "all_lists"}:
        return []
    return filtered


def evaluate_strategies(
    entry_script: str | None = None,
    exit_script: str | None = None,
    ticker_filter: str | None = None,
    strategy_path: str | None = None,
    since_days: int | None = None,
    dsl_content: str | None = None,
    strategy_name: str | None = None,
    exchange: str | None = None,
    ticker_list: str | None = None,
    scan_scope: str | None = None,
    progress_callback=None,
) -> pd.DataFrame:
    """Run strategy scoring and return a ranked DataFrame without plotting side effects."""
    backtester = Backtester()
    latest_market_date = backtester.db.get_latest_market_date()
    tickers = list(
        _cached_strategy_tickers(str(backtester.db_path), latest_market_date, ticker_filter)
    )
    tickers = filter_tickers_by_exchange_and_list(
        tickers,
        exchange=exchange,
        ticker_list=ticker_list,
        scan_scope=scan_scope,
    )
    strategies = _load_strategy_specs(
        backtester,
        strategy_path=strategy_path,
        entry_script=entry_script,
        exit_script=exit_script,
        dsl_content=dsl_content,
        strategy_name=strategy_name,
    )

    if not strategies:
        return pd.DataFrame()

    cache_key = _strategy_request_signature(
        strategy_path=strategy_path,
        entry_script=entry_script,
        exit_script=exit_script,
        dsl_content=dsl_content,
        strategy_name=strategy_name,
        since_days=since_days,
        exchange=exchange,
        ticker_list=ticker_list,
        scan_scope=scan_scope,
        latest_market_date=latest_market_date,
        tickers=tickers,
    )
    cache_path = _strategy_eval_cache_dir() / f"{cache_key}.pkl"
    if cache_path.exists():
        cached_mtime_ns = cache_path.stat().st_mtime_ns
        cached_df = _load_cached_strategy_eval(cache_key, cached_mtime_ns)
        if cached_df is not None:
            if progress_callback is not None:
                try:
                    progress_callback(
                        {
                            "job": "backtest",
                            "phase": "done",
                            "pct": 100.0,
                            "detail": f"Loaded cached results for {len(cached_df)} rows",
                            "label": strategy_name or "Backtest",
                            "active": False,
                        }
                    )
                except Exception:
                    pass
            return cached_df.copy()

    all_results = []
    for strat in strategies:
        results = backtester.run_parallel_backtest(
            tickers,
            strat["func"],
            days=500,
            strategy_kwargs=strat.get("kwargs"),
            show_progress=False,
            progress_label=f"{strat['name']} ({len(tickers)} tickers)",
            progress_callback=progress_callback,
        )
        for res in results:
            if not res or "error" in res:
                continue

            df = res.get("df")
            strategy_max_days = strat.get("max_days")
            recent_days = find_recent_entry_days(
                df,
                strat,
                max_days=(
                    min(since_days, strategy_max_days)
                    if since_days is not None and strategy_max_days is not None
                    else since_days if since_days is not None else strategy_max_days
                ),
            )
            recent_days_value = 999 if recent_days is None else int(recent_days)
            max_allowed_days = (
                min(since_days, strategy_max_days)
                if since_days is not None and strategy_max_days is not None
                else since_days if since_days is not None else strategy_max_days
            )

            if max_allowed_days is not None and recent_days_value > max_allowed_days:
                continue

            all_results.append(
                {
                    "Ticker": res["ticker"],
                    "Strategy": strat["name"],
                    "Return (%)": res["total_return_pct"],
                    "Win Rate (%)": res["win_rate_pct"],
                    "Profit Factor": res["profit_factor"],
                    "Sharpe": res.get("sharpe_ratio", 0),
                    "Max DD (%)": res.get("max_drawdown_pct", 0),
                    "Trades": res.get("num_trades", 0),
                    "Days Since Entry": recent_days_value,
                    "df": df,
                }
            )

    summary_df = pd.DataFrame(all_results)
    if summary_df.empty:
        return summary_df

    summary_df["Quality Score"] = (
        summary_df["Return (%)"]
        * (summary_df["Win Rate (%)"] / 100)
        * (summary_df["Sharpe"] + 1)
        / ((1 + summary_df["Trades"] / 100.0) * (1 + summary_df["Max DD (%)"] / 10.0))
    )
    if since_days is not None:
        summary_df = summary_df.sort_values(
            by=["Days Since Entry", "Quality Score"], ascending=[True, False]
        )
    else:
        summary_df = summary_df.sort_values(by="Quality Score", ascending=False)

    summary_df = summary_df.reset_index(drop=True)
    _save_cached_strategy_eval(cache_key, summary_df)
    return summary_df


def churn_db(
    entry_script: str | None = None,
    exit_script: str | None = None,
    ticker_filter: str | None = None,
    strategy_path: str | None = None,
    plot_top: int = 20,
    force_refresh: bool = False,
    since_days: int | None = None,
):
    backtester = Backtester()

    # Phase 0: Clean plots directory at the start of every discovery run
    print("Cleaning previous plots...")
    manifest_path = Path("plots/plot_manifest.json")
    if manifest_path.exists():
        manifest_path.unlink()  # Start fresh manifest

    for ext in ["*.svg", "*.html"]:
        for file in Path("plots").glob(ext):
            if "index.html" in file.name:
                continue  # Keep the dashboard
            try:
                file.unlink()
            except PermissionError:
                pass  # Skip if open
            except Exception as e:
                print(f"Error deleting {file.name}: {e}")

    # Get all tickers from DB
    latest_market_date = backtester.db.get_latest_market_date()
    tickers = list(
        _cached_strategy_tickers(str(backtester.db_path), latest_market_date, ticker_filter)
    )

    strategies = _load_strategy_specs(
        backtester,
        strategy_path=strategy_path,
        entry_script=entry_script,
        exit_script=exit_script,
        dsl_content=None,
        strategy_name=None,
    )

    if not strategies:
        print("No strategies found to run.")
        return

    all_results = []
    # Fetch data only once per ticker to speed up multiple strategy runs
    print(
        f"Churning {len(tickers)} tickers through {len(strategies)} strategies (Total {len(tickers)*len(strategies)} runs)..."
    )

    # Pre-loading data or using a shared cache could speed this up,
    # but the backtester already uses a CachedStrategyManager.

    strategy_iter = strategies
    try:
        from tqdm import tqdm  # type: ignore

        strategy_iter = tqdm(strategies, desc="Strategies", unit="strategy")
    except Exception:
        strategy_iter = strategies

    for strat in strategy_iter:
        print(f"Running Strategy: {strat['name']}")
        results = backtester.run_parallel_backtest(
            tickers,
            strat["func"],
            days=500,  # Reduced from 730 to 500 (~2 years) for faster discovery
            strategy_kwargs=strat.get("kwargs"),
            show_progress=True,
            progress_label=f"{strat['name']} ({len(tickers)} tickers)",
        )
        for res in results:
            if res and "error" not in res:
                df = res.get("df")

                strategy_max_days = strat.get("max_days")
                recent_days = find_recent_entry_days(
                    df,
                    strat,
                    max_days=(
                        min(since_days, strategy_max_days)
                        if since_days is not None and strategy_max_days is not None
                        else since_days if since_days is not None else strategy_max_days
                    ),
                )
                recent_days_value = 999 if recent_days is None else int(recent_days)
                max_allowed_days = (
                    min(since_days, strategy_max_days)
                    if since_days is not None and strategy_max_days is not None
                    else since_days if since_days is not None else strategy_max_days
                )

                if max_allowed_days is not None and recent_days_value > max_allowed_days:
                    continue

                all_results.append(
                    {
                        "Ticker": res["ticker"],
                        "Strategy": strat["name"],
                        "Return (%)": res["total_return_pct"],
                        "Win Rate (%)": res["win_rate_pct"],
                        "Profit Factor": res["profit_factor"],
                        "Sharpe": res.get("sharpe_ratio", 0),
                        "Max DD (%)": res.get("max_drawdown_pct", 0),
                        "Trades": res.get("num_trades", 0),
                        "Days Since Entry": recent_days_value,
                        "df": res.get("df"),
                    }
                )

    # Convert to DataFrame and sort by Score
    summary_df = pd.DataFrame(all_results)
    if not summary_df.empty:
        summary_df["Quality Score"] = (
            summary_df["Return (%)"]
            * (summary_df["Win Rate (%)"] / 100)
            * (summary_df["Sharpe"] + 1)
            / (
                (1 + summary_df["Trades"] / 100.0)
                * (1 + summary_df["Max DD (%)"] / 10.0)
            )
        )
        # If filtering by since_days, we might want to sort by recency instead of quality
        if since_days is not None:
            summary_df = summary_df.sort_values(
                by=["Days Since Entry", "Quality Score"], ascending=[True, False]
            )
        else:
            summary_df = summary_df.sort_values(by="Quality Score", ascending=False)

        print("\nTop 10 Strategy/ETF Combinations:")
        # Display with 2 decimals, excluding the bulky 'df' column
        cols_to_print = [c for c in summary_df.columns if c != "df"]
        print(
            summary_df[cols_to_print]
            .head(10)
            .to_string(index=False, float_format=lambda x: "{:.2f}".format(x))
        )

        # Plot top performers
        if plot_top > 0:
            print(f"\nPlotting top {plot_top} and bottom {plot_top} performers...")
            # Use a fresh import to avoid any scoping issues inside the loop
            from ETF_screener.plotter_plotly import InteractivePlotter as PFPlot

            p = PFPlot()

            # Prepare rich manifest data for the dashboard
            rich_manifest = []

            # Select indices for top and bottom performers
            top_indices = list(range(min(plot_top, len(summary_df))))
            # Bottom performers are those with the lowest Quality Score
            # We skip those that already in top_indices if overlap exists
            bottom_potential = list(
                range(max(0, len(summary_df) - plot_top), len(summary_df))
            )
            bottom_indices = [idx for idx in bottom_potential if idx not in top_indices]

            # Combine them but keep track of which is which
            all_indices = [(idx, "top") for idx in top_indices] + [
                (idx, "bottom") for idx in bottom_indices
            ]

            for i, rank_type in all_indices:
                row = summary_df.iloc[i]
                ticker = row["Ticker"]
                strategy_name = row["Strategy"]
                # Find the original result to get the DF
                found = False
                for res in all_results:
                    if (
                        res.get("Ticker") == ticker
                        and res.get("Strategy") == strategy_name
                        and "df" in res
                    ):
                        # Define the filename first
                        plot_filename = (
                            f"{ticker}_{strategy_name}_interactive.html".lower()
                        )

                        # Ensure the directory exists
                        plot_path = Path("plots") / plot_filename

                        # Phase 1: Skip if already exists (unless we want to force refresh)
                        if plot_path.exists() and not force_refresh:
                            # Still add to manifest even if skipped plotting
                            pass
                        else:
                            print(
                                f"Generating plot for {ticker} ({strategy_name}) [{rank_type}]..."
                            )
                            # Use f-string to define the symbol properly for InteractivePlotter
                            p.plot_etf_analysis(
                                res["df"].copy(), f"{ticker}_{strategy_name}"
                            )

                        rich_manifest.append(
                            {
                                "file": plot_filename,
                                "ticker": str(ticker),
                                "strategy": str(strategy_name),
                                "rank_type": rank_type,
                                "return_pct": (
                                    float(row["Return (%)"])
                                    if not pd.isna(row["Return (%)"])
                                    else 0.0
                                ),
                                "win_rate": (
                                    float(row["Win Rate (%)"])
                                    if not pd.isna(row["Win Rate (%)"])
                                    else 0.0
                                ),
                                "profit_factor": (
                                    float(row["Profit Factor"])
                                    if not pd.isna(row["Profit Factor"])
                                    else 0.0
                                ),
                                "sharpe": (
                                    float(row["Sharpe"])
                                    if not pd.isna(row["Sharpe"])
                                    else 0.0
                                ),
                                "max_dd": (
                                    float(row.get("Max DD (%)", 0))
                                    if not pd.isna(row.get("Max DD (%)", 0))
                                    else 0.0
                                ),
                                "trades": (
                                    int(row["Trades"])
                                    if not pd.isna(row["Trades"])
                                    else 0
                                ),
                            }
                        )
                        found = True
                        break
                if not found:
                    print(
                        f"Warning: Could not find data to plot for {ticker} / {strategy_name}"
                    )

            # Save the rich manifest to help the SVG chooser
            try:
                import json

                manifest_path = Path("plots") / "plot_manifest.json"
                manifest_json = json.dumps(rich_manifest, indent=2)
                manifest_path.write_text(manifest_json)

                # Manually trigger the HTML update logic from plotter since we aren't calling plot_multiple_etfs
                target_ui = Path("plots/index.html")
                root_ui = Path("browser.html")
                # If browser.html is missing, try to treat plots/index.html as the template if it exists
                if root_ui.exists():
                    import shutil
                    import re

                    shutil.copy2(root_ui, target_ui)

                import re

                if target_ui.exists():
                    content = target_ui.read_text(encoding="utf-8")
                    # Use backticks for a multiline template string in JS
                    # This is much safer for JSON injection
                    # Escaping the JSON for JS template literal
                    escaped_json = (
                        manifest_json.replace("\\", "\\\\")
                        .replace("`", "\\`")
                        .replace("${", "\\${")
                    )
                    new_manifest_line = f"const rawManifest = `{escaped_json}`;"

                    # Clean up any potential failed injections (single quote or multi-line)
                    content = re.sub(
                        r"const rawManifest = '.*?';",
                        new_manifest_line,
                        content,
                        flags=re.DOTALL,
                    )
                    content = re.sub(
                        r"const rawManifest = `.*?`;",
                        new_manifest_line,
                        content,
                        flags=re.DOTALL,
                    )

                    target_ui.write_text(content, encoding="utf-8")
                    print(f"Injected {len(rich_manifest)} items into dashboard.")
                else:
                    print(
                        f"Warning: Dashboard UI file not found (checked browser.html and {target_ui})"
                    )
            except Exception as e:
                import traceback

                print(f"Warning: Could not save rich manifest: {e}")
                traceback.print_exc()

        # Save to CSV with 2 decimal precision (keeps full precision in memory/code)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{get_paths()['data']['discovery']}/discovery_results_{timestamp}.csv"

        # Exclude the bulky 'df' column from CSV output for better compatibility with Spreadsheet tools
        cols_to_save = [c for c in summary_df.columns if c != "df"]

        # Keep only profitable results and limit to 100 rows for easier viewing
        clean_df = summary_df[summary_df["Return (%)"] > 0].head(100)

        clean_df[cols_to_save].to_csv(output_name, index=False, float_format="%.2f")

        # Also maintain a symlink-like constant copy for the PS1 script if needed
        clean_df[cols_to_save].to_csv(
            f"{get_paths()['data']['discovery']}/multi_strategy_results.csv", index=False, float_format="%.2f"
        )

        # Keep only the 3 most recent discovery CSV files to save space
        try:
            history_files = sorted(
                Path(get_paths()['data']['discovery']).glob("discovery_results_*.csv"),
                key=os.path.getmtime,
                reverse=True,
            )
            if len(history_files) > 3:
                for old_file in history_files[3:]:
                    old_file.unlink()
                print(f"Cleaned up {len(history_files) - 3} old discovery CSV files.")
        except Exception as e:
            print(f"Warning: Could not cleanup old CSVs: {e}")

        # Also save to "custom_script_results.csv" for run_custom_backtest.ps1 compatibility
        if not strategy_path:
            clean_df[cols_to_save].to_csv(
                f"{get_paths()['data']['discovery']}/custom_script_results.csv", index=False, float_format="%.2f"
            )

        print(f"\nFull results saved to {output_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", type=str, help="Entry condition (DSL)")
    parser.add_argument("--exit", type=str, help="Exit condition (DSL)")
    parser.add_argument("--filter", type=str, help="Ticker filter")
    parser.add_argument("--strat_path", type=str, help="Path to .dsl file or directory")
    parser.add_argument(
        "--plot", type=int, default=20, help="Number of top performers to plot"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force refresh (cleans plots/ folder)"
    )
    parser.add_argument(
        "--since",
        type=int,
        default=None,
        help="Only include tickers where an entry occurred within N days",
    )
    args = parser.parse_args()

    churn_db(
        entry_script=args.entry,
        exit_script=args.exit,
        ticker_filter=args.filter,
        strategy_path=args.strat_path,
        plot_top=args.plot,
        force_refresh=args.force,
        since_days=args.since,
    )
