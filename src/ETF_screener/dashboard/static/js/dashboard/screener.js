// Dashboard screener. See README.md in static/js/dashboard for the feature map.

async function applyDsl() {
  // Extract current DSL from editor and pass it to runScreen
  const dsl = getStrategyEntryDsl();
  if (!dsl.trim()) {
    alert("Please enter strategy DSL before applying.");
    return;
  }
  toggleStrategyPanel();
  // Pass true to indicate we're using custom DSL from active editor
  runScreen(dsl);
}

// Initial Load
function createRunRequestId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `run-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function cancelScan() {
  if (scanAbortController || marketDataBackgroundRefreshPromise) {
    const screenAbortController = scanAbortController;
    const screenRequestId = scanRunId;
    const backfillAbortController = marketDataBackgroundRefreshAbortController;
    const backfillRequestId = marketDataBackgroundRefreshRequestId;
    const stopButton = document.getElementById("stop-run-btn");
    if (stopButton) {
      stopButton.disabled = true;
      stopButton.textContent = "Stopping…";
    }
    showToast(screenAbortController ? "Stopping the screener run…" : "Stopping the data fill…");
    const cancellationRequests = [];
    if (screenRequestId) {
      cancellationRequests.push(fetch("/api/jobs/screen/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: screenRequestId }),
        keepalive: true,
      }));
    }
    if (backfillRequestId) {
      cancellationRequests.push(fetch("/api/jobs/market-refresh/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: backfillRequestId }),
        keepalive: true,
      }));
    }
    screenAbortController?.abort();
    backfillAbortController?.abort();
    await Promise.allSettled(cancellationRequests);
  }
}

function syncScreenerRunButtonState(running = false) {
  const runBtn = document.getElementById("run-btn");
  const stopBtn = document.getElementById("stop-run-btn");
  const refreshingMarketData = Boolean(marketDataBackgroundRefreshPromise);
  if (!runBtn) {
    return;
  }
  runBtn.dataset.running = running ? "1" : "0";
  if (stopBtn) {
    stopBtn.classList.toggle("hidden", !running && !refreshingMarketData);
    stopBtn.disabled = !running && !refreshingMarketData;
    stopBtn.textContent = running ? "Stop Run" : "Stop Data Update";
  }
  if (running) {
    runBtn.innerHTML = `
        <svg class="w-3.5 h-3.5 mr-1 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="9" stroke-width="2" stroke-opacity="0.3"></circle>
          <path d="M21 12a9 9 0 00-9-9" stroke-width="2" stroke-linecap="round"></path>
        </svg>
        Running
      `;
    runBtn.classList.remove("bg-green-600", "hover:bg-green-500");
    runBtn.classList.add("bg-emerald-500", "cursor-wait");
    runBtn.disabled = true;
    return;
  }
  runBtn.textContent = "Run Screener";
  runBtn.classList.remove("bg-emerald-500", "cursor-wait");
  runBtn.classList.add("bg-green-600", "hover:bg-green-500");
  updateScanActionButtonsState();
}

function findContradictoryScreenDslConditions(expressions) {
  const operand = String.raw`(?:[A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?|\d+(?:\.\d+)?)`;
  const comparison = new RegExp(
    `(${operand})\\s*(GT|GTE|GE|LT|LTE|LE|EQ|NE|>=|<=|==|!=|>|<)\\s*(${operand})`,
    "gi",
  );
  const aliases = {
    GT: ">", GTE: ">=", GE: ">=", LT: "<", LTE: "<=", LE: "<=",
    EQ: "==", NE: "!=",
  };
  const inverse = { ">": "<", ">=": "<=", "<": ">", "<=": ">=", "==": "==", "!=": "!=" };
  const constraints = new Map();

  for (const expression of expressions) {
    comparison.lastIndex = 0;
    let found;
    while ((found = comparison.exec(expression)) !== null) {
      let left = found[1].toLowerCase();
      let operator = aliases[found[2].toUpperCase()] || found[2];
      let right = found[3].toLowerCase();
      if (left === right) continue;
      if (left > right) {
        [left, right] = [right, left];
        operator = inverse[operator];
      }
      const key = `${left}\u0000${right}`;
      if (!constraints.has(key)) constraints.set(key, new Set());
      constraints.get(key).add(operator);
    }
  }

  for (const [key, operators] of constraints) {
    const impossible = (
      (operators.has(">") && (operators.has("<") || operators.has("<=") || operators.has("==")))
      || (operators.has(">=") && operators.has("<"))
      || (operators.has("<") && (operators.has(">") || operators.has(">=") || operators.has("==")))
      || (operators.has("<=") && operators.has(">"))
      || (operators.has("==") && operators.has("!="))
    );
    if (impossible) {
      const [left, right] = key.split("\u0000");
      return `Contradictory conditions: '${left}' and '${right}' cannot satisfy ${[...operators].join(" and ")} at the same candle.`;
    }
  }
  return "";
}

function updateScreenDslValidation(readiness) {
  const node = document.getElementById("screen-dsl-validation");
  if (!node) return;
  node.classList.remove("hidden");
  if (readiness.ready) {
    node.className = "mt-3 rounded-lg border border-emerald-400/30 bg-emerald-950/35 px-3 py-2 text-xs font-semibold text-emerald-200";
    node.textContent = "Script checks passed. The server will validate it again before screening.";
  } else {
    node.className = "mt-3 rounded-lg border border-rose-400/40 bg-rose-950/35 px-3 py-2 text-xs font-semibold text-rose-200";
    node.textContent = `Script needs attention: ${readiness.reason}`;
  }
}

function getScreenDslReadiness(source = null) {
  const node = document.getElementById("screen-dsl-editor");
  if ((!node || !node.tagName) && (source === null || String(source || "").trim() === "")) {
    // Keep lightweight test/embedded dashboard shells usable when the
    // optional DSL editor is not rendered.
    return { ready: true, reason: "Run the control-based screener" };
  }
  const text = String(source === null ? node?.value || "" : source).trim();
  if (!text) {
    return { ready: false, reason: "Enter a screening script first" };
  }

  if (/^\s*(?:universe|strategy)\b/i.test(text)) {
    let braces = 0;
    let parentheses = 0;
    for (const char of text) {
      if (char === "{") braces += 1;
      if (char === "}") braces -= 1;
      if (char === "(") parentheses += 1;
      if (char === ")") parentheses -= 1;
      if (braces < 0 || parentheses < 0) {
        return { ready: false, reason: "Fix unmatched braces or parentheses in the DSLX program" };
      }
    }
    return braces === 0 && parentheses === 0
      ? { ready: true, reason: "Run the DSLX program" }
      : { ready: false, reason: "Fix unmatched braces or parentheses in the DSLX program" };
  }

  const lines = text.split(/\r?\n/)
    .map((line) => line.replace(/(?:#|\/\/).*$/, "").trim())
    .filter(Boolean);
  const conditionLines = [];
  let previousWasCondition = false;
  let pendingConnector = false;
  let depth = 0;

  for (const line of lines) {
    for (const char of line) {
      if (char === "(") depth += 1;
      if (char === ")") depth -= 1;
      if (depth < 0) {
        return { ready: false, reason: "Fix unmatched parentheses in the script" };
      }
    }

    if (/^(?:candle_age|days|max_days|max_signal_age_days|signal_max_days|since_days)\s*:\s*\d+$/i.test(line)
      || /^candle_age\s+(?:LTE|LE|EQ)\s+\d+$/i.test(line)
      || /^period_1d$/i.test(line)) {
      continue;
    }

    if (/^(?:AND|OR|&&|\|\|)$/i.test(line)) {
      if (!previousWasCondition || pendingConnector) {
        return { ready: false, reason: "A logical operator must connect two conditions" };
      }
      pendingConnector = true;
      previousWasCondition = false;
      continue;
    }

    const section = line.match(/^(TRIGGER|FILTER|ENTRY|EXIT)\s*:\s*(.*)$/i);
    const expression = section ? section[2].trim() : line;
    if (!expression || /^(?:AND|OR|&&|\|\|)$/i.test(expression)) {
      return { ready: false, reason: "Add a condition to the script" };
    }
    if (/^(?:&&|\|\|)|(?:&&|\|\|)\s*$/i.test(expression)) {
      return { ready: false, reason: "A logical operator must connect two conditions" };
    }
    if (/\b(?:GT|GTE|LT|LTE|GE|LE|EQ|NE)\s*$/i.test(expression)
      || /^(?:GT|GTE|LT|LTE|GE|LE|EQ|NE)\b/i.test(expression)) {
      return { ready: false, reason: "Complete the comparison in the script" };
    }
    conditionLines.push(expression);
    previousWasCondition = true;
    pendingConnector = false;
  }

  if (depth !== 0) {
    return { ready: false, reason: "Fix unmatched parentheses in the script" };
  }
  if (!conditionLines.length) {
    return { ready: false, reason: "Add at least one screening condition" };
  }
  if (pendingConnector) {
    return { ready: false, reason: "Finish the condition after AND/OR" };
  }
  const contradiction = findContradictoryScreenDslConditions(conditionLines);
  if (contradiction) {
    return { ready: false, reason: contradiction };
  }
  return { ready: true, reason: "Run the screener" };
}

function updateScanActionButtonsState() {
  const dslReadiness = getScreenDslReadiness();
  const dslText = String(document.getElementById("screen-dsl-editor")?.value || "");
  const hasConcreteDslxSource = /^\s*source\s+universe\.(?!selected\b)[A-Za-z_][A-Za-z0-9_]*\s*$/im.test(dslText);
  updateScreenDslValidation(dslReadiness);
  const readiness = !tickerUniverseExplicitlyChosen && !hasConcreteDslxSource
    ? { ready: false, reason: "Choose a ticker universe first" }
    : dslReadiness;
  const scanBtn = document.getElementById("scan-btn");
  const runBtn = document.getElementById("run-btn");

  if (scanBtn && scanBtn.dataset.running !== "1") {
    scanBtn.disabled = !readiness.ready;
    scanBtn.title = readiness.reason;
  }

  if (runBtn && runBtn.dataset.running !== "1") {
    runBtn.disabled = !readiness.ready;
    runBtn.title = readiness.reason;
  }
}

function resetScanUI() {
  const spinner = document.getElementById("loading-spinner");
  const list = document.getElementById("ticker-list");

  stopJobProgressPolling();
  stopScreenEventPolling();
  if (spinner) spinner.classList.add("hidden");
  setNavScanProgress({
    show: false,
    contextLabel: "Context",
    contextText: "0%",
    contextPct: 0,
    contextWorking: false,
    globalLabel: "Global",
    globalText: "0%",
    globalPct: 0,
    globalWorking: false,
  });

  if (list) list.style.opacity = "1.0";
  scanAbortController = null;
  scanRunId = null;
  syncScreenerRunButtonState(false);
  updateScanActionButtonsState();
}

async function runScreen(customDsl = null) {
  const typedDsl = document.getElementById("screen-dsl-editor")?.value.trim() || "";
  customDsl = String(customDsl || typedDsl).trim() || null;
  const list = document.getElementById("ticker-list");
  const spinner = document.getElementById("loading-spinner");
  const scanBtn = document.getElementById("scan-btn");
  const runBtn = document.getElementById("run-btn");
  const errorSection = document.getElementById("error-section");
  const errorList = document.getElementById("error-list");

  const requestedDsl = String(customDsl || typedDsl).trim();
  const hasConcreteDslxSource = /^\s*source\s+universe\.(?!selected\b)[A-Za-z_][A-Za-z0-9_]*\s*$/im.test(requestedDsl);
  if (!tickerUniverseExplicitlyChosen && !hasConcreteDslxSource) {
    resetScanUI();
    return;
  }

  if (normalizeScanScope(tickerScanScope) === "list" && getScopeTickers(tickerScanScope).length === 0) {
    await openListEditorModal();
    return;
  }

  const dslReadiness = getScreenDslReadiness(customDsl === null ? typedDsl : customDsl);
  if (!dslReadiness.ready) {
    showToast(dslReadiness.reason, true);
    updateScanActionButtonsState();
    return;
  }

  if (!customDsl) {
    syncScreenFilterStateFromDom();
  }
  if (!customDsl && validateHaEmaVolumeConditions(screenFilters.ha_ema_volume_conditions).length) {
    showToast("Fix the contradictory HA OHLC conditions before scanning.", true);
    return;
  }

  // Set up abortion
  const abortController = new AbortController();
  scanAbortController = abortController;
  scanRunId = createRunRequestId();

  if (spinner) spinner.classList.remove("hidden");
  setNavScanProgress({
    show: true,
    contextLabel: "Screen",
    contextText: "Starting...",
    contextPct: 0,
    contextWorking: false,
  });
  startJobProgressPolling("screen", "Global");
  setNavScanProgress({
    show: true,
    globalLabel: "Global",
    globalText: "Preparing...",
    globalPct: 0,
    globalWorking: true,
  });

  if (scanBtn) {
    scanBtn.textContent = "Scanning...";
    scanBtn.classList.add("bg-indigo-400"); // De-emphasize while running
    scanBtn.classList.remove("bg-indigo-600");
    scanBtn.disabled = true;
  }

  syncScreenerRunButtonState(true);

  if (list) list.style.opacity = "0.5";

  try {
    // Screen the local cache immediately. Market refresh is intentionally
    // separate so a large, cautiously throttled Yahoo update never blocks
    // the first visible matches or the rest of the dashboard.
    await ensureGuiMarketBackbone({
      allowRefresh: false,
      refreshStaleInBackground: true,
      requestId: scanRunId,
      signal: abortController.signal,
    });
    startJobProgressPolling("screen", "Global");
    setNavScanProgress({
      show: true,
      contextLabel: "Screen",
      contextText: "Queued...",
      contextPct: 1,
      contextWorking: true,
      globalLabel: "Global",
      globalText: "Waiting...",
      globalPct: 0,
      globalWorking: true,
    });
    let url = "/api/screen";
    const universeParams = getUniverseFilterParams();
    universeParams.set("request_id", scanRunId);
    if (!customDsl) {
      const screenParams = getScreenDisqualifierParams();
      const controlParams = buildScreenFilterParams();
      screenParams.forEach((value, key) => {
        universeParams.set(key, value);
      });
      controlParams.forEach((value, key) => {
        universeParams.set(key, value);
      });
    }
    const screenQuery = universeParams.toString();
    if (screenQuery) {
      url += `?${screenQuery}`;
    }
    if (customDsl) {
      url += `${screenQuery ? "&" : "?"}dsl_content=${encodeURIComponent(customDsl)}`;
      syncStrategySelections("");
      currentStrategy = "";
    } else {
      currentStrategy = "";
    }
    const activePresetName = String(document.getElementById("screen-preset-select")?.value || "").trim();
    setLastScreenMatches([], {
      strategy_name: currentStrategy || (customDsl ? "Editor Draft" : ""),
      preset_name: activePresetName,
      scan_scope: normalizeScanScope(tickerScanScope),
      ticker_list: universeParams.get("ticker_list") || "",
      disqualifiers: screenDisqualifiers,
    });
    lastScreenCandidatePool = [];
    lastScreenScanFilters = null;
    console.log("Screen scan starting with URL:", url);
    console.log("Current strategy:", currentStrategy);

    if (list) {
      list.innerHTML = '<div class="text-sm text-slate-400 italic p-4 text-center">Scanning… matches will appear here as they are found.</div>';
    }
    startScreenEventPolling(scanRunId, (payload) => {
      const phase = String(payload.phase || "screen");
      const phaseLabels = {
        loading: "Loading cache",
        evaluating: "Evaluating strategy",
        screen: "Screen",
      };
      const pct = Number(payload.phase_pct ?? payload.pct ?? 0);
      setNavScanProgress({
        contextLabel: phaseLabels[phase] || phase,
        contextText: String(payload.detail || `${Math.round(pct)}%`),
        contextPct: Number.isFinite(pct) ? pct : 0,
        contextWorking: true,
      });
    });

    let resp = null;
    let rawData = null;
    try {
      resp = await fetch(url, { signal: abortController.signal, cache: "no-store" });
      console.log("Fetch response status:", resp.status, "URL:", url);

      rawData = await resp.json();
      if (!resp.ok) {
        throw new Error(rawData.detail || "Screen request failed");
      }
      console.log("JSON parsed successfully. Data keys:", Object.keys(rawData));

      // Complete the bar
      setNavScanProgress({
        contextLabel: "Screen",
        contextText: "100%",
        contextPct: 100,
        contextWorking: false,
        globalLabel: "Global",
        globalText: "100%",
        globalPct: 100,
        globalWorking: false,
      });

      // Small delay to let user see 100%
      await new Promise(r => setTimeout(r, 500));
      resetScanUI();

      // Handle new response format
      const hasFormat = rawData.matches !== undefined;
      const matches = hasFormat ? rawData.matches : rawData;
      const errors = hasFormat ? rawData.errors : [];
      console.log("Data format check - hasFormat:", hasFormat, "matches count:", matches?.length, "errors count:", errors?.length);

      if (!customDsl) {
        saveLastCompletedStrategy(currentStrategy);
      }

      if (!Array.isArray(matches)) {
        console.error("ERROR: matches is not an array!", typeof matches, matches);
        throw new Error("Expected matches to be an array, got " + typeof matches);
      }

      list.innerHTML = "";
      document.getElementById("match-count").textContent = matches.length;
      console.log("List cleared, match count updated to:", matches.length);
      setLastScreenMatches(matches, {
        strategy_name: rawData.strategy_name || currentStrategy || (customDsl ? "Editor Draft" : "Custom Controls"),
        preset_name: rawData.preset_name || activePresetName,
        scan_scope: normalizeScanScope(tickerScanScope),
        ticker_list: universeParams.get("ticker_list") || "",
        disqualifiers: screenDisqualifiers,
      });
      lastScreenCandidatePool = Array.isArray(rawData.candidate_pool)
        ? rawData.candidate_pool.slice()
        : [];
      lastScreenScanFilters = normalizeScreenFiltersClient(rawData.filters || screenFilters);

      if (screenAutoExportEnabled && matches.length > 0) {
        try {
          await exportTopMatches();
        } catch (autoExportErr) {
          showToast(`Automatic CSV download failed: ${autoExportErr.message || autoExportErr}`, true);
        }
      }

      // Update ticker dropdown options based on screen results.
      if (matches.length > 0) {
        setTickerSelectUniverse(matches.map((item) => ({
          ticker: item.ticker,
          label: item.name || item.ticker,
        })));
        renderTickerSelectOptions({ preserveSelection: true });
      }

      // Display errors if any
      if (errors && errors.length > 0) {
        errorSection.classList.remove("hidden");
        document.getElementById("error-count").textContent =
          rawData.total_errors || errors.length;
        errorList.innerHTML = errors
          .map(
            (err) => `
                    <div class="mb-1 border-b border-slate-50 pb-1">
                        <span class="font-bold text-slate-700">${err.ticker}</span>: 
                        <span class="text-red-400 capitalize">${err.error}</span>
                    </div>
                `,
          )
          .join("");
      } else {
        errorSection.classList.add("hidden");
      }

      if (matches.length === 0) {
        list.innerHTML =
          '<div class="text-sm text-slate-400 italic p-4 text-center">No matching tickers found for the current screener controls.</div>';
      }

      // Keep the full response in lastScreenMatches for export, but do
      // not create thousands of DOM nodes at once. Large universes can
      // otherwise freeze the browser before the result panel becomes
      // usable.
      const maxVisibleMatches = 200;
      const visibleMatches = matches.slice(0, maxVisibleMatches);
      if (matches.length > maxVisibleMatches) {
        const notice = document.createElement("div");
        notice.className = "mb-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs text-indigo-700";
        notice.textContent = `Showing the first ${maxVisibleMatches} of ${matches.length} matches. Export CSV includes all matches.`;
        list.appendChild(notice);
      }

      visibleMatches.forEach((item, idx) => {
        try {
          list.appendChild(createScreenMatchCard(item, idx));
          console.log(`Card ${idx} added for ${item.ticker}`);
        } catch (cardErr) {
          console.error(`Error processing card at index ${idx}:`, cardErr);
          console.error("Item data:", item);
        }
      });
      console.log("All cards processed successfully");
    } finally {
      // The real backend and event-stream progress own both bars.
    }
  } catch (err) {
    if (err && (err.name === "AbortError" || abortController.signal.aborted)) {
      resetScanUI();
      showToast("Screener run stopped.");
      return;
    }
    const errMsg = err instanceof Error ? err.message : String(err);
    const errStack = err instanceof Error ? err.stack : "No stack trace";
    console.error("=== SCREEN SCAN ERROR ===");
    console.error("Message:", errMsg);
    console.error("Stack:", errStack);
    console.error("Full Error Object:", err);
    if (list) {
      list.innerHTML =
        `<div class="text-xs text-red-500 p-2">Screen error: ${errMsg}<br/><span class="text-[9px] text-slate-500">Check console for details.</span></div>`;
    }
    setNavScanProgress({
      globalLabel: "Global",
      globalText: "FAILED",
      globalPct: 100,
      globalWorking: false,
    });
    setLastScreenMatches([], {
      strategy_name: currentStrategy || (customDsl ? "Editor Draft" : ""),
      preset_name: String(document.getElementById("screen-preset-select")?.value || "").trim(),
      scan_scope: normalizeScanScope(tickerScanScope),
      ticker_list: getUniverseFilterParams().get("ticker_list") || "",
      disqualifiers: screenDisqualifiers,
    });
    resetScanUI();
  }
}

