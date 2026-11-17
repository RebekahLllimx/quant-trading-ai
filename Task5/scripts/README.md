# Task 5 Script Guide

## Primary teaching case

- `cancer_case_analysis.py` validates the dataset, performs training-only feature selection, trains four classifiers, and writes frozen evaluation outputs.
- `build_task5_dashboard.py` rebuilds the four-page public dashboard from committed structured results.

## Financial experiments

- `fetch_stock_data.py`, `prepare_ml_data.py`, `train_classifiers.py`, `plot_evaluation.py`, and `validate_results.py` implement the chronological cross-sectional experiment.
- Files containing `experiment2` implement the alternative 20-day label design and its independent validation.
- `fetch_catl_case.py` and `catl_case_analysis.py` implement the CATL versus CSI 300 case study.

## Recommended order

```bash
python Task5/scripts/cancer_case_analysis.py
python Task5/scripts/validate_results.py
python Task5/scripts/validate_experiment2.py
python Task5/scripts/build_task5_dashboard.py
```

Dashboard builders read frozen results; they do not tune models. Data and metadata live under `data/task5/`, models under `artifacts/models/task5/`, and maintained charts under `artifacts/charts/task5/`.
