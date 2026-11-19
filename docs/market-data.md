# Market-data refresh

Tasks 1-4 share ten daily-price snapshots. `market_data.py` defines their symbols,
display labels, and canonical filenames. Display labels never determine paths.
`data/csv/manifest.json` records each file's hash, date coverage, price adjustment,
currency, volume unit, and latest provider. The manifest's `as_of` is the requested
refresh date in Asia/Shanghai; each instrument's `end` is its last available bar.
Weekday scheduling does not imply that either exchange traded that day.

## Architecture

```text
Tencent / AKShare / optional Tushare
    -> provider-specific field adapter
    -> OHLCV validation and history reconciliation
    -> temporary snapshot with canonical filenames
    -> Task 1 page, Task 2 page, Task 3 JSON and page, Task 4 page
    -> row-by-row comparison against CSVs and file-hash validation
    -> local file replacement
```

`update_all_data.py` handles fetching and bounded retries. `market_data.py` owns
the schema and history rules. `refresh_pipeline.py` builds in a temporary
directory and publishes the complete stock-data bundle. If a provider, builder,
or consistency check fails, the working snapshot is unchanged. If file
replacement fails, the publisher restores the previous bytes. Replacements are
atomic per file; the directory is not an atomic filesystem transaction. GitHub
publication is one commit, after stock-data and Task 7 validation both pass.

Tasks 1, 2, and 4 preserve their existing page layout and refresh only embedded
data. Task 3 uses its maintained page builder. Plotting scripts read
the committed snapshots; they do not fetch prices or create alternative stock
files. The older Task 1 and Task 2 update commands forward to the unified CLI.

## Provider contracts

- Tencent is first, AKShare is the fallback, and `--prefer-tushare` opts into a
  configured Tushare account. Retries are bounded to three attempts per provider.
  Authentication or permission errors disable Tushare for that market for the run.
  An explicit rate-limit response stops the whole run immediately; it is not
  retried. Missing response fields or adjustment series advance to the next
  provider without repeating an incompatible request.
- Prices use forward adjustment (`qfq`). A Tencent response containing only
  unadjusted `day` bars is rejected. AKShare uses `stock_zh_a_hist_em` and
  `stock_hk_hist_em`; Chinese response keys remain unchanged inside the adapter.
- OHLC prices and volume must be finite; prices must be positive and volume
  nonnegative. Dates must be unique daily observations, no later than `as_of`.
  High/low bounds and the returned symbol are checked before publication.
- A-share volume is in 100-share lots; Hong Kong volume is in shares. Amounts
  are in CNY or HKD. Tushare A-share amounts are converted from thousands of CNY.
  Tushare HK OHLC prices are multiplied by the returned `adj_factor`, as specified
  in its [HK adjusted-price contract](https://tushare.pro/document/2?doc_id=339).
  Missing optional fields remain empty, not zero. Dashboards preserve the same
  underlying OHLCV values instead of rounding prices during data export.

Older snapshots without recorded provenance retain `not recorded` as their
adjustment metadata. The whole-file `qfq` label requires either a previously
verified history or an adjusted-provider response covering every retained date.
An unverified older prefix keeps the file's adjustment status unspecified.
Filename migration alone cannot verify a price-adjustment basis.

The [AKShare quote documentation](https://akshare.akfamily.xyz/data/stock/stock_quote.html)
defines these field names and units. The tested refresh release is AKShare
1.20.65, which requires Python 3.11.5 or newer; this project uses Python 3.12.
Provider imports and call signatures are checked offline with
`tools/check_refresh_dependencies.py`. Live availability still depends on the
provider's service and network.

## Historical prices and adjustment changes

Recent responses are joined to existing history by date. If overlapping OHLC
prices agree, the pipeline retains the earlier observations and appends new
ones. It recomputes changes and amplitudes from the resulting price sequence.
A shorter rolling response therefore does not silently erase old history.

Forward-adjusted historical prices can change after corporate actions. When
overlapping prices differ, replacement is allowed only if the new response
covers every existing date. Partial rebases and disjoint date ranges fail with
an error. A full-history fetch is then needed; mixing old and newly adjusted
prices would create artificial returns. Switching providers is subject to the
same continuity check. If a provider's response cannot be reconciled, the updater
tries the next provider before failing the run.

## Run and verify

Use the refresh environment for live providers and stock-page builds:

```bash
python3.12 -m venv .venv-refresh
source .venv-refresh/bin/activate
python -m pip install -r requirements-refresh.txt
python -m pip check
python tools/check_refresh_dependencies.py

# Live refresh; optional TUSHARE_TOKEN is read from the environment.
python update_all_data.py

# Offline rebuild from the current CSVs.
python update_all_data.py --rebuild-only
python tools/validate_market_snapshot.py
python -m unittest discover -s tests -v
```

`--force` bypasses the weekday/current-date scheduling hint. `--as-of YYYY-MM-DD`
sets the snapshot date explicitly. `--check` returns 0 when an update is needed
and 1 otherwise. Invalid inputs fail with an error rather than being reported
as current.

The Python 3.10 research environment in `requirements.txt` remains the supported
path for saved-model reproduction and `tools/run_all_validations.py`. The refresh
environment does not load or retrain those models. Research reports are fixed
analyses; rebuilding rolling price pages does not revise their published figures.

## Migrate the previous updater's filenames

If both a canonical filename and its former display-name alias exist, review and
merge them explicitly:

```bash
python update_all_data.py --rebuild-only --migrate-legacy
```

The same continuity rules apply. Before removing aliases, the publisher backs up
the replaced bundle and original alias files under `.refresh-backups/legacy-*/`.
That local directory is ignored by Git. Unknown daily-price filenames are never
deleted automatically. Normal refreshes reject aliases, so a second naming
scheme cannot silently reappear.
