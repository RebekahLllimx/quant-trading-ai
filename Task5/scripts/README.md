# Task 5 Script Guide

## Primary classification case

- `cancer_case_analysis.py` validates the dataset, performs training-only feature selection, trains four classifiers, and writes frozen evaluation outputs.
- `build_task5_dashboard.py` rebuilds the four-page public dashboard from committed structured results.

## Financial experiments

- `fetch_stock_data.py`, `prepare_ml_data.py`, `train_classifiers.py`, `plot_evaluation.py`, and `validate_results.py` implement the chronological cross-sectional experiment.
- Files containing `experiment2` implement the alternative 20-day label design and its independent validation.
- `fetch_catl_case.py` and `catl_case_analysis.py` implement the CATL versus CSI 300 case study.

## Offline dashboard rebuild

Run from the repository root after installing `requirements.txt`:

```bash
python tools/run_all_validations.py
python Task5/scripts/build_task5_dashboard.py
```

This reads the committed results and rebuilds HTML. To refit the primary classification case, run `python Task5/scripts/cancer_case_analysis.py` first. Financial fetch scripts require network access; they are separate from the offline checks above.

Data and metadata live under `data/task5/`, models under `artifacts/models/task5/`, and charts under `artifacts/charts/task5/`. Model-training and research scripts overwrite their generated outputs; dashboard builders overwrite only their presentation files.
