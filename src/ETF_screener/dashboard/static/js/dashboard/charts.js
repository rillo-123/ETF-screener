// Dashboard charts. See README.md in static/js/dashboard for the feature map.

const RANGE_PRESETS = [
  { days: 21, label: "1M", buttonId: "range-btn-1m" },
  { days: 63, label: "3M", buttonId: "range-btn-3m" },
  { days: 126, label: "6M", buttonId: "range-btn-6m" },
  { days: 365, label: "1Y", buttonId: "range-btn-1y" },
  { days: 365 * 2, label: "2Y", buttonId: "range-btn-2y" },
  { days: 365 * 3, label: "3Y", buttonId: "range-btn-3y" },
];
const LAST_CHART_RANGE_KEY = "etf-discovery:last-chart-range-days";
const LAST_CHART_TA_PARAMS_KEY = "etf-discovery:last-chart-ta-params";

function readSavedChartRangeDays() {
  try {
    const raw = localStorage.getItem(LAST_CHART_RANGE_KEY);
    const value = Number(raw);
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : null;
  } catch (err) {
    return null;
  }
}

function saveChartRangeDays(days) {
  try {
    localStorage.setItem(LAST_CHART_RANGE_KEY, String(Math.floor(days)));
  } catch (err) {
    // Ignore storage failures in privacy-restricted environments.
  }
}

function getRangeButton(days) {
  const preset = RANGE_PRESETS.find((item) => item.days === days);
  return preset ? document.getElementById(preset.buttonId) : null;
}

function getRangeLabel(days) {
  const preset = RANGE_PRESETS.find((item) => item.days === days);
  if (preset) return preset.label;
  if (days === FIXED_CHART_WINDOW_DAYS) return `${days}D`;
  if (days >= 365) return `${Math.round(days / 365)}Y`;
  if (days >= 30) return `${Math.round(days / 30)}M`;
  return `${days}D`;
}

function updateRangeChrome() {
  const label = document.getElementById("chart-range-label");
  if (label) {
    label.textContent = `${getRangeLabel(currentDays)} chart`;
  }

  const universeReady = tickerUniverseExplicitlyChosen;
  const universeReason = universeReady ? "" : "Choose a ticker universe first";

  RANGE_PRESETS.forEach((preset) => {
    const days = preset.days;
    const button = getRangeButton(days);
    if (!button) {
      return;
    }
    const active = currentDays === days;
    if (!button.dataset.baseClass) {
      button.dataset.baseClass = button.className;
    }
    if (!button.dataset.baseTitle) {
      button.dataset.baseTitle = button.title || "";
    }
    button.className = button.dataset.baseClass;
    button.style.backgroundColor = active ? "#4f46e5" : "";
    button.style.borderColor = active ? "#818cf8" : "";
    button.style.boxShadow = active ? "0 0 0 2px rgba(165, 180, 252, 0.38)" : "";
    button.style.transform = active ? "translateY(-1px)" : "";
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.dataset.active = active ? "true" : "false";
    button.disabled = !universeReady;
    button.title = universeReady ? button.dataset.baseTitle || "" : universeReason;
  });
}

function getChartEmaCandidatePeriods(filters = screenFilters) {
  return [...new Set(getChartEmaCandidateSpecs(filters).map((spec) => spec.period))].sort((a, b) => a - b);
}

function getChartEmaCandidateSpecs(filters = screenFilters) {
  const specs = [filters.ema_slope_period_1, filters.ema_slope_period_2, filters.ema_slope_period_3].map((period) => ({ period: Math.round(Number(period)), source: "close" }));
  if (filters.ema_relationship_enabled) {
    specs.push({ period: Math.round(Number(filters.ema_relationship_fast)), source: "close" }, { period: Math.round(Number(filters.ema_relationship_slow)), source: "close" });
  }
  if (filters.price_ema_sources?.length || filters.price_ema_source) {
    (filters.price_ema_sources || [filters.price_ema_source || "close"]).forEach((source) => specs.push({ period: Math.round(Number(filters.price_ema_period)), source: String(source).toLowerCase() }));
  }
  if (filters.ema_flatten_enabled) {
    specs.push({ period: Math.round(Number(filters.ema_flatten_period)), source: "close" });
  }
  if (filters.ha_ema_volume_enabled) {
    specs.push(
      { period: Math.round(Number(filters.ha_ema_volume_ema1_period)), source: String(filters.ha_ema_volume_ema1_source || "close") },
      { period: Math.round(Number(filters.ha_ema_volume_ema2_period)), source: String(filters.ha_ema_volume_ema2_source || "close") },
    );
  }
  document.querySelectorAll('.screen-timeline-step input[id$="-period"]').forEach((node) => {
    if (!node.closest(".screen-timeline-step")?.classList.contains("hidden")) {
      specs.push({ period: Math.round(Number(node.value)), source: "close" });
    }
  });
  return [...new Map(specs.filter((spec) => Number.isFinite(spec.period) && spec.period >= 2 && spec.period <= 500 && ["open", "high", "low", "close"].includes(spec.source)).map((spec) => [`${spec.period}:${spec.source}`, spec])).values()].sort((a, b) => a.period - b.period || a.source.localeCompare(b.source));
}

function getChartEmaVisibility() {
  try {
    const parsed = JSON.parse(readStickyValue(EMA_OVERLAY_VISIBILITY_KEY, "{}") || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    return {};
  }
}

function getVisibleChartEmaPeriods(filters = screenFilters) {
  const visibility = getChartEmaVisibility();
  return getChartEmaCandidatePeriods(filters).filter((period) => visibility[String(period)] !== false);
}

function getVisibleChartEmaSpecs(filters = screenFilters) {
  const visibility = getChartEmaVisibility();
  return getChartEmaCandidateSpecs(filters).filter((spec) => visibility[`${spec.period}:${spec.source}`] !== false && visibility[String(spec.period)] !== false);
}

function renderEmaOverlayControls(filters = screenFilters) {
  const container = document.getElementById("screen-ema-overlay-controls");
  if (!container) return;
  const specs = getChartEmaCandidateSpecs(filters);
  const visibility = getChartEmaVisibility();
  container.innerHTML = '<span class="w-full text-[9px] font-bold uppercase tracking-[0.14em] text-slate-400">Chart EMA overlays</span>';
  specs.forEach((spec) => {
    const period = spec.period;
    const visibilityKey = `${period}:${spec.source}`;
    const label = document.createElement("label");
    label.className = "inline-flex items-center gap-1 rounded-full bg-white px-2 py-1 text-[10px] font-semibold text-slate-600";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = visibility[visibilityKey] !== false && visibility[String(period)] !== false;
    checkbox.className = "h-3 w-3 rounded border-slate-300 text-rose-600 focus:ring-rose-500";
    checkbox.addEventListener("change", () => {
      const next = getChartEmaVisibility();
      next[visibilityKey] = checkbox.checked;
      writeStickyValue(EMA_OVERLAY_VISIBILITY_KEY, JSON.stringify(next));
      if (currentTicker) loadChart(currentTicker);
    });
    label.appendChild(checkbox);
    const text = document.createElement("span");
    text.textContent = `EMA ${period} ${String(spec.source).charAt(0).toUpperCase()}${String(spec.source).slice(1)}`;
    label.appendChild(text);
    container.appendChild(label);
  });
}

function renderChartEmaLegend(figData, chartDiv) {
  const container = document.getElementById("chart-ema-legend");
  if (!container) return;
  container.innerHTML = "";
  const traces = (figData?.data || []).map((trace, index) => ({ trace, index }))
    .filter(({ trace }) => /^EMA\s+\d+(?:\s+(?:HA\s+)?(?:Open|High|Low|Close))?$/i.test(String(trace?.name || "")));
  if (!traces.length) return;

  const heading = document.createElement("span");
  heading.className = "mr-1 text-[10px] font-bold uppercase tracking-wide text-slate-400";
  heading.textContent = "EMA";
  container.appendChild(heading);

  traces.forEach(({ trace, index }) => {
    const label = document.createElement("label");
    label.className = "inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-600";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = trace.visible !== "legendonly" && trace.visible !== false;
    checkbox.className = "h-3 w-3 rounded border-slate-300 text-rose-600 focus:ring-rose-500";
    checkbox.addEventListener("change", () => {
      Plotly.restyle(chartDiv, { visible: checkbox.checked ? true : "legendonly" }, [index]);
      const visibility = getChartEmaVisibility();
      const match = String(trace.name || "").match(/^EMA\s+(\d+)(?:\s+(?:HA\s+)?(Open|High|Low|Close))?$/i);
      if (match) {
        const key = `${match[1]}:${String(match[2] || "Close").toLowerCase()}`;
        visibility[key] = checkbox.checked;
        writeStickyValue(EMA_OVERLAY_VISIBILITY_KEY, JSON.stringify(visibility));
      }
    });
    label.appendChild(checkbox);
    const text = document.createElement("span");
    text.textContent = String(trace.name);
    if (trace.line?.color) text.style.color = trace.line.color;
    label.appendChild(text);
    container.appendChild(label);
  });
}

function getChartTAParameters() {
  const read = (id, fallback) => {
    const value = Number(document.getElementById(id)?.value);
    return Number.isFinite(value) ? Math.round(value) : fallback;
  };
  return {
    macd_fast: read("chart-macd-fast", 12),
    macd_slow: read("chart-macd-slow", 26),
    macd_signal: read("chart-macd-signal", 9),
    rsi_period: read("chart-rsi-period", 14),
    stoch_rsi_period: read("chart-stoch-rsi-period", 14),
    stoch_rsi_k: read("chart-stoch-rsi-k", 3),
    stoch_rsi_d: read("chart-stoch-rsi-d", 3),
    supertrend_period: read("chart-supertrend-period", 10),
    supertrend_multiplier: Number(document.getElementById("chart-supertrend-multiplier")?.value || 3),
    candle_mode: document.getElementById("chart-candle-mode")?.value || "heikin_ashi",
    rsi_trigger: read("screen-rsi-cross-value", 50),
    stoch_trigger: read("screen-stoch-cross-value", 20),
  };
}

function getAppliedChartTAParameters() {
  const params = getChartTAParameters();
  return Object.fromEntries(CHART_TA_PARAMETER_KEYS.map((key) => [key, params[key]]));
}

function setChartTAParametersApplied() {
  appliedChartTAParameters = getAppliedChartTAParameters();
  updateChartTAApplyButton();
}

function updateChartTAApplyButton() {
  const button = document.getElementById("chart-ta-apply-btn");
  if (!button || !appliedChartTAParameters) {
    return;
  }
  button.disabled = JSON.stringify(getAppliedChartTAParameters()) === JSON.stringify(appliedChartTAParameters);
}

function saveChartTAParameters(params) {
  try {
    localStorage.setItem(LAST_CHART_TA_PARAMS_KEY, JSON.stringify(params));
  } catch (err) {
    // Ignore storage failures in privacy-restricted environments.
  }
}

function restoreChartTAParameters() {
  try {
    const raw = JSON.parse(localStorage.getItem(LAST_CHART_TA_PARAMS_KEY) || "null");
    if (!raw || typeof raw !== "object") {
      return;
    }
    const fields = {
      macd_fast: "chart-macd-fast",
      macd_slow: "chart-macd-slow",
      macd_signal: "chart-macd-signal",
      rsi_period: "chart-rsi-period",
      stoch_rsi_period: "chart-stoch-rsi-period",
      stoch_rsi_k: "chart-stoch-rsi-k",
      stoch_rsi_d: "chart-stoch-rsi-d",
      supertrend_period: "chart-supertrend-period",
      supertrend_multiplier: "chart-supertrend-multiplier",
      candle_mode: "chart-candle-mode",
    };
    Object.entries(fields).forEach(([key, id]) => {
      const node = document.getElementById(id);
      if (node && raw[key] !== undefined) {
        node.value = raw[key];
      }
    });
  } catch (err) {
    // Ignore malformed saved settings.
  }
}

function applyChartTAParameters() {
  saveChartTAParameters(getChartTAParameters());
  setChartTAParametersApplied();
  if (currentTicker) {
    loadChart(currentTicker);
  }
}

function scheduleChartTriggerRefresh() {
  if (!currentTicker) {
    return;
  }
  if (chartTriggerRefreshTimer) {
    clearTimeout(chartTriggerRefreshTimer);
  }
  chartTriggerRefreshTimer = setTimeout(() => {
    chartTriggerRefreshTimer = null;
    loadChart(currentTicker);
  }, 250);
}

function convertCandlesToHeikinAshi(trace) {
  if (!trace || trace.type !== "candlestick" || !Array.isArray(trace.open)) {
    return trace;
  }
  const open = [], high = [], low = [], close = [];
  trace.open.forEach((rawOpen, index) => {
    const o = Number(rawOpen), h = Number(trace.high?.[index]), l = Number(trace.low?.[index]), c = Number(trace.close?.[index]);
    if (![o, h, l, c].every(Number.isFinite)) return;
    const haClose = (o + h + l + c) / 4;
    const haOpen = index === 0 ? (o + c) / 2 : (open[index - 1] + close[index - 1]) / 2;
    open.push(haOpen);
    close.push(haClose);
    high.push(Math.max(h, haOpen, haClose));
    low.push(Math.min(l, haOpen, haClose));
  });
  return {
    ...trace,
    open, high, low, close,
    name: "Heikin Ashi",
    increasing: { line: { color: "#16a34a" }, fillcolor: "#16a34a" },
    decreasing: { line: { color: "#dc2626" }, fillcolor: "#dc2626" },
  };
}

async function loadChart(ticker, strategyOverride = "") {
  console.log("loadChart starting for", ticker);
  currentTicker = ticker;
  storeTickerSelection(ticker);
  // Set the label dynamically after fetching chart data

  const tickerSelect = document.getElementById("ticker-select");
  if (tickerSelect) {
    tickerSelect.value = ticker;
  }

  const chartDiv = document.getElementById("plotly-chart");
  chartDiv.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4"></div>
                <div id="loading-status" class="text-indigo-600 font-medium text-sm animate-pulse uppercase tracking-widest text-center">
                    Fetching live data for ${ticker}...
                </div>
            </div>
        `;


  try {
  const strategySelect = document.getElementById("strategy-select");
  const preferredStrategy = String(strategyOverride || "").trim();
  const strategyName = preferredStrategy
    || ((strategySelect && strategySelect.value) ? strategySelect.value : currentStrategy);
  if (preferredStrategy) {
    syncStrategySelections(preferredStrategy, { syncBacktestCheckboxes: false });
    currentStrategy = preferredStrategy;
  }
    const taParams = getChartTAParameters();
    const chartQuery = new URLSearchParams({ days: String(currentDays), ...taParams });
    chartQuery.set("ema_relationship_enabled", screenFilters.ema_relationship_enabled ? "true" : "false");
    chartQuery.set("ema_relationship_fast", String(screenFilters.ema_relationship_fast));
    chartQuery.set("ema_relationship_slow", String(screenFilters.ema_relationship_slow));
    chartQuery.set("supertrend_event_enabled", screenFilters.supertrend_event_enabled ? "true" : "false");
    chartQuery.set("ema_slope_period_1", String(screenFilters.ema_slope_period_1));
    chartQuery.set("ema_slope_period_2", String(screenFilters.ema_slope_period_2));
    chartQuery.set("ema_slope_period_3", String(screenFilters.ema_slope_period_3));
    chartQuery.set("ema_overlay_periods", JSON.stringify(getVisibleChartEmaPeriods(screenFilters)));
    chartQuery.set("ema_overlay_specs", JSON.stringify(getVisibleChartEmaSpecs(screenFilters)));
    if (strategyName) {
      chartQuery.set("strategy", strategyName);
    }
    const activeDsl = String(document.getElementById("screen-dsl-editor")?.value || "").trim();
    if (activeDsl) {
      chartQuery.set("dsl_content", activeDsl);
      // DSL charts derive overlays from the script, not legacy controls.
      chartQuery.set("ema_overlay_periods", "[]");
      chartQuery.set("ema_overlay_specs", "[]");
    }
    const url = `/api/chart/${ticker}?${chartQuery.toString()}`;
    console.info("loadChart request URL", url);
    const resp = await fetch(url);
    const responseData = await resp.json();
    console.info("loadChart response status", resp.status);

    if (!resp.ok) throw new Error(responseData.detail || "Server error");

    // Set the label using the returned strategy_name
    document.getElementById("active-ticker-title").textContent =
      `${ticker} - ${responseData.strategy_name || "Strategy Analysis"}`;

    let figData = null;
    if (responseData.figure) {
      try {
        figData = typeof responseData.figure === "string"
          ? JSON.parse(responseData.figure)
          : responseData.figure;
      } catch (e) {
        console.warn("Figure JSON parse failed, falling back to data/layout", e);
      }
    }
    if (!figData || !figData.data || !figData.layout) {
      figData = {
        data: responseData.data || [],
        layout: responseData.layout || {}
      };
    }

    console.info("loadChart payload summary", {
      ticker,
      traces: (figData.data || []).length,
      layoutKeys: Object.keys(figData.layout || {}).length,
    });

    if (!figData.data || figData.data.length === 0) {
      throw new Error("No chart traces returned by server.");
    }

    // Reset responsive layout
    figData.layout.autosize = true;
    figData.layout.width = undefined;
    figData.layout.height = undefined;
    if (!figData.layout.margin) {
      figData.layout.margin = { l: 60, r: 20, t: 30, b: 80 };
    }
    figData.layout.paper_bgcolor = "#ffffff";
    figData.layout.plot_bgcolor = "#ffffff";

    // A newly opened diagram should begin fitted to all of its data. The
    // backend may provide fixed ranges for its requested context window,
    // so explicitly discard those ranges before Plotly performs its first
    // layout pass. This applies to every subplot, not only the price pane.
    const chartAxisKeys = new Set(["xaxis", "yaxis"]);
    Object.keys(figData.layout).forEach((key) => {
      if (/^[xy]axis\d*$/.test(key)) chartAxisKeys.add(key);
    });
    chartAxisKeys.forEach((key) => {
      const axis = (
        figData.layout[key]
        && typeof figData.layout[key] === "object"
        && !Array.isArray(figData.layout[key])
      ) ? figData.layout[key] : {};
      delete axis.range;
      axis.autorange = true;
      figData.layout[key] = axis;
    });

    // Preserve backend axis label visibility rules (e.g., bottom-only timeline).
    // Only fill in minimal defaults when not provided.
    Object.keys(figData.layout).forEach((key) => {
      if (key.startsWith("xaxis")) {
        if (figData.layout[key].visible === undefined) {
          figData.layout[key].visible = true;
        }
      if (figData.layout[key].tickfont === undefined) {
        figData.layout[key].tickfont = {
          size: 11,
          color: "#334155",
        };
      }
      figData.layout[key].showspikes = true;
      figData.layout[key].spikemode = "across";
      figData.layout[key].spikesnap = "cursor";
      figData.layout[key].spikethickness = 1;
      figData.layout[key].spikecolor = "#64748b";
    }
  });
  figData.layout.hovermode = "x unified";
  figData.layout.hoverdistance = -1;
  figData.layout.spikedistance = -1;

    chartDiv.innerHTML = "";
    await Plotly.newPlot(chartDiv, figData.data, figData.layout, {
      responsive: true,
      displayModeBar: false,
      displaylogo: false,
      scrollZoom: true,
    });
    const autoscaleChartAxes = (extraLayout = {}) => {
      const update = { ...extraLayout };
      chartAxisKeys.forEach((key) => {
        update[`${key}.autorange`] = true;
      });
      return Plotly.relayout(chartDiv, update);
    };
    // Apply autorange once more after Plotly has created all matched
    // subplot axes. Start in pan mode so the toolbar does not present a
    // newly fitted diagram as if Zoom were already selected.
    await autoscaleChartAxes({ dragmode: "pan" });
    renderChartEmaLegend(figData, chartDiv);

    const toolsActions = document.getElementById("plotly-tools-actions");
    if (toolsActions) {
      toolsActions.innerHTML = "";

      const setActive = (mode) => {
        toolsActions.querySelectorAll(".plotly-tool-btn[data-mode]").forEach((btn) => {
          btn.classList.toggle("is-active", btn.dataset.mode === mode);
        });
      };

      const addBtn = (label, title, onClick, mode = null) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "plotly-tool-btn";
        btn.textContent = label;
        btn.title = title;
        if (mode) {
          btn.dataset.mode = mode;
        }
        btn.addEventListener("click", onClick);
        toolsActions.appendChild(btn);
        return btn;
      };

      addBtn("Pan", "Pan chart", () => {
        Plotly.relayout(chartDiv, { dragmode: "pan" });
        setActive("pan");
      }, "pan");

      addBtn("Zoom", "Box zoom", () => {
        Plotly.relayout(chartDiv, { dragmode: "zoom" });
        setActive("zoom");
      }, "zoom");

      addBtn("Autoscale", "Autoscale axes", () => {
        autoscaleChartAxes();
      });

      addBtn("Reset", "Reset axes and zoom mode", () => {
        autoscaleChartAxes({ dragmode: "zoom" });
        setActive("zoom");
      });

      addBtn("PNG", "Download chart as PNG", () => {
        Plotly.downloadImage(chartDiv, {
          format: "png",
          filename: `${ticker}_chart`,
          width: chartDiv.clientWidth || 1400,
          height: chartDiv.clientHeight || 900,
          scale: 2,
        });
      });

      setActive("pan");
    }

    console.info("loadChart render complete", ticker);
  } catch (err) {
    console.error("loadChart error:", err);
    chartDiv.innerHTML = `<div class="p-8 text-center text-red-500">${err.message}</div>`;
  }
}

function setRange(days) {
  // The diagram intentionally uses one fixed context window.
  currentDays = FIXED_CHART_WINDOW_DAYS;
  updateRangeChrome();
  if (currentTicker) loadChart(currentTicker);
}

