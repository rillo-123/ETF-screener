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
          getBoundingClientRect() {{
            return {{ width: this.clientWidth, height: this.clientHeight, left: 0, top: 0, right: this.clientWidth, bottom: this.clientHeight }};
          }}
          getContext() {{
            const gradient = {{ addColorStop() {{}} }};
            const noop = () => {{}};
            return {{
              save: noop,
              restore: noop,
              scale: noop,
              translate: noop,
              rotate: noop,
              clearRect: noop,
              fillRect: noop,
              beginPath: noop,
              arc: noop,
              ellipse: noop,
              closePath: noop,
              fill: noop,
              stroke: noop,
              moveTo: noop,
              lineTo: noop,
              createLinearGradient: () => gradient,
              createRadialGradient: () => gradient,
              lineCap: "",
              lineJoin: "",
              globalAlpha: 1,
              fillStyle: "",
              strokeStyle: "",
              lineWidth: 1,
            }};
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
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
            ? ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
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

        (async () => {{
          if (window.dashboardReadyPromise) {{
            await window.dashboardReadyPromise;
          }}
          if (document.getElementById("tab-screener").classList.contains("hidden")) {{
            throw new Error("Dashboard did not start on Screener");
          }}
          if (!document.getElementById("tab-btn-screener").classList.contains("active")) {{
            throw new Error("Screener tab button was not active on startup");
          }}

          if (typeof window.showTab !== "function") {{
            throw new Error("showTab is not exposed on window");
          }}
          if (typeof window.exportTopMatches !== "function") {{
            throw new Error("exportTopMatches is not exposed on window");
          }}
          if (typeof window.stepSwarmDays !== "function") {{
            throw new Error("stepSwarmDays is not exposed on window");
          }}
          if (typeof window.loadSwarmLab !== "function") {{
            throw new Error("loadSwarmLab is not exposed on window");
          }}
          if (typeof window.toggleSwarmLabPlayback !== "function") {{
            throw new Error("toggleSwarmLabPlayback is not exposed on window");
          }}
          localStorage.setItem("etf-discovery:last-dashboard-tab", "screener");
          if (typeof window.resetDashboardTabPreference !== "function") {{
            throw new Error("resetDashboardTabPreference is not exposed on window");
          }}
          window.resetDashboardTabPreference();
          if (localStorage.getItem("etf-discovery:last-dashboard-tab") !== "screener") {{
            throw new Error("Reset did not restore the dashboard tab to Screener");
          }}
          if (!document.getElementById("tab-btn-screener").classList.contains("active")) {{
            throw new Error("Reset did not return to Screener");
          }}
          window.showTab("swarm");
          if (document.getElementById("tab-swarm").classList.contains("hidden")) {{
            throw new Error("Swarm tab stayed hidden after showTab('swarm')");
          }}
          if (!document.getElementById("tab-btn-swarm").classList.contains("active")) {{
            throw new Error("Swarm tab button did not become active");
          }}
          window.showTab("swarm-lab");
          if (document.getElementById("tab-swarm-lab").classList.contains("hidden")) {{
            throw new Error("Swarm Lab tab stayed hidden after showTab('swarm-lab')");
          }}
          if (!document.getElementById("tab-btn-swarm-lab").classList.contains("active")) {{
            throw new Error("Swarm Lab tab button did not become active");
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


def test_dashboard_js_swarm_lab_does_not_call_market_endpoints():
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
            const gradient = {{ addColorStop() {{}} }};
            const noop = () => {{}};
            return {{
              save: noop,
              restore: noop,
              scale: noop,
              translate: noop,
              rotate: noop,
              clearRect: noop,
              fillRect: noop,
              beginPath: noop,
              arc: noop,
              ellipse: noop,
              closePath: noop,
              fill: noop,
              stroke: noop,
              moveTo: noop,
              lineTo: noop,
              createLinearGradient: () => gradient,
              createRadialGradient: () => gradient,
              lineCap: "",
              lineJoin: "",
              globalAlpha: 1,
              fillStyle: "",
              strokeStyle: "",
              lineWidth: 1,
            }};
          }}
        }}

        const calls = [];
        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});

        [
          "swarm-lab-status",
          "swarm-lab-empty",
          "swarm-lab-refresh-btn",
          "swarm-lab-play-btn",
          "swarm-lab-stop-btn",
          "swarm-lab-population-slider",
          "swarm-lab-population-label",
          "swarm-lab-node-count-slider",
          "swarm-lab-node-count-label",
          "swarm-lab-mutation-slider",
          "swarm-lab-mutation-label",
          "swarm-lab-repulsion-slider",
          "swarm-lab-repulsion-label",
          "swarm-lab-speed-slider",
          "swarm-lab-speed-label",
          "swarm-lab-zoom-slider",
          "swarm-lab-zoom-label",
          "swarm-lab-stats",
          "swarm-lab-world-caption",
          "swarm-lab-hover",
          "swarm-lab-selected",
          "swarm-lab-canvas",
        ].forEach(getElement);

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => selector === ".tab-btn"
            ? ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async (url) => {{
          calls.push(String(url));
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

        (async () => {{
          if (window.dashboardReadyPromise) {{
            await window.dashboardReadyPromise;
          }}
          calls.length = 0;
          window.showTab("swarm-lab");
          await window.loadSwarmLab(true);

          const forbidden = ["/api/swarm-world", "/api/swarm-history", "/api/market-status", "/api/market-data/refresh"];
          forbidden.forEach((fragment) => {{
            if (calls.some((call) => call.includes(fragment))) {{
              throw new Error(`Swarm Lab should not call market endpoint: ${{fragment}}`);
            }}
          }});

          if (document.getElementById("tab-swarm-lab").classList.contains("hidden")) {{
            throw new Error("Swarm Lab tab stayed hidden");
          }}
          if (!document.getElementById("tab-btn-swarm-lab").classList.contains("active")) {{
            throw new Error("Swarm Lab tab button did not become active");
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

def test_dashboard_js_renders_backtest_race_lanes():
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
          getBoundingClientRect() {{
            return {{ width: this.clientWidth, height: this.clientHeight, left: 0, top: 0, right: this.clientWidth, bottom: this.clientHeight }};
          }}
          getContext() {{
            const gradient = {{ addColorStop() {{}} }};
            const noop = () => {{}};
            return {{
              save: noop,
              restore: noop,
              scale: noop,
              translate: noop,
              rotate: noop,
              clearRect: noop,
              fillRect: noop,
              beginPath: noop,
              arc: noop,
              ellipse: noop,
              closePath: noop,
              fill: noop,
              stroke: noop,
              moveTo: noop,
              lineTo: noop,
              createLinearGradient: () => gradient,
              createRadialGradient: () => gradient,
              lineCap: "",
              lineJoin: "",
              globalAlpha: 1,
              fillStyle: "",
              strokeStyle: "",
              lineWidth: 1,
            }};
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
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
            ? ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async () => ({{
          ok: true,
          json: async () => ({{}}),
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
          if (typeof window.updateBacktestRaceFromSnapshot !== "function") {{
            throw new Error("updateBacktestRaceFromSnapshot is not exposed on window");
          }}
          if (typeof window.renderBacktestRace !== "function") {{
            throw new Error("renderBacktestRace is not exposed on window");
          }}
          if (typeof window.startBacktestRacePlayback !== "function") {{
            throw new Error("startBacktestRacePlayback is not exposed on window");
          }}
          if (typeof window.restartBacktestRacePlayback !== "function") {{
            throw new Error("restartBacktestRacePlayback is not exposed on window");
          }}
          window.updateBacktestRaceFromSnapshot({{
            backtest_race: {{
              selected_strategies: ["Alpha", "Beta", "Gamma"],
              active_strategy: "Alpha",
              completed: 1,
              total: 3,
              pct: 42,
              phase: "running",
              detail: "Alpha (1/3)",
              lanes: [
                {{ strategy: "Alpha", status: "complete", progress_pct: 100, detail: "Alpha", speed_score: 5.2, avg_quality_score: 5.2, return_pct: 1500.0, trades: 9, processed_tickers: 12, total_tickers: 15, scored_tickers: 3, no_trade_tickers: 9 }},
                {{ strategy: "Beta", status: "complete", progress_pct: 100, detail: "Queued", speed_score: 2.0, avg_quality_score: 2.0, return_pct: 200.0, trades: 4, processed_tickers: 8, total_tickers: 15, scored_tickers: 2, no_trade_tickers: 6 }},
                {{ strategy: "Gamma", status: "complete", progress_pct: 100, detail: "Queued", speed_score: 1.0, avg_quality_score: 1.0, return_pct: 50.0, trades: 1, processed_tickers: 5, total_tickers: 15, scored_tickers: 1, no_trade_tickers: 4 }}
              ]
            }}
          }});
          window.renderBacktestRace();
          const panel = document.getElementById("backtest-race-panel");
          const track = document.getElementById("backtest-race-track");
          if (panel.classList.contains("hidden")) {{
            throw new Error("Race panel should be visible after rendering lanes");
          }}
          if (!track.innerHTML.includes("Alpha") || !track.innerHTML.includes("Beta") || !track.innerHTML.includes("Gamma")) {{
            throw new Error("Race track did not render all selected strategies");
          }}
          if (!track.innerHTML.includes("Fuel Profitability")) {{
            throw new Error("Race track did not render fuel metadata");
          }}
          if (!track.innerHTML.includes("Profitability")) {{
            throw new Error("Race track did not render profitability metadata");
          }}
          if (!track.innerHTML.includes("Trades 9")) {{
            throw new Error("Race track did not render the trade count in the lane header");
          }}
          if (!track.innerHTML.includes("Processed 12/15") || !track.innerHTML.includes("Scored 3") || !track.innerHTML.includes("No trade 9")) {{
            throw new Error("Race track did not render processed/scored/no-trade lane counters");
          }}
          if (!track.innerHTML.includes("transform: translate")) {{
            throw new Error("Race track did not include the motion transform");
          }}
          if (!track.innerHTML.includes("width: 100%")) {{
            throw new Error("Race track did not autoscale the leader to full lane width");
          }}
          if (!track.innerHTML.includes("width: 13.33%")) {{
            throw new Error("Race track did not scale the runner-up lane to 200/1500");
          }}
          if (!track.innerHTML.includes("width: 3.33%")) {{
            throw new Error("Race track did not scale the third lane to 50/1500");
          }}
          window.updateBacktestRaceFromSnapshot({{
            backtest_race: {{
              selected_strategies: ["Alpha", "Beta", "Gamma"],
              active_strategy: "Alpha",
              completed: 0,
              total: 3,
              pct: 10,
              phase: "running",
              detail: "Only Alpha has emitted so far",
              lanes: [
                {{ strategy: "Alpha", status: "running", progress_pct: 10, detail: "Alpha started" }}
              ]
            }}
          }});
          if (!track.innerHTML.includes("Alpha") || !track.innerHTML.includes("Beta") || !track.innerHTML.includes("Gamma")) {{
            throw new Error("Partial race snapshots should still render every selected strategy lane");
          }}
          if (!track.innerHTML.includes("Beta") || !track.innerHTML.includes("Queued")) {{
            throw new Error("Missing selected strategies should render as queued lanes");
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


def test_dashboard_js_restart_backtest_race_resets_to_start():
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
          getBoundingClientRect() {{
            return {{ width: this.clientWidth, height: this.clientHeight, left: 0, top: 0, right: this.clientWidth, bottom: this.clientHeight }};
          }}
          getContext() {{
            const gradient = {{ addColorStop() {{}} }};
            const noop = () => {{}};
            return {{
              save: noop,
              restore: noop,
              scale: noop,
              translate: noop,
              rotate: noop,
              clearRect: noop,
              fillRect: noop,
              beginPath: noop,
              arc: noop,
              ellipse: noop,
              closePath: noop,
              fill: noop,
              stroke: noop,
              moveTo: noop,
              lineTo: noop,
              createLinearGradient: () => gradient,
              createRadialGradient: () => gradient,
              lineCap: "",
              lineJoin: "",
              globalAlpha: 1,
              fillStyle: "",
              strokeStyle: "",
              lineWidth: 1,
            }};
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});
        getElement("backtest-race-panel").classList.add("hidden");

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => selector === ".tab-btn"
            ? ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async () => ({{
          ok: true,
          json: async () => ({{}}),
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
          window.updateBacktestRaceFromSnapshot({{
            backtest_race: {{
              selected_strategies: ["Alpha", "Beta"],
              active_strategy: "Beta",
              pct: 100,
              phase: "done",
              detail: "Finished 2 lanes",
              lanes: [
                {{ strategy: "Alpha", status: "done", progress_pct: 100, detail: "Done", speed_score: 4.2, avg_quality_score: 4.2 }},
                {{ strategy: "Beta", status: "done", progress_pct: 100, detail: "Done", speed_score: 1.1, avg_quality_score: 1.1 }}
              ]
            }}
          }});
          window.restartBacktestRacePlayback();
          const status = document.getElementById("backtest-race-status").textContent;
          const track = document.getElementById("backtest-race-track").innerHTML;
          if (!status.includes("Running") && !status.includes("Paused at 0%")) {{
            throw new Error(`Restart did not put the race back into a live starting state: ${{status}}`);
          }}
          if (!track.includes("width: 0%")) {{
            throw new Error("Restart did not reset the lane positions to the starting line");
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


def test_dashboard_js_race_lanes_follow_selected_strategies():
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
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          closest() {{ return null; }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});
        getElement("backtest-race-panel").classList.add("hidden");
        getElement("backtest-selected-count");
        getElement("backtest-run-btn");
        getElement("ticker-select");
        getElement("strategy-select");

        const alpha = new Element("alpha-check");
        alpha.className = "backtest-strategy-checkbox";
        alpha.value = "Alpha";
        alpha.checked = true;
        const beta = new Element("beta-check");
        beta.className = "backtest-strategy-checkbox";
        beta.value = "Beta";
        beta.checked = false;
        const gamma = new Element("gamma-check");
        gamma.className = "backtest-strategy-checkbox";
        gamma.value = "Gamma";
        gamma.checked = false;
        const checkboxes = [alpha, beta, gamma];

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => {{
            if (selector === ".tab-btn") {{
              return ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`));
            }}
            if (selector === ".backtest-strategy-checkbox") {{
              return checkboxes;
            }}
            return [];
          }},
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async () => ({{
          ok: true,
          json: async () => ({{ content: "ENTRY: close > ema_50\\nEXIT: false" }}),
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
          window.updateBacktestRaceFromSnapshot({{
            backtest_race: {{
              selected_strategies: ["OldOne", "OldTwo"],
              active_strategy: "OldOne",
              pct: 100,
              phase: "done",
              detail: "Cached old run",
              lanes: [
                {{ strategy: "OldOne", status: "done", progress_pct: 100, detail: "Done" }},
                {{ strategy: "OldTwo", status: "done", progress_pct: 100, detail: "Done" }},
              ],
            }},
          }});
          let track = document.getElementById("backtest-race-track").innerHTML;
          if (!track.includes("OldOne") || !track.includes("OldTwo")) {{
            throw new Error("Test setup did not render the old cached lanes");
          }}

          alpha.checked = false;
          beta.checked = true;
          gamma.checked = true;
          window.handleBacktestStrategyChooserChange();

          track = document.getElementById("backtest-race-track").innerHTML;
          if (!track.includes("Beta") || !track.includes("Gamma")) {{
            throw new Error("Race lanes did not update to the selected strategies");
          }}
          if (track.includes("OldOne") || track.includes("OldTwo") || track.includes("Alpha")) {{
            throw new Error("Race lanes still contain stale or unselected strategies");
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


def test_dashboard_js_restores_last_strategy_without_checking_backtest_lane():
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
            this.checked = false;
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          closest() {{ return null; }}
        }}

        const savedName = "supertrend_st_crossdown_ema50_slope_turnup";
        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});
        getElement("backtest-selected-count");
        getElement("backtest-run-btn");
        getElement("ticker-select");
        getElement("strategy-editor");
        getElement("strategy-filename");
        const strategySelect = getElement("strategy-select");
        strategySelect.options = [{{ value: savedName }}];

        const savedCheckbox = new Element("saved-check");
        savedCheckbox.className = "backtest-strategy-checkbox";
        savedCheckbox.value = savedName;
        savedCheckbox.checked = false;
        const otherCheckbox = new Element("other-check");
        otherCheckbox.className = "backtest-strategy-checkbox";
        otherCheckbox.value = "super_loose";
        otherCheckbox.checked = false;
        const checkboxes = [savedCheckbox, otherCheckbox];

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => {{
            if (selector === ".tab-btn") {{
              return ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`));
            }}
            if (selector === ".backtest-strategy-checkbox") {{
              return checkboxes;
            }}
            return [];
          }},
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        storage.set("etf-discovery:last-completed-strategy", savedName);
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async (url) => {{
          if (String(url).includes("/api/strategy/")) {{
            return {{ ok: true, json: async () => ({{ content: "ENTRY: close > ema_50\\nEXIT: false" }}) }};
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

        (async () => {{
          if (window.dashboardReadyPromise) {{
            await window.dashboardReadyPromise;
          }}
          if (strategySelect.value !== savedName) {{
            throw new Error("Last completed strategy should still restore into the strategy select");
          }}
          if (savedCheckbox.checked || otherCheckbox.checked) {{
            throw new Error("Restoring the last completed strategy should not auto-check Backtester lanes");
          }}
          if (document.getElementById("backtest-selected-count").textContent !== "0 selected") {{
            throw new Error("Backtester selected count should remain zero after restore");
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


def test_dashboard_js_terminal_inactive_backtest_progress_stops_polling():
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
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          closest() {{ return null; }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});
        [
          "nav-scan-progress",
          "nav-scan-context-bar",
          "nav-scan-context-text",
          "nav-scan-context-label",
          "nav-scan-global-bar",
          "nav-scan-global-text",
          "nav-scan-global-label",
          "backtest-progress-panel",
          "backtest-progress-detail",
          "backtest-progress-percent",
          "backtest-context-label",
          "backtest-context-text",
          "backtest-context-bar",
          "backtest-global-label",
          "backtest-global-text",
          "backtest-global-bar",
        ].forEach(getElement);
        getElement("nav-scan-global-bar").classList.add("animate-pulse");
        getElement("backtest-global-bar").classList.add("animate-pulse");

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => selector === ".tab-btn"
            ? ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        global.localStorage = {{
          getItem: () => "",
          setItem: () => {{}},
          removeItem: () => {{}},
        }};
        global.fetch = async () => ({{ ok: true, json: async () => ({{}}) }});
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
          if (typeof window.applyJobProgressSnapshot !== "function") {{
            throw new Error("applyJobProgressSnapshot is not exposed on window");
          }}
          const done = window.applyJobProgressSnapshot({{
            job: "backtest",
            phase: "done",
            active: false,
            pct: 100,
            label: "Backtest Matrix",
            detail: "Finished 12 rows.",
          }}, "backtest");
          if (!done) {{
            throw new Error("Inactive done backtest snapshot should stop polling");
          }}
          if (document.getElementById("nav-scan-global-bar").classList.contains("animate-pulse")) {{
            throw new Error("Nav progress should stop pulsing on terminal snapshot");
          }}
          if (document.getElementById("backtest-global-bar").classList.contains("animate-pulse")) {{
            throw new Error("Backtest progress should stop pulsing on terminal snapshot");
          }}
          if (document.getElementById("backtest-global-text").textContent !== "Finished 12 rows.") {{
            throw new Error("Backtest progress text did not apply terminal detail");
          }}
          if (document.getElementById("backtest-global-bar").style.width !== "100%") {{
            throw new Error("Backtest progress did not land at 100%");
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


def test_dashboard_js_disables_backtest_controls_without_ticker_universe():
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
            this.checked = false;
            this.title = "";
            this.clientWidth = 900;
            this.clientHeight = 520;
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          focus() {{}}
          getBoundingClientRect() {{
            return {{ width: this.clientWidth, height: this.clientHeight, left: 0, top: 0, right: this.clientWidth, bottom: this.clientHeight }};
          }}
          getContext() {{
            const gradient = {{ addColorStop() {{}} }};
            const noop = () => {{}};
            return {{
              save: noop,
              restore: noop,
              scale: noop,
              translate: noop,
              rotate: noop,
              clearRect: noop,
              fillRect: noop,
              beginPath: noop,
              arc: noop,
              ellipse: noop,
              closePath: noop,
              fill: noop,
              stroke: noop,
              moveTo: noop,
              lineTo: noop,
              createLinearGradient: () => gradient,
              createRadialGradient: () => gradient,
              lineCap: "",
              lineJoin: "",
              globalAlpha: 1,
              fillStyle: "",
              strokeStyle: "",
              lineWidth: 1,
            }};
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});
        getElement("backtest-race-panel").classList.add("hidden");
        getElement("backtest-run-btn");
        getElement("backtest-race-start-btn");
        getElement("backtest-race-stop-btn");
        getElement("backtest-race-restart-btn");
        const strategyCheckbox = getElement("strategy-checkbox-alpha");
        strategyCheckbox.className = "backtest-strategy-checkbox";
        strategyCheckbox.value = "Alpha";
        strategyCheckbox.checked = true;

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => {{
            if (selector === ".tab-btn") {{
              return ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`));
            }}
            if (selector === ".backtest-strategy-checkbox") {{
              return [strategyCheckbox];
            }}
            if (selector === "#scan-source-toggle .scan-source-btn, #swarm-scan-source-toggle .scan-source-btn") {{
              return [];
            }}
            return [];
          }},
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async () => ({{
          ok: true,
          json: async () => ({{ items: [] }}),
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
          if (typeof window.setScanSource !== "function") {{
            throw new Error("setScanSource is not exposed on window");
          }}
          const runBtn = document.getElementById("backtest-run-btn");
          const startBtn = document.getElementById("backtest-race-start-btn");
          const stopBtn = document.getElementById("backtest-race-stop-btn");
          const restartBtn = document.getElementById("backtest-race-restart-btn");
          if (!runBtn.disabled) {{
            throw new Error("Backtest run button should be disabled when no ticker universe is selected");
          }}
          if (!startBtn.disabled || !stopBtn.disabled || !restartBtn.disabled) {{
            throw new Error("Race controls should be disabled when no ticker universe is selected");
          }}
          if (!String(runBtn.title || "").includes("Choose a ticker universe first")) {{
            throw new Error("Run button should explain why the universe is required");
          }}
          await window.setScanSource("xetra");
          if (runBtn.disabled) {{
            throw new Error("Backtest run button should unlock after explicitly choosing a universe");
          }}
          if (!startBtn.disabled || !stopBtn.disabled || !restartBtn.disabled) {{
            throw new Error("Race controls should stay disabled until a race exists");
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


def test_dashboard_js_restores_backtest_race_after_reload():
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
          getBoundingClientRect() {{
            return {{ width: this.clientWidth, height: this.clientHeight, left: 0, top: 0, right: this.clientWidth, bottom: this.clientHeight }};
          }}
          getContext() {{
            const gradient = {{ addColorStop() {{}} }};
            const noop = () => {{}};
            return {{
              save: noop,
              restore: noop,
              scale: noop,
              translate: noop,
              rotate: noop,
              clearRect: noop,
              fillRect: noop,
              beginPath: noop,
              arc: noop,
              ellipse: noop,
              closePath: noop,
              fill: noop,
              stroke: noop,
              moveTo: noop,
              lineTo: noop,
              createLinearGradient: () => gradient,
              createRadialGradient: () => gradient,
              lineCap: "",
              lineJoin: "",
              globalAlpha: 1,
              fillStyle: "",
              strokeStyle: "",
              lineWidth: 1,
            }};
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].forEach((tab) => {{
          getElement(`tab-${{tab}}`).classList.add("hidden");
          getElement(`tab-btn-${{tab}}`).classList.add("tab-btn");
        }});
        getElement("backtest-race-panel").classList.add("hidden");

        global.window = global;
        global.window.addEventListener = () => {{}};
        global.document = {{
          body: new Element("body"),
          createElement: (tag) => new Element(tag),
          getElementById: getElement,
          querySelectorAll: (selector) => selector === ".tab-btn"
            ? ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
            : [],
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
        }};
        const storage = new Map();
        storage.set(
          "etf-discovery:last-backtest-race",
          JSON.stringify({{
            signature: "saved::race",
            strategies: ["Alpha", "Beta"],
            lanes: [
              {{ strategy: "Alpha", index: 1, status: "done", progress_pct: 100, detail: "Done", speed_score: 4.2, avg_quality_score: 4.2, speed_factor: 1.2 }},
              {{ strategy: "Beta", index: 2, status: "done", progress_pct: 100, detail: "Done", speed_score: 1.1, avg_quality_score: 1.1, speed_factor: 0.7 }}
            ],
            targetProgress: 100,
            displayProgress: 100,
            status: "done",
            activeStrategy: "Beta",
            detail: "Finished 2 lanes",
            motionTick: 12
          }})
        );
        global.localStorage = {{
          getItem: (key) => storage.has(key) ? storage.get(key) : "",
          setItem: (key, value) => {{ storage.set(key, String(value)); }},
          removeItem: (key) => {{ storage.delete(key); }},
        }};
        global.fetch = async () => ({{
          ok: true,
          json: async () => ({{}}),
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
          const panel = document.getElementById("backtest-race-panel");
          const track = document.getElementById("backtest-race-track");
          const status = document.getElementById("backtest-race-status");
          if (panel.classList.contains("hidden")) {{
            throw new Error("Restored race panel should be visible after reload");
          }}
          if (!track.innerHTML.includes("Alpha") || !track.innerHTML.includes("Beta")) {{
            throw new Error("Restored race lanes were not rendered from cache");
          }}
          if (!String(status.textContent || "").includes("Finished 2 lanes")) {{
            throw new Error("Restored race detail text was not preserved");
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


def test_dashboard_js_run_screen_does_not_auto_refresh_market_data():
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
            this.hidden = false;
            this.clientWidth = 900;
            this.clientHeight = 520;
          }}
          addEventListener() {{}}
          setAttribute(name, value) {{ this[name] = value; }}
          appendChild(child) {{ this.children.push(child); return child; }}
          remove() {{}}
          getBoundingClientRect() {{
            return {{ width: this.clientWidth, height: this.clientHeight, left: 0, top: 0, right: this.clientWidth, bottom: this.clientHeight }};
          }}
          getContext() {{
            const gradient = {{ addColorStop() {{}} }};
            const noop = () => {{}};
            return {{
              save: noop,
              restore: noop,
              scale: noop,
              translate: noop,
              rotate: noop,
              clearRect: noop,
              fillRect: noop,
              beginPath: noop,
              arc: noop,
              ellipse: noop,
              closePath: noop,
              fill: noop,
              stroke: noop,
              moveTo: noop,
              lineTo: noop,
              createLinearGradient: () => gradient,
              createRadialGradient: () => gradient,
              lineCap: "",
              lineJoin: "",
              globalAlpha: 1,
              fillStyle: "",
              strokeStyle: "",
              lineWidth: 1,
            }};
          }}
        }}

        const elements = new Map();
        const getElement = (id) => {{
          if (!elements.has(id)) elements.set(id, new Element(id));
          return elements.get(id);
        }};

        [
          "ticker-list",
          "loading-spinner",
          "scan-btn",
          "run-btn",
          "strategy-select",
          "error-section",
          "error-list",
          "match-count",
          "shortlist-market-status",
          "shortlist-status",
          "market-refresh-btn",
          "shortlist-refresh-btn",
          "shortlist-as-of",
          "shortlist-buy-count",
          "shortlist-watch-count",
          "shortlist-skip-count",
          "shortlist-empty",
          "shortlist-content",
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
          addEventListener: (event, handler) => {{
            if (event === "DOMContentLoaded" && typeof handler === "function") {{
              handler();
            }}
          }},
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
              json: async () => ({{
                today: "2026-04-29",
                latest_market_date: "2026-04-15",
                days_stale: 14,
                is_stale: true,
                tracked_tickers: 2,
                fresh_tickers: 0,
                missing_tickers: 0,
                stale_tickers: 2,
              }}),
            }};
          }}
          if (String(url).includes("/api/screen")) {{
            return {{
              ok: true,
              json: async () => ({{
                matches: [],
                errors: [],
                total_errors: 0,
                total_candidates: 0,
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
          calls.length = 0;
          await window.setScanSource("sweden");
          calls.length = 0;
          await window.runScreen();

          if (!calls.some((call) => call.includes("/api/screen"))) {{
            throw new Error("Expected the screener to call /api/screen");
          }}
          if (calls.some((call) => call.includes("/api/market-data/refresh"))) {{
            throw new Error("Screener should not auto-refresh market data");
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
            ? ["screener", "shortlist", "swarm", "swarm-lab", "backtest"].map((tab) => getElement(`tab-btn-${{tab}}`))
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
        """
    )

    result = subprocess.run(
        [node, "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
