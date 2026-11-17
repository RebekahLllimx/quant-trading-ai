#!/usr/bin/env python3
"""Build the portable Task5 dashboard around experiment 2."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from dashboard_runtime import data_analytics_plugin_root
from experiment2_common import METADATA_DIR, MODEL_LABELS, PROCESSED_DIR, PROJECT_ROOT, TASK_DIR, ensure_directories, write_json


PLUGIN_ROOT = data_analytics_plugin_root()
DASHBOARD_DIR = TASK_DIR / "dashboard"
ARTIFACT_PATH = DASHBOARD_DIR / "artifact.json"
OUTPUT_PATH = DASHBOARD_DIR / "index.html"


def records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.replace([np.inf, -np.inf], np.nan).where(pd.notna(frame), None)
    return clean.to_dict("records")


def source(source_id: str, label: str, path: str, description: str, definitions: list[str]) -> dict:
    return {
        "id": source_id,
        "label": label,
        "path": path,
        "query": {
            "engine": "duckdb",
            "language": "sql",
            "sql": f"SELECT * FROM read_csv_auto('{path}', header=true)",
            "description": description,
            "tables_used": [path],
            "filters": ["Shanghai and ShenzhenA-share100Only freeze the stock pool", "End of Month Observation", "2025Annual Out-of-Sample Testing"],
            "metric_definitions": definitions,
        },
    }


def main() -> None:
    ensure_directories()
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    metrics_all = pd.read_csv(PROCESSED_DIR / "task5_experiment2_model_metrics.csv")
    model_order = ["logistic_regression", "decision_tree", "random_forest"]
    metrics = metrics_all[metrics_all["model"].isin(model_order)].copy()
    metrics["test_rows"] = 1065
    metrics["auc_ci"] = metrics.apply(lambda row: f"{row['auc_ci_low']:.3f}-{row['auc_ci_high']:.3f}", axis=1)
    predictions = pd.read_csv(PROCESSED_DIR / "task5_experiment2_test_predictions.csv", parse_dates=["Date"])
    roc = pd.read_csv(PROCESSED_DIR / "task5_experiment2_roc_points.csv")
    importance = pd.read_csv(PROCESSED_DIR / "task5_experiment2_feature_importance.csv")
    split = pd.read_csv(METADATA_DIR / "split_summary.csv")
    yearly = pd.read_csv(METADATA_DIR / "yearly_label_summary.csv")

    feature_labels = {
        "return_1d": "1daily earnings", "return_5d": "5daily earnings", "return_10d": "10daily earnings", "return_20d": "20daily earnings",
        "ma5_gap": "Price/MA5-1", "ma20_gap": "Price/MA20-1", "ma60_gap": "Price/MA60-1", "rsi14": "RSI14",
        "macd_pct": "MACD/Price", "atr14_pct": "ATR14/Price", "volatility20": "20daily volatility",
        "volume_ratio20": "Volume ratio20day", "amount_ratio20": "Turnover ratio20day", "intraday_range": "intraday amplitude",
        "open_close_return": "Open Closing Earnings", "excess_return_5d": "relative market5daily earnings",
        "excess_return_20d": "relative market20daily earnings", "return_20d_rank": "20Daily Return Cross-Section Ranking",
        "market_median_return_5d": "Market5Median Daily Earnings", "market_median_return_20d": "Market20Median Daily Earnings",
        "market_breadth_20d": "Market20Daily Upside Breadth", "market_dispersion_20d": "Market20Daily Return Dispersion",
    }
    importance["feature_label"] = importance["feature"].map(feature_labels)
    importance["rank"] = importance.groupby("model")["absolute_importance"].rank(method="first", ascending=False).astype(int)
    importance = importance[importance["rank"] <= 12].copy()

    confusion_rows = []
    for (model, model_label), part in predictions.groupby(["model", "model_label"], sort=False):
        matrix = confusion_matrix(part["Label"], part["prediction"], labels=[0, 1])
        for actual in range(2):
            for predicted in range(2):
                confusion_rows.append(
                    {
                        "model": model,
                        "model_label": model_label,
                        "actual_label": "Actual does not rise" if actual == 0 else "actual rise",
                        "predicted_label": "The forecast does not rise." if predicted == 0 else "Forecast rise",
                        "count": int(matrix[actual, predicted]),
                        "row_rate": float(matrix[actual, predicted] / matrix[actual].sum()),
                    }
                )
    confusion_frame = pd.DataFrame(confusion_rows)

    comparison_rows = []
    first_auc = {"logistic_regression": 0.5210, "decision_tree": 0.5068, "random_forest": 0.5189}
    for model in model_order:
        model_label = MODEL_LABELS[model]
        comparison_rows.append({"model": model, "model_label": model_label, "scheme": "Baseline scenario: Daily5day", "auc": first_auc[model]})
        comparison_rows.append({"model": model, "model_label": model_label, "scheme": "Adjustment Plan: End of the month20day", "auc": float(metrics.set_index("model").at[model, "auc"])})
    comparison = pd.DataFrame(comparison_rows)

    split["split_label"] = split["Split"].map({"train": "Training set", "validation": "Validation set", "development": "Development Kit", "test": "Test set"})
    yearly["Year"] = yearly["Year"].astype(str)
    yearly["split_label"] = yearly["Split"].map({"train": "Training period", "validation": "Verification period", "development": "Development period", "test": "Test Period"})
    run = json.loads((METADATA_DIR / "model_run.json").read_text(encoding="utf-8"))
    generated_at = run["created_at"]

    sources = [
        source("metrics_source", "Adjustment Plan Model Metrics", "data/task5/experiment2/processed/task5_experiment2_model_metrics.csv", "After locking the design in2025Year Test Set Calculation. ", ["AUCUse Rising Probability. ", "Accuracy, Precision, Recall, F1use0.5classification threshold. "]),
        source("predictions_source", "2025Sample-by-sample prediction", "data/task5/experiment2/processed/task5_experiment2_test_predictions.csv", "Each Stock's Future at the End of Each Month20Probability of a daily increase. ", ["A record is a stock, One month-end and one model. "]),
        source("dataset_source", "End-of-Month Feature Label Panel", "data/task5/experiment2/processed/task5_experiment2_dataset.csv", "Price Volume, Relative strength and contemporaneous market condition features. ", ["Label=1If and only if the future20The return on the trading day is greater than0. ", "All features by observation date. "]),
        source("importance_source", "Model Feature Importance", "data/task5/experiment2/processed/task5_experiment2_feature_importance.csv", "Standardized logistic regression coefficients and tree model impurity importance.. ", ["Model dependence does not equal causal effect. "]),
    ]

    cards = []
    for card_id, label, field, fmt, description in [
        ("auc", "2025 AUC", "auc", "number", "Cross-threshold sorting capability; 0.5Approaching Random. "),
        ("accuracy", "Accuracy", "accuracy", "percent", "0.5Overall correct classification ratio under threshold. "),
        ("precision", "Accuracy rate", "precision", "percent", "The proportion of actual increases during predicted increases. "),
        ("recall", "Recall rate", "recall", "percent", "Proportion identified during the actual rise. "),
        ("f1", "F1", "f1", "percent", "Harmonic mean of precision and recall. "),
        ("rows", "Test sample", "test_rows", "compact", "2025year11Month-end stock sample. "),
    ]:
        cards.append({"id": card_id, "description": description, "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": label, "field": field, "format": fmt}]})

    charts = [
        {
            "id": "experiment_comparison", "title": "Out-of-sample for two rounds of program adjustmentAUC", "subtitle": "The target is different from the test period, Used to diagnose whether target adjustment improves information content", "type": "bar", "intent": "comparison", "dataset": "experiment_comparison", "sourceId": "metrics_source",
            "encodings": {"x": {"field": "model_label", "type": "nominal", "label": "model"}, "y": {"field": "auc", "type": "quantitative", "label": "AUC"}, "color": {"field": "scheme", "type": "nominal", "label": "Plan"}, "tooltip": [{"field": "auc", "type": "quantitative", "label": "AUC"}]},
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Sort", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "full",
        },
        {
            "id": "yearly_label", "title": "The future20Daily increase ratio", "subtitle": "The baseline rate of labels varies significantly with market years", "type": "bar", "intent": "comparison", "dataset": "yearly_labels", "sourceId": "dataset_source",
            "encodings": {"x": {"field": "Year", "type": "ordinal", "label": "Year"}, "y": {"field": "positive_rate", "type": "quantitative", "label": "Rising proportion", "format": "percent"}, "color": {"field": "split_label", "type": "nominal", "label": "Data Segment"}, "tooltip": [{"field": "rows", "type": "quantitative", "label": "Sample size", "format": "compact"}]},
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "50%", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "roc", "title": "2025yearROCcurve", "subtitle": "Logistic regression slightly higher than random, Tree Model Did Not Maintain Validation Period Advantage", "type": "line", "intent": "comparison", "dataset": "roc_points", "sourceId": "metrics_source",
            "encodings": {"x": {"field": "fpr", "type": "quantitative", "label": "false positive rate FPR"}, "y": {"field": "tpr", "type": "quantitative", "label": "The true rate TPR"}, "color": {"field": "model_label", "type": "nominal", "label": "model"}, "tooltip": [{"field": "threshold", "type": "quantitative", "label": "Threshold"}, {"field": "auc", "type": "quantitative", "label": "AUC"}]},
            "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "confusion", "title": "0.5Threshold Classification Results", "subtitle": "Show predicted distribution by true category", "type": "bar", "intent": "comparison", "dataset": "confusion", "sourceId": "predictions_source",
            "encodings": {"x": {"field": "actual_label", "type": "nominal", "label": "Real Label"}, "y": {"field": "row_rate", "type": "quantitative", "label": "Proportion within the category", "format": "percent"}, "color": {"field": "predicted_label", "type": "nominal", "label": "Prediction"}, "tooltip": [{"field": "count", "type": "quantitative", "label": "Sample size", "format": "compact"}]},
            "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "importance", "title": "former12Item Model Interpretation Value", "subtitle": "Logistic regression has positive and negative directions; tree model is non-negative importance", "type": "horizontalBar", "intent": "comparison", "dataset": "importance", "sourceId": "importance_source",
            "encodings": {"x": {"field": "feature_label", "type": "nominal", "label": "Feature"}, "y": {"field": "importance", "type": "quantitative", "label": "Interpretation value"}, "tooltip": [{"field": "rank", "type": "quantitative", "label": "Absolute Importance Ranking"}, {"field": "importance_type", "type": "text", "label": "Caliber"}]},
            "referenceLines": [{"axis": "y", "value": 0, "label": "zero", "color": "neutral"}], "settings": {"sort": "ascending", "showValues": True}, "palette": {"kind": "diverging", "midpoint": 0}, "layout": "full",
        },
    ]

    tables = [
        {
            "id": "model_table", "title": "Adjustment Plan: 2025Annual Test Metrics", "subtitle": "AUCUsing probability; The remaining indicators are used0.5Threshold", "dataset": "model_comparison", "sourceId": "metrics_source", "defaultSort": {"field": "auc", "direction": "desc"}, "density": "spacious",
            "columns": [{"field": "model_label", "label": "model", "type": "text"}, {"field": "auc", "label": "AUC", "format": "number"}, {"field": "auc_ci", "label": "AUC 95%Interval", "type": "text"}, {"field": "accuracy", "label": "Accuracy", "format": "percent"}, {"field": "precision", "label": "Precision", "format": "percent"}, {"field": "recall", "label": "Recall", "format": "percent"}, {"field": "f1", "label": "F1", "format": "percent"}], "layout": "full",
        },
        {
            "id": "split_table", "title": "time series division", "subtitle": "End-of-month stock sample; Crossing the year-end boundary20The day tag has been deleted.", "dataset": "split_summary", "sourceId": "dataset_source", "defaultSort": {"field": "start", "direction": "asc"}, "density": "spacious",
            "columns": [{"field": "split_label", "label": "Data Segment", "type": "text"}, {"field": "start", "label": "Start Date", "type": "date"}, {"field": "end", "label": "End Date", "type": "date"}, {"field": "rows", "label": "Sample size", "format": "compact"}, {"field": "months", "label": "Number of months", "format": "number"}, {"field": "positive_rate", "label": "Rising proportion", "format": "percent"}], "layout": "full",
        },
    ]

    blocks = [
        {"id": "opening", "type": "markdown", "body": "## Key Findings\n\nAdjust the plan to change the issue to predicting the future at the end of the month.20The absolute rise and fall of the trading day. Logistic Regression2025yearAUCFor0.529, than the baseline scenario0.521Slightly higher; decision trees and random forests are below0.5, It indicates that extending the period only brought limited and model-dependent improvements., Complex models do not have stable extrapolation after market condition changes.. ", "sourceId": "metrics_source"},
        {"id": "workflow", "type": "markdown", "body": "## Nine-step combat route\n\n1. PrepareAPIFreeze the market and do coverage, Missing, Label drift and profit distribution exploration; 2. Constructing the future20Daily Absolute Gain/Loss Tag; 3. Select price and quantity, Relative strength and market state features; 4. Press2018-2022training, 2023Verification, 2024Development, 2025Test execution time isolation; 5. Train three types of models and lock parameters before testing.; 6. Output2025Probability of increase; 7. useAUC, ROCand confusion matrix evaluation; 8. View standardized coefficients and feature importance; 9. Save Model, Prediction, Indicator, Hash and33Item verification result. ", "sourceId": "dataset_source"},
        {"id": "cards", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "comparison_block", "type": "chart", "chartId": "experiment_comparison", "layout": "full"},
        {"id": "yearly_block", "type": "chart", "chartId": "yearly_label", "layout": "half"},
        {"id": "roc_block", "type": "chart", "chartId": "roc", "layout": "half"},
        {"id": "confusion_block", "type": "chart", "chartId": "confusion", "layout": "half"},
        {"id": "importance_block", "type": "chart", "chartId": "importance", "layout": "full"},
        {"id": "model_table_block", "type": "table", "tableId": "model_table", "layout": "full"},
        {"id": "split_table_block", "type": "table", "tableId": "split_table", "layout": "full"},
        {"id": "caveats", "type": "markdown", "body": "## Use boundaries\n\n- BestAUCBlock bootstrap method95%interval is approximately0.499 - 0.587, Still Touching Random Benchmark. \n- Objectives of the two-round programme, Different frequency and test intervals, Compare for diagnosis, It's not a strict model competition.. \n- This task only evaluates the classification ability, No handling fee calculated, Slippage or portfolio returns. \n- Stock pool by2018Liquidity freeze at the beginning of the year, Not historical index components on a period-by-period basis. \n- Model Importance Does Not Indicate Causal Effect. "},
    ]

    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1, "surface": "dashboard", "title": "Task 5 - Machine-Learning Case Studies: Shanghai and ShenzhenAStock rise and fall classification", "description": "AFuture of Stock Month End20Daily Gain/Loss Classification, And with daily5Comparison of Daily Baseline Scenarios. ", "generatedAt": generated_at,
            "filters": [{"id": "model_filter", "label": "model", "dataset": "model_metrics", "field": "model_label", "defaultValue": "Logistic Regression", "includeAll": False, "targets": [{"dataset": "model_metrics", "field": "model_label"}, {"dataset": "roc_points", "field": "model_label"}, {"dataset": "confusion", "field": "model_label"}, {"dataset": "importance", "field": "model_label"}]}],
            "cards": cards, "charts": charts, "tables": tables, "sources": sources, "blocks": blocks,
        },
        "snapshot": {"version": 1, "generatedAt": generated_at, "status": "ready", "datasets": {"model_metrics": records(metrics), "model_comparison": records(metrics), "experiment_comparison": records(comparison), "yearly_labels": records(yearly), "roc_points": records(roc), "confusion": records(confusion_frame), "importance": records(importance), "split_summary": records(split)}},
        "sources": sources,
        "package_info": {"originUrl": "artifact://task5-experiment2"},
    }
    write_json(ARTIFACT_PATH, artifact)
    command = ["node", str(PLUGIN_ROOT / "skills/build-report/scripts/deliver_portable_artifact.mjs"), "--input", str(ARTIFACT_PATH), "--output", str(OUTPUT_PATH)]
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    print(f"[done] dashboard -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
