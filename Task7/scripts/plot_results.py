#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate report figures from validated TASK7 outputs."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "task7"
OUTPUT = ROOT / "artifacts" / "charts" / "task7"
OUTPUT.mkdir(parents=True, exist_ok=True)

COLORS = {"A": "#D87831", "B": "#147D72", "C": "#3B62A8", "Benchmark": "#747C80"}


def setup_style():
    plt.rcParams.update(
        {
            "font.sans-serif": [
                "PingFang SC",
                "Hiragino Sans GB",
                "Arial Unicode MS",
                "Noto Sans CJK SC",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#B9C3BF",
            "axes.labelcolor": "#31444A",
            "text.color": "#14242B",
            "xtick.color": "#61727A",
            "ytick.color": "#61727A",
            "grid.color": "#E4EAE7",
            "grid.linewidth": 0.8,
            "axes.titleweight": "semibold",
        }
    )


def load_daily():
    daily = {}
    for strategy in "ABC":
        frame = pd.read_csv(DATA / "processed" / f"strategy_{strategy.lower()}_daily.csv")
        frame["Date"] = pd.to_datetime(frame["Date"])
        daily[strategy] = frame
    benchmark = pd.read_csv(DATA / "processed" / "benchmark_daily.csv")
    benchmark["Date"] = pd.to_datetime(benchmark["Date"])
    return daily, benchmark


def nav_and_drawdown():
    daily, benchmark = load_daily()
    fig, axes = plt.subplots(
        2, 1, figsize=(9.2, 6.8), sharex=True, gridspec_kw={"height_ratios": [1.7, 1]}
    )
    for strategy, frame in daily.items():
        nav = frame["NAV"] / frame["NAV"].iloc[0] * 100
        axes[0].plot(frame["Date"], nav, label=f"策略{strategy}", color=COLORS[strategy], lw=1.7)
        axes[1].plot(
            frame["Date"],
            frame["Drawdown"] * 100,
            label=f"策略{strategy}",
            color=COLORS[strategy],
            lw=1.3,
        )
    bnav = benchmark["BenchmarkNAV"] / benchmark["BenchmarkNAV"].iloc[0] * 100
    axes[0].plot(
        benchmark["Date"],
        bnav,
        label="沪深300",
        color=COLORS["Benchmark"],
        lw=1.5,
        ls="--",
    )
    axes[0].axhline(100, color="#AAB5B1", lw=0.8)
    axes[0].set_ylabel("归一化净值")
    axes[0].set_title("三策略历史净值与回撤（2016-2026）", loc="left", fontsize=13)
    axes[0].legend(ncol=4, frameon=False, loc="upper left")
    axes[0].grid(axis="y")
    axes[1].axhline(0, color="#AAB5B1", lw=0.8)
    axes[1].set_ylabel("回撤（%）")
    axes[1].set_xlabel("日期")
    axes[1].grid(axis="y")
    axes[1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(OUTPUT / "figure1_nav_drawdown.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def parameter_sensitivity():
    b = pd.read_csv(DATA / "processed" / "strategy_b_parameter_sensitivity.csv")
    c = pd.read_csv(DATA / "processed" / "strategy_c_parameter_sensitivity.csv")
    b["parameter"] = b["ma_fast"].astype(str) + "/" + b["ma_slow"].astype(str)
    c["parameter"] = c["lookback"].astype(int).astype(str) + "日"
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2))

    for ax, frame, title in [
        (axes[0], b, "策略B：均线参数"),
        (axes[1], c, "策略C：动量窗口"),
    ]:
        labels = list(dict.fromkeys(frame["parameter"]))
        x = np.arange(len(labels))
        width = 0.34
        dev = [
            frame[(frame["parameter"] == label) & (frame["period"] == "development")][
                "cumulative_return"
            ].iloc[0]
            * 100
            for label in labels
        ]
        val = [
            frame[(frame["parameter"] == label) & (frame["period"] == "validation")][
                "cumulative_return"
            ].iloc[0]
            * 100
            for label in labels
        ]
        ax.bar(x - width / 2, dev, width, label="开发期", color="#86B9B1")
        ax.bar(x + width / 2, val, width, label="验证期", color="#3B62A8")
        ax.axhline(0, color="#7D8783", lw=0.8)
        ax.set_xticks(x, labels)
        ax.set_ylabel("累计收益（%）")
        ax.set_title(title, loc="left", fontsize=12)
        ax.grid(axis="y")
        for idx, value in enumerate(dev):
            ax.text(idx - width / 2, value + (1 if value >= 0 else -2.5), f"{value:.1f}", ha="center", va="bottom" if value >= 0 else "top", fontsize=8)
        for idx, value in enumerate(val):
            ax.text(idx + width / 2, value + (1 if value >= 0 else -2.5), f"{value:.1f}", ha="center", va="bottom" if value >= 0 else "top", fontsize=8)
    axes[0].legend(frameon=False, ncol=2, loc="upper left")
    fig.suptitle("参数只在开发期与验证期比较", x=0.06, ha="left", fontsize=13, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUTPUT / "figure2_parameter_sensitivity.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def period_performance():
    metrics = json.loads((DATA / "metadata" / "backtest_metrics.json").read_text())
    periods = ["development", "validation", "oos"]
    labels = ["开发期\n2016-2023", "验证期\n2024-2025", "样本外\n2026"]
    x = np.arange(3)
    width = 0.23
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    for offset, strategy in enumerate("ABC"):
        values = [metrics[strategy][period]["cumulative_return"] * 100 for period in periods]
        bars = ax.bar(
            x + (offset - 1) * width,
            values,
            width,
            label=f"策略{strategy}",
            color=COLORS[strategy],
        )
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + (1 if value >= 0 else -2),
                f"{value:.1f}",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=8,
            )
    ax.axhline(0, color="#7D8783", lw=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("累计收益（%）")
    ax.set_title("开发、验证与参数冻结后的样本外表现", loc="left", fontsize=13)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.grid(axis="y")
    fig.tight_layout()
    fig.savefig(OUTPUT / "figure3_period_performance.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def cost_stress():
    metrics = json.loads((DATA / "metadata" / "backtest_metrics.json").read_text())
    stress = json.loads((DATA / "metadata" / "cost_stress_metrics.json").read_text())
    labels = ["策略A", "策略B", "策略C"]
    x = np.arange(3)
    width = 0.34
    base = [metrics[s]["full"]["cumulative_return"] * 100 for s in "ABC"]
    doubled = [stress[s]["full"]["cumulative_return"] * 100 for s in "ABC"]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.bar(x - width / 2, base, width, label="基础成本", color="#3B62A8")
    ax.bar(x + width / 2, doubled, width, label="成本翻倍", color="#D87831")
    ax.axhline(0, color="#7D8783", lw=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("全期累计收益（%）")
    ax.set_title("成本翻倍压力测试", loc="left", fontsize=13)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    ax.grid(axis="y")
    for i, (left, right) in enumerate(zip(base, doubled)):
        ax.text(i - width / 2, left + (1 if left >= 0 else -2), f"{left:.1f}", ha="center", va="bottom" if left >= 0 else "top", fontsize=8)
        ax.text(i + width / 2, right + (1 if right >= 0 else -2), f"{right:.1f}", ha="center", va="bottom" if right >= 0 else "top", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT / "figure4_cost_stress.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    setup_style()
    nav_and_drawdown()
    parameter_sensitivity()
    period_performance()
    cost_stress()
    print(f"✅ Wrote TASK7 figures to {OUTPUT}")


if __name__ == "__main__":
    main()
