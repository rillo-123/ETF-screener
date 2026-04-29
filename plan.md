# Plan

Last updated: 2026-04-28 21:47:42 +02:00

## Current objective

Build an ETF-first dashboard that reuses cached artifacts for shortlist discovery, swarm exploration, and chart drill-down.

## Current state

- The database now has dedicated `etf_metadata` and `etf_shortlist_artifacts` tables for persisted shortlist state.
- `src/ETF_screener/shortlist_engine.py` now builds a reusable shortlist snapshot from cached parquet first, DB fallback second, and analyzes the universe in parallel threads.
- The shortlist engine scores each ticker across product, exposure, and technical state, then persists `Buy` / `Watch` / `Skip` artifacts with reason strings and score components.
- The dashboard now exposes `/api/shortlist` as a cache-first read API that only rebuilds when the market data is newer or `refresh=true` is requested.
- The dashboard now has a dedicated `Shortlist` tab that consumes the cached shortlist API and routes card clicks into the existing chart drill-down.
- The database now also has a persisted `swarm_world_artifacts` table so exploratory layout state can be reused instead of recalculated on every tab open.
- `src/ETF_screener/swarm_world.py` now projects shortlist artifacts into a stable rectangular grid with per-ticker energy, row/column, radius, and coordinates.
- The dashboard now exposes `/api/swarm-world` and a fourth `Swarm` tab that renders cached real ticker nodes on the charged sphere.
- The Swarm tab now has a replayable timeline slider with play, stop, and restart controls.
- The Swarm Play path now loads the world if needed, rebuilds agents after an ended run, and reliably starts the animation loop from one entrypoint.
- Swarm agents currently start from random alternating real nodes, capped at 5,000 agents, and carry mutable fast/slow EMA, RSI, spawn-limit, mutation-rate, jump-cost, exploration, metabolism, and speed traits.
- Swarm ticker and agent energy now start from a neutral `10000` baseline, agents gain or lose energy from the current timeline step, spend energy to jump, split when above their mutable spawn limit, and die below zero.
- Ticker nodes persist with a visible wealth floor; tickers should only disappear if an explicit delisting/inactive-ticker model is added.
- The Swarm side panel now exposes a selected-agent inspector so the active genome can be read while the simulation runs.
- Swarm jump decisions now use learned ticker memory, exploration, jump cost, behavior DNA, and global investor-like screening over all real tickers.
- Swarm now starts with more than a thousand agents and records completed agents so the end of a run can show the ten most profitable genomes.
- The Swarm world now uses an auto-fit square-ish grid for logical neighborhood coordinates, while rendering only real tickers on the spherical map.
- The Swarm tab now describes agent knowledge as a global ticker scan; the old local sense knob has been removed from the GUI.
- The Swarm tab now starts in a lighter browser-safe density mode: agents per alternating node defaults to `20`, with the hard `5000` ceiling still reachable at high slider values.
- Tickers and agents now use different canvas marks: tickers stay as round nodes, while agents draw as directional wedge markers with small energy bars.
- Agent motion now uses direct global jumps between real tickers based on each agent's DNA criteria.
- Swarm ticker balls are white/neutral, with radius proportional to `log10(simulated wealth)`; color no longer encodes simulated gain/loss or shortlist label.
- Globe zoom now uses a smaller ticker draw radius than projected map zoom so thousands of white ticker balls remain distinct instead of merging into a few blobs.
- Initial sphere placement now hashes ticker identity into the Fibonacci sphere seed and runs a short load-time relaxation pass so the first frame starts less clustered.
- The Swarm canvas now has a first charged-sphere projection prototype: cells get stable non-equatorial sphere positions, real ticker balls repel as wealth-scaled positive charges, and the camera projects the active region onto the rectangular canvas.
- The Swarm tab now has a `Zoom` knob; full zoom-out shows the charged world as a ball, while zoomed-in views show a rectangular projection with a stable non-polar camera anchor.
- Agents now render as smaller virus-like particles instead of wedge markers, while ticker balls render larger for better visibility.
- Market data storage now preserves yfinance dividend actions when available.
- The dashboard now exposes `/api/swarm-history`, a cache-only total-return history endpoint for Swarm tickers with close and dividend series.
- Swarm agent energy now uses real-return steps: price change plus dividend contribution minus a small annual inflation hurdle.
- Swarm agents now carry behavior DNA modules such as `ema_cross_up`, `ema_cross_down`, `rsi_low`, and `rsi_high`, with evolvable fast/slow EMA periods, thresholds, and stay/jump weights.
- Swarm hotlist DNA now includes human-readable investment rule interpretations so winning agents can be translated into behavior rules.
- Swarm timeline returns now use cached close-to-close history when available, falling back to neutral returns for missing or short histories.
- The Swarm top-agent panel now auto-saves the ten best agent DNA records as `config/swarm_agent_dna.json` using `swarm_agent_dna_v2` JSON.
- The dashboard browser code has been moved out of the Jinja template into static files served from `/static/js/dashboard.js` and `/static/js/browser-log-relay.js`.
- Dashboard inline handlers are explicitly exposed on `window`, and a Node-based JavaScript smoke test now verifies the Swarm tab switch path.
- The top header controls are now explicitly treated as Screener-only controls, and strategy selection no longer auto-runs the screener.
- The shortlist tab now supports explicit `All` / `Buy` / `Watch` / `Skip` filtering without refetching or recomputing the snapshot.
- The dashboard now exposes market freshness status plus a `Refresh Market Data` path that refreshes stale tickers in parallel and rebuilds the shortlist afterward.
- Market refresh now reuses existing local history and fetches only the missing delta plus an indicator warm-up window instead of re-downloading a full fixed history window for every stale ticker.
- The chart drill-down now uses the same incremental ticker refresh path, so opening a stale chart tops up that ticker instead of forcing a full-history refill.
- Market freshness now uses a stricter active-universe view: blacklisted/inactive tickers are ignored, missing/stale active tickers make the cache status stale, and a manual dashboard refresh tops up all active tickers with incremental fetches.
- Chart drill-down now treats anything older than today's local date as stale so opened charts attempt to use the newest available daily bars.
- Regression coverage now exists for shortlist artifact ranking, snapshot reuse, and the shortlist API contract.
- `plan.md` and `progress.md` are now the repo-tracked resume surface for future work turns.

## Locked decisions

- Prefer cached artifacts over request-time recomputation whenever the snapshot is fresh.
- Distinguish clearly between `data as of` and `computed at`; rebuilding the shortlist alone should never pretend to make stale market data fresh.
- Use parallel threads for per-ticker shortlist analysis because this path is mostly storage reads plus moderate indicator work.
- Use parallel threads for stale market-data refresh, but write refreshed artifacts back sequentially so we avoid SQLite threading trouble.
- Prefer delta fetches over full-history refills whenever local ticker history already exists; only fall back to a deeper full fetch when the cache is genuinely too thin.
- Treat the dashboard `Refresh Market Data` action as a latest-available top-up for the active tracked universe, not a "fresh enough within a few days" no-op.
- Exclude blacklisted and inactive tickers from freshness debt unless an explicit revalidation workflow is added later.
- Keep the shortlist engine ETF-first; DSL remains optional and secondary.
- Keep the existing graphics and chart/ribbon work as the drill-down view rather than removing it.
- Keep the Swarm tab cache-first by deriving it from shortlist artifacts instead of building a separate scoring pipeline.
- Keep Swarm simulation browser-side for now, but avoid letting the Jinja template become the application bundle; static JavaScript files are the baseline for the next modular split.
- Keep the local dashboard runner watching `*.js` files now that browser code lives under `src/ETF_screener/dashboard/static/js`.
- Prefer explicit user actions over auto-running scans when switching context or selecting a strategy.
- Model Swarm agents as small mutable genomes instead of hard-coded dots: indicator windows, thresholds, jump behavior, spawn limits, and mutation rate should all be traits.
- Treat Swarm behavior as explicit DNA rule modules where parameters and action weights can mutate over generations.
- Interpret EMA cross behavior as a true fast/slow EMA crossover, for example EMA 30 crossing EMA 50.
- Save top-agent DNA through the dashboard backend after each completed Swarm run; keep it as the latest config snapshot until run history/audit requirements are clearer.
- Keep ticker node coordinates fixed during simulation so users can build spatial memory of the ETF map.
- Do not generate dummy Swarm tickers now that the charged sphere is self-organizing; empty grid intersections remain only implicit gaps in local perception.
- Retire local Chebyshev grid sense for the spherical Swarm behavior model; agents now have total knowledge of available real tickers and decide from their own global criteria.
- Treat Swarm population as agents per alternating grid node, default `100`, with a hard effective cap of `5000`.
- Treat dividends as part of investable agent energy when yfinance provides them; fall back to price-only behavior when dividends are absent.
- Use inflation as a universal hurdle, not as a penalty for sitting still.
- Treat ticker survival separately from agent survival: agents can die below zero, but real ticker nodes remain visible unless the ETF is delisted or removed from the active universe.
- Keep top-agent DNA meaningful to a human investor by saving both numeric genome parameters and plain-language behavior rules.
- Keep Swarm visual semantics legible: tickers should be larger than agents, ticker color should stay neutral, and zoomed-out views may intentionally aggregate/fuzz fine detail.
- Treat the sphere/projection Swarm world as both the visual layer and the conceptual investment landscape; do not preserve grid movement if it makes jumping unintuitive.
- Treat global jumping as the next meaningful behavior experiment: an agent may jump away from a winning position when its DNA says another ticker has a stronger global setup, such as low RSI, EMA cross, dividend preference, or drawdown avoidance.
- Model ticker layout on the sphere as positive charges on a frictionless surface: ticker charge scales with simulated wealth, ticker nodes repel each other, and the solver must avoid artificial equator clumping.
- Treat the Swarm timeline as a replayable simulation over historical market dates, with explicit play, stop, and restart controls instead of a purely ambient animation.
- Keep `plan.md` and `progress.md` tracked at the repo root.
- Refresh both docs on every future implementation turn when plan or progress changes meaningfully.

## Next steps

- Live-test the global, historically available screening model: agents may inspect current/past indicator state for all real tickers at the current timeline step, but must not see future returns.
- Check that winner DNA explains when to hold, when to jump while ahead, and what kind of ticker setup to jump toward.
- Live-test and tune the charged-sphere prototype: charge caps, velocity damping, zoom range, activity-centering, ticker ball sizes, and virus-agent visibility.
- Watch whether the new anchored camera still shows enough ticker density during active runs; if it remains sparse, add a density-aware viewport target instead of pure activity centering.
- Improve sphere projection polish: add drag/pan later if auto-centering feels too jumpy, and add a clearer legend for full-globe versus projected-map modes.
- Split `dashboard.js` into smaller domain files next, with Swarm simulation/rendering as the highest-value candidate for a module or Web Worker.
- Tune large-population grid performance now that the default request can seed up to 5,000 agents; a Web Worker is the likely next step if the main thread starts to stutter.
- Tune large-population grid performance before raising default density again; the current browser-safe path caps default agents dynamically, trims trails, limits drawn agents, and limits loaded history records.
- Add a compact Swarm legend for ticker colors, virus-like agents, energy bars, sense radius, and selected-agent highlighting.
- Add fuller browser-level verification for Swarm canvas interaction if Playwright becomes part of the dashboard test flow; the current Node smoke test covers basic tab switching without a real browser.
- Consider moving the Swarm simulation to a Web Worker before adding many more agents, trails, pheromone fields, or heavier visuals.
- Add import/replay from `config/swarm_agent_dna.json` after the autosaved DNA workflow proves useful.
- Add richer behavior modules next, such as low-RSI entry, EMA cross entry, dividend preference, RSI crossing its own signal line, drawdown avoidance, profit-protection jumps, and global exploration preferences.
- Decide whether market refresh should stay manual-only or whether we should offer an opt-in auto-refresh prompt when active-universe data is not at the latest available date.
- Decide whether the strict local-date freshness threshold should later become exchange-calendar aware, especially around weekends and exchange holidays.
- Add the next shortlist filters and sort controls in the UI: region, asset class, issuer, and freshness are the best follow-ups now that `Buy / Watch / Skip` is in place.
- Add the next Swarm layer: explicit pheromone fields, richer hover overlays, and controls for seeding a run from exported top-agent DNA.
- Improve metadata quality beyond `config/etfs.json` heuristics so product scoring can include TER, fund size, domicile, and distribution policy later.
- Decide whether the shortlist tab should open charts in-place later or keep using the current screener chart surface as the single drill-down.
- Keep updating `plan.md` and `progress.md` on every future implementation turn when state changes meaningfully.

## Blockers and risks

- Current product and exposure scoring is intentionally heuristic because the repo does not yet store richer ETF metadata like TER or AUM.
- The shortlist tab now has label filtering, but it still lacks richer ETF product facts and broader filter/sort controls.
- The Swarm tab currently uses a lightweight browser simulation without a worker or persisted run ledger, so it is exploratory rather than analytically mature.
- Swarm grid mode needs careful performance control because timeline replay, up to 5,000 agents, mutation, local perception scoring, and hundreds of ticker histories can become expensive in the browser.
- Sphere/projection rendering can add visual cost; zoomed-out mode should draw simplified agents and possibly aggregate cells if the canvas gets fuzzy or slow.
- Charge-weighted ticker repulsion can become unstable if rich nodes exert too much force; cap charge scaling and use bounded tangent-plane velocity so the sphere remains legible.
- Jump inference should stay explainable at first; if the behavior becomes too clever too early, it will be hard to tell whether agents are learning or merely chasing noise.
- Cached-history gaps produce neutral behavior/return signals for affected tickers, which is safe but can make underfilled histories less informative.
- Dividend history depends on yfinance action availability; missing dividends safely behave as zero dividends.
- Full-universe market refresh can take time on a large Xetra universe, so we should be careful about turning it into an automatic page-load behavior.
- Delta refresh is now much lighter on network usage, but a full-universe pass can still take noticeable time because thousands of tickers may each require a small incremental request.
- A real browser automation harness is still absent; current JavaScript coverage is a lightweight Node fake-DOM smoke test plus syntax parsing.
- Repo worktree already contains unrelated local changes, so edits should stay isolated to the new maintenance flow and docs.
