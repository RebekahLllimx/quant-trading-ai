#!/usr/bin/env python3
"""Reusable analysis functions for the TASK5 CATL classification case."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss,
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score, roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from statsmodels.stats.outliers_influence import variance_inflation_factor


ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / "data" / "task5" / "catl"
RAW_DIR = CASE_DIR / "raw"
PROCESSED_DIR = CASE_DIR / "processed"
RESULT_DIR = CASE_DIR / "results"
MODEL_DIR = ROOT / "artifacts" / "models" / "task5" / "catl"
SEED = 42
HORIZON = 20

FEATURES = [
    "return_1d", "return_5d", "return_10d", "return_20d",
    "ma5_gap", "ma20_gap", "ma60_gap", "rsi14", "macd_pct",
    "atr14_pct", "volatility20", "intraday_range", "open_close_return",
    "volume_ratio20", "amount_ratio20", "excess_return_5d",
    "excess_return_20d", "benchmark_return_20d",
    "benchmark_volatility20", "beta60",
]

FEATURE_NAMES = {
    "return_1d": "1日收益", "return_5d": "5日收益", "return_10d": "10日收益",
    "return_20d": "20日收益", "ma5_gap": "5日均线偏离", "ma20_gap": "20日均线偏离",
    "ma60_gap": "60日均线偏离", "rsi14": "RSI(14)", "macd_pct": "MACD/价格",
    "atr14_pct": "ATR(14)/价格", "volatility20": "20日波动率", "intraday_range": "日内振幅",
    "open_close_return": "开收盘收益", "volume_ratio20": "20日量比", "amount_ratio20": "20日额比",
    "excess_return_5d": "5日超额收益", "excess_return_20d": "20日超额收益",
    "benchmark_return_20d": "沪深300 20日收益", "benchmark_volatility20": "沪深300 20日波动率",
    "beta60": "60日贝塔",
}

MODEL_NAMES = {
    "logistic_regression": "逻辑回归", "decision_tree": "决策树",
    "random_forest": "随机森林", "gradient_boosting": "梯度提升",
}


class QuantileClipper(BaseEstimator, TransformerMixin):
    """Clip each column using quantiles learned from the training fold only."""

    def __init__(self, lower: float = 0.01, upper: float = 0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):
        arr = np.asarray(X, dtype=float)
        self.lower_bounds_ = np.nanquantile(arr, self.lower, axis=0)
        self.upper_bounds_ = np.nanquantile(arr, self.upper, axis=0)
        return self

    def transform(self, X):
        return np.clip(np.asarray(X, dtype=float), self.lower_bounds_, self.upper_bounds_)


def ensure_dirs() -> None:
    for path in (PROCESSED_DIR, RESULT_DIR, MODEL_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_daily() -> pd.DataFrame:
    stock = pd.read_csv(RAW_DIR / "300750_SZ.csv", parse_dates=["Date"])
    benchmark = pd.read_csv(RAW_DIR / "000300_SH.csv", parse_dates=["Date"])
    merged = stock.merge(benchmark, on="Date", suffixes=("_stock", "_benchmark"), validate="one_to_one")
    return merged.sort_values("Date").reset_index(drop=True)


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def build_samples(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = daily.copy()
    sclose = d["Close_stock"]
    bclose = d["Close_benchmark"]
    sret1 = sclose.pct_change()
    bret1 = bclose.pct_change()

    for k in (1, 5, 10, 20):
        d[f"return_{k}d"] = sclose.pct_change(k)
    for k in (5, 20, 60):
        d[f"ma{k}_gap"] = sclose / sclose.rolling(k, min_periods=k).mean() - 1
    d["rsi14"] = _rsi(sclose)
    ema12 = sclose.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = sclose.ewm(span=26, adjust=False, min_periods=26).mean()
    d["macd_pct"] = (ema12 - ema26) / sclose

    previous = sclose.shift(1)
    true_range = pd.concat([
        d["High_stock"] - d["Low_stock"],
        (d["High_stock"] - previous).abs(),
        (d["Low_stock"] - previous).abs(),
    ], axis=1).max(axis=1)
    d["atr14_pct"] = true_range.rolling(14, min_periods=14).mean() / sclose
    d["volatility20"] = sret1.rolling(20, min_periods=20).std()
    d["intraday_range"] = (d["High_stock"] - d["Low_stock"]) / sclose
    d["open_close_return"] = d["Close_stock"] / d["Open_stock"] - 1
    d["volume_ratio20"] = d["Volume_stock"] / d["Volume_stock"].rolling(20, min_periods=20).mean()
    d["amount_ratio20"] = d["Amount_stock"] / d["Amount_stock"].rolling(20, min_periods=20).mean()

    d["excess_return_5d"] = sclose.pct_change(5) - bclose.pct_change(5)
    d["excess_return_20d"] = sclose.pct_change(20) - bclose.pct_change(20)
    d["benchmark_return_20d"] = bclose.pct_change(20)
    d["benchmark_volatility20"] = bret1.rolling(20, min_periods=20).std()
    d["beta60"] = sret1.rolling(60, min_periods=60).cov(bret1) / bret1.rolling(60, min_periods=60).var()

    d["stock_future_20d"] = sclose.shift(-HORIZON) / sclose - 1
    d["benchmark_future_20d"] = bclose.shift(-HORIZON) / bclose - 1
    d["future_excess_20d"] = d["stock_future_20d"] - d["benchmark_future_20d"]
    d["label_end_date"] = d["Date"].shift(-HORIZON)
    d["target"] = (d["future_excess_20d"] > 0).astype("Int64")
    d.loc[d["future_excess_20d"].isna(), "target"] = pd.NA

    d["week"] = d["Date"].dt.to_period("W-FRI")
    weekly = d.groupby("week", observed=True).tail(1).copy()
    weekly = weekly.dropna(subset=FEATURES + ["target", "label_end_date"]).reset_index(drop=True)
    weekly["target"] = weekly["target"].astype(int)
    weekly["year"] = weekly["Date"].dt.year
    weekly["split"] = np.where(weekly["Date"] < "2025-01-01", "development", "test")
    return d, weekly


def rolling_folds(samples: pd.DataFrame) -> list[tuple[int, np.ndarray, np.ndarray]]:
    folds = []
    for year in (2021, 2022, 2023, 2024):
        cutoff = pd.Timestamp(f"{year}-01-01")
        train = (samples["Date"] < cutoff) & (samples["label_end_date"] < cutoff)
        valid = samples["year"].eq(year)
        folds.append((year, train.to_numpy(), valid.to_numpy()))
    return folds


def make_pipeline(model_key: str, params: dict | None = None) -> Pipeline:
    params = dict(params or {})
    steps = [("clip", QuantileClipper()), ("impute", SimpleImputer(strategy="median"))]
    if model_key == "logistic_regression":
        steps.extend([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=3000, random_state=SEED, **params)),
        ])
    elif model_key == "decision_tree":
        steps.append(("model", DecisionTreeClassifier(random_state=SEED, **params)))
    elif model_key == "random_forest":
        steps.append(("model", RandomForestClassifier(
            n_estimators=400, random_state=SEED, n_jobs=-1, class_weight="balanced_subsample", **params
        )))
    elif model_key == "gradient_boosting":
        steps.append(("model", GradientBoostingClassifier(random_state=SEED, **params)))
    else:
        raise KeyError(model_key)
    return Pipeline(steps)


def univariate_audit(samples: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, yearly = [], []
    for feature in FEATURES:
        aucs = []
        for year, train_mask, valid_mask in rolling_folds(samples):
            pipe = make_pipeline("logistic_regression", {"C": 0.3})
            pipe.fit(samples.loc[train_mask, [feature]], samples.loc[train_mask, "target"])
            prob = pipe.predict_proba(samples.loc[valid_mask, [feature]])[:, 1]
            auc = roc_auc_score(samples.loc[valid_mask, "target"], prob)
            coefficient = float(pipe.named_steps["model"].coef_[0, 0])
            aucs.append(auc)
            yearly.append({
                "feature": feature, "feature_cn": FEATURE_NAMES[feature], "validation_year": year,
                "auc": auc, "training_direction": int(np.sign(coefficient)),
                "validation_above_random": bool(auc > 0.5),
            })
        rows.append({
            "feature": feature, "feature_cn": FEATURE_NAMES[feature], "mean_auc": np.mean(aucs),
            "std_auc": np.std(aucs, ddof=1), "min_auc": np.min(aucs), "max_auc": np.max(aucs),
            "years_above_0_5": int(np.sum(np.asarray(aucs) > 0.5)),
        })
    return (
        pd.DataFrame(rows).sort_values(["mean_auc", "years_above_0_5"], ascending=False).reset_index(drop=True),
        pd.DataFrame(yearly),
    )


def select_features(samples: pd.DataFrame, audit: pd.DataFrame, max_features: int = 8) -> tuple[list[str], pd.DataFrame, pd.DataFrame]:
    development = samples[samples["Date"] < "2025-01-01"]
    corr = development[FEATURES].corr()
    selected, decisions = [], []
    for row in audit.itertuples(index=False):
        feature = row.feature
        blockers = [chosen for chosen in selected if abs(corr.loc[feature, chosen]) >= 0.80]
        stable_enough = row.years_above_0_5 >= 2
        if not stable_enough:
            reason = "滚动验证中少于2年AUC高于0.5"
            keep = False
        elif blockers:
            reason = f"与已保留 {blockers[0]} 高相关"
            keep = False
        elif len(selected) >= max_features:
            reason = f"超过{max_features}个特征的预设复杂度上限"
            keep = False
        else:
            selected.append(feature)
            reason = "通过滚动验证与相关性去冗余"
            keep = True
        decisions.append({"feature": feature, "feature_cn": FEATURE_NAMES[feature], "keep_initial": keep, "reason": reason})

    # Ensure a usable, still development-only set if the strict rule retains too few variables.
    if len(selected) < 4:
        for feature in audit["feature"]:
            if feature in selected:
                continue
            blockers = [chosen for chosen in selected if abs(corr.loc[feature, chosen]) >= 0.80]
            if not blockers:
                selected.append(feature)
                for item in decisions:
                    if item["feature"] == feature:
                        item["keep_initial"] = True
                        item["reason"] = "作为开发期排名靠前的低冗余备选变量保留"
                if len(selected) >= 4:
                    break

    vif_history = []
    while len(selected) > 2:
        matrix = development[selected].replace([np.inf, -np.inf], np.nan)
        matrix = matrix.fillna(matrix.median())
        matrix = (matrix - matrix.mean()) / matrix.std(ddof=0).replace(0, 1)
        vifs = pd.Series(
            [variance_inflation_factor(matrix.values, i) for i in range(matrix.shape[1])], index=selected
        )
        vif_history.extend({"iteration": len(vif_history), "feature": f, "vif": float(v)} for f, v in vifs.items())
        if float(vifs.max()) < 5:
            break
        removed = str(vifs.idxmax())
        selected.remove(removed)
        for item in decisions:
            if item["feature"] == removed:
                item["keep_initial"] = False
                item["reason"] = f"VIF={vifs[removed]:.2f}超过5，迭代删除"

    decision_df = pd.DataFrame(decisions)
    decision_df["selected_final"] = decision_df["feature"].isin(selected)
    final_matrix = development[selected].fillna(development[selected].median())
    final_matrix = (final_matrix - final_matrix.mean()) / final_matrix.std(ddof=0).replace(0, 1)
    final_vif = pd.DataFrame({
        "feature": selected,
        "vif": [variance_inflation_factor(final_matrix.values, i) for i in range(final_matrix.shape[1])],
    })
    final_vif["feature_cn"] = final_vif["feature"].map(FEATURE_NAMES)
    return selected, decision_df, final_vif


PARAM_GRIDS = {
    "logistic_regression": [{"C": c} for c in (0.03, 0.1, 0.3, 1.0)],
    "decision_tree": [
        {"max_depth": d, "min_samples_leaf": leaf, "class_weight": "balanced"}
        for d, leaf in product((2, 3, 4), (8, 15))
    ],
    "random_forest": [
        {"max_depth": d, "min_samples_leaf": leaf, "max_features": "sqrt"}
        for d, leaf in product((3, 5, 7), (5, 10))
    ],
    "gradient_boosting": [
        {"n_estimators": n, "learning_rate": lr, "max_depth": d, "min_samples_leaf": 8}
        for n, lr, d in product((80, 150), (0.03, 0.05), (1, 2))
    ],
}


def tune_models(samples: pd.DataFrame, selected: list[str]) -> tuple[dict, pd.DataFrame]:
    best, records = {}, []
    for model_key, grid in PARAM_GRIDS.items():
        for params in grid:
            aucs = []
            for year, train_mask, valid_mask in rolling_folds(samples):
                model = make_pipeline(model_key, params)
                model.fit(samples.loc[train_mask, selected], samples.loc[train_mask, "target"])
                prob = model.predict_proba(samples.loc[valid_mask, selected])[:, 1]
                aucs.append(roc_auc_score(samples.loc[valid_mask, "target"], prob))
            records.append({
                "model": model_key, "model_cn": MODEL_NAMES[model_key], "params": json.dumps(params, ensure_ascii=False),
                "mean_validation_auc": float(np.mean(aucs)), "std_validation_auc": float(np.std(aucs, ddof=1)),
                **{f"auc_{year}": float(auc) for (year, _, _), auc in zip(rolling_folds(samples), aucs)},
            })
    tuning = pd.DataFrame(records)
    for model_key in PARAM_GRIDS:
        subset = tuning[tuning["model"] == model_key].sort_values(
            ["mean_validation_auc", "std_validation_auc"], ascending=[False, True]
        )
        best[model_key] = json.loads(subset.iloc[0]["params"])
    return best, tuning


def moving_block_auc_ci(y: np.ndarray, p: np.ndarray, block: int = 4, reps: int = 2000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    n = len(y)
    values = []
    starts = np.arange(n)
    for _ in range(reps):
        indices = []
        while len(indices) < n:
            start = int(rng.choice(starts))
            indices.extend((start + np.arange(block)) % n)
        idx = np.asarray(indices[:n])
        if np.unique(y[idx]).size == 2:
            values.append(roc_auc_score(y[idx], p[idx]))
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def evaluate_models(samples: pd.DataFrame, selected: list[str], best_params: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    cutoff = pd.Timestamp("2025-01-01")
    train_mask = (samples["Date"] < cutoff) & (samples["label_end_date"] < cutoff)
    test_mask = samples["Date"] >= cutoff
    y_test = samples.loc[test_mask, "target"].to_numpy()
    predictions, metrics, roc_rows, fitted = [], [], [], {}
    for model_key, params in best_params.items():
        model = make_pipeline(model_key, params)
        model.fit(samples.loc[train_mask, selected], samples.loc[train_mask, "target"])
        prob = model.predict_proba(samples.loc[test_mask, selected])[:, 1]
        pred = (prob >= 0.5).astype(int)
        auc = roc_auc_score(y_test, prob)
        low, high = moving_block_auc_ci(y_test, prob)
        tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
        metrics.append({
            "model": model_key, "model_cn": MODEL_NAMES[model_key], "roc_auc": auc,
            "auc_ci_low": low, "auc_ci_high": high, "pr_auc": average_precision_score(y_test, prob),
            "accuracy": accuracy_score(y_test, pred), "balanced_accuracy": balanced_accuracy_score(y_test, pred),
            "precision": precision_score(y_test, pred, zero_division=0), "recall": recall_score(y_test, pred, zero_division=0),
            "f1": f1_score(y_test, pred, zero_division=0), "brier": brier_score_loss(y_test, prob),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "params": json.dumps(params, ensure_ascii=False),
        })
        fpr, tpr, thresholds = roc_curve(y_test, prob)
        roc_rows.extend({"model": model_key, "fpr": a, "tpr": b, "threshold": c} for a, b, c in zip(fpr, tpr, thresholds))
        frame = pd.DataFrame({
            "Date": samples.loc[test_mask, "Date"].to_numpy(), "target": y_test,
            "future_excess_20d": samples.loc[test_mask, "future_excess_20d"].to_numpy(),
            "model": model_key, "probability": prob, "prediction": pred,
        })
        predictions.append(frame)
        fitted[model_key] = model
    return pd.DataFrame(metrics), pd.concat(predictions, ignore_index=True), pd.DataFrame(roc_rows), fitted


def grouped_descriptives(samples: pd.DataFrame) -> pd.DataFrame:
    development = samples[samples["Date"] < "2025-01-01"]
    rows = []
    for feature in FEATURES:
        a = development.loc[development["target"] == 0, feature]
        b = development.loc[development["target"] == 1, feature]
        pooled = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / max(len(a) + len(b) - 2, 1))
        raw_auc = roc_auc_score(development["target"], development[feature])
        rows.append({
            "feature": feature, "feature_cn": FEATURE_NAMES[feature],
            "y0_mean": a.mean(), "y1_mean": b.mean(), "y0_median": a.median(), "y1_median": b.median(),
            "y0_std": a.std(), "y1_std": b.std(), "standardized_mean_difference": (b.mean() - a.mean()) / pooled,
            "raw_univariate_auc": raw_auc, "direction_free_auc": max(raw_auc, 1 - raw_auc),
        })
    return pd.DataFrame(rows)


def explanation_tables(fitted: dict, selected: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    lr = fitted["logistic_regression"].named_steps["model"]
    coefficients = pd.DataFrame({"feature": selected, "coefficient": lr.coef_[0]})
    coefficients["feature_cn"] = coefficients["feature"].map(FEATURE_NAMES)
    rows = []
    for key in ("decision_tree", "random_forest", "gradient_boosting"):
        values = fitted[key].named_steps["model"].feature_importances_
        rows.extend({"model": key, "model_cn": MODEL_NAMES[key], "feature": f, "feature_cn": FEATURE_NAMES[f], "importance": v}
                    for f, v in zip(selected, values))
    return coefficients, pd.DataFrame(rows)


def pipeline_controls(samples: pd.DataFrame, selected: list[str]) -> dict:
    cutoff = pd.Timestamp("2025-01-01")
    train = (samples["Date"] < cutoff) & (samples["label_end_date"] < cutoff)
    test = samples["Date"] >= cutoff
    X_train, X_test = samples.loc[train, selected], samples.loc[test, selected]
    y_train, y_test = samples.loc[train, "target"].to_numpy(), samples.loc[test, "target"].to_numpy()
    base = make_pipeline("logistic_regression", {"C": 0.3})
    base.fit(X_train, y_train)
    p = base.predict_proba(X_test)[:, 1]
    sklearn_auc = roc_auc_score(y_test, p)
    ranks = rankdata(p)
    n1, n0 = int(y_test.sum()), int((1 - y_test).sum())
    mann_whitney_auc = (ranks[y_test == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

    rng = np.random.default_rng(SEED)
    permuted = []
    for _ in range(50):
        y_perm = rng.permutation(y_train)
        model = make_pipeline("logistic_regression", {"C": 0.3})
        model.fit(X_train, y_perm)
        permuted.append(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))

    feature = selected[0]
    train_median = float(X_train[feature].median())
    y_syn_train = (X_train[feature].fillna(train_median) > train_median).astype(int)
    y_syn_test = (X_test[feature].fillna(train_median) > train_median).astype(int)
    synthetic = make_pipeline("logistic_regression", {"C": 10.0})
    synthetic.fit(X_train, y_syn_train)
    syn_auc = roc_auc_score(y_syn_test, synthetic.predict_proba(X_test)[:, 1])
    return {
        "sklearn_auc": float(sklearn_auc), "mann_whitney_auc": float(mann_whitney_auc),
        "auc_formula_absolute_difference": float(abs(sklearn_auc - mann_whitney_auc)),
        "permuted_label_auc_mean": float(np.mean(permuted)), "permuted_label_auc_std": float(np.std(permuted, ddof=1)),
        "synthetic_predictable_label_auc": float(syn_auc), "synthetic_feature": feature,
    }


@dataclass
class AnalysisBundle:
    daily: pd.DataFrame
    samples: pd.DataFrame
    audit: pd.DataFrame
    yearly_audit: pd.DataFrame
    selected: list[str]
    decisions: pd.DataFrame
    vif: pd.DataFrame
    best_params: dict
    tuning: pd.DataFrame
    metrics: pd.DataFrame
    predictions: pd.DataFrame
    roc_points: pd.DataFrame
    coefficients: pd.DataFrame
    importances: pd.DataFrame
    grouped: pd.DataFrame
    controls: dict


def run_and_save() -> AnalysisBundle:
    ensure_dirs()
    daily_raw = load_daily()
    daily, samples = build_samples(daily_raw)
    audit, yearly_audit = univariate_audit(samples)
    selected, decisions, vif = select_features(samples, audit)
    best_params, tuning = tune_models(samples, selected)
    metrics, predictions, roc_points, fitted = evaluate_models(samples, selected, best_params)
    coefficients, importances = explanation_tables(fitted, selected)
    grouped = grouped_descriptives(samples)
    controls = pipeline_controls(samples, selected)

    tables = {
        "daily_features.csv": daily,
        "weekly_samples.csv": samples,
        "univariate_audit.csv": audit,
        "univariate_yearly_auc.csv": yearly_audit,
        "feature_decisions.csv": decisions,
        "final_vif.csv": vif,
        "model_tuning.csv": tuning,
        "model_metrics.csv": metrics,
        "test_predictions.csv": predictions,
        "roc_points.csv": roc_points,
        "logistic_coefficients.csv": coefficients,
        "tree_importances.csv": importances,
        "grouped_descriptives.csv": grouped,
    }
    for name, frame in tables.items():
        target = PROCESSED_DIR / name if name in {"daily_features.csv", "weekly_samples.csv"} else RESULT_DIR / name
        frame.to_csv(target, index=False, encoding="utf-8-sig")
    for key, model in fitted.items():
        with (MODEL_DIR / f"{key}.pkl").open("wb") as handle:
            pickle.dump(model, handle)

    summary = {
        "daily_rows": len(daily_raw), "weekly_samples": len(samples),
        "development_samples": int((samples["Date"] < "2025-01-01").sum()),
        "final_train_samples_after_purge": int(((samples["Date"] < "2025-01-01") & (samples["label_end_date"] < "2025-01-01")).sum()),
        "test_samples": int((samples["Date"] >= "2025-01-01").sum()),
        "approx_independent_20d_windows": float((samples["Date"].max() - samples["Date"].min()).days / 365.25 * 252 / 20),
        "positive_rate_overall": float(samples["target"].mean()),
        "positive_rate_test": float(samples.loc[samples["Date"] >= "2025-01-01", "target"].mean()),
        "selected_features": selected, "best_params": best_params, "controls": controls,
        "best_test_model": metrics.sort_values("roc_auc", ascending=False).iloc[0]["model"],
        "best_test_auc": float(metrics["roc_auc"].max()),
    }
    (RESULT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return AnalysisBundle(
        daily, samples, audit, yearly_audit, selected, decisions, vif, best_params, tuning,
        metrics, predictions, roc_points, coefficients, importances, grouped, controls,
    )


if __name__ == "__main__":
    bundle = run_and_save()
    print((RESULT_DIR / "summary.json").read_text(encoding="utf-8"))
    print(bundle.metrics.sort_values("roc_auc", ascending=False).to_string(index=False))
