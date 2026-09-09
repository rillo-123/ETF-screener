// Dashboard shell. See README.md in static/js/dashboard for the feature map.

function getDashboardTabs() {
  return DASHBOARD_TABS
    .map((name) => document.getElementById(`tab-${name}`))
    .filter(Boolean);
}

function mountPersistentMarketWorkspace() {
  const workspace = document.getElementById("global-workspace");
  const chartCard = document.getElementById("chart-card");
  if (workspace && chartCard && chartCard.parentElement !== workspace) {
    workspace.appendChild(chartCard);
  }
}

function updatePersistentMarketWorkspaceVisibility(tab) {
  const workspace = document.getElementById("global-workspace");
  if (workspace) {
    workspace.classList.toggle("hidden", tab !== "screener");
  }
}

function normalizeDashboardTab(value) {
  const cleaned = String(value || "screener").trim().toLowerCase();
  return DASHBOARD_TABS.includes(cleaned) ? cleaned : "screener";
}

function updateTabChrome(tab) {
  const screenerControls = document.getElementById("nav-screener-controls");
  const chartRangeControls = document.getElementById("nav-chart-range-controls");
  const context = document.getElementById("nav-tab-context");
  if (screenerControls) {
    screenerControls.classList.toggle("hidden", tab !== "screener" && tab !== "editor");
  }
  if (chartRangeControls) {
    chartRangeControls.classList.toggle("hidden", tab === "screener");
  }
  if (!context) {
    return;
  }
  if (tab === "playbook") {
    context.textContent = "Graph Playground: experiment with visual trade setups";
  } else if (tab === "editor") {
    context.textContent = "DSLX Editor: shape entry and exit rules side by side";
  } else {
    context.textContent = "Screener: place the event markers, then click Run Screener";
  }
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
  mountPersistentMarketWorkspace();
  updatePersistentMarketWorkspaceVisibility(tab);
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

