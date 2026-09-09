// Dashboard market-data. See README.md in static/js/dashboard for the feature map.

async function loadMarketStatus(source = tickerScanScope) {
  const marketStatus = document.getElementById("shortlist-market-status");
  const refreshButton = document.getElementById("shortlist-refresh-btn");
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
      if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.textContent = "Refresh Universe";
        refreshButton.title = "Refresh the stale data for the selected universe";
      }
      marketStatus.className = "text-xs font-bold uppercase tracking-wide text-amber-600";
      marketStatus.textContent = `${getActiveSourceLabel(normalizedSource)}: market data needs top-up · universe ${Number(data.tracked_tickers || 0)} · latest ${data.latest_market_date || "unknown"} · stale ${Number(data.stale_tickers || 0)} · missing ${Number(data.missing_tickers || 0)}`;
    } else {
      if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.textContent = "Data Fresh";
        refreshButton.title = "The selected universe is already fresh";
      }
      marketStatus.className = "text-xs font-bold uppercase tracking-wide text-emerald-600";
      marketStatus.textContent = `${getActiveSourceLabel(normalizedSource)}: market data fresh through ${data.latest_market_date || "unknown"} · universe ${Number(data.tracked_tickers || 0)} · ${Number(data.fresh_tickers || data.tracked_tickers || 0)} active tickers`;
    }
    if (Number(document.getElementById("refresh-history-years")?.value || 0) > 0 && refreshButton) {
      refreshButton.disabled = false;
      refreshButton.textContent = "Download History";
      refreshButton.title = "Download available history for the selected universe";
    }
    if (marketHistoryRefreshRunning && refreshButton) refreshButton.disabled = true;
    return data;
  } catch (err) {
    if (refreshButton) {
      refreshButton.disabled = false;
      refreshButton.textContent = "Refresh Universe";
      refreshButton.title = "Refresh the selected market data";
    }
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
    await refreshMarketData(options);
    refreshed = true;
  }
  if (
    options.refreshStaleInBackground === true
    && status
    && (
      Number(status.missing_tickers || 0)
      + Number(status.stale_tickers || 0)
    ) > 0
  ) {
    startBackgroundMarketDataRefresh(status, options);
  }
  return { status, refreshed };
}

function startBackgroundMarketDataRefresh(status, options = {}) {
  const queuedCount = (
    Number(status?.missing_tickers || 0)
    + Number(status?.stale_tickers || 0)
  );
  if (
    marketDataBackgroundRefreshPromise
    ||
    marketDataBackgroundRefreshAttempted
    || queuedCount <= 0
  ) {
    return marketDataBackgroundRefreshPromise;
  }
  marketDataBackgroundRefreshAttempted = true;
  const source = normalizeScanScope(tickerScanScope);
  const params = new URLSearchParams({
    depth: "180",
    max_workers: "2",
    force: "false",
    stale_after_days: "0",
    // Include stale cached symbols as well as never-cached symbols. The
    // screen continues against the local cache while this request runs.
    missing_only: "false",
    source,
  });
  const requestId = createRunRequestId();
  const abortController = new AbortController();
  marketDataBackgroundRefreshRequestId = requestId;
  marketDataBackgroundRefreshAbortController = abortController;
  params.set("request_id", requestId);
  if (source === "list") {
    const tickerList = getUniverseFilterParams().get("ticker_list");
    if (tickerList) params.set("ticker_list", tickerList);
  }
  const marketStatus = document.getElementById("shortlist-market-status");
  if (marketStatus) {
    marketStatus.textContent += " · updating stale market data in background";
  }
  setBackgroundDataProgress(true, queuedCount);
  marketDataBackgroundRefreshPromise = fetch(
    `/api/market-data/refresh?${params.toString()}`,
    { method: "POST", signal: abortController.signal },
  )
    .then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "Missing-data backfill failed");
      }
      if (Number(payload.refreshed || 0) > 0) {
        showToast(
          `Updated ${Number(payload.refreshed)} market symbol${Number(payload.refreshed) === 1 ? "" : "s"}.`,
        );
      }
      return loadMarketStatus(source);
    })
    .catch((error) => {
      marketDataBackgroundRefreshAttempted = false;
      if (error?.name !== "AbortError") {
        console.warn("Automatic market-data refresh failed", error);
      }
      return null;
    })
    .finally(() => {
      marketDataBackgroundRefreshPromise = null;
      marketDataBackgroundRefreshAbortController = null;
      marketDataBackgroundRefreshRequestId = null;
      setBackgroundDataProgress(false);
      syncScreenerRunButtonState(Boolean(scanAbortController));
    });
  syncScreenerRunButtonState(Boolean(scanAbortController));
  return marketDataBackgroundRefreshPromise;
}

async function ensureFreshMarketData() {
  return ensureGuiMarketBackbone({ allowRefresh: true });
}

let marketHistoryRefreshRunning = false;

async function refreshMarketData(options = {}) {
  if (marketHistoryRefreshRunning) return;
  marketHistoryRefreshRunning = true;
  const historyYears = Number(options.historyYears || 0);
  const historySelect = document.getElementById("refresh-history-years");
  if (historySelect) historySelect.disabled = true;
  const source = normalizeScanScope(tickerScanScope);
  const shortlistRefreshBtn = document.getElementById("shortlist-refresh-btn");
  const marketStatus = document.getElementById("shortlist-market-status");
  const shortlistStatus = document.getElementById("shortlist-status");
  const activeSourceLabel = getActiveSourceLabel(source);
  let refreshSucceeded = false;

  if (shortlistRefreshBtn) {
    shortlistRefreshBtn.disabled = true;
    shortlistRefreshBtn.textContent = historyYears ? "Downloading History..." : "Refreshing Universe...";
  }
  if (marketStatus) {
    marketStatus.className = "text-xs font-bold uppercase tracking-wide text-indigo-600";
    marketStatus.textContent = historyYears
      ? `Downloading up to ${historyYears} years for ${activeSourceLabel}; shorter histories may be available...`
      : `Refreshing ${activeSourceLabel} market data and rebuilding shortlist...`;
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
    startJobProgressPolling("market-refresh", "Market Refresh", "Preparing market refresh...");
    const refreshParams = new URLSearchParams();
    refreshParams.set("depth", "180");
    refreshParams.set("history_years", String(historyYears));
    refreshParams.set("max_workers", "2");
    // Refresh only stale/missing symbols. A manual click should not force
    // a full-market refetch when the status already identifies a small
    // stale subset.
    refreshParams.set("force", "false");
    refreshParams.set("stale_after_days", "0");
    refreshParams.set("source", source);
    const requestId = String(options.requestId || "").trim();
    if (requestId) {
      refreshParams.set("request_id", requestId);
    }
    if (source === "list") {
      const universeParams = getUniverseFilterParams();
      const tickerList = universeParams.get("ticker_list");
      if (tickerList) {
        refreshParams.set("ticker_list", tickerList);
      }
    }
    const resp = await fetch(`/api/market-data/refresh?${refreshParams.toString()}`, {
      method: "POST",
      signal: options.signal,
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Market refresh failed");
    }
    refreshSucceeded = true;

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
    if (err && err.name === "AbortError") {
      return;
    }
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
    marketHistoryRefreshRunning = false;
    if (historySelect) historySelect.disabled = false;
    if (refreshSucceeded) await loadMarketStatus();
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
      if (!refreshSucceeded) {
        shortlistRefreshBtn.disabled = false;
        shortlistRefreshBtn.textContent = "Refresh Universe";
      }
    }
  }
}

