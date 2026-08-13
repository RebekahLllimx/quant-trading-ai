#!/usr/bin/env python3
"""Generate the five numbered figures used by the Task5 report."""

from __future__ import annotations

import json
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from task5_common import CHART_DIR, METADATA_DIR, PROCESSED_DIR, ensure_directories, write_json


COLORS = {
    "train": "#4C78A8",
    "validation": "#F2A541",
    "test": "#8C8C8C",
    "logistic_regression": "#4C78A8",
    "decision_tree": "#F28E2B",
    "random_forest": "#59A14F",
    "neutral": "#7A7A7A",
}
SPLIT_LABELS = {"train": "训练集", "validation": "验证集", "test": "测试集"}
FEATURE_LABELS = {
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


def configure_style() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Songti SC", "STSong", "Arial Unicode MS", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "axes.titleweight": "normal",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.frameon": True,
            "legend.framealpha": 0.9,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "grid.color": "#D9D9D9",
            "grid.linewidth": 0.6,
            "axes.edgecolor": "#777777",
        }
    )


def save(fig: plt.Figure, filename: str) -> None:
    fig.savefig(CHART_DIR / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_time_split(dataset: pd.DataFrame) -> None:
    monthly = (
        dataset.assign(Month=dataset["Date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["Month", "Split"], as_index=False)
        .size()
    )
    fig, ax = plt.subplots(figsize=(13.5, 5.6))
    for split in ("train", "validation", "test"):
        part = monthly[monthly["Split"] == split]
        ax.bar(part["Month"], part["size"], width=25, color=COLORS[split], label=SPLIT_LABELS[split], alpha=0.9)
    ax.axvline(pd.Timestamp("2023-01-01"), color="#334155", linestyle="--", linewidth=1.2)
    ax.axvline(pd.Timestamp("2024-01-01"), color="#334155", linestyle="--", linewidth=1.2)
    ax.set_title("训练集、验证集与测试集的时间划分")
    ax.set_ylabel("每月股票交易日样本数")
    ax.set_xlabel("观察日期")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="lower left", ncol=3)
    ax.grid(axis="x", visible=False)
    fig.text(0.5, 0.01, "注：跨越分段边界的5日标签已经清除，测试集不参与参数选择。", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, "time_split.png")


def plot_label_distribution(dataset: pd.DataFrame) -> None:
    split = dataset.groupby("Split")["Label"].agg(["count", "sum"]).reindex(["train", "validation", "test"])
    split["positive_rate"] = split["sum"] / split["count"]
    yearly = dataset.assign(Year=dataset["Date"].dt.year).groupby("Year")["Label"].mean()

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), gridspec_kw={"width_ratios": [0.85, 1.45]})
    x = np.arange(3)
    positive = split["positive_rate"].to_numpy()
    axes[0].bar(x, 1 - positive, color="#D9D9D9", label="不涨（0）")
    axes[0].bar(x, positive, bottom=1 - positive, color=COLORS["train"], label="上涨（1）")
    axes[0].set_xticks(x, [SPLIT_LABELS[i] for i in split.index])
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("标签占比")
    axes[0].set_title("各数据段的0/1构成")
    axes[0].legend(loc="upper center", ncol=2)
    for index, value in enumerate(positive):
        axes[0].text(index, 1 - value / 2, f"{value:.1%}", ha="center", va="center", color="white", weight="bold")

    bar_colors = [COLORS["train"] if year <= 2022 else COLORS["validation"] if year == 2023 else COLORS["test"] for year in yearly.index]
    axes[1].bar(yearly.index.astype(str), yearly.values, color=bar_colors)
    axes[1].axhline(0.5, color="#334155", linewidth=1.2, linestyle="--", label="50%参考线")
    axes[1].set_ylim(0.38, 0.60)
    axes[1].set_ylabel("未来5日上涨比例")
    axes[1].set_title("年度标签比例随市场状态变化")
    axes[1].legend(loc="upper right")
    for index, value in enumerate(yearly.values):
        axes[1].text(index, value + 0.006, f"{value:.1%}", ha="center", fontsize=9)
    fig.suptitle("未来5日涨跌标签分布", fontsize=13, fontweight="normal", y=1.01)
    for ax in axes:
        ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "label_distribution.png")


def plot_roc(metrics: pd.DataFrame, roc_points: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    metric_lookup = metrics.set_index("model")
    for model in ("logistic_regression", "decision_tree", "random_forest"):
        part = roc_points[roc_points["model"] == model]
        row = metric_lookup.loc[model]
        label = f"{row['model_label']}  AUC={row['auc']:.3f}"
        ax.plot(part["fpr"], part["tpr"], color=COLORS[model], linewidth=1.8, label=label)
    ax.plot([0, 1], [0, 1], color=COLORS["neutral"], linestyle="--", linewidth=1.0, label="随机分类 AUC=0.500")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("假阳性率 FPR")
    ax.set_ylabel("真正率 TPR")
    ax.set_title("三种分类模型的测试集ROC曲线")
    ax.legend(loc="lower right", fontsize=9.0)
    fig.text(0.5, 0.015, "注：AUC使用模型输出的上涨概率计算。", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, "roc_curves.png")


def plot_confusion(metrics: pd.DataFrame) -> None:
    models = ["logistic_regression", "decision_tree", "random_forest"]
    lookup = metrics.set_index("model")
    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.7))
    for ax, model in zip(axes, models):
        row = lookup.loc[model]
        matrix = np.array([[row["tn"], row["fp"]], [row["fn"], row["tp"]]], dtype=float)
        normalized = matrix / matrix.sum(axis=1, keepdims=True)
        annotation = np.empty((2, 2), dtype=object)
        for i in range(2):
            for j in range(2):
                annotation[i, j] = f"{int(matrix[i, j]):,}\n{normalized[i, j]:.1%}"
        sns.heatmap(
            normalized,
            annot=False,
            cmap="Blues",
            vmin=0,
            vmax=1,
            cbar=False,
            square=True,
            linewidths=1.5,
            linecolor="white",
            ax=ax,
        )
        for i in range(2):
            for j in range(2):
                text_color = "white" if normalized[i, j] >= 0.45 else "#1F2937"
                ax.text(j + 0.5, i + 0.5, annotation[i, j], ha="center", va="center", fontsize=11, color=text_color)
        ax.set_title(f"{row['model_label']}\nAUC={row['auc']:.3f}, F1={row['f1']:.3f}")
        ax.set_xlabel("预测标签")
        ax.set_ylabel("实际标签")
        ax.set_xticklabels(["不涨 0", "上涨 1"])
        ax.set_yticklabels(["不涨 0", "上涨 1"], rotation=0)
    fig.suptitle("测试集混淆矩阵（分类阈值0.5）", fontsize=13, fontweight="normal", y=1.04)
    fig.tight_layout()
    save(fig, "confusion_matrices.png")


def plot_importance(importance: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.2, 7.0))
    logistic = importance[importance["model"] == "logistic_regression"].copy().sort_values("importance")
    logistic["label"] = logistic["feature"].map(FEATURE_LABELS)
    colors = np.where(logistic["importance"] >= 0, COLORS["logistic_regression"], "#9E9E9E")
    axes[0].barh(logistic["label"], logistic["importance"], color=colors)
    axes[0].axvline(0, color="#334155", linewidth=1)
    axes[0].set_title("逻辑回归标准化系数")
    axes[0].set_xlabel("系数（正值提高上涨概率）")

    forest = importance[importance["model"] == "random_forest"].copy().sort_values("importance")
    forest["label"] = forest["feature"].map(FEATURE_LABELS)
    axes[1].barh(forest["label"], forest["importance"], color=COLORS["logistic_regression"])
    axes[1].set_title("随机森林不纯度特征重要性")
    axes[1].set_xlabel("相对重要性（合计为1）")
    for ax in axes:
        ax.grid(axis="y", visible=False)
        sns.despine(ax=ax)
    fig.suptitle("模型使用的历史特征", fontsize=13, fontweight="normal", y=1.01)
    fig.text(0.5, 0.01, "注：系数和特征重要性只描述模型关系，不表示因果作用。", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, "feature_importance.png")


def main() -> None:
    ensure_directories()
    configure_style()
    dataset = pd.read_csv(PROCESSED_DIR / "task5_ml_dataset.csv", parse_dates=["Date", "label_end_date"])
    metrics = pd.read_csv(PROCESSED_DIR / "task5_model_metrics.csv")
    roc_points = pd.read_csv(PROCESSED_DIR / "task5_roc_points.csv")
    importance = pd.read_csv(PROCESSED_DIR / "task5_feature_importance.csv")
    plot_time_split(dataset)
    plot_label_distribution(dataset)
    plot_roc(metrics, roc_points)
    plot_confusion(metrics)
    plot_importance(importance)

    chart_map = {
        "created_at": datetime.now().astimezone().isoformat(),
        "charts": [
            {"file": "time_split.png", "question": "样本如何按时间隔离？", "family": "trend/comparison", "takeaway": "参数选择和测试期被严格隔离。"},
            {"file": "label_distribution.png", "question": "类别比例是否随市场阶段变化？", "family": "composition/comparison", "takeaway": "上涨比例存在年度状态变化。"},
            {"file": "roc_curves.png", "question": "模型能否跨阈值区分涨跌？", "family": "uncertainty/benchmark", "takeaway": "三模型仅略高于随机排序。"},
            {"file": "confusion_matrices.png", "question": "0.5阈值下错误来自哪里？", "family": "matrix", "takeaway": "弱信号使模型倾向预测不涨，召回率较低。"},
            {"file": "feature_importance.png", "question": "模型依赖哪些历史变量？", "family": "ranking", "takeaway": "重要性用于解释模型依赖，不是因果证据。"},
        ],
        "palette": "muted blue, orange, green and gray on a white background",
    }
    write_json(METADATA_DIR / "chart_map.json", chart_map)
    print(f"[done] figures -> {CHART_DIR}")


if __name__ == "__main__":
    main()
