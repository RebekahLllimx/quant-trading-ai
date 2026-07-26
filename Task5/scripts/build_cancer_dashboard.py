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
    "logistic_regression": "逻辑回归",
    "decision_tree": "决策树",
    "random_forest": "随机森林",
    "gradient_boosting": "梯度提升",
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
                "scikit-learn乳腺癌诊断数据",
                "恶性重编码为1",
                "分层80/20划分",
                "随机种子42",
                "测试集不参与特征筛选",
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
        lambda row: f"{row.auc_ci_low:.3f}至{row.auc_ci_high:.3f}", axis=1
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
        "recall": "恶性召回率",
        "specificity": "特异度",
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
            model_label="逻辑回归",
            value=coefficients["coefficient"],
            value_type="标准化系数",
        )[["model", "model_label", "feature", "feature_cn", "value", "value_type"]],
        importance[importance.model.isin(["random_forest", "gradient_boosting"])]
        .assign(value=lambda frame: frame["importance"], value_type="不纯度重要性")
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
        "test_samples": int((dataset.split == "测试集").sum()),
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
        frame.to_csv(RESULT / name, index=False, encoding="utf-8-sig")

    sources = [
        source(
            "summary_source", "看板摘要指标",
            "data/task5/breast_cancer/results/dashboard_summary.csv",
            "由冻结测试指标、特征筛选和管线核对结果生成的一行摘要。",
            [
                "best_auc为四种模型测试ROC-AUC的最大值。",
                "highest_malignant_recall使用恶性=1和0.5阈值。",
                "random_label_auc为500次随机训练标签的平均测试AUC。",
            ],
        ),
        source(
            "metrics_source", "四种模型测试指标",
            "data/task5/breast_cancer/results/dashboard_model_metrics.csv",
            "四种锁定模型在114例测试样本上的分类指标。",
            [
                "ROC-AUC和PR-AUC使用恶性概率计算。",
                "混淆矩阵指标使用0.5阈值。",
                "AUC区间使用普通样本Bootstrap。",
            ],
        ),
        source(
            "roc_source", "测试集ROC曲线点",
            "data/task5/breast_cancer/results/roc_points.csv",
            "移动概率阈值后得到的FPR和TPR。",
            ["四种模型使用同一组114例测试样本。"],
        ),
        source(
            "feature_source", "训练集特征筛选",
            "data/task5/breast_cancer/results/dashboard_selected_features.csv",
            "仅使用455例训练样本得到的最终特征、五折稳定性与VIF。",
            [
                "五折方向先在折内训练部分确定。",
                "绝对相关系数达到0.90的重复变量不重复保留。",
                "最终VIF目标低于5。",
            ],
        ),
        source(
            "stability_source", "候选特征稳定性",
            "data/task5/breast_cancer/results/dashboard_feature_stability.csv",
            "训练集中五折定向单变量AUC靠前的15项特征。",
            ["测试集不参与候选特征排序。"],
        ),
        source(
            "lr_source", "逻辑回归标准化系数",
            "data/task5/breast_cancer/results/dashboard_lr_coefficients.csv",
            "锁定逻辑回归模型中6项标准化特征的系数。",
            ["系数用于解释模型方向，不表示医学因果。"],
        ),
        source(
            "rf_source", "随机森林特征重要性",
            "data/task5/breast_cancer/results/dashboard_rf_importance.csv",
            "锁定随机森林模型中6项特征的不纯度重要性。",
            ["不纯度重要性用于解释模型使用方式，不表示医学因果。"],
        ),
        source(
            "class_source", "训练测试类别构成",
            "data/task5/breast_cancer/results/dashboard_class_counts.csv",
            "分层80/20划分后的良性与恶性样本数量。",
            ["原始569例样本按随机种子42划分，恶性重编码为1。"],
        ),
    ]

    cards = [
        {"id": "best_auc", "description": "四种模型在114例测试样本上的最高排序能力。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "最高测试AUC", "field": "best_auc", "format": "number"}]},
        {"id": "test_samples", "description": "此前没有参与特征筛选或调参的患者样本。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "测试样本", "field": "test_samples", "format": "compact"}]},
        {"id": "selected_features", "description": "经五折稳定性、相关性去重和VIF筛选后保留。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "最终特征", "field": "selected_features", "format": "compact"}]},
        {"id": "recall", "description": "0.5阈值下四种模型中的最高恶性召回率。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "最高恶性召回率", "field": "highest_malignant_recall", "format": "percent"}]},
        {"id": "specificity", "description": "0.5阈值下四种模型中的最高良性识别率。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "最高特异度", "field": "highest_specificity", "format": "percent"}]},
        {"id": "random_auc", "description": "随机打乱训练标签500次后的平均测试AUC。", "dataset": "summary", "sourceId": "summary_source", "metrics": [{"label": "随机标签AUC", "field": "random_label_auc", "format": "number"}]},
    ]

    charts = [
        {
            "id": "model_auc", "title": "四种模型的测试ROC-AUC",
            "subtitle": "逻辑回归与随机森林并列约0.994，前三种模型区间高度重叠",
            "type": "bar", "intent": "comparison", "dataset": "model_metrics", "sourceId": "metrics_source",
            "encodings": {
                "x": {"field": "model_label", "type": "nominal", "label": "模型"},
                "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"},
                "tooltip": [{"field": "auc_ci", "type": "text", "label": "95%区间"}],
            },
            "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机排序", "color": "neutral", "lineStyle": "dashed"}],
            "palette": {"kind": "semantic"}, "layout": "full",
        },
        {
            "id": "roc", "title": "测试集ROC曲线",
            "subtitle": "四种模型使用同一组114例患者样本",
            "type": "line", "intent": "comparison", "dataset": "roc_points", "sourceId": "roc_source",
            "encodings": {
                "x": {"field": "fpr", "type": "quantitative", "label": "假阳性率FPR"},
                "y": {"field": "tpr", "type": "quantitative", "label": "真阳性率TPR"},
                "color": {"field": "model_label", "type": "nominal", "label": "模型"},
                "tooltip": [
                    {"field": "model_label", "type": "text", "label": "模型"},
                    {"field": "threshold", "type": "quantitative", "label": "概率阈值"},
                    {"field": "roc_auc", "type": "quantitative", "label": "AUC"},
                ],
            },
            "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "threshold", "title": "0.5阈值下的分类指标",
            "subtitle": "决策树的Balanced Accuracy和恶性召回率最高，梯度提升的F1更高",
            "type": "bar", "intent": "comparison", "dataset": "threshold_metrics", "sourceId": "metrics_source",
            "encodings": {
                "x": {"field": "model_label", "type": "nominal", "label": "模型"},
                "y": {"field": "value", "type": "quantitative", "label": "指标值", "format": "percent"},
                "color": {"field": "metric_label", "type": "nominal", "label": "指标"},
            },
            "settings": {"grouped": True}, "palette": {"kind": "categorical"}, "layout": "half",
        },
        {
            "id": "stability", "title": "候选特征的五折稳定性",
            "subtitle": "排序和方向仅根据训练集计算，显示前15项",
            "type": "horizontalBar", "intent": "comparison", "dataset": "feature_stability", "sourceId": "stability_source",
            "encodings": {
                "x": {"field": "feature_cn", "type": "nominal", "label": "特征"},
                "y": {"field": "cv_auc_mean", "type": "quantitative", "label": "五折平均AUC"},
                "tooltip": [
                    {"field": "cv_auc_std", "type": "quantitative", "label": "折间标准差"},
                    {"field": "direction_consistency", "type": "quantitative", "label": "方向一致率", "format": "percent"},
                ],
            },
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "sequential"}, "layout": "full",
        },
        {
            "id": "lr_explanation", "title": "逻辑回归标准化系数",
            "subtitle": "正值把样本推向恶性，负值把样本推向良性",
            "type": "horizontalBar", "intent": "comparison", "dataset": "lr_explanation", "sourceId": "lr_source",
            "encodings": {
                "x": {"field": "feature_cn", "type": "nominal", "label": "特征"},
                "y": {"field": "value", "type": "quantitative", "label": "标准化系数"},
            },
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "diverging"}, "layout": "half",
        },
        {
            "id": "rf_explanation", "title": "随机森林特征重要性",
            "subtitle": "较大值周长使用最多，重要性不表示医学因果",
            "type": "horizontalBar", "intent": "comparison", "dataset": "rf_explanation", "sourceId": "rf_source",
            "encodings": {
                "x": {"field": "feature_cn", "type": "nominal", "label": "特征"},
                "y": {"field": "value", "type": "quantitative", "label": "不纯度重要性"},
            },
            "settings": {"sort": "ascending", "showValues": True},
            "palette": {"kind": "sequential"}, "layout": "half",
        },
    ]

    tables = [
        {
            "id": "model_table", "title": "四种模型结果汇总",
            "subtitle": "AUC使用概率，其他分类指标使用0.5阈值",
            "dataset": "model_metrics", "sourceId": "metrics_source",
            "defaultSort": {"field": "roc_auc", "direction": "desc"},
            "density": "spacious", "layout": "full",
            "columns": [
                {"field": "model_label", "label": "模型", "type": "text"},
                {"field": "cv_auc_mean", "label": "训练五折AUC", "format": "number"},
                {"field": "roc_auc", "label": "测试AUC", "format": "number"},
                {"field": "auc_ci", "label": "95%区间", "type": "text"},
                {"field": "balanced_accuracy", "label": "Balanced Acc.", "format": "percent"},
                {"field": "precision", "label": "Precision", "format": "percent"},
                {"field": "recall", "label": "恶性Recall", "format": "percent"},
                {"field": "specificity", "label": "Specificity", "format": "percent"},
                {"field": "f1", "label": "F1", "format": "percent"},
            ],
        },
        {
            "id": "feature_table", "title": "最终入选特征",
            "subtitle": "特征在读取测试集结果前锁定",
            "dataset": "selected_features", "sourceId": "feature_source",
            "defaultSort": {"field": "cv_auc_mean", "direction": "desc"},
            "density": "spacious", "layout": "full",
            "columns": [
                {"field": "feature_cn", "label": "特征", "type": "text"},
                {"field": "cv_auc_mean", "label": "五折AUC", "format": "number"},
                {"field": "cv_auc_std", "label": "折间标准差", "format": "number"},
                {"field": "direction_consistency", "label": "方向一致率", "format": "percent"},
                {"field": "vif", "label": "VIF", "format": "number"},
                {"field": "direction", "label": "样本方向", "type": "text"},
            ],
        },
    ]

    blocks = [
        {
            "id": "opening", "type": "markdown", "sourceId": "metrics_source",
            "body": "## 分类结果\n\n逻辑回归与随机森林的测试AUC均约为0.994，梯度提升约为0.992，决策树约为0.972。前三种模型的区间高度重叠，千分位差别不足以形成稳定排名。阈值取0.5时，决策树的Balanced Accuracy和恶性召回率最高，梯度提升的F1和Brier更好。",
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
            "body": "## 阅读边界\n\n- 恶性统一编码为1，所有Recall和FN均按这一口径解释。\n- 特征筛选只使用455例训练样本，114例测试样本只用于最终评价。\n- 高AUC来自当前数据结构和X、Y之间较直接的形态联系，不代表算法在其他数据上同样有效。\n- 这是教学数据上的内部测试，没有外部医院、不同设备或不同人群验证。\n- 系数和树模型重要性解释模型依赖，不表示医学因果，也不能用于临床诊断。",
        },
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "TASK5 AI交易引擎：乳腺癌分类模型评估",
            "description": "用569例乳腺癌诊断样本完成特征筛选、四模型训练、ROC-AUC评价和模型解释。",
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
