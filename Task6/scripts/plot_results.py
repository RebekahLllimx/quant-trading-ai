#!/usr/bin/env python3
"""Create numbered, report-ready TASK6 figures from frozen result tables."""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from task6_common import (
    ADDON_METADATA_DIR,
    ADDON_PROCESSED_DIR,
    CHART_DIR,
    ENHANCED_PROCESSED_DIR,
    MAIN_METADATA_DIR,
    MAIN_PROCESSED_DIR,
    MODEL_LABELS,
    SOURCE_DIR,
    ensure_directories,
)


COLORS = {
    "linear_regression": "#2F5597",
    "ridge": "#5B9BD5",
    "logistic_regression": "#8064A2",
    "decision_tree": "#ED7D31",
    "random_forest": "#70AD47",
    "hist_gradient_boosting": "#A64D79",
    "market": "#7F7F7F",
    "buffer": "#5B9BD5",
    "ml": "#C55A11",
    "buy_hold": "#7F7F7F",
    "ma": "#4472C4",
}


FEATURE_LABELS = {
    "rank__Enterprise Multiple(EVexceptEBITDA)": "EV/EBITDARanking",
    "rank__Price-to-book ratioPB(MRQ)": "PBRanking",
    "rank__Market-to-market ratePCF(Net cash flowTTM)": "PCF(Net Cash)Ranking",
    "rank__Market-to-market ratePCF(Operating cash flowTTM)": "PCF(operation)Ranking",
    "rank__P/E RatioPE(TTM)": "PERanking",
    "rank__P/E RatioPE(TTM,Deduct non-recurring gains and losses)": "DeductionPERanking",
    "rank__Price-to-sales ratioPS(TTM)": "PSRanking",
    "rank__Dividend yield(near12month)": "Dividend Yield Ranking",
    "rank__MV": "Market Cap Ranking",
    "rank__Net profit year-on-year growth rate": "Net profit growth ranking",
    "rank__Year-on-year growth rate of net assets": "Net Asset Growth Ranking",
    "rank__Total profit(Year-over-year growth rate)": "Total profit growth ranking",
    "rank__Basic earnings per share(Year-over-year growth rate)": "EPSGrowth Ranking",
    "rank__Year-on-year growth rate of total assets": "Total Asset Growth Ranking",
    "rank__Net cash flow year-on-year growth rate": "Net Cash Growth Ranking",
    "rank__Net cash flow from operating activities(Year-over-year growth rate)": "Operating Cash Flow Growth Ranking",
    "rank__Operating profit(Year-over-year growth rate)": "Operating profit growth ranking",
    "rank__Total Operating Income(Year-over-year growth rate)": "Revenue growth ranking",
    "rank__Operating revenue(Year-over-year growth rate)": "Operating income growth ranking",
    "value_composite": "value compound factor",
    "growth_composite": "growth compound factor",
    "income_growth_composite": "Compound profit growth",
    "cashflow_composite": "Cash Flow Compound Factor",
}


def setup_style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Songti SC", "STSong", "Arial Unicode MS", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.size": 10.5,
        "axes.titlesize": 13,
        "axes.labelsize": 10.5,
        "legend.fontsize": 9.5,
    })


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHART_DIR / name, dpi=190, bbox_inches="tight")
    plt.close(fig)


def main_figures() -> None:
    source = pd.read_csv(SOURCE_DIR / "model_data.csv", dtype={"Code": "string"})
    source["Date"] = pd.to_datetime(source["Date"])
    dataset = pd.read_csv(MAIN_PROCESSED_DIR / "main_model_dataset.csv", parse_dates=["Date"], dtype={"Code": "string"})
    candidates = pd.read_csv(MAIN_PROCESSED_DIR / "main_candidate_metrics.csv")
    model_metrics = pd.read_csv(MAIN_PROCESSED_DIR / "main_model_metrics.csv")
    predictions = pd.read_csv(MAIN_PROCESSED_DIR / "main_test_predictions.csv", parse_dates=["Date"], dtype={"Code": "string"})
    returns = pd.read_csv(MAIN_PROCESSED_DIR / "main_quarterly_returns.csv", parse_dates=["Date"])
    importance = pd.read_csv(MAIN_PROCESSED_DIR / "main_feature_importance.csv")
    metadata = json.loads((MAIN_METADATA_DIR / "model_run.json").read_text(encoding="utf-8"))
    strategy_model = metadata["strategy_model"]

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    counts = source.groupby("Date").size()
    axes[0].bar([f"{date.year}Q{date.quarter}" for date in counts.index], counts, color="#5B9BD5")
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].set_ylabel("stock-Quarterly Sample Number")
    axes[0].set_title("Sample size per quarter")
    clipped = source["Next_Ret"].clip(source["Next_Ret"].quantile(0.01), source["Next_Ret"].quantile(0.99))
    axes[1].hist(clipped, bins=45, color="#A5A5A5", edgecolor="white")
    axes[1].axvline(0, color="#C00000", linestyle="--", linewidth=1)
    axes[1].set_xlabel("Next Quarter Yield (1%-99%Shrink Tail Display) ")
    axes[1].set_ylabel("Sample size")
    axes[1].set_title("Target variable distribution")
    fig.suptitle("Figure1: Quarterly Sample Coverage andNext_RetDistribution", fontsize=14, y=1.02)
    save(fig, "figure01_data_profile.png")

    dates = sorted(dataset["Date"].unique())
    fig, ax = plt.subplots(figsize=(10.2, 2.8))
    for index, date in enumerate(dates):
        split = dataset.loc[dataset["Date"] == date, "Split"].iloc[0]
        color = "#4472C4" if split == "train" else "#ED7D31"
        ax.scatter(index, 1, s=260, color=color, edgecolor="white", linewidth=1.5, zorder=3)
        ax.text(index, 0.78, f"{pd.Timestamp(date).year}Q{pd.Timestamp(date).quarter}", ha="center", fontsize=9)
    ax.plot(range(len(dates)), np.ones(len(dates)), color="#BFBFBF", linewidth=2, zorder=1)
    ax.axvline(6.5, color="#C00000", linestyle="--", linewidth=1.2)
    ax.text(3, 1.25, "Training set: former7Season", ha="center", color="#2F5597", weight="bold")
    ax.text(8, 1.25, "Test set: after3Season", ha="center", color="#C55A11", weight="bold")
    ax.set_ylim(0.55, 1.5)
    ax.set_xlim(-0.5, len(dates) - 0.5)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title("Figure2: strictly arranged according to time7:3division")
    save(fig, "figure02_time_split.png")

    selected_candidates = candidates.sort_values(["model", "mean_validation_ic"], ascending=[True, False]).groupby("model").head(1)
    order = ["linear_regression", "ridge", "logistic_regression", "decision_tree", "random_forest", "hist_gradient_boosting"]
    selected_candidates = selected_candidates.set_index("model").loc[order].reset_index()
    fig, ax = plt.subplots(figsize=(8.7, 4.4))
    bars = ax.bar(selected_candidates["model_label"], selected_candidates["mean_validation_ic"], color=[COLORS[item] for item in order])
    ax.axhline(0, color="#666666", linewidth=1)
    ax.set_ylabel("Extended Window AverageRank IC")
    ax.set_title("Figure3: Ranking ability of rolling validation during training period")
    for bar, value in zip(bars, selected_candidates["mean_validation_ic"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.003, f"{value:.3f}", ha="center")
    save(fig, "figure03_validation_ic.png")

    ic_rows = []
    for (model, date), part in predictions.groupby(["model", "Date"]):
        ic_rows.append({"model": model, "model_label": MODEL_LABELS[model], "Date": date, "ic": part["Next_Ret"].corr(part["prediction"], method="spearman")})
    ic_frame = pd.DataFrame(ic_rows)
    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    for model in order:
        part = ic_frame[ic_frame["model"] == model].sort_values("Date")
        ax.plot([f"{date.year}Q{date.quarter}" for date in part["Date"]], part["ic"], marker="o", linewidth=2, label=MODEL_LABELS[model], color=COLORS[model])
    ax.axhline(0, color="#666666", linestyle="--", linewidth=1)
    ax.set_ylabel("Rank IC")
    ax.set_title("Figure4: Six models are in3A test quarter.Rank IC")
    ax.legend(ncol=3)
    save(fig, "figure04_test_ic.png")

    strict = returns[returns["portfolio"] == "strict_top30"].copy()
    plot_rows = strict[["Date", "model", "model_label", "gross_return"]].rename(columns={"gross_return": "return"})
    market = strict[strict["model"] == strategy_model][["Date", "market_return"]].drop_duplicates().assign(model="market", model_label="Market-wide equal rights").rename(columns={"market_return": "return"})
    plot_rows = pd.concat([plot_rows, market], ignore_index=True)
    pivot = plot_rows.pivot(index="Date", columns="model", values="return")
    ordered_columns = order + ["market"]
    pivot = pivot[ordered_columns]
    fig, ax = plt.subplots(figsize=(10.4, 5.0))
    x = np.arange(len(pivot))
    width = 0.11
    for index, column in enumerate(ordered_columns):
        label = MODEL_LABELS[column] if column in MODEL_LABELS else "Market-wide equal rights"
        ax.bar(x + (index - (len(ordered_columns) - 1) / 2) * width, pivot[column], width=width, label=label, color=COLORS[column])
    ax.axhline(0, color="#666666", linewidth=1)
    ax.set_xticks(x, [f"{date.year}Q{date.quarter}" for date in pivot.index])
    ax.set_ylabel("Quarterly return rate")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.set_title("Figure5: Test PeriodTop 30Comparison of portfolio and market average returns")
    ax.legend(ncol=4, fontsize=8)
    save(fig, "figure05_quarterly_returns.png")

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    for column in ordered_columns:
        wealth = (1 + pivot[column]).cumprod()
        label = MODEL_LABELS[column] if column in MODEL_LABELS else "Market-wide equal rights"
        linewidth = 3 if column == strategy_model else 1.8
        ax.plot([f"{date.year}Q{date.quarter}" for date in pivot.index], wealth, marker="o", label=label, color=COLORS[column], linewidth=linewidth)
    ax.axhline(1, color="#999999", linestyle="--", linewidth=1)
    ax.set_ylabel("Accumulated Net Asset Value (Starting point=1) ")
    ax.set_title("Figure6: Six kindsTop 30Strategy and Market Cumulative Net Worth")
    ax.legend(ncol=3, fontsize=8)
    save(fig, "figure06_cumulative_wealth.png")

    strategy = returns[returns["model"] == strategy_model].copy()
    comparison = strategy.pivot(index="Date", columns="portfolio", values=["gross_return", "net_return", "turnover"])
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    wealth_series = {
        "strictTop 30 (Gross earnings) ": (1 + comparison[("gross_return", "strict_top30")]).cumprod(),
        "strictTop 30 (Deduction of cost) ": (1 + comparison[("net_return", "strict_top30")]).cumprod(),
        "Top 50buffering (Deduction of cost) ": (1 + comparison[("net_return", "buffer_top30_top50")]).cumprod(),
    }
    for label, series in wealth_series.items():
        axes[0].plot([f"{date.year}Q{date.quarter}" for date in series.index], series, marker="o", label=label)
    axes[0].set_title("Benefit and cost sensitivity")
    axes[0].set_ylabel("Accumulated Net Asset Value")
    axes[0].legend(fontsize=8)
    width = 0.34
    x = np.arange(len(comparison))
    axes[1].bar(x - width / 2, comparison[("turnover", "strict_top30")], width, label="strictTop 30", color="#4472C4")
    axes[1].bar(x + width / 2, comparison[("turnover", "buffer_top30_top50")], width, label="Top 50buffering", color="#5B9BD5")
    axes[1].set_xticks(x, [f"{date.year}Q{date.quarter}" for date in comparison.index])
    axes[1].set_ylim(0, 1.08)
    axes[1].set_ylabel("Unilateral turnover rate")
    axes[1].set_title("Turnover Rate Comparison")
    axes[1].legend(fontsize=8)
    fig.suptitle("Figure7: 20bpCost and buffer swap sensitivity", fontsize=14, y=1.02)
    save(fig, "figure07_cost_buffer.png")

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 5.0))
    ridge = importance[importance["model"] == "ridge"].dropna().nlargest(10, "absolute_importance").sort_values("importance")
    axes[0].barh([FEATURE_LABELS.get(item, item) for item in ridge["feature"]], ridge["importance"], color=np.where(ridge["importance"] >= 0, "#4472C4", "#C55A11"))
    axes[0].axvline(0, color="#666666", linewidth=1)
    axes[0].set_title("RidgeRegression coefficient (direction) ")
    forest = importance[importance["model"] == "random_forest"].dropna().nlargest(10, "absolute_importance").sort_values("importance")
    axes[1].barh([FEATURE_LABELS.get(item, item) for item in forest["feature"]], forest["importance"], color="#70AD47")
    axes[1].set_title("Random forest feature importance")
    fig.suptitle("Figure8: Feature dependence of regularized linear models and tree models", fontsize=14, y=1.02)
    save(fig, "figure08_feature_importance.png")


def additional_figures() -> None:
    daily = pd.read_csv(ADDON_PROCESSED_DIR / "additional_daily_features.csv", parse_dates=["trade_date"])
    metrics = pd.read_csv(ADDON_PROCESSED_DIR / "additional_model_metrics.csv")
    roc = pd.read_csv(ADDON_PROCESSED_DIR / "additional_roc_points.csv")
    tuning = pd.read_csv(ADDON_PROCESSED_DIR / "additional_tuning_rounds.csv")
    strategy = pd.read_csv(ADDON_PROCESSED_DIR / "additional_strategy_daily.csv", parse_dates=["trade_date"])
    metadata = json.loads((ADDON_METADATA_DIR / "model_run.json").read_text(encoding="utf-8"))
    addon_quality = json.loads((ADDON_METADATA_DIR / "data_quality_report.json").read_text(encoding="utf-8"))
    security_name = addon_quality["security_name_used_in_report"]

    fig, axes = plt.subplots(2, 1, figsize=(10.2, 6.4), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    axes[0].plot(daily["trade_date"], daily["close"], label="Close", color="#4472C4", linewidth=1.6)
    axes[0].plot(daily["trade_date"], daily["ma5"], label="MA5", color="#ED7D31", linewidth=1)
    axes[0].plot(daily["trade_date"], daily["ma20"], label="MA20", color="#70AD47", linewidth=1)
    test_start = pd.Timestamp(addon_quality["test_start"])
    axes[0].axvline(test_start, color="#C00000", linestyle="--", linewidth=1.2, label="Test Period Start")
    axes[0].set_ylabel("Price")
    axes[0].legend(ncol=4)
    axes[1].plot(daily["trade_date"], daily["rsi14"] * 100, color="#A64D79", linewidth=1.2)
    axes[1].axhline(70, color="#C00000", linestyle="--", linewidth=1)
    axes[1].axhline(30, color="#70AD47", linestyle="--", linewidth=1)
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("RSI14")
    fig.suptitle(f"Figure9: {security_name}Price, Trends andRSIFilter Criteria", fontsize=14, y=1.02)
    save(fig, "figure09_additional_indicators.png")

    fig, axes = plt.subplots(2, 1, figsize=(10.2, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
    buy_threshold = float(metadata["signal"]["buy_threshold"])
    sell_threshold = float(metadata["signal"]["sell_threshold"])
    axes[0].plot(strategy["trade_date"], strategy["strategy_probability"], color="#C55A11", linewidth=1.4, label="Probability of increase")
    axes[0].axhline(buy_threshold, color="#70AD47", linestyle="--", label=f"Buy Threshold{buy_threshold:.2f}")
    axes[0].axhline(sell_threshold, color="#C00000", linestyle="--", label=f"Sell threshold{sell_threshold:.2f}")
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("Probability")
    axes[0].legend(ncol=3)
    axes[1].fill_between(strategy["trade_date"], strategy["ml_position"], color="#5B9BD5", alpha=0.75)
    axes[1].set_ylim(0, float(metadata["signal"]["max_position"]) * 1.05)
    axes[1].set_ylabel("Position")
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    fig.suptitle(f"Figure10: {metadata['selected_strategy_model_label']}Probability, Double threshold and actual position", fontsize=14, y=1.02)
    save(fig, "figure10_additional_probability_position.png")

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    ax.plot(strategy["trade_date"], strategy["ml_wealth"], label="MLtiming", color=COLORS["ml"], linewidth=2.3)
    ax.plot(strategy["trade_date"], strategy["buy_hold_wealth"], label="Buy and hold", color=COLORS["buy_hold"], linewidth=1.8)
    ax.plot(strategy["trade_date"], strategy["ma_wealth"], label="Moving Average Strategy", color=COLORS["ma"], linewidth=1.8)
    ax.axhline(1, color="#999999", linestyle="--", linewidth=1)
    ax.set_ylabel("Cumulative Net Deduction Cost")
    ax.set_title("Figure11: Test period net value of three strategies in the additional questions")
    ax.legend()
    save(fig, "figure11_additional_wealth.png")

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    ax.plot(strategy["trade_date"], strategy["ml_drawdown"], label="MLtiming", color=COLORS["ml"], linewidth=2)
    ax.plot(strategy["trade_date"], strategy["buy_hold_drawdown"], label="Buy and hold", color=COLORS["buy_hold"], linewidth=1.5)
    ax.plot(strategy["trade_date"], strategy["ma_drawdown"], label="Moving Average Strategy", color=COLORS["ma"], linewidth=1.5)
    ax.axhline(0, color="#666666", linewidth=1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.set_ylabel("drawdown")
    ax.set_title("Figure12: Drawdown paths of three additional question strategies")
    ax.legend()
    save(fig, "figure12_additional_drawdown.png")

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.8))
    model_order = ["logistic_regression", "decision_tree", "random_forest"]
    metric_index = metrics.set_index("model").loc[model_order]
    model_x = np.arange(len(model_order))
    axes[0].bar(model_x, metric_index["test_auc"], color=["#4472C4", "#ED7D31", "#70AD47"])
    axes[0].axhline(0.5, color="#7F7F7F", linestyle="--", linewidth=1)
    axes[0].set_xticks(model_x, [MODEL_LABELS[item] for item in model_order], rotation=12)
    axes[0].set_ylim(0.3, 0.8)
    axes[0].set_ylabel("TestAUC")
    axes[0].set_title("The second round of 3 model comparison")
    for index, value in enumerate(metric_index["test_auc"]):
        axes[0].text(index, value + 0.012, f"{value:.3f}", ha="center", fontsize=9)

    round_x = np.arange(len(tuning))
    width = 0.34
    axes[1].bar(round_x - width / 2, tuning["validation_auc"], width, label="Internal verification during training period", color="#5B9BD5")
    axes[1].bar(round_x + width / 2, tuning["test_auc"], width, label="Test Period", color="#ED7D31")
    axes[1].axhline(0.5, color="#7F7F7F", linestyle="--", linewidth=1)
    axes[1].set_xticks(round_x, [f"The{int(item)}wheel" for item in tuning["round"]])
    axes[1].set_ylim(0.3, 0.85)
    axes[1].set_title("Three-round parameter tuning results")
    axes[1].legend(fontsize=8)
    for index, (validation_auc, test_auc) in enumerate(zip(tuning["validation_auc"], tuning["test_auc"])):
        axes[1].text(index - width / 2, validation_auc + 0.012, f"{validation_auc:.3f}", ha="center", fontsize=8)
        axes[1].text(index + width / 2, test_auc + 0.012, f"{test_auc:.3f}", ha="center", fontsize=8)
    fig.suptitle("Figure13: Three rounds of parameter tuning compared with classification models", fontsize=14, y=1.02)
    save(fig, "figure13_tuning_results.png")


def enhanced_figures() -> None:
    weighted_returns = pd.read_csv(ENHANCED_PROCESSED_DIR / "main_weighted_quarterly_returns.csv", parse_dates=["Date"])
    weighted_metrics = pd.read_csv(ENHANCED_PROCESSED_DIR / "main_weighted_strategy_metrics.csv")
    auc_grid = pd.read_csv(ENHANCED_PROCESSED_DIR / "additional_guarded_auc_grid.csv")

    labels = {"EW_Top30": "EW Top-30", "PW_Top30": "PW Top-30", "Validation_Selected": "Validation Set SelectionPW20"}
    colors = {"EW_Top30": "#4472C4", "PW_Top30": "#70AD47", "Validation_Selected": "#ED7D31"}
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    pivot = weighted_returns.pivot(index="Date", columns="portfolio_label", values="net_return")
    x = np.arange(len(pivot))
    width = 0.25
    for idx, column in enumerate(["EW_Top30", "PW_Top30", "Validation_Selected"]):
        axes[0].bar(x + (idx - 1) * width, pivot[column], width, label=labels[column], color=colors[column])
    axes[0].set_xticks(x, [f"{d.year}Q{d.quarter}" for d in pivot.index])
    axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    axes[0].set_ylabel("Cost-Deduction Quarterly Earnings")
    axes[0].set_title("Quarterly Earnings")
    axes[0].legend(fontsize=8)
    metric_index = weighted_metrics.set_index("portfolio_label")
    order = ["EW_Top30", "PW_Top30", "Validation_Selected"]
    bars = axes[1].bar([labels[x] for x in order], metric_index.loc[order, "total_return"], color=[colors[x] for x in order])
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    axes[1].set_ylabel("Cumulative net income for three quarters")
    axes[1].set_title("Accumulated income (Volatility not shown) ")
    axes[1].tick_params(axis="x", rotation=10)
    for bar, value in zip(bars, metric_index.loc[order, "total_return"]):
        axes[1].text(bar.get_x() + bar.get_width()/2, value + .008, f"{value:.2%}", ha="center")
    fig.suptitle("Figure14: equal weightEWweighted with predictionPWCombination Comparison", fontsize=14, y=1.02)
    save(fig, "figure14_ew_pw_comparison.png")

    fig, ax = plt.subplots(figsize=(8.8, 4.5))
    compare = auc_grid.set_index("candidate").loc[["validation_winner", "existing_baseline"]]
    x = np.arange(2)
    width = .34
    ax.bar(x-width/2, compare["validation_auc"], width, label="VerificationAUC", color="#5B9BD5")
    ax.bar(x+width/2, compare["test_auc"], width, label="TestAUC", color="#ED7D31")
    ax.axhline(.5, color="#7F7F7F", linestyle="--", linewidth=1)
    ax.set_xticks(x, ["Grid Validation Champion", "Original rolling logistic regression"])
    ax.set_ylim(.45, .80)
    ax.set_ylabel("AUC")
    ax.set_title("Figure15: 144Out-of-sample test of controlled grid search groups")
    ax.legend()
    for idx, row in enumerate(compare.itertuples()):
        ax.text(idx-width/2, row.validation_auc+.008, f"{row.validation_auc:.3f}", ha="center")
        ax.text(idx+width/2, row.test_auc+.008, f"{row.test_auc:.3f}", ha="center")
    save(fig, "figure15_guarded_auc_grid.png")


def main() -> None:
    ensure_directories()
    for existing in CHART_DIR.glob("figure*.png"):
        existing.unlink()
    setup_style()
    main_figures()
    additional_figures()
    enhanced_figures()
    print("[plots] wrote 15 figures to artifacts/charts/task6")


if __name__ == "__main__":
    main()
