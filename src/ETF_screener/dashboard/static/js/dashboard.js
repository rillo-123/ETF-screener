// Dashboard startup and HTML event handlers. Feature code lives in dashboard/.
// See dashboard/README.md for the feature map and loading rules.

setupConsoleCapture();

// Show default tab on load
document.addEventListener('DOMContentLoaded', async function() {
  mountPersistentMarketWorkspace();
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
  restoreChartTAParameters();
  const restoredStrategy = await restoreLastCompletedStrategy();
  if (restoredStrategy) {
    console.info("Restored last completed strategy", restoredStrategy);
  }
  restoreBacktestRaceStateFromStorage();
  // Keep the diagram context stable regardless of older saved range choices.
  currentDays = FIXED_CHART_WINDOW_DAYS;
  populateBacktestAxisControls(backtestDefaultMetrics());
  bindBacktestStrategyChooserControls();
  bindBacktestRaceControls();
  renderBacktestRace();
  updateBacktestStrategyCount();
  syncBacktestStrategyCheckboxChrome();
  ensureRepeatedRsiStep();
  ensureRepeatedEventSteps();
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
    await loadDslxStrategyList();
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
  cancelScan,
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
  applyBacktestPreset,
  loadDslxStrategyList,
  loadDslxStrategyFromScreener,
  reloadSelectedDslxStrategy,
  saveDslxStrategy,
  runEditorScreen,
  openEditorBacktest,
  saveBacktestPreset,
  resetDashboardTabPreference,
  runScreen,
  saveScreenPreset,
  saveAsStrategy,
  saveFromModal,
  saveStrategy,
  setNavScanProgress,
  activateCustomTickerList,
  setActiveCustomTickerList,
  setBacktestSourceMode,
  setListBuilderExchange,
  setListBuilderSearch,
  setListBuilderList,
  toggleListBuilderSelectedOnly,
  setScanSource,
  stepDecimalInput,
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

