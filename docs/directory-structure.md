# Repository Structure

The repository separates public entry points, executable research code, structured evidence, and generated artifacts.

```text
Task1/ ... Task8/       task-specific README, scripts, and dashboard
data/                   raw snapshots, processed datasets, and metadata
artifacts/models/       serialized estimators used by the validated pipelines
artifacts/charts/       charts used by the analyses and dashboards
reports/                eight generated English PDF reports
src/                    shared indicator and equation utilities
tools/                  repository-wide validation and report builders
tests/                  offline regression tests
market_data.py          instrument registry, OHLCV contract, and history rules
refresh_pipeline.py     staged snapshot builds and publication validation
update_all_data.py      provider adapters and the market-refresh CLI
.github/workflows/      scheduled refresh and validation workflows
index.html              GitHub Pages hub
```

## File responsibilities

- `TaskN/README.md` explains the task, method, result, limitations, and entry points.
- `TaskN/scripts/` contains data preparation, research, validation, and page-build code.
- `TaskN/dashboard/index.html` is the stable public page for each task.
- `data/csv/` holds the shared daily-price snapshots used by Tasks 1-4. Tasks 5-7 use task-specific trees under `data/task5/`, `data/task6/`, and `data/task7/`, with raw, processed, and metadata files where required.
- `data/csv/manifest.json` records snapshot hashes, coverage, units, and price-adjustment provenance. The [market-data guide](market-data.md) explains refresh and migration commands.
- `artifacts/models/` stores estimators only when the matching feature contract and metadata are present.
- `reports/TaskN_Report.pdf` contains the task's methods, results, and interpretation.

## Evidence rules

1. Structured CSV or JSON files are the source of displayed metrics; HTML is a presentation layer.
2. Network refresh is separate from offline reproduction so committed examples remain inspectable.
3. A backtest, a platform simulation, and a public-data shadow portfolio are labeled separately.
4. No account identifiers, passwords, cookies, tokens, or private share links belong in the repository.
5. Generated files are kept only when they support a maintained dashboard, validation check, or report.

## Validation and rebuilding

From the repository root:

```bash
python tools/run_all_validations.py
```

The Python 3.10 research environment runs structure checks, unit tests, stock-page consistency checks, and Task 5-7 result validators without fetching prices or training models. The wrapper preserves the saved validation reports. Live-provider refresh uses Python 3.12 and `requirements-refresh.txt` separately.

Dashboard builders replace HTML and presentation JSON. Tasks 1, 2, and 4 preserve their page layout and JavaScript calculations while refreshing embedded data. The unified updater stages and validates all four stock pages before replacing the working snapshot. Research pipelines can also replace predictions, model bundles, charts, and metadata. Task 7's market-data refresh uses network access; its offline shadow engine reads the committed snapshots.
