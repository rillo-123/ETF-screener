// Dashboard utils. See README.md in static/js/dashboard for the feature map.

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

function readSavedScreenFilters() {
  try {
    const raw = localStorage.getItem(LAST_SCREEN_FILTERS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch (err) {
    return null;
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

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char] || char);
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

// --- Toast notification ---
function showToast(msg, isError = false) {
  const t = document.createElement("div");
  t.textContent = msg;
  t.className = `fixed bottom-6 right-6 ${isError ? 'bg-red-600' : 'bg-emerald-600'} text-white py-2 px-4 rounded-lg shadow-lg z-[200] text-sm font-bold transition-opacity`;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; setTimeout(() => t.remove(), 400); }, 2800);
}

