# Kingston storage setup

Configured on 2026-09-06 for the Kingston XS1000 at **F:**.

| Content | Location |
| --- | --- |
| Canonical price history, one Parquet file per ticker | `F:/ETF-screener-data/parquet` |
| Regenerable backtest, indicator and screen caches | `F:/ETF-screener-data/cache` |
| Verified database snapshot from before the backfill | `F:/ETF-screener-data/backups/etfs-before-history.db` |
| Working SQLite database | `data/etf_db/etfs.db` in the repository |
| Code, strategies, lists and exported reports | Their existing repository locations |

The small working database stays on the internal drive. Large Parquet histories
and derived caches now use the USB. The raw price history is shared by strategies;
temporary strategy-specific results live only in the bounded cache directory.

## Configuration

`config/paths.json` retains portable defaults. The ignored, machine-specific
`config/paths.local.json` overrides storage paths and enables this setup:

```json
{
  "external_storage_root": "F:/ETF-screener-data",
  "data": {
    "parquet": "F:/ETF-screener-data/parquet",
    "cache": "F:/ETF-screener-data/cache"
  },
  "cache_policy": {
    "max_bytes": 1073741824,
    "max_files": 5000,
    "max_age_days": 14
  },
  "history_retention_days": 1830,
  "nasdaq_focus_file": "config/nasdaq_focus.json"
}
```

If Windows assigns another drive letter, update the three F: paths in that file
and restart the app. Keep the SSD connected while using the app. Configuration
access and default price-store operations check the `.etf-screener-storage`
marker: a missing drive produces a clear connection error instead of silently
creating an empty replacement store. Explicit custom storage paths remain usable
for tests and maintenance.

## Cache behavior

Backtest frames and result metadata, indicator calculations, screen requests,
screen indicator history, and strategy-evaluation results share the configured
cache root. A completed cache write triggers oldest-first eviction to enforce a
1 GiB logical-byte budget, 5,000-file limit, and 14-day lifetime. Reads treat
expired files as misses. Files currently held open may need a later eviction
attempt; filesystem allocation overhead is additional to the logical-byte budget.

Canonical `*_data.parquet` files, database files, strategies and exported reports
are outside that policy. Price writes use a temporary file followed by replacement
so a failed write does not overwrite the last complete history file.

## Focused Nasdaq history

`config/nasdaq_focus.json` records 400 stocks selected from the official Nasdaq
common-share directory using the highest local 20-session average dollar
turnover as of 2026-09-04. Selection also required a $3 average price, 150,000
average daily shares, and 20 active sessions. ETFs, warrants and similar listings
were excluded by the existing official-directory importer.

The Nasdaq source uses this focus in its shared refresh and screening filters.
The dashboard ticker catalogue reflects the same focus. Explicit custom-list
overrides remain available; the full `config/nasdaq.json` catalogue is preserved.
Normal vitality and blacklist checks still apply. Currently 399 pass those
checks; BSP has only 47 sessions against the existing 50-session minimum.

The initial download obtained **469,413 daily rows for all 400 symbols**:
349 have approximately five years (1,256 sessions); 51 have shorter available
histories. The downloaded Parquet files total approximately **72 MB**. Shorter
histories are recorded rather than fabricated or repeatedly requested.

The refresh service, startup refresh, and nightly refresh honor the configured
1,830-calendar-day retention. Ordinary refreshes continue adding only the missing
tail. The backfill is resumable:

```powershell
.venv/Scripts/python.exe scripts/prepare_nasdaq_history.py
```

Completion and coverage are saved in `parquet/nasdaq-history-status.json` on the
SSD. This historical membership is today's selected list, not a reconstructed
historical Nasdaq universe; performance studies must account for that limitation.

## Migration record

- Copied and SHA-256 verified all **9,952** original canonical price files.
- Created a consistent SQLite backup and checked its integrity.
- Activated USB paths, then verified both copies again before deleting originals.
- Removed obsolete derived caches from the old local directories. The old
  `data/parquet` is empty; a few small non-cache records in `data/cache` remain.
- Local free space increased from approximately **19 GB to 51 GB** during the work.
- `data/storage_migration.json` contains the original file checksums and sizes.

The cleanup command is deliberately limited to known legacy cache names and
directories. Its default is an inspection; applying it requires `-Apply`:

```powershell
./scripts/clean_legacy_caches.ps1
```

Validation included missing-drive behavior, failed price writes preserving old
data, cache limits/expiry, Nasdaq focus precedence, market refresh, screening,
backtesting, query services, Node controls and Chromium interactions:
**101 passed, 3 existing skips**. Eight focused follow-up checks also passed,
including the final Nasdaq metadata correction. Live configured checks confirmed
400 Nasdaq picker entries, 399 eligible query entries, and database integrity.

## Dashboard history downloads

Use the History selector beside Refresh Universe: Latest prices keeps the normal
incremental refresh; 1, 3, 5 or 10 years downloads the available daily history for
the selected universe, including symbols already current. Download History merges
prices into Kingston's canonical Parquet files without discarding older saved
history. Recently listed symbols may return a shorter period. Both progress bars
track the refresh, with completed ticker counts and failures during downloading.
The working database still follows its normal retention policy on later refreshes;
the longer canonical Parquet history remains on Kingston.
