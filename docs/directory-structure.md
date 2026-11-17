# Repository Structure and File Lifecycle

The repository separates public entry points, executable research code, structured evidence, and generated artifacts.

```text
Task1/ ... Task8/       task-specific README, scripts, and dashboard
data/                   raw snapshots, processed datasets, and metadata
artifacts/models/       serialized estimators used by the validated pipelines
artifacts/charts/       maintained English charts used by current analyses
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
- `data/taskN/raw/` stores frozen source snapshots; processed and metadata directories store derived evidence and provenance.
- `artifacts/models/` stores estimators only when the matching feature contract and metadata are present.
- `reports/TaskN_Report.pdf` is generated from the maintained English task summary.

## Evidence rules

1. Structured CSV or JSON files are the source of displayed metrics; HTML is a presentation layer.
2. Network refresh is separate from offline reproduction so committed examples remain inspectable.
3. A backtest, a platform simulation, and a public-data shadow portfolio are labeled separately.
4. No account identifiers, passwords, cookies, tokens, or private share links belong in the repository.
5. Generated files are kept only when they support a maintained dashboard, validation check, or report.

## Maintenance checks

Run the repository-wide validation before publishing:

```bash
python tools/run_all_validations.py
```

When a data contract changes, update the producer, consumer, metadata, dashboard, and validation in the same change.
