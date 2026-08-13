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
                        "actual_label": "实际不涨 0" if actual == 0 else "实际上涨 1",
                        "predicted": predicted,
                        "predicted_label": "预测不涨 0" if predicted == 0 else "预测上涨 1",
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
            "filters": ["沪深A股", "正式样本2018-02-01至2025-12-31", "测试集2024-01-01至2025-12-31"],
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
    model_metrics["auc_ci"] = model_metrics.apply(lambda row: f"{row['auc_ci_low']:.3f}–{row['auc_ci_high']:.3f}", axis=1)

    importance["feature_label"] = importance["feature"].map(
        {
            "return_1d": "1日收益",
            "return_5d": "5日收益",
            "return_10d": "10日收益",
            "return_20d": "20日收益",
            "ma5_gap": "价格/MA5-1",
            "ma20_gap": "价格/MA20-1",
            "ma60_gap": "价格/MA60-1",
            "rsi14": "RSI14",
            "macd_pct": "MACD/价格",
            "atr14_pct": "ATR14/价格",
            "volatility20": "20日波动率",
            "volume_ratio20": "成交量比20日",
            "amount_ratio20": "成交额比20日",
            "intraday_range": "日内振幅",
            "open_close_return": "开收盘收益",
        }
    )
    importance["explanation_value"] = importance["importance"]
    importance["rank"] = importance.groupby("model")["absolute_importance"].rank(method="first", ascending=False).astype(int)
    yearly["year"] = yearly["year"].astype(str)
    yearly_labels["Year"] = yearly_labels["Year"].astype(str)
    yearly_labels["split_label"] = yearly_labels["Split"].map({"train": "训练期", "validation": "验证期", "test": "测试期"})
    split_summary["SplitLabel"] = split_summary["Split"].map({"train": "训练集", "validation": "验证集", "test": "测试集"})

    generated_at = json.loads((METADATA_DIR / "model_run.json").read_text(encoding="utf-8"))["created_at"]
    metric_source = source_spec(
        "model_metrics_source",
        "测试集模型指标",
        "data/task5/processed/task5_model_metrics.csv",
        "从冻结测试集概率预测重新计算AUC与0.5阈值分类指标。",
        [
            "AUC=ROC曲线下面积，使用上涨概率而不是0/1预测标签计算。",
            "Accuracy=(TP+TN)/全部测试样本。",
            "Precision=TP/(TP+FP)，Recall=TP/(TP+FN)，F1为二者调和平均。",
        ],
    )
    prediction_source = source_spec(
        "prediction_source",
        "测试集逐样本预测",
        "data/task5/processed/task5_test_predictions.csv",
        "三种锁定模型对2024—2025测试样本生成的上涨概率和0.5阈值预测。",
        ["一条记录是一只股票在一个测试交易日上的一个模型预测。", "阈值曲线只改变展示阈值，不重新训练模型。"],
    )
    data_source = source_spec(
        "dataset_source",
        "API冻结特征标签面板",
        "data/task5/processed/task5_ml_dataset.csv",
        "由2017—2025 API行情快照构造15个仅使用当日及历史信息的比例特征。",
        ["Label=1 当且仅当未来5个交易日调整后收益率大于0。", "时间切分为2018—2022训练、2023验证、2024—2025测试。"],
    )
    importance_source = source_spec(
        "importance_source",
        "模型解释结果",
        "data/task5/processed/task5_feature_importance.csv",
        "逻辑回归标准化系数与树模型不纯度特征重要性。",
        ["系数和重要性描述模型依赖关系，不表示因果作用。"],
    )
    sources = [metric_source, prediction_source, data_source, importance_source]

    cards = []
    for card_id, label, field, fmt, description in [
        ("auc_card", "测试集 AUC", "auc", "number", "跨全部分类阈值的涨跌排序能力；0.5接近随机。"),
        ("accuracy_card", "准确率", "accuracy", "percent", "在0.5分类阈值下的总体判对比例。"),
        ("precision_card", "精确率", "precision", "percent", "预测上涨的样本中实际上涨的比例。"),
        ("recall_card", "召回率", "recall", "percent", "实际上涨样本中被模型识别的比例。"),
        ("f1_card", "F1", "f1", "percent", "精确率与召回率的调和平均。"),
        ("test_rows_card", "测试样本", "test_rows", "compact", "2024—2025年股票—交易日样本数。"),
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
            "title": "测试期年度AUC",
            "subtitle": "分别检查2024与2025，观察弱信号是否只来自单一年份",
            "type": "bar",
            "intent": "comparison",
            "dataset": "yearly_metrics",
            "sourceId": "model_metrics_source",
            "encodings": {
                "x": {"field": "year", "type": "ordinal", "label": "年份"},
                "y": {"field": "auc", "type": "quantitative", "label": "AUC", "format": "number"},
                "tooltip": [
                    {"field": "accuracy", "type": "quantitative", "label": "准确率", "format": "percent"},
                    {"field": "f1", "type": "quantitative", "label": "F1", "format": "percent"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机基准", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "half",
        },
        {
            "id": "yearly_label_rate",
            "title": "年度未来5日上涨比例",
            "subtitle": "标签基准率随市场阶段变化，2023年最低",
            "type": "bar",
            "intent": "comparison",
            "dataset": "yearly_labels",
            "sourceId": "dataset_source",
            "encodings": {
                "x": {"field": "Year", "type": "ordinal", "label": "年份"},
                "y": {"field": "positive_rate", "type": "quantitative", "label": "上涨比例", "format": "percent"},
                "color": {"field": "split_label", "type": "nominal", "label": "数据段"},
                "tooltip": [{"field": "rows", "type": "quantitative", "label": "样本数", "format": "compact"}],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "50%", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "categorical"},
            "layout": "half",
        },
        {
            "id": "roc_chart",
            "title": "测试集ROC曲线",
            "subtitle": "曲线越靠近左上角，跨阈值区分能力越强",
            "type": "line",
            "intent": "comparison",
            "dataset": "roc_points",
            "sourceId": "model_metrics_source",
            "encodings": {
                "x": {"field": "fpr", "type": "quantitative", "label": "假阳性率 FPR"},
                "y": {"field": "tpr", "type": "quantitative", "label": "真正率 TPR"},
                "color": {"field": "model_label", "type": "nominal", "label": "模型"},
                "tooltip": [
                    {"field": "threshold", "type": "quantitative", "label": "阈值"},
                    {"field": "auc", "type": "quantitative", "label": "AUC"},
                ],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "TPR=0.5参考", "color": "neutral", "lineStyle": "dotted"}],
            "palette": {"kind": "categorical"},
            "layout": "full",
        },
        {
            "id": "confusion_heatmap",
            "title": "0.5阈值混淆矩阵",
            "subtitle": "颜色为同一真实类别内的占比，悬停查看计数",
            "type": "heatmap",
            "intent": "comparison",
            "dataset": "confusion",
            "sourceId": "prediction_source",
            "encodings": {
                "x": {"field": "predicted_label", "type": "nominal", "label": "预测标签"},
                "y": {"field": "row_rate", "type": "quantitative", "label": "行占比", "format": "percent"},
                "color": {"field": "actual_label", "type": "nominal", "label": "实际标签"},
                "tooltip": [{"field": "count", "type": "quantitative", "label": "样本数", "format": "compact"}],
            },
            "palette": {"kind": "sequential"},
            "layout": "half",
        },
        {
            "id": "threshold_chart",
            "title": "分类阈值敏感性",
            "subtitle": "阈值只改变判定规则，不改变AUC或重新训练模型",
            "type": "line",
            "intent": "trend",
            "dataset": "threshold_metrics",
            "sourceId": "prediction_source",
            "encodings": {
                "x": {"field": "threshold", "type": "quantitative", "label": "上涨概率阈值"},
                "y": {"field": "metric_value", "type": "quantitative", "label": "指标值", "format": "percent"},
                "color": {"field": "metric_label", "type": "nominal", "label": "指标"},
                "tooltip": [
                    {"field": "predicted_positive_rate", "type": "quantitative", "label": "预测上涨比例", "format": "percent"},
                    {"field": "predicted_positive", "type": "quantitative", "label": "预测上涨样本", "format": "compact"},
                ],
            },
            "referenceLines": [{"axis": "x", "value": 0.5, "label": "报告阈值", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"},
            "layout": "half",
        },
        {
            "id": "importance_chart",
            "title": "模型特征解释值",
            "subtitle": "逻辑回归为带方向的标准化系数；树模型为非负不纯度重要性",
            "type": "horizontalBar",
            "intent": "comparison",
            "dataset": "importance",
            "sourceId": "importance_source",
            "encodings": {
                "x": {"field": "feature_label", "type": "nominal", "label": "特征"},
                "y": {"field": "explanation_value", "type": "quantitative", "label": "解释值"},
                "tooltip": [
                    {"field": "rank", "type": "quantitative", "label": "绝对重要性排名"},
                    {"field": "importance_type", "type": "text", "label": "解释口径"},
                ],
            },
            "referenceLines": [{"axis": "x", "value": 0, "label": "零", "color": "neutral"}],
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "diverging", "midpoint": 0},
            "layout": "full",
        },
    ]

    tables = [
        {
            "id": "model_comparison",
            "title": "三模型与多数类基线的测试结果",
            "subtitle": "AUC使用概率；其余指标使用固定0.5阈值",
            "dataset": "model_comparison",
            "sourceId": "model_metrics_source",
            "defaultSort": {"field": "auc", "direction": "desc"},
            "density": "spacious",
            "columns": [
                {"field": "model_label", "label": "模型", "type": "text"},
                {"field": "auc", "label": "AUC", "format": "number"},
                {"field": "auc_ci", "label": "AUC 95%区间", "type": "text"},
                {"field": "accuracy", "label": "Accuracy", "format": "percent"},
                {"field": "precision", "label": "Precision", "format": "percent"},
                {"field": "recall", "label": "Recall", "format": "percent"},
                {"field": "f1", "label": "F1", "format": "percent"},
            ],
            "layout": "full",
        },
        {
            "id": "split_table",
            "title": "训练、验证与测试数据段",
            "subtitle": "股票—交易日样本；5日标签跨界样本已清除",
            "dataset": "split_summary",
            "sourceId": "dataset_source",
            "defaultSort": {"field": "start", "direction": "asc"},
            "density": "spacious",
            "columns": [
                {"field": "SplitLabel", "label": "数据段", "type": "text"},
                {"field": "start", "label": "起始日期", "type": "date"},
                {"field": "end", "label": "结束日期", "type": "date"},
                {"field": "rows", "label": "样本数", "format": "compact"},
                {"field": "symbols", "label": "股票数", "format": "number"},
                {"field": "positive_rate", "label": "上涨比例", "format": "percent"},
            ],
            "layout": "full",
        },
    ]

    blocks = [
        {
            "id": "opening",
            "type": "markdown",
            "body": "## 结论先行\n\n三种模型的测试集AUC均接近0.5。逻辑回归最高（0.521），随机森林次之（0.519），说明技术特征只提供了很弱的方向排序信息，不能据此推断策略可盈利。使用顶部模型筛选器可联动查看年度表现、混淆矩阵、阈值敏感性和特征解释。",
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
            "body": "## 使用边界\n\n- AUC略高于0.5只说明测试期排序略优于随机，不等于扣除交易成本后可盈利。\n- 股票池按2018年1月成交额中位数冻结，不是历史沪深300成分股。\n- 多数股票使用Tushare日涨跌幅复合得到的公司行动调整收益指数；模型只使用尺度无关特征。\n- 0.5阈值下召回率较低，反映弱信号与训练/测试基准率变化；本任务没有用测试集重新调阈值。\n- 特征重要性和逻辑回归系数不表示因果作用。",
        },
    ]

    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "TASK5 AI交易引擎：A股涨跌分类评估",
            "description": "100只历史高流动性A股，未来5日涨跌分类，2024—2025严格样本外测试。",
            "generatedAt": generated_at,
            "filters": [
                {
                    "id": "model_filter",
                    "label": "模型",
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
