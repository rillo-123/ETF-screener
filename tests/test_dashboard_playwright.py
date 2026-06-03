from pathlib import Path


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
              <select id="backtest-x-axis"></select>
              <select id="backtest-y-axis"></select>
              <select id="backtest-color-by">
                <option value="strategy">Strategy</option>
              </select>
              <div id="backtest-chart"></div>
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
    traces = page.evaluate("() => window.__plots.at(-1).data")
    assert [trace["name"] for trace in traces] == ["Alpha", "Beta"]
    assert traces[0]["marker"]["color"] != traces[1]["marker"]["color"]
    assert traces[0]["x"] == [1.4]
    assert traces[0]["y"] == [12]


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
