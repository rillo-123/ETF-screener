// Dashboard backtest-results. See README.md in static/js/dashboard for the feature map.

function setBacktestEmptyState(message) {
  const emptyState = document.getElementById("backtest-empty");
  const content = document.getElementById("backtest-content");
  const body = document.getElementById("backtest-table-body");
  const chartDiv = document.getElementById("backtest-chart");
  const racePanel = document.getElementById("backtest-race-panel");

  if (body) {
    body.innerHTML = "";
  }
  backtestMatrixRows = [];
  backtestTradeDotRows = [];
  backtestExcludedTickers = new Set();
  backtestStrategySummaries = [];
  backtestStrategyAxisCatalog = backtestDefaultStructureAxisCatalog();
  updateBacktestBestStructureCard([]);
  setBacktestStructurePanelVisible(false);
  setBacktestBehaviorPanelVisible(false);
  updateBacktestTableHeaderState();
  if (chartDiv && window.Plotly) {
    Plotly.purge(chartDiv);
  }
  const structureChartDiv = document.getElementById("backtest-structure-chart");
  if (structureChartDiv && window.Plotly) {
    Plotly.purge(structureChartDiv);
  }
  const behaviorChartDiv = document.getElementById("backtest-behavior-chart");
  if (behaviorChartDiv && window.Plotly) {
    Plotly.purge(behaviorChartDiv);
  }
  if (racePanel && !backtestRaceState) {
    racePanel.classList.add("hidden");
  }
  emptyState.textContent = message;
  emptyState.classList.remove("hidden");
  content.classList.add("hidden");
}

function prepareBacktestLiveResults(message = "Waiting for scored backtest rows...") {
  const emptyState = document.getElementById("backtest-empty");
  const content = document.getElementById("backtest-content");
  const body = document.getElementById("backtest-table-body");
  if (body) {
    body.innerHTML = "";
  }
  if (emptyState) {
    emptyState.textContent = message;
    emptyState.classList.add("hidden");
  }
  if (content) {
    content.classList.remove("hidden");
  }
  backtestMatrixRows = [];
  backtestTradeDotRows = [];
  backtestExcludedTickers = new Set();
  backtestStrategySummaries = [];
  backtestStrategyAxisCatalog = backtestDefaultStructureAxisCatalog();
  updateBacktestBestStructureCard([]);
  setBacktestStructurePanelVisible(false);
  setBacktestBehaviorPanelVisible(false);
  updateBacktestTableHeaderState();
  populateBacktestAxisControls(backtestDefaultMetrics());
  renderBacktestScatter();
  renderBacktestStructureRadar();
  renderBacktestBehaviorRadar();
}

function backtestDefaultMetrics() {
  return [
    { key: "quality_score", label: "Quality Score", kind: "score" },
    { key: "return_pct", label: "Return (%)", kind: "percent" },
    { key: "win_rate_pct", label: "Win Rate (%)", kind: "percent" },
    { key: "sharpe", label: "Sharpe", kind: "ratio" },
    { key: "profit_factor", label: "Profit Factor", kind: "ratio" },
    { key: "max_dd_pct", label: "Max Drawdown (%)", kind: "percent" },
    { key: "trades", label: "Trades", kind: "count" },
    { key: "days_since_entry", label: "Days Since Entry", kind: "days" },
  ];
}

function backtestDefaultStructureAxisCatalog() {
  return BACKTEST_STRUCTURE_AXIS_DEFAULTS.map((item) => ({ ...item }));
}

function backtestDefaultBehaviorAxisCatalog() {
  return BACKTEST_BEHAVIOR_AXIS_DEFAULTS.map((item) => ({ ...item }));
}

function clampBacktestRadarValue(value, max = 10) {
  return Math.max(0, Math.min(max, Number(value || 0) || 0));
}

function scaleBacktestRadarMetric(value, { min = 0, max = 1, invert = false } = {}) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || max <= min) {
    return 0;
  }
  const normalized = Math.max(0, Math.min(1, (numeric - min) / (max - min)));
  const scaled = (invert ? 1 - normalized : normalized) * 10;
  return Number(scaled.toFixed(2));
}

function normalizeBacktestStructureAxisCatalog(catalog) {
  const rawItems = Array.isArray(catalog) && catalog.length > 0
    ? catalog
    : backtestDefaultStructureAxisCatalog();
  return rawItems.map((item, index) => ({
    key: String(item?.key || BACKTEST_STRUCTURE_AXIS_DEFAULTS[index]?.key || `axis_${index + 1}`),
    label: String(item?.label || BACKTEST_STRUCTURE_AXIS_DEFAULTS[index]?.label || `Axis ${index + 1}`),
    max: Math.max(1, Number(item?.max || BACKTEST_STRUCTURE_AXIS_DEFAULTS[index]?.max || 10) || 10),
  }));
}

function normalizeBacktestStructureAxes(axes, axisCatalog = backtestStrategyAxisCatalog) {
  const safeAxes = axes && typeof axes === "object" ? axes : {};
  const catalog = normalizeBacktestStructureAxisCatalog(axisCatalog);
  return catalog.reduce((acc, axis) => {
    acc[axis.key] = clampBacktestRadarValue(safeAxes[axis.key], axis.max);
    return acc;
  }, {});
}

function backtestStrategySummaryHasBehaviorData(summary) {
  if (!summary || typeof summary !== "object") {
    return false;
  }
  return [
    summary.avg_quality_score,
    summary.quality_score,
    summary.return_pct,
    summary.sharpe,
    summary.win_rate_pct,
    summary.profit_factor,
    summary.max_dd_pct,
    summary.trades,
    summary.scored_tickers,
  ].some((value) => Number(value || 0) !== 0);
}

function deriveBacktestBehaviorProfile(summary) {
  const quality = Number(summary?.avg_quality_score ?? summary?.quality_score ?? 0) || 0;
  const returnPct = Number(summary?.return_pct ?? 0) || 0;
  const sharpe = Number(summary?.sharpe ?? 0) || 0;
  const winRatePct = Number(summary?.win_rate_pct ?? 0) || 0;
  const profitFactor = Number(summary?.profit_factor ?? 0) || 0;
  const maxDdPct = Number(summary?.max_dd_pct ?? 0) || 0;
  const axisOrder = backtestDefaultBehaviorAxisCatalog().map((axis) => axis.key);
  const behaviorAxes = {
    quality: scaleBacktestRadarMetric(quality, { min: 0, max: 20 }),
    profitability: scaleBacktestRadarMetric(returnPct, { min: -10, max: 20 }),
    risk_adjusted: scaleBacktestRadarMetric(sharpe, { min: -0.5, max: 2.5 }),
    consistency: scaleBacktestRadarMetric(winRatePct, { min: 30, max: 70 }),
    payoff_efficiency: scaleBacktestRadarMetric(profitFactor, { min: 0.8, max: 2.0 }),
    drawdown_control: scaleBacktestRadarMetric(maxDdPct, { min: 2, max: 20, invert: true }),
  };
  const values = axisOrder.map((key) => Number(behaviorAxes[key] || 0));
  const behaviorScore = values.length
    ? Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2))
    : 0;
  return {
    behavior_score: behaviorScore,
    behavior_axes: axisOrder.reduce((acc, key) => {
      acc[key] = clampBacktestRadarValue(behaviorAxes[key]);
      return acc;
    }, {}),
    axis_order: axisOrder,
    raw_metrics: {
      quality,
      profitability: returnPct,
      risk_adjusted: sharpe,
      consistency: winRatePct,
      payoff_efficiency: profitFactor,
      drawdown_control: maxDdPct,
    },
  };
}

function normalizeBacktestStrategySummary(summary, index = 0, axisCatalog = backtestStrategyAxisCatalog) {
  const catalog = normalizeBacktestStructureAxisCatalog(axisCatalog);
  const normalized = {
    strategy: String(summary?.strategy || summary?.label || `Strategy ${index + 1}`),
    quality_score: Number(summary?.quality_score || 0) || 0,
    avg_quality_score: Number(summary?.avg_quality_score ?? summary?.quality_score ?? 0) || 0,
    return_pct: Number(summary?.return_pct || 0) || 0,
    sharpe: Number(summary?.sharpe || 0) || 0,
    win_rate_pct: Number(summary?.win_rate_pct || 0) || 0,
    profit_factor: Number(summary?.profit_factor || 0) || 0,
    max_dd_pct: Number(summary?.max_dd_pct || 0) || 0,
    trades: Number(summary?.trades || 0) || 0,
    scored_tickers: Number(summary?.scored_tickers ?? summary?.count ?? 0) || 0,
    total_tickers: Number(summary?.total_tickers ?? summary?.ticker_count ?? summary?.count ?? 0) || 0,
    structure_score: Number(summary?.structure_score || 0) || 0,
    structure_axes: normalizeBacktestStructureAxes(summary?.structure_axes, catalog),
    structure_tags: Array.isArray(summary?.structure_tags)
      ? summary.structure_tags.map((tag) => String(tag || "")).filter(Boolean)
      : [],
    axis_order: Array.isArray(summary?.axis_order) && summary.axis_order.length > 0
      ? summary.axis_order.map((item) => String(item || "")).filter(Boolean)
      : catalog.map((axis) => axis.key),
  };
  normalized.behavior_profile = deriveBacktestBehaviorProfile(normalized);
  normalized.has_behavior_data = backtestStrategySummaryHasBehaviorData(normalized);
  return normalized;
}

function updateBacktestBestStructureCard(summaries = backtestStrategySummaries) {
  const node = document.getElementById("bt-best-structure");
  if (!node) {
    return;
  }
  const best = (Array.isArray(summaries) ? summaries : [])
    .map((item) => Number(item?.structure_score || 0))
    .filter(Number.isFinite);
  node.textContent = (best.length ? Math.max(...best) : 0).toFixed(2);
}

function setBacktestStructurePanelVisible(show) {
  const panel = document.getElementById("backtest-structure-panel");
  if (!panel) {
    return;
  }
  panel.classList.toggle("hidden", !show);
}

function setBacktestBehaviorPanelVisible(show) {
  const panel = document.getElementById("backtest-behavior-panel");
  if (!panel) {
    return;
  }
  panel.classList.toggle("hidden", !show);
}

function syncBacktestStrategySummariesFromRaceState() {
  if (!backtestRaceState || !Array.isArray(backtestRaceState.lanes) || backtestRaceState.lanes.length === 0) {
    return false;
  }
  backtestStrategySummaries = backtestRaceState.lanes.map((lane, index) => (
    normalizeBacktestStrategySummary(lane, index, backtestStrategyAxisCatalog)
  ));
  updateBacktestBestStructureCard(backtestStrategySummaries);
  setBacktestStructurePanelVisible(backtestStrategySummaries.length > 0);
  return true;
}

function setBacktestStructureData({
  summaries = [],
  strategyProfile = null,
  axisCatalog = null,
  strategyName = "",
} = {}) {
  backtestStrategyAxisCatalog = normalizeBacktestStructureAxisCatalog(axisCatalog);
  const sourceSummaries = Array.isArray(summaries) && summaries.length > 0
    ? summaries
    : (strategyProfile && typeof strategyProfile === "object"
      ? [{
        strategy: String(strategyName || "Editor Draft"),
        ...strategyProfile,
      }]
      : []);
  backtestStrategySummaries = sourceSummaries.map((item, index) => (
    normalizeBacktestStrategySummary(item, index, backtestStrategyAxisCatalog)
  ));
  if (!backtestStrategySummaries.length) {
    syncBacktestStrategySummariesFromRaceState();
  }
  updateBacktestBestStructureCard(backtestStrategySummaries);
  setBacktestStructurePanelVisible(backtestStrategySummaries.length > 0);
  renderBacktestStructureRadar();
  renderBacktestBehaviorRadar();
}

function getBacktestMetricLabel(key) {
  const metric = backtestMetricCatalog.find((item) => item.key === key);
  return metric ? metric.label : key;
}

function formatBacktestBehaviorRawMetric(key, value) {
  const numeric = Number(value || 0);
  if (key === "profitability" || key === "consistency" || key === "drawdown_control") {
    return `${numeric.toFixed(2)}%`;
  }
  return numeric.toFixed(2);
}

function hashBacktestStrategyName(strategy) {
  const text = String(strategy || "Other");
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash * 31) + text.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function uniqueBacktestStrategyNames(strategies) {
  const seen = new Set();
  const names = [];
  (Array.isArray(strategies) ? strategies : []).forEach((item) => {
    const name = String(item || "").trim();
    if (!name || seen.has(name)) {
      return;
    }
    seen.add(name);
    names.push(name);
  });
  return names;
}

function getBacktestStrategyColorMap(strategies) {
  const names = uniqueBacktestStrategyNames(strategies);
  const usedIndexes = new Set();
  const colorMap = new Map();
  names.forEach((name, order) => {
    let colorIndex = hashBacktestStrategyName(name) % BACKTEST_STRATEGY_COLORS.length;
    let attempts = 0;
    while (usedIndexes.has(colorIndex) && attempts < BACKTEST_STRATEGY_COLORS.length) {
      colorIndex = (colorIndex + 1) % BACKTEST_STRATEGY_COLORS.length;
      attempts += 1;
    }
    if (attempts >= BACKTEST_STRATEGY_COLORS.length) {
      colorIndex = order % BACKTEST_STRATEGY_COLORS.length;
    }
    usedIndexes.add(colorIndex);
    colorMap.set(name, BACKTEST_STRATEGY_COLORS[colorIndex]);
  });
  return colorMap;
}

function getBacktestStrategyColor(strategy, strategies = []) {
  const name = String(strategy || "Other").trim() || "Other";
  const colorMap = getBacktestStrategyColorMap([...uniqueBacktestStrategyNames(strategies), name]);
  return colorMap.get(name) || BACKTEST_STRATEGY_COLORS[0];
}

function getBacktestGroupColor(group, groups = []) {
  return getBacktestStrategyColor(group, groups);
}

function inferBacktestExchange(ticker) {
  const symbol = String(ticker || "").toUpperCase();
  if (symbol.endsWith(".ST") || symbol.endsWith(".SS")) {
    return "sweden";
  }
  if (symbol.endsWith(".DE") || symbol.endsWith(".F") || symbol.endsWith(".DU") || symbol.endsWith(".HM") || symbol.endsWith(".SG") || symbol.endsWith(".BE") || symbol.endsWith(".MU")) {
    return "xetra";
  }
  if (symbol && !symbol.includes(".")) {
    return "nasdaq";
  }
  return "unknown";
}

function computeBacktestLiveQuality(row) {
  const quality = Number(row.quality_score);
  if (Number.isFinite(quality) && quality !== 0) {
    return quality;
  }
  const returnPct = Number(row.return_pct || 0);
  const winRatePct = Number(row.win_rate_pct || 0);
  const sharpe = Number(row.sharpe || 0);
  const maxDdPct = Number(row.max_dd_pct || 0);
  const trades = Number(row.trades || 0);
  return returnPct
    * (winRatePct / 100)
    * (sharpe + 1)
    / ((1 + trades / 100.0) * (1 + maxDdPct / 10.0));
}

function normalizeBacktestTickerKey(ticker) {
  return String(ticker || "").trim().toUpperCase();
}

function isBacktestTickerExcluded(ticker) {
  const key = normalizeBacktestTickerKey(ticker);
  return key ? backtestExcludedTickers.has(key) : false;
}

function setBacktestTickerExcluded(ticker, excluded, { renderTable = true, renderScatter = true } = {}) {
  const key = normalizeBacktestTickerKey(ticker);
  if (!key) {
    return false;
  }
  const isExcluded = Boolean(excluded);
  const changed = isExcluded
    ? !backtestExcludedTickers.has(key)
    : backtestExcludedTickers.has(key);
  if (!changed) {
    return false;
  }
  if (isExcluded) {
    backtestExcludedTickers.add(key);
  } else {
    backtestExcludedTickers.delete(key);
  }
  if (renderTable) {
    renderBacktestTable(backtestMatrixRows);
  }
  if (renderScatter) {
    scheduleBacktestScatterRender();
  }
  return true;
}

function normalizeBacktestMatrixRow(row) {
  if (!row || typeof row !== "object") {
    return null;
  }
  const ticker = String(row.ticker || row.Ticker || "").trim();
  const strategy = String(row.strategy || row.Strategy || "").trim();
  const trades = Math.max(0, Math.round(Number(row.trades ?? row.Trades ?? 0) || 0));
  if (!ticker || !strategy) {
    return null;
  }
  const normalized = {
    ticker,
    strategy,
    exchange: String(row.exchange || row.Exchange || inferBacktestExchange(ticker)),
    quality_score: Number(row.quality_score ?? row["Quality Score"] ?? 0) || 0,
    return_pct: Number(row.return_pct ?? row["Return (%)"] ?? 0) || 0,
    win_rate_pct: Number(row.win_rate_pct ?? row["Win Rate (%)"] ?? 0) || 0,
    profit_factor: Number(row.profit_factor ?? row["Profit Factor"] ?? 0) || 0,
    sharpe: Number(row.sharpe ?? row.Sharpe ?? 0) || 0,
    max_dd_pct: Number(row.max_dd_pct ?? row["Max DD (%)"] ?? 0) || 0,
    trades,
    days_since_entry: Number(row.days_since_entry ?? row["Days Since Entry"] ?? 999) || 999,
  };
  normalized.quality_score = Number(computeBacktestLiveQuality(normalized).toFixed(2));
  return normalized;
}

function normalizeBacktestScatterRow(row) {
  const normalized = normalizeBacktestMatrixRow(row);
  if (!normalized || Number(normalized.trades || 0) <= 0) {
    return null;
  }
  return normalized;
}

function normalizeBacktestTradePoint(rawPoint, fallbackIndex = 1) {
  const point = rawPoint && typeof rawPoint === "object" ? rawPoint : {};
  const tradeIndex = Math.max(1, Math.round(Number(point.trade_index ?? point.index ?? fallbackIndex) || fallbackIndex));
  const gainPct = Number(point.gain_pct ?? point.profit_pct ?? point.return_pct ?? point.profit ?? 0);
  return {
    trade_index: tradeIndex,
    trade_gain_pct: Number.isFinite(gainPct) ? gainPct : 0,
    buy_date: String(point.buy_date || point.entry_date || ""),
    sell_date: String(point.sell_date || point.exit_date || point.date || ""),
    buy_price: Number(point.buy_price ?? point.entry_price ?? 0) || 0,
    sell_price: Number(point.sell_price ?? point.exit_price ?? point.price ?? 0) || 0,
    estimated: false,
  };
}

function expandBacktestTradeDots(row, sourceRow = row) {
  const aggregate = normalizeBacktestMatrixRow(row);
  if (!aggregate || Number(aggregate.trades || 0) <= 0) {
    return [];
  }
  const rawTradePoints = Array.isArray(sourceRow?.trade_points)
    ? sourceRow.trade_points
    : (Array.isArray(sourceRow?.trades_detail) ? sourceRow.trades_detail : []);
  const realPoints = rawTradePoints
    .map((point, index) => normalizeBacktestTradePoint(point, index + 1))
    .filter((point) => Number.isFinite(point.trade_gain_pct));
  const points = realPoints.length > 0
    ? realPoints
    : [{
      trade_index: 1,
      trade_gain_pct: Number(aggregate.return_pct || 0),
      buy_date: "",
      sell_date: "",
      buy_price: 0,
      sell_price: 0,
      estimated: true,
    }];
  return points.map((point) => ({
    ...aggregate,
    ...point,
    dot_id: `${aggregate.strategy}::${aggregate.ticker}::${point.trade_index}`,
  }));
}

function getBacktestTradeDotSize(row) {
  const gainPct = Math.max(0, Number(row?.trade_gain_pct ?? 0) || 0);
  const diameter = 7 + (Math.log1p(gainPct) * 5.2);
  return Math.max(7, Math.min(30, diameter));
}

function getBacktestTableSortConfig() {
  return [
    { key: "ticker", label: "Ticker", defaultDirection: "asc" },
    { key: "strategy", label: "Strategy", defaultDirection: "asc" },
    { key: "quality_score", label: "Quality", defaultDirection: "desc" },
    { key: "return_pct", label: "Return", defaultDirection: "desc" },
    { key: "win_rate_pct", label: "Win Rate", defaultDirection: "desc" },
    { key: "sharpe", label: "Sharpe", defaultDirection: "desc" },
    { key: "profit_factor", label: "PF", defaultDirection: "desc" },
    { key: "max_dd_pct", label: "Max DD", defaultDirection: "asc" },
    { key: "trades", label: "Trades", defaultDirection: "desc" },
    { key: "days_since_entry", label: "Days Since Entry", defaultDirection: "asc" },
  ];
}

function getBacktestTableSortDescriptor(key) {
  return getBacktestTableSortConfig().find((entry) => entry.key === key) || null;
}

function getBacktestTableSortValue(row, key) {
  if (!row || typeof row !== "object") {
    return "";
  }
  if (key === "ticker" || key === "strategy" || key === "exchange") {
    return String(row[key] || "").toUpperCase();
  }
  return Number(row[key] || 0);
}

function sortBacktestTableRows(rows) {
  const safeRows = Array.isArray(rows) ? [...rows] : [];
  const descriptor = getBacktestTableSortDescriptor(backtestTableSortKey) || getBacktestTableSortDescriptor("quality_score");
  const sortKey = descriptor ? descriptor.key : "quality_score";
  const direction = backtestTableSortDirection === "asc" ? 1 : -1;
  return safeRows.sort((left, right) => {
    const leftValue = getBacktestTableSortValue(left, sortKey);
    const rightValue = getBacktestTableSortValue(right, sortKey);
    let primary = 0;
    if (typeof leftValue === "string" || typeof rightValue === "string") {
      primary = String(leftValue).localeCompare(String(rightValue));
    } else {
      primary = Number(leftValue) - Number(rightValue);
    }
    if (primary !== 0) {
      return primary * direction;
    }
    const qualityDelta = Number(right?.quality_score || 0) - Number(left?.quality_score || 0);
    if (qualityDelta !== 0) {
      return qualityDelta;
    }
    const tickerDelta = String(left?.ticker || "").localeCompare(String(right?.ticker || ""));
    if (tickerDelta !== 0) {
      return tickerDelta;
    }
    return String(left?.strategy || "").localeCompare(String(right?.strategy || ""));
  });
}

function updateBacktestTableHeaderState() {
  getBacktestTableSortConfig().forEach((entry) => {
    const button = document.getElementById(`backtest-sort-${entry.key}`);
    if (!button) {
      return;
    }
    const isActive = backtestTableSortKey === entry.key;
    const suffix = isActive ? (backtestTableSortDirection === "asc" ? " ^" : " v") : "";
    button.textContent = `${entry.label}${suffix}`;
    button.className = `inline-flex items-center gap-1 rounded px-1 py-0.5 hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-300 ${isActive ? "bg-slate-200 text-slate-900" : ""}`;
    button.setAttribute("aria-sort", isActive ? (backtestTableSortDirection === "asc" ? "ascending" : "descending") : "none");
  });
}

function setBacktestTableSort(key) {
  const descriptor = getBacktestTableSortDescriptor(key);
  if (!descriptor) {
    return;
  }
  if (backtestTableSortKey === descriptor.key) {
    backtestTableSortDirection = backtestTableSortDirection === "asc" ? "desc" : "asc";
  } else {
    backtestTableSortKey = descriptor.key;
    backtestTableSortDirection = descriptor.defaultDirection;
  }
  updateBacktestTableHeaderState();
  renderBacktestTable(backtestMatrixRows);
}

function mergeBacktestScatterRows(rows, { render = true } = {}) {
  const incomingRows = Array.isArray(rows) ? rows : [rows];
  const byKey = new Map(
    backtestMatrixRows.map((row) => [`${row.strategy}::${row.ticker}`, row])
  );
  const dotsByKey = new Map(
    backtestTradeDotRows.map((row) => [row.dot_id || `${row.strategy}::${row.ticker}::${row.trade_index}`, row])
  );
  let changed = false;
  incomingRows.forEach((item) => {
    const tableRow = normalizeBacktestMatrixRow(item);
    if (!tableRow) {
      return;
    }
    byKey.set(`${tableRow.strategy}::${tableRow.ticker}`, tableRow);
    expandBacktestTradeDots(tableRow, item).forEach((dot) => {
      const existing = dotsByKey.get(dot.dot_id);
      if (existing && dot.estimated && !existing.estimated) {
        return;
      }
      dotsByKey.set(dot.dot_id, dot);
    });
    changed = true;
  });
  if (!changed) {
    return false;
  }
  backtestMatrixRows = Array.from(byKey.values()).sort((left, right) => (
    Number(right.quality_score || 0) - Number(left.quality_score || 0)
  ));
  backtestTradeDotRows = Array.from(dotsByKey.values()).sort((left, right) => (
    Number(right.trade_gain_pct || 0) - Number(left.trade_gain_pct || 0)
  ));
  updateBacktestSummaryCardsFromRows();
  renderBacktestTable(backtestMatrixRows);
  if (render) {
    scheduleBacktestScatterRender();
  }
  return true;
}

function scheduleBacktestScatterRender() {
  if (backtestScatterRenderTimer) {
    return;
  }
  backtestScatterRenderTimer = setTimeout(() => {
    backtestScatterRenderTimer = null;
    renderBacktestScatter();
  }, 150);
}

function updateBacktestSummaryCardsFromRows(summaryRows = backtestMatrixRows) {
  const rows = Array.isArray(summaryRows) ? summaryRows : [];
  const scoredRows = rows.filter((row) => Number(row?.trades || 0) > 0);
  const metricRows = scoredRows.length > 0 ? scoredRows : rows;
  const strategyCount = new Set(rows.map((row) => row.strategy).filter(Boolean)).size;
  const returnValues = metricRows.map((row) => Number(row.return_pct)).filter(Number.isFinite);
  const drawdownValues = metricRows.map((row) => Number(row.max_dd_pct)).filter(Number.isFinite);
  const sharpeValues = metricRows.map((row) => Number(row.sharpe)).filter(Number.isFinite);
  const qualityValues = metricRows.map((row) => Number(row.quality_score)).filter(Number.isFinite);
  const avg = (values) => values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : 0;
  const median = (values) => {
    if (!values.length) return 0;
    const sorted = [...values].sort((left, right) => left - right);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2
      ? sorted[middle]
      : (sorted[middle - 1] + sorted[middle]) / 2;
  };
  const strategyNode = document.getElementById("bt-strategy");
  const countNode = document.getElementById("bt-count");
  const bestQualityNode = document.getElementById("bt-best-quality");
  const avgReturnNode = document.getElementById("bt-avg-return");
  const medianReturnNode = document.getElementById("bt-median-return");
  const medianDrawdownNode = document.getElementById("bt-median-drawdown");
  const avgSharpeNode = document.getElementById("bt-avg-sharpe");
  if (strategyNode) {
    strategyNode.textContent = strategyCount > 1 ? `${strategyCount} strategies` : (rows[0]?.strategy || "Running");
  }
  if (countNode) {
    countNode.textContent = String(rows.length);
  }
  if (bestQualityNode) {
    bestQualityNode.textContent = (qualityValues.length ? Math.max(...qualityValues) : 0).toFixed(2);
  }
  if (avgReturnNode) {
    avgReturnNode.textContent = `${avg(returnValues).toFixed(2)}%`;
  }
  if (medianReturnNode) {
    medianReturnNode.textContent = `${median(returnValues).toFixed(2)}%`;
  }
  if (medianDrawdownNode) {
    medianDrawdownNode.textContent = `${median(drawdownValues).toFixed(2)}%`;
  }
  if (avgSharpeNode) {
    avgSharpeNode.textContent = avg(sharpeValues).toFixed(2);
  }
}

function ensureBacktestTableHeader(body) {
  const table = body?.closest?.("table");
  if (!table) {
    return;
  }
  let thead = table.querySelector("thead");
  if (!thead) {
    thead = document.createElement("thead");
    thead.className = "bg-slate-100 text-[10px] font-bold uppercase tracking-wide text-slate-500";
    thead.innerHTML = "<tr></tr>";
    table.insertBefore(thead, body);
  }
  const headerRow = thead.querySelector("tr");
  if (!headerRow || Array.from(headerRow.children).some((cell) => cell.textContent.trim().toLowerCase() === "exclude")) {
    return;
  }
  const headers = getBacktestTableSortConfig()
    .map((entry) => `<th class="px-4 py-3 text-left"><button id="backtest-sort-${entry.key}" type="button" onclick="setBacktestTableSort('${entry.key}')">${entry.label}</button></th>`)
    .join("");
  if (!headerRow.children.length) {
    headerRow.innerHTML = headers;
  }
  const excludeHeader = document.createElement("th");
  excludeHeader.className = "px-4 py-3 text-left";
  excludeHeader.textContent = "Exclude";
  headerRow.appendChild(excludeHeader);
}

function renderBacktestTable(rows) {
  const body = document.getElementById("backtest-table-body");
  if (!body) {
    return;
  }
  ensureBacktestTableHeader(body);
  updateBacktestTableHeaderState();
  const strategyNames = uniqueBacktestStrategyNames(
    (Array.isArray(rows) ? rows : []).map((row) => row.strategy)
  );
  const displayedRows = sortBacktestTableRows(rows).slice(0, 100);
  body.innerHTML = "";
  displayedRows.forEach((row) => {
    const tr = document.createElement("tr");
    const strategyColor = getBacktestStrategyColor(row.strategy, strategyNames);
    const tradeCount = Number(row.trades || 0);
    const noTrades = tradeCount <= 0;
    const excludedTicker = isBacktestTickerExcluded(row.ticker);
    tr.className = `hover:bg-slate-50 cursor-pointer ${excludedTicker ? "bg-slate-50/80" : ""}`;
    tr.style.opacity = excludedTicker ? "0.72" : "1";
    tr.onclick = () => {
      showTab("screener");
      loadChart(row.ticker, row.strategy || "");
    };
    tr.innerHTML = `
        <td class="px-4 py-3 font-bold text-slate-800">${escapeHtml(row.ticker)}</td>
        <td class="px-4 py-3 font-mono text-slate-600">
          <span class="inline-flex min-w-0 items-center gap-2">
            <span class="h-2.5 w-2.5 shrink-0 rounded-full" style="background: ${strategyColor};"></span>
            <span>${escapeHtml(row.strategy || "")}</span>
          </span>
        </td>
        <td class="px-4 py-3 font-mono text-indigo-700">${Number(row.quality_score || 0).toFixed(2)}</td>
        <td class="px-4 py-3 font-mono ${Number(row.return_pct || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}">${Number(row.return_pct || 0).toFixed(2)}%</td>
        <td class="px-4 py-3 font-mono">${Number(row.win_rate_pct || 0).toFixed(2)}%</td>
        <td class="px-4 py-3 font-mono">${Number(row.sharpe || 0).toFixed(2)}</td>
        <td class="px-4 py-3 font-mono">${Number(row.profit_factor || 0).toFixed(2)}</td>
        <td class="px-4 py-3 font-mono">${Number(row.max_dd_pct || 0).toFixed(2)}%</td>
        <td class="px-4 py-3 font-mono">
          <span class="inline-flex items-center gap-2">
            <span>${tradeCount}</span>
            ${noTrades
              ? '<span class="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-800">No trades</span>'
              : ""}
          </span>
        </td>
        <td class="px-4 py-3 font-mono">${Number(row.days_since_entry || 0)}</td>
      `;
    const excludeCell = document.createElement("td");
    excludeCell.className = "px-4 py-3";
    excludeCell.onclick = (event) => {
      if (event && typeof event.stopPropagation === "function") {
        event.stopPropagation();
      }
    };
    const excludeLabel = document.createElement("label");
    excludeLabel.className = "inline-flex cursor-pointer items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500";
    excludeLabel.onclick = (event) => {
      if (event && typeof event.stopPropagation === "function") {
        event.stopPropagation();
      }
    };
    const excludeCheckbox = document.createElement("input");
    excludeCheckbox.type = "checkbox";
    excludeCheckbox.className = "h-4 w-4 shrink-0 cursor-pointer rounded border-slate-300 text-rose-600 focus:ring-rose-400";
    excludeCheckbox.checked = excludedTicker;
    excludeCheckbox.setAttribute("aria-label", `Exclude ${row.ticker} from scatter plot`);
    excludeCheckbox.title = "Exclude this ticker from the 2D scatter plot";
    excludeCheckbox.onclick = (event) => {
      if (event && typeof event.stopPropagation === "function") {
        event.stopPropagation();
      }
    };
    excludeCheckbox.onchange = (event) => {
      if (event && typeof event.stopPropagation === "function") {
        event.stopPropagation();
      }
      setBacktestTickerExcluded(row.ticker, Boolean(event?.target?.checked));
    };
    const excludeText = document.createElement("span");
    excludeText.textContent = "Exclude";
    excludeLabel.appendChild(excludeCheckbox);
    excludeLabel.appendChild(excludeText);
    excludeCell.appendChild(excludeLabel);
    tr.appendChild(excludeCell);
    body.appendChild(tr);
  });
}

window.setBacktestTableSort = setBacktestTableSort;

