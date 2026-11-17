#!/usr/bin/env python3
"""Build the source-backed portable TASK5 breast-cancer dashboard."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dashboard_runtime import data_analytics_plugin_root


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "data" / "task5" / "breast_cancer" / "results"
DASHBOARD = ROOT / "Task5" / "dashboard"
PAGES = DASHBOARD / "pages"
ARTIFACTS = DASHBOARD / "artifacts"
ARTIFACT = ARTIFACTS / "cancer.json"
OUTPUT = PAGES / "cancer.html"
PLUGIN_ROOT = data_analytics_plugin_root()

MODEL_NAMES = {
    "logistic_regression": "Logistic Regression",
    "decision_tree": "Decision tree",
    "random_forest": "Random Forest",
    "gradient_boosting": "gradient boost",
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
            "engine": "duckdb",
            "language": "sql",
            "sql": f"SELECT * FROM read_csv_auto('{relative_path}', header=true)",
            "description": description,
            "tables_used": [relative_path],
            "filters": [
                "scikit-learnBreast cancer diagnostic data",
                "Malignant recoding is1",
                "Layering80/20division",
                "random seed42",
                "Test set does not participate in feature filtering",
            ],
            "metric_definitions": definitions,
        },
    }


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(RESULT / "model_metrics.csv")
    tuning = pd.read_csv(RESULT / "model_tuning.csv")
    roc = pd.read_csv(RESULT / "roc_points.csv")
    grouped = pd.read_csv(RESULT / "grouped_feature_audit.csv")
    decisions = pd.read_csv(RESULT / "feature_decisions.csv")
    vif = pd.read_csv(RESULT / "final_vif.csv")
    coefficients = pd.read_csv(RESULT / "logistic_coefficients.csv")
    importance = pd.read_csv(RESULT / "tree_importances.csv")
    dataset = pd.read_csv(RESULT / "dataset.csv")
    summary_json = json.loads((RESULT / "summary.json").read_text(encoding="utf-8"))

    model_data = metrics.merge(
        tuning[["model", "cv_auc_mean", "cv_auc_std", "best_params"]],
        on="model",
        how="left",
    )
    model_data["model_label"] = model_data["model"].map(MODEL_NAMES)
    model_data["auc_ci"] = model_data.apply(
        lambda row: f"{row.auc_ci_low:.3f}to{row.auc_ci_high:.3f}", axis=1
    )
    model_order = {
        "logistic_regression": 0,
        "random_forest": 1,
        "gradient_boosting": 2,
        "decision_tree": 3,
    }
    model_data["display_order"] = model_data["model"].map(model_order)
    model_data = model_data.sort_values("display_order").reset_index(drop=True)

    roc["model_label"] = roc["model"].map(MODEL_NAMES)
    roc = roc.merge(model_data[["model", "roc_auc"]], on="model", how="left")

    threshold_metrics = model_data[[
        "model", "model_label", "balanced_accuracy", "precision",
        "recall", "specificity", "f1",
    ]].melt(
        id_vars=["model", "model_label"],
        var_name="metric",
        value_name="value",
    )
    metric_labels = {
        "balanced_accuracy": "Balanced Accuracy",
        "precision": "Precision",
        "recall": "False negative rate",
        "specificity": "Specificity",
        "f1": "F1",
    }
    threshold_metrics["metric_label"] = threshold_metrics["metric"].map(metric_labels)

    selected = (
        decisions[decisions.selected_final]
        .merge(grouped[[
            "feature", "cv_auc_mean", "cv_auc_std", "cv_auc_min",
            "direction_consistency", "direction",
        ]], on="feature", how="left")
        .merge(vif[["feature", "vif"]], on="feature", how="left")
    )
    selected = selected[[
        "feature", "feature_cn", "cv_auc_mean", "cv_auc_std", "cv_auc_min",
        "direction_consistency", "vif", "direction", "reason",
    ]].sort_values("cv_auc_mean", ascending=False)

    feature_stability = grouped.head(15)[[
        "feature", "feature_cn", "cv_auc_mean", "cv_auc_std",
        "cv_auc_min", "direction_consistency",
    ]].copy()

    explanation = pd.concat([
        coefficients.assign(
            model="logistic_regression",
            model_label="Logistic Regression",
            value=coefficients["coefficient"],
            value_type="Standardized coefficient",
        )[["model", "model_label", "feature", "feature_cn", "value", "value_type"]],
        importance[importance.model.isin(["random_forest", "gradient_boosting"])]
        .assign(value=lambda frame: frame["importance"], value_type="Importance of Purity")
        [["model", "model_cn", "feature", "feature_cn", "value", "value_type"]]
        .rename(columns={"model_cn": "model_label"}),
    ], ignore_index=True)
    explanation["absolute_value"] = explanation["value"].abs()
    explanation["rank"] = (
        explanation.groupby("model")["absolute_value"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    lr_explanation = explanation[explanation.model == "logistic_regression"].copy()
    rf_explanation = explanation[explanation.model == "random_forest"].copy()

    class_counts = (
        dataset.groupby(["split", "diagnosis"])
        .size()
        .rename("samples")
        .reset_index()
    )
    class_counts["class_rate"] = class_counts.groupby("split")["samples"].transform(
        lambda values: values / values.sum()
    )

    summary = pd.DataFrame([{
        "best_auc": model_data.roc_auc.max(),
        "test_samples": int((dataset.split == "Test set").sum()),
        "selected_features": len(selected),
        "highest_malignant_recall": model_data.recall.max(),
        "highest_specificity": model_data.specificity.max(),
        "random_label_auc": summary_json["controls"]["permuted_label_auc_mean"],
    }])

    extracts = {
        "dashboard_summary.csv": summary,
        "dashboard_model_metrics.csv": model_data,
        "dashboard_threshold_metrics.csv": threshold_metrics,
        "dashboard_feature_stability.csv": feature_stability,
        "dashboard_selected_features.csv": selected,
        "dashboard_lr_coefficients.csv": lr_explanation,
        "dashboard_rf_importance.csv": rf_explanation,
        "dashboard_class_counts.csv": class_counts,
    }
    for name, frame in extracts.items():
        frame.to_csv(RESULT / name, index=False, encoding="utf-8")

    sources = [
        source(
            "summary_source", "Dashboard Summary Indicator",
            "data/task5/breast_cancer/results/dashboard_summary.csv",
            "by freeze test indicator, A one-line summary generated from feature selection and pipeline verification results.. ",
            [
                "best_aucTest for the 4 modelROC-AUCThe maximum value. ",
                "highest_malignant_recallUse malignant=1and0.5Threshold. ",
                "random_label_aucFor500Average Test of Sub-Randomly Trained LabelsAUC. ",
            ],
        ),
        source(
            "metrics_source", "4 Model Test Index",
            "data/task5/breast_cancer/results/dashboard_model_metrics.csv",
            "Four locking models in114Classification metrics on example test samples. ",
            [
                "ROC-AUCandPR-AUCUsing the Malignant Probability Calculation. ",
                "confusion matrix indicator usage0.5Threshold. ",
                "AUCUse ordinary samples in the intervalBootstrap. ",
            ],
        ),
        source(
            "roc_source", "Test setROCCurve Point",
            "data/task5/breast_cancer/results/roc_points.csv",
            "obtained after moving the probability thresholdFPRandTPR. ",
            ["The 4 model uses the same set114Example Test Sample. "],
        ),
        source(
            "feature_source", "training set feature filtering",
            "data/task5/breast_cancer/results/dashboard_selected_features.csv",
            "Use only455The final features obtained from the training sample, for instance, Five fold stability andVIF. ",
            [
                "The five-fold direction is first determined within the internal training part. ",
                "The absolute correlation coefficient reaches0.90The duplicate variable is not retained repeatedly.. ",
                "UltimatelyVIFTarget below5. ",
            ],
        ),
        source(
            "stability_source", "candidate feature stability",
            "data/task5/breast_cancer/results/dashboard_feature_stability.csv",
            "Five-fold directional univariate in the training setAUCFrontline15Item feature. ",
            ["The test set does not participate in candidate feature ranking. "],
        ),
        source(
            "lr_source", "Standardized coefficients of logistic regression",
            "data/task5/breast_cancer/results/dashboard_lr_coefficients.csv",
            "In locked logistic regression model6Coefficients of item standardized features. ",
            ["coefficients are used to explain the model orientation, does not indicate medical cause and effect. "],
        ),
        source(
            "rf_source", "Random forest feature importance",
            "data/task5/breast_cancer/results/dashboard_rf_importance.csv",
            "In locked random forest model6Importance of Impurity for the Feature. ",
            ["Impurity importance is used to explain the way the model is used., does not indicate medical cause and effect. "],
        ),
        source(
            "class_source", "Training Test Category Composition",
            "data/task5/breast_cancer/results/dashboard_class_counts.csv",
            "Layering80/20Number of benign and malignant samples after division. ",
            ["Original569Example sample by random seed42division, Malignant recoding is1. "],
        ),
    ]

    cards = [
        {"id": "best_auc", "description": "The 4 model is in114Highest ranking ability on the example test samples. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Highest testAUC", "field": "best_auc", "format": "number"}]},
        {"id": "test_samples", "description": "Patients' samples that had not previously participated in feature selection or parameter tuning.. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Test sample", "field": "test_samples", "format": "compact"}]},
        {"id": "selected_features", "description": "Five-fold stability after folding, Correlation deweighting andVIFKeep After Filtering. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Final Features", "field": "selected_features", "format": "compact"}]},
        {"id": "recall", "description": "0.5Highest malignant recall rate among four models under the threshold. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Highest Severity Recall Rate", "field": "highest_malignant_recall", "format": "percent"}]},
        {"id": "specificity", "description": "0.5Highest benign recognition rate among the four models below the threshold. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Highest specificity", "field": "highest_specificity", "format": "percent"}]},
        {"id": "random_auc", "description": "Random Disable Training Label500Average test after thisAUC. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Random LabelAUC", "field": "random_label_auc", "format": "number"}]},
    ]

    charts = [
        {
            "id": "model_auc", "title": "Testing of the four modelsROC-AUC",
            "subtitle": "Logistic regression and random forest are roughly equal0.994, The first three models have highly overlapping ranges",
            "type": "bar", "intent": "comparison", "dataset": "model_metrics", "sourceId": "metrics_source",
            "encodings": {
                "x": {"field": "model_label", "type": "nominal", "label": "model"},
                "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"},
                "tooltip": [{"field": "auc_ci", "type": "text", "label": "95%Interval"}],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Sort", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"}, "layout": "full",
        },
        {
            "id": "roc", "title": "Test setROCcurve",
            "subtitle": "The 4 model uses the same set114Sample of patients",
            "type": "line", "intent": "comparison", "dataset": "roc_points", "sourceId": "roc_source",
            "encodings": {
                "x": {"field": "fpr", "type": "quantitative", "label": "false positive rateFPR"},
                "y": {"field": "tpr", "type": "quantitative", "label": "true positive rateTPR"},
                "color": {"field": "model_label", "type": "nominal", "label": "model"},
                "tooltip": [
                    {"field": "model_label", "type": "text", "label": "model"},
                    {"field": "threshold", "type": "quantitative", "label": "probability threshold"},
                    {"field": "roc_auc", "type": "quantitative", "label": "AUC"},
                ],
            },
            "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "threshold", "title": "0.5Classification indicators under threshold",
            "subtitle": "The decision treeBalanced Accuracyand malignant recall has the highest, gradient boosting&#39;sF1Higher",
            "type": "bar", "intent": "comparison", "dataset": "threshold_metrics", "sourceId": "metrics_source",
            "encodings": {
                "x": {"field": "model_label", "type": "nominal", "label": "model"},
                "y": {"field": "value", "type": "quantitative", "label": "Index value", "format": "percent"},
                "color": {"field": "metric_label", "type": "nominal", "label": "Indicator"},
            },
            "settings": {"grouped": True}, "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "stability", "title": "Five-fold stability of candidate features",
            "subtitle": "Ranking and direction are calculated solely based on the training set., Before display15item",
            "type": "horizontalBar", "intent": "comparison", "dataset": "feature_stability", "sourceId": "stability_source",
            "encodings": {
                "x": {"field": "feature_cn", "type": "nominal", "label": "Feature"},
                "y": {"field": "cv_auc_mean", "type": "quantitative", "label": "50% off averageAUC"},
                "tooltip": [
                    {"field": "cv_auc_std", "type": "quantitative", "label": "standard deviation of fold"},
                    {"field": "direction_consistency", "type": "quantitative", "label": "Directional Consistency Rate", "format": "percent"},
                ],
            },
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "sequential"}, "layout": "full",
        },
        {
            "id": "lr_explanation", "title": "Standardized coefficients of logistic regression",
            "subtitle": "Positive values push the sample towards malignancy., Negative values push the sample to benign",
            "type": "horizontalBar", "intent": "comparison", "dataset": "lr_explanation", "sourceId": "lr_source",
            "encodings": {
                "x": {"field": "feature_cn", "type": "nominal", "label": "Feature"},
                "y": {"field": "value", "type": "quantitative", "label": "Standardized coefficient"},
            },
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "diverging"}, "layout": "half",
        },
        {
            "id": "rf_explanation", "title": "Random forest feature importance",
            "subtitle": "Larger Perimeter Most Used, Importance does not imply medical causation.",
            "type": "horizontalBar", "intent": "comparison", "dataset": "rf_explanation", "sourceId": "rf_source",
            "encodings": {
                "x": {"field": "feature_cn", "type": "nominal", "label": "Feature"},
                "y": {"field": "value", "type": "quantitative", "label": "Importance of Purity"},
            },
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "sequential"}, "layout": "half",
        },
    ]

    tables = [
        {
            "id": "model_table", "title": "Summary of 4 Model Results",
            "subtitle": "AUCProbability of use, Use of other disaggregated indicators0.5Threshold",
            "dataset": "model_metrics", "sourceId": "metrics_source",
            "defaultSort": {"field": "roc_auc", "direction": "desc"},
            "density": "spacious", "layout": "full",
            "columns": [
                {"field": "model_label", "label": "model", "type": "text"},
                {"field": "cv_auc_mean", "label": "50% off trainingAUC", "format": "number"},
                {"field": "roc_auc", "label": "TestAUC", "format": "number"},
                {"field": "auc_ci", "label": "95%Interval", "type": "text"},
                {"field": "balanced_accuracy", "label": "Balanced Acc.", "format": "percent"},
                {"field": "precision", "label": "Precision", "format": "percent"},
                {"field": "recall", "label": "malignantRecall", "format": "percent"},
                {"field": "specificity", "label": "Specificity", "format": "percent"},
                {"field": "f1", "label": "F1", "format": "percent"},
            ],
        },
        {
            "id": "feature_table", "title": "Final Selected Features",
            "subtitle": "Features are locked before reading test set results",
            "dataset": "selected_features", "sourceId": "feature_source",
            "defaultSort": {"field": "cv_auc_mean", "direction": "desc"},
            "density": "spacious", "layout": "full",
            "columns": [
                {"field": "feature_cn", "label": "Feature", "type": "text"},
                {"field": "cv_auc_mean", "label": "50% offAUC", "format": "number"},
                {"field": "cv_auc_std", "label": "standard deviation of fold", "format": "number"},
                {"field": "direction_consistency", "label": "Directional Consistency Rate", "format": "percent"},
                {"field": "vif", "label": "VIF", "format": "number"},
                {"field": "direction", "label": "Sample direction", "type": "text"},
            ],
        },
    ]

    blocks = [
        {
            "id": "opening", "type": "markdown", "sourceId": "metrics_source",
            "body": "## Classification results\n\nTests of logistic regression and random forestAUCBoth are approximately0.994, The gradient lift is approximately0.992, The decision tree is approximately0.972. The first three models have highly overlapping intervals, Thousandth differences are insufficient to form a stable ranking. Threshold selection0.5time, The decision treeBalanced Accuracyand malignant recall has the highest, gradient boosting&#39;sF1andBrierBetter. ",
        },
        {"id": "cards", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "model_auc_block", "type": "chart", "chartId": "model_auc", "layout": "full"},
        {"id": "roc_block", "type": "chart", "chartId": "roc", "layout": "half"},
        {"id": "threshold_block", "type": "chart", "chartId": "threshold", "layout": "half"},
        {"id": "stability_block", "type": "chart", "chartId": "stability", "layout": "full"},
        {"id": "lr_block", "type": "chart", "chartId": "lr_explanation", "layout": "half"},
        {"id": "rf_block", "type": "chart", "chartId": "rf_explanation", "layout": "half"},
        {"id": "model_table_block", "type": "table", "tableId": "model_table", "layout": "full"},
        {"id": "feature_table_block", "type": "table", "tableId": "feature_table", "layout": "full"},
        {
            "id": "caveats", "type": "markdown",
            "body": "## Reading the boundaries\n\n- Malignant uniform coding is1, AllRecallandFNAll explained according to this 1 caliber. \n- Feature filtering uses only455Example training sample, 114For example, the test sample is only used for final evaluation. \n- highAUCfrom the current data structure andX, YThe more direct morphological link, Does not represent that the algorithm is equally effective on other data. \n- This is an internal test on teaching data, No external hospital, Validation on different devices or different populations. \n- Coefficient and tree model importance explain model dependency., does not indicate medical cause and effect, Nor can it be used for clinical diagnosis.. ",
        },
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "Task 5 - Machine-Learning Case Studies: Evaluation of breast cancer classification model",
            "description": "use569Example: breast cancer diagnosis samples completed feature selection, 4 model training, ROC-AUCEvaluation and Model Interpretation. ",
            "generatedAt": generated,
            "filters": [],
            "cards": cards,
            "charts": charts,
            "tables": tables,
            "sources": sources,
            "blocks": blocks,
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated,
            "status": "ready",
            "datasets": {
                "summary": records(summary),
                "model_metrics": records(model_data),
                "roc_points": records(roc),
                "threshold_metrics": records(threshold_metrics),
                "feature_stability": records(feature_stability),
                "selected_features": records(selected),
                "lr_explanation": records(lr_explanation),
                "rf_explanation": records(rf_explanation),
                "class_counts": records(class_counts),
            },
        },
        "sources": sources,
        "package_info": {"originUrl": "artifact://task5-breast-cancer-classification"},
    }
    ARTIFACT.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    command = [
        "node",
        str(PLUGIN_ROOT / "skills/build-report/scripts/deliver_portable_artifact.mjs"),
        "--input", str(ARTIFACT),
        "--output", str(OUTPUT),
    ]
    result = subprocess.run(
        command, cwd=PLUGIN_ROOT, text=True, capture_output=True
    )
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
