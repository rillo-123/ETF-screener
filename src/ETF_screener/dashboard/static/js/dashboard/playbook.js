// Dashboard playbook. See README.md in static/js/dashboard for the feature map.

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
        <div class="mt-1 text-xs text-slate-500">Rules ${Number(row.final_score || 0).toFixed(0)}/6 • ${row.label || ""}</div>
      </td>
      <td class="px-4 py-3 align-top font-mono text-slate-800">${Number(row.entry || 0).toFixed(2)}</td>
      <td class="px-4 py-3 align-top font-mono text-slate-800">
        ${Number(row.stop || 0).toFixed(2)}
        <div class="mt-1 text-xs text-slate-500">${row.support_basis ? `${row.support_basis} ${Number(row.support_level || 0).toFixed(2)}` : "No nearby support"}</div>
      </td>
      <td class="px-4 py-3 align-top font-mono text-slate-800">
        ${row.target !== null && row.target !== undefined ? Number(row.target).toFixed(2) : "-"}
        <div class="mt-1 text-xs text-slate-500">${row.target_basis || "No target"}</div>
      </td>
      <td class="px-4 py-3 align-top">
        <div class="font-semibold text-slate-800">${Number(row.max_loss_pct || 0).toFixed(2)}%</div>
        <div class="mt-1 text-xs text-slate-500">${row.reward_risk_ratio !== null && row.reward_risk_ratio !== undefined ? `${Number(row.reward_risk_ratio).toFixed(1)}R upside` : "R/R n/a"}</div>
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

