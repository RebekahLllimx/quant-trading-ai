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
                "case": "乳腺癌诊断",
                "domain": "公开医学教学数据",
                "target": "恶性=1，良性=0",
                "train_samples": cancer["train_samples"],
                "test_samples": cancer["test_samples"],
                "best_model": "逻辑回归 / 随机森林",
                "best_auc": cancer["best_auc"],
                "auc_ci": "0.983—1.000",
                "role": "课程主案例：展示完整分类流程",
            },
            {
                "order": 2,
                "case": "A股60日截面排名",
                "domain": "冻结沪深A股股票池",
                "target": "未来60日收益前30%与后30%",
                "train_samples": 4349,
                "test_samples": 525,
                "best_model": "随机森林",
                "best_auc": float(first_metrics[first_metrics.model == "random_forest"].auc.iloc[0]),
                "auc_ci": "0.298—0.684",
                "role": "金融尝试：截面选股",
            },
            {
                "order": 3,
                "case": "A股20日绝对涨跌",
                "domain": "冻结沪深A股股票池",
                "target": "未来20日收益是否为正",
                "train_samples": 7867,
                "test_samples": 1065,
                "best_model": "逻辑回归",
                "best_auc": float(second_metrics[second_metrics.model == "logistic_regression"].auc.iloc[0]),
                "auc_ci": "0.499—0.587",
                "role": "金融尝试：月末涨跌分类",
            },
            {
                "order": 4,
                "case": "宁德时代20日超额收益",
                "domain": "300750.SZ与沪深300",
                "target": "未来20日是否跑赢沪深300",
                "train_samples": 318,
                "test_samples": 48,
                "best_model": "决策树",
                "best_auc": float(catl_metrics[catl_metrics.model == "decision_tree"].roc_auc.iloc[0]),
                "auc_ci": "0.349—0.691",
                "role": "金融尝试：单股相对基准",
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
    cases.to_csv(DATA / "overview_cases.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(DATA / "overview_summary.csv", index=False, encoding="utf-8-sig")

    sources = [
        {
            "id": "cases_source",
            "label": "TASK5四个分类口径",
            "path": "Task5/dashboard/data/overview_cases.csv",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_csv_auto('Task5/dashboard/data/overview_cases.csv', header=true)",
                "description": "由乳腺癌主案例与三次金融尝试的冻结结果整理。",
                "tables_used": ["Task5/dashboard/data/overview_cases.csv"],
                "filters": ["乳腺癌使用固定80/20分层划分", "金融数据使用2025年样本外测试"],
                "metric_definitions": ["best_auc是每个问题定义下的最高测试ROC-AUC。"],
            },
        },
        {
            "id": "summary_source",
            "label": "TASK5看板摘要",
            "path": "Task5/dashboard/data/overview_summary.csv",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_csv_auto('Task5/dashboard/data/overview_summary.csv', header=true)",
                "description": "主案例和金融尝试的关键数量。",
                "tables_used": ["Task5/dashboard/data/overview_summary.csv"],
                "filters": ["只使用冻结结果"],
                "metric_definitions": ["finance_highest_auc是三次金融尝试最佳AUC的最大值。"],
            },
        },
    ]

    cards = [
        {"id": "patients", "description": "scikit-learn乳腺癌诊断全部患者样本。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "患者样本", "field": "patients", "format": "compact"}]},
        {"id": "features", "description": "相关性去重与VIF检查后保留。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "主案例特征", "field": "selected_features", "format": "compact"}]},
        {"id": "cancer_auc", "description": "逻辑回归与随机森林并列最高。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "主案例AUC", "field": "cancer_auc", "format": "number"}]},
        {"id": "attempts", "description": "截面排名、绝对涨跌与单股超额收益。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "金融任务定义", "field": "finance_attempts", "format": "compact"}]},
        {"id": "finance_auc", "description": "三次金融尝试中的最高样本外AUC。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "金融最高AUC", "field": "finance_highest_auc", "format": "number"}]},
    ]
    charts = [
        {
            "id": "case_auc",
            "title": "四个分类口径的最高测试AUC",
            "subtitle": "乳腺癌形态特征与Y的区分度明显高于当前金融特征",
            "type": "bar",
            "intent": "comparison",
            "dataset": "cases",
            "sourceId": "cases_source",
            "encodings": {
                "x": {"field": "case", "type": "nominal", "label": "分类问题"},
                "y": {"field": "best_auc", "type": "quantitative", "label": "ROC-AUC"},
                "tooltip": [
                    {"field": "best_model", "type": "text", "label": "最高AUC模型"},
                    {"field": "auc_ci", "type": "text", "label": "95%区间"},
                    {"field": "test_samples", "type": "quantitative", "label": "测试样本", "format": "compact"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机排序", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "full",
        }
    ]
    tables = [
        {
            "id": "case_table",
            "title": "问题定义与样本边界",
            "subtitle": "AUC必须和X、Y、样本结构一起解释",
            "dataset": "cases",
            "sourceId": "cases_source",
            "defaultSort": {"field": "order", "direction": "asc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "order", "label": "序号", "format": "number"},
                {"field": "case", "label": "案例", "type": "text"},
                {"field": "domain", "label": "数据范围", "type": "text"},
                {"field": "target", "label": "Y", "type": "text"},
                {"field": "train_samples", "label": "训练/拟合样本", "format": "compact"},
                {"field": "test_samples", "label": "测试样本", "format": "compact"},
                {"field": "best_model", "label": "最高AUC模型", "type": "text"},
                {"field": "best_auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "95%区间", "type": "text"},
                {"field": "role", "label": "在TASK5中的作用", "type": "text"},
            ],
        }
    ]
    blocks = [
        {
            "id": "opening",
            "type": "markdown",
            "body": "## TASK5 分类研究全景\n\n课程主体使用乳腺癌诊断数据，展示从数据检查、特征筛选到ROC-AUC和混淆矩阵的完整分类流程。三次金融尝试保留在作品集中，用于比较问题定义、数据信息量和模型表现之间的差异。",
        },
        {"id": "cards", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "auc_block", "type": "chart", "chartId": "case_auc", "layout": "full"},
        {"id": "table_block", "type": "table", "tableId": "case_table", "layout": "full"},
        {
            "id": "navigation",
            "type": "markdown",
            "body": "## 分页内容\n\n- [乳腺癌分类主案例](cancer.html)：数据分布、特征筛选、ROC、阈值指标和特征解释。\n- [金融市场三次尝试](finance.html)：三种Y、样本范围、模型AUC和分层结论。\n- [宁德时代单股案例](catl.html)：未来20日相对沪深300的分类设计和计算核对。",
        },
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "TASK5 AI交易引擎：分类模型与场景对比",
            "description": "乳腺癌主案例和三次金融分类尝试的分页作品集。",
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
