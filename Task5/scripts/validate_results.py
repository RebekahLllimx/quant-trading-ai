#!/usr/bin/env python3
"""Independent reproducibility checks for the Task5 modeling outputs."""

from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from task5_common import CHART_DIR, METADATA_DIR, PROCESSED_DIR, sha256_file, write_json


def close(a: float, b: float, tolerance: float = 1e-10) -> bool:
    return bool(np.isclose(a, b, atol=tolerance, rtol=tolerance))


def main() -> None:
    dataset_path = PROCESSED_DIR / "task5_ml_dataset.csv"
    prediction_path = PROCESSED_DIR / "task5_test_predictions.csv"
    metrics_path = PROCESSED_DIR / "task5_model_metrics.csv"
    dataset = pd.read_csv(dataset_path, parse_dates=["Date", "label_end_date"])
    predictions = pd.read_csv(prediction_path, parse_dates=["Date"])
    metrics = pd.read_csv(metrics_path).set_index("model")

    checks = []

    def add(name: str, passed: bool, evidence: str, severity: str = "high") -> None:
        checks.append({"check": name, "passed": bool(passed), "severity_if_failed": severity, "evidence": evidence})

    add(
        "dataset_key_uniqueness",
        dataset.duplicated(["Symbol", "Date"]).sum() == 0,
        f"duplicate Symbol-Date rows={dataset.duplicated(['Symbol', 'Date']).sum()}",
    )
    add("binary_label", set(dataset["Label"].unique()) == {0, 1}, f"values={sorted(dataset['Label'].unique().tolist())}")
    add("no_missing_model_cells", dataset.isna().sum().sum() == 0, f"missing cells={dataset.isna().sum().sum()}")

    overlap = {}
    date_sets = {split: set(part["Date"]) for split, part in dataset.groupby("Split")}
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlap[f"{left}_{right}"] = len(date_sets[left] & date_sets[right])
    add("split_date_disjointness", all(value == 0 for value in overlap.values()), f"date overlaps={overlap}")
    add(
        "train_label_purge",
        dataset.loc[dataset["Split"] == "train", "label_end_date"].max() <= pd.Timestamp("2022-12-31"),
        f"latest train label end={dataset.loc[dataset['Split']=='train', 'label_end_date'].max().date()}",
    )
    add(
        "validation_label_purge",
        dataset.loc[dataset["Split"] == "validation", "label_end_date"].max() <= pd.Timestamp("2023-12-31"),
        f"latest validation label end={dataset.loc[dataset['Split']=='validation', 'label_end_date'].max().date()}",
    )

    test = dataset[dataset["Split"] == "test"]
    expected_test_rows = len(test)
    metric_checks = []
    for model, part in predictions.groupby("model"):
        stored = metrics.loc[model]
        y = part["Label"].to_numpy()
        probability = part["probability"].to_numpy()
        predicted = (probability >= 0.5).astype(int)
        recalculated = {
            "auc": roc_auc_score(y, probability),
            "accuracy": accuracy_score(y, predicted),
            "precision": precision_score(y, predicted, zero_division=0),
            "recall": recall_score(y, predicted, zero_division=0),
            "f1": f1_score(y, predicted, zero_division=0),
        }
        all_match = all(close(recalculated[key], stored[key]) for key in recalculated)
        metric_checks.append({"model": model, "all_match": all_match, **recalculated})
        add(
            f"metrics_recompute_{model}",
            all_match,
            ", ".join(f"{key}={value:.12f}" for key, value in recalculated.items()),
        )
        add(
            f"prediction_grain_{model}",
            len(part) == expected_test_rows and part.duplicated(["Symbol", "Date"]).sum() == 0,
            f"rows={len(part)}, expected={expected_test_rows}, duplicate keys={part.duplicated(['Symbol','Date']).sum()}",
        )
        label_auc = roc_auc_score(y, predicted) if np.unique(predicted).size > 1 else 0.5
        add(
            f"auc_uses_probability_{model}",
            close(stored["auc"], recalculated["auc"]) and not close(stored["auc"], label_auc),
            f"stored/probability AUC={stored['auc']:.6f}; hard-label AUC={label_auc:.6f}",
        )

    first_labels = None
    label_consistency = True
    for _, part in predictions.sort_values(["model", "Date", "Symbol"]).groupby("model"):
        values = part.sort_values(["Date", "Symbol"])[["Date", "Symbol", "Label"]].reset_index(drop=True)
        if first_labels is None:
            first_labels = values
        elif not values.equals(first_labels):
            label_consistency = False
    add("same_test_labels_for_all_models", label_consistency, f"models={predictions['model'].nunique()}")

    manifest = json.loads((METADATA_DIR / "raw_manifest.json").read_text(encoding="utf-8"))
    hash_failures = []
    for item in manifest["files"]:
        raw_path = dataset_path.parents[1] / "raw" / f"{item['symbol'].replace('.', '_')}.csv"
        if not raw_path.exists() or sha256_file(raw_path) != item["sha256"]:
            hash_failures.append(item["symbol"])
    add("raw_snapshot_hashes", not hash_failures, f"hash mismatches={hash_failures[:10]}")

    chart_files = ["time_split.png", "label_distribution.png", "roc_curves.png", "confusion_matrices.png", "feature_importance.png"]
    bad_charts = [name for name in chart_files if not (CHART_DIR / name).exists() or (CHART_DIR / name).stat().st_size < 10_000]
    add("chart_outputs_exist", not bad_charts, f"missing or too small={bad_charts}", severity="medium")

    failed = [item for item in checks if not item["passed"]]
    report = {
        "validated_at": datetime.now().astimezone().isoformat(),
        "overall_assessment": "ready_to_share_with_caveats" if not failed else "needs_revision",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": failed,
        "checks": checks,
        "metric_recalculations": metric_checks,
        "required_caveats": [
            "AUC values are only slightly above 0.5 and do not establish a profitable strategy.",
            "The universe is frozen from January 2018 liquidity and is not a historical index constituent panel.",
            "Price levels are scale-free adjusted return indexes for most symbols; only ratio features are modeled.",
            "Three initial raw files came from an earlier frozen qfq API attempt and are explicitly identified in the manifest.",
            "Current provider limits prevented automatic company-name enrichment; stock codes remain the stable identifiers.",
        ],
    }
    write_json(METADATA_DIR / "validation_report.json", report)
    print(f"[validation] {report['overall_assessment']}: {report['checks_passed']}/{report['checks_total']} checks passed")
    if failed:
        for item in failed:
            print(f"FAIL {item['check']}: {item['evidence']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

