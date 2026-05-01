# Progress

## 2026-04-28 21:47:42 +02:00

- Fixed ticker nodes visually shrinking toward death during Swarm playback.
- Added `SWARM_TICKER_WEALTH_FLOOR` in `src/ETF_screener/dashboard/static/js/dashboard.js` so ticker simulated wealth cannot collapse to zero just because recent returns were poor.
- Kept agent death behavior unchanged; this change only affects real ticker node persistence/visibility.
- Renamed the selected ticker card label from `Ticker EUR` to `Ticker wealth` to avoid implying that the ticker itself is a spendable agent account.
- Updated `plan.md` to make the modeling rule explicit: tickers remain visible unless an explicit delisting/inactive-ticker model removes them.
- Verified the live static JS endpoint is serving the ticker wealth floor.
- Verified both static JS files parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: weak tickers should shrink but not appear to die off.
- Next resume point: live-test whether the minimum ticker radius/wealth floor feels right; tune the floor if weak tickers still look like they vanish.

## 2026-04-28 21:45:03 +02:00

- Tuned the initial charged-sphere layout to reduce clustering at the beginning of a Swarm run.
- Changed `stableSwarmSphereVector()` so ticker identity hashes into the Fibonacci sphere seed instead of relying mostly on grid row/column ordering.
- Added `relaxInitialSwarmSphere()` to run a short repulsion pre-relaxation pass after the world and history load.
- Stored the relaxed sphere vector as the reset baseline so `resetSwarmSimulation()` does not snap nodes back to the pre-relaxed clustered seed.
- Verified the live static JS endpoint is serving the relaxation code.
- Verified both static JS files parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: the first Swarm frame should start with less ticker clumping.
- Next resume point: live-test first-frame globe density; if clustering remains, increase relaxation steps or switch to a stronger deterministic sphere-packing pass.

## 2026-04-28 21:40:21 +02:00

- Fixed the full-globe Swarm view showing only a few apparent balls.
- Root cause: full-globe mode was using the same large wealth-scaled ticker radius as map/projection mode, so thousands of white circles visually merged into a handful of blobs.
- Added `getSwarmTickerDrawRadius()` in `src/ETF_screener/dashboard/static/js/dashboard.js`.
- Full-globe zoom now draws ticker balls much smaller while preserving larger wealth-scaled balls in zoomed projection mode.
- Updated dashboard assertions for the new globe-radius helper.
- Verified the live static JS endpoint is serving the smaller globe-radius code.
- Verified both static JS files parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: full-globe view should show a dense field of many small white ticker balls instead of a few merged blobs.
- Next resume point: live-test globe zoom at minimum zoom and tune the globe radius multiplier if the field is still too clumpy or too faint.

## 2026-04-28 21:33:52 +02:00

- Implemented the Swarm visual simplification in `src/ETF_screener/dashboard/static/js/dashboard.js`: ticker balls now render white/neutral, with radius still driven by `log10(simulated wealth)`.
- Removed gain/loss and shortlist-label color semantics from ticker ball drawing so color no longer competes with wealth radius.
- Replaced local grid-neighborhood candidate selection with global ticker candidate selection: agents evaluate all real visible tickers when making a jump decision.
- Changed jump movement from one-grid-step travel to direct jumps between real ticker nodes on the sphere.
- Reworked jump friction to use spherical distance rather than grid row/column distance.
- Staggered agent decision timing so global scans are distributed over frames instead of every agent rescoring the whole world on the same frame.
- Replaced the Swarm `Sense` slider in the GUI with a read-only `Knowledge: Global ticker scan` panel.
- Updated investment-rule copy from local-neighbor language to global ticker setup language.
- Verified the live static JS endpoint is serving the white-ball/global-candidate code.
- Verified both static JS files parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: the Swarm should now behave more like global investor agents deciding when and where to rotate.
- Next resume point: live-test whether global jumps are legible and whether the winning DNA rules feel useful rather than noisy.

## 2026-04-28 21:24:02 +02:00

- Updated `plan.md` with the next Swarm behavior pivot.
- Planned to simplify ticker ball rendering to neutral white, with radius proportional to `log10(simulated wealth)` instead of using green/red/label color semantics.
- Planned to retire local grid perception for the spherical Swarm model because jumping between grid neighbors is no longer intuitive once the visual world is self-organizing.
- Planned a global investor-style decision model: agents can inspect all real tickers at the current timeline step and jump according to their DNA criteria, such as low RSI, EMA crosses, dividends, drawdown avoidance, or profit-protection rules.
- Captured the key constraint: global knowledge may use current and historical indicator state, but not future returns.
- Captured the goal for meaningful hotlist DNA: winners should explain when to hold, when to jump while already ahead, and what type of ticker setup to jump toward.
- Current status: planning/docs only; no code changed in this update.
- Next resume point: implement white wealth-scaled ticker balls first, then replace local grid sensing with global ticker scoring/jump selection.

## 2026-04-28 21:16:46 +02:00

- Removed frontend-generated dummy Swarm ticker nodes from the active spherical world.
- Swarm now renders and simulates only real ticker nodes from `/api/swarm-world`; empty grid intersections are implicit gaps rather than placeholder balls.
- Kept backend `is_dummy: false` serialization for real nodes so the API contract remains explicit and compatible.
- Simplified dummy-specific chart disabling, hover copy, card rendering, drawing branches, and DNA target filtering in `src/ETF_screener/dashboard/static/js/dashboard.js`.
- Updated dashboard tests so `DUMMY-R` is expected to be absent from the frontend source.
- Updated `plan.md` to treat dummy nodes as retired now that the charged sphere self-organizes.
- Verified the live static JS endpoint is serving the real-only Swarm code.
- Verified both static JS files parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: the Swarm sphere should use less memory and show only actual ETF tickers.
- Next resume point: live-test whether local perception feels too sparse without dummy placeholders; if so, tune sense radius or nearest-real-neighbor lookup rather than reintroducing dummy balls.

## 2026-04-28 21:12:26 +02:00

- Responded to browser memory exhaustion during Swarm testing.
- Lowered the default Swarm density from `100` to `20` agents per alternating node in both the dashboard control and JS state.
- Kept the hard `SWARM_MAX_AGENTS = 5000` ceiling, but added a dynamic effective cap so normal/default runs start much lighter and only high slider values approach the full cap.
- Limited Swarm history loading to `900` tickers instead of requesting up to `5000` histories at once.
- Reduced trail retention from an open `1400` trail target to a `260` trail cap.
- Added a drawn-agent cap so very dense runs can still simulate more agents than they render every frame.
- Verified the live static JS endpoint is serving the lighter defaults.
- Verified both static JS files parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: the Swarm should use far less browser memory at startup while still allowing deliberate stress tests via the density slider.
- Next resume point: retest Swarm memory in the browser; if it still spikes, move simulation/history processing to a Web Worker or reduce history payload shape further.

## 2026-04-28 21:09:12 +02:00

- Investigated the report that only about eight Swarm ticker balls were visible.
- Confirmed the backend still returns the full Swarm world: `/api/swarm-world` reported 2,968 real ticker nodes across a 72 x 42 grid.
- Adjusted the Swarm projection camera in `src/ETF_screener/dashboard/static/js/dashboard.js` so the initial and low-activity view keeps a stable broad anchor instead of drifting toward a sparse spherical cap.
- Clamped camera latitude away from polar views so the rectangular projection is less likely to show only a thin cap of the world.
- Reduced the projection zoom ceiling from `4.0x` to `2.2x` and changed the default from `1.0x` to `0.75x` in both the JS state and the dashboard slider.
- Verified the live static JS endpoint is serving the updated code.
- Verified both static JS files parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: the Swarm world data is intact, and the map should reopen with a broader, less sparse ticker view.
- Next resume point: live-test visual density; tune radius/zoom/density targeting further if the balls still look too few or too sparse.

## 2026-04-28 21:02:32 +02:00

- Investigated the dead Swarm tab after the dashboard JavaScript extraction.
- Confirmed there was no existing browser-click harness: no Playwright, Puppeteer, jsdom, or Selenium dependency is installed.
- Added explicit `window` exports for dashboard inline handlers in `src/ETF_screener/dashboard/static/js/dashboard.js`, including `showTab`, Swarm controls, shortlist filters, strategy actions, and modal actions.
- Added `tests/test_dashboard_js.py`, a lightweight Node fake-DOM smoke test that loads `dashboard.js`, verifies `window.showTab`, and checks that `showTab("swarm")` reveals the Swarm section and activates its tab button.
- Found the live issue: the old uvicorn reloader process was still serving the pre-static app, so `/static/js/dashboard.js` returned `404` and the browser had no dashboard JS.
- Restarted the dashboard server cleanly; `/`, `/static/js/dashboard.js`, and `/static/js/browser-log-relay.js` now all return `200`.
- Updated `run_dashboard.ps1` so uvicorn reload watches `*.js` files too.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: the Swarm button path is covered by a smoke test, and the live server is serving the extracted JavaScript.
- Next resume point: reopen the dashboard and live-test Swarm tab loading; add Playwright later if we want true browser/canvas interaction coverage.

## 2026-04-28 20:52:25 +02:00

- Added FastAPI static serving in `src/ETF_screener/dashboard/app_fast.py` for dashboard browser assets under `/static`.
- Extracted the main dashboard script from `src/ETF_screener/dashboard/templates/index.html` into `src/ETF_screener/dashboard/static/js/dashboard.js`.
- Extracted the browser log relay script into `src/ETF_screener/dashboard/static/js/browser-log-relay.js`.
- Kept the template focused on HTML/CSS structure while preserving existing classic-script globals used by inline event handlers.
- Updated `tests/test_dashboard_api.py` so dashboard UI checks include the fetched static JavaScript source and verify both static script tags.
- Verified both extracted scripts parse with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py -q`; all 17 tests passed.
- Current status: the dashboard is still browser-driven, but the first JS extraction is complete and ready for a cleaner module/Web Worker split.
- Next resume point: split `dashboard.js` into smaller domain files, starting with Swarm simulation/rendering if playback performance needs more headroom.

## 2026-04-28 20:32:25 +02:00

- Implemented the first charged-sphere Swarm visual prototype in `src/ETF_screener/dashboard/templates/index.html`.
- Added stable Fibonacci-style sphere placement for grid cells so initial ticker positions do not clump along the equator.
- Added wealth-scaled positive-charge repulsion for real ticker balls on the sphere, with bounded sampled forces and velocity damping.
- Added a Swarm `Zoom` knob: low zoom shows the world as a ball, higher zoom shows a rectangular projection centered on current activity.
- Increased real ticker ball size and changed agents from wedge markers to smaller virus-like particles with spiky radial shapes.
- Kept the existing logical grid movement, local sense, investment return math, DNA, timeline, and chart drill-down behavior unchanged.
- Updated dashboard assertions for the zoom control, charged-sphere helpers, and virus-like agent copy.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`; parsed 2 scripts.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py -q`; all 17 tests passed.
- Confirmed the running dashboard still responds at `http://127.0.0.1:5000/`.
- Current status: the Swarm is visually projected onto a charged sphere, but the exact force/zoom/size constants still need live tuning.
- Next resume point: live-test the projection, tune charge caps and camera behavior, then consider adding drag/pan if auto-centering is too jumpy.

## 2026-04-28 20:25:24 +02:00

- Added another visual/physics requirement to `plan.md`: ticker nodes on the future sphere should behave like positive charges on a frictionless spherical surface.
- Captured that ticker charge should scale with simulated wealth, nodes should repel each other along the sphere surface, and the solver must avoid artificial equator clumping.
- Current status: planning/docs only; no sphere physics code has been implemented yet.
- Next resume point: prototype charge-weighted tangent-plane repulsion on unit-sphere coordinates with stable non-equatorial seeding and capped forces.

## 2026-04-28 20:22:41 +02:00

- Discussed current Swarm color semantics after live testing: real ticker dots use simulated-wealth green/pink shifts with shortlist-label fallback, dummy cells are muted slate, and agents use light/violet energy coloring with small energy bars.
- Captured the next visual direction in `plan.md`: make ticker balls larger, make agents smaller and virus-like, add a `Zoom` knob, and explore a spherical world rendered through a rectangular projection.
- Chose the conceptual camera model for the next visual pass: keep local neighborhood simulation semantics, but render the visible region like a map projection centered on the most active part of the sphere, with full zoom-out showing the world as a ball.
- Current status: no code changed for sphere/projection rendering yet; this turn only updated the living plan/progress notes.
- Next resume point: implement a first visual prototype for bigger ticker balls, virus-like agents, zoom control, and activity-centered projection without changing the investment/DNA rules.

## 2026-04-27 22:17:34 +02:00

- Added dividend-aware yfinance fetching in `src/ETF_screener/yfinance_fetcher.py` using actions data when available.
- Added a `dividends` column to `etf_data`, including lightweight schema upgrade support and dataframe upserts in `src/ETF_screener/database.py`.
- Preserved dividends through the incremental market refresh normalization path in `src/ETF_screener/market_data_service.py`.
- Extended `/api/swarm-history` so Swarm histories return `dates`, `closes`, and `dividends`, with safe zero-dividend fallback for older databases.
- Changed Swarm return math in `src/ETF_screener/dashboard/templates/index.html` so agent energy uses price return plus dividend contribution minus a universal 2.5% annual inflation hurdle.
- Added dividend contribution and real-step return details to the selected ticker card.
- Added human-readable investment rule interpretations for hotlist DNA in selected-agent cards, top-agent cards, and saved top-agent DNA payloads.
- Updated tests for dividend persistence, dividend history serialization, inflation/DNA UI contracts, and saved DNA rules.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\database.py src\\ETF_screener\\yfinance_fetcher.py src\\ETF_screener\\market_data_service.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`; parsed 2 scripts.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_market_data_service.py -q`; all 22 tests passed.
- Current status: Swarm agents now model total-return investing more realistically, and winner DNA is more directly readable as investment behavior.
- Next resume point: live-test whether the new rule interpretations are actually useful, then consider adding explicit dividend-preference DNA modules.

## 2026-04-27 21:47:31 +02:00

- Replaced the Swarm island projection with a stable auto-fit grid in `src/ETF_screener/swarm_world.py`.
- Bumped the Swarm artifact version to `swarm_v3_grid` and added persisted `grid_row` / `grid_col` support in `src/ETF_screener/database.py`.
- Extended `/api/swarm-world` to expose `layout`, `rows`, `columns`, `cell_width`, and `cell_height`, while real nodes now serialize `row`, `col`, and `is_dummy: false`.
- Changed the Swarm frontend to generate frontend-only dummy cells for empty grid intersections; dummy nodes are visible/sensible but cannot be opened as charts or saved as real DNA targets.
- Changed agents to discrete grid actors: each agent stores row/column, perceives cells within adjustable Chebyshev sense radius, and moves at most one grid step per decision.
- Added Swarm GUI knobs for `Sense` and `Agents / Node`; default seeding uses 100 agents per alternating grid node with a hard 5,000-agent cap.
- Kept existing timeline playback, jump-cost control, DNA autosave, top-agent panel, selected-agent inspector, and real-ticker chart drill-down behavior.
- Updated dashboard and Swarm world tests for the grid metadata, row/column placement, dummy-node UI contract, and new controls.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\database.py src\\ETF_screener\\swarm_world.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`; parsed 2 scripts.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_swarm_world_engine.py tests\\test_dashboard_api.py -q`; all 18 tests passed.
- Current status: Swarm now runs on a complete rectangular grid landscape with local perception and capped dense agent seeding.
- Next resume point: live-test the Swarm tab with a full cached universe and tune rendering or move simulation work to a Web Worker if 5,000-agent playback stutters.

## 2026-04-25 21:25:19 +02:00

- Hardened Swarm playback startup in `src/ETF_screener/dashboard/templates/index.html`.
- Added a single `startSwarmPlayback()` path that waits for loading, loads the world if needed, rebuilds agents after an ended run, and starts the animation loop reliably.
- Added `ensureSwarmAnimationLoop()` so Play and load completion share the same frame scheduling behavior.
- Added a `swarmLoadingPromise` guard so repeated Play/Refresh clicks do not race concurrent world/history loads.
- Disabled the Play button while Swarm loading is in progress and added dashboard assertions for the startup helpers.
- Updated `plan.md` with the more reliable Swarm Play path.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_swarm_world_engine.py -q`; all 17 tests passed.
- Current status: pressing Play should be forgiving whether the Swarm tab is still loading, stopped, finished, or empty of active agents.
- Next resume point: add a visible loading/ready indicator near the Play button if users still find startup ambiguous.

## 2026-04-25 21:15:51 +02:00

- Pinned Swarm ticker nodes to their seeded island coordinates; ticker worth and color can change, but ticker positions no longer move during playback.
- Replaced the old ticker-node physics step with a fixed-node worth updater in `src/ETF_screener/dashboard/templates/index.html`.
- Clarified Swarm copy so agent movement means target changes/travel between fixed ticker nodes, with distance represented as jump friction.
- Updated dashboard assertions and `plan.md` to reflect the fixed ticker map.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_swarm_world_engine.py -q`; all 17 tests passed.
- Current status: ticker nodes are stable landmarks; only wedge-shaped agents move.
- Next resume point: add a compact in-tab legend for fixed ticker nodes, agent wedges, energy bars, and jump friction.

## 2026-04-25 21:09:33 +02:00

- Changed the Swarm canvas visual language so ticker nodes remain round, while moving agents render as directional wedge markers with small energy bars.
- Updated Swarm copy to distinguish round ticker nodes from wedge-shaped learner agents.
- Added dashboard assertions for the wedge-agent rendering contract.
- Updated `plan.md` to record the new ticker/agent mark distinction and the next legend follow-up.
- Current status: the Swarm map no longer shows tickers and agents as two competing sets of balls.
- Next resume point: add a compact legend that explains island halos, ticker node colors, wedge agents, and energy bars directly in the Swarm tab.

## 2026-04-25 17:52:33 +02:00

- Added `/api/swarm-history` in `src/ETF_screener/dashboard/app_fast.py`, returning cache-only close-price history for current Swarm tickers without triggering network refreshes.
- Changed the Swarm browser simulation in `src/ETF_screener/dashboard/templates/index.html` to use cached close-to-close returns when available, with neutral returns/signals for missing or short histories.
- Replaced the synthetic EMA/RSI-like jump pressure with explicit behavior DNA modules: `ema_cross_up`, `ema_cross_down`, `rsi_low`, and `rsi_high`, with EMA modules carrying evolvable fast/slow periods and stay/jump weights.
- Expanded the selected-agent and top-agent UI so behavior DNA is readable after a run.
- Replaced manual DNA export with automatic saving of the top ten completed agents to `config/swarm_agent_dna.json` as `swarm_agent_dna_v2` JSON after each completed run.
- Updated `plan.md` with the visible island halos, history-backed behavior, browser DNA export decision, and next resume points.
- Added regression coverage for `/api/swarm-history` and the new DNA/export UI contract in `tests/test_dashboard_api.py`.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_swarm_world_engine.py -q`; all 17 tests passed.
- Current status: Swarm agents now decide stay/jump from explicit, evolvable behavior DNA over cached price history, and completed runs can export their best genomes.
- Next resume point: try a live full Swarm run, confirm `config/swarm_agent_dna.json` updates, then decide whether to add replay/import from that saved DNA JSON or move the heavier simulation work into a Web Worker.

## 2026-04-24 21:10:21 +02:00

- Changed market freshness toward a latest-available workflow in `src/ETF_screener/market_data_service.py`.
- Added blacklist/inactive filtering to the dashboard market refresher so known invalid tickers no longer count against active freshness or get refreshed by default.
- Changed freshness thresholds to allow `stale_after_days=0`, meaning the dashboard can ask for today's local-date daily bars instead of accepting data that is a few calendar days old.
- Changed market status so missing or stale active tickers make the status stale even if one ticker has today's date.
- Changed the dashboard market refresh endpoint default to `force=true` and `stale_after_days=0`, while preserving incremental delta fetches for existing ticker history.
- Updated the Shortlist tab refresh button to call the strict top-up path and show active-universe stale/missing counts.
- Changed chart drill-down freshness so opening a chart attempts to top up a ticker when its cached data is older than today's local date.
- Added regression coverage for blacklist filtering, zero-day refresh behavior, and the stricter dashboard API contract.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\market_data_service.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_market_data_service.py tests\\test_shortlist_engine.py tests\\test_dashboard_api.py tests\\test_swarm_world_engine.py -q`; all 23 tests passed.
- Started a fresh reload-enabled dashboard instance at `http://127.0.0.1:5001` because the existing `5000` server was still serving old code.
- Current status: the app now prefers the freshest obtainable active-universe data whenever the dashboard market refresh is used.
- Live cache note before a full refresh run: latest market date is `2026-04-24`, but strict active-universe status still reports 2,548 stale active tickers and 7 missing active tickers, with 1,270 blacklisted tickers excluded.
- Next resume point: run the dashboard `Refresh Market Data` action, or call `/api/market-data/refresh?depth=400&max_workers=8&force=true&stale_after_days=0`, then verify the active-universe stale count drops.

## 2026-04-24 20:00:01 +02:00

- Changed Swarm world placement in `src/ETF_screener/swarm_world.py` from score-bucket coordinates to a stable random-island layout.
- Bumped the cached world artifact version to `swarm_v2_islands` so old score-chart worlds rebuild automatically.
- Added per-node starting velocity and charge metadata in the world builder, with frontend fallbacks for older cached rows.
- Changed the Swarm canvas copy and background label so the world reads as a wrapped island projection rather than a quality/energy chart.
- Added frontend ticker-ball physics: visible tickers move on a wrapped rectangular projection, repel sampled neighbors, and scale charge from current simulated worth.
- Updated agent travel and jump-distance calculations to use wrapped shortest-path distances.
- Kept the self-organizing force lightweight by sampling neighbor repulsion instead of doing full all-pairs physics.
- Updated dashboard and Swarm engine tests for the island world version and moving-world UI.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\swarm_world.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_swarm_world_engine.py -q`; all 16 tests passed.
- Current status: the Swarm world now behaves like a self-organizing island arena instead of a nuclide-style score chart.
- Next resume point: tune the repulsion/charge constants in the live dashboard and consider moving node physics to a Web Worker if the large-agent run stutters.

## 2026-04-24 19:40:21 +02:00

- Updated Swarm v2 so agents no longer use global environment knowledge when choosing jumps.
- Removed shortlist score, momentum score, ticker energy, and current-step return from the agent jump scoring function.
- Changed jump inference to use each agent's own learned ticker memory, recent personal returns, exploration bias, and jump cost.
- Increased the initial Swarm population to `1200` agents with a cap of `1800`.
- Removed automatic respawning after death; dead agents are recorded in a completed-agent ledger instead.
- Added an end-of-run `Top Agents` panel that lists the ten most profitable agents/genomes when the timeline finishes or all agents die.
- Updated dashboard assertions for the top-agent panel, large initial population, and completed-agent ledger.
- Verified embedded dashboard JavaScript parses with Node `new Function(...)`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_swarm_world_engine.py -q`; all 16 tests passed.
- Current status: Swarm evolution is now less pre-informed and more population-driven, but the environment return stream is still synthetic until real cached history is connected.
- Next resume point: connect timeline returns to real cached ticker history while keeping agent decisions limited to observations they have personally earned.

## 2026-04-24 19:33:23 +02:00

- Added `plan.md` and `progress.md` to Git tracking.
- Implemented the first Swarm v2 slice in `src/ETF_screener/dashboard/templates/index.html`.
- Added timeline controls: slider, play/pause, stop, and restart-from-beginning behavior.
- Changed first-generation agent seeding so agents are spread evenly across the visible ticker land instead of all starting from the highest-energy subset.
- Added mutable agent genomes with EMA fast/slow, RSI length/buy/sell thresholds, spawn limit, mutation rate, jump-cost sensitivity, exploration bias, metabolism, and speed.
- Changed ticker and agent energy to start from a neutral `10000` baseline.
- Added timeline-step energy updates, jump energy costs, mutation-based splitting above each agent's own spawn limit, and death when agent energy drops below zero.
- Added a selected-agent inspector so clicking an agent shows its current energy and genome traits.
- Added dashboard template assertions in `tests/test_dashboard_api.py` for the new Swarm controls and genome fields.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_swarm_world_engine.py -q`; all 16 tests passed.
- Verified the embedded dashboard JavaScript parses with Node `new Function(...)`.
- Current status: Swarm v2 is interactive and genome-driven, but its timeline return model is still synthetic and derived from cached node scores rather than real historical bars.
- Next resume point: connect Swarm timeline steps to real cached ticker history, add a clearer visual legend, and consider a Web Worker before adding pheromone fields or heavier genetic controls.

## 2026-04-24 19:26:22 +02:00

- Refined the next Swarm milestone in `plan.md` from a raw idea into an implementation-ready Swarm v2 plan.
- Planned mutable agent traits for EMA/RSI parameters, spawn limit, mutation rate, jump cost sensitivity, and exploration bias.
- Planned a replayable timeline UI with slider, play, stop, and restart-from-beginning controls.
- Planned even first-generation agent distribution across ticker land and neutral starting ticker energy of `10000`.
- Chose a first-pass jump inference rule: agents score candidate tickers using their own EMA/RSI traits, recent momentum, distance/jump cost, and exploration bias, then jump only when that beats staying put.
- Current status: this is now a design-ready next milestone; no Swarm v2 code has been implemented yet.
- Next resume point: implement the Swarm v2 simulation state and controls in the dashboard, then add focused tests for the new UI/API contract.

## 2026-04-23 22:11:36 +02:00

- Added persisted `swarm_world_artifacts` support to `src/ETF_screener/database.py`.
- Added `src/ETF_screener/swarm_world.py`, which reuses cached shortlist artifacts to build a stable rectangular ticker world with energy, momentum, freshness, radius, and deterministic coordinates.
- Added `/api/swarm-world` to `src/ETF_screener/dashboard/app_fast.py`.
- Added a fourth `Swarm` tab to `src/ETF_screener/dashboard/templates/index.html` with a canvas-based ticker world, label filters, pinned-node inspection, and live bug agents that wander, feed, split, and respawn.
- Kept the Swarm implementation cache-first by deriving it from shortlist artifacts rather than recomputing ticker analysis live in the request path.
- Added regression coverage in `tests/test_swarm_world_engine.py` and extended `tests/test_dashboard_api.py` for the new tab and world endpoint.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_swarm_world_engine.py tests\\test_dashboard_api.py -q`; all 16 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\database.py src\\ETF_screener\\swarm_world.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Current status: the dashboard now has a fourth exploratory tab with all cached tickers plotted as balls in a rectangular world plus a first-pass agent simulation on top.
- Next resume point: decide whether to move the simulation to a Web Worker, then add pheromone fields and the first explicit GA controls.

## 2026-04-23 21:53:02 +02:00

- Changed market refresh from fixed-window refetching to incremental delta updates in `src/ETF_screener/market_data_service.py`.
- Extended `src/ETF_screener/yfinance_fetcher.py` so refresh jobs can request explicit `start_date` / `end_date` windows instead of only `N` trailing days.
- Updated `src/ETF_screener/database.py` inserts to upsert existing ticker/date rows, which lets overlap windows recompute indicators cleanly during delta refreshes.
- Updated the chart endpoint in `src/ETF_screener/dashboard/app_fast.py` to use the shared incremental `refresh_ticker_data()` path instead of its own full-history fetch logic.
- Added regression coverage in `tests/test_market_data_service.py` for delta-window refresh behavior and updated `tests/test_dashboard_api.py` to match the shared refresher flow.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_market_data_service.py tests\\test_dashboard_api.py -q`; all 17 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\yfinance_fetcher.py src\\ETF_screener\\database.py src\\ETF_screener\\market_data_service.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Current status: stale data refresh now pulls only the missing slice plus a warm-up buffer, reuses existing local artifacts, and still rebuilds shortlist outputs afterward.
- Next resume point: decide whether freshness thresholds should use trading days, then add the next shortlist filters.

## 2026-04-23 21:45:09 +02:00

- Added `src/ETF_screener/market_data_service.py` with a reusable `MarketDataRefresher` that reports cache freshness and refreshes stale tickers in parallel.
- Added market freshness helpers to `src/ETF_screener/database.py` so the dashboard can distinguish latest market date from latest shortlist rebuild time.
- Added `/api/market-status` and `/api/market-data/refresh` to `src/ETF_screener/dashboard/app_fast.py`.
- Updated the shortlist UI in `src/ETF_screener/dashboard/templates/index.html` to show market freshness, expose a `Refresh Market Data` button, and relabel the summary date as `Data As Of`.
- Updated the chart endpoint so opening a stale ticker chart now fetches fresher data for that ticker automatically.
- Added tests in `tests/test_market_data_service.py` and extended `tests/test_dashboard_api.py` for market freshness endpoints and controls.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_market_data_service.py tests\\test_dashboard_api.py -q`; all 16 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\database.py src\\ETF_screener\\market_data_service.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Current status: stale shortlist dates are now explainable in-product, and there is a direct UI path to refresh the underlying market data instead of only rebuilding artifacts.
- Next resume point: decide whether stale market data should trigger an optional auto-refresh prompt, then add the next shortlist filters.

## 2026-04-23 21:36:32 +02:00

- Added client-side `All` / `Buy` / `Watch` / `Skip` shortlist filters in `src/ETF_screener/dashboard/templates/index.html`.
- Kept the shortlist interaction cache-first by filtering the already-loaded shortlist rows in memory instead of triggering new API calls or recomputation.
- Added dashboard test coverage for the new shortlist filter controls in `tests/test_dashboard_api.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py -q`; all 12 tests passed.
- Current status: shortlist labels are now both scoring outputs and usable browsing controls.
- Next resume point: add the next practical filters like region, asset class, and freshness.

## 2026-04-23 21:27:26 +02:00

- Scoped the top header controls in `src/ETF_screener/dashboard/templates/index.html` so they read as Screener-only controls instead of looking global across every tab.
- Removed the implicit screener auto-run on strategy selection and removed the initial auto-screen on dashboard load, so screening is now an explicit `Run Screener` action.
- Added clearer shortlist guidance text so the tab reads as a discovery queue that leads into the chart drill-down, not an auto-buy list.
- Kept the existing chart workflow intact while reducing cross-tab UI confusion.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py -q`; all 12 tests passed.
- Current status: the dashboard mental model is cleaner, with less surprising auto-execution and clearer tab ownership.
- Next resume point: add shortlist filters and richer product metadata so the ETF-first workflow becomes more actionable.

## 2026-04-23 21:22:40 +02:00

- Added a dedicated `Shortlist` tab to `src/ETF_screener/dashboard/templates/index.html`.
- Wired the tab to lazily fetch `/api/shortlist`, reuse cached shortlist artifacts by default, and offer an explicit refresh path when needed.
- Rendered shortlist summary cards plus ranked ETF cards that route into the existing screener chart view, so the graphics stay the drill-down layer instead of being duplicated.
- Updated `tests/test_dashboard_api.py` so the dashboard tab expectations now include the new `Shortlist` workflow tab.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py -q`; all 12 tests passed.
- Current status: the ETF-first shortlist flow is now visible in the dashboard and backed by persisted artifacts.
- Next resume point: add shortlist filters and richer product metadata so the rankings feel more actionable and less heuristic.

## 2026-04-23 21:18:34 +02:00

- Added persistent shortlist schema in `src/ETF_screener/database.py` with `etf_metadata` and `etf_shortlist_artifacts` tables plus read/write helpers.
- Added `src/ETF_screener/shortlist_engine.py`, which prefers cached parquet artifacts, falls back to DB data when needed, enriches only when indicators are missing, and analyzes tickers in parallel threads.
- Implemented an initial ETF-first scoring model that blends product, exposure, and technical state into persisted `Buy` / `Watch` / `Skip` shortlist artifacts with reasons and component breakdowns.
- Added `/api/shortlist` in `src/ETF_screener/dashboard/app_fast.py` so the dashboard can read the cached shortlist without recomputing it on every request.
- Added regression coverage in `tests/test_shortlist_engine.py` and extended `tests/test_dashboard_api.py` for shortlist API serialization.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_shortlist_engine.py tests\\test_dashboard_api.py -q`; all 14 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\database.py src\\ETF_screener\\shortlist_engine.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Current status: the repo now has a reusable shortlist artifact backend, but the UI still needs a dedicated shortlist view to make it a first-class workflow.
- Next resume point: build the shortlist frontend tab/card view and wire it to the existing chart drill-down.

## 2026-04-23 20:56:40 +02:00

- Added shared DSL recency support in `src/ETF_screener/scripts/churn_strategies.py`.
- `parse_dsl_content()` now reads `MAX_DAYS` aliases, and `find_recent_entry_days()` now computes the newest still-valid trigger age from trigger/filter/exit semantics.
- Filled the direct `entry_script` / `exit_script` strategy path with the same recency metadata so CLI custom runs stay aligned with saved DSL behavior.
- Wired the dashboard screen endpoint in `src/ETF_screener/dashboard/app_fast.py` to use movie-scan style recency when a strategy declares `MAX_DAYS`, while keeping the old latest-bar-only rule for strategies without it.
- Replaced the custom backward scan loop in `src/ETF_screener/scripts/movie_scanner.py` with the shared recency helper so scanner and strategy screening now agree on signal age logic.
- Added regression tests in `tests/test_churn_strategies.py` and `tests/test_dashboard_api.py` for DSL parsing, age detection, and the `MAX_DAYS` dashboard behavior.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_churn_strategies.py tests\\test_dashboard_api.py -q`; all 14 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\scripts\\churn_strategies.py src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\movie_scanner.py`.
- Current status: strategy flows now support opt-in recency windows from the DSL, and movie scan logic is shared instead of duplicated.
- Next resume point: run one or two real strategies with `MAX_DAYS` through the live screen and movie scanner to confirm the real-data experience.

## 2026-04-23 20:37:51 +02:00

- Simplified the Plotly strategy ribbon model in `src/ETF_screener/plotter_plotly.py`.
- Merged `QUALIFY` blocks into a single `SETUP` ribbon lane so charts no longer draw a separate qualify strip.
- Changed aggregate evaluation to use the merged setup lane and kept `INVALIDATE` as a veto on the positive stack.
- Gated `INVALIDATE` rendering so it only appears on bars where the positive stack was otherwise ready and then got vetoed.
- Added Plotly regression coverage for merged setup/qualify behavior and invalidate gating in `tests/test_plotter_plotly.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_plotter_plotly.py -q`; all 19 tests passed.
- Current status: the chart semantics now match the intended mental model more closely, with less ribbon clutter.
- Next resume point: visually spot-check one or two real dashboard strategies to confirm the simplified ribbons read well in practice.

## 2026-04-23 20:22:11 +02:00

- Added `update-devtools.ps1` at the repo root and the reusable implementation in `scripts/update-devtools.ps1`.
- Added matching `update-devtools` helpers to both `profile.ps1` copies and documented the new command in `README.md`.
- Created root-level `plan.md` and `progress.md` as tracked resume docs for future turns.
- Syntax-checked the new and updated PowerShell scripts successfully.
- Real machine run: upgraded stable VS Code from `1.96.4` to `1.117.0` through `winget`.
- Real machine run: `code --update-extensions` still reports a built-in `github.copilot-chat` downgrade conflict, and the script now marks that as a failed maintenance pass even when the CLI itself returns `0`.
- Mocked verification passed for missing `winget`, missing `code`, already-current VS Code, upgrade failure while VS Code is running, and extension-output error detection.
- Current status: implementation complete, VS Code is updated, and the maintenance command is correctly surfacing the remaining extension conflict.
- Next resume point: decide whether to keep that built-in extension conflict as a hard failure or add a narrower ignore rule for that specific downgrade case.

## 2026-04-23 20:11:16 +02:00

- Added the initial `update-devtools` implementation plan to the repo root.
- Started wiring a dedicated VS Code maintenance command, profile helper, README entry, and resumable working docs.
- Next resume point: run verification, capture results, and refresh both living docs with final status for this turn.
