#!/usr/bin/env python3
"""Build the TASK5 finance-attempts portdashboard page."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dashboard_runtime import data_analytics_plugin_root


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "Task5" / "dashboard"
PAGES = DASHBOARD / "pages"
ARTIFACTS = DASHBOARD / "artifacts"
DATA = DASHBOARD / "data"
ARTIFACT = ARTIFACTS / "finance.json"
OUTPUT = PAGES / "finance.html"
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
            "filters": ["2025annual out-of-sample testing", "Divided by time", "AUCUsing Predicted Probability"],
            "metric_definitions": definitions,
        },
    }


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    first_metrics = pd.read_csv(ROOT / "data/task5/processed/task5_model_metrics.csv")
    second_metrics = pd.read_csv(ROOT / "data/task5/experiment2/processed/task5_experiment2_model_metrics.csv")
    catl_metrics = pd.read_csv(ROOT / "data/task5/catl/results/model_metrics.csv")
    first_run = json.loads((ROOT / "data/task5/metadata/model_run.json").read_text(encoding="utf-8"))
    second_run = json.loads((ROOT / "data/task5/experiment2/metadata/model_run.json").read_text(encoding="utf-8"))
    catl_run = json.loads((ROOT / "data/task5/catl/results/summary.json").read_text(encoding="utf-8"))

    first = first_metrics[first_metrics.model.isin(MODEL_NAMES)].copy()
    first["attempt"] = "Section60Daily Ranking"
    first["model_cn"] = first["model"].map(MODEL_NAMES)
    first = first.rename(columns={"auc": "roc_auc"})

    second = second_metrics[second_metrics.model.isin(MODEL_NAMES)].copy()
    second["attempt"] = "20Daily Absolute Change"
    second["model_cn"] = second["model"].map(MODEL_NAMES)
    second = second.rename(columns={"auc": "roc_auc"})

    catl = catl_metrics[catl_metrics.model.isin(MODEL_NAMES)].copy()
    catl["attempt"] = "CATL20Daily excess return"

    model_results = pd.concat(
        [
            first[["attempt", "model", "model_cn", "roc_auc", "auc_ci_low", "auc_ci_high"]],
            second[["attempt", "model", "model_cn", "roc_auc", "auc_ci_low", "auc_ci_high"]],
            catl[["attempt", "model", "model_cn", "roc_auc", "auc_ci_low", "auc_ci_high"]],
        ],
        ignore_index=True,
    )
    model_results["auc_ci"] = model_results.apply(
        lambda row: f"{row.auc_ci_low:.3f} - {row.auc_ci_high:.3f}", axis=1
    )

    best_rows = (
        model_results.sort_values(["attempt", "roc_auc"], ascending=[True, False])
        .groupby("attempt", as_index=False)
        .head(1)
        .copy()
    )
    attempt_order = {
        "Section60Daily Ranking": 1,
        "20Daily Absolute Change": 2,
        "CATL20Daily excess return": 3,
    }
    best_rows["order"] = best_rows.attempt.map(attempt_order)
    best_rows = best_rows.sort_values("order")

    attempts = pd.DataFrame(
        [
            {
                "order": 1,
                "attempt": "Section60Daily Ranking",
                "stock_scope": "Freeze Shanghai and ShenzhenA-share pool",
                "observation": "stockxEnd of the month",
                "target": "The future60Trading day earnings are before the same period.30%or after30%",
                "fit_samples": int(first_run["fit_rows"]),
                "test_samples": int(first_run["test_rows"]),
                "test_period": "2025year, 9end of month",
                "best_model": "Random Forest",
                "best_auc": float(first.loc[first.roc_auc.idxmax(), "roc_auc"]),
                "auc_ci": f"{first.loc[first.roc_auc.idxmax(), 'auc_ci_low']:.3f} - {first.loc[first.roc_auc.idxmax(), 'auc_ci_high']:.3f}",
                "reading": "Corresponding cross-section stock selection, But the interval crossed0.5",
            },
            {
                "order": 2,
                "attempt": "20Daily Absolute Change",
                "stock_scope": "Freeze Shanghai and ShenzhenA-share pool",
                "observation": "stockxEnd of the month",
                "target": "The future20Is the return on a trading day greater than0",
                "fit_samples": int(second_run["fit_rows"]),
                "test_samples": int(second_run["test_rows"]),
                "test_period": "2025year, 11end of month",
                "best_model": "Logistic Regression",
                "best_auc": float(second.loc[second.roc_auc.idxmax(), "roc_auc"]),
                "auc_ci": f"{second.loc[second.roc_auc.idxmax(), 'auc_ci_low']:.3f} - {second.loc[second.roc_auc.idxmax(), 'auc_ci_high']:.3f}",
                "reading": "Sample increase, But only retain very weak linear signals",
            },
            {
                "order": 3,
                "attempt": "CATL20Daily excess return",
                "stock_scope": "300750.SZWith Shanghai and Shenzhen300",
                "observation": "Single strandxWeekend",
                "target": "The future20Whether trading day returns exceed CSI300",
                "fit_samples": int(catl_run["final_train_samples_after_purge"]),
                "test_samples": int(catl_run["test_samples"]),
                "test_period": "2025year, 48Weekly sample",
                "best_model": "Decision tree",
                "best_auc": float(catl_run["best_test_auc"]),
                "auc_ci": "0.349 - 0.691",
                "reading": "The single-strand difference is smaller., But the effective time window is too small",
            },
        ]
    )

    summary = pd.DataFrame(
        [
            {
                "attempts": 3,
                "highest_auc": attempts.best_auc.max(),
                "first_auc": attempts.loc[attempts.order == 1, "best_auc"].iloc[0],
                "second_auc": attempts.loc[attempts.order == 2, "best_auc"].iloc[0],
                "catl_auc": attempts.loc[attempts.order == 3, "best_auc"].iloc[0],
            }
        ]
    )

    attempts.to_csv(DATA / "finance_attempts.csv", index=False, encoding="utf-8")
    model_results.to_csv(DATA / "finance_model_results.csv", index=False, encoding="utf-8")
    summary.to_csv(DATA / "finance_summary.csv", index=False, encoding="utf-8")

    sources = [
        source(
            "attempts_source",
            "Three financial classification designs",
            "Task5/dashboard/data/finance_attempts.csv",
            "Task calibration organized from results of three frozen models, Samples and Best TestsAUC. ",
            [
                "The first timeYFor the future60Before the day section30%With later30%. ",
                "The second timeYFor the future20Is the daily absolute return positive?. ",
                "Third timeYFor the future of Ningde era20Whether daily earnings exceed Shanghai and Shenzhen.300. ",
            ],
        ),
        source(
            "models_source",
            "Model metrics of three financial attempts",
            "Task5/dashboard/data/finance_model_results.csv",
            "Organize Models Locked in Each Attempt2025Out-of-sample for the yearAUC. ",
            ["ROC-AUCUsing positive class probability calculations. ", "Confidence Interval Using Time BlocksBootstrap. "],
        ),
        source(
            "summary_source",
            "Financial Page Summary Metrics",
            "Task5/dashboard/data/finance_summary.csv",
            "The best of three attempts.AUCAbstract. ",
            ["Each bestAUCCalculated according to the highest model value in the corresponding test set. "],
        ),
    ]

    cards = [
        {"id": "attempts", "description": "changed separatelyY, Watch Frequency or Stock Range. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Task Definition", "field": "attempts", "format": "compact"}]},
        {"id": "first", "description": "end-of-month section60Daily Return Ranking. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Best on the first tryAUC", "field": "first_auc", "format": "number"}]},
        {"id": "second", "description": "Future at the end of the month20Daily Absolute Change. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Second bestAUC", "field": "second_auc", "format": "number"}]},
        {"id": "catl", "description": "Ningde Era Future20Daily excess return. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Single-strand cases are best.AUC", "field": "catl_auc", "format": "number"}]},
    ]

    charts = [
        {
            "id": "best_auc",
            "title": "Best tests of the three financial classificationsAUC",
            "subtitle": "Task caliber is different, Numerical values are used to observe learnability, No direct ranking",
            "type": "bar",
            "intent": "comparison",
            "dataset": "best_results",
            "sourceId": "attempts_source",
            "encodings": {
                "x": {"field": "attempt", "type": "nominal", "label": "Task Definition"},
                "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"},
                "tooltip": [
                    {"field": "model_cn", "type": "text", "label": "The best model"},
                    {"field": "auc_ci", "type": "text", "label": "95%Interval"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Sort", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "full",
        },
        {
            "id": "all_models",
            "title": "Models in each taskAUC",
            "subtitle": "Complex models did not consistently outperform in three out-of-sample tests.",
            "type": "bar",
            "intent": "comparison",
            "dataset": "model_results",
            "sourceId": "models_source",
            "encodings": {
                "x": {"field": "attempt", "type": "nominal", "label": "Task Definition"},
                "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"},
                "color": {"field": "model_cn", "type": "nominal", "label": "model"},
                "tooltip": [{"field": "auc_ci", "type": "text", "label": "95%Interval"}],
            },
            "settings": {"grouped": True},
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Sort", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "categorical"},
            "layout": "full",
        },
    ]

    tables = [
        {
            "id": "attempt_table",
            "title": "Caliber and results of three tasks",
            "subtitle": "Sample size must be interpreted in conjunction with observation frequency and label overlap.",
            "dataset": "attempts",
            "sourceId": "attempts_source",
            "defaultSort": {"field": "order", "direction": "asc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "order", "label": "Serial number", "format": "number"},
                {"field": "attempt", "label": "Task", "type": "text"},
                {"field": "stock_scope", "label": "Stock Range", "type": "text"},
                {"field": "observation", "label": "Observation unit", "type": "text"},
                {"field": "target", "label": "YDefinition", "type": "text"},
                {"field": "fit_samples", "label": "Fit sample", "format": "compact"},
                {"field": "test_samples", "label": "Test sample", "format": "compact"},
                {"field": "best_model", "label": "highestAUCmodel", "type": "text"},
                {"field": "best_auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "95%Interval", "type": "text"},
                {"field": "reading", "label": "Interpretation", "type": "text"},
            ],
        },
        {
            "id": "model_table",
            "title": "Out of sample for all modelsAUC",
            "subtitle": "Each row corresponds to a task definition and a locked model.",
            "dataset": "model_results",
            "sourceId": "models_source",
            "defaultSort": {"field": "roc_auc", "direction": "desc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "attempt", "label": "Task", "type": "text"},
                {"field": "model_cn", "label": "model", "type": "text"},
                {"field": "roc_auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "95%Interval", "type": "text"},
            ],
        },
    ]

    blocks = [
        {
            "id": "opening",
            "type": "markdown",
            "body": "## How the problem changes\n\nThe financial data part does not repeatedly modify the same model., But rather changed the cross-sectional ranking sequentially, Three types: absolute price change, and single stock relative to benchmarkY. Out-of-sample for three tasksAUCAll close to0.5, It shows that current technical features have not formed a stable ranking ability under the corresponding prediction targets.. ",
        },
        {"id": "cards", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "best_auc_block", "type": "chart", "chartId": "best_auc", "layout": "full"},
        {"id": "models_block", "type": "chart", "chartId": "all_models", "layout": "full"},
        {"id": "attempt_table_block", "type": "table", "tableId": "attempt_table", "layout": "full"},
        {"id": "model_table_block", "type": "table", "tableId": "model_table", "layout": "full"},
        {
            "id": "takeaways",
            "type": "markdown",
            "body": "## Why are the results close to random\n\n**AUCThe meaning of. ** AUCFor0.53, Indicates that when randomly selecting a set of positive and negative samples, The model has about53%The probability of putting the positive class in front., only about higher than random sort3percentage points. Confidence intervals for three time blocks all overlap0.5, The current gap is insufficient to confirm stable signals. \n\n**Calculation and troubleshooting. ** Label Recaltation, Date Boundary, Mann-WhitneyNo errors were found in the rank formula and verification with the same test label.. Random Label AverageAUCFor0.497, The human predictable label is0.996, Indicates that the pipeline can learn when there is information. \n\n**intertemporal change. ** 60In the daily section ranking, Logistic RegressionAUCby2023year&#39;s0.752Drop to2024year&#39;s0.575and2025year&#39;s0.509, Random forest is also composed0.726Drop to0.594and0.533. Relationships in the training period do not stably continue into the final test period.. \n\n**information boundary. ** 20Most remaining variables are derived from transformations of the same price and volume sequences., Valuation cannot be overridden., Financial report, Industry boom, Policies and Corporate Events. 20day and60Day labels are still overlapping., The number of records is significantly more than the number of independent market states. \n\n**Conclusion Boundary. ** Current results cannot conclude that machine-learning is invalid; can support the conclusion that, Existing price quantity characteristics, The target definition and time range are not sufficient to form stable out-of-sample ranking ability.. Improvement order should be trading decision andY, Information Coverage, Sample and Validation, Finally, the complexity of the model.. ",
        },
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "TASK5 Attempts at Classifying Financial Markets",
            "description": "Comparison of Three Definitions of Stock Classification, Out of sampleAUCand its research boundaries. ",
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
                "attempts": records(attempts),
                "best_results": records(best_rows),
                "model_results": records(model_results),
            },
        },
        "sources": sources,
        "package_info": {"originUrl": "artifact://task5-finance-attempts"},
    }
    ARTIFACT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    command = [
        "node",
        str(PLUGIN_ROOT / "skills/build-report/scripts/deliver_portable_artifact.mjs"),
        "--input",
        str(ARTIFACT),
        "--output",
        str(OUTPUT),
    ]
    result = subprocess.run(command, cwd=PLUGIN_ROOT, text=True, capture_output=True)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    print(f"[done] dashboard -> {OUTPUT}")


if __name__ == "__main__":
    main()
