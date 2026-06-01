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
          window.applyBacktestRaceEvent({
            type: "ticker_done",
            lane: "Alpha",
            payload: {
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
          });
          window.applyBacktestRaceEvent({
            type: "ticker_done",
            lane: "Beta",
            payload: {
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
          });
          await new Promise((resolve) => setTimeout(resolve, 250));
        }
        """
    )

    assert "hidden" not in (page.locator("#backtest-content").get_attribute("class") or "")
    assert page.locator("#bt-count").inner_text() == "2"
    assert page.locator("#backtest-table-body tr").count() == 2
    traces = page.evaluate("() => window.__plots.at(-1).data")
    assert [trace["name"] for trace in traces] == ["Alpha", "Beta"]
    assert traces[0]["marker"]["color"] != traces[1]["marker"]["color"]
    assert traces[0]["x"] == [1.4]
    assert traces[0]["y"] == [12]
