#!/usr/bin/env python3
"""Build the TASK5 finance-attempts portfolio dashboard page."""

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
    "logistic_regression": "逻辑回归",
    "decision_tree": "决策树",
    "random_forest": "随机森林",
    "gradient_boosting": "梯度提升",
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
            "filters": ["2025年样本外测试", "按时间划分", "AUC使用预测概率"],
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
    first["attempt"] = "截面60日排名"
    first["model_cn"] = first["model"].map(MODEL_NAMES)
    first = first.rename(columns={"auc": "roc_auc"})

    second = second_metrics[second_metrics.model.isin(MODEL_NAMES)].copy()
    second["attempt"] = "20日绝对涨跌"
    second["model_cn"] = second["model"].map(MODEL_NAMES)
    second = second.rename(columns={"auc": "roc_auc"})

    catl = catl_metrics[catl_metrics.model.isin(MODEL_NAMES)].copy()
    catl["attempt"] = "宁德时代20日超额收益"

    model_results = pd.concat(
        [
            first[["attempt", "model", "model_cn", "roc_auc", "auc_ci_low", "auc_ci_high"]],
            second[["attempt", "model", "model_cn", "roc_auc", "auc_ci_low", "auc_ci_high"]],
            catl[["attempt", "model", "model_cn", "roc_auc", "auc_ci_low", "auc_ci_high"]],
        ],
        ignore_index=True,
    )
    model_results["auc_ci"] = model_results.apply(
        lambda row: f"{row.auc_ci_low:.3f}—{row.auc_ci_high:.3f}", axis=1
    )

    best_rows = (
        model_results.sort_values(["attempt", "roc_auc"], ascending=[True, False])
        .groupby("attempt", as_index=False)
        .head(1)
        .copy()
    )
    attempt_order = {
        "截面60日排名": 1,
        "20日绝对涨跌": 2,
        "宁德时代20日超额收益": 3,
    }
    best_rows["order"] = best_rows.attempt.map(attempt_order)
    best_rows = best_rows.sort_values("order")

    attempts = pd.DataFrame(
        [
            {
                "order": 1,
                "attempt": "截面60日排名",
                "stock_scope": "冻结沪深A股股票池",
                "observation": "股票×月末",
                "target": "未来60交易日收益位于同期前30%或后30%",
                "fit_samples": int(first_run["fit_rows"]),
                "test_samples": int(first_run["test_rows"]),
                "test_period": "2025年，9个月末",
                "best_model": "随机森林",
                "best_auc": float(first.loc[first.roc_auc.idxmax(), "roc_auc"]),
                "auc_ci": f"{first.loc[first.roc_auc.idxmax(), 'auc_ci_low']:.3f}—{first.loc[first.roc_auc.idxmax(), 'auc_ci_high']:.3f}",
                "reading": "对应截面选股，但区间跨过0.5",
            },
            {
                "order": 2,
                "attempt": "20日绝对涨跌",
                "stock_scope": "冻结沪深A股股票池",
                "observation": "股票×月末",
                "target": "未来20交易日收益是否大于0",
                "fit_samples": int(second_run["fit_rows"]),
                "test_samples": int(second_run["test_rows"]),
                "test_period": "2025年，11个月末",
                "best_model": "逻辑回归",
                "best_auc": float(second.loc[second.roc_auc.idxmax(), "roc_auc"]),
                "auc_ci": f"{second.loc[second.roc_auc.idxmax(), 'auc_ci_low']:.3f}—{second.loc[second.roc_auc.idxmax(), 'auc_ci_high']:.3f}",
                "reading": "样本增加，但只保留很弱的线性信号",
            },
            {
                "order": 3,
                "attempt": "宁德时代20日超额收益",
                "stock_scope": "300750.SZ与沪深300",
                "observation": "单股×周末",
                "target": "未来20交易日收益是否超过沪深300",
                "fit_samples": int(catl_run["final_train_samples_after_purge"]),
                "test_samples": int(catl_run["test_samples"]),
                "test_period": "2025年，48个周度样本",
                "best_model": "决策树",
                "best_auc": float(catl_run["best_test_auc"]),
                "auc_ci": "0.349—0.691",
                "reading": "单股差异更小，但有效时间窗口太少",
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

    attempts.to_csv(DATA / "finance_attempts.csv", index=False, encoding="utf-8-sig")
    model_results.to_csv(DATA / "finance_model_results.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(DATA / "finance_summary.csv", index=False, encoding="utf-8-sig")

    sources = [
        source(
            "attempts_source",
            "三次金融分类设计",
            "Task5/dashboard/data/finance_attempts.csv",
            "由三组冻结模型结果整理的任务口径、样本和最佳测试AUC。",
            [
                "第一次Y为未来60日截面前30%与后30%。",
                "第二次Y为未来20日绝对收益是否为正。",
                "第三次Y为宁德时代未来20日收益是否超过沪深300。",
            ],
        ),
        source(
            "models_source",
            "三次金融尝试的模型指标",
            "Task5/dashboard/data/finance_model_results.csv",
            "整理各次尝试中锁定模型的2025年样本外AUC。",
            ["ROC-AUC使用正类概率计算。", "置信区间使用时间块Bootstrap。"],
        ),
        source(
            "summary_source",
            "金融页摘要指标",
            "Task5/dashboard/data/finance_summary.csv",
            "三次尝试的最佳AUC摘要。",
            ["各次最佳AUC按对应测试集中的最高模型值计算。"],
        ),
    ]

    cards = [
        {"id": "attempts", "description": "分别改变了Y、观察频率或股票范围。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "任务定义", "field": "attempts", "format": "compact"}]},
        {"id": "first", "description": "月末截面的60日收益排名。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "第一次最佳AUC", "field": "first_auc", "format": "number"}]},
        {"id": "second", "description": "月末未来20日绝对涨跌。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "第二次最佳AUC", "field": "second_auc", "format": "number"}]},
        {"id": "catl", "description": "宁德时代未来20日超额收益。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "单股案例最佳AUC", "field": "catl_auc", "format": "number"}]},
    ]

    charts = [
        {
            "id": "best_auc",
            "title": "三次金融分类的最佳测试AUC",
            "subtitle": "任务口径不同，数值用于观察可学习性，不直接排名",
            "type": "bar",
            "intent": "comparison",
            "dataset": "best_results",
            "sourceId": "attempts_source",
            "encodings": {
                "x": {"field": "attempt", "type": "nominal", "label": "任务定义"},
                "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"},
                "tooltip": [
                    {"field": "model_cn", "type": "text", "label": "最佳模型"},
                    {"field": "auc_ci", "type": "text", "label": "95%区间"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机排序", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "full",
        },
        {
            "id": "all_models",
            "title": "各任务中的模型AUC",
            "subtitle": "复杂模型并未在三个样本外测试中持续领先",
            "type": "bar",
            "intent": "comparison",
            "dataset": "model_results",
            "sourceId": "models_source",
            "encodings": {
                "x": {"field": "attempt", "type": "nominal", "label": "任务定义"},
                "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"},
                "color": {"field": "model_cn", "type": "nominal", "label": "模型"},
                "tooltip": [{"field": "auc_ci", "type": "text", "label": "95%区间"}],
            },
            "settings": {"grouped": True},
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机排序", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "categorical"},
            "layout": "full",
        },
    ]

    tables = [
        {
            "id": "attempt_table",
            "title": "三次任务的口径与结果",
            "subtitle": "样本量必须结合观察频率和标签重叠程度解释",
            "dataset": "attempts",
            "sourceId": "attempts_source",
            "defaultSort": {"field": "order", "direction": "asc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "order", "label": "序号", "format": "number"},
                {"field": "attempt", "label": "任务", "type": "text"},
                {"field": "stock_scope", "label": "股票范围", "type": "text"},
                {"field": "observation", "label": "观察单位", "type": "text"},
                {"field": "target", "label": "Y定义", "type": "text"},
                {"field": "fit_samples", "label": "拟合样本", "format": "compact"},
                {"field": "test_samples", "label": "测试样本", "format": "compact"},
                {"field": "best_model", "label": "最高AUC模型", "type": "text"},
                {"field": "best_auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "95%区间", "type": "text"},
                {"field": "reading", "label": "解读", "type": "text"},
            ],
        },
        {
            "id": "model_table",
            "title": "全部模型的样本外AUC",
            "subtitle": "每一行对应一个任务定义和一个锁定模型",
            "dataset": "model_results",
            "sourceId": "models_source",
            "defaultSort": {"field": "roc_auc", "direction": "desc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "attempt", "label": "任务", "type": "text"},
                {"field": "model_cn", "label": "模型", "type": "text"},
                {"field": "roc_auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "95%区间", "type": "text"},
            ],
        },
    ]

    blocks = [
        {
            "id": "opening",
            "type": "markdown",
            "body": "## 问题如何变化\n\n金融数据部分没有反复修饰同一个模型，而是先后改变了截面排名、绝对涨跌和单股相对基准三种Y。三个任务的样本外AUC都接近0.5，说明当前技术特征没有在对应预测目标下形成稳定的排序能力。",
        },
        {"id": "cards", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "best_auc_block", "type": "chart", "chartId": "best_auc", "layout": "full"},
        {"id": "models_block", "type": "chart", "chartId": "all_models", "layout": "full"},
        {"id": "attempt_table_block", "type": "table", "tableId": "attempt_table", "layout": "full"},
        {"id": "model_table_block", "type": "table", "tableId": "model_table", "layout": "full"},
        {
            "id": "takeaways",
            "type": "markdown",
            "body": "## 为什么结果接近随机\n\n**AUC的含义。** AUC为0.53，表示随机抽取一组正负样本时，模型约有53%的概率把正类排在前面，只比随机排序高约3个百分点。三个时间块置信区间均覆盖0.5，现有差距不足以确认稳定信号。\n\n**计算排查。** 标签复算、日期边界、Mann-Whitney秩公式和同一测试标签检查没有发现错误。随机标签平均AUC为0.497，人工可预测标签为0.996，说明管线能够在有信息时学习。\n\n**跨期变化。** 60日截面排名中，逻辑回归AUC由2023年的0.752降到2024年的0.575和2025年的0.509，随机森林也由0.726降到0.594和0.533。训练期关系没有稳定延续到最终测试期。\n\n**信息边界。** 20余项变量大多由同一价格和成交量序列变换而来，不能覆盖估值、财报、行业景气、政策和公司事件。20日与60日标签还存在重叠，记录数明显多于独立市场状态数。\n\n**结论边界。** 当前结果不能推出机器学习无效；能够支持的结论是，现有价量特征、目标定义和时间范围尚不足以形成稳定的样本外排序能力。改进顺序应为交易决策与Y、信息覆盖、样本和验证，最后才是模型复杂度。",
        },
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "TASK5 金融市场分类尝试",
            "description": "对比三种股票分类定义、样本外AUC及其研究边界。",
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
