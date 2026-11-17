#!/usr/bin/env python3
"""Create report figures for Task5 experiment 2 and its baseline comparison."""

from __future__ import annotations

from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from experiment2_common import CHART_DIR, METADATA_DIR, PROCESSED_DIR, ensure_directories, write_json


COLORS = {
    "train": "#4C78A8",
    "validation": "#F2A541",
    "development": "#59A14F",
    "test": "#8C8C8C",
    "logistic_regression": "#4C78A8",
    "decision_tree": "#F28E2B",
    "random_forest": "#59A14F",
    "neutral": "#7A7A7A",
}
SPLIT_LABELS = {"train": "Training set", "validation": "Validation set", "development": "Development Kit", "test": "Test set"}
FEATURE_LABELS = {
    "return_1d": "1daily earnings",
    "return_5d": "5daily earnings",
    "return_10d": "10daily earnings",
    "return_20d": "20daily earnings",
    "ma5_gap": "Price/MA5-1",
    "ma20_gap": "Price/MA20-1",
    "ma60_gap": "Price/MA60-1",
    "rsi14": "RSI14",
    "macd_pct": "MACD/Price",
    "atr14_pct": "ATR14/Price",
    "volatility20": "20daily volatility",
    "volume_ratio20": "Volume ratio20day",
    "amount_ratio20": "Turnover ratio20day",
    "intraday_range": "intraday amplitude",
    "open_close_return": "Open Closing Earnings",
    "excess_return_5d": "relative market5daily earnings",
    "excess_return_20d": "relative market20daily earnings",
    "return_20d_rank": "20Daily Return Cross-Section Ranking",
    "market_median_return_5d": "Market5Median Daily Earnings",
    "market_median_return_20d": "Market20Median Daily Earnings",
    "market_breadth_20d": "Market20Daily Upside Breadth",
    "market_dispersion_20d": "Market20Daily Return Dispersion",
}


def configure_style() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Songti SC", "STSong", "Arial Unicode MS", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
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


def plot_baseline_comparison(metrics: pd.DataFrame) -> None:
    models = ["logistic_regression", "decision_tree", "random_forest"]
    first_auc = {"logistic_regression": 0.5210, "decision_tree": 0.5068, "random_forest": 0.5189}
    lookup = metrics.set_index("model")
    second_auc = {model: float(lookup.at[model, "auc"]) for model in models}
    labels = [lookup.at[model, "model_label"] for model in models]
    x = np.arange(len(models))
    width = 0.34
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    bars1 = ax.bar(x - width / 2, [first_auc[m] for m in models], width, label="The first time: Daily Predictions for the Future5day", color="#AFC6E0")
    bars2 = ax.bar(x + width / 2, [second_auc[m] for m in models], width, label="The second time: Forecasting the future at month-end20day", color="#4C78A8")
    ax.axhline(0.5, color=COLORS["neutral"], linestyle="--", linewidth=1.1, label="Random Sort 0.500")
    ax.set_xticks(x, labels)
    ax.set_ylim(0.47, 0.545)
    ax.set_ylabel("Test set AUC")
    ax.set_title("Out-of-sample for two experimentsAUCComparison")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="x", visible=False)
    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.0012, f"{bar.get_height():.3f}", ha="center", fontsize=9)
    fig.text(0.5, 0.012, "Note: Objectives of the two experiments, Different observation frequencies and test intervals, Figure comparison for diagnosis, It's not a strict model competition.. ", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, "baseline_comparison.png")


def plot_time_split(dataset: pd.DataFrame) -> None:
    monthly = dataset.groupby(["Date", "Split"], as_index=False).size()
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    for split in ("train", "test"):
        part = monthly[monthly["Split"] == split]
        ax.bar(part["Date"], part["size"], width=22, color=COLORS[split], label=SPLIT_LABELS[split], alpha=0.92)
    test_start = dataset.loc[dataset["Split"] == "test", "Date"].min()
    ax.axvline(test_start, color="#334155", linestyle="--", linewidth=1.1)
    ax.set_ylabel("Number of shares per observation month")
    ax.set_xlabel("Month end observation date")
    ax.set_title("The time division of the second experiment and end-of-month sampling.")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="lower left", ncol=2, fontsize=9)
    ax.grid(axis="x", visible=False)
    fig.text(0.5, 0.012, "Note: Take the first according to the observation date at the end of the month70%training, after30%Test; Training labels that cross split points have been deleted. ", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, "time_split.png")


def plot_label_distribution(dataset: pd.DataFrame) -> None:
    summary = dataset.groupby("Split")["Label"].agg(["count", "sum"]).reindex(["train", "test"])
    summary["positive_rate"] = summary["sum"] / summary["count"]
    yearly = dataset.assign(Year=dataset["Date"].dt.year).groupby("Year")["Label"].mean()
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2), gridspec_kw={"width_ratios": [1.0, 1.45]})
    x = np.arange(len(summary))
    positive = summary["positive_rate"].to_numpy()
    axes[0].bar(x, 1 - positive, color="#D9D9D9", label="No increase (0) ")
    axes[0].bar(x, positive, bottom=1 - positive, color="#4C78A8", label="rise (1) ")
    axes[0].set_xticks(x, [SPLIT_LABELS[value] for value in summary.index], rotation=12)
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("Label proportion")
    axes[0].set_title("of each data segment0/1composition")
    axes[0].legend(loc="upper center", ncol=2, fontsize=9)
    for index, value in enumerate(positive):
        axes[0].text(index, 1 - value / 2, f"{value:.1%}", ha="center", va="center", color="white", weight="bold")

    test_year = dataset.loc[dataset["Split"] == "test", "Date"].dt.year.min()
    colors = [COLORS["train"] if year < test_year else COLORS["test"] for year in yearly.index]
    axes[1].bar(yearly.index.astype(str), yearly.to_numpy(), color=colors)
    axes[1].axhline(0.5, color="#334155", linestyle="--", linewidth=1.1, label="50%Reference line")
    axes[1].set_ylim(0.30, 0.65)
    axes[1].set_ylabel("The future20Daily increase ratio")
    axes[1].set_title("The annual label ratio varies with market conditions.")
    axes[1].legend(loc="upper right", fontsize=9)
    for index, value in enumerate(yearly.to_numpy()):
        axes[1].text(index, value + 0.012, f"{value:.1%}", ha="center", fontsize=9)
    for ax in axes:
        ax.grid(axis="x", visible=False)
    fig.suptitle("The Future of the Second Experiment20Daily Gain/Loss Label Distribution", fontsize=13, y=1.01)
    fig.tight_layout()
    save(fig, "label_distribution.png")


def plot_roc(metrics: pd.DataFrame, roc_points: pd.DataFrame) -> None:
    lookup = metrics.set_index("model")
    fig, ax = plt.subplots(figsize=(8.7, 5.2))
    for model in ("logistic_regression", "decision_tree", "random_forest"):
        part = roc_points[roc_points["model"] == model]
        row = lookup.loc[model]
        ax.plot(part["fpr"], part["tpr"], color=COLORS[model], linewidth=1.8, label=f"{row['model_label']}  AUC={row['auc']:.3f}")
    ax.plot([0, 1], [0, 1], color=COLORS["neutral"], linestyle="--", linewidth=1.0, label="Random Sort AUC=0.500")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("false positive rate FPR")
    ax.set_ylabel("The true rate TPR")
    ax.set_title("The second experiment: Time Series Test SetROCcurve")
    ax.legend(loc="lower right", fontsize=9)
    fig.text(0.5, 0.014, "Note: AUCCalculated by the rising probability; The test set is only evaluated once after the design and parameters are fixed.. ", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, "roc_curves.png")


def plot_confusion(metrics: pd.DataFrame) -> None:
    models = ["logistic_regression", "decision_tree", "random_forest"]
    lookup = metrics.set_index("model")
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.6))
    for ax, model in zip(axes, models):
        row = lookup.loc[model]
        matrix = np.array([[row["tn"], row["fp"]], [row["fn"], row["tp"]]], dtype=float)
        normalized = matrix / matrix.sum(axis=1, keepdims=True)
        sns.heatmap(normalized, cmap="Blues", vmin=0, vmax=1, cbar=False, square=True, linewidths=1.5, linecolor="white", ax=ax)
        for i in range(2):
            for j in range(2):
                color = "white" if normalized[i, j] >= 0.45 else "#1F2937"
                ax.text(j + 0.5, i + 0.5, f"{int(matrix[i, j]):,}\n{normalized[i, j]:.1%}", ha="center", va="center", fontsize=10.5, color=color)
        ax.set_title(f"{row['model_label']}\nAUC={row['auc']:.3f}, F1={row['f1']:.3f}")
        ax.set_xlabel("Forecast Label")
        ax.set_ylabel("Actual Label")
        ax.set_xticklabels(["No increase 0", "rise 1"])
        ax.set_yticklabels(["No increase 0", "rise 1"], rotation=0)
    fig.suptitle("The second experiment: Time series test set confusion matrix (Threshold0.5) ", fontsize=13, y=1.04)
    fig.tight_layout()
    save(fig, "confusion_matrices.png")


def plot_importance(importance: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 6.4))
    logistic = importance[importance["model"] == "logistic_regression"].nlargest(12, "absolute_importance").sort_values("importance")
    logistic_labels = logistic["feature"].map(FEATURE_LABELS)
    axes[0].barh(logistic_labels, logistic["importance"], color=np.where(logistic["importance"] >= 0, "#4C78A8", "#9E9E9E"))
    axes[0].axvline(0, color="#334155", linewidth=1)
    axes[0].set_title("Logistic Regression: The largest absolute value12standardized coefficient")
    axes[0].set_xlabel("coefficient (Just at the moment when the probability of a rise is increasing) ")

    forest = importance[importance["model"] == "random_forest"].nlargest(12, "importance").sort_values("importance")
    axes[1].barh(forest["feature"].map(FEATURE_LABELS), forest["importance"], color="#59A14F")
    axes[1].set_title("Random Forest: former12Impurity Item Importance")
    axes[1].set_xlabel("Relative importance")
    for ax in axes:
        ax.grid(axis="y", visible=False)
        sns.despine(ax=ax)
    fig.suptitle("Feature explanation of the model in the second experiment", fontsize=13, y=1.01)
    fig.text(0.5, 0.012, "Note: Coefficient and importance describe model dependence, does not represent a causal relationship; Importance is shared among related features. ", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, "feature_importance.png")


def main() -> None:
    ensure_directories()
    configure_style()
    dataset = pd.read_csv(PROCESSED_DIR / "task5_experiment2_dataset.csv", parse_dates=["Date", "label_end_date"])
    metrics = pd.read_csv(PROCESSED_DIR / "task5_experiment2_model_metrics.csv")
    roc_points = pd.read_csv(PROCESSED_DIR / "task5_experiment2_roc_points.csv")
    importance = pd.read_csv(PROCESSED_DIR / "task5_experiment2_feature_importance.csv")
    plot_baseline_comparison(metrics)
    plot_time_split(dataset)
    plot_label_distribution(dataset)
    plot_roc(metrics, roc_points)
    plot_confusion(metrics)
    plot_importance(importance)
    write_json(
        METADATA_DIR / "chart_map.json",
        {
            "created_at": datetime.now().astimezone().isoformat(),
            "charts": [
                {"file": "baseline_comparison.png", "purpose": "compare the two experimental designs without claiming identical samples"},
                {"file": "time_split.png", "purpose": "show strict time isolation and month-end sampling"},
                {"file": "label_distribution.png", "purpose": "show label drift across market years"},
                {"file": "roc_curves.png", "purpose": "show 2025 ranking performance across thresholds"},
                {"file": "confusion_matrices.png", "purpose": "show threshold-specific errors"},
                {"file": "feature_importance.png", "purpose": "explain model dependence with a non-causal caveat"},
            ],
        },
    )
    print(f"[done] charts -> {CHART_DIR}")


if __name__ == "__main__":
    main()
