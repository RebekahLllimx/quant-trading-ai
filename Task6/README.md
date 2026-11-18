# Task 6 - ML Strategy Research

Task 6 connects model scores to portfolio decisions. It uses chronological validation, converts predictions into positions, deducts turnover costs, and compares the resulting portfolio with an equal-weight universe.

## Main study: quarterly cross-sectional ranking

- Split quarterly observations chronologically, not randomly.
- Compare linear, ridge, logistic, tree, random-forest, and histogram-gradient models.
- Rank predicted next-quarter returns and form an equal-weight top-30 portfolio.
- Compare against the contemporaneous equal-weight universe.
- Deduct `0.2% x one-way turnover` from gross returns.
- Test a rank-buffer variant designed to reduce unnecessary turnover.
- Compare equal-weight and prediction-weighted extensions selected on validation data.

The held-out period contains three quarters. The report therefore presents cumulative return, annualized return, Sharpe ratio, turnover, and drawdown together with the test dates and sample size.

## Extension study: single-stock timing

The extension predicts Ping An Bank's next three-day direction from rolling price and volume features using stochastic-gradient logistic regression. On the final held-out window, ROC-AUC reached `0.571`. The report records the tested variants and retains the same test window across comparisons.

The model-selection comparison is part of the result rather than an omitted tuning detail. A larger search produced a validation AUC of `0.752` but only `0.538` on the untouched test. The frozen rolling baseline transferred more consistently (`0.623` validation, `0.571` test), so the test window is treated as a one-time audit rather than another tuning surface.

## Inspect the committed results

Use the pinned environment in the root `requirements.txt`. From the repository root:

```bash
python tools/run_all_validations.py
python Task6/scripts/build_dashboard.py
```

This checks the saved predictions and portfolios and rebuilds the dashboard without refitting a model.

## Rerun the research pipelines

The following commands refit models and replace generated predictions, portfolio records, metadata, and figures:

```bash
python Task6/scripts/main_pipeline.py
python Task6/scripts/additional_pipeline.py
python Task6/scripts/enhanced_pipeline.py
python Task6/scripts/plot_results.py
python Task6/scripts/build_dashboard.py
python Task6/scripts/validate_results.py
```

## Entry points

- [Interactive dashboard](dashboard/index.html)
- [Dashboard data contract](dashboard/README.md)
- [English report](../reports/Task6_Report.pdf)
- Structured outputs: [`../data/task6/`](../data/task6/)

The report records three data constraints that affect interpretation: incomplete point-in-time disclosure metadata, no historical index-membership history, and incomplete liquidity flags.
