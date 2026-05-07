let backtestSourceMode = "saved";
    let shortlistLoaded = false;
    let shortlistRows = [];
    let shortlistFilter = "All";
    let swarmLoaded = false;
    let swarmWorld = null;
    let swarmNodes = [];
    let swarmRealNodes = [];
    let swarmFilter = "All";
    let swarmAgents = [];
    let swarmTrails = [];
    let swarmPlaying = false;
    let swarmAnimationHandle = null;
    let swarmLastFrameTime = null;
    let swarmFrameCounter = 0;
    let swarmBirthCount = 0;
    let swarmDeathCount = 0;
    let swarmSelectedTicker = null;
    let swarmSelectedAgentId = null;
    let swarmHoveredTicker = null;
    let swarmGenerationMax = 1;
    let swarmStaticLayer = null;
    let swarmVisibleNodes = [];
    let swarmNutrientNodes = [];
    let swarmNodeMap = new Map();
    let swarmGridNodeMap = new Map();
    let swarmTimelineIndex = 0;
    let swarmCompletedAgents = [];
    let swarmJumpCostMultiplier = 2.0;
    let swarmHistoryByTicker = new Map();
    let swarmHistoryMeta = null;
    let swarmTimelineMax = 1000;
    let swarmTopAgentSnapshots = [];
    let swarmLoadingPromise = null;
    let swarmDnaSaveInFlight = false;
    let swarmDnaLastSavedSignature = "";
    let swarmPlaybackAccumulator = 0;
    let swarmSenseRadius = 1;
    let swarmAgentsPerNode = 20;
    let swarmZoomLevel = 0.75;
    let swarmCameraVector = { x: 0, y: 0, z: 1 };
    let swarmCameraManual = false;
    let swarmCameraDrag = { active: false, moved: false, lastX: 0, lastY: 0 };
    let swarmSuppressNextClick = false;
    let swarmThreeReady = false;
    let swarmThreeScene = null;
    let swarmThreeCamera = null;
    let swarmThreeRenderer = null;
    let swarmThreeRaycaster = null;
    let swarmThreePointer = null;
    let swarmThreeSphere = null;
    let swarmThreeGridGroup = null;
    let swarmThreeAssetGroup = null;
    let swarmThreeAgentGroup = null;
    let swarmThreeAssetMeshes = new Map();
    let swarmThreeAssetTextures = new Map();
    let swarmThreeAgentMeshes = new Map();
    let swarmThreeDebugCapGeometryCache = new Map();
    let swarmRenderDiagnostics = {
      threeSupport: null,
      renderPath: "",
      lastGridSignature: "",
    };
    let swarmDebugSphereRadius = null;
    let swarmLoadProgressTimer = null;
    let swarmLoadProgressValue = 0;
    let swarmLoadProgressLabel = "Swarm";
    let swarmDebugAssetCount = 24;
    let swarmLabLoaded = false;
    let swarmLabPlaying = false;
    let swarmLabAnimationHandle = null;
    let swarmLabLastFrameTime = null;
    let swarmLabFrameCounter = 0;
    let swarmLabWorld = null;
    let swarmLabNodes = [];
    let swarmLabAgents = [];
    let swarmLabTrails = [];
    let swarmLabHoveredNodeId = null;
    let swarmLabSelectedNodeId = null;
    let swarmLabPopulation = 72;
    let swarmLabNodeCount = 24;
    let swarmLabMutation = 0.08;
    let swarmLabRepulsion = 0.55;
    let swarmLabSpeed = 1.0;
    let swarmLabZoom = 1.0;
    let swarmLabGenerationMax = 1;
    let swarmLabBirthCount = 0;
    let swarmLabDeathCount = 0;
    let marketDataAutoRefreshAttempted = false;
    let tickerSelectUniverse = [];
    let tickerUniverseLoadPromise = null;
    let tickerSelectLastValue = "";
    let tickerScanScope = "xetra";
    let tickerListMode = "custom";
    let customTickerLists = [];
    let customTickerListActiveName = "My List";
    let customTickerListName = "My List";
    let customTickerList = [];
    let customTickerListDraft = [];
    let customTickerListDraftSourceName = "My List";
    let listBuilderExchange = "all";
    let listBuilderSearch = "";
    const SWARM_TIMELINE_MAX = 1000;
    const SWARM_HISTORY_DAYS = 420;
    const SWARM_HISTORY_LIMIT = 900;
    const SWARM_DNA_SCHEMA_VERSION = "swarm_agent_dna_v2";
    const SWARM_DNA_CONFIG_PATH = "config/swarm_agent_dna.json";
    const SWARM_STARTING_ENERGY = 10000;
    const SWARM_TICKER_WEALTH_FLOOR = SWARM_STARTING_ENERGY * 0.18;
    const SWARM_ANNUAL_INFLATION_RATE = 0.025;
    const SWARM_MAX_AGENTS = 5000;
    const SWARM_MAX_TRAILS = 260;
    const SWARM_MAX_DRAWN_AGENTS = 1400;
    const SWARM_SPHERE_REPULSION_SAMPLE = 26;
    const SWARM_SPHERE_REPULSION_LIMIT = 0.018;
    const SWARM_SPHERE_VELOCITY_LIMIT = 0.015;
    const SWARM_SPHERE_INITIAL_RELAX_STEPS = 18;
    const LAST_TICKER_SELECT_KEY = "etf-discovery:last-ticker-select";
    const LAST_EXCHANGE_SELECT_KEY = "etf-discovery:last-exchange-select";
    const LAST_SCAN_SCOPE_KEY = "etf-discovery:last-scan-scope";
    const LAST_SWARM_DEBUG_ASSET_COUNT_KEY = "etf-discovery:last-swarm-debug-asset-count";
    const LAST_LIST_MODE_KEY = "etf-discovery:last-list-mode";
    const LAST_CUSTOM_LIST_KEY = "etf-discovery:last-custom-list";
    const LAST_CUSTOM_LIST_NAME_KEY = "etf-discovery:last-custom-list-name";
    const LAST_DASHBOARD_TAB_KEY = "etf-discovery:last-dashboard-tab";

    function getDashboardTabs() {
      return ["screener", "shortlist", "swarm", "swarm-lab", "backtest"]
        .map((name) => document.getElementById(`tab-${name}`))
        .filter(Boolean);
    }

    function normalizeDashboardTab(value) {
      const cleaned = String(value || "screener").trim().toLowerCase();
      return ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].includes(cleaned) ? cleaned : "screener";
    }

    function readStickyValue(key, fallback = "") {
      try {
        const raw = localStorage.getItem(key);
        return raw === null || raw === undefined ? fallback : String(raw);
      } catch (err) {
        return fallback;
      }
    }

    function writeStickyValue(key, value) {
      try {
        localStorage.setItem(key, String(value ?? ""));
      } catch (err) {
        // Ignore storage failures in restricted environments.
      }
    }

    function normalizeExchangeFilter(value) {
      const cleaned = String(value || "all").trim().toLowerCase();
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
      if (["list", "chosen", "chosen_list", "custom"].includes(cleaned)) {
        return "list";
      }
      if (["all_lists", "alllists", "all list", "all lists"].includes(cleaned)) {
        return "all_lists";
      }
      if (["debug", "demo", "dummy", "synthetic"].includes(cleaned)) {
        return "debug";
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
      if (/\.(DE|F)$/.test(upperTicker) || !upperTicker.includes(".")) {
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
      if (scope === "xetra" || scope === "sweden") {
        return tickerSelectUniverse.filter((item) => item.exchange === scope);
      }
      if (scope === "debug") {
        return tickerSelectUniverse;
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
      } else if (normalizedScope === "xetra") {
        placeholder.textContent = "Select Xetra ticker...";
      } else if (normalizedScope === "debug") {
        placeholder.textContent = "Debug mode uses synthetic swarm assets...";
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
      ticker.disabled = (normalizedScope === "sweden" && visible.length === 0) || (normalizedScope === "all_lists" && visible.length === 0);
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
        "#scan-source-toggle .scan-source-btn, #swarm-scan-source-toggle .scan-source-btn"
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
      updateSwarmDebugChrome();
    }

    function getSwarmDebugNodes() {
      return {
        panel: document.getElementById("swarm-debug-controls"),
        input: document.getElementById("swarm-debug-count"),
        label: document.getElementById("swarm-debug-count-label"),
      };
    }

    function normalizeSwarmDebugAssetCount(value) {
      const parsed = Number.parseInt(String(value || "").trim(), 10);
      if (!Number.isFinite(parsed)) {
        return 24;
      }
      return Math.max(1, Math.min(400, parsed));
    }

    function updateSwarmDebugChrome() {
      const nodes = getSwarmDebugNodes();
      const debugActive = normalizeScanScope(tickerScanScope) === "debug";
      if (nodes.panel) {
        nodes.panel.classList.toggle("hidden", !debugActive);
        nodes.panel.hidden = !debugActive;
      }
      if (nodes.input) {
        nodes.input.disabled = !debugActive;
        nodes.input.value = String(swarmDebugAssetCount);
      }
      if (nodes.label) {
        nodes.label.textContent = String(swarmDebugAssetCount);
      }
    }

    function getSwarmDebugAssetCount() {
      return normalizeSwarmDebugAssetCount(swarmDebugAssetCount);
    }

    async function setSwarmDebugAssetCount(value) {
      swarmDebugAssetCount = normalizeSwarmDebugAssetCount(value);
      writeStickyValue(LAST_SWARM_DEBUG_ASSET_COUNT_KEY, swarmDebugAssetCount);
      updateSwarmDebugChrome();
      if (normalizeScanScope(tickerScanScope) === "debug"
        && (swarmLoaded || !document.getElementById("tab-swarm").classList.contains("hidden"))) {
        if (swarmLoadingPromise) {
          await swarmLoadingPromise;
        }
        await loadSwarmWorld(true);
      }
    }

    async function applyScanScopeSelection(mode) {
      const normalized = normalizeScanScope(mode);
      tickerScanScope = normalized;
      writeStickyValue(LAST_SCAN_SCOPE_KEY, normalized);
      updateScanScopeChrome();
      loadMarketStatus(normalized).catch((err) => {
        console.warn("Could not refresh market status after scope change", err);
      });
      if ((normalized === "list" || normalized === "all_lists") && getScopeTickers(normalized).length === 0) {
        await openListEditorModal();
      }
      if (swarmLoaded || !document.getElementById("tab-swarm").classList.contains("hidden")) {
        loadSwarmWorld(true).catch((err) => {
          console.warn("Could not refresh swarm world after scope change", err);
        });
      }
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
          .join(" · ") || item.ticker;
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
        button.className = button.dataset.baseClass;
        button.style.backgroundColor = active ? "#4f46e5" : "";
        button.style.borderColor = active ? "#818cf8" : "";
        button.style.boxShadow = active ? "0 0 0 2px rgba(165, 180, 252, 0.38)" : "";
        button.style.transform = active ? "translateY(-1px)" : "";
        button.setAttribute("aria-pressed", active ? "true" : "false");
        button.dataset.active = active ? "true" : "false";
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

      if (body) {
        body.innerHTML = "";
      }
      if (chartDiv && window.Plotly) {
        Plotly.purge(chartDiv);
      }
      emptyState.textContent = message;
      emptyState.classList.remove("hidden");
      content.classList.add("hidden");
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
          ? reasons.map((reason) => `<div class="text-[11px] text-slate-500">• ${reason}</div>`).join("")
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
              <div class="mt-1 font-semibold text-slate-700">${row.asset_class || "ETF"} · ${row.region || "Unknown"}</div>
              <div class="text-slate-500">${row.issuer || "Unknown issuer"}</div>
            </div>
            <div class="rounded-lg bg-slate-50 px-3 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Timing</div>
              <div class="mt-1 font-semibold text-slate-700">${formatShortlistEntryAge(row.recent_entry_days)}</div>
              <div class="text-slate-500">Close ${Number(row.close || 0).toFixed(2)} · ${(Number(row.volume || 0) / 1000).toFixed(0)}K vol</div>
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

    function setSwarmEmptyState(message) {
      const emptyState = document.getElementById("swarm-empty");
      const content = document.getElementById("swarm-content");
      if (emptyState) {
        emptyState.textContent = message;
        emptyState.classList.remove("hidden");
      }
      if (content) {
        content.classList.add("hidden");
      }
    }

    function getSwarmLoadProgressNodes() {
      return {
        panel: document.getElementById("swarm-load-progress"),
        label: document.getElementById("swarm-load-progress-label"),
        text: document.getElementById("swarm-load-progress-text"),
        bar: document.getElementById("swarm-load-progress-bar"),
      };
    }

    function setSwarmLoadProgress(state = {}) {
      const nodes = getSwarmLoadProgressNodes();
      const show = state.show;
      if (show === true && nodes.panel) {
        nodes.panel.classList.remove("hidden");
      } else if (show === false && nodes.panel) {
        nodes.panel.classList.add("hidden");
      }

      if (state.label && nodes.label) {
        nodes.label.textContent = state.label;
      }
      if (state.text && nodes.text) {
        nodes.text.textContent = state.text;
      }
      if (state.pct !== undefined && nodes.bar) {
        const pct = Math.max(0, Math.min(100, Number(state.pct) || 0));
        nodes.bar.style.width = `${pct}%`;
      }
      if (state.working !== undefined && nodes.bar) {
        nodes.bar.classList.toggle("animate-pulse", Boolean(state.working));
      }
      if (state.working === false && nodes.bar) {
        nodes.bar.classList.remove("animate-pulse");
      }
    }

    function clearSwarmLoadProgressTimer() {
      if (swarmLoadProgressTimer) {
        clearInterval(swarmLoadProgressTimer);
        swarmLoadProgressTimer = null;
      }
    }

    function stopSwarmLoadProgress({ keepVisible = false } = {}) {
      clearSwarmLoadProgressTimer();
      swarmLoadProgressValue = 0;
      if (keepVisible) {
        setSwarmLoadProgress({
          show: true,
          label: swarmLoadProgressLabel,
          text: "100%",
          pct: 100,
          working: false,
        });
      } else {
        setSwarmLoadProgress({ show: false, pct: 0, working: false });
      }
    }

    function startSwarmLoadProgress(label = "Swarm", text = "Refreshing world...") {
      clearSwarmLoadProgressTimer();
      swarmLoadProgressLabel = label;
      swarmLoadProgressValue = 8;
      setSwarmLoadProgress({
        show: true,
        label,
        text,
        pct: swarmLoadProgressValue,
        working: true,
      });
      swarmLoadProgressTimer = setInterval(() => {
        if (swarmLoadProgressValue < 90) {
          swarmLoadProgressValue = Math.min(90, swarmLoadProgressValue + Math.max(0.9, (90 - swarmLoadProgressValue) * 0.12));
          setSwarmLoadProgress({
            show: true,
            label,
            text: `${Math.round(swarmLoadProgressValue)}%`,
            pct: swarmLoadProgressValue,
            working: true,
          });
          return;
        }
        const pulse = 88 + Math.round(4 * (0.5 + 0.5 * Math.sin(Date.now() / 320)));
        setSwarmLoadProgress({
          show: true,
          label,
          text: "WORKING",
          pct: pulse,
          working: true,
        });
      }, 220);
    }

    function updateSwarmFilterButtons() {
      ["All", "Buy", "Watch", "Skip"].forEach((label) => {
        const button = document.getElementById(`swarm-filter-${label.toLowerCase()}`);
        if (!button) {
          return;
        }
        const isActive = swarmFilter === label;
        button.className = `rounded-full border px-3 py-1.5 text-xs font-bold transition-all ${
          isActive
            ? "border-violet-300 bg-violet-600 text-white shadow-sm"
            : "border-slate-300 bg-white text-slate-700"
        }`;
      });
    }

    function getSwarmGridMeta() {
      const world = (swarmWorld && swarmWorld.world) || {};
      const columns = Math.max(1, Math.round(Number(world.columns || 1)));
      const rows = Math.max(1, Math.round(Number(world.rows || 1)));
      const width = Number(world.width || 1600);
      const height = Number(world.height || 920);
      return {
        columns,
        rows,
        width,
        height,
        cellWidth: Number(world.cell_width || (width / columns)),
        cellHeight: Number(world.cell_height || (height / rows)),
      };
    }

    function getSwarmGridKey(row, col) {
      return `${Math.round(Number(row || 0))}:${Math.round(Number(col || 0))}`;
    }

    function normalizeSwarmVector(vector) {
      const x = Number(vector && vector.x || 0);
      const y = Number(vector && vector.y || 0);
      const z = Number(vector && vector.z || 0);
      const length = Math.max(0.000001, Math.hypot(x, y, z));
      return { x: x / length, y: y / length, z: z / length };
    }

    function stableSwarmSphereVector(index, total, seed = "") {
      const count = Math.max(1, Number(total || 1));
      const idx = Math.max(0, Number(index || 0));
      const phase = seed ? stableSwarmFraction(seed, "sphere-index") : 0;
      const goldenAngle = Math.PI * (3 - Math.sqrt(5));
      const y = 1 - ((idx + 0.5) / count) * 2;
      const radius = Math.sqrt(Math.max(0, 1 - (y * y)));
      const theta = (idx + phase) * goldenAngle;
      return normalizeSwarmVector({
        x: Math.cos(theta) * radius,
        y,
        z: Math.sin(theta) * radius,
      });
    }

    function sphereVectorToWorld(vector) {
      const normalized = normalizeSwarmVector(vector);
      const world = getSwarmWorldSize();
      const lon = Math.atan2(normalized.z, normalized.x);
      const lat = Math.asin(clampSwarm(normalized.y, -1, 1));
      return {
        x: ((lon + Math.PI) / (Math.PI * 2)) * world.width,
        y: ((Math.PI / 2 - lat) / Math.PI) * world.height,
      };
    }

    function worldToSphereVector(x, y) {
      const world = getSwarmWorldSize();
      const lon = (Number(x || 0) / Math.max(1, world.width)) * Math.PI * 2 - Math.PI;
      const lat = Math.PI / 2 - (Number(y || 0) / Math.max(1, world.height)) * Math.PI;
      return normalizeSwarmVector({
        x: Math.cos(lat) * Math.cos(lon),
        y: Math.sin(lat),
        z: Math.cos(lat) * Math.sin(lon),
      });
    }

    function getSwarmSphereTangentBasis(vector) {
      const normal = normalizeSwarmVector(vector);
      const anchor = Math.abs(normal.y) > 0.82 ? { x: 1, y: 0, z: 0 } : { x: 0, y: 1, z: 0 };
      let tangentX = normalizeSwarmVector({
        x: anchor.y * normal.z - anchor.z * normal.y,
        y: anchor.z * normal.x - anchor.x * normal.z,
        z: anchor.x * normal.y - anchor.y * normal.x,
      });
      if (Math.hypot(tangentX.x, tangentX.y, tangentX.z) < 0.000001) {
        tangentX = normalizeSwarmVector({
          x: 0,
          y: normal.z,
          z: -normal.y,
        });
      }
      const tangentY = normalizeSwarmVector({
        x: normal.y * tangentX.z - normal.z * tangentX.y,
        y: normal.z * tangentX.x - normal.x * tangentX.z,
        z: normal.x * tangentX.y - normal.y * tangentX.x,
      });
      return { normal, tangentX, tangentY };
    }

    function projectSwarmVectorToTangentPlane(vector, normal) {
      const basisNormal = normalizeSwarmVector(normal);
      const dot = (Number(vector.x || 0) * basisNormal.x)
        + (Number(vector.y || 0) * basisNormal.y)
        + (Number(vector.z || 0) * basisNormal.z);
      return normalizeSwarmVector({
        x: Number(vector.x || 0) - (basisNormal.x * dot),
        y: Number(vector.y || 0) - (basisNormal.y * dot),
        z: Number(vector.z || 0) - (basisNormal.z * dot),
      });
    }

    function resolveSwarmDebugCapCollisions(nodes, sphereRadius, iterations = 3) {
      const realNodes = Array.isArray(nodes) ? nodes : [];
      if (realNodes.length < 2) {
        return;
      }
      const safeSphereRadius = Math.max(1, Number(sphereRadius || 1));
      for (let pass = 0; pass < iterations; pass += 1) {
        let hadOverlap = false;
        for (let idx = 0; idx < realNodes.length; idx += 1) {
          const node = realNodes[idx];
          node.sphereVector = normalizeSwarmVector(node.sphereVector || worldToSphereVector(node.x, node.y));
          const nodeRadius = Math.max(0.9, Number(node.capRadius || node.radius || node.baseRadius || 1));
          for (let otherIdx = idx + 1; otherIdx < realNodes.length; otherIdx += 1) {
            const other = realNodes[otherIdx];
            other.sphereVector = normalizeSwarmVector(other.sphereVector || worldToSphereVector(other.x, other.y));
            const otherRadius = Math.max(0.9, Number(other.capRadius || other.radius || other.baseRadius || 1));
            const dot = clampSwarm(
              (node.sphereVector.x * other.sphereVector.x) + (node.sphereVector.y * other.sphereVector.y) + (node.sphereVector.z * other.sphereVector.z),
              -0.999999,
              0.999999,
            );
            const angle = Math.acos(dot);
            const targetAngle = Math.max(0.02, (nodeRadius + otherRadius) / safeSphereRadius);
            const overlap = targetAngle - angle;
            if (overlap <= 0.0001) {
              continue;
            }
            hadOverlap = true;
            const nodeToOther = projectSwarmVectorToTangentPlane({
              x: other.sphereVector.x - (node.sphereVector.x * dot),
              y: other.sphereVector.y - (node.sphereVector.y * dot),
              z: other.sphereVector.z - (node.sphereVector.z * dot),
            }, node.sphereVector);
            const otherToNode = projectSwarmVectorToTangentPlane({
              x: node.sphereVector.x - (other.sphereVector.x * dot),
              y: node.sphereVector.y - (other.sphereVector.y * dot),
              z: node.sphereVector.z - (other.sphereVector.z * dot),
            }, other.sphereVector);
            const separation = overlap * 0.52;
            node.sphereVector = normalizeSwarmVector({
              x: node.sphereVector.x - (nodeToOther.x * separation),
              y: node.sphereVector.y - (nodeToOther.y * separation),
              z: node.sphereVector.z - (nodeToOther.z * separation),
            });
            other.sphereVector = normalizeSwarmVector({
              x: other.sphereVector.x - (otherToNode.x * separation),
              y: other.sphereVector.y - (otherToNode.y * separation),
              z: other.sphereVector.z - (otherToNode.z * separation),
            });
          }
        }
        if (!hadOverlap) {
          break;
        }
      }
    }

    function getSwarmDebugCapRadius(node) {
      const baseRadius = Math.max(0.9, Number(node?.baseRadius ?? node?.radius ?? 1));
      return clampSwarm(8.0 + (baseRadius * 6.0), 8.0, 34.0);
    }

    function getSwarmDebugSphereRadius(nodes = swarmVisibleNodes) {
      const safeNodes = Array.isArray(nodes) ? nodes : [];
      if (!safeNodes.length) {
        return Number((swarmWorld && swarmWorld.world && (swarmWorld.world.radius || swarmWorld.world.diameter / 2)) || 160);
      }
      const capRadii = safeNodes.map((node) => getSwarmDebugCapRadius(node));
      const totalCapArea = capRadii.reduce((sum, radius) => sum + (Math.PI * (radius ** 2)), 0);
      const averageCapRadius = capRadii.reduce((sum, radius) => sum + radius, 0) / Math.max(1, capRadii.length);
      const packingFraction = 0.34;
      const fittedRadius = Math.sqrt(totalCapArea / (4 * Math.PI * Math.max(0.05, packingFraction)));
      return Math.max(averageCapRadius * 2.9, fittedRadius, 12);
    }

    function getSwarmDebugAdaptiveSphereRadius(nodes, fallbackRadius = swarmDebugSphereRadius) {
      const safeNodes = Array.isArray(nodes) ? nodes : [];
      if (!safeNodes.length) {
        return Math.max(1, Number(fallbackRadius || getSwarmDebugSphereRadius()));
      }
      const baselineRadius = Math.max(1, getSwarmDebugSphereRadius(safeNodes));
      const currentRadius = Math.max(1, Number(fallbackRadius || baselineRadius));
      let requiredRadius = Math.max(currentRadius, baselineRadius);
      let overlapPressure = 0;
      for (let idx = 0; idx < safeNodes.length; idx += 1) {
        const node = safeNodes[idx];
        const nodeVector = normalizeSwarmVector(node.sphereVector || worldToSphereVector(node.x, node.y));
        const nodeRadius = Math.max(0.9, Number(node.capRadius || getSwarmDebugCapRadius(node)));
        for (let otherIdx = idx + 1; otherIdx < safeNodes.length; otherIdx += 1) {
          const other = safeNodes[otherIdx];
          const otherVector = normalizeSwarmVector(other.sphereVector || worldToSphereVector(other.x, other.y));
          const otherRadius = Math.max(0.9, Number(other.capRadius || getSwarmDebugCapRadius(other)));
          const dot = clampSwarm(
            (nodeVector.x * otherVector.x) + (nodeVector.y * otherVector.y) + (nodeVector.z * otherVector.z),
            -0.999999,
            0.999999,
          );
          const angle = Math.max(0.01, Math.acos(dot));
          const targetAngle = Math.max(0.02, (nodeRadius + otherRadius) / currentRadius);
          const overlap = targetAngle - angle;
          if (overlap <= 0.0001) {
            continue;
          }
          overlapPressure = Math.max(overlapPressure, overlap / Math.max(0.02, targetAngle));
          const localRadius = (nodeRadius + otherRadius) / Math.max(angle, targetAngle * 0.72);
          requiredRadius = Math.max(requiredRadius, localRadius);
        }
      }
      const maxGrowthStep = currentRadius * 1.08;
      const pressureRadius = currentRadius * (1 + clampSwarm(overlapPressure * 0.22, 0, 0.08));
      const crowdingCap = baselineRadius * clampSwarm(1.35 + (safeNodes.length / 60), 1.45, 2.4);
      return clampSwarm(Math.max(baselineRadius, pressureRadius, requiredRadius), baselineRadius, Math.max(maxGrowthStep, crowdingCap));
    }

    function getSwarmDebugTouchRadius(node, nearestAngle, sphereRadius) {
      const currentRadius = Math.max(0.9, Number(node?.capRadius ?? node?.radius ?? node?.baseRadius ?? 1));
      const fittedRadius = Number.isFinite(nearestAngle) && nearestAngle > 0
        ? nearestAngle * Math.max(1, sphereRadius) * 0.68
        : currentRadius * 1.16;
      return clampSwarm(Math.max(currentRadius, fittedRadius), currentRadius, Math.max(currentRadius, sphereRadius * 0.49));
    }

    function getSphereBasis(camera = swarmCameraVector) {
      const forward = normalizeSwarmVector(camera);
      const pole = Math.abs(forward.y) > 0.92 ? { x: 0, y: 0, z: 1 } : { x: 0, y: 1, z: 0 };
      const right = normalizeSwarmVector({
        x: pole.y * forward.z - pole.z * forward.y,
        y: pole.z * forward.x - pole.x * forward.z,
        z: pole.x * forward.y - pole.y * forward.x,
      });
      const up = normalizeSwarmVector({
        x: forward.y * right.z - forward.z * right.y,
        y: forward.z * right.x - forward.x * right.z,
        z: forward.x * right.y - forward.y * right.x,
      });
      return { forward, right, up };
    }

    function rotateSwarmVectorAroundAxis(vector, axis, angle) {
      const normalizedVector = normalizeSwarmVector(vector);
      const normalizedAxis = normalizeSwarmVector(axis);
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      const dot = (normalizedVector.x * normalizedAxis.x)
        + (normalizedVector.y * normalizedAxis.y)
        + (normalizedVector.z * normalizedAxis.z);
      return normalizeSwarmVector({
        x: (normalizedVector.x * cos)
          + ((normalizedAxis.y * normalizedVector.z) - (normalizedAxis.z * normalizedVector.y)) * sin
          + (normalizedAxis.x * dot * (1 - cos)),
        y: (normalizedVector.y * cos)
          + ((normalizedAxis.z * normalizedVector.x) - (normalizedAxis.x * normalizedVector.z)) * sin
          + (normalizedAxis.y * dot * (1 - cos)),
        z: (normalizedVector.z * cos)
          + ((normalizedAxis.x * normalizedVector.y) - (normalizedAxis.y * normalizedVector.x)) * sin
          + (normalizedAxis.z * dot * (1 - cos)),
      });
    }

    function orbitSwarmCamera(deltaX, deltaY) {
      const safeDx = Number(deltaX || 0);
      const safeDy = Number(deltaY || 0);
      if (Math.abs(safeDx) < 0.001 && Math.abs(safeDy) < 0.001) {
        return;
      }
      const basis = getSphereBasis(swarmCameraVector);
      const yaw = -safeDx * 0.0055;
      const pitch = -safeDy * 0.0055;
      let nextVector = rotateSwarmVectorAroundAxis(swarmCameraVector, { x: 0, y: 1, z: 0 }, yaw);
      nextVector = rotateSwarmVectorAroundAxis(nextVector, basis.right, pitch);
      swarmCameraVector = normalizeSwarmVector({
        x: nextVector.x,
        y: clampSwarm(nextVector.y, -0.82, 0.82),
        z: nextVector.z,
      });
      swarmCameraManual = true;
    }

    function drawSwarmDebugSphereGraticule(ctx, layout) {
      if (!ctx || !layout || !isSwarmDebugMode()) {
        return;
      }
      const latitudes = [-75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75];
      const longitudes = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150];
      const latSteps = 72;
      const lonSteps = 72;
      const projectPoint = (latDeg, lonDeg) => {
        const lat = (latDeg * Math.PI) / 180;
        const lon = (lonDeg * Math.PI) / 180;
        const worldPoint = sphereVectorToWorld({
          x: Math.cos(lat) * Math.cos(lon),
          y: Math.sin(lat),
          z: Math.cos(lat) * Math.sin(lon),
        });
        return worldToCanvas(layout, worldPoint.x, worldPoint.y);
      };
      const strokeCurve = (points, strokeStyle, lineWidth, alpha = 1) => {
        let drawing = false;
        ctx.beginPath();
        ctx.lineWidth = lineWidth;
        ctx.strokeStyle = strokeStyle;
        ctx.globalAlpha = alpha;
        points.forEach((point) => {
          if (!point || point.backSide) {
            if (drawing) {
              ctx.stroke();
              ctx.beginPath();
              drawing = false;
            }
            return;
          }
          if (!drawing) {
            ctx.moveTo(point.x, point.y);
            drawing = true;
          } else {
            ctx.lineTo(point.x, point.y);
          }
        });
        if (drawing) {
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      };

      ctx.save();
      ctx.beginPath();
      ctx.arc(layout.width / 2, layout.height / 2, layout.sphereRadius + 0.5, 0, Math.PI * 2);
      ctx.clip();
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      latitudes.forEach((latDeg) => {
        const points = [];
        for (let step = 0; step <= latSteps; step += 1) {
          const lonDeg = -180 + ((step / latSteps) * 360);
          points.push(projectPoint(latDeg, lonDeg));
        }
        const isEquator = Math.abs(latDeg) < 0.001;
        strokeCurve(
          points,
          isEquator ? "rgba(250, 204, 21, 0.98)" : "rgba(250, 204, 21, 0.72)",
          isEquator ? 2.2 : 1.35,
          1,
        );
      });

      longitudes.forEach((lonDeg) => {
        const points = [];
        for (let step = 0; step <= lonSteps; step += 1) {
          const latDeg = 90 - ((step / lonSteps) * 180);
          points.push(projectPoint(latDeg, lonDeg));
        }
        const isPrime = Math.abs(lonDeg) < 0.001;
        strokeCurve(
          points,
          isPrime ? "rgba(254, 240, 138, 0.98)" : "rgba(250, 204, 21, 0.68)",
          isPrime ? 2.0 : 1.25,
          1,
        );
      });

      ctx.restore();
    }

    function disposeSwarmThreeGridGroup() {
      if (!swarmThreeGridGroup) {
        return;
      }
      while (swarmThreeGridGroup.children.length > 0) {
        const child = swarmThreeGridGroup.children[0];
        swarmThreeGridGroup.remove(child);
        if (child?.geometry?.dispose) {
          child.geometry.dispose();
        }
        if (child?.material?.dispose) {
          child.material.dispose();
        }
      }
    }

    function syncSwarmThreeGrid() {
      if (!swarmThreeScene || !swarmThreeGridGroup) {
        return;
      }
      disposeSwarmThreeGridGroup();
      swarmThreeGridGroup.visible = isSwarmDebugMode();
      if (!isSwarmDebugMode()) {
        return;
      }

      const THREE = window.THREE;
      const sphereRadius = getSwarmSphereRadius();
      const gridRadius = sphereRadius * 1.0045;
      const latitudeValues = [-75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75];
      const longitudeValues = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150];
      const latSegments = 48;
      const lonSegments = 48;
      const gridSignature = `${sphereRadius}:${latitudeValues.length}:${longitudeValues.length}:${isSwarmDebugMode() ? "debug" : "standard"}`;
      if (swarmRenderDiagnostics.lastGridSignature !== gridSignature) {
        swarmRenderDiagnostics.lastGridSignature = gridSignature;
        console.info("[SWARM] Rebuilding sphere graticule", {
          sphereRadius,
          latitudeLines: latitudeValues.length,
          longitudeLines: longitudeValues.length,
          debugMode: isSwarmDebugMode(),
        });
      }

      const buildLine = (points, material) => {
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, material);
        line.renderOrder = 12;
        line.frustumCulled = false;
        return line;
      };

      const longitudeMaterial = new THREE.LineBasicMaterial({
        color: 0xfacc15,
        transparent: true,
        opacity: 0.9,
        depthTest: false,
        depthWrite: false,
      });
      const equatorMaterial = new THREE.LineBasicMaterial({
        color: 0xfef08a,
        transparent: true,
        opacity: 1,
        depthTest: false,
        depthWrite: false,
      });
      const latitudeMaterial = new THREE.LineBasicMaterial({
        color: 0xfacc15,
        transparent: true,
        opacity: 0.82,
        depthTest: false,
        depthWrite: false,
      });
      const primeMaterial = new THREE.LineBasicMaterial({
        color: 0xfef08a,
        transparent: true,
        opacity: 1,
        depthTest: false,
        depthWrite: false,
      });

      latitudeValues.forEach((latDeg) => {
        const lat = (latDeg * Math.PI) / 180;
        const points = [];
        for (let step = 0; step <= latSegments; step += 1) {
          const lon = -Math.PI + ((step / latSegments) * Math.PI * 2);
          points.push(new THREE.Vector3(
            Math.cos(lat) * Math.cos(lon) * gridRadius,
            Math.sin(lat) * gridRadius,
            Math.cos(lat) * Math.sin(lon) * gridRadius,
          ));
        }
        const material = Math.abs(latDeg) < 0.001 ? equatorMaterial.clone() : latitudeMaterial.clone();
        swarmThreeGridGroup.add(buildLine(points, material));
      });

      longitudeValues.forEach((lonDeg) => {
        const lon = (lonDeg * Math.PI) / 180;
        const points = [];
        for (let step = 0; step <= lonSegments; step += 1) {
          const lat = (Math.PI / 2) - ((step / lonSegments) * Math.PI);
          points.push(new THREE.Vector3(
            Math.cos(lat) * Math.cos(lon) * gridRadius,
            Math.sin(lat) * gridRadius,
            Math.cos(lat) * Math.sin(lon) * gridRadius,
          ));
        }
        const material = Math.abs(lonDeg) < 0.001 ? primeMaterial.clone() : longitudeMaterial.clone();
        swarmThreeGridGroup.add(buildLine(points, material));
      });
    }

    function updateSwarmCameraVector() {
      if (swarmCameraManual || swarmCameraDrag.active) {
        return;
      }
      let weighted = { x: 0, y: 0, z: 120 };
      swarmAgents.forEach((agent) => {
        const vector = agent.sphereVector || worldToSphereVector(agent.x, agent.y);
        const weight = Math.sqrt(Math.max(1, Number(agent.energy || SWARM_STARTING_ENERGY)) / SWARM_STARTING_ENERGY);
        weighted.x += vector.x * weight;
        weighted.y += vector.y * weight;
        weighted.z += vector.z * weight;
      });
      if (swarmAgents.length < 24 && Math.hypot(weighted.x, weighted.y, weighted.z) < 122) {
      swarmVisibleNodes.slice(0, 160).forEach((node) => {
          const vector = node.sphereVector || worldToSphereVector(node.x, node.y);
          const weight = Math.sqrt(Math.max(1, Number(node.simEnergy || SWARM_STARTING_ENERGY)) / SWARM_STARTING_ENERGY) * 0.12;
          weighted.x += vector.x * weight;
          weighted.y += vector.y * weight;
          weighted.z += vector.z * weight;
        });
      }
      if (Math.hypot(weighted.x, weighted.y, weighted.z) >= 0.01) {
        const nextVector = normalizeSwarmVector(weighted);
        swarmCameraVector = normalizeSwarmVector({
          x: nextVector.x,
          y: clampSwarm(nextVector.y, -0.82, 0.82),
          z: nextVector.z,
        });
      }
    }

    function assignSwarmSpherePosition(node) {
      const meta = getSwarmGridMeta();
      const total = Math.max(1, meta.rows * meta.columns);
      const index = Math.round(Number(node.row || 0)) * meta.columns + Math.round(Number(node.col || 0));
      node.sphereVector = node.sphereVector || stableSwarmSphereVector(index, total, node.ticker || node.name || `${node.row}:${node.col}`);
      const worldPoint = sphereVectorToWorld(node.sphereVector);
      node.x = worldPoint.x;
      node.y = worldPoint.y;
      node.seedX = worldPoint.x;
      node.seedY = worldPoint.y;
      return node;
    }

    function normalizeSwarmSphereNodes(nodes) {
      return (Array.isArray(nodes) ? nodes : []).map((node) => {
        const sphereRadius = Number(node.sphere_radius || node.sphereRadius || getSwarmSphereRadius() || 160);
        const rawSphere = {
          x: Number(node.sphere_x ?? node.x ?? 0),
          y: Number(node.sphere_y ?? node.y ?? 0),
          z: Number(node.sphere_z ?? node.z ?? 0),
        };
        const vector = normalizeSwarmVector(rawSphere);
        const sphereVector = (Math.hypot(rawSphere.x, rawSphere.y, rawSphere.z) > 0.000001)
          ? vector
          : stableSwarmSphereVector(
            Math.round(Number(node.row ?? node.grid_row ?? 0)) * Math.max(1, Number(node.col ?? node.grid_col ?? 1)),
            Math.max(1, nodes.length),
            node.ticker || node.name || "",
          );
        const scaled = {
          x: sphereVector.x * sphereRadius,
          y: sphereVector.y * sphereRadius,
          z: sphereVector.z * sphereRadius,
        };
        const worldPoint = sphereVectorToWorld(sphereVector);
        return {
          ...node,
          row: Math.round(Number(node.row ?? node.grid_row ?? 0)),
          col: Math.round(Number(node.col ?? node.grid_col ?? 0)),
          sphereRadius,
          sphereVector,
          seedSphereVector: { ...sphereVector },
          x: Number.isFinite(rawSphere.x) ? rawSphere.x : scaled.x,
          y: Number.isFinite(rawSphere.y) ? rawSphere.y : scaled.y,
          z: Number.isFinite(rawSphere.z) ? rawSphere.z : scaled.z,
          seedX: Number.isFinite(rawSphere.x) ? rawSphere.x : worldPoint.x,
          seedY: Number.isFinite(rawSphere.y) ? rawSphere.y : worldPoint.y,
          is_dummy: Boolean(node.is_dummy),
        };
      });
    }

    function getSwarmNodeId(node) {
      return node ? String(node.ticker || getSwarmGridKey(node.row, node.col)) : "";
    }

    function getSwarmNodeAtGrid(row, col) {
      return swarmGridNodeMap.get(getSwarmGridKey(row, col)) || null;
    }

    function normalizeSwarmGridNodes(nodes) {
      return normalizeSwarmSphereNodes(nodes);
    }

    function normalizeSwarmDebugSphereNodes(nodes) {
      const source = normalizeSwarmSphereNodes(Array.isArray(nodes) ? nodes : []);
      const safeCount = Math.max(1, source.length);
      const baseVectors = source.map((node, idx) => {
        const rawVector = normalizeSwarmVector(node.sphereVector || {
          x: Number(node.sphere_x ?? node.x ?? 0),
          y: Number(node.sphere_y ?? node.y ?? 0),
          z: Number(node.sphere_z ?? node.z ?? 0),
        });
        const fallbackVector = stableSwarmSphereVector(idx, safeCount, node.ticker || node.name || `${idx}`);
        const seededVector = Math.hypot(rawVector.x, rawVector.y, rawVector.z) > 0.000001 ? rawVector : fallbackVector;
        const { tangentX, tangentY } = getSwarmSphereTangentBasis(seededVector);
        const wobblePhase = stableSwarmFraction(String(node.ticker || idx), "debug-sphere-wobble") * Math.PI * 2;
        const wobbleAmount = (stableSwarmFraction(String(node.ticker || idx), "debug-sphere-shift") - 0.5) * 0.11;
        const jitter = {
          x: ((tangentX.x * Math.cos(wobblePhase)) + (tangentY.x * Math.sin(wobblePhase))) * wobbleAmount,
          y: ((tangentX.y * Math.cos(wobblePhase)) + (tangentY.y * Math.sin(wobblePhase))) * wobbleAmount,
          z: ((tangentX.z * Math.cos(wobblePhase)) + (tangentY.z * Math.sin(wobblePhase))) * wobbleAmount,
        };
        const sphereVector = normalizeSwarmVector({
          x: seededVector.x + jitter.x,
          y: seededVector.y + jitter.y,
          z: seededVector.z + jitter.z,
        });
        return {
          ...node,
          sphereVector,
        };
      });

      swarmDebugSphereRadius = getSwarmDebugSphereRadius(baseVectors);

      return baseVectors.map((node, idx) => {
        const capRadius = getSwarmDebugCapRadius(node);
        const worldPoint = sphereVectorToWorld(node.sphereVector);
        return {
          ...node,
          capRadius,
          mass: Math.max(0.75, Math.pow(capRadius / 8, 1.35)),
          sphereRadius: swarmDebugSphereRadius,
          capAngularRadius: capRadius / Math.max(1, swarmDebugSphereRadius),
          sphereVector: node.sphereVector,
          seedSphereVector: { ...node.sphereVector },
          sphereVelocity: { x: 0, y: 0, z: 0 },
          x: worldPoint.x,
          y: worldPoint.y,
          z: node.sphereVector.z * swarmDebugSphereRadius,
          seedX: worldPoint.x,
          seedY: worldPoint.y,
        };
      });
    }

    function normalizeSwarmDebugPlaneNodes(nodes) {
      return normalizeSwarmDebugSphereNodes(nodes);
    }

    function refreshSwarmDerivedState() {
      const realVisible = swarmFilter === "All"
        ? [...swarmRealNodes]
        : swarmRealNodes.filter((node) => node.label === swarmFilter);
      swarmVisibleNodes = [...realVisible];
      swarmVisibleNodes.forEach((node) => {
        if (node.simEnergy === undefined) {
          node.simEnergy = Number(node.value || node.close || SWARM_STARTING_ENERGY);
        }
        if (node.baseValue === undefined) {
          node.baseValue = Number(node.value || node.close || SWARM_STARTING_ENERGY);
        }
        if (node.baseRadius === undefined) {
          node.baseRadius = Number(node.radius || 1);
        }
        if (node.vx === undefined) {
          node.vx = (stableSwarmFraction(node.ticker, "vx-client") - 0.5) * 0.16;
        }
        if (node.vy === undefined) {
          node.vy = (stableSwarmFraction(node.ticker, "vy-client") - 0.5) * 0.16;
        }
        if (node.charge === undefined) {
          node.charge = 1;
        }
        if (!node.sphereVector) {
          node.sphereVector = normalizeSwarmVector({
            x: Number(node.sphere_x ?? node.x ?? 0),
            y: Number(node.sphere_y ?? node.y ?? 0),
            z: Number(node.sphere_z ?? node.z ?? 0),
          });
        }
        if (!node.seedSphereVector) {
          node.seedSphereVector = { ...node.sphereVector };
        }
        if (node.seedX === undefined) {
          node.seedX = Number(node.x || 0);
        }
        if (node.seedY === undefined) {
          node.seedY = Number(node.y || 0);
        }
      });
      swarmVisibleNodes.sort((a, b) => {
        const labelDiff = ({ Buy: 0, Watch: 1, Skip: 2 }[a.label] || 3) - ({ Buy: 0, Watch: 1, Skip: 2 }[b.label] || 3);
        if (labelDiff !== 0) {
          return labelDiff;
        }
        return Number(b.energy || 0) - Number(a.energy || 0);
      });
      swarmNutrientNodes = swarmVisibleNodes.slice(0, Math.min(swarmVisibleNodes.length, 180));
      swarmNodeMap = new Map(swarmVisibleNodes.map((node) => [node.ticker, node]));
      swarmGridNodeMap = new Map(swarmVisibleNodes.map((node) => [getSwarmGridKey(node.row, node.col), node]));
    }

    function stableSwarmFraction(text, salt = "") {
      const source = `${salt}:${text || ""}`;
      let hash = 2166136261;
      for (let idx = 0; idx < source.length; idx += 1) {
        hash ^= source.charCodeAt(idx);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0) / 4294967295;
    }

    function clampSwarm(value, floor, ceiling) {
      return Math.max(floor, Math.min(ceiling, Number(value)));
    }

    function getSwarmWorldSize() {
      return {
        width: Number((swarmWorld && swarmWorld.world && swarmWorld.world.width) || 1600),
        height: Number((swarmWorld && swarmWorld.world && swarmWorld.world.height) || 920),
      };
    }

    function getSwarmSphereRadius() {
      if (isSwarmDebugMode() && Number.isFinite(swarmDebugSphereRadius)) {
        return Number(swarmDebugSphereRadius);
      }
      return Number((swarmWorld && swarmWorld.world && (swarmWorld.world.radius || swarmWorld.world.diameter / 2)) || 160);
    }

    function isSwarmDebugMode() {
      return normalizeScanScope(tickerScanScope) === "debug";
    }

    function isSwarmPlaneMode() {
      return false;
    }

    function getSwarmWorldFitDistance() {
      const sphereRadius = Math.max(1, getSwarmSphereRadius());
      const camera = swarmThreeCamera;
      const cameraFov = camera && Number.isFinite(camera.fov) ? camera.fov : 50;
      const fovRadians = clampSwarm((cameraFov * Math.PI) / 180, 0.35, Math.PI - 0.35);
      const fitDistance = sphereRadius / Math.max(0.001, Math.sin(fovRadians / 2));
      const framedDistance = fitDistance * 1.08 + Math.max(6, sphereRadius * 0.08);
      return Math.max(sphereRadius * 1.9, framedDistance);
    }

    function updateSwarmWorldVisibilityIndicator(cameraDistance = null) {
      const badge = document.getElementById("swarm-world-visibility");
      if (!badge) {
        return;
      }
      const fitDistance = getSwarmWorldFitDistance();
      const visible = Number.isFinite(cameraDistance)
        ? cameraDistance >= fitDistance * 0.98
        : swarmZoomLevel <= 1;
      badge.textContent = visible ? "Whole world visible" : "Zoomed in";
      badge.classList.toggle("bg-emerald-50", visible);
      badge.classList.toggle("border-emerald-200", visible);
      badge.classList.toggle("text-emerald-700", visible);
      badge.classList.toggle("bg-violet-50", !visible);
      badge.classList.toggle("border-violet-200", !visible);
      badge.classList.toggle("text-violet-700", !visible);
    }

    function getSwarmScopeQueryParams() {
      const scope = normalizeScanScope(tickerScanScope);
      const params = new URLSearchParams();
      params.set("scan_scope", scope);
      if (scope === "debug") {
        params.set("debug_assets", String(getSwarmDebugAssetCount()));
      }
      if (scope === "xetra" || scope === "sweden") {
        params.set("exchange", scope);
      }
      if (scope === "list" || scope === "all_lists") {
        const lists = scope === "list"
          ? sortTickersByUniverse(customTickerList)
          : sortTickersByUniverse(
            (Array.isArray(customTickerLists) && customTickerLists.length > 0
              ? customTickerLists
              : [{ tickers: customTickerList }]).flatMap((entry) => Array.isArray(entry.tickers) ? entry.tickers : [])
          );
        if (lists.length > 0) {
          params.set("ticker_list", lists.join(","));
        }
      }
      return params.toString();
    }

    function hasSwarmThreeSupport() {
      const supported = typeof window !== "undefined" && typeof window.THREE !== "undefined";
      if (swarmRenderDiagnostics.threeSupport !== supported) {
        swarmRenderDiagnostics.threeSupport = supported;
        if (supported) {
          console.info("[SWARM] Three.js detected", {
            revision: window.THREE?.REVISION || "unknown",
          });
        } else {
          console.warn("[SWARM] Three.js unavailable; canvas fallback will be used");
        }
      }
      return supported;
    }

    function setSwarmRenderPath(path, details = null) {
      if (swarmRenderDiagnostics.renderPath === path) {
        return;
      }
      swarmRenderDiagnostics.renderPath = path;
      if (details) {
        console.info(`[SWARM] Render path -> ${path}`, details);
      } else {
        console.info(`[SWARM] Render path -> ${path}`);
      }
    }

    function setSwarmThreeRendererSize() {
      if (!swarmThreeRenderer || !swarmThreeCamera) {
        return;
      }
      const canvas = swarmThreeRenderer.domElement;
      const wrap = document.getElementById("swarm-canvas-wrap");
      if (!canvas || !wrap) {
        return;
      }
      const rect = wrap.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      swarmThreeRenderer.setPixelRatio(window.devicePixelRatio || 1);
      swarmThreeRenderer.setSize(width, height, false);
      swarmThreeCamera.aspect = width / Math.max(1, height);
      swarmThreeCamera.updateProjectionMatrix();
    }

    function ensureSwarmThreeScene() {
      if (isSwarmPlaneMode()) {
        setSwarmRenderPath("canvas", { reason: "plane-mode" });
        return false;
      }
      if (!hasSwarmThreeSupport()) {
        setSwarmRenderPath("canvas", { reason: "three-missing" });
        return false;
      }
      const canvas = document.getElementById("swarm-canvas");
      const wrap = document.getElementById("swarm-canvas-wrap");
      if (!canvas || !wrap) {
        console.warn("[SWARM] Three.js scene unavailable; missing canvas or wrapper", {
          hasCanvas: Boolean(canvas),
          hasWrap: Boolean(wrap),
        });
        setSwarmRenderPath("canvas", { reason: "missing-dom" });
        return false;
      }
      if (swarmThreeReady && swarmThreeRenderer) {
        setSwarmThreeRendererSize();
        setSwarmRenderPath("three", {
          reason: "reuse-scene",
          zoom: Number(swarmZoomLevel || 0),
        });
        return true;
      }

      const THREE = window.THREE;
      swarmThreeScene = new THREE.Scene();
      swarmThreeScene.background = new THREE.Color(0x020617);
      swarmThreeScene.fog = new THREE.FogExp2(0x020617, 0.00075);

      swarmThreeCamera = new THREE.PerspectiveCamera(40, 1, 0.1, 10000);
      swarmThreeCamera.position.set(0, 0, getSwarmWorldFitDistance());
      swarmThreeCamera.lookAt(0, 0, 0);

      swarmThreeRenderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        preserveDrawingBuffer: true,
      });
      swarmThreeRenderer.outputColorSpace = THREE.SRGBColorSpace || THREE.LinearSRGBColorSpace || undefined;
      swarmThreeRenderer.setClearColor(0x020617, 1);
      setSwarmThreeRendererSize();

      const ambient = new THREE.AmbientLight(0xffffff, 1.1);
      const hemi = new THREE.HemisphereLight(0xa5b4fc, 0x020617, 1.6);
      const key = new THREE.DirectionalLight(0xf8fafc, 1.7);
      key.position.set(1.8, 1.2, 2.2);
      const rim = new THREE.DirectionalLight(0x818cf8, 0.65);
      rim.position.set(-2.4, -1.2, -1.6);
      swarmThreeScene.add(ambient, hemi, key, rim);

      swarmThreeSphere = new THREE.Mesh(
        new THREE.SphereGeometry(getSwarmSphereRadius(), 64, 64),
        new THREE.MeshPhongMaterial({
          color: 0x0f172a,
          transparent: true,
          opacity: 0.18,
          wireframe: true,
          shininess: 12,
        }),
      );
      swarmThreeScene.add(swarmThreeSphere);
      updateSwarmThreeSphereAppearance();

      swarmThreeGridGroup = new THREE.Group();
      swarmThreeScene.add(swarmThreeGridGroup);
      swarmThreeAssetGroup = new THREE.Group();
      swarmThreeAgentGroup = new THREE.Group();
      swarmThreeScene.add(swarmThreeAssetGroup);
      swarmThreeScene.add(swarmThreeAgentGroup);
      swarmThreeRaycaster = new THREE.Raycaster();
      swarmThreePointer = new THREE.Vector2();
      swarmThreeReady = true;
      console.info("[SWARM] Three.js scene initialized", {
        revision: THREE.REVISION || "unknown",
        debugMode: isSwarmDebugMode(),
        zoom: Number(swarmZoomLevel || 0),
        devicePixelRatio: Number(window.devicePixelRatio || 1),
      });
      setSwarmRenderPath("three", { reason: "scene-created" });

      const onResize = () => {
        if (swarmThreeReady) {
          setSwarmThreeRendererSize();
          drawSwarmScene();
        }
      };
      if (!window.__swarmThreeResizeHooked) {
        window.__swarmThreeResizeHooked = true;
        window.addEventListener("resize", onResize);
      }
      return true;
    }

    function normalizeSwarmPointer(clientX, clientY) {
      const canvas = swarmThreeRenderer ? swarmThreeRenderer.domElement : document.getElementById("swarm-canvas");
      if (!canvas) {
        return { x: 0, y: 0 };
      }
      const rect = canvas.getBoundingClientRect();
      return {
        x: ((clientX - rect.left) / Math.max(1, rect.width)) * 2 - 1,
        y: -(((clientY - rect.top) / Math.max(1, rect.height)) * 2 - 1),
      };
    }

    function updateSwarmThreeAssetTransform(node, mesh) {
      if (!mesh || !node) {
        return;
      }
      const THREE = window.THREE;
      const sphereRadius = getSwarmSphereRadius();
      const vector = normalizeSwarmVector(node.sphereVector || worldToSphereVector(node.x, node.y));
      if (mesh.userData?.renderKind === "debug-cap") {
        mesh.position.set(0, 0, 0);
        mesh.scale.setScalar(1);
        const north = new THREE.Vector3(0, 1, 0);
        const target = new THREE.Vector3(vector.x, vector.y, vector.z);
        mesh.quaternion.setFromUnitVectors(north, target);
      } else {
        const baseRadius = Math.max(1.2, Number(node.capRadius || node.radius || 1) * 2.0);
        const position = new THREE.Vector3(vector.x, vector.y, vector.z).multiplyScalar(sphereRadius);
        mesh.position.copy(position);
        mesh.scale.setScalar(baseRadius);
      }
      mesh.userData.node = node;
    }

    function updateSwarmThreeAgentTransform(agent, mesh) {
      if (!mesh || !agent) {
        return;
      }
      const THREE = window.THREE;
      const sphereRadius = getSwarmSphereRadius();
      const positionVector = normalizeSwarmVector(agent.sphereVector || worldToSphereVector(agent.x, agent.y));
      const position = new THREE.Vector3(positionVector.x, positionVector.y, positionVector.z).multiplyScalar(sphereRadius * 1.005);
      mesh.position.copy(position);
      mesh.scale.setScalar(Math.max(0.75, getSwarmAgentRadius(agent, { detailScale: 1 })));
      mesh.userData.agent = agent;
    }

    function updateSwarmThreeSphereAppearance() {
      if (!swarmThreeSphere || !swarmThreeSphere.material) {
        return;
      }
      const material = swarmThreeSphere.material;
      if (isSwarmDebugMode()) {
        material.color?.setHex?.(0xe5e7eb);
        material.opacity = 0.42;
        material.wireframe = false;
        material.shininess = 4;
        material.emissive?.setHex?.(0x9ca3af);
      } else {
        material.color?.setHex?.(0x0f172a);
        material.opacity = 0.18;
        material.wireframe = true;
        material.shininess = 12;
        material.emissive?.setHex?.(0x000000);
      }
      material.transparent = true;
      material.needsUpdate = true;
    }

    function getSwarmAssetBorderColor(node) {
      const palette = [
        0x22d3ee,
        0x60a5fa,
        0xa78bfa,
        0xf59e0b,
        0x34d399,
        0xf472b6,
        0xfb7185,
        0xc084fc,
      ];
      const index = Math.floor(stableSwarmFraction(String(node?.ticker || ""), "asset-border") * palette.length);
      return palette[index % palette.length];
    }

    function getSwarmAssetTexture(borderColor) {
      const THREE = window.THREE;
      const key = String(borderColor || 0xffffff);
      if (swarmThreeAssetTextures.has(key)) {
        return swarmThreeAssetTextures.get(key);
      }
      const canvas = document.createElement("canvas");
      canvas.width = 192;
      canvas.height = 192;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        return null;
      }
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      const radius = 74;
      const border = 11;
      const glow = ctx.createRadialGradient(cx - 20, cy - 24, 10, cx, cy, 92);
      glow.addColorStop(0, "rgba(255,255,255,0.95)");
      glow.addColorStop(0.55, "rgba(255,255,255,0.74)");
      glow.addColorStop(1, "rgba(255,255,255,0.0)");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, 92, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,0.64)";
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = border;
      ctx.strokeStyle = `rgba(${(borderColor >> 16) & 255}, ${(borderColor >> 8) & 255}, ${borderColor & 255}, 0.92)`;
      ctx.beginPath();
      ctx.arc(cx, cy, radius - (border * 0.22), 0, Math.PI * 2);
      ctx.stroke();
      ctx.lineWidth = 4;
      ctx.strokeStyle = "rgba(255,255,255,0.28)";
      ctx.beginPath();
      ctx.arc(cx, cy, radius - 8, 0, Math.PI * 2);
      ctx.stroke();

      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;
      texture.colorSpace = THREE.SRGBColorSpace || texture.colorSpace;
      swarmThreeAssetTextures.set(key, texture);
      return texture;
    }

    function getSwarmThreeDebugCapGeometry(sphereRadius, angularRadius) {
      const THREE = window.THREE;
      const radiusKey = Math.round(Number(sphereRadius || 0) * 10) / 10;
      const angularKey = Math.round(Number(angularRadius || 0) * 1000) / 1000;
      const key = `${radiusKey}:${angularKey}`;
      if (!swarmThreeDebugCapGeometryCache.has(key)) {
        const capGeometry = new THREE.SphereGeometry(
          radiusKey * 1.0015,
          18,
          12,
          0,
          Math.PI * 2,
          0,
          angularKey,
        );
        const rimPoints = [];
        const rimRadius = radiusKey * 1.0035;
        const rimSegments = 32;
        for (let step = 0; step < rimSegments; step += 1) {
          const phi = (step / rimSegments) * Math.PI * 2;
          rimPoints.push(new THREE.Vector3(
            Math.sin(angularKey) * Math.cos(phi) * rimRadius,
            Math.cos(angularKey) * rimRadius,
            Math.sin(angularKey) * Math.sin(phi) * rimRadius,
          ));
        }
        const rimGeometry = new THREE.BufferGeometry().setFromPoints(rimPoints);
        swarmThreeDebugCapGeometryCache.set(key, { capGeometry, rimGeometry });
      }
      return swarmThreeDebugCapGeometryCache.get(key);
    }

    function createSwarmThreeDebugCapMesh(node, sphereRadius) {
      const THREE = window.THREE;
      const angularRadius = clampSwarm(
        Number(node.capAngularRadius || (Number(node.capRadius || 1) / Math.max(1, sphereRadius)) || 0.12),
        0.05,
        Math.PI * 0.42,
      );
      const ringColor = getSwarmAssetBorderColor(node);
      const cachedGeometry = getSwarmThreeDebugCapGeometry(sphereRadius, angularRadius);
      const capMaterial = new THREE.MeshPhongMaterial({
        color: 0xf8fafc,
        transparent: true,
        opacity: 0.96,
        shininess: 18,
        specular: new THREE.Color(0xffffff),
        side: THREE.DoubleSide,
        polygonOffset: true,
        polygonOffsetFactor: -1,
        polygonOffsetUnits: -2,
      });
      const group = new THREE.Group();
      const capMesh = new THREE.Mesh(cachedGeometry.capGeometry, capMaterial);
      capMesh.renderOrder = 10;
      group.add(capMesh);

      const rimMaterial = new THREE.LineBasicMaterial({
        color: ringColor,
        transparent: true,
        opacity: 0.95,
        depthTest: true,
        depthWrite: false,
      });
      const rim = new THREE.LineLoop(cachedGeometry.rimGeometry, rimMaterial);
      rim.renderOrder = 11;
      group.add(rim);
      group.userData.renderKind = "debug-cap";
      group.userData.capSignature = `${sphereRadius}:${angularRadius.toFixed(5)}:${ringColor}`;
      return group;
    }

    function disposeSwarmThreeAssetVisual(mesh) {
      if (!mesh) {
        return;
      }
      mesh.traverse?.((child) => {
        child.material?.dispose?.();
      });
      if (mesh.material?.dispose) {
        mesh.material.dispose();
      }
    }

    function syncSwarmThreeScene() {
      if (!swarmThreeReady) {
        return;
      }
      const THREE = window.THREE;
      const sphereRadius = getSwarmSphereRadius();
      if (swarmThreeSphere) {
        const sphereSignature = `${Math.round(sphereRadius)}:${isSwarmDebugMode() ? "debug" : "normal"}`;
        if (swarmThreeSphere.userData.sphereSignature !== sphereSignature) {
          swarmThreeSphere.geometry.dispose?.();
          swarmThreeSphere.geometry = new THREE.SphereGeometry(
            sphereRadius,
            isSwarmDebugMode() ? 32 : 48,
            isSwarmDebugMode() ? 24 : 32,
          );
          swarmThreeSphere.userData.sphereSignature = sphereSignature;
        }
      }
      updateSwarmThreeSphereAppearance();
      syncSwarmThreeGrid();

      const assetIds = new Set();
      swarmVisibleNodes.forEach((node) => {
        const id = String(node.ticker || "");
        assetIds.add(id);
        let mesh = swarmThreeAssetMeshes.get(id);
        const shouldUseDebugCap = isSwarmDebugMode();
        const capSignature = shouldUseDebugCap
          ? `${sphereRadius}:${clampSwarm(Number(node.capAngularRadius || 0.12), 0.05, Math.PI * 0.42).toFixed(5)}:${getSwarmAssetBorderColor(node)}`
          : "sprite";
        if (mesh && mesh.userData?.capSignature !== capSignature) {
          swarmThreeAssetGroup.remove(mesh);
          disposeSwarmThreeAssetVisual(mesh);
          swarmThreeAssetMeshes.delete(id);
          mesh = null;
        }
        if (!mesh) {
          if (shouldUseDebugCap) {
            mesh = createSwarmThreeDebugCapMesh(node, sphereRadius);
          } else {
            const radius = Math.max(1.2, Number(node.capRadius || node.radius || 1) * 2.0);
            const ringColor = getSwarmAssetBorderColor(node);
            const texture = getSwarmAssetTexture(ringColor);
            if (!texture) {
              return;
            }
            const material = new THREE.SpriteMaterial({
              map: texture,
              transparent: true,
              depthWrite: false,
              depthTest: true,
              opacity: 1.0,
              color: 0xffffff,
            });
            mesh = new THREE.Sprite(material);
            mesh.userData.renderKind = "sprite";
            mesh.userData.capSignature = "sprite";
            mesh.scale.setScalar(radius);
          }
          mesh.userData.node = node;
          swarmThreeAssetGroup.add(mesh);
          swarmThreeAssetMeshes.set(id, mesh);
        }
        updateSwarmThreeAssetTransform(node, mesh);
      });
      Array.from(swarmThreeAssetMeshes.entries()).forEach(([id, mesh]) => {
        if (!assetIds.has(id)) {
          swarmThreeAssetGroup.remove(mesh);
          disposeSwarmThreeAssetVisual(mesh);
          swarmThreeAssetMeshes.delete(id);
        }
      });

      const agentIds = new Set();
      if (!isSwarmDebugMode()) {
        swarmAgents.slice(0, SWARM_MAX_DRAWN_AGENTS).forEach((agent) => {
          const id = String(agent.id || "");
          agentIds.add(id);
          let mesh = swarmThreeAgentMeshes.get(id);
          if (!mesh) {
            const geometry = new THREE.SphereGeometry(1, 12, 12);
            const material = new THREE.MeshStandardMaterial({
              color: agent.energy >= SWARM_STARTING_ENERGY ? 0xa5b4fc : 0xf9a8d4,
              transparent: true,
              opacity: 0.8,
              roughness: 0.7,
              metalness: 0.02,
            });
            mesh = new THREE.Mesh(geometry, material);
            mesh.userData.agent = agent;
            swarmThreeAgentGroup.add(mesh);
            swarmThreeAgentMeshes.set(id, mesh);
          }
          updateSwarmThreeAgentTransform(agent, mesh);
        });
      }
      Array.from(swarmThreeAgentMeshes.entries()).forEach(([id, mesh]) => {
        if (!agentIds.has(id)) {
          swarmThreeAgentGroup.remove(mesh);
          mesh.geometry?.dispose?.();
          if (mesh.material?.dispose) {
            mesh.material.dispose();
          }
          swarmThreeAgentMeshes.delete(id);
        }
      });
    }

    function renderSwarmThreeScene() {
      if (isSwarmPlaneMode()) {
        setSwarmRenderPath("canvas", { reason: "plane-mode-render" });
        return false;
      }
      if (!ensureSwarmThreeScene()) {
        return false;
      }
      syncSwarmThreeScene();
      const cameraDistance = getSwarmWorldFitDistance() / Math.max(0.35, swarmZoomLevel);
      const cameraVector = normalizeSwarmVector(swarmCameraVector || { x: 0, y: 0, z: 1 });
      swarmThreeCamera.position.set(
        cameraVector.x * cameraDistance,
        cameraVector.y * cameraDistance,
        cameraVector.z * cameraDistance,
      );
      swarmThreeCamera.lookAt(0, 0, 0);
      swarmThreeCamera.updateProjectionMatrix();
      swarmThreeRenderer.render(swarmThreeScene, swarmThreeCamera);
      setSwarmRenderPath("three", {
        reason: "frame-rendered",
        debugMode: isSwarmDebugMode(),
        nodes: swarmVisibleNodes.length,
        agents: Math.min(swarmAgents.length, SWARM_MAX_DRAWN_AGENTS),
      });
      updateSwarmWorldVisibilityIndicator(cameraDistance);
      return true;
    }

    function stepSwarmDays(days = 1) {
      const delta = Math.max(1, Math.round(Number(days || 1)));
      swarmPlaying = false;
      swarmLastFrameTime = null;
      swarmPlaybackAccumulator = 0;
      advanceSwarmTimeline(delta);
    }

    function advanceSwarmTimeline(days = 1, { fromPlayback = false } = {}) {
      const stepCount = Math.max(1, Math.round(Math.abs(Number(days || 1))));
      const direction = Number(days || 1) < 0 ? -1 : 1;
      for (let idx = 0; idx < stepCount; idx += 1) {
        const nextStep = clampSwarm(swarmTimelineIndex + direction, 0, swarmTimelineMax);
        if (nextStep === swarmTimelineIndex) {
          break;
        }
        swarmTimelineIndex = nextStep;
        swarmVisibleNodes.forEach((node) => {
          const currentValue = Math.max(1, Number(node.simEnergy || node.baseValue || node.value || node.close || SWARM_STARTING_ENERGY));
          const nextReturn = getSwarmNodeReturn(node, swarmTimelineIndex);
          node.simEnergy = Math.max(SWARM_TICKER_WEALTH_FLOOR, currentValue * (1 + nextReturn));
        });
        updateFixedSwarmNodeWorth();
      }
      if (!fromPlayback) {
        swarmPlaying = false;
        swarmLastFrameTime = null;
      }
      updateSwarmTimelineControls();
      updateSwarmSummary();
      drawSwarmScene();
    }

    function normalizeSwarmHistoryPayload(payload) {
      const dates = Array.isArray(payload && payload.dates) ? payload.dates.map((value) => String(value)) : [];
      const rawCloses = Array.isArray(payload && payload.closes) ? payload.closes : [];
      const rawDividends = Array.isArray(payload && payload.dividends) ? payload.dividends : [];
      const closes = rawCloses.map((value) => Number(value)).filter((value) => Number.isFinite(value) && value > 0);
      const dividends = closes.map((_, idx) => {
        const value = Number(rawDividends[Math.max(0, rawDividends.length - closes.length + idx)] || 0);
        return Number.isFinite(value) && value > 0 ? value : 0;
      });
      return {
        dates: dates.slice(-closes.length),
        closes,
        dividends,
        emaCache: new Map(),
        rsiCache: new Map(),
      };
    }

    function refreshSwarmTimelineMax() {
      let maxStep = 0;
      swarmHistoryByTicker.forEach((history) => {
        maxStep = Math.max(maxStep, Math.max(0, history.closes.length - 1));
      });
      swarmTimelineMax = maxStep > 0 ? Math.min(SWARM_TIMELINE_MAX, maxStep) : SWARM_TIMELINE_MAX;
      swarmTimelineIndex = clampSwarm(swarmTimelineIndex, 0, swarmTimelineMax);
      updateSwarmTimelineControls();
    }

    function getSwarmHistoryForTicker(ticker) {
      return swarmHistoryByTicker.get(String(ticker || "").toUpperCase()) || null;
    }

    function getSwarmHistoryIndex(history, step = swarmTimelineIndex) {
      if (!history || history.closes.length < 2) {
        return -1;
      }
      return Math.round(clampSwarm(step, 1, history.closes.length - 1));
    }

    function buildSwarmEmaSeries(closes, period) {
      const cleanPeriod = Math.max(2, Math.round(Number(period || 20)));
      const alpha = 2 / (cleanPeriod + 1);
      const series = [];
      closes.forEach((close, idx) => {
        series.push(idx === 0 ? close : (close * alpha) + (series[idx - 1] * (1 - alpha)));
      });
      return series;
    }

    function getSwarmEmaSeries(history, period) {
      const cleanPeriod = Math.max(2, Math.round(Number(period || 20)));
      if (!history.emaCache.has(cleanPeriod)) {
        history.emaCache.set(cleanPeriod, buildSwarmEmaSeries(history.closes, cleanPeriod));
      }
      return history.emaCache.get(cleanPeriod);
    }

    function buildSwarmRsiSeries(closes, period) {
      const cleanPeriod = Math.max(2, Math.round(Number(period || 14)));
      const series = new Array(closes.length).fill(50);
      let avgGain = 0;
      let avgLoss = 0;

      for (let idx = 1; idx < closes.length; idx += 1) {
        const delta = closes[idx] - closes[idx - 1];
        const gain = Math.max(0, delta);
        const loss = Math.max(0, -delta);
        if (idx <= cleanPeriod) {
          avgGain += gain;
          avgLoss += loss;
          if (idx === cleanPeriod) {
            avgGain /= cleanPeriod;
            avgLoss /= cleanPeriod;
          }
        } else {
          avgGain = ((avgGain * (cleanPeriod - 1)) + gain) / cleanPeriod;
          avgLoss = ((avgLoss * (cleanPeriod - 1)) + loss) / cleanPeriod;
        }

        if (idx >= cleanPeriod) {
          if (avgLoss === 0 && avgGain > 0) {
            series[idx] = 100;
          } else if (avgGain === 0 && avgLoss === 0) {
            series[idx] = 50;
          } else {
            const rs = avgGain / Math.max(0.000001, avgLoss);
            series[idx] = 100 - (100 / (1 + rs));
          }
        }
      }

      return series;
    }

    function getSwarmRsiSeries(history, period) {
      const cleanPeriod = Math.max(2, Math.round(Number(period || 14)));
      if (!history.rsiCache.has(cleanPeriod)) {
        history.rsiCache.set(cleanPeriod, buildSwarmRsiSeries(history.closes, cleanPeriod));
      }
      return history.rsiCache.get(cleanPeriod);
    }

    function normalizeSwarmEmaPair(module = {}, fallbackFast = 30, fallbackSlow = 50) {
      const legacyPeriod = module.period ?? module.ema_period;
      let fastPeriod = Math.round(Number(module.fastPeriod ?? module.fast_period ?? (legacyPeriod ? Number(legacyPeriod) * 0.6 : fallbackFast)));
      let slowPeriod = Math.round(Number(module.slowPeriod ?? module.slow_period ?? legacyPeriod ?? fallbackSlow));
      fastPeriod = clampSwarm(Number.isFinite(fastPeriod) ? fastPeriod : fallbackFast, 2, 180);
      slowPeriod = clampSwarm(Number.isFinite(slowPeriod) ? slowPeriod : fallbackSlow, 3, 260);
      if (fastPeriod >= slowPeriod) {
        slowPeriod = clampSwarm(fastPeriod + 4, 3, 260);
      }
      if (fastPeriod >= slowPeriod) {
        fastPeriod = clampSwarm(slowPeriod - 4, 2, 180);
      }
      return {
        fastPeriod: Math.round(fastPeriod),
        slowPeriod: Math.round(slowPeriod),
      };
    }

    function getSwarmNodeReturn(node, step = swarmTimelineIndex) {
      if (isSwarmDebugMode()) {
        return 0;
      }
      const history = getSwarmHistoryForTicker(node && node.ticker);
      const idx = getSwarmHistoryIndex(history, step);
      if (idx < 1) {
        return 0;
      }
      const previous = Number(history.closes[idx - 1] || 0);
      const current = Number(history.closes[idx] || 0);
      if (previous <= 0 || current <= 0) {
        return 0;
      }
      const dividend = Number((history.dividends || [])[idx] || 0);
      const nominalReturn = ((current + Math.max(0, dividend)) / previous) - 1;
      const inflationDrag = Math.pow(1 + SWARM_ANNUAL_INFLATION_RATE, 1 / 252) - 1;
      return clampSwarm(nominalReturn - inflationDrag, -0.18, 0.18);
    }

    function getSwarmNodeDividendYield(node, step = swarmTimelineIndex) {
      const history = getSwarmHistoryForTicker(node && node.ticker);
      const idx = getSwarmHistoryIndex(history, step);
      if (idx < 1) {
        return 0;
      }
      const previous = Number(history.closes[idx - 1] || 0);
      const dividend = Number((history.dividends || [])[idx] || 0);
      return previous > 0 ? Math.max(0, dividend) / previous : 0;
    }

    function getSwarmNodeSignal(ticker, module, step = swarmTimelineIndex) {
      const history = getSwarmHistoryForTicker(ticker);
      const idx = getSwarmHistoryIndex(history, step);
      if (idx < 1 || !module) {
        return false;
      }
      const type = String(module.type || "");
      if (type === "ema_cross_up" || type === "ema_cross_down") {
        const pair = normalizeSwarmEmaPair(module);
        const fastEma = getSwarmEmaSeries(history, pair.fastPeriod);
        const slowEma = getSwarmEmaSeries(history, pair.slowPeriod);
        const prevFast = Number(fastEma[idx - 1] || 0);
        const currentFast = Number(fastEma[idx] || 0);
        const prevSlow = Number(slowEma[idx - 1] || 0);
        const currentSlow = Number(slowEma[idx] || 0);
        return type === "ema_cross_up"
          ? prevFast <= prevSlow && currentFast > currentSlow
          : prevFast >= prevSlow && currentFast < currentSlow;
      }
      if (type === "rsi_low" || type === "rsi_high") {
        const rsi = getSwarmRsiSeries(history, module.period);
        const currentRsi = Number(rsi[idx] ?? 50);
        const threshold = Number(module.threshold ?? (type === "rsi_low" ? 35 : 70));
        return type === "rsi_low" ? currentRsi <= threshold : currentRsi >= threshold;
      }
      return false;
    }

    function resetSwarmNodeEnergy() {
      swarmVisibleNodes.forEach((node) => {
        node.simEnergy = Number(node.baseValue || node.value || node.close || SWARM_STARTING_ENERGY);
        node.charge = 1;
        node.vx = 0;
        node.vy = 0;
        if (node.seedX !== undefined) {
          node.x = Number(node.seedX || 0);
        }
        if (node.seedY !== undefined) {
          node.y = Number(node.seedY || 0);
        }
        if (node.seedSphereVector) {
          node.sphereVector = { ...node.seedSphereVector };
        } else {
          node.sphereVector = worldToSphereVector(node.x, node.y);
        }
      });
    }

    function updateFixedSwarmNodeWorth() {
      if (!swarmVisibleNodes.length) {
        return;
      }
      if (isSwarmDebugMode()) {
        const realNodes = swarmVisibleNodes;
        const currentDebugRadius = Math.max(1, Number(swarmDebugSphereRadius || getSwarmSphereRadius()));
        const targetDebugRadius = getSwarmDebugAdaptiveSphereRadius(realNodes, currentDebugRadius);
        const sphereRadius = targetDebugRadius > currentDebugRadius
          ? targetDebugRadius
          : (currentDebugRadius + ((targetDebugRadius - currentDebugRadius) * 0.08));
        swarmDebugSphereRadius = Math.max(1, sphereRadius);
        const forces = realNodes.map(() => ({ x: 0, y: 0, z: 0 }));
        realNodes.forEach((node, idx) => {
          const seedVector = normalizeSwarmVector(node.sphereVector || worldToSphereVector(node.x, node.y));
          node.sphereVector = seedVector;
          const capRadius = getSwarmDebugCapRadius(node);
          node.capRadius = capRadius;
          node.mass = Math.max(0.75, Math.pow(capRadius / 8, 1.35));
          node.sphereRadius = swarmDebugSphereRadius;
          node.capAngularRadius = capRadius / Math.max(1, sphereRadius);
          const velocity = node.sphereVelocity || { x: 0, y: 0, z: 0 };
          node.sphereVelocity = projectSwarmVectorToTangentPlane(velocity, seedVector);
        });
        for (let idx = 0; idx < realNodes.length; idx += 1) {
          const node = realNodes[idx];
          const nodeVector = normalizeSwarmVector(node.sphereVector || worldToSphereVector(node.x, node.y));
          const nodeRadius = Math.max(0.9, Number(node.capRadius || getSwarmDebugCapRadius(node)));
          for (let otherIdx = idx + 1; otherIdx < realNodes.length; otherIdx += 1) {
            const other = realNodes[otherIdx];
            const otherVector = normalizeSwarmVector(other.sphereVector || worldToSphereVector(other.x, other.y));
            const dot = clampSwarm(
              (nodeVector.x * otherVector.x) + (nodeVector.y * otherVector.y) + (nodeVector.z * otherVector.z),
              -0.999999,
              0.999999,
            );
            const angle = Math.acos(dot);
            const otherRadius = Math.max(0.9, Number(other.capRadius || getSwarmDebugCapRadius(other)));
            const targetAngle = Math.max(0.02, (nodeRadius + otherRadius) / sphereRadius);
            const nodeToOther = projectSwarmVectorToTangentPlane({
              x: otherVector.x - (nodeVector.x * dot),
              y: otherVector.y - (nodeVector.y * dot),
              z: otherVector.z - (nodeVector.z * dot),
            }, nodeVector);
            const otherToNode = projectSwarmVectorToTangentPlane({
              x: nodeVector.x - (otherVector.x * dot),
              y: nodeVector.y - (otherVector.y * dot),
              z: nodeVector.z - (otherVector.z * dot),
            }, otherVector);
            const gap = angle - targetAngle;
            const nodeMass = Math.max(0.75, Number(node.mass || 1));
            const otherMass = Math.max(0.75, Number(other.mass || 1));
            const attractionBias = Math.sqrt(nodeMass * otherMass);
            const spring = clampSwarm(gap * 0.052 * attractionBias, -0.08, 0.08);
            const overlap = Math.max(0, targetAngle - angle);
            const correction = clampSwarm(overlap * 0.2, 0, 0.11);
            const coupling = spring + correction;
            forces[idx].x += nodeToOther.x * coupling;
            forces[idx].y += nodeToOther.y * coupling;
            forces[idx].z += nodeToOther.z * coupling;
            forces[otherIdx].x += otherToNode.x * coupling;
            forces[otherIdx].y += otherToNode.y * coupling;
            forces[otherIdx].z += otherToNode.z * coupling;
          }
        }
        realNodes.forEach((node, idx) => {
          const currentMass = Math.max(0.45, Number(node.mass || 1));
          const fixedRadius = clampSwarm(getSwarmDebugCapRadius(node), 1.35, 34);
          const force = forces[idx];
          const velocity = node.sphereVelocity || { x: 0, y: 0, z: 0 };
          const damping = 0.93;
          const nextVelocity = projectSwarmVectorToTangentPlane({
            x: (velocity.x * damping) + (force.x / currentMass),
            y: (velocity.y * damping) + (force.y / currentMass),
            z: (velocity.z * damping) + (force.z / currentMass),
          }, node.sphereVector);
          const speed = Math.hypot(nextVelocity.x, nextVelocity.y, nextVelocity.z);
          const velocityLimit = 0.03;
          const cappedVelocity = speed > velocityLimit
            ? {
              x: nextVelocity.x * (velocityLimit / speed),
              y: nextVelocity.y * (velocityLimit / speed),
              z: nextVelocity.z * (velocityLimit / speed),
            }
            : nextVelocity;
          node.sphereVelocity = cappedVelocity;
          node.sphereVector = normalizeSwarmVector({
            x: node.sphereVector.x + cappedVelocity.x,
            y: node.sphereVector.y + cappedVelocity.y,
            z: node.sphereVector.z + cappedVelocity.z,
          });
          const worldPoint = sphereVectorToWorld(node.sphereVector);
          node.x = worldPoint.x;
          node.y = worldPoint.y;
          node.z = node.sphereVector.z * node.sphereRadius;
          node.seedX = worldPoint.x;
          node.seedY = worldPoint.y;
          node.radius = fixedRadius;
          node.capRadius = fixedRadius;
          node.capAngularRadius = fixedRadius / Math.max(1, node.sphereRadius);
          node.vx = 0;
          node.vy = 0;
        });
        resolveSwarmDebugCapCollisions(realNodes, sphereRadius, 5);
        swarmVisibleNodes.forEach((node) => {
          const worldPoint = sphereVectorToWorld(node.sphereVector);
          node.x = worldPoint.x;
          node.y = worldPoint.y;
          node.z = node.sphereVector.z * node.sphereRadius;
          node.seedX = worldPoint.x;
          node.seedY = worldPoint.y;
          const worth = Math.max(SWARM_TICKER_WEALTH_FLOOR, Number(node.simEnergy || node.baseValue || SWARM_STARTING_ENERGY));
          node.charge = 1 + (Math.sqrt(worth / SWARM_STARTING_ENERGY) * 0.2);
          node.radius = clampSwarm(Number(node.capRadius || node.baseRadius || node.radius || 1), 1.35, 34);
          node.capRadius = node.radius;
          node.capAngularRadius = node.radius / Math.max(1, node.sphereRadius);
        });
        return;
      }
      const realNodes = swarmVisibleNodes;
      realNodes.forEach((node, idx) => {
        node.sphereVector = node.sphereVector || worldToSphereVector(node.x, node.y);
        let force = { x: 0, y: 0, z: 0 };
        const currentValue = Math.max(1, Number(node.simEnergy || node.baseValue || node.value || node.close || SWARM_STARTING_ENERGY));
        const currentMass = Math.max(0.45, Number(node.mass || 1));
        const currentReturn = getSwarmNodeReturn(node);
        const currentRadius = clampSwarm(
          Number(node.baseRadius || node.radius || 1) * (0.92 + (Math.log10(currentValue) * 0.06)),
          0.7,
          18,
        );
        node.radius = currentRadius;
        const sampleCount = Math.min(SWARM_SPHERE_REPULSION_SAMPLE, Math.max(0, realNodes.length - 1));
        for (let sample = 0; sample < sampleCount; sample += 1) {
          const offset = 1 + Math.floor(stableSwarmFraction(`${node.ticker}:${sample}`, "sphere-neighbor") * Math.max(1, realNodes.length - 1));
          const other = realNodes[(idx + offset) % realNodes.length];
          if (!other || other === node) {
            continue;
          }
          other.sphereVector = other.sphereVector || worldToSphereVector(other.x, other.y);
          const otherMass = Math.max(0.45, Number(other.mass || 1));
          const otherReturn = getSwarmNodeReturn(other);
          const dot = clampSwarm(
            (node.sphereVector.x * other.sphereVector.x) + (node.sphereVector.y * other.sphereVector.y) + (node.sphereVector.z * other.sphereVector.z),
            -0.98,
            0.98,
          );
          const tangent = normalizeSwarmVector({
            x: node.sphereVector.x - (other.sphereVector.x * dot),
            y: node.sphereVector.y - (other.sphereVector.y * dot),
            z: node.sphereVector.z - (other.sphereVector.z * dot),
          });
          const returnSimilarity = 1 - clampSwarm(Math.abs(currentReturn - otherReturn) / 0.08, 0, 1);
          const sameDirection = Math.sign(currentReturn || 0) === Math.sign(otherReturn || 0);
          const direction = sameDirection ? 1 : -1;
          const distanceFactor = Math.pow(Math.max(0.08, 1 - dot), 1.15);
          const coupling = ((Math.abs(currentReturn) + Math.abs(otherReturn) + 0.0025) * (0.35 + (0.65 * returnSimilarity)) * direction) / distanceFactor;
          const collisionAngle = ((currentRadius + Number(other.radius || 1)) / Math.max(1, getSwarmSphereRadius())) * 1.12;
          const overlap = Math.max(0, collisionAngle - Math.acos(clampSwarm(dot, -1, 1)));
          const collisionImpulse = overlap > 0 ? (overlap / Math.max(collisionAngle, 0.0001)) * 0.04 : 0;
          const strength = clampSwarm((coupling / Math.max(0.75, Math.sqrt(currentMass * otherMass))) + collisionImpulse, -SWARM_SPHERE_REPULSION_LIMIT, SWARM_SPHERE_REPULSION_LIMIT);
          force.x += tangent.x * strength;
          force.y += tangent.y * strength;
          force.z += tangent.z * strength;
        }
        const velocity = node.sphereVelocity || { x: 0, y: 0, z: 0 };
        node.sphereVelocity = {
          x: clampSwarm(velocity.x + (force.x / currentMass), -SWARM_SPHERE_VELOCITY_LIMIT, SWARM_SPHERE_VELOCITY_LIMIT),
          y: clampSwarm(velocity.y + (force.y / currentMass), -SWARM_SPHERE_VELOCITY_LIMIT, SWARM_SPHERE_VELOCITY_LIMIT),
          z: clampSwarm(velocity.z + (force.z / currentMass), -SWARM_SPHERE_VELOCITY_LIMIT, SWARM_SPHERE_VELOCITY_LIMIT),
        };
        node.sphereVector = normalizeSwarmVector({
          x: node.sphereVector.x + node.sphereVelocity.x,
          y: node.sphereVector.y + node.sphereVelocity.y,
          z: node.sphereVector.z + node.sphereVelocity.z,
        });
        const worldPoint = sphereVectorToWorld(node.sphereVector);
        node.x = worldPoint.x;
        node.y = worldPoint.y;
        node.seedX = worldPoint.x;
        node.seedY = worldPoint.y;
      });
      swarmVisibleNodes.forEach((node) => {
        const worth = Math.max(SWARM_TICKER_WEALTH_FLOOR, Number(node.simEnergy || node.baseValue || SWARM_STARTING_ENERGY));
        node.charge = 0.75 + Math.sqrt(worth / SWARM_STARTING_ENERGY) * 1.8;
        node.radius = clampSwarm(Number(node.baseRadius || node.radius || 1) * (0.92 + (Math.log10(worth) * 0.06)), 0.7, 18);
        node.vx = 0;
        node.vy = 0;
      });
    }

    function relaxInitialSwarmSphere(steps = SWARM_SPHERE_INITIAL_RELAX_STEPS) {
      const count = Math.round(clampSwarm(Number(steps || 0), 0, 40));
      if (!swarmVisibleNodes.length || count <= 0) {
        return;
      }
      swarmVisibleNodes.forEach((node) => {
        node.sphereVelocity = { x: 0, y: 0, z: 0 };
      });
      for (let idx = 0; idx < count; idx += 1) {
        updateFixedSwarmNodeWorth();
      }
      swarmVisibleNodes.forEach((node) => {
        node.sphereVelocity = { x: 0, y: 0, z: 0 };
        node.seedX = Number(node.x || 0);
        node.seedY = Number(node.y || 0);
        node.seedSphereVector = node.sphereVector ? { ...node.sphereVector } : worldToSphereVector(node.x, node.y);
      });
    }

    function relaxInitialSwarmPlane(steps = SWARM_SPHERE_INITIAL_RELAX_STEPS) {
      return relaxInitialSwarmSphere(steps);
    }

    function updateSwarmTimelineControls() {
      const slider = document.getElementById("swarm-timeline-slider");
      const label = document.getElementById("swarm-timeline-label");
      const mode = document.getElementById("swarm-timeline-mode");
      const playBtn = document.getElementById("swarm-play-btn");
      const step1Btn = document.getElementById("swarm-step-1-btn");
      const step10Btn = document.getElementById("swarm-step-10-btn");
      if (slider) {
        slider.max = String(swarmTimelineMax);
        slider.value = String(swarmTimelineIndex);
      }
      if (label) {
        label.textContent = `Step ${swarmTimelineIndex} / ${swarmTimelineMax}`;
      }
      if (mode) {
        mode.textContent = swarmPlaying ? "Playing" : "Stopped";
      }
      if (playBtn) {
        playBtn.textContent = swarmPlaying ? "Pause" : "Play";
        playBtn.disabled = Boolean(swarmLoadingPromise);
        playBtn.classList.toggle("cursor-wait", Boolean(swarmLoadingPromise));
      }
      if (step1Btn) {
        step1Btn.disabled = Boolean(swarmLoadingPromise);
      }
      if (step10Btn) {
        step10Btn.disabled = Boolean(swarmLoadingPromise);
      }
    }

    function setSwarmTimeline(nextStep, manual = false) {
      swarmTimelineIndex = clampSwarm(Math.round(nextStep || 0), 0, swarmTimelineMax);
      if (manual) {
        swarmPlaying = false;
        swarmLastFrameTime = null;
        swarmPlaybackAccumulator = 0;
      }
      updateFixedSwarmNodeWorth();
      updateSwarmTimelineControls();
      updateSwarmSummary();
      drawSwarmScene();
    }

    function updateSwarmJumpCostControl() {
      const slider = document.getElementById("swarm-jump-cost-slider");
      const label = document.getElementById("swarm-jump-cost-label");
      if (slider) {
        slider.value = String(swarmJumpCostMultiplier);
      }
      if (label) {
        label.textContent = `${Number(swarmJumpCostMultiplier).toFixed(2)}x market friction`;
      }
    }

    function setSwarmJumpCost(nextValue) {
      swarmJumpCostMultiplier = clampSwarm(Number(nextValue || 2), 0.5, 8);
      updateSwarmJumpCostControl();
      updateSwarmPanels();
    }

    function updateSwarmGridControls() {
      const senseSlider = document.getElementById("swarm-sense-slider");
      const senseLabel = document.getElementById("swarm-sense-label");
      const agentsSlider = document.getElementById("swarm-agents-per-node-slider");
      const agentsLabel = document.getElementById("swarm-agents-per-node-label");
      const zoomSlider = document.getElementById("swarm-zoom-slider");
      const zoomLabel = document.getElementById("swarm-zoom-label");
      if (senseSlider) {
        senseSlider.value = String(swarmSenseRadius);
      }
      if (senseLabel) {
        senseLabel.textContent = "Global asset scan";
      }
      if (agentsSlider) {
        agentsSlider.value = String(swarmAgentsPerNode);
      }
      if (agentsLabel) {
        agentsLabel.textContent = `${swarmAgentsPerNode} per alternating asset · cap ${getSwarmEffectiveAgentCap()}`;
      }
      if (zoomSlider) {
        zoomSlider.value = String(swarmZoomLevel);
      }
      if (zoomLabel) {
        zoomLabel.textContent = swarmZoomLevel <= 0.45
          ? "full globe"
          : `${Number(swarmZoomLevel).toFixed(2)}x sphere view`;
      }
      updateSwarmWorldVisibilityIndicator();
    }

    function setSwarmSense(nextValue) {
      swarmSenseRadius = Math.round(clampSwarm(Number(nextValue || 1), 1, 5));
      updateSwarmGridControls();
      updateSwarmPanels();
    }

    function setSwarmAgentsPerNode(nextValue) {
      swarmAgentsPerNode = Math.round(clampSwarm(Number(nextValue || 20), 1, 100));
      updateSwarmGridControls();
      resetSwarmSimulation();
    }

    function getSwarmEffectiveAgentCap() {
      return Math.round(clampSwarm(500 + (swarmAgentsPerNode * 45), 500, SWARM_MAX_AGENTS));
    }

    function setSwarmZoom(nextValue) {
      swarmZoomLevel = clampSwarm(Number(nextValue || 0.75), 0.35, 2.2);
      updateSwarmGridControls();
      drawSwarmScene();
    }

    function getSwarmCanvasLayout(canvas = document.getElementById("swarm-canvas")) {
      if (!canvas) {
        return null;
      }
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(1, rect.width);
      const height = Math.max(1, rect.height);
      if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
      }

      const worldWidth = Number((swarmWorld && swarmWorld.world && swarmWorld.world.width) || 1600);
      const worldHeight = Number((swarmWorld && swarmWorld.world && swarmWorld.world.height) || 920);
      const padding = 22;
      const scale = Math.min(
        Math.max(0.1, (width - (padding * 2)) / worldWidth),
        Math.max(0.1, (height - (padding * 2)) / worldHeight),
      );
      const offsetX = (width - (worldWidth * scale)) / 2;
      const offsetY = (height - (worldHeight * scale)) / 2;

      return {
        canvas,
        rect,
        dpr,
        width,
        height,
        worldWidth,
        worldHeight,
        scale,
        sphereRadius: Math.min(width, height) * (isSwarmDebugMode() ? 0.48 : 0.43),
        detailScale: clampSwarm(0.8 + (swarmZoomLevel * 0.34), 0.72, 2.15),
        offsetX,
        offsetY,
      };
    }

    function worldToCanvas(layout, x, y) {
      if (isSwarmPlaneMode()) {
        const planeX = Number(x || 0);
        const planeY = Number(y || 0);
        return {
          x: layout.offsetX + (planeX * layout.scale),
          y: layout.offsetY + (planeY * layout.scale),
          depth: 0,
          visible: planeX >= 0 && planeX <= layout.worldWidth && planeY >= 0 && planeY <= layout.worldHeight,
          backSide: false,
        };
      }
      const vector = worldToSphereVector(x, y);
      const basis = getSphereBasis(swarmCameraVector);
      const depth = (vector.x * basis.forward.x) + (vector.y * basis.forward.y) + (vector.z * basis.forward.z);
      const horizontal = (vector.x * basis.right.x) + (vector.y * basis.right.y) + (vector.z * basis.right.z);
      const vertical = (vector.x * basis.up.x) + (vector.y * basis.up.y) + (vector.z * basis.up.z);
      const centerX = layout.width / 2;
      const centerY = layout.height / 2;

      if (isSwarmDebugMode() || swarmZoomLevel <= 0.45) {
        return {
          x: centerX + (horizontal * layout.sphereRadius),
          y: centerY - (vertical * layout.sphereRadius),
          depth,
          visible: isSwarmDebugMode() ? depth > -0.2 : depth > -0.12,
          backSide: depth < 0,
        };
      }

      const camLon = Math.atan2(basis.forward.z, basis.forward.x);
      const camLat = Math.asin(clampSwarm(basis.forward.y, -1, 1));
      const lon = Math.atan2(vector.z, vector.x);
      const lat = Math.asin(clampSwarm(vector.y, -1, 1));
      let deltaLon = lon - camLon;
      if (deltaLon > Math.PI) deltaLon -= Math.PI * 2;
      if (deltaLon < -Math.PI) deltaLon += Math.PI * 2;
      const deltaLat = lat - camLat;
      const mapScale = Math.min(layout.width / (Math.PI * 2), layout.height / Math.PI) * swarmZoomLevel;
      return {
        x: centerX + (deltaLon * mapScale),
        y: centerY - (deltaLat * mapScale),
        depth,
        visible: Math.abs(deltaLon) < Math.PI && Math.abs(deltaLat) < (Math.PI / 2),
        backSide: false,
      };
    }

    function wrapWorldPosition(node) {
      const worldWidth = Number((swarmWorld && swarmWorld.world && swarmWorld.world.width) || 1600);
      const worldHeight = Number((swarmWorld && swarmWorld.world && swarmWorld.world.height) || 920);
      node.x = ((Number(node.x || 0) % worldWidth) + worldWidth) % worldWidth;
      node.y = ((Number(node.y || 0) % worldHeight) + worldHeight) % worldHeight;
    }

    function getWrappedDelta(ax, ay, bx, by) {
      const worldWidth = Number((swarmWorld && swarmWorld.world && swarmWorld.world.width) || 1600);
      const worldHeight = Number((swarmWorld && swarmWorld.world && swarmWorld.world.height) || 920);
      let dx = Number(bx || 0) - Number(ax || 0);
      let dy = Number(by || 0) - Number(ay || 0);
      if (dx > worldWidth / 2) dx -= worldWidth;
      if (dx < -worldWidth / 2) dx += worldWidth;
      if (dy > worldHeight / 2) dy -= worldHeight;
      if (dy < -worldHeight / 2) dy += worldHeight;
      return { dx, dy };
    }

    function getSwarmNodeAtPoint(clientX, clientY) {
      if (!isSwarmPlaneMode() && swarmThreeReady && swarmThreeRenderer && swarmThreeCamera && swarmThreeRaycaster && swarmThreePointer) {
        const pointer = normalizeSwarmPointer(clientX, clientY);
        swarmThreePointer.set(pointer.x, pointer.y);
        swarmThreeRaycaster.setFromCamera(swarmThreePointer, swarmThreeCamera);
        const meshes = Array.from(swarmThreeAssetMeshes.values());
        const hits = swarmThreeRaycaster.intersectObjects(meshes, true);
        if (hits.length > 0) {
          const hit = hits[0];
          const object = hit && hit.object ? hit.object : null;
          return object ? (object.userData.node || object.parent?.userData?.node || null) : null;
        }
      }
      const layout = getSwarmCanvasLayout();
      if (!layout || swarmVisibleNodes.length === 0) {
        return null;
      }

      const x = clientX - layout.rect.left;
      const y = clientY - layout.rect.top;
      let winner = null;
      let winnerDistance = Number.POSITIVE_INFINITY;

      swarmVisibleNodes.forEach((node) => {
        const point = worldToCanvas(layout, node.x, node.y);
        if (!point.visible) {
          return;
        }
        const radius = getSwarmTickerDrawRadius(node, layout);
        const dist = Math.hypot(x - point.x, y - point.y);
        if (dist <= radius + 3 && dist < winnerDistance) {
          winner = node;
          winnerDistance = dist;
        }
      });

      return winner;
    }

    function getSwarmAgentAtPoint(clientX, clientY) {
      if (!isSwarmPlaneMode() && swarmThreeReady && swarmThreeRenderer && swarmThreeCamera && swarmThreeRaycaster && swarmThreePointer) {
        const pointer = normalizeSwarmPointer(clientX, clientY);
        swarmThreePointer.set(pointer.x, pointer.y);
        swarmThreeRaycaster.setFromCamera(swarmThreePointer, swarmThreeCamera);
        const meshes = Array.from(swarmThreeAgentMeshes.values());
        const hits = swarmThreeRaycaster.intersectObjects(meshes, true);
        if (hits.length > 0) {
          const hit = hits[0];
          const object = hit && hit.object ? hit.object : null;
          return object ? (object.userData.agent || object.parent?.userData?.agent || null) : null;
        }
      }
      const layout = getSwarmCanvasLayout();
      if (!layout || swarmAgents.length === 0) {
        return null;
      }

      const x = clientX - layout.rect.left;
      const y = clientY - layout.rect.top;
      let winner = null;
      let winnerDistance = Number.POSITIVE_INFINITY;

      const drawnAgents = swarmAgents.length > SWARM_MAX_DRAWN_AGENTS
        ? swarmAgents.filter((agent, idx) => idx < 120 || (idx % Math.ceil(swarmAgents.length / SWARM_MAX_DRAWN_AGENTS)) === 0)
        : swarmAgents;

      drawnAgents.forEach((agent) => {
        const point = worldToCanvas(layout, agent.x, agent.y);
        if (!point.visible) {
          return;
        }
        const radius = Math.max(5, getSwarmAgentRadius(agent, layout));
        const dist = Math.hypot(x - point.x, y - point.y);
        if (dist <= radius + 6 && dist < winnerDistance) {
          winner = agent;
          winnerDistance = dist;
        }
      });

      return winner;
    }

    function renderSwarmNodeCard(node) {
      if (!node) {
        return "No asset selected.";
      }
      const nextReturn = getSwarmNodeReturn(node);
      const dividendYield = getSwarmNodeDividendYield(node);
      return `
        <div class="space-y-3">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900 text-lg leading-none">${node.ticker}</span>
                <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${getShortlistLabelClasses(node.label)}">${node.label}</span>
              </div>
              <div class="mt-1 text-sm text-slate-600">${node.name || node.ticker}</div>
            </div>
            <div class="text-right shrink-0">
              <div class="text-[10px] uppercase tracking-wide text-slate-400 font-bold">Asset value</div>
              <div class="text-2xl font-bold text-slate-900">${Number(node.simEnergy || SWARM_STARTING_ENERGY).toFixed(0)}</div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="rounded-lg bg-slate-50 px-3 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Profile</div>
              <div class="mt-1 font-semibold text-slate-700">${node.asset_class || "ETF"} · ${node.region || "Unknown"}</div>
              <div class="text-slate-500">${node.issuer || "Unknown issuer"}</div>
            </div>
            <div class="rounded-lg bg-slate-50 px-3 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Signal</div>
              <div class="mt-1 font-semibold text-slate-700">${formatShortlistEntryAge(node.recent_entry_days)}</div>
              <div class="text-slate-500">${(Number(node.volume || 0) / 1000).toFixed(0)}K volume</div>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 text-xs">
            <div class="rounded-lg border border-slate-200 px-2 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Final</div>
              <div class="mt-1 text-lg font-bold text-slate-800">${Number(node.final_score || 0).toFixed(0)}</div>
            </div>
            <div class="rounded-lg border border-slate-200 px-2 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Momentum</div>
              <div class="mt-1 text-lg font-bold text-slate-800">${Number(node.momentum_score || 0).toFixed(0)}</div>
            </div>
            <div class="rounded-lg border border-slate-200 px-2 py-2">
              <div class="uppercase tracking-wide text-slate-400 font-bold">Real Step %</div>
              <div class="mt-1 text-lg font-bold ${nextReturn >= 0 ? "text-emerald-700" : "text-rose-700"}">${(nextReturn * 100).toFixed(2)}</div>
            </div>
          </div>
          <div class="rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
            <span class="font-bold uppercase tracking-wide text-emerald-600">Dividend contribution</span>
            <span class="font-semibold"> ${(dividendYield * 100).toFixed(3)}% this step</span>
            <span class="text-emerald-700"> · returns are price plus dividends minus ${(SWARM_ANNUAL_INFLATION_RATE * 100).toFixed(1)}% annual inflation.</span>
          </div>
        </div>
      `;
    }

    function getSwarmGenomeEmaPair(genome = {}) {
      return normalizeSwarmEmaPair({
        fastPeriod: genome.emaFastPeriod ?? genome.ema_fast_period,
        slowPeriod: genome.emaSlowPeriod ?? genome.ema_slow_period,
        period: genome.emaPeriod ?? genome.ema_period,
      });
    }

    function cloneSwarmBehaviorModule(module = {}, genome = {}) {
      const type = String(module.type || "");
      const payload = {
        type,
        stay_weight: Number(module.stayWeight ?? module.stay_weight ?? 0),
        jump_weight: Number(module.jumpWeight ?? module.jump_weight ?? 0),
      };
      if (type === "ema_cross_up" || type === "ema_cross_down") {
        const genomePair = getSwarmGenomeEmaPair(genome);
        const pair = normalizeSwarmEmaPair(module, genomePair.fastPeriod, genomePair.slowPeriod);
        payload.fast_period = pair.fastPeriod;
        payload.slow_period = pair.slowPeriod;
      } else {
        payload.period = Math.round(Number(module.period || 0));
        payload.threshold = module.threshold === undefined ? null : Math.round(Number(module.threshold || 0));
      }
      return payload;
    }

    function cloneSwarmDna(genome = {}) {
      const emaPair = getSwarmGenomeEmaPair(genome);
      const sourceModules = Array.isArray(genome.behaviorModules)
        ? genome.behaviorModules
        : (Array.isArray(genome.behavior_modules) ? genome.behavior_modules : []);
      return JSON.parse(JSON.stringify({
        schema_version: SWARM_DNA_SCHEMA_VERSION,
        ema_fast_period: emaPair.fastPeriod,
        ema_slow_period: emaPair.slowPeriod,
        rsi_period: Math.round(Number(genome.rsiPeriod ?? genome.rsi_period ?? 14)),
        rsi_low: Math.round(Number(genome.rsiLow ?? genome.rsi_low ?? 35)),
        rsi_high: Math.round(Number(genome.rsiHigh ?? genome.rsi_high ?? 70)),
        behavior_modules: sourceModules.map((module) => cloneSwarmBehaviorModule(module, genome)),
        mutation_rate: Number(genome.mutationRate ?? genome.mutation_rate ?? 0),
        spawn_limit: Number(genome.spawnLimit ?? genome.spawn_limit ?? 0),
        jump_cost_sensitivity: Number(genome.jumpCostSensitivity ?? genome.jump_cost_sensitivity ?? 0),
        exploration_bias: Number(genome.explorationBias ?? genome.exploration_bias ?? 0),
        metabolism: Number(genome.metabolism || 0),
        speed: Number(genome.speed || 0),
      }));
    }

    function formatSwarmDnaSummary(dna = {}) {
      const modules = Array.isArray(dna.behavior_modules) ? dna.behavior_modules : [];
      const emaUp = modules.find((module) => module.type === "ema_cross_up") || {};
      const emaDown = modules.find((module) => module.type === "ema_cross_down") || {};
      const rsiLow = modules.find((module) => module.type === "rsi_low") || {};
      const rsiHigh = modules.find((module) => module.type === "rsi_high") || {};
      const legacyEma = Number(dna.ema_period || emaUp.period || 0);
      const emaFast = Math.round(Number(dna.ema_fast_period || emaUp.fast_period || emaDown.fast_period || (legacyEma ? legacyEma * 0.6 : 30)));
      const emaSlow = Math.round(Number(dna.ema_slow_period || emaUp.slow_period || emaDown.slow_period || legacyEma || 50));
      return `EMA ${emaFast}/${emaSlow} up J ${Number(emaUp.jump_weight || 0).toFixed(2)} / down S ${Number(emaDown.stay_weight || 0).toFixed(2)} · RSI ${dna.rsi_period || rsiLow.period || 14} ${rsiLow.threshold || dna.rsi_low || 35}/${rsiHigh.threshold || dna.rsi_high || 70}`;
    }

    function interpretSwarmDnaRules(dna = {}) {
      const modules = Array.isArray(dna.behavior_modules) ? dna.behavior_modules : [];
      const emaUp = modules.find((module) => module.type === "ema_cross_up") || {};
      const emaDown = modules.find((module) => module.type === "ema_cross_down") || {};
      const rsiLow = modules.find((module) => module.type === "rsi_low") || {};
      const rsiHigh = modules.find((module) => module.type === "rsi_high") || {};
      const emaFast = Math.round(Number(dna.ema_fast_period || emaUp.fast_period || emaDown.fast_period || 30));
      const emaSlow = Math.round(Number(dna.ema_slow_period || emaUp.slow_period || emaDown.slow_period || 50));
      const low = Math.round(Number(rsiLow.threshold || dna.rsi_low || 35));
      const high = Math.round(Number(rsiHigh.threshold || dna.rsi_high || 70));
      const jumpCost = Number(dna.jump_cost_sensitivity || 1);
      const exploration = Number(dna.exploration_bias || 0);
      const rules = [
        `Hold winners while EMA ${emaFast} stays constructive against EMA ${emaSlow}; jump only when a global ticker setup clears friction.`,
        `Treat dividends as part of total return and judge each step against the ${(SWARM_ANNUAL_INFLATION_RATE * 100).toFixed(1)}% annual inflation hurdle.`,
        `Use RSI ${low}-${high} as comfort bounds: oversold cells can be recovery candidates, overheated cells need stronger trend evidence.`,
      ];
      if (jumpCost >= 1.15) {
        rules.push("Move reluctantly: require a larger global edge before paying transaction and jump friction.");
      } else {
        rules.push("Move readily when a global alternative looks better after transaction and jump friction.");
      }
      if (exploration >= 0.55) {
        rules.push("Keep a deliberate curiosity bias toward unvisited assets anywhere in the world.");
      } else {
        rules.push("Prefer known assets with positive memory over novelty.");
      }
      return rules;
    }

    function renderSwarmAgentCard(agent) {
      if (!agent) {
        return "Click an agent to inspect its mutable traits.";
      }
      const target = agent.targetTicker ? swarmNodeMap.get(agent.targetTicker) : null;
      const genome = agent.genome || {};
      const dna = cloneSwarmDna(genome);
      const emaPair = getSwarmGenomeEmaPair(genome);
      const memoryCount = Object.keys(agent.memory || {}).length;
      return `
        <div class="space-y-3">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="font-bold text-slate-900">Generation ${agent.generation}</div>
              <div class="text-xs text-slate-500">${target ? `On ${target.ticker}` : "No ticker target"} · age ${Math.round(agent.age || 0)} · ${memoryCount} learned tickers</div>
            </div>
            <div class="text-right">
              <div class="text-[10px] uppercase tracking-wide text-slate-400 font-bold">Energy</div>
              <div class="text-xl font-bold ${agent.energy >= 0 ? "text-emerald-700" : "text-rose-700"}">${Number(agent.energy || 0).toFixed(0)}</div>
            </div>
          </div>
          <div class="rounded-lg border border-violet-100 bg-violet-50 px-3 py-2 text-xs text-violet-900">
            <div class="font-bold uppercase tracking-wide text-violet-500">Behavior DNA</div>
            <div class="mt-1 font-semibold">${formatSwarmDnaSummary(dna)}</div>
          </div>
          <div class="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs text-emerald-950">
            <div class="font-bold uppercase tracking-wide text-emerald-600">Investment rule interpretation</div>
            <ul class="mt-1 list-disc pl-4 space-y-1">
              ${interpretSwarmDnaRules(dna).map((rule) => `<li>${rule}</li>`).join("")}
            </ul>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="rounded-lg bg-slate-50 px-3 py-2"><span class="font-bold text-slate-400">EMA cross</span><div class="font-semibold text-slate-800">${emaPair.fastPeriod} / ${emaPair.slowPeriod}</div></div>
            <div class="rounded-lg bg-slate-50 px-3 py-2"><span class="font-bold text-slate-400">RSI</span><div class="font-semibold text-slate-800">${Math.round(genome.rsiPeriod || 0)} · ${Math.round(genome.rsiLow || 0)}-${Math.round(genome.rsiHigh || 0)}</div></div>
            <div class="rounded-lg bg-slate-50 px-3 py-2"><span class="font-bold text-slate-400">Spawn</span><div class="font-semibold text-slate-800">${Number(genome.spawnLimit || 0).toFixed(0)}</div></div>
            <div class="rounded-lg bg-slate-50 px-3 py-2"><span class="font-bold text-slate-400">Mutation</span><div class="font-semibold text-slate-800">${(Number(genome.mutationRate || 0) * 100).toFixed(1)}%</div></div>
            <div class="rounded-lg bg-slate-50 px-3 py-2"><span class="font-bold text-slate-400">Jump cost</span><div class="font-semibold text-slate-800">${Number(genome.jumpCostSensitivity || 0).toFixed(2)}</div></div>
            <div class="rounded-lg bg-slate-50 px-3 py-2"><span class="font-bold text-slate-400">Explore</span><div class="font-semibold text-slate-800">${Number(genome.explorationBias || 0).toFixed(2)}</div></div>
          </div>
        </div>
      `;
    }

    function snapshotSwarmAgent(agent) {
      const genome = agent.genome || {};
      const dna = cloneSwarmDna(genome);
      const targetNode = agent.targetTicker ? swarmNodeMap.get(agent.targetTicker) : null;
      return {
        id: agent.id,
        generation: agent.generation,
        targetTicker: targetNode ? agent.targetTicker || "" : "",
        energy: Number(agent.energy || 0),
        profit: Number(agent.energy || 0) - SWARM_STARTING_ENERGY,
        age: Number(agent.age || 0),
        learnedTickers: Object.keys(agent.memory || {}).length,
        emaFastPeriod: Math.round(genome.emaFastPeriod || 0),
        emaSlowPeriod: Math.round(genome.emaSlowPeriod || 0),
        rsiPeriod: Math.round(genome.rsiPeriod || 0),
        rsiLow: Math.round(genome.rsiLow || 0),
        rsiHigh: Math.round(genome.rsiHigh || 0),
        mutationRate: Number(genome.mutationRate || 0),
        spawnLimit: Number(genome.spawnLimit || 0),
        dna,
      };
    }

    function getSwarmTopAgentSnapshots() {
      return [...swarmCompletedAgents, ...swarmAgents.map(snapshotSwarmAgent)]
        .sort((a, b) => Number(b.profit || 0) - Number(a.profit || 0))
        .slice(0, 10);
    }

    function setSwarmDnaSaveStatus(message, tone = "muted") {
      const status = document.getElementById("swarm-dna-save-status");
      if (!status) {
        return;
      }
      const toneClass = {
        muted: "text-slate-400",
        saving: "text-violet-600",
        saved: "text-emerald-600",
        error: "text-rose-600",
      }[tone] || "text-slate-400";
      status.className = `text-[11px] font-bold ${toneClass}`;
      status.textContent = message;
    }

    function renderSwarmTopAgents(forceMessage = false) {
      const topEl = document.getElementById("swarm-top-agents");
      if (!topEl) {
        return;
      }

      const finished = swarmTimelineIndex >= swarmTimelineMax || (swarmAgents.length === 0 && swarmCompletedAgents.length > 0);
      if (forceMessage || !finished) {
        swarmTopAgentSnapshots = [];
        setSwarmDnaSaveStatus("Autosaves to config", "muted");
        topEl.innerHTML = "The ten most profitable agents appear when the timeline finishes.";
        return;
      }

      const snapshots = getSwarmTopAgentSnapshots();
      swarmTopAgentSnapshots = snapshots;

      if (!snapshots.length) {
        setSwarmDnaSaveStatus("No DNA to save", "muted");
        topEl.innerHTML = "No surviving agent results yet.";
        return;
      }

      topEl.innerHTML = `
        <div class="space-y-2">
          ${snapshots.map((agent, idx) => `
            <div class="rounded-lg bg-slate-50 px-3 py-2">
              <div class="flex items-center justify-between gap-2">
                <span class="font-bold text-slate-800">#${idx + 1} Gen ${agent.generation}</span>
                <span class="font-bold ${agent.profit >= 0 ? "text-emerald-700" : "text-rose-700"}">${agent.profit >= 0 ? "+" : ""}${Number(agent.profit).toFixed(0)}</span>
              </div>
              <div class="mt-1 text-[11px] text-slate-500">${agent.targetTicker || "No ticker"} · ${formatSwarmDnaSummary(agent.dna)} · mut ${(agent.mutationRate * 100).toFixed(1)}%</div>
              <div class="mt-1 text-[11px] text-emerald-700">${interpretSwarmDnaRules(agent.dna)[0]}</div>
            </div>
          `).join("")}
        </div>
      `;
      autoSaveSwarmTopAgentDna();
    }

    function buildSwarmTopAgentDnaPayload() {
      const topAgents = (swarmTopAgentSnapshots.length ? swarmTopAgentSnapshots : getSwarmTopAgentSnapshots())
        .map((agent, idx) => ({
          rank: idx + 1,
          id: agent.id,
          generation: agent.generation,
          energy: Number(agent.energy || 0),
          profit: Number(agent.profit || 0),
          age: Number(agent.age || 0),
          target_ticker: agent.targetTicker || "",
          learned_ticker_count: Number(agent.learnedTickers || 0),
          dna: agent.dna,
          rules: interpretSwarmDnaRules(agent.dna),
        }));

      return {
        schema_version: SWARM_DNA_SCHEMA_VERSION,
        created_at: new Date().toISOString(),
        world_version: swarmWorld && swarmWorld.world ? swarmWorld.world.version : null,
        as_of_date: swarmWorld ? swarmWorld.as_of_date : null,
        simulation: {
          steps: swarmTimelineIndex,
          max_steps: swarmTimelineMax,
          filter: swarmFilter,
          visible_node_count: swarmVisibleNodes.length,
          starting_energy: SWARM_STARTING_ENERGY,
          jump_cost_multiplier: Number(swarmJumpCostMultiplier || 0),
          history_days: SWARM_HISTORY_DAYS,
          history_ticker_count: swarmHistoryMeta ? Number(swarmHistoryMeta.count || 0) : 0,
        },
        top_agents: topAgents,
      };
    }

    function getSwarmDnaPayloadSignature(payload) {
      return JSON.stringify({
        schema_version: payload.schema_version,
        world_version: payload.world_version,
        as_of_date: payload.as_of_date,
        simulation: payload.simulation,
        top_agents: payload.top_agents.map((agent) => ({
          id: agent.id,
          generation: agent.generation,
          profit: Number(agent.profit || 0).toFixed(4),
          dna: agent.dna,
        })),
      });
    }

    async function autoSaveSwarmTopAgentDna() {
      if (!swarmTopAgentSnapshots.length) {
        return;
      }
      const payload = buildSwarmTopAgentDnaPayload();
      const signature = getSwarmDnaPayloadSignature(payload);
      if (swarmDnaSaveInFlight || signature === swarmDnaLastSavedSignature) {
        return;
      }

      swarmDnaSaveInFlight = true;
      setSwarmDnaSaveStatus("Saving DNA...", "saving");
      try {
        const resp = await fetch("/api/swarm-dna/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "DNA save failed");
        }
        swarmDnaLastSavedSignature = signature;
        setSwarmDnaSaveStatus(`Saved ${data.agent_count || payload.top_agents.length} to ${data.path || SWARM_DNA_CONFIG_PATH}`, "saved");
      } catch (err) {
        console.warn("Swarm DNA autosave failed", err);
        setSwarmDnaSaveStatus("DNA save failed", "error");
      } finally {
        swarmDnaSaveInFlight = false;
      }
    }

    function updateSwarmPanels() {
      const hoverEl = document.getElementById("swarm-hover");
      const selectedEl = document.getElementById("swarm-selected");
      const selectedAgentEl = document.getElementById("swarm-agent-selected");
      const openBtn = document.getElementById("swarm-selected-open");
      const captionEl = document.getElementById("swarm-world-caption");

      const hoverNode = swarmHoveredTicker ? swarmNodeMap.get(swarmHoveredTicker) : null;
      const selectedNode = swarmSelectedTicker ? swarmNodeMap.get(swarmSelectedTicker) : null;
      const selectedAgent = swarmSelectedAgentId
        ? swarmAgents.find((agent) => agent.id === swarmSelectedAgentId)
        : null;

      if (hoverEl) {
        hoverEl.innerHTML = hoverNode
          ? renderSwarmNodeCard(hoverNode)
          : "Move across the sphere to inspect asset clusters.";
      }
      if (selectedEl) {
        selectedEl.innerHTML = selectedNode
          ? renderSwarmNodeCard(selectedNode)
          : "Click an asset to pin it here and jump into the Screener chart.";
      }
      if (openBtn) {
        openBtn.disabled = !selectedNode;
      }
      if (selectedAgentEl) {
        selectedAgentEl.innerHTML = renderSwarmAgentCard(selectedAgent);
      }
      if (captionEl) {
        if (selectedAgent) {
          captionEl.textContent = `Agent gen ${selectedAgent.generation} · energy ${Number(selectedAgent.energy || 0).toFixed(0)}`;
        } else if (selectedNode) {
          captionEl.textContent = `Pinned ${selectedNode.ticker} · click Open Chart to inspect`;
        } else if (hoverNode) {
          captionEl.textContent = `${hoverNode.ticker} · ${hoverNode.label} · asset value ${Number(hoverNode.simEnergy || SWARM_STARTING_ENERGY).toFixed(0)}`;
        } else if (isSwarmDebugMode()) {
          captionEl.textContent = "Debug sphere · caps attract and settle";
        } else {
          captionEl.textContent = "Hover an asset to inspect it";
        }
      }
    }

    function updateSwarmSummary() {
      const avgEnergy = swarmAgents.length
        ? swarmAgents.reduce((sum, agent) => sum + Number(agent.energy || 0), 0) / swarmAgents.length
        : 0;

      const bugCountEl = document.getElementById("swarm-bug-count");
      const avgEl = document.getElementById("swarm-energy-avg");
      const visibleEl = document.getElementById("swarm-visible-count");
      const genEl = document.getElementById("swarm-generation-count");
      const birthEl = document.getElementById("swarm-birth-count");
      const deathEl = document.getElementById("swarm-death-count");

      if (bugCountEl) bugCountEl.textContent = String(swarmAgents.length);
      if (avgEl) avgEl.textContent = Number(avgEnergy).toFixed(1);
      if (visibleEl) visibleEl.textContent = String(swarmVisibleNodes.length);
      if (genEl) genEl.textContent = String(swarmGenerationMax);
      if (birthEl) birthEl.textContent = String(swarmBirthCount);
      if (deathEl) deathEl.textContent = String(swarmDeathCount);
      updateSwarmTimelineControls();
    }

    function createSwarmGenome(seed = null) {
      const base = seed || {};
      const rate = Number(base.mutationRate ?? base.mutation_rate ?? (0.035 + (Math.random() * 0.055)));
      const mutate = (value, spread, floor, ceil, integer = false) => {
        const start = value !== undefined ? Number(value) : floor + (Math.random() * (ceil - floor));
        const activeSpread = seed ? spread * Math.max(0.25, rate * 12) : spread;
        const next = start * (1 + ((Math.random() - 0.5) * activeSpread));
        const clamped = clampSwarm(next, floor, ceil);
        return integer ? Math.round(clamped) : clamped;
      };
      const mutateWeight = (value, spread, floor, ceil) => {
        const start = value !== undefined ? Number(value) : floor + (Math.random() * (ceil - floor));
        return clampSwarm(start + ((Math.random() - 0.5) * spread * Math.max(0.3, rate * 10)), floor, ceil);
      };
      const seedModules = Array.isArray(base.behaviorModules)
        ? base.behaviorModules
        : (Array.isArray(base.behavior_modules) ? base.behavior_modules : []);
      const baseModules = new Map(
        seedModules.map((module) => [module.type, {
          ...module,
          fastPeriod: module.fastPeriod ?? module.fast_period,
          slowPeriod: module.slowPeriod ?? module.slow_period,
          stayWeight: module.stayWeight ?? module.stay_weight,
          jumpWeight: module.jumpWeight ?? module.jump_weight,
        }]),
      );
      const baseEmaModule = baseModules.get("ema_cross_up") || baseModules.get("ema_cross_down") || {};
      const baseEmaPair = normalizeSwarmEmaPair({
        fastPeriod: base.emaFastPeriod ?? base.ema_fast_period ?? baseEmaModule.fastPeriod,
        slowPeriod: base.emaSlowPeriod ?? base.ema_slow_period ?? baseEmaModule.slowPeriod,
        period: base.emaPeriod ?? base.ema_period ?? baseEmaModule.period,
      });
      const hasEmaSeed = base.emaFastPeriod !== undefined
        || base.ema_fast_period !== undefined
        || base.emaSlowPeriod !== undefined
        || base.ema_slow_period !== undefined
        || base.emaPeriod !== undefined
        || base.ema_period !== undefined
        || baseEmaModule.fastPeriod !== undefined
        || baseEmaModule.slowPeriod !== undefined
        || baseEmaModule.period !== undefined;
      const emaFastPeriod = mutate(hasEmaSeed ? baseEmaPair.fastPeriod : undefined, 0.46, 5, 120, true);
      let emaSlowPeriod = mutate(hasEmaSeed ? baseEmaPair.slowPeriod : undefined, 0.42, 10, 240, true);
      if (emaFastPeriod >= emaSlowPeriod) {
        emaSlowPeriod = Math.round(clampSwarm(emaFastPeriod + 4, 10, 240));
      }
      const rsiPeriod = mutate(base.rsiPeriod ?? base.rsi_period ?? baseModules.get("rsi_low")?.period, 0.42, 6, 34, true);
      const rsiLow = mutate(base.rsiLow ?? base.rsi_low ?? baseModules.get("rsi_low")?.threshold, 0.18, 18, 48, true);
      const rsiHigh = mutate(base.rsiHigh ?? base.rsi_high ?? baseModules.get("rsi_high")?.threshold, 0.16, 58, 86, true);
      const genome = {
        dnaVersion: SWARM_DNA_SCHEMA_VERSION,
        emaFastPeriod,
        emaSlowPeriod,
        rsiPeriod,
        rsiLow,
        rsiHigh,
        spawnLimit: mutate(base.spawnLimit ?? base.spawn_limit, 0.38, 11800, 22000),
        mutationRate: mutate(base.mutationRate ?? base.mutation_rate ?? rate, 0.5, 0.008, 0.18),
        jumpCostSensitivity: mutate(base.jumpCostSensitivity ?? base.jump_cost_sensitivity, 0.5, 0.35, 2.2),
        explorationBias: mutate(base.explorationBias ?? base.exploration_bias, 0.65, 0.05, 1.4),
        metabolism: mutate(base.metabolism, 0.3, 0.45, 1.7),
        speed: mutate(base.speed, 0.28, 0.7, 1.8),
      };
      if (genome.rsiLow >= genome.rsiHigh) {
        genome.rsiLow = Math.max(18, genome.rsiHigh - 18);
      }
      genome.behaviorModules = [
        {
          type: "ema_cross_up",
          fastPeriod: genome.emaFastPeriod,
          slowPeriod: genome.emaSlowPeriod,
          stayWeight: mutateWeight(baseModules.get("ema_cross_up")?.stayWeight ?? -0.15, 0.35, -1.4, 1.4),
          jumpWeight: mutateWeight(baseModules.get("ema_cross_up")?.jumpWeight ?? 0.85, 0.45, -1.4, 1.8),
        },
        {
          type: "ema_cross_down",
          fastPeriod: genome.emaFastPeriod,
          slowPeriod: genome.emaSlowPeriod,
          stayWeight: mutateWeight(baseModules.get("ema_cross_down")?.stayWeight ?? -0.8, 0.45, -1.8, 1.4),
          jumpWeight: mutateWeight(baseModules.get("ema_cross_down")?.jumpWeight ?? 0.45, 0.4, -1.4, 1.8),
        },
        {
          type: "rsi_low",
          period: genome.rsiPeriod,
          threshold: genome.rsiLow,
          stayWeight: mutateWeight(baseModules.get("rsi_low")?.stayWeight ?? 0.35, 0.36, -1.4, 1.6),
          jumpWeight: mutateWeight(baseModules.get("rsi_low")?.jumpWeight ?? 0.22, 0.36, -1.4, 1.6),
        },
        {
          type: "rsi_high",
          period: genome.rsiPeriod,
          threshold: genome.rsiHigh,
          stayWeight: mutateWeight(baseModules.get("rsi_high")?.stayWeight ?? -0.35, 0.36, -1.6, 1.4),
          jumpWeight: mutateWeight(baseModules.get("rsi_high")?.jumpWeight ?? 0.42, 0.36, -1.4, 1.8),
        },
      ];
      return genome;
    }

    function spawnSwarmAgent(seedNode, generation = 1, genome = null, startingEnergy = SWARM_STARTING_ENERGY) {
      const node = seedNode || swarmNutrientNodes[0] || swarmVisibleNodes[0];
      if (!node) {
        return null;
      }
      const jitterX = (Math.random() - 0.5) * 18;
      const jitterY = (Math.random() - 0.5) * 18;
      return {
        id: `${node.ticker}-${generation}-${Math.random().toString(36).slice(2, 8)}`,
        row: Math.round(Number(node.row || 0)),
        col: Math.round(Number(node.col || 0)),
        x: Number(node.x || 0) + (jitterX * 0.12),
        y: Number(node.y || 0) + (jitterY * 0.12),
        sphereVector: node.sphereVector ? { ...node.sphereVector } : worldToSphereVector(node.x, node.y),
        vx: 0,
        vy: 0,
        energy: Math.max(250, Number(startingEnergy || SWARM_STARTING_ENERGY)),
        age: 0,
        generation,
        genome: createSwarmGenome(genome),
        targetTicker: node.ticker,
        currentTicker: node.ticker,
        memory: {},
        recentReturns: [],
        nextDecisionFrame: swarmFrameCounter + Math.floor(stableSwarmFraction(`${node.ticker}:${generation}:${Math.random()}`, "decision-offset") * 18),
      };
    }

    function getSwarmAgentRadius(agent, layout) {
      const wealthRatio = Math.max(0.03, Number(agent.energy || 0) / SWARM_STARTING_ENERGY);
      return clampSwarm(2.4 + (Math.sqrt(wealthRatio) * 2.2), 2.8, 7.5) * layout.detailScale;
    }

    function getSwarmTickerDrawRadius(node, layout) {
      const baseRadius = Number(node && (node.capRadius || node.radius) || 0);
      if (isSwarmDebugMode()) {
        return clampSwarm(baseRadius * 2.8 * layout.detailScale, 8.0, 48.0);
      }
      if (swarmZoomLevel <= 0.45) {
        return clampSwarm(baseRadius * 0.18, 2.2, 7.2);
      }
      return Math.max(5.5, baseRadius * layout.detailScale);
    }

    function getSwarmAgentHeading(agent) {
      const speed = Math.hypot(Number(agent.vx || 0), Number(agent.vy || 0));
      if (speed > 0.05) {
        return Math.atan2(Number(agent.vy || 0), Number(agent.vx || 0));
      }
      const target = agent.targetTicker ? swarmNodeMap.get(agent.targetTicker) : null;
      if (target) {
        const delta = getWrappedDelta(agent.x, agent.y, target.x, target.y);
        return Math.atan2(delta.dy, delta.dx);
      }
      return stableSwarmFraction(agent.id, "heading") * Math.PI * 2;
    }

    function rememberSwarmAgentReturn(agent, ticker, marketReturn) {
      if (!agent || !ticker) {
        return;
      }
      const memory = agent.memory || {};
      const entry = memory[ticker] || {
        visits: 0,
        totalReturn: 0,
        bestReturn: Number.NEGATIVE_INFINITY,
        worstReturn: Number.POSITIVE_INFINITY,
      };
      entry.visits += 1;
      entry.totalReturn += marketReturn;
      entry.bestReturn = Math.max(entry.bestReturn, marketReturn);
      entry.worstReturn = Math.min(entry.worstReturn, marketReturn);
      memory[ticker] = entry;
      agent.memory = memory;
      agent.recentReturns = [...(agent.recentReturns || []), marketReturn].slice(-Math.max(3, Number(agent.genome.rsiPeriod || 14)));
    }

    function getSwarmBehaviorScore(agent, node, action) {
      const genome = agent.genome || {};
      const modules = Array.isArray(genome.behaviorModules) ? genome.behaviorModules : [];
      return modules.reduce((sum, module) => {
        if (!getSwarmNodeSignal(node.ticker, module)) {
          return sum;
        }
        const weightKey = action === "stay" ? "stayWeight" : "jumpWeight";
        return sum + Number(module[weightKey] || 0);
      }, 0);
    }

    function getAgentNodeScore(agent, node, jumpDistance = 0, action = "jump") {
      if (!node) {
        return Number.NEGATIVE_INFINITY;
      }
      const genome = agent.genome || {};
      const learned = (agent.memory || {})[node.ticker];
      const avgReturn = learned ? learned.totalReturn / Math.max(1, learned.visits) : 0;
      const bestReturn = learned ? learned.bestReturn : 0;
      const worstReturn = learned ? learned.worstReturn : 0;
      const visits = learned ? learned.visits : 0;
      const behaviorScore = getSwarmBehaviorScore(agent, node, action);
      const currentEnergy = Number(agent.energy || SWARM_STARTING_ENERGY);
      const profitProtection = action === "jump" && currentEnergy > SWARM_STARTING_ENERGY
        ? Math.log10(Math.max(10, currentEnergy / SWARM_STARTING_ENERGY)) * Number(genome.jumpCostSensitivity || 1)
        : 0;
      const novelty = visits === 0 ? Number(genome.explorationBias || 0.2) : 1 / Math.sqrt(visits + 1);
      const exploration = (stableSwarmFraction(`${agent.id}:${node.ticker}`, String(swarmTimelineIndex)) - 0.5)
        * Number(genome.explorationBias || 0.2);
      const cost = action === "jump"
        ? Number(genome.jumpCostSensitivity || 1) * swarmJumpCostMultiplier * (0.12 + (jumpDistance * 0.32))
        : 0;
      const stayBias = action === "stay" ? 0.45 : 0;
      return (avgReturn * 170) + (bestReturn * 28) + (worstReturn * 16) + (behaviorScore * 1.55) + profitProtection + novelty + exploration + stayBias - cost;
    }

    function getSwarmGlobalCandidateNodes(agent, current = null) {
      const nodes = swarmVisibleNodes.length > 0 ? swarmVisibleNodes : swarmNutrientNodes;
      if (current && !nodes.some((node) => node.ticker === current.ticker)) {
        return [current, ...nodes];
      }
      return nodes;
    }

    function getGlobalJumpDistance(agent, node) {
      if (!agent || !node) {
        return 0;
      }
      const current = agent.sphereVector || worldToSphereVector(agent.x, agent.y);
      const target = node.sphereVector || worldToSphereVector(node.x, node.y);
      const dot = clampSwarm((current.x * target.x) + (current.y * target.y) + (current.z * target.z), -1, 1);
      return Math.acos(dot) / Math.PI;
    }

    function pickSwarmFoodNode(agent) {
      if (!swarmVisibleNodes.length) {
        return null;
      }

      const current = getSwarmNodeAtGrid(agent.row, agent.col) || (agent.targetTicker ? swarmNodeMap.get(agent.targetTicker) : null);
      const pool = getSwarmGlobalCandidateNodes(agent, current);

      const stayScore = getAgentNodeScore(agent, current, 0, "stay");
      let bestNode = current;
      let bestScore = stayScore;

      pool.forEach((node) => {
        const dist = getGlobalJumpDistance(agent, node);
        const action = current && node.ticker === current.ticker ? "stay" : "jump";
        const score = getAgentNodeScore(agent, node, dist, action);
        if (score > bestScore + 0.2) {
          bestScore = score;
          bestNode = node;
        }
      });

      return bestNode || pool[0] || current;
    }

    function renderSwarmStaticLayer() {
      const layout = getSwarmCanvasLayout();
      if (!layout) {
        return;
      }

      if (!swarmStaticLayer) {
        swarmStaticLayer = document.createElement("canvas");
      }
      swarmStaticLayer.width = layout.canvas.width;
      swarmStaticLayer.height = layout.canvas.height;
      const ctx = swarmStaticLayer.getContext("2d");
      ctx.setTransform(layout.dpr, 0, 0, layout.dpr, 0, 0);
      ctx.clearRect(0, 0, layout.width, layout.height);

      const bg = ctx.createLinearGradient(0, 0, layout.width, layout.height);
      bg.addColorStop(0, "#020617");
      bg.addColorStop(0.5, "#0f172a");
      bg.addColorStop(1, "#111827");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, layout.width, layout.height);

      ctx.fillStyle = "rgba(15, 23, 42, 0.72)";
      ctx.fillRect(layout.offsetX, layout.offsetY, layout.worldWidth * layout.scale, layout.worldHeight * layout.scale);
      ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
      ctx.lineWidth = 1;
      if (isSwarmPlaneMode()) {
        const planeGlow = ctx.createRadialGradient(layout.width / 2, layout.height / 2, 30, layout.width / 2, layout.height / 2, layout.sphereRadius * 0.9);
        planeGlow.addColorStop(0, "rgba(59, 130, 246, 0.16)");
        planeGlow.addColorStop(0.6, "rgba(15, 23, 42, 0.12)");
        planeGlow.addColorStop(1, "rgba(2, 6, 23, 0.0)");
        ctx.fillStyle = planeGlow;
        ctx.fillRect(layout.offsetX, layout.offsetY, layout.worldWidth * layout.scale, layout.worldHeight * layout.scale);
        ctx.strokeStyle = "rgba(59, 130, 246, 0.42)";
        ctx.lineWidth = 1.4;
        ctx.strokeRect(layout.offsetX, layout.offsetY, layout.worldWidth * layout.scale, layout.worldHeight * layout.scale);
      } else if (isSwarmDebugMode()) {
        const cx = layout.width / 2;
        const cy = layout.height / 2;
        const gradient = ctx.createRadialGradient(
          cx - layout.sphereRadius * 0.28,
          cy - layout.sphereRadius * 0.30,
          layout.sphereRadius * 0.08,
          cx,
          cy,
          layout.sphereRadius,
        );
        gradient.addColorStop(0, "rgba(248, 250, 252, 0.96)");
        gradient.addColorStop(0.56, "rgba(226, 232, 240, 0.66)");
        gradient.addColorStop(1, "rgba(148, 163, 184, 0.22)");
        ctx.beginPath();
        ctx.arc(cx, cy, layout.sphereRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
        drawSwarmDebugSphereGraticule(ctx, layout);
        ctx.strokeStyle = "rgba(241, 245, 249, 0.90)";
        ctx.lineWidth = 2.6;
        ctx.stroke();
      } else if (swarmZoomLevel <= 0.45) {
        const cx = layout.width / 2;
        const cy = layout.height / 2;
        const gradient = ctx.createRadialGradient(cx - layout.sphereRadius * 0.32, cy - layout.sphereRadius * 0.34, layout.sphereRadius * 0.05, cx, cy, layout.sphereRadius);
        gradient.addColorStop(0, "rgba(30, 41, 59, 0.96)");
        gradient.addColorStop(0.72, "rgba(15, 23, 42, 0.92)");
        gradient.addColorStop(1, "rgba(2, 6, 23, 0.98)");
        ctx.beginPath();
        ctx.arc(cx, cy, layout.sphereRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
        ctx.strokeStyle = "rgba(148, 163, 184, 0.45)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        ctx.strokeRect(layout.offsetX, layout.offsetY, layout.worldWidth * layout.scale, layout.worldHeight * layout.scale);
      }

      const gridMeta = getSwarmGridMeta();
      const maxGridLines = 140;
      const colStep = Math.max(1, Math.ceil(gridMeta.columns / maxGridLines));
      const rowStep = Math.max(1, Math.ceil(gridMeta.rows / maxGridLines));
      if (!isSwarmPlaneMode() && swarmZoomLevel > 0.45) {
        for (let col = colStep; col < gridMeta.columns; col += colStep) {
          const x = layout.offsetX + (col * gridMeta.cellWidth * layout.scale);
          ctx.strokeStyle = "rgba(148, 163, 184, 0.08)";
          ctx.beginPath();
          ctx.moveTo(x, layout.offsetY);
          ctx.lineTo(x, layout.offsetY + (layout.worldHeight * layout.scale));
          ctx.stroke();
        }
        for (let row = rowStep; row < gridMeta.rows; row += rowStep) {
          const y = layout.offsetY + (row * gridMeta.cellHeight * layout.scale);
          ctx.strokeStyle = "rgba(148, 163, 184, 0.08)";
          ctx.beginPath();
          ctx.moveTo(layout.offsetX, y);
          ctx.lineTo(layout.offsetX + (layout.worldWidth * layout.scale), y);
          ctx.stroke();
        }
      }

      ctx.fillStyle = "rgba(226, 232, 240, 0.72)";
      ctx.font = "11px sans-serif";
      ctx.fillText(
        isSwarmDebugMode()
          ? `${gridMeta.columns} x ${gridMeta.rows} debug sphere`
          : swarmZoomLevel <= 0.45
          ? `${gridMeta.columns} x ${gridMeta.rows} cells on charged sphere`
          : `${gridMeta.columns} x ${gridMeta.rows} charged sphere projection`,
        layout.offsetX + 6,
        layout.offsetY + 16,
      );
      updateSwarmWorldVisibilityIndicator(getSwarmWorldFitDistance() / Math.max(0.35, swarmZoomLevel));
    }

    function drawSwarmScene() {
      if (isSwarmDebugMode() && swarmTrails.length) {
        swarmTrails = [];
      }
      if (renderSwarmThreeScene()) {
        return;
      }
      setSwarmRenderPath("canvas", {
        reason: "draw-fallback",
        debugMode: isSwarmDebugMode(),
      });
      const layout = getSwarmCanvasLayout();
      if (!layout) {
        console.warn("[SWARM] Canvas draw skipped; layout unavailable");
        return;
      }
      updateSwarmCameraVector();
      const ctx = layout.canvas.getContext("2d");
      ctx.setTransform(layout.dpr, 0, 0, layout.dpr, 0, 0);
      ctx.clearRect(0, 0, layout.width, layout.height);

      if (swarmStaticLayer) {
        ctx.drawImage(swarmStaticLayer, 0, 0, layout.width, layout.height);
      }

      if (!isSwarmDebugMode()) {
        swarmTrails.forEach((trail) => {
          const a = worldToCanvas(layout, trail.x1, trail.y1);
          const b = worldToCanvas(layout, trail.x2, trail.y2);
          if (!a.visible || !b.visible) {
            return;
          }
          ctx.strokeStyle = `rgba(129, 140, 248, ${Math.max(0.05, trail.life / 40)})`;
          ctx.lineWidth = Math.max(0.7, trail.width * layout.scale);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        });
      }

      const drawHighlight = (node, stroke, fill, fillAlpha = 0.14) => {
        if (!node) {
          return;
        }
        const point = worldToCanvas(layout, node.x, node.y);
        if (!point.visible) {
          return;
        }
      const radius = getSwarmTickerDrawRadius(node, layout);
        ctx.beginPath();
        ctx.fillStyle = fill;
        ctx.globalAlpha = fillAlpha;
        ctx.arc(point.x, point.y, radius + 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 2;
        ctx.arc(point.x, point.y, radius + 3, 0, Math.PI * 2);
        ctx.stroke();
      };

      const hoverNode = swarmHoveredTicker ? swarmNodeMap.get(swarmHoveredTicker) : null;
      const selectedNode = swarmSelectedTicker ? swarmNodeMap.get(swarmSelectedTicker) : null;
      const selectedAgent = swarmSelectedAgentId
        ? swarmAgents.find((agent) => agent.id === swarmSelectedAgentId)
        : null;

      swarmVisibleNodes.forEach((node) => {
        const point = worldToCanvas(layout, node.x, node.y);
        if (!point.visible) {
          return;
        }
        const radius = getSwarmTickerDrawRadius(node, layout);
        ctx.beginPath();
        const wealthRatio = clampSwarm(Number(node.simEnergy || SWARM_STARTING_ENERGY) / SWARM_STARTING_ENERGY, 0.05, 12);
        ctx.fillStyle = "#f8fafc";
        ctx.globalAlpha = clampSwarm(0.58 + (Math.log10(Math.max(1, wealthRatio)) * 0.12), 0.46, 0.86) * (point.backSide ? 0.38 : 1);
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = point.backSide ? 0.20 : 0.82;
        const borderColor = node.label === "Buy"
          ? "rgba(34, 211, 238, 0.95)"
          : node.label === "Skip"
            ? "rgba(244, 114, 182, 0.95)"
            : "rgba(96, 165, 250, 0.95)";
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = Math.max(0.7, layout.detailScale * 0.8);
        ctx.stroke();
        ctx.globalAlpha = 1;
      });

      drawHighlight(hoverNode, "rgba(191, 219, 254, 1)", "#bfdbfe");
      drawHighlight(selectedNode, "rgba(250, 204, 21, 1)", "#fde68a", 0.18);

      if (!isSwarmDebugMode()) {
        swarmAgents.forEach((agent) => {
          const point = worldToCanvas(layout, agent.x, agent.y);
          if (!point.visible) {
            return;
          }
        const radius = getSwarmAgentRadius(agent, layout);
        const heading = getSwarmAgentHeading(agent);
        const selected = selectedAgent && selectedAgent.id === agent.id;
        const wealthRatio = clampSwarm(Number(agent.energy || 0) / SWARM_STARTING_ENERGY, 0, 2.4);
        const spikeCount = swarmZoomLevel <= 0.45 ? 5 : 8;
        if (isSwarmDebugMode()) {
          ctx.beginPath();
          ctx.fillStyle = "rgba(15, 23, 42, 0.28)";
          ctx.arc(point.x + 1.6, point.y + 2.1, radius * 1.04, 0, Math.PI * 2);
          ctx.fill();

          const capGradient = ctx.createRadialGradient(
            point.x - (radius * 0.25),
            point.y - (radius * 0.28),
            Math.max(1, radius * 0.12),
            point.x,
            point.y,
            radius * 1.08,
          );
          capGradient.addColorStop(0, "rgba(250, 250, 250, 0.98)");
          capGradient.addColorStop(0.58, wealthRatio >= 1 ? "rgba(226, 232, 240, 0.94)" : "rgba(216, 180, 254, 0.92)");
          capGradient.addColorStop(1, wealthRatio >= 1 ? "rgba(148, 163, 184, 0.88)" : "rgba(168, 85, 247, 0.88)");
          ctx.beginPath();
          ctx.arc(point.x, point.y, radius * 1.08, 0, Math.PI * 2);
          ctx.fillStyle = capGradient;
          ctx.fill();
          ctx.strokeStyle = selected ? "rgba(250, 204, 21, 1)" : "rgba(241, 245, 249, 0.92)";
          ctx.lineWidth = selected ? 2.0 : 1.2;
          ctx.stroke();
        } else {
          ctx.beginPath();
          for (let idx = 0; idx < spikeCount * 2; idx += 1) {
            const angle = heading + (idx / (spikeCount * 2)) * Math.PI * 2;
            const spikeRadius = radius * (idx % 2 === 0 ? 1.45 : 0.82);
            const px = point.x + Math.cos(angle) * spikeRadius;
            const py = point.y + Math.sin(angle) * spikeRadius;
            if (idx === 0) {
              ctx.moveTo(px, py);
            } else {
              ctx.lineTo(px, py);
            }
          }
          ctx.closePath();
          ctx.fillStyle = wealthRatio >= 1 ? "rgba(248, 250, 252, 0.90)" : "rgba(196, 181, 253, 0.88)";
          ctx.fill();
          ctx.beginPath();
          ctx.arc(point.x, point.y, radius * 0.72, 0, Math.PI * 2);
          ctx.fillStyle = wealthRatio >= 1 ? "rgba(34, 197, 94, 0.42)" : "rgba(167, 139, 250, 0.46)";
          ctx.fill();
          ctx.strokeStyle = selected ? "rgba(250, 204, 21, 1)" : "rgba(15, 23, 42, 0.96)";
          ctx.lineWidth = selected ? 2.1 : 1.0;
          ctx.stroke();
        }

        const barWidth = radius * 1.8;
        const barX = point.x - (barWidth / 2);
        const barY = point.y + radius + 2;
        ctx.fillStyle = "rgba(15, 23, 42, 0.78)";
        ctx.fillRect(barX, barY, barWidth, 2.6);
        ctx.fillStyle = wealthRatio >= 1 ? "rgba(34, 197, 94, 0.95)" : "rgba(251, 113, 133, 0.95)";
          ctx.fillRect(barX, barY, barWidth * clampSwarm(wealthRatio / 2, 0.08, 1), 2.6);
        });
      }
    }

    function resetSwarmSimulation() {
      refreshSwarmDerivedState();
      swarmPlaying = false;
      swarmTimelineIndex = 0;
      swarmPlaybackAccumulator = 0;
      swarmBirthCount = 0;
      swarmDeathCount = 0;
      swarmGenerationMax = 1;
      swarmTrails = [];
      swarmAgents = [];
      swarmCompletedAgents = [];
      swarmTopAgentSnapshots = [];
      swarmSelectedAgentId = null;
      swarmDnaSaveInFlight = false;
      swarmDnaLastSavedSignature = "";
      setSwarmDnaSaveStatus("Autosaves to config", "muted");
      resetSwarmNodeEnergy();
      updateFixedSwarmNodeWorth();

      if (!swarmVisibleNodes.length) {
        updateSwarmSummary();
        drawSwarmScene();
        return;
      }

      const seedNodes = swarmVisibleNodes.filter((node) => ((Math.round(Number(node.row || 0)) + Math.round(Number(node.col || 0))) % 2) === 0);
      const agentCount = Math.min(getSwarmEffectiveAgentCap(), Math.max(1, seedNodes.length * swarmAgentsPerNode));
      for (let idx = 0; idx < agentCount; idx += 1) {
        const seed = seedNodes.length
          ? seedNodes[Math.floor(stableSwarmFraction(`${idx}:${swarmFrameCounter}`, "agent-seed") * seedNodes.length) % seedNodes.length]
          : swarmVisibleNodes[idx % swarmVisibleNodes.length];
        const agent = spawnSwarmAgent(seed, 1);
        if (agent) {
          swarmAgents.push(agent);
        }
      }

      updateSwarmSummary();
      updateSwarmPanels();
      updateSwarmJumpCostControl();
      updateSwarmGridControls();
      renderSwarmTopAgents(true);
      ensureSwarmThreeScene();
      drawSwarmScene();
    }

    function setSwarmFilter(label) {
      swarmFilter = label;
      updateSwarmFilterButtons();
      swarmHoveredTicker = null;
      swarmSelectedAgentId = null;
      if (swarmSelectedTicker && !swarmNodes.some((node) => node.ticker === swarmSelectedTicker && (label === "All" || node.label === label))) {
        swarmSelectedTicker = null;
      }
      refreshSwarmDerivedState();
      updateSwarmPanels();
      resetSwarmSimulation();
    }

    function ensureSwarmAnimationLoop() {
      if (!swarmAnimationHandle && !document.getElementById("tab-swarm").classList.contains("hidden")) {
        swarmLastFrameTime = null;
        swarmAnimationHandle = requestAnimationFrame(runSwarmFrame);
      }
    }

    async function startSwarmPlayback() {
      if (swarmLoadingPromise) {
        await swarmLoadingPromise;
      }
      if (!swarmLoaded) {
        await loadSwarmWorld();
      }
      if (!swarmVisibleNodes.length) {
        updateSwarmPanels();
        drawSwarmScene();
        return;
      }
      if (!swarmAgents.length || swarmTimelineIndex >= swarmTimelineMax) {
        resetSwarmSimulation();
      }
      swarmPlaying = true;
      swarmPlaybackAccumulator = 0;
      updateSwarmTimelineControls();
      ensureSwarmAnimationLoop();
    }

    async function toggleSwarmPlayback() {
      if (swarmPlaying) {
        swarmPlaying = false;
        swarmLastFrameTime = null;
        updateSwarmTimelineControls();
        drawSwarmScene();
        return;
      }
      await startSwarmPlayback();
    }

    function stopSwarmPlayback() {
      swarmPlaying = false;
      swarmLastFrameTime = null;
      swarmPlaybackAccumulator = 0;
      updateSwarmTimelineControls();
      drawSwarmScene();
    }

    function openSelectedSwarmTicker() {
      if (!swarmSelectedTicker) {
        return;
      }
      showTab("screener");
      loadChart(swarmSelectedTicker);
    }

    function stepSwarmSimulation(dt) {
      if (isSwarmDebugMode() && swarmTrails.length) {
        swarmTrails = [];
      }
      if (!swarmVisibleNodes.length || !swarmAgents.length) {
        if (swarmCompletedAgents.length) {
          swarmPlaying = false;
          renderSwarmTopAgents();
        }
        updateSwarmSummary();
        return;
      }

      if (swarmTimelineIndex >= swarmTimelineMax) {
        swarmPlaying = false;
        renderSwarmTopAgents();
        updateSwarmSummary();
        return;
      }

      const timeScale = Math.max(0.5, Math.min(2.2, dt / 16.666));
      swarmFrameCounter += 1;
      swarmPlaybackAccumulator += dt;
      let advancedTimeline = false;

      swarmTrails = swarmTrails
        .map((trail) => ({ ...trail, life: trail.life - (0.9 * timeScale) }))
        .filter((trail) => trail.life > 0);

      while (swarmPlaybackAccumulator >= 240) {
        swarmPlaybackAccumulator -= 240;
        advanceSwarmTimeline(1, { fromPlayback: true });
        advancedTimeline = true;
      }
      updateFixedSwarmNodeWorth();

      swarmAgents.forEach((agent) => {
        agent.age += timeScale;

        if (!agent.targetTicker || !swarmNodeMap.has(agent.targetTicker) || swarmFrameCounter >= Number(agent.nextDecisionFrame || 0)) {
          agent.nextDecisionFrame = swarmFrameCounter + Math.round(clampSwarm(14 / Math.max(0.5, Number(agent.genome.speed || 1)), 8, 28));
          const previousTarget = getSwarmNodeAtGrid(agent.row, agent.col) || (agent.targetTicker ? swarmNodeMap.get(agent.targetTicker) : null);
          const nextTarget = pickSwarmFoodNode(agent);
          if (previousTarget && nextTarget && previousTarget.ticker !== nextTarget.ticker) {
            const jumpDistance = getGlobalJumpDistance(agent, nextTarget);
            agent.energy -= (1 + (jumpDistance * 10)) * 8 * Number(agent.genome.jumpCostSensitivity || 1) * swarmJumpCostMultiplier;
          }
          agent.targetTicker = nextTarget ? nextTarget.ticker : null;
          agent.currentTicker = nextTarget ? nextTarget.ticker : null;
          if (nextTarget) {
            const prevX = agent.x;
            const prevY = agent.y;
            agent.row = Math.round(Number(nextTarget.row || 0));
            agent.col = Math.round(Number(nextTarget.col || 0));
            agent.x = Number(nextTarget.x || 0);
            agent.y = Number(nextTarget.y || 0);
            agent.sphereVector = nextTarget.sphereVector ? { ...nextTarget.sphereVector } : worldToSphereVector(agent.x, agent.y);
            agent.vx = agent.x - prevX;
            agent.vy = agent.y - prevY;
            if (!isSwarmDebugMode() && swarmTrails.length < SWARM_MAX_TRAILS && previousTarget && previousTarget.ticker !== nextTarget.ticker) {
              swarmTrails.push({
                x1: prevX,
                y1: prevY,
                x2: agent.x,
                y2: agent.y,
                width: 1.1 + (Math.log10(Math.max(10, agent.energy)) / 3),
                life: 40,
              });
            }
          }
        }

        const target = getSwarmNodeAtGrid(agent.row, agent.col) || (agent.targetTicker ? swarmNodeMap.get(agent.targetTicker) : null);
        if (target && advancedTimeline) {
          const marketReturn = getSwarmNodeReturn(target);
          rememberSwarmAgentReturn(agent, target.ticker, marketReturn);
          agent.energy *= (1 + marketReturn);
        }

        agent.energy -= (1.8 * Number(agent.genome.metabolism || 1)) * timeScale;
        agent.vx *= 0.5;
        agent.vy *= 0.5;
      });

      if (swarmAgents.length < getSwarmEffectiveAgentCap()) {
        const parent = swarmAgents.find((agent) => agent.energy > Number(agent.genome.spawnLimit || 15000));
        if (parent) {
          const parentEnergyBeforeSpawn = Number(parent.energy || 0);
          const spawnLimit = Number(parent.genome.spawnLimit || 15000);
          const surplus = Math.max(0, parentEnergyBeforeSpawn - spawnLimit);
          parent.energy = parentEnergyBeforeSpawn * 0.5;
          const childHeadStart = clampSwarm(
            SWARM_STARTING_ENERGY + (surplus * 0.35) + (parent.energy > spawnLimit ? parent.energy - spawnLimit : 0) * 0.15,
            SWARM_STARTING_ENERGY,
            parentEnergyBeforeSpawn * 0.72,
          );
          const child = spawnSwarmAgent(
            swarmNodeMap.get(parent.targetTicker) || swarmNutrientNodes[0] || swarmVisibleNodes[0],
            parent.generation + 1,
            parent.genome,
            childHeadStart,
          );
          if (child) {
            swarmBirthCount += 1;
            swarmGenerationMax = Math.max(swarmGenerationMax, child.generation);
            swarmAgents.push(child);
          }
        }
      }

      swarmAgents = swarmAgents.filter((agent) => {
        if (agent.energy > 0) {
          return true;
        }
        swarmDeathCount += 1;
        swarmCompletedAgents.push(snapshotSwarmAgent(agent));
        if (swarmSelectedAgentId === agent.id) {
          swarmSelectedAgentId = null;
        }
        return false;
      });

      if (swarmTimelineIndex >= swarmTimelineMax) {
        swarmPlaying = false;
        swarmCompletedAgents.push(...swarmAgents.map(snapshotSwarmAgent));
        swarmAgents = [];
        swarmSelectedAgentId = null;
        renderSwarmTopAgents();
      }

      updateSwarmSummary();
      updateSwarmPanels();
    }

    function runSwarmFrame(timestamp) {
      swarmAnimationHandle = null;
      if (swarmLastFrameTime === null) {
        swarmLastFrameTime = timestamp;
      }
      const dt = timestamp - swarmLastFrameTime;
      swarmLastFrameTime = timestamp;

      if (swarmPlaying) {
        stepSwarmSimulation(dt);
      }
      drawSwarmScene();

      if (!document.getElementById("tab-swarm").classList.contains("hidden")) {
        swarmAnimationHandle = requestAnimationFrame(runSwarmFrame);
      }
    }

    async function loadSwarmHistory() {
      swarmHistoryByTicker = new Map();
      swarmHistoryMeta = null;
      refreshSwarmTimelineMax();

      try {
        const scopeQuery = getSwarmScopeQueryParams();
        const resp = await fetch(`/api/swarm-history?days=${SWARM_HISTORY_DAYS}&limit=${SWARM_HISTORY_LIMIT}${scopeQuery ? `&${scopeQuery}` : ""}`);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Swarm history request failed");
        }

        const history = data.history || {};
        Object.entries(history).forEach(([ticker, payload]) => {
          const normalized = normalizeSwarmHistoryPayload(payload);
          if (normalized.closes.length >= 2) {
            swarmHistoryByTicker.set(String(ticker).toUpperCase(), normalized);
          }
        });
        swarmHistoryMeta = data;
        refreshSwarmTimelineMax();
      } catch (err) {
        console.warn("Swarm history unavailable; agent behavior will use neutral returns.", err);
        swarmHistoryByTicker = new Map();
        swarmHistoryMeta = { count: 0, error: String(err && err.message ? err.message : err) };
        refreshSwarmTimelineMax();
      }
    }

    async function loadSwarmWorld(forceRefresh = false) {
      if (swarmLoadingPromise) {
        return swarmLoadingPromise;
      }
      const status = document.getElementById("swarm-status");
      const refreshBtn = document.getElementById("swarm-refresh-btn");
      const countEl = document.getElementById("swarm-count");
      const asOfEl = document.getElementById("swarm-as-of");
      const content = document.getElementById("swarm-content");
      const empty = document.getElementById("swarm-empty");
      const scope = normalizeScanScope(tickerScanScope);
      swarmDebugSphereRadius = null;

      const backbone = await ensureGuiMarketBackbone();
      const shouldRefreshWorld = forceRefresh || Boolean(backbone && backbone.refreshed);

      if (swarmLoaded && !shouldRefreshWorld) {
        stopSwarmLoadProgress();
        ensureSwarmThreeScene();
        drawSwarmScene();
        return;
      }

      const loadTask = (async () => {
      startSwarmLoadProgress(
        "Swarm",
        shouldRefreshWorld ? "Refreshing production world..." : "Loading cached production world...",
      );
      setSwarmEmptyState(
        shouldRefreshWorld ? "Refreshing production swarm..." : "Loading cached production swarm...",
      );
      if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.textContent = shouldRefreshWorld ? "Refreshing..." : "Loading...";
      }
      if (status) {
        status.className = "text-xs font-bold uppercase tracking-wide text-violet-600";
        status.textContent = shouldRefreshWorld
          ? "Rebuilding production swarm world..."
          : "Loading cached production swarm world...";
      }

      try {
        const scopeQuery = getSwarmScopeQueryParams();
        const resp = await fetch(`/api/swarm-world?limit=5000${shouldRefreshWorld ? "&refresh=true" : ""}${scopeQuery ? `&${scopeQuery}` : ""}`);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Swarm world request failed");
        }

        setSwarmLoadProgress({
          show: true,
          label: "Swarm",
          text: "Loading world...",
          pct: 96,
          working: true,
        });
        swarmWorld = data;
        swarmRealNodes = normalizeSwarmSphereNodes(Array.isArray(data.nodes) ? data.nodes : []);
        swarmNodes = swarmRealNodes;
        swarmLoaded = true;
        swarmHoveredTicker = null;
        if (swarmSelectedTicker && !swarmNodes.some((node) => node.ticker === swarmSelectedTicker)) {
          swarmSelectedTicker = null;
        }
        swarmSelectedAgentId = null;
        swarmAgents = [];
        swarmCompletedAgents = [];
        swarmTopAgentSnapshots = [];
        swarmHistoryByTicker = new Map();
        swarmHistoryMeta = null;
        swarmTimelineIndex = 0;
        swarmTimelineMax = 0;
        swarmPlaying = false;
        swarmPlaybackAccumulator = 0;
        swarmBirthCount = 0;
        swarmDeathCount = 0;
        swarmGenerationMax = 1;

        if (countEl) countEl.textContent = `${Number(data.count || 0)} assets`;
        if (asOfEl) asOfEl.textContent = data.as_of_date || "-";
        if (status) {
          status.className = "text-xs font-bold uppercase tracking-wide text-emerald-600";
          status.textContent = `Swarm sphere ready · ${Number(data.count || 0)} assets · ${normalizeScanScope(tickerScanScope)} scope · data as of ${data.as_of_date || "unknown"}`;
        }
        if (empty) empty.classList.add("hidden");
        if (content) content.classList.remove("hidden");

        refreshSwarmDerivedState();
        ensureSwarmThreeScene();
        drawSwarmScene();
        updateSwarmPanels();
        setSwarmLoadProgress({
          show: true,
          label: "Swarm",
          text: "100%",
          pct: 100,
          working: false,
        });
        setTimeout(() => stopSwarmLoadProgress(), 180);
        if (status) {
          status.className = "text-xs font-bold uppercase tracking-wide text-emerald-600";
          status.textContent = `Swarm sphere ready · ${Number(data.count || 0)} assets · ${normalizeScanScope(tickerScanScope)} scope · data as of ${data.as_of_date || "unknown"}`;
        }
        updateSwarmFilterButtons();
        updateSwarmSummary();
      } catch (err) {
        stopSwarmLoadProgress();
        setSwarmEmptyState(`Swarm world error: ${err.message || err}`);
        if (status) {
          status.className = "text-xs font-bold uppercase tracking-wide text-rose-600";
          status.textContent = "Swarm world load failed";
        }
      } finally {
        clearSwarmLoadProgressTimer();
        if (refreshBtn) {
          refreshBtn.disabled = false;
          refreshBtn.textContent = "Refresh World";
        }
        swarmLoadingPromise = null;
        updateSwarmTimelineControls();
      }
      })();

      swarmLoadingPromise = loadTask;
      updateSwarmTimelineControls();
      return loadTask;
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
      } else if (tab === "swarm") {
        context.textContent = "Swarm: production asset explorer";
      } else if (tab === "swarm-lab") {
        context.textContent = "Swarm Lab: tune the abstract model";
      } else if (tab === "backtest") {
        context.textContent = "Backtester: choose what to evaluate below";
      } else {
        context.textContent = "Screener controls: pick a strategy, then click Run Screener";
      }
    }

    function getSwarmLabCanvas() {
      return document.getElementById("swarm-lab-canvas");
    }

    function getSwarmLabCanvasLayout(canvas = getSwarmLabCanvas()) {
      if (!canvas) {
        return null;
      }
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(1, rect.width);
      const height = Math.max(1, rect.height);
      if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
      }
      return {
        canvas,
        rect,
        dpr,
        width,
        height,
        scale: Math.min(width / 1600, height / 900) * swarmLabZoom,
        worldWidth: 1600,
        worldHeight: 900,
      };
    }

    function getSwarmLabWorldCenter(layout) {
      return {
        x: layout.width / 2,
        y: layout.height / 2,
      };
    }

    function getSwarmLabGlobeRadius(layout) {
      return Math.min(layout.width, layout.height) * 0.46 * swarmLabZoom;
    }

    const swarmLabSurfaceYaw = -0.95;
    const swarmLabSurfacePitch = 0.52;

    function projectSwarmLabSurfacePoint(layout, x, y) {
      const center = getSwarmLabWorldCenter(layout);
      const radius = getSwarmLabGlobeRadius(layout);
      const lon = ((Number(x || 0) / 1600) - 0.5) * Math.PI * 2;
      const lat = (0.5 - (Number(y || 0) / 900)) * Math.PI * 0.88;
      const cosLat = Math.cos(lat);
      const sinLat = Math.sin(lat);
      const cosLon = Math.cos(lon);
      const sinLon = Math.sin(lon);
      const vx = cosLat * sinLon;
      const vy = sinLat;
      const vz = cosLat * cosLon;

      const cosYaw = Math.cos(swarmLabSurfaceYaw);
      const sinYaw = Math.sin(swarmLabSurfaceYaw);
      const xYaw = (vx * cosYaw) + (vz * sinYaw);
      const zYaw = (-vx * sinYaw) + (vz * cosYaw);

      const cosPitch = Math.cos(swarmLabSurfacePitch);
      const sinPitch = Math.sin(swarmLabSurfacePitch);
      const yPitch = (vy * cosPitch) - (zYaw * sinPitch);
      const zPitch = (vy * sinPitch) + (zYaw * cosPitch);

      return {
        x: center.x + (xYaw * radius * 0.94),
        y: center.y - (yPitch * radius * 0.76),
        z: zPitch,
      };
    }

    function drawSwarmLabGlobeBackdrop(ctx, layout) {
      const center = getSwarmLabWorldCenter(layout);
      const radius = getSwarmLabGlobeRadius(layout);
      const horizonY = center.y - (radius * 0.10);
      const glow = ctx.createRadialGradient(
        center.x - radius * 0.14,
        center.y - radius * 0.18,
        radius * 0.04,
        center.x,
        center.y,
        radius * 1.15,
      );
      glow.addColorStop(0, "rgba(125, 211, 252, 0.34)");
      glow.addColorStop(0.34, "rgba(129, 140, 248, 0.18)");
      glow.addColorStop(1, "rgba(15, 23, 42, 0)");
      const rim = ctx.createLinearGradient(center.x - radius, center.y - radius, center.x + radius, center.y + radius);
      rim.addColorStop(0, "rgba(191, 219, 254, 0.98)");
      rim.addColorStop(0.35, "rgba(125, 211, 252, 0.92)");
      rim.addColorStop(0.62, "rgba(129, 140, 248, 0.88)");
      rim.addColorStop(1, "rgba(34, 211, 238, 0.94)");
      const sphereFill = ctx.createRadialGradient(
        center.x - radius * 0.25,
        center.y - radius * 0.28,
        radius * 0.08,
        center.x,
        center.y,
        radius * 1.02,
      );
      sphereFill.addColorStop(0, "rgba(15, 23, 42, 0.96)");
      sphereFill.addColorStop(0.45, "rgba(15, 23, 42, 0.72)");
      sphereFill.addColorStop(1, "rgba(8, 15, 32, 0.98)");

      ctx.save();
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "screen";
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(center.x, center.y, radius * 1.08, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalCompositeOperation = "source-over";

      ctx.beginPath();
      ctx.arc(center.x, center.y, radius * 0.995, 0, Math.PI * 2);
      ctx.fillStyle = sphereFill;
      ctx.fill();

      ctx.save();
      ctx.beginPath();
      ctx.arc(center.x, center.y, radius * 0.988, 0, Math.PI * 2);
      if (typeof ctx.clip === "function") {
        ctx.clip();
        const horizonShade = ctx.createRadialGradient(
          center.x - radius * 0.10,
          center.y - radius * 0.08,
          radius * 0.24,
          center.x,
          center.y,
          radius,
        );
        horizonShade.addColorStop(0, "rgba(56, 189, 248, 0.08)");
        horizonShade.addColorStop(0.6, "rgba(15, 23, 42, 0.05)");
        horizonShade.addColorStop(1, "rgba(15, 23, 42, 0.30)");
        ctx.fillStyle = horizonShade;
        ctx.fillRect(center.x - radius, center.y - radius, radius * 2, radius * 2);
      }
      ctx.restore();

      ctx.shadowColor = "rgba(56, 189, 248, 0.28)";
      ctx.shadowBlur = 22;
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = rim;
      ctx.beginPath();
      ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
      ctx.stroke();
      ctx.shadowBlur = 0;

      const latitudeValues = [-75, -45, -15, 0, 15, 45, 75];
      latitudeValues.forEach((latDeg) => {
        const lat = (latDeg * Math.PI) / 180;
        const ringRadius = Math.max(0, radius * Math.cos(lat) * 0.985);
        const ringY = center.y + (Math.sin(lat) * radius * 0.56);
        ctx.strokeStyle = latDeg === 0
          ? "rgba(248, 250, 252, 0.72)"
          : "rgba(186, 230, 253, 0.28)";
        ctx.lineWidth = latDeg === 0 ? 2.4 : 1.5;
        ctx.beginPath();
        if (typeof ctx.ellipse === "function") {
          ctx.ellipse(center.x, ringY, ringRadius, Math.max(2, ringRadius * 0.30), -0.12, 0, Math.PI * 2);
        } else {
          ctx.arc(center.x, ringY, ringRadius, 0, Math.PI * 2);
        }
        ctx.stroke();
      });

      const longitudeValues = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150];
      longitudeValues.forEach((lonDeg) => {
        const tilt = (lonDeg * Math.PI) / 180;
        ctx.strokeStyle = lonDeg === 0
          ? "rgba(248, 250, 252, 0.68)"
          : "rgba(186, 230, 253, 0.18)";
        ctx.lineWidth = lonDeg === 0 ? 2.0 : 1.2;
        ctx.beginPath();
        for (let step = 0; step <= 48; step += 1) {
          const t = (step / 48) * Math.PI * 2;
          const x = center.x + Math.sin(t) * radius * Math.cos(tilt) * 0.94;
          const y = center.y + Math.cos(t) * radius * 0.58;
          if (step === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      });

      ctx.shadowColor = "rgba(14, 165, 233, 0.24)";
      ctx.shadowBlur = 18;
      ctx.strokeStyle = "rgba(191, 219, 254, 0.5)";
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      ctx.arc(center.x, horizonY, radius * 0.98, 0, Math.PI * 2);
      ctx.stroke();

      ctx.shadowBlur = 12;
      ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(center.x, center.y, radius * 0.64, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    function swarmLabWorldToCanvas(layout, x, y) {
      return projectSwarmLabSurfacePoint(layout, x, y);
    }

    function swarmLabCanvasToWorld(layout, x, y) {
      const center = getSwarmLabWorldCenter(layout);
      return {
        x: 800 + ((x - center.x) / Math.max(0.0001, layout.scale)),
        y: 450 + ((y - center.y) / Math.max(0.0001, layout.scale)),
      };
    }

    function buildSwarmLabNodes(count) {
      const safeCount = Math.max(6, Math.min(64, Math.round(Number(count || 24))));
      const nodes = [];
      const palette = ["#60a5fa", "#34d399", "#f59e0b", "#f472b6", "#a78bfa", "#22d3ee"];
      for (let idx = 0; idx < safeCount; idx += 1) {
        const angle = (Math.PI * 2 * idx) / safeCount;
        const radius = 210 + ((idx % 5) * 22) + ((Math.random() - 0.5) * 18);
        const x = 800 + (Math.cos(angle) * radius) + ((Math.random() - 0.5) * 70);
        const y = 450 + (Math.sin(angle * 1.4) * (radius * 0.62)) + ((Math.random() - 0.5) * 70);
        nodes.push({
          id: `node-${idx + 1}`,
          label: `Node ${String(idx + 1).padStart(2, "0")}`,
          x,
          y,
          vx: 0,
          vy: 0,
          radius: 14 + ((idx % 4) * 2),
          energy: 70 + ((idx % 7) * 7),
          color: palette[idx % palette.length],
        });
      }
      return nodes;
    }

    function spawnSwarmLabAgent(index, node = null) {
      const home = node || swarmLabNodes[index % Math.max(1, swarmLabNodes.length)] || {
        x: 800,
        y: 450,
      };
      const offset = (Math.random() - 0.5) * 38;
      const angle = Math.random() * Math.PI * 2;
      return {
        id: `agent-${index + 1}`,
        x: home.x + (Math.cos(angle) * offset),
        y: home.y + (Math.sin(angle) * offset),
        vx: (Math.random() - 0.5) * 1.6,
        vy: (Math.random() - 0.5) * 1.6,
        energy: 100 + (Math.random() * 20),
        age: 0,
        generation: 1,
        targetId: home.id,
        memory: {},
      };
    }

    function updateSwarmLabControls() {
      const populationSlider = document.getElementById("swarm-lab-population-slider");
      const populationLabel = document.getElementById("swarm-lab-population-label");
      const nodeCountSlider = document.getElementById("swarm-lab-node-count-slider");
      const nodeCountLabel = document.getElementById("swarm-lab-node-count-label");
      const mutationSlider = document.getElementById("swarm-lab-mutation-slider");
      const mutationLabel = document.getElementById("swarm-lab-mutation-label");
      const repulsionSlider = document.getElementById("swarm-lab-repulsion-slider");
      const repulsionLabel = document.getElementById("swarm-lab-repulsion-label");
      const speedSlider = document.getElementById("swarm-lab-speed-slider");
      const speedLabel = document.getElementById("swarm-lab-speed-label");
      const zoomSlider = document.getElementById("swarm-lab-zoom-slider");
      const zoomLabel = document.getElementById("swarm-lab-zoom-label");

      if (populationSlider) populationSlider.value = String(swarmLabPopulation);
      if (populationLabel) populationLabel.textContent = `${swarmLabPopulation} agents`;
      if (nodeCountSlider) nodeCountSlider.value = String(swarmLabNodeCount);
      if (nodeCountLabel) nodeCountLabel.textContent = `${swarmLabNodeCount} nodes`;
      if (mutationSlider) mutationSlider.value = String(swarmLabMutation);
      if (mutationLabel) mutationLabel.textContent = `${(swarmLabMutation * 100).toFixed(1)}% mutation`;
      if (repulsionSlider) repulsionSlider.value = String(swarmLabRepulsion);
      if (repulsionLabel) repulsionLabel.textContent = `${Number(swarmLabRepulsion).toFixed(2)} repulsion`;
      if (speedSlider) speedSlider.value = String(swarmLabSpeed);
      if (speedLabel) speedLabel.textContent = `${Number(swarmLabSpeed).toFixed(2)}x speed`;
      if (zoomSlider) zoomSlider.value = String(swarmLabZoom);
      if (zoomLabel) zoomLabel.textContent = `${Number(swarmLabZoom).toFixed(2)}x world`;
    }

    function renderSwarmLabPanels() {
      const hoverEl = document.getElementById("swarm-lab-hover");
      const selectedEl = document.getElementById("swarm-lab-selected");
      const worldLabel = document.getElementById("swarm-lab-world-caption");
      const stats = document.getElementById("swarm-lab-stats");
      const selected = swarmLabSelectedNodeId ? swarmLabNodes.find((node) => node.id === swarmLabSelectedNodeId) : null;
      const hovered = swarmLabHoveredNodeId ? swarmLabNodes.find((node) => node.id === swarmLabHoveredNodeId) : null;
      if (hoverEl) {
        hoverEl.innerHTML = hovered
          ? `<div class="font-bold text-slate-800">${hovered.label}</div><div class="text-slate-500">Energy ${Number(hovered.energy || 0).toFixed(0)} · radius ${Number(hovered.radius || 0).toFixed(0)}</div>`
          : "Move across the lab to inspect nodes.";
      }
      if (selectedEl) {
        selectedEl.innerHTML = selected
          ? `<div class="font-bold text-slate-800">${selected.label}</div><div class="text-slate-500">Pinned node in the abstract world.</div>`
          : "Click a node to pin it here.";
      }
      if (worldLabel) {
        worldLabel.textContent = swarmLabPlaying ? "Playing" : "Paused";
      }
      if (stats) {
        const avgEnergy = swarmLabAgents.length
          ? swarmLabAgents.reduce((sum, agent) => sum + Number(agent.energy || 0), 0) / swarmLabAgents.length
          : 0;
        stats.textContent = `${swarmLabNodes.length} nodes · ${swarmLabAgents.length} agents · avg energy ${avgEnergy.toFixed(1)} · gen ${swarmLabGenerationMax}`;
      }
      updateSwarmLabControls();
    }

    function resetSwarmLabSimulation() {
      swarmLabWorld = {
        width: 1600,
        height: 900,
      };
      swarmLabNodes = buildSwarmLabNodes(swarmLabNodeCount);
      swarmLabAgents = [];
      swarmLabTrails = [];
      swarmLabFrameCounter = 0;
      swarmLabBirthCount = 0;
      swarmLabDeathCount = 0;
      swarmLabGenerationMax = 1;
      swarmLabSelectedNodeId = null;
      swarmLabHoveredNodeId = null;
      const cap = Math.max(12, Math.round(Number(swarmLabPopulation || 72)));
      for (let idx = 0; idx < cap; idx += 1) {
        swarmLabAgents.push(spawnSwarmLabAgent(idx, swarmLabNodes[idx % swarmLabNodes.length]));
      }
      renderSwarmLabPanels();
      drawSwarmLabScene();
    }

    function setSwarmLabPopulation(nextValue) {
      swarmLabPopulation = Math.round(clampSwarm(Number(nextValue || 72), 12, 240));
      resetSwarmLabSimulation();
    }

    function setSwarmLabNodeCount(nextValue) {
      swarmLabNodeCount = Math.round(clampSwarm(Number(nextValue || 24), 6, 64));
      resetSwarmLabSimulation();
    }

    function setSwarmLabMutation(nextValue) {
      swarmLabMutation = clampSwarm(Number(nextValue || 0.08), 0.01, 0.35);
      updateSwarmLabControls();
    }

    function setSwarmLabRepulsion(nextValue) {
      swarmLabRepulsion = clampSwarm(Number(nextValue || 0.55), 0.0, 1.5);
      updateSwarmLabControls();
    }

    function setSwarmLabSpeed(nextValue) {
      swarmLabSpeed = clampSwarm(Number(nextValue || 1.0), 0.35, 3.0);
      updateSwarmLabControls();
    }

    function setSwarmLabZoom(nextValue) {
      swarmLabZoom = clampSwarm(Number(nextValue || 1.0), 0.6, 1.8);
      updateSwarmLabControls();
      drawSwarmLabScene();
    }

    function drawSwarmLabScene() {
      const canvas = getSwarmLabCanvas();
      const layout = getSwarmLabCanvasLayout(canvas);
      if (!layout) {
        return;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        return;
      }
      ctx.save();
      ctx.scale(layout.dpr, layout.dpr);
      ctx.clearRect(0, 0, layout.width, layout.height);
      const bg = ctx.createLinearGradient(0, 0, 0, layout.height);
      bg.addColorStop(0, "#0f172a");
      bg.addColorStop(1, "#111827");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, layout.width, layout.height);
      drawSwarmLabGlobeBackdrop(ctx, layout);

      const globeRadius = getSwarmLabGlobeRadius(layout) * 0.985;
      const globeCenter = getSwarmLabWorldCenter(layout);

      const projectedTrails = swarmLabTrails.map((trail) => ({
        trail,
        x1: projectSwarmLabSurfacePoint(layout, trail.x1, trail.y1),
        x2: projectSwarmLabSurfacePoint(layout, trail.x2, trail.y2),
      }));
      projectedTrails.forEach(({ trail, x1, x2 }) => {
        const alpha = Math.max(0, Math.min(0.34, trail.life / 92));
        ctx.strokeStyle = `rgba(96, 165, 250, ${alpha})`;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(x1.x, x1.y);
        ctx.lineTo(x2.x, x2.y);
        ctx.stroke();
      });

      const projectedNodes = swarmLabNodes
        .map((node) => ({ node, point: swarmLabWorldToCanvas(layout, node.x, node.y) }))
        .sort((a, b) => a.point.z - b.point.z);
      projectedNodes.forEach(({ node, point }) => {
        const selected = node.id === swarmLabSelectedNodeId;
        const hovered = node.id === swarmLabHoveredNodeId;
        const depthAlpha = 0.44 + (Math.max(-1, Math.min(1, point.z)) + 1) * 0.24;
        ctx.beginPath();
        ctx.fillStyle = node.color;
        ctx.globalAlpha = hovered ? 1 : depthAlpha;
        ctx.arc(point.x, point.y, node.radius * (hovered ? 1.35 : 1) * (0.92 + (point.z * 0.06)), 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = selected ? "#facc15" : "rgba(15, 23, 42, 0.72)";
        ctx.lineWidth = selected ? 2.4 : 1.2;
        ctx.stroke();
      });

      const projectedAgents = swarmLabAgents
        .map((agent) => ({ agent, point: swarmLabWorldToCanvas(layout, agent.x, agent.y) }))
        .sort((a, b) => a.point.z - b.point.z);
      projectedAgents.forEach(({ agent, point }) => {
        ctx.fillStyle = agent.energy >= 90 ? "#ddd6fe" : "#67e8f9";
        ctx.globalAlpha = 0.74 + (Math.max(-1, Math.min(1, point.z)) + 1) * 0.12;
        const canTransform = typeof ctx.translate === "function" && typeof ctx.rotate === "function";
        if (canTransform) {
          ctx.save();
          ctx.translate(point.x, point.y);
          ctx.rotate(Math.atan2(agent.vy || 0, agent.vx || 0) + Math.PI / 2);
          ctx.beginPath();
          if (typeof ctx.roundRect === "function") {
            ctx.roundRect(-1.2, -4.2, 2.4, 8.4, 1.2);
          } else {
            ctx.ellipse(0, 0, 1.6, 4.0, 0, 0, Math.PI * 2);
          }
          ctx.fill();
          ctx.restore();
        } else {
          ctx.beginPath();
          ctx.arc(point.x, point.y, 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      ctx.restore();
    }

    function getSwarmLabNodeAtPoint(clientX, clientY) {
      const layout = getSwarmLabCanvasLayout();
      if (!layout || !swarmLabNodes.length) {
        return null;
      }
      const x = clientX - layout.rect.left;
      const y = clientY - layout.rect.top;
      let winner = null;
      let winnerDistance = Number.POSITIVE_INFINITY;
      swarmLabNodes.forEach((node) => {
        const point = swarmLabWorldToCanvas(layout, node.x, node.y);
        const dist = Math.hypot(x - point.x, y - point.y);
        if (dist <= node.radius + 8 && dist < winnerDistance) {
          winner = node;
          winnerDistance = dist;
        }
      });
      return winner;
    }

    function stepSwarmLabSimulation(dt) {
      if (!swarmLabAgents.length || !swarmLabNodes.length) {
        return;
      }
      swarmLabFrameCounter += 1;
      const timeScale = Math.max(0.35, Math.min(2.4, dt / 16.666)) * swarmLabSpeed;
      swarmLabTrails = swarmLabTrails
        .map((trail) => ({ ...trail, life: trail.life - (1.3 * timeScale) }))
        .filter((trail) => trail.life > 0);

      swarmLabAgents.forEach((agent) => {
        agent.age += timeScale;
        let chosenNode = null;
        let chosenScore = Number.POSITIVE_INFINITY;
        swarmLabNodes.forEach((node) => {
          const dx = node.x - agent.x;
          const dy = node.y - agent.y;
          const distance = Math.max(0.001, Math.hypot(dx, dy));
          const mutationBias = 1 + (swarmLabMutation * ((Math.sin(agent.age / 7) + 1) * 0.25));
          const score = distance / Math.max(0.2, node.energy / 70) * mutationBias;
          if (score < chosenScore) {
            chosenScore = score;
            chosenNode = node;
          }
        });

        if (chosenNode) {
          agent.targetId = chosenNode.id;
          const dx = chosenNode.x - agent.x;
          const dy = chosenNode.y - agent.y;
          const distance = Math.max(0.001, Math.hypot(dx, dy));
          const pull = (chosenNode.energy / 160) * swarmLabSpeed;
          const nx = dx / distance;
          const ny = dy / distance;
          agent.vx += nx * pull * 0.08;
          agent.vy += ny * pull * 0.08;
        }

        swarmLabAgents.forEach((other) => {
          if (other === agent) {
            return;
          }
          const dx = agent.x - other.x;
          const dy = agent.y - other.y;
          const distance = Math.max(0.001, Math.hypot(dx, dy));
          if (distance < 28) {
            const repulse = (28 - distance) / 28 * swarmLabRepulsion * 0.025;
            agent.vx += (dx / distance) * repulse;
            agent.vy += (dy / distance) * repulse;
          }
        });

        agent.vx = clampSwarm(agent.vx * 0.965, -4.5, 4.5);
        agent.vy = clampSwarm(agent.vy * 0.965, -4.5, 4.5);
        const prevX = agent.x;
        const prevY = agent.y;
        agent.x = clampSwarm(agent.x + (agent.vx * timeScale), 0, 1600);
        agent.y = clampSwarm(agent.y + (agent.vy * timeScale), 0, 900);
        agent.energy -= (0.18 + (swarmLabMutation * 0.4)) * timeScale;

        if (chosenNode) {
          const proximity = Math.max(0, 1 - (Math.hypot(chosenNode.x - agent.x, chosenNode.y - agent.y) / 240));
          agent.energy += proximity * 0.65 * timeScale;
        }

        if (Math.hypot(agent.vx, agent.vy) > 0.25) {
          swarmLabTrails.push({ x1: prevX, y1: prevY, x2: agent.x, y2: agent.y, life: 38 });
        }

        if (agent.energy > 132 && swarmLabAgents.length < swarmLabPopulation + 48) {
          swarmLabBirthCount += 1;
          swarmLabGenerationMax = Math.max(swarmLabGenerationMax, agent.generation + 1);
          swarmLabAgents.push({
            id: `agent-${swarmLabFrameCounter}-${swarmLabBirthCount}`,
            x: agent.x + ((Math.random() - 0.5) * 18),
            y: agent.y + ((Math.random() - 0.5) * 18),
            vx: -agent.vx + ((Math.random() - 0.5) * 0.5),
            vy: -agent.vy + ((Math.random() - 0.5) * 0.5),
            energy: 96,
            age: 0,
            generation: agent.generation + 1,
            targetId: chosenNode ? chosenNode.id : null,
            memory: {},
          });
          agent.energy *= 0.68;
        }

        if (agent.energy <= 0) {
          swarmLabDeathCount += 1;
          const seed = swarmLabNodes[swarmLabDeathCount % swarmLabNodes.length];
          agent.x = seed.x;
          agent.y = seed.y;
          agent.vx = (Math.random() - 0.5) * 1.4;
          agent.vy = (Math.random() - 0.5) * 1.4;
          agent.energy = 92;
          agent.age = 0;
          agent.generation = 1;
        }
      });

      swarmLabNodes.forEach((node, idx) => {
        const pulse = Math.sin((swarmLabFrameCounter / 22) + idx) * 6;
        node.energy = clampSwarm(node.energy + pulse * 0.1, 24, 160);
        node.radius = clampSwarm(12 + (node.energy / 22), 12, 22);
      });

      if (swarmLabAgents.length > Math.max(swarmLabPopulation, 1)) {
        swarmLabAgents = swarmLabAgents.slice(0, Math.max(swarmLabPopulation, 1));
      }
    }

    function runSwarmLabFrame(timestamp) {
      swarmLabAnimationHandle = null;
      if (swarmLabLastFrameTime === null) {
        swarmLabLastFrameTime = timestamp;
      }
      const dt = timestamp - swarmLabLastFrameTime;
      swarmLabLastFrameTime = timestamp;
      if (swarmLabPlaying) {
        stepSwarmLabSimulation(dt);
      }
      drawSwarmLabScene();
      if (!document.getElementById("tab-swarm-lab").classList.contains("hidden")) {
        swarmLabAnimationHandle = requestAnimationFrame(runSwarmLabFrame);
      }
    }

    function ensureSwarmLabAnimationLoop() {
      if (!swarmLabAnimationHandle && !document.getElementById("tab-swarm-lab").classList.contains("hidden")) {
        swarmLabLastFrameTime = null;
        swarmLabAnimationHandle = requestAnimationFrame(runSwarmLabFrame);
      }
    }

    async function loadSwarmLab(forceRefresh = false) {
      const status = document.getElementById("swarm-lab-status");
      const empty = document.getElementById("swarm-lab-empty");
      const content = document.getElementById("swarm-lab-content");
      const refreshBtn = document.getElementById("swarm-lab-refresh-btn");
      if (swarmLabLoaded && !forceRefresh) {
        if (content) {
          content.classList.remove("hidden");
        }
        renderSwarmLabPanels();
        drawSwarmLabScene();
        ensureSwarmLabAnimationLoop();
        return;
      }
      if (status) {
        status.textContent = forceRefresh ? "Reinitialising abstract lab..." : "Loading abstract lab...";
      }
      if (empty) {
        empty.classList.add("hidden");
      }
      if (content) {
        content.classList.remove("hidden");
      }
      if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.textContent = forceRefresh ? "Resetting..." : "Loading...";
      }
      swarmLabLoaded = true;
      swarmLabPlaying = false;
      swarmLabLastFrameTime = null;
      resetSwarmLabSimulation();
      updateSwarmLabControls();
      renderSwarmLabPanels();
      if (status) {
        status.textContent = "Abstract lab ready";
      }
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "Reset Lab";
      }
      ensureSwarmLabAnimationLoop();
    }

    function toggleSwarmLabPlayback() {
      if (swarmLabPlaying) {
        swarmLabPlaying = false;
        swarmLabLastFrameTime = null;
        drawSwarmLabScene();
        renderSwarmLabPanels();
        return;
      }
      swarmLabPlaying = true;
      ensureSwarmLabAnimationLoop();
      renderSwarmLabPanels();
    }

    function stopSwarmLabPlayback() {
      swarmLabPlaying = false;
      swarmLabLastFrameTime = null;
      drawSwarmLabScene();
      renderSwarmLabPanels();
    }

    async function loadMarketStatus(source = tickerScanScope) {
      const marketStatus = document.getElementById("shortlist-market-status");
      if (!marketStatus) {
        return null;
      }

      try {
        const normalizedSource = normalizeScanScope(source);
        if (normalizedSource === "debug") {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-amber-600";
          marketStatus.textContent = "Debug scope uses synthetic swarm assets";
          return null;
        }
        const resp = await fetch(`/api/market-status?stale_after_days=0&source=${encodeURIComponent(normalizedSource)}`);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Market status request failed");
        }

        if (data.is_stale) {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-amber-600";
          marketStatus.textContent = `Market data needs top-up · latest ${data.latest_market_date || "unknown"} · stale ${Number(data.stale_tickers || 0)} · missing ${Number(data.missing_tickers || 0)}`;
        } else {
          marketStatus.className = "text-xs font-bold uppercase tracking-wide text-emerald-600";
          marketStatus.textContent = `Market data fresh through ${data.latest_market_date || "unknown"} · ${Number(data.fresh_tickers || data.tracked_tickers || 0)} active tickers`;
        }
        return data;
      } catch (err) {
        marketStatus.className = "text-xs font-bold uppercase tracking-wide text-rose-600";
        marketStatus.textContent = "Could not determine market data freshness";
        return null;
      }
    }

    async function ensureGuiMarketBackbone() {
      if (normalizeScanScope(tickerScanScope) === "debug") {
        return { status: null, refreshed: false, debug: true };
      }
      const status = await loadMarketStatus(tickerScanScope);
      let refreshed = false;
      if (status && status.is_stale && !marketDataAutoRefreshAttempted) {
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
      if (tab !== 'swarm' && swarmAnimationHandle) {
        cancelAnimationFrame(swarmAnimationHandle);
        swarmAnimationHandle = null;
      }
      if (tab !== 'swarm-lab' && swarmLabAnimationHandle) {
        cancelAnimationFrame(swarmLabAnimationHandle);
        swarmLabAnimationHandle = null;
      }
      if (tab === 'backtest') {
        loadBacktestMetrics();
      } else if (tab === 'shortlist') {
        ensureGuiMarketBackbone().catch((err) => {
          console.warn("Auto-refresh check failed", err);
        });
        loadShortlist();
      } else if (tab === 'swarm') {
        loadSwarmWorld(false);
      } else if (tab === 'swarm-lab') {
        loadSwarmLab(false);
      }
    }

    window.showTab = showTab;

    const DEFAULT_DASHBOARD_TAB = "swarm-lab";
    let dashboardDefaultTabApplied = false;

    function applyDefaultDashboardTab() {
      if (dashboardDefaultTabApplied) {
        return;
      }
      const labCanvas = document.getElementById("swarm-lab-canvas");
      if (!labCanvas || typeof labCanvas.getBoundingClientRect !== "function") {
        return;
      }
      dashboardDefaultTabApplied = true;
      const pendingTab = normalizeDashboardTab(window.__dashboardPendingTab || "");
      if (window.__dashboardPendingTab) {
        window.__dashboardPendingTab = null;
        showTab(pendingTab);
        return;
      }
      showTab(DEFAULT_DASHBOARD_TAB);
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
      let marketProgressInterval = null;
      let marketPhase = "checking";
      let marketProgress = 0;

      const updateMarketProgress = (state) => {
        setNavScanProgress({
          show: true,
          contextLabel: state.contextLabel || "Market",
          contextText: state.contextText || "WORKING",
          contextPct: state.contextPct ?? marketProgress,
          contextWorking: state.contextWorking ?? true,
        });
      };

      const startMarketProgress = () => {
        if (marketProgressInterval) {
          clearInterval(marketProgressInterval);
        }
        marketProgressInterval = setInterval(() => {
          if (marketPhase === "checking") {
            marketProgress = Math.min(22, marketProgress + 1.5);
            updateMarketProgress({
              contextLabel: "Market",
              contextText: "Checking...",
              contextPct: marketProgress,
            });
            return;
          }
          if (marketPhase === "refreshing") {
            marketProgress = Math.min(88, marketProgress + Math.max(0.6, (88 - marketProgress) * 0.08));
            updateMarketProgress({
              contextLabel: "Market",
              contextText: `${Math.round(marketProgress)}%`,
              contextPct: marketProgress,
            });
            return;
          }
          if (marketPhase === "rebuilding") {
            marketProgress = Math.min(96, marketProgress + Math.max(0.4, (96 - marketProgress) * 0.06));
            updateMarketProgress({
              contextLabel: "Market",
              contextText: "Rebuilding...",
              contextPct: marketProgress,
            });
          }
        }, 320);
      };

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
        updateMarketProgress({
          contextLabel: "Market",
          contextText: "Checking...",
          contextPct: 0,
          contextWorking: false,
        });
        startJobProgressPolling("market-refresh", "Global");
        startMarketProgress();
        marketPhase = "refreshing";
        const resp = await fetch(`/api/market-data/refresh?depth=400&max_workers=8&force=true&stale_after_days=0&source=${encodeURIComponent(source)}`, {
          method: "POST",
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Market refresh failed");
        }

        marketPhase = "rebuilding";
        updateMarketProgress({
          contextLabel: "Market",
          contextText: "Rebuilding...",
          contextPct: 94,
          contextWorking: true,
        });
        shortlistLoaded = false;
        await loadMarketStatus();
        await loadShortlist(true);
        marketPhase = "done";
        updateMarketProgress({
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
        marketPhase = "done";
        updateMarketProgress({
          contextLabel: "Market",
          contextText: "FAILED",
          contextPct: 100,
          contextWorking: false,
        });
        showToast(`Market refresh failed: ${err.message || err}`, true);
      } finally {
        if (marketProgressInterval) {
          clearInterval(marketProgressInterval);
        }
        marketProgressInterval = null;
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
      if (!document.getElementById("tab-backtest").classList.contains("hidden")) {
        loadBacktestMetrics();
      }
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

    async function loadBacktestMetrics() {
      const strategySelect = document.getElementById("strategy-select");
      const strategyName = strategySelect && strategySelect.value ? strategySelect.value : "";
      const editorDsl = getActiveEditorDsl();
      const runBtn = document.getElementById("backtest-run-btn");
      const body = document.getElementById("backtest-table-body");
      const chartDiv = document.getElementById("backtest-chart");
      const content = document.getElementById("backtest-content");
      const signalDays = getBacktestSignalDays();

      if (backtestSourceMode === "saved" && !strategyName) {
        setBacktestEmptyState("Select a saved strategy first, then open Backtester to score it.");
        return;
      }
      if (backtestSourceMode === "editor" && !editorDsl) {
        setBacktestEmptyState("Editor Draft is selected, but the Labs editor is empty.");
        return;
      }
      if ((normalizeScanScope(tickerScanScope) === "list" || normalizeScanScope(tickerScanScope) === "all_lists") && getScopeTickers(tickerScanScope).length === 0) {
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
      startJobProgressPolling("backtest", "Global");
      setNavScanProgress({
        show: true,
        globalLabel: "Global",
        globalText: "Preparing...",
        globalPct: 0,
        globalWorking: true,
      });

      let btFakeProg = 0;
      let btWorkingPhase = false;
      let btProgressInterval = null;
      const startBacktestProgress = () => {
        btProgressInterval = setInterval(() => {
          const nodes = getNavScanProgressNodes();
          if (!nodes.contextBar || !nodes.contextText) return;

          if (btFakeProg < 90) {
            btFakeProg = Math.min(90, btFakeProg + Math.max(0.45, (90 - btFakeProg) * 0.1));
            setNavScanProgress({
              contextLabel: "Backtest",
              contextText: `${Math.round(btFakeProg)}%`,
              contextPct: btFakeProg,
            });
            return;
          }

          if (!btWorkingPhase) {
            btWorkingPhase = true;
            setNavScanProgress({
              contextLabel: "Backtest",
              contextText: "WORKING",
              contextPct: 90,
              contextWorking: true,
            });
          }

          const contextPulse = 88 + Math.round(4 * (0.5 + 0.5 * Math.sin(Date.now() / 400)));
          setNavScanProgress({
            contextLabel: "Backtest",
            contextText: "WORKING",
            contextPct: contextPulse,
            contextWorking: true,
          });
        }, 300);
      };
      startBacktestProgress();

      setBacktestEmptyState(`Evaluating ${backtestSourceMode === 'editor' ? 'Editor Draft' : strategyName}...`);
      runBtn.disabled = true;
      runBtn.textContent = "Evaluating...";

      try {
        await ensureGuiMarketBackbone();
        startJobProgressPolling("backtest", "Global");
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
        let url = `/api/backtest?limit=25`;
        const universeParams = getUniverseFilterParams();
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
          url += `&strategy=${encodeURIComponent(strategyName)}`;
        }
        const resp = await fetch(url);
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Backtest request failed");
        }

        document.getElementById("bt-strategy").textContent =
          `${data.strategy_name || strategyName || "Editor Draft"} (${data.source_type === "editor" ? "Editor Draft" : "Saved Strategy"})`;
        document.getElementById("bt-count").textContent = String(data.summary?.count || 0);
        document.getElementById("bt-best-quality").textContent = Number(data.summary?.best_quality || 0).toFixed(2);
        document.getElementById("bt-avg-return").textContent = `${Number(data.summary?.avg_return || 0).toFixed(2)}%`;
        document.getElementById("bt-avg-sharpe").textContent = Number(data.summary?.avg_sharpe || 0).toFixed(2);

        body.innerHTML = "";
        const rows = Array.isArray(data.rows) ? data.rows : [];
        if (rows.length === 0) {
          setBacktestEmptyState(`No scored results were returned for ${data.strategy_name || strategyName || 'Editor Draft'}.`);
          return;
        }

        rows.forEach((row) => {
          const tr = document.createElement("tr");
          tr.className = "hover:bg-slate-50 cursor-pointer";
          tr.onclick = () => {
            showTab('screener');
            loadChart(row.ticker);
          };
          tr.innerHTML = `
            <td class="px-4 py-3 font-bold text-slate-800">${row.ticker}</td>
            <td class="px-4 py-3 font-mono text-indigo-700">${Number(row.quality_score || 0).toFixed(2)}</td>
            <td class="px-4 py-3 font-mono ${Number(row.return_pct || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}">${Number(row.return_pct || 0).toFixed(2)}%</td>
            <td class="px-4 py-3 font-mono">${Number(row.win_rate_pct || 0).toFixed(2)}%</td>
            <td class="px-4 py-3 font-mono">${Number(row.sharpe || 0).toFixed(2)}</td>
            <td class="px-4 py-3 font-mono">${Number(row.profit_factor || 0).toFixed(2)}</td>
            <td class="px-4 py-3 font-mono">${Number(row.max_dd_pct || 0).toFixed(2)}%</td>
            <td class="px-4 py-3 font-mono">${Number(row.trades || 0)}</td>
            <td class="px-4 py-3 font-mono">${Number(row.days_since_entry || 0)}</td>
          `;
          body.appendChild(tr);
        });

        if (chartDiv) {
          const chart = data.chart || { data: [], layout: {} };
          if (chart.data && chart.data.length > 0 && window.Plotly) {
            await Plotly.newPlot(chartDiv, chart.data, chart.layout || {}, {
              responsive: true,
              displayModeBar: false,
              displaylogo: false,
            });
          } else if (window.Plotly) {
            Plotly.purge(chartDiv);
          }
        }

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
        await new Promise((resolve) => setTimeout(resolve, 300));
      } catch (err) {
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
        await new Promise((resolve) => setTimeout(resolve, 250));
      } finally {
        if (btProgressInterval) clearInterval(btProgressInterval);
        btProgressInterval = null;
        stopJobProgressPolling();
        resetScanUI();
        runBtn.disabled = false;
        runBtn.textContent = "Evaluate Strategy";
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
      if (tickerScanScope === "debug") {
        tickerScanScope = "xetra";
        writeStickyValue(LAST_SCAN_SCOPE_KEY, tickerScanScope);
      }
      swarmDebugAssetCount = normalizeSwarmDebugAssetCount(
        readStickyValue(LAST_SWARM_DEBUG_ASSET_COUNT_KEY, "24")
      );
      updateScanScopeChrome();
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
      const swarmCanvas = document.getElementById("swarm-canvas");
      if (swarmCanvas) {
        const stopSwarmCameraDrag = () => {
          if (!swarmCameraDrag.active) {
            return;
          }
          swarmCameraDrag.active = false;
          swarmCanvas.style.cursor = "grab";
          if (swarmCameraDrag.moved) {
            swarmSuppressNextClick = true;
          }
        };
        swarmCanvas.addEventListener("pointerdown", (event) => {
          if (event.button !== 0 && event.pointerType !== "touch") {
            return;
          }
          swarmCanvas.setPointerCapture?.(event.pointerId);
          swarmCameraDrag.active = true;
          swarmCameraDrag.moved = false;
          swarmCameraDrag.lastX = event.clientX;
          swarmCameraDrag.lastY = event.clientY;
          swarmCanvas.style.cursor = "grabbing";
          event.preventDefault();
        });
        swarmCanvas.addEventListener("pointermove", (event) => {
          if (swarmCameraDrag.active) {
            const deltaX = event.clientX - swarmCameraDrag.lastX;
            const deltaY = event.clientY - swarmCameraDrag.lastY;
            if (Math.abs(deltaX) > 0 || Math.abs(deltaY) > 0) {
              swarmCameraDrag.moved = true;
              orbitSwarmCamera(deltaX, deltaY);
              swarmCameraDrag.lastX = event.clientX;
              swarmCameraDrag.lastY = event.clientY;
              drawSwarmScene();
            }
            event.preventDefault();
            return;
          }
          const node = getSwarmNodeAtPoint(event.clientX, event.clientY);
          const nextTicker = node ? node.ticker : null;
          if (nextTicker !== swarmHoveredTicker) {
            swarmHoveredTicker = nextTicker;
            updateSwarmPanels();
            drawSwarmScene();
          }
        });
        swarmCanvas.addEventListener("pointerleave", () => {
          stopSwarmCameraDrag();
          if (swarmHoveredTicker !== null) {
            swarmHoveredTicker = null;
            updateSwarmPanels();
            drawSwarmScene();
          }
        });
        swarmCanvas.addEventListener("pointerup", (event) => {
          swarmCanvas.releasePointerCapture?.(event.pointerId);
          stopSwarmCameraDrag();
        });
        swarmCanvas.addEventListener("pointercancel", stopSwarmCameraDrag);
        swarmCanvas.addEventListener("click", (event) => {
          if (swarmSuppressNextClick) {
            swarmSuppressNextClick = false;
            return;
          }
          const agent = getSwarmAgentAtPoint(event.clientX, event.clientY);
          if (agent) {
            swarmSelectedAgentId = agent.id;
          } else {
            const node = getSwarmNodeAtPoint(event.clientX, event.clientY);
            swarmSelectedTicker = node ? node.ticker : null;
            swarmSelectedAgentId = null;
          }
          updateSwarmPanels();
          drawSwarmScene();
        });
        window.addEventListener("pointerup", stopSwarmCameraDrag);
      }
      const swarmLabCanvas = document.getElementById("swarm-lab-canvas");
      if (swarmLabCanvas) {
        swarmLabCanvas.addEventListener("pointermove", (event) => {
          const node = getSwarmLabNodeAtPoint?.(event.clientX, event.clientY);
          const nextId = node ? node.id : null;
          if (nextId !== swarmLabHoveredNodeId) {
            swarmLabHoveredNodeId = nextId;
            renderSwarmLabPanels();
            drawSwarmLabScene();
          }
        });
        swarmLabCanvas.addEventListener("pointerleave", () => {
          if (swarmLabHoveredNodeId !== null) {
            swarmLabHoveredNodeId = null;
            renderSwarmLabPanels();
            drawSwarmLabScene();
          }
        });
        swarmLabCanvas.addEventListener("click", (event) => {
          const node = getSwarmLabNodeAtPoint?.(event.clientX, event.clientY);
          swarmLabSelectedNodeId = node ? node.id : null;
          renderSwarmLabPanels();
          drawSwarmLabScene();
        });
      }
      window.addEventListener("resize", () => {
        if (swarmLoaded) {
          drawSwarmScene();
        }
        if (swarmLabLoaded) {
          drawSwarmLabScene();
        }
      });
      applyDefaultDashboardTab();
    });
    applyDefaultDashboardTab();
    let currentDays = 365 * 2;
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

      strategySelect.value = savedStrategy;
      currentStrategy = savedStrategy;
      await updateEditorContent(savedStrategy);
      return savedStrategy;
    }

    // --- Refresh strategies dropdown without full page reload ---
    async function refreshStrategiesDropdown(selectName = null) {
      try {
        const resp = await fetch("/api/strategies");
        const strategies = await resp.json();
        const sel = document.getElementById("strategy-select");
        const prev = selectName || sel.value;
        sel.innerHTML = '<option value="">-- No Active Strategy --</option>';
        strategies.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          sel.appendChild(opt);
        });
        if (prev) sel.value = prev;
      } catch (e) {
        console.error("Failed to refresh strategies dropdown", e);
      }
    }

    // UI Helpers
    function toggleStrategyPanel() {
      const panel = document.getElementById("strategy-panel");
      panel.classList.toggle("hidden");
    }

    async function updateEditorContent(strategyName) {
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
      } catch (err) {
        console.error("Failed to load strategy", err);
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
        showToast(`Change the name first — "${name}" is the original.`, true);
        document.getElementById("modify-modal-name").focus();
        return;
      }
      await _doSave(name, content, name);
      closeModifyModal();
    }

    // Save As — requires a name that differs from the source
    async function saveAsStrategy() {
      const name = document.getElementById("strategy-filename").value.trim();
      const content = document.getElementById("strategy-editor").value;
      if (!name || !content) { showToast("Need both a name and DSL content!", true); return; }
      if (name === sourceStrategyName) {
        showToast(`Change the name first — "${name}" is the original.`, true);
        document.getElementById("strategy-filename").focus();
        return;
      }
      await _doSave(name, content, name);
    }

    // Overwrite — saves back to the exact source file
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
      };
      syncExportMatchesButtonState();
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

      if (!job || !active) {
        return false;
      }
      if (expectedJob && job !== expectedJob) {
        return false;
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

      return !active && (phase === "done" || phase === "failed");
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

    function resetScanUI() {
      const spinner = document.getElementById("loading-spinner");
      const scanBtn = document.getElementById("scan-btn");
      const runBtn = document.getElementById("run-btn");
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

      if (scanBtn) {
        scanBtn.textContent = "Run Scanner";
        scanBtn.classList.add("bg-indigo-600");
        scanBtn.classList.remove("bg-indigo-400");
        scanBtn.disabled = false;
      }

      if (runBtn) {
        runBtn.innerHTML = `
            <svg class="w-3.5 h-3.5 mr-1" fill="currentColor" viewBox="0 0 24 24">
              <path d="M5 3l14 9-14 9V3z"></path>
            </svg>
            Run Screener
          `;
        runBtn.classList.remove("bg-emerald-500", "cursor-wait");
        runBtn.classList.add("bg-green-600");
        runBtn.disabled = false;
      }

      if (list) list.style.opacity = "1.0";
      scanAbortController = null;
    }

    async function runScreen(customDsl = null) {
      const list = document.getElementById("ticker-list");
      const spinner = document.getElementById("loading-spinner");
      const scanBtn = document.getElementById("scan-btn");
      const runBtn = document.getElementById("run-btn");
      const strategySelect = document.getElementById("strategy-select");
      const errorSection = document.getElementById("error-section");
      const errorList = document.getElementById("error-list");

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
        await ensureGuiMarketBackbone();
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
        const universeQuery = universeParams.toString();
        if (universeQuery) {
          url += `?${universeQuery}`;
        }
        if (customDsl) {
          url += `${universeQuery ? "&" : "?"}dsl_content=${encodeURIComponent(customDsl)}`;
          strategySelect.value = "";
          currentStrategy = "";
        } else if (strategySelect.value) {
          url += `${universeQuery ? "&" : "?"}strategy=${strategySelect.value}`;
          currentStrategy = strategySelect.value;
        } else {
          currentStrategy = "";
        }
        setLastScreenMatches([], {
          strategy_name: currentStrategy || (customDsl ? "Editor Draft" : ""),
          scan_scope: normalizeScanScope(tickerScanScope),
          ticker_list: universeParams.get("ticker_list") || "",
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
          });

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
                              <span class="text-slate-800 font-bold font-mono">${closeVal.toFixed(2)}€</span>
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
        });
        resetScanUI();
      }
    }

    async function loadChart(ticker) {
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
      const strategyName = (strategySelect && strategySelect.value) ? strategySelect.value : currentStrategy;
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
      });

    // Initialize
    const dashboardReadyPromise = (async function initializeDashboard() {
      const restoredStrategy = await restoreLastCompletedStrategy();
      if (restoredStrategy) {
        console.info("Restored last completed strategy", restoredStrategy);
      }
      const restoredDays = readSavedChartRangeDays();
      if (restoredDays !== null) {
        currentDays = restoredDays;
      }
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
      closeModifyModal,
      closeListEditorModal,
      openListEditorModal,
      loadBacktestMetrics,
      loadShortlist,
      loadSwarmWorld,
      loadSwarmLab,
      saveListEditor,
      modifyStrategy,
      openSelectedSwarmTicker,
      refreshMarketData,
      ensureFreshMarketData,
      exportTopMatches,
      resetDashboardTabPreference,
      resetSwarmSimulation,
      runScreen,
      saveAsStrategy,
      saveFromModal,
      saveStrategy,
      setBacktestSourceMode,
      setListBuilderExchange,
      setListBuilderSearch,
      setListBuilderList,
      setScanSource,
      setSwarmDebugAssetCount,
      setSwarmLabMutation,
      setSwarmLabNodeCount,
      setSwarmLabPopulation,
      setSwarmLabRepulsion,
      setSwarmLabSpeed,
      setSwarmLabZoom,
      setRange,
      dashboardReadyPromise,
      setShortlistFilter,
      setSwarmAgentsPerNode,
      setSwarmFilter,
      setSwarmJumpCost,
      setSwarmSense,
      setSwarmTimeline,
      setSwarmZoom,
      stepSwarmDays,
      showTab,
      stopSwarmPlayback,
      stopSwarmLabPlayback,
      testMe,
      toggleStrategyPanel,
      toggleVisibleListBuilderTickers,
      toggleSwarmPlayback,
      toggleSwarmLabPlayback,
    });
