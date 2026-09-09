# Dashboard JavaScript guide

Start with the file for the feature you want to change. `../dashboard.js` only
starts the dashboard and exposes the handlers used by the HTML template.
There is no JavaScript build step: edit a file and reload the dashboard.

| What you want to change | File |
| --- | --- |
| Tabs and the persistent workspace | `shell.js` |
| Exchanges, ticker selection, saved lists and the list editor | `universe.js` |
| Filter defaults and shared runtime values | `state.js` |
| Reading, validating and applying screen filters | `screen-filters.js` |
| Timeline rules, ordering and age controls | `timeline.js` |
| Filter input event listeners | `screen-bindings.js` |
| DSLX loading/saving, presets and strategy editors | `strategies.js` |
| Starting/cancelling scans and validating scan readiness | `screener.js` |
| Match cards, cached result filtering and exports | `screen-results.js` |
| Price charts, overlays, chart settings and toolbar | `charts.js` |
| Market data status and refresh requests | `market-data.js` |
| Progress bars and streamed job events | `progress.js` |
| Playbook table and requests | `playbook.js` |
| Backtest selection and evaluation requests | `backtest-run.js` |
| Backtest row data, sorting, summary cards and table | `backtest-results.js` |
| Backtest scatter and radar charts | `backtest-charts.js` |
| Backtest race state, playback and incoming race events | `backtest-race.js` |
| Shared formatting, escaping and saved preferences | `utils.js` |
| Console capture and log delivery | `logging.js` |

## How the files work together

`dashboard/assets.py` lists the scripts in their loading order. The page loads
`state.js` first, then the feature files, then `dashboard.js` last. Each script
has its own cache version, so changing a feature updates its URL on the next
page load. The Node and browser tests use this same list.

These are ordinary browser scripts sharing the existing functions and variables,
not isolated ES modules. For example, `screener.js` can call `loadChart()` from
`charts.js`, and both can read shared values from `state.js`. Moving functions
into separate files makes navigation easier, but does not remove that coupling.

- Put feature behavior in its corresponding file, rather than in the entrypoint.
- Define functions in feature files; start requests and register startup listeners
  from `dashboard.js`, after every feature has loaded.
- Keep shared mutable values in `state.js`. Avoid duplicate top-level names.
- For a new HTML event handler, add its function to the `Object.assign(window, ...)`
  list in `dashboard.js` so the template's intent stays explicit.
- Register any new file in `DASHBOARD_SCRIPTS` in `dashboard/assets.py`.
- Keep the scripts ordered; do not add `async` or change one file to `type="module"`
  without also changing how its dependencies and HTML handlers are provided.

For a later refactor, isolate one feature's state and public functions at a time.
Splitting the Python API by feature is a separate follow-up.

## Checking a change

From the repository root in PowerShell:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_dashboard_js.py tests/test_dashboard_api.py tests/test_dashboard_playwright.py --timeout=120
```

The JavaScript tests exercise controls with Node. The Playwright tests exercise
the scripts in Chromium, including the server-rendered dashboard page.
