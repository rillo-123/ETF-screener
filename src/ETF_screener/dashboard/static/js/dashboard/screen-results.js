// Dashboard screen-results. See README.md in static/js/dashboard for the feature map.

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

function matchStrategyNames(match) {
  const names = [];
  const add = (value) => {
    const name = String(value || "").trim();
    if (name && !names.includes(name)) names.push(name);
  };
  if (Array.isArray(match?.strategies)) match.strategies.forEach(add);
  add(match?.strategy);
  add(match?.strategy_name);
  if (names.length === 0) add(lastScreenMeta?.strategy_name);
  return names;
}

function renderMatchStrategyBadges(match) {
  return matchStrategyNames(match).map((name) => (
    `<span class="inline-flex max-w-full items-center rounded-full border border-violet-200 bg-violet-50 px-1.5 py-0.5 text-[9px] font-bold leading-none text-violet-700" title="Matched by strategy: ${escapeHtml(name)}">${escapeHtml(name)}</span>`
  )).join("");
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
    for (const index of [1, 2, 3]) {
      const selected = String(filters[`ema_slope_${index}`] || "any");
      const state = String(item[`ema_slope_${index}_state`] || "unknown");
      if (selected !== "any" && selected !== state) {
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
  if (Array.isArray(filters.rsi_events) && filters.rsi_events.length > 1) return false;
  const localKeys = [
    "volume_range", "macd_event_enabled", "rsi_event_enabled", "stoch_event_enabled",
    "supertrend_event_enabled", "macd_event_age", "rsi_event_age", "stoch_event_age", "supertrend_event_age",
    "ema_slope_period_1", "ema_slope_period_2", "ema_slope_period_3",
    "ema_slope_1", "ema_slope_2", "ema_slope_3",
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
          <div class="flex flex-col"><div class="flex flex-wrap items-center gap-1.5"><span class="font-bold text-slate-800 text-lg leading-none">${escapeHtml(item.ticker)}</span><span class="text-[10px] font-bold text-indigo-400">#${idx + 1}</span>${renderMatchStrategyBadges(item)}</div><span class="mt-1 text-[11px] text-slate-500">${escapeHtml(item.name || "")}</span><span class="text-[10px] text-indigo-600 mt-1 uppercase tracking-wider">${escapeHtml(item.status || "TRENDING")}</span></div>
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

function createScreenMatchCard(item, index) {
  const card = document.createElement("div");
  card.className =
    "ticker-card p-3 bg-slate-50 border-l-4 border-indigo-500 rounded shadow-sm hover:shadow-md hover:bg-indigo-50 cursor-pointer transition-all";
  card.onclick = () => loadChart(item.ticker);
  const statusText = item.status || "TRENDING";
  const statusColor = item.status === "Entry Signal"
    ? "text-emerald-500 animate-pulse font-bold"
    : "text-indigo-600";
  const closeVal = Number(item.close ?? 0);
  const volumeVal = Number(item.recent_avg_volume ?? item.volume ?? 0);
  const changePctVal = Number(item.change_pct ?? 0);
  const scoreVal = Number(item.score ?? 0);
  const rsiVal = Number(item.rsi ?? 0);
  const sequenceText = String(item.event_sequence || "").trim();
  const changeVal = Number.isFinite(changePctVal) ? changePctVal.toFixed(2) : "0.00";
  const changeColor = parseFloat(changeVal) >= 0 ? "text-emerald-500" : "text-rose-500";
  const sign = parseFloat(changeVal) >= 0 ? "+" : "";

  card.innerHTML = `
    <div class="flex justify-between items-start">
      <div class="flex flex-col">
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="font-bold text-slate-800 text-lg leading-none">${escapeHtml(item.ticker || "")}</span>
          <span class="text-[10px] font-bold text-indigo-400">#${index + 1}</span>
          ${renderMatchStrategyBadges(item)}
        </div>
        <span class="mt-1 text-[11px] text-slate-500">${escapeHtml(item.name || "")}</span>
        <span class="text-[10px] ${statusColor} mt-1 uppercase tracking-wider">${escapeHtml(statusText)}</span>
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
    </div>`;
  return card;
}

function appendLiveScreenMatch(item) {
  if (!item || !item.ticker) return;
  const key = `${item.strategy || ""}|${item.ticker}|${item.days_since_entry ?? item.age ?? 0}`;
  if (liveScreenMatchKeys.has(key)) return;
  liveScreenMatchKeys.add(key);
  liveScreenMatches.push(item);
  const list = document.getElementById("ticker-list");
  if (list && liveScreenMatches.length === 1) {
    list.innerHTML = "";
    list.style.opacity = "1";
  }
  if (list && liveScreenMatches.length <= 200) {
    list.appendChild(createScreenMatchCard(item, liveScreenMatches.length - 1));
  }
  const count = document.getElementById("match-count");
  if (count) count.textContent = String(liveScreenMatches.length);
}

