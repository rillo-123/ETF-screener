"""Ordered browser assets shared by the dashboard template and its tests."""

from pathlib import Path

JAVASCRIPT_DIR = Path(__file__).parent / "static" / "js"

# Classic scripts share the existing dashboard bindings. Load state first and
# startup last; feature files must not start requests or bind UI events on load.
DASHBOARD_SCRIPTS = (
    "dashboard/state.js",
    "dashboard/utils.js",
    "dashboard/logging.js",
    "dashboard/shell.js",
    "dashboard/universe.js",
    "dashboard/screen-filters.js",
    "dashboard/timeline.js",
    "dashboard/screen-bindings.js",
    "dashboard/strategies.js",
    "dashboard/screen-results.js",
    "dashboard/screener.js",
    "dashboard/charts.js",
    "dashboard/market-data.js",
    "dashboard/progress.js",
    "dashboard/playbook.js",
    "dashboard/backtest-results.js",
    "dashboard/backtest-race.js",
    "dashboard/backtest-charts.js",
    "dashboard/backtest-run.js",
    "dashboard.js",
)


def dashboard_script_urls() -> list[str]:
    """Version every feature independently so edits invalidate browser caches."""
    return [
        f"/static/js/{name}?v={(JAVASCRIPT_DIR / name).stat().st_mtime_ns}"
        for name in DASHBOARD_SCRIPTS
    ]
