#!/usr/bin/env python3
"""Build the TASK5 portfolio overview dashboard page."""

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
ARTIFACT = ARTIFACTS / "overview.json"
OUTPUT = PAGES / "overview.html"
PLUGIN_ROOT = data_analytics_plugin_root()


def records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.replace([np.inf, -np.inf], np.nan).where(pd.notna(frame), None)
    return clean.to_dict("records")


def main() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    cancer = json.loads((ROOT / "data/task5/breast_cancer/results/summary.json").read_text(encoding="utf-8"))
    first_metrics = pd.read_csv(ROOT / "data/task5/processed/task5_model_metrics.csv")
    second_metrics = pd.read_csv(ROOT / "data/task5/experiment2/processed/task5_experiment2_model_metrics.csv")
    catl_metrics = pd.read_csv(ROOT / "data/task5/catl/results/model_metrics.csv")

    cases = pd.DataFrame(
        [
            {
                "order": 1,
                "case": "Breast Cancer Diagnosis",
                "domain": "Open medical teaching data",
                "target": "malignant=1, Benign=0",
                "train_samples": cancer["train_samples"],
                "test_samples": cancer["test_samples"],
                "best_model": "Logistic Regression / Random Forest",
                "best_auc": cancer["best_auc"],
                "auc_ci": "0.983 - 1.000",
                "role": "Main Case Study of the Course: Display the complete classification process",
            },
            {
                "order": 2,
                "case": "A-share60Daily Cross-Section Ranking",
                "domain": "Freeze Shanghai and ShenzhenA-share pool",
                "target": "The future60Before daily earnings30%With later30%",
                "train_samples": 4349,
                "test_samples": 525,
                "best_model": "Random Forest",
                "best_auc": float(first_metrics[first_metrics.model == "random_forest"].auc.iloc[0]),
                "auc_ci": "0.298 - 0.684",
                "role": "financial attempt: Cross-sectional stock selection",
            },
            {
                "order": 3,
                "case": "A-share20Daily Absolute Change",
                "domain": "Freeze Shanghai and ShenzhenA-share pool",
                "target": "The future20Is the daily return positive?",
                "train_samples": 7867,
                "test_samples": 1065,
                "best_model": "Logistic Regression",
                "best_auc": float(second_metrics[second_metrics.model == "logistic_regression"].auc.iloc[0]),
                "auc_ci": "0.499 - 0.587",
                "role": "financial attempt: Month-end rise and fall classification",
            },
            {
                "order": 4,
                "case": "CATL20Daily excess return",
                "domain": "300750.SZWith Shanghai and Shenzhen300",
                "target": "The future20Does Japan Win Shanghai and Shenzhen300",
                "train_samples": 318,
                "test_samples": 48,
                "best_model": "Decision tree",
                "best_auc": float(catl_metrics[catl_metrics.model == "decision_tree"].roc_auc.iloc[0]),
                "auc_ci": "0.349 - 0.691",
                "role": "financial attempt: Single Stock Relative Benchmark",
            },
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "patients": cancer["samples"],
                "selected_features": len(cancer["selected_features"]),
                "cancer_auc": cancer["best_auc"],
                "finance_attempts": 3,
                "finance_highest_auc": cases[cases.order > 1].best_auc.max(),
            }
        ]
    )
    cases.to_csv(DATA / "overview_cases.csv", index=False, encoding="utf-8")
    summary.to_csv(DATA / "overview_summary.csv", index=False, encoding="utf-8")

    sources = [
        {
            "id": "cases_source",
            "label": "TASK5Four classification caliber",
            "path": "Task5/dashboard/data/overview_cases.csv",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_csv_auto('Task5/dashboard/data/overview_cases.csv', header=true)",
                "description": "Organized from the frozen results of the main breast cancer case and three financial attempts.. ",
                "tables_used": ["Task5/dashboard/data/overview_cases.csv"],
                "filters": ["Breast cancer using fixed80/20hierarchical division", "Use of financial data2025annual out-of-sample testing"],
                "metric_definitions": ["best_aucIt is the highest test under each problem definitionROC-AUC. "],
            },
        },
        {
            "id": "summary_source",
            "label": "TASK5Dashboard Summary",
            "path": "Task5/dashboard/data/overview_summary.csv",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_csv_auto('Task5/dashboard/data/overview_summary.csv', header=true)",
                "description": "Key quantities of the main case and financial attempts. ",
                "tables_used": ["Task5/dashboard/data/overview_summary.csv"],
                "filters": ["Use only frozen results"],
                "metric_definitions": ["finance_highest_aucBest of three financial attemptsAUCThe maximum value. "],
            },
        },
    ]

    cards = [
        {"id": "patients", "description": "scikit-learnAll patient samples for breast cancer diagnosis. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Patient sample", "field": "patients", "format": "compact"}]},
        {"id": "features", "description": "Correlation deduplication andVIFRetention after inspection. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Main Case Characteristics", "field": "selected_features", "format": "compact"}]},
        {"id": "cancer_auc", "description": "Logistic regression and random forest rank the highest in parallel. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Main CaseAUC", "field": "cancer_auc", "format": "number"}]},
        {"id": "attempts", "description": "Section Ranking, Absolute price changes and individual stock excess returns. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "Financial Task Definition", "field": "finance_attempts", "format": "compact"}]},
        {"id": "finance_auc", "description": "The highest out-of-sample in three financial attemptsAUC. ", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "The highest financialAUC", "field": "finance_highest_auc", "format": "number"}]},
    ]
    charts = [
        {
            "id": "case_auc",
            "title": "Highest test of the four classification calibersAUC",
            "subtitle": "Morphological characteristics of breast cancer andYDiscrimination is significantly higher than current financial features",
            "type": "bar",
            "intent": "comparison",
            "dataset": "cases",
            "sourceId": "cases_source",
            "encodings": {
                "x": {"field": "case", "type": "nominal", "label": "classification problem"},
                "y": {"field": "best_auc", "type": "quantitative", "label": "ROC-AUC"},
                "tooltip": [
                    {"field": "best_model", "type": "text", "label": "highestAUCmodel"},
                    {"field": "auc_ci", "type": "text", "label": "95%Interval"},
                    {"field": "test_samples", "type": "quantitative", "label": "Test sample", "format": "compact"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "Random Sort", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "full",
        }
    ]
    tables = [
        {
            "id": "case_table",
            "title": "Problem definition and sample boundaries",
            "subtitle": "AUCmust andX, Y, Explain the sample structure together",
            "dataset": "cases",
            "sourceId": "cases_source",
            "defaultSort": {"field": "order", "direction": "asc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "order", "label": "Serial number", "format": "number"},
                {"field": "case", "label": "Case study", "type": "text"},
                {"field": "domain", "label": "Data Range", "type": "text"},
                {"field": "target", "label": "Y", "type": "text"},
                {"field": "train_samples", "label": "training/Fit sample", "format": "compact"},
                {"field": "test_samples", "label": "Test sample", "format": "compact"},
                {"field": "best_model", "label": "highestAUCmodel", "type": "text"},
                {"field": "best_auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "95%Interval", "type": "text"},
                {"field": "role", "label": "InTASK5role in", "type": "text"},
            ],
        }
    ]
    blocks = [
        {
            "id": "opening",
            "type": "markdown",
            "body": "## TASK5 Panoramic View of Taxonomic Research\n\nThe main course uses breast cancer diagnostic data, Display from Data Check, Feature selection toROC-AUCComplete classification process of confusion matrices. Three financial attempts retained in the portfolio, Used to compare question definitions, Differences between data information volume and model performance. ",
        },
        {"id": "cards", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "auc_block", "type": "chart", "chartId": "case_auc", "layout": "full"},
        {"id": "table_block", "type": "table", "tableId": "case_table", "layout": "full"},
        {
            "id": "navigation",
            "type": "markdown",
            "body": "## Pagination content\n\n- [Breast Cancer Classification Main Case](cancer.html): Data distribution, Feature Selection, ROC, Threshold metrics and feature interpretation. \n- [Three Attempts in the Financial Market](finance.html): Three typesY, Sample Range, modelAUCand stratification conclusions. \n- [Ningde era single-share case](catl.html): The future20Daily comparison with Shanghai and Shenzhen300Classification design and calculation check. ",
        },
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "Task 5 - Machine-Learning Case Studies: Classification Model and Scenario Comparison",
            "description": "Main breast cancer case and three financial classification attempts are presented in a paginated portfolio.. ",
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
            "datasets": {"summary": records(summary), "cases": records(cases)},
        },
        "sources": sources,
        "package_info": {"originUrl": "artifact://task5-overview"},
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
