# Progress

## 2026-05-22 00:00:03 +02:00

- Added a new early-entry strategy, `supertrend_st_crossdown_ema50_slope_turnup.dsl`, that keeps `ema_200_slope > 0`, requires a recent Supertrend crossdown below `ema_50`, and triggers when `ema_50_slope` turns positive.
- Updated the DSL parser coverage and added a churn/backtest smoke test so the new trigger and setup window are both verified.
- Verified with `python -m pytest -q tests/test_dsl_parser.py tests/test_churn_strategies.py`; all 13 tests passed.
- Current status: the early-entry milestone is set and the repo notes now reflect the new strategy checkpoint.
- Next resume point: if you want to tune it further, decide whether to shorten the Supertrend lookback window or widen it by a few bars.

## 2026-05-15 16:03:13 +02:00

- Collapsed the user-facing launcher surface into a single root `run.ps1` frontend and moved the dashboard implementation into `scripts/run_dashboard.ps1`.
- Redirected the old root `run_*.ps1` entrypoints into the scripts folder, updated the dashboard bootstrap flow, and pointed the workflow/test callers at `scripts/run_all_tests.ps1`.
- Updated the README so the launch examples now center on `run.ps1` instead of the individual root wrappers.
- Verified the dashboard API/JS tests still pass after the launcher refactor.
- Next resume point: run the new `run.ps1` frontend end to end and confirm the dashboard launcher behaves as expected.

## 2026-05-10 14:36:19 +02:00

- -Summary
- Next resume point: Review the latest commit and pick up the next implementation task.

## 2026-05-10 14:35:05 +02:00

- -Summary
- Next resume point: Applied fixes before stopping: E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:5:1,   |, 3 | """Backtesting engine for ETF trading strategies.""", 4 |, 5 | import hashlib,   | ^^^^^^^^^^^^^^, 6 | import logging, 7 | import re,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:6:1,   |, 5 | import hashlib, 6 | import logging,   | ^^^^^^^^^^^^^^, 7 | import re, 8 | import sys,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:7:1,   |, 5 | import hashlib, 6 | import logging, 7 | import re,   | ^^^^^^^^^, 8 | import sys, 9 | from pathlib import Path,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:8:1,   |, 6 | import logging, 7 | import re, 8 | import sys,   | ^^^^^^^^^^, 9 | from pathlib import Path,   |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:9:1,    |,  7 | import re,  8 | import sys,  9 | from pathlib import Path,    | ^^^^^^^^^^^^^^^^^^^^^^^^, 10 |, 11 | import numpy as np,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:11:1,    |,  9 | from pathlib import Path, 10 |, 11 | import numpy as np,    | ^^^^^^^^^^^^^^^^^^, 12 | import pandas as pd,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:12:1,    |, 11 | import numpy as np, 12 | import pandas as pd,    | ^^^^^^^^^^^^^^^^^^^, 13 |, 14 | from ETF_screener.database import ETFDatabase,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:14:1,    |, 12 | import pandas as pd, 13 |, 14 | from ETF_screener.database import ETFDatabase,    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^, 15 | from ETF_screener.indicators import (, 16 |     calculate_adx,,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:15:1,    |, 14 |   from ETF_screener.database import ETFDatabase, 15 | / from ETF_screener.indicators import (, 16 | |     calculate_adx,, 17 | |     calculate_ema,, 18 | |     calculate_macd,, 19 | |     calculate_rsi,, 20 | |     calculate_rsi_ema,, 21 | |     calculate_stochastic,, 22 | |     calculate_stoch_rsi,, 23 | |     calculate_supertrend,, 24 | |     calculate_linreg_slope,, 25 | |     calculate_tsi,, 26 | | ),    | |_^, 27 |   from ETF_screener.strategy_manager import CachedStrategyManager,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:27:1,    |, 25 |     calculate_tsi,, 26 | ), 27 | from ETF_screener.strategy_manager import CachedStrategyManager,    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^, 28 |, 29 | logger = logging.getLogger(__name__),    |, , F841 Local variable `price_col` is assigned to but never used,    --> src\ETF_screener\backtester.py:184:13,     |, 182 |             df["Date"] = pd.to_datetime(df.get("Date", df.get("date"))), 183 |             df = df.sort_values("Date").reset_index(drop=True), 184 |             price_col = "Close" if "Close" in df else "close",     |             ^^^^^^^^^, 185 |             kwargs = strategy_kwargs or {},     |, help: Remove assignment to unused variable `price_col`, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:5:1,   |, 3 | """SQLite database interface for ETF data persistence.""", 4 |, 5 | import sqlite3,   | ^^^^^^^^^^^^^^, 6 | from pathlib import Path, 7 | from typing import Optional,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:6:1,   |, 5 | import sqlite3, 6 | from pathlib import Path,   | ^^^^^^^^^^^^^^^^^^^^^^^^, 7 | from typing import Optional,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:7:1,   |, 5 | import sqlite3, 6 | from pathlib import Path, 7 | from typing import Optional,   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^, 8 |, 9 | import pandas as pd,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:9:1,   |, 7 | from typing import Optional, 8 |, 9 | import pandas as pd,   | ^^^^^^^^^^^^^^^^^^^,   |, , F821 Undefined name `logger`,    --> src\ETF_screener\market_data_service.py:356:13,     |, 354 |         promoted = self.delisting_tracker.promote_aged_missing(threshold_days=14), 355 |         if promoted:, 356 |             logger.info("Promoted %d missing tickers to blacklist", len(promoted)),     |             ^^^^^^, 357 |         self._emit_progress(, 358 |             progress_callback,,     |, , E402 Module level import not at top of file,  --> src\ETF_screener\storage.py:5:1,   |, 3 | """Data storage utilities for parquet files.""", 4 |, 5 | from pathlib import Path,   | ^^^^^^^^^^^^^^^^^^^^^^^^, 6 |, 7 | import pandas as pd,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\storage.py:7:1,   |, 5 | from pathlib import Path, 6 |, 7 | import pandas as pd,   | ^^^^^^^^^^^^^^^^^^^,   |, , F841 Local variable `trigger_trace` is assigned to but never used,    --> tests\test_plotter_plotly.py:542:5,     |, 540 |         df, "TEST", strategy_content=strategy_content, 541 |     ), 542 |     trigger_trace = next(,     |     ^^^^^^^^^^^^^, 543 |         t, 544 |         for t in fig.data,     |, help: Remove assignment to unused variable `trigger_trace`, , Found 19 errors., No fixes available (2 hidden fixes can be enabled with the `--unsafe-fixes` option)., black.

## 2026-05-07 19:06:55 +02:00

- -Summary
- Next resume point: Review the latest commit and pick up the next implementation task.

## 2026-05-06 23:26:06 +02:00

- -Summary
- Next resume point: Review the latest commit and pick up the next implementation task.

## 2026-05-06 22:09:43 +02:00

- -Summary
- Next resume point: Review the latest commit and pick up the next implementation task.

## 2026-05-06 22:08:43 +02:00

- Switched the dashboard to a local Three.js loader so the Swarm globe no longer depends on the CDN.
- Added swarm renderer diagnostics to the browser console and confirmed the earlier missing graticule was caused by Three.js not loading.
- The debug Swarm globe now renders visible sphere-hugging cap geometry instead of floating sprite markers, and the globe/graticule are visible in live testing.
- Next resume point: Reload the debug Swarm globe, live-tune cap depth and contact behavior, and decide whether the next pass should emphasize exact tangency or richer cap shading.

## 2026-05-05 22:47:42 +02:00

- -Summary
- Next resume point: Review the latest commit and pick up the next implementation task.

## 2026-05-05 22:47:12 +02:00

- -Summary
- Next resume point: Applied fixes before stopping: E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:5:1,   |, 3 | """Backtesting engine for ETF trading strategies.""", 4 |, 5 | import hashlib,   | ^^^^^^^^^^^^^^, 6 | import logging, 7 | import re,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:6:1,   |, 5 | import hashlib, 6 | import logging,   | ^^^^^^^^^^^^^^, 7 | import re, 8 | import sys,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:7:1,   |, 5 | import hashlib, 6 | import logging, 7 | import re,   | ^^^^^^^^^, 8 | import sys, 9 | from pathlib import Path,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:8:1,   |, 6 | import logging, 7 | import re, 8 | import sys,   | ^^^^^^^^^^, 9 | from pathlib import Path,   |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:9:1,    |,  7 | import re,  8 | import sys,  9 | from pathlib import Path,    | ^^^^^^^^^^^^^^^^^^^^^^^^, 10 |, 11 | import numpy as np,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:11:1,    |,  9 | from pathlib import Path, 10 |, 11 | import numpy as np,    | ^^^^^^^^^^^^^^^^^^, 12 | import pandas as pd,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:12:1,    |, 11 | import numpy as np, 12 | import pandas as pd,    | ^^^^^^^^^^^^^^^^^^^, 13 |, 14 | from ETF_screener.database import ETFDatabase,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:14:1,    |, 12 | import pandas as pd, 13 |, 14 | from ETF_screener.database import ETFDatabase,    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^, 15 | from ETF_screener.indicators import (, 16 |     calculate_adx,,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:15:1,    |, 14 |   from ETF_screener.database import ETFDatabase, 15 | / from ETF_screener.indicators import (, 16 | |     calculate_adx,, 17 | |     calculate_ema,, 18 | |     calculate_macd,, 19 | |     calculate_rsi,, 20 | |     calculate_rsi_ema,, 21 | |     calculate_stochastic,, 22 | |     calculate_stoch_rsi,, 23 | |     calculate_supertrend,, 24 | |     calculate_linreg_slope,, 25 | |     calculate_tsi,, 26 | | ),    | |_^, 27 |   from ETF_screener.strategy_manager import CachedStrategyManager,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:27:1,    |, 25 |     calculate_tsi,, 26 | ), 27 | from ETF_screener.strategy_manager import CachedStrategyManager,    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^, 28 |, 29 | logger = logging.getLogger(__name__),    |, , F841 Local variable `price_col` is assigned to but never used,    --> src\ETF_screener\backtester.py:184:13,     |, 182 |             df["Date"] = pd.to_datetime(df.get("Date", df.get("date"))), 183 |             df = df.sort_values("Date").reset_index(drop=True), 184 |             price_col = "Close" if "Close" in df else "close",     |             ^^^^^^^^^, 185 |             kwargs = strategy_kwargs or {},     |, help: Remove assignment to unused variable `price_col`, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:5:1,   |, 3 | """SQLite database interface for ETF data persistence.""", 4 |, 5 | import sqlite3,   | ^^^^^^^^^^^^^^, 6 | from pathlib import Path, 7 | from typing import Optional,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:6:1,   |, 5 | import sqlite3, 6 | from pathlib import Path,   | ^^^^^^^^^^^^^^^^^^^^^^^^, 7 | from typing import Optional,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:7:1,   |, 5 | import sqlite3, 6 | from pathlib import Path, 7 | from typing import Optional,   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^, 8 |, 9 | import pandas as pd,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:9:1,   |, 7 | from typing import Optional, 8 |, 9 | import pandas as pd,   | ^^^^^^^^^^^^^^^^^^^,   |, , F821 Undefined name `logger`,    --> src\ETF_screener\market_data_service.py:356:13,     |, 354 |         promoted = self.delisting_tracker.promote_aged_missing(threshold_days=14), 355 |         if promoted:, 356 |             logger.info("Promoted %d missing tickers to blacklist", len(promoted)),     |             ^^^^^^, 357 |         self._emit_progress(, 358 |             progress_callback,,     |, , E402 Module level import not at top of file,  --> src\ETF_screener\storage.py:5:1,   |, 3 | """Data storage utilities for parquet files.""", 4 |, 5 | from pathlib import Path,   | ^^^^^^^^^^^^^^^^^^^^^^^^, 6 |, 7 | import pandas as pd,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\storage.py:7:1,   |, 5 | from pathlib import Path, 6 |, 7 | import pandas as pd,   | ^^^^^^^^^^^^^^^^^^^,   |, , F841 Local variable `trigger_trace` is assigned to but never used,    --> tests\test_plotter_plotly.py:542:5,     |, 540 |         df, "TEST", strategy_content=strategy_content, 541 |     ), 542 |     trigger_trace = next(,     |     ^^^^^^^^^^^^^, 543 |         t, 544 |         for t in fig.data,     |, help: Remove assignment to unused variable `trigger_trace`, , Found 19 errors., No fixes available (2 hidden fixes can be enabled with the `--unsafe-fixes` option)., black.

## 2026-05-05 20:37:56 +02:00

- -Summary
- Next resume point: Review the latest commit and pick up the next implementation task.

## 2026-05-05 20:37:25 +02:00

- -Summary
- Next resume point: Applied fixes before stopping: E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:4:1,   |, 2 | """Backtesting engine for ETF trading strategies.""", 3 |, 4 | import hashlib,   | ^^^^^^^^^^^^^^, 5 | import logging, 6 | import re,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:5:1,   |, 4 | import hashlib, 5 | import logging,   | ^^^^^^^^^^^^^^, 6 | import re, 7 | import sys,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:6:1,   |, 4 | import hashlib, 5 | import logging, 6 | import re,   | ^^^^^^^^^, 7 | import sys, 8 | from pathlib import Path,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\backtester.py:7:1,   |, 5 | import logging, 6 | import re, 7 | import sys,   | ^^^^^^^^^^, 8 | from pathlib import Path,   |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:8:1,    |,  6 | import re,  7 | import sys,  8 | from pathlib import Path,    | ^^^^^^^^^^^^^^^^^^^^^^^^,  9 |, 10 | import numpy as np,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:10:1,    |,  8 | from pathlib import Path,  9 |, 10 | import numpy as np,    | ^^^^^^^^^^^^^^^^^^, 11 | import pandas as pd,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:11:1,    |, 10 | import numpy as np, 11 | import pandas as pd,    | ^^^^^^^^^^^^^^^^^^^, 12 |, 13 | from ETF_screener.database import ETFDatabase,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:13:1,    |, 11 | import pandas as pd, 12 |, 13 | from ETF_screener.database import ETFDatabase,    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^, 14 | from ETF_screener.indicators import (, 15 |     calculate_adx,,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:14:1,    |, 13 |   from ETF_screener.database import ETFDatabase, 14 | / from ETF_screener.indicators import (, 15 | |     calculate_adx,, 16 | |     calculate_ema,, 17 | |     calculate_macd,, 18 | |     calculate_rsi,, 19 | |     calculate_rsi_ema,, 20 | |     calculate_stochastic,, 21 | |     calculate_stoch_rsi,, 22 | |     calculate_supertrend,, 23 | |     calculate_linreg_slope,, 24 | |     calculate_tsi,, 25 | | ),    | |_^, 26 |   from ETF_screener.strategy_manager import CachedStrategyManager,    |, , E402 Module level import not at top of file,   --> src\ETF_screener\backtester.py:26:1,    |, 24 |     calculate_tsi,, 25 | ), 26 | from ETF_screener.strategy_manager import CachedStrategyManager,    | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^, 27 |, 28 | logger = logging.getLogger(__name__),    |, , F841 Local variable `price_col` is assigned to but never used,    --> src\ETF_screener\backtester.py:178:13,     |, 176 |             df["Date"] = pd.to_datetime(df.get("Date", df.get("date"))), 177 |             df = df.sort_values("Date").reset_index(drop=True), 178 |             price_col = "Close" if "Close" in df else "close",     |             ^^^^^^^^^, 179 |             kwargs = strategy_kwargs or {},     |, help: Remove assignment to unused variable `price_col`, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:4:1,   |, 2 | """SQLite database interface for ETF data persistence.""", 3 |, 4 | import sqlite3,   | ^^^^^^^^^^^^^^, 5 | from pathlib import Path, 6 | from typing import Optional,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:5:1,   |, 4 | import sqlite3, 5 | from pathlib import Path,   | ^^^^^^^^^^^^^^^^^^^^^^^^, 6 | from typing import Optional,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:6:1,   |, 4 | import sqlite3, 5 | from pathlib import Path, 6 | from typing import Optional,   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^, 7 |, 8 | import pandas as pd,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\database.py:8:1,   |, 6 | from typing import Optional, 7 |, 8 | import pandas as pd,   | ^^^^^^^^^^^^^^^^^^^,   |, , F821 Undefined name `logger`,    --> src\ETF_screener\market_data_service.py:322:13,     |, 320 |         promoted = self.delisting_tracker.promote_aged_missing(threshold_days=14), 321 |         if promoted:, 322 |             logger.info("Promoted %d missing tickers to blacklist", len(promoted)),     |             ^^^^^^, 323 |         self._emit_progress(, 324 |             progress_callback,,     |, , E402 Module level import not at top of file,  --> src\ETF_screener\storage.py:4:1,   |, 2 | """Data storage utilities for parquet files.""", 3 |, 4 | from pathlib import Path,   | ^^^^^^^^^^^^^^^^^^^^^^^^, 5 |, 6 | import pandas as pd,   |, , E402 Module level import not at top of file,  --> src\ETF_screener\storage.py:6:1,   |, 4 | from pathlib import Path, 5 |, 6 | import pandas as pd,   | ^^^^^^^^^^^^^^^^^^^,   |, , F841 Local variable `trigger_trace` is assigned to but never used,    --> tests\test_plotter_plotly.py:544:5,     |, 542 |         df, "TEST", strategy_content=strategy_content, 543 |     ), 544 |     trigger_trace = next(,     |     ^^^^^^^^^^^^^, 545 |         t, 546 |         for t in fig.data,     |, help: Remove assignment to unused variable `trigger_trace`, , Found 23 errors (4 fixed, 19 remaining)., No fixes available (2 hidden fixes can be enabled with the `--unsafe-fixes` option)., black.

## 2026-05-05 20:30:39 +02:00

- Updated the end-of-day workflow so it now refreshes `plan.md` and `progress.md` before staging, committing, and pushing.
- Next resume point: Run the end-of-day workflow after the next coding turn so the resume docs stay synchronized with the branch state.

## 2026-05-04 21:54:43 +02:00

- Added a new end-of-day workflow in `scripts/workflow_end_of_day.ps1` plus the root wrapper `workflow_end_of_day.ps1`.
- The workflow runs `run_all_tests.ps1`, applies light auto-fixes with `ruff --fix` and `black` when tests fail, reruns the suite once, and then commits and pushes the current branch if everything passes.
- The commit step intentionally excludes obvious local runtime artifacts such as `etf.db` and `config/delisting_state.json` so the workflow stays focused on source changes.
- Current status: the repo now has a single repeatable maintenance entrypoint for end-of-day testing, cleanup, commit, and push.
- Next resume point: run the workflow on a real branch state, then decide whether it should gain a dry-run mode or additional commit filters for generated artifacts.

## 2026-05-02 22:09:18 +02:00

- Tightened the Plotly ribbon chart gutter by lowering the shared left margin and moving the left-side ribbon labels slightly inward.
- Updated `config/ribbon_settings.json` and the corresponding defaults in `src/ETF_screener/plotter_plotly.py` so the chart uses the more compact left spacing consistently.
- Adjusted the plotter regression test to expect the new compact left margin.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_plotter_plotly.py tests\\test_dashboard_api.py -q`; all 52 tests passed.
- Current status: the screener chart should sit noticeably farther left with less dead space while keeping the ribbon labels readable.
- Next resume point: if you want it even tighter, we can trim the left gutter a bit more or make the ribbon label annotations slightly smaller.

## 2026-05-02 22:06:21 +02:00

- Folded `vulture` into the default `run_all_tests.ps1` path so a plain test run now covers both pytest and dead-code scanning.
- Kept the repo-local `vulture_whitelist.py` in place so deliberate FastAPI route handlers and helper APIs stay out of the dead-code noise.
- Verified `.\run_all_tests.ps1` now passes end-to-end with `118 passed` and a clean vulture run.
- Current status: the default quality suite now checks both tests and dead-code coverage in one command.
- Next resume point: if needed, we can add a small `-NoVulture` escape hatch later, but for now the default behavior matches the preference to keep vulture inside the main runner.

## 2026-05-02 22:04:48 +02:00

- Added `vulture_whitelist.py` to pin the deliberate FastAPI route handlers and public helper entrypoints that vulture cannot infer from static imports alone.
- Fixed `run_all_tests.ps1` to use plain ASCII in its success and failure summaries so the nested Windows PowerShell invocation can parse it cleanly.
- Restored the `lane_width` call path in `src/ETF_screener/plotter_plotly.py` so the chart tests and dashboard chart endpoint work again.
- Verified the exact command `.\run_vulture.ps1 -RunTests -ExtraArgs "--exclude static/assets/js" -OutFile .\logs\vulture_report.log` now completes successfully with the nested test suite passing.
- Current status: the repo-local vulture quality gate is green again, and the noisy framework false positives are covered by the whitelist file instead of failing the scan.
- Next resume point: if we want to make the scan even cleaner, we can trim the whitelist or teach `run_vulture.ps1` to emit a shorter summary when the report is empty.

## 2026-05-02 21:58:19 +02:00

- Ran `vulture` across `src` and `tests`.
- Fixed the real syntax issue it found in `src/ETF_screener/snippets.py` by restoring the missing `get_paths` import and correcting the constructor indentation.
- Renamed a few intentionally unused cache-helper parameters and a test-local trace variable so they stop surfacing as avoidable noise.
- `vulture` still reports many FastAPI route handlers and helper APIs as unused, but those are expected false positives because the framework wires them up dynamically.
- Verified the cleaned files still parse with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\snippets.py src\\ETF_screener\\scripts\\churn_strategies.py src\\ETF_screener\\dashboard\\app_fast.py tests\\test_plotter_plotly.py tests\\test_dashboard_api.py tests\\test_churn_strategies.py`.
- Current status: the dead-code scan is cleaner, and the only remaining `vulture` noise is mostly framework-driven false positives.
- Next resume point: if you want, we can add a repo-local `vulture` ignore list for the deliberate FastAPI and utility surfaces so the scan output is much quieter.

## 2026-05-02 21:54:45 +02:00

- Added request-level caches for both the strategy evaluator and the screener in `src/ETF_screener/scripts/churn_strategies.py` and `src/ETF_screener/dashboard/app_fast.py`.
- Cache keys now include the strategy text, source scope, selected list/exchange filters, latest market date, and the selected ticker universe, so identical consecutive GUI runs can hit the fast path.
- Kept the existing per-ticker and per-strategy caches in place; this new layer sits above them so the whole result payload can be reused instead of just the individual ticker work.
- Added regression tests proving the evaluator and screener only do the expensive backtest work once for identical repeated requests.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_churn_strategies.py tests\\test_dashboard_api.py -q`; all 30 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\scripts\\churn_strategies.py src\\ETF_screener\\dashboard\\app_fast.py tests\\test_churn_strategies.py tests\\test_dashboard_api.py`.
- Current status: identical consecutive screen/backtest runs should now feel noticeably snappier instead of taking the same time again.
- Next resume point: if you want more speed, the next target would be reducing the first-run cost by precomputing the busiest strategy results in the background.

## 2026-05-02 21:47:51 +02:00

- Fixed the Plotly row calculation bug in `src/ETF_screener/plotter_plotly.py` where a stale `aggregated_row = 3 + num_ribbons` line was overwriting the correct bottom-row placement.
- The aggregated buy/sell lane now sits on its own row below the last DSL ribbon, so `Trigger` and `Aggregated` no longer stack on the same vertical band.
- Kept the strategy-referenced TA curve panels from the earlier patch, so the chart still shows the actual indicator curves the DSL uses.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_plotter_plotly.py tests\\test_dashboard_api.py -q`; all 51 tests passed.
- Verified the rendered trace axis mapping in a quick local sample: `Context` on `y4`, `Trigger` on `y5`, and `Aggregated` on `y6`.
- Current status: the chart layout is now correctly separated and the bottom summary lane is no longer colliding with the last ribbon.
- Next resume point: if you want, we can still make the lane labels visually tighter or add a separator band between ribbon groups.

## 2026-05-02 21:33:23 +02:00

- Expanded the Plotly chart path in `src/ETF_screener/plotter_plotly.py` so strategy-referenced TA curves are no longer limited to just EMA and Supertrend overlays.
- Added dedicated oscillator and momentum panels for referenced indicators such as RSI, MACD, Stochastic, TSI, ADX, slopes, and the volume EMA helper when those tokens appear in the DSL and the DataFrame has the columns.
- Kept Supertrend overlay gating in place, but now it also recognizes plain `st_is_green` / `st_is_red` style references as a reason to draw the supertrend curve.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\plotter_plotly.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_plotter_plotly.py tests\\test_dashboard_api.py -q`; all 51 tests passed.
- Current status: chart drill-down should now show the strategy's actual TA curves much more faithfully instead of only the old overlay subset.
- Next resume point: if you want, we can tune the panel grouping or colors so dense strategies stay readable with fewer overlapping lines.

## 2026-05-02 19:24:10 +02:00

- Added copy buttons for the visible `strategy-select` dropdown in the top bar and the saved-list selector inside the list builder modal.
- Added a reusable `copySelectText()` helper in `src/ETF_screener/dashboard/static/js/dashboard.js` so the selected option label can be copied to the clipboard.
- Kept the browser-safe fallback path for clipboard access, with a toast if copying fails.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_market_data_service.py tests\\test_churn_strategies.py -q`; all 37 tests passed.
- Verified syntax with `node --check src\\ETF_screener\\dashboard\\static\\js\\dashboard.js`.
- Current status: the main dropdowns are now copy-friendly without changing the rest of the dashboard layout.
- Next resume point: if you want, we can apply the same copy affordance to the hidden ticker dropdown or other picker-style controls.

## 2026-05-02 19:16:11 +02:00

- Read the dashboard logs and found the repeat Sweden failures were the same nine Yahoo-missing symbols: `BONAV-A.ST`, `CAT-A.ST`, `HAKI-A.ST`, `MANG.ST`, `MSON-A.ST`, `MTG-A.ST`, `SVOL-A.ST`, `VPLAY-A.ST`, and `WTW-A.ST`.
- Added those symbols to `config/blacklist.json` so they are excluded from the dashboard universe, scan/backtest tickers, and market refresh tracking.
- Updated `src/ETF_screener/dashboard/app_fast.py` and `src/ETF_screener/scripts/churn_strategies.py` to filter out blacklisted tickers before they reach the UI or the screen engine.
- Fixed the browser screen loop in `src/ETF_screener/dashboard/static/js/dashboard.js` so `progInterval` is cleared safely without throwing a follow-up JavaScript error.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_market_data_service.py tests\\test_churn_strategies.py -q`; all 37 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py src\\ETF_screener\\market_data_service.py src\\ETF_screener\\yfinance_fetcher.py`.
- Current status: the Swedish scan should stop surfacing those repeated failed-load entries from Yahoo, and the browser progress loop should stay clean.
- Next resume point: if any Sweden symbols still fail, inspect the new logs for the exact remaining tickers and blacklist or remap only those.

## 2026-05-02 19:08:11 +02:00

- Switched `src/ETF_screener/market_data_service.py` to a sequential Sweden refresh path, because the full 406-name Stockholm burst was still producing too many load failures even after lowering concurrency.
- Kept the retry/backoff layer in `src/ETF_screener/yfinance_fetcher.py` so individual symbols still get a couple of extra chances before being marked failed.
- Left the source-aware market status and refresh plumbing in place so Sweden, Xetra, and saved lists still resolve the correct universe file.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_market_data_service.py -q`; all 34 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\market_data_service.py src\\ETF_screener\\yfinance_fetcher.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Current status: Sweden refreshes should be much less likely to generate a wall of failures now that they run one ticker at a time.
- Next resume point: if failures remain, inspect the specific tickers and decide whether a small blacklist or a symbol remap is needed.

## 2026-05-02 19:05:12 +02:00

- Added retry/backoff to `src/ETF_screener/yfinance_fetcher.py` so a temporary Yahoo failure has a second and third chance before a ticker is marked failed.
- Lowered refresh concurrency for `config/sweden.json` inside `src/ETF_screener/market_data_service.py`, because the full 406-name Stockholm burst was likely tripping Yahoo rate limits.
- Kept custom lists gentle too when they are small enough to refresh serially without needing the full worker pool.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_market_data_service.py -q`; all 34 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\yfinance_fetcher.py src\\ETF_screener\\market_data_service.py src\\ETF_screener\\dashboard\\app_fast.py`.
- Current status: Sweden refreshes should be much less likely to blow up into a wall of 406-style load failures.
- Next resume point: if the problem still appears, we should inspect the exact failing symbols and decide whether to blacklist or special-case them.

## 2026-05-02 18:57:51 +02:00

- Made market freshness source-aware in `src/ETF_screener/dashboard/app_fast.py` so the selected scan source now resolves its own metadata file instead of always falling back to Xetra.
- Extended `src/ETF_screener/market_data_service.py` to understand the custom multi-list JSON shape, including active-list and all-lists modes.
- Updated `src/ETF_screener/dashboard/static/js/dashboard.js` to send the current scan source to `/api/market-status` and `/api/market-data/refresh`, and to say `Sweden`, `saved list`, or `all saved lists` in the refresh copy.
- Routed the manual refresh button directly to the selected source instead of doing an extra freshness precheck first.
- Kept `screen()` and `backtest_view()` tied to the active source when they request a GUI market top-up.
- Added regression coverage for the new source-aware refresh plumbing and kept the market-data tests aligned with the current business-day behavior.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_market_data_service.py -q`; all 34 tests passed.
- Verified syntax with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\market_data_service.py`.
- Current status: Sweden and custom-list refreshes now report the right universe size instead of the default Xetra count.
- Next resume point: decide whether the shortlist tab should also become source-aware, or leave it as the general ETF snapshot for now.

## 2026-05-02 18:57:06 +02:00

- Fixed the scan-source wiring so `Sweden` no longer falls back to the old Xetra exchange path.
- Added `All Lists` to the source chooser and made the scan universe resolve directly from the selected source instead of a separate exchange dropdown.
- Upgraded the saved-list store to a small collection model with an active list, so `My List` now means the selected list and the modal can switch between saved lists.
- Added a saved-list selector inside the list builder modal, plus a multi-list save/load round-trip through `/api/custom-ticker-list`.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 31 tests passed.
- Current status: the source chooser and list builder now match the requested model much more closely.
- Next resume point: if you want, we can polish the list modal further by adding delete/duplicate buttons for saved lists.

## 2026-05-02 18:46:07 +02:00

- Swapped the source chooser from a dropdown to a compact button group so the scanner now reads `Xetra`, `Sweden`, or `My List` without adding another dropdown to the top bar.
- Kept the list builder as a separate `Edit My List...` action, so the user still has one place to build the list and one place to choose the scan source.
- The active source button now carries the visual emphasis, while the list builder button keeps showing the current saved list name and ticker count.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 31 tests passed.
- Current status: the top bar should feel noticeably less crowded now that the scan source is a button group rather than another dropdown.
- Next resume point: if you want, we can later make the active source button even more minimal by using icons or shorter labels.

## 2026-05-02 18:41:16 +02:00

- Simplified the top bar again so the scanner uses one source chooser with `Xetra`, `Sweden`, and `My List` instead of separate exchange and list scan controls.
- Kept the list builder as a separate `Edit My List...` button, and made that button show the current saved list name and count.
- The scan source now drives both the backend universe selection and the hidden ticker drill-down universe, so the UI stays consistent without an extra exchange dropdown.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 31 tests passed.
- Current status: the scanning controls should feel simpler and more direct now that the source choice is a single control.
- Next resume point: if you want, we can make the source chooser a segmented control instead of a dropdown next.

## 2026-05-02 18:32:55 +02:00

- Made the `Scan Scope` control visually prominent by wrapping it in a dedicated top-bar panel with a stronger accent, label, and helper text.
- The selector now changes its accent styling based on whether it is set to `Entire Exchange` or `Chosen List`, so the current mode is easier to read at a glance.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 28 tests passed.
- Current status: the scan-scope switch should now be much harder to miss in the toolbar.
- Next resume point: if you want, we can make the scan-scope control even bolder by turning it into a segmented toggle instead of a dropdown.

## 2026-05-02 18:31:19 +02:00

- Added a sticky `Scan Scope` selector to the dashboard top bar so the screener can work either against the whole exchange or against the saved custom list.
- Wired the new scope through `/api/screen` and `/api/backtest`, and updated the shared ticker filter helper so `list` mode uses only the chosen list while `exchange` mode uses the selected exchange bucket.
- The top-bar exchange selector now gets disabled when the scan scope is set to `Chosen List`, which makes the active universe choice clearer in the UI.
- If the user chooses list scope with no saved tickers yet, the dashboard opens the list builder instead of starting a meaningless empty scan.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 31 tests passed.
- Current status: the scanner now has an explicit either/or universe selector, which should make the top bar much less ambiguous.
- Next resume point: if you want, the next polish pass could make the scan-scope label more visual or add a tiny helper text under it.

## 2026-05-02 18:17:14 +02:00

- Added a `List Name` field to the custom list modal so the single saved list can now be named directly in the UI.
- The saved custom-list JSON now stores both `name` and `tickers`, with `config/custom_ticker_list.json` bumped to `custom_ticker_list_v2`.
- The sticky top-bar selector now uses the saved list name when it is available, so the visible label matches what you named it.
- The backend save/load endpoints now round-trip the list name as part of the payload, while still accepting the older name-less format.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\plotter.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 26 tests passed.
- Current status: the list workflow now supports both a custom ticker set and a human-readable name without adding a full multi-list manager.
- Next resume point: if you want, we can make the list name update live in the sticky selector as you type, or keep it as a save-time change only.

## 2026-05-02 18:13:48 +02:00

- Replaced the small 64-name Swedish seed with a broader `config/sweden.json` and `config/sweden.csv` generated from the official Nasdaq Nordic Stockholm shares feed.
- The new Sweden file now contains 406 symbols, keyed by yfinance-style tickers like `ABB.ST` and `VOLV-B.ST`, so the runtime lookup stays compatible with yfinance.
- The dashboard universe merge and plotter lookup already consume `sweden.json`, so the Swedish selector and modal should now surface a much fuller market list.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\plotter.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 26 tests passed.
- Current status: the Sweden selector should now feel like a real market universe instead of a tiny starter list.
- Next resume point: if you want, we can still curate that 406-name feed down later, or add another quick filter for large caps versus smaller names.

## 2026-05-02 18:04:32 +02:00

- Added a dedicated Swedish universe seed in `config/sweden.csv` and `config/sweden.json`, built from `reference/swedish_equities_option_A.csv`.
- Wired the dashboard metadata loader in `src/ETF_screener/dashboard/app_fast.py` to merge `sweden.json` alongside `xetra.json` and the legacy ETF metadata file.
- The ticker universe endpoint now keeps Swedish entries in the modal universe even when they are not present in the local price database, and classifies them as `sweden` via the `STO` market flag.
- Updated `src/ETF_screener/plotter.py` so Swedish tickers can resolve friendly names from `config/sweden.json` too.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\plotter.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 26 tests passed.
- Current status: the Swedish picker now has a real curated source file instead of relying on suffix heuristics alone.
- Next resume point: if you want the list to cover more than the current 64 Swedish names, we can extend `reference/swedish_equities_option_A.csv` or replace it with a broader market feed.

## 2026-05-02 17:30:35 +02:00

- Tweaked the builder to trust backend exchange metadata when it exists, which makes the Swedish filter more accurate for tickers that do not obviously reveal their market from the symbol alone.
- The modal still searches company names, issuers, regions, and asset class, but the backend-provided exchange bucket now drives the filter when available.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 29 tests passed.
- Current status: the list builder should feel smarter and more reliable for Swedish tickers specifically.
- Next resume point: if you want, we can add named saved lists or a tiny issuer filter row inside the modal next.

## 2026-05-02 17:29:44 +02:00

- Expanded the list builder so the modal search now matches ticker, company name, issuer, asset class, and region instead of only terse ticker text.
- Added a cached `/api/ticker-universe` endpoint that returns richer metadata for the modal, and rewired the frontend to load that universe once at startup.
- The modal now shows the company name prominently, with ticker and issuer/region metadata underneath, which should be much more usable for Swedish exchange names.
- Kept the saved list in `config/custom_ticker_list.json` and left the exchange filter intact, so the builder is still sticky but far easier to browse.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 29 tests passed.
- Current status: the list builder is now both checkbox-based and metadata-aware, which should make the Swedish side much easier to manage.
- Next resume point: if you want, the next polish step could be adding even richer filters like issuer chips or a saved “Sweden only” view in the modal.

## 2026-05-02 17:16:31 +02:00

- Replaced the freeform list prompt with a checkbox-based list builder modal that can search and filter tickers by exchange.
- Added a real JSON-backed store at `config/custom_ticker_list.json`, with new `/api/custom-ticker-list` GET and POST endpoints in the dashboard backend.
- The modal now loads the saved list from the server, lets you tick visible names into a draft, and saves the final selection back to config as the source of truth.
- Kept localStorage only as a fallback cache, while the top bar still shows the sticky `My List` selector and `Edit My List...` entry.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 28 tests passed.
- Current status: the list workflow is now much closer to a real builder and should feel snappier than the old prompt flow.
- Next resume point: if you want, we can add named saved lists or a true multi-list manager after this single-list flow settles in.

## 2026-05-02 17:07:52 +02:00

- Reworked the list workflow so `Edit My List...` now opens a lightweight modal editor instead of a blocking browser prompt.
- Kept `My List` as the sticky default top-bar choice, and made the modal show a live count plus a short preview of the current custom list.
- The list selector still filters Screen and Backtest requests through the same shared universe params, but the editing path is now much less disruptive.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 24 tests passed.
- Current status: the list feature should feel snappier because editing no longer interrupts the page with a modal browser prompt.
- Next resume point: if you want even more speed, we can add a true saved-list picker or a one-click clear action next.

## 2026-05-02 15:16:22 +02:00

- Removed the `All Tickers` option from the top-bar list selector so the chooser now stays minimal.
- Kept `My List` as the default visible choice and `Edit My List...` as the only explicit list-management action.
- The list selector still remains sticky, and a missing custom list will simply prompt when the user tries to define one.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 24 tests passed.
- Current status: the top bar is now exchange plus a lean list chooser, without the redundant all-tickers escape hatch.
- Next resume point: if you want, we can make the list selector even more direct by turning `Edit My List...` into a small button beside `My List`.

## 2026-05-02 15:13:26 +02:00

- Changed dashboard startup to stay passive on refresh instead of auto-launching a scan, backtest, or market-top-up before the user clicks anything.
- Kept the sticky exchange and custom list controls intact, but moved the startup path to a simple market-status read so the page waits for explicit input.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_js.py tests\\test_dashboard_api.py -q`; all 24 tests passed.
- Current status: browser refresh should no longer kick off heavy scripts on its own.
- Next resume point: if you still want any auto-status activity on load, we can make it read-only instead of starting work.

## 2026-05-02 15:02:30 +02:00

- Reworked the visible top bar so it now shows a sticky `Exchange` selector plus a sticky user-defined `List` selector instead of the old visible ticker picker.
- Kept the ticker dropdown in the DOM as a hidden chart-drilldown control so the chart path still works, but removed it from the main top bar.
- Wired the selected exchange and custom list into both `/api/screen` and `/api/backtest`, so the new controls actually filter the run universe.
- Cleaned up the shared ticker-list helper in `src/ETF_screener/scripts/churn_strategies.py` and removed a redundant no-op filter call.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 27 tests passed.
- Current status: the top bar now matches the requested exchange-plus-list selector model, and the selection should stay sticky across rerenders.
- Next resume point: if the Swedish bucket still feels too thin, wire in a proper Sweden listings source instead of relying only on ticker suffixes.

## 2026-05-02 14:53:27 +02:00

- Added a sticky top-bar exchange selector in `src/ETF_screener/dashboard/templates/index.html` with `All Exchanges`, `Xetra / Germany`, and `Swedish Exchange`.
- Added frontend persistence in `src/ETF_screener/dashboard/static/js/dashboard.js` so both the exchange filter and the ticker selector remember their values across chart loads and screener rerenders.
- The ticker dropdown now re-renders from a cached universe instead of hard-resetting, so the chosen exchange stays put instead of jumping back.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 24 dashboard tests passed.
- Current status: the top bar now has a persistent exchange control, and the ticker selector should no longer snap back on you.
- Next resume point: if you want the Swedish bucket to show a fuller real universe, we can wire in a proper Sweden listings source next.

## 2026-05-02 14:41:35 +02:00

- Fixed the frontend job routing so the Screener listens to `screen` progress and the Backtester listens to `backtest` progress, instead of silently swapping the two.
- This was the missing piece behind the GUI looking blank even though the terminal logs were moving.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 24 dashboard tests passed.
- Current status: the next browser load should attach the global bar to the correct backend job.
- Next resume point: if it still looks empty after a fresh reload, the next check is the browser console or the exact action being run.

## 2026-05-02 14:41:35 +02:00

- Fixed the GUI progress bar disappearing after a market-data top-up by reattaching the poller and re-showing the panel once Screen or Backtest resumes.
- This matters because the nested market-refresh path was clearing the live poller before the main job could paint its own progress state.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 24 dashboard tests passed.
- Current status: the GUI should now stay visible through the refresh transition and continue moving during the main job.
- Next resume point: if you still see a blank area, we should inspect the browser console for a JS runtime error or verify the route the page is calling.

## 2026-05-02 14:35:10 +02:00

- Moved the heavy `screen()` and `backtest_view()` compute calls off the async event loop in `src/ETF_screener/dashboard/app_fast.py` so the browser can keep polling `/api/job-progress` while the terminal log progresses.
- This fixed the "terminal moves but GUI bar is stuck" problem by letting the frontend fetch progress updates concurrently with the long-running screen/backtest request.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 24 dashboard tests passed.
- Current status: the GUI should now see live progress movement instead of only the final result.
- Next resume point: if the market-refresh route ever needs the same live-poll behavior, we can move more of that path off the event loop too.

## 2026-05-02 14:28:45 +02:00

- Added a real backend job-progress snapshot at `/api/job-progress` in `src/ETF_screener/dashboard/app_fast.py`.
- Wired `screen()`, `backtest_view()`, and market refresh to publish progress state from the server, and made the frontend poll that snapshot for the global bar.
- Kept the context bar local to the active action while the global bar now reflects actual server-side job state instead of a pure UI estimate.
- Updated `src/ETF_screener/scripts/churn_strategies.py` so `evaluate_strategies()` can forward progress callbacks into the shared backtester path.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py tests\\test_churn_strategies.py -q`; all 27 tests passed.
- Current status: the dashboard now has a real progress source for the global bar, not just fake animation.
- Next resume point: decide whether any other long-running dashboard jobs should publish into `/api/job-progress`, or whether the current trio is enough for now.

## 2026-05-02 14:15:27 +02:00

- Reworked the top navigation progress area into two stacked bars in `src/ETF_screener/dashboard/templates/index.html`: a context bar for the active task and a global bar for broader dashboard state.
- Added shared progress helpers in `src/ETF_screener/dashboard/static/js/dashboard.js` so Screener and Backtester flows can update the two bars consistently.
- Kept the old scan area compact, but made the labels more explicit: `Screen` during screener runs, `Backtest` during backtests, and `Global` for the broader dashboard state.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_dashboard_js.py -q`; all 24 tests passed.
- Current status: the GUI progress indicator is now more informative without adding a larger status system.
- Next resume point: if you want even more clarity, we can feed the global bar from other long-running actions like market refresh or make it reflect backend phase changes more explicitly.

## 2026-05-02 13:56:09 +02:00

- Optimized `src/ETF_screener/backtester.py` in three layers: scripted backtests now use a process-safe worker path, the per-ticker simulation loop now operates on pre-extracted arrays, and completed scripted runs are cached by ticker, strategy hash, day count, latest ticker date, and a local cache version.
- Repeat scripted backtests can now skip both the strategy evaluation phase and the simulation loop when the matching parquet and result cache files already exist.
- The parallel backtest path still uses `ProcessPoolExecutor` for the common scripted-strategy case, while falling back to threads for generic strategies.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\backtester.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_backtester.py tests\\test_dashboard_api.py -q`; all 31 tests passed.
- Current status: the heavy backtest path is faster and more process-friendly without changing the dashboard behavior.
- Next resume point: benchmark the user-facing screen/backtest runtime, then decide whether more aggressive vectorization or caching is still worth it.

## 2026-05-02 09:43:20 +02:00

- Added a cached dashboard ticker list and a cached screen-universe helper in `src/ETF_screener/dashboard/app_fast.py`.
- Both caches are keyed by the latest market date, so repeated index-page and `/api/screen` requests can reuse the same ticker lists until new market data arrives.
- Updated `plan.md` to treat repeated screen/backtest reads as a performance target and to note the remaining heavy path.
- Current status: the dashboard should stop rescanning `etf_data` for the home page and screen universe on every request.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py -q`; all 21 tests passed.
- Next resume point: decide whether `/api/backtest` deserves the same latest-date cache treatment if it still repeats expensive universe scans.

## 2026-05-02 13:44:47 +02:00

- Added a cached strategy ticker-universe helper in `src/ETF_screener/scripts/churn_strategies.py`.
- `evaluate_strategies()` and `churn_db()` now reuse the latest-market-date ticker cache, so they stop re-running the same full `etf_data` ticker scan on every call.
- Verified with `.venv\\Scripts\\python.exe -m py_compile src\\ETF_screener\\dashboard\\app_fast.py src\\ETF_screener\\scripts\\churn_strategies.py`.
- Verified with `.venv\\Scripts\\python.exe -m pytest tests\\test_dashboard_api.py tests\\test_churn_strategies.py -q`; all 24 tests passed.
- Current status: the main request-path scans are now cached consistently across the dashboard and strategy helpers.
- Next resume point: decide whether to attack the actual backtest compute loop next, or to prototype GPU/WebGL only in the browser-rendering layer where it can realistically help.

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
