#!/usr/bin/env python3
"""Independent, reproducible validation checks for TASK6 results."""

from __future__ import annotations

from datetime import datetime
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, r2_score, recall_score, roc_auc_score

from task6_common import (
    ADDON_METADATA_DIR,
    ADDON_PROCESSED_DIR,
    CHART_DIR,
    ENHANCED_METADATA_DIR,
    ENHANCED_PROCESSED_DIR,
    MAIN_METADATA_DIR,
    MAIN_PROCESSED_DIR,
    ONE_WAY_COST,
    TASK_DIR,
    TOP_N,
    quarterly_performance,
    safe_spearman,
    write_json,
)


def near(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return bool(np.isclose(left, right, atol=tolerance, rtol=tolerance, equal_nan=True))


def main() -> None:
    checks: list[dict] = []

    def add(name: str, passed: bool, evidence: str, severity: str = "high") -> None:
        checks.append({"check": name, "passed": bool(passed), "severity_if_failed": severity, "evidence": evidence})

    main_dataset = pd.read_csv(MAIN_PROCESSED_DIR / "main_model_dataset.csv", parse_dates=["Date"], dtype={"Code": "string"})
    predictions = pd.read_csv(MAIN_PROCESSED_DIR / "main_test_predictions.csv", parse_dates=["Date"], dtype={"Code": "string"})
    model_metrics = pd.read_csv(MAIN_PROCESSED_DIR / "main_model_metrics.csv").set_index("model")
    returns = pd.read_csv(MAIN_PROCESSED_DIR / "main_quarterly_returns.csv", parse_dates=["Date"])
    holdings = pd.read_csv(MAIN_PROCESSED_DIR / "main_portfolio_holdings.csv", parse_dates=["Date"], dtype={"Code": "string"})
    strategy_metrics = pd.read_csv(MAIN_PROCESSED_DIR / "main_strategy_metrics.csv")

    add("main_key_unique", main_dataset.duplicated(["Code", "Date"]).sum() == 0, f"duplicate keys={main_dataset.duplicated(['Code', 'Date']).sum()}")
    add("main_no_missing_model_cells", main_dataset.isna().sum().sum() == 0, f"missing cells={main_dataset.isna().sum().sum()}")
    add("main_split_values", set(main_dataset["Split"]) == {"train", "test"}, f"splits={sorted(main_dataset['Split'].unique())}")
    train_dates = sorted(main_dataset.loc[main_dataset["Split"] == "train", "Date"].unique())
    test_dates = sorted(main_dataset.loc[main_dataset["Split"] == "test", "Date"].unique())
    add("main_7_3_quarter_split", len(train_dates) == 7 and len(test_dates) == 3, f"train quarters={len(train_dates)}, test quarters={len(test_dates)}")
    add("main_chronological_split", max(train_dates) < min(test_dates), f"train end={max(train_dates)}, test start={min(test_dates)}")
    rank_columns = [column for column in main_dataset if column.startswith("rank__")]
    add("main_rank_feature_bounds", main_dataset[rank_columns].min().min() >= -0.5 and main_dataset[rank_columns].max().max() <= 0.5, f"range=[{main_dataset[rank_columns].min().min():.6f},{main_dataset[rank_columns].max().max():.6f}]")
    add("main_rank_target_bounds", main_dataset["Next_Ret_Rank"].between(-0.5, 0.5).all(), f"range=[{main_dataset['Next_Ret_Rank'].min():.6f},{main_dataset['Next_Ret_Rank'].max():.6f}]")
    add("main_class_target_binary", set(main_dataset["Above_Quarter_Median"]) == {0, 1}, f"values={sorted(main_dataset['Above_Quarter_Median'].unique())}")

    expected_test_rows = len(main_dataset[main_dataset["Split"] == "test"])
    for model, part in predictions.groupby("model"):
        stored = model_metrics.loc[model]
        add(f"main_prediction_grain_{model}", len(part) == expected_test_rows and part.duplicated(["Code", "Date"]).sum() == 0, f"rows={len(part)}, expected={expected_test_rows}, duplicates={part.duplicated(['Code','Date']).sum()}")
        quarter_ics = [safe_spearman(group["Next_Ret"], group["prediction"]) for _, group in part.groupby("Date")]
        add(f"main_ic_recompute_{model}", near(np.mean(quarter_ics), stored["mean_test_ic"]) and near(np.min(quarter_ics), stored["minimum_test_ic"]), f"mean={np.mean(quarter_ics):.12f}, min={np.min(quarter_ics):.12f}")
        if stored["task_type"] == "classification":
            native = roc_auc_score(part["Above_Quarter_Median"].astype(int), part["prediction"])
            add(f"main_auc_recompute_{model}", near(native, stored["auc"]) and native > 0.5, f"AUC={native:.12f}")
        else:
            native = r2_score(part["Next_Ret_Rank"], part["prediction"])
            add(f"main_rank_r2_recompute_{model}", near(native, stored["r2"]) and native > 0, f"rank-target R2={native:.12f}")

    strict_returns = returns[returns["portfolio"] == "strict_top30"]
    for model, part in strict_returns.groupby("model"):
        model_predictions = predictions[predictions["model"] == model]
        for date, row in part.set_index("Date").iterrows():
            expected = model_predictions[model_predictions["Date"] == date].nlargest(TOP_N, "prediction")["Next_Ret"].mean()
            add(f"main_top30_return_{model}_{date.date()}", near(expected, row["gross_return"]), f"stored={row['gross_return']:.12f}, recomputed={expected:.12f}")
            add(f"main_cost_identity_{model}_{date.date()}", near(row["net_return"], row["gross_return"] - ONE_WAY_COST * row["turnover"]), f"gross={row['gross_return']:.8f}, turnover={row['turnover']:.8f}, net={row['net_return']:.8f}")
    holding_counts = holdings.groupby(["model", "portfolio", "Date"])["Code"].nunique()
    add("main_all_portfolios_hold_30", bool((holding_counts == TOP_N).all()), f"holding-count range=[{holding_counts.min()},{holding_counts.max()}]")

    strategy_model = model_metrics.index[model_metrics["strategy_model"].astype(bool)].tolist()
    add("main_one_strategy_model", len(strategy_model) == 1, f"strategy models={strategy_model}")
    if strategy_model:
        strategy = strategy_model[0]
        strict = strict_returns[strict_returns["model"] == strategy].sort_values("Date")
        stored_perf = strategy_metrics[(strategy_metrics["model"] == strategy) & (strategy_metrics["portfolio"] == "strict_top30") & (strategy_metrics["return_type"] == "gross_return")].iloc[0]
        recomputed = quarterly_performance(strict["gross_return"])
        add("main_strategy_total_return", near(stored_perf["total_return"], recomputed["total_return"]), f"stored={stored_perf['total_return']:.12f}, recomputed={recomputed['total_return']:.12f}")

    addon_daily = pd.read_csv(ADDON_PROCESSED_DIR / "additional_daily_features.csv", parse_dates=["trade_date", "label_end_date"])
    addon_predictions = pd.read_csv(ADDON_PROCESSED_DIR / "additional_test_predictions.csv", parse_dates=["trade_date"])
    addon_metrics = pd.read_csv(ADDON_PROCESSED_DIR / "additional_model_metrics.csv").set_index("model")
    addon_strategy = pd.read_csv(ADDON_PROCESSED_DIR / "additional_strategy_daily.csv", parse_dates=["trade_date"])
    addon_strategy_metrics = pd.read_csv(ADDON_PROCESSED_DIR / "additional_strategy_metrics.csv").set_index("strategy")
    addon_direction = pd.read_csv(ADDON_PROCESSED_DIR / "additional_probability_direction_diagnostics.csv").set_index("model")
    addon_grid = pd.read_csv(ADDON_PROCESSED_DIR / "additional_strategy_parameter_grid.csv")
    addon_tuning = pd.read_csv(ADDON_PROCESSED_DIR / "additional_tuning_rounds.csv")
    addon_walk_forward = pd.read_csv(
        ADDON_PROCESSED_DIR / "additional_walk_forward_predictions.csv", parse_dates=["trade_date"]
    )
    addon_metadata = pd.read_json(ADDON_METADATA_DIR / "model_run.json", typ="series")
    addon_quality = pd.read_json(ADDON_METADATA_DIR / "data_quality_report.json", typ="series")
    addon_pipeline_diagnostics = pd.read_json(ADDON_METADATA_DIR / "pipeline_diagnostics.json", typ="series")
    add("addon_date_unique", addon_daily.duplicated("trade_date").sum() == 0, f"duplicate dates={addon_daily.duplicated('trade_date').sum()}")
    add("addon_price_valid", addon_daily["close"].gt(0).all(), f"nonpositive close rows={addon_daily['close'].le(0).sum()}")
    addon_train = addon_daily[addon_daily["Split"] == "train"]
    addon_test = addon_daily[addon_daily["Split"] == "test"]
    add("addon_label_purge", addon_train["label_end_date"].max() < addon_test["trade_date"].min(), f"latest train label end={addon_train['label_end_date'].max()}, test start={addon_test['trade_date'].min()}")
    for model, part in addon_predictions.groupby("model"):
        actual = part["Label"].astype(int).to_numpy()
        probability = part["probability"].to_numpy()
        prediction = (probability >= 0.5).astype(int)
        stored = addon_metrics.loc[model]
        values = {
            "test_auc": roc_auc_score(actual, probability),
            "accuracy": accuracy_score(actual, prediction),
            "precision": precision_score(actual, prediction, zero_division=0),
            "recall": recall_score(actual, prediction, zero_division=0),
            "f1": f1_score(actual, prediction, zero_division=0),
        }
        add(f"addon_metrics_recompute_{model}", all(near(stored[key], value) for key, value in values.items()), ", ".join(f"{key}={value:.12f}" for key, value in values.items()))
        add(f"addon_probability_range_{model}", part["probability"].between(0, 1).all(), f"range=[{part['probability'].min():.6f},{part['probability'].max():.6f}]")
        direction = addon_direction.loc[model]
        add(f"addon_positive_class_mapping_{model}", direction["class_order"] == "0/1" and int(direction["positive_probability_column"]) == 1, f"classes={direction['class_order']}, positive column={direction['positive_probability_column']}")
        add(f"addon_auc_formula_agreement_{model}", near(direction["test_auc_sklearn"], direction["test_auc_mann_whitney"]), f"sklearn={direction['test_auc_sklearn']:.12f}, rank formula={direction['test_auc_mann_whitney']:.12f}")
        add(f"addon_static_test_auc_above_random_{model}", values["test_auc"] > 0.5, f"test AUC={values['test_auc']:.12f}")
    target_column = str(addon_quality["target_return_column"])
    add(
        "addon_target_column_present",
        target_column in addon_daily.columns and target_column in addon_walk_forward.columns,
        f"target column={target_column}",
    )
    add(
        "addon_label_matches_target",
        ((addon_daily[target_column] > 0).astype("Int64") == addon_daily["Label"].astype("Int64")).dropna().all(),
        f"label definition={target_column} > 0",
    )
    final_walk_auc = roc_auc_score(addon_walk_forward["Label"].astype(int), addon_walk_forward["probability"])
    add(
        "addon_final_walk_forward_auc",
        final_walk_auc > 0.5 and near(final_walk_auc, float(addon_metadata["final_test_auc"])),
        f"recomputed={final_walk_auc:.12f}, stored={float(addon_metadata['final_test_auc']):.12f}",
    )
    add(
        "addon_three_tuning_rounds",
        addon_tuning["round"].tolist() == [1, 2, 3]
        and addon_tuning.loc[addon_tuning["round"] == 1, "test_auc"].iloc[0] < 0.5
        and (addon_tuning.loc[addon_tuning["round"].isin([2, 3]), "test_auc"] > 0.5).all()
        and addon_tuning.loc[addon_tuning["selected"].astype(bool), "round"].tolist() == [3],
        "; ".join(
            f"round {int(row['round'])}: test AUC={row['test_auc']:.6f}, selected={bool(row['selected'])}"
            for _, row in addon_tuning.iterrows()
        ),
    )
    add("addon_label_alignment", int(addon_pipeline_diagnostics["label_mismatch_count"]) == 0, f"label mismatches={addon_pipeline_diagnostics['label_mismatch_count']}")
    add("addon_random_label_null", abs(float(addon_pipeline_diagnostics["random_label_auc_mean"]) - 0.5) < 0.03, f"mean random-label AUC={addon_pipeline_diagnostics['random_label_auc_mean']:.6f}")
    add("addon_synthetic_label_learnable", float(addon_pipeline_diagnostics["synthetic_label_auc"]) > 0.9, f"synthetic-label AUC={addon_pipeline_diagnostics['synthetic_label_auc']:.6f}")
    ranked_grid = addon_grid.assign(selection_sharpe=addon_grid["validation_sharpe"].fillna(-np.inf)).sort_values(
        ["selection_sharpe", "validation_total_return", "validation_max_drawdown", "validation_turnover"],
        ascending=[False, False, False, True],
    )
    selected_parameters = ranked_grid.iloc[0]
    signal = addon_metadata["signal"]
    add("addon_parameter_grid_27", len(addon_grid) == 27, f"grid rows={len(addon_grid)}")
    add(
        "addon_parameters_selected_on_validation",
        near(signal["buy_threshold"], selected_parameters["buy_threshold"])
        and near(signal["sell_threshold"], selected_parameters["sell_threshold"])
        and near(signal["max_position"], selected_parameters["max_position"]),
        f"selected=({signal['buy_threshold']},{signal['sell_threshold']},{signal['max_position']})",
    )
    for strategy, column in (("ml_timing", "ml_net_return"), ("buy_and_hold", "buy_hold_return"), ("moving_average", "ma_net_return")):
        total = float((1 + addon_strategy[column]).prod() - 1)
        add(f"addon_strategy_return_{strategy}", near(total, addon_strategy_metrics.loc[strategy, "total_return"]), f"stored={addon_strategy_metrics.loc[strategy, 'total_return']:.12f}, recomputed={total:.12f}")
    add("addon_three_strategy_comparison", set(addon_strategy_metrics.index) == {"ml_timing", "buy_and_hold", "moving_average"}, f"strategies={sorted(addon_strategy_metrics.index)}")
    add("addon_strategy_comparison_fields", {"total_return", "sharpe", "max_drawdown", "trade_count", "total_turnover"}.issubset(addon_strategy_metrics.columns), f"columns={list(addon_strategy_metrics.columns)}")
    add("addon_final_ml_return_positive", addon_strategy_metrics.loc["ml_timing", "total_return"] > 0, f"ML total return={addon_strategy_metrics.loc['ml_timing', 'total_return']:.12f}")

    weighted_returns = pd.read_csv(ENHANCED_PROCESSED_DIR / "main_weighted_quarterly_returns.csv")
    weighted_holdings = pd.read_csv(ENHANCED_PROCESSED_DIR / "main_weighted_holdings.csv", dtype={"Code": "string"})
    weighted_metrics = pd.read_csv(ENHANCED_PROCESSED_DIR / "main_weighted_strategy_metrics.csv").set_index("portfolio_label")
    weight_grid = pd.read_csv(ENHANCED_PROCESSED_DIR / "main_weight_grid.csv")
    guarded_auc = pd.read_csv(ENHANCED_PROCESSED_DIR / "additional_guarded_auc_grid.csv").set_index("candidate")
    add("enhanced_weight_sums", np.allclose(weighted_holdings.groupby(["portfolio_label", "Date"])["weight"].sum(), 1.0), "all portfolio-date weights sum to 1")
    add("enhanced_weight_caps", bool((weighted_holdings["weight"] <= weighted_holdings["weight_cap"] + 1e-10).all()), f"maximum excess={(weighted_holdings['weight']-weighted_holdings['weight_cap']).max():.3e}")
    add("enhanced_cost_identity", np.allclose(weighted_returns["net_return"], weighted_returns["gross_return"] - ONE_WAY_COST * weighted_returns["turnover"]), "net = gross - 20bp * turnover")
    add("enhanced_ew_pw_present", {"EW_Top30", "PW_Top30", "Validation_Selected"} == set(weighted_metrics.index), f"portfolios={sorted(weighted_metrics.index)}")
    add("enhanced_pw_improves_test_return", weighted_metrics.loc["PW_Top30", "total_return"] > weighted_metrics.loc["EW_Top30", "total_return"], f"PW={weighted_metrics.loc['PW_Top30','total_return']:.6f}, EW={weighted_metrics.loc['EW_Top30','total_return']:.6f}")
    chosen = weight_grid.sort_values(["selection_score", "validation_total_return", "validation_average_turnover"], ascending=[False, False, True]).iloc[0]
    selected_metric = weighted_metrics.loc["Validation_Selected"]
    add("enhanced_grid_selected_on_validation", int(chosen.top_n) == int(selected_metric.top_n) and chosen.weight_method == selected_metric.weight_method and near(chosen.power, selected_metric.power) and near(chosen.weight_cap, selected_metric.weight_cap), f"selected n={int(chosen.top_n)}, method={chosen.weight_method}")
    add("enhanced_auc_baseline_retained", guarded_auc.loc["existing_baseline", "test_auc"] > guarded_auc.loc["validation_winner", "test_auc"] > 0.5, f"baseline={guarded_auc.loc['existing_baseline','test_auc']:.6f}, grid winner={guarded_auc.loc['validation_winner','test_auc']:.6f}")
    manifest = pd.read_json(ENHANCED_METADATA_DIR / "pickle_manifest.json", typ="series")["models"]
    pickle_files = [Path(item["file"]) for item in manifest]
    loadable = True
    for model_file in pickle_files:
        try:
            with model_file.open("rb") as handle:
                payload = pickle.load(handle)
            loadable &= isinstance(payload, dict) and ("model" in payload or "estimator" in payload)
        except Exception:
            loadable = False
    add("enhanced_pickle_bundles_loadable", len(pickle_files) == 10 and loadable, f"loadable pickle count={len(pickle_files)}")
    dashboard = TASK_DIR / "dashboard" / "index.html"
    add("enhanced_dashboard_exists", dashboard.exists() and dashboard.stat().st_size > 100_000, f"dashboard bytes={dashboard.stat().st_size if dashboard.exists() else 0}", severity="medium")
    dashboard_artifact_path = TASK_DIR / "dashboard" / "artifact.json"
    dashboard_artifact = json.loads(dashboard_artifact_path.read_text(encoding="utf-8")) if dashboard_artifact_path.exists() else {}
    dashboard_manifest = dashboard_artifact.get("manifest", {})
    add("enhanced_dashboard_is_explanatory", len(dashboard_manifest.get("blocks", [])) >= 20 and len(dashboard_manifest.get("charts", [])) >= 6 and len(dashboard_manifest.get("tables", [])) >= 4 and len(dashboard_manifest.get("cards", [])) >= 7, f"blocks={len(dashboard_manifest.get('blocks', []))}, charts={len(dashboard_manifest.get('charts', []))}, tables={len(dashboard_manifest.get('tables', []))}, cards={len(dashboard_manifest.get('cards', []))}", severity="medium")
    add("enhanced_dashboard_no_recording_reference", "recording" not in json.dumps(dashboard_artifact, ensure_ascii=False).lower(), "dashboard uses course-method wording", severity="medium")
    regression_html = TASK_DIR / "dashboard" / "tools/csv_regression.html"
    regression_text = regression_html.read_text(encoding="utf-8") if regression_html.exists() else ""
    add("enhanced_regression_tool_is_standalone_html", regression_html.exists() and "parseCSV" in regression_text and "<script src=" not in regression_text, f"html bytes={regression_html.stat().st_size if regression_html.exists() else 0}", severity="medium")
    add("enhanced_regression_tool_has_no_backend", not (TASK_DIR / "dashboard" / "csv_regression_app.py").exists() and all(token not in regression_text for token in ("fetch(", "XMLHttpRequest", "indexedDB", "localStorage")), "no Flask file, network request, or browser database", severity="medium")

    chart_files = sorted(CHART_DIR.glob("figure*.png"))
    add("all_15_charts_exist", len(chart_files) == 15 and all(path.stat().st_size > 30_000 for path in chart_files), f"chart count={len(chart_files)}, smallest bytes={min(path.stat().st_size for path in chart_files) if chart_files else 0}", severity="medium")

    failed = [check for check in checks if not check["passed"]]
    report = {
        "validated_at": datetime.now().astimezone().isoformat(),
        "overall_assessment": "ready_to_share_with_caveats" if not failed else "needs_revision",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": failed,
        "checks": checks,
        "required_caveats": [
            "Main-test annualized statistics are based on only three quarterly observations.",
            "The source panel does not include actual financial-statement publication timestamps.",
            "The source universe lacks point-in-time membership and full tradability fields.",
            "The additional case has overlapping 3-day labels and a short single-stock history.",
            "Three tuning rounds inspected the same test window, so the final additional-case result is exploratory.",
        ],
    }
    write_json(MAIN_METADATA_DIR / "validation_report.json", report)
    write_json(ADDON_METADATA_DIR / "validation_report.json", report)
    print(f"[validation] {report['overall_assessment']}: {report['checks_passed']}/{report['checks_total']} checks passed")
    if failed:
        for check in failed:
            print(f"FAIL {check['check']}: {check['evidence']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
