import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


def test_dashboard_js_exposes_and_switches_swarm_tab():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for dashboard JavaScript smoke tests")

    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )
    script = textwrap.dedent(
        f"""
        const fs = require("fs");

        class ClassList {{
          constructor() {{ this.values = new Set(); }}
          add(...names) {{ names.forEach((name) => this.values.add(name)); }}
          remove(...names) {{ names.forEach((name) => this.values.delete(name)); }}
          contains(name) {{ return this.values.has(name); }}
          toggle(name, force) {{
            const shouldAdd = force === undefined ? !this.values.has(name) : Boolean(force);
            if (shouldAdd) this.values.add(name);
            else this.values.delete(name);
            return shouldAdd;
          }}
        }}

        class Element {{
          constructor(id = "") {{
            this.id = id;
            this.classList = new ClassList();
            this.children = [];
            this.dataset = {{}};
            this.style = {{}};
            this.options = [];
            this.value = "";
            this.textContent = "";
            this.innerHTML = "";
            this.disabled = false;
            this.clientWidth = 900;
            this.clientHeight = 520;
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          getContext() {{
            const noop = () => {{}};
            return new Proxy({{}}, {{ get: () => noop, set: () => true }});
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => selector === ".tab-btn"
            ? ["screener", "shortlist", "swarm", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: () => {{}},
        }};
        global.localStorage = {{
          getItem: () => "",
          setItem: () => {{}},
          removeItem: () => {{}},
        }};
        global.fetch = async (url) => ({{
          ok: true,
          json: async () => String(url).includes("swarm-world")
            ? {{ world: {{ layout: "grid", rows: 1, columns: 1, cell_width: 1, cell_height: 1 }}, nodes: [], count: 0 }}
            : String(url).includes("ticker-universe")
              ? {{ count: 0, items: [] }}
              : String(url).includes("custom-ticker-list")
                ? {{ count: 0, tickers: [] }}
            : String(url).includes("swarm-history")
              ? {{ histories: [], count: 0 }}
              : {{}},
        }});
        global.requestAnimationFrame = () => 1;
        global.cancelAnimationFrame = () => {{}};
        global.setTimeout = () => 1;
        global.setInterval = () => 1;
        global.clearInterval = () => {{}};
        global.alert = () => {{}};
        global.Plotly = {{ purge: () => {{}}, relayout: () => {{}}, downloadImage: () => {{}} }};

        const source = fs.readFileSync({str(dashboard_js)!r}, "utf8");
        Function(source)();

        if (typeof window.showTab !== "function") {{
          throw new Error("showTab is not exposed on window");
        }}
        window.showTab("swarm");
        if (document.getElementById("tab-swarm").classList.contains("hidden")) {{
          throw new Error("Swarm tab stayed hidden after showTab('swarm')");
        }}
        if (!document.getElementById("tab-btn-swarm").classList.contains("active")) {{
          throw new Error("Swarm tab button did not become active");
        }}
        """
    )

    result = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_dashboard_js_persists_chart_range():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for dashboard JavaScript smoke tests")

    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )
    script = textwrap.dedent(
        f"""
        const fs = require("fs");

        class ClassList {{
          constructor() {{ this.values = new Set(); }}
          add(...names) {{ names.forEach((name) => this.values.add(name)); }}
          remove(...names) {{ names.forEach((name) => this.values.delete(name)); }}
          contains(name) {{ return this.values.has(name); }}
          toggle(name, force) {{
            const shouldAdd = force === undefined ? !this.values.has(name) : Boolean(force);
            if (shouldAdd) this.values.add(name);
            else this.values.delete(name);
            return shouldAdd;
          }}
        }}

        class Element {{
          constructor(id = "") {{
            this.id = id;
            this.classList = new ClassList();
            this.children = [];
            this.dataset = {{}};
            this.style = {{}};
            this.options = [];
            this.value = "";
            this.textContent = "";
            this.innerHTML = "";
            this.disabled = false;
            this.clientWidth = 900;
            this.clientHeight = 520;
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          getContext() {{
            const noop = () => {{}};
            return new Proxy({{}}, {{ get: () => noop, set: () => true }});
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});
        getElement("chart-range-label");
        getElement("range-btn-1m");
        getElement("range-btn-3m");
        getElement("range-btn-6m");
        getElement("range-btn-1y");
        getElement("range-btn-2y");
        getElement("range-btn-3y");

        const storage = new Map([["etf-discovery:last-chart-range-days", "126"]]);

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => selector === ".tab-btn"
            ? ["screener", "shortlist", "swarm", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: () => {{}},
        }};
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async () => ({{
          ok: true,
          json: async () => ({{ count: 0, items: [], world: {{ layout: "grid", rows: 1, columns: 1, cell_width: 1, cell_height: 1 }}, nodes: [], count: 0 }}),
        }});
        global.requestAnimationFrame = () => 1;
        global.cancelAnimationFrame = () => {{}};
        global.setTimeout = () => 1;
        global.setInterval = () => 1;
        global.clearInterval = () => {{}};
        global.alert = () => {{}};
        global.Plotly = {{ purge: () => {{}}, relayout: () => {{}}, downloadImage: () => {{}} }};

        const source = fs.readFileSync({str(dashboard_js)!r}, "utf8");
        Function(source)();

        (async () => {{
          if (window.dashboardReadyPromise) {{
            await window.dashboardReadyPromise;
          }}
          await Promise.resolve();

          if (document.getElementById("chart-range-label").textContent !== "6M chart") {{
            throw new Error("Dashboard did not restore the saved chart range");
          }}

          window.setRange(63);
          if (storage.get("etf-discovery:last-chart-range-days") !== "63") {{
            throw new Error("Dashboard did not persist the updated chart range");
          }}
        }})().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """
    )

    result = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_dashboard_js_auto_refreshes_stale_market_data():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for dashboard JavaScript smoke tests")

    dashboard_js = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ETF_screener"
        / "dashboard"
        / "static"
        / "js"
        / "dashboard.js"
    )
    script = textwrap.dedent(
        f"""
        const fs = require("fs");

        class ClassList {{
          constructor() {{ this.values = new Set(); }}
          add(...names) {{ names.forEach((name) => this.values.add(name)); }}
          remove(...names) {{ names.forEach((name) => this.values.delete(name)); }}
          contains(name) {{ return this.values.has(name); }}
          toggle(name, force) {{
            const shouldAdd = force === undefined ? !this.values.has(name) : Boolean(force);
            if (shouldAdd) this.values.add(name);
            else this.values.delete(name);
            return shouldAdd;
          }}
        }}

        class Element {{
          constructor(id = "") {{
            this.id = id;
            this.classList = new ClassList();
            this.children = [];
            this.dataset = {{}};
            this.style = {{}};
            this.options = [];
            this.value = "";
            this.textContent = "";
            this.innerHTML = "";
            this.disabled = false;
            this.clientWidth = 900;
            this.clientHeight = 520;
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          getContext() {{
            const noop = () => {{}};
            return new Proxy({{}}, {{ get: () => noop, set: () => true }});
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        [
          "shortlist-market-status",
          "market-refresh-btn",
          "shortlist-refresh-btn",
          "shortlist-status",
          "shortlist-as-of",
          "shortlist-buy-count",
          "shortlist-watch-count",
          "shortlist-skip-count",
          "shortlist-empty",
          "shortlist-content",
          "ticker-select",
          "strategy-select",
          "tab-screener",
          "tab-shortlist",
          "tab-swarm",
          "tab-backtest",
          "tab-btn-screener",
          "tab-btn-shortlist",
          "tab-btn-swarm",
          "tab-btn-backtest",
        ].forEach(getElement);

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => selector === ".tab-btn"
            ? ["screener", "shortlist", "swarm", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: () => {{}},
        }};
        global.localStorage = {{
          getItem: () => "",
          setItem: () => {{}},
          removeItem: () => {{}},
        }};
        const calls = [];
        let marketStatusCalls = 0;
        global.fetch = async (url) => {{
          calls.push(String(url));
          if (String(url).includes("/api/market-status")) {{
            marketStatusCalls += 1;
            return {{
              ok: true,
              json: async () => marketStatusCalls === 1
                ? {{
                    today: "2026-04-29",
                    latest_market_date: "2026-04-29",
                    days_stale: 0,
                    is_stale: false,
                    tracked_tickers: 2,
                    fresh_tickers: 2,
                    missing_tickers: 0,
                    stale_tickers: 0,
                  }}
                : marketStatusCalls === 2
                ? {{
                    today: "2026-04-29",
                    latest_market_date: "2026-04-15",
                    days_stale: 14,
                    is_stale: true,
                    tracked_tickers: 2,
                    fresh_tickers: 0,
                    missing_tickers: 0,
                    stale_tickers: 2,
                  }}
                : {{
                    today: "2026-04-29",
                    latest_market_date: "2026-04-29",
                    days_stale: 0,
                    is_stale: false,
                    tracked_tickers: 2,
                    fresh_tickers: 2,
                    missing_tickers: 0,
                    stale_tickers: 0,
                  }},
            }};
          }}
          if (String(url).includes("/api/market-data/refresh")) {{
            return {{
              ok: true,
              json: async () => ({{
                refreshed: 2,
                failed: 0,
                latest_market_date: "2026-04-29",
                shortlist_rebuilt: true,
              }}),
            }};
          }}
          if (String(url).includes("/api/shortlist")) {{
            return {{
              ok: true,
              json: async () => ({{
                as_of_date: "2026-04-29",
                rows: [],
                labels: {{ Buy: 0, Watch: 0, Skip: 0 }},
              }}),
            }};
          }}
          if (String(url).includes("/api/ticker-universe")) {{
            return {{
              ok: true,
              json: async () => ({{
                count: 0,
                items: [],
              }}),
            }};
          }}
          if (String(url).includes("/api/custom-ticker-list")) {{
            return {{
              ok: true,
              json: async () => ({{
                count: 0,
                tickers: [],
              }}),
            }};
          }}
          if (String(url).includes("swarm-world")) {{
            return {{
              ok: true,
              json: async () => ({{ world: {{ layout: "grid", rows: 1, columns: 1, cell_width: 1, cell_height: 1 }}, nodes: [], count: 0 }}),
            }};
          }}
          if (String(url).includes("swarm-history")) {{
            return {{
              ok: true,
              json: async () => ({{ histories: [], count: 0 }}),
            }};
          }}
          return {{
            ok: true,
            json: async () => ({{}}),
          }};
        }};
        global.requestAnimationFrame = () => 1;
        global.cancelAnimationFrame = () => {{}};
        global.setTimeout = () => 1;
        global.setInterval = () => 1;
        global.clearInterval = () => {{}};
        global.alert = () => {{}};
        global.showToast = () => {{}};
        global.Plotly = {{ purge: () => {{}}, relayout: () => {{}}, downloadImage: () => {{}} }};

        const source = fs.readFileSync({str(dashboard_js)!r}, "utf8");
        Function(source)();

        (async () => {{
          if (window.dashboardReadyPromise) {{
            await window.dashboardReadyPromise;
          }}
          await Promise.resolve();
          await Promise.resolve();
          await Promise.resolve();
          await window.ensureFreshMarketData();
          if (!calls.some((call) => call.includes("/api/market-data/refresh"))) {{
            throw new Error("Expected stale market data to trigger an automatic refresh");
          }}
          if (document.getElementById("shortlist-market-status").textContent.indexOf("fresh through 2026-04-29") === -1) {{
            throw new Error("Expected market status to update after refresh");
          }}
        }})().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """
    )

    result = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
