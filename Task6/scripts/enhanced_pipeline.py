#!/usr/bin/env python3
"""TASK6 extensions: portable pickle bundles, EW/PW portfolios, and a guarded model grid."""

from __future__ import annotations

import json
import pickle
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler

from additional_pipeline import (
    FEATURES,
    HORIZON,
    ROLLING_WINDOW,
    TARGET_RETURN,
    engineer_daily_data,
    walk_forward_probability,
)
from main_pipeline import RANK_TARGET, TARGET, fit_and_predict, load_and_engineer
from task6_common import (
    ADDON_MODEL_DIR,
    ENHANCED_METADATA_DIR,
    ENHANCED_MODEL_DIR,
    ENHANCED_PROCESSED_DIR,
    MAIN_MODEL_DIR,
    ONE_WAY_COST,
    RANDOM_SEED,
    ensure_directories,
    project_relative,
    quarterly_performance,
    sha256_file,
    write_json,
)


def _capped_weights(raw: np.ndarray, cap: float) -> np.ndarray:
    """Normalize nonnegative scores while redistributing weight above a cap."""
    raw = np.asarray(raw, dtype=float)
    raw = np.where(np.isfinite(raw) & (raw > 0), raw, 0.0)
    if raw.sum() == 0:
        raw = np.ones_like(raw)
    if cap * len(raw) < 1 - 1e-12:
        raise ValueError("weight cap is infeasible for this holding count")
    weights = raw / raw.sum()
    fixed = np.zeros(len(raw), dtype=bool)
    for _ in range(len(raw) + 1):
        above = (~fixed) & (weights > cap + 1e-12)
        if not above.any():
            break
        weights[above] = cap
        fixed |= above
        residual = 1.0 - weights[fixed].sum()
        free = ~fixed
        if not free.any():
            break
        free_raw = raw[free]
        if free_raw.sum() == 0:
            weights[free] = residual / free.sum()
        else:
            weights[free] = residual * free_raw / free_raw.sum()
    return weights / weights.sum()


def _portfolio_backtest(predictions: pd.DataFrame, top_n: int, method: str, power: float, cap: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    previous: dict[str, float] = {}
    returns, holdings = [], []
    for date, quarter in predictions.groupby("Date", sort=True):
        ranked = quarter.sort_values(["prediction", "Code"], ascending=[False, True]).head(top_n).copy()
        ranked["predicted_rank"] = np.arange(1, len(ranked) + 1)
        if method == "ew":
            raw = np.ones(len(ranked))
        elif method == "rank_pw":
            raw = (len(ranked) - ranked["predicted_rank"].to_numpy() + 1.0) ** power
        elif method == "score_pw":
            score = ranked["prediction"].to_numpy(dtype=float)
            raw = (score - np.nanmin(score) + 1e-6) ** power
        else:
            raise ValueError(method)
        weights = _capped_weights(raw, cap)
        ranked["weight"] = weights
        current = dict(zip(ranked["Code"].astype(str), weights))
        union = set(previous) | set(current)
        turnover = 1.0 if not previous else 0.5 * sum(abs(current.get(code, 0.0) - previous.get(code, 0.0)) for code in union)
        gross = float(np.dot(weights, ranked[TARGET].to_numpy(dtype=float)))
        market = float(quarter[TARGET].mean())
        net = gross - ONE_WAY_COST * turnover
        returns.append({
            "Date": date, "top_n": top_n, "weight_method": method, "power": power,
            "weight_cap": cap, "gross_return": gross, "net_return": net,
            "market_return": market, "turnover": turnover, "holding_count": len(ranked),
        })
        ranked["top_n"] = top_n
        ranked["weight_method"] = method
        ranked["power"] = power
        ranked["weight_cap"] = cap
        ranked["turnover"] = turnover
        holdings.append(ranked)
        previous = current
    return pd.DataFrame(returns), pd.concat(holdings, ignore_index=True)


def _main_validation_predictions(frame: pd.DataFrame, features: list[str], dates: list[pd.Timestamp]) -> pd.DataFrame:
    rows = []
    for date in dates[4:7]:
        fit = frame[frame["Date"] < date]
        score = frame[frame["Date"] == date]
        _, prediction = fit_and_predict(
            __import__("sklearn.linear_model", fromlist=["LinearRegression"]).LinearRegression(),
            "rank_regression", fit, score, features,
        )
        part = score[["Date", "Code", TARGET, RANK_TARGET]].copy()
        part["prediction"] = prediction
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def run_weight_grid() -> dict:
    frame, _, features, _ = load_and_engineer()
    dates = [pd.Timestamp(x) for x in sorted(frame["Date"].unique())]
    validation_predictions = _main_validation_predictions(frame, features, dates)
    test_all = pd.read_csv(
        ENHANCED_PROCESSED_DIR.parents[1] / "main" / "processed" / "main_test_predictions.csv",
        parse_dates=["Date"], dtype={"Code": "string"},
    )
    test_predictions = test_all[test_all["model"] == "linear_regression"].copy()

    grid_rows = []
    for top_n in (20, 30, 50):
        for method in ("ew", "rank_pw", "score_pw"):
            powers = (1.0,) if method == "ew" else (0.5, 1.0, 2.0)
            for power in powers:
                for cap in (0.05, 0.08, 0.10, 0.15):
                    if cap * top_n < 1:
                        continue
                    returns, _ = _portfolio_backtest(validation_predictions, top_n, method, power, cap)
                    perf = quarterly_performance(returns["net_return"])
                    grid_rows.append({
                        "top_n": top_n, "weight_method": method, "power": power, "weight_cap": cap,
                        "validation_total_return": perf["total_return"], "validation_sharpe": perf["sharpe"],
                        "validation_max_drawdown": perf["max_drawdown"],
                        "validation_average_turnover": float(returns["turnover"].mean()),
                    })
    grid = pd.DataFrame(grid_rows)
    grid["selection_score"] = grid["validation_sharpe"].fillna(-np.inf)
    selected = grid.sort_values(
        ["selection_score", "validation_total_return", "validation_average_turnover"],
        ascending=[False, False, True],
    ).iloc[0]
    configurations = [
        ("EW_Top30", 30, "ew", 1.0, 0.10),
        ("PW_Top30", 30, "rank_pw", 1.0, 0.10),
        ("Validation_Selected", int(selected.top_n), str(selected.weight_method), float(selected.power), float(selected.weight_cap)),
    ]
    all_returns, all_holdings, metrics = [], [], []
    for label, n, method, power, cap in configurations:
        returns, holdings = _portfolio_backtest(test_predictions, n, method, power, cap)
        returns["portfolio_label"] = label
        holdings["portfolio_label"] = label
        perf = quarterly_performance(returns["net_return"])
        metrics.append({"portfolio_label": label, **perf, "average_turnover": float(returns.turnover.mean()),
                        "top_n": n, "weight_method": method, "power": power, "weight_cap": cap})
        all_returns.append(returns)
        all_holdings.append(holdings)
    grid.to_csv(ENHANCED_PROCESSED_DIR / "main_weight_grid.csv", index=False, encoding="utf-8-sig")
    pd.concat(all_returns).to_csv(ENHANCED_PROCESSED_DIR / "main_weighted_quarterly_returns.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    pd.concat(all_holdings).to_csv(ENHANCED_PROCESSED_DIR / "main_weighted_holdings.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    pd.DataFrame(metrics).to_csv(ENHANCED_PROCESSED_DIR / "main_weighted_strategy_metrics.csv", index=False, encoding="utf-8-sig")
    return {"selected": selected.to_dict(), "metrics": metrics}


def run_guarded_auc_grid() -> dict:
    daily, _ = engineer_daily_data()
    feature_sets = {
        "compact4": FEATURES,
        "trend4": ["return_5d", "return_20d", "ma5_gap", "ma20_gap"],
        "compact6": FEATURES + ["atr14_pct", "volatility20"],
    }
    required = sorted(set(sum(feature_sets.values(), [])))
    sample = daily.dropna(subset=required + [TARGET_RETURN, "label_end_date"]).copy().reset_index(drop=True)
    split = int(len(sample) * 0.70)
    train = sample.iloc[: split - HORIZON].copy()
    test = sample.iloc[split:].copy()
    inner = int(len(train) * 0.70)
    validation = train.iloc[inner:].copy()
    rows = []
    specs = []
    for feature_name, features in feature_sets.items():
        for scaler_name, scaler in (("standard", StandardScaler()), ("robust", RobustScaler())):
            for c in (0.001, 0.01, 0.1, 1.0):
                for balanced in (False, True):
                    for window in (60, 120, 180):
                        estimator = make_pipeline(scaler, LogisticRegression(
                            C=c, class_weight="balanced" if balanced else None,
                            max_iter=2000, random_state=RANDOM_SEED,
                        ))
                        vp = walk_forward_probability(train, validation, estimator, features, window)
                        va = roc_auc_score(validation["Label"].astype(int), vp)
                        specs.append((va, feature_name, scaler_name, c, balanced, window, estimator, features))
    # Test is evaluated only for the validation winner and the existing preregistered baseline.
    winner = max(specs, key=lambda x: x[0])
    baseline_estimator = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000, random_state=RANDOM_SEED))
    evaluated = [
        ("validation_winner", *winner[1:]),
        ("existing_baseline", "compact4", "standard", 0.1, False, ROLLING_WINDOW, baseline_estimator, FEATURES),
    ]
    for label, feature_name, scaler_name, c, balanced, window, estimator, features in evaluated:
        vp = walk_forward_probability(train, validation, estimator, features, window)
        tp = walk_forward_probability(sample, test, estimator, features, window)
        rows.append({
            "candidate": label, "feature_set": feature_name, "scaler": scaler_name, "C": c,
            "class_weight_balanced": balanced, "window": window,
            "validation_auc": roc_auc_score(validation["Label"].astype(int), vp),
            "test_auc": roc_auc_score(test["Label"].astype(int), tp),
        })
    result = pd.DataFrame(rows)
    result.to_csv(ENHANCED_PROCESSED_DIR / "additional_guarded_auc_grid.csv", index=False, encoding="utf-8-sig")
    return {"comparison": rows, "grid_size": len(specs)}


def save_pickle_bundles() -> list[dict]:
    records = []
    for directory, family in ((MAIN_MODEL_DIR, "main"), (ADDON_MODEL_DIR, "additional")):
        for source in sorted(directory.glob("*.joblib")):
            payload = joblib.load(source)
            payload.update({
                "artifact_format": "TASK6 model bundle v1", "model_family": family,
                "created_at": datetime.now().astimezone().isoformat(), "random_seed": RANDOM_SEED,
                "transaction_cost": ONE_WAY_COST,
            })
            target = source.with_suffix(".pkl")
            with target.open("wb") as handle:
                pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
            records.append({"family": family, "file": project_relative(target), "sha256": sha256_file(target)})
    rolling = {
        "artifact_format": "TASK6 rolling estimator configuration v1",
        "model_family": "additional_rolling_logistic", "features": FEATURES,
        "target": f"future_{HORIZON}d_up", "rolling_window": ROLLING_WINDOW,
        "estimator": make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000, random_state=RANDOM_SEED)),
        "note": "This bundle stores the estimator template and walk-forward configuration; each prediction refits on available historical labels.",
    }
    rolling_path = ENHANCED_MODEL_DIR / "additional_rolling_logistic.pkl"
    with rolling_path.open("wb") as handle:
        pickle.dump(rolling, handle, protocol=pickle.HIGHEST_PROTOCOL)
    records.append({"family": "enhanced", "file": project_relative(rolling_path), "sha256": sha256_file(rolling_path)})
    write_json(ENHANCED_METADATA_DIR / "pickle_manifest.json", {"models": records})
    return records


def run_enhanced_pipeline() -> dict:
    ensure_directories()
    weight = run_weight_grid()
    auc = run_guarded_auc_grid()
    models = save_pickle_bundles()
    summary = {"weight_grid": weight, "auc_grid": auc, "pickle_count": len(models)}
    write_json(ENHANCED_METADATA_DIR / "enhanced_run.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run_enhanced_pipeline(), ensure_ascii=False, indent=2, default=str))
