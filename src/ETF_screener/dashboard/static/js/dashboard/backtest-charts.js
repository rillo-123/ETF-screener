// Dashboard backtest-charts. See README.md in static/js/dashboard for the feature map.

function populateBacktestAxisControls(metrics) {
  backtestMetricCatalog = Array.isArray(metrics) && metrics.length > 0 ? metrics : backtestDefaultMetrics();
  const xSelect = document.getElementById("backtest-x-axis");
  const ySelect = document.getElementById("backtest-y-axis");
  if (!xSelect || !ySelect) {
    return;
  }

  const previousX = xSelect.value || "sharpe";
  const previousY = ySelect.value || "return_pct";
  [xSelect, ySelect].forEach((select) => {
    select.innerHTML = "";
    backtestMetricCatalog.forEach((metric) => {
      const opt = document.createElement("option");
      opt.value = metric.key;
      opt.textContent = metric.label;
      select.appendChild(opt);
    });
  });
  const keys = new Set(backtestMetricCatalog.map((metric) => metric.key));
  xSelect.value = keys.has(previousX) ? previousX : "sharpe";
  ySelect.value = keys.has(previousY) ? previousY : "return_pct";
  if (!keys.has(xSelect.value)) {
    xSelect.value = backtestMetricCatalog[0]?.key || "";
  }
  if (!keys.has(ySelect.value)) {
    ySelect.value = backtestMetricCatalog[1]?.key || backtestMetricCatalog[0]?.key || "";
  }
}

function renderBacktestScatter() {
  const chartDiv = document.getElementById("backtest-chart");
  if (!chartDiv || !window.Plotly) {
    return;
  }
  const rows = Array.isArray(backtestTradeDotRows) && backtestTradeDotRows.length > 0
    ? backtestTradeDotRows.filter((row) => !isBacktestTickerExcluded(row.ticker))
    : [];
  if (rows.length === 0) {
    Plotly.purge(chartDiv);
    return;
  }

  const xKey = document.getElementById("backtest-x-axis")?.value || "sharpe";
  const yKey = document.getElementById("backtest-y-axis")?.value || "return_pct";
  const colorBy = "strategy";
  const groups = new Map();
  rows.forEach((row) => {
    const x = Number(row[xKey]);
    const y = Number(row[yKey]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      return;
    }
    const group = String(row[colorBy] || "Other");
    if (!groups.has(group)) {
      groups.set(group, []);
    }
    groups.get(group).push(row);
  });
  const strategyNames = Array.from(groups.keys());

  const traces = Array.from(groups.entries()).map(([group, groupRows]) => ({
    type: "scatter",
    mode: "markers",
    name: group,
    x: groupRows.map((row) => Number(row[xKey])),
    y: groupRows.map((row) => Number(row[yKey])),
    text: groupRows.map((row) => `${row.strategy} / ${row.ticker}`),
    customdata: groupRows.map((row) => [
      row.strategy,
      row.ticker,
      row.exchange,
      Number(row.quality_score || 0).toFixed(2),
      Number(row.return_pct || 0).toFixed(2),
      Number(row.sharpe || 0).toFixed(2),
      Number(row.win_rate_pct || 0).toFixed(2),
      Number(row.max_dd_pct || 0).toFixed(2),
      Number(row.trades || 0),
      Number(row.days_since_entry || 0),
      Number(row.trade_index || 0),
      Number(row.trade_gain_pct || 0).toFixed(2),
      row.estimated ? "estimated avg" : "actual",
      row.sell_date || "",
    ]),
    marker: {
      size: groupRows.map((row) => getBacktestTradeDotSize(row)),
      color: getBacktestGroupColor(colorBy === "strategy" ? group : groupRows[0]?.strategy || group, strategyNames),
      opacity: 0.78,
      line: { color: "#ffffff", width: 1 },
    },
    hovertemplate:
      "<b>%{customdata[0]}</b><br>" +
      "Ticker: %{customdata[1]}<br>" +
      "Universe: %{customdata[2]}<br>" +
      `${getBacktestMetricLabel(xKey)}: %{x:.2f}<br>` +
      `${getBacktestMetricLabel(yKey)}: %{y:.2f}<br>` +
      "Quality: %{customdata[3]}<br>" +
      "Return: %{customdata[4]}%<br>" +
      "Sharpe: %{customdata[5]}<br>" +
      "Win Rate: %{customdata[6]}%<br>" +
      "Max DD: %{customdata[7]}%<br>" +
      "Trades: %{customdata[8]}<br>" +
      "Trade #: %{customdata[10]}<br>" +
      "Trade gain: %{customdata[11]}% (%{customdata[12]})<br>" +
      "Exit: %{customdata[13]}<br>" +
      "Days Since Entry: %{customdata[9]}<extra></extra>",
  }));

  Plotly.newPlot(chartDiv, traces, {
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    margin: { l: 60, r: 20, t: 24, b: 55 },
    xaxis: { title: getBacktestMetricLabel(xKey), zeroline: true, automargin: true },
    yaxis: { title: getBacktestMetricLabel(yKey), zeroline: true, automargin: true },
    legend: { orientation: "h", y: -0.24 },
  }, {
    responsive: true,
    displayModeBar: false,
    displaylogo: false,
  });
}

function renderBacktestStructureRadar() {
  const chartDiv = document.getElementById("backtest-structure-chart");
  if (!chartDiv || !window.Plotly) {
    return;
  }
  const axisCatalog = normalizeBacktestStructureAxisCatalog(backtestStrategyAxisCatalog);
  const summaries = (Array.isArray(backtestStrategySummaries) ? backtestStrategySummaries : [])
    .map((summary, index) => normalizeBacktestStrategySummary(summary, index, axisCatalog))
    .filter((summary) => summary.strategy);
  if (!summaries.length) {
    setBacktestStructurePanelVisible(false);
    Plotly.purge(chartDiv);
    return;
  }
  setBacktestStructurePanelVisible(true);

  const sorted = [...summaries].sort((left, right) => (
    Number(right.structure_score || 0) - Number(left.structure_score || 0)
  ));
  const strategyNames = sorted.map((item) => item.strategy);
  const axisLabelsByKey = new Map(axisCatalog.map((axis) => [axis.key, axis.label]));
  const maxAxis = axisCatalog.reduce((max, axis) => Math.max(max, Number(axis.max || 10) || 10), 10);
  const traces = sorted.map((summary) => {
    const axisOrder = Array.isArray(summary.axis_order) && summary.axis_order.length > 0
      ? summary.axis_order.filter((key) => axisLabelsByKey.has(key))
      : axisCatalog.map((axis) => axis.key);
    const theta = axisOrder.map((key) => axisLabelsByKey.get(key) || key);
    const r = axisOrder.map((key) => Number(summary.structure_axes?.[key] || 0));
    const closedTheta = theta.concat(theta[0] || "");
    const closedR = r.concat(r[0] ?? 0);
    const tags = Array.isArray(summary.structure_tags) ? summary.structure_tags : [];
    return {
      type: "scatterpolar",
      mode: "lines+markers",
      fill: "toself",
      name: summary.strategy,
      theta: closedTheta,
      r: closedR,
      line: {
        color: getBacktestStrategyColor(summary.strategy, strategyNames),
        width: 2.5,
      },
      marker: {
        color: getBacktestStrategyColor(summary.strategy, strategyNames),
        size: 6,
      },
      opacity: 0.55,
      customdata: closedTheta.map((axisLabel, idx) => [
        summary.strategy,
        Number(summary.structure_score || 0).toFixed(2),
        axisLabel,
        Number(closedR[idx] || 0).toFixed(2),
        tags.join(", "),
      ]),
      hovertemplate:
        "<b>%{customdata[0]}</b><br>" +
        "Structure Score: %{customdata[1]}<br>" +
        "Axis: %{customdata[2]}<br>" +
        "Value: %{customdata[3]}<br>" +
        "Tags: %{customdata[4]}<extra></extra>",
    };
  });

  Plotly.newPlot(chartDiv, traces, {
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    margin: { l: 40, r: 40, t: 28, b: 28 },
    legend: { orientation: "h", y: -0.12 },
    polar: {
      bgcolor: "#ffffff",
      radialaxis: {
        visible: true,
        range: [0, maxAxis],
        tickfont: { size: 10 },
        gridcolor: "#dbe4f0",
        linecolor: "#cbd5e1",
      },
      angularaxis: {
        tickfont: { size: 11, color: "#475569" },
        gridcolor: "#e2e8f0",
        linecolor: "#cbd5e1",
      },
    },
  }, {
    responsive: true,
    displayModeBar: false,
    displaylogo: false,
  });
}

function renderBacktestBehaviorRadar() {
  const chartDiv = document.getElementById("backtest-behavior-chart");
  if (!chartDiv || !window.Plotly) {
    return;
  }
  const axisCatalog = backtestDefaultBehaviorAxisCatalog();
  const summaries = (Array.isArray(backtestStrategySummaries) ? backtestStrategySummaries : [])
    .map((summary, index) => normalizeBacktestStrategySummary(summary, index, backtestStrategyAxisCatalog))
    .filter((summary) => summary.strategy && summary.has_behavior_data);
  if (!summaries.length) {
    setBacktestBehaviorPanelVisible(false);
    Plotly.purge(chartDiv);
    return;
  }
  setBacktestBehaviorPanelVisible(true);

  const sorted = [...summaries]
    .map((summary) => ({
      ...summary,
      behavior_profile: summary.behavior_profile || deriveBacktestBehaviorProfile(summary),
    }))
    .sort((left, right) => (
      Number(right.behavior_profile?.behavior_score || 0) - Number(left.behavior_profile?.behavior_score || 0)
    ));
  const strategyNames = sorted.map((item) => item.strategy);
  const axisLabelsByKey = new Map(axisCatalog.map((axis) => [axis.key, axis.label]));
  const traces = sorted.map((summary) => {
    const profile = summary.behavior_profile || deriveBacktestBehaviorProfile(summary);
    const axisOrder = Array.isArray(profile.axis_order) && profile.axis_order.length > 0
      ? profile.axis_order.filter((key) => axisLabelsByKey.has(key))
      : axisCatalog.map((axis) => axis.key);
    const theta = axisOrder.map((key) => axisLabelsByKey.get(key) || key);
    const r = axisOrder.map((key) => Number(profile.behavior_axes?.[key] || 0));
    const closedTheta = theta.concat(theta[0] || "");
    const closedR = r.concat(r[0] ?? 0);
    const closedKeys = axisOrder.concat(axisOrder[0] || "");
    return {
      type: "scatterpolar",
      mode: "lines+markers",
      fill: "toself",
      name: summary.strategy,
      theta: closedTheta,
      r: closedR,
      line: {
        color: getBacktestStrategyColor(summary.strategy, strategyNames),
        width: 2.5,
      },
      marker: {
        color: getBacktestStrategyColor(summary.strategy, strategyNames),
        size: 6,
      },
      opacity: 0.55,
      customdata: closedTheta.map((axisLabel, idx) => {
        const axisKey = closedKeys[idx] || axisOrder[0] || "";
        const rawValue = profile.raw_metrics?.[axisKey] ?? 0;
        return [
          summary.strategy,
          Number(profile.behavior_score || 0).toFixed(2),
          axisLabel,
          Number(closedR[idx] || 0).toFixed(2),
          formatBacktestBehaviorRawMetric(axisKey, rawValue),
        ];
      }),
      hovertemplate:
        "<b>%{customdata[0]}</b><br>" +
        "Behavior Score: %{customdata[1]}<br>" +
        "Axis: %{customdata[2]}<br>" +
        "Normalized: %{customdata[3]} / 10<br>" +
        "Raw: %{customdata[4]}<extra></extra>",
    };
  });

  Plotly.newPlot(chartDiv, traces, {
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    margin: { l: 40, r: 40, t: 28, b: 28 },
    legend: { orientation: "h", y: -0.12 },
    polar: {
      bgcolor: "#ffffff",
      radialaxis: {
        visible: true,
        range: [0, 10],
        tickfont: { size: 10 },
        gridcolor: "#dbe4f0",
        linecolor: "#cbd5e1",
      },
      angularaxis: {
        tickfont: { size: 11, color: "#475569" },
        gridcolor: "#e2e8f0",
        linecolor: "#cbd5e1",
      },
    },
  }, {
    responsive: true,
    displayModeBar: false,
    displaylogo: false,
  });
}

