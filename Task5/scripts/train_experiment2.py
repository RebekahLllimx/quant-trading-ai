#!/usr/bin/env python3
"""Select on 2023-2024, refit, and test the locked experiment on 2025."""

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
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score, roc_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from experiment2_common import FEATURE_COLUMNS, METADATA_DIR, MODEL_DIR, MODEL_LABELS, PROCESSED_DIR, RANDOM_SEED, ensure_directories, sha256_file, write_json


def fit_clip_bounds(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "feature": FEATURE_COLUMNS,
        "lower": frame[FEATURE_COLUMNS].quantile(0.005).to_numpy(),
        "upper": frame[FEATURE_COLUMNS].quantile(0.995).to_numpy(),
    })


def apply_clip(frame: pd.DataFrame, bounds: pd.DataFrame) -> pd.DataFrame:
    result = frame[FEATURE_COLUMNS].copy()
    lookup = bounds.set_index("feature")
    for feature in FEATURE_COLUMNS:
        result[feature] = result[feature].clip(lookup.at[feature, "lower"], lookup.at[feature, "upper"])
    return result


def metric_row(y_true: np.ndarray, probability: np.ndarray, threshold: float = 0.5) -> dict:
    prediction = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    return {
        "auc": float(roc_auc_score(y_true, probability)),
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "threshold": threshold,
    }


def mean_monthly_auc(y_true: np.ndarray, probability: np.ndarray, dates: pd.Series) -> float:
    local = pd.DataFrame({"Date": pd.to_datetime(dates).to_numpy(), "y": y_true, "p": probability})
    values = [roc_auc_score(group["y"], group["p"]) for _, group in local.groupby("Date") if group["y"].nunique() == 2]
    return float(np.mean(values))


def moving_block_bootstrap_auc(y_true: np.ndarray, probability: np.ndarray, dates: pd.Series, *, repetitions: int = 1000, block_length: int = 3, seed: int = RANDOM_SEED) -> tuple[float, float]:
    date_values = pd.to_datetime(dates).dt.strftime("%Y-%m-%d").to_numpy()
    groups = [np.flatnonzero(date_values == value) for value in sorted(np.unique(date_values))]
    generator = np.random.default_rng(seed)
    blocks_needed = int(np.ceil(len(groups) / block_length))
    max_start = max(1, len(groups) - block_length + 1)
    scores = []
    for _ in range(repetitions):
        sampled_groups = []
        for _ in range(blocks_needed):
            start = int(generator.integers(0, max_start))
            sampled_groups.extend(groups[start : start + block_length])
        indexes = np.concatenate(sampled_groups[: len(groups)])
        if np.unique(y_true[indexes]).size == 2:
            scores.append(roc_auc_score(y_true[indexes], probability[indexes]))
    low, high = np.quantile(scores, [0.025, 0.975])
    return float(low), float(high)


def candidate_models() -> dict[str, list[tuple[str, object, dict]]]:
    logistic = []
    for c_value in (0.01, 0.1, 1.0):
        estimator = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(C=c_value, class_weight="balanced", max_iter=2000, solver="lbfgs", random_state=RANDOM_SEED)),
            ]
        )
        logistic.append((f"C={c_value:g}", estimator, {"C": c_value, "class_weight": "balanced"}))

    tree_settings = [
        {"max_depth": 3, "min_samples_leaf": 50},
        {"max_depth": 5, "min_samples_leaf": 30},
        {"max_depth": 7, "min_samples_leaf": 20},
    ]
    trees = [
        (
            f"depth={setting['max_depth']},leaf={setting['min_samples_leaf']}",
            DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM_SEED, **setting),
            {**setting, "class_weight": "balanced"},
        )
        for setting in tree_settings
    ]

    forest_settings = [
        {"max_depth": 5, "min_samples_leaf": 20, "max_features": "sqrt"},
        {"max_depth": 8, "min_samples_leaf": 15, "max_features": "sqrt"},
        {"max_depth": 10, "min_samples_leaf": 10, "max_features": 0.7},
    ]
    forests = [
        (
            f"depth={setting['max_depth']},leaf={setting['min_samples_leaf']},features={setting['max_features']}",
            RandomForestClassifier(n_estimators=400, max_samples=0.8, class_weight="balanced", n_jobs=-1, random_state=RANDOM_SEED, **setting),
            {**setting, "n_estimators": 400, "max_samples": 0.8, "class_weight": "balanced"},
        )
        for setting in forest_settings
    ]
    return {"logistic_regression": logistic, "decision_tree": trees, "random_forest": forests}


def importance_values(model_name: str, fitted: object) -> np.ndarray:
    if model_name == "logistic_regression":
        return fitted.named_steps["classifier"].coef_[0]
    return fitted.feature_importances_


def main() -> None:
    ensure_directories()
    dataset_path = PROCESSED_DIR / "task5_experiment2_dataset.csv"
    frame = pd.read_csv(dataset_path, parse_dates=["Date", "label_end_date"])
    splits = {name: part.copy() for name, part in frame.groupby("Split", sort=False)}
    required = ("train", "validation", "development", "test")
    if any(name not in splits or splits[name].empty for name in required):
        raise RuntimeError("实验二数据缺少训练、验证、开发或测试分段。")

    selection_bounds = fit_clip_bounds(splits["train"])
    x_train = apply_clip(splits["train"], selection_bounds)
    y_train = splits["train"]["Label"].to_numpy()
    selected: dict[str, dict] = {}
    selection_rows: list[dict] = []
    for model_name, candidates in candidate_models().items():
        best = None
        for order, (candidate_name, estimator, parameters) in enumerate(candidates):
            fitted = clone(estimator).fit(x_train, y_train)
            row = {
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "candidate": candidate_name,
                "candidate_order": order,
                "parameters": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
            }
            period_aucs = []
            for split_name in ("validation", "development"):
                part = splits[split_name]
                probability = fitted.predict_proba(apply_clip(part, selection_bounds))[:, 1]
                result = metric_row(part["Label"].to_numpy(), probability)
                result["mean_monthly_auc"] = mean_monthly_auc(part["Label"].to_numpy(), probability, part["Date"])
                row.update({f"{split_name}_{key}": value for key, value in result.items()})
                period_aucs.append(result["auc"])
            row["selection_score_mean_auc"] = float(np.mean(period_aucs))
            row["selection_score_min_auc"] = float(np.min(period_aucs))
            selection_rows.append(row)
            key = (row["selection_score_mean_auc"], row["selection_score_min_auc"], -order)
            if best is None or key > best["key"]:
                best = {"key": key, "candidate": candidate_name, "estimator": estimator, "parameters": parameters, "selection_score": row["selection_score_mean_auc"]}
            print(f"[select] {MODEL_LABELS[model_name]} {candidate_name}: 2023={period_aucs[0]:.4f}, 2024={period_aucs[1]:.4f}, mean={np.mean(period_aucs):.4f}")
        selected[model_name] = best

    pd.DataFrame(selection_rows).to_csv(PROCESSED_DIR / "task5_experiment2_candidate_metrics.csv", index=False, encoding="utf-8-sig")

    fit_frame = frame[frame["Split"].isin(["train", "validation", "development"])].copy()
    bounds = fit_clip_bounds(fit_frame)
    bounds.to_csv(METADATA_DIR / "feature_clip_bounds.csv", index=False, encoding="utf-8-sig")
    x_fit, y_fit = apply_clip(fit_frame, bounds), fit_frame["Label"].to_numpy()
    test = splits["test"]
    x_test, y_test = apply_clip(test, bounds), test["Label"].to_numpy()

    metric_rows, prediction_frames, roc_rows, importance_rows = [], [], [], []
    model_metadata = {}
    for model_index, (model_name, choice) in enumerate(selected.items()):
        fitted = clone(choice["estimator"]).fit(x_fit, y_fit)
        probability = fitted.predict_proba(x_test)[:, 1]
        result = metric_row(y_test, probability)
        result["mean_monthly_auc"] = mean_monthly_auc(y_test, probability, test["Date"])
        low, high = moving_block_bootstrap_auc(y_test, probability, test["Date"], seed=RANDOM_SEED + model_index)
        result["auc_ci_low"], result["auc_ci_high"] = low, high
        metric_rows.append({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "selected_candidate": choice["candidate"],
            "selection_score_mean_auc": choice["selection_score"],
            **result,
        })

        prediction = test[["Date", "Symbol", "Name", "Label", "future_return_20d"]].copy()
        prediction["model"], prediction["model_label"] = model_name, MODEL_LABELS[model_name]
        prediction["probability"] = probability
        prediction["prediction"] = (probability >= 0.5).astype(int)
        prediction_frames.append(prediction)

        fpr, tpr, thresholds = roc_curve(y_test, probability)
        thresholds = np.where(np.isfinite(thresholds), thresholds, 1.0)
        roc_rows.extend({"model": model_name, "model_label": MODEL_LABELS[model_name], "fpr": float(a), "tpr": float(b), "threshold": float(c), "auc": result["auc"]} for a, b, c in zip(fpr, tpr, thresholds))

        values = importance_values(model_name, fitted)
        importance_rows.extend({"model": model_name, "model_label": MODEL_LABELS[model_name], "feature": feature, "importance": float(value), "absolute_importance": float(abs(value)), "importance_type": "standardized_coefficient" if model_name == "logistic_regression" else "impurity_importance"} for feature, value in zip(FEATURE_COLUMNS, values))

        model_path = MODEL_DIR / f"{model_name}.joblib"
        joblib.dump({"model": fitted, "features": FEATURE_COLUMNS, "clip_bounds": bounds, "threshold": 0.5, "target": "future_20d_absolute_direction"}, model_path)
        model_metadata[model_name] = {
            "selected_candidate": choice["candidate"],
            "parameters": choice["parameters"],
            "selection_score_mean_auc": choice["selection_score"],
            "model_file": model_path.name,
            "model_sha256": sha256_file(model_path),
        }
        print(f"[test-once] {MODEL_LABELS[model_name]} AUC={result['auc']:.4f}, 95% block CI=[{low:.4f}, {high:.4f}]")

    baseline_probability = float(y_fit.mean())
    baseline = np.full(len(y_test), baseline_probability)
    baseline_result = metric_row(y_test, baseline)
    baseline_result.update({"mean_monthly_auc": 0.5, "auc_ci_low": 0.5, "auc_ci_high": 0.5})
    metric_rows.append({
        "model": "constant_baseline",
        "model_label": MODEL_LABELS["constant_baseline"],
        "selected_candidate": "2018-2024 positive prevalence",
        "selection_score_mean_auc": 0.5,
        **baseline_result,
    })

    metrics_path = PROCESSED_DIR / "task5_experiment2_model_metrics.csv"
    predictions_path = PROCESSED_DIR / "task5_experiment2_test_predictions.csv"
    pd.DataFrame(metric_rows).to_csv(metrics_path, index=False, encoding="utf-8-sig")
    pd.concat(prediction_frames, ignore_index=True).to_csv(predictions_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    pd.DataFrame(roc_rows).to_csv(PROCESSED_DIR / "task5_experiment2_roc_points.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(importance_rows).to_csv(PROCESSED_DIR / "task5_experiment2_feature_importance.csv", index=False, encoding="utf-8-sig")

    run_metadata = {
        "created_at": datetime.now().astimezone().isoformat(),
        "experiment": "Task5 experiment 2",
        "random_seed": RANDOM_SEED,
        "target": "future 20-trading-day absolute return greater than zero",
        "selection_rule": "highest mean AUC over 2023 validation and 2024 development; minimum period AUC breaks ties",
        "selection_fit_period": "2018-02 through 2022-11",
        "refit_rule": "selected candidates refitted on 2018-2024; 2025 evaluated once",
        "winsorization": "0.5% and 99.5% bounds learned only from the applicable fit sample",
        "auc_uncertainty": "95% moving-block bootstrap by month-end date, 3-month blocks, 1000 repetitions",
        "classification_threshold": 0.5,
        "feature_columns": FEATURE_COLUMNS,
        "fit_rows": int(len(fit_frame)), "test_rows": int(len(test)),
        "test_positive_rate": float(y_test.mean()), "constant_baseline_probability": baseline_probability,
        "selected_models": model_metadata,
        "dataset_sha256": sha256_file(dataset_path), "metrics_sha256": sha256_file(metrics_path), "predictions_sha256": sha256_file(predictions_path),
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "scikit_learn": sklearn.__version__},
    }
    write_json(METADATA_DIR / "model_run.json", run_metadata)
    print(pd.DataFrame(metric_rows)[["model_label", "auc", "auc_ci_low", "auc_ci_high", "accuracy", "f1"]].to_string(index=False))


if __name__ == "__main__":
    main()
