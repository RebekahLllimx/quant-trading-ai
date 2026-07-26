#!/usr/bin/env python3
"""Breast-cancer classification analysis used by the formal TASK5 notebook."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from statsmodels.stats.outliers_influence import variance_inflation_factor


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "task5" / "breast_cancer"
RESULT_DIR = DATA_DIR / "results"
MODEL_DIR = ROOT / "artifacts" / "models" / "task5" / "breast_cancer"
SEED = 42

MODEL_NAMES = {
    "logistic_regression": "逻辑回归",
    "decision_tree": "决策树",
    "random_forest": "随机森林",
    "gradient_boosting": "梯度提升",
}

FEATURE_NAMES = {
    "mean radius": "平均半径", "mean texture": "平均纹理", "mean perimeter": "平均周长",
    "mean area": "平均面积", "mean smoothness": "平均光滑度", "mean compactness": "平均紧密度",
    "mean concavity": "平均凹度", "mean concave points": "平均凹点数", "mean symmetry": "平均对称度",
    "mean fractal dimension": "平均分形维数", "radius error": "半径标准误", "texture error": "纹理标准误",
    "perimeter error": "周长标准误", "area error": "面积标准误", "smoothness error": "光滑度标准误",
    "compactness error": "紧密度标准误", "concavity error": "凹度标准误",
    "concave points error": "凹点数标准误", "symmetry error": "对称度标准误",
    "fractal dimension error": "分形维数标准误", "worst radius": "较大值半径",
    "worst texture": "较大值纹理", "worst perimeter": "较大值周长", "worst area": "较大值面积",
    "worst smoothness": "较大值光滑度", "worst compactness": "较大值紧密度",
    "worst concavity": "较大值凹度", "worst concave points": "较大值凹点数",
    "worst symmetry": "较大值对称度", "worst fractal dimension": "较大值分形维数",
}


@dataclass
class Bundle:
    data: pd.DataFrame
    train: pd.DataFrame
    test: pd.DataFrame
    quality: pd.DataFrame
    descriptives: pd.DataFrame
    grouped: pd.DataFrame
    audit: pd.DataFrame
    decisions: pd.DataFrame
    vif: pd.DataFrame
    selected: list[str]
    tuning: pd.DataFrame
    metrics: pd.DataFrame
    predictions: pd.DataFrame
    roc_points: pd.DataFrame
    coefficients: pd.DataFrame
    importances: pd.DataFrame
    controls: dict
    models: dict


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data() -> pd.DataFrame:
    bunch = load_breast_cancer(as_frame=True)
    frame = bunch.data.copy()
    # sklearn encodes malignant=0 and benign=1. Recode so the clinically
    # consequential class is the positive class throughout the report.
    frame["target"] = (bunch.target == 0).astype(int)
    frame["diagnosis"] = frame["target"].map({0: "良性", 1: "恶性"})
    frame.insert(0, "sample_id", np.arange(1, len(frame) + 1))
    return frame


def split_data(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_idx, test_idx = train_test_split(
        np.arange(len(data)), test_size=0.20, random_state=SEED, stratify=data["target"]
    )
    train = data.iloc[np.sort(train_idx)].copy()
    test = data.iloc[np.sort(test_idx)].copy()
    train["split"] = "训练集"
    test["split"] = "测试集"
    return train, test


def data_quality(data: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    return pd.DataFrame([
        {"检查": "样本数", "结果": len(data), "通过": len(data) == 569},
        {"检查": "数值特征数", "结果": len(features), "通过": len(features) == 30},
        {"检查": "必需字段缺失单元格", "结果": int(data[features + ["target"]].isna().sum().sum()), "通过": not data[features + ["target"]].isna().any().any()},
        {"检查": "完全重复的特征行", "结果": int(data[features].duplicated().sum()), "通过": not data[features].duplicated().any()},
        {"检查": "标签取值", "结果": str(sorted(data["target"].unique().tolist())), "通过": set(data["target"]) == {0, 1}},
        {"检查": "样本编号唯一", "结果": int(data["sample_id"].nunique()), "通过": data["sample_id"].is_unique},
    ])


def describe_features(data: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    desc = data[features].describe().T.reset_index().rename(columns={
        "index": "feature", "count": "样本数", "mean": "均值", "std": "标准差",
        "min": "最小值", "25%": "25%", "50%": "中位数", "75%": "75%", "max": "最大值",
    })
    desc.insert(1, "feature_cn", desc["feature"].map(FEATURE_NAMES))
    return desc


def grouped_audit(train: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Audit univariate separation and its stability using training data only."""
    rows = []
    y = train["target"].to_numpy()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    for feature in features:
        benign = train.loc[train.target == 0, feature]
        malignant = train.loc[train.target == 1, feature]
        pooled_sd = np.sqrt(((len(benign) - 1) * benign.var(ddof=1) + (len(malignant) - 1) * malignant.var(ddof=1)) / (len(train) - 2))
        raw_auc = roc_auc_score(y, train[feature])
        global_direction = 1 if raw_auc >= 0.5 else -1
        fold_aucs, fold_directions = [], []
        values = train[feature].to_numpy()
        for fit_idx, validation_idx in cv.split(values, y):
            fit_auc = roc_auc_score(y[fit_idx], values[fit_idx])
            direction = 1 if fit_auc >= 0.5 else -1
            validation_auc = roc_auc_score(y[validation_idx], values[validation_idx] * direction)
            fold_aucs.append(validation_auc)
            fold_directions.append(direction)
        rows.append({
            "feature": feature,
            "feature_cn": FEATURE_NAMES[feature],
            "benign_mean": benign.mean(),
            "malignant_mean": malignant.mean(),
            "standardized_mean_difference": (malignant.mean() - benign.mean()) / pooled_sd,
            "raw_auc": raw_auc,
            "direction_free_auc": max(raw_auc, 1 - raw_auc),
            "cv_auc_mean": float(np.mean(fold_aucs)),
            "cv_auc_std": float(np.std(fold_aucs, ddof=1)),
            "cv_auc_min": float(np.min(fold_aucs)),
            "direction_consistency": float(np.mean(np.asarray(fold_directions) == global_direction)),
            "direction": "值越大越偏恶性" if raw_auc >= 0.5 else "值越小越偏恶性",
        })
    return pd.DataFrame(rows).sort_values(
        ["cv_auc_mean", "direction_consistency", "direction_free_auc"], ascending=False
    ).reset_index(drop=True)


def select_features(train: pd.DataFrame, grouped: pd.DataFrame, max_features: int = 8) -> tuple[list[str], pd.DataFrame, pd.DataFrame]:
    features = grouped["feature"].tolist()
    corr = train[features].corr()
    selected: list[str] = []
    decisions = []
    for row in grouped.itertuples(index=False):
        blockers = [chosen for chosen in selected if abs(corr.loc[row.feature, chosen]) >= 0.90]
        if blockers:
            keep = False
            reason = f"与已保留的{FEATURE_NAMES[blockers[0]]}高度相关"
        elif len(selected) >= max_features:
            keep = False
            reason = f"超过预设的{max_features}项复杂度上限"
        else:
            keep = True
            selected.append(row.feature)
            reason = "五折区分度和方向稳定性靠前，且未与已选变量高度重复"
        decisions.append({"feature": row.feature, "feature_cn": row.feature_cn, "keep_initial": keep, "reason": reason})

    # VIF is evaluated on the training set only. Iteratively remove the largest
    # value until conventional multicollinearity risk is below five.
    while len(selected) > 3:
        matrix = StandardScaler().fit_transform(train[selected])
        vifs = pd.Series([variance_inflation_factor(matrix, i) for i in range(matrix.shape[1])], index=selected)
        if float(vifs.max()) < 5:
            break
        removed = str(vifs.idxmax())
        selected.remove(removed)
        for item in decisions:
            if item["feature"] == removed:
                item["keep_initial"] = False
                item["reason"] = f"训练集VIF={vifs[removed]:.2f}，迭代删除"

    final_matrix = StandardScaler().fit_transform(train[selected])
    final_vif = pd.DataFrame({
        "feature": selected,
        "vif": [variance_inflation_factor(final_matrix, i) for i in range(final_matrix.shape[1])],
    })
    final_vif["feature_cn"] = final_vif["feature"].map(FEATURE_NAMES)
    decision_frame = pd.DataFrame(decisions)
    decision_frame["selected_final"] = decision_frame["feature"].isin(selected)
    return selected, decision_frame, final_vif


def make_models(selected: list[str]) -> dict[str, tuple[Pipeline, dict]]:
    scaled = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=5000, random_state=SEED)),
    ])
    tree = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", DecisionTreeClassifier(random_state=SEED)),
    ])
    forest = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(n_estimators=500, random_state=SEED, n_jobs=-1)),
    ])
    boosting = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", GradientBoostingClassifier(random_state=SEED)),
    ])
    return {
        "logistic_regression": (scaled, {
            "model__C": [0.1, 1.0, 10.0], "model__class_weight": [None, "balanced"],
        }),
        "decision_tree": (tree, {
            "model__max_depth": [2, 3, 4, 5], "model__min_samples_leaf": [5, 10, 15],
            "model__class_weight": [None, "balanced"],
        }),
        "random_forest": (forest, {
            "model__max_depth": [3, 5, None], "model__min_samples_leaf": [2, 5, 10],
            "model__max_features": ["sqrt"], "model__class_weight": [None, "balanced_subsample"],
        }),
        "gradient_boosting": (boosting, {
            "model__n_estimators": [80, 120], "model__learning_rate": [0.03, 0.05, 0.10],
            "model__max_depth": [1, 2], "model__min_samples_leaf": [5, 10],
        }),
    }


def bootstrap_auc(y: np.ndarray, probability: np.ndarray, iterations: int = 2000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    values = []
    for _ in range(iterations):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        values.append(roc_auc_score(y[idx], probability[idx]))
    return tuple(np.quantile(values, [0.025, 0.975]))


def train_and_evaluate(train: pd.DataFrame, test: pd.DataFrame, selected: list[str]) -> tuple:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    y_train = train["target"].to_numpy()
    y_test = test["target"].to_numpy()
    tuning_rows, metric_rows, prediction_rows, roc_rows = [], [], [], []
    coefficients, importance_rows, fitted = [], [], {}

    for key, (pipeline, grid) in make_models(selected).items():
        # Single-process tuning keeps notebook output deterministic and avoids
        # child-process dependency warnings leaking into the exported report.
        search = GridSearchCV(pipeline, grid, scoring="roc_auc", cv=cv, n_jobs=1, refit=True, return_train_score=False)
        search.fit(train[selected], y_train)
        model = search.best_estimator_
        probability = model.predict_proba(test[selected])[:, 1]
        predicted = (probability >= 0.5).astype(int)
        low, high = bootstrap_auc(y_test, probability)
        tn, fp, fn, tp = confusion_matrix(y_test, predicted, labels=[0, 1]).ravel()
        specificity = tn / (tn + fp)
        metric_rows.append({
            "model": key, "model_cn": MODEL_NAMES[key], "roc_auc": roc_auc_score(y_test, probability),
            "auc_ci_low": low, "auc_ci_high": high, "pr_auc": average_precision_score(y_test, probability),
            "accuracy": accuracy_score(y_test, predicted), "balanced_accuracy": balanced_accuracy_score(y_test, predicted),
            "precision": precision_score(y_test, predicted, zero_division=0), "recall": recall_score(y_test, predicted, zero_division=0),
            "specificity": specificity, "f1": f1_score(y_test, predicted, zero_division=0),
            "brier": brier_score_loss(y_test, probability), "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        })
        best_index = int(search.best_index_)
        tuning_rows.append({
            "model": key, "model_cn": MODEL_NAMES[key], "best_params": json.dumps(search.best_params_, ensure_ascii=False, sort_keys=True),
            "cv_auc_mean": float(search.cv_results_["mean_test_score"][best_index]),
            "cv_auc_std": float(search.cv_results_["std_test_score"][best_index]),
            "candidate_count": len(search.cv_results_["params"]),
        })
        for sample_id, actual, prob, pred in zip(test["sample_id"], y_test, probability, predicted):
            prediction_rows.append({"sample_id": sample_id, "target": actual, "model": key, "probability": prob, "predicted": pred})
        fpr, tpr, thresholds = roc_curve(y_test, probability)
        for a, b, threshold in zip(fpr, tpr, thresholds):
            roc_rows.append({"model": key, "model_cn": MODEL_NAMES[key], "fpr": a, "tpr": b, "threshold": threshold})

        estimator = model.named_steps["model"]
        if key == "logistic_regression":
            for feature, value in zip(selected, estimator.coef_[0]):
                coefficients.append({"feature": feature, "feature_cn": FEATURE_NAMES[feature], "coefficient": value})
        else:
            for feature, value in zip(selected, estimator.feature_importances_):
                importance_rows.append({"model": key, "model_cn": MODEL_NAMES[key], "feature": feature, "feature_cn": FEATURE_NAMES[feature], "importance": value})
        fitted[key] = model

    return (
        pd.DataFrame(tuning_rows), pd.DataFrame(metric_rows), pd.DataFrame(prediction_rows),
        pd.DataFrame(roc_rows), pd.DataFrame(coefficients), pd.DataFrame(importance_rows), fitted,
    )


def pipeline_controls(train: pd.DataFrame, test: pd.DataFrame, selected: list[str], fitted: dict) -> dict:
    y_test = test["target"].to_numpy()
    probability = fitted["logistic_regression"].predict_proba(test[selected])[:, 1]
    sklearn_auc = roc_auc_score(y_test, probability)
    ranks = pd.Series(probability).rank(method="average").to_numpy()
    n1, n0 = int(y_test.sum()), int((1 - y_test).sum())
    mann_whitney = (ranks[y_test == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

    rng = np.random.default_rng(SEED)
    permuted_auc = []
    base = clone(fitted["logistic_regression"])
    for _ in range(500):
        base.fit(train[selected], rng.permutation(train["target"].to_numpy()))
        permuted_auc.append(roc_auc_score(y_test, base.predict_proba(test[selected])[:, 1]))
    return {
        "sklearn_auc": float(sklearn_auc),
        "mann_whitney_auc": float(mann_whitney),
        "auc_formula_absolute_difference": float(abs(sklearn_auc - mann_whitney)),
        "permuted_label_auc_mean": float(np.mean(permuted_auc)),
        "permuted_label_auc_std": float(np.std(permuted_auc, ddof=1)),
        "train_test_sample_overlap": int(len(set(train.sample_id) & set(test.sample_id))),
    }


def run_and_save() -> Bundle:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()
    features = list(load_breast_cancer().feature_names)
    train, test = split_data(data)
    quality = data_quality(data, features)
    descriptives = describe_features(train, features)
    grouped = grouped_audit(train, features)
    selected, decisions, vif = select_features(train, grouped)
    tuning, metrics, predictions, roc_points, coefficients, importances, models = train_and_evaluate(train, test, selected)
    controls = pipeline_controls(train, test, selected, models)

    full = pd.concat([train, test]).sort_values("sample_id")
    outputs = {
        "dataset.csv": full,
        "data_quality.csv": quality,
        "descriptive_statistics.csv": descriptives,
        "grouped_feature_audit.csv": grouped,
        "feature_decisions.csv": decisions,
        "final_vif.csv": vif,
        "model_tuning.csv": tuning,
        "model_metrics.csv": metrics,
        "test_predictions.csv": predictions,
        "roc_points.csv": roc_points,
        "logistic_coefficients.csv": coefficients,
        "tree_importances.csv": importances,
    }
    for filename, frame in outputs.items():
        frame.to_csv(RESULT_DIR / filename, index=False, encoding="utf-8-sig")
    for key, model in models.items():
        joblib.dump(model, MODEL_DIR / f"{key}.pkl")

    summary = {
        "source": "scikit-learn load_breast_cancer",
        "samples": len(data), "features": len(features), "positive_class": "恶性",
        "positive_rate": float(data.target.mean()), "train_samples": len(train), "test_samples": len(test),
        "train_positive_rate": float(train.target.mean()), "test_positive_rate": float(test.target.mean()),
        "selected_features": selected,
        "best_model": metrics.loc[metrics.roc_auc.idxmax(), "model"],
        "best_auc": float(metrics.roc_auc.max()),
        "controls": controls,
    }
    (RESULT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "source": "scikit-learn.datasets.load_breast_cancer",
        "sklearn_target_original": {"0": "malignant", "1": "benign"},
        "report_target": {"0": "benign", "1": "malignant"},
        "split": {"method": "stratified 80/20 holdout", "random_state": SEED},
        "dataset_sha256": sha256(RESULT_DIR / "dataset.csv"),
    }
    (RESULT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return Bundle(
        data=data, train=train, test=test, quality=quality, descriptives=descriptives, grouped=grouped,
        audit=grouped, decisions=decisions, vif=vif, selected=selected, tuning=tuning, metrics=metrics,
        predictions=predictions, roc_points=roc_points, coefficients=coefficients, importances=importances,
        controls=controls, models=models,
    )


if __name__ == "__main__":
    bundle = run_and_save()
    print("Selected:", bundle.selected)
    print(bundle.tuning.to_string(index=False))
    print(bundle.metrics.sort_values("roc_auc", ascending=False).to_string(index=False))
