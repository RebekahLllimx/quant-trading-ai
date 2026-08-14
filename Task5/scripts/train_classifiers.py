#!/usr/bin/env python3
"""Select on 2023-2024, refit, and evaluate the locked models once on 2025."""

from __future__ import annotations

import json
import platform
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from task5_common import (
    FEATURE_COLUMNS,
    METADATA_DIR,
    MODEL_LABELS,
    PROCESSED_DIR,
    RANDOM_SEED,
    ensure_directories,
    sha256_file,
    write_json,
)


MODEL_DIR = PROCESSED_DIR / "models"


def metric_row(y_true: np.ndarray, probability: np.ndarray, threshold: float = 0.5) -> dict:
    prediction = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    return {
        "auc": float(roc_auc_score(y_true, probability)),
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "threshold": threshold,
    }


def mean_monthly_auc(y_true: np.ndarray, probability: np.ndarray, dates: pd.Series) -> float:
    local = pd.DataFrame({"Date": pd.to_datetime(dates).to_numpy(), "y": y_true, "p": probability})
    scores = []
    for _, group in local.groupby("Date"):
        if group["y"].nunique() == 2:
            scores.append(roc_auc_score(group["y"], group["p"]))
    return float(np.mean(scores))


def moving_block_bootstrap_auc(
    y_true: np.ndarray,
    probability: np.ndarray,
    dates: pd.Series,
    *,
    repetitions: int = 1000,
    block_length: int = 3,
    seed: int = RANDOM_SEED,
) -> tuple[float, float]:
    """Resample three-month date blocks to retain cross-section and label overlap."""
    date_values = pd.to_datetime(dates).dt.strftime("%Y-%m-%d").to_numpy()
    unique_dates = np.array(sorted(np.unique(date_values)))
    groups = [np.flatnonzero(date_values == value) for value in unique_dates]
    rng = np.random.default_rng(seed)
    scores = []
    blocks_needed = int(np.ceil(len(groups) / block_length))
    max_start = max(1, len(groups) - block_length + 1)
    for _ in range(repetitions):
        sampled_groups = []
        for _ in range(blocks_needed):
            start = int(rng.integers(0, max_start))
            sampled_groups.extend(groups[start : start + block_length])
        indexes = np.concatenate(sampled_groups[: len(groups)])
        sampled_y = y_true[indexes]
        if np.unique(sampled_y).size == 2:
            scores.append(roc_auc_score(sampled_y, probability[indexes]))
    return tuple(float(value) for value in np.quantile(scores, [0.025, 0.975]))


def candidate_models() -> dict[str, list[tuple[str, object, dict]]]:
    logistic = []
    for c_value in (0.01, 0.1, 1.0):
        estimator = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        C=c_value,
                        max_iter=1500,
                        solver="lbfgs",
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        )
        logistic.append((f"C={c_value:g}", estimator, {"C": c_value}))

    tree_settings = [
        {"max_depth": 3, "min_samples_leaf": 50},
        {"max_depth": 5, "min_samples_leaf": 30},
        {"max_depth": 7, "min_samples_leaf": 20},
    ]
    trees = [
        (
            f"depth={settings['max_depth']},leaf={settings['min_samples_leaf']}",
            DecisionTreeClassifier(random_state=RANDOM_SEED, **settings),
            settings,
        )
        for settings in tree_settings
    ]

    forest_settings = [
        {"max_depth": 5, "min_samples_leaf": 20, "max_features": "sqrt"},
        {"max_depth": 8, "min_samples_leaf": 15, "max_features": "sqrt"},
        {"max_depth": 10, "min_samples_leaf": 10, "max_features": 0.7},
    ]
    forests = [
        (
            f"depth={settings['max_depth']},leaf={settings['min_samples_leaf']},features={settings['max_features']}",
            RandomForestClassifier(
                n_estimators=400,
                n_jobs=-1,
                random_state=RANDOM_SEED,
                max_samples=0.80,
                class_weight="balanced",
                **settings,
            ),
            {"n_estimators": 400, "max_samples": 0.80, "class_weight": "balanced", **settings},
        )
        for settings in forest_settings
    ]
    return {"logistic_regression": logistic, "decision_tree": trees, "random_forest": forests}


def model_importance(model_name: str, model) -> np.ndarray:
    if model_name == "logistic_regression":
        return model.named_steps["classifier"].coef_[0]
    return model.feature_importances_


def main() -> None:
    ensure_directories()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = PROCESSED_DIR / "task5_ml_dataset.csv"
    if not dataset_path.exists():
        raise FileNotFoundError("请先运行 prepare_ml_data.py。")
    frame = pd.read_csv(dataset_path, parse_dates=["Date", "label_end_date"])
    splits = {name: part.copy() for name, part in frame.groupby("Split", sort=False)}
    for required in ("train", "validation", "development", "test"):
        if required not in splits or splits[required].empty:
            raise RuntimeError(f"数据集中缺少 {required} 样本。")

    x_train = splits["train"][FEATURE_COLUMNS]
    y_train = splits["train"]["Label"].to_numpy()
    selection_rows = []
    selected = {}

    for model_name, candidates in candidate_models().items():
        best = None
        for order, (candidate_name, estimator, parameters) in enumerate(candidates):
            fitted = clone(estimator).fit(x_train, y_train)
            period_metrics = {}
            aucs = []
            for split_name in ("validation", "development"):
                part = splits[split_name]
                probability = fitted.predict_proba(part[FEATURE_COLUMNS])[:, 1]
                metrics = metric_row(part["Label"].to_numpy(), probability)
                metrics["mean_monthly_auc"] = mean_monthly_auc(part["Label"].to_numpy(), probability, part["Date"])
                period_metrics.update({f"{split_name}_{key}": value for key, value in metrics.items()})
                aucs.append(metrics["auc"])
            selection_score = float(np.mean(aucs))
            stability_score = float(np.min(aucs))
            selection_rows.append(
                {
                    "model": model_name,
                    "model_label": MODEL_LABELS[model_name],
                    "candidate": candidate_name,
                    "candidate_order": order,
                    "parameters": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
                    "selection_score_mean_auc": selection_score,
                    "selection_score_min_auc": stability_score,
                    **period_metrics,
                }
            )
            candidate_key = (selection_score, stability_score, -order)
            if best is None or candidate_key > best["key"]:
                best = {
                    "key": candidate_key,
                    "estimator": estimator,
                    "parameters": parameters,
                    "candidate": candidate_name,
                    "selection_score": selection_score,
                }
            print(
                f"[select] {MODEL_LABELS[model_name]} {candidate_name}: "
                f"2023 AUC={aucs[0]:.4f}, 2024 AUC={aucs[1]:.4f}, mean={selection_score:.4f}"
            )
        selected[model_name] = best

    candidates_path = PROCESSED_DIR / "task5_candidate_metrics.csv"
    pd.DataFrame(selection_rows).to_csv(candidates_path, index=False, encoding="utf-8-sig")

    fit_frame = frame[frame["Split"].isin(["train", "validation", "development"])].copy()
    x_fit = fit_frame[FEATURE_COLUMNS]
    y_fit = fit_frame["Label"].to_numpy()
    test = splits["test"]
    x_test = test[FEATURE_COLUMNS]
    y_test = test["Label"].to_numpy()

    metric_rows = []
    prediction_frames = []
    roc_rows = []
    importance_rows = []
    yearly_rows = []
    model_metadata = {}

    for model_index, (model_name, choice) in enumerate(selected.items()):
        fitted = clone(choice["estimator"]).fit(x_fit, y_fit)
        probability = fitted.predict_proba(x_test)[:, 1]
        metrics = metric_row(y_test, probability)
        metrics["mean_monthly_auc"] = mean_monthly_auc(y_test, probability, test["Date"])
        low, high = moving_block_bootstrap_auc(
            y_test,
            probability,
            test["Date"],
            seed=RANDOM_SEED + model_index,
        )
        metrics["auc_ci_low"] = low
        metrics["auc_ci_high"] = high
        metric_rows.append(
            {
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "selected_candidate": choice["candidate"],
                "selection_score_mean_auc": choice["selection_score"],
                **metrics,
            }
        )

        prediction = test[["Date", "Symbol", "Name", "Label", "future_return_60d", "future_return_rank"]].copy()
        prediction["model"] = model_name
        prediction["model_label"] = MODEL_LABELS[model_name]
        prediction["probability"] = probability
        prediction["prediction"] = (probability >= 0.5).astype(int)
        prediction_frames.append(prediction)

        fpr, tpr, thresholds = roc_curve(y_test, probability)
        finite_thresholds = np.where(np.isfinite(thresholds), thresholds, 1.0)
        roc_rows.extend(
            {
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "fpr": float(fpr_value),
                "tpr": float(tpr_value),
                "threshold": float(threshold),
                "auc": metrics["auc"],
            }
            for fpr_value, tpr_value, threshold in zip(fpr, tpr, finite_thresholds)
        )

        values = model_importance(model_name, fitted)
        importance_rows.extend(
            {
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "feature": feature,
                "importance": float(value),
                "absolute_importance": float(abs(value)),
                "importance_type": "standardized_coefficient" if model_name == "logistic_regression" else "impurity_importance",
            }
            for feature, value in zip(FEATURE_COLUMNS, values)
        )

        yearly_rows.append(
            {
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "year": 2025,
                **metric_row(y_test, probability),
                "mean_monthly_auc": metrics["mean_monthly_auc"],
            }
        )

        model_path = MODEL_DIR / f"{model_name}.joblib"
        joblib.dump(
            {"model": fitted, "features": FEATURE_COLUMNS, "threshold": 0.5, "target": "60d_top30_vs_bottom30"},
            model_path,
        )
        model_metadata[model_name] = {
            "selected_candidate": choice["candidate"],
            "parameters": choice["parameters"],
            "selection_score_mean_auc": choice["selection_score"],
            "model_file": model_path.name,
            "model_sha256": sha256_file(model_path),
        }
        print(
            f"[test-once] {MODEL_LABELS[model_name]} 2025 AUC={metrics['auc']:.4f} "
            f"95% block CI [{low:.4f}, {high:.4f}]"
        )

    baseline_probability = float(y_fit.mean())
    baseline_scores = np.full(len(y_test), baseline_probability)
    baseline_metrics = metric_row(y_test, baseline_scores)
    baseline_metrics.update(
        {
            "mean_monthly_auc": 0.5,
            "auc_ci_low": 0.5,
            "auc_ci_high": 0.5,
        }
    )
    metric_rows.append(
        {
            "model": "majority_baseline",
            "model_label": MODEL_LABELS["majority_baseline"],
            "selected_candidate": "pretest prevalence",
            "selection_score_mean_auc": 0.5,
            **baseline_metrics,
        }
    )

    metrics_path = PROCESSED_DIR / "task5_model_metrics.csv"
    predictions_path = PROCESSED_DIR / "task5_test_predictions.csv"
    pd.DataFrame(metric_rows).to_csv(metrics_path, index=False, encoding="utf-8-sig")
    pd.concat(prediction_frames, ignore_index=True).to_csv(predictions_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    pd.DataFrame(roc_rows).to_csv(PROCESSED_DIR / "task5_roc_points.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(importance_rows).to_csv(PROCESSED_DIR / "task5_feature_importance.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(yearly_rows).to_csv(PROCESSED_DIR / "task5_yearly_metrics.csv", index=False, encoding="utf-8-sig")

    run_metadata = {
        "created_at": datetime.now().astimezone().isoformat(),
        "random_seed": RANDOM_SEED,
        "target": "future 60-trading-day top 30% versus bottom 30% cross-sectional return",
        "selection_rule": "highest mean AUC across 2023 validation and 2024 development; minimum annual AUC breaks ties",
        "refit_rule": "selected hyperparameters refitted on 2018-2024 before one 2025 test evaluation",
        "auc_uncertainty": "95% moving-block bootstrap over month-end dates; three-month blocks; 1000 repetitions",
        "classification_threshold": 0.5,
        "feature_columns": FEATURE_COLUMNS,
        "fit_rows": int(len(fit_frame)),
        "test_rows": int(len(test)),
        "test_months": int(test["Date"].nunique()),
        "training_positive_rate": baseline_probability,
        "models": model_metadata,
        "outputs": {
            "candidate_metrics_sha256": sha256_file(candidates_path),
            "metrics_sha256": sha256_file(metrics_path),
            "predictions_sha256": sha256_file(predictions_path),
        },
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    write_json(METADATA_DIR / "model_run.json", run_metadata)
    print(pd.DataFrame(metric_rows)[["model_label", "auc", "mean_monthly_auc", "accuracy", "precision", "recall", "f1"]].to_string(index=False))


if __name__ == "__main__":
    main()
