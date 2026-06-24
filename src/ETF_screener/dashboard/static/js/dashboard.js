    let backtestSourceMode = "saved";
    let shortlistLoaded = false;
    let shortlistRows = [];
    let shortlistFilter = "All";
    let queryCatalog = null;
    let queryRows = [];
    let queryColumns = [];
    let queryLoaded = false;
    let queryProgressTimers = [];
    let marketDataAutoRefreshAttempted = false;
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
    let listBuilderExchange = "all";
    let listBuilderSearch = "";
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
    let currentDays = 365 * 2;
    let screenDisqualifiers = {
      exclude_overbought: false,
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
    const LAST_BACKTEST_RACE_KEY = "etf-discovery:last-backtest-race";
    const LAST_BACKTEST_RACE_FUEL_KEY = "etf-discovery:last-backtest-race-fuel";
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
    function getDashboardTabs() {
      return ["screener", "shortlist", "query", "backtest"]
        .map((name) => document.getElementById(`tab-${name}`))
        .filter(Boolean);
    }

    function normalizeDashboardTab(value) {
      const cleaned = String(value || "screener").trim().toLowerCase();
      return ["screener", "shortlist", "query", "backtest"].includes(cleaned) ? cleaned : "screener";
    }

    function readStickyValue(key, fallback = "") {
      try {
        const raw = localStorage.getItem(key);
        return raw === null || raw === undefined ? fallback : String(raw);
      } catch (err) {
        return fallback;
      }
    }

    function hasStickyValue(key) {
      try {
        const raw = localStorage.getItem(key);
        return raw !== null && raw !== undefined && String(raw).trim() !== "";
      } catch (err) {
        return false;
      }
    }

    function writeStickyValue(key, value) {
      try {
        localStorage.setItem(key, String(value ?? ""));
      } catch (err) {
        // Ignore storage failures in restricted environments.
      }
    }

    function getQueryDataset() {
      const node = document.getElementById("query-dataset");
      return String(node?.value || "signal_scan").trim().toLowerCase();
    }

    function getQueryDatasetConfig(dataset = getQueryDataset()) {
      if (!queryCatalog || typeof queryCatalog !== "object") {
        return {};
      }
      const config = queryCatalog?.[dataset];
      return config && typeof config === "object" ? config : {};
    }

    function populateQueryTickerOptions(tickers = []) {
      const select = document.getElementById("query-ticker");
      if (!select) {
        return;
      }
      const currentValue = String(select.value || "").trim().toUpperCase();
      const options = Array.from(new Set((Array.isArray(tickers) ? tickers : [])
        .map((item) => String(item || "").trim().toUpperCase())
        .filter(Boolean)));
      select.innerHTML = '<option value="">Select ticker...</option>';
      options.forEach((ticker) => {
        const option = document.createElement("option");
        option.value = ticker;
        option.textContent = ticker;
        select.appendChild(option);
      });
      if (currentValue && options.includes(currentValue)) {
        select.value = currentValue;
      } else if (!currentValue && options.length) {
        select.value = options[0];
      }
    }

    function getQuerySignalConfig(signal = getQueryInputValue("query-signal", "trend_forming")) {
      const signalEntries = Array.isArray(queryCatalog?.signal_scan?.signals)
        ? queryCatalog.signal_scan.signals
        : [];
      return signalEntries.find((entry) => String(entry?.key || "") === String(signal || "")) || null;
    }

    async function loadQueryCatalog(force = false) {
      if (queryLoaded && !force) {
        return queryCatalog;
      }
      const resp = await fetch("/api/query/catalog", { cache: "no-store" });
      if (!resp.ok) {
        throw new Error("Could not load query catalog");
      }
      queryCatalog = await resp.json();
      populateQueryTickerOptions(queryCatalog?.tickers || []);
      queryLoaded = true;
      updateQueryControls();
      return queryCatalog;
    }

    function getQueryInputValue(id, fallback = "") {
      const node = document.getElementById(id);
      return node ? String(node.value || "").trim() : fallback;
    }

    function setQueryStatus(message, tone = "slate") {
      const node = document.getElementById("query-status");
      if (!node) {
        return;
      }
      node.textContent = String(message || "");
      node.className = `text-xs font-bold uppercase tracking-wide text-${tone}-500`;
    }

    function formatQueryCell(value) {
      if (value === null || value === undefined || value === "") {
        return "â€”";
      }
      if (typeof value === "object") {
        try {
          return JSON.stringify(value);
        } catch (err) {
          return String(value);
        }
      }
      return String(value);
    }

    function clearQueryProgressTimers() {
      queryProgressTimers.forEach((handle) => {
        try {
          clearTimeout(handle);
        } catch (err) {
          // Ignore timer cleanup issues in constrained environments.
        }
      });
      queryProgressTimers = [];
    }

    function hideQueryProgressPanel() {
      const shell = document.getElementById("query-progress-shell");
      if (shell) {
        shell.classList.add("hidden");
      }
    }

    function appendQueryActivity(message, tone = "slate") {
      const log = document.getElementById("query-activity-log");
      if (!log) {
        return;
      }
      const entry = document.createElement("div");
      entry.className = `rounded-lg border border-${tone}-500/20 bg-slate-900/70 px-3 py-2 text-xs text-slate-200`;
      entry.textContent = String(message || "");
      log.appendChild(entry);
      const children = Array.from(log.children || []);
      while (children.length > 6) {
        const oldest = children.shift();
        if (oldest && typeof oldest.remove === "function") {
          oldest.remove();
        }
      }
      const caption = document.getElementById("query-activity-caption");
      if (caption) {
        caption.textContent = `${Array.from(log.children || []).length} recent update${(log.children || []).length === 1 ? "" : "s"}`;
      }
    }

    function setQueryProgress(value, message, tone = "amber", options = {}) {
      const shell = document.getElementById("query-progress-shell");
      const label = document.getElementById("query-progress-label");
      const messageNode = document.getElementById("query-progress-message");
      const pctNode = document.getElementById("query-progress-pct");
      const bar = document.getElementById("query-progress-bar");
      const safeValue = Math.max(0, Math.min(100, Number(value || 0)));
      const indeterminate = Boolean(options?.indeterminate);
      if (shell) {
        shell.classList.remove("hidden");
      }
      if (label) {
        label.className = `text-[11px] font-bold uppercase tracking-wide text-${tone}-700`;
      }
      if (messageNode) {
        messageNode.textContent = String(message || "");
      }
      if (pctNode) {
        pctNode.textContent = indeterminate ? "Working..." : `${Math.round(safeValue)}%`;
        pctNode.className = `text-xs font-bold uppercase tracking-wide text-${tone}-700`;
      }
      if (bar) {
        bar.style.width = `${safeValue}%`;
        bar.classList.toggle("animate-pulse", indeterminate);
      }
    }

    function resetQueryProgressPanel() {
      clearQueryProgressTimers();
      const log = document.getElementById("query-activity-log");
      if (log) {
        log.innerHTML = "";
      }
      const caption = document.getElementById("query-activity-caption");
      if (caption) {
        caption.textContent = "Latest query steps appear here.";
      }
      setQueryProgress(0, "Waiting for the next query run.", "amber");
    }

    function startQueryProgress(details) {
      clearQueryProgressTimers();
      const signalRun = details?.dataset === "signal_scan";
      const stages = signalRun
        ? [
            { pct: 8, message: "Preparing the actionable signal scan.", activity: "Loaded the current query settings and selected universe." },
            { pct: 22, message: "Checking data freshness for the chosen universe.", activity: "Verifying whether the stored market backbone needs a refresh." },
            { pct: 48, message: "Scanning stored price history across the selected universe.", activity: "Running the signal rules against the cached price backbone." },
            { pct: 76, message: "Ranking the strongest actionable matches.", activity: "Sorting candidates by reliability and signal age." },
            { pct: 82, message: "Still scanning the selected universe. This can take a while on larger runs.", activity: "The backend is still working through the remaining ticker histories.", indeterminate: true },
          ]
        : [
            { pct: 10, message: "Preparing the structured query.", activity: "Collected the requested filters and preview columns." },
            { pct: 38, message: "Reading the requested dataset.", activity: "Pulling the matching rows from the stored backbone." },
            { pct: 72, message: "Formatting the preview rows.", activity: "Shaping the response so the preview stays responsive." },
            { pct: 80, message: "Still working on the response.", activity: "Waiting for the backend query to finish and return the preview.", indeterminate: true },
          ];
      const delays = signalRun ? [0, 200, 700, 1400, 2600] : [0, 200, 700, 1800];
      stages.forEach((stage, index) => {
        const handle = setTimeout(() => {
          setQueryProgress(stage.pct, stage.message, "amber", { indeterminate: Boolean(stage.indeterminate) });
          appendQueryActivity(stage.activity, "amber");
        }, delays[index] || 0);
        queryProgressTimers.push(handle);
      });
    }

    function finishQueryProgress(message, success = true) {
      clearQueryProgressTimers();
      const tone = success ? "emerald" : "rose";
      setQueryProgress(100, message, tone);
      appendQueryActivity(message, tone);
      if (success) {
        const handle = setTimeout(() => {
          hideQueryProgressPanel();
        }, 1200);
        queryProgressTimers.push(handle);
      }
    }

    function getQuerySignalScanSource() {
      return normalizeScanScope(tickerScanScope || "xetra");
    }

    async function openQueryTickerChart(ticker) {
      const symbol = String(ticker || "").trim().toUpperCase();
      if (!symbol) {
        return;
      }
      showTab("screener");
      await loadChart(symbol);
    }

    function buildQueryRequestDetails() {
      const dataset = getQueryDataset();
      const params = new URLSearchParams();
      params.set("dataset", dataset);
      const cliParts = ["etfs", "query", "--dataset", dataset];
      if (dataset === "signal_scan") {
        const source = getQuerySignalScanSource();
        const signal = getQueryInputValue("query-signal", "trend_forming");
        const signalAgeMax = getQueryInputValue("query-signal-age-max", "5");
        const minReliability = getQueryInputValue("query-min-reliability", "6.0");
        const refreshIfNeededNode = document.getElementById("query-refresh-if-needed");
        const refreshIfNeeded = Boolean(refreshIfNeededNode?.checked);
        params.set("source", source);
        params.set("signal", signal);
        params.set("signal_age_max", signalAgeMax);
        params.set("min_reliability", minReliability);
        params.set("refresh_if_needed", refreshIfNeeded ? "true" : "false");
        cliParts.push(
          "--source", source,
          "--signal", signal,
          "--signal-age-max", signalAgeMax,
          "--min-reliability", minReliability,
        );
      } else if (dataset === "price_history") {
        const ticker = getQueryInputValue("query-ticker").toUpperCase();
        const days = getQueryInputValue("query-days", "90");
        const startDate = getQueryInputValue("query-start-date");
        const endDate = getQueryInputValue("query-end-date");
        if (ticker) {
          params.set("ticker", ticker);
          cliParts.push("--ticker", ticker);
        }
        if (days) {
          params.set("days", days);
          cliParts.push("--days", days);
        }
        if (startDate) {
          params.set("start_date", startDate);
          cliParts.push("--start-date", startDate);
        }
        if (endDate) {
          params.set("end_date", endDate);
          cliParts.push("--end-date", endDate);
        }
      } else if (dataset === "shortlist") {
        const label = getQueryInputValue("query-label", "All");
        const sortBy = getQueryInputValue("query-sort-by", "final_score");
        params.set("label", label);
        params.set("sort_by", sortBy);
        cliParts.push("--label", label, "--sort-by", sortBy);
      }
      const limit = getQueryInputValue("query-limit", "120");
      const columns = getQueryInputValue("query-columns");
      if (limit) {
        params.set("limit", limit);
        cliParts.push("--limit", limit);
      }
      if (columns) {
        params.set("columns", columns);
        cliParts.push("--columns", columns);
      }
      return {
        dataset,
        params,
        apiPath: `/api/query/run?${params.toString()}`,
        cliCall: cliParts.join(" "),
      };
    }

    function updateQueryCallPreviews() {
      const details = buildQueryRequestDetails();
      const apiNode = document.getElementById("query-api-call");
      const cliNode = document.getElementById("query-cli-call");
      if (apiNode) {
        apiNode.textContent = details.apiPath;
      }
      if (cliNode) {
        cliNode.textContent = details.cliCall;
      }
    }

    function updateQueryControls() {
      const dataset = getQueryDataset();
      const isSignalScan = dataset === "signal_scan";
      const isPriceHistory = dataset === "price_history";
      const sourceGroup = document.getElementById("query-source-group");
      const sourceReadout = document.getElementById("query-source-readout");
      const sourceNote = document.getElementById("query-source-note");
      const signalGroup = document.getElementById("query-signal-group");
      const signalAgeGroup = document.getElementById("query-signal-age-group");
      const reliabilityGroup = document.getElementById("query-reliability-group");
      const refreshGroup = document.getElementById("query-refresh-group");
      const tickerGroup = document.getElementById("query-ticker-group");
      const labelGroup = document.getElementById("query-label-group");
      const daysGroup = document.getElementById("query-days-group");
      const startGroup = document.getElementById("query-start-group");
      const endGroup = document.getElementById("query-end-group");
      const sortGroup = document.getElementById("query-sort-group");
      if (sourceGroup) sourceGroup.classList.toggle("hidden", !isSignalScan);
      if (signalGroup) signalGroup.classList.toggle("hidden", !isSignalScan);
      if (signalAgeGroup) signalAgeGroup.classList.toggle("hidden", !isSignalScan);
      if (reliabilityGroup) reliabilityGroup.classList.toggle("hidden", !isSignalScan);
      if (refreshGroup) refreshGroup.classList.toggle("hidden", !isSignalScan);
      if (tickerGroup) tickerGroup.classList.toggle("hidden", !isPriceHistory);
      if (daysGroup) daysGroup.classList.toggle("hidden", !isPriceHistory);
      if (startGroup) startGroup.classList.toggle("hidden", !isPriceHistory);
      if (endGroup) endGroup.classList.toggle("hidden", !isPriceHistory);
      if (labelGroup) labelGroup.classList.toggle("hidden", isSignalScan || isPriceHistory);
      if (sortGroup) sortGroup.classList.toggle("hidden", isSignalScan || isPriceHistory);
      const datasetCard = document.getElementById("query-summary-dataset");
      const signalSource = getQuerySignalScanSource();
      const sourceMap = {
        xetra: "Xetra",
        nasdaq: "Nasdaq",
        sweden: "Sweden",
        list: "My List",
        all_lists: "All Lists",
      };
      if (datasetCard) {
        datasetCard.textContent = dataset === "signal_scan"
          ? "Signal Scan"
          : dataset === "shortlist"
          ? "Shortlist Snapshot"
          : "Ticker History";
      }
      if (sourceReadout) {
        sourceReadout.textContent = sourceMap[signalSource] || "Xetra";
      }
      if (sourceNote) {
        sourceNote.textContent = "Uses the ticker universe selected in the top bar.";
        sourceNote.className = "mt-2 text-[11px] text-slate-500";
      }
      if (isSignalScan) {
        const signalConfig = getQuerySignalConfig();
        const ageNode = document.getElementById("query-signal-age-max");
        const reliabilityNode = document.getElementById("query-min-reliability");
        if (signalConfig && ageNode && !String(ageNode.dataset.userEdited || "").trim()) {
          ageNode.value = String(signalConfig.default_age_max || 5);
        }
        if (signalConfig && reliabilityNode && !String(reliabilityNode.dataset.userEdited || "").trim()) {
          reliabilityNode.value = String(signalConfig.default_min_reliability || 6.0);
        }
      }
      updateQueryCallPreviews();
    }

    function renderQueryResults(result) {
      queryRows = Array.isArray(result?.rows) ? result.rows.slice() : [];
      queryColumns = Array.isArray(result?.columns) ? result.columns.slice() : [];
      const empty = document.getElementById("query-empty");
      const content = document.getElementById("query-content");
      const head = document.getElementById("query-results-head");
      const body = document.getElementById("query-results-body");
      const rowsNode = document.getElementById("query-summary-rows");
      const returnedNode = document.getElementById("query-summary-returned");
      const rangeNode = document.getElementById("query-summary-range");
      const sourceNode = document.getElementById("query-summary-source");

      if (rowsNode) {
        rowsNode.textContent = String(result?.row_count || 0);
      }
      if (returnedNode) {
        returnedNode.textContent = String(result?.returned_rows || 0);
      }
      if (sourceNode) {
        if (result?.dataset === "signal_scan") {
          const sourceMap = {
            xetra: "Xetra",
            nasdaq: "Nasdaq",
            sweden: "Sweden",
            list: "My List",
            all_lists: "All Lists",
          };
          sourceNode.textContent = sourceMap[String(result?.source || "").trim().toLowerCase()] || String(result?.source || "-");
        } else {
          sourceNode.textContent = String(result?.source || "-");
        }
      }
      if (rangeNode) {
        if (result?.dataset === "signal_scan") {
          rangeNode.textContent = String(result?.summary?.latest_market_date || "â€”");
        } else if (result?.dataset === "price_history") {
          const earliest = result?.summary?.earliest_date || "â€”";
          const latest = result?.summary?.latest_date || "â€”";
          rangeNode.textContent = `${earliest} â†’ ${latest}`;
        } else {
          rangeNode.textContent = String(result?.summary?.as_of_date || "â€”");
        }
      }

      if (head) {
        head.innerHTML = "";
        if (queryColumns.length) {
          const tr = document.createElement("tr");
          queryColumns.forEach((column) => {
            const th = document.createElement("th");
            th.className = "px-3 py-2 text-left text-xs font-bold uppercase tracking-wide";
            th.textContent = String(column);
            tr.appendChild(th);
          });
          head.appendChild(tr);
        }
      }

      if (body) {
        body.innerHTML = "";
        queryRows.forEach((row) => {
          const tr = document.createElement("tr");
          queryColumns.forEach((column) => {
            const td = document.createElement("td");
            td.className = "px-3 py-2 align-top text-slate-700";
            const rawValue = row?.[column];
            if (String(column || "").trim().toLowerCase() === "ticker" && String(rawValue || "").trim()) {
              const button = document.createElement("button");
              button.type = "button";
              button.className = "font-bold text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:text-indigo-500";
              button.textContent = formatQueryCell(rawValue);
              button.title = `Open ${String(rawValue || "").trim().toUpperCase()} in Screener`;
              button.addEventListener("click", () => {
                openQueryTickerChart(rawValue).catch((err) => {
                  console.warn("Could not open query ticker chart", err);
                });
              });
              td.appendChild(button);
            } else {
              td.textContent = formatQueryCell(rawValue);
            }
            tr.appendChild(td);
          });
          body.appendChild(tr);
        });
      }

      if (empty) {
        empty.classList.toggle("hidden", queryRows.length > 0);
        if (!queryRows.length) {
          empty.textContent = result?.dataset === "signal_scan"
            ? "No actionable tickers matched the current signal and universe."
            : "The query returned no rows for the current filters.";
        }
      }
      if (content) {
        content.classList.toggle("hidden", queryRows.length === 0);
      }
    }

    async function loadQueryResults() {
      try {
        await loadQueryCatalog();
      } catch (err) {
        setQueryStatus(`Catalog error: ${err.message || err}`, "rose");
        finishQueryProgress(`Catalog load failed: ${err.message || err}`, false);
        throw err;
      }
      const details = buildQueryRequestDetails();
      if (details.dataset === "price_history" && !details.params.get("ticker")) {
        setQueryStatus("Choose a ticker before running Ticker History.", "amber");
        renderQueryResults({
          dataset: details.dataset,
          row_count: 0,
          returned_rows: 0,
          source: "-",
          summary: {},
          columns: [],
          rows: [],
        });
        finishQueryProgress("Ticker History needs a ticker before the query can run.", false);
        return;
      }
      if (details.dataset === "signal_scan") {
        const source = String(details.params.get("source") || "xetra");
        if ((source === "list" || source === "all_lists") && getScopeTickers(source).length === 0) {
          setQueryStatus("Choose a universe with tickers before running Signal Scan.", "amber");
          renderQueryResults({
            dataset: details.dataset,
            row_count: 0,
            returned_rows: 0,
            source,
            summary: { latest_market_date: null },
            columns: [],
            rows: [],
          });
          finishQueryProgress("Signal Scan stopped because the selected list universe is empty.", false);
          return;
        }
      }

      const runBtn = document.getElementById("query-run-btn");
      if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = "Running...";
      }
      startQueryProgress(details);
      setQueryStatus(details.dataset === "signal_scan" ? "Scanning actionable signals..." : "Running structured query...", "amber");
      updateQueryCallPreviews();
      try {
        const resp = await fetch(details.apiPath, { cache: "no-store" });
        appendQueryActivity("The query backend responded. Rendering the preview now.", "amber");
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data?.detail || "Query failed");
        }
        renderQueryResults(data);
        if (details.dataset === "signal_scan") {
          const refreshRequested = Boolean(data?.refresh?.requested);
          const refreshed = Number(data?.refresh?.result?.refreshed || 0);
          const refreshText = refreshRequested
            ? ` Refreshed ${refreshed} stale tickers first.`
            : " Market data was already fresh enough.";
          const successMessage = `Found ${data.row_count || 0} actionable tickers.${refreshText}`;
          setQueryStatus(successMessage, "emerald");
          finishQueryProgress(successMessage, true);
        } else {
          const successMessage = `Returned ${data.returned_rows || 0} preview rows from ${data.row_count || 0} matching rows.`;
          setQueryStatus(successMessage, "emerald");
          finishQueryProgress(successMessage, true);
        }
      } catch (err) {
        renderQueryResults({
          dataset: details.dataset,
          row_count: 0,
          returned_rows: 0,
          source: "-",
          summary: {},
          columns: [],
          rows: [],
        });
        const errorMessage = `Query error: ${err.message || err}`;
        setQueryStatus(errorMessage, "rose");
        finishQueryProgress(errorMessage, false);
        throw err;
      } finally {
        if (runBtn) {
          runBtn.disabled = false;
          runBtn.textContent = "Run Query";
        }
      }
    }

    function readBacktestRaceSnapshot() {
      try {
        const raw = localStorage.getItem(LAST_BACKTEST_RACE_KEY);
        if (!raw) {
          return null;
        }
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === "object" ? parsed : null;
      } catch (err) {
        return null;
      }
    }

    function writeBacktestRaceSnapshot(snapshot) {
      try {
        if (!snapshot || typeof snapshot !== "object") {
          localStorage.removeItem(LAST_BACKTEST_RACE_KEY);
          return;
        }
        localStorage.setItem(LAST_BACKTEST_RACE_KEY, JSON.stringify(snapshot));
      } catch (err) {
        // Ignore storage failures in restricted environments.
      }
    }

    function normalizeExchangeFilter(value) {
      const cleaned = String(value || "all").trim().toLowerCase();
      if (["nasdaq", "us", "usa"].includes(cleaned)) {
        return "nasdaq";
      }
      if (["xetra", "germany", "de"].includes(cleaned)) {
        return "xetra";
      }
      if (["sweden", "stockholm", "stockholms", "se", "ss", "st"].includes(cleaned)) {
        return "sweden";
      }
      return "all";
    }

    function normalizeScanScope(value) {
      const cleaned = String(value || "xetra").trim().toLowerCase();
      if (["nasdaq", "us", "usa", "us_stocks", "us-stocks"].includes(cleaned)) {
        return "nasdaq";
      }
      if (["list", "chosen", "chosen_list", "custom"].includes(cleaned)) {
        return "list";
      }
      if (["all_lists", "alllists", "all list", "all lists"].includes(cleaned)) {
        return "all_lists";
      }
      if (["sweden", "stockholm", "stockholms", "se", "ss", "st"].includes(cleaned)) {
        return "sweden";
      }
      if (["xetra", "germany", "de", "exchange", "all"].includes(cleaned)) {
        return "xetra";
      }
      return "xetra";
    }

    function getTickerExchangeBucket(ticker, label = "") {
      const upperTicker = String(ticker || "").toUpperCase();
      const upperLabel = String(label || "").toUpperCase();
      if (/\.(ST|SE|SS)$/.test(upperTicker) || upperLabel.includes("STOCKHOLM") || upperLabel.includes("SWED") || upperTicker.includes("SWE")) {
        return "sweden";
      }
      if (upperLabel.includes("NASDAQ") || upperLabel.includes("UNITED STATES") || upperLabel.includes("USA")) {
        return "nasdaq";
      }
      if (/\.(DE|F|DU|HM|SG|BE|MU)$/.test(upperTicker)) {
        return "xetra";
      }
      return "all";
    }

    function getTickerSelectNodes() {
      return {
        ticker: document.getElementById("ticker-select"),
      };
    }

    function captureTickerSelectUniverse() {
      const { ticker } = getTickerSelectNodes();
      if (!ticker || tickerSelectUniverse.length > 0) {
        return;
      }
      tickerSelectUniverse = Array.from(ticker.options)
        .filter((option) => option && option.value)
        .map((option) => ({
          ticker: String(option.value).toUpperCase(),
          label: String(option.textContent || option.value || "").trim(),
          exchange: getTickerExchangeBucket(option.value, option.textContent || option.value),
        }));
    }

    function setTickerSelectUniverse(items) {
      tickerSelectUniverse = (Array.isArray(items) ? items : [])
        .map((item) => {
          if (typeof item === "string") {
            return {
              ticker: String(item).toUpperCase(),
              label: String(item).toUpperCase(),
              name: String(item).toUpperCase(),
              issuer: "",
              asset_class: "",
              region: "",
              exchange: getTickerExchangeBucket(item, item),
            };
          }
          const ticker = String(item.ticker || item.value || item.symbol || "").toUpperCase();
          const label = String(item.label || item.text || item.name || item.ticker || item.value || "").trim();
          const exchange = normalizeExchangeFilter(item.exchange || getTickerExchangeBucket(item.ticker || item.value || item.symbol || "", item.label || item.text || item.name || ""));
          return {
            ticker,
            label,
            name: String(item.name || item.label || item.text || item.ticker || item.value || "").trim() || label || ticker,
            issuer: String(item.issuer || "").trim(),
            asset_class: String(item.asset_class || item.assetClass || "").trim(),
            region: String(item.region || "").trim(),
            exchange,
          };
        })
        .filter((item) => item.ticker);
    }

    function getScopeTickers(scope) {
      const normalized = normalizeScanScope(scope);
      if (normalized === "list") {
        return sortTickersByUniverse(customTickerList);
      }
      if (normalized === "all_lists") {
        const sourceLists = Array.isArray(customTickerLists) && customTickerLists.length > 0
          ? customTickerLists
          : [{ name: customTickerListActiveName || customTickerListName, tickers: customTickerList }];
        return sortTickersByUniverse(
          sourceLists.flatMap((entry) => Array.isArray(entry.tickers) ? entry.tickers : [])
        );
      }
      return [];
    }

    function getFilteredTickerUniverse() {
      const scope = normalizeScanScope(tickerScanScope);
      if (scope === "xetra" || scope === "sweden" || scope === "nasdaq") {
        return tickerSelectUniverse.filter((item) => item.exchange === scope);
      }
      const scopeTickers = new Set(getScopeTickers(scope));
      if (scopeTickers.size === 0) {
        return scope === "list" ? [] : tickerSelectUniverse;
      }
      return tickerSelectUniverse.filter((item) => scopeTickers.has(item.ticker));
    }

    function renderTickerSelectOptions({ preserveSelection = true } = {}) {
      const { ticker } = getTickerSelectNodes();
      if (!ticker) {
        return;
      }

      captureTickerSelectUniverse();

      const selectedTicker = preserveSelection
        ? String(ticker.value || tickerSelectLastValue || readStickyValue(LAST_TICKER_SELECT_KEY, "")).toUpperCase()
        : "";

      const normalizedScope = normalizeScanScope(tickerScanScope);

      const visible = getFilteredTickerUniverse();
      ticker.innerHTML = "";

      const placeholder = document.createElement("option");
      placeholder.value = "";
      if (normalizedScope === "sweden") {
        placeholder.textContent = visible.length > 0
          ? "Select Swedish ticker..."
          : "No Swedish exchange tickers loaded yet";
      } else if (normalizedScope === "nasdaq") {
        placeholder.textContent = visible.length > 0
          ? "Select Nasdaq ticker..."
          : "No Nasdaq tickers loaded yet";
      } else if (normalizedScope === "xetra") {
        placeholder.textContent = "Select Xetra ticker...";
      } else if (normalizedScope === "all_lists") {
        placeholder.textContent = visible.length > 0
          ? "Select ticker from all lists..."
          : "No saved list tickers loaded yet";
      } else if (normalizedScope === "list") {
        placeholder.textContent = visible.length > 0
          ? "Select ticker from My List..."
          : "No saved list tickers loaded yet";
      } else {
        placeholder.textContent = "Select Ticker...";
      }
      ticker.appendChild(placeholder);

      visible.forEach((item) => {
        const opt = document.createElement("option");
        opt.value = item.ticker;
        opt.textContent = item.label || item.ticker;
        ticker.appendChild(opt);
      });

      const hasSelectedTicker = selectedTicker && visible.some((item) => item.ticker === selectedTicker);
      if (hasSelectedTicker) {
        ticker.value = selectedTicker;
      } else if (visible.length === 1) {
        ticker.value = visible[0].ticker;
      } else {
        ticker.value = "";
      }
      ticker.disabled = ((normalizedScope === "sweden" || normalizedScope === "nasdaq") && visible.length === 0) || (normalizedScope === "all_lists" && visible.length === 0);
      tickerSelectLastValue = ticker.value || "";
      writeStickyValue(LAST_TICKER_SELECT_KEY, tickerSelectLastValue);
    }

    function storeTickerSelection(value) {
      tickerSelectLastValue = String(value || "");
      writeStickyValue(LAST_TICKER_SELECT_KEY, tickerSelectLastValue);
    }

    function parseTickerListText(text) {
      return String(text || "")
        .split(/[\s,;]+/)
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean);
    }

    function normalizeListName(value) {
      const name = String(value || "").trim();
      return name || "My List";
    }

    function readCustomTickerList() {
      return parseTickerListText(readStickyValue(LAST_CUSTOM_LIST_KEY, ""));
    }

    function readCustomTickerListName() {
      return normalizeListName(customTickerListActiveName || readStickyValue(LAST_CUSTOM_LIST_NAME_KEY, "My List"));
    }

    function writeCustomTickerListName(name) {
      customTickerListName = normalizeListName(name);
      customTickerListActiveName = customTickerListName;
      writeStickyValue(LAST_CUSTOM_LIST_NAME_KEY, customTickerListName);
      return customTickerListName;
    }

    function writeCustomTickerList(tickers, name = customTickerListName) {
      customTickerList = sortTickersByUniverse(tickers);
      writeStickyValue(LAST_CUSTOM_LIST_KEY, customTickerList.join(","));
      writeCustomTickerListName(name);
      return customTickerList;
    }

    function normalizeCustomTickerListsPayload(payload) {
      const rawLists = Array.isArray(payload?.lists) ? payload.lists : [];
      const lists = [];
      const seen = new Set();
      const addEntry = (entry, fallbackName = "My List") => {
        const name = normalizeListName(entry?.name || fallbackName);
        const tickers = sortTickersByUniverse(entry?.tickers || []);
        if (seen.has(name)) {
          const idx = lists.findIndex((item) => item.name === name);
          if (idx >= 0) {
            lists[idx] = { name, tickers };
          }
        } else {
          seen.add(name);
          lists.push({ name, tickers });
        }
      };

      if (rawLists.length > 0) {
        rawLists.forEach((entry) => addEntry(entry));
      } else if (Array.isArray(payload?.tickers) || typeof payload?.tickers === "string") {
        addEntry({
          name: payload?.name || payload?.active_name || "My List",
          tickers: payload?.tickers || [],
        });
      }

      if (lists.length === 0) {
        lists.push({ name: "My List", tickers: [] });
      }

      const activeName = normalizeListName(
        payload?.active_name || payload?.name || lists[0]?.name || "My List"
      );
      const activeList = lists.find((item) => item.name === activeName) || lists[0];
      return {
        lists,
        activeName,
        activeList: {
          name: activeList.name,
          tickers: sortTickersByUniverse(activeList.tickers),
        },
      };
    }

    function sortTickersByUniverse(tickers) {
      const order = new Map(
        tickerSelectUniverse.map((item, index) => [String(item.ticker || "").toUpperCase(), index])
      );
      return Array.from(new Set((Array.isArray(tickers) ? tickers : [])
        .map((item) => String(item || "").trim().toUpperCase())
        .filter(Boolean)))
        .sort((a, b) => {
          const aIndex = order.has(a) ? order.get(a) : Number.MAX_SAFE_INTEGER;
          const bIndex = order.has(b) ? order.get(b) : Number.MAX_SAFE_INTEGER;
          if (aIndex !== bIndex) {
            return aIndex - bIndex;
          }
          return a.localeCompare(b);
        });
    }

    function getTickerUniverseSearchText(item) {
      return [
        item.ticker,
        item.label,
        item.name,
        item.issuer,
        item.asset_class,
        item.region,
      ]
        .map((part) => String(part || "").trim().toUpperCase())
        .filter(Boolean)
        .join(" ");
    }

    async function loadTickerUniverseFromServer() {
      try {
        const resp = await fetch("/api/ticker-universe", { cache: "no-store" });
        if (!resp.ok) {
          throw new Error(`status ${resp.status}`);
        }
        const data = await resp.json();
        const items = Array.isArray(data.items)
          ? data.items
          : Array.isArray(data.tickers)
            ? data.tickers
            : [];
        setTickerSelectUniverse(items);
        renderTickerSelectOptions({ preserveSelection: true });
        return tickerSelectUniverse;
      } catch (err) {
        console.warn("Falling back to hidden ticker select universe", err);
        captureTickerSelectUniverse();
        renderTickerSelectOptions({ preserveSelection: true });
        return tickerSelectUniverse;
      }
    }

    async function ensureTickerUniverseLoaded() {
      if (!tickerUniverseLoadPromise) {
        tickerUniverseLoadPromise = loadTickerUniverseFromServer();
      }
      return tickerUniverseLoadPromise;
    }

    function getAllCustomListTickers() {
      const sourceLists = Array.isArray(customTickerLists) && customTickerLists.length > 0
        ? customTickerLists
        : [{ name: customTickerListActiveName || customTickerListName, tickers: customTickerList }];
      return sortTickersByUniverse(
        sourceLists.flatMap((entry) => Array.isArray(entry.tickers) ? entry.tickers : [])
      );
    }

    function getCustomListEntryByName(name) {
      const normalized = normalizeListName(name);
      return (Array.isArray(customTickerLists) ? customTickerLists : []).find((entry) => normalizeListName(entry.name) === normalized) || null;
    }

    function upsertCustomListEntry(sourceName, nextName, tickers) {
      const source = normalizeListName(sourceName);
      const dest = normalizeListName(nextName);
      const normalizedTickers = sortTickersByUniverse(tickers);
      const nextLists = (Array.isArray(customTickerLists) ? customTickerLists : [])
        .filter((entry) => {
          const entryName = normalizeListName(entry.name);
          if (source === "__new__") {
            return entryName !== dest;
          }
          return entryName !== source && entryName !== dest;
        })
        .map((entry) => ({
          name: normalizeListName(entry.name),
          tickers: sortTickersByUniverse(entry.tickers || []),
        }));
      nextLists.push({ name: dest, tickers: normalizedTickers });
      customTickerLists = nextLists;
      customTickerListActiveName = dest;
      customTickerListName = dest;
      customTickerList = normalizedTickers;
      return { lists: nextLists, active_name: dest, active_list: { name: dest, tickers: normalizedTickers } };
    }

    async function loadCustomTickerListFromServer() {
      try {
        const resp = await fetch("/api/custom-ticker-list", { cache: "no-store" });
        if (!resp.ok) {
          throw new Error(`status ${resp.status}`);
        }
        const data = await resp.json();
        const normalized = normalizeCustomTickerListsPayload(data);
        customTickerLists = normalized.lists;
        customTickerListActiveName = normalized.activeName;
        customTickerListName = normalized.activeName;
        customTickerList = sortTickersByUniverse(normalized.activeList.tickers);
        writeCustomTickerList(customTickerList, customTickerListActiveName);
        return {
          lists: normalized.lists,
          active_name: normalized.activeName,
          active_list: normalized.activeList,
          tickers: customTickerList,
          name: customTickerListActiveName,
        };
      } catch (err) {
        console.warn("Falling back to locally cached ticker list", err);
        const fallback = sortTickersByUniverse(readCustomTickerList());
        const name = readCustomTickerListName();
        customTickerLists = [{ name, tickers: fallback }];
        customTickerListActiveName = name;
        customTickerListName = name;
        customTickerList = fallback;
        writeCustomTickerList(fallback, name);
        return {
          lists: customTickerLists,
          active_name: name,
          active_list: { name, tickers: fallback },
          tickers: fallback,
          name,
        };
      }
    }

    async function persistCustomTickerListsToServer(collection) {
      const normalizedLists = Array.isArray(collection?.lists) ? collection.lists : [];
      const activeName = normalizeListName(collection?.active_name || collection?.name || customTickerListActiveName);
      const normalizedCollection = normalizeCustomTickerListsPayload({
        active_name: activeName,
        lists: normalizedLists,
      });
      customTickerLists = normalizedCollection.lists;
      customTickerListActiveName = normalizedCollection.activeName;
      customTickerListName = normalizedCollection.activeName;
      customTickerList = sortTickersByUniverse(normalizedCollection.activeList.tickers);
      writeCustomTickerList(customTickerList, customTickerListActiveName);
      try {
        const resp = await fetch("/api/custom-ticker-list", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            schema_version: "custom_ticker_lists_v3",
            active_name: normalizedCollection.activeName,
            lists: normalizedCollection.lists,
          }),
        });
        if (!resp.ok) {
          throw new Error(`status ${resp.status}`);
        }
        const data = await resp.json();
        const saved = normalizeCustomTickerListsPayload(data);
        return {
          lists: saved.lists,
          tickers: sortTickersByUniverse(saved.activeList.tickers),
          name: normalizeListName(data.active_name || data.name || normalizedCollection.activeName),
          savedToServer: true,
        };
      } catch (err) {
        console.warn("Could not persist custom ticker list to server", err);
        return {
          lists: normalizedCollection.lists,
          tickers: sortTickersByUniverse(normalizedCollection.activeList.tickers),
          name: normalizedCollection.activeName,
          savedToServer: false,
        };
      }
    }

    function getListSelectNodes() {
      return {
        list: document.getElementById("list-select"),
      };
    }

    function getScanSourceButtons() {
      return Array.from(document.querySelectorAll(
        "#scan-source-toggle .scan-source-btn"
      ));
    }

    function updateScanScopeChrome() {
      const scopeButtons = getScanSourceButtons();
      const normalized = normalizeScanScope(tickerScanScope);
      tickerScanScope = normalized;
      scopeButtons.forEach((button) => {
        if (!button) {
          return;
        }
        const active = String(button.dataset.scope || "") === normalized;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
      renderTickerSelectOptions({ preserveSelection: true });
      updateQueryControls();
    }

    async function applyScanScopeSelection(mode) {
      const normalized = normalizeScanScope(mode);
      tickerScanScope = normalized;
      tickerUniverseExplicitlyChosen = true;
      writeStickyValue(LAST_SCAN_SCOPE_KEY, normalized);
      updateScanScopeChrome();
      updateRangeChrome();
      updateScanActionButtonsState();
      loadMarketStatus(normalized).catch((err) => {
        console.warn("Could not refresh market status after scope change", err);
      });
      if ((normalized === "list" || normalized === "all_lists") && getScopeTickers(normalized).length === 0) {
        await openListEditorModal();
      }
      updateBacktestRunButtonState();
    }

    function setScanSource(mode) {
      return applyScanScopeSelection(mode);
    }

    function updateListSelectChrome() {
      const activeName = normalizeListName(customTickerListActiveName || customTickerListName);
      const customCount = customTickerList.length;
      const editBtn = document.getElementById("list-edit-btn");
      if (editBtn) {
        editBtn.textContent = customCount > 0 ? `Edit ${activeName} (${customCount})` : `Edit ${activeName}...`;
        editBtn.title = customCount > 0
          ? `Edit the saved list ${activeName} (${customCount} tickers)`
          : `Build the saved list ${activeName}`;
      }
    }

    function getListBuilderListSelectNode() {
      return document.getElementById("list-modal-list-select");
    }

    function updateListBuilderListSelector() {
      const listSelect = getListBuilderListSelectNode();
      if (!listSelect) {
        return;
      }
      const activeName = normalizeListName(customTickerListDraftSourceName || customTickerListActiveName);
      listSelect.innerHTML = "";

      const entries = Array.isArray(customTickerLists) ? customTickerLists : [];
      if (entries.length === 0) {
        const option = document.createElement("option");
        option.value = activeName;
        option.textContent = activeName;
        listSelect.appendChild(option);
      } else {
        entries.forEach((entry) => {
          const option = document.createElement("option");
          option.value = normalizeListName(entry.name);
          option.textContent = normalizeListName(entry.name);
          listSelect.appendChild(option);
        });
      }

      const newOption = document.createElement("option");
      newOption.value = "__new__";
      newOption.textContent = "+ New List";
      listSelect.appendChild(newOption);
      listSelect.value = activeName;
    }

    async function openListEditorModal() {
      await ensureTickerUniverseLoaded();
      const modal = document.getElementById("list-modal");
      if (!modal) {
        return;
      }

      customTickerListDraftSourceName = normalizeListName(customTickerListActiveName || customTickerListName || readCustomTickerListName());
      customTickerListDraft = sortTickersByUniverse(customTickerList);
      customTickerListName = normalizeListName(customTickerListDraftSourceName);
      listBuilderExchange = "all";
      listBuilderSearch = "";
      modal.style.display = "flex";
      updateListBuilderListSelector();
      renderListBuilderModal();
      window.setTimeout(() => {
        const searchInput = document.getElementById("list-modal-search");
        if (searchInput) {
          searchInput.focus();
        }
      }, 0);
      tickerListMode = "custom";
      writeStickyValue(LAST_LIST_MODE_KEY, tickerListMode);
      updateListSelectChrome();
    }

    function closeListEditorModal() {
      const modal = document.getElementById("list-modal");
      if (modal) {
        modal.style.display = "none";
      }
    }

    function setListBuilderList(value) {
      const normalized = normalizeListName(value);
      if (normalized === "__new__") {
        customTickerListDraftSourceName = "__new__";
        customTickerListDraft = [];
        customTickerListName = "My List";
      } else {
        const selected = getCustomListEntryByName(normalized);
        customTickerListDraftSourceName = normalized;
        customTickerListName = normalized;
        customTickerListDraft = sortTickersByUniverse(selected ? selected.tickers : []);
      }
      updateListBuilderListSelector();
      renderListBuilderModal();
    }

    function setListBuilderExchange(exchange) {
      listBuilderExchange = normalizeExchangeFilter(exchange);
      renderListBuilderModal();
    }

    function setListBuilderSearch(value) {
      listBuilderSearch = String(value || "");
      renderListBuilderModal();
    }

    function getListBuilderVisibleTickers() {
      const search = String(listBuilderSearch || "").trim().toUpperCase();
      const exchange = normalizeExchangeFilter(listBuilderExchange);
      return tickerSelectUniverse.filter((item) => {
        if (exchange !== "all" && item.exchange !== exchange) {
          return false;
        }
        if (search && !getTickerUniverseSearchText(item).includes(search)) {
          return false;
        }
        return true;
      });
    }

    function syncListBuilderCount() {
      const countLabel = document.getElementById("list-modal-count");
      if (countLabel) {
        countLabel.textContent = `${customTickerListDraft.length} selected`;
      }
    }

    function syncListBuilderPreview() {
      const previewLabel = document.getElementById("list-modal-preview");
      if (previewLabel) {
        const listName = normalizeListName(customTickerListName);
        const tickersText = customTickerListDraft.length > 0
          ? customTickerListDraft.slice(0, 6).join(", ") + (customTickerListDraft.length > 6 ? ", ..." : "")
          : "No custom tickers selected yet";
        previewLabel.textContent = `${listName}: ${tickersText}`;
      }
    }

    function renderListBuilderModal() {
      const grid = document.getElementById("list-modal-grid");
      const visibleCountLabel = document.getElementById("list-modal-visible-count");
      const searchInput = document.getElementById("list-modal-search");
      const nameInput = document.getElementById("list-modal-name");
      const listSelect = getListBuilderListSelectNode();
      const exchangeButtons = document.querySelectorAll("[data-list-exchange]");
      const visible = getListBuilderVisibleTickers();

      if (searchInput && searchInput.value !== listBuilderSearch) {
        searchInput.value = listBuilderSearch;
      }
      if (nameInput && nameInput.value !== normalizeListName(customTickerListName)) {
        nameInput.value = normalizeListName(customTickerListName);
      }
      if (listSelect && listSelect.value !== normalizeListName(customTickerListDraftSourceName || customTickerListName)) {
        updateListBuilderListSelector();
      }
      exchangeButtons.forEach((btn) => {
        const btnExchange = normalizeExchangeFilter(btn.dataset.listExchange);
        const active = btnExchange === normalizeExchangeFilter(listBuilderExchange);
        btn.style.backgroundColor = active ? "#4f46e5" : "#1e293b";
        btn.style.color = active ? "#ffffff" : "#e2e8f0";
        btn.style.borderColor = active ? "rgba(165,180,252,0.9)" : "rgba(148,163,184,0.35)";
      });
      if (visibleCountLabel) {
        visibleCountLabel.textContent = `${visible.length} visible`;
      }
      if (!grid) {
        syncListBuilderCount();
        syncListBuilderPreview();
        return;
      }

      grid.innerHTML = "";
      if (visible.length === 0) {
        const empty = document.createElement("div");
        empty.className = "rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500";
        empty.textContent = "No tickers match the current filter.";
        grid.appendChild(empty);
        syncListBuilderCount();
        syncListBuilderPreview();
        return;
      }

      visible.forEach((item) => {
        const label = document.createElement("label");
        label.className = "flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm hover:border-indigo-300";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500";
        checkbox.value = item.ticker;
        checkbox.checked = customTickerListDraft.includes(item.ticker);
        checkbox.addEventListener("change", (event) => {
          const ticker = String(event.target.value || "").toUpperCase();
          if (event.target.checked) {
            if (!customTickerListDraft.includes(ticker)) {
              customTickerListDraft = sortTickersByUniverse([...customTickerListDraft, ticker]);
            }
          } else {
            customTickerListDraft = customTickerListDraft.filter((value) => value !== ticker);
          }
          syncListBuilderCount();
          syncListBuilderPreview();
        });

        const body = document.createElement("div");
        body.className = "min-w-0 flex-1";

        const topRow = document.createElement("div");
        topRow.className = "flex items-center justify-between gap-3";

        const tickerText = document.createElement("div");
        tickerText.className = "truncate text-sm font-bold text-slate-800";
        tickerText.textContent = item.label || item.name || item.ticker;

        const badge = document.createElement("span");
        badge.className = "rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-500";
        badge.textContent = item.ticker;

        topRow.appendChild(tickerText);
        topRow.appendChild(badge);
        body.appendChild(topRow);

        const sub = document.createElement("div");
        sub.className = "mt-0.5 text-[11px] text-slate-500";
        sub.textContent = [item.issuer, item.asset_class, item.region]
          .map((part) => String(part || "").trim())
          .filter(Boolean)
          .join(" Â· ") || item.ticker;
        body.appendChild(sub);

        label.appendChild(checkbox);
        label.appendChild(body);
        grid.appendChild(label);
      });

      syncListBuilderCount();
      syncListBuilderPreview();
    }

    function toggleVisibleListBuilderTickers(selectAll) {
      const visible = getListBuilderVisibleTickers().map((item) => item.ticker);
      const next = new Set(customTickerListDraft);
      visible.forEach((ticker) => {
        if (selectAll) {
          next.add(ticker);
        } else {
          next.delete(ticker);
        }
      });
      customTickerListDraft = sortTickersByUniverse(Array.from(next));
      renderListBuilderModal();
    }

    async function saveListEditor() {
      customTickerListDraft = sortTickersByUniverse(customTickerListDraft);
      const nameInput = document.getElementById("list-modal-name");
      const nextName = normalizeListName(nameInput ? nameInput.value : customTickerListName);
      const savedCollection = upsertCustomListEntry(customTickerListDraftSourceName, nextName, customTickerListDraft);
      const saved = await persistCustomTickerListsToServer(savedCollection);
      customTickerLists = Array.isArray(saved.lists) ? saved.lists : customTickerLists;
      customTickerList = sortTickersByUniverse(saved.tickers || []);
      customTickerListName = normalizeListName(saved.name || nextName);
      customTickerListActiveName = customTickerListName;
      customTickerListDraftSourceName = customTickerListName;
      tickerListMode = "custom";
      writeStickyValue(LAST_LIST_MODE_KEY, tickerListMode);
      updateListSelectChrome();
      updateBacktestRunButtonState();
      closeListEditorModal();
      showToast(
        saved.savedToServer
          ? `Saved ${customTickerList.length} tickers to ${customTickerListName}`
          : `Saved ${customTickerList.length} tickers locally as ${customTickerListName}, but could not update config JSON`,
        !saved.savedToServer
      );
    }

    function applyListSelectionMode(mode) {
      const normalized = String(mode || "custom").trim().toLowerCase();
      if (normalized === "edit") {
        openListEditorModal();
        return;
      }

      tickerListMode = "custom";
      if (customTickerList.length === 0) {
        openListEditorModal();
        return;
      }
      writeStickyValue(LAST_LIST_MODE_KEY, tickerListMode);
      updateListSelectChrome();
    }

    function getUniverseFilterParams() {
      const params = new URLSearchParams();
      const scope = normalizeScanScope(tickerScanScope);
      params.set("scan_scope", scope);
      const scopeTickers = getScopeTickers(scope);
      if ((scope === "list" || scope === "all_lists") && scopeTickers.length > 0) {
        params.set("ticker_list", scopeTickers.join(","));
      }
      return params;
    }

    function normalizeScreenDisqualifiers(raw = null) {
      const source = raw && typeof raw === "object" ? raw : {};
      return {
        exclude_overbought: Boolean(source.exclude_overbought),
        exclude_weak_liquidity: Boolean(source.exclude_weak_liquidity),
        exclude_unprofitable: Boolean(source.exclude_unprofitable),
      };
    }

    function readSavedScreenDisqualifiers() {
      try {
        const raw = localStorage.getItem(LAST_SCREEN_DISQUALIFIERS_KEY);
        if (!raw) {
          return normalizeScreenDisqualifiers();
        }
        return normalizeScreenDisqualifiers(JSON.parse(raw));
      } catch (err) {
        return normalizeScreenDisqualifiers();
      }
    }

    function persistScreenDisqualifiers() {
      try {
        localStorage.setItem(
          LAST_SCREEN_DISQUALIFIERS_KEY,
          JSON.stringify(normalizeScreenDisqualifiers(screenDisqualifiers))
        );
      } catch (err) {
        return;
      }
    }

    function syncScreenDisqualifierChrome() {
      const checkboxMap = {
        exclude_overbought: document.getElementById("disqualify-overbought"),
        exclude_weak_liquidity: document.getElementById("disqualify-weak-liquidity"),
        exclude_unprofitable: document.getElementById("disqualify-unprofitable"),
      };
      Object.entries(checkboxMap).forEach(([key, node]) => {
        if (node) {
          node.checked = Boolean(screenDisqualifiers[key]);
        }
      });
    }

    function getScreenDisqualifierParams() {
      const params = new URLSearchParams();
      Object.entries(normalizeScreenDisqualifiers(screenDisqualifiers)).forEach(([key, enabled]) => {
        if (enabled) {
          params.set(key, "true");
        }
      });
      return params;
    }

    function setScreenDisqualifier(key, enabled) {
      if (!Object.prototype.hasOwnProperty.call(screenDisqualifiers, key)) {
        return;
      }
      screenDisqualifiers = {
        ...screenDisqualifiers,
        [key]: Boolean(enabled),
      };
      persistScreenDisqualifiers();
      syncScreenDisqualifierChrome();
    }

    function readSavedScreenAutoExportEnabled() {
      try {
        return String(localStorage.getItem(LAST_SCREEN_AUTO_EXPORT_KEY) || "").trim().toLowerCase() === "true";
      } catch (err) {
        return false;
      }
    }

    function persistScreenAutoExportEnabled() {
      try {
        localStorage.setItem(LAST_SCREEN_AUTO_EXPORT_KEY, screenAutoExportEnabled ? "true" : "false");
      } catch (err) {
        return;
      }
    }

    function syncScreenAutoExportChrome() {
      const node = document.getElementById("auto-export-google-drive");
      if (node) {
        node.checked = Boolean(screenAutoExportEnabled);
      }
    }

    function setScreenAutoExportEnabled(enabled) {
      screenAutoExportEnabled = Boolean(enabled);
      persistScreenAutoExportEnabled();
      syncScreenAutoExportChrome();
    }

    const RANGE_PRESETS = [
      { days: 21, label: "1M", buttonId: "range-btn-1m" },
      { days: 63, label: "3M", buttonId: "range-btn-3m" },
      { days: 126, label: "6M", buttonId: "range-btn-6m" },
      { days: 365, label: "1Y", buttonId: "range-btn-1y" },
      { days: 365 * 2, label: "2Y", buttonId: "range-btn-2y" },
      { days: 365 * 3, label: "3Y", buttonId: "range-btn-3y" },
    ];
    const LAST_CHART_RANGE_KEY = "etf-discovery:last-chart-range-days";

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

    function getActiveEditorDsl() {
      const strategyEditor = document.getElementById("strategy-editor");
      return strategyEditor ? strategyEditor.value.trim() : "";
    }

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

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char] || char);
    }

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

    function getBacktestProgressNodes() {
      return {
        panel: document.getElementById("backtest-progress-panel"),
        detail: document.getElementById("backtest-progress-detail"),
        percent: document.getElementById("backtest-progress-percent"),
        contextLabel: document.getElementById("backtest-context-label"),
        contextText: document.getElementById("backtest-context-text"),
        contextBar: document.getElementById("backtest-context-bar"),
        globalLabel: document.getElementById("backtest-global-label"),
        globalText: document.getElementById("backtest-global-text"),
        globalBar: document.getElementById("backtest-global-bar"),
      };
    }

    function setBacktestProgress(state = {}) {
      const nodes = getBacktestProgressNodes();
      if (state.show === true && nodes.panel) {
        nodes.panel.classList.remove("hidden");
      } else if (state.show === false && nodes.panel) {
        nodes.panel.classList.add("hidden");
      }

      const contextPct = state.contextPct !== undefined
        ? Math.max(0, Math.min(100, Number(state.contextPct) || 0))
        : null;
      const globalPct = state.globalPct !== undefined
        ? Math.max(0, Math.min(100, Number(state.globalPct) || 0))
        : null;

      if (state.detail && nodes.detail) nodes.detail.textContent = state.detail;
      if (state.contextLabel && nodes.contextLabel) nodes.contextLabel.textContent = state.contextLabel;
      if (state.contextText && nodes.contextText) nodes.contextText.textContent = state.contextText;
      if (contextPct !== null && nodes.contextBar) nodes.contextBar.style.width = `${contextPct}%`;
      if (state.contextWorking !== undefined && nodes.contextBar) {
        nodes.contextBar.classList.toggle("animate-pulse", Boolean(state.contextWorking));
      }

      if (state.globalLabel && nodes.globalLabel) nodes.globalLabel.textContent = state.globalLabel;
      if (state.globalText && nodes.globalText) nodes.globalText.textContent = state.globalText;
      if (globalPct !== null && nodes.globalBar) nodes.globalBar.style.width = `${globalPct}%`;
      if (state.globalWorking !== undefined && nodes.globalBar) {
        nodes.globalBar.classList.toggle("animate-pulse", Boolean(state.globalWorking));
      }

      const visiblePct = globalPct !== null ? globalPct : contextPct;
      if (visiblePct !== null && nodes.percent) {
        nodes.percent.textContent = `${Math.round(visiblePct)}%`;
      }
    }

    function setShortlistEmptyState(message) {
      const emptyState = document.getElementById("shortlist-empty");
      const content = document.getElementById("shortlist-content");
      const grid = document.getElementById("shortlist-grid");
      if (grid) {
        grid.innerHTML = "";
      }
      if (emptyState) {
        emptyState.textContent = message;
        emptyState.classList.remove("hidden");
      }
      if (content) {
        content.classList.add("hidden");
      }
    }

    function getShortlistLabelClasses(label) {
      if (label === "Buy") {
        return "bg-emerald-100 text-emerald-700 border border-emerald-200";
      }
      if (label === "Watch") {
        return "bg-amber-100 text-amber-700 border border-amber-200";
      }
      return "bg-rose-100 text-rose-700 border border-rose-200";
    }

    function formatShortlistEntryAge(days) {
      if (days === null || days === undefined || Number.isNaN(Number(days))) {
        return "No fresh signal";
      }
      const value = Number(days);
      return value === 0 ? "Triggered today" : `${value} trading days ago`;
    }

    function updateShortlistFilterButtons() {
      ["All", "Buy", "Watch", "Skip"].forEach((label) => {
        const button = document.getElementById(`shortlist-filter-${label.toLowerCase()}`);
        if (!button) {
          return;
        }
        const isActive = shortlistFilter === label;
        button.className = `rounded-full border px-3 py-1.5 text-xs font-bold transition-all ${
          isActive
            ? "border-sky-300 bg-sky-600 text-white shadow-sm"
            : "border-slate-300 bg-white text-slate-700"
        }`;
      });
    }

    function getVisibleShortlistRows() {
      if (shortlistFilter === "All") {
        return shortlistRows;
      }
      return shortlistRows.filter((row) => row.label === shortlistFilter);
    }

    function renderShortlistRows() {
      const grid = document.getElementById("shortlist-grid");
      const emptyState = document.getElementById("shortlist-empty");
      const content = document.getElementById("shortlist-content");
      const countEl = document.getElementById("shortlist-count");

      if (!grid || !emptyState || !content || !countEl) {
        return;
      }

      updateShortlistFilterButtons();

      if (shortlistRows.length === 0) {
        setShortlistEmptyState("No shortlist artifacts were available yet.");
        return;
      }

      const rows = getVisibleShortlistRows();
      countEl.textContent = String(rows.length);
      grid.innerHTML = "";

      rows.forEach((row, idx) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "ticker-card text-left rounded-xl bg-white shadow border border-slate-200 p-4 hover:border-sky-300 hover:shadow-lg transition-all";
        card.onclick = () => {
          showTab("screener");
          loadChart(row.ticker);
        };

        const reasons = Array.isArray(row.reasons) ? row.reasons.slice(0, 3) : [];
        const reasonHtml = reasons.length
          ? reasons.map((reason) => `<div class="text-[11px] text-slate-500">â€¢ ${reason}</div>`).join("")
          : '<div class="text-[11px] text-slate-400">No explanation available yet.</div>';

        card.innerHTML = `
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-bold text-sky-500">#${idx + 1}</span>
                <span class="font-bold text-slate-900 text-lg leading-none">${row.ticker}</span>
                <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${getShortlistLabelClasses(row.label)}">${row.label}</span>
              </div>
              <div class="mt-1 text-sm text-slate-600 truncate">${row.name || row.ticker}</div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-[10px] uppercase tracking-wide text-slate-400 font-bold">Final Score</div>
              <div class="text-2xl font-bold text-slate-900">${Number(row.final_score || 0).toFixed(1)}</div>
            </div>
          </div>
          <div class="mt-3 grid grid-cols-2 gap-3 text-xs">
            <div class="rounded-lg bg-slate-50 px-3 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Profile</div>
              <div class="mt-1 font-semibold text-slate-700">${row.asset_class || "ETF"} Â· ${row.region || "Unknown"}</div>
              <div class="text-slate-500">${row.issuer || "Unknown issuer"}</div>
            </div>
            <div class="rounded-lg bg-slate-50 px-3 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Timing</div>
              <div class="mt-1 font-semibold text-slate-700">${formatShortlistEntryAge(row.recent_entry_days)}</div>
              <div class="text-slate-500">Close ${Number(row.close || 0).toFixed(2)} Â· ${(Number(row.volume || 0) / 1000).toFixed(0)}K vol</div>
            </div>
          </div>
          <div class="mt-3 grid grid-cols-3 gap-2 text-xs">
            <div class="rounded-lg border border-slate-200 px-2 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Product</div>
              <div class="mt-1 text-lg font-bold text-slate-800">${Number(row.product_score || 0).toFixed(0)}</div>
            </div>
            <div class="rounded-lg border border-slate-200 px-2 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Exposure</div>
              <div class="mt-1 text-lg font-bold text-slate-800">${Number(row.exposure_score || 0).toFixed(0)}</div>
            </div>
            <div class="rounded-lg border border-slate-200 px-2 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Technical</div>
              <div class="mt-1 text-lg font-bold text-slate-800">${Number(row.technical_score || 0).toFixed(0)}</div>
            </div>
          </div>
          <div class="mt-3 space-y-1">
            ${reasonHtml}
          </div>
          <div class="mt-3 pt-3 border-t border-slate-100 text-[11px] font-bold text-sky-600 uppercase tracking-wide">
            Open chart drill-down
          </div>
        `;
        grid.appendChild(card);
      });

      if (rows.length === 0) {
        grid.innerHTML = `
          <div class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500 xl:col-span-2">
            No ${shortlistFilter.toLowerCase()} ideas in the current shortlist snapshot.
          </div>
        `;
        emptyState.classList.add("hidden");
        content.classList.remove("hidden");
        return;
      }

      emptyState.classList.add("hidden");
      content.classList.remove("hidden");
    }

    function setShortlistFilter(label) {
      shortlistFilter = label;
      renderShortlistRows();
    }
    function updateTabChrome(tab) {
      const screenerControls = document.getElementById("nav-screener-controls");
      const context = document.getElementById("nav-tab-context");
      if (screenerControls) {
        screenerControls.classList.toggle("hidden", tab !== "screener");
      }
      if (!context) {
        return;
      }
      if (tab === "shortlist") {
        context.textContent = "Shortlist: browse ideas, then open the chart";
      } else if (tab === "query") {
        context.textContent = "Query: direct data exploration over the stored backbone";
      } else if (tab === "backtest") {
        context.textContent = "Backtester: choose what to evaluate below";
      } else {
        context.textContent = "Screener controls: pick a strategy, then click Run Screener";
      }
    }
    async function loadMarketStatus(source = tickerScanScope) {
      const marketStatus = document.getElementById("shortlist-market-status");
      if (!marketStatus) {
        return null;
      }

      try {
        const normalizedSource = normalizeScanScope(source);
        const resp = await fetch(`/api/market-status?stale_after_days=0&source=${encodeURIComponent(normalizedSource)}`);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Market status request failed");
        }

        if (data.is_stale) {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-amber-600";
          marketStatus.textContent = `Market data needs top-up Â· latest ${data.latest_market_date || "unknown"} Â· stale ${Number(data.stale_tickers || 0)} Â· missing ${Number(data.missing_tickers || 0)}`;
        } else {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-emerald-600";
          marketStatus.textContent = `Market data fresh through ${data.latest_market_date || "unknown"} Â· ${Number(data.fresh_tickers || data.tracked_tickers || 0)} active tickers`;
        }
        return data;
      } catch (err) {
        marketStatus.className = "text-xs font-bold uppercase tracking-wide text-rose-600";
        marketStatus.textContent = "Could not determine market data freshness";
        return null;
      }
    }

    async function ensureGuiMarketBackbone(options = {}) {
      const allowRefresh = options.allowRefresh !== false;
      const status = await loadMarketStatus(tickerScanScope);
      let refreshed = false;
      if (allowRefresh && status && status.is_stale && !marketDataAutoRefreshAttempted) {
        marketDataAutoRefreshAttempted = true;
        await refreshMarketData();
        refreshed = true;
      }
      return { status, refreshed };
    }

    async function ensureFreshMarketData() {
      return ensureGuiMarketBackbone();
    }

    function showTab(tab) {
      tab = normalizeDashboardTab(tab);
      console.log('[TABBAR] Switching to tab:', tab);
      fetch('/api/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level: 'info', message: `[TABBAR] Switching to tab: ${tab}` })
      });
      writeStickyValue(LAST_DASHBOARD_TAB_KEY, tab);
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
      });
      getDashboardTabs().forEach((section) => section.classList.add('hidden'));
      const activeBtn = document.getElementById(`tab-btn-${tab}`);
      if (activeBtn) {
        activeBtn.classList.add('active');
      }
      const activeSection = document.getElementById(`tab-${tab}`);
      if (activeSection) {
        activeSection.classList.remove('hidden');
      }
      updateTabChrome(tab);
      if (tab === 'backtest') {
        updateBacktestRunButtonState();
      } else if (tab === 'query') {
        loadQueryCatalog().catch((err) => {
          console.warn("Query catalog failed to load", err);
          setQueryStatus("Could not load query catalog.", "rose");
        });
      } else if (tab === 'shortlist') {
        ensureGuiMarketBackbone().catch((err) => {
          console.warn("Auto-refresh check failed", err);
        });
        loadShortlist();
      }
    }

    window.showTab = showTab;

    const DEFAULT_DASHBOARD_TAB = "screener";
    let dashboardDefaultTabApplied = false;

    function applyDefaultDashboardTab() {
      if (dashboardDefaultTabApplied) {
        return;
      }
      const tabsRoot = document.getElementById("dashboard-tabs");
      if (!tabsRoot) {
        return;
      }
      dashboardDefaultTabApplied = true;
      const pendingTab = normalizeDashboardTab(window.__dashboardPendingTab || "");
      if (window.__dashboardPendingTab) {
        window.__dashboardPendingTab = null;
        showTab(pendingTab);
        return;
      }
      const savedTab = normalizeDashboardTab(readStickyValue(LAST_DASHBOARD_TAB_KEY, DEFAULT_DASHBOARD_TAB));
      showTab(savedTab);
    }

    function resetDashboardTabPreference() {
      dashboardDefaultTabApplied = false;
      showTab(DEFAULT_DASHBOARD_TAB);
    }

    async function refreshMarketData() {
      const source = normalizeScanScope(tickerScanScope);
      const marketRefreshBtn = document.getElementById("market-refresh-btn");
      const shortlistRefreshBtn = document.getElementById("shortlist-refresh-btn");
      const marketStatus = document.getElementById("shortlist-market-status");
      const shortlistStatus = document.getElementById("shortlist-status");

      if (marketRefreshBtn) {
        marketRefreshBtn.disabled = true;
        marketRefreshBtn.textContent = "Refreshing Data...";
      }
      if (shortlistRefreshBtn) {
        shortlistRefreshBtn.disabled = true;
      }
      if (marketStatus) {
        marketStatus.className = "text-xs font-bold uppercase tracking-wide text-indigo-600";
        const sourceLabel = source === "sweden"
          ? "Sweden"
          : source === "nasdaq"
          ? "Nasdaq"
          : source === "list"
          ? "saved list"
          : source === "all_lists"
          ? "all saved lists"
          : "Xetra";
        marketStatus.textContent = `Topping up ${sourceLabel} market data and rebuilding shortlist...`;
      }
      if (shortlistStatus) {
        shortlistStatus.textContent = "Waiting for fresh market data...";
      }

      try {
        setNavScanProgress({
          show: true,
          contextLabel: "Market",
          contextText: "Checking...",
          contextPct: 0,
          contextWorking: false,
        });
        startJobProgressPolling("market-refresh", "Global");
        const resp = await fetch(`/api/market-data/refresh?depth=400&max_workers=8&force=true&stale_after_days=0&source=${encodeURIComponent(source)}`, {
          method: "POST",
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Market refresh failed");
        }

        setNavScanProgress({
          show: true,
          contextLabel: "Market",
          contextText: "Rebuilding...",
          contextPct: 94,
          contextWorking: true,
        });
        shortlistLoaded = false;
        await loadMarketStatus();
        await loadShortlist(true);
        setNavScanProgress({
          show: true,
          contextLabel: "Market",
          contextText: "100%",
          contextPct: 100,
          contextWorking: false,
        });
        showToast(`Market refresh: ${Number(data.refreshed || 0)} updated, ${Number(data.failed || 0)} failed`);
      } catch (err) {
        if (marketStatus) {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-rose-600";
          marketStatus.textContent = `Market refresh failed: ${err.message || err}`;
        }
        setNavScanProgress({
          show: true,
          contextLabel: "Market",
          contextText: "FAILED",
          contextPct: 100,
          contextWorking: false,
        });
        showToast(`Market refresh failed: ${err.message || err}`, true);
      } finally {
        stopJobProgressPolling();
        setNavScanProgress({
          show: false,
          contextLabel: "Market",
          contextText: "0%",
          contextPct: 0,
          contextWorking: false,
          globalLabel: "Global",
          globalText: "0%",
          globalPct: 0,
          globalWorking: false,
        });
        if (marketRefreshBtn) {
          marketRefreshBtn.disabled = false;
          marketRefreshBtn.textContent = "Refresh Market Data";
        }
        if (shortlistRefreshBtn) {
          shortlistRefreshBtn.disabled = false;
        }
      }
    }

    async function loadShortlist(forceRefresh = false) {
      const refreshBtn = document.getElementById("shortlist-refresh-btn");
      const status = document.getElementById("shortlist-status");
      const asOfEl = document.getElementById("shortlist-as-of");
      const buyEl = document.getElementById("shortlist-buy-count");
      const watchEl = document.getElementById("shortlist-watch-count");
      const skipEl = document.getElementById("shortlist-skip-count");

      if (shortlistLoaded && !forceRefresh) {
        return;
      }

      setShortlistEmptyState(forceRefresh ? "Refreshing shortlist snapshot..." : "Loading shortlist snapshot...");
      if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.textContent = forceRefresh ? "Refreshing..." : "Loading...";
      }
      if (status) {
        status.textContent = forceRefresh ? "Rebuilding shortlist artifacts..." : "Loading cached shortlist snapshot...";
      }

      try {
        await ensureGuiMarketBackbone();
        const url = `/api/shortlist?limit=60${forceRefresh ? "&refresh=true" : ""}`;
        const resp = await fetch(url);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Shortlist request failed");
        }

        const rows = Array.isArray(data.rows) ? data.rows : [];
        shortlistRows = rows;
        asOfEl.textContent = data.as_of_date || "-";
        buyEl.textContent = String((data.labels && data.labels.Buy) || 0);
        watchEl.textContent = String((data.labels && data.labels.Watch) || 0);
        skipEl.textContent = String((data.labels && data.labels.Skip) || 0);

        if (rows.length === 0) {
          setShortlistEmptyState("No shortlist artifacts were available yet.");
          shortlistLoaded = true;
          return;
        }

        renderShortlistRows();
        if (status) {
          status.textContent = `Snapshot date: ${data.as_of_date || "unknown"}`;
        }
        shortlistLoaded = true;
      } catch (err) {
        setShortlistEmptyState(`Shortlist error: ${err.message || err}`);
        if (status) {
          status.textContent = "Shortlist load failed";
        }
      } finally {
        if (refreshBtn) {
          refreshBtn.disabled = false;
          refreshBtn.textContent = "Refresh Shortlist";
        }
      }
    }

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
      if ((scope === "list" || scope === "all_lists") && !universeParams.get("ticker_list")) {
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
      const sharpeValues = metricRows.map((row) => Number(row.sharpe)).filter(Number.isFinite);
      const qualityValues = metricRows.map((row) => Number(row.quality_score)).filter(Number.isFinite);
      const avg = (values) => values.length
        ? values.reduce((sum, value) => sum + value, 0) / values.length
        : 0;
      const strategyNode = document.getElementById("bt-strategy");
      const countNode = document.getElementById("bt-count");
      const bestQualityNode = document.getElementById("bt-best-quality");
      const avgReturnNode = document.getElementById("bt-avg-return");
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
      if (avgSharpeNode) {
        avgSharpeNode.textContent = avg(sharpeValues).toFixed(2);
      }
    }

    function renderBacktestTable(rows) {
      const body = document.getElementById("backtest-table-body");
      if (!body) {
        return;
      }
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

    function populateBacktestAxisControls(metrics) {
      backtestMetricCatalog = Array.isArray(metrics) && metrics.length > 0 ? metrics : backtestDefaultMetrics();
      const xSelect = document.getElementById("backtest-x-axis");
      const ySelect = document.getElementById("backtest-y-axis");
      if (!xSelect || !ySelect) {
        return;
      }

      const previousX = xSelect.value || "sharpe";
      const previousY = ySelect.value || "return_pct";
      [xSelect, ySelect].forEach((select) => {
        select.innerHTML = "";
        backtestMetricCatalog.forEach((metric) => {
          const opt = document.createElement("option");
          opt.value = metric.key;
          opt.textContent = metric.label;
          select.appendChild(opt);
        });
      });
      const keys = new Set(backtestMetricCatalog.map((metric) => metric.key));
      xSelect.value = keys.has(previousX) ? previousX : "sharpe";
      ySelect.value = keys.has(previousY) ? previousY : "return_pct";
      if (!keys.has(xSelect.value)) {
        xSelect.value = backtestMetricCatalog[0]?.key || "";
      }
      if (!keys.has(ySelect.value)) {
        ySelect.value = backtestMetricCatalog[1]?.key || backtestMetricCatalog[0]?.key || "";
      }
    }

    function renderBacktestScatter() {
      const chartDiv = document.getElementById("backtest-chart");
      if (!chartDiv || !window.Plotly) {
        return;
      }
      const rows = Array.isArray(backtestTradeDotRows) && backtestTradeDotRows.length > 0
        ? backtestTradeDotRows.filter((row) => !isBacktestTickerExcluded(row.ticker))
        : [];
      if (rows.length === 0) {
        Plotly.purge(chartDiv);
        return;
      }

      const xKey = document.getElementById("backtest-x-axis")?.value || "sharpe";
      const yKey = document.getElementById("backtest-y-axis")?.value || "return_pct";
      const colorBy = "strategy";
      const groups = new Map();
      rows.forEach((row) => {
        const x = Number(row[xKey]);
        const y = Number(row[yKey]);
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
          return;
        }
        const group = String(row[colorBy] || "Other");
        if (!groups.has(group)) {
          groups.set(group, []);
        }
        groups.get(group).push(row);
      });
      const strategyNames = Array.from(groups.keys());

      const traces = Array.from(groups.entries()).map(([group, groupRows]) => ({
        type: "scatter",
        mode: "markers",
        name: group,
        x: groupRows.map((row) => Number(row[xKey])),
        y: groupRows.map((row) => Number(row[yKey])),
        text: groupRows.map((row) => `${row.strategy} / ${row.ticker}`),
        customdata: groupRows.map((row) => [
          row.strategy,
          row.ticker,
          row.exchange,
          Number(row.quality_score || 0).toFixed(2),
          Number(row.return_pct || 0).toFixed(2),
          Number(row.sharpe || 0).toFixed(2),
          Number(row.win_rate_pct || 0).toFixed(2),
          Number(row.max_dd_pct || 0).toFixed(2),
          Number(row.trades || 0),
          Number(row.days_since_entry || 0),
          Number(row.trade_index || 0),
          Number(row.trade_gain_pct || 0).toFixed(2),
          row.estimated ? "estimated avg" : "actual",
          row.sell_date || "",
        ]),
        marker: {
          size: groupRows.map((row) => getBacktestTradeDotSize(row)),
          color: getBacktestGroupColor(colorBy === "strategy" ? group : groupRows[0]?.strategy || group, strategyNames),
          opacity: 0.78,
          line: { color: "#ffffff", width: 1 },
        },
        hovertemplate:
          "<b>%{customdata[0]}</b><br>" +
          "Ticker: %{customdata[1]}<br>" +
          "Universe: %{customdata[2]}<br>" +
          `${getBacktestMetricLabel(xKey)}: %{x:.2f}<br>` +
          `${getBacktestMetricLabel(yKey)}: %{y:.2f}<br>` +
          "Quality: %{customdata[3]}<br>" +
          "Return: %{customdata[4]}%<br>" +
          "Sharpe: %{customdata[5]}<br>" +
          "Win Rate: %{customdata[6]}%<br>" +
          "Max DD: %{customdata[7]}%<br>" +
          "Trades: %{customdata[8]}<br>" +
          "Trade #: %{customdata[10]}<br>" +
          "Trade gain: %{customdata[11]}% (%{customdata[12]})<br>" +
          "Exit: %{customdata[13]}<br>" +
          "Days Since Entry: %{customdata[9]}<extra></extra>",
      }));

      Plotly.newPlot(chartDiv, traces, {
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        margin: { l: 60, r: 20, t: 24, b: 55 },
        xaxis: { title: getBacktestMetricLabel(xKey), zeroline: true, automargin: true },
        yaxis: { title: getBacktestMetricLabel(yKey), zeroline: true, automargin: true },
        legend: { orientation: "h", y: -0.24 },
      }, {
        responsive: true,
        displayModeBar: false,
        displaylogo: false,
      });
    }

    function renderBacktestStructureRadar() {
      const chartDiv = document.getElementById("backtest-structure-chart");
      if (!chartDiv || !window.Plotly) {
        return;
      }
      const axisCatalog = normalizeBacktestStructureAxisCatalog(backtestStrategyAxisCatalog);
      const summaries = (Array.isArray(backtestStrategySummaries) ? backtestStrategySummaries : [])
        .map((summary, index) => normalizeBacktestStrategySummary(summary, index, axisCatalog))
        .filter((summary) => summary.strategy);
      if (!summaries.length) {
        setBacktestStructurePanelVisible(false);
        Plotly.purge(chartDiv);
        return;
      }
      setBacktestStructurePanelVisible(true);

      const sorted = [...summaries].sort((left, right) => (
        Number(right.structure_score || 0) - Number(left.structure_score || 0)
      ));
      const strategyNames = sorted.map((item) => item.strategy);
      const axisLabelsByKey = new Map(axisCatalog.map((axis) => [axis.key, axis.label]));
      const maxAxis = axisCatalog.reduce((max, axis) => Math.max(max, Number(axis.max || 10) || 10), 10);
      const traces = sorted.map((summary) => {
        const axisOrder = Array.isArray(summary.axis_order) && summary.axis_order.length > 0
          ? summary.axis_order.filter((key) => axisLabelsByKey.has(key))
          : axisCatalog.map((axis) => axis.key);
        const theta = axisOrder.map((key) => axisLabelsByKey.get(key) || key);
        const r = axisOrder.map((key) => Number(summary.structure_axes?.[key] || 0));
        const closedTheta = theta.concat(theta[0] || "");
        const closedR = r.concat(r[0] ?? 0);
        const tags = Array.isArray(summary.structure_tags) ? summary.structure_tags : [];
        return {
          type: "scatterpolar",
          mode: "lines+markers",
          fill: "toself",
          name: summary.strategy,
          theta: closedTheta,
          r: closedR,
          line: {
            color: getBacktestStrategyColor(summary.strategy, strategyNames),
            width: 2.5,
          },
          marker: {
            color: getBacktestStrategyColor(summary.strategy, strategyNames),
            size: 6,
          },
          opacity: 0.55,
          customdata: closedTheta.map((axisLabel, idx) => [
            summary.strategy,
            Number(summary.structure_score || 0).toFixed(2),
            axisLabel,
            Number(closedR[idx] || 0).toFixed(2),
            tags.join(", "),
          ]),
          hovertemplate:
            "<b>%{customdata[0]}</b><br>" +
            "Structure Score: %{customdata[1]}<br>" +
            "Axis: %{customdata[2]}<br>" +
            "Value: %{customdata[3]}<br>" +
            "Tags: %{customdata[4]}<extra></extra>",
        };
      });

      Plotly.newPlot(chartDiv, traces, {
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        margin: { l: 40, r: 40, t: 28, b: 28 },
        legend: { orientation: "h", y: -0.12 },
        polar: {
          bgcolor: "#ffffff",
          radialaxis: {
            visible: true,
            range: [0, maxAxis],
            tickfont: { size: 10 },
            gridcolor: "#dbe4f0",
            linecolor: "#cbd5e1",
          },
          angularaxis: {
            tickfont: { size: 11, color: "#475569" },
            gridcolor: "#e2e8f0",
            linecolor: "#cbd5e1",
          },
        },
      }, {
        responsive: true,
        displayModeBar: false,
        displaylogo: false,
      });
    }

    function renderBacktestBehaviorRadar() {
      const chartDiv = document.getElementById("backtest-behavior-chart");
      if (!chartDiv || !window.Plotly) {
        return;
      }
      const axisCatalog = backtestDefaultBehaviorAxisCatalog();
      const summaries = (Array.isArray(backtestStrategySummaries) ? backtestStrategySummaries : [])
        .map((summary, index) => normalizeBacktestStrategySummary(summary, index, backtestStrategyAxisCatalog))
        .filter((summary) => summary.strategy && summary.has_behavior_data);
      if (!summaries.length) {
        setBacktestBehaviorPanelVisible(false);
        Plotly.purge(chartDiv);
        return;
      }
      setBacktestBehaviorPanelVisible(true);

      const sorted = [...summaries]
        .map((summary) => ({
          ...summary,
          behavior_profile: summary.behavior_profile || deriveBacktestBehaviorProfile(summary),
        }))
        .sort((left, right) => (
          Number(right.behavior_profile?.behavior_score || 0) - Number(left.behavior_profile?.behavior_score || 0)
        ));
      const strategyNames = sorted.map((item) => item.strategy);
      const axisLabelsByKey = new Map(axisCatalog.map((axis) => [axis.key, axis.label]));
      const traces = sorted.map((summary) => {
        const profile = summary.behavior_profile || deriveBacktestBehaviorProfile(summary);
        const axisOrder = Array.isArray(profile.axis_order) && profile.axis_order.length > 0
          ? profile.axis_order.filter((key) => axisLabelsByKey.has(key))
          : axisCatalog.map((axis) => axis.key);
        const theta = axisOrder.map((key) => axisLabelsByKey.get(key) || key);
        const r = axisOrder.map((key) => Number(profile.behavior_axes?.[key] || 0));
        const closedTheta = theta.concat(theta[0] || "");
        const closedR = r.concat(r[0] ?? 0);
        const closedKeys = axisOrder.concat(axisOrder[0] || "");
        return {
          type: "scatterpolar",
          mode: "lines+markers",
          fill: "toself",
          name: summary.strategy,
          theta: closedTheta,
          r: closedR,
          line: {
            color: getBacktestStrategyColor(summary.strategy, strategyNames),
            width: 2.5,
          },
          marker: {
            color: getBacktestStrategyColor(summary.strategy, strategyNames),
            size: 6,
          },
          opacity: 0.55,
          customdata: closedTheta.map((axisLabel, idx) => {
            const axisKey = closedKeys[idx] || axisOrder[0] || "";
            const rawValue = profile.raw_metrics?.[axisKey] ?? 0;
            return [
              summary.strategy,
              Number(profile.behavior_score || 0).toFixed(2),
              axisLabel,
              Number(closedR[idx] || 0).toFixed(2),
              formatBacktestBehaviorRawMetric(axisKey, rawValue),
            ];
          }),
          hovertemplate:
            "<b>%{customdata[0]}</b><br>" +
            "Behavior Score: %{customdata[1]}<br>" +
            "Axis: %{customdata[2]}<br>" +
            "Normalized: %{customdata[3]} / 10<br>" +
            "Raw: %{customdata[4]}<extra></extra>",
        };
      });

      Plotly.newPlot(chartDiv, traces, {
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        margin: { l: 40, r: 40, t: 28, b: 28 },
        legend: { orientation: "h", y: -0.12 },
        polar: {
          bgcolor: "#ffffff",
          radialaxis: {
            visible: true,
            range: [0, 10],
            tickfont: { size: 10 },
            gridcolor: "#dbe4f0",
            linecolor: "#cbd5e1",
          },
          angularaxis: {
            tickfont: { size: 11, color: "#475569" },
            gridcolor: "#e2e8f0",
            linecolor: "#cbd5e1",
          },
        },
      }, {
        responsive: true,
        displayModeBar: false,
        displaylogo: false,
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

      if (backtestSourceMode === "saved" && !activeSavedStrategy) {
        setBacktestEmptyState("Select a saved strategy first, then open Backtester to score it.");
        return;
      }
      if (backtestSourceMode === "editor" && !editorDsl) {
        setBacktestEmptyState("Editor Draft is selected, but the Labs editor is empty.");
        return;
      }
      if (!tickerUniverseExplicitlyChosen) {
        setBacktestEmptyState("Choose a ticker universe first before running Backtester.");
        return;
      }
      const universeParams = getUniverseFilterParams();
      const chosenScope = universeParams.get("scan_scope");
      if ((chosenScope === "list" || chosenScope === "all_lists") && !universeParams.get("ticker_list")) {
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
        await ensureGuiMarketBackbone({ allowRefresh: false });
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
        const data = await resp.json();
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
        document.getElementById("bt-avg-sharpe").textContent = Number(data.summary?.avg_sharpe || 0).toFixed(2);
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
    // Show default tab on load
    document.addEventListener('DOMContentLoaded', async function() {
      console.log('[TABBAR] Tab bar rendered');
      fetch('/api/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level: 'info', message: '[TABBAR] Tab bar rendered' })
      });
      tickerScanScope = normalizeScanScope(readStickyValue(LAST_SCAN_SCOPE_KEY, "xetra"));
      tickerUniverseExplicitlyChosen = false;
      screenDisqualifiers = readSavedScreenDisqualifiers();
      syncScreenDisqualifierChrome();
      screenAutoExportEnabled = readSavedScreenAutoExportEnabled();
      syncScreenAutoExportChrome();
      updateScanScopeChrome();
      updateRangeChrome();
      updateListSelectChrome();
      await ensureTickerUniverseLoaded();
      const loadedList = await loadCustomTickerListFromServer();
      customTickerLists = Array.isArray(loadedList.lists) ? loadedList.lists : [];
      customTickerListActiveName = normalizeListName(loadedList.active_name || loadedList.name || readCustomTickerListName());
      customTickerList = Array.isArray(loadedList.tickers) ? loadedList.tickers : [];
      customTickerListName = customTickerListActiveName;
      updateListSelectChrome();
      const tickerSelect = document.getElementById("ticker-select");
      if (tickerSelect) {
        tickerSelectLastValue = readStickyValue(LAST_TICKER_SELECT_KEY, tickerSelect.value || "");
        renderTickerSelectOptions({ preserveSelection: true });
        tickerSelect.addEventListener("change", (event) => {
          storeTickerSelection(event.target.value);
        });
      }
      applyDefaultDashboardTab();
    });
    applyDefaultDashboardTab();
    let currentTicker = "";
    let currentStrategy = "";
    let sourceStrategyName = ""; // tracks what strategy is being modified
    let scanAbortController = null;
    let navScanProgressPoller = null;
    let navScanProgressJob = null;
    let lastScreenMatches = [];
    let lastScreenMeta = {
      strategy_name: "",
      scan_scope: "",
      exchange: "",
      ticker_list: "",
      disqualifiers: normalizeScreenDisqualifiers(),
    };
    let exportTopMatchesInFlight = false;
    const LAST_COMPLETED_STRATEGY_KEY = "etf-discovery:last-completed-strategy";

    // --- Console Log Capture System ---
    const consoleLogs = [];
    const maxLogsBeforeSend = 50;
    
    function setupConsoleCapture() {
      const originalLog = console.log;
      const originalError = console.error;
      const originalWarn = console.warn;
      const originalInfo = console.info;
      
      const captureLog = (level, args) => {
        const timestamp = new Date().toISOString();
        const message = args.map(arg => {
          if (typeof arg === 'object') {
            try { return JSON.stringify(arg); } catch { return String(arg); }
          }
          return String(arg);
        }).join(' ');
        
        consoleLogs.push({ timestamp, level, message });
        if (consoleLogs.length >= maxLogsBeforeSend) {
          flushConsoleLogs();
        }
      };
      
      console.log = function(...args) {
        originalLog.apply(console, args);
        captureLog('LOG', args);
      };
      
      console.error = function(...args) {
        originalError.apply(console, args);
        captureLog('ERROR', args);
      };
      
      console.warn = function(...args) {
        originalWarn.apply(console, args);
        captureLog('WARN', args);
      };
      
      console.info = function(...args) {
        originalInfo.apply(console, args);
        captureLog('INFO', args);
      };
      
      // Flush remaining logs on page unload
      window.addEventListener('beforeunload', flushConsoleLogs);
      
      // Flush logs every 30 seconds
      setInterval(flushConsoleLogs, 30000);
    }
    
    async function flushConsoleLogs() {
      if (consoleLogs.length === 0) return;
      const logsToSend = [...consoleLogs];
      consoleLogs.length = 0;
      
      try {
        await fetch('/api/log/console', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ logs: logsToSend })
        });
      } catch (err) {
        // Silently fail to avoid infinite loops if logging fails
      }
    }
    
    // Start capturing console logs immediately
    setupConsoleCapture();

    // --- Toast notification ---
    function showToast(msg, isError = false) {
      const t = document.createElement("div");
      t.textContent = msg;
      t.className = `fixed bottom-6 right-6 ${isError ? 'bg-red-600' : 'bg-emerald-600'} text-white py-2 px-4 rounded-lg shadow-lg z-[200] text-sm font-bold transition-opacity`;
      document.body.appendChild(t);
      setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 400); }, 2800);
    }

    function saveLastCompletedStrategy(strategyName) {
      try {
        if (strategyName) {
          localStorage.setItem(LAST_COMPLETED_STRATEGY_KEY, strategyName);
        } else {
          localStorage.removeItem(LAST_COMPLETED_STRATEGY_KEY);
        }
      } catch (err) {
        console.warn("Could not persist strategy selection", err);
      }
    }

    function loadLastCompletedStrategy() {
      try {
        return localStorage.getItem(LAST_COMPLETED_STRATEGY_KEY) || "";
      } catch (err) {
        console.warn("Could not read saved strategy selection", err);
        return "";
      }
    }

    function getStrategySelects() {
      return ["strategy-select"]
        .map((id) => document.getElementById(id))
        .filter(Boolean);
    }

    function syncStrategySelections(strategyName, { syncBacktestCheckboxes = true } = {}) {
      const value = strategyName || "";
      getStrategySelects().forEach((select) => {
        const hasOption = !value || Array.from(select.options).some((opt) => opt.value === value);
        select.value = hasOption ? value : "";
      });
      if (syncBacktestCheckboxes) {
        document.querySelectorAll(".backtest-strategy-checkbox").forEach((input) => {
          input.checked = value ? input.value === value : false;
        });
      }
      updateBacktestStrategyCount();
      syncBacktestStrategyCheckboxChrome();
    }

    function renderBacktestStrategyChooser(strategies, selectedName = "") {
      const list = document.getElementById("backtest-strategy-list");
      if (!list) {
        return;
      }
      list.innerHTML = "";
      strategies.forEach((strategy) => {
        const label = document.createElement("label");
        label.className = "flex items-center gap-2 border-b border-slate-100 px-3 py-2 last:border-b-0 hover:bg-slate-50";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.className = "backtest-strategy-checkbox h-4 w-4 rounded border-slate-300 text-indigo-600";
        input.value = strategy;
        input.checked = Boolean(selectedName && selectedName === strategy);
        input.addEventListener("change", handleBacktestStrategyChooserChange);

        const text = document.createElement("span");
        text.className = "truncate";
        text.textContent = strategy;

        label.appendChild(input);
        label.appendChild(text);
        list.appendChild(label);
      });
      updateBacktestStrategyCount();
      syncBacktestStrategyCheckboxChrome();
      bindBacktestStrategyChooserControls();
    }

    async function restoreLastCompletedStrategy() {
      const strategySelect = document.getElementById("strategy-select");
      if (!strategySelect) {
        return "";
      }

      const savedStrategy = loadLastCompletedStrategy();
      if (!savedStrategy) {
        return "";
      }

      const hasOption = Array.from(strategySelect.options).some((opt) => opt.value === savedStrategy);
      if (!hasOption) {
        saveLastCompletedStrategy("");
        return "";
      }

      currentStrategy = savedStrategy;
      await updateEditorContent(savedStrategy, { syncBacktestCheckboxes: false });
      return savedStrategy;
    }

    // --- Refresh strategies dropdown without full page reload ---
    async function refreshStrategiesDropdown(selectName = null) {
      try {
        const resp = await fetch("/api/strategies");
        const strategies = await resp.json();
        const selects = [
          ...getStrategySelects(),
        ].filter(Boolean);
        selects.forEach((sel) => {
          const prev = selectName || sel.value;
          sel.innerHTML = '<option value="">-- No Active Strategy --</option>';
          strategies.forEach((s) => {
            const opt = document.createElement("option");
            opt.value = s;
            opt.textContent = s;
            sel.appendChild(opt);
          });
          if (prev) sel.value = prev;
        });
        renderBacktestStrategyChooser(strategies, selectName || "");
      } catch (e) {
        console.error("Failed to refresh strategies dropdown", e);
      }
    }

    // UI Helpers
    function toggleStrategyPanel() {
      const panel = document.getElementById("strategy-panel");
      panel.classList.toggle("hidden");
    }

    async function updateEditorContent(strategyName, { syncBacktestCheckboxes = true } = {}) {
      syncStrategySelections(strategyName, { syncBacktestCheckboxes });
      currentStrategy = strategyName || "";
      const strategyEditor = document.getElementById("strategy-editor");
      const strategyFilename = document.getElementById("strategy-filename");

      // If the Labs editor is not mounted in this render, avoid throwing and
      // let the rest of the dashboard (including chart loading) continue.
      if (!strategyEditor || !strategyFilename) {
        console.warn("Strategy editor elements not found; skipping editor sync.");
        return;
      }

      if (!strategyName) {
        strategyEditor.value = "";
        strategyFilename.value = "";
        updateBacktestRunButtonState();
        return;
      }
      try {
        const resp = await fetch(`/api/strategy/${encodeURIComponent(strategyName)}`);
        if (!resp.ok) {
          throw new Error("Failed to load strategy content");
        }
        const data = await resp.json();
        strategyEditor.value = data.content;
        strategyFilename.value = strategyName;
        updateBacktestRunButtonState();
      } catch (err) {
        console.error("Failed to load strategy", err);
        updateBacktestRunButtonState();
      }
    }

    function bumpStrategyVersion(name) {
      const base = String(name || "").trim();
      if (!base) {
        return "custom_strategy_v2";
      }
      const match = base.match(/^(.*?)([_-])?v(\d+)$/i);
      if (!match) {
        return `${base}_v2`;
      }
      const prefix = match[1];
      const separator = match[2] || "_";
      const currentVersion = Number.parseInt(match[3], 10);
      const nextVersion = Number.isFinite(currentVersion) ? currentVersion + 1 : 2;
      return `${prefix}${separator}v${nextVersion}`;
    }

    // Opens the modify modal for the current strategy or visible draft.
    async function modifyStrategy() {
      const strategySelect = document.getElementById("strategy-select");
      const strategyName = strategySelect ? strategySelect.value : "";
      const modal = document.getElementById("modify-modal");
      if (!modal) {
        showToast("Modify dialog is missing from page.", true);
        return;
      }

      if (!strategyName) {
        // Fallback: allow editing current DSL text from Labs panel even without an active dropdown selection.
        const editor = document.getElementById("strategy-editor");
        const filename = document.getElementById("strategy-filename");
        const existingDsl = editor ? editor.value : "";
        const baseName = (filename && filename.value ? filename.value : "custom_strategy").trim() || "custom_strategy";

        document.getElementById("modify-modal-editor").value = existingDsl;
        document.getElementById("modify-modal-name").value = bumpStrategyVersion(baseName);
        document.getElementById("modify-modal-source").textContent = "Based on: unsaved editor content";
        sourceStrategyName = baseName;

        modal.style.display = "flex";
        document.getElementById("modify-modal-editor").focus();
        return;
      }

      // Open immediately, then load the exact file content for the selected strategy.
      document.getElementById("modify-modal-editor").value = "Loading strategy file...";
      document.getElementById("modify-modal-name").value = bumpStrategyVersion(strategyName);
      document.getElementById("modify-modal-source").textContent = "Based on: " + strategyName;
      sourceStrategyName = strategyName;
      modal.style.display = "flex";
      document.getElementById("modify-modal-editor").focus();

      try {
        const resp = await fetch(`/api/strategy/${encodeURIComponent(strategyName)}`);
        if (!resp.ok) {
          throw new Error("Failed to load selected strategy");
        }
        const data = await resp.json();
        document.getElementById("modify-modal-editor").value = data.content || "";
      } catch (err) {
        console.error("Failed to load selected strategy", err);
        document.getElementById("modify-modal-editor").value = "";
        showToast("Could not load selected strategy file.", true);
      }
    }

    function closeModifyModal() {
      document.getElementById("modify-modal").style.display = "none";
    }

    async function saveFromModal() {
      const name = document.getElementById("modify-modal-name").value.trim();
      const content = document.getElementById("modify-modal-editor").value;
      if (!name || !content) { showToast("Need both a name and DSL content!", true); return; }
      if (name === sourceStrategyName) {
        showToast(`Change the name first â€” "${name}" is the original.`, true);
        document.getElementById("modify-modal-name").focus();
        return;
      }
      await _doSave(name, content, name);
      closeModifyModal();
    }

    // Save As â€” requires a name that differs from the source
    async function saveAsStrategy() {
      const name = document.getElementById("strategy-filename").value.trim();
      const content = document.getElementById("strategy-editor").value;
      if (!name || !content) { showToast("Need both a name and DSL content!", true); return; }
      if (name === sourceStrategyName) {
        showToast(`Change the name first â€” "${name}" is the original.`, true);
        document.getElementById("strategy-filename").focus();
        return;
      }
      await _doSave(name, content, name);
    }

    // Overwrite â€” saves back to the exact source file
    async function saveStrategy() {
      const name = document.getElementById("strategy-filename").value.trim();
      const content = document.getElementById("strategy-editor").value;
      if (!name || !content) { showToast("Need both a name and DSL content!", true); return; }
      await _doSave(name, content, name);
    }

    async function _doSave(name, content, selectAfter) {
      try {
        const resp = await fetch('/api/strategy/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, content })
        });
        const res = await resp.json();
        if (resp.ok && res.status === 'success') {
          await refreshStrategiesDropdown(selectAfter);
          sourceStrategyName = name;
          document.getElementById("source-strategy-name").textContent = name;
          showToast(`Saved: ${name}.dsl`);
        } else {
          showToast("Error: " + (res.detail || 'Unknown error'), true);
        }
      } catch (err) {
        showToast("Save failed: " + err, true);
      }
    }

    function syncExportMatchesButtonState() {
      const button = document.getElementById("export-matches-btn");
      if (!button) {
        return;
      }
      const busy = exportTopMatchesInFlight;
      button.dataset.busy = busy ? "1" : "0";
      button.classList.toggle("opacity-80", busy);
      button.classList.toggle("cursor-wait", busy);
    }

    function setLastScreenMatches(matches, meta = {}) {
      lastScreenMatches = Array.isArray(matches) ? matches.slice() : [];
      lastScreenMeta = {
        strategy_name: String(meta.strategy_name || meta.strategy || currentStrategy || "").trim(),
        scan_scope: String(meta.scan_scope || "").trim(),
        exchange: String(meta.exchange || "").trim(),
        ticker_list: String(meta.ticker_list || "").trim(),
        disqualifiers: normalizeScreenDisqualifiers(meta.disqualifiers || screenDisqualifiers),
      };
      syncExportMatchesButtonState();
    }

    async function exportTopMatchesToGoogleDrive(autoTriggered = false) {
      if (!Array.isArray(lastScreenMatches) || lastScreenMatches.length === 0) {
        return null;
      }
      const resp = await fetch("/api/screen/export/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          matches: lastScreenMatches,
          strategy_name: lastScreenMeta.strategy_name || currentStrategy || "Top Matches",
          scan_scope: lastScreenMeta.scan_scope || "",
          exchange: lastScreenMeta.exchange || "",
          ticker_list: lastScreenMeta.ticker_list || "",
          disqualifiers: normalizeScreenDisqualifiers(lastScreenMeta.disqualifiers),
        }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = data.detail || "Failed to export to Google Drive";
        throw new Error(detail);
      }
      const title = String(data.title || "Google Sheet").trim();
      const link = String(data.spreadsheet_url || "").trim();
      showToast(
        autoTriggered
          ? `Auto-exported to Google Sheets: ${title}`
          : `Exported to Google Sheets: ${title}`
      );
      return { ...data, spreadsheet_url: link };
    }

    async function exportTopMatches() {
      if (exportTopMatchesInFlight) {
        return;
      }
      if (!Array.isArray(lastScreenMatches) || lastScreenMatches.length === 0) {
        showToast("Run the screener first so there are matches to export.", true);
        return;
      }

      const button = document.getElementById("export-matches-btn");
      exportTopMatchesInFlight = true;
      syncExportMatchesButtonState();
      if (button) {
        button.textContent = "Exporting...";
      }

      try {
        const resp = await fetch("/api/screen/export", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            matches: lastScreenMatches,
            strategy_name: lastScreenMeta.strategy_name || currentStrategy || "Top Matches",
            scan_scope: lastScreenMeta.scan_scope || "",
            exchange: lastScreenMeta.exchange || "",
            ticker_list: lastScreenMeta.ticker_list || "",
          }),
        });
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          throw new Error(data.detail || "Failed to export top matches");
        }
        const blob = await resp.blob();
        const header = resp.headers.get("content-disposition") || "";
        const fileMatch = header.match(/filename="?([^";]+)"?/i);
        const filename = fileMatch ? fileMatch[1] : "top_matches.csv";
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 0);
        showToast(`CSV exported as ${filename}`);
      } catch (err) {
        showToast(`Export failed: ${err}`, true);
      } finally {
        exportTopMatchesInFlight = false;
        if (button) {
          button.textContent = "Export CSV";
        }
        syncExportMatchesButtonState();
      }
    }

    async function applyDsl() {
      // Extract current DSL from editor and pass it to runScreen
      const dsl = document.getElementById("strategy-editor").value;
      if (!dsl.trim()) {
        alert("Please enter strategy DSL before applying.");
        return;
      }
      toggleStrategyPanel();
      // Pass true to indicate we're using custom DSL from active editor
      runScreen(dsl);
    }

    // Initial Load
    function cancelScan() {
      if (scanAbortController) {
        scanAbortController.abort();
        resetScanUI();
      }
    }

    function stopJobProgressPolling() {
      if (navScanProgressPoller) {
        clearInterval(navScanProgressPoller);
      }
      navScanProgressPoller = null;
      navScanProgressJob = null;
    }

    function applyJobProgressSnapshot(snapshot, expectedJob = navScanProgressJob) {
      if (!snapshot || typeof snapshot !== "object") {
        return false;
      }

      const job = String(snapshot.job || "");
      const phase = String(snapshot.phase || "idle");
      const active = Boolean(snapshot.active);
      const pctValue = Number(snapshot.pct);
      const pct = Number.isFinite(pctValue) ? Math.max(0, Math.min(100, pctValue)) : 0;
      const terminal = phase === "done" || phase === "failed";

      if (!job) {
        return false;
      }
      if (expectedJob && job !== expectedJob) {
        return false;
      }
      if (!active && !terminal) {
        return false;
      }
      if (job === "backtest" && backtestProgressStartedAt > 0) {
        const snapshotTime = Date.parse(String(snapshot.updated_at || ""));
        if (Number.isFinite(snapshotTime) && snapshotTime < backtestProgressStartedAt - 1000) {
          return false;
        }
      }

      const label = String(snapshot.label || navScanProgressJob || "Global");
      const detail = String(snapshot.detail || "").trim();
      const text = detail || (
        phase === "done"
          ? "Done"
          : phase === "failed"
            ? "Failed"
            : `${Math.round(pct)}%`
      );
      setNavScanProgress({
        show: true,
        globalLabel: label,
        globalText: text,
        globalPct: pct,
        globalWorking: active && phase !== "done" && phase !== "failed",
      });
      if (job === "backtest") {
        let backtestWorkText = "";
        if (snapshot.payload && typeof snapshot.payload === "object") {
          updateBacktestRaceFromSnapshot(snapshot.payload);
          backtestWorkText = formatBacktestWorkProgress(snapshot.payload.backtest_race, text);
          const runId = String(snapshot.payload.backtest_race?.run_id || snapshot.payload.run_id || "");
          void pollBacktestRaceEvents(runId);
        } else if (backtestRaceState) {
          backtestRaceState.targetProgress = pct;
          backtestRaceState.status = phase;
          backtestRaceState.detail = detail || backtestRaceState.detail || "";
          renderBacktestRace();
        }
        const backtestText = backtestWorkText || text;
        setBacktestProgress({
          show: true,
          detail: backtestText,
          globalLabel: label,
          globalText: backtestText,
          globalPct: pct,
          globalWorking: active && phase !== "done" && phase !== "failed",
        });
      }
      return !active && terminal;
    }

    function startJobProgressPolling(expectedJob, fallbackLabel = "Global") {
      stopJobProgressPolling();
      navScanProgressJob = expectedJob;

      const poll = async () => {
        try {
          const resp = await fetch("/api/job-progress", { cache: "no-store" });
          if (!resp.ok) {
            return;
          }
          const snapshot = await resp.json();
          const done = applyJobProgressSnapshot(snapshot, expectedJob);
          if (done && snapshot && snapshot.job === expectedJob) {
            stopJobProgressPolling();
          }
        } catch (err) {
          console.warn("Job progress poll failed", err);
        }
      };

      setNavScanProgress({
        show: true,
        globalLabel: fallbackLabel,
        globalText: "Waiting...",
        globalPct: 0,
        globalWorking: true,
      });
      poll();
      navScanProgressPoller = setInterval(poll, 350);
    }

    function getNavScanProgressNodes() {
      return {
        panel: document.getElementById("nav-scan-progress"),
        contextBar: document.getElementById("nav-scan-context-bar"),
        contextText: document.getElementById("nav-scan-context-text"),
        contextLabel: document.getElementById("nav-scan-context-label"),
        globalBar: document.getElementById("nav-scan-global-bar"),
        globalText: document.getElementById("nav-scan-global-text"),
        globalLabel: document.getElementById("nav-scan-global-label"),
      };
    }

    function setNavScanProgress(state = {}) {
      const nodes = getNavScanProgressNodes();
      const show = state.show;
      if (show === true && nodes.panel) {
        nodes.panel.classList.remove("hidden");
      } else if (show === false && nodes.panel) {
        nodes.panel.classList.add("hidden");
      }

      if (state.contextLabel && nodes.contextLabel) {
        nodes.contextLabel.textContent = state.contextLabel;
      }
      if (state.contextText && nodes.contextText) {
        nodes.contextText.textContent = state.contextText;
      }
      if (state.contextPct !== undefined && nodes.contextBar) {
        const pct = Math.max(0, Math.min(100, Number(state.contextPct) || 0));
        nodes.contextBar.style.width = `${pct}%`;
      }
      if (state.contextWorking !== undefined && nodes.contextBar) {
        nodes.contextBar.classList.toggle("animate-pulse", Boolean(state.contextWorking));
      }

      if (state.globalLabel && nodes.globalLabel) {
        nodes.globalLabel.textContent = state.globalLabel;
      }
      if (state.globalText && nodes.globalText) {
        nodes.globalText.textContent = state.globalText;
      }
      if (state.globalPct !== undefined && nodes.globalBar) {
        const pct = Math.max(0, Math.min(100, Number(state.globalPct) || 0));
        nodes.globalBar.style.width = `${pct}%`;
      }
      if (state.globalWorking !== undefined && nodes.globalBar) {
        nodes.globalBar.classList.toggle("animate-pulse", Boolean(state.globalWorking));
      }
    }

    function updateScanActionButtonsState() {
      const readiness = tickerUniverseExplicitlyChosen
        ? { ready: true, reason: "Run screener" }
        : { ready: false, reason: "Choose a ticker universe first" };
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
      updateScanActionButtonsState();
    }

    async function runScreen(customDsl = null) {
      const list = document.getElementById("ticker-list");
      const spinner = document.getElementById("loading-spinner");
      const scanBtn = document.getElementById("scan-btn");
      const runBtn = document.getElementById("run-btn");
      const strategySelect = document.getElementById("strategy-select");
      const errorSection = document.getElementById("error-section");
      const errorList = document.getElementById("error-list");

      if (!tickerUniverseExplicitlyChosen) {
        resetScanUI();
        return;
      }

      if ((normalizeScanScope(tickerScanScope) === "list" || normalizeScanScope(tickerScanScope) === "all_lists") && getScopeTickers(tickerScanScope).length === 0) {
        await openListEditorModal();
        return;
      }

      // Set up abortion
      scanAbortController = new AbortController();

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

      if (runBtn) {
        runBtn.innerHTML = `
            <svg class="w-3.5 h-3.5 mr-1 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" stroke-width="2" stroke-opacity="0.3"></circle>
              <path d="M21 12a9 9 0 00-9-9" stroke-width="2" stroke-linecap="round"></path>
            </svg>
            Running
          `;
        runBtn.classList.remove("bg-green-600");
        runBtn.classList.add("bg-emerald-500", "cursor-wait");
        runBtn.disabled = true;
      }

      if (list) list.style.opacity = "0.5";

      try {
        await ensureGuiMarketBackbone({ allowRefresh: false });
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
        const screenParams = getScreenDisqualifierParams();
        screenParams.forEach((value, key) => {
          universeParams.set(key, value);
        });
        const screenQuery = universeParams.toString();
        if (screenQuery) {
          url += `?${screenQuery}`;
        }
        if (customDsl) {
          url += `${screenQuery ? "&" : "?"}dsl_content=${encodeURIComponent(customDsl)}`;
          syncStrategySelections("");
          currentStrategy = "";
        } else if (strategySelect.value) {
          url += `${screenQuery ? "&" : "?"}strategy=${strategySelect.value}`;
          currentStrategy = strategySelect.value;
        } else {
          currentStrategy = "";
        }
        setLastScreenMatches([], {
          strategy_name: currentStrategy || (customDsl ? "Editor Draft" : ""),
          scan_scope: normalizeScanScope(tickerScanScope),
          ticker_list: universeParams.get("ticker_list") || "",
          disqualifiers: screenDisqualifiers,
        });
        console.log("Screen scan starting with URL:", url);
        console.log("Current strategy:", currentStrategy);

        // Fake progress only for the early part of the wait. Once the bar
        // reaches the high-80s, switch to an indeterminate "working" state
        // so the UI does not appear frozen while the backend finishes.
        let fakeProg = 0;
        let isWorkingPhase = false;
        let progInterval = null;
        const startProgress = () => {
          progInterval = setInterval(() => {
            const nodes = getNavScanProgressNodes();
            if (!nodes.contextBar || !nodes.contextText) return;

            if (fakeProg < 90) {
              fakeProg = Math.min(90, fakeProg + Math.max(0.5, (90 - fakeProg) * 0.12));
              setNavScanProgress({
                contextLabel: "Screen",
                contextText: `${Math.round(fakeProg)}%`,
                contextPct: fakeProg,
              });
              return;
            }

            if (!isWorkingPhase) {
              isWorkingPhase = true;
              setNavScanProgress({
                contextLabel: "Screen",
                contextText: "WORKING",
                contextPct: 90,
                contextWorking: true,
              });
            }

            const pulse = 88 + Math.round(4 * (0.5 + 0.5 * Math.sin(Date.now() / 350)));
            setNavScanProgress({
              contextLabel: "Screen",
              contextText: "WORKING",
              contextPct: pulse,
              contextWorking: true,
            });
          }, 300);
        };
        startProgress();

        let resp = null;
        let rawData = null;
        try {
          resp = await fetch(url, { signal: scanAbortController.signal });
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
            strategy_name: currentStrategy || (customDsl ? "Editor Draft" : ""),
            scan_scope: normalizeScanScope(tickerScanScope),
            ticker_list: universeParams.get("ticker_list") || "",
            disqualifiers: screenDisqualifiers,
          });

          if (screenAutoExportEnabled && matches.length > 0) {
            try {
              await exportTopMatchesToGoogleDrive(true);
            } catch (autoExportErr) {
              showToast(`Google auto-export failed: ${autoExportErr.message || autoExportErr}`, true);
            }
          }

          // Update ticker dropdown options based on screen results.
          if (matches.length > 0 && (strategySelect.value || customDsl)) {
            setTickerSelectUniverse(matches.map((item) => ({
              ticker: item.ticker,
              label: item.ticker,
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
              '<div class="text-sm text-slate-400 italic p-4 text-center">No matching ETFs found for this strategy...</div>';
          }

          matches.forEach((item, idx) => {
            try {
              const card = document.createElement("div");
              card.className =
                "ticker-card p-3 bg-slate-50 border-l-4 border-indigo-500 rounded shadow-sm hover:shadow-md hover:bg-indigo-50 cursor-pointer transition-all";
              card.onclick = () => loadChart(item.ticker);
              const statusText = item.status || "TRENDING";
              const statusColor =
                item.status === "Entry Signal"
                  ? "text-emerald-500 animate-pulse font-bold"
                  : "text-indigo-600";

              const closeVal = Number(item.close ?? 0);
              const volumeVal = Number(item.volume ?? 0);
              const returnPctVal = Number(item.return_pct ?? 0);
              const changePctVal = Number(item.change_pct ?? 0);
              const scoreVal = Number(item.score ?? 0);

              const changeVal = Number.isFinite(changePctVal)
                ? changePctVal.toFixed(2)
                : "0.00";
              const changeColor =
                parseFloat(changeVal) >= 0 ? "text-emerald-500" : "text-rose-500";
              const sign = parseFloat(changeVal) >= 0 ? "+" : "";

              card.innerHTML = `
                        <div class="flex justify-between items-start">
                            <div class="flex flex-col">
                                <div class="flex items-baseline gap-1.5">
                                  <span class="font-bold text-slate-800 text-lg leading-none">${item.ticker}</span>
                                  <span class="text-[10px] font-bold text-indigo-400">#${idx + 1}</span>
                                </div>
                                <span class="text-[10px] ${statusColor} mt-1 uppercase tracking-wider">${statusText}</span>
                            </div>
                            <div class="flex flex-col items-end">
                              <span class="text-slate-800 font-bold font-mono">${closeVal.toFixed(2)}â‚¬</span>
                                <span class="text-[10px] ${changeColor} font-mono">${sign}${changeVal}%</span>
                            </div>
                        </div>
                        <div class="mt-2 pt-2 border-t border-slate-200/50 flex justify-between items-center">
                            <div class="text-[10px] text-slate-400 font-semibold">
                              ${(volumeVal / 1000).toFixed(0)}K VOLUME
                            </div>
                            <div class="text-[10px] font-bold text-indigo-600">
                              ${(scoreVal * 100).toFixed(0)} pts
                            </div>
                        </div>
                    `;
              list.appendChild(card);
              console.log(`Card ${idx} added for ${item.ticker}`);
            } catch (cardErr) {
              console.error(`Error processing card at index ${idx}:`, cardErr);
              console.error("Item data:", item);
            }
          });
          console.log("All cards processed successfully");
        } finally {
          if (progInterval) clearInterval(progInterval);
          progInterval = null;
        }
      } catch (err) {
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
          scan_scope: normalizeScanScope(tickerScanScope),
          ticker_list: getUniverseFilterParams().get("ticker_list") || "",
          disqualifiers: screenDisqualifiers,
        });
        resetScanUI();
      }
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
        const strategyPart = strategyName ? `&strategy=${encodeURIComponent(strategyName)}` : "";
        const url = `/api/chart/${ticker}?days=${currentDays}${strategyPart}`;
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
          }
        });

        chartDiv.innerHTML = "";
        await Plotly.newPlot(chartDiv, figData.data, figData.layout, {
          responsive: true,
          displayModeBar: false,
          displaylogo: false,
          scrollZoom: true,
        });

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
            Plotly.relayout(chartDiv, { "xaxis.autorange": true, "yaxis.autorange": true });
          });

          addBtn("Reset", "Reset axes and zoom mode", () => {
            Plotly.relayout(chartDiv, { "xaxis.autorange": true, "yaxis.autorange": true, dragmode: "zoom" });
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

          setActive("zoom");
        }

        console.info("loadChart render complete", ticker);
      } catch (err) {
        console.error("loadChart error:", err);
        chartDiv.innerHTML = `<div class="p-8 text-center text-red-500">${err.message}</div>`;
      }
    }

    function setRange(days) {
      currentDays = days;
      saveChartRangeDays(days);
      updateRangeChrome();
      if (currentTicker) loadChart(currentTicker);
    }

    document
      .getElementById("ticker-select")
      .addEventListener("change", (e) => {
        storeTickerSelection(e.target.value);
        if (e.target.value) loadChart(e.target.value);
      });

    document
      .getElementById("strategy-select")
      .addEventListener("change", (e) => {
        updateEditorContent(e.target.value);
        currentStrategy = e.target.value || "";
        syncBacktestRaceLanesToCurrentSelection();
      });

    // Initialize
    const dashboardReadyPromise = (async function initializeDashboard() {
      const restoredStrategy = await restoreLastCompletedStrategy();
      if (restoredStrategy) {
        console.info("Restored last completed strategy", restoredStrategy);
      }
      restoreBacktestRaceStateFromStorage();
      const restoredDays = readSavedChartRangeDays();
      if (restoredDays !== null) {
        currentDays = restoredDays;
      }
      populateBacktestAxisControls(backtestDefaultMetrics());
      bindBacktestStrategyChooserControls();
      bindBacktestRaceControls();
      renderBacktestRace();
      updateQueryControls();
      updateBacktestStrategyCount();
      syncBacktestStrategyCheckboxChrome();
      updateScanActionButtonsState();
      updateBacktestRunButtonState();
      updateRangeChrome();
      await loadMarketStatus();
      syncExportMatchesButtonState();
    })();

    function testMe() {
      const dsl = document.getElementById("strategy-editor").value;
      alert("Prototype Working!\n\nCurrent Editor Text:\n" + dsl);
    }

    Object.assign(window, {
      applyDsl,
      applyJobProgressSnapshot,
      closeModifyModal,
      closeListEditorModal,
      openListEditorModal,
      handleBacktestStrategyChooserChange,
      loadBacktestMetrics,
      openQueryTickerChart,
      loadQueryResults,
      loadShortlist,
      mergeBacktestScatterRows,
      prepareBacktestLiveResults,
      renderBacktestScatter,
      saveListEditor,
      selectBacktestStrategies,
      updateBacktestRunButtonState,
      modifyStrategy,
      refreshMarketData,
      ensureFreshMarketData,
      exportTopMatches,
      resetDashboardTabPreference,
      runScreen,
      saveAsStrategy,
      saveFromModal,
      saveStrategy,
      setBacktestSourceMode,
      setListBuilderExchange,
      setListBuilderSearch,
      setListBuilderList,
      setScanSource,
      setScreenAutoExportEnabled,
      setScreenDisqualifier,
      setRange,
      updateQueryControls,
      startJobProgressPolling,
      stopJobProgressPolling,
      dashboardReadyPromise,
      setShortlistFilter,
      showTab,
      testMe,
      toggleStrategyPanel,
      toggleVisibleListBuilderTickers,
    });

