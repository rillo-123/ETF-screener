    let backtestSourceMode = "saved";
    let playbookLoaded = false;
    let playbookSourceSignature = "";
    let playbookRows = [];
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
    const LAST_SCREEN_PRESET_KEY = "etf-discovery:last-screen-preset";
    const LAST_PLAYBOOK_RISK_PCT_KEY = "etf-discovery:last-playbook-risk-pct";
    const LAST_BACKTEST_RACE_KEY = "etf-discovery:last-backtest-race";
    const LAST_BACKTEST_RACE_FUEL_KEY = "etf-discovery:last-backtest-race-fuel";
    const SCREEN_DEFAULT_FILTERS = {
      lookback_days: 30,
      volume_range: { min: 0, max: 20000000 },
      macd_event_enabled: true,
      rsi_event_enabled: true,
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
      ema_relationship_age: 30,
      supertrend_cross_mode: "red_to_green",
      ema_slope_20: "any",
      ema_slope_50: "any",
      ema_slope_200: "any",
      ema_slope_lookback: 5,
      ema_slope_flat_tolerance: 0.1,
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
      rsi_trigger: 50,
      stoch_trigger: 20,
    };
    const CHART_TA_PARAMETER_KEYS = [
      "macd_fast", "macd_slow", "macd_signal", "rsi_period",
      "stoch_rsi_period", "stoch_rsi_k", "stoch_rsi_d",
      "supertrend_period", "supertrend_multiplier",
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
    const DASHBOARD_TABS = ["screener", "playbook"];

    function getDashboardTabs() {
      return DASHBOARD_TABS
        .map((name) => document.getElementById(`tab-${name}`))
        .filter(Boolean);
    }

    function normalizeDashboardTab(value) {
      const cleaned = String(value || "screener").trim().toLowerCase();
      return DASHBOARD_TABS.includes(cleaned) ? cleaned : "screener";
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

    function getPlaybookRiskPct() {
      const node = document.getElementById("playbook-risk-pct");
      const raw = node
        ? Number(node.value)
        : Number(readStickyValue(LAST_PLAYBOOK_RISK_PCT_KEY, "5"));
      if (!Number.isFinite(raw)) {
        return 5;
      }
      return Math.max(0.5, Math.min(25, raw));
    }

    function clampNumber(value, minimum, maximum, fallback) {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) {
        return fallback;
      }
      return Math.max(minimum, Math.min(maximum, numeric));
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
        return "list";
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
          const exchange = getTickerExchangeBucket(
            item.ticker || item.value || item.symbol || "",
            item.label || item.text || item.name || item.exchange || "",
          ) === "sweden"
            ? "sweden"
            : normalizeExchangeFilter(item.exchange || getTickerExchangeBucket(item.ticker || item.value || item.symbol || "", item.label || item.text || item.name || ""));
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
      } else if (normalizedScope === "list") {
        const activeListName = normalizeListName(customTickerListActiveName || customTickerListName);
        placeholder.textContent = visible.length > 0
          ? `Select ticker from ${activeListName}...`
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
      ticker.disabled = ((normalizedScope === "sweden" || normalizedScope === "nasdaq") && visible.length === 0)
        || (normalizedScope === "list" && visible.length === 0);
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

    function escapeSearchRegex(text) {
      return String(text || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function matchesListBuilderSearchText(searchText, query) {
      const normalizedText = String(searchText || "").toUpperCase();
      const tokens = String(query || "")
        .trim()
        .toUpperCase()
        .split(/\s+/)
        .filter(Boolean);
      if (tokens.length === 0) {
        return true;
      }
      return tokens.every((token) => {
        if (!/[*?]/.test(token)) {
          return normalizedText.includes(token);
        }
        try {
          const pattern = escapeSearchRegex(token)
            .replace(/\\\*/g, ".*")
            .replace(/\\\?/g, ".");
          return new RegExp(pattern, "i").test(normalizedText);
        } catch (err) {
          const simplified = token.replace(/[*?]/g, "");
          return !simplified || normalizedText.includes(simplified);
        }
      });
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
        summary: null,
      };
    }

    function renderScanSourceListPreview() {
      const panel = document.getElementById("scan-source-list-preview");
      const title = document.getElementById("scan-source-list-preview-title");
      const body = document.getElementById("scan-source-list-preview-body");
      const toggleBtn = document.getElementById("list-preview-btn");
      const listMode = normalizeScanScope(tickerScanScope) === "list";
      const activeName = normalizeListName(customTickerListActiveName || customTickerListName);
      const tickers = Array.isArray(customTickerList) ? customTickerList.slice() : [];

      if (toggleBtn) {
        toggleBtn.disabled = !listMode;
        toggleBtn.style.opacity = listMode ? "1" : "0.6";
        toggleBtn.textContent = scanSourceListPreviewOpen ? "Hide Tickers" : "Show Tickers";
      }
      if (!panel || !title || !body) {
        return;
      }

      const shouldShow = listMode && scanSourceListPreviewOpen;
      panel.hidden = !shouldShow;
      title.textContent = `${activeName} · ${tickers.length} ticker${tickers.length === 1 ? "" : "s"}`;
      body.innerHTML = "";

      if (!shouldShow) {
        return;
      }

      if (tickers.length === 0) {
        const emptyNode = document.createElement("div");
        emptyNode.className = "scan-source-list-empty";
        emptyNode.textContent = "This list has no tickers yet.";
        body.appendChild(emptyNode);
        return;
      }

      tickers.forEach((ticker) => {
        const chip = document.createElement("div");
        chip.className = "scan-source-list-chip";
        chip.textContent = ticker;
        body.appendChild(chip);
      });
    }

    function toggleScanSourceListPreview() {
      if (normalizeScanScope(tickerScanScope) !== "list") {
        return;
      }
      scanSourceListPreviewOpen = !scanSourceListPreviewOpen;
      renderScanSourceListPreview();
    }

    function getScanSourceButtons() {
      return Array.from(document.querySelectorAll(
        "#scan-source-toggle .scan-source-btn"
      ));
    }

    function describeActiveScanScope(scope = tickerScanScope) {
      const normalized = normalizeScanScope(scope);
      if (normalized === "list") {
        const activeName = normalizeListName(customTickerListActiveName || customTickerListName);
        const count = Array.isArray(customTickerList) ? customTickerList.length : 0;
        return `${activeName} saved list (${count} ticker${count === 1 ? "" : "s"})`;
      }
      if (normalized === "sweden") {
        return "Sweden universe";
      }
      if (normalized === "nasdaq") {
        return "Nasdaq universe";
      }
      return "Xetra universe";
    }

    function getActiveSourceLabel(scope = tickerScanScope, options = {}) {
      const normalized = normalizeScanScope(scope);
      const includeCount = options.includeCount === true;
      if (normalized === "list") {
        const activeName = normalizeListName(customTickerListActiveName || customTickerListName);
        const count = Array.isArray(customTickerList) ? customTickerList.length : 0;
        return includeCount
          ? `${activeName} (${count} ticker${count === 1 ? "" : "s"})`
          : activeName;
      }
      if (normalized === "sweden") {
        return "Sweden";
      }
      if (normalized === "nasdaq") {
        return "Nasdaq";
      }
      return "Xetra";
    }

    function updateScanScopeChrome() {
      const scopeButtons = getScanSourceButtons();
      const normalized = normalizeScanScope(tickerScanScope);
      const listSelect = document.getElementById("list-select");
      const listPicker = document.getElementById("scan-source-list-picker");
      const listUniverseBadge = document.getElementById("list-select-universe-badge");
      tickerScanScope = normalized;
      scopeButtons.forEach((button) => {
        if (!button) {
          return;
        }
        const active = String(button.dataset.scope || "") === normalized;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
      const listMode = normalized === "list";
      if (listPicker) {
        listPicker.classList.toggle("is-scan-active", listMode);
      }
      if (listSelect) {
        listSelect.classList.toggle("is-scan-active", listMode);
        listSelect.disabled = !listMode;
      }
      if (listUniverseBadge) {
        const activeListName = normalizeListName(customTickerListActiveName || customTickerListName);
        if (listMode) {
          listUniverseBadge.textContent = `List universe: ${activeListName}`;
          listUniverseBadge.style.display = "inline-flex";
          listUniverseBadge.classList.add("is-active");
        } else {
          listUniverseBadge.style.display = "none";
          listUniverseBadge.classList.remove("is-active");
        }
      }
      renderScanSourceListPreview();
      renderTickerSelectOptions({ preserveSelection: true });
    }

    async function applyScanScopeSelection(mode) {
      const normalized = normalizeScanScope(mode);
      tickerScanScope = normalized;
      playbookLoaded = false;
      playbookSourceSignature = "";
      tickerUniverseExplicitlyChosen = true;
      writeStickyValue(LAST_SCAN_SCOPE_KEY, normalized);
      updateScanScopeChrome();
      updateRangeChrome();
      updateScanActionButtonsState();
      loadMarketStatus(normalized).catch((err) => {
        console.warn("Could not refresh market status after scope change", err);
      });
      if (normalized === "list" && getScopeTickers(normalized).length === 0) {
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
      const entries = Array.isArray(customTickerLists) && customTickerLists.length > 0
        ? customTickerLists
        : [{ name: activeName, tickers: customTickerList }];
      const { list, summary } = getListSelectNodes();
      if (list) {
        list.innerHTML = "";
        entries.forEach((entry) => {
          const option = document.createElement("option");
          const name = normalizeListName(entry.name);
          const count = Array.isArray(entry.tickers) ? entry.tickers.length : 0;
          option.value = name;
          option.textContent = `${name} (${count})`;
          list.appendChild(option);
        });
        list.value = activeName;
        list.disabled = entries.length === 0;
      }
      const listSelect = document.getElementById("list-select");
      if (listSelect) {
        listSelect.title = `${activeName} (${customCount} tickers)`;
      }
      const modalTitle = document.getElementById("list-modal-title");
      if (modalTitle) {
        modalTitle.textContent = activeName === "__new__"
          ? "Build Saved Lists"
          : `Build Saved Lists: ${activeName}`;
      }
      const editBtn = document.getElementById("list-edit-btn");
      if (editBtn) {
        editBtn.textContent = customCount > 0 ? `Edit ${activeName} (${customCount})` : `Edit ${activeName}...`;
        editBtn.title = customCount > 0
          ? `Edit the saved list ${activeName} (${customCount} tickers)`
          : `Build the saved list ${activeName}`;
      }
      renderScanSourceListPreview();
      updateScanScopeChrome();
    }

    function getListBuilderListSelectNode() {
      return document.getElementById("list-modal-list-select");
    }

    async function setActiveCustomTickerList(name, options = {}) {
      const normalized = normalizeListName(name);
      const selected = getCustomListEntryByName(normalized)
        || (Array.isArray(customTickerLists) && customTickerLists.length > 0 ? customTickerLists[0] : null)
        || { name: normalized, tickers: [] };
      const activeName = normalizeListName(selected.name || normalized);
      const tickers = sortTickersByUniverse(selected.tickers || []);
      customTickerListActiveName = activeName;
      customTickerListName = activeName;
      customTickerList = tickers;
      scanSourceListPreviewOpen = true;
      playbookLoaded = false;
      playbookSourceSignature = "";
      writeCustomTickerList(tickers, activeName);
      updateListSelectChrome();
      renderTickerSelectOptions({ preserveSelection: options.preserveSelection !== false });
      updateScanActionButtonsState();
      updateBacktestRunButtonState();
      if (options.persist !== false) {
        try {
          await persistCustomTickerListsToServer({
            active_name: activeName,
            lists: customTickerLists,
          });
        } catch (err) {
          console.warn("Could not persist active saved list selection", err);
        }
      }
      return { name: activeName, tickers };
    }

    async function activateCustomTickerList(name, options = {}) {
      const result = await setActiveCustomTickerList(name, options);
      const normalizedScope = normalizeScanScope(tickerScanScope);
      if (options.switchScanSource === false) {
        return result;
      }
      if (normalizedScope !== "list") {
        await applyScanScopeSelection("list");
      } else {
        updateScanScopeChrome();
      }
      return result;
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
      listBuilderSelectedOnly = false;
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

    function toggleListBuilderSelectedOnly() {
      listBuilderSelectedOnly = !listBuilderSelectedOnly;
      renderListBuilderModal();
    }

    function getListBuilderVisibleTickers() {
      const search = String(listBuilderSearch || "").trim();
      const exchange = normalizeExchangeFilter(listBuilderExchange);
      return tickerSelectUniverse.filter((item) => {
        if (exchange !== "all" && item.exchange !== exchange) {
          return false;
        }
        if (search && !matchesListBuilderSearchText(getTickerUniverseSearchText(item), search)) {
          return false;
        }
        if (listBuilderSelectedOnly && !customTickerListDraft.includes(item.ticker)) {
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
      const deleteBtn = document.getElementById("list-modal-delete-btn");
      const modalTitle = document.getElementById("list-modal-title");
      const selectedOnlyBtn = document.getElementById("list-modal-selected-only-btn");
      const selectedTitle = document.getElementById("list-modal-selected-title");
      const selectedList = document.getElementById("list-modal-selected-list");
      const exchangeButtons = document.querySelectorAll("[data-list-exchange]");
      const visible = getListBuilderVisibleTickers();
      const isNewList = normalizeListName(customTickerListDraftSourceName) === "__new__";
      const activeDraftName = normalizeListName(customTickerListName);

      if (searchInput && searchInput.value !== listBuilderSearch) {
        searchInput.value = listBuilderSearch;
      }
      if (nameInput && nameInput.value !== normalizeListName(customTickerListName)) {
        nameInput.value = normalizeListName(customTickerListName);
      }
      if (listSelect && listSelect.value !== normalizeListName(customTickerListDraftSourceName || customTickerListName)) {
        updateListBuilderListSelector();
      }
      if (deleteBtn) {
        deleteBtn.disabled = isNewList;
        deleteBtn.style.opacity = isNewList ? "0.45" : "1";
        deleteBtn.style.cursor = isNewList ? "not-allowed" : "pointer";
        deleteBtn.title = isNewList
          ? "Save the new list before deleting it"
          : `Delete the saved list ${normalizeListName(customTickerListDraftSourceName)}`;
      }
      if (modalTitle) {
        modalTitle.textContent = isNewList
          ? "Build Saved Lists: New List"
          : `Build Saved Lists: ${activeDraftName}`;
      }
      if (selectedOnlyBtn) {
        selectedOnlyBtn.style.backgroundColor = listBuilderSelectedOnly ? "#2563eb" : "#0f172a";
        selectedOnlyBtn.style.color = listBuilderSelectedOnly ? "#ffffff" : "#bfdbfe";
        selectedOnlyBtn.style.borderColor = listBuilderSelectedOnly ? "rgba(147,197,253,0.85)" : "rgba(96,165,250,0.4)";
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
      if (selectedTitle) {
        selectedTitle.textContent = `${customTickerListDraft.length} Selected Tickers`;
      }
      if (selectedList) {
        selectedList.innerHTML = "";
        if (customTickerListDraft.length === 0) {
          const emptyChip = document.createElement("div");
          emptyChip.textContent = "No stocks in this list yet.";
          emptyChip.style.fontSize = "0.85rem";
          emptyChip.style.color = "#94a3b8";
          selectedList.appendChild(emptyChip);
        } else {
          customTickerListDraft.forEach((ticker) => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.textContent = ticker;
            chip.title = `Remove ${ticker} from ${activeDraftName}`;
            chip.style.borderRadius = "999px";
            chip.style.border = "1px solid rgba(129,140,248,0.3)";
            chip.style.background = "#1e1b4b";
            chip.style.color = "#e0e7ff";
            chip.style.padding = "0.32rem 0.62rem";
            chip.style.fontSize = "0.78rem";
            chip.style.fontWeight = "700";
            chip.addEventListener("click", () => {
              customTickerListDraft = customTickerListDraft.filter((value) => value !== ticker);
              renderListBuilderModal();
            });
            selectedList.appendChild(chip);
          });
        }
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
      playbookLoaded = false;
      playbookSourceSignature = "";
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

    async function deleteListEditorSelection() {
      const sourceName = normalizeListName(customTickerListDraftSourceName);
      if (sourceName === "__new__") {
        return;
      }
      const confirmed = typeof window.confirm !== "function"
        ? true
        : window.confirm(`Delete the saved list "${sourceName}"?`);
      if (!confirmed) {
        return;
      }

      let nextLists = (Array.isArray(customTickerLists) ? customTickerLists : [])
        .filter((entry) => normalizeListName(entry.name) !== sourceName)
        .map((entry) => ({
          name: normalizeListName(entry.name),
          tickers: sortTickersByUniverse(entry.tickers || []),
        }));
      if (nextLists.length === 0) {
        nextLists = [{ name: "My List", tickers: [] }];
      }
      const preferredActiveName = normalizeListName(customTickerListActiveName);
      const fallbackEntry = nextLists.find((entry) => normalizeListName(entry.name) === preferredActiveName) || nextLists[0];
      const saved = await persistCustomTickerListsToServer({
        active_name: normalizeListName(fallbackEntry.name),
        lists: nextLists,
      });
      customTickerLists = Array.isArray(saved.lists) ? saved.lists : nextLists;
      customTickerList = sortTickersByUniverse(saved.tickers || fallbackEntry.tickers || []);
      customTickerListName = normalizeListName(saved.name || fallbackEntry.name);
      customTickerListActiveName = customTickerListName;
      customTickerListDraftSourceName = customTickerListName;
      customTickerListDraft = sortTickersByUniverse(customTickerList);
      playbookLoaded = false;
      playbookSourceSignature = "";
      updateListSelectChrome();
      renderTickerSelectOptions({ preserveSelection: true });
      updateScanActionButtonsState();
      updateBacktestRunButtonState();
      closeListEditorModal();
      showToast(`Deleted ${sourceName}. Active list is now ${customTickerListName}.`);
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
      if (scope === "list" && scopeTickers.length > 0) {
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

    function setPlaybookEmptyState(message) {
      const emptyState = document.getElementById("playbook-empty");
      const content = document.getElementById("playbook-content");
      const body = document.getElementById("playbook-table-body");
      if (body) {
        body.innerHTML = "";
      }
      if (emptyState) {
        emptyState.textContent = message;
        emptyState.classList.remove("hidden");
      }
      if (content) {
        content.classList.add("hidden");
      }
    }

    function getPlaybookDecisionClasses(value) {
      const text = String(value || "");
      if (text.startsWith("Trade")) {
        return "bg-emerald-100 text-emerald-700 border border-emerald-200";
      }
      if (text.startsWith("Watch")) {
        return "bg-amber-100 text-amber-700 border border-amber-200";
      }
      return "bg-slate-100 text-slate-700 border border-slate-200";
    }

    function renderPlaybookRows() {
      const body = document.getElementById("playbook-table-body");
      const emptyState = document.getElementById("playbook-empty");
      const content = document.getElementById("playbook-content");
      if (!body || !emptyState || !content) {
        return;
      }
      if (!Array.isArray(playbookRows) || playbookRows.length === 0) {
        setPlaybookEmptyState("No playbook candidates matched the current universe.");
        return;
      }

      body.innerHTML = "";
      playbookRows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-violet-50/40 transition-colors";

        const reasons = Array.isArray(row.reasons) && row.reasons.length > 0
          ? row.reasons.join(" • ")
          : "No extra notes yet.";
        tr.innerHTML = `
          <td class="px-4 py-3 align-top">
            <button type="button" class="font-bold text-violet-700 hover:text-violet-900"
              onclick="showTab('screener'); loadChart('${String(row.ticker || "").replace(/'/g, "\\'")}')">
              ${row.ticker || ""}
            </button>
            <div class="mt-1 text-xs text-slate-500">${row.name || row.ticker || ""}</div>
          </td>
          <td class="px-4 py-3 align-top">
            <span class="rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${getPlaybookDecisionClasses(row.decision)}">${row.decision || ""}</span>
            <div class="mt-1 text-xs text-slate-500">Rules ${Array.isArray(row.reasons) ? row.reasons.length : 0}/6 • ${row.label || ""}</div>
          </td>
          <td class="px-4 py-3 align-top font-mono text-slate-800">${Number(row.entry || 0).toFixed(2)}</td>
          <td class="px-4 py-3 align-top font-mono text-slate-800">
            ${Number(row.stop || 0).toFixed(2)}
            <div class="mt-1 text-xs text-slate-500">${row.support_basis ? `${row.support_basis} ${Number(row.support_level || 0).toFixed(2)}` : "No nearby support"}</div>
          </td>
          <td class="px-4 py-3 align-top">
            <div class="font-semibold text-slate-800">${Number(row.max_loss_pct || 0).toFixed(2)}%</div>
            <div class="mt-1 text-xs text-slate-500">${row.technical_risk_pct !== null && row.technical_risk_pct !== undefined ? `Technical ${Number(row.technical_risk_pct).toFixed(2)}%` : "Technical n/a"}</div>
          </td>
          <td class="px-4 py-3 align-top">
            <div class="font-semibold text-slate-800">${row.stop_basis === "technical" ? "Technical" : "Risk Cap"}</div>
            <div class="mt-1 text-xs text-slate-500">${row.recent_entry_days === null || row.recent_entry_days === undefined ? "No fresh signal age" : `${row.recent_entry_days}d since signal`}</div>
          </td>
          <td class="px-4 py-3 align-top">
            <div class="text-slate-700">${row.note || ""}</div>
            <div class="mt-1 text-xs text-slate-500">${reasons}</div>
          </td>
        `;
        body.appendChild(tr);
      });

      emptyState.classList.add("hidden");
      content.classList.remove("hidden");
    }

    async function loadPlaybook(forceRefresh = false) {
      const status = document.getElementById("playbook-status");
      const asOfEl = document.getElementById("playbook-as-of");
      const tradeEl = document.getElementById("playbook-trade-count");
      const watchEl = document.getElementById("playbook-watch-count");
      const riskCappedEl = document.getElementById("playbook-risk-capped-count");
      const runBtn = document.getElementById("playbook-run-btn");
      const riskInput = document.getElementById("playbook-risk-pct");
      if (!status || !asOfEl || !tradeEl || !watchEl || !riskCappedEl || !runBtn || !riskInput) {
        return;
      }

      const riskPct = getPlaybookRiskPct();
      riskInput.value = String(riskPct);
      writeStickyValue(LAST_PLAYBOOK_RISK_PCT_KEY, riskPct);

      const universeParams = getUniverseFilterParams();
      const currentSignature = `${universeParams.toString()}&risk_pct=${riskPct}`;
      const currentScope = universeParams.get("scan_scope") || "xetra";
      if (playbookLoaded && !forceRefresh && playbookSourceSignature === currentSignature) {
        return;
      }

      setPlaybookEmptyState(forceRefresh ? "Refreshing playbook candidates..." : "Loading playbook candidates...");
      runBtn.disabled = true;
      runBtn.textContent = forceRefresh ? "Refreshing..." : "Loading...";
      status.textContent = forceRefresh
        ? `Rebuilding playbook for ${describeActiveScanScope(currentScope)}...`
        : `Loading playbook for ${describeActiveScanScope(currentScope)}...`;

      try {
        universeParams.set("limit", "12");
        universeParams.set("risk_pct", String(riskPct));
        if (forceRefresh) {
          universeParams.set("refresh", "true");
        }
        const resp = await fetch(`/api/playbook?${universeParams.toString()}`);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Playbook request failed");
        }

        playbookRows = Array.isArray(data.rows) ? data.rows : [];
        asOfEl.textContent = data.as_of_date || "-";
        tradeEl.textContent = String((data.summary && data.summary.trade_count) || 0);
        watchEl.textContent = String((data.summary && data.summary.watch_count) || 0);
        riskCappedEl.textContent = String((data.summary && data.summary.risk_capped_count) || 0);
        playbookSourceSignature = currentSignature;
        playbookLoaded = true;

        if (playbookRows.length === 0) {
          setPlaybookEmptyState("No playbook candidates matched the current universe.");
          status.textContent = "Playbook returned no candidates";
          return;
        }

        renderPlaybookRows();
        status.textContent = `Snapshot date: ${data.as_of_date || "unknown"} • ${describeActiveScanScope(currentScope)} • risk cap ${Number(data.risk_pct || riskPct).toFixed(1)}%`;
      } catch (err) {
        setPlaybookEmptyState(`Playbook error: ${err.message || err}`);
        status.textContent = "Playbook load failed";
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = "Run Graph Playground";
      }
    }

    function coerceFilterBoolean(value, fallback) {
      if (typeof value === "boolean") {
        return value;
      }
      const normalized = String(value ?? "").trim().toLowerCase();
      if (["1", "true", "yes", "on"].includes(normalized)) {
        return true;
      }
      if (["0", "false", "no", "off"].includes(normalized)) {
        return false;
      }
      return fallback;
    }

    function normalizeScreenFiltersClient(raw = {}) {
      const lookbackDays = Math.round(clampNumber(raw.lookback_days, 30, 365, SCREEN_DEFAULT_FILTERS.lookback_days));
      const volumeMin = clampNumber(raw?.volume_range?.min, 0, 100000000, SCREEN_DEFAULT_FILTERS.volume_range.min);
      const volumeMax = clampNumber(raw?.volume_range?.max, 0, 100000000, SCREEN_DEFAULT_FILTERS.volume_range.max);
      const normalized = {
        lookback_days: lookbackDays,
        volume_range: {
          min: Math.min(volumeMin, volumeMax),
          max: Math.max(volumeMin, volumeMax),
        },
        macd_event_enabled: coerceFilterBoolean(raw.macd_event_enabled, SCREEN_DEFAULT_FILTERS.macd_event_enabled),
        rsi_event_enabled: coerceFilterBoolean(raw.rsi_event_enabled, SCREEN_DEFAULT_FILTERS.rsi_event_enabled),
        stoch_event_enabled: coerceFilterBoolean(raw.stoch_event_enabled, SCREEN_DEFAULT_FILTERS.stoch_event_enabled),
        supertrend_event_enabled: coerceFilterBoolean(raw.supertrend_event_enabled, SCREEN_DEFAULT_FILTERS.supertrend_event_enabled),
        ema_relationship_enabled: coerceFilterBoolean(raw.ema_relationship_enabled, SCREEN_DEFAULT_FILTERS.ema_relationship_enabled),
        ema_relationship_fast: Math.round(clampNumber(raw.ema_relationship_fast, 2, 200, SCREEN_DEFAULT_FILTERS.ema_relationship_fast)),
        ema_relationship_slow: Math.round(clampNumber(raw.ema_relationship_slow, 3, 400, SCREEN_DEFAULT_FILTERS.ema_relationship_slow)),
        ema_relationship_slope: ["any", "positive", "negative"].includes(String(raw.ema_relationship_slope || "").trim()) ? String(raw.ema_relationship_slope).trim() : SCREEN_DEFAULT_FILTERS.ema_relationship_slope,
        ema_relationship_allowance: clampNumber(raw.ema_relationship_allowance, 0, 5, SCREEN_DEFAULT_FILTERS.ema_relationship_allowance),
        rsi_cross_value: clampNumber(raw.rsi_cross_value, 0, 100, SCREEN_DEFAULT_FILTERS.rsi_cross_value),
        rsi_cross_mode: ["cross_up", "cross_down"].includes(String(raw.rsi_cross_mode || "").trim())
          ? String(raw.rsi_cross_mode).trim()
          : SCREEN_DEFAULT_FILTERS.rsi_cross_mode,
        stoch_cross_value: clampNumber(raw.stoch_cross_value, 0, 100, SCREEN_DEFAULT_FILTERS.stoch_cross_value),
        stoch_cross_mode: ["cross_up", "cross_down"].includes(String(raw.stoch_cross_mode || "").trim())
          ? String(raw.stoch_cross_mode).trim()
          : SCREEN_DEFAULT_FILTERS.stoch_cross_mode,
        stoch_cross_region: ["below", "above", "any"].includes(String(raw.stoch_cross_region || "").trim())
          ? String(raw.stoch_cross_region).trim()
          : SCREEN_DEFAULT_FILTERS.stoch_cross_region,
        macd_cross_mode: ["low_cross_buy", "high_cross_sell", "bullish_cross", "bearish_cross"].includes(String(raw.macd_cross_mode || "").trim())
          ? String(raw.macd_cross_mode).trim()
          : SCREEN_DEFAULT_FILTERS.macd_cross_mode,
        macd_event_age: Math.round(clampNumber(
          raw.macd_event_age,
          0,
          lookbackDays,
          raw?.macd_cross_window ? (Number(raw.macd_cross_window.min || 0) + Number(raw.macd_cross_window.max || lookbackDays)) / 2 : SCREEN_DEFAULT_FILTERS.macd_event_age,
        )),
        rsi_event_age: Math.round(clampNumber(
          raw.rsi_event_age,
          0,
          lookbackDays,
          raw?.rsi_cross_window ? (Number(raw.rsi_cross_window.min || 0) + Number(raw.rsi_cross_window.max || lookbackDays)) / 2 : SCREEN_DEFAULT_FILTERS.rsi_event_age,
        )),
        stoch_event_age: Math.round(clampNumber(
          raw.stoch_event_age,
          0,
          lookbackDays,
          raw?.stoch_cross_window ? (Number(raw.stoch_cross_window.min || 0) + Number(raw.stoch_cross_window.max || lookbackDays)) / 2 : SCREEN_DEFAULT_FILTERS.stoch_event_age,
        )),
        supertrend_event_age: Math.round(clampNumber(raw.supertrend_event_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.supertrend_event_age)),
        ema_relationship_age: Math.round(clampNumber(raw.ema_relationship_age, 0, lookbackDays, SCREEN_DEFAULT_FILTERS.ema_relationship_age)),
        supertrend_cross_mode: ["green_to_red", "red_to_green"].includes(String(raw.supertrend_cross_mode || "").trim())
          ? String(raw.supertrend_cross_mode).trim()
          : SCREEN_DEFAULT_FILTERS.supertrend_cross_mode,
        ema_slope_20: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_20 || "").trim()) ? String(raw.ema_slope_20).trim() : "any",
        ema_slope_50: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_50 || "").trim()) ? String(raw.ema_slope_50).trim() : "any",
        ema_slope_200: ["any", "positive", "flat", "negative"].includes(String(raw.ema_slope_200 || "").trim()) ? String(raw.ema_slope_200).trim() : "any",
        ema_slope_lookback: Math.round(clampNumber(raw.ema_slope_lookback, 1, 30, SCREEN_DEFAULT_FILTERS.ema_slope_lookback)),
        ema_slope_flat_tolerance: clampNumber(raw.ema_slope_flat_tolerance, 0, 5, SCREEN_DEFAULT_FILTERS.ema_slope_flat_tolerance),
        chart_ta: {
          macd_fast: Math.round(clampNumber(raw?.chart_ta?.macd_fast, 2, 100, CHART_TA_DEFAULTS.macd_fast)),
          macd_slow: Math.round(clampNumber(raw?.chart_ta?.macd_slow, 3, 200, CHART_TA_DEFAULTS.macd_slow)),
          macd_signal: Math.round(clampNumber(raw?.chart_ta?.macd_signal, 1, 100, CHART_TA_DEFAULTS.macd_signal)),
          rsi_period: Math.round(clampNumber(raw?.chart_ta?.rsi_period, 2, 100, CHART_TA_DEFAULTS.rsi_period)),
          stoch_rsi_period: Math.round(clampNumber(raw?.chart_ta?.stoch_rsi_period, 2, 100, CHART_TA_DEFAULTS.stoch_rsi_period)),
          stoch_rsi_k: Math.round(clampNumber(raw?.chart_ta?.stoch_rsi_k, 1, 30, CHART_TA_DEFAULTS.stoch_rsi_k)),
          stoch_rsi_d: Math.round(clampNumber(raw?.chart_ta?.stoch_rsi_d, 1, 30, CHART_TA_DEFAULTS.stoch_rsi_d)),
          supertrend_period: Math.round(clampNumber(raw?.chart_ta?.supertrend_period, 2, 100, CHART_TA_DEFAULTS.supertrend_period)),
          supertrend_multiplier: clampNumber(raw?.chart_ta?.supertrend_multiplier, 0.5, 10, CHART_TA_DEFAULTS.supertrend_multiplier),
          rsi_trigger: clampNumber(raw?.chart_ta?.rsi_trigger, 0, 100, raw.rsi_cross_value ?? CHART_TA_DEFAULTS.rsi_trigger),
          stoch_trigger: clampNumber(raw?.chart_ta?.stoch_trigger, 0, 100, raw.stoch_cross_value ?? CHART_TA_DEFAULTS.stoch_trigger),
        },
      };
      return normalized;
    }

    function formatCompactVolume(value) {
      const numeric = Number(value || 0);
      if (!Number.isFinite(numeric)) {
        return "0";
      }
      if (numeric >= 1000000) {
        return `${(numeric / 1000000).toFixed(1)}M`;
      }
      if (numeric >= 1000) {
        return `${(numeric / 1000).toFixed(0)}K`;
      }
      return String(Math.round(numeric));
    }

    function eventAgeToSliderValue(age, lookbackDays) {
      const safeLookback = Math.max(1, Number(lookbackDays || SCREEN_DEFAULT_FILTERS.lookback_days));
      const safeAge = clampNumber(age, 0, safeLookback, 0);
      return safeLookback - safeAge;
    }

    function sliderValueToEventAge(value, lookbackDays) {
      const safeLookback = Math.max(1, Number(lookbackDays || SCREEN_DEFAULT_FILTERS.lookback_days));
      const safeValue = clampNumber(value, 0, safeLookback, safeLookback);
      return Math.round(safeLookback - safeValue);
    }

    function setEventSliderValue(id, age, lookbackDays) {
      const node = document.getElementById(id);
      if (!node) {
        return;
      }
      node.max = String(lookbackDays);
      node.value = String(eventAgeToSliderValue(age, lookbackDays));
    }

    function getEventSliderAge(id, lookbackDays, fallbackAge) {
      const node = document.getElementById(id);
      if (!node) {
        return fallbackAge;
      }
      node.max = String(lookbackDays);
      return sliderValueToEventAge(node.value, lookbackDays);
    }

    function formatEventAge(age) {
      const numeric = Math.max(0, Math.round(Number(age || 0)));
      return numeric === 0 ? "Today" : `${numeric}d ago`;
    }

    function formatTimelinePosition(age, lookbackDays) {
      const numeric = Math.max(0, Math.round(Number(age || 0)));
      const lookback = Math.max(1, Math.round(Number(lookbackDays || SCREEN_DEFAULT_FILTERS.lookback_days)));
      const positionPct = Math.round(((lookback - numeric) / lookback) * 100);
      return numeric === 0
        ? `Today only · ${positionPct}% toward today`
        : `Within last ${numeric}d · ${positionPct}% toward today`;
    }

    function updateEventAgeReadoutFromSlider(sliderId, readoutId) {
      const readout = document.getElementById(readoutId);
      if (!readout) {
        return;
      }
      const age = getEventSliderAge(sliderId, screenFilters.lookback_days, 0);
      readout.textContent = formatTimelinePosition(age, screenFilters.lookback_days);
    }

    function getMacdModeShortLabel(mode) {
      const labels = {
        low_cross_buy: "Bullish below zero",
        high_cross_sell: "Bearish above zero",
        bullish_cross: "Bullish any region",
        bearish_cross: "Bearish any region",
      };
      return labels[String(mode || "")] || labels.low_cross_buy;
    }

    function getMacdControlState(mode) {
      const normalized = String(mode || "");
      if (normalized === "low_cross_buy") return { direction: "bullish_cross", region: "below" };
      if (normalized === "high_cross_sell") return { direction: "bearish_cross", region: "above" };
      return { direction: normalized === "bearish_cross" ? "bearish_cross" : "bullish_cross", region: "any" };
    }

    function getMacdModeFromControls() {
      const direction = document.getElementById("screen-macd-cross-mode")?.value === "bearish_cross"
        ? "bearish_cross"
        : "bullish_cross";
      const region = ["below", "above", "any"].find((value) => document.getElementById(`screen-macd-cross-region-${value}`)?.checked) || "any";
      if (direction === "bullish_cross" && region === "below") return "low_cross_buy";
      if (direction === "bearish_cross" && region === "above") return "high_cross_sell";
      return direction;
    }

    function getRsiModeShortLabel(mode) {
      const labels = {
        cross_up: "Cross Up",
        cross_down: "Cross Down",
      };
      return labels[String(mode || "")] || labels.cross_up;
    }

    function getRsiModeLongLabel(mode) {
      const labels = {
        cross_up: "Cross Up",
        cross_down: "Cross Down",
      };
      return labels[String(mode || "")] || labels.cross_up;
    }

    function getStochModeShortLabel(mode) {
      const labels = {
        cross_up: "K/D Up",
        cross_down: "K/D Down",
      };
      return labels[String(mode || "")] || labels.cross_up;
    }

    function getStochModeLongLabel(mode) {
      const labels = {
        cross_up: "K/D Cross Up",
        cross_down: "K/D Cross Down",
      };
      return labels[String(mode || "")] || labels.cross_up;
    }

    function getStochRegionLongLabel(region) {
      const labels = { below: "Below trigger", above: "Above trigger", any: "Any region" };
      return labels[String(region || "")] || labels.below;
    }

    function getMacdModeLongLabel(mode) {
      const labels = {
        low_cross_buy: "MACD/Signal bullish cross below zero / Buy",
        high_cross_sell: "MACD/Signal bearish cross above zero / Sell",
        bullish_cross: "MACD/Signal bullish cross in any region",
        bearish_cross: "MACD/Signal bearish cross in any region",
      };
      return labels[String(mode || "")] || labels.low_cross_buy;
    }

    function getRangePairValues(minId, maxId, fallbackRange) {
      const minNode = document.getElementById(minId);
      const maxNode = document.getElementById(maxId);
      return {
        min: clampNumber(minNode?.value, fallbackRange.min, fallbackRange.max, fallbackRange.min),
        max: clampNumber(maxNode?.value, fallbackRange.min, fallbackRange.max, fallbackRange.max),
      };
    }

    function getScreenEventReadiness(filters = screenFilters) {
      return [
        filters.rsi_event_enabled
          ? { label: `RSI ${getRsiModeShortLabel(filters.rsi_cross_mode)}`, age: Number(filters.rsi_event_age || 0) }
          : null,
        filters.macd_event_enabled
          ? { label: `MACD ${getMacdModeShortLabel(filters.macd_cross_mode)}`, age: Number(filters.macd_event_age || 0) }
          : null,
        filters.stoch_event_enabled
          ? { label: `StochRSI ${getStochModeShortLabel(filters.stoch_cross_mode)}`, age: Number(filters.stoch_event_age || 0) }
          : null,
        filters.supertrend_event_enabled
          ? { label: `Supertrend ${filters.supertrend_cross_mode === "green_to_red" ? "green to red" : "red to green"}`, age: Number(filters.supertrend_event_age || 0) }
          : null,
        filters.ema_relationship_enabled
          ? { label: `EMA ${filters.ema_relationship_fast}/${filters.ema_relationship_slow} cross`, age: Number(filters.ema_relationship_age || 0) }
          : null,
      ].filter(Boolean).sort((left, right) => right.age - left.age);
    }

    function updateTimelineStepPositions(filters = screenFilters) {
      const badges = getScreenEventReadiness(filters);
      const node = document.getElementById("screen-sequence-badges");
      if (!node) {
        return;
      }
      if (badges.length === 0) {
        node.innerHTML = '<span class="rounded-full bg-white/85 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Volume only</span>';
        return;
      }
      node.innerHTML = badges
        .map((item) => `<span class="rounded-full bg-white/85 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-rose-700">${escapeHtml(item.label)} ${escapeHtml(formatEventAge(item.age))}</span>`)
        .join("");
    }

    function updateTimelineTrackBounds(lookbackDays) {
      ["screen-rsi-cross-age", "screen-macd-cross-age", "screen-stoch-cross-age", "screen-supertrend-cross-age", "screen-ema-relationship-age"].forEach((id) => {
        const node = document.getElementById(id);
        if (node) {
          node.max = String(lookbackDays);
        }
      });
      const leftLabel = `${Math.round(lookbackDays)}d ago`;
      ["screen-rsi-axis-left", "screen-macd-axis-left", "screen-stoch-axis-left", "screen-supertrend-axis-left"].forEach((id) => {
        const node = document.getElementById(id);
        if (node) {
          node.textContent = leftLabel;
        }
      });
      const emaLeftLabel = document.getElementById("screen-ema-relationship-axis-left");
      if (emaLeftLabel) {
        emaLeftLabel.textContent = "Window start";
      }
    }

    function updateScreenSequenceSummary(filters = screenFilters) {
      const node = document.getElementById("screen-sequence-summary");
      if (!node) {
        return;
      }
      const phases = getScreenEventReadiness(filters);
      node.textContent = phases.length > 0
        ? `${phases.map((phase) => phase.label).join(" -> ")} by event point`
        : "Volume-only screen with no event requirements";
    }

    function syncScreenEventToggleChrome(filters = screenFilters) {
      [
        { key: "rsi_event_enabled", checkboxId: "screen-rsi-event-enabled", stepId: "screen-rsi-event-step" },
        { key: "macd_event_enabled", checkboxId: "screen-macd-event-enabled", stepId: "screen-macd-event-step" },
        { key: "stoch_event_enabled", checkboxId: "screen-stoch-event-enabled", stepId: "screen-stoch-event-step" },
        { key: "supertrend_event_enabled", checkboxId: "screen-supertrend-event-enabled", stepId: "screen-supertrend-event-step" },
        { key: "ema_relationship_enabled", checkboxId: "screen-ema-relationship-event-enabled", stepId: "screen-ema-relationship-event-step" },
      ].forEach(({ key, checkboxId, stepId }) => {
        const enabled = Boolean(filters[key]);
        const checkbox = document.getElementById(checkboxId);
        const step = document.getElementById(stepId);
        if (checkbox) {
          checkbox.checked = enabled;
        }
        if (step) {
          step.style.opacity = enabled ? "1" : "0.5";
          step.style.filter = enabled ? "none" : "grayscale(0.2)";
          step.classList.toggle("is-disabled", !enabled);
        }
      });
    }

    function syncScreenFilterStateFromDom() {
      const nextFilters = normalizeScreenFiltersClient({
        lookback_days: screenFilters.lookback_days,
        volume_range: getRangePairValues(
          "screen-volume-min",
          "screen-volume-max",
          { min: 0, max: SCREEN_DEFAULT_FILTERS.volume_range.max }
        ),
        macd_event_enabled: document.getElementById("screen-macd-event-enabled")?.checked,
        rsi_event_enabled: document.getElementById("screen-rsi-event-enabled")?.checked,
        stoch_event_enabled: document.getElementById("screen-stoch-event-enabled")?.checked,
        supertrend_event_enabled: document.getElementById("screen-supertrend-event-enabled")?.checked,
        ema_relationship_enabled: document.getElementById("screen-ema-relationship-event-enabled")?.checked,
        ema_relationship_fast: document.getElementById("screen-ema-relationship-fast")?.value,
        ema_relationship_slow: document.getElementById("screen-ema-relationship-slow")?.value,
        ema_relationship_slope: document.getElementById("screen-ema-relationship-slope")?.value,
        ema_relationship_allowance: document.getElementById("screen-ema-relationship-allowance")?.value,
        rsi_cross_value: document.getElementById("screen-rsi-cross-value")?.value,
        rsi_cross_mode: document.getElementById("screen-rsi-cross-mode")?.value,
        stoch_cross_value: document.getElementById("screen-stoch-cross-value")?.value,
        stoch_cross_mode: document.getElementById("screen-stoch-cross-mode")?.value,
        stoch_cross_region: ["below", "above", "any"].find((region) => document.getElementById(`screen-stoch-cross-region-${region}`)?.checked),
        macd_cross_mode: getMacdModeFromControls(),
        macd_event_age: getEventSliderAge("screen-macd-cross-age", screenFilters.lookback_days, screenFilters.macd_event_age),
        rsi_event_age: getEventSliderAge("screen-rsi-cross-age", screenFilters.lookback_days, screenFilters.rsi_event_age),
        stoch_event_age: getEventSliderAge("screen-stoch-cross-age", screenFilters.lookback_days, screenFilters.stoch_event_age),
        supertrend_cross_mode: document.getElementById("screen-supertrend-cross-mode")?.value,
        supertrend_event_age: getEventSliderAge("screen-supertrend-cross-age", screenFilters.lookback_days, screenFilters.supertrend_event_age),
        ema_relationship_age: getEventSliderAge("screen-ema-relationship-age", screenFilters.lookback_days, screenFilters.ema_relationship_age),
        ema_slope_20: document.getElementById("screen-ema-20-slope")?.value,
        ema_slope_50: document.getElementById("screen-ema-50-slope")?.value,
        ema_slope_200: document.getElementById("screen-ema-200-slope")?.value,
        ema_slope_lookback: document.getElementById("screen-ema-slope-lookback")?.value,
        ema_slope_flat_tolerance: document.getElementById("screen-ema-slope-tolerance")?.value,
      });
      screenFilters = nextFilters;
      applyScreenFilters(nextFilters, { syncPreset: false });
      refreshScreenProjection();
      return nextFilters;
    }

    function applyScreenFilters(filters, { syncPreset = false } = {}) {
      screenFilters = normalizeScreenFiltersClient(filters);
      const chartTA = screenFilters.chart_ta || CHART_TA_DEFAULTS;
      Object.entries({
        macd_fast: "chart-macd-fast",
        macd_slow: "chart-macd-slow",
        macd_signal: "chart-macd-signal",
        rsi_period: "chart-rsi-period",
        stoch_rsi_period: "chart-stoch-rsi-period",
        stoch_rsi_k: "chart-stoch-rsi-k",
        stoch_rsi_d: "chart-stoch-rsi-d",
        supertrend_period: "chart-supertrend-period",
        supertrend_multiplier: "chart-supertrend-multiplier",
      }).forEach(([key, id]) => {
        const node = document.getElementById(id);
        if (node && chartTA[key] !== undefined) {
          node.value = String(chartTA[key]);
        }
      });
      saveChartTAParameters({
        ...chartTA,
        rsi_trigger: screenFilters.rsi_cross_value,
        stoch_trigger: screenFilters.stoch_cross_value,
      });
      const volumeMinNode = document.getElementById("screen-volume-min");
      const volumeMaxNode = document.getElementById("screen-volume-max");
      if (volumeMinNode) volumeMinNode.value = String(screenFilters.volume_range.min);
      if (volumeMaxNode) volumeMaxNode.value = String(screenFilters.volume_range.max);
      updateTimelineTrackBounds(screenFilters.lookback_days);
      setEventSliderValue("screen-macd-cross-age", screenFilters.macd_event_age, screenFilters.lookback_days);
      setEventSliderValue("screen-rsi-cross-age", screenFilters.rsi_event_age, screenFilters.lookback_days);
      setEventSliderValue("screen-stoch-cross-age", screenFilters.stoch_event_age, screenFilters.lookback_days);
        setEventSliderValue("screen-supertrend-cross-age", screenFilters.supertrend_event_age, screenFilters.lookback_days);
      setEventSliderValue("screen-ema-relationship-age", screenFilters.ema_relationship_age, screenFilters.lookback_days);
      [
        ["screen-ema-20-slope", screenFilters.ema_slope_20],
        ["screen-ema-50-slope", screenFilters.ema_slope_50],
        ["screen-ema-200-slope", screenFilters.ema_slope_200],
        ["screen-ema-slope-lookback", screenFilters.ema_slope_lookback],
        ["screen-ema-slope-tolerance", screenFilters.ema_slope_flat_tolerance],
        ["screen-ema-relationship-fast", screenFilters.ema_relationship_fast],
        ["screen-ema-relationship-slow", screenFilters.ema_relationship_slow],
        ["screen-ema-relationship-slope", screenFilters.ema_relationship_slope],
        ["screen-ema-relationship-allowance", screenFilters.ema_relationship_allowance],
      ].forEach(([id, value]) => {
        const node = document.getElementById(id);
        if (node) node.value = String(value);
      });
      syncScreenEventToggleChrome(screenFilters);
      const rsiCrossNode = document.getElementById("screen-rsi-cross-value");
      if (rsiCrossNode) {
        rsiCrossNode.value = String(screenFilters.rsi_cross_value);
      }
      const rsiModeNode = document.getElementById("screen-rsi-cross-mode");
      if (rsiModeNode) {
        rsiModeNode.value = String(screenFilters.rsi_cross_mode || SCREEN_DEFAULT_FILTERS.rsi_cross_mode);
      }
      const stochCrossNode = document.getElementById("screen-stoch-cross-value");
      if (stochCrossNode) {
        stochCrossNode.value = String(screenFilters.stoch_cross_value);
      }
      const stochModeNode = document.getElementById("screen-stoch-cross-mode");
      if (stochModeNode) {
        stochModeNode.value = String(screenFilters.stoch_cross_mode || SCREEN_DEFAULT_FILTERS.stoch_cross_mode);
      }
      ["below", "above", "any"].forEach((region) => {
        const node = document.getElementById(`screen-stoch-cross-region-${region}`);
        if (node) node.checked = region === String(screenFilters.stoch_cross_region || "below");
      });
      const macdModeNode = document.getElementById("screen-macd-cross-mode");
      if (macdModeNode) {
        macdModeNode.value = getMacdControlState(screenFilters.macd_cross_mode).direction;
      }
      const macdControlState = getMacdControlState(screenFilters.macd_cross_mode);
      ["below", "above", "any"].forEach((region) => {
        const node = document.getElementById(`screen-macd-cross-region-${region}`);
        if (node) node.checked = region === macdControlState.region;
      });
      const supertrendModeNode = document.getElementById("screen-supertrend-cross-mode");
      if (supertrendModeNode) supertrendModeNode.value = String(screenFilters.supertrend_cross_mode || SCREEN_DEFAULT_FILTERS.supertrend_cross_mode);
      const volumeReadout = document.getElementById("screen-volume-readout");
      if (volumeReadout) {
        volumeReadout.textContent = `${formatCompactVolume(screenFilters.volume_range.min)} - ${formatCompactVolume(screenFilters.volume_range.max)}`;
      }
      const rsiCrossReadout = document.getElementById("screen-rsi-cross-value-readout");
      if (rsiCrossReadout) {
        rsiCrossReadout.textContent = `${Math.round(screenFilters.rsi_cross_value)}`;
      }
      const rsiModeReadout = document.getElementById("screen-rsi-mode-readout");
      if (rsiModeReadout) {
        rsiModeReadout.textContent = getRsiModeLongLabel(screenFilters.rsi_cross_mode);
      }
      const stochCrossReadout = document.getElementById("screen-stoch-cross-value-readout");
      if (stochCrossReadout) {
        stochCrossReadout.textContent = `${Math.round(screenFilters.stoch_cross_value)}`;
      }
      const stochModeReadout = document.getElementById("screen-stoch-mode-readout");
      if (stochModeReadout) {
        stochModeReadout.textContent = `${getStochModeLongLabel(screenFilters.stoch_cross_mode)} · ${getStochRegionLongLabel(screenFilters.stoch_cross_region)}`;
      }
      const macdReadout = document.getElementById("screen-macd-cross-readout");
      if (macdReadout) {
        macdReadout.textContent = formatTimelinePosition(screenFilters.macd_event_age, screenFilters.lookback_days);
      }
      const macdModeReadout = document.getElementById("screen-macd-mode-readout");
      if (macdModeReadout) {
        macdModeReadout.textContent = getMacdModeLongLabel(screenFilters.macd_cross_mode);
      }
      const rsiEventReadout = document.getElementById("screen-rsi-cross-readout");
      if (rsiEventReadout) {
        rsiEventReadout.textContent = formatTimelinePosition(screenFilters.rsi_event_age, screenFilters.lookback_days);
      }
      const stochReadout = document.getElementById("screen-stoch-cross-readout");
      if (stochReadout) {
        stochReadout.textContent = formatTimelinePosition(screenFilters.stoch_event_age, screenFilters.lookback_days);
      }
      const supertrendReadout = document.getElementById("screen-supertrend-cross-readout");
      if (supertrendReadout) supertrendReadout.textContent = formatTimelinePosition(screenFilters.supertrend_event_age, screenFilters.lookback_days);
      const emaRelationshipReadout = document.getElementById("screen-ema-relationship-event-readout");
      if (emaRelationshipReadout) emaRelationshipReadout.textContent = `Cross within last ${screenFilters.ema_relationship_age}d`;
      const emaRelationshipLabel = document.getElementById("screen-ema-relationship-readout");
      if (emaRelationshipLabel) emaRelationshipLabel.textContent = `${screenFilters.ema_relationship_fast} / ${screenFilters.ema_relationship_slow} · ${screenFilters.ema_relationship_slope} · ±${Number(screenFilters.ema_relationship_allowance).toFixed(2)}%`;
      const supertrendModeReadout = document.getElementById("screen-supertrend-mode-readout");
      if (supertrendModeReadout) supertrendModeReadout.textContent = screenFilters.supertrend_cross_mode === "green_to_red" ? "Green to red" : "Red to green";
      updateTimelineStepPositions(screenFilters);
      updateScreenSequenceSummary(screenFilters);
      if (syncPreset) {
        populateScreenPresetSelect();
      }
    }

    function getScreenFiltersForRequest() {
      return syncScreenFilterStateFromDom();
    }

    function buildScreenFilterParams() {
      const filters = getScreenFiltersForRequest();
      const params = new URLSearchParams();
      params.set("lookback_days", String(filters.lookback_days));
      params.set("volume_min", String(filters.volume_range.min));
      params.set("volume_max", String(filters.volume_range.max));
      params.set("macd_event_enabled", filters.macd_event_enabled ? "true" : "false");
      params.set("rsi_event_enabled", filters.rsi_event_enabled ? "true" : "false");
      params.set("stoch_event_enabled", filters.stoch_event_enabled ? "true" : "false");
      params.set("rsi_cross_value", String(filters.rsi_cross_value));
      params.set("rsi_cross_mode", String(filters.rsi_cross_mode || SCREEN_DEFAULT_FILTERS.rsi_cross_mode));
      params.set("stoch_cross_value", String(filters.stoch_cross_value));
      params.set("stoch_cross_mode", String(filters.stoch_cross_mode || SCREEN_DEFAULT_FILTERS.stoch_cross_mode));
      params.set("stoch_cross_region", String(filters.stoch_cross_region || SCREEN_DEFAULT_FILTERS.stoch_cross_region));
      params.set("macd_cross_mode", String(filters.macd_cross_mode || SCREEN_DEFAULT_FILTERS.macd_cross_mode));
      params.set("macd_event_age", String(filters.macd_event_age));
      params.set("rsi_event_age", String(filters.rsi_event_age));
      params.set("stoch_event_age", String(filters.stoch_event_age));
      params.set("supertrend_event_enabled", filters.supertrend_event_enabled ? "true" : "false");
      params.set("supertrend_cross_mode", String(filters.supertrend_cross_mode || SCREEN_DEFAULT_FILTERS.supertrend_cross_mode));
      params.set("supertrend_event_age", String(filters.supertrend_event_age));
      params.set("ema_relationship_enabled", filters.ema_relationship_enabled ? "true" : "false");
      params.set("ema_relationship_fast", String(filters.ema_relationship_fast));
      params.set("ema_relationship_slow", String(filters.ema_relationship_slow));
      params.set("ema_relationship_slope", String(filters.ema_relationship_slope));
      params.set("ema_relationship_allowance", String(filters.ema_relationship_allowance));
      params.set("ema_relationship_age", String(filters.ema_relationship_age));
      const chartTA = getChartTAParameters();
      params.set("supertrend_period", String(chartTA.supertrend_period));
      params.set("supertrend_multiplier", String(chartTA.supertrend_multiplier));
      params.set("ema_slope_20", String(filters.ema_slope_20 || "any"));
      params.set("ema_slope_50", String(filters.ema_slope_50 || "any"));
      params.set("ema_slope_200", String(filters.ema_slope_200 || "any"));
      params.set("ema_slope_lookback", String(filters.ema_slope_lookback));
      params.set("ema_slope_flat_tolerance", String(filters.ema_slope_flat_tolerance));
      const presetSelect = document.getElementById("screen-preset-select");
      if (presetSelect && presetSelect.value) {
        params.set("preset_name", presetSelect.value);
      }
      return params;
    }

    function populateScreenPresetSelect() {
      const select = document.getElementById("screen-preset-select");
      if (!select) {
        return;
      }
      const requestedValue = String(readStickyValue(LAST_SCREEN_PRESET_KEY, screenPresetCatalog.active_name || "")).trim();
      select.innerHTML = '<option value="">Custom</option>';
      (Array.isArray(screenPresetCatalog.presets) ? screenPresetCatalog.presets : []).forEach((preset) => {
        if (!preset || !preset.name) {
          return;
        }
        const option = document.createElement("option");
        option.value = String(preset.name);
        option.textContent = String(preset.name);
        select.appendChild(option);
      });
      const hasRequested = requestedValue
        && Array.from(select.options || []).some((option) => option.value === requestedValue);
      select.value = hasRequested ? requestedValue : "";
    }

    async function loadScreenPresets() {
      const resp = await fetch("/api/screen/presets", { cache: "no-store" });
      if (!resp.ok) {
        throw new Error("Could not load screener presets");
      }
      const payload = await resp.json();
      screenPresetCatalog = {
        active_name: String(payload?.active_name || ""),
        default_filters: normalizeScreenFiltersClient(payload?.default_filters || SCREEN_DEFAULT_FILTERS),
        presets: Array.isArray(payload?.presets) ? payload.presets.map((preset) => ({
          name: String(preset?.name || "").trim(),
          filters: normalizeScreenFiltersClient(preset?.filters || SCREEN_DEFAULT_FILTERS),
        })).filter((preset) => preset.name) : [],
      };
      populateScreenPresetSelect();
      const presetName = String(readStickyValue(LAST_SCREEN_PRESET_KEY, screenPresetCatalog.active_name || "")).trim();
      const preset = screenPresetCatalog.presets.find((entry) => entry.name === presetName)
        || screenPresetCatalog.presets.find((entry) => entry.name === screenPresetCatalog.active_name);
      if (preset) {
        applyScreenFilters(preset.filters);
        const nameNode = document.getElementById("screen-preset-name");
        if (nameNode) {
          nameNode.value = preset.name;
        }
        writeStickyValue(LAST_SCREEN_PRESET_KEY, preset.name);
        const select = document.getElementById("screen-preset-select");
        if (select) {
          select.value = preset.name;
        }
      } else {
        applyScreenFilters(screenPresetCatalog.default_filters || SCREEN_DEFAULT_FILTERS);
      }
      return screenPresetCatalog;
    }

    async function applyScreenPreset(name) {
      const presetName = String(name || "").trim();
      if (!presetName) {
        writeStickyValue(LAST_SCREEN_PRESET_KEY, "");
        return;
      }
      const preset = screenPresetCatalog.presets.find((entry) => entry.name === presetName);
      if (!preset) {
        writeStickyValue(LAST_SCREEN_PRESET_KEY, "");
        return;
      }
      writeStickyValue(LAST_SCREEN_PRESET_KEY, preset.name);
      applyScreenFilters(preset.filters);
      const nameNode = document.getElementById("screen-preset-name");
      if (nameNode) {
        nameNode.value = preset.name;
      }
    }

    async function saveScreenPreset() {
      const nameNode = document.getElementById("screen-preset-name");
      const presetName = String(nameNode?.value || "").trim();
      if (!presetName) {
        showToast("Enter a preset name first.", true);
        return;
      }
      const nextPreset = {
        name: presetName,
        filters: {
          ...getScreenFiltersForRequest(),
          chart_ta: {
            ...getChartTAParameters(),
            rsi_trigger: Number(document.getElementById("screen-rsi-cross-value")?.value || 50),
            stoch_trigger: Number(document.getElementById("screen-stoch-cross-value")?.value || 20),
          },
        },
      };
      const nextPresets = Array.isArray(screenPresetCatalog.presets)
        ? screenPresetCatalog.presets.filter((preset) => preset && preset.name !== presetName)
        : [];
      nextPresets.push(nextPreset);
      const resp = await fetch("/api/screen/presets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          active_name: presetName,
          presets: nextPresets,
        }),
      });
      const payload = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(payload.detail || "Could not save preset");
      }
      screenPresetCatalog = {
        active_name: String(payload?.active_name || presetName),
        default_filters: normalizeScreenFiltersClient(payload?.default_filters || SCREEN_DEFAULT_FILTERS),
        presets: Array.isArray(payload?.presets) ? payload.presets.map((preset) => ({
          name: String(preset?.name || "").trim(),
          filters: normalizeScreenFiltersClient(preset?.filters || SCREEN_DEFAULT_FILTERS),
        })).filter((preset) => preset.name) : [],
      };
      writeStickyValue(LAST_SCREEN_PRESET_KEY, presetName);
      populateScreenPresetSelect();
      const select = document.getElementById("screen-preset-select");
      if (select) {
        select.value = presetName;
      }
      showToast(`Saved preset: ${presetName}`);
    }

    function bindScreenControlInputs() {
      [
        "screen-volume-min",
        "screen-volume-max",
        "screen-rsi-cross-value",
        "screen-rsi-event-enabled",
        "screen-rsi-cross-mode",
        "screen-stoch-cross-value",
        "screen-stoch-event-enabled",
        "screen-stoch-cross-mode",
        "screen-supertrend-event-enabled",
        "screen-supertrend-cross-mode",
        "screen-macd-event-enabled",
        "screen-macd-cross-mode",
        "screen-macd-cross-age",
        "screen-rsi-cross-age",
        "screen-stoch-cross-age",
        "screen-supertrend-cross-age",
        "screen-ema-relationship-age",
        "screen-ema-relationship-event-enabled",
        "screen-ema-relationship-fast",
        "screen-ema-relationship-slow",
        "screen-ema-relationship-mode",
        "screen-ema-relationship-slope",
        "screen-ema-relationship-lookback",
        "screen-ema-relationship-tolerance",
        "screen-ema-20-slope",
        "screen-ema-50-slope",
        "screen-ema-200-slope",
        "screen-ema-slope-lookback",
        "screen-ema-slope-tolerance",
      ].forEach((id) => {
        const node = document.getElementById(id);
        if (!node || node.dataset.bound === "1") {
          return;
        }
        node.dataset.bound = "1";
        node.addEventListener("input", () => {
          const readoutIdBySlider = {
            "screen-macd-cross-age": "screen-macd-cross-readout",
            "screen-rsi-cross-age": "screen-rsi-cross-readout",
            "screen-stoch-cross-age": "screen-stoch-cross-readout",
            "screen-supertrend-cross-age": "screen-supertrend-cross-readout",
            "screen-ema-relationship-age": "screen-ema-relationship-event-readout",
          };
          const readoutId = readoutIdBySlider[id];
          if (readoutId) {
            updateEventAgeReadoutFromSlider(id, readoutId);
          }
          syncScreenFilterStateFromDom();
        });
      });
      [
        "chart-macd-fast",
        "chart-macd-slow",
        "chart-macd-signal",
        "chart-rsi-period",
        "chart-stoch-rsi-period",
        "chart-stoch-rsi-k",
        "chart-stoch-rsi-d",
        "chart-supertrend-period",
        "chart-supertrend-multiplier",
      ].forEach((id) => {
        const node = document.getElementById(id);
        if (!node || node.dataset.taApplyBound === "1") {
          return;
        }
        node.dataset.taApplyBound = "1";
        node.addEventListener("input", updateChartTAApplyButton);
      });
      ["screen-rsi-cross-value", "screen-stoch-cross-value"].forEach((id) => {
        const node = document.getElementById(id);
        if (!node || node.dataset.chartTriggerBound === "1") {
          return;
        }
        node.dataset.chartTriggerBound = "1";
        node.addEventListener("input", scheduleChartTriggerRefresh);
      });
      [
        "screen-ema-relationship-event-enabled",
        "screen-ema-relationship-fast",
        "screen-ema-relationship-slow",
        "screen-ema-relationship-mode",
        "screen-supertrend-event-enabled",
      ].forEach((id) => {
        const node = document.getElementById(id);
        if (!node || node.dataset.chartOverlayBound === "1") {
          return;
        }
        node.dataset.chartOverlayBound = "1";
        node.addEventListener("input", scheduleChartTriggerRefresh);
        node.addEventListener("change", scheduleChartTriggerRefresh);
      });
      ["below", "above", "any"].forEach((region) => {
        const node = document.getElementById(`screen-stoch-cross-region-${region}`);
        if (!node) return;
        if (node.dataset.screenRegionBound === "1") {
          return;
        }
        node.dataset.screenRegionBound = "1";
        node.addEventListener("change", syncScreenFilterStateFromDom);
      });
      ["below", "above", "any"].forEach((region) => {
        const node = document.getElementById(`screen-macd-cross-region-${region}`);
        if (!node || node.dataset.screenRegionBound === "1") {
          return;
        }
        node.dataset.screenRegionBound = "1";
        node.addEventListener("change", syncScreenFilterStateFromDom);
      });
      applyScreenFilters(screenFilters);
      setChartTAParametersApplied();
    }

    function updateTabChrome(tab) {
      const screenerControls = document.getElementById("nav-screener-controls");
      const chartRangeControls = document.getElementById("nav-chart-range-controls");
      const context = document.getElementById("nav-tab-context");
      if (screenerControls) {
        screenerControls.classList.toggle("hidden", tab !== "screener");
      }
      if (chartRangeControls) {
        chartRangeControls.classList.toggle("hidden", tab === "screener");
      }
      if (!context) {
        return;
      }
      if (tab === "playbook") {
        context.textContent = "Graph Playground: experiment with visual trade setups";
      } else {
        context.textContent = "Screener: place the event markers, then click Run Screener";
      }
    }
    async function loadMarketStatus(source = tickerScanScope) {
      const marketStatus = document.getElementById("shortlist-market-status");
      if (!marketStatus) {
        return null;
      }

      try {
        const normalizedSource = normalizeScanScope(source);
        const statusParams = new URLSearchParams();
        statusParams.set("stale_after_days", "0");
        statusParams.set("source", normalizedSource);
        if (normalizedSource === "list") {
          const universeParams = getUniverseFilterParams();
          const tickerList = universeParams.get("ticker_list");
          if (tickerList) {
            statusParams.set("ticker_list", tickerList);
          }
        }
        const resp = await fetch(`/api/market-status?${statusParams.toString()}`);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Market status request failed");
        }

        if (data.is_stale) {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-amber-600";
          marketStatus.textContent = `${getActiveSourceLabel(normalizedSource)}: market data needs top-up · latest ${data.latest_market_date || "unknown"} · stale ${Number(data.stale_tickers || 0)} · missing ${Number(data.missing_tickers || 0)}`;
        } else {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-emerald-600";
          marketStatus.textContent = `${getActiveSourceLabel(normalizedSource)}: market data fresh through ${data.latest_market_date || "unknown"} · ${Number(data.fresh_tickers || data.tracked_tickers || 0)} active tickers`;
        }
        return data;
      } catch (err) {
        marketStatus.className = "text-xs font-bold uppercase tracking-wide text-rose-600";
        marketStatus.textContent = "Could not determine market data freshness";
        return null;
      }
    }

    async function ensureGuiMarketBackbone(options = {}) {
      const allowRefresh = options.allowRefresh === true;
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
      return ensureGuiMarketBackbone({ allowRefresh: true });
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
      if (tab === 'playbook') {
        loadPlaybook().catch((err) => {
          console.warn("Playbook failed to load", err);
        });
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
      const shortlistRefreshBtn = document.getElementById("shortlist-refresh-btn");
      const marketStatus = document.getElementById("shortlist-market-status");
      const shortlistStatus = document.getElementById("shortlist-status");
      const activeSourceLabel = getActiveSourceLabel(source);

      if (shortlistRefreshBtn) {
        shortlistRefreshBtn.disabled = true;
        shortlistRefreshBtn.textContent = `Refreshing ${activeSourceLabel}...`;
      }
      if (marketStatus) {
        marketStatus.className = "text-xs font-bold uppercase tracking-wide text-indigo-600";
        marketStatus.textContent = `Refreshing ${activeSourceLabel} market data and rebuilding shortlist...`;
      }
      if (shortlistStatus) {
        shortlistStatus.textContent = `Waiting for fresh ${activeSourceLabel} market data...`;
      }

      try {
        if (source === "list") {
          try {
            await persistCustomTickerListsToServer({
              active_name: normalizeListName(customTickerListActiveName || customTickerListName),
              lists: customTickerLists,
            });
          } catch (persistErr) {
            console.warn("Could not persist active saved list before refresh", persistErr);
          }
        }
        setNavScanProgress({
          show: true,
          contextLabel: "Market",
          contextText: "Checking...",
          contextPct: 0,
          contextWorking: false,
        });
        startJobProgressPolling("market-refresh", "Global");
        const refreshParams = new URLSearchParams();
        refreshParams.set("depth", "180");
        refreshParams.set("max_workers", "8");
        refreshParams.set("force", "true");
        refreshParams.set("stale_after_days", "0");
        refreshParams.set("source", source);
        if (source === "list") {
          const universeParams = getUniverseFilterParams();
          const tickerList = universeParams.get("ticker_list");
          if (tickerList) {
            refreshParams.set("ticker_list", tickerList);
          }
        }
        const resp = await fetch(`/api/market-data/refresh?${refreshParams.toString()}`, {
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
        playbookLoaded = false;
        playbookSourceSignature = "";
        await loadMarketStatus();
        if (!document.getElementById("tab-playbook")?.classList.contains("hidden")) {
          await loadPlaybook(true);
        }
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
        if (shortlistRefreshBtn) {
          shortlistRefreshBtn.disabled = false;
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
      tickerUniverseExplicitlyChosen = true;
      updateListSelectChrome();
      syncScreenerRunButtonState(false);
      updateScanActionButtonsState();
      updateBacktestRunButtonState();
      updateRangeChrome();
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
    let lastScreenCandidatePool = [];
    let lastScreenScanFilters = null;
    let lastScreenMeta = {
      strategy_name: "",
      preset_name: "",
      scan_scope: "",
      exchange: "",
      ticker_list: "",
      disqualifiers: normalizeScreenDisqualifiers(),
    };
    let screenPresetCatalog = {
      active_name: "",
      default_filters: { ...SCREEN_DEFAULT_FILTERS },
      presets: [],
    };
    let screenFilters = JSON.parse(JSON.stringify(SCREEN_DEFAULT_FILTERS));
    let appliedChartTAParameters = null;
    let chartTriggerRefreshTimer = null;
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
        preset_name: String(meta.preset_name || "").trim(),
        scan_scope: String(meta.scan_scope || "").trim(),
        exchange: String(meta.exchange || "").trim(),
        ticker_list: String(meta.ticker_list || "").trim(),
        disqualifiers: normalizeScreenDisqualifiers(meta.disqualifiers || screenDisqualifiers),
      };
      syncExportMatchesButtonState();
    }

    function projectCachedScreenResults(filters = screenFilters) {
      if (!Array.isArray(lastScreenCandidatePool) || lastScreenCandidatePool.length === 0) {
        return null;
      }
      const eventSpecs = [
        { enabled: "macd_event_enabled", age: "macd_event_age", value: "macd_cross_days_ago", label: "MACD" },
        { enabled: "rsi_event_enabled", age: "rsi_event_age", value: "rsi_cross_days_ago", label: "RSI" },
        { enabled: "stoch_event_enabled", age: "stoch_event_age", value: "stoch_cross_days_ago", label: "StochRSI" },
        { enabled: "supertrend_event_enabled", age: "supertrend_event_age", value: "supertrend_cross_days_ago", label: "Supertrend" },
      ];
      const matches = lastScreenCandidatePool.filter((item) => {
        const avgVolume = Number(item.recent_avg_volume || 0);
        if (avgVolume < Number(filters.volume_range?.min || 0) || avgVolume > Number(filters.volume_range?.max || 0)) {
          return false;
        }
        for (const [period, key] of [[20, "ema_slope_20"], [50, "ema_slope_50"], [200, "ema_slope_200"]]) {
          const selected = String(filters[key] || "any");
          if (selected !== "any" && selected !== String(item[`ema_slope_${period}_state`] || "unknown")) {
            return false;
          }
        }
        return eventSpecs.every((spec) => {
          if (!filters[spec.enabled]) return true;
          const rawAge = item[spec.value];
          const age = Number(rawAge);
          return rawAge !== null && rawAge !== undefined
            && Number.isFinite(age) && age <= Number(filters[spec.age] || 0);
        });
      }).map((item) => {
        const activeEvents = eventSpecs
          .filter((spec) => filters[spec.enabled])
          .map((spec) => ({ label: spec.label, age: Number(item[spec.value]) }))
          .sort((a, b) => b.age - a.age);
        const sequence = activeEvents.map((event) => event.label).join(" -> ") || "Volume only";
        const totalAge = activeEvents.reduce((sum, event) => sum + event.age, 0);
        const rsi = Number(item.rsi || 0);
        const rsiLevel = Number(filters.rsi_cross_value || 50);
        const score = Math.round((Math.max(0, Number(filters.lookback_days || 30) * 3 - totalAge)
          + Math.min(18, Math.log10(Math.max(Number(item.recent_avg_volume || 1), 1)) * 3)
          + (filters.rsi_event_enabled ? Math.max(0, 18 - Math.abs(rsi - rsiLevel)) : 0)) * 100) / 100;
        return {
          ...item,
          event_sequence: sequence,
          status: activeEvents.length ? "Sequence aligned" : "Volume aligned",
          score,
          macd_event_enabled: Boolean(filters.macd_event_enabled),
          rsi_event_enabled: Boolean(filters.rsi_event_enabled),
          stoch_event_enabled: Boolean(filters.stoch_event_enabled),
        };
      });
      return matches.sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
    }

    function canProjectScreenFiltersLocally(filters = screenFilters) {
      if (!lastScreenScanFilters) return false;
      const localKeys = [
        "volume_range", "macd_event_enabled", "rsi_event_enabled", "stoch_event_enabled",
        "supertrend_event_enabled", "macd_event_age", "rsi_event_age", "stoch_event_age", "supertrend_event_age",
        "ema_slope_20", "ema_slope_50", "ema_slope_200",
      ];
      const comparable = (value) => JSON.stringify(value);
      const scan = lastScreenScanFilters;
      return Object.keys(filters).every((key) => localKeys.includes(key)
        || comparable(filters[key]) === comparable(scan[key]));
    }

    function refreshScreenProjection() {
      if (!canProjectScreenFiltersLocally(screenFilters)) return false;
      const projected = projectCachedScreenResults(screenFilters);
      if (!projected) return false;
      const list = document.getElementById("ticker-list");
      const count = document.getElementById("match-count");
      if (count) count.textContent = String(projected.length);
      if (list) {
        const visibleMatches = projected.slice(0, 100);
        list.innerHTML = visibleMatches.length
          ? ""
          : '<div class="text-sm text-slate-400 italic p-4 text-center">No matching tickers for the current controls.</div>';
        if (projected.length > visibleMatches.length) {
          const notice = document.createElement("div");
          notice.className = "mb-2 rounded-lg bg-amber-50 px-3 py-2 text-[11px] font-semibold text-amber-700";
          notice.textContent = `Showing the top 100 of ${projected.length} matches.`;
          list.appendChild(notice);
        }
        visibleMatches.forEach((item, idx) => {
          const card = document.createElement("div");
          card.className = "ticker-card p-3 bg-slate-50 border-l-4 border-indigo-500 rounded shadow-sm hover:shadow-md hover:bg-indigo-50 cursor-pointer transition-all";
          card.onclick = () => loadChart(item.ticker);
          const change = Number(item.change_pct || 0);
          card.innerHTML = `
            <div class="flex justify-between items-start">
              <div class="flex flex-col"><div class="flex items-baseline gap-1.5"><span class="font-bold text-slate-800 text-lg leading-none">${escapeHtml(item.ticker)}</span><span class="text-[10px] font-bold text-indigo-400">#${idx + 1}</span></div><span class="mt-1 text-[11px] text-slate-500">${escapeHtml(item.name || "")}</span><span class="text-[10px] text-indigo-600 mt-1 uppercase tracking-wider">${escapeHtml(item.status || "TRENDING")}</span></div>
              <div class="flex flex-col items-end"><span class="text-slate-800 font-bold font-mono">${Number(item.close || 0).toFixed(2)}</span><span class="text-[10px] ${change >= 0 ? "text-emerald-500" : "text-rose-500"} font-mono">${change >= 0 ? "+" : ""}${change.toFixed(2)}%</span></div>
            </div>
            <div class="mt-2 text-[11px] font-semibold text-rose-700">${escapeHtml(item.event_sequence || "Event sequence")}</div>
            <div class="mt-2 grid grid-cols-3 gap-2 rounded-lg bg-slate-100/80 px-2 py-2 text-[10px] font-semibold text-slate-500"><div>RSI <span class="block text-sm font-bold text-slate-800">${Number(item.rsi || 0).toFixed(1)}</span></div><div>VOL20 <span class="block text-sm font-bold text-slate-800">${formatCompactVolume(Number(item.recent_avg_volume || item.volume || 0))}</span></div><div>SCORE <span class="block text-sm font-bold text-slate-800">${Number(item.score || 0).toFixed(1)}</span></div></div>`;
          list.appendChild(card);
        });
      }
      setLastScreenMatches(projected, lastScreenMeta);
      return true;
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
        pagePanel: document.getElementById("page-progress-banner"),
        pageBar: document.getElementById("page-progress-bar"),
        pageText: document.getElementById("page-progress-text"),
        pageLabel: document.getElementById("page-progress-label"),
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
      if (show === true && nodes.pagePanel) {
        nodes.pagePanel.hidden = false;
      } else if (show === false && nodes.pagePanel) {
        nodes.pagePanel.hidden = true;
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

      if (nodes.pageLabel) {
        const nextLabel = state.contextLabel || state.globalLabel || nodes.contextLabel?.textContent || nodes.globalLabel?.textContent || "Working";
        nodes.pageLabel.textContent = nextLabel;
      }
      if (nodes.pageText) {
        const nextText = state.globalText || state.contextText || nodes.globalText?.textContent || nodes.contextText?.textContent || "Working...";
        nodes.pageText.textContent = nextText;
      }
      if (nodes.pageBar) {
        const rawPct = state.globalPct !== undefined
          ? state.globalPct
          : state.contextPct !== undefined
            ? state.contextPct
            : parseFloat(String(nodes.globalBar?.style.width || nodes.pageBar.style.width || "0").replace("%", ""));
        const pct = Math.max(0, Math.min(100, Number(rawPct) || 0));
        nodes.pageBar.style.width = `${pct}%`;
        const working = state.globalWorking !== undefined
          ? Boolean(state.globalWorking)
          : state.contextWorking !== undefined
            ? Boolean(state.contextWorking)
            : false;
        nodes.pageBar.classList.toggle("animate-pulse", working);
      }
    }

    function syncScreenerRunButtonState(running = false) {
      const runBtn = document.getElementById("run-btn");
      if (!runBtn) {
        return;
      }
      runBtn.dataset.running = running ? "1" : "0";
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
      runBtn.disabled = !tickerUniverseExplicitlyChosen;
      runBtn.title = tickerUniverseExplicitlyChosen ? "Run the control-based screener" : "Choose a ticker universe first";
    }

    function updateScanActionButtonsState() {
      const readiness = tickerUniverseExplicitlyChosen
        ? { ready: true, reason: "Run the control-based screener" }
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
      syncScreenerRunButtonState(false);
      updateScanActionButtonsState();
    }

    async function runScreen(customDsl = null) {
      const list = document.getElementById("ticker-list");
      const spinner = document.getElementById("loading-spinner");
      const scanBtn = document.getElementById("scan-btn");
      const runBtn = document.getElementById("run-btn");
      const errorSection = document.getElementById("error-section");
      const errorList = document.getElementById("error-list");

      if (!tickerUniverseExplicitlyChosen) {
        resetScanUI();
        return;
      }

      if (normalizeScanScope(tickerScanScope) === "list" && getScopeTickers(tickerScanScope).length === 0) {
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

      syncScreenerRunButtonState(true);

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
        const controlParams = buildScreenFilterParams();
        screenParams.forEach((value, key) => {
          universeParams.set(key, value);
        });
        controlParams.forEach((value, key) => {
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

        // Fake progress only for the early part of the wait. Once the bar
        // reaches 90%, hold it steady and mark it as working so the UI stays
        // calm while the backend finishes.
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
            setNavScanProgress({
              contextLabel: "Screen",
              contextText: "WORKING",
              contextPct: 90,
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
              await exportTopMatchesToGoogleDrive(true);
            } catch (autoExportErr) {
              showToast(`Google auto-export failed: ${autoExportErr.message || autoExportErr}`, true);
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
              const volumeVal = Number(item.recent_avg_volume ?? item.volume ?? 0);
              const changePctVal = Number(item.change_pct ?? 0);
              const scoreVal = Number(item.score ?? 0);
              const rsiVal = Number(item.rsi ?? 0);
              const sequenceText = String(item.event_sequence || "").trim();

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
                                <span class="mt-1 text-[11px] text-slate-500">${escapeHtml(item.name || "")}</span>
                                <span class="text-[10px] ${statusColor} mt-1 uppercase tracking-wider">${statusText}</span>
                            </div>
                            <div class="flex flex-col items-end">
                              <span class="text-slate-800 font-bold font-mono">${closeVal.toFixed(2)}</span>
                                <span class="text-[10px] ${changeColor} font-mono">${sign}${changeVal}%</span>
                            </div>
                        </div>
                        <div class="mt-2 text-[11px] font-semibold text-rose-700">${escapeHtml(sequenceText || "Event sequence")}</div>
                        <div class="mt-2 grid grid-cols-3 gap-2 rounded-lg bg-slate-100/80 px-2 py-2 text-[10px] font-semibold text-slate-500">
                            <div>RSI <span class="block text-sm font-bold text-slate-800">${Number.isFinite(rsiVal) ? rsiVal.toFixed(1) : "-"}</span></div>
                            <div>VOL20 <span class="block text-sm font-bold text-slate-800">${formatCompactVolume(volumeVal)}</span></div>
                            <div>SCORE <span class="block text-sm font-bold text-slate-800">${scoreVal.toFixed(1)}</span></div>
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
          preset_name: String(document.getElementById("screen-preset-select")?.value || "").trim(),
          scan_scope: normalizeScanScope(tickerScanScope),
          ticker_list: getUniverseFilterParams().get("ticker_list") || "",
          disqualifiers: screenDisqualifiers,
        });
        resetScanUI();
      }
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
        if (strategyName) {
          chartQuery.set("strategy", strategyName);
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
      const taControls = document.getElementById("chart-ta-controls");
      const taSlot = document.getElementById("screen-ta-controls-slot");
      if (taControls && taSlot) {
        taSlot.appendChild(taControls);
      }
      restoreChartTAParameters();
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
      updateBacktestStrategyCount();
      syncBacktestStrategyCheckboxChrome();
      bindScreenControlInputs();
      updateScanActionButtonsState();
      updateBacktestRunButtonState();
      updateRangeChrome();
      const playbookRiskNode = document.getElementById("playbook-risk-pct");
      if (playbookRiskNode) {
        playbookRiskNode.value = String(getPlaybookRiskPct());
      }
      await loadMarketStatus();
      try {
        await loadScreenPresets();
      } catch (err) {
        console.warn("Could not load screener presets", err);
        applyScreenFilters(SCREEN_DEFAULT_FILTERS);
      }
      setChartTAParametersApplied();
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
      loadPlaybook,
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
      applyScreenPreset,
      resetDashboardTabPreference,
      runScreen,
      saveScreenPreset,
      saveAsStrategy,
      saveFromModal,
      saveStrategy,
      activateCustomTickerList,
      setActiveCustomTickerList,
      setBacktestSourceMode,
      setListBuilderExchange,
      setListBuilderSearch,
      setListBuilderList,
      toggleListBuilderSelectedOnly,
      setScanSource,
      setScreenAutoExportEnabled,
      setScreenDisqualifier,
      setRange,
      startJobProgressPolling,
      stopJobProgressPolling,
      dashboardReadyPromise,
      deleteListEditorSelection,
      showTab,
      testMe,
      toggleStrategyPanel,
      toggleVisibleListBuilderTickers,
    });

