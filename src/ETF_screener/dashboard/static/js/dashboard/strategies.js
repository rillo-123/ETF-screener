// Dashboard strategies. See README.md in static/js/dashboard for the feature map.

function syncStrategyEditorFromParts() {
  const combined = document.getElementById("strategy-editor");
  if (!document.getElementById("strategy-entry-editor")) {
    return combined ? combined.value : "";
  }
  const entry = String(document.getElementById("strategy-entry-editor")?.value || "").trim();
  const exit = String(document.getElementById("strategy-exit-editor")?.value || "").trim();
  if (!combined) return entry;
  combined.value = exit ? `TRIGGER: ${entry}\nEXIT: ${exit}` : entry;
  return combined.value;
}

function setStrategyEditorParts(content) {
  const raw = String(content || "").trim();
  const entryNode = document.getElementById("strategy-entry-editor");
  const exitNode = document.getElementById("strategy-exit-editor");
  const combined = document.getElementById("strategy-editor");
  const entryMatch = raw.match(/(?:^|\n)\s*(?:TRIGGER|ENTRY)\s*:\s*([\s\S]*?)(?=\n\s*EXIT\s*:|$)/i);
  const exitMatch = raw.match(/(?:^|\n)\s*EXIT\s*:\s*([\s\S]*)$/i);
  if (entryNode) entryNode.value = entryMatch ? entryMatch[1].trim() : raw;
  if (exitNode) exitNode.value = exitMatch ? exitMatch[1].trim() : "";
  if (combined) combined.value = raw;
  return raw;
}

function getActiveEditorDsl() {
  const entry = String(document.getElementById("screen-dsl-editor")?.value || "").trim();
  const exit = String(document.getElementById("screen-exit-editor")?.value || "").trim();
  if (!entry) {
    const strategyEntry = document.getElementById("strategy-entry-editor");
    return strategyEntry ? syncStrategyEditorFromParts().trim() : String(document.getElementById("strategy-editor")?.value || "").trim();
  }
  if (/^\s*(?:universe|strategy)\b/i.test(entry)) {
    return entry;
  }
  const lines = entry.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const metadata = lines.filter((line) => /^(?:candle_age\s+(?:LTE|LE|EQ)\s+\d+|period_1d)$/i.test(line));
  const expression = lines.filter((line) => !metadata.includes(line)).join(" ");
  const exitExpression = exit.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).join(" ");
  return [...metadata, `ENTRY: ${expression}`, exitExpression ? `EXIT: ${exitExpression}` : ""].filter(Boolean).join("\n");
}

function getStrategyEntryDsl() {
  const entryNode = document.getElementById("strategy-entry-editor");
  if (entryNode) return String(entryNode.value || "").trim();
  return String(document.getElementById("strategy-editor")?.value || "").trim();
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
  const backtestSelect = document.getElementById("backtest-preset-select");
  if (backtestSelect) {
    backtestSelect.innerHTML = '<option value="">Choose preset</option>';
    (Array.isArray(screenPresetCatalog.presets) ? screenPresetCatalog.presets : []).forEach((preset) => {
      const option = document.createElement("option");
      option.value = String(preset.name);
      option.textContent = String(preset.name);
      backtestSelect.appendChild(option);
    });
    backtestSelect.value = hasRequested ? requestedValue : "";
  }
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
      dsl: String(preset?.dsl || "").trim(),
      exit_dsl: String(preset?.exit_dsl || preset?.exit || "").trim(),
      filters: normalizeScreenFiltersClient(preset?.filters || SCREEN_DEFAULT_FILTERS),
    })).filter((preset) => preset.name) : [],
  };
  populateScreenPresetSelect();
  const presetName = String(readStickyValue(LAST_SCREEN_PRESET_KEY, screenPresetCatalog.active_name || "")).trim();
  const preset = screenPresetCatalog.presets.find((entry) => entry.name === presetName)
    || screenPresetCatalog.presets.find((entry) => entry.name === screenPresetCatalog.active_name);
  if (preset) {
    if (preset.dsl) {
      const dslEditor = document.getElementById("screen-dsl-editor");
      if (dslEditor) dslEditor.value = preset.dsl;
      const exitEditor = document.getElementById("screen-exit-editor");
      if (exitEditor) exitEditor.value = preset.exit_dsl || preset.exit || "";
      updateScanActionButtonsState();
    } else {
      applyScreenFilters(preset.filters);
    }
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
  syncBacktestPresetPreview();
  const savedFilters = readSavedScreenFilters();
  if (savedFilters) {
    applyScreenFilters(savedFilters);
  }
  return screenPresetCatalog;
}

async function loadDslxStrategy(name) {
  const response = await fetch(`/api/dslx-strategy/${encodeURIComponent(name)}`, { cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Could not load DSLX strategy");
  }
  const editor = document.getElementById("screen-dsl-editor");
  if (editor) {
    editor.value = String(payload.content || "");
    editor.dispatchEvent(new Event("input", { bubbles: true }));
  }
  const filename = document.getElementById("dslx-strategy-filename");
  if (filename) filename.value = String(payload.name || name);
  const screenerFileSelect = document.getElementById("screen-dslx-file-select");
  if (screenerFileSelect) screenerFileSelect.value = String(payload.name || name);
  setLoadedDslxScript(String(payload.name || name));
  document.querySelectorAll("[data-dslx-strategy]").forEach((node) => {
    node.classList.toggle("bg-indigo-700", node.dataset.dslxStrategy === name);
    node.classList.toggle("text-white", node.dataset.dslxStrategy === name);
  });
  showToast(`Loaded DSLX file: ${name}.dslx`);
}

function setLoadedDslxScript(name = "") {
  const status = document.getElementById("screen-dslx-script-status");
  if (!status) return;
  const normalizedName = String(name || "").replace(/\.dslx$/i, "").trim();
  status.textContent = normalizedName
    ? `DSLX: ${normalizedName}.dslx`
    : "DSLX: unsaved draft";
}

async function loadDslxStrategyList() {
  const list = document.getElementById("dslx-strategy-list");
  const screenerFileSelect = document.getElementById("screen-dslx-file-select");
  if (!list && !screenerFileSelect) return;
  if (list) list.textContent = "Loading…";
  try {
    const response = await fetch("/api/dslx-strategies", { cache: "no-store" });
    const strategies = await response.json();
    if (!response.ok) throw new Error("Could not list DSLX strategies");
    if (list) list.innerHTML = "";
    const selectedName = String(screenerFileSelect?.value || "");
    if (screenerFileSelect) {
      screenerFileSelect.innerHTML = '<option value="">Choose DSLX file</option>';
    }
    if (!Array.isArray(strategies) || strategies.length === 0) {
      if (list) list.textContent = "No .dslx files found.";
      return;
    }
    strategies.forEach((name) => {
      if (list) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.dslxStrategy = String(name);
        button.className = "block w-full rounded px-2 py-2 text-left font-mono text-xs text-slate-200 hover:bg-slate-700";
        button.textContent = `${name}.dslx`;
        button.title = "Double-click to load this DSLX file";
        button.addEventListener("dblclick", () => {
          loadDslxStrategy(String(name)).catch((error) => showToast(error.message, true));
        });
        list.appendChild(button);
      }
      if (screenerFileSelect) {
        const option = document.createElement("option");
        option.value = String(name);
        option.textContent = `${name}.dslx`;
        screenerFileSelect.appendChild(option);
      }
    });
    if (screenerFileSelect && strategies.includes(selectedName)) {
      screenerFileSelect.value = selectedName;
    }
  } catch (error) {
    if (list) list.textContent = "Could not load DSLX files.";
    console.error("Failed to load DSLX strategy list", error);
  }
}

function loadDslxStrategyFromScreener(name) {
  if (!name) return;
  loadDslxStrategy(String(name)).catch((error) => showToast(error.message, true));
}

async function reloadSelectedDslxStrategy() {
  const select = document.getElementById("screen-dslx-file-select");
  const name = String(select?.value || "").trim();
  const button = document.getElementById("screen-dslx-reload-btn");
  if (button) button.disabled = true;
  try {
    // Refresh the catalogue as well as the selected content. This makes
    // files added outside the editor visible without restarting Uvicorn.
    await loadDslxStrategyList();
    if (!name) {
      showToast("DSLX file list refreshed.");
      return;
    }
    if (select) select.value = name;
    await loadDslxStrategy(name);
  } catch (error) {
    showToast(error.message || "Could not refresh DSLX strategies", true);
  } finally {
    if (button) button.disabled = false;
  }
}

async function saveDslxStrategy() {
  const filename = String(document.getElementById("dslx-strategy-filename")?.value || "").trim();
  const content = String(document.getElementById("screen-dsl-editor")?.value || "");
  if (!filename) {
    showToast("Enter a DSLX file name before saving.", true);
    return;
  }
  try {
    const response = await fetch("/api/dslx-strategy/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: filename, content }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "Could not save DSLX strategy");
    const savedName = String(payload.name || filename).replace(/\.dslx$/i, "");
    const field = document.getElementById("dslx-strategy-filename");
    if (field) field.value = savedName;
    await loadDslxStrategyList();
    setLoadedDslxScript(savedName);
    showToast(`Saved DSLX file: ${savedName}.dslx`);
  } catch (error) {
    showToast(error.message || "Could not save DSLX strategy", true);
  }
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
  if (preset.dsl) {
    const dslEditor = document.getElementById("screen-dsl-editor");
    if (dslEditor) dslEditor.value = preset.dsl;
    const exitEditor = document.getElementById("screen-exit-editor");
    if (exitEditor) exitEditor.value = preset.exit_dsl || preset.exit || "";
    updateScanActionButtonsState();
  } else {
    applyScreenFilters(preset.filters);
  }
  writeStickyValue(LAST_SCREEN_FILTERS_KEY, JSON.stringify(preset.filters));
  const nameNode = document.getElementById("screen-preset-name");
  if (nameNode) {
    nameNode.value = preset.name;
  }
}

async function applyBacktestPreset(name) {
  const presetName = String(name || "").trim();
  if (!presetName) return;
  await applyScreenPreset(presetName);
  setBacktestSourceMode("editor");
  syncBacktestPresetPreview();
  updateBacktestRunButtonState();
}

function syncBacktestPresetPreview() {
  const entry = String(document.getElementById("screen-dsl-editor")?.value || "");
  const exit = String(document.getElementById("screen-exit-editor")?.value || "");
  const entryPreview = document.getElementById("backtest-entry-preview");
  const exitPreview = document.getElementById("backtest-exit-preview");
  if (entryPreview) entryPreview.value = entry;
  if (exitPreview) exitPreview.value = exit;
}

function syncBacktestDslEditors() {
  const entry = document.getElementById("backtest-entry-preview");
  const exit = document.getElementById("backtest-exit-preview");
  const screenEntry = document.getElementById("screen-dsl-editor");
  const screenExit = document.getElementById("screen-exit-editor");
  if (entry && screenEntry) screenEntry.value = entry.value;
  if (exit && screenExit) screenExit.value = exit.value;
  updateScanActionButtonsState();
  updateBacktestRunButtonState();
}

async function saveBacktestPreset() {
  const name = String(document.getElementById("backtest-preset-name")?.value || "").trim();
  const screenName = document.getElementById("screen-preset-name");
  if (!name) {
    showToast("Enter a preset name first.", true);
    return;
  }
  if (screenName) screenName.value = name;
  await saveScreenPreset();
  const select = document.getElementById("backtest-preset-select");
  if (select) select.value = name;
}

async function saveScreenPreset() {
  const nameNode = document.getElementById("screen-preset-name");
  const presetName = String(nameNode?.value || "").trim();
  if (!presetName) {
    showToast("Enter a preset name first.", true);
    return;
  }
  const dsl = String(document.getElementById("screen-dsl-editor")?.value || "").trim();
  const exitDsl = String(document.getElementById("screen-exit-editor")?.value || "").trim();
  const nextPreset = dsl
    ? { name: presetName, dsl, ...(exitDsl ? { exit_dsl: exitDsl } : {}) }
    : {
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
    ? screenPresetCatalog.presets.filter((preset) => preset && preset.dsl && preset.name !== presetName)
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
      dsl: String(preset?.dsl || "").trim(),
      exit_dsl: String(preset?.exit_dsl || preset?.exit || "").trim(),
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

async function runEditorScreen() {
  const entry = String(document.getElementById("screen-dsl-editor")?.value || "").trim();
  if (!entry) {
    showToast("Write an entry rule before running the screen.", true);
    return;
  }
  showTab("screener");
  await runScreen(entry);
}

function openEditorBacktest() {
  syncBacktestPresetPreview();
  setBacktestSourceMode("editor");
  showTab("backtest");
  updateBacktestRunButtonState();
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
    setStrategyEditorParts("");
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
    setStrategyEditorParts(data.content);
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
  const content = syncStrategyEditorFromParts();
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
  const content = syncStrategyEditorFromParts();
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

