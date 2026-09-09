// Dashboard backtest-race. See README.md in static/js/dashboard for the feature map.

function getBacktestRaceFuelConfig(key = backtestRaceFuelMetric) {
  return BACKTEST_RACE_FUEL_METRICS.find((metric) => metric.key === key)
    || BACKTEST_RACE_FUEL_METRICS[0];
}

function normalizeBacktestRaceFuelMetric(value) {
  return getBacktestRaceFuelConfig(String(value || "return_pct")).key;
}

function getBacktestRaceFuelValue(lane, metricKey = backtestRaceFuelMetric) {
  const key = normalizeBacktestRaceFuelMetric(metricKey);
  if (key === "avg_quality_score") {
    return Number(lane?.avg_quality_score ?? lane?.quality_score ?? 0) || 0;
  }
  return Number(lane?.[key] ?? 0) || 0;
}

function formatBacktestRaceFuelValue(value, metricKey = backtestRaceFuelMetric) {
  const config = getBacktestRaceFuelConfig(metricKey);
  const numeric = Number(value || 0);
  if (config.kind === "percent") {
    return formatBacktestPercent(numeric);
  }
  if (config.kind === "count") {
    return Math.round(Math.max(0, numeric)).toLocaleString();
  }
  return numeric.toFixed(2);
}

function getBacktestRaceScaledFuel(lane, lanes, metricKey = backtestRaceFuelMetric) {
  const values = Array.isArray(lanes)
    ? lanes.map((item) => getBacktestRaceFuelValue(item, metricKey)).filter((value) => Number.isFinite(value))
    : [];
  const raw = getBacktestRaceFuelValue(lane, metricKey);
  if (!values.length || !Number.isFinite(raw)) {
    return 0;
  }
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  if (maxValue > 0) {
    return Math.max(0, Math.min(100, (raw / maxValue) * 100));
  }
  if (maxValue === 0 && minValue < 0) {
    return Math.max(0, Math.min(100, ((raw - minValue) / (0 - minValue)) * 100));
  }
  if (maxValue < 0) {
    if (maxValue === minValue) {
      return 100;
    }
    return Math.max(0, Math.min(100, ((raw - minValue) / (maxValue - minValue)) * 100));
  }
  return 0;
}

backtestRaceFuelMetric = normalizeBacktestRaceFuelMetric(
  readStickyValue(LAST_BACKTEST_RACE_FUEL_KEY, "return_pct")
);

function getBacktestRaceNodes() {
  return {
    panel: document.getElementById("backtest-race-panel"),
    track: document.getElementById("backtest-race-track"),
    status: document.getElementById("backtest-race-status"),
    progress: document.getElementById("backtest-race-progress"),
    fuel: document.getElementById("backtest-race-fuel"),
    start: document.getElementById("backtest-race-start-btn"),
    stop: document.getElementById("backtest-race-stop-btn"),
    restart: document.getElementById("backtest-race-restart-btn"),
  };
}

function buildBacktestRaceSignature({ sourceMode, strategyName, strategies, signalDays, universeQuery }) {
  const sortedStrategies = Array.isArray(strategies) ? strategies.map((item) => String(item || "").trim()).filter(Boolean) : [];
  return [
    String(sourceMode || "saved"),
    String(strategyName || ""),
    String(signalDays ?? "auto"),
    sortedStrategies.join("|"),
    String(universeQuery || ""),
  ].join("::");
}

function computeBacktestRaceSpeedFactor(lane, minScore, maxScore) {
  const raw = Number(
    lane?.speed_score ?? lane?.avg_quality_score ?? lane?.quality_score ?? lane?.return_pct ?? 0
  );
  if (!Number.isFinite(raw)) {
    return 1.0;
  }
  if (!Number.isFinite(minScore) || !Number.isFinite(maxScore) || maxScore === minScore) {
    return 1.0;
  }
  const normalized = Math.max(0, Math.min(1, (raw - minScore) / (maxScore - minScore)));
  return Number((0.55 + (normalized * 1.1)).toFixed(2));
}

function normalizeBacktestRaceLanes(lanes) {
  const items = Array.isArray(lanes) ? lanes.map((lane, index) => ({
    strategy: String(lane?.strategy || lane?.label || `Lane ${index + 1}`),
    index: Number.isFinite(Number(lane?.index)) ? Number(lane.index) : index + 1,
    status: String(lane?.status || "queued"),
    progress_pct: Math.max(0, Math.min(100, Number(lane?.progress_pct ?? 0) || 0)),
    visual_progress_pct: Math.max(
      0,
      Math.min(100, Number(lane?.visual_progress_pct ?? lane?.display_pct ?? lane?.progress_pct ?? 0) || 0)
    ),
    detail: String(lane?.detail || ""),
    count: Number(lane?.count || 0),
    ticker_count: Number(lane?.ticker_count || 0),
    processed_tickers: Number(lane?.processed_tickers ?? lane?.completed_tickers ?? 0) || 0,
    scored_tickers: Number(lane?.scored_tickers ?? lane?.count ?? 0) || 0,
    no_trade_tickers: Number(lane?.no_trade_tickers ?? 0) || 0,
    error_tickers: Number(lane?.error_tickers ?? 0) || 0,
    completed_tickers: Number(lane?.completed_tickers || 0),
    total_tickers: Number(lane?.total_tickers || lane?.ticker_count || 0),
    last_ticker: String(lane?.last_ticker || ""),
    best_ticker: String(lane?.best_ticker || ""),
    best_return_pct: Number(lane?.best_return_pct || 0),
    trades: Number(lane?.trades || 0),
    quality_score: Number(lane?.quality_score || 0),
    avg_quality_score: Number(lane?.avg_quality_score || 0),
    return_pct: Number(lane?.return_pct || 0),
    sharpe: Number(lane?.sharpe || 0),
    win_rate_pct: Number(lane?.win_rate_pct || 0),
    profit_factor: Number(lane?.profit_factor || 0),
    max_dd_pct: Number(lane?.max_dd_pct || 0),
    structure_score: Number(lane?.structure_score || 0),
    structure_axes: normalizeBacktestStructureAxes(lane?.structure_axes, backtestStrategyAxisCatalog),
    structure_tags: Array.isArray(lane?.structure_tags)
      ? lane.structure_tags.map((tag) => String(tag || "")).filter(Boolean)
      : [],
    axis_order: Array.isArray(lane?.axis_order) && lane.axis_order.length > 0
      ? lane.axis_order.map((item) => String(item || "")).filter(Boolean)
      : normalizeBacktestStructureAxisCatalog(backtestStrategyAxisCatalog).map((axis) => axis.key),
    speed_score: Number(lane?.speed_score ?? lane?.avg_quality_score ?? lane?.quality_score ?? lane?.return_pct ?? 0),
    speed_factor: Number(lane?.speed_factor || 0),
    display_pct: Math.max(0, Math.min(100, Number(lane?.display_pct ?? lane?.progress_pct ?? 0) || 0)),
  })) : [];
  const rawScores = items
    .map((lane) => Number(lane.speed_score))
    .filter((value) => Number.isFinite(value));
  const minScore = rawScores.length ? Math.min(...rawScores) : NaN;
  const maxScore = rawScores.length ? Math.max(...rawScores) : NaN;
  return items.map((lane) => ({
    ...lane,
    speed_factor: lane.speed_factor > 0
      ? lane.speed_factor
      : computeBacktestRaceSpeedFactor(lane, minScore, maxScore),
  }));
}

function createBacktestRaceState({
  signature = "",
  strategies = [],
  lanes = [],
  targetProgress = 0,
  displayProgress = 0,
  status = "idle",
  playing = false,
  activeStrategy = "",
  detail = "",
} = {}) {
  const normalizedLanes = normalizeBacktestRaceLanes(
    lanes.length > 0
      ? lanes
      : strategies.map((strategy, index) => ({
        strategy,
        index: index + 1,
        status: "queued",
        progress_pct: 0,
        visual_progress_pct: 0,
        detail: "Queued",
        speed_score: 0,
        trades: 0,
      }))
  );
  return {
    signature,
    strategies: Array.isArray(strategies) ? strategies.slice() : [],
    lanes: normalizedLanes,
    targetProgress: Math.max(0, Math.min(100, Number(targetProgress) || 0)),
    displayProgress: Math.max(0, Math.min(100, Number(displayProgress) || 0)),
    status,
    playing,
    activeStrategy,
    detail,
    motionTick: 0,
  };
}

function persistBacktestRaceState() {
  if (!backtestRaceState) {
    writeBacktestRaceSnapshot(null);
    return;
  }
  writeBacktestRaceSnapshot({
    signature: backtestRaceState.signature || "",
    strategies: Array.isArray(backtestRaceState.strategies) ? backtestRaceState.strategies.slice() : [],
    lanes: Array.isArray(backtestRaceState.lanes)
      ? backtestRaceState.lanes.map((lane) => ({ ...lane }))
      : [],
    targetProgress: Number(backtestRaceState.targetProgress || 0),
    displayProgress: Number(backtestRaceState.displayProgress || 0),
    status: String(backtestRaceState.status || "idle"),
    activeStrategy: String(backtestRaceState.activeStrategy || ""),
    detail: String(backtestRaceState.detail || ""),
    motionTick: Number(backtestRaceState.motionTick || 0),
    updatedAt: new Date().toISOString(),
  });
}

function restoreBacktestRaceStateFromStorage() {
  const snapshot = readBacktestRaceSnapshot();
  if (!snapshot || !Array.isArray(snapshot.strategies) || snapshot.strategies.length === 0) {
    return false;
  }
  backtestRaceState = createBacktestRaceState({
    signature: String(snapshot.signature || ""),
    strategies: snapshot.strategies.map((item) => String(item || "")).filter(Boolean),
    lanes: Array.isArray(snapshot.lanes) ? snapshot.lanes : [],
    targetProgress: Number(snapshot.targetProgress || 0),
    displayProgress: Number(snapshot.displayProgress || snapshot.targetProgress || 0),
    status: String(snapshot.status || "done") === "running" ? "paused" : String(snapshot.status || "done"),
    activeStrategy: String(snapshot.activeStrategy || ""),
    detail: String(snapshot.detail || "Restored cached race"),
    playing: String(snapshot.status || "done") === "running",
  });
  backtestRaceState.motionTick = Number(snapshot.motionTick || 0);
  backtestRaceCache.set(backtestRaceState.signature, {
    ...backtestRaceState,
    lanes: Array.isArray(backtestRaceState.lanes) ? backtestRaceState.lanes.map((lane) => ({ ...lane })) : [],
  });
  renderBacktestRace();
  setBacktestRacePanelVisible(true);
  ensureBacktestRaceMotionLoop();
  return true;
}

function updateBacktestRaceButtons() {
  const nodes = getBacktestRaceNodes();
  const readiness = getBacktestRunReadiness();
  const enabled = Boolean(readiness.ready);
  const hasRace = Boolean(backtestRaceState && Array.isArray(backtestRaceState.lanes) && backtestRaceState.lanes.length > 0);
  const requestActive = Boolean(backtestRaceAbortController);
  if (nodes.start) {
    nodes.start.disabled = !enabled || !hasRace;
    nodes.start.textContent = requestActive && backtestRacePlaying
      ? "Running"
      : requestActive
        ? "Resume"
        : hasRace
          ? "Run Again"
          : "Start";
    nodes.start.title = !enabled
      ? readiness.reason
      : requestActive
        ? "Resume the visible race"
        : hasRace
          ? "Start a fresh backtest run"
          : "Run a backtest first";
  }
  if (nodes.stop) {
    nodes.stop.disabled = !enabled || (!hasRace && !requestActive);
    nodes.stop.title = !enabled
      ? readiness.reason
      : hasRace || requestActive
        ? "Stop the current race"
        : "Start a backtest first";
  }
  if (nodes.restart) {
    nodes.restart.disabled = !enabled || !hasRace;
    nodes.restart.title = !enabled
      ? readiness.reason
      : hasRace
        ? "Restart the current race from the beginning"
        : "Run a backtest first";
  }
}

function setBacktestRacePanelVisible(show) {
  const nodes = getBacktestRaceNodes();
  if (!nodes.panel) {
    return;
  }
  nodes.panel.classList.toggle("hidden", !show);
  updateBacktestRaceButtons();
}

function ensureBacktestRaceMotionLoop() {
  if (!backtestRaceState || !Array.isArray(backtestRaceState.lanes) || backtestRaceState.lanes.length === 0) {
    if (backtestRaceMotionHandle) {
      cancelAnimationFrame(backtestRaceMotionHandle);
    }
    backtestRaceMotionHandle = null;
    backtestRaceLastMotionFrame = null;
    return;
  }
  if (!backtestRacePlaying) {
    if (backtestRaceMotionHandle) {
      cancelAnimationFrame(backtestRaceMotionHandle);
    }
    backtestRaceMotionHandle = null;
    backtestRaceLastMotionFrame = null;
    return;
  }
  if (backtestRaceMotionHandle) {
    return;
  }
  const step = (timestamp) => {
    if (!backtestRaceState || !Array.isArray(backtestRaceState.lanes) || backtestRaceState.lanes.length === 0) {
      backtestRaceMotionHandle = null;
      backtestRaceLastMotionFrame = null;
      return;
    }
    if (backtestRaceLastMotionFrame === null) {
      backtestRaceLastMotionFrame = timestamp;
    }
    const delta = Math.max(0, (timestamp - backtestRaceLastMotionFrame) / 1000.0);
    backtestRaceLastMotionFrame = timestamp;
    backtestRaceState.motionTick = Number(backtestRaceState.motionTick || 0) + (delta * 90);
    backtestRaceState.lanes = backtestRaceState.lanes.map((lane) => {
      const current = Number(lane.visual_progress_pct ?? lane.progress_pct ?? 0);
      const backend = Number(lane.progress_pct || 0);
      const laneBoost = Number(lane.speed_factor || 1.0);
      const speedStep = 12 * laneBoost;
      const catchUp = Math.max(0, backend - current) * 0.12;
      const next = Math.min(100, current + ((speedStep + catchUp) * delta));
      return {
        ...lane,
        visual_progress_pct: Math.max(current, next),
      };
    });
    persistBacktestRaceState();
    renderBacktestRace();
    if (!backtestRacePlaying) {
      backtestRaceMotionHandle = null;
      backtestRaceLastMotionFrame = null;
      return;
    }
    backtestRaceMotionHandle = requestAnimationFrame(step);
  };
  backtestRaceMotionHandle = requestAnimationFrame(step);
}

function getBacktestRaceLeaderReturn(lanes) {
  if (!Array.isArray(lanes) || lanes.length === 0) {
    return 0;
  }
  return lanes.reduce((max, lane) => {
    const value = Number(lane?.return_pct ?? 0) || 0;
    return value > max ? value : max;
  }, 0);
}

function getBacktestRaceMinReturn(lanes) {
  if (!Array.isArray(lanes) || lanes.length === 0) {
    return 0;
  }
  return lanes.reduce((min, lane) => {
    const value = Number(lane?.return_pct ?? 0) || 0;
    return value < min ? value : min;
  }, 0);
}

function getBacktestRaceScaledProfitability(lane, leaderReturn, floorReturn) {
  const raw = Number(lane?.return_pct ?? 0) || 0;
  if (!Number.isFinite(raw)) {
    return 0;
  }
  if (Number.isFinite(leaderReturn) && leaderReturn > 0) {
    return Math.max(0, Math.min(100, (raw / leaderReturn) * 100));
  }
  if (Number.isFinite(leaderReturn) && leaderReturn === 0 && Number.isFinite(floorReturn) && floorReturn < 0) {
    const normalized = (raw - floorReturn) / (0 - floorReturn);
    return Math.max(0, Math.min(100, normalized * 100));
  }
  if (Number.isFinite(leaderReturn) && leaderReturn < 0) {
    const minReturn = Number.isFinite(floorReturn) ? floorReturn : leaderReturn;
    if (leaderReturn === minReturn) {
      return 100;
    }
    const normalized = (raw - minReturn) / (leaderReturn - minReturn);
    return Math.max(0, Math.min(100, normalized * 100));
  }
  return 0;
}

function formatBacktestPercent(value) {
  const numeric = Number(value || 0);
  const prefix = numeric > 0 ? "+" : "";
  return `${prefix}${numeric.toFixed(2)}%`;
}

function isBacktestRaceTerminalStatus(status) {
  const cleaned = String(status || "").trim().toLowerCase();
  return ["done", "complete", "completed", "finished", "success", "succeeded"].includes(cleaned);
}

function formatBacktestWorkProgress(race, fallbackText = "") {
  const workCompleted = Number(race?.work_completed ?? NaN);
  const workTotal = Number(race?.work_total ?? NaN);
  if (Number.isFinite(workCompleted) && Number.isFinite(workTotal) && workTotal > 0) {
    return `${Math.max(0, Math.round(workCompleted)).toLocaleString()}/${Math.round(workTotal).toLocaleString()} checks`;
  }
  return fallbackText;
}

function resetBacktestRaceState({ keepPanelVisible = false } = {}) {
  backtestRacePlaying = false;
  backtestRaceLastFrameTime = null;
  if (backtestRaceAnimationHandle) {
    cancelAnimationFrame(backtestRaceAnimationHandle);
  }
  backtestRaceAnimationHandle = null;
  if (backtestRaceMotionHandle) {
    cancelAnimationFrame(backtestRaceMotionHandle);
  }
  backtestRaceMotionHandle = null;
  backtestRaceLastMotionFrame = null;
  if (backtestRaceAbortController) {
    backtestRaceAbortController.abort();
  }
  backtestRaceAbortController = null;
  backtestRaceState = null;
  backtestRaceCurrentSignature = "";
  if (!keepPanelVisible) {
    setBacktestRacePanelVisible(false);
  } else {
    updateBacktestRaceButtons();
  }
}

function renderBacktestRace() {
  const nodes = getBacktestRaceNodes();
  if (!nodes.panel || !nodes.track) {
    return;
  }
  bindBacktestRaceControls();
  if (!backtestRaceState || !Array.isArray(backtestRaceState.lanes) || backtestRaceState.lanes.length === 0) {
    nodes.track.innerHTML = `
      <div class="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
        Run a backtest to line up the lanes.
      </div>
    `;
    if (nodes.status) {
      nodes.status.textContent = "Waiting for a run...";
    }
    if (nodes.progress) {
      nodes.progress.textContent = "0%";
    }
    updateBacktestRaceButtons();
    return;
  }

  const displayProgress = Math.max(
    0,
    Math.min(100, Number(backtestRaceState.displayProgress ?? backtestRaceState.targetProgress ?? 0) || 0)
  );
  const motionTick = Number(backtestRaceState.motionTick || 0);
  const lanes = backtestRaceState.lanes.map((lane) => ({ ...lane }));
  const fuelMetric = getBacktestRaceFuelConfig();
  const visualProgress = lanes.length > 0
    ? lanes.reduce((sum, lane) => sum + Math.max(0, Math.min(100, Number(lane.progress_pct ?? 0) || 0)), 0) / lanes.length
    : displayProgress;
  const statusText = backtestRaceState.status === "running"
    ? (backtestRacePlaying
      ? `Running ${backtestRaceState.activeStrategy || "race"}`
      : `Paused at ${Math.round(visualProgress)}%`)
    : backtestRaceState.status === "done"
      ? (backtestRaceState.detail || "Done")
      : backtestRaceState.status === "stopped"
        ? (backtestRaceState.detail || `Stopped at ${Math.round(visualProgress)}%`)
      : backtestRaceState.status === "failed"
        ? (backtestRaceState.detail || "Failed")
        : backtestRaceState.detail || "Ready";

  if (nodes.status) {
    nodes.status.textContent = statusText;
  }

  if (nodes.progress) {
    nodes.progress.textContent = `${Math.round(visualProgress)}% run`;
  }

  const strategyNames = lanes.map((item) => item.strategy);
  const laneMarkup = lanes.map((lane) => {
    const strategyColor = getBacktestStrategyColor(lane.strategy, strategyNames);
    const rawLaneProgress = Math.max(
      0,
      Math.min(100, Number(lane.progress_pct ?? 0) || 0)
    );
    const visualLaneProgress = Math.max(
      rawLaneProgress,
      Math.max(
        0,
        Math.min(100, Number(lane.visual_progress_pct ?? lane.display_pct ?? rawLaneProgress) || 0)
      )
    );
    const fuelProgress = getBacktestRaceScaledFuel(lane, lanes, fuelMetric.key);
    const laneIsComplete = isBacktestRaceTerminalStatus(lane.status);
    const raceIsLive = backtestRaceState.status === "running" || backtestRacePlaying;
    const profitability = Number(lane.return_pct ?? 0);
    const laneStatus = laneIsComplete
      ? "Complete"
      : lane.status === "running"
        ? "Running"
          : lane.status === "failed"
            ? "Failed"
            : "Queued";
    const quality = Number(lane.avg_quality_score ?? lane.quality_score ?? 0);
    const tradeCount = Math.max(0, Math.round(Number(lane.trades ?? 0) || 0));
    const processedTickers = Math.max(0, Math.round(Number(lane.processed_tickers ?? lane.completed_tickers ?? 0) || 0));
    const scoredTickers = Math.max(0, Math.round(Number(lane.scored_tickers ?? lane.count ?? 0) || 0));
    const noTradeTickers = Math.max(0, Math.round(Number(lane.no_trade_tickers ?? 0) || 0));
    const errorTickers = Math.max(0, Math.round(Number(lane.error_tickers ?? 0) || 0));
    const totalTickers = Math.max(0, Math.round(Number(lane.total_tickers ?? lane.ticker_count ?? 0) || 0));
    const fuelValue = getBacktestRaceFuelValue(lane, fuelMetric.key);
    const hasScoredData = scoredTickers > 0 || tradeCount > 0;
    const dataWidth = Number(Math.max(0, Math.min(100, hasScoredData ? fuelProgress : 0)).toFixed(2));
    const markerWidth = dataWidth;
    const laneNudge = Math.sin((motionTick / 12.5) + lane.index) * (backtestRacePlaying ? 0.8 : 0.3);
    const structureScore = Number(lane.structure_score || 0);
    return `
      <div class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 shadow-sm">
        <div class="mb-1.5 flex items-center justify-between gap-3 text-[11px] font-bold uppercase tracking-wide text-slate-500">
          <span class="flex min-w-0 items-center gap-2">
            <span class="h-2.5 w-2.5 shrink-0 rounded-full" style="background: ${strategyColor};"></span>
            <span class="truncate">${escapeHtml(lane.strategy)}</span>
          </span>
          <div class="flex items-center gap-2">
            <span class="rounded-full border border-slate-200 bg-white px-2 py-0.5 font-mono text-[10px] text-slate-600">${processedTickers}/${totalTickers || "?"}</span>
            <span class="font-mono">${escapeHtml(laneStatus)}</span>
          </div>
        </div>
        <div class="relative h-9 overflow-hidden rounded-md border border-slate-200 bg-white">
          <div class="absolute inset-x-2 top-1/2 h-2 -translate-y-1/2 rounded-full bg-slate-200"></div>
          <div class="absolute inset-y-0 left-2 right-2 overflow-hidden rounded-md">
            <div data-role="fuel-fill" class="absolute inset-y-0 left-0 h-full rounded-md bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-300 opacity-90" style="width: ${dataWidth}%"></div>
          </div>
          <div class="absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border border-white shadow-sm transition-transform duration-150 ease-out"
               style="left: calc(${markerWidth}% + ${laneNudge}px); transform: translate(-50%, -50%); background: ${strategyColor}; box-shadow: 0 0 0 2px rgba(255,255,255,0.7), 0 4px 10px rgba(15,23,42,0.18);"></div>
        </div>
        <div class="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <span class="font-mono">Processed ${processedTickers.toLocaleString()}${totalTickers ? `/${totalTickers.toLocaleString()}` : ""}</span>
          <span class="font-mono">Scored ${scoredTickers.toLocaleString()}</span>
          <span class="font-mono">No trade ${noTradeTickers.toLocaleString()}</span>
          ${errorTickers > 0 ? `<span class="font-mono text-rose-600">Errors ${errorTickers.toLocaleString()}</span>` : ""}
          <span class="font-mono">Fuel ${escapeHtml(fuelMetric.label)} ${formatBacktestRaceFuelValue(fuelValue, fuelMetric.key)}</span>
          <span class="font-mono">Trades ${tradeCount.toLocaleString()}</span>
          <span class="font-mono ${profitability >= 0 ? "text-emerald-600" : "text-rose-600"}">Profitability ${formatBacktestPercent(profitability)}</span>
          <span>Quality ${quality.toFixed(2)}</span>
          <span>Structure ${structureScore.toFixed(2)}</span>
          <span class="font-mono">${rawLaneProgress.toFixed(0)}% run</span>
          <span class="font-mono text-slate-400">${hasScoredData ? `${fuelMetric.label} data ${dataWidth.toFixed(0)}%` : "No scored data"}</span>
        </div>
        <div class="mt-1 text-[11px] text-slate-400">${escapeHtml(lane.detail || "Queued")}</div>
      </div>
    `;
  }).join("");

  nodes.track.innerHTML = `
    <div class="space-y-3">
      ${laneMarkup}
    </div>
  `;
  setBacktestRacePanelVisible(true);
  updateBacktestRaceButtons();
  ensureBacktestRaceMotionLoop();
}

function seedBacktestRaceState({
  signature = "",
  strategies = [],
  lanes = [],
  targetProgress = 0,
  displayProgress = 0,
  status = "queued",
  activeStrategy = "",
  detail = "",
} = {}) {
  backtestRaceCurrentSignature = signature;
  backtestRaceState = createBacktestRaceState({
    signature,
    strategies,
    lanes,
    targetProgress,
    displayProgress,
    status,
    activeStrategy,
    detail,
    playing: backtestRacePlaying,
  });
  persistBacktestRaceState();
  renderBacktestRace();
  return backtestRaceState;
}

function updateBacktestRaceFromSnapshot(snapshot) {
  const race = snapshot && snapshot.backtest_race ? snapshot.backtest_race : snapshot;
  if (!race || typeof race !== "object") {
    return false;
  }
  const lanes = Array.isArray(race.lanes) ? race.lanes : [];
  const strategies = Array.isArray(race.selected_strategies) ? race.selected_strategies : lanes.map((lane) => lane.strategy).filter(Boolean);
  const runId = String(race.run_id || snapshot?.run_id || "");
  if (runId && runId !== backtestRaceEventRunId) {
    backtestRaceEventRunId = runId;
    backtestRaceNextEventSeq = 1;
  }
  const signature = buildBacktestRaceSignature({
    sourceMode: backtestSourceMode,
    strategyName: strategies[0] || "",
    strategies,
    signalDays: getBacktestSignalDays(),
    universeQuery: getUniverseFilterParams().toString(),
  });
  const cached = backtestRaceCache.get(signature);
  const incoming = cached && cached.lanes && lanes.length === 0 ? cached.lanes : lanes;
  const previousLanes = backtestRaceState && backtestRaceState.signature === signature
    ? backtestRaceState.lanes
    : [];
  const incomingByStrategy = new Map(
    incoming
      .map((lane) => [String(lane?.strategy || ""), lane])
      .filter(([strategy]) => Boolean(strategy))
  );
  const previousByStrategy = new Map(
    previousLanes
      .map((lane) => [String(lane?.strategy || ""), lane])
      .filter(([strategy]) => Boolean(strategy))
  );
  const nextLanes = strategies.length > 0
    ? strategies.map((strategy, index) => {
      const incomingLane = incomingByStrategy.get(String(strategy)) || {};
      const previousLane = previousByStrategy.get(String(strategy)) || {};
      return {
        ...previousLane,
        ...incomingLane,
        strategy,
        index: Number(incomingLane.index ?? previousLane.index ?? index + 1),
        status: String(incomingLane.status || previousLane.status || "queued"),
        progress_pct: Number(incomingLane.progress_pct ?? previousLane.progress_pct ?? 0) || 0,
        visual_progress_pct: Number(previousLane.visual_progress_pct ?? incomingLane.visual_progress_pct ?? incomingLane.progress_pct ?? previousLane.progress_pct ?? 0) || 0,
        detail: String(incomingLane.detail || previousLane.detail || "Queued"),
        speed_score: Number(incomingLane.speed_score ?? previousLane.speed_score ?? 0) || 0,
      };
    })
    : incoming;
  const nextState = createBacktestRaceState({
    signature,
    strategies,
    lanes: nextLanes,
    targetProgress: Number(race.pct ?? snapshot?.pct ?? 0) || 0,
    displayProgress: backtestRaceState && backtestRaceState.signature === signature
      ? Number(backtestRaceState.displayProgress || 0)
      : Number(race.pct ?? snapshot?.pct ?? 0) || 0,
    status: String(race.phase || snapshot?.phase || "running"),
    activeStrategy: String(race.active_strategy || race.activeStrategy || ""),
    detail: String(race.detail || snapshot?.detail || ""),
    playing: backtestRacePlaying,
  });
  backtestRaceState = nextState;
  backtestRaceCache.set(signature, {
    ...nextState,
    lanes: nextState.lanes.map((lane) => ({ ...lane })),
  });
  syncBacktestStrategySummariesFromRaceState();
  persistBacktestRaceState();
  renderBacktestRace();
  renderBacktestStructureRadar();
  renderBacktestBehaviorRadar();
  return true;
}

function applyBacktestRaceEvent(event) {
  if (!event || typeof event !== "object") {
    return false;
  }
  const eventType = String(event.type || "");
  const laneName = String(event.lane || event.payload?.strategy || "");
  const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
  if (eventType === "ticker_done") {
    mergeBacktestScatterRows(payload, { render: true });
  }
  if (!backtestRaceState || !Array.isArray(backtestRaceState.lanes)) {
    return false;
  }
  if (!laneName && eventType !== "run_done") {
    return false;
  }

  if (eventType === "run_done") {
    backtestRaceState.status = "done";
    backtestRaceState.detail = `${Number(payload.rows_scored || 0)} rows scored`;
    backtestRaceState.targetProgress = 100;
    backtestRaceState.displayProgress = 100;
    renderBacktestRace();
    return true;
  }

  const laneIndex = backtestRaceState.lanes.findIndex((lane) => String(lane.strategy) === laneName);
  if (laneIndex < 0) {
    return false;
  }
  const lane = { ...backtestRaceState.lanes[laneIndex] };
  if (eventType === "lane_started") {
    lane.status = "running";
    lane.detail = "Started";
    lane.progress_pct = Math.max(0, Number(lane.progress_pct || 0));
  } else if (eventType === "ticker_done") {
    const laneSnapshot = payload.lane && typeof payload.lane === "object" ? payload.lane : {};
    Object.assign(lane, laneSnapshot);
    lane.status = "running";
    lane.progress_pct = Math.max(0, Math.min(100, Number(payload.progress_pct ?? lane.progress_pct ?? 0) || 0));
    lane.completed_tickers = Number(payload.completed ?? lane.completed_tickers ?? 0) || 0;
    lane.total_tickers = Number(payload.total ?? lane.total_tickers ?? 0) || 0;
    lane.processed_tickers = Number(payload.processed ?? payload.completed ?? lane.processed_tickers ?? lane.completed_tickers ?? 0) || 0;
    lane.scored_tickers = Number(payload.scored_tickers ?? lane.scored_tickers ?? lane.count ?? 0) || 0;
    lane.no_trade_tickers = Number(payload.no_trade_tickers ?? lane.no_trade_tickers ?? 0) || 0;
    lane.error_tickers = Number(payload.error_tickers ?? lane.error_tickers ?? 0) || 0;
    lane.last_ticker = String(payload.ticker || lane.last_ticker || "");
    lane.detail = lane.total_tickers
      ? `${lane.processed_tickers}/${lane.total_tickers} tickers, last ${lane.last_ticker || "-"}`
      : `Last ${lane.last_ticker || "ticker"} complete`;
  } else if (eventType === "lane_cached") {
    lane.status = "done";
    lane.progress_pct = 100;
    lane.detail = String(payload.detail || "Loaded cached results");
  } else if (eventType === "lane_done") {
    const laneSnapshot = payload.lane && typeof payload.lane === "object" ? payload.lane : {};
    Object.assign(lane, laneSnapshot);
    lane.status = "done";
    lane.progress_pct = 100;
    lane.detail = String(lane.detail || `${Number(payload.rows_scored || 0)} rows scored`);
  } else {
    return false;
  }
  backtestRaceState.lanes[laneIndex] = lane;
  syncBacktestStrategySummariesFromRaceState();
  persistBacktestRaceState();
  renderBacktestRace();
  renderBacktestStructureRadar();
  renderBacktestBehaviorRadar();
  return true;
}

async function pollBacktestRaceEvents(runId = backtestRaceEventRunId) {
  const safeRunId = String(runId || "");
  if (backtestRaceEventFetchInFlight) {
    return false;
  }
  backtestRaceEventFetchInFlight = true;
  try {
    const params = new URLSearchParams({
      after_seq: String(backtestRaceNextEventSeq - 1),
    });
    if (safeRunId) {
      params.set("run_id", safeRunId);
    }
    const resp = await fetch(`/api/backtest/events?${params.toString()}`, { cache: "no-store" });
    if (!resp.ok) {
      return false;
    }
    const data = await resp.json();
    const events = Array.isArray(data.events) ? data.events : [];
    events.forEach((event) => {
      applyBacktestRaceEvent(event);
      const seq = Number(event.seq || 0);
      if (Number.isFinite(seq)) {
        backtestRaceNextEventSeq = Math.max(backtestRaceNextEventSeq, seq + 1);
      }
    });
    if (Number(data.next_seq) > 0) {
      backtestRaceNextEventSeq = Math.max(backtestRaceNextEventSeq, Number(data.next_seq));
    }
    return events.length > 0;
  } catch (err) {
    console.warn("Backtest race event poll failed", err);
    return false;
  } finally {
    backtestRaceEventFetchInFlight = false;
  }
}

function startBacktestRacePlayback({ autoplay = true } = {}) {
  if (!backtestRaceState || !Array.isArray(backtestRaceState.lanes) || backtestRaceState.lanes.length === 0) {
    return;
  }
  backtestRacePlaying = Boolean(autoplay);
  backtestRaceState.playing = backtestRacePlaying;
  backtestRaceState.status = "running";
  persistBacktestRaceState();
  backtestRaceLastFrameTime = null;
  updateBacktestRaceButtons();
  if (!backtestRacePlaying) {
    renderBacktestRace();
    return;
  }
  ensureBacktestRaceMotionLoop();
  renderBacktestRace();
}

function pauseBacktestRacePlayback() {
  backtestRacePlaying = false;
  if (backtestRaceState) {
    backtestRaceState.playing = false;
    persistBacktestRaceState();
  }
  if (backtestRaceAnimationHandle) {
    cancelAnimationFrame(backtestRaceAnimationHandle);
  }
  backtestRaceAnimationHandle = null;
  if (backtestRaceMotionHandle) {
    cancelAnimationFrame(backtestRaceMotionHandle);
  }
  backtestRaceMotionHandle = null;
  backtestRaceLastFrameTime = null;
  backtestRaceLastMotionFrame = null;
  updateBacktestRaceButtons();
  renderBacktestRace();
}

function stopBacktestRacePlayback({ abortRequest = true } = {}) {
  if (abortRequest && backtestRaceAbortController) {
    backtestRaceAbortController.abort();
  }
  pauseBacktestRacePlayback();
  if (backtestRaceState) {
    backtestRaceState.status = "stopped";
    backtestRaceState.detail = "Stopped";
    persistBacktestRaceState();
    renderBacktestRace();
  }
}

function buildBacktestRaceSeedLanes(strategies = []) {
  return Array.isArray(strategies) ? strategies.map((strategy, index) => ({
    strategy,
    index: index + 1,
    status: "queued",
    progress_pct: 0,
    visual_progress_pct: 0,
    detail: "Queued",
    speed_score: 0,
  })) : [];
}

function syncBacktestRaceLanesToCurrentSelection({ onlyWhenRaceExists = true } = {}) {
  if (backtestRaceAbortController) {
    return false;
  }

  const nodes = getBacktestRaceNodes();
  const hasRace = Boolean(backtestRaceState && Array.isArray(backtestRaceState.lanes) && backtestRaceState.lanes.length > 0);
  const panelVisible = Boolean(nodes.panel && !nodes.panel.classList.contains("hidden"));
  if (onlyWhenRaceExists && !hasRace && !panelVisible) {
    return false;
  }

  const strategySelect = document.getElementById("strategy-select");
  const selectedStrategies = backtestSourceMode === "editor"
    ? [strategySelect?.value || "Editor Draft"]
    : getBacktestSelectedStrategies();
  const strategies = selectedStrategies
    .map((strategy) => String(strategy || "").trim())
    .filter(Boolean);

  if (strategies.length === 0) {
    resetBacktestRaceState({ keepPanelVisible: false });
    renderBacktestRace();
    return true;
  }

  const signature = buildBacktestRaceSignature({
    sourceMode: backtestSourceMode,
    strategyName: backtestSourceMode === "editor" ? (strategySelect?.value || "Editor Draft") : (strategies[0] || ""),
    strategies,
    signalDays: getBacktestSignalDays(),
    universeQuery: getUniverseFilterParams().toString(),
  });
  const existingStrategies = backtestRaceState && Array.isArray(backtestRaceState.strategies)
    ? backtestRaceState.strategies.map((strategy) => String(strategy || ""))
    : [];
  if (
    backtestRaceState
    && backtestRaceState.signature === signature
    && existingStrategies.join("|") === strategies.join("|")
  ) {
    return false;
  }

  backtestRacePlaying = false;
  seedBacktestRaceState({
    signature,
    strategies,
    lanes: buildBacktestRaceSeedLanes(strategies),
    targetProgress: 0,
    displayProgress: 0,
    status: "queued",
    activeStrategy: strategies[0] || "",
    detail: "Ready to run selected strategies.",
  });
  setBacktestRacePanelVisible(true);
  return true;
}

function restartBacktestRacePlayback() {
  const selectedStrategies = getBacktestSelectedStrategies();
  const restartStrategies = selectedStrategies.length > 0
    ? selectedStrategies
    : backtestRaceState && Array.isArray(backtestRaceState.strategies) && backtestRaceState.strategies.length > 0
      ? backtestRaceState.strategies.slice()
      : [];
  const restartSignature = backtestRaceState && backtestRaceState.signature
    ? backtestRaceState.signature
    : buildBacktestRaceSignature({
      sourceMode: backtestSourceMode,
      strategyName: restartStrategies[0] || (document.getElementById("strategy-select")?.value || "Editor Draft"),
      strategies: restartStrategies,
      signalDays: getBacktestSignalDays(),
      universeQuery: getUniverseFilterParams().toString(),
    });
  if (backtestRaceAbortController) {
    backtestRaceAbortController.abort();
  }
  pauseBacktestRacePlayback();
  if (restartSignature) {
    backtestRaceCache.delete(restartSignature);
  }
  writeBacktestRaceSnapshot(null);
  seedBacktestRaceState({
    signature: restartSignature,
    strategies: restartStrategies,
    lanes: buildBacktestRaceSeedLanes(restartStrategies),
    targetProgress: 0,
    displayProgress: 0,
    status: "running",
    activeStrategy: restartStrategies[0] || "",
    detail: "Restarting from the beginning...",
  });
  void loadBacktestMetrics({ restartRace: true });
}

function bindBacktestRaceControls() {
  const nodes = getBacktestRaceNodes();
  if (nodes.fuel) {
    if (nodes.fuel.value !== backtestRaceFuelMetric) {
      nodes.fuel.value = backtestRaceFuelMetric;
    }
    if (nodes.fuel.dataset.bound !== "1") {
      nodes.fuel.dataset.bound = "1";
      nodes.fuel.addEventListener("change", () => {
        backtestRaceFuelMetric = normalizeBacktestRaceFuelMetric(nodes.fuel.value);
        writeStickyValue(LAST_BACKTEST_RACE_FUEL_KEY, backtestRaceFuelMetric);
        renderBacktestRace();
      });
    }
  }
  if (nodes.start && nodes.start.dataset.bound !== "1") {
    nodes.start.dataset.bound = "1";
    nodes.start.addEventListener("click", () => {
      const readiness = getBacktestRunReadiness();
      if (!readiness.ready) {
        return;
      }

      if (backtestRaceAbortController) {
        if (
          backtestRaceState
          && Array.isArray(backtestRaceState.lanes)
          && backtestRaceState.lanes.length > 0
          && !backtestRacePlaying
        ) {
          startBacktestRacePlayback({ autoplay: true });
        }
        return;
      }

      void loadBacktestMetrics({ restartRace: true });
    });
  }
  if (nodes.stop && nodes.stop.dataset.bound !== "1") {
    nodes.stop.dataset.bound = "1";
    nodes.stop.addEventListener("click", () => {
      stopBacktestRacePlayback({ abortRequest: true });
    });
  }
  if (nodes.restart && nodes.restart.dataset.bound !== "1") {
    nodes.restart.dataset.bound = "1";
    nodes.restart.addEventListener("click", () => {
      restartBacktestRacePlayback();
    });
  }
}

