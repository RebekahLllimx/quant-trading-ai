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
            "filters": ["沪深A股100只冻结股票池", "月末观察", "2025年严格样本外测试"],
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
    metrics["auc_ci"] = metrics.apply(lambda row: f"{row['auc_ci_low']:.3f}–{row['auc_ci_high']:.3f}", axis=1)
    predictions = pd.read_csv(PROCESSED_DIR / "task5_experiment2_test_predictions.csv", parse_dates=["Date"])
    roc = pd.read_csv(PROCESSED_DIR / "task5_experiment2_roc_points.csv")
    importance = pd.read_csv(PROCESSED_DIR / "task5_experiment2_feature_importance.csv")
    split = pd.read_csv(METADATA_DIR / "split_summary.csv")
    yearly = pd.read_csv(METADATA_DIR / "yearly_label_summary.csv")

    feature_labels = {
        "return_1d": "1日收益", "return_5d": "5日收益", "return_10d": "10日收益", "return_20d": "20日收益",
        "ma5_gap": "价格/MA5-1", "ma20_gap": "价格/MA20-1", "ma60_gap": "价格/MA60-1", "rsi14": "RSI14",
        "macd_pct": "MACD/价格", "atr14_pct": "ATR14/价格", "volatility20": "20日波动率",
        "volume_ratio20": "成交量比20日", "amount_ratio20": "成交额比20日", "intraday_range": "日内振幅",
        "open_close_return": "开收盘收益", "excess_return_5d": "相对市场5日收益",
        "excess_return_20d": "相对市场20日收益", "return_20d_rank": "20日收益截面排名",
        "market_median_return_5d": "市场5日中位收益", "market_median_return_20d": "市场20日中位收益",
        "market_breadth_20d": "市场20日上涨广度", "market_dispersion_20d": "市场20日收益离散度",
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
                        "actual_label": "实际不涨" if actual == 0 else "实际上涨",
                        "predicted_label": "预测不涨" if predicted == 0 else "预测上涨",
                        "count": int(matrix[actual, predicted]),
                        "row_rate": float(matrix[actual, predicted] / matrix[actual].sum()),
                    }
                )
    confusion_frame = pd.DataFrame(confusion_rows)

    comparison_rows = []
    first_auc = {"logistic_regression": 0.5210, "decision_tree": 0.5068, "random_forest": 0.5189}
    for model in model_order:
        model_label = MODEL_LABELS[model]
        comparison_rows.append({"model": model, "model_label": model_label, "scheme": "基准方案：每日5日", "auc": first_auc[model]})
        comparison_rows.append({"model": model, "model_label": model_label, "scheme": "调整方案：月末20日", "auc": float(metrics.set_index("model").at[model, "auc"])})
    comparison = pd.DataFrame(comparison_rows)

    split["split_label"] = split["Split"].map({"train": "训练集", "validation": "验证集", "development": "开发集", "test": "测试集"})
    yearly["Year"] = yearly["Year"].astype(str)
    yearly["split_label"] = yearly["Split"].map({"train": "训练期", "validation": "验证期", "development": "开发期", "test": "测试期"})
    run = json.loads((METADATA_DIR / "model_run.json").read_text(encoding="utf-8"))
    generated_at = run["created_at"]

    sources = [
        source("metrics_source", "调整方案模型指标", "data/task5/experiment2/processed/task5_experiment2_model_metrics.csv", "锁定设计后在2025年测试集计算。", ["AUC使用上涨概率。", "Accuracy、Precision、Recall、F1使用0.5分类阈值。"]),
        source("predictions_source", "2025逐样本预测", "data/task5/experiment2/processed/task5_experiment2_test_predictions.csv", "每只股票在每个月末的未来20日上涨概率。", ["一条记录是一只股票、一个月末和一个模型。"]),
        source("dataset_source", "月末特征标签面板", "data/task5/experiment2/processed/task5_experiment2_dataset.csv", "价格量、相对强弱和同期市场状态特征。", ["Label=1当且仅当未来20个交易日收益率大于0。", "所有特征截止观察日。"]),
        source("importance_source", "模型特征重要性", "data/task5/experiment2/processed/task5_experiment2_feature_importance.csv", "逻辑回归标准化系数和树模型不纯度重要性。", ["模型依赖不等于因果作用。"]),
    ]

    cards = []
    for card_id, label, field, fmt, description in [
        ("auc", "2025 AUC", "auc", "number", "跨阈值排序能力；0.5接近随机。"),
        ("accuracy", "准确率", "accuracy", "percent", "0.5阈值下总体判对比例。"),
        ("precision", "精确率", "precision", "percent", "预测上涨中实际上涨的比例。"),
        ("recall", "召回率", "recall", "percent", "实际上涨中被识别的比例。"),
        ("f1", "F1", "f1", "percent", "精确率与召回率的调和平均。"),
        ("rows", "测试样本", "test_rows", "compact", "2025年11个月末股票样本。"),
    ]:
        cards.append({"id": card_id, "description": description, "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": label, "field": field, "format": fmt}]})

    charts = [
        {
            "id": "experiment_comparison", "title": "两轮方案调整的样本外AUC", "subtitle": "目标与测试期不同，用于诊断目标调整是否改善信息含量", "type": "bar", "intent": "comparison", "dataset": "experiment_comparison", "sourceId": "metrics_source",
            "encodings": {"x": {"field": "model_label", "type": "nominal", "label": "模型"}, "y": {"field": "auc", "type": "quantitative", "label": "AUC"}, "color": {"field": "scheme", "type": "nominal", "label": "方案"}, "tooltip": [{"field": "auc", "type": "quantitative", "label": "AUC"}]},
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机排序", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "full",
        },
        {
            "id": "yearly_label", "title": "未来20日上涨比例", "subtitle": "标签基准率随市场年份明显变化", "type": "bar", "intent": "comparison", "dataset": "yearly_labels", "sourceId": "dataset_source",
            "encodings": {"x": {"field": "Year", "type": "ordinal", "label": "年份"}, "y": {"field": "positive_rate", "type": "quantitative", "label": "上涨比例", "format": "percent"}, "color": {"field": "split_label", "type": "nominal", "label": "数据段"}, "tooltip": [{"field": "rows", "type": "quantitative", "label": "样本数", "format": "compact"}]},
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "50%", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "roc", "title": "2025年ROC曲线", "subtitle": "逻辑回归略高于随机，树模型没有保持验证期优势", "type": "line", "intent": "comparison", "dataset": "roc_points", "sourceId": "metrics_source",
            "encodings": {"x": {"field": "fpr", "type": "quantitative", "label": "假阳性率 FPR"}, "y": {"field": "tpr", "type": "quantitative", "label": "真正率 TPR"}, "color": {"field": "model_label", "type": "nominal", "label": "模型"}, "tooltip": [{"field": "threshold", "type": "quantitative", "label": "阈值"}, {"field": "auc", "type": "quantitative", "label": "AUC"}]},
            "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "confusion", "title": "0.5阈值的分类结果", "subtitle": "按真实类别展示预测分布", "type": "bar", "intent": "comparison", "dataset": "confusion", "sourceId": "predictions_source",
            "encodings": {"x": {"field": "actual_label", "type": "nominal", "label": "真实标签"}, "y": {"field": "row_rate", "type": "quantitative", "label": "类别内占比", "format": "percent"}, "color": {"field": "predicted_label", "type": "nominal", "label": "预测"}, "tooltip": [{"field": "count", "type": "quantitative", "label": "样本数", "format": "compact"}]},
            "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "importance", "title": "前12项模型解释值", "subtitle": "逻辑回归有正负方向；树模型为非负重要性", "type": "horizontalBar", "intent": "comparison", "dataset": "importance", "sourceId": "importance_source",
            "encodings": {"x": {"field": "feature_label", "type": "nominal", "label": "特征"}, "y": {"field": "importance", "type": "quantitative", "label": "解释值"}, "tooltip": [{"field": "rank", "type": "quantitative", "label": "绝对重要性排名"}, {"field": "importance_type", "type": "text", "label": "口径"}]},
            "referenceLines": [{"axis": "y", "value": 0, "label": "零", "color": "neutral"}], "settings": {"sort": "ascending", "showValues": True}, "palette": {"kind": "diverging", "midpoint": 0}, "layout": "full",
        },
    ]

    tables = [
        {
            "id": "model_table", "title": "调整方案：2025年测试指标", "subtitle": "AUC用概率；其余指标用0.5阈值", "dataset": "model_comparison", "sourceId": "metrics_source", "defaultSort": {"field": "auc", "direction": "desc"}, "density": "spacious",
            "columns": [{"field": "model_label", "label": "模型", "type": "text"}, {"field": "auc", "label": "AUC", "format": "number"}, {"field": "auc_ci", "label": "AUC 95%区间", "type": "text"}, {"field": "accuracy", "label": "Accuracy", "format": "percent"}, {"field": "precision", "label": "Precision", "format": "percent"}, {"field": "recall", "label": "Recall", "format": "percent"}, {"field": "f1", "label": "F1", "format": "percent"}], "layout": "full",
        },
        {
            "id": "split_table", "title": "时间序列划分", "subtitle": "月末股票样本；跨越年末边界的20日标签已删除", "dataset": "split_summary", "sourceId": "dataset_source", "defaultSort": {"field": "start", "direction": "asc"}, "density": "spacious",
            "columns": [{"field": "split_label", "label": "数据段", "type": "text"}, {"field": "start", "label": "起始日期", "type": "date"}, {"field": "end", "label": "结束日期", "type": "date"}, {"field": "rows", "label": "样本数", "format": "compact"}, {"field": "months", "label": "月数", "format": "number"}, {"field": "positive_rate", "label": "上涨比例", "format": "percent"}], "layout": "full",
        },
    ]

    blocks = [
        {"id": "opening", "type": "markdown", "body": "## 主要发现\n\n调整方案把问题改为月末预测未来20个交易日绝对涨跌。逻辑回归2025年AUC为0.529，比基准方案的0.521略高；决策树和随机森林低于0.5，说明延长周期只带来了有限且模型依赖的改善，复杂模型在市场状态变化后没有稳定外推。", "sourceId": "metrics_source"},
        {"id": "workflow", "type": "markdown", "body": "## 九步实战路线\n\n1. 准备API冻结行情并做覆盖、缺失、标签漂移与收益分布探索；2. 构造未来20日绝对涨跌标签；3. 选择价格量、相对强弱和市场状态特征；4. 按2018-2022训练、2023验证、2024开发、2025测试进行时间隔离；5. 训练三类模型并在测试前锁定参数；6. 输出2025上涨概率；7. 用AUC、ROC和混淆矩阵评估；8. 查看标准化系数与特征重要性；9. 保存模型、预测、指标、哈希和33项校验结果。", "sourceId": "dataset_source"},
        {"id": "cards", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
        {"id": "comparison_block", "type": "chart", "chartId": "experiment_comparison", "layout": "full"},
        {"id": "yearly_block", "type": "chart", "chartId": "yearly_label", "layout": "half"},
        {"id": "roc_block", "type": "chart", "chartId": "roc", "layout": "half"},
        {"id": "confusion_block", "type": "chart", "chartId": "confusion", "layout": "half"},
        {"id": "importance_block", "type": "chart", "chartId": "importance", "layout": "full"},
        {"id": "model_table_block", "type": "table", "tableId": "model_table", "layout": "full"},
        {"id": "split_table_block", "type": "table", "tableId": "split_table", "layout": "full"},
        {"id": "caveats", "type": "markdown", "body": "## 使用边界\n\n- 最佳AUC的区组自助法95%区间约为0.499—0.587，仍触及随机基准。\n- 两轮方案的目标、频率和测试区间不同，比较用于诊断，不是严格的模型竞赛。\n- 本任务只评价分类能力，没有计算手续费、滑点或投资组合收益。\n- 股票池按2018年初流动性冻结，不是逐期历史指数成分股。\n- 模型重要性不表示因果作用。"},
    ]

    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1, "surface": "dashboard", "title": "TASK5 AI交易引擎：沪深A股涨跌分类", "description": "A股月末未来20日涨跌分类，以及与每日5日基准方案的比较。", "generatedAt": generated_at,
            "filters": [{"id": "model_filter", "label": "模型", "dataset": "model_metrics", "field": "model_label", "defaultValue": "逻辑回归", "includeAll": False, "targets": [{"dataset": "model_metrics", "field": "model_label"}, {"dataset": "roc_points", "field": "model_label"}, {"dataset": "confusion", "field": "model_label"}, {"dataset": "importance", "field": "model_label"}]}],
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
