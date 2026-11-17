#!/usr/bin/env python3
"""Build the canonical portable HTML dashboard artifact for Task5."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

from dashboard_runtime import data_analytics_plugin_root
from task5_common import DASHBOARD_DIR, METADATA_DIR, MODEL_LABELS, PROCESSED_DIR, PROJECT_ROOT, ensure_directories, write_json


PLUGIN_ROOT = data_analytics_plugin_root()
ARTIFACT_PATH = DASHBOARD_DIR / "artifact.json"
OUTPUT_PATH = DASHBOARD_DIR / "index.html"


def records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.replace([np.inf, -np.inf], np.nan).where(pd.notna(frame), None)
    return clean.to_dict("records")


def downsample_roc(frame: pd.DataFrame, points: int = 160) -> pd.DataFrame:
    parts = []
    for _, part in frame.groupby("model", sort=False):
        part = part.sort_values("fpr").reset_index(drop=True)
        indexes = np.unique(np.linspace(0, len(part) - 1, min(points, len(part))).astype(int))
        parts.append(part.iloc[indexes])
    return pd.concat(parts, ignore_index=True)


def threshold_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, model_label), part in predictions.groupby(["model", "model_label"], sort=False):
        y = part["Label"].to_numpy()
        probability = part["probability"].to_numpy()
        for threshold in np.arange(0.05, 0.951, 0.05):
            predicted = (probability >= threshold).astype(int)
            tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
            rows.append(
                {
                    "model": model,
                    "model_label": model_label,
                    "threshold": round(float(threshold), 2),
                    "precision": float(precision_score(y, predicted, zero_division=0)),
                    "recall": float(recall_score(y, predicted, zero_division=0)),
                    "f1": float(f1_score(y, predicted, zero_division=0)),
                    "false_positive_rate": float(fp / (fp + tn)),
                    "predicted_positive_rate": float(predicted.mean()),
                    "predicted_positive": int(predicted.sum()),
                }
            )
    return pd.DataFrame(rows)


def confusion_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, model_label), part in predictions.groupby(["model", "model_label"], sort=False):
        matrix = confusion_matrix(part["Label"], part["prediction"], labels=[0, 1])
        for actual in range(2):
            denominator = matrix[actual].sum()
            for predicted in range(2):
                rows.append(
                    {
                        "model": model,
                        "model_label": model_label,
                        "actual": actual,
                        "actual_label": "Actual does not rise 0" if actual == 0 else "actual rise 1",
                        "predicted": predicted,
                        "predicted_label": "The forecast does not rise. 0" if predicted == 0 else "Forecast rise 1",
                        "count": int(matrix[actual, predicted]),
                        "row_rate": float(matrix[actual, predicted] / denominator),
                    }
                )
    return pd.DataFrame(rows)


def source_spec(source_id: str, label: str, path: str, description: str, definitions: list[str]) -> dict:
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
            "filters": ["Shanghai and ShenzhenA-share", "formal sample2018-02-01to2025-12-31", "Test set2024-01-01to2025-12-31"],
            "metric_definitions": definitions,
        },
    }


def main() -> None:
    ensure_directories()
    metrics = pd.read_csv(PROCESSED_DIR / "task5_model_metrics.csv")
    predictions = pd.read_csv(PROCESSED_DIR / "task5_test_predictions.csv", parse_dates=["Date"])
    yearly = pd.read_csv(PROCESSED_DIR / "task5_yearly_metrics.csv")
    roc = downsample_roc(pd.read_csv(PROCESSED_DIR / "task5_roc_points.csv"))
    importance = pd.read_csv(PROCESSED_DIR / "task5_feature_importance.csv")
    split_summary = pd.read_csv(METADATA_DIR / "split_summary.csv")
    yearly_labels = pd.read_csv(METADATA_DIR / "yearly_label_summary.csv")
    threshold = threshold_metrics(predictions)
    threshold = threshold.melt(
        id_vars=["model", "model_label", "threshold", "predicted_positive_rate", "predicted_positive"],
        value_vars=["precision", "recall", "f1"],
        var_name="metric",
        value_name="metric_value",
    )
    threshold["metric_label"] = threshold["metric"].map({"precision": "Precision", "recall": "Recall", "f1": "F1"})
    confusion = confusion_rows(predictions)

    model_order = ["logistic_regression", "decision_tree", "random_forest"]
    model_metrics = metrics[metrics["model"].isin(model_order)].copy()
    model_metrics["test_rows"] = int(predictions[predictions["model"] == model_order[0]].shape[0])
    model_metrics["auc_above_random"] = model_metrics["auc"] - 0.5
    model_metrics["auc_ci"] = model_metrics.apply(lambda row: f"{row['auc_ci_low']:.3f}-{row['auc_ci_high']:.3f}", axis=1)

    importance["feature_label"] = importance["feature"].map(
        {
            "return_1d": "1daily earnings",
            "return_5d": "5daily earnings",
            "return_10d": "10daily earnings",
            "return_20d": "20daily earnings",
            "ma5_gap": "Price/MA5-1",
            "ma20_gap": "Price/MA20-1",
            "ma60_gap": "Price/MA60-1",
            "rsi14": "RSI14",
            "macd_pct": "MACD/Price",
            "atr14_pct": "ATR14/Price",
            "volatility20": "20daily volatility",
            "volume_ratio20": "Volume ratio20day",
            "amount_ratio20": "Turnover ratio20day",
            "intraday_range": "intraday amplitude",
            "open_close_return": "Open Closing Earnings",
        }
    )
    importance["explanation_value"] = importance["importance"]
    importance["rank"] = importance.groupby("model")["absolute_importance"].rank(method="first", ascending=False).astype(int)
    yearly["year"] = yearly["year"].astype(str)
    yearly_labels["Year"] = yearly_labels["Year"].astype(str)
    yearly_labels["split_label"] = yearly_labels["Split"].map({"train": "Training period", "validation": "Verification period", "test": "Test Period"})
    split_summary["SplitLabel"] = split_summary["Split"].map({"train": "Training set", "validation": "Validation set", "test": "Test set"})

    generated_at = json.loads((METADATA_DIR / "model_run.json").read_text(encoding="utf-8"))["created_at"]
    metric_source = source_spec(
        "model_metrics_source",
        "Model Metrics on the Test Set",
        "data/task5/processed/task5_model_metrics.csv",
        "Recalculated from frozen test set probability predictionsAUCand0.5Threshold Classification Metrics. ",
        [
            "AUC=ROCArea under the curve, Use the upside probability instead0/1Prediction Label Calculation. ",
            "Accuracy=(TP+TN)/All test samples. ",
            "Precision=TP/(TP+FP), Recall=TP/(TP+FN), F1for the two to reconcile the average. ",
        ],
    )
    prediction_source = source_spec(
        "prediction_source",
        "Sample-by-sample prediction on the test set",
        "data/task5/processed/task5_test_predictions.csv",
        "Three kinds of locking model pairs2024 - 2025Probability of increase generated by the test sample and0.5threshold prediction. ",
        ["A single record is the model prediction of a stock on a test trading day.. ", "Threshold curve only changes display threshold, Don&#39;t retrain the model. "],
    )
    data_source = source_spec(
        "dataset_source",
        "APIFreeze Feature Labels Panel",
        "data/task5/processed/task5_ml_dataset.csv",
        "by2017 - 2025 APIMarket snapshot construction15Only ratio features using current day and historical information are applied.. ",
        ["Label=1 If and only if the future5Post-adjustment return greater than on trading days0. ", "Time is divided into2018 - 2022training, 2023Verification, 2024 - 2025Test. "],
    )
    importance_source = source_spec(
        "importance_source",
        "Model Explanation Results",
        "data/task5/processed/task5_feature_importance.csv",
        "Standardized coefficients of logistic regression and feature importance of impurity in tree models.. ",
        ["Coefficients and importance describe model dependencies, does not indicate a causal effect. "],
    )
    sources = [metric_source, prediction_source, data_source, importance_source]

    cards = []
    for card_id, label, field, fmt, description in [
        ("auc_card", "Test set AUC", "auc", "number", "Up and down ranking ability across all classification thresholds; 0.5Approaching Random. "),
        ("accuracy_card", "Accuracy", "accuracy", "percent", "In0.5Overall correct classification ratio under the classification threshold. "),
        ("precision_card", "Accuracy rate", "precision", "percent", "The proportion of samples predicted to rise that actually rise.. "),
        ("recall_card", "Recall rate", "recall", "percent", "Proportion of actual rising samples identified by the model. "),
        ("f1_card", "F1", "f1", "percent", "Harmonic mean of precision and recall. "),
        ("test_rows_card", "Test sample", "test_rows", "compact", "2024 - 2025Annual Stock - Sample number of trading days. "),
    ]:
        cards.append(
            {
                "id": card_id,
                "description": description,
                "dataset": "model_metrics",
                "sourceId": "model_metrics_source",
                "metrics": [{"label": label, "field": field, "format": fmt}],
            }
        )

    charts = [
        {
            "id": "yearly_auc",
            "title": "Test Period YearAUC",
            "subtitle": "Check separately2024and2025, Observe whether weak signals come only from a single year",
            "type": "bar",
            "intent": "comparison",
            "dataset": "yearly_metrics",
            "sourceId": "model_metrics_source",
            "encodings": {
                "x": {"field": "year", "type": "ordinal", "label": "Year"},
                "y": {"field": "auc", "type": "quantitative", "label": "AUC", "format": "number"},
                "tooltip": [
                    {"field": "accuracy", "type": "quantitative", "label": "Accuracy", "format": "percent"},
                    {"field": "f1", "type": "quantitative", "label": "F1", "format": "percent"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Benchmark", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "half",
        },
        {
            "id": "yearly_label_rate",
            "title": "Yearly Future5Daily increase ratio",
            "subtitle": "Label Baseline Rate Changes with Market Phases, 2023Annual minimum",
            "type": "bar",
            "intent": "comparison",
            "dataset": "yearly_labels",
            "sourceId": "dataset_source",
            "encodings": {
                "x": {"field": "Year", "type": "ordinal", "label": "Year"},
                "y": {"field": "positive_rate", "type": "quantitative", "label": "Rising proportion", "format": "percent"},
                "color": {"field": "split_label", "type": "nominal", "label": "Data Segment"},
                "tooltip": [{"field": "rows", "type": "quantitative", "label": "Sample size", "format": "compact"}],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "50%", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "categorical"},
            "layout": "half",
        },
        {
            "id": "roc_chart",
            "title": "Test setROCcurve",
            "subtitle": "The closer the curve is to the upper-left corner, The greater the ability to distinguish across thresholds",
            "type": "line",
            "intent": "comparison",
            "dataset": "roc_points",
            "sourceId": "model_metrics_source",
            "encodings": {
                "x": {"field": "fpr", "type": "quantitative", "label": "false positive rate FPR"},
                "y": {"field": "tpr", "type": "quantitative", "label": "The true rate TPR"},
                "color": {"field": "model_label", "type": "nominal", "label": "model"},
                "tooltip": [
                    {"field": "threshold", "type": "quantitative", "label": "Threshold"},
                    {"field": "auc", "type": "quantitative", "label": "AUC"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "TPR=0.5Reference", "color": "neutral", "lineStyle": "dotted"}],
            "palette": {"kind": "categorical"},
            "layout": "full",
        },
        {
            "id": "confusion_heatmap",
            "title": "0.5threshold confusion matrix",
            "subtitle": "The color represents the proportion within the same true category, Hover View Count",
            "type": "heatmap",
            "intent": "comparison",
            "dataset": "confusion",
            "sourceId": "prediction_source",
            "encodings": {
                "x": {"field": "predicted_label", "type": "nominal", "label": "Forecast Label"},
                "y": {"field": "row_rate", "type": "quantitative", "label": "Row Percentage", "format": "percent"},
                "color": {"field": "actual_label", "type": "nominal", "label": "Actual Label"},
                "tooltip": [{"field": "count", "type": "quantitative", "label": "Sample size", "format": "compact"}],
            },
            "palette": {"kind": "sequential"},
            "layout": "half",
        },
        {
            "id": "threshold_chart",
            "title": "classification threshold sensitivity",
            "subtitle": "Threshold only changes judgment rules, No changeAUCor retrain the model",
            "type": "line",
            "intent": "trend",
            "dataset": "threshold_metrics",
            "sourceId": "prediction_source",
            "encodings": {
                "x": {"field": "threshold", "type": "quantitative", "label": "Rising probability threshold"},
                "y": {"field": "metric_value", "type": "quantitative", "label": "Index value", "format": "percent"},
                "color": {"field": "metric_label", "type": "nominal", "label": "Indicator"},
                "tooltip": [
                    {"field": "predicted_positive_rate", "type": "quantitative", "label": "Proportion of forecast rise", "format": "percent"},
                    {"field": "predicted_positive", "type": "quantitative", "label": "Forecast rise sample", "format": "compact"},
                ],
            },
            "referenceLines": [{"axis": "x", "value": 0.5, "label": "Report Threshold", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "half",
        },
        {
            "id": "importance_chart",
            "title": "Model Feature Explanation Value",
            "subtitle": "Logistic regression for standardized coefficients with direction; Tree Model Uses Non-Negative Impurity Importance",
            "type": "horizontalBar",
            "intent": "comparison",
            "dataset": "importance",
            "sourceId": "importance_source",
            "encodings": {
                "x": {"field": "feature_label", "type": "nominal", "label": "Feature"},
                "y": {"field": "explanation_value", "type": "quantitative", "label": "Interpretation value"},
                "tooltip": [
                    {"field": "rank", "type": "quantitative", "label": "Absolute Importance Ranking"},
                    {"field": "importance_type", "type": "text", "label": "Explain the caliber"},
                ],
            },
            "referenceLines": [{"axis": "x", "value": 0, "label": "zero", "color": "neutral"}],
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "diverging", "midpoint": 0},
            "layout": "full",
        },
    ]

    tables = [
        {
            "id": "model_comparison",
            "title": "Testing results of the three models and the majority-class baseline.",
            "subtitle": "AUCProbability of use; The remaining indicators use fixed0.5Threshold",
            "dataset": "model_comparison",
            "sourceId": "model_metrics_source",
            "defaultSort": {"field": "auc", "direction": "desc"},
            "density": "spacious",
            "columns": [
                {"field": "model_label", "label": "model", "type": "text"},
                {"field": "auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "AUC 95%Interval", "type": "text"},
                {"field": "accuracy", "label": "Accuracy", "format": "percent"},
                {"field": "precision", "label": "Precision", "format": "percent"},
                {"field": "recall", "label": "Recall", "format": "percent"},
                {"field": "f1", "label": "F1", "format": "percent"},
            ],
            "layout": "full",
        },
        {
            "id": "split_table",
            "title": "training, Verification and Test Data Segment",
            "subtitle": "stock - Trading Day Sample; 5Day label cross-border sample cleared",
            "dataset": "split_summary",
            "sourceId": "dataset_source",
            "defaultSort": {"field": "start", "direction": "asc"},
            "density": "spacious",
            "columns": [
                {"field": "SplitLabel", "label": "Data Segment", "type": "text"},
                {"field": "start", "label": "Start Date", "type": "date"},
                {"field": "end", "label": "End Date", "type": "date"},
                {"field": "rows", "label": "Sample size", "format": "compact"},
                {"field": "symbols", "label": "Number of shares", "format": "number"},
                {"field": "positive_rate", "label": "Rising proportion", "format": "percent"},
            ],
            "layout": "full",
        },
    ]

    blocks = [
        {
            "id": "opening",
            "type": "markdown",
            "body": "## Summary\n\nTest sets of three modelsAUCAll are approaching.0.5. Logistic Regression Highest (0.521) , Random Forest (0.519) , It indicates that technical features only provide very weak directional ranking information., Cannot infer that the strategy is profitable based on this. Using the top model selector allows linked viewing of annual performance., Confusion matrix, Threshold Sensitivity and Feature Interpretation. ",
            "sourceId": "model_metrics_source",
        },
        {"id": "hero_metrics", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "yearly_auc_block", "type": "chart", "chartId": "yearly_auc", "layout": "half"},
        {"id": "yearly_label_block", "type": "chart", "chartId": "yearly_label_rate", "layout": "half"},
        {"id": "roc_block", "type": "chart", "chartId": "roc_chart", "layout": "full"},
        {"id": "confusion_block", "type": "chart", "chartId": "confusion_heatmap", "layout": "half"},
        {"id": "threshold_block", "type": "chart", "chartId": "threshold_chart", "layout": "half"},
        {"id": "importance_block", "type": "chart", "chartId": "importance_chart", "layout": "full"},
        {"id": "comparison_table_block", "type": "table", "tableId": "model_comparison", "layout": "full"},
        {"id": "split_table_block", "type": "table", "tableId": "split_table", "layout": "full"},
        {
            "id": "caveats",
            "type": "markdown",
            "body": "## Use boundaries\n\n- AUCslightly above0.5Only indicates that the ranking in the test period is slightly better than random., Not equal to profit after deducting transaction costs. \n- Stock pool by2018year1Median monthly turnover freeze, Not historical Shanghai and Shenzhen300Constituent stocks. \n- Most stock useTushareThe company action-adjusted return index compounded from daily price changes.; The model only uses scale-invariant features. \n- 0.5Lower recall under threshold, Reflecting Weak Signals and Training/Test baseline rate variation; This task did not use the test set to re-adjust thresholds. \n- Feature importance and logistic regression coefficients do not indicate causality.. ",
        },
    ]

    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "Task 5 - Machine-Learning Case Studies: AStock Price Rise and Fall Classification Assessment",
            "description": "100Only historically high liquidityA-share, The future5Daily Gain/Loss Classification, 2024 - 2025Strict out-of-sample testing. ",
            "generatedAt": generated_at,
            "filters": [
                {
                    "id": "model_filter",
                    "label": "model",
                    "dataset": "model_metrics",
                    "field": "model_label",
                    "defaultValue": MODEL_LABELS["logistic_regression"],
                    "includeAll": False,
                    "targets": [
                        {"dataset": "model_metrics", "field": "model_label"},
                        {"dataset": "yearly_metrics", "field": "model_label"},
                        {"dataset": "confusion", "field": "model_label"},
                        {"dataset": "threshold_metrics", "field": "model_label"},
                        {"dataset": "importance", "field": "model_label"},
                    ],
                }
            ],
            "cards": cards,
            "charts": charts,
            "tables": tables,
            "sources": sources,
            "blocks": blocks,
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {
                "model_metrics": records(model_metrics),
                "model_comparison": records(metrics),
                "yearly_metrics": records(yearly),
                "yearly_labels": records(yearly_labels),
                "roc_points": records(roc),
                "confusion": records(confusion),
                "threshold_metrics": records(threshold),
                "importance": records(importance),
                "split_summary": records(split_summary),
            },
        },
        "sources": sources,
        "package_info": {"originUrl": "artifact://task5-ai-trading-engine"},
    }
    write_json(ARTIFACT_PATH, artifact)
    command = [
        "node",
        str(PLUGIN_ROOT / "skills/build-report/scripts/deliver_portable_artifact.mjs"),
        "--input",
        str(ARTIFACT_PATH),
        "--output",
        str(OUTPUT_PATH),
    ]
    result = subprocess.run(command, cwd=PLUGIN_ROOT, text=True, capture_output=True)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    receipt_path = OUTPUT_PATH.with_suffix(".receipt.json")
    if receipt_path.exists():
        print(receipt_path.read_text(encoding="utf-8"))
    print(f"[done] dashboard -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
