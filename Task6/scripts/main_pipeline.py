#!/usr/bin/env python3
"""Leak-aware quarterly cross-sectional return ranking and Top-30 backtest."""

from __future__ import annotations

import json
import platform
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_absolute_error, mean_squared_error, r2_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from task6_common import (
    BUFFER_RANK,
    MAIN_METADATA_DIR,
    MAIN_MODEL_DIR,
    MAIN_PROCESSED_DIR,
    MODEL_LABELS,
    ONE_WAY_COST,
    RANDOM_SEED,
    SOURCE_DIR,
    TOP_N,
    ensure_directories,
    project_relative,
    quarterly_performance,
    safe_spearman,
    sha256_file,
    write_json,
)


SOURCE_FILE = SOURCE_DIR / "model_data.csv"
TARGET = "Next_Ret"
RANK_TARGET = "Next_Ret_Rank"
CLASS_TARGET = "Above_Quarter_Median"
KEY_COLUMNS = ["Date", "Code"]
VALUE_FEATURES = [
    "企业倍数(EV除EBITDA)",
    "市净率PB(MRQ)",
    "市现率PCF(现金净流量TTM)",
    "市现率PCF(经营现金流TTM)",
    "市盈率PE(TTM)",
    "市盈率PE(TTM,扣除非经常性损益)",
    "市销率PS(TTM)",
]
GROWTH_FEATURES = [
    "净利润同比增长率",
    "净资产同比增长率",
    "利润总额(同比增长率)",
    "基本每股收益(同比增长率)",
    "总资产同比增长率",
    "现金净流量同比增长率",
    "经营活动产生的现金流量净额(同比增长率)",
    "营业利润(同比增长率)",
    "营业总收入(同比增长率)",
]
INCOME_GROWTH_FEATURES = [
    "净利润同比增长率",
    "利润总额(同比增长率)",
    "营业利润(同比增长率)",
    "营业总收入(同比增长率)",
]
CASHFLOW_FEATURES = [
    "现金净流量同比增长率",
    "经营活动产生的现金流量净额(同比增长率)",
]


def load_and_engineer() -> tuple[pd.DataFrame, list[str], list[str], dict]:
    frame = pd.read_csv(SOURCE_FILE, dtype={"Code": "string"})
    frame["Date"] = pd.to_datetime(frame["Date"], errors="raise")
    frame["Code"] = frame["Code"].str.zfill(6)
    raw_features = [column for column in frame.columns if column not in KEY_COLUMNS + [TARGET]]
    frame[raw_features + [TARGET]] = frame[raw_features + [TARGET]].apply(pd.to_numeric, errors="coerce")
    frame.replace([np.inf, -np.inf], np.nan, inplace=True)

    grouped = frame.groupby("Date", sort=True)
    rank_features = []
    for column in raw_features:
        derived = f"rank__{column}"
        frame[derived] = grouped[column].rank(pct=True, method="average") - 0.5
        rank_features.append(derived)

    frame["value_composite"] = -frame[[f"rank__{column}" for column in VALUE_FEATURES]].mean(axis=1)
    frame["growth_composite"] = frame[[f"rank__{column}" for column in GROWTH_FEATURES]].mean(axis=1)
    frame["income_growth_composite"] = frame[[f"rank__{column}" for column in INCOME_GROWTH_FEATURES]].mean(axis=1)
    frame["cashflow_composite"] = frame[[f"rank__{column}" for column in CASHFLOW_FEATURES]].mean(axis=1)
    composite_features = ["value_composite", "growth_composite", "income_growth_composite", "cashflow_composite"]
    model_features = rank_features + composite_features
    frame[RANK_TARGET] = grouped[TARGET].rank(pct=True, method="average") - 0.5
    frame[CLASS_TARGET] = (frame[TARGET] > grouped[TARGET].transform("median")).astype(int)

    quality = {
        "source_file": project_relative(SOURCE_FILE),
        "source_sha256": sha256_file(SOURCE_FILE),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "date_min": frame["Date"].min().date().isoformat(),
        "date_max": frame["Date"].max().date().isoformat(),
        "quarter_count": int(frame["Date"].nunique()),
        "stock_count": int(frame["Code"].nunique()),
        "duplicate_code_date_rows": int(frame.duplicated(KEY_COLUMNS).sum()),
        "missing_raw_cells": int(frame[raw_features + [TARGET]].isna().sum().sum()),
        "nonfinite_raw_cells": int((~np.isfinite(frame[raw_features + [TARGET]].to_numpy(dtype=float))).sum()),
        "target_summary": {key: float(value) for key, value in frame[TARGET].describe().items()},
        "rank_target_summary": {key: float(value) for key, value in frame[RANK_TARGET].describe().items()},
        "classification_positive_rate": float(frame[CLASS_TARGET].mean()),
        "rows_by_quarter": {str(date.date()): int(count) for date, count in frame.groupby("Date").size().items()},
        "important_caveat": "原始样本未提供财务报表实际披露日，因此无法独立验证所有季末财务因子在交易时点已可得。",
    }
    return frame, raw_features, model_features, quality


def model_candidates() -> dict[str, list[tuple[str, object, dict, str]]]:
    return {
        "linear_regression": [
            ("ordinary least squares", LinearRegression(), {}, "rank_regression"),
        ],
        "ridge": [
            (f"alpha={alpha:g}", Ridge(alpha=alpha), {"alpha": alpha}, "rank_regression")
            for alpha in (1.0, 10.0, 100.0)
        ],
        "logistic_regression": [
            (
                f"C={regularization:g}",
                make_pipeline(
                    StandardScaler(),
                    LogisticRegression(C=regularization, max_iter=2000, random_state=RANDOM_SEED),
                ),
                {"C": regularization},
                "classification",
            )
            for regularization in (0.01, 0.1, 1.0)
        ],
        "decision_tree": [
            (
                f"depth={depth},leaf={leaf}",
                DecisionTreeRegressor(max_depth=depth, min_samples_leaf=leaf, random_state=RANDOM_SEED),
                {"max_depth": depth, "min_samples_leaf": leaf},
                "rank_regression",
            )
            for depth, leaf in ((2, 100), (3, 100), (3, 250), (4, 250))
        ],
        "random_forest": [
            (
                f"depth={depth},leaf={leaf},features={features}",
                RandomForestRegressor(
                    n_estimators=300,
                    max_depth=depth,
                    min_samples_leaf=leaf,
                    max_features=features,
                    random_state=RANDOM_SEED,
                    n_jobs=-1,
                ),
                {"n_estimators": 300, "max_depth": depth, "min_samples_leaf": leaf, "max_features": features},
                "rank_regression",
            )
            for depth, leaf, features in ((3, 20, 0.5), (5, 20, 0.5), (5, 50, 1.0), (7, 50, 0.5))
        ],
        "hist_gradient_boosting": [
            (
                f"leaves={leaves},l2={regularization:g}",
                HistGradientBoostingRegressor(
                    max_iter=200,
                    learning_rate=0.05,
                    max_leaf_nodes=leaves,
                    l2_regularization=regularization,
                    random_state=RANDOM_SEED,
                ),
                {"max_iter": 200, "learning_rate": 0.05, "max_leaf_nodes": leaves, "l2_regularization": regularization},
                "rank_regression",
            )
            for leaves, regularization in ((7, 1.0), (15, 1.0), (15, 10.0))
        ],
    }


def fit_and_predict(estimator: object, task_type: str, fit: pd.DataFrame, score: pd.DataFrame, features: list[str]) -> tuple[object, np.ndarray]:
    if task_type == "classification":
        fitted = clone(estimator).fit(fit[features], fit[CLASS_TARGET].astype(int))
        classes = fitted.classes_ if hasattr(fitted, "classes_") else fitted[-1].classes_
        positive_index = int(np.flatnonzero(np.asarray(classes) == 1)[0])
        return fitted, fitted.predict_proba(score[features])[:, positive_index]
    fitted = clone(estimator).fit(fit[features], fit[RANK_TARGET])
    return fitted, fitted.predict(score[features])


def select_candidates(frame: pd.DataFrame, features: list[str], train_dates: list[pd.Timestamp]) -> tuple[dict, pd.DataFrame]:
    validation_dates = train_dates[4:]
    selections: dict[str, dict] = {}
    rows: list[dict] = []
    for model_name, candidates in model_candidates().items():
        best = None
        for order, (candidate_name, estimator, parameters, task_type) in enumerate(candidates):
            quarter_ics = []
            quarter_top30_excess = []
            quarter_native_metrics = []
            for validation_date in validation_dates:
                fit = frame[frame["Date"] < validation_date]
                validation = frame[frame["Date"] == validation_date]
                fitted, prediction = fit_and_predict(estimator, task_type, fit, validation, features)
                ic = safe_spearman(validation[TARGET], prediction)
                ranked = validation[[TARGET]].copy()
                ranked["prediction"] = prediction
                excess = float(ranked.nlargest(TOP_N, "prediction")[TARGET].mean() - ranked[TARGET].mean())
                quarter_ics.append(ic)
                quarter_top30_excess.append(excess)
                if task_type == "classification":
                    quarter_native_metrics.append(roc_auc_score(validation[CLASS_TARGET].astype(int), prediction))
                else:
                    quarter_native_metrics.append(r2_score(validation[RANK_TARGET], prediction))
            row = {
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "task_type": task_type,
                "target": CLASS_TARGET if task_type == "classification" else RANK_TARGET,
                "candidate": candidate_name,
                "candidate_order": order,
                "parameters": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
                "mean_validation_ic": float(np.mean(quarter_ics)),
                "minimum_validation_ic": float(np.min(quarter_ics)),
                "positive_ic_ratio": float(np.mean(np.asarray(quarter_ics) > 0)),
                "mean_validation_top30_excess": float(np.mean(quarter_top30_excess)),
                "native_metric": "AUC" if task_type == "classification" else "rank_target_R2",
                "mean_validation_native_metric": float(np.mean(quarter_native_metrics)),
            }
            for date, ic, excess, native_metric in zip(validation_dates, quarter_ics, quarter_top30_excess, quarter_native_metrics):
                key = f"{pd.Timestamp(date).year}Q{pd.Timestamp(date).quarter}"
                row[f"ic_{key}"] = ic
                row[f"top30_excess_{key}"] = excess
                row[f"native_metric_{key}"] = native_metric
            rows.append(row)
            selection_key = (row["mean_validation_ic"], row["minimum_validation_ic"], -order)
            if best is None or selection_key > best["selection_key"]:
                best = {
                    "selection_key": selection_key,
                    "candidate": candidate_name,
                    "estimator": estimator,
                    "parameters": parameters,
                    "task_type": task_type,
                    "mean_validation_ic": row["mean_validation_ic"],
                    "minimum_validation_ic": row["minimum_validation_ic"],
                    "mean_validation_native_metric": row["mean_validation_native_metric"],
                }
        selections[model_name] = best
    return selections, pd.DataFrame(rows)


def strict_portfolios(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    returns: list[dict] = []
    holdings: list[pd.DataFrame] = []
    for model_name, model_frame in predictions.groupby("model", sort=False):
        previous: set[str] = set()
        for date, quarter in model_frame.groupby("Date", sort=True):
            ranked = quarter.sort_values(["prediction", "Code"], ascending=[False, True]).copy()
            ranked["predicted_rank"] = np.arange(1, len(ranked) + 1)
            selected = ranked.head(TOP_N).copy()
            current = set(selected["Code"].astype(str))
            turnover = 1.0 if not previous else 1.0 - len(previous & current) / TOP_N
            gross_return = float(selected[TARGET].mean())
            market_return = float(quarter[TARGET].mean())
            returns.append({
                "Date": date,
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "portfolio": "strict_top30",
                "gross_return": gross_return,
                "net_return": gross_return - ONE_WAY_COST * turnover,
                "market_return": market_return,
                "gross_excess": gross_return - market_return,
                "net_excess": gross_return - ONE_WAY_COST * turnover - market_return,
                "turnover": turnover,
                "holding_count": len(selected),
            })
            selected["model"] = model_name
            selected["portfolio"] = "strict_top30"
            selected["turnover"] = turnover
            holdings.append(selected)
            previous = current
    return pd.DataFrame(returns), pd.concat(holdings, ignore_index=True)


def buffered_portfolio(predictions: pd.DataFrame, strategy_model: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_model = predictions[predictions["model"] == strategy_model]
    previous: set[str] = set()
    return_rows: list[dict] = []
    holding_rows: list[pd.DataFrame] = []
    for date, quarter in selected_model.groupby("Date", sort=True):
        ranked = quarter.sort_values(["prediction", "Code"], ascending=[False, True]).copy()
        ranked["predicted_rank"] = np.arange(1, len(ranked) + 1)
        eligible_previous = ranked[ranked["Code"].astype(str).isin(previous) & ranked["predicted_rank"].le(BUFFER_RANK)]
        keep = eligible_previous["Code"].astype(str).tolist()
        fill = ranked[~ranked["Code"].astype(str).isin(keep)].head(TOP_N - len(keep))["Code"].astype(str).tolist()
        current = set(keep + fill)
        selected = ranked[ranked["Code"].astype(str).isin(current)].copy()
        turnover = 1.0 if not previous else 1.0 - len(previous & current) / TOP_N
        gross_return = float(selected[TARGET].mean())
        market_return = float(quarter[TARGET].mean())
        return_rows.append({
            "Date": date,
            "model": strategy_model,
            "model_label": MODEL_LABELS[strategy_model],
            "portfolio": "buffer_top30_top50",
            "gross_return": gross_return,
            "net_return": gross_return - ONE_WAY_COST * turnover,
            "market_return": market_return,
            "gross_excess": gross_return - market_return,
            "net_excess": gross_return - ONE_WAY_COST * turnover - market_return,
            "turnover": turnover,
            "holding_count": len(selected),
        })
        selected["model"] = strategy_model
        selected["portfolio"] = "buffer_top30_top50"
        selected["turnover"] = turnover
        holding_rows.append(selected)
        previous = current
    return pd.DataFrame(return_rows), pd.concat(holding_rows, ignore_index=True)


def choose_strategy_model(selections: dict[str, dict], tolerance: float = 0.01) -> str:
    complexity_order = ["linear_regression", "ridge", "logistic_regression", "decision_tree", "random_forest", "hist_gradient_boosting"]
    best_score = max(item["mean_validation_ic"] for item in selections.values())
    eligible = {name for name, item in selections.items() if item["mean_validation_ic"] >= best_score - tolerance}
    return next(name for name in complexity_order if name in eligible)


def run_main_pipeline() -> dict:
    ensure_directories()
    frame, raw_features, model_features, quality = load_and_engineer()
    dates = [pd.Timestamp(date) for date in sorted(frame["Date"].unique())]
    if len(dates) != 10:
        raise ValueError(f"预期10个季度，实际为{len(dates)}")
    train_dates, test_dates = dates[:7], dates[7:]
    frame["Split"] = np.where(frame["Date"].isin(train_dates), "train", "test")
    if frame.duplicated(KEY_COLUMNS).any() or frame[model_features + [TARGET, RANK_TARGET, CLASS_TARGET]].isna().any().any():
        raise ValueError("数据未通过唯一键或完整性检查")
    frame.to_csv(MAIN_PROCESSED_DIR / "main_model_dataset.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    quality.update({
        "split_rule": "first 7 unique quarters train, last 3 unique quarters test",
        "train_dates": [date.date().isoformat() for date in train_dates],
        "test_dates": [date.date().isoformat() for date in test_dates],
        "train_rows": int(frame["Split"].eq("train").sum()),
        "test_rows": int(frame["Split"].eq("test").sum()),
        "model_features": model_features,
    })
    write_json(MAIN_METADATA_DIR / "data_quality_report.json", quality)

    selections, candidate_metrics = select_candidates(frame, model_features, train_dates)
    candidate_metrics.to_csv(MAIN_PROCESSED_DIR / "main_candidate_metrics.csv", index=False, encoding="utf-8-sig")
    strategy_model = choose_strategy_model(selections)

    train = frame[frame["Split"] == "train"].copy()
    test = frame[frame["Split"] == "test"].copy()
    metric_rows: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []
    importance_rows: list[dict] = []
    model_metadata: dict[str, dict] = {}
    for model_name, choice in selections.items():
        task_type = choice["task_type"]
        fitted, prediction = fit_and_predict(choice["estimator"], task_type, train, test, model_features)
        test_prediction = test[["Date", "Code", TARGET, RANK_TARGET, CLASS_TARGET]].copy()
        test_prediction["model"] = model_name
        test_prediction["model_label"] = MODEL_LABELS[model_name]
        test_prediction["prediction"] = prediction
        prediction_frames.append(test_prediction)
        quarter_ics = [safe_spearman(part[TARGET], part["prediction"]) for _, part in test_prediction.groupby("Date")]
        native_metric = roc_auc_score(test[CLASS_TARGET].astype(int), prediction) if task_type == "classification" else r2_score(test[RANK_TARGET], prediction)
        metric_rows.append({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "task_type": task_type,
            "target": CLASS_TARGET if task_type == "classification" else RANK_TARGET,
            "selected_candidate": choice["candidate"],
            "validation_mean_ic": choice["mean_validation_ic"],
            "validation_minimum_ic": choice["minimum_validation_ic"],
            "native_metric": "AUC" if task_type == "classification" else "rank_target_R2",
            "validation_native_metric": choice["mean_validation_native_metric"],
            "test_native_metric": native_metric,
            "mae": mean_absolute_error(test[RANK_TARGET], prediction) if task_type != "classification" else np.nan,
            "rmse": mean_squared_error(test[RANK_TARGET], prediction) ** 0.5 if task_type != "classification" else np.nan,
            "r2": native_metric if task_type != "classification" else np.nan,
            "auc": native_metric if task_type == "classification" else np.nan,
            "brier": brier_score_loss(test[CLASS_TARGET].astype(int), prediction) if task_type == "classification" else np.nan,
            "mean_test_ic": float(np.mean(quarter_ics)),
            "minimum_test_ic": float(np.min(quarter_ics)),
            "positive_test_ic_ratio": float(np.mean(np.asarray(quarter_ics) > 0)),
            "strategy_model": model_name == strategy_model,
        })
        if model_name in {"linear_regression", "ridge"}:
            values = fitted.coef_
            importance_type = "coefficient"
        elif model_name == "logistic_regression":
            values = fitted.named_steps["logisticregression"].coef_[0]
            importance_type = "standardized_coefficient"
        elif model_name in {"decision_tree", "random_forest"}:
            values = fitted.feature_importances_
            importance_type = "impurity_importance"
        else:
            values = np.full(len(model_features), np.nan)
            importance_type = "not_reported"
        importance_rows.extend({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "feature": feature,
            "importance": float(value) if np.isfinite(value) else np.nan,
            "absolute_importance": float(abs(value)) if np.isfinite(value) else np.nan,
            "importance_type": importance_type,
        } for feature, value in zip(model_features, values))
        model_path = MAIN_MODEL_DIR / f"{model_name}.joblib"
        joblib.dump({
            "model": fitted,
            "features": model_features,
            "target": CLASS_TARGET if task_type == "classification" else RANK_TARGET,
            "task_type": task_type,
            "train_dates": [date.date().isoformat() for date in train_dates],
        }, model_path)
        model_metadata[model_name] = {
            "candidate": choice["candidate"],
            "parameters": choice["parameters"],
            "task_type": task_type,
            "target": CLASS_TARGET if task_type == "classification" else RANK_TARGET,
            "validation_mean_ic": choice["mean_validation_ic"],
            "validation_native_metric": choice["mean_validation_native_metric"],
            "model_file": model_path.name,
            "model_sha256": sha256_file(model_path),
        }

    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions.to_csv(MAIN_PROCESSED_DIR / "main_test_predictions.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(MAIN_PROCESSED_DIR / "main_model_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(importance_rows).to_csv(MAIN_PROCESSED_DIR / "main_feature_importance.csv", index=False, encoding="utf-8-sig")

    strict_returns, strict_holdings = strict_portfolios(predictions)
    buffer_returns, buffer_holdings = buffered_portfolio(predictions, strategy_model)
    portfolio_returns = pd.concat([strict_returns, buffer_returns], ignore_index=True)
    holdings = pd.concat([strict_holdings, buffer_holdings], ignore_index=True)
    portfolio_returns.to_csv(MAIN_PROCESSED_DIR / "main_quarterly_returns.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    holdings.to_csv(MAIN_PROCESSED_DIR / "main_portfolio_holdings.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    performance_rows = []
    for (model_name, portfolio), part in portfolio_returns.groupby(["model", "portfolio"]):
        for return_type in ("gross_return", "net_return"):
            result = quarterly_performance(part.sort_values("Date")[return_type])
            performance_rows.append({
                "model": model_name,
                "model_label": MODEL_LABELS[model_name],
                "portfolio": portfolio,
                "return_type": return_type,
                "average_turnover": float(part["turnover"].mean()),
                **result,
            })
    market = strict_returns[strict_returns["model"] == strategy_model].sort_values("Date")
    performance_rows.append({
        "model": "market_equal_weight",
        "model_label": MODEL_LABELS["market_equal_weight"],
        "portfolio": "market_equal_weight",
        "return_type": "gross_return",
        "average_turnover": np.nan,
        **quarterly_performance(market["market_return"]),
    })
    performance = pd.DataFrame(performance_rows)
    performance.to_csv(MAIN_PROCESSED_DIR / "main_strategy_metrics.csv", index=False, encoding="utf-8-sig")

    run_metadata = {
        "created_at": datetime.now().astimezone().isoformat(),
        "random_seed": RANDOM_SEED,
        "task": "TASK6 quarterly cross-sectional return ranking",
        "source_file": project_relative(SOURCE_FILE),
        "source_sha256": sha256_file(SOURCE_FILE),
        "split": "chronological 7 quarters train / 3 quarters test",
        "validation": "expanding window; validate on training quarters 5-7",
        "candidate_selection": "highest mean quarterly Spearman IC; minimum IC and simpler candidate break ties",
        "strategy_model_selection": "best validation mean IC, but choose the simpler model when within 0.01 IC of the best",
        "strategy_model": strategy_model,
        "regression_target": "within-quarter percentile rank of Next_Ret, centered to [-0.5, 0.5]",
        "classification_target": "1 when Next_Ret is above the same quarter's cross-sectional median, otherwise 0",
        "portfolio_evaluation": "raw realized Next_Ret; target transformations are used only for model fitting and diagnostics",
        "portfolio": f"equal-weight predicted top {TOP_N}; buffer sensitivity retains prior holdings through rank {BUFFER_RANK}",
        "transaction_cost": f"{ONE_WAY_COST:.4f} times one-sided portfolio turnover",
        "feature_count": len(model_features),
        "features": model_features,
        "models": model_metadata,
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "required_caveats": [
            "测试集只有3个季度，年化收益、波动率和夏普比率仅作描述。",
            "回归R²评价的是横截面收益排名目标，不是个股收益率点预测精度。",
            "样本未提供财务报表实际披露日，无法完全排除时点可得性风险。",
            "股票池缺少历史成分、ST、停牌、流动性和可交易性标记，可能存在幸存者偏差。",
            "20bp为教学用合并成本假设，不等同于某一账户的实际费率。",
        ],
    }
    write_json(MAIN_METADATA_DIR / "model_run.json", run_metadata)
    return {
        "strategy_model": strategy_model,
        "strategy_model_label": MODEL_LABELS[strategy_model],
        "train_rows": len(train),
        "test_rows": len(test),
        "test_dates": [date.date().isoformat() for date in test_dates],
        "metrics": metrics,
        "quarterly_returns": portfolio_returns,
        "performance": performance,
    }


if __name__ == "__main__":
    result = run_main_pipeline()
    print(f"[main] strategy model: {result['strategy_model_label']}")
    print(result["metrics"].to_string(index=False))
