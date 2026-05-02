"""Whitelisted references for vulture.

This file intentionally references symbols that are part of the public API,
FastAPI route wiring, or dynamic helper entry points that vulture cannot infer
from static imports alone.
"""


def _keep(*_args):
    return None


from ETF_screener.backtester import ema_supertrend_strategy
from ETF_screener.config_loader import apply_flag_config, load_command_config
from ETF_screener.dashboard import app_fast as dashboard_app_fast
from ETF_screener.database import ETFDatabase
from ETF_screener.etf_discovery import ETFDiscovery
from ETF_screener.logging_setup import isatty
from ETF_screener.plotter import evaluate_simple_condition
from ETF_screener.plotter_plotly import InteractivePlotter
from ETF_screener.screener import Screener
from ETF_screener import screener_api
from ETF_screener.snippets import Snippet
from ETF_screener.xetra_extractor import XetraExtractor


_keep(
    ema_supertrend_strategy,
    load_command_config,
    apply_flag_config,
    dashboard_app_fast.job_progress,
    dashboard_app_fast.favicon,
    dashboard_app_fast.list_strategies,
    dashboard_app_fast.get_strategy,
    dashboard_app_fast.ticker_universe,
    dashboard_app_fast.get_custom_ticker_list,
    dashboard_app_fast.save_custom_ticker_list,
    dashboard_app_fast.market_status,
    dashboard_app_fast.shortlist,
    dashboard_app_fast.swarm_world,
    dashboard_app_fast.swarm_history,
    dashboard_app_fast.save_swarm_dna,
    dashboard_app_fast.save_strategy,
    dashboard_app_fast.screen,
    dashboard_app_fast.backtest_view,
    dashboard_app_fast.get_chart,
    dashboard_app_fast.screen_basic,
    dashboard_app_fast.browser_log,
    dashboard_app_fast.save_console_logs,
    ETFDatabase.row_factory,
    ETFDatabase.insert_etf_data,
    ETFDatabase.get_latest_swarm_world_updated_at,
    ETFDatabase.prune_old_data,
    ETFDiscovery.get_working_tickers,
    ETFDiscovery.add_to_working,
    ETFDiscovery.fetch_xetra_etfs_from_justetfs,
    isatty,
    evaluate_simple_condition,
    InteractivePlotter._condition_lines,
    InteractivePlotter._compact_ribbon_label_color,
    InteractivePlotter._isolated_true_mask,
    Screener.fetch_and_store,
    screener_api.GT,
    screener_api.GTE,
    screener_api.LT,
    screener_api.LTE,
    screener_api.EQ,
    screener_api.NE,
    screener_api.ScreenerAPI.filter_supertrend,
    screener_api.ScreenerAPI.filter_close,
    screener_api.ScreenerAPI.filter_ema,
    screener_api.ScreenerAPI.filter_pullback,
    screener_api.ScreenerAPI.filter_volume,
    screener_api.ScreenerAPI.filter_red_streak,
    Snippet,
    Snippet.get_all_data,
    Snippet.map_parallel,
    Snippet.filter_overbought,
    Snippet.filter_oversold,
    Snippet.filter_by_ema,
    Snippet.filter_by_supertrend,
    Snippet.find_oversold_in_period,
    Snippet.find_overbought_in_period,
    XetraExtractor.validated_count,
    XetraExtractor.blacklisted_count,
    XetraExtractor.get_working_tickers,
)
