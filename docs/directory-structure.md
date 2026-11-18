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
.github/workflows/      scheduled refresh and validation workflows
index.html              GitHub Pages hub
```

## File responsibilities

- `TaskN/README.md` explains the task, method, result, limitations, and entry points.
- `TaskN/scripts/` contains data preparation, research, validation, and page-build code.
- `TaskN/dashboard/index.html` is the stable public page for each task.
- `data/csv/` holds the shared daily-price snapshots used by Tasks 1-4. Tasks 5-7 use task-specific trees under `data/task5/`, `data/task6/`, and `data/task7/`, with raw, processed, and metadata files where required.
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

The wrapper runs the structure checks, unit tests, and Task 5-7 result validators without fetching new prices or training models. Individual validators write timestamped validation reports; the wrapper restores those files after the check.

Dashboard builders replace HTML and presentation JSON. Research pipelines can also replace predictions, model bundles, charts, and metadata. Task 7's market-data refresh uses network access; its offline shadow engine reads the committed snapshots. Task 4 refreshes the data embedded in its standalone dashboard without replacing the page layout.
