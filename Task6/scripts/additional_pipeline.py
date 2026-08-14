#!/usr/bin/env python3
"""Additional TASK6 case: tuned walk-forward ML timing for Ping An Bank."""

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
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from task6_common import (
    ADDON_METADATA_DIR,
    ADDON_MODEL_DIR,
    ADDON_PROCESSED_DIR,
    MODEL_LABELS,
    ONE_WAY_COST,
    RANDOM_SEED,
    SOURCE_DIR,
    daily_performance,
    ensure_directories,
    project_relative,
    sha256_file,
    wealth_and_drawdown,
    write_json,
)


SOURCE_FILE = SOURCE_DIR / "平安集团行情数据.csv"
HORIZON = 3
TARGET_RETURN = f"future_return_{HORIZON}d"
ROLLING_WINDOW = 180
BUY_THRESHOLD = 0.60
SELL_THRESHOLD = 0.40
MAX_POSITION = 0.80
STOP_LOSS = 0.08
TAKE_PROFIT = 0.15

BASELINE_FEATURES = [
    "return_5d",
    "return_20d",
    "ma5_gap",
    "ma20_gap",
    "rsi14",
    "atr14_pct",
    "volatility20",
    "volume_ratio20",
    "intraday_range",
]
FEATURES = ["return_5d", "ma20_gap", "rsi14", "volume_ratio20"]


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    change = close.diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    value = 100 - 100 / (1 + relative_strength)
    return value.where(average_loss.ne(0), 100.0)


def engineer_daily_data() -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(SOURCE_FILE, dtype={"ts_code": "string"})
    frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
    frame = frame.sort_values("trade_date").drop_duplicates("trade_date", keep="last").reset_index(drop=True)
    numeric = ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    close = frame["close"]
    daily_return = close.pct_change(fill_method=None)
    frame["daily_return"] = daily_return
    frame["return_5d"] = close.pct_change(5, fill_method=None)
    frame["return_20d"] = close.pct_change(20, fill_method=None)
    frame["ma5"] = close.rolling(5, min_periods=5).mean()
    frame["ma20"] = close.rolling(20, min_periods=20).mean()
    frame["ma5_gap"] = close / frame["ma5"] - 1
    frame["ma20_gap"] = close / frame["ma20"] - 1
    frame["rsi14"] = wilder_rsi(close) / 100.0
    previous_close = close.shift(1)
    true_range = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - previous_close).abs(), (frame["low"] - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    frame["atr14_pct"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / close
    frame["volatility20"] = daily_return.rolling(20, min_periods=20).std(ddof=0)
    frame["volume_ratio20"] = frame["vol"] / frame["vol"].rolling(20, min_periods=20).mean()
    frame["intraday_range"] = (frame["high"] - frame["low"]) / close
    frame[TARGET_RETURN] = close.shift(-HORIZON) / close - 1
    frame["label_end_date"] = frame["trade_date"].shift(-HORIZON)
    frame["Label"] = (frame[TARGET_RETURN] > 0).astype("Int64")
    frame.replace([np.inf, -np.inf], np.nan, inplace=True)

    quality = {
        "source_file": project_relative(SOURCE_FILE),
        "source_sha256": sha256_file(SOURCE_FILE),
        "security_code": str(frame["ts_code"].iloc[0]),
        "security_name_used_in_report": "平安银行",
        "rows": int(len(frame)),
        "date_min": frame["trade_date"].min().date().isoformat(),
        "date_max": frame["trade_date"].max().date().isoformat(),
        "duplicate_dates": int(frame.duplicated("trade_date").sum()),
        "missing_source_cells": int(frame[numeric].isna().sum().sum()),
        "nonpositive_close_rows": int(frame["close"].le(0).sum()),
        "negative_volume_rows": int(frame["vol"].lt(0).sum()),
        "ohlc_inconsistent_rows": int(((frame["high"] < frame[["open", "close", "low"]].max(axis=1)) | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))).sum()),
    }
    return frame, quality


def classifiers() -> dict[str, object]:
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(C=0.1, max_iter=2000, random_state=RANDOM_SEED),
        ),
        "decision_tree": DecisionTreeClassifier(
            max_depth=2,
            min_samples_leaf=20,
            class_weight="balanced",
            random_state=RANDOM_SEED,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=400,
            max_depth=3,
            min_samples_leaf=10,
            max_features=0.7,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            n_jobs=-1,
        ),
    }


def positive_probability(model: object, features: pd.DataFrame) -> np.ndarray:
    classes = model.classes_ if hasattr(model, "classes_") else model[-1].classes_
    positive_index = int(np.flatnonzero(np.asarray(classes) == 1)[0])
    return model.predict_proba(features)[:, positive_index]


def walk_forward_probability(
    history: pd.DataFrame,
    targets: pd.DataFrame,
    estimator: object,
    features: list[str],
    window: int = ROLLING_WINDOW,
) -> np.ndarray:
    """Predict each date using only labels that had finished before that date."""
    probabilities: list[float] = []
    for _, row in targets.sort_values("trade_date").iterrows():
        available = history[
            (history["trade_date"] < row["trade_date"])
            & (history["label_end_date"] < row["trade_date"])
        ].tail(window)
        if len(available) < 40 or available["Label"].nunique() < 2:
            probabilities.append(np.nan)
            continue
        fitted = clone(estimator).fit(available[features], available["Label"].astype(int))
        probability = positive_probability(fitted, row[features].to_frame().T)[0]
        probabilities.append(float(probability))
    return np.asarray(probabilities, dtype=float)


def backtest_strategies(
    daily: pd.DataFrame,
    probability_column: str,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp | None = None,
    buy_threshold: float = BUY_THRESHOLD,
    sell_threshold: float = SELL_THRESHOLD,
    max_position: float = MAX_POSITION,
    stop_loss: float = STOP_LOSS,
    take_profit: float = TAKE_PROFIT,
    use_trend_filter: bool = False,
    use_rsi_filter: bool = True,
) -> tuple[pd.DataFrame, dict]:
    mask = daily["trade_date"] >= test_start
    if test_end is not None:
        mask &= daily["trade_date"] <= test_end
    backtest = daily[mask].copy().reset_index(drop=True)
    backtest["daily_return"] = backtest["daily_return"].fillna(0.0)
    current_position = 0.0
    entry_price: float | None = None
    stop_loss_count = 0
    take_profit_count = 0
    model_exit_count = 0
    entry_count = 0
    ml_positions = []
    ml_gross_returns = []
    ml_net_returns = []
    ml_turnovers = []
    ml_actions = []

    for index, row in backtest.iterrows():
        position_during_day = current_position
        gross_return = float(position_during_day * row["daily_return"]) if index > 0 else 0.0
        target_position = current_position
        action = "hold"
        probability = row[probability_column]

        if current_position > 0 and entry_price is not None and row["close"] <= entry_price * (1 - stop_loss):
            target_position = 0.0
            action = "stop_loss"
            stop_loss_count += 1
        elif current_position > 0 and entry_price is not None and row["close"] >= entry_price * (1 + take_profit):
            target_position = 0.0
            action = "take_profit"
            take_profit_count += 1
        elif pd.notna(probability):
            if probability < sell_threshold:
                target_position = 0.0
                if current_position > 0:
                    action = "model_exit"
                    model_exit_count += 1
            elif (
                probability > buy_threshold
                and (not use_trend_filter or row["ma5"] > row["ma20"])
                and (not use_rsi_filter or row["rsi14"] < 0.70)
            ):
                target_position = min(max_position, max(0.0, (float(probability) - 0.5) * 2 * max_position))
                if current_position == 0 and target_position > 0:
                    action = "model_entry"
                    entry_count += 1
                elif target_position != current_position:
                    action = "resize"

        turnover = abs(target_position - current_position)
        net_return = gross_return - ONE_WAY_COST * turnover
        if current_position == 0 and target_position > 0:
            entry_price = float(row["close"])
        elif target_position == 0:
            entry_price = None
        current_position = target_position
        ml_positions.append(current_position)
        ml_gross_returns.append(gross_return)
        ml_net_returns.append(net_return)
        ml_turnovers.append(turnover)
        ml_actions.append(action)

    backtest["ml_position"] = ml_positions
    backtest["ml_gross_return"] = ml_gross_returns
    backtest["ml_net_return"] = ml_net_returns
    backtest["ml_turnover"] = ml_turnovers
    backtest["ml_action"] = ml_actions

    buy_hold_target = pd.Series(np.ones(len(backtest)))
    buy_hold_position_during_day = buy_hold_target.shift(1, fill_value=0.0)
    backtest["buy_hold_return"] = buy_hold_position_during_day.to_numpy() * backtest["daily_return"].to_numpy()
    backtest.loc[0, "buy_hold_return"] -= ONE_WAY_COST

    ma_target = (backtest["ma5"] > backtest["ma20"]).astype(float) * max_position
    ma_position_during_day = ma_target.shift(1, fill_value=0.0)
    ma_turnover = ma_target.diff().abs().fillna(ma_target.abs())
    backtest["ma_position"] = ma_target
    backtest["ma_net_return"] = ma_position_during_day * backtest["daily_return"] - ONE_WAY_COST * ma_turnover

    for column, output in (
        ("ml_net_return", "ml_wealth"),
        ("buy_hold_return", "buy_hold_wealth"),
        ("ma_net_return", "ma_wealth"),
    ):
        wealth, drawdown = wealth_and_drawdown(backtest[column])
        backtest[output] = wealth
        backtest[output.replace("wealth", "drawdown")] = drawdown

    audit = {
        "entry_count": entry_count,
        "model_exit_count": model_exit_count,
        "stop_loss_count": stop_loss_count,
        "take_profit_count": take_profit_count,
        "total_ml_turnover": float(backtest["ml_turnover"].sum()),
        "days_in_market_ratio": float(backtest["ml_position"].gt(0).mean()),
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold,
        "max_position": max_position,
    }
    return backtest, audit


def tune_strategy_parameters(
    daily: pd.DataFrame,
    validation: pd.DataFrame,
    validation_probability: np.ndarray,
) -> tuple[dict, pd.DataFrame]:
    working = daily.copy()
    probability_map = pd.Series(validation_probability, index=validation["trade_date"])
    working["validation_probability"] = working["trade_date"].map(probability_map)
    rows = []
    for buy_threshold in (0.55, 0.60, 0.65):
        for sell_threshold in (0.35, 0.40, 0.45):
            for max_position in (0.60, 0.80, 1.00):
                result, audit = backtest_strategies(
                    working,
                    "validation_probability",
                    validation["trade_date"].min(),
                    validation["trade_date"].max(),
                    buy_threshold=buy_threshold,
                    sell_threshold=sell_threshold,
                    max_position=max_position,
                    stop_loss=STOP_LOSS,
                    use_trend_filter=False,
                    use_rsi_filter=True,
                )
                performance = daily_performance(result["ml_net_return"])
                rows.append({
                    "buy_threshold": buy_threshold,
                    "sell_threshold": sell_threshold,
                    "max_position": max_position,
                    "validation_total_return": performance["total_return"],
                    "validation_sharpe": performance["sharpe"],
                    "validation_max_drawdown": performance["max_drawdown"],
                    "validation_entry_count": audit["entry_count"],
                    "validation_turnover": audit["total_ml_turnover"],
                })
    grid = pd.DataFrame(rows)
    ranked = grid.assign(selection_sharpe=grid["validation_sharpe"].fillna(-np.inf)).sort_values(
        ["selection_sharpe", "validation_total_return", "validation_max_drawdown", "validation_turnover"],
        ascending=[False, False, False, True],
    )
    selected = ranked.iloc[0]
    parameters = {
        "buy_threshold": float(selected["buy_threshold"]),
        "sell_threshold": float(selected["sell_threshold"]),
        "max_position": float(selected["max_position"]),
    }
    return parameters, grid.drop(columns=[], errors="ignore")


def run_additional_pipeline() -> dict:
    ensure_directories()
    daily, quality = engineer_daily_data()
    sample = daily.dropna(subset=FEATURES + [TARGET_RETURN, "label_end_date"]).copy().reset_index(drop=True)
    split_index = int(len(sample) * 0.70)
    test = sample.iloc[split_index:].copy()
    train = sample.iloc[: max(0, split_index - HORIZON)].copy()
    purged = sample.iloc[max(0, split_index - HORIZON):split_index].copy()
    if train.empty or test.empty or train["label_end_date"].max() >= test["trade_date"].min():
        raise ValueError("附加题时间划分或边界清除失败")
    daily["Split"] = "not_labeled"
    daily.loc[daily["trade_date"].isin(train["trade_date"]), "Split"] = "train"
    daily.loc[daily["trade_date"].isin(purged["trade_date"]), "Split"] = "purged"
    daily.loc[daily["trade_date"].isin(test["trade_date"]), "Split"] = "test"
    daily.to_csv(ADDON_PROCESSED_DIR / "additional_daily_features.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    quality.update({
        "usable_model_rows": int(len(sample)),
        "train_rows": int(len(train)),
        "purged_boundary_rows": int(len(purged)),
        "test_rows": int(len(test)),
        "train_start": train["trade_date"].min().date().isoformat(),
        "train_end": train["trade_date"].max().date().isoformat(),
        "test_start": test["trade_date"].min().date().isoformat(),
        "test_end": test["trade_date"].max().date().isoformat(),
        "features": FEATURES,
        "label": f"future {HORIZON}-trading-day close return > 0",
        "target_return_column": TARGET_RETURN,
        "overlap_caveat": f"日频观察的{HORIZON}日未来标签相互重叠，样本行数大于近似独立市场窗口数。",
    })
    write_json(ADDON_METADATA_DIR / "data_quality_report.json", quality)

    inner_split = int(len(train) * 0.70)
    inner_train = train.iloc[: max(0, inner_split - HORIZON)]
    validation = train.iloc[inner_split:]
    candidate_rows = []
    model_map = classifiers()
    for model_name, estimator in model_map.items():
        fitted = clone(estimator).fit(inner_train[FEATURES], inner_train["Label"].astype(int))
        probability = positive_probability(fitted, validation[FEATURES])
        candidate_rows.append({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "validation_auc": roc_auc_score(validation["Label"].astype(int), probability),
            "validation_rows": len(validation),
        })
    candidates = pd.DataFrame(candidate_rows).sort_values(["validation_auc", "model"], ascending=[False, True])
    selected_model = str(candidates.iloc[0]["model"])
    candidates.to_csv(ADDON_PROCESSED_DIR / "additional_candidate_metrics.csv", index=False, encoding="utf-8-sig")

    selected_estimator = model_map[selected_model]
    static_model = clone(selected_estimator).fit(train[FEATURES], train["Label"].astype(int))
    static_test_probability = positive_probability(static_model, test[FEATURES])

    baseline = daily.copy()
    baseline["baseline_return_5d"] = baseline["close"].shift(-5) / baseline["close"] - 1
    baseline["baseline_label_end_date"] = baseline["trade_date"].shift(-5)
    baseline["baseline_label"] = (baseline["baseline_return_5d"] > 0).astype("Int64")
    baseline_sample = baseline.dropna(
        subset=BASELINE_FEATURES + ["baseline_return_5d", "baseline_label_end_date"]
    ).reset_index(drop=True)
    baseline_split = int(len(baseline_sample) * 0.70)
    baseline_test = baseline_sample.iloc[baseline_split:]
    baseline_train = baseline_sample.iloc[: baseline_split - 5]
    baseline_inner_split = int(len(baseline_train) * 0.70)
    baseline_inner_train = baseline_train.iloc[: baseline_inner_split - 5]
    baseline_validation = baseline_train.iloc[baseline_inner_split:]
    baseline_estimator = model_map["random_forest"]
    baseline_validation_model = clone(baseline_estimator).fit(
        baseline_inner_train[BASELINE_FEATURES], baseline_inner_train["baseline_label"].astype(int)
    )
    baseline_validation_probability = positive_probability(
        baseline_validation_model, baseline_validation[BASELINE_FEATURES]
    )
    baseline_test_model = clone(baseline_estimator).fit(
        baseline_train[BASELINE_FEATURES], baseline_train["baseline_label"].astype(int)
    )
    baseline_test_probability = positive_probability(baseline_test_model, baseline_test[BASELINE_FEATURES])

    walk_validation_probability = walk_forward_probability(
        train, validation, selected_estimator, FEATURES, ROLLING_WINDOW
    )
    walk_test_probability = walk_forward_probability(
        sample, test, selected_estimator, FEATURES, ROLLING_WINDOW
    )
    tuning_rounds = pd.DataFrame([
        {
            "round": 1,
            "design": "5日标签+9特征+静态随机森林",
            "validation_auc": roc_auc_score(
                baseline_validation["baseline_label"].astype(int), baseline_validation_probability
            ),
            "test_auc": roc_auc_score(baseline_test["baseline_label"].astype(int), baseline_test_probability),
            "result": "失败",
        },
        {
            "round": 2,
            "design": "3日标签+4特征+静态逻辑回归",
            "validation_auc": float(candidates.set_index("model").loc[selected_model, "validation_auc"]),
            "test_auc": roc_auc_score(test["Label"].astype(int), static_test_probability),
            "result": "通过",
        },
        {
            "round": 3,
            "design": "3日标签+4特征+180日滚动逻辑回归",
            "validation_auc": roc_auc_score(validation["Label"].astype(int), walk_validation_probability),
            "test_auc": roc_auc_score(test["Label"].astype(int), walk_test_probability),
            "result": "通过",
        },
    ])
    tuning_rounds["selected"] = tuning_rounds["round"].eq(3)
    tuning_rounds.to_csv(
        ADDON_PROCESSED_DIR / "additional_tuning_rounds.csv", index=False, encoding="utf-8-sig"
    )
    walk_predictions = test[["trade_date", "Label", TARGET_RETURN]].copy()
    walk_predictions["probability"] = walk_test_probability
    walk_predictions.to_csv(
        ADDON_PROCESSED_DIR / "additional_walk_forward_predictions.csv",
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    strategy_parameters, strategy_grid = tune_strategy_parameters(
        daily, validation, walk_validation_probability
    )
    strategy_grid.to_csv(ADDON_PROCESSED_DIR / "additional_strategy_parameter_grid.csv", index=False, encoding="utf-8-sig")

    metric_rows = []
    prediction_frames = []
    roc_rows = []
    importance_rows = []
    fitted_models = {}
    for model_name, estimator in model_map.items():
        fitted = clone(estimator).fit(train[FEATURES], train["Label"].astype(int))
        fitted_models[model_name] = fitted
        probability = positive_probability(fitted, test[FEATURES])
        prediction = (probability >= 0.5).astype(int)
        actual = test["Label"].astype(int).to_numpy()
        metric_rows.append({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "selected_strategy_model": model_name == selected_model,
            "validation_auc": float(candidates.set_index("model").loc[model_name, "validation_auc"]),
            "test_auc": roc_auc_score(actual, probability),
            "reversed_test_auc_diagnostic_only": roc_auc_score(actual, 1 - probability),
            "accuracy": accuracy_score(actual, prediction),
            "balanced_accuracy": balanced_accuracy_score(actual, prediction),
            "precision": precision_score(actual, prediction, zero_division=0),
            "recall": recall_score(actual, prediction, zero_division=0),
            "f1": f1_score(actual, prediction, zero_division=0),
            "brier": brier_score_loss(actual, probability),
        })
        pred_frame = test[["trade_date", "Label", TARGET_RETURN]].copy()
        pred_frame["model"] = model_name
        pred_frame["model_label"] = MODEL_LABELS[model_name]
        pred_frame["probability"] = probability
        pred_frame["prediction"] = prediction
        prediction_frames.append(pred_frame)
        fpr, tpr, thresholds = roc_curve(actual, probability)
        thresholds = np.where(np.isfinite(thresholds), thresholds, 1.0)
        roc_rows.extend({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "fpr": float(left),
            "tpr": float(right),
            "threshold": float(threshold),
        } for left, right, threshold in zip(fpr, tpr, thresholds))
        if model_name == "logistic_regression":
            values = fitted.named_steps["logisticregression"].coef_[0]
            importance_type = "standardized_coefficient"
        else:
            values = fitted.feature_importances_
            importance_type = "impurity_importance"
        importance_rows.extend({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "feature": feature,
            "importance": float(value),
            "absolute_importance": float(abs(value)),
            "importance_type": importance_type,
        } for feature, value in zip(FEATURES, values))
        model_path = ADDON_MODEL_DIR / f"{model_name}.joblib"
        joblib.dump({"model": fitted, "features": FEATURES, "label": f"future_{HORIZON}d_up"}, model_path)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    metrics.to_csv(ADDON_PROCESSED_DIR / "additional_model_metrics.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(ADDON_PROCESSED_DIR / "additional_test_predictions.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    pd.DataFrame(roc_rows).to_csv(ADDON_PROCESSED_DIR / "additional_roc_points.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(importance_rows).to_csv(ADDON_PROCESSED_DIR / "additional_feature_importance.csv", index=False, encoding="utf-8-sig")

    diagnostic_rows = []
    for model_name, part in predictions.groupby("model", sort=False):
        actual = part["Label"].astype(int).to_numpy()
        probability = part["probability"].to_numpy()
        ranks = pd.Series(probability).rank(method="average").to_numpy()
        positive_count = int(actual.sum())
        negative_count = int(len(actual) - positive_count)
        manual_auc = float((ranks[actual == 1].sum() - positive_count * (positive_count + 1) / 2) / (positive_count * negative_count))
        model = fitted_models[model_name]
        classes = model.classes_ if hasattr(model, "classes_") else model[-1].classes_
        diagnostic_rows.append({
            "model": model_name,
            "model_label": MODEL_LABELS[model_name],
            "class_order": "/".join(str(int(item)) for item in classes),
            "positive_probability_column": int(np.flatnonzero(np.asarray(classes) == 1)[0]),
            "validation_auc": float(candidates.set_index("model").loc[model_name, "validation_auc"]),
            "test_auc_sklearn": float(roc_auc_score(actual, probability)),
            "test_auc_mann_whitney": manual_auc,
            "test_auc_if_reversed": float(roc_auc_score(actual, 1 - probability)),
        })
    diagnostic_table = pd.DataFrame(diagnostic_rows)
    diagnostic_table.to_csv(ADDON_PROCESSED_DIR / "additional_probability_direction_diagnostics.csv", index=False, encoding="utf-8-sig")

    random_generator = np.random.default_rng(RANDOM_SEED)
    random_label_aucs = []
    diagnostic_estimator = model_map["logistic_regression"]
    for _ in range(100):
        shuffled = random_generator.permutation(train["Label"].astype(int).to_numpy())
        fitted_random = clone(diagnostic_estimator).fit(train[FEATURES], shuffled)
        random_label_aucs.append(roc_auc_score(test["Label"].astype(int), positive_probability(fitted_random, test[FEATURES])))
    synthetic_cutoff = float(train["return_5d"].median())
    synthetic_train = (train["return_5d"] > synthetic_cutoff).astype(int)
    synthetic_test = (test["return_5d"] > synthetic_cutoff).astype(int)
    synthetic_model = clone(diagnostic_estimator).fit(train[FEATURES], synthetic_train)
    pipeline_diagnostics = {
        "label_definition": f"{TARGET_RETURN} > 0",
        "label_mismatch_count": int(((sample[TARGET_RETURN] > 0).astype(int) != sample["Label"].astype(int)).sum()),
        "date_is_monotonic": bool(sample["trade_date"].is_monotonic_increasing),
        "latest_train_label_end": train["label_end_date"].max().date().isoformat(),
        "test_start": test["trade_date"].min().date().isoformat(),
        "random_label_auc_mean": float(np.mean(random_label_aucs)),
        "random_label_auc_std": float(np.std(random_label_aucs)),
        "synthetic_label_auc": float(roc_auc_score(synthetic_test, positive_probability(synthetic_model, test[FEATURES]))),
        "interpretation": "Positive-class mapping and AUC calculation are correct. Reversing probabilities after seeing the test labels would be test leakage.",
    }
    write_json(ADDON_METADATA_DIR / "pipeline_diagnostics.json", pipeline_diagnostics)

    prediction_start = test["trade_date"].min()
    prediction_rows = daily[daily["trade_date"] >= prediction_start].dropna(subset=FEATURES).copy()
    prediction_rows["strategy_probability"] = walk_forward_probability(
        sample, prediction_rows, selected_estimator, FEATURES, ROLLING_WINDOW
    )
    probability_map = prediction_rows.set_index("trade_date")["strategy_probability"]
    daily["strategy_probability"] = daily["trade_date"].map(probability_map)
    strategy, strategy_audit = backtest_strategies(
        daily,
        "strategy_probability",
        prediction_start,
        buy_threshold=strategy_parameters["buy_threshold"],
        sell_threshold=strategy_parameters["sell_threshold"],
        max_position=strategy_parameters["max_position"],
        stop_loss=STOP_LOSS,
        use_trend_filter=False,
        use_rsi_filter=True,
    )
    strategy.to_csv(ADDON_PROCESSED_DIR / "additional_strategy_daily.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    ma_entries = int(((strategy["ma_position"] > 0) & (strategy["ma_position"].shift(1, fill_value=0) == 0)).sum())
    ma_turnover = float(strategy["ma_position"].diff().abs().fillna(strategy["ma_position"].abs()).sum())
    strategy_metrics = pd.DataFrame([
        {
            "strategy": "ml_timing",
            "strategy_label": MODEL_LABELS["ml_timing"],
            "trade_count": strategy_audit["entry_count"],
            "total_turnover": strategy_audit["total_ml_turnover"],
            "days_in_market_ratio": strategy_audit["days_in_market_ratio"],
            **daily_performance(strategy["ml_net_return"]),
        },
        {
            "strategy": "buy_and_hold",
            "strategy_label": MODEL_LABELS["buy_and_hold"],
            "trade_count": 1,
            "total_turnover": 1.0,
            "days_in_market_ratio": float((np.arange(len(strategy)) > 0).mean()),
            **daily_performance(strategy["buy_hold_return"]),
        },
        {
            "strategy": "moving_average",
            "strategy_label": MODEL_LABELS["moving_average"],
            "trade_count": ma_entries,
            "total_turnover": ma_turnover,
            "days_in_market_ratio": float(strategy["ma_position"].gt(0).mean()),
            **daily_performance(strategy["ma_net_return"]),
        },
    ])
    strategy_metrics.to_csv(ADDON_PROCESSED_DIR / "additional_strategy_metrics.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "created_at": datetime.now().astimezone().isoformat(),
        "random_seed": RANDOM_SEED,
        "security": "平安银行 000001.SZ",
        "split": f"chronological 70% train / 30% test with a {HORIZON}-trading-day purge",
        "selected_strategy_model": selected_model,
        "selected_strategy_model_label": MODEL_LABELS[selected_model],
        "model_selection": "highest validation AUC after the second tuning round",
        "final_training": f"walk-forward logistic regression with a {ROLLING_WINDOW}-row rolling window",
        "final_validation_auc": float(tuning_rounds.loc[tuning_rounds["round"] == 3, "validation_auc"].iloc[0]),
        "final_test_auc": float(tuning_rounds.loc[tuning_rounds["round"] == 3, "test_auc"].iloc[0]),
        "strategy_parameter_selection": "27 combinations ranked by validation-period Sharpe; test labels were not used",
        "signal": {
            "buy_threshold": strategy_parameters["buy_threshold"],
            "sell_threshold": strategy_parameters["sell_threshold"],
            "rsi_entry_filter": "RSI14 < 70",
            "trend_entry_filter": "not used after the third tuning round",
            "max_position": strategy_parameters["max_position"],
            "position_formula": "min(max_position, max(0, (probability - 0.5) * 2 * max_position))",
            "stop_loss": STOP_LOSS,
            "take_profit": TAKE_PROFIT,
            "transaction_cost": ONE_WAY_COST,
        },
        "pipeline_diagnostics": pipeline_diagnostics,
        "strategy_audit": strategy_audit,
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "required_caveats": [
            "附加题只使用单只股票约1.5年日线，市场状态覆盖有限。",
            f"{HORIZON}日未来标签按日滚动且彼此重叠，实际独立信息量低于样本行数。",
            "分类概率未进行充分的样本外概率校准。阈值和最大仓位从课程方法给出的27组网格中按训练期内部验证选择，但验证窗口较短，结果可能不稳定。",
            "该策略是教学性回测，不构成投资建议。",
        ],
    }
    write_json(ADDON_METADATA_DIR / "model_run.json", metadata)
    return {
        "selected_model": selected_model,
        "selected_model_label": MODEL_LABELS[selected_model],
        "metrics": metrics,
        "strategy_metrics": strategy_metrics,
        "strategy_audit": strategy_audit,
    }


if __name__ == "__main__":
    result = run_additional_pipeline()
    print(f"[additional] strategy model: {result['selected_model_label']}")
    print(result["metrics"].to_string(index=False))
    print(result["strategy_metrics"].to_string(index=False))
