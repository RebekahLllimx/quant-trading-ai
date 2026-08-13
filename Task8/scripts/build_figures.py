#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 TASK8 综合报告统一重绘核心中文图表。"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "charts" / "task8"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#1F4E79"
BLUE_2 = "#5B9BD5"
ORANGE = "#E07A3F"
GREEN = "#2E7D65"
RED = "#B24A4A"
GRAY = "#7A7F87"
LIGHT_GRAY = "#D9DEE5"
GRID = "#E7EAEE"
TEXT = "#20252B"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": [
            "Songti SC",
            "STSong",
            "SimSun",
            "Times New Roman",
            "Arial Unicode MS",
            "serif",
        ],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#AAB1BA",
        "axes.labelcolor": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "text.color": TEXT,
        "font.size": 10.5,
    }
)


def finish(fig: plt.Figure, name: str, *, h_pad: float = 1.0) -> Path:
    path = OUT / name
    fig.tight_layout(h_pad=h_pad)
    fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def percent_label(value: float, digits: int = 1) -> str:
    return f"{value:+.{digits}f}%"


def style_axis(ax: plt.Axes, *, ygrid: bool = True) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    if ygrid:
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def figure01_system_loop() -> Path:
    fig, ax = plt.subplots(figsize=(11.2, 4.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    boxes = [
        (0.45, 3.55, "研究问题", "明确收益来源与可否证假设"),
        (2.75, 3.55, "数据治理", "时点、复权、缺失与版本"),
        (5.05, 3.55, "特征与模型", "指标、规则与机器学习"),
        (7.35, 3.55, "组合决策", "仓位、成本与风险预算"),
        (9.65, 3.55, "执行监控", "订单、成交、漂移与停用"),
    ]
    for i, (x, y, title, sub) in enumerate(boxes):
        color = BLUE if i < 3 else (ORANGE if i == 3 else GREEN)
        patch = FancyBboxPatch(
            (x, y),
            1.9,
            1.25,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor="white",
            edgecolor=color,
            linewidth=1.8,
        )
        ax.add_patch(patch)
        ax.text(x + 0.95, y + 0.79, title, ha="center", va="center", fontsize=12, weight="bold", color=color)
        ax.text(x + 0.95, y + 0.37, sub, ha="center", va="center", fontsize=8.8, color=TEXT)
        if i < len(boxes) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + 1.92, y + 0.63),
                    (boxes[i + 1][0] - 0.05, y + 0.63),
                    arrowstyle="-|>",
                    mutation_scale=13,
                    linewidth=1.3,
                    color=GRAY,
                )
            )

    feedback = FancyBboxPatch(
        (3.0, 0.65),
        6.0,
        1.35,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        facecolor="#F5F7FA",
        edgecolor=GRAY,
        linewidth=1.2,
    )
    ax.add_patch(feedback)
    ax.text(6.0, 1.48, "复盘与迭代", ha="center", va="center", fontsize=12, weight="bold", color=TEXT)
    ax.text(
        6.0,
        1.05,
        "比较预期与实现差异，更新数据、假设、参数、风控和监控规则",
        ha="center",
        va="center",
        fontsize=9.3,
        color=TEXT,
    )
    ax.add_patch(
        FancyArrowPatch(
            (10.6, 3.5),
            (9.0, 1.45),
            connectionstyle="arc3,rad=-0.14",
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.3,
            color=GRAY,
        )
    )
    ax.add_patch(
        FancyArrowPatch(
            (3.0, 1.45),
            (1.35, 3.5),
            connectionstyle="arc3,rad=-0.14",
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.3,
            color=GRAY,
        )
    )
    ax.text(6.0, 5.55, "量化研究在数据、模型、决策和执行之间循环校正", ha="center", fontsize=14, weight="bold")
    ax.text(6.0, 0.12, "本报告按系统环节讨论前七项任务，说明每一层输入如何影响最终交易结果。", ha="center", fontsize=9.2, color=GRAY)
    return finish(fig, "图01_量化研究闭环.png")


def figure02_rules_return_drawdown() -> Path:
    labels = ["双均线策略", "海龟策略", "买入持有"]
    returns = np.array([-5.67, -0.74, -18.24])
    drawdowns = np.array([-15.20, -9.72, -21.35])
    colors = [BLUE, ORANGE, GRAY]

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.6), sharey=False)
    for ax, values, title in zip(axes, [returns, drawdowns], ["累计收益率", "最大回撤"]):
        x = np.arange(len(labels))
        bars = ax.bar(x, values, color=colors, width=0.62, zorder=3)
        ax.axhline(0, color=TEXT, linewidth=0.9)
        ax.set_xticks(x, labels)
        ax.set_ylabel("百分比（%）")
        ax.set_title(title, fontsize=12.5, weight="bold")
        style_axis(ax)
        lower = min(values) - 5
        ax.set_ylim(lower, 3)
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.8, percent_label(v, 2), ha="center", va="bottom", color="white", fontsize=9.5, weight="bold")
    fig.suptitle("任务三与任务四规则策略的收益和回撤比较", fontsize=14, weight="bold", y=1.01)
    fig.text(
        0.5,
        -0.02,
        "贵州茅台，2025-05-29至2026-07-03；初始资金100万元；手续费与滑点口径一致。",
        ha="center",
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图02_规则策略收益与回撤.png")


def figure03_parameter_heatmap() -> Path:
    short = [3, 5, 10, 15, 20, 30]
    long = [10, 15, 20, 30, 40, 60]
    returns = np.array(
        [
            [70.2, -11.5, -10.8, -17.4, -15.4, -16.9],
            [-7.4, -11.5, -20.8, -18.7, -17.4, -19.8],
            [np.nan, -16.8, -20.5, -17.1, -13.8, -8.5],
            [np.nan, np.nan, -15.9, -22.1, -17.8, -11.5],
            [np.nan, np.nan, np.nan, -17.4, -10.4, -11.1],
            [np.nan, np.nan, np.nan, np.nan, -9.0, -6.8],
        ]
    )
    cmap = LinearSegmentedColormap.from_list("risk", ["#B24A4A", "#F0B56D", "#F7F7F7", "#78B5A4", "#2E7D65"])
    masked = np.ma.masked_invalid(returns)

    fig, ax = plt.subplots(figsize=(8.7, 5.4))
    im = ax.imshow(masked, cmap=cmap, vmin=-30, vmax=30, aspect="auto")
    ax.set_xticks(np.arange(len(long)), long)
    ax.set_yticks(np.arange(len(short)), short)
    ax.set_xlabel("长均线周期（日）")
    ax.set_ylabel("短均线周期（日）")
    ax.set_title("双均线参数组合的累计收益率", fontsize=13.5, weight="bold", pad=12)
    for i in range(len(short)):
        for j in range(len(long)):
            value = returns[i, j]
            if not math.isnan(value):
                color = "white" if value < -14 or value > 30 else TEXT
                ax.text(j, i, f"{value:.1f}", ha="center", va="center", color=color, fontsize=9.5, weight="bold" if value > 0 else "normal")
    cbar = fig.colorbar(im, ax=ax, shrink=0.88)
    cbar.set_label("累计收益率（%）")
    ax.text(
        0.0,
        -0.18,
        "空白格表示短周期不小于长周期；孤立高值不构成稳定参数区域。",
        transform=ax.transAxes,
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图03_双均线参数敏感性.png")


def figure04_task5_auc_intervals() -> Path:
    p = ROOT / "data" / "task5" / "processed" / "task5_model_metrics.csv"
    df = pd.read_csv(p, encoding="utf-8-sig")
    df = df[df["model"] != "majority_baseline"].copy()
    df["auc_pct"] = df["auc"]
    y = np.arange(len(df))
    left = df["auc"] - df["auc_ci_low"]
    right = df["auc_ci_high"] - df["auc"]

    fig, ax = plt.subplots(figsize=(8.8, 4.4))
    ax.errorbar(
        df["auc"],
        y,
        xerr=np.vstack([left, right]),
        fmt="o",
        color=BLUE,
        ecolor=BLUE_2,
        elinewidth=2.2,
        capsize=5,
        markersize=7,
        zorder=3,
    )
    ax.axvline(0.5, color=RED, linestyle="--", linewidth=1.2, label="随机排序基准（0.500）")
    ax.set_yticks(y, df["model_label"])
    ax.set_xlim(0.20, 0.74)
    ax.set_xlabel("测试集曲线下面积")
    ax.set_title("任务五金融分类模型的样本外判别能力及区间", fontsize=13.5, weight="bold")
    style_axis(ax)
    for x, yy in zip(df["auc"], y):
        ax.text(x + 0.012, yy, f"{x:.3f}", va="center", fontsize=9.5)
    ax.legend(loc="lower right", frameon=False)
    ax.text(
        0.0,
        -0.2,
        "点为2025年测试集曲线下面积；横线为重采样区间。三种模型区间均覆盖0.500。",
        transform=ax.transAxes,
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图04_TASK5样本外AUC区间.png")


def figure05_task5_cross_period_auc() -> Path:
    cand = pd.read_csv(ROOT / "data" / "task5" / "processed" / "task5_candidate_metrics.csv", encoding="utf-8-sig")
    final = pd.read_csv(ROOT / "data" / "task5" / "processed" / "task5_model_metrics.csv", encoding="utf-8-sig")
    final = final[final["model"] != "majority_baseline"].copy()
    rows = []
    for _, r in final.iterrows():
        match = cand[(cand["model"] == r["model"]) & (cand["candidate"] == r["selected_candidate"])].iloc[0]
        rows.append(
            {
                "模型": r["model_label"],
                "2023年验证期": match["validation_auc"],
                "2024年开发期": match["development_auc"],
                "2025年测试期": r["auc"],
            }
        )
    df = pd.DataFrame(rows)
    periods = ["2023年验证期", "2024年开发期", "2025年测试期"]
    colors = [BLUE, ORANGE, GREEN]
    markers = ["o", "s", "^"]

    fig, ax = plt.subplots(figsize=(9.0, 4.7))
    base = np.arange(len(periods))
    offsets = [-0.18, 0.0, 0.18]
    for i, row in df.iterrows():
        vals = [row[p] for p in periods]
        ax.scatter(base + offsets[i], vals, s=70, color=colors[i], marker=markers[i], label=row["模型"], zorder=3)
        for x, v in zip(base + offsets[i], vals):
            ax.text(x, v + 0.015, f"{v:.3f}", ha="center", fontsize=8.8)
    ax.axhline(0.5, color=RED, linestyle="--", linewidth=1.1, label="随机排序基准")
    ax.set_xticks(base, periods)
    ax.set_ylim(0.42, 0.82)
    ax.set_ylabel("曲线下面积")
    ax.set_title("任务五模型判别能力在三个离散时期的变化", fontsize=13.5, weight="bold")
    style_axis(ax)
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.31), frameon=False)
    ax.text(
        0.0,
        -0.15,
        "时期为预先划分的验证、开发和测试窗口；散点不表示连续时间趋势。",
        transform=ax.transAxes,
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图05_TASK5跨期AUC.png")


def load_task6_datasets() -> dict[str, list[dict]]:
    artifact = json.loads((ROOT / "Task6" / "dashboard" / "artifact.json").read_text(encoding="utf-8"))
    return artifact["snapshot"]["datasets"]


def figure06_task6_quarterly_returns() -> Path:
    df = pd.DataFrame(load_task6_datasets()["quarter_compare"])
    labels = ["2021年四季度", "2022年一季度", "2022年二季度"]
    dates = sorted(df["Date"].unique())
    series = ["EW Top30", "全市场等权"]
    colors = [BLUE, GRAY]
    hatches = ["", "//"]

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    x = np.arange(len(dates))
    width = 0.34
    for i, (name, color, hatch) in enumerate(zip(series, colors, hatches)):
        vals = [float(df[(df["Date"] == d) & (df["portfolio"] == name)]["net_return"].iloc[0]) * 100 for d in dates]
        bars = ax.bar(x + (i - 0.5) * width, vals, width, color=color, hatch=hatch, edgecolor="white", label="线性回归前30组合" if i == 0 else "全市场等权", zorder=3)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + (0.8 if v >= 0 else -0.9), percent_label(v, 1), ha="center", va="bottom" if v >= 0 else "top", fontsize=8.9)
    ax.axhline(0, color=TEXT, linewidth=0.9)
    ax.set_xticks(x, labels)
    ax.set_ylabel("季度收益率（%）")
    ax.set_title("任务六测试期组合与全市场等权的季度收益", fontsize=13.5, weight="bold")
    style_axis(ax)
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.text(
        0.0,
        -0.18,
        "仅包含三个测试季度；策略结果扣除单边20个基点交易成本。",
        transform=ax.transAxes,
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图06_TASK6季度组合收益.png")


def figure07_task6_validation_test_auc() -> Path:
    df = pd.DataFrame(load_task6_datasets()["tuning_long"])
    rounds = ["第1轮", "第2轮", "第3轮"]
    labels = ["静态随机森林", "静态逻辑回归", "滚动逻辑回归"]
    val = [float(df[(df["round_label"] == r) & (df["sample"] == "验证集")]["auc"].iloc[0]) for r in rounds]
    test = [float(df[(df["round_label"] == r) & (df["sample"] == "测试集")]["auc"].iloc[0]) for r in rounds]

    fig, ax = plt.subplots(figsize=(9.0, 4.9))
    x = np.arange(len(rounds))
    for i in range(len(rounds)):
        ax.plot([x[i] - 0.13, x[i] + 0.13], [val[i], test[i]], color=LIGHT_GRAY, linewidth=2.5, zorder=1)
    ax.scatter(x - 0.13, val, s=75, color=BLUE, marker="o", label="验证集", zorder=3)
    ax.scatter(x + 0.13, test, s=75, color=ORANGE, marker="s", label="测试集", zorder=3)
    for xx, vv in zip(x - 0.13, val):
        ax.text(xx, vv + 0.018, f"{vv:.3f}", ha="center", fontsize=9)
    for xx, vv in zip(x + 0.13, test):
        ax.text(xx, vv - 0.027, f"{vv:.3f}", ha="center", fontsize=9)
    ax.axhline(0.5, color=RED, linestyle="--", linewidth=1.1, label="随机排序基准")
    ax.set_xticks(x, [f"{r}\n{m}" for r, m in zip(rounds, labels)])
    ax.set_ylim(0.28, 0.82)
    ax.set_ylabel("曲线下面积")
    ax.set_title("任务六三轮方向模型的验证与测试表现", fontsize=13.5, weight="bold")
    style_axis(ax)
    ax.legend(frameon=False, ncol=3, loc="lower right")
    ax.text(
        0.0,
        -0.18,
        "连线只连接同一轮实验的验证与测试结果，不表示随时间连续改进。",
        transform=ax.transAxes,
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图07_TASK6验证与测试AUC.png")


def figure08_task7_nav_drawdown() -> Path:
    names = {"A": "策略A：基线", "B": "策略B：风险约束", "C": "策略C：动量轮动"}
    colors = {"A": ORANGE, "B": GREEN, "C": BLUE}
    styles = {"A": "-", "B": "--", "C": "-"}
    data = {}
    for key in names:
        d = pd.read_csv(ROOT / "data" / "task7" / "processed" / f"strategy_{key.lower()}_daily.csv", encoding="utf-8-sig")
        d["Date"] = pd.to_datetime(d["Date"])
        d["归一化净值"] = d["NAV"] / d["NAV"].iloc[0]
        data[key] = d
    bench = pd.read_csv(ROOT / "data" / "task7" / "processed" / "benchmark_daily.csv", encoding="utf-8-sig")
    bench["Date"] = pd.to_datetime(bench["Date"])
    bench["归一化净值"] = bench["BenchmarkNAV"] / bench["BenchmarkNAV"].iloc[0]
    bench["回撤"] = bench["归一化净值"] / bench["归一化净值"].cummax() - 1

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.4, 6.8), sharex=True, gridspec_kw={"height_ratios": [2.0, 1.0]})
    for key, d in data.items():
        ax1.plot(d["Date"], d["归一化净值"], color=colors[key], linestyle=styles[key], linewidth=1.45 if key != "C" else 1.8, label=names[key])
        ax2.plot(d["Date"], d["Drawdown"] * 100, color=colors[key], linestyle=styles[key], linewidth=1.2)
    ax1.plot(bench["Date"], bench["归一化净值"], color=GRAY, linestyle=":", linewidth=1.5, label="沪深300基准")
    ax2.plot(bench["Date"], bench["回撤"] * 100, color=GRAY, linestyle=":", linewidth=1.2)
    ax1.set_ylabel("归一化净值")
    ax1.set_title("任务七三策略与沪深300的本地扩展样本路径", fontsize=13.5, weight="bold")
    ax1.legend(ncol=2, frameon=False, loc="upper left")
    style_axis(ax1)
    ax2.axhline(0, color=TEXT, linewidth=0.8)
    ax2.fill_between(bench["Date"], bench["回撤"] * 100, 0, color=GRAY, alpha=0.07)
    ax2.set_ylabel("回撤（%）")
    ax2.set_xlabel("日期")
    style_axis(ax2)
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.text(
        0.5,
        0.005,
        "2016-01-04至2026-07-24；本地扩展样本复算，不等同于平台回测或模拟盘结果。",
        ha="center",
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图08_TASK7本地扩展净值与回撤.png", h_pad=0.8)


def figure09_task7_cost_stress() -> Path:
    base = json.loads((ROOT / "data" / "task7" / "metadata" / "backtest_metrics.json").read_text(encoding="utf-8"))
    stress = json.loads((ROOT / "data" / "task7" / "metadata" / "cost_stress_metrics.json").read_text(encoding="utf-8"))
    labels = ["策略A", "策略B", "策略C"]
    normal = [base[k]["full"]["cumulative_return"] * 100 for k in ["A", "B", "C"]]
    doubled = [stress[k]["full"]["cumulative_return"] * 100 for k in ["A", "B", "C"]]

    fig, ax = plt.subplots(figsize=(8.8, 4.9))
    x = np.arange(3)
    width = 0.34
    b1 = ax.bar(x - width / 2, normal, width, color=BLUE, label="基础成本", zorder=3)
    b2 = ax.bar(x + width / 2, doubled, width, color=ORANGE, hatch="//", edgecolor="white", label="成本翻倍", zorder=3)
    ax.axhline(0, color=TEXT, linewidth=0.9)
    ax.set_xticks(x, labels)
    ax.set_ylabel("累计收益率（%）")
    ax.set_title("任务七本地扩展样本的成本压力测试", fontsize=13.5, weight="bold")
    style_axis(ax)
    ax.legend(frameon=False, loc="upper left")
    for bars in [b1, b2]:
        for b in bars:
            v = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, v + (1.6 if v >= 0 else -2.0), percent_label(v, 1), ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    changes = [d - n for n, d in zip(normal, doubled)]
    for i, change in enumerate(changes):
        ax.text(i, -62, f"变化 {change:.1f}个百分点", ha="center", fontsize=8.8, color=RED)
    ax.set_ylim(-66, 66)
    ax.text(
        0.0,
        -0.16,
        "成本翻倍后，三策略累计收益分别变化-23.2、-11.5和-31.4个百分点。",
        transform=ax.transAxes,
        fontsize=9.2,
        color=GRAY,
    )
    return finish(fig, "图09_TASK7成本压力测试.png")


def main() -> None:
    builders = [
        figure01_system_loop,
        figure02_rules_return_drawdown,
        figure03_parameter_heatmap,
        figure04_task5_auc_intervals,
        figure05_task5_cross_period_auc,
        figure06_task6_quarterly_returns,
        figure07_task6_validation_test_auc,
        figure08_task7_nav_drawdown,
        figure09_task7_cost_stress,
    ]
    for builder in builders:
        print(builder())


if __name__ == "__main__":
    main()
