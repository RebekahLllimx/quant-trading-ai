#!/usr/bin/env python3
"""Independent data and metric checks for Task5 experiment 2."""

from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from experiment2_common import (
    CHART_DIR,
    FEATURE_COLUMNS,
    METADATA_DIR,
    MODEL_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    sha256_file,
    write_json,
)


def near(left: float, right: float, tolerance: float = 1e-10) -> bool:
    return bool(np.isclose(left, right, atol=tolerance, rtol=tolerance))


def main() -> None:
    dataset = pd.read_csv(
        PROCESSED_DIR / "task5_experiment2_dataset.csv", parse_dates=["Date", "label_end_date"]
    )
    predictions = pd.read_csv(
        PROCESSED_DIR / "task5_experiment2_test_predictions.csv", parse_dates=["Date"]
    )
    metrics = pd.read_csv(PROCESSED_DIR / "task5_experiment2_model_metrics.csv").set_index("model")
    clip_bounds = pd.read_csv(METADATA_DIR / "feature_clip_bounds.csv")
    checks: list[dict] = []

    def add(name: str, passed: bool, evidence: str, severity: str = "high") -> None:
        checks.append({"check": name, "passed": bool(passed), "severity_if_failed": severity, "evidence": evidence})

    duplicate_count = int(dataset.duplicated(["Symbol", "Date"]).sum())
    add("dataset_key_uniqueness", duplicate_count == 0, f"duplicate Symbol-Date rows={duplicate_count}")
    add("binary_label", set(dataset["Label"].unique()) == {0, 1}, f"values={sorted(dataset['Label'].unique().tolist())}")
    add("no_missing_model_cells", int(dataset.isna().sum().sum()) == 0, f"missing cells={int(dataset.isna().sum().sum())}")
    add("finite_features", bool(np.isfinite(dataset[FEATURE_COLUMNS].to_numpy()).all()), "all model feature cells are finite")
    add(
        "label_matches_future_return",
        bool(np.array_equal(dataset["Label"].to_numpy(), (dataset["future_return_20d"] > 0).astype(int).to_numpy())),
        "Label equals 1[future_return_20d > 0]",
    )
    add(
        "target_horizon_positive",
        bool((dataset["label_end_date"] > dataset["Date"]).all()),
        f"minimum horizon calendar days={(dataset['label_end_date'] - dataset['Date']).dt.days.min()}",
    )

    date_sets = {split: set(part["Date"]) for split, part in dataset.groupby("Split")}
    pairs = [("train", "validation"), ("train", "development"), ("train", "test"), ("validation", "development"), ("validation", "test"), ("development", "test")]
    overlaps = {f"{left}_{right}": len(date_sets[left] & date_sets[right]) for left, right in pairs}
    add("split_date_disjointness", all(value == 0 for value in overlaps.values()), f"date overlaps={overlaps}")
    boundaries = {"train": "2022-12-31", "validation": "2023-12-31", "development": "2024-12-31", "test": "2025-12-31"}
    for split, boundary in boundaries.items():
        latest = dataset.loc[dataset["Split"] == split, "label_end_date"].max()
        add(f"{split}_label_boundary", latest <= pd.Timestamp(boundary), f"latest label end={latest.date()}, boundary={boundary}")

    years = dataset.assign(Year=dataset["Date"].dt.year).groupby("Year")["Date"].nunique()
    add(
        "annual_month_end_counts",
        bool((years.loc[[2023, 2024, 2025]] == 11).all()),
        f"unique month-end dates by year={years.to_dict()}",
        severity="medium",
    )
    month_keys = dataset["Date"].dt.to_period("M")
    add(
        "one_observation_date_per_month",
        dataset.groupby(month_keys)["Date"].nunique().max() == 1,
        f"maximum dates in a calendar month={dataset.groupby(month_keys)['Date'].nunique().max()}",
    )

    constant_market_features = [
        "market_median_return_5d",
        "market_median_return_20d",
        "market_breadth_20d",
        "market_dispersion_20d",
    ]
    maximum_within_date_unique = int(dataset.groupby("Date")[constant_market_features].nunique().to_numpy().max())
    add("market_state_shared_within_date", maximum_within_date_unique == 1, f"maximum unique same-date market-state values={maximum_within_date_unique}")
    add(
        "excess_return_5d_identity",
        bool(np.allclose(dataset["excess_return_5d"], dataset["return_5d"] - dataset["market_median_return_5d"], atol=1e-12, rtol=1e-12)),
        "excess_return_5d = return_5d - market median",
    )
    add(
        "excess_return_20d_identity",
        bool(np.allclose(dataset["excess_return_20d"], dataset["return_20d"] - dataset["market_median_return_20d"], atol=1e-12, rtol=1e-12)),
        "excess_return_20d = return_20d - market median",
    )
    add(
        "rank_feature_range",
        dataset["return_20d_rank"].between(-0.5, 0.5).all(),
        f"range=[{dataset['return_20d_rank'].min():.4f}, {dataset['return_20d_rank'].max():.4f}]",
    )

    add(
        "clip_bounds_cover_features",
        set(clip_bounds["feature"]) == set(FEATURE_COLUMNS),
        f"bounds={len(clip_bounds)}, expected={len(FEATURE_COLUMNS)}",
    )
    add(
        "clip_bounds_ordered",
        bool((clip_bounds["lower"] <= clip_bounds["upper"]).all()),
        f"unordered rows={int((clip_bounds['lower'] > clip_bounds['upper']).sum())}",
    )

    test = dataset[dataset["Split"] == "test"]
    expected_test_rows = len(test)
    recalculations = []
    for model, part in predictions.groupby("model"):
        stored = metrics.loc[model]
        y_true = part["Label"].to_numpy()
        probability = part["probability"].to_numpy()
        prediction = (probability >= 0.5).astype(int)
        result = {
            "auc": roc_auc_score(y_true, probability),
            "accuracy": accuracy_score(y_true, prediction),
            "precision": precision_score(y_true, prediction, zero_division=0),
            "recall": recall_score(y_true, prediction, zero_division=0),
            "f1": f1_score(y_true, prediction, zero_division=0),
        }
        all_match = all(near(result[key], stored[key]) for key in result)
        recalculations.append({"model": model, "all_match": all_match, **result})
        add(f"metrics_recompute_{model}", all_match, ", ".join(f"{key}={value:.12f}" for key, value in result.items()))
        add(
            f"prediction_grain_{model}",
            len(part) == expected_test_rows and int(part.duplicated(["Symbol", "Date"]).sum()) == 0,
            f"rows={len(part)}, expected={expected_test_rows}, duplicate keys={int(part.duplicated(['Symbol', 'Date']).sum())}",
        )
        add(
            f"probability_range_{model}",
            part["probability"].between(0, 1).all(),
            f"range=[{part['probability'].min():.6f}, {part['probability'].max():.6f}]",
        )

    reference = None
    consistent = True
    for _, part in predictions.groupby("model"):
        labels = part.sort_values(["Date", "Symbol"])[["Date", "Symbol", "Label"]].reset_index(drop=True)
        if reference is None:
            reference = labels
        elif not labels.equals(reference):
            consistent = False
    add("same_test_labels_for_all_models", consistent, f"model count={predictions['model'].nunique()}")

    interval_rows = metrics.loc[["logistic_regression", "decision_tree", "random_forest"]]
    add(
        "auc_intervals_ordered_and_contain_point",
        bool(((interval_rows["auc_ci_low"] <= interval_rows["auc"]) & (interval_rows["auc"] <= interval_rows["auc_ci_high"])).all()),
        "all three point estimates fall inside their stored block-bootstrap intervals",
    )

    manifest_path = RAW_DIR.parent / "metadata" / "raw_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hash_failures = []
    for item in manifest["files"]:
        raw_path = RAW_DIR / f"{item['symbol'].replace('.', '_')}.csv"
        if not raw_path.exists() or sha256_file(raw_path) != item["sha256"]:
            hash_failures.append(item["symbol"])
    add("raw_snapshot_hashes", not hash_failures, f"hash mismatches={hash_failures[:10]}")

    model_files = [MODEL_DIR / f"{model}.joblib" for model in ("logistic_regression", "decision_tree", "random_forest")]
    bad_models = [path.name for path in model_files if not path.exists() or path.stat().st_size < 1000]
    add("model_artifacts_exist", not bad_models, f"missing or too small={bad_models}")

    chart_files = ["baseline_comparison.png", "time_split.png", "label_distribution.png", "roc_curves.png", "confusion_matrices.png", "feature_importance.png"]
    bad_charts = [name for name in chart_files if not (CHART_DIR / name).exists() or (CHART_DIR / name).stat().st_size < 10_000]
    add("chart_outputs_exist", not bad_charts, f"missing or too small={bad_charts}", severity="medium")

    failed = [check for check in checks if not check["passed"]]
    report = {
        "validated_at": datetime.now().astimezone().isoformat(),
        "overall_assessment": "ready_to_share_with_caveats" if not failed else "needs_revision",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": failed,
        "checks": checks,
        "metric_recalculations": recalculations,
        "required_caveats": [
            "The best 2025 AUC is only 0.529 and its moving-block confidence interval reaches approximately 0.5.",
            "The second experiment improves logistic-regression AUC modestly but does not improve every model.",
            "The frozen universe is based on January 2018 liquidity rather than point-in-time index membership.",
            "No fees, slippage, trading constraints or portfolio construction are included because this is a classification experiment.",
            "Feature importance describes model dependence and is not causal evidence.",
        ],
    }
    write_json(METADATA_DIR / "validation_report.json", report)
    print(f"[validation] {report['overall_assessment']}: {report['checks_passed']}/{report['checks_total']} checks passed")
    if failed:
        for check in failed:
            print(f"FAIL {check['check']}: {check['evidence']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
