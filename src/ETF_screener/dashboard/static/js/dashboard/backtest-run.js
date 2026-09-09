// Dashboard backtest-run. See README.md in static/js/dashboard for the feature map.

function setBacktestSourceMode(mode) {
  backtestSourceMode = mode === "editor" ? "editor" : "saved";
  const savedBtn = document.getElementById("bt-source-saved");
  const editorBtn = document.getElementById("bt-source-editor");
  if (savedBtn && editorBtn) {
    savedBtn.className = `rounded-md px-3 py-2 text-sm font-bold ${backtestSourceMode === 'saved' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`;
    editorBtn.className = `rounded-md px-3 py-2 text-sm font-bold ${backtestSourceMode === 'editor' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`;
  }
  syncBacktestRaceLanesToCurrentSelection();
  updateBacktestRunButtonState();
}

function getBacktestSignalDays() {
  const signalDaysInput = document.getElementById("backtest-since-days");
  if (!signalDaysInput) {
    return null;
  }
  const raw = String(signalDaysInput.value || "").trim();
  if (!raw) {
    return null;
  }
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    return null;
  }
  return Math.floor(value);
}

function getBacktestSelectedStrategies() {
  return Array.from(document.querySelectorAll(".backtest-strategy-checkbox"))
    .filter((input) => Boolean(input.checked))
    .map((input) => input.value)
    .filter(Boolean);
}

function syncBacktestStrategyCheckboxChrome() {
  document.querySelectorAll(".backtest-strategy-checkbox").forEach((input) => {
    const row = input.closest ? input.closest("label") : null;
    if (!row) {
      return;
    }
    row.classList.toggle("bg-emerald-50", Boolean(input.checked));
    row.classList.toggle("text-emerald-900", Boolean(input.checked));
    row.style.backgroundColor = input.checked ? "#ecfdf5" : "";
    row.style.fontWeight = input.checked ? "700" : "";
  });
}

function updateBacktestStrategyCount() {
  const countNode = document.getElementById("backtest-selected-count");
  if (!countNode) {
    return;
  }
  const selectedCount = getBacktestSelectedStrategies().length;
  countNode.textContent = `${selectedCount} selected`;
}

function getBacktestRunReadiness() {
  if (!tickerUniverseExplicitlyChosen) {
    return { ready: false, reason: "Choose a ticker universe first" };
  }

  if (backtestSourceMode === "editor") {
    return getActiveEditorDsl()
      ? { ready: true, reason: "Evaluate editor draft" }
      : { ready: false, reason: "Editor Draft needs DSL content" };
  }

  if (getBacktestSelectedStrategies().length === 0) {
    return { ready: false, reason: "Select at least one saved strategy" };
  }

  const universeParams = getUniverseFilterParams();
  const scope = universeParams.get("scan_scope");
  if (scope === "list" && !universeParams.get("ticker_list")) {
    return { ready: false, reason: "Choose tickers for the selected list universe" };
  }

  return { ready: true, reason: "Evaluate selected strategies" };
}

function updateBacktestRunButtonState() {
  const runBtn = document.getElementById("backtest-run-btn");
  if (!runBtn || runBtn.dataset.running === "1") {
    return;
  }

  const readiness = getBacktestRunReadiness();
  runBtn.disabled = !readiness.ready;
  runBtn.title = readiness.reason;
  runBtn.className = readiness.ready
    ? "bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold py-2 px-4 rounded-lg border border-emerald-500/60 transition-all"
    : "bg-slate-300 text-slate-500 text-sm font-bold py-2 px-4 rounded-lg border border-slate-300 transition-all cursor-not-allowed";
  updateBacktestRaceButtons();
}

function selectBacktestStrategies(mode) {
  const selectAll = mode === "all";
  document.querySelectorAll(".backtest-strategy-checkbox").forEach((input) => {
    input.checked = selectAll;
  });
  syncBacktestStrategyCheckboxChrome();
  handleBacktestStrategyChooserChange();
}

function handleBacktestStrategyChooserChange() {
  syncBacktestStrategyCheckboxChrome();
  const selected = getBacktestSelectedStrategies();
  updateBacktestStrategyCount();
  const primary = selected.length === 1 ? selected[0] : "";
  if (primary) {
    updateEditorContent(primary);
  } else {
    getStrategySelects().forEach((select) => {
      select.value = "";
    });
    currentStrategy = "";
  }
  syncBacktestRaceLanesToCurrentSelection();
  updateBacktestRunButtonState();
}

function bindBacktestStrategyChooserControls() {
  const allBtn = document.getElementById("backtest-select-all-btn");
  const noneBtn = document.getElementById("backtest-select-none-btn");
  if (allBtn && allBtn.dataset.bound !== "1") {
    allBtn.dataset.bound = "1";
    allBtn.addEventListener("click", () => selectBacktestStrategies("all"));
  }
  if (noneBtn && noneBtn.dataset.bound !== "1") {
    noneBtn.dataset.bound = "1";
    noneBtn.addEventListener("click", () => selectBacktestStrategies("none"));
  }
  document.querySelectorAll(".backtest-strategy-checkbox").forEach((input) => {
    if (input.dataset.bound === "1") {
      return;
    }
    input.dataset.bound = "1";
    input.addEventListener("change", handleBacktestStrategyChooserChange);
  });
}

async function loadBacktestMetrics({ restartRace = false } = {}) {
  const strategySelect = document.getElementById("strategy-select");
  const strategyName = strategySelect && strategySelect.value ? strategySelect.value : "";
  const selectedStrategies = getBacktestSelectedStrategies();
  const effectiveStrategies = selectedStrategies.length > 0 ? selectedStrategies : (strategyName ? [strategyName] : []);
  const activeSavedStrategy = effectiveStrategies[0] || "";
  const editorDsl = getActiveEditorDsl();
  const runBtn = document.getElementById("backtest-run-btn");
  const content = document.getElementById("backtest-content");
  const signalDays = getBacktestSignalDays();
  const targetReturnInput = document.getElementById("bt-target-return-pct");
  const targetHorizonInput = document.getElementById("bt-target-horizon-days");
  const targetReturnPct = Number(targetReturnInput?.value ?? 3);
  const targetHorizonDays = Number(targetHorizonInput?.value ?? 10);
  if (!(targetReturnPct > 0) || !(targetHorizonDays >= 1)) {
    setBacktestEmptyState("Set a positive profit target and at least one trading day.");
    return;
  }

  if (backtestSourceMode === "saved" && !activeSavedStrategy) {
    setBacktestEmptyState("Select a saved strategy first, then open Backtester to score it.");
    return;
  }
  if (!tickerUniverseExplicitlyChosen) {
    setBacktestEmptyState("Choose a ticker universe first before running Backtester.");
    return;
  }
  const universeParams = getUniverseFilterParams();
  const chosenScope = universeParams.get("scan_scope");
  if (chosenScope === "list" && !universeParams.get("ticker_list")) {
    await openListEditorModal();
    setBacktestEmptyState("Choose some tickers for the saved list before running Backtester.");
    return;
  }

  setNavScanProgress({
    show: true,
    contextLabel: "Screen",
    contextText: "Backtest",
    contextPct: 0,
    contextWorking: false,
  });
  if (backtestRaceAbortController) {
    backtestRaceAbortController.abort();
  }
  backtestRaceAbortController = typeof AbortController !== "undefined"
    ? new AbortController()
    : null;
  backtestProgressStartedAt = Date.now();
  setNavScanProgress({
    show: true,
    globalLabel: "Global",
    globalText: "Preparing...",
    globalPct: 0,
    globalWorking: true,
  });
  setBacktestProgress({
    show: true,
    detail: "Preparing backtest...",
    contextLabel: "Request",
    contextText: "0%",
    contextPct: 0,
    contextWorking: false,
    globalLabel: "Backend",
    globalText: "Preparing...",
    globalPct: 0,
    globalWorking: true,
  });

  let btProgressInterval = null;

  const runLabel = backtestSourceMode === "editor"
    ? "Editor Draft"
    : `${effectiveStrategies.length} saved strateg${effectiveStrategies.length === 1 ? "y" : "ies"}`;
  prepareBacktestLiveResults(`Evaluating ${runLabel}...`);
  const raceSignature = buildBacktestRaceSignature({
    sourceMode: backtestSourceMode,
    strategyName: backtestSourceMode === "editor" ? (strategyName || "Editor Draft") : (effectiveStrategies[0] || ""),
    strategies: effectiveStrategies,
    signalDays,
    universeQuery: universeParams.toString(),
  });
  const cachedRace = restartRace ? null : backtestRaceCache.get(raceSignature);
  const seededLanes = cachedRace && Array.isArray(cachedRace.lanes)
    ? cachedRace.lanes.map((lane, index) => ({
      ...lane,
      index: index + 1,
      status: "queued",
      progress_pct: 0,
      visual_progress_pct: 0,
      detail: "Queued",
    }))
    : [];
  seedBacktestRaceState({
    signature: raceSignature,
    strategies: effectiveStrategies.length > 0 ? effectiveStrategies : [strategyName || "Editor Draft"],
    lanes: seededLanes,
    targetProgress: cachedRace ? cachedRace.targetProgress || 0 : 0,
    displayProgress: 0,
    status: "running",
    activeStrategy: effectiveStrategies[0] || strategyName || "Editor Draft",
    detail: restartRace ? "Restarting from the beginning..." : "Queued on backend...",
  });
  startBacktestRacePlayback({ autoplay: true });
  runBtn.disabled = true;
  runBtn.textContent = "Evaluating...";
  runBtn.dataset.running = "1";

  try {
    // A scan must not silently use a stale market universe. The first
    // scan for a stale scope tops up that scope; later scans reuse it.
    await ensureGuiMarketBackbone({ allowRefresh: true });
    setNavScanProgress({
      show: true,
      contextLabel: "Backtest",
      contextText: "Queued...",
      contextPct: 1,
      contextWorking: true,
      globalLabel: "Global",
      globalText: "Waiting...",
      globalPct: 0,
      globalWorking: true,
    });
    setBacktestProgress({
      show: true,
      detail: "Queued on backend...",
      contextLabel: "Request",
      contextText: "Queued...",
      contextPct: 1,
      contextWorking: true,
      globalLabel: "Backend",
      globalText: "Waiting...",
      globalPct: 0,
      globalWorking: true,
    });
    let url = backtestSourceMode === "editor"
      ? `/api/backtest?limit=1000`
      : `/api/backtest/matrix?limit=1000`;
    const universeQuery = universeParams.toString();
    if (universeQuery) {
      url += `&${universeQuery}`;
    }
    if (signalDays !== null) {
      url += `&signal_days=${encodeURIComponent(String(signalDays))}`;
    }
    url += `&target_return_pct=${encodeURIComponent(String(targetReturnPct))}`;
    url += `&target_horizon_days=${encodeURIComponent(String(Math.floor(targetHorizonDays)))}`;
    if (backtestSourceMode === "editor") {
      url += `&strategy=${encodeURIComponent(strategyName || 'Editor Draft')}`;
      url += `&dsl_content=${encodeURIComponent(editorDsl)}`;
    } else {
      const strategyCount = document.querySelectorAll(".backtest-strategy-checkbox").length;
      if (effectiveStrategies.length === strategyCount && strategyCount > 0) {
        url += `&all_strategies=true`;
      } else {
        url += `&strategies=${encodeURIComponent(effectiveStrategies.join(","))}`;
      }
    }
    const requestStartedAt = Date.now();
    backtestProgressStartedAt = requestStartedAt;
    const responsePromise = fetch(url, backtestRaceAbortController ? { signal: backtestRaceAbortController.signal } : undefined);
    startJobProgressPolling("backtest", "Global");
    const resp = await responsePromise;
    let data = {};
    if (typeof resp.text === "function") {
      const responseText = await resp.text();
      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch (_parseError) {
        if (!resp.ok) {
          throw new Error(responseText || "Backtest request failed");
        }
        throw new Error("Backtest returned an invalid response");
      }
    } else if (typeof resp.json === "function") {
      data = await resp.json();
    }
    if (!resp.ok) {
      throw new Error(data.detail || "Backtest request failed");
    }

    document.getElementById("bt-strategy").textContent =
      data.source_type === "saved_matrix"
        ? `${Number(data.summary?.strategy_count || effectiveStrategies.length || 0)} strategies`
        : `${data.strategy_name || strategyName || "Editor Draft"} (${data.source_type === "editor" ? "Editor Draft" : "Saved Strategy"})`;
    document.getElementById("bt-count").textContent = String(data.summary?.count || 0);
    document.getElementById("bt-best-quality").textContent = Number(data.summary?.best_quality || 0).toFixed(2);
    document.getElementById("bt-avg-return").textContent = `${Number(data.summary?.avg_return || 0).toFixed(2)}%`;
    const medianReturnNode = document.getElementById("bt-median-return");
    if (medianReturnNode) {
      medianReturnNode.textContent = `${Number(data.summary?.median_return || 0).toFixed(2)}%`;
    }
    const medianDrawdownNode = document.getElementById("bt-median-drawdown");
    if (medianDrawdownNode) {
      medianDrawdownNode.textContent = `${Number(data.summary?.median_max_dd || 0).toFixed(2)}%`;
    }
    document.getElementById("bt-avg-sharpe").textContent = Number(data.summary?.avg_sharpe || 0).toFixed(2);
    const targetLabel = document.getElementById("bt-target-hit-label");
    const targetRate = document.getElementById("bt-target-hit-rate");
    if (targetLabel) targetLabel.textContent = `${targetReturnPct.toFixed(1)}% in ${Math.floor(targetHorizonDays)}d`;
    if (targetRate) {
      const rate = Number(data.summary?.target_hit_rate_pct);
      const entries = Number(data.summary?.target_entries || 0);
      targetRate.textContent = Number.isFinite(rate) && entries > 0 ? `${rate.toFixed(1)}%` : "—";
      targetRate.title = `${Number(data.summary?.target_hits || 0)} of ${entries} eligible entries reached the target`;
    }
    setBacktestStructureData({
      summaries: data.strategy_summaries,
      strategyProfile: data.strategy_profile,
      axisCatalog: data.strategy_axis_catalog,
      strategyName: data.strategy_name || strategyName || "Editor Draft",
    });

    if (data.race || Array.isArray(data.strategy_summaries)) {
      updateBacktestRaceFromSnapshot({
        backtest_race: data.race || {
          selected_strategies: data.strategies || effectiveStrategies,
          lanes: data.strategy_summaries || [],
          pct: 100,
          phase: "done",
          detail: `Finished ${Number(data.summary?.count || 0)} rows scored.`,
          active_strategy: effectiveStrategies[effectiveStrategies.length - 1] || "",
        },
      });
      backtestRaceCache.set(raceSignature, {
        ...backtestRaceState,
        lanes: Array.isArray(backtestRaceState?.lanes)
          ? backtestRaceState.lanes.map((lane) => ({ ...lane }))
          : [],
      });
    }

    const rows = Array.isArray(data.rows) ? data.rows : [];
    if (rows.length === 0) {
      const body = document.getElementById("backtest-table-body");
      if (body) {
        body.innerHTML = "";
      }
      if (window.Plotly) {
        const scatterChartDiv = document.getElementById("backtest-chart");
        if (scatterChartDiv) {
          Plotly.purge(scatterChartDiv);
        }
      }
      if (backtestMatrixRows.length === 0 && backtestStrategySummaries.length === 0) {
        setBacktestEmptyState(`No scored results were returned for ${data.strategy_name || strategyName || 'Editor Draft'}.`);
      } else {
        document.getElementById("backtest-empty").classList.add("hidden");
        content.classList.remove("hidden");
      }
      setBacktestProgress({
        show: true,
        detail: "Finished, but no scored rows were returned.",
        contextLabel: "Request",
        contextText: "100%",
        contextPct: 100,
        contextWorking: false,
        globalLabel: "Backend",
        globalText: "100%",
        globalPct: 100,
        globalWorking: false,
      });
      return;
    }

    populateBacktestAxisControls(data.metrics || backtestDefaultMetrics());
    mergeBacktestScatterRows(rows, { render: false });
    renderBacktestScatter();
    renderBacktestStructureRadar();
    renderBacktestBehaviorRadar();

    document.getElementById("backtest-empty").classList.add("hidden");
    content.classList.remove("hidden");
    if (btProgressInterval) clearInterval(btProgressInterval);
    btProgressInterval = null;
    setNavScanProgress({
      contextLabel: "Backtest",
      contextText: "100%",
      contextPct: 100,
      contextWorking: false,
      globalLabel: "Global",
      globalText: "100%",
      globalPct: 100,
      globalWorking: false,
    });
    setBacktestProgress({
      show: true,
      detail: `Finished ${rows.length} plotted rows.`,
      contextLabel: "Request",
      contextText: "100%",
      contextPct: 100,
      contextWorking: false,
      globalLabel: "Backend",
      globalText: "100%",
      globalPct: 100,
      globalWorking: false,
    });
    await new Promise((resolve) => setTimeout(resolve, 300));
  } catch (err) {
    if (err && err.name === "AbortError") {
      setBacktestEmptyState("Backtest stopped.");
      setNavScanProgress({
        contextLabel: "Backtest",
        contextText: "STOPPED",
        contextPct: 0,
        contextWorking: false,
        globalLabel: "Global",
        globalText: "STOPPED",
        globalPct: 0,
        globalWorking: false,
      });
      setBacktestProgress({
        show: true,
        detail: "Stopped by user.",
        contextLabel: "Request",
        contextText: "STOPPED",
        contextPct: 0,
        contextWorking: false,
        globalLabel: "Backend",
        globalText: "STOPPED",
        globalPct: 0,
        globalWorking: false,
      });
      return;
    }
    if (btProgressInterval) clearInterval(btProgressInterval);
    btProgressInterval = null;
    setBacktestEmptyState(`Backtest error: ${err.message || err}`);
    setNavScanProgress({
      contextLabel: "Backtest",
      contextText: "FAILED",
      contextPct: 100,
      contextWorking: false,
      globalLabel: "Global",
      globalText: "FAILED",
      globalPct: 100,
      globalWorking: false,
    });
    setBacktestProgress({
      show: true,
      detail: `Failed: ${err.message || err}`,
      contextLabel: "Request",
      contextText: "FAILED",
      contextPct: 100,
      contextWorking: false,
      globalLabel: "Backend",
      globalText: "FAILED",
      globalPct: 100,
      globalWorking: false,
    });
    await new Promise((resolve) => setTimeout(resolve, 250));
  } finally {
    if (btProgressInterval) clearInterval(btProgressInterval);
    btProgressInterval = null;
    stopJobProgressPolling();
    backtestRaceAbortController = null;
    resetScanUI();
    delete runBtn.dataset.running;
    runBtn.textContent = "Evaluate Selected";
    updateBacktestRunButtonState();
  }
}
