import os
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def _run_dashboard_server():
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    port = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(src_dir)
        if not existing_pythonpath
        else f"{src_dir}{os.pathsep}{existing_pythonpath}"
    )

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ETF_screener.dashboard.app_fast:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=repo_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("Dashboard server exited before becoming ready.")
            try:
                with urllib.request.urlopen(f"{base_url}/", timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Timed out waiting for dashboard server to start.")
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def test_backtest_scatter_updates_from_streamed_events_with_strategy_colors(page):
    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )

    page.set_content(
        """
        <html>
          <body>
            <select id="ticker-select"></select>
            <select id="strategy-select"></select>
            <div id="backtest-empty"></div>
            <div id="backtest-content" class="hidden">
              <div id="bt-strategy"></div>
              <div id="bt-count"></div>
              <div id="bt-best-quality"></div>
              <div id="bt-avg-return"></div>
              <div id="bt-avg-sharpe"></div>
              <div id="bt-best-structure"></div>
              <select id="backtest-x-axis"></select>
              <select id="backtest-y-axis"></select>
              <select id="backtest-color-by">
                <option value="strategy">Strategy</option>
              </select>
              <div id="backtest-chart"></div>
              <div id="backtest-structure-chart"></div>
              <table><tbody id="backtest-table-body"></tbody></table>
            </div>
          </body>
        </html>
        """,
        wait_until="domcontentloaded",
    )
    page.evaluate(
        """
        () => {
          window.__plots = [];
          window.Plotly = {
            purge() {},
            relayout() {},
            downloadImage() {},
            newPlot: async (node, data, layout, config) => {
              window.__plots.push({ data, layout, config });
            },
          };
          window.alert = () => {};
          window.fetch = async () => ({ ok: true, json: async () => ({}) });
          const originalGetElementById = document.getElementById.bind(document);
          document.getElementById = (id) => {
            let node = originalGetElementById(id);
            if (node) return node;
            node = document.createElement(id.includes("select") ? "select" : "div");
            node.id = id;
            node.style.display = "none";
            document.body.appendChild(node);
            return node;
          };
        }
        """
    )
    page.add_script_tag(path=str(dashboard_js))
    page.evaluate(
        """
        async () => {
          await window.dashboardReadyPromise;
          window.prepareBacktestLiveResults("Running...");
          window.mergeBacktestScatterRows({
            strategy: "Alpha",
            ticker: "AAA.DE",
            trades: 3,
            return_pct: 12,
            win_rate_pct: 66,
            profit_factor: 1.8,
            sharpe: 1.4,
            max_dd_pct: 5,
            quality_score: 18,
          });
          window.mergeBacktestScatterRows({
            strategy: "Beta",
            ticker: "BBB.ST",
            trades: 2,
            return_pct: 7,
            win_rate_pct: 55,
            profit_factor: 1.2,
            sharpe: 0.8,
            max_dd_pct: 4,
            quality_score: 9,
          });
          await new Promise((resolve) => setTimeout(resolve, 250));
        }
        """
    )

    assert "hidden" not in (
        page.locator("#backtest-content").get_attribute("class") or ""
    )
    assert page.locator("#bt-count").inner_text() == "2"
    assert page.locator("#backtest-table-body tr").count() == 2
    traces = page.evaluate(
        "() => [...window.__plots].reverse().find((plot) => plot.data.some((trace) => trace.type === 'scatter'))?.data || []"
    )
    assert [trace["name"] for trace in traces] == ["Alpha", "Beta"]
    assert traces[0]["marker"]["color"] != traces[1]["marker"]["color"]
    assert traces[0]["x"] == [1.4]
    assert traces[0]["y"] == [12]


def test_backtest_scatter_excludes_checked_ticker_from_plot_only(page):
    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )

    page.set_content(
        """
        <html>
          <body>
            <select id="ticker-select"></select>
            <select id="strategy-select"></select>
            <div id="backtest-empty"></div>
            <div id="backtest-content" class="hidden">
              <div id="bt-strategy"></div>
              <div id="bt-count"></div>
              <div id="bt-best-quality"></div>
              <div id="bt-avg-return"></div>
              <div id="bt-avg-sharpe"></div>
              <div id="bt-best-structure"></div>
              <select id="backtest-x-axis"></select>
              <select id="backtest-y-axis"></select>
              <select id="backtest-color-by">
                <option value="strategy">Strategy</option>
              </select>
              <div id="backtest-chart"></div>
              <div id="backtest-structure-chart"></div>
              <table><tbody id="backtest-table-body"></tbody></table>
            </div>
          </body>
        </html>
        """,
        wait_until="domcontentloaded",
    )
    page.evaluate(
        """
        () => {
          window.__plots = [];
          window.Plotly = {
            purge() {},
            relayout() {},
            downloadImage() {},
            newPlot: async (node, data, layout, config) => {
              window.__plots.push({ data, layout, config });
            },
          };
          window.alert = () => {};
          window.fetch = async () => ({ ok: true, json: async () => ({}) });
          const originalGetElementById = document.getElementById.bind(document);
          document.getElementById = (id) => {
            let node = originalGetElementById(id);
            if (node) return node;
            node = document.createElement(id.includes("select") ? "select" : "div");
            node.id = id;
            node.style.display = "none";
            document.body.appendChild(node);
            return node;
          };
        }
        """
    )
    page.add_script_tag(path=str(dashboard_js))
    page.evaluate(
        """
        async () => {
          await window.dashboardReadyPromise;
          window.prepareBacktestLiveResults("Running...");
          window.mergeBacktestScatterRows([
            {
              strategy: "Alpha",
              ticker: "AAA.DE",
              trades: 3,
              return_pct: 12,
              win_rate_pct: 66,
              profit_factor: 1.8,
              sharpe: 1.4,
              max_dd_pct: 5,
              quality_score: 18,
            },
            {
              strategy: "Beta",
              ticker: "BBB.ST",
              trades: 2,
              return_pct: 7,
              win_rate_pct: 55,
              profit_factor: 1.2,
              sharpe: 0.8,
              max_dd_pct: 4,
              quality_score: 9,
            },
          ]);
          await new Promise((resolve) => setTimeout(resolve, 250));
        }
        """
    )

    assert page.locator("#backtest-table-body tr").count() == 2
    assert page.locator("#backtest-table-body input[type='checkbox']").count() == 2
    assert (
        page.locator("#backtest-table-body tr").first.locator("td").count() == 11
    )
    assert (
        page.locator("#backtest-table-body tr").nth(1).locator("td").count() == 11
    )
    assert (
        page.locator("#backtest-table-body tr")
        .first.locator("td")
        .last.locator("input[type='checkbox']")
        .is_visible()
    )
    assert (
        page.locator("#backtest-table-body tr")
        .nth(1).locator("td")
        .last.locator("input[type='checkbox']")
        .is_visible()
    )
    assert (
        page.locator("#backtest-table-body tr")
        .first.locator("td")
        .last.inner_text()
        .strip()
        == "Exclude"
    )

    page.locator("#backtest-table-body input[type='checkbox']").first.check()
    page.wait_for_timeout(250)

    traces = page.evaluate(
        "() => [...window.__plots].reverse().find((plot) => plot.data.some((trace) => trace.type === 'scatter'))?.data || []"
    )
    assert [trace["name"] for trace in traces] == ["Beta"]
    assert page.locator("#backtest-table-body tr").count() == 2
    assert page.locator("#backtest-table-body input[type='checkbox']").first.is_checked()

    page.locator("#backtest-table-body input[type='checkbox']").first.uncheck()
    page.wait_for_timeout(250)

    traces = page.evaluate(
        "() => [...window.__plots].reverse().find((plot) => plot.data.some((trace) => trace.type === 'scatter'))?.data || []"
    )
    assert [trace["name"] for trace in traces] == ["Alpha", "Beta"]
    assert (
        not page.locator("#backtest-table-body input[type='checkbox']").first.is_checked()
    )


def test_backtest_structure_radar_renders_selected_saved_strategies(page):
    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )

    page.set_content(
        """
        <html>
          <body>
            <div id="scan-source-toggle"></div>
            <button id="backtest-run-btn"></button>
            <select id="ticker-select"></select>
            <select id="strategy-select"></select>
            <textarea id="strategy-editor"></textarea>
            <div id="backtest-empty"></div>
            <div id="backtest-content" class="hidden">
              <div id="bt-strategy"></div>
              <div id="bt-count"></div>
              <div id="bt-best-quality"></div>
              <div id="bt-avg-return"></div>
              <div id="bt-avg-sharpe"></div>
              <div id="bt-best-structure"></div>
              <select id="backtest-x-axis"></select>
              <select id="backtest-y-axis"></select>
              <select id="backtest-color-by">
                <option value="strategy">Strategy</option>
              </select>
              <div id="backtest-chart"></div>
              <div id="backtest-structure-chart"></div>
              <table><tbody id="backtest-table-body"></tbody></table>
            </div>
            <label><input class="backtest-strategy-checkbox" type="checkbox" value="Alpha" checked></label>
            <label><input class="backtest-strategy-checkbox" type="checkbox" value="Beta" checked></label>
          </body>
        </html>
        """,
        wait_until="domcontentloaded",
    )
    page.evaluate(
        """
        () => {
          window.__plots = [];
          window.Plotly = {
            purge() {},
            relayout() {},
            downloadImage() {},
            newPlot: async (node, data, layout, config) => {
              window.__plots.push({ nodeId: node.id, data, layout, config });
            },
          };
          window.alert = () => {};
          const originalGetElementById = document.getElementById.bind(document);
          document.getElementById = (id) => {
            let node = originalGetElementById(id);
            if (node) return node;
            node = document.createElement(id.includes("select") ? "select" : id.includes("btn") ? "button" : "div");
            node.id = id;
            node.style.display = "none";
            document.body.appendChild(node);
            return node;
          };
          window.fetch = async (url) => {
            const text = String(url);
            if (text.includes("/api/market-status")) {
              return {
                ok: true,
                json: async () => ({
                  today: "2026-06-07",
                  latest_market_date: "2026-06-07",
                  days_stale: 0,
                  is_stale: false,
                  tracked_tickers: 2,
                  fresh_tickers: 2,
                  missing_tickers: 0,
                  stale_tickers: 0,
                }),
              };
            }
            if (text.includes("/api/ticker-universe")) {
              return {
                ok: true,
                json: async () => ({
                  items: [
                    { ticker: "AAA.DE", name: "AAA", label: "AAA", exchange: "xetra" },
                    { ticker: "BBB.ST", name: "BBB", label: "BBB", exchange: "sweden" },
                  ],
                }),
              };
            }
            if (text.includes("/api/backtest/matrix")) {
              return {
                ok: true,
                json: async () => ({
                  source_type: "saved_matrix",
                  strategies: ["Alpha", "Beta"],
                  summary: {
                    count: 2,
                    strategy_count: 2,
                    best_quality: 10,
                    avg_return: 9.5,
                    avg_sharpe: 1.1,
                  },
                  metrics: [],
                  strategy_axis_catalog: [
                    { key: "trend_context", label: "Trend Context", max: 10 },
                    { key: "confirmation_depth", label: "Confirmation Depth", max: 10 },
                    { key: "trigger_precision", label: "Trigger Precision", max: 10 },
                    { key: "exit_discipline", label: "Exit Discipline", max: 10 },
                    { key: "risk_control", label: "Risk Control", max: 10 },
                    { key: "time_discipline", label: "Time Discipline", max: 10 },
                  ],
                  strategy_summaries: [
                    {
                      strategy: "Alpha",
                      avg_quality_score: 10,
                      return_pct: 12,
                      sharpe: 1.2,
                      win_rate_pct: 60,
                      profit_factor: 1.5,
                      max_dd_pct: 5,
                      trades: 4,
                      structure_score: 8.5,
                      structure_axes: {
                        trend_context: 9,
                        confirmation_depth: 8,
                        trigger_precision: 7,
                        exit_discipline: 8,
                        risk_control: 9,
                        time_discipline: 10,
                      },
                      structure_tags: ["trend_gated", "has_time_stop"],
                    },
                    {
                      strategy: "Beta",
                      avg_quality_score: 9,
                      return_pct: 7,
                      sharpe: 1.0,
                      win_rate_pct: 55,
                      profit_factor: 1.2,
                      max_dd_pct: 4,
                      trades: 3,
                      structure_score: 6.25,
                      structure_axes: {
                        trend_context: 5,
                        confirmation_depth: 6,
                        trigger_precision: 8,
                        exit_discipline: 6,
                        risk_control: 7,
                        time_discipline: 5.5,
                      },
                      structure_tags: ["event_trigger"],
                    },
                  ],
                  race: {
                    selected_strategies: ["Alpha", "Beta"],
                    lanes: [
                      {
                        strategy: "Alpha",
                        status: "done",
                        progress_pct: 100,
                        detail: "Done",
                        avg_quality_score: 10,
                        return_pct: 12,
                        sharpe: 1.2,
                        win_rate_pct: 60,
                        profit_factor: 1.5,
                        max_dd_pct: 5,
                        trades: 4,
                        structure_score: 8.5,
                        structure_axes: {
                          trend_context: 9,
                          confirmation_depth: 8,
                          trigger_precision: 7,
                          exit_discipline: 8,
                          risk_control: 9,
                          time_discipline: 10,
                        },
                        structure_tags: ["trend_gated", "has_time_stop"],
                      },
                      {
                        strategy: "Beta",
                        status: "done",
                        progress_pct: 100,
                        detail: "Done",
                        avg_quality_score: 9,
                        return_pct: 7,
                        sharpe: 1,
                        win_rate_pct: 55,
                        profit_factor: 1.2,
                        max_dd_pct: 4,
                        trades: 3,
                        structure_score: 6.25,
                        structure_axes: {
                          trend_context: 5,
                          confirmation_depth: 6,
                          trigger_precision: 8,
                          exit_discipline: 6,
                          risk_control: 7,
                          time_discipline: 5.5,
                        },
                        structure_tags: ["event_trigger"],
                      },
                    ],
                    pct: 100,
                    phase: "done",
                    detail: "Finished 2 rows scored.",
                    active_strategy: "Beta",
                  },
                  rows: [
                    {
                      ticker: "AAA.DE",
                      strategy: "Alpha",
                      quality_score: 10,
                      return_pct: 12,
                      win_rate_pct: 60,
                      profit_factor: 1.5,
                      sharpe: 1.2,
                      max_dd_pct: 5,
                      trades: 4,
                      days_since_entry: 2,
                    },
                    {
                      ticker: "BBB.ST",
                      strategy: "Beta",
                      quality_score: 9,
                      return_pct: 7,
                      win_rate_pct: 55,
                      profit_factor: 1.2,
                      sharpe: 1,
                      max_dd_pct: 4,
                      trades: 3,
                      days_since_entry: 5,
                    },
                  ],
                }),
              };
            }
            if (text.includes("/api/job-progress")) {
              return { ok: true, json: async () => ({}) };
            }
            return { ok: true, json: async () => ({}) };
          };
        }
        """
    )
    page.add_script_tag(path=str(dashboard_js))
    page.evaluate(
        """
        async () => {
          await window.dashboardReadyPromise;
          await window.setScanSource("xetra");
          await window.loadBacktestMetrics();
        }
        """
    )

    radar_traces = page.evaluate(
        "() => [...window.__plots].reverse().find((plot) => plot.nodeId === 'backtest-structure-chart')?.data || []"
    )
    assert [trace["name"] for trace in radar_traces] == ["Alpha", "Beta"]
    assert all(trace["type"] == "scatterpolar" for trace in radar_traces)
    behavior_traces = page.evaluate(
        "() => [...window.__plots].reverse().find((plot) => plot.nodeId === 'backtest-behavior-chart')?.data || []"
    )
    assert [trace["name"] for trace in behavior_traces] == ["Alpha", "Beta"]
    assert behavior_traces[0]["theta"] == [
        "Quality",
        "Return",
        "Sharpe",
        "Win Rate",
        "Profit Factor",
        "Drawdown Control",
        "Quality",
    ]
    assert page.locator("#bt-best-structure").inner_text() == "8.50"


def test_backtest_structure_radar_renders_editor_draft_profile(page):
    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )

    page.set_content(
        """
        <html>
          <body>
            <div id="scan-source-toggle"></div>
            <button id="backtest-run-btn"></button>
            <select id="ticker-select"></select>
            <select id="strategy-select"></select>
            <textarea id="strategy-editor">TRIGGER: close > ema_20
EXIT: close < ema_20</textarea>
            <div id="backtest-empty"></div>
            <div id="backtest-content" class="hidden">
              <div id="bt-strategy"></div>
              <div id="bt-count"></div>
              <div id="bt-best-quality"></div>
              <div id="bt-avg-return"></div>
              <div id="bt-avg-sharpe"></div>
              <div id="bt-best-structure"></div>
              <select id="backtest-x-axis"></select>
              <select id="backtest-y-axis"></select>
              <select id="backtest-color-by">
                <option value="strategy">Strategy</option>
              </select>
              <div id="backtest-chart"></div>
              <div id="backtest-structure-chart"></div>
              <div id="backtest-behavior-chart"></div>
              <table><tbody id="backtest-table-body"></tbody></table>
            </div>
          </body>
        </html>
        """,
        wait_until="domcontentloaded",
    )
    page.evaluate(
        """
        () => {
          window.__plots = [];
          window.Plotly = {
            purge() {},
            relayout() {},
            downloadImage() {},
            newPlot: async (node, data, layout, config) => {
              window.__plots.push({ nodeId: node.id, data, layout, config });
            },
          };
          window.alert = () => {};
          const originalGetElementById = document.getElementById.bind(document);
          document.getElementById = (id) => {
            let node = originalGetElementById(id);
            if (node) return node;
            node = document.createElement(id.includes("select") ? "select" : id.includes("btn") ? "button" : "div");
            node.id = id;
            node.style.display = "none";
            document.body.appendChild(node);
            return node;
          };
          window.fetch = async (url) => {
            const text = String(url);
            if (text.includes("/api/market-status")) {
              return {
                ok: true,
                json: async () => ({
                  today: "2026-06-07",
                  latest_market_date: "2026-06-07",
                  days_stale: 0,
                  is_stale: false,
                  tracked_tickers: 2,
                  fresh_tickers: 2,
                  missing_tickers: 0,
                  stale_tickers: 0,
                }),
              };
            }
            if (text.includes("/api/ticker-universe")) {
              return {
                ok: true,
                json: async () => ({
                  items: [
                    { ticker: "AAA.DE", name: "AAA", label: "AAA", exchange: "xetra" },
                  ],
                }),
              };
            }
            if (text.includes("/api/backtest?")) {
              return {
                ok: true,
                json: async () => ({
                  source_type: "editor",
                  strategy_name: "Editor Draft",
                  summary: {
                    count: 1,
                    best_quality: 12,
                    avg_return: 12,
                    avg_sharpe: 1.4,
                    trades: 3,
                  },
                  strategy_axis_catalog: [
                    { key: "trend_context", label: "Trend Context", max: 10 },
                    { key: "confirmation_depth", label: "Confirmation Depth", max: 10 },
                    { key: "trigger_precision", label: "Trigger Precision", max: 10 },
                    { key: "exit_discipline", label: "Exit Discipline", max: 10 },
                    { key: "risk_control", label: "Risk Control", max: 10 },
                    { key: "time_discipline", label: "Time Discipline", max: 10 },
                  ],
                  strategy_profile: {
                    structure_score: 7.1,
                    structure_axes: {
                      trend_context: 6,
                      confirmation_depth: 7,
                      trigger_precision: 8,
                      exit_discipline: 7,
                      risk_control: 8,
                      time_discipline: 6.5,
                    },
                    structure_tags: ["event_trigger"],
                    axis_order: [
                      "trend_context",
                      "confirmation_depth",
                      "trigger_precision",
                      "exit_discipline",
                      "risk_control",
                      "time_discipline",
                    ],
                  },
                  strategy_summaries: [
                    {
                      strategy: "Editor Draft",
                      avg_quality_score: 12,
                      return_pct: 12,
                      sharpe: 1.4,
                      win_rate_pct: 60,
                      profit_factor: 1.5,
                      max_dd_pct: 4,
                      trades: 3,
                      structure_score: 7.1,
                      structure_axes: {
                        trend_context: 6,
                        confirmation_depth: 7,
                        trigger_precision: 8,
                        exit_discipline: 7,
                        risk_control: 8,
                        time_discipline: 6.5,
                      },
                      structure_tags: ["event_trigger"],
                    },
                  ],
                  race: {
                    selected_strategies: ["Editor Draft"],
                    lanes: [
                      {
                        strategy: "Editor Draft",
                        status: "done",
                        progress_pct: 100,
                        detail: "Done",
                        avg_quality_score: 12,
                        return_pct: 12,
                        sharpe: 1.4,
                        win_rate_pct: 60,
                        profit_factor: 1.5,
                        max_dd_pct: 4,
                        trades: 3,
                        structure_score: 7.1,
                        structure_axes: {
                          trend_context: 6,
                          confirmation_depth: 7,
                          trigger_precision: 8,
                          exit_discipline: 7,
                          risk_control: 8,
                          time_discipline: 6.5,
                        },
                        structure_tags: ["event_trigger"],
                      },
                    ],
                    pct: 100,
                    phase: "done",
                    detail: "Finished 1 row scored.",
                    active_strategy: "Editor Draft",
                  },
                  rows: [
                    {
                      ticker: "AAA.DE",
                      strategy: "Editor Draft",
                      quality_score: 12,
                      return_pct: 12,
                      win_rate_pct: 60,
                      profit_factor: 1.5,
                      sharpe: 1.4,
                      max_dd_pct: 4,
                      trades: 3,
                      days_since_entry: 2,
                    },
                  ],
                }),
              };
            }
            if (text.includes("/api/job-progress")) {
              return { ok: true, json: async () => ({}) };
            }
            return { ok: true, json: async () => ({}) };
          };
        }
        """
    )
    page.add_script_tag(path=str(dashboard_js))
    page.evaluate(
        """
        async () => {
          await window.dashboardReadyPromise;
          await window.setScanSource("xetra");
          await window.setBacktestSourceMode("editor");
          await window.loadBacktestMetrics();
        }
        """
    )

    radar_traces = page.evaluate(
        "() => [...window.__plots].reverse().find((plot) => plot.nodeId === 'backtest-structure-chart')?.data || []"
    )
    assert [trace["name"] for trace in radar_traces] == ["Editor Draft"]
    assert radar_traces[0]["type"] == "scatterpolar"
    behavior_traces = page.evaluate(
        "() => [...window.__plots].reverse().find((plot) => plot.nodeId === 'backtest-behavior-chart')?.data || []"
    )
    assert [trace["name"] for trace in behavior_traces] == ["Editor Draft"]
    assert behavior_traces[0]["type"] == "scatterpolar"
    assert page.locator("#bt-best-structure").inner_text() == "7.10"


def test_backtest_exclude_checkbox_renders_in_live_dashboard_shell(page):
    with _run_dashboard_server() as base_url:
        page.route(
            "**/api/**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=(
                    '{"today":"2026-06-07","latest_market_date":"2026-06-07",'
                    '"days_stale":0,"is_stale":false,"tracked_tickers":0,'
                    '"fresh_tickers":0,"missing_tickers":0,"stale_tickers":0}'
                    if "/api/market-status" in route.request.url
                    else '{"items":[]}'
                ),
            ),
        )
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => typeof window.prepareBacktestLiveResults === 'function' && !!window.dashboardReadyPromise"
        )
        page.evaluate(
            """
            async () => {
              await window.dashboardReadyPromise;
              window.showTab("backtest");
              window.prepareBacktestLiveResults("Running...");
              window.mergeBacktestScatterRows([
                {
                  strategy: "Alpha",
                  ticker: "AAA.DE",
                  trades: 3,
                  return_pct: 12,
                  win_rate_pct: 66,
                  profit_factor: 1.8,
                  sharpe: 1.4,
                  max_dd_pct: 5,
                  quality_score: 18,
                },
                {
                  strategy: "Beta",
                  ticker: "BBB.ST",
                  trades: 2,
                  return_pct: 7,
                  win_rate_pct: 55,
                  profit_factor: 1.2,
                  sharpe: 0.8,
                  max_dd_pct: 4,
                  quality_score: 9,
                },
              ]);
              await new Promise((resolve) => setTimeout(resolve, 250));
            }
            """
        )

        exclude_header = page.locator("th", has_text="Exclude")
        first_row_last_cell = page.locator("#backtest-table-body tr").first.locator("td").last

        assert exclude_header.is_visible()
        assert page.locator("#backtest-table-body tr").count() == 2
        assert first_row_last_cell.locator("input[type='checkbox']").is_visible()
        assert first_row_last_cell.inner_text().strip().upper() == "EXCLUDE"


def test_backtest_all_strategies_requests_all_strategies_flag(page):
    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )

    page.set_content(
        """
        <html>
          <body>
            <div id="scan-source-toggle"></div>
            <button id="backtest-run-btn"></button>
            <select id="ticker-select"></select>
            <select id="strategy-select"></select>
            <textarea id="strategy-editor"></textarea>
            <div id="backtest-empty"></div>
            <div id="backtest-content" class="hidden">
              <div id="bt-strategy"></div>
              <div id="bt-count"></div>
              <div id="bt-best-quality"></div>
              <div id="bt-avg-return"></div>
              <div id="bt-avg-sharpe"></div>
              <select id="backtest-x-axis"></select>
              <select id="backtest-y-axis"></select>
              <select id="backtest-color-by">
                <option value="strategy">Strategy</option>
              </select>
              <div id="backtest-chart"></div>
              <table><tbody id="backtest-table-body"></tbody></table>
            </div>
            <label><input class="backtest-strategy-checkbox" type="checkbox" value="Alpha" checked></label>
            <label><input class="backtest-strategy-checkbox" type="checkbox" value="Beta" checked></label>
          </body>
        </html>
        """,
        wait_until="domcontentloaded",
    )
    page.evaluate(
        """
        () => {
          window.__fetchUrls = [];
          window.Plotly = {
            purge() {},
            relayout() {},
            downloadImage() {},
            newPlot: async () => {},
          };
          window.alert = () => {};
          const originalGetElementById = document.getElementById.bind(document);
          document.getElementById = (id) => {
            let node = originalGetElementById(id);
            if (node) return node;
            node = document.createElement(id.includes("select") ? "select" : id.includes("btn") ? "button" : "div");
            node.id = id;
            node.style.display = "none";
            document.body.appendChild(node);
            return node;
          };
          window.fetch = async (url) => {
            const text = String(url);
            window.__fetchUrls.push(text);
            if (text.includes("/api/market-status")) {
              return {
                ok: true,
                json: async () => ({
                  today: "2026-06-02",
                  latest_market_date: "2026-06-02",
                  days_stale: 0,
                  is_stale: false,
                  tracked_tickers: 2,
                  fresh_tickers: 2,
                  missing_tickers: 0,
                  stale_tickers: 0,
                }),
              };
            }
            if (text.includes("/api/ticker-universe")) {
              return {
                ok: true,
                json: async () => ({
                  items: [
                    { ticker: "AAA.DE", name: "AAA", label: "AAA", exchange: "xetra" },
                    { ticker: "BBB.DE", name: "BBB", label: "BBB", exchange: "xetra" },
                  ],
                }),
              };
            }
            if (text.includes("/api/backtest/matrix")) {
              return {
                ok: true,
                json: async () => ({
                  source_type: "saved_matrix",
                  strategies: ["Alpha", "Beta"],
                  summary: {
                    count: 0,
                    strategy_count: 2,
                    best_quality: 0,
                    avg_return: 0,
                    avg_sharpe: 0,
                  },
                  metrics: [],
                  rows: [],
                  strategy_summaries: [],
                  race: {
                    selected_strategies: ["Alpha", "Beta"],
                    lanes: [],
                    pct: 100,
                    phase: "done",
                    detail: "Finished 0 rows scored.",
                    active_strategy: "Beta",
                  },
                }),
              };
            }
            if (text.includes("/api/job-progress")) {
              return { ok: true, json: async () => ({}) };
            }
            return { ok: true, json: async () => ({}) };
          };
        }
        """
    )
    page.add_script_tag(path=str(dashboard_js))
    page.evaluate(
        """
        async () => {
          await window.dashboardReadyPromise;
          await window.setScanSource("xetra");
          await window.loadBacktestMetrics();
        }
        """
    )

    request_url = page.evaluate(
        "() => window.__fetchUrls.find((url) => url.includes('/api/backtest/matrix'))"
    )
    assert request_url
    assert "all_strategies=true" in request_url
    assert "&strategies=" not in request_url
    assert "?strategies=" not in request_url
