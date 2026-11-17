"""Build a small, consistent set of English figures for the PDF reports."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = ["#355C7D", "#C06C84", "#6C8EAD", "#E39A59", "#4F8A72", "#8C6BB1"]


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def load_market_file(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame = frame.sort_values("Date").drop_duplicates("Date")
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["Close"])


def task1() -> None:
    files = sorted((ROOT / "data/csv").glob("*_daily.csv"))
    fig, ax = plt.subplots(figsize=(9.2, 4.3), constrained_layout=True)
    for path in files:
        frame = load_market_file(path)
        label = path.stem.replace("_daily", "").split("_", 1)[1].replace("_", " ").title()
        normalized = frame["Close"] / frame["Close"].iloc[0] * 100
        ax.plot(frame["Date"], normalized, lw=1.3, label=label)
    ax.axhline(100, color="#999999", lw=0.8)
    ax.set(title="Normalized Closing Prices", ylabel="Initial value = 100")
    ax.grid(alpha=0.2)
    ax.legend(ncol=2, fontsize=7, frameon=False)
    save(fig, "task1_normalized_prices.png")

    summary = pd.read_csv(ROOT / "data/csv/AH_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9), constrained_layout=True)
    names = summary["Name"]
    axes[0].barh(names, summary["Return (%)"], color=np.where(summary["Return (%)"] >= 0, COLORS[4], COLORS[1]))
    axes[0].axvline(0, color="#666666", lw=0.8)
    axes[0].set_title("Period Return")
    axes[0].set_xlabel("Percent")
    axes[1].scatter(summary["Annualized Volatility (%)"], summary["Maximum Drawdown (%)"], c=COLORS[0], s=42)
    for _, row in summary.iterrows():
        axes[1].annotate(row["Name"], (row["Annualized Volatility (%)"], row["Maximum Drawdown (%)"]), xytext=(4, 3), textcoords="offset points", fontsize=7)
    axes[1].set(title="Risk Comparison", xlabel="Annualized volatility (%)", ylabel="Maximum drawdown (%)")
    axes[1].grid(alpha=0.2)
    save(fig, "task1_market_comparison.png")


def task2() -> None:
    frame = load_market_file(ROOT / "data/csv/600519_kweichow_moutai_a_share_daily.csv")
    close = frame["Close"]
    ma20 = close.rolling(20).mean()
    sigma = close.rolling(20).std(ddof=0)
    upper, lower = ma20 + 2 * sigma, ma20 - 2 * sigma
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False, min_periods=9).mean()

    fig, axes = plt.subplots(3, 1, figsize=(9.2, 7.2), sharex=True, constrained_layout=True, gridspec_kw={"height_ratios": [2.2, 1, 1]})
    axes[0].plot(frame["Date"], close, color=COLORS[0], lw=1.2, label="Close")
    axes[0].plot(frame["Date"], ma20, color=COLORS[3], lw=1, label="MA20")
    axes[0].fill_between(frame["Date"], lower, upper, color=COLORS[2], alpha=0.15, label="Bollinger band")
    axes[0].set_title("Price, Trend, and Volatility Envelope")
    axes[0].legend(frameon=False, ncol=3, fontsize=8)
    axes[1].plot(frame["Date"], rsi, color=COLORS[4], lw=1)
    axes[1].axhline(70, color="#999999", ls="--", lw=0.8); axes[1].axhline(30, color="#999999", ls="--", lw=0.8)
    axes[1].set(ylabel="RSI(14)", ylim=(0, 100))
    axes[2].plot(frame["Date"], dif, color=COLORS[0], lw=1, label="DIF")
    axes[2].plot(frame["Date"], dea, color=COLORS[1], lw=1, label="DEA")
    axes[2].bar(frame["Date"], 2 * (dif - dea), color=np.where((dif-dea) >= 0, COLORS[4], COLORS[1]), alpha=0.45)
    axes[2].set(ylabel="MACD"); axes[2].legend(frameon=False, fontsize=8)
    for ax in axes: ax.grid(alpha=0.18)
    save(fig, "task2_indicator_panels.png")


def task3() -> None:
    raw = json.loads((ROOT / "Task3/dashboard/data.json").read_text())['600519']
    frame = pd.DataFrame(raw["data"], columns=["Date", "Open", "Close", "High", "Low", "Volume"])
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame["MA5"] = frame["Close"].rolling(5).mean(); frame["MA15"] = frame["Close"].rolling(15).mean()
    cross = np.sign(frame["MA5"] - frame["MA15"]).diff()
    fig, ax = plt.subplots(figsize=(9.2, 4.5), constrained_layout=True)
    ax.plot(frame["Date"], frame["Close"], color="#333333", lw=1, label="Close")
    ax.plot(frame["Date"], frame["MA5"], color=COLORS[3], lw=1, label="MA5")
    ax.plot(frame["Date"], frame["MA15"], color=COLORS[0], lw=1, label="MA15")
    buys = frame[cross > 0]; sells = frame[cross < 0]
    ax.scatter(buys["Date"], buys["Close"], marker="^", color=COLORS[4], s=35, label="Long entry")
    ax.scatter(sells["Date"], sells["Close"], marker="v", color=COLORS[1], s=35, label="Exit")
    ax.set(title="MA(5, 15) Signals on Kweichow Moutai", ylabel="Adjusted close")
    ax.grid(alpha=0.2); ax.legend(frameon=False, ncol=5, fontsize=8)
    save(fig, "task3_signals.png")

    short_grid = [3, 5, 10, 15, 20, 30]
    long_grid = [10, 15, 20, 30, 40, 60]
    returns = np.full((len(short_grid), len(long_grid)), np.nan)
    daily = frame["Close"].pct_change().fillna(0)
    for i, short in enumerate(short_grid):
        for j, long in enumerate(long_grid):
            if short >= long: continue
            signal = frame["Close"].rolling(short).mean() > frame["Close"].rolling(long).mean()
            position = signal.shift(1, fill_value=False).astype(float)
            turnover = position.diff().abs().fillna(0)
            net = position * daily - turnover * 0.0004
            returns[i, j] = (1 + net).prod() - 1
    fig, ax = plt.subplots(figsize=(7.4, 4.6), constrained_layout=True)
    image = ax.imshow(returns * 100, cmap="RdYlGn", aspect="auto")
    ax.set(xticks=range(len(long_grid)), xticklabels=long_grid, yticks=range(len(short_grid)), yticklabels=short_grid, xlabel="Long window", ylabel="Short window", title="Parameter Sensitivity: Net Return (%)")
    for i in range(len(short_grid)):
        for j in range(len(long_grid)):
            if np.isfinite(returns[i,j]): ax.text(j, i, f"{returns[i,j]*100:.1f}", ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, shrink=0.8)
    save(fig, "task3_sensitivity.png")


def task4() -> None:
    spec = importlib.util.spec_from_file_location("turtle_strategy", ROOT / "Task4/scripts/turtle_strategy.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    raw = json.loads((ROOT / "Task3/dashboard/data.json").read_text())["600519"]
    frame = pd.DataFrame(raw["data"], columns=["Date", "Open", "Close", "High", "Low", "Volume"])
    frame["Date"] = pd.to_datetime(frame["Date"])
    result = module.run_backtest(frame)
    metrics = module.calc_metrics(result)
    equity = pd.DataFrame(result["equity_curve"]); equity["date"] = pd.to_datetime(equity["date"])
    bench = pd.DataFrame(result["bh_equity_curve"]); bench["date"] = pd.to_datetime(bench["date"])
    e = equity["equity"] / equity["equity"].iloc[0]
    b = bench["equity"] / bench["equity"].iloc[0]
    drawdown = e / e.cummax() - 1
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 6.0), sharex=True, constrained_layout=True, gridspec_kw={"height_ratios": [2, 1]})
    axes[0].plot(equity["date"], e, color=COLORS[0], label="Turtle strategy")
    axes[0].plot(bench["date"], b, color="#777777", ls="--", label="Buy and hold")
    axes[0].set(title="Equity Comparison", ylabel="Growth of 1.0"); axes[0].legend(frameon=False)
    axes[1].fill_between(equity["date"], drawdown, 0, color=COLORS[1], alpha=0.35)
    axes[1].set(ylabel="Drawdown", xlabel="Date")
    for ax in axes: ax.grid(alpha=0.2)
    fig.text(0.99, 0.01, f"Return {metrics['total_return']:.2f}% | MDD {metrics['mdd']:.2f}% | Trades {metrics['total_trades']}", ha="right", fontsize=8, color="#555555")
    save(fig, "task4_equity_drawdown.png")


def task5() -> None:
    roc = pd.read_csv(ROOT / "data/task5/breast_cancer/results/roc_points.csv")
    metrics = pd.read_csv(ROOT / "data/task5/breast_cancer/results/model_metrics.csv")
    label_map = {
        "logistic_regression": "Logistic regression",
        "decision_tree": "Decision tree",
        "random_forest": "Random forest",
        "gradient_boosting": "Gradient boosting",
    }
    fig, ax = plt.subplots(figsize=(8.4, 4.8), constrained_layout=True)
    for (model, group), color in zip(roc.groupby("model", sort=False), COLORS):
        auc = metrics.loc[metrics["model"] == model, "roc_auc"].iloc[0]
        ax.plot(group["fpr"], group["tpr"], lw=1.8, color=color,
                label=f"{label_map[model]} (AUC {auc:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", lw=1, color="#777777", label="Random ranking")
    ax.set(xlabel="False-positive rate", ylabel="True-positive rate",
           title="Breast-Cancer Test-Set ROC Curves", xlim=(0, 1), ylim=(0, 1))
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    save(fig, "task5_medical_roc.png")

    finance = pd.read_csv(ROOT / "data/task5/experiment2/processed/task5_experiment2_model_metrics.csv")
    finance = finance[finance["model"] != "constant_baseline"].copy()
    finance["label"] = finance["model"].map(label_map)
    x = np.arange(len(finance))
    lower = finance["auc"] - finance["auc_ci_low"]
    upper = finance["auc_ci_high"] - finance["auc"]
    fig, ax = plt.subplots(figsize=(8.4, 4.2), constrained_layout=True)
    ax.bar(x, finance["auc"], color=COLORS[:len(finance)], width=0.62)
    ax.errorbar(x, finance["auc"], yerr=[lower, upper], fmt="none", ecolor="#333333", capsize=4, lw=1)
    ax.axhline(0.5, color="#777777", ls="--", lw=1, label="Random-ranking baseline")
    ax.set(xticks=x, xticklabels=finance["label"], ylabel="Test ROC-AUC",
           title="Chronological Financial Test", ylim=(0.38, 0.66))
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "task5_financial_auc.png")


def task6() -> None:
    quarterly = pd.read_csv(ROOT / "data/task6/main/processed/main_quarterly_returns.csv")
    quarterly["Date"] = pd.to_datetime(quarterly["Date"])
    fig, ax = plt.subplots(figsize=(8.6, 4.6), constrained_layout=True)
    model_order = ["linear_regression", "ridge", "logistic_regression", "decision_tree", "random_forest"]
    labels = {
        "linear_regression": "Linear regression",
        "ridge": "Ridge",
        "logistic_regression": "Logistic regression",
        "decision_tree": "Decision tree",
        "random_forest": "Random forest",
    }
    for model, color in zip(model_order, COLORS):
        group = quarterly[quarterly["model"] == model].sort_values("Date")
        wealth = (1 + group["net_return"]).cumprod()
        ax.plot(group["Date"], wealth, marker="o", ms=4, lw=1.5, color=color, label=labels[model])
    market = quarterly[quarterly["model"] == model_order[0]].sort_values("Date")
    ax.plot(market["Date"], (1 + market["market_return"]).cumprod(), marker="o", ms=4,
            lw=1.5, color="#777777", label="Market equal weight")
    ax.axhline(1, color="#999999", lw=0.8)
    ax.set(title="Top-30 Portfolio Wealth in the Test Quarters", ylabel="Growth of 1.0", xlabel="Quarter")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    save(fig, "task6_portfolio_wealth.png")

    weighted = pd.read_csv(ROOT / "data/task6/enhanced/processed/main_weighted_quarterly_returns.csv")
    weighted["Date"] = pd.to_datetime(weighted["Date"])
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 4.0), constrained_layout=True)
    for label, color in zip(["EW_Top30", "PW_Top30"], COLORS[:2]):
        group = weighted[weighted["portfolio_label"] == label].sort_values("Date")
        display = "Equal weight" if label.startswith("EW") else "Prediction weight"
        quarter_labels = [f"{date.year} Q{date.quarter}" for date in group["Date"]]
        positions = np.arange(len(group)) + (-0.18 if label.startswith("EW") else 0.18)
        axes[0].bar(positions, group["net_return"] * 100, width=0.36,
                    alpha=0.82, color=color, label=display)
        axes[1].plot(np.arange(len(group)), (1 + group["net_return"]).cumprod(), marker="o",
                     lw=1.7, color=color, label=display)
    axes[0].set(title="Quarterly Net Return", ylabel="Percent")
    axes[0].set(xticks=np.arange(len(quarter_labels)), xticklabels=quarter_labels)
    axes[1].set(xticks=np.arange(len(quarter_labels)), xticklabels=quarter_labels)
    axes[1].set(title="Cumulative Wealth", ylabel="Growth of 1.0")
    for ax in axes:
        ax.grid(axis="y", alpha=0.18)
        ax.legend(frameon=False, fontsize=8)
    save(fig, "task6_weighting_comparison.png")

    guarded = pd.read_csv(ROOT / "data/task6/enhanced/processed/additional_guarded_auc_grid.csv")
    guarded["display"] = guarded["candidate"].map({
        "validation_winner": "Validation winner",
        "existing_baseline": "Frozen rolling baseline",
    })
    x = np.arange(len(guarded))
    width = 0.34
    fig, ax = plt.subplots(figsize=(7.6, 3.8), constrained_layout=True)
    ax.bar(x - width / 2, guarded["validation_auc"], width, color=COLORS[0], label="Validation AUC")
    ax.bar(x + width / 2, guarded["test_auc"], width, color=COLORS[3], label="Test AUC")
    ax.axhline(0.5, color="#777777", ls="--", lw=1, label="Random-ranking baseline")
    for offset, column in [(-width / 2, "validation_auc"), (width / 2, "test_auc")]:
        for position, value in zip(x, guarded[column]):
            ax.text(position + offset, value + 0.008, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set(
        xticks=x,
        xticklabels=guarded["display"],
        ylabel="ROC-AUC",
        title="Validation Selection and Untouched Test Performance",
        ylim=(0.45, 0.80),
    )
    ax.grid(axis="y", alpha=0.18)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center")
    save(fig, "task6_validation_gap.png")


def task7() -> None:
    data = json.loads((ROOT / "Task7/dashboard/data/dashboard.json").read_text())
    dates = pd.to_datetime(data["dates"])
    fig, ax = plt.subplots(figsize=(9.2, 4.4), constrained_layout=True)
    for strategy, color in zip(["A", "B", "C"], COLORS):
        ax.plot(dates, data["nav_series"][strategy], label=f"Strategy {strategy}", color=color, lw=1.3)
    ax.set(title="Public-Data Shadow Portfolio", ylabel="Portfolio value", xlabel="Date")
    ax.grid(alpha=0.2); ax.legend(frameon=False)
    save(fig, "task7_shadow_nav.png")

    backtests = pd.DataFrame(data["joinquant_backtests"])
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8), constrained_layout=True)
    axes[0].bar(backtests["strategy"], backtests["strategy_return"] * 100, color=COLORS[:3])
    axes[0].axhline(0, color="#666666", lw=0.8); axes[0].set(title="JoinQuant Cumulative Return", ylabel="Percent")
    axes[1].bar(backtests["strategy"], -backtests["max_drawdown"] * 100, color=COLORS[:3])
    axes[1].set(title="JoinQuant Maximum Drawdown", ylabel="Loss from peak (%)")
    save(fig, "task7_platform_comparison.png")


def task8() -> None:
    fig, ax = plt.subplots(figsize=(9.2, 2.8), constrained_layout=True)
    ax.axis("off")
    labels = ["Market data", "Indicators", "Rule-based\nstrategies", "Machine\nlearning", "Portfolio\nconstruction", "Monitoring"]
    x = np.linspace(0.07, 0.93, len(labels))
    for i, (xi, label) in enumerate(zip(x, labels)):
        ax.text(xi, 0.5, label, ha="center", va="center", fontsize=9, bbox=dict(boxstyle="round,pad=0.45", fc="#F4F6F8", ec="#9AA3AC"))
        if i < len(labels)-1: ax.annotate("", (x[i+1]-0.065,0.5), (xi+0.065,0.5), arrowprops=dict(arrowstyle="->", color="#6B7178", lw=1.1))
    ax.set_title("Research Pipeline", fontsize=12, fontweight="bold")
    save(fig, "task8_pipeline.png")


if __name__ == "__main__":
    task1(); task2(); task3(); task4(); task5(); task6(); task7(); task8()
    for path in sorted(OUT.glob("*.png")):
        print(path)
