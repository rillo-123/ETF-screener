// Dashboard progress. See README.md in static/js/dashboard for the feature map.

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

function stopScreenEventPolling() {
  if (screenEventPoller) clearInterval(screenEventPoller);
  screenEventPoller = null;
  screenEventPollInFlight = false;
}

function startScreenEventPolling(runId, onProgress) {
  stopScreenEventPolling();
  screenEventSeq = 0;
  liveScreenMatches = [];
  liveScreenMatchKeys = new Set();
  let seenRun = false;
  const poll = async () => {
    if (screenEventPollInFlight) return;
    screenEventPollInFlight = true;
    try {
      const response = await fetch(
        `/api/screen/events?run_id=${encodeURIComponent(runId)}&after_seq=${screenEventSeq}&limit=500`,
        { cache: "no-store" },
      );
      if (!response.ok) return;
      const snapshot = await response.json();
      const events = Array.isArray(snapshot.events) ? snapshot.events : [];
      if (snapshot.active || events.length) seenRun = true;
      events.forEach((event) => {
        screenEventSeq = Math.max(screenEventSeq, Number(event.seq || 0));
        if (event.type === "match") {
          appendLiveScreenMatch(event.payload?.match);
        } else if (event.type === "progress" && typeof onProgress === "function") {
          onProgress(event.payload || {});
        }
      });
      if (seenRun && !snapshot.active) stopScreenEventPolling();
    } catch (err) {
      console.warn("Screen event polling failed", err);
    } finally {
      screenEventPollInFlight = false;
    }
  };
  screenEventPoller = setInterval(poll, 500);
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
  if (job === "market-refresh") {
    const downloading = phase === "refreshing";
    setNavScanProgress({
      show: true,
      contextLabel: downloading ? "Downloading prices" : label,
      contextText: text,
      contextPct: downloading ? Math.max(0, Math.min(100, (pct - 5) / 75 * 100)) : pct,
      contextWorking: active,
    });
  }
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

function startJobProgressPolling(expectedJob, fallbackLabel = "Global", fallbackText = "Waiting...") {
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
    globalText: fallbackText,
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
    pageScanProgress: document.getElementById("page-scan-progress"),
    pageBar: document.getElementById("page-progress-bar"),
    pageText: document.getElementById("page-progress-text"),
    pageLabel: document.getElementById("page-progress-label"),
    pagePhaseBar: document.getElementById("page-phase-progress-bar"),
    pagePhaseText: document.getElementById("page-phase-progress-text"),
    pagePhaseLabel: document.getElementById("page-phase-progress-label"),
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
    nodes.pagePanel.hidden = !marketDataBackgroundRefreshPromise;
    pageOverallProgressPct = 0;
    pagePhaseProgressPct = 0;
    pagePhaseProgressKey = "";
    if (nodes.pageBar) nodes.pageBar.style.width = "0%";
    if (nodes.pagePhaseBar) nodes.pagePhaseBar.style.width = "0%";
  }
  if (show === true && nodes.pageScanProgress) {
    nodes.pageScanProgress.hidden = false;
  } else if (show === false && nodes.pageScanProgress) {
    nodes.pageScanProgress.hidden = true;
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
    const nextLabel = state.globalLabel || nodes.globalLabel?.textContent || "Overall";
    nodes.pageLabel.textContent = nextLabel;
  }
  if (nodes.pageText) {
    const nextText = state.globalText || nodes.globalText?.textContent || "Waiting…";
    nodes.pageText.textContent = nextText;
  }
  if (nodes.pageBar) {
    if (state.globalPct !== undefined) {
      const pct = Math.max(0, Math.min(100, Number(state.globalPct) || 0));
      pageOverallProgressPct = Math.max(pageOverallProgressPct, pct);
      nodes.pageBar.style.width = `${pageOverallProgressPct}%`;
    }
    nodes.pageBar.classList.toggle(
      "animate-pulse",
      Boolean(state.globalWorking),
    );
  }
  if (nodes.pagePhaseLabel) {
    const nextLabel = state.contextLabel || nodes.contextLabel?.textContent || "Current phase";
    if (nextLabel !== pagePhaseProgressKey) {
      pagePhaseProgressKey = nextLabel;
      pagePhaseProgressPct = 0;
      if (nodes.pagePhaseBar) nodes.pagePhaseBar.style.width = "0%";
    }
    nodes.pagePhaseLabel.textContent = nextLabel;
  }
  if (nodes.pagePhaseText) {
    const nextText = state.contextText || nodes.contextText?.textContent || "Working…";
    nodes.pagePhaseText.textContent = nextText;
  }
  if (nodes.pagePhaseBar) {
    if (state.contextPct !== undefined) {
      const pct = Math.max(0, Math.min(100, Number(state.contextPct) || 0));
      pagePhaseProgressPct = Math.max(pagePhaseProgressPct, pct);
      nodes.pagePhaseBar.style.width = `${pagePhaseProgressPct}%`;
    }
    nodes.pagePhaseBar.classList.toggle(
      "animate-pulse",
      Boolean(state.contextWorking),
    );
  }
}

function setBackgroundDataProgress(show, queuedCount = 0) {
  const banner = document.getElementById("page-progress-banner");
  const panel = document.getElementById("page-background-progress");
  const text = document.getElementById("page-background-progress-text");
  if (panel) panel.hidden = !show;
  if (text && show) {
    const count = Math.max(0, Number(queuedCount) || 0);
    text.textContent = `${count} stale or missing symbol${count === 1 ? "" : "s"} queued · active`;
  }
  if (banner) {
    const scanVisible = !document.getElementById("page-scan-progress")?.hidden;
    banner.hidden = !show && !scanVisible;
  }
}

