# Blockers and risks

- The new Nasdaq universe is intentionally curated from the official listing directory, but U.S. common-share classification is still heuristic and may need tuning as edge-case securities show up in results.
- The first Nasdaq vitality filter is intentionally simple and recent-data based; if it feels too loose or too harsh, the next tuning step is threshold work rather than more UI.
- Full-universe Nasdaq refresh can be meaningfully heavier than Sweden, so manual refresh and cached query behavior remain important for keeping the GUI responsive.

- Current product and exposure scoring is intentionally heuristic because the repo does not yet store richer ETF metadata like TER or AUM.
- The shortlist tab now has label filtering, but it still lacks richer ETF product facts and broader filter and sort controls.
- The Swarm tab currently uses a lightweight browser simulation without a worker or persisted run ledger, so it is exploratory rather than analytically mature.
- Swarm grid mode needs careful performance control because timeline replay, up to 5,000 agents, mutation, local perception scoring, and hundreds of ticker histories can become expensive in the browser.
- Sphere or projection rendering can add visual cost; zoomed-out mode should draw simplified agents and possibly aggregate cells if the canvas gets fuzzy or slow.
- Charge-weighted ticker repulsion can become unstable if rich nodes exert too much force; cap charge scaling and use bounded tangent-plane velocity so the sphere remains legible.
- Jump inference should stay explainable at first; if the behavior becomes too clever too early, it will be hard to tell whether agents are learning or merely chasing noise.
- Cached-history gaps produce neutral behavior or return signals for affected tickers, which is safe but can make underfilled histories less informative.
- Dividend history depends on yfinance action availability; missing dividends safely behave as zero dividends.
- Full-universe market refresh can take time on a large Xetra universe, so we should be careful about turning it into an automatic page-load behavior.
- Delta refresh is now much lighter on network usage, but a full-universe pass can still take noticeable time because thousands of tickers may each require a small incremental request.
- Caching the screen universe reduces repeated reads, but the actual backtest workload is still intentionally heavy until we decide how much of it should be cached or precomputed.
- GPU acceleration is not a good first fix for the current bottlenecks because the slowest pieces are still SQLite, yfinance, and per-ticker control flow rather than raw rasterization or matrix math.
- Process workers help the scripted backtest path, but they still do not change the fact that the underlying workload is intentionally heavy for large ticker sets.
- The result cache is keyed by the latest ticker date so stale outputs should fall away automatically when fresh market data arrives.
- A real browser automation harness is still absent; current JavaScript coverage is a lightweight Node fake-DOM smoke test plus syntax parsing.
- Repo worktree can contain unrelated local changes, so edits should stay isolated to the active maintenance flow and docs.
