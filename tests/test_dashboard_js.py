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
    script = textwrap.dedent(f"""
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
            ? {{ world: {{ layout: "sphere", radius: 1, diameter: 2, surface_area: 12.566, asset_count: 0 }}, nodes: [], count: 0 }}
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
        if (typeof window.exportTopMatches !== "function") {{
          throw new Error("exportTopMatches is not exposed on window");
        }}
        if (typeof window.stepSwarmDays !== "function") {{
          throw new Error("stepSwarmDays is not exposed on window");
        }}
        if (typeof window.setSwarmDebugAssetCount !== "function") {{
          throw new Error("setSwarmDebugAssetCount is not exposed on window");
        }}
        window.showTab("swarm");
        if (document.getElementById("tab-swarm").classList.contains("hidden")) {{
          throw new Error("Swarm tab stayed hidden after showTab('swarm')");
        }}
        if (!document.getElementById("tab-btn-swarm").classList.contains("active")) {{
          throw new Error("Swarm tab button did not become active");
        }}
        """)

    result = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_dashboard_js_scan_source_buttons_toggle_debug_controls():
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
    script = textwrap.dedent(f"""
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
            this.hidden = false;
            this.clientWidth = 900;
            this.clientHeight = 520;
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{
            this.children.push(child);
            if (Array.isArray(this.options)) {{
              this.options.push(child);
            }}
            return child;
          }}
          remove() {{}}
          focus() {{}}
          getBoundingClientRect() {{
            return {{ width: this.clientWidth, height: this.clientHeight, left: 0, top: 0, right: this.clientWidth, bottom: this.clientHeight }};
          }}
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

        ["xetra", "sweden", "list", "all_lists", "debug"].forEach((scope) => {{
          const screenerBtn = getElement(`scan-source-${{scope}}`);
          screenerBtn.dataset.scope = scope;
          screenerBtn.classList.add("scan-source-btn");
          const swarmBtn = getElement(`swarm-scan-source-${{scope}}`);
          swarmBtn.dataset.scope = scope;
          swarmBtn.classList.add("scan-source-btn");
        }});

        ["list-modal-xetra", "list-modal-sweden", "list-modal-all"].forEach((id, index) => {{
          const btn = getElement(id);
          btn.dataset.listExchange = index === 0 ? "xetra" : index === 1 ? "sweden" : "all";
        }});

        [
          "swarm-debug-controls",
          "swarm-debug-count",
          "swarm-debug-count-label",
          "swarm-world-visibility",
          "ticker-select",
          "shortlist-market-status",
          "list-modal",
          "list-modal-grid",
          "list-modal-visible-count",
          "list-modal-search",
          "list-modal-name",
          "list-modal-preview",
          "list-modal-list-select",
          "list-modal-count",
          "strategy-select",
          "strategy-editor",
          "strategy-filename",
        ].forEach(getElement);

        getElement("strategy-select").options = [new Element("strategy-option")];

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => {{
            if (selector === ".tab-btn") {{
              return ["screener", "shortlist", "swarm", "backtest"]
                .map((tab) => getElement(`tab-btn-${{tab}}`));
            }}
            if (selector.includes(".scan-source-btn")) {{
              return ["xetra", "sweden", "list", "all_lists", "debug"].flatMap((scope) => [
                getElement(`scan-source-${{scope}}`),
                getElement(`swarm-scan-source-${{scope}}`),
              ]);
            }}
            if (selector === "[data-list-exchange]") {{
              return ["list-modal-xetra", "list-modal-sweden", "list-modal-all"]
                .map((id) => getElement(id));
            }}
            return [];
          }},
          addEventListener: () => {{}},
        }};
        global.localStorage = {{
          getItem: (key) => {{
            if (key === "etf-discovery:last-custom-list") return "AAA,BBB";
            if (key === "etf-discovery:last-custom-list-name") return "My List";
            if (key === "etf-discovery:last-swarm-debug-asset-count") return "24";
            return "";
          }},
          setItem: () => {{}},
          removeItem: () => {{}},
        }};
        global.fetch = async (url) => {{
          const target = String(url);
          if (target.includes("/api/ticker-universe")) {{
            return {{
              ok: true,
              json: async () => ({{
                count: 3,
                items: [
                  {{ ticker: "AAA", exchange: "xetra", label: "AAA" }},
                  {{ ticker: "BBB", exchange: "sweden", label: "BBB" }},
                  {{ ticker: "CCC", exchange: "xetra", label: "CCC" }},
                ],
              }}),
            }};
          }}
          if (target.includes("/api/custom-ticker-list")) {{
            return {{
              ok: true,
              json: async () => ({{
                active_name: "My List",
                lists: [{{ name: "My List", tickers: ["AAA", "BBB"] }}],
                tickers: ["AAA", "BBB"],
              }}),
            }};
          }}
          if (target.includes("/api/market-status")) {{
            return {{
              ok: true,
              json: async () => ({{
                today: "2026-05-05",
                latest_market_date: "2026-05-05",
                days_stale: 0,
                is_stale: false,
                fresh_tickers: 3,
                tracked_tickers: 3,
              }}),
            }};
          }}
          if (target.includes("/api/log")) {{
            return {{ ok: true, json: async () => ({{ ok: true }}) }};
          }}
          return {{ ok: true, json: async () => ({{}}) }};
        }};
        global.requestAnimationFrame = () => 1;
        global.cancelAnimationFrame = () => {{}};
        global.setTimeout = () => 1;
        global.setInterval = () => 1;
        global.clearInterval = () => {{}};
        global.alert = () => {{}};
        global.Plotly = {{ purge: () => {{}}, relayout: () => {{}}, downloadImage: () => {{}} }};

        const source = fs.readFileSync({str(dashboard_js)!r}, "utf8");
        Function(source)();

        const waitForReady = window.dashboardReadyPromise || Promise.resolve();

        (async () => {{
          await waitForReady;

          const debugPanel = getElement("swarm-debug-controls");
          const sourceScopes = ["xetra", "sweden", "list", "all_lists", "debug"];

          const assertScope = (expectedScope, expectDebugVisible) => {{
            sourceScopes.forEach((scope) => {{
              const screenerActive = getElement(`scan-source-${{scope}}`).classList.contains("is-active");
              const swarmActive = getElement(`swarm-scan-source-${{scope}}`).classList.contains("is-active");
              const shouldBeActive = scope === expectedScope;
              if (screenerActive !== shouldBeActive) {{
                throw new Error(`Screener scope ${{scope}} active state mismatch for ${{expectedScope}}`);
              }}
              if (swarmActive !== shouldBeActive) {{
                throw new Error(`Swarm scope ${{scope}} active state mismatch for ${{expectedScope}}`);
              }}
            }});
            if (debugPanel.hidden !== !expectDebugVisible) {{
              throw new Error(`Debug panel visibility mismatch for ${{expectedScope}}`);
            }}
            if (getElement("swarm-debug-count").disabled !== !expectDebugVisible) {{
              throw new Error(`Debug input disabled state mismatch for ${{expectedScope}}`);
            }}
          }};

          for (const scope of sourceScopes) {{
            await window.setScanSource(scope);
            assertScope(scope, scope === "debug");
          }}

          const worldCaption = getElement("swarm-world-caption");
          await window.setScanSource("debug");
          if (typeof window.loadSwarmWorld === "function") {{
            await window.loadSwarmWorld(true);
          }}
          if (!String(worldCaption.textContent || "").toLowerCase().includes("debug sphere")) {{
            throw new Error("Debug sphere caption did not appear");
          }}

          const worldBadge = getElement("swarm-world-visibility");
          await window.setSwarmZoom(2.2);
          if (worldBadge.textContent !== "Zoomed in") {{
            throw new Error("World visibility badge did not show zoomed-in state");
          }}
          await window.setSwarmZoom(0.35);
          if (worldBadge.textContent !== "Whole world visible") {{
            throw new Error("World visibility badge did not show whole-world state");
          }}

          await window.setScanSource("xetra");
          assertScope("xetra", false);
        }})().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """)

    result = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_dashboard_js_modify_strategy_bumps_existing_version():
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
    script = textwrap.dedent(f"""
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
          focus() {{}}
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
          "strategy-select",
          "strategy-editor",
          "strategy-filename",
          "modify-modal",
          "modify-modal-editor",
          "modify-modal-name",
          "modify-modal-source",
          "shortlist-market-status",
          "tab-screener",
          "tab-shortlist",
          "tab-swarm",
          "tab-backtest",
          "tab-btn-screener",
          "tab-btn-shortlist",
          "tab-btn-swarm",
          "tab-btn-backtest",
        ].forEach(getElement);

        getElement("strategy-select").value = "my_strategy_v2";
        getElement("strategy-editor").value = "FILTER: close > ema_20";
        getElement("strategy-filename").value = "my_strategy_v2";
        getElement("modify-modal").style.display = "none";

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
        global.fetch = async (url) => {{
          if (String(url).includes("/api/strategy/")) {{
            return {{
              ok: true,
              json: async () => ({{ name: "my_strategy_v2", content: "TRIGGER: close > ema_20" }}),
            }};
          }}
          if (String(url).includes("/api/market-status")) {{
            return {{
              ok: true,
              json: async () => ({{
                today: "2026-04-29",
                latest_market_date: "2026-04-29",
                days_stale: 0,
                is_stale: false,
                tracked_tickers: 1,
                fresh_tickers: 1,
                missing_tickers: 0,
                stale_tickers: 0,
              }}),
            }};
          }}
          if (String(url).includes("/api/custom-ticker-list")) {{
            return {{
              ok: true,
              json: async () => ({{ count: 0, tickers: [] }}),
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
          await window.modifyStrategy();
          const name = document.getElementById("modify-modal-name").value;
          if (name !== "my_strategy_v3") {{
            throw new Error(`Expected version bump to my_strategy_v3, got ${{name}}`);
          }}
        }})().catch((err) => {{
          console.error(err);
          process.exit(1);
        }});
        """)

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
    script = textwrap.dedent(f"""
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
        """)

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
    script = textwrap.dedent(f"""
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
              json: async () => ({{ world: {{ layout: "sphere", radius: 1, diameter: 2, surface_area: 12.566, asset_count: 0 }}, nodes: [], count: 0 }}),
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
        """)

    result = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
