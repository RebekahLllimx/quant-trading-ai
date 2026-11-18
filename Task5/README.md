# Task 5 - Classification Workflow and Financial Transfer Tests

Task 5 builds a supervised-classification workflow on a labeled medical dataset, then applies the same validation discipline to three chronological financial classification problems.

## Primary case

The scikit-learn breast-cancer dataset contains 569 observations and 30 cell-nucleus features. The workflow recodes malignant cases as `1`, creates a stratified 80/20 split, performs feature screening on the training set only, and compares logistic regression, decision tree, random forest, and gradient boosting.

Logistic regression and random forest both achieved test ROC-AUC near `0.994`; gradient boosting reached about `0.992`, and the decision tree about `0.972`. Their intervals overlap, so thousandth-level differences do not support a stable ranking. The comparison also reports balanced accuracy, recall, F1, Brier score, confusion matrices, and feature importance.

## Financial transfer study

Three chronological financial designs produced out-of-sample AUC values of `0.533`, `0.529`, and `0.524`, with confidence intervals covering `0.5`. The accompanying checks cover split dates, label construction, random labels, deliberately predictable labels, and performance by market period. These results show that the selected financial features did not produce a stable ranking signal on the held-out samples.

## Validate or rebuild the dashboard

After installing the root requirements, run from the repository root. The first command checks portfolio entry points, unit tests, and saved Task 5-7 results; the second rebuilds Task 5's pages from saved outputs without fitting models.

```bash
python tools/run_all_validations.py
python Task5/scripts/build_task5_dashboard.py
```

To rerun the primary classification experiment, use `python Task5/scripts/cancer_case_analysis.py`. It refits models and replaces the case's generated outputs. The [script guide](scripts/README.md) separates this step from financial-data refresh and dashboard rendering.

## Entry points

- [Four-page dashboard](dashboard/index.html)
- [Script guide](scripts/README.md)
- [English report](../reports/Task5_Report.pdf)
- Structured outputs: [`../data/task5/`](../data/task5/)

The validation suite checks input hashes, split boundaries, metric recomputation, prediction grain, and required outputs.
