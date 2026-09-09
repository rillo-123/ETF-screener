// Dashboard universe. See README.md in static/js/dashboard for the feature map.

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
  if (["all", "all_markets", "all-markets"].includes(cleaned)) {
    return "all";
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
  if (normalized === "all") {
    return "All tracked markets";
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
  if (normalized === "all") {
    return "All Markets";
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
  marketDataAutoRefreshAttempted = false;
  marketDataBackgroundRefreshAttempted = false;
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

