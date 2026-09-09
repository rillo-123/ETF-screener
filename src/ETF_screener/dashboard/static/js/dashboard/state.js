// Dashboard state. See README.md in static/js/dashboard for the feature map.

let backtestSourceMode = "saved";
let playbookLoaded = false;
let playbookSourceSignature = "";
let playbookRows = [];
let marketDataAutoRefreshAttempted = false;
let marketDataBackgroundRefreshAttempted = false;
let marketDataBackgroundRefreshPromise = null;
let marketDataBackgroundRefreshAbortController = null;
let marketDataBackgroundRefreshRequestId = null;
let pageOverallProgressPct = 0;
let pagePhaseProgressPct = 0;
let pagePhaseProgressKey = "";
let tickerSelectUniverse = [];
let tickerUniverseLoadPromise = null;
let tickerSelectLastValue = "";
let tickerScanScope = "xetra";
let tickerUniverseExplicitlyChosen = false;
let tickerListMode = "custom";
let customTickerLists = [];
let customTickerListActiveName = "My List";
let customTickerListName = "My List";
let customTickerList = [];
let customTickerListDraft = [];
let customTickerListDraftSourceName = "My List";
let scanSourceListPreviewOpen = true;
let listBuilderExchange = "all";
let listBuilderSearch = "";
let listBuilderSelectedOnly = false;
let backtestMatrixRows = [];
let backtestTradeDotRows = [];
let backtestExcludedTickers = new Set();
let backtestStrategySummaries = [];
let backtestStrategyAxisCatalog = [];
let backtestMetricCatalog = [];
let backtestTableSortKey = "quality_score";
let backtestTableSortDirection = "desc";
let backtestScatterRenderTimer = null;
let backtestRaceState = null;
let backtestRaceCache = new Map();
let backtestRacePlaying = false;
let backtestRaceAnimationHandle = null;
let backtestRaceLastFrameTime = null;
let backtestRaceMotionHandle = null;
let backtestRaceLastMotionFrame = null;
let backtestRaceAbortController = null;
let backtestRaceCurrentSignature = "";
let backtestRaceFuelMetric = "return_pct";
let backtestRaceEventRunId = "";
let backtestRaceNextEventSeq = 1;
let backtestRaceEventFetchInFlight = false;
let backtestProgressStartedAt = 0;
const FIXED_CHART_WINDOW_DAYS = 90;
let currentDays = FIXED_CHART_WINDOW_DAYS;
let screenDisqualifiers = {
  exclude_weak_liquidity: false,
  exclude_unprofitable: false,
};
let screenAutoExportEnabled = false;
const LAST_TICKER_SELECT_KEY = "etf-discovery:last-ticker-select";
const LAST_EXCHANGE_SELECT_KEY = "etf-discovery:last-exchange-select";
const LAST_SCAN_SCOPE_KEY = "etf-discovery:last-scan-scope";
const LAST_SCREEN_DISQUALIFIERS_KEY = "etf-discovery:last-screen-disqualifiers";
const LAST_SCREEN_AUTO_EXPORT_KEY = "etf-discovery:last-screen-auto-export";
const LAST_LIST_MODE_KEY = "etf-discovery:last-list-mode";
const LAST_CUSTOM_LIST_KEY = "etf-discovery:last-custom-list";
const LAST_CUSTOM_LIST_NAME_KEY = "etf-discovery:last-custom-list-name";
const LAST_DASHBOARD_TAB_KEY = "etf-discovery:last-dashboard-tab";
const LAST_SCREEN_PRESET_KEY = "etf-discovery:last-screen-preset";
const LAST_SCREEN_FILTERS_KEY = "etf-discovery:last-screen-filters";
const LAST_PLAYBOOK_RISK_PCT_KEY = "etf-discovery:last-playbook-risk-pct";
const LAST_BACKTEST_RACE_KEY = "etf-discovery:last-backtest-race";
const LAST_BACKTEST_RACE_FUEL_KEY = "etf-discovery:last-backtest-race-fuel";
const EMA_OVERLAY_VISIBILITY_KEY = "etf-discovery:ema-overlay-visibility";
const DEFAULT_TIMELINE_ORDER = ["rsi", "macd", "stoch", "supertrend", "ema_relationship"];
const RSI_TIMELINE_KEYS = ["rsi", "rsi_2", "rsi_3"];
const REPEATABLE_TIMELINE_BASE_KEYS = ["macd", "stoch", "supertrend", "ema_relationship", "price_ema", "volume_spike", "ema_flatten"];
const REPEATABLE_TIMELINE_KEYS = REPEATABLE_TIMELINE_BASE_KEYS.flatMap((key) => [key, `${key}_2`, `${key}_3`]);
const SCREEN_DEFAULT_FILTERS = {
  lookback_days: 30,
  volume_range: { min: 0, max: 20000000 },
  macd_event_enabled: true,
  rsi_event_enabled: true,
  rsi_filter_enabled: false,
  rsi_filter_min: 50,
  stoch_event_enabled: true,
  supertrend_event_enabled: false,
  rsi_cross_value: 50,
  rsi_cross_mode: "cross_up",
  stoch_cross_value: 20,
  stoch_cross_mode: "cross_up",
  stoch_cross_region: "below",
  macd_cross_mode: "low_cross_buy",
  macd_event_age: 45,
  rsi_event_age: 90,
  stoch_event_age: 15,
  supertrend_event_age: 30,
  ema_relationship_enabled: false,
  ema_relationship_fast: 10,
  ema_relationship_slow: 20,
  ema_relationship_slope: "positive",
  ema_relationship_allowance: 0.1,
  ema_relationship_fast_slope: "positive",
  ema_relationship_slow_slope: "positive",
  ema_relationship_cross_mode: "cross_up",
  ema_relationship_age: 30,
  price_ema_event_enabled: false,
  price_ema_period: 20,
  price_ema_source: "close",
  price_ema_sources: ["close"],
  price_ema_cross_mode: "cross_up",
  price_ema_event_age: 30,
  ema_flatten_enabled: false,
  ema_flatten_period: 20,
  ema_flatten_lookback: 5,
  ema_flatten_tolerance: 0.1,
  ema_flatten_mode: "either",
  ema_flatten_event_age: 30,
  volume_spike_enabled: false,
  volume_spike_period: 20,
  volume_spike_multiplier: 2.0,
  volume_spike_age: 5,
  ha_ema_volume_enabled: false,
  ha_ema_volume_ema1_period: 20,
  ha_ema_volume_ema1_source: "close",
  ha_ema_volume_ema2_period: 50,
  ha_ema_volume_ema2_source: "close",
  ha_ema_volume_start_field: "open",
  ha_ema_volume_start_line: "ema2",
  ha_ema_volume_start_relation: "above",
  ha_ema_volume_end_field: "close",
  ha_ema_volume_end_line: "ema1",
  ha_ema_volume_end_relation: "above",
  ha_ema_volume_conditions: [
    { field: "open", enabled: false, zone: "above_ema1" },
    { field: "high", enabled: false, zone: "above_ema1" },
    { field: "low", enabled: false, zone: "below_ema2" },
    { field: "close", enabled: true, zone: "above_ema1" },
  ],
  ha_ema_volume_candle_color: "green",
  ha_ema_volume_period: 20,
  ha_ema_volume_multiplier: 2.5,
  ha_ema_volume_event_age: 30,
  supertrend_cross_mode: "red_to_green",
  ema_slope_20: "any",
  ema_slope_50: "any",
  ema_slope_200: "any",
  ema_slope_period_1: 20,
  ema_slope_period_2: 50,
  ema_slope_period_3: 200,
  ema_slope_1: "any",
  ema_slope_2: "any",
  ema_slope_3: "any",
  ema_slope_lookback: 5,
  ema_slope_flat_tolerance: 0.1,
  timeline_order: [...DEFAULT_TIMELINE_ORDER],
};
const CHART_TA_DEFAULTS = {
  macd_fast: 12,
  macd_slow: 26,
  macd_signal: 9,
  rsi_period: 14,
  stoch_rsi_period: 14,
  stoch_rsi_k: 3,
  stoch_rsi_d: 3,
  supertrend_period: 10,
  supertrend_multiplier: 3.0,
  candle_mode: "heikin_ashi",
  rsi_trigger: 50,
  stoch_trigger: 20,
};
const CHART_TA_PARAMETER_KEYS = [
  "macd_fast", "macd_slow", "macd_signal", "rsi_period",
  "stoch_rsi_period", "stoch_rsi_k", "stoch_rsi_d",
  "supertrend_period", "supertrend_multiplier",
  "candle_mode",
];
const BACKTEST_RACE_FUEL_METRICS = [
  { key: "return_pct", label: "Profitability", kind: "percent" },
  { key: "avg_quality_score", label: "Quality", kind: "score" },
  { key: "sharpe", label: "Sharpe", kind: "ratio" },
  { key: "win_rate_pct", label: "Win Rate", kind: "percent" },
  { key: "profit_factor", label: "Profit Factor", kind: "ratio" },
  { key: "trades", label: "Trades", kind: "count" },
];
const BACKTEST_STRATEGY_COLORS = [
  "#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed",
  "#0891b2", "#be123c", "#4d7c0f", "#9333ea", "#0f766e",
  "#ea580c", "#1d4ed8", "#b91c1c", "#047857", "#a16207",
  "#db2777", "#0284c7", "#65a30d", "#c2410c", "#6d28d9",
  "#0d9488", "#e11d48", "#4338ca", "#15803d", "#b45309",
];
const BACKTEST_STRUCTURE_AXIS_DEFAULTS = [
  { key: "trend_context", label: "Trend Context", max: 10 },
  { key: "confirmation_depth", label: "Confirmation Depth", max: 10 },
  { key: "trigger_precision", label: "Trigger Precision", max: 10 },
  { key: "exit_discipline", label: "Exit Discipline", max: 10 },
  { key: "risk_control", label: "Risk Control", max: 10 },
  { key: "time_discipline", label: "Time Discipline", max: 10 },
];
const BACKTEST_BEHAVIOR_AXIS_DEFAULTS = [
  { key: "quality", label: "Quality", max: 10 },
  { key: "profitability", label: "Return", max: 10 },
  { key: "risk_adjusted", label: "Sharpe", max: 10 },
  { key: "consistency", label: "Win Rate", max: 10 },
  { key: "payoff_efficiency", label: "Profit Factor", max: 10 },
  { key: "drawdown_control", label: "Drawdown Control", max: 10 },
];
const DASHBOARD_TABS = ["screener", "editor", "backtest", "playbook"];

let currentTicker = "";
let currentStrategy = "";
let sourceStrategyName = ""; // tracks what strategy is being modified
let scanAbortController = null;
let scanRunId = null;
let screenEventPoller = null;
let screenEventPollInFlight = false;
let screenEventSeq = 0;
let liveScreenMatches = [];
let liveScreenMatchKeys = new Set();
let navScanProgressPoller = null;
let navScanProgressJob = null;
let lastScreenMatches = [];
let lastScreenCandidatePool = [];
let lastScreenScanFilters = null;
let lastScreenMeta = {
  strategy_name: "",
  preset_name: "",
  scan_scope: "",
  exchange: "",
  ticker_list: "",
  disqualifiers: { ...screenDisqualifiers },
};
let screenPresetCatalog = {
  active_name: "",
  default_filters: { ...SCREEN_DEFAULT_FILTERS },
  presets: [],
};
let screenFilters = JSON.parse(JSON.stringify(SCREEN_DEFAULT_FILTERS));
let screenEventOrder = [...DEFAULT_TIMELINE_ORDER];
let screenActiveEventKey = "rsi";
let appliedChartTAParameters = null;
let chartTriggerRefreshTimer = null;
let exportTopMatchesInFlight = false;
const LAST_COMPLETED_STRATEGY_KEY = "etf-discovery:last-completed-strategy";

