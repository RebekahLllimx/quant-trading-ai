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
    "logistic_regression": "逻辑回归", "decision_tree": "决策树",
    "random_forest": "随机森林", "gradient_boosting": "梯度提升",
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
            "filters": ["宁德时代300750.SZ", "沪深300000300.SH", "周末观察", "未来20交易日超额收益标签", "2025最终测试"],
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
    metric_data["auc_ci"] = metric_data.apply(lambda r: f"{r.auc_ci_low:.3f}–{r.auc_ci_high:.3f}", axis=1)
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
    validation["validation_year"] = validation["validation_year"].str[-4:] + "年"
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
                "actual_label": "实际未跑赢 0" if actual == 0 else "实际跑赢 1",
                "predicted_label": "预测未跑赢 0" if predicted == 0 else "预测跑赢 1",
                "count": int(value), "row_rate": float(value / denom),
            })
    confusion = pd.DataFrame(confusion_rows)
    decision_confusion = confusion[confusion["model"] == "decision_tree"].copy()

    explanation = pd.concat([
        coefficients.assign(model="logistic_regression", model_label="逻辑回归", value=coefficients["coefficient"], value_type="标准化系数")
            [["model", "model_label", "feature", "feature_cn", "value", "value_type"]],
        importance.assign(value=importance["importance"], value_type="不纯度重要性")
            [["model", "model_cn", "feature", "feature_cn", "value", "value_type"]]
            .rename(columns={"model_cn": "model_label"}),
    ], ignore_index=True)
    explanation["absolute_value"] = explanation["value"].abs()
    explanation["rank"] = explanation.groupby("model")["absolute_value"].rank(method="first", ascending=False).astype(int)
    decision_explanation = explanation[explanation["model"] == "decision_tree"].copy()

    yearly = samples.groupby(samples.Date.dt.year).target.agg(["count", "mean"]).reset_index()
    yearly.columns = ["year", "rows", "positive_rate"]
    yearly["year"] = yearly["year"].astype(str) + "年"
    yearly["period"] = np.where(yearly.year == "2025年", "最终测试", "开发期")

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
        frame.to_csv(RESULT / name, index=False, encoding="utf-8-sig")

    sources = [
        source("metrics_source", "最终测试模型指标", "data/task5/catl/results/dashboard_model_metrics.csv", "四种锁定模型在2025周度测试样本上的分类指标。", ["ROC-AUC使用Y=1概率计算。", "混淆矩阵指标使用0.5阈值。", "AUC区间使用4周移动时间块Bootstrap。"]),
        source("validation_source", "滚动开发验证", "data/task5/catl/results/dashboard_validation_auc.csv", "四种模型锁定参数在2021—2024的扩展窗口AUC。", ["每折只用更早数据训练。", "训练样本label_end_date早于验证年起点。"]),
        source("roc_source", "ROC曲线点", "data/task5/catl/results/roc_points.csv", "2025最终测试上移动分类阈值生成的FPR和TPR。", ["每个模型在同一组48条周度样本上评估。"]),
        source("confusion_source", "决策树混淆矩阵", "data/task5/catl/results/dashboard_decision_tree_confusion.csv", "2025最终测试中决策树实际类别和0.5阈值预测类别的交叉表。", ["row_rate是各实际类别内的预测占比。"]),
        source("explanation_source", "决策树特征重要性", "data/task5/catl/results/dashboard_decision_tree_importance.csv", "2025年AUC最高模型的开发期训练特征重要性。", ["不纯度重要性表示模型使用方式，不表示因果关系。"]),
        source("samples_source", "周度建模样本", "data/task5/catl/processed/weekly_samples.csv", "每个自然周最后一个交易日的特征、20日未来超额收益和0/1标签。", ["Y=1当且仅当宁德时代未来20交易日收益高于沪深300。", "所有X只使用观察日及以前数据。"]),
        source("feature_source", "最终入选特征", "data/task5/catl/results/dashboard_selected_features.csv", "仅根据2018—2024开发期滚动AUC、相关性与VIF筛选的变量。", ["mean_auc是2021—2024四个滚动验证年的单变量逻辑回归平均AUC。", "VIF目标低于5。"]),
    ]

    cards = [
        {"id": "auc", "description": "2025年概率排序能力；0.5接近随机。", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "2025 ROC-AUC", "field": "roc_auc", "format": "number"}]},
        {"id": "validation", "description": "2021—2024四个扩展窗口的平均AUC。", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "开发期平均AUC", "field": "mean_validation_auc", "format": "number"}]},
        {"id": "balanced", "description": "0.5阈值下对两类召回率取平均。", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Balanced Accuracy", "field": "balanced_accuracy", "format": "percent"}]},
        {"id": "precision", "description": "预测跑赢的样本中实际跑赢的比例。", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Precision", "field": "precision", "format": "percent"}]},
        {"id": "recall", "description": "实际跑赢的样本中被模型识别的比例。", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "Recall", "field": "recall", "format": "percent"}]},
        {"id": "rows", "description": "2025年具有完整20日未来标签的周度观察。", "dataset": "model_metrics", "sourceId": "metrics_source", "metrics": [{"label": "测试样本", "field": "test_rows", "format": "compact"}]},
    ]

    charts = [
        {"id": "model_auc", "title": "四种模型的2025年AUC", "subtitle": "决策树略高于0.5，但不确定区间跨过随机基准", "type": "bar", "intent": "comparison", "dataset": "model_comparison", "sourceId": "metrics_source", "encodings": {"x": {"field": "model_label", "type": "nominal", "label": "模型"}, "y": {"field": "roc_auc", "type": "quantitative", "label": "ROC-AUC"}, "tooltip": [{"field": "auc_ci", "type": "text", "label": "95%区间"}]}, "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机排序", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "semantic"}, "layout": "full"},
        {"id": "yearly_labels", "title": "分年度Y=1比例", "subtitle": "标签基准率随市场状态变化，2025年为52.1%", "type": "bar", "intent": "comparison", "dataset": "yearly_labels", "sourceId": "samples_source", "encodings": {"x": {"field": "year", "type": "ordinal", "label": "年份"}, "y": {"field": "positive_rate", "type": "quantitative", "label": "Y=1比例", "format": "percent"}, "color": {"field": "period", "type": "nominal", "label": "数据段"}, "tooltip": [{"field": "rows", "type": "quantitative", "label": "周度样本", "format": "compact"}]}, "referenceLines": [{"axis": "y", "value": 0.5, "label": "50%", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "validation_auc", "title": "锁定参数的跨年验证AUC", "subtitle": "四种模型在2021—2024扩展窗口中的稳定性", "type": "line", "intent": "trend", "dataset": "validation_auc", "sourceId": "validation_source", "encodings": {"x": {"field": "validation_year", "type": "ordinal", "label": "验证年"}, "y": {"field": "auc", "type": "quantitative", "label": "ROC-AUC"}, "color": {"field": "model_label", "type": "nominal", "label": "模型"}, "tooltip": [{"field": "model_label", "type": "text", "label": "模型"}]}, "referenceLines": [{"axis": "y", "value": 0.5, "label": "随机排序", "color": "neutral", "lineStyle": "dashed"}], "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "roc", "title": "2025年最终测试ROC曲线", "subtitle": "四种模型在同一组48条周度样本上的跨阈值比较", "type": "line", "intent": "comparison", "dataset": "roc_points", "sourceId": "roc_source", "encodings": {"x": {"field": "fpr", "type": "quantitative", "label": "假阳性率 FPR"}, "y": {"field": "tpr", "type": "quantitative", "label": "真阳性率 TPR"}, "color": {"field": "model_label", "type": "nominal", "label": "模型"}, "tooltip": [{"field": "model_label", "type": "text", "label": "模型"}, {"field": "threshold", "type": "quantitative", "label": "概率阈值"}, {"field": "roc_auc", "type": "quantitative", "label": "AUC"}]}, "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "confusion", "title": "决策树0.5阈值混淆矩阵", "subtitle": "2025年AUC最高模型：更少误判，但漏掉较多实际跑赢样本", "type": "bar", "intent": "comparison", "dataset": "decision_confusion", "sourceId": "confusion_source", "encodings": {"x": {"field": "actual_label", "type": "nominal", "label": "实际类别"}, "y": {"field": "row_rate", "type": "quantitative", "label": "类别内占比", "format": "percent"}, "color": {"field": "predicted_label", "type": "nominal", "label": "预测类别"}, "tooltip": [{"field": "count", "type": "quantitative", "label": "样本数", "format": "compact"}]}, "settings": {"stacked": True}, "palette": {"kind": "categorical"}, "layout": "half"},
        {"id": "explanation", "title": "决策树特征重要性", "subtitle": "重要性反映模型分裂使用频率和贡献，不表示因果关系", "type": "horizontalBar", "intent": "comparison", "dataset": "decision_explanation", "sourceId": "explanation_source", "encodings": {"x": {"field": "feature_cn", "type": "nominal", "label": "特征"}, "y": {"field": "value", "type": "quantitative", "label": "不纯度重要性"}, "tooltip": [{"field": "rank", "type": "quantitative", "label": "排名"}]}, "settings": {"sort": "ascending", "showValues": True}, "palette": {"kind": "sequential"}, "layout": "full"},
    ]

    tables = [
        {"id": "model_table", "title": "四种模型结果汇总", "subtitle": "AUC使用概率；其他分类指标使用0.5阈值", "dataset": "model_comparison", "sourceId": "metrics_source", "defaultSort": {"field": "roc_auc", "direction": "desc"}, "density": "spacious", "columns": [{"field": "model_label", "label": "模型", "type": "text"}, {"field": "mean_validation_auc", "label": "开发AUC", "format": "number"}, {"field": "roc_auc", "label": "2025 AUC", "format": "number"}, {"field": "auc_ci", "label": "95%区间", "type": "text"}, {"field": "balanced_accuracy", "label": "Balanced Acc.", "format": "percent"}, {"field": "precision", "label": "Precision", "format": "percent"}, {"field": "recall", "label": "Recall", "format": "percent"}, {"field": "f1", "label": "F1", "format": "percent"}], "layout": "full"},
        {"id": "feature_table", "title": "开发期入选特征", "subtitle": "特征在打开2025年测试集前锁定", "dataset": "selected_features", "sourceId": "feature_source", "defaultSort": {"field": "mean_auc", "direction": "desc"}, "density": "spacious", "columns": [{"field": "feature_cn", "label": "特征", "type": "text"}, {"field": "mean_auc", "label": "滚动平均AUC", "format": "number"}, {"field": "std_auc", "label": "AUC标准差", "format": "number"}, {"field": "years_above_0_5", "label": "AUC>0.5年数", "format": "number"}, {"field": "vif", "label": "VIF", "format": "number"}, {"field": "reason", "label": "保留理由", "type": "text"}], "layout": "full"},
    ]

    blocks = [
        {"id": "opening", "type": "markdown", "body": "## 结果与边界\n\n2025年测试中，决策树AUC最高为0.524，时间块Bootstrap区间为0.349—0.691，跨过0.5；其余三个模型也没有通过预测能力检验。AUC复算和标签检查未发现机械错误，20日标签重叠、单股样本较少和信息覆盖不足是当前设计的主要边界。这不是一个可用于交易的模型。", "sourceId": "metrics_source"},
        {"id": "cards", "type": "metric-strip", "cardIds": [c["id"] for c in cards]},
        {"id": "model_auc_block", "type": "chart", "chartId": "model_auc", "layout": "full"},
        {"id": "yearly_labels_block", "type": "chart", "chartId": "yearly_labels", "layout": "half"},
        {"id": "validation_auc_block", "type": "chart", "chartId": "validation_auc", "layout": "half"},
        {"id": "roc_block", "type": "chart", "chartId": "roc", "layout": "half"},
        {"id": "confusion_block", "type": "chart", "chartId": "confusion", "layout": "half"},
        {"id": "explanation_block", "type": "chart", "chartId": "explanation", "layout": "full"},
        {"id": "model_table_block", "type": "table", "tableId": "model_table", "layout": "full"},
        {"id": "feature_table_block", "type": "table", "tableId": "feature_table", "layout": "full"},
        {"id": "caveats", "type": "markdown", "body": "## 阅读边界\n\n- 一共370条周度记录，但相邻周的20日标签重叠，全期近似独立窗口约91个，2025年约12个。\n- 当前区间很宽，无法区分关系换向、弱信号和抽样波动。\n- 管线检查只能排除机械错误，不能证明标签和数据设计充分。\n- 模型只预测超额收益方向，不输出幅度，也未计算交易成本或仓位。\n- 测试集打开后未重新选变量、调参或事后倒转概率。"},
    ]

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1, "surface": "dashboard",
            "title": "TASK5 AI交易引擎：宁德时代相对沪深300分类",
            "description": "周末预测宁德时代未来20个交易日是否跑赢沪深300，2025年严格样本外评估。",
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
