#!/usr/bin/env python3
"""Build the source-backed portable TASK5 CATL dashboard."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dashboard_runtime import data_analytics_plugin_root


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "data" / "task5" / "catl" / "results"
PROCESSED = ROOT / "data" / "task5" / "catl" / "processed"
DASHBOARD = ROOT / "Task5" / "dashboard"
PAGES = DASHBOARD / "pages"
ARTIFACTS = DASHBOARD / "artifacts"
ARTIFACT = ARTIFACTS / "catl.json"
OUTPUT = PAGES / "catl.html"
PLUGIN_ROOT = data_analytics_plugin_root()

MODEL_NAMES = {
    "logistic_regression": "Logistic Regression", "decision_tree": "Decision tree",
    "random_forest": "Random Forest", "gradient_boosting": "gradient boost",
}


def records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.replace([np.inf, -np.inf], np.nan).where(pd.notna(frame), None)
    return clean.to_dict("records")


def source(source_id: str, label: str, relative_path: str, description: str, definitions: list[str]) -> dict:
    return {
        "id": source_id,
        "label": label,
        "path": relative_path,
        "query": {
            "engine": "duckdb", "language": "sql",
            "sql": f"SELECT * FROM read_csv_auto('{relative_path}', header=true)",
            "description": description, "tables_used": [relative_path],
            "filters": ["CATL300750.SZ", "Shanghai and Shenzhen300000300.SH", "Weekend Observations", "The future20Excess Return on Trading Day Tag", "2025Final Test"],
            "metric_definitions": definitions,
        },
    }


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(RESULT / "model_metrics.csv")
    tuning = pd.read_csv(RESULT / "model_tuning.csv")
    predictions = pd.read_csv(RESULT / "test_predictions.csv", parse_dates=["Date"])
    roc = pd.read_csv(RESULT / "roc_points.csv")
    coefficients = pd.read_csv(RESULT / "logistic_coefficients.csv")
    importance = pd.read_csv(RESULT / "tree_importances.csv")
    feature_audit = pd.read_csv(RESULT / "univariate_audit.csv")
    decisions = pd.read_csv(RESULT / "feature_decisions.csv")
    vif = pd.read_csv(RESULT / "final_vif.csv")
    samples = pd.read_csv(PROCESSED / "weekly_samples.csv", parse_dates=["Date", "label_end_date"])

    best_tuning = tuning.sort_values(
        ["mean_validation_auc", "std_validation_auc"], ascending=[False, True]
    ).groupby("model", as_index=False).head(1)
    metric_data = metrics.merge(
        best_tuning[["model", "mean_validation_auc", "std_validation_auc", "auc_2021", "auc_2022", "auc_2023", "auc_2024"]],
        on="model", how="left",
    )
    metric_data["model_label"] = metric_data["model"].map(MODEL_NAMES)
    metric_data["test_rows"] = int(predictions[predictions.model == "decision_tree"].shape[0])
    metric_data["auc_ci"] = metric_data.apply(lambda r: f"{r.auc_ci_low:.3f}-{r.auc_ci_high:.3f}", axis=1)
    metric_data["auc_minus_random"] = metric_data["roc_auc"] - 0.5
    # The portable reader also has a semantic fallback that reads the first row
    # before interactive filters initialise. Keep the dashboard headline aligned
    # with the frozen best test model in both modes.
    model_order = {"decision_tree": 0, "gradient_boosting": 1, "random_forest": 2, "logistic_regression": 3}
    metric_data["display_order"] = metric_data["model"].map(model_order)
    metric_data = metric_data.sort_values("display_order").reset_index(drop=True)

    validation = best_tuning.melt(
        id_vars=["model"], value_vars=["auc_2021", "auc_2022", "auc_2023", "auc_2024"],
        var_name="validation_year", value_name="auc",
    )
    validation["validation_year"] = validation["validation_year"].str[-4:] + "year"
    validation["model_label"] = validation["model"].map(MODEL_NAMES)

    roc["model_label"] = roc["model"].map(MODEL_NAMES)
    roc = roc.merge(metric_data[["model", "roc_auc"]], on="model", how="left")

    confusion_rows = []
    for row in metric_data.itertuples(index=False):
        for actual, predicted, value in [
            (0, 0, row.tn), (0, 1, row.fp), (1, 0, row.fn), (1, 1, row.tp),
        ]:
            denom = row.tn + row.fp if actual == 0 else row.fn + row.tp
            confusion_rows.append({
                "model": row.model, "model_label": row.model_label,
                "actual_label": "Actual no win 0" if actual == 0 else "Actual win 1",
                "predicted_label": "Predictions not outperforming 0" if predicted == 0 else "Forecast to win 1",
                "count": int(value), "row_rate": float(value / denom),
            })
    confusion = pd.DataFrame(confusion_rows)
    decision_confusion = confusion[confusion["model"] == "decision_tree"].copy()

    explanation = pd.concat([
        coefficients.assign(model="logistic_regression", model_label="Logistic Regression", value=coefficients["coefficient"], value_type="Standardized coefficient")
            [["model", "model_label", "feature", "feature_cn", "value", "value_type"]],
        importance.assign(value=importance["importance"], value_type="Importance of Purity")
            [["model", "model_cn", "feature", "feature_cn", "value", "value_type"]]
            .rename(columns={"model_cn": "model_label"}),
    ], ignore_index=True)
    explanation["absolute_value"] = explanation["value"].abs()
    explanation["rank"] = explanation.groupby("model")["absolute_value"].rank(method="first", ascending=False).astype(int)
    decision_explanation = explanation[explanation["model"] == "decision_tree"].copy()

    yearly = samples.groupby(samples.Date.dt.year).target.agg(["count", "mean"]).reset_index()
    yearly.columns = ["year", "rows", "positive_rate"]
    yearly["year"] = yearly["year"].astype(str) + "year"
    yearly["period"] = np.where(yearly.year == "2025year", "Final Test", "Development period")

    selected = decisions[decisions.selected_final].merge(
        feature_audit[["feature", "mean_auc", "std_auc", "years_above_0_5"]], on="feature", how="left"
    ).merge(vif[["feature", "vif"]], on="feature", how="left")
    selected = selected[["feature", "feature_cn", "mean_auc", "std_auc", "years_above_0_5", "vif", "reason"]]

    # Freeze the exact dashboard-facing extracts so every source link is auditable.
    extracts = {
        "dashboard_model_metrics.csv": metric_data,
        "dashboard_validation_auc.csv": validation,
        "dashboard_decision_tree_confusion.csv": decision_confusion,
        "dashboard_decision_tree_importance.csv": decision_explanation,
        "dashboard_yearly_labels.csv": yearly,
        "dashboard_selected_features.csv": selected,
    }
    for name, frame in extracts.items():
        frame.to_csv(RESULT / name, index=False, encoding="utf-8")

    sources = [
        source("metrics_source", "Final Test Model Metrics", "data/task5/catl/results/dashboard_model_metrics.csv", "Four locking models in2025Classification indicators on weekly test samples. ", ["ROC-AUCuseY=1probability calculation. ", "confusion matrix indicator usage0.5Threshold. ", "AUCinterval use4Week Move Time BlockBootstrap. "]),
        source("validation_source", "Rolling development validation", "data/task5/catl/results/dashboard_validation_auc.csv", "The 4 model lock parameter is in2021 - 2024Extended window ofAUC. ", ["Trained with earlier data per fold. ", "Training samplelabel_end_dateEarlier than the validation year start point. "]),
        source("roc_source", "ROCCurve Point", "data/task5/catl/results/roc_points.csv", "2025Generated by adjusting the classification threshold on the final testFPRandTPR. ", ["Each model is in the same group.48Evaluated on a weekly sample of items. "]),
        source("confusion_source", "decision tree confusion matrix", "data/task5/catl/results/dashboard_decision_tree_confusion.csv", "2025In the final test, the actual class of the decision tree and0.5Cross-tabulation of threshold prediction categories. ", ["row_rateProportion of Predictions Within Each Actual Category. "]),
        source("explanation_source", "Decision Tree Feature Importance", "data/task5/catl/results/dashboard_decision_tree_importance.csv", "2025yearAUCFeature importance of the highest model in the development period training. ", ["Impurity importance indicates how the model is used., does not indicate a causal relationship. "]),
        source("samples_source", "Weekly Modeling Sample", "data/task5/catl/processed/weekly_samples.csv", "Features on the last trading day of each natural week., 20Excess returns of the Japanese market and0/1Tags. ", ["Y=1If and only if the future of Ningde era20Trading day earnings higher than Shanghai and Shenzhen300. ", "AllXOnly using data from the observation day and earlier. "]),
        source("feature_source", "Final Selected Features", "data/task5/catl/results/dashboard_selected_features.csv", "Only according2018 - 2024Development Phase RollingAUC, Relevance andVIFSelected variables. ", ["mean_aucYes2021 - 2024Average univariate logistic regression over four rolling validation years.AUC. ", "VIFTarget below5. "]),
    ]

    cards = [
        {"id": "auc", "description": "2025Annual Probability Ranking Capability; 0.5Approaching Random. ", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "2025 ROC-AUC", "field": "roc_auc", "format": "number"}]},
        {"id": "validation", "description": "2021 - 2024Average of four extended windowsAUC. ", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Average development periodAUC", "field": "mean_validation_auc", "format": "number"}]},
        {"id": "balanced", "description": "0.5Under the threshold, take the average recall rate of the two categories. ", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Balanced Accuracy", "field": "balanced_accuracy", "format": "percent"}]},
        {"id": "precision", "description": "The proportion of samples predicted to outperform that actually outperform.. ", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Precision", "field": "precision", "format": "percent"}]},
        {"id": "recall", "description": "Proportion of actual outperforming samples identified by the model. ", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Recall", "field": "recall", "format": "percent"}]},
        {"id": "rows", "description": "2025Year with complete20Weekly Observation of the Future Label of the Day. ", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Test sample", "field": "test_rows", "format": "compact"}]},
    ]

    charts = [
        {"id": "model_auc", "title": "4 kind of model2025yearAUC", "subtitle": "decision tree slightly higher0.5, But the uncertainty interval crosses the random benchmark", "type": "bar", "intent": "comparison", "dataset": "model_comparison", "sourceId": "metrics_source", "encodings": {"x": {"field": "model_label", "type": "nominal", "label": "model"}, "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"}, "tooltip": [{"field": "auc_ci", "type": "text", "label": "95%Interval"}]}, "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Sort", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "semantic"}, "layout": "full"},
        {"id": "yearly_labels", "title": "AnnualY=1proportion", "subtitle": "Label Baseline Rate Changes with Market Conditions, 2025Year is52.1%", "type": "bar", "intent": "comparison", "dataset": "yearly_labels", "sourceId": "samples_source", "encodings": {"x": {"field": "year", "type": "ordinal", "label": "Year"}, "y": {"field": "positive_rate", "type": "quantitative", "label": "Y=1proportion", "format": "percent"}, "color": {"field": "period", "type": "nominal", "label": "Data Segment"}, "tooltip": [{"field": "rows", "type": "quantitative", "label": "Weekly Sample", "format": "compact"}]}, "referenceLines": [{"axis": "y", "value": 0.5, "label": "50%", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "validation_auc", "title": "Cross-year validation of locked parametersAUC", "subtitle": "The 4 model is in2021 - 2024Stability in the Extended Window", "type": "line", "intent": "trend", "dataset": "validation_auc", "sourceId": "validation_source", "encodings": {"x": {"field": "validation_year", "type": "ordinal", "label": "Verification Year"}, "y": {"field": "auc", "type": "quantitative", "label": "ROC-AUC"}, "color": {"field": "model_label", "type": "nominal", "label": "model"}, "tooltip": [{"field": "model_label", "type": "text", "label": "model"}]}, "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Sort", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "roc", "title": "2025Year-end final testROCcurve", "subtitle": "4 models in the same group48Cross-Threshold Comparisons on Weekly Samples", "type": "line", "intent": "comparison", "dataset": "roc_points", "sourceId": "roc_source", "encodings": {"x": {"field": "fpr", "type": "quantitative", "label": "false positive rate FPR"}, "y": {"field": "tpr", "type": "quantitative", "label": "true positive rate TPR"}, "color": {"field": "model_label", "type": "nominal", "label": "model"}, "tooltip": [{"field": "model_label", "type": "text", "label": "model"}, {"field": "threshold", "type": "quantitative", "label": "probability threshold"}, {"field": "roc_auc", "type": "quantitative", "label": "AUC"}]}, "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "confusion", "title": "Decision tree0.5threshold confusion matrix", "subtitle": "2025yearAUCThe highest model: Less misjudgment, But miss a lot of actual outperforming samples", "type": "bar", "intent": "comparison", "dataset": "decision_confusion", "sourceId": "confusion_source", "encodings": {"x": {"field": "actual_label", "type": "nominal", "label": "Actual Category"}, "y": {"field": "row_rate", "type": "quantitative", "label": "Proportion within the category", "format": "percent"}, "color": {"field": "predicted_label", "type": "nominal", "label": "Prediction Category"}, "tooltip": [{"field": "count", "type": "quantitative", "label": "Sample size", "format": "compact"}]}, "settings": {"stacked": True}, "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "explanation", "title": "Decision Tree Feature Importance", "subtitle": "Importance reflects model split usage frequency and contribution, does not indicate a causal relationship", "type": "horizontalBar", "intent": "comparison", "dataset": "decision_explanation", "sourceId": "explanation_source", "encodings": {"x": {"field": "feature_cn", "type": "nominal", "label": "Feature"}, "y": {"field": "value", "type": "quantitative", "label": "Importance of Purity"}, "tooltip": [{"field": "rank", "type": "quantitative", "label": "Ranking"}]}, "settings": {"sort": "ascending", "showValues": True}, "palette": {"kind": "sequential"}, "layout": "full"},
    ]

    tables = [
        {"id": "model_table", "title": "Summary of 4 Model Results", "subtitle": "AUCProbability of use; Use of other disaggregated indicators0.5Threshold", "dataset": "model_comparison", "sourceId": "metrics_source", "defaultSort": {"field": "roc_auc", "direction": "desc"}, "density": "spacious", "columns": [{"field": "model_label", "label": "model", "type": "text"}, {"field": "mean_validation_auc", "label": "DevelopmentAUC", "format": "number"}, {"field": "roc_auc", "label": "2025 AUC", "format": "number"}, {"field": "auc_ci", "label": "95%Interval", "type": "text"}, {"field": "balanced_accuracy", "label": "Balanced Acc.", "format": "percent"}, {"field": "precision", "label": "Precision", "format": "percent"}, {"field": "recall", "label": "Recall", "format": "percent"}, {"field": "f1", "label": "F1", "format": "percent"}], "layout": "full"},
        {"id": "feature_table", "title": "Selected characteristics in development period", "subtitle": "Feature is enabled2025Locked before the annual test set", "dataset": "selected_features", "sourceId": "feature_source", "defaultSort": {"field": "mean_auc", "direction": "desc"}, "density": "spacious", "columns": [{"field": "feature_cn", "label": "Feature", "type": "text"}, {"field": "mean_auc", "label": "Moving averageAUC", "format": "number"}, {"field": "std_auc", "label": "AUCStandard deviation", "format": "number"}, {"field": "years_above_0_5", "label": "AUC>0.5Number of years", "format": "number"}, {"field": "vif", "label": "VIF", "format": "number"}, {"field": "reason", "label": "Reason for Retention", "type": "text"}], "layout": "full"},
    ]

    blocks = [
        {"id": "opening", "type": "markdown", "body": "## Results and Boundaries\n\n2025In the annual test, Decision treeAUCThe maximum is0.524, Time blockBootstrapinterval is0.349 - 0.691, Across0.5; The remaining three models also did not pass the predictive ability test.. AUCRecalculation and label checks did not find mechanical errors, 20Day label overlap, A small number of single-stock samples and insufficient information coverage are the main boundaries of the current design.. This is not a model that can be used for trading. ", "sourceId": "metrics_source"},
        {"id": "cards", "type": "metric-strip", "cardIds": [c["id"] for c in cards]},
        {"id": "model_auc_block", "type": "chart", "chartId": "model_auc", "layout": "full"},
        {"id": "yearly_labels_block", "type": "chart", "chartId": "yearly_labels", "layout": "half"},
        {"id": "validation_auc_block", "type": "chart", "chartId": "validation_auc", "layout": "half"},
        {"id": "roc_block", "type": "chart", "chartId": "roc", "layout": "half"},
        {"id": "confusion_block", "type": "chart", "chartId": "confusion", "layout": "half"},
        {"id": "explanation_block", "type": "chart", "chartId": "explanation", "layout": "full"},
        {"id": "model_table_block", "type": "table", "tableId": "model_table", "layout": "full"},
        {"id": "feature_table_block", "type": "table", "tableId": "feature_table", "layout": "full"},
        {"id": "caveats", "type": "markdown", "body": "## Reading the boundaries\n\n- In total370Weekly record, But of the adjacent weeks20Day label overlap, Full-period approximate independent window approx.91one, 2025About year12one. \n- The current interval is wide, Relational commutation cannot be distinguished, Weak signal and sampling fluctuation. \n- Pipeline checks can only rule out mechanical errors, Cannot prove that labels and data design are sufficient. \n- The model only predicts the direction of excess returns, No output amplitude, Trading costs or positions are not calculated. \n- Variables are not re-selected after the test set is opened, Che-in or post-reversal probability. "},
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1, "surface": "dashboard",
            "title": "Task 5 - Machine-Learning Case Studies: Ningde era relative to Shanghai and Shenzhen300Category",
            "description": "Weekend Predicts the Future of the Ningde Era20Does the last trading day outperform Shanghai and Shenzhen300, 2025Strict out-of-sample assessment in. ",
            "generatedAt": generated,
            "filters": [],
            "cards": cards, "charts": charts, "tables": tables, "sources": sources, "blocks": blocks,
        },
        "snapshot": {"version": 1, "generatedAt": generated, "status": "ready", "datasets": {
            "model_metrics": records(metric_data), "model_comparison": records(metric_data),
            "validation_auc": records(validation), "roc_points": records(roc), "decision_confusion": records(decision_confusion),
            "decision_explanation": records(decision_explanation), "yearly_labels": records(yearly), "selected_features": records(selected),
        }},
        "sources": sources,
        "package_info": {"originUrl": "artifact://task5-catl-relative-classification"},
    }
    ARTIFACT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    command = ["node", str(PLUGIN_ROOT / "skills/build-report/scripts/deliver_portable_artifact.mjs"), "--input", str(ARTIFACT), "--output", str(OUTPUT)]
    result = subprocess.run(command, cwd=PLUGIN_ROOT, text=True, capture_output=True)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    receipt = OUTPUT.with_suffix(".receipt.json")
    if receipt.exists():
        print(receipt.read_text(encoding="utf-8"))
    print(f"[done] dashboard -> {OUTPUT}")


if __name__ == "__main__":
    main()
