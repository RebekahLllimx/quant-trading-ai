#!/usr/bin/env python3
"""Generate a read-only audit notebook for Task5 features and sample size."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Task5" / "feature_selection_audit.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def main() -> None:
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    }
    notebook["cells"] = [
        md(
            """
# TASK5 特征与样本量审计

本Notebook不重新训练模型，也不使用2025年测试结果选择特征。它只回答三个问题：数据是否适合建模；现有特征是否与标签有关且能跨时期保持方向；训练样本的独立时间跨度是否足以支持当前模型复杂度。
"""
        ),
        md(
            """
## 结论摘要

特征应同时满足三项条件：与目标存在可重复关系、关系在不同时间段相对稳定、构造时不使用观察日之后的信息。相关性筛选只能使用训练期以及用于模型开发的2023—2024年，2025年继续保持为最终测试期。

需要特别区分“记录数”和“独立市场状态数”。训练集虽然有5,726条股票—月末记录，但只覆盖58个月。股票层面的历史收益和相对强弱可以利用同月横截面差异；市场状态特征在同一个月对所有股票取值相同，因此它们实际只有58个训练时间点，不能按5,726条独立样本理解。
"""
        ),
        md("## 一、数据与审计口径"),
        code(
            """
from pathlib import Path
import json
import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import display
from scipy.stats import ks_2samp
from sklearn.metrics import roc_auc_score

pd.set_option("display.max_columns", 40)
pd.set_option("display.float_format", lambda value: f"{value:.4f}")
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Songti SC", "STSong", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False,
})

START = Path.cwd().resolve()
ROOT = START if (START / "data" / "task5").exists() else START.parent
DATASET_PATH = ROOT / "data" / "task5" / "experiment2" / "processed" / "task5_experiment2_dataset.csv"
METADATA_DIR = ROOT / "data" / "task5" / "experiment2" / "metadata"

FEATURES = [
    "return_1d", "return_5d", "return_10d", "return_20d",
    "ma5_gap", "ma20_gap", "ma60_gap", "rsi14", "macd_pct", "atr14_pct",
    "volatility20", "volume_ratio20", "amount_ratio20", "intraday_range", "open_close_return",
    "excess_return_5d", "excess_return_20d", "return_20d_rank",
    "market_median_return_5d", "market_median_return_20d",
    "market_breadth_20d", "market_dispersion_20d",
]
MARKET_FEATURES = [
    "market_median_return_5d", "market_median_return_20d",
    "market_breadth_20d", "market_dispersion_20d",
]

dataset = pd.read_csv(DATASET_PATH, parse_dates=["Date", "label_end_date"])
print(f"数据：{len(dataset):,}行，{dataset['Symbol'].nunique()}只股票，{dataset['Date'].nunique()}个月末")
"""
        ),
        code(
            """
RAW_DIR = ROOT / "data" / "task5" / "raw"
manifest = json.loads((ROOT / "data" / "task5" / "metadata" / "raw_manifest.json").read_text(encoding="utf-8"))
raw_audit_rows = []
for item in manifest["files"]:
    path = RAW_DIR / f"{item['symbol'].replace('.', '_')}.csv"
    raw = pd.read_csv(path, parse_dates=["Date"])
    price_columns = ["Open", "High", "Low", "Close"]
    numeric_columns = price_columns + ["Volume", "Amount"]
    raw_audit_rows.append({
        "symbol": item["symbol"],
        "rows": len(raw),
        "start": raw["Date"].min(),
        "end": raw["Date"].max(),
        "duplicate_dates": raw["Date"].duplicated().sum(),
        "missing_core": raw[numeric_columns].isna().sum().sum(),
        "nonpositive_price": raw[price_columns].le(0).any(axis=1).sum(),
        "negative_volume_amount": (raw[["Volume", "Amount"]] < 0).any(axis=1).sum(),
        "ohlc_inconsistent": (
            (raw[["Open", "Close", "Low"]].max(axis=1) - raw["High"] > 1e-8)
            | (raw["Low"] - raw[["Open", "Close", "High"]].min(axis=1) > 1e-8)
        ).sum(),
        "date_not_increasing": int(not raw["Date"].is_monotonic_increasing),
    })

raw_audit = pd.DataFrame(raw_audit_rows)
raw_summary = pd.DataFrame({
    "项目": [
        "原始股票文件", "每股最少交易日", "每股交易日中位数", "每股最多交易日",
        "最早日期", "最晚日期", "重复日期", "核心字段缺失", "非正价格",
        "负成交量或成交额", "OHLC关系不一致", "日期未递增文件",
        "2025年前已结束交易的股票",
    ],
    "结果": [
        len(raw_audit), raw_audit["rows"].min(), raw_audit["rows"].median(), raw_audit["rows"].max(),
        raw_audit["start"].min(), raw_audit["end"].max(), raw_audit["duplicate_dates"].sum(),
        raw_audit["missing_core"].sum(), raw_audit["nonpositive_price"].sum(),
        raw_audit["negative_volume_amount"].sum(), raw_audit["ohlc_inconsistent"].sum(),
        raw_audit["date_not_increasing"].sum(), (raw_audit["end"] < pd.Timestamp("2025-01-01")).sum(),
    ],
})
print("表0：原始行情质量概览")
display(raw_summary)
"""
        ),
        code(
            """
coverage = dataset.groupby(["Split", "Date"])["Symbol"].nunique().rename("stocks_per_month").reset_index()
split_summary = (
    dataset.groupby("Split", as_index=False)
    .agg(
        rows=("Label", "size"),
        months=("Date", "nunique"),
        symbols=("Symbol", "nunique"),
        start=("Date", "min"),
        end=("Date", "max"),
        positive_rate=("Label", "mean"),
    )
)
monthly_coverage = coverage.groupby("Split", as_index=False).agg(
    min_stocks=("stocks_per_month", "min"),
    median_stocks=("stocks_per_month", "median"),
    max_stocks=("stocks_per_month", "max"),
)
split_summary = split_summary.merge(monthly_coverage, on="Split")
split_order = pd.CategoricalDtype(["train", "validation", "development", "test"], ordered=True)
split_summary["Split"] = split_summary["Split"].astype(split_order)
split_summary = split_summary.sort_values("Split")
print("表1：样本量与月度覆盖")
display(split_summary)
"""
        ),
        md(
            """
一条记录是一只股票在一个月末的状态。月末股票数接近100，说明横截面覆盖较整齐；但模型的时间外推能力取决于经历了多少个月和多少种市场状态，不能只看总行数。
"""
        ),
        md("## 二、数据质量与未来信息检查"),
        code(
            """
split_year_end = {
    "train": pd.Timestamp("2022-12-31"),
    "validation": pd.Timestamp("2023-12-31"),
    "development": pd.Timestamp("2024-12-31"),
    "test": pd.Timestamp("2025-12-31"),
}

checks = {
    "股票-日期键无重复": dataset.duplicated(["Symbol", "Date"]).sum() == 0,
    "无缺失单元格": dataset.isna().sum().sum() == 0,
    "所有特征均为有限数": np.isfinite(dataset[FEATURES].to_numpy()).all(),
    "标签只包含0和1": set(dataset["Label"].unique()) == {0, 1},
    "标签结束日在观察日之后": (dataset["label_end_date"] > dataset["Date"]).all(),
    "标签等于未来20日收益是否大于0": np.array_equal((dataset["future_return_20d"] > 0).astype(int), dataset["Label"]),
    "特征列不含标签或未来收益字段": not bool(set(FEATURES) & {"Label", "future_return_20d", "label_end_date"}),
}
for split_name, year_end in split_year_end.items():
    checks[f"{split_name}标签未跨越分段年末"] = dataset.loc[dataset["Split"] == split_name, "label_end_date"].le(year_end).all()

market_unique = dataset.groupby("Date")[MARKET_FEATURES].nunique().max()
quality_view = pd.DataFrame({"检查": checks.keys(), "通过": checks.values()})
print("表2：数据质量与标签边界检查")
display(quality_view)
print("市场状态特征在每个月末的最大不同取值数（应为1）：")
display(market_unique.to_frame("最大不同取值数"))
assert all(checks.values())
assert market_unique.eq(1).all()
"""
        ),
        md(
            """
代码路径检查表明：收益、均线、RSI、MACD、ATR和成交量指标均使用当日或此前的滚动窗口；相对市场特征使用同一观察日、同一股票池中已经形成的历史收益；只有标签使用 `shift(-20)` 读取未来收盘价。这里通过了字段、日期和分段边界三层检查，但仍应把这一规则保留为自动化测试。
"""
        ),
        md("## 三、特征相关性与跨时期稳定性"),
        code(
            """
def safe_auc(y_true, score):
    if pd.Series(y_true).nunique() < 2 or pd.Series(score).nunique() < 2:
        return np.nan
    return roc_auc_score(y_true, score)


def monthly_cross_section_auc(frame, feature, direction):
    values = []
    for _, part in frame.groupby("Date"):
        auc = safe_auc(part["Label"], direction * part[feature])
        if np.isfinite(auc):
            values.append(auc)
    return np.mean(values) if values else np.nan


train = dataset[dataset["Split"] == "train"]
validation = dataset[dataset["Split"] == "validation"]
development = dataset[dataset["Split"] == "development"]

audit_rows = []
for feature in FEATURES:
    raw_train_auc = safe_auc(train["Label"], train[feature])
    direction = 1 if raw_train_auc >= 0.5 else -1
    train_auc = safe_auc(train["Label"], direction * train[feature])
    validation_auc = safe_auc(validation["Label"], direction * validation[feature])
    development_auc = safe_auc(development["Label"], direction * development[feature])
    ks_validation = ks_2samp(train[feature], validation[feature]).statistic
    ks_development = ks_2samp(train[feature], development[feature]).statistic
    audit_rows.append({
        "feature": feature,
        "type": "market_state" if feature in MARKET_FEATURES else "stock_level",
        "direction_from_train": direction,
        "train_auc": train_auc,
        "validation_auc": validation_auc,
        "development_auc": development_auc,
        "min_holdout_auc": min(validation_auc, development_auc),
        "mean_holdout_auc": np.mean([validation_auc, development_auc]),
        "stable_direction": validation_auc > 0.5 and development_auc > 0.5,
        "max_ks_shift": max(ks_validation, ks_development),
        "train_monthly_cs_auc": monthly_cross_section_auc(train, feature, direction),
        "validation_monthly_cs_auc": monthly_cross_section_auc(validation, feature, direction),
        "development_monthly_cs_auc": monthly_cross_section_auc(development, feature, direction),
    })

feature_audit = pd.DataFrame(audit_rows)
feature_audit["status"] = np.select(
    [
        feature_audit["stable_direction"] & (feature_audit["max_ks_shift"] < 0.25),
        feature_audit["stable_direction"],
    ],
    ["候选保留", "方向稳定但分布漂移"],
    default="暂不优先",
)
feature_audit = feature_audit.sort_values(["status", "min_holdout_auc"], ascending=[True, False])
feature_audit.to_csv(METADATA_DIR / "feature_selection_audit.csv", index=False, encoding="utf-8-sig")

print("表3：按训练期确定方向后，在2023和2024检查稳定性")
display(feature_audit[[
    "feature", "type", "train_auc", "validation_auc", "development_auc",
    "min_holdout_auc", "max_ks_shift", "train_monthly_cs_auc", "status",
]].sort_values("min_holdout_auc", ascending=False))
"""
        ),
        code(
            """
plot_data = feature_audit.sort_values("min_holdout_auc")
fig, axes = plt.subplots(1, 2, figsize=(13.5, 8.0))
axes[0].barh(plot_data["feature"], plot_data["validation_auc"], color="#4C78A8", alpha=0.85, label="2023验证")
axes[0].scatter(plot_data["development_auc"], plot_data["feature"], color="#F28E2B", s=35, label="2024开发", zorder=3)
axes[0].axvline(0.5, color="#555555", linestyle="--", linewidth=1)
axes[0].set_title("A. 训练期定向后的跨时期单变量AUC")
axes[0].set_xlabel("AUC")
axes[0].legend()

axes[1].barh(plot_data["feature"], plot_data["max_ks_shift"], color="#59A14F")
axes[1].axvline(0.25, color="#555555", linestyle="--", linewidth=1, label="较明显漂移参考线")
axes[1].set_title("B. 相对训练期的最大分布偏移（KS）")
axes[1].set_xlabel("KS统计量")
axes[1].legend()
fig.suptitle("图1：特征相关性与分布稳定性审计", fontsize=14, y=1.01)
fig.tight_layout()
plt.show()
"""
        ),
        md(
            """
这里的AUC只用于单变量诊断，不等于多变量模型表现。方向只由2018—2022训练期决定，再原样应用到2023和2024。如果某个特征在两个后续时期都高于0.5，才能称为方向相对稳定。KS统计量用于识别特征分布变化；它不直接判断预测是否有效，但可以提示模型是否面对了与训练期不同的输入环境。

市场状态特征在同一个月对所有股票完全相同，因此月内横截面AUC为空。它们可以帮助预测整体市场方向，却不能在同一个月末区分哪只股票更好。
"""
        ),
        md("## 四、相关特征的冗余检查"),
        code(
            """
train_corr = train[FEATURES].corr()
pairs = (
    train_corr.where(np.triu(np.ones(train_corr.shape), 1).astype(bool))
    .stack()
    .rename("correlation")
    .reset_index()
)
pairs["abs_correlation"] = pairs["correlation"].abs()
high_pairs = pairs[pairs["abs_correlation"] >= 0.85].sort_values("abs_correlation", ascending=False)
print("表4：训练期绝对相关系数不低于0.85的特征对")
display(high_pairs)
"""
        ),
        md(
            """
高相关特征不应全部机械保留。更稳妥的做法是先按经济含义分组，再在同组中优先保留跨时期方向更稳定、分布漂移更小且解释更清楚的一项。这样既减少多重共线性，也降低树模型在相似变量之间反复切分的自由度。
"""
        ),
        md("## 五、训练样本是否足够"),
        code(
            """
def one_way_icc(frame):
    groups = [part["Label"].to_numpy(dtype=float) for _, part in frame.groupby("Date")]
    sizes = np.array([len(group) for group in groups], dtype=float)
    means = np.array([group.mean() for group in groups])
    total_n = sizes.sum()
    grand = np.concatenate(groups).mean()
    ms_between = np.sum(sizes * (means - grand) ** 2) / (len(groups) - 1)
    ms_within = np.sum([np.sum((group - group.mean()) ** 2) for group in groups]) / (total_n - len(groups))
    n0 = (total_n - np.sum(sizes ** 2) / total_n) / (len(groups) - 1)
    icc = (ms_between - ms_within) / (ms_between + (n0 - 1) * ms_within)
    design_effect = 1 + (sizes.mean() - 1) * max(icc, 0)
    return icc, design_effect, total_n / design_effect

icc, design_effect, approximate_effective_rows = one_way_icc(train)
sample_assessment = pd.DataFrame({
    "指标": [
        "训练记录数", "训练月份数", "训练股票数", "平均每月股票数", "候选特征数",
        "每个特征对应训练月份", "标签月内相关ICC近似", "聚类设计效应", "近似有效记录数",
    ],
    "结果": [
        len(train), train["Date"].nunique(), train["Symbol"].nunique(),
        len(train) / train["Date"].nunique(), len(FEATURES),
        train["Date"].nunique() / len(FEATURES), icc, design_effect, approximate_effective_rows,
    ],
})
print("表5：训练样本容量诊断")
display(sample_assessment)
"""
        ),
        md(
            """
## 六、结论与建议

1. **数据本身可以继续使用。** 100份原始行情没有重复日期、缺失核心字段、非正价格、负成交量或实质性OHLC矛盾。3只股票在2025年前结束交易，保留这些股票反而有助于减少只留下现存公司的幸存者偏差。建模面板的股票—日期键唯一，标签结束日也没有跨越各数据段边界。
2. **现有22项特征不应原样全部视为有效。** 应以训练期确定方向，用2023和2024检查稳定性，并在高度相关的变量中保留代表项。2025年只用于最终评价，不能参与本轮筛选。
3. **数据支持的精简核心可以先缩到4项。** 日内振幅、MA5偏离、1日收益和10日收益在2023与2024保持同一方向，分布偏移也低于0.25。开收盘收益与1日收益相关系数为0.89，因此两者只保留一个；5日收益和RSI虽然方向一致，但增量较弱且与其他趋势指标相关，可先作为备选。
4. **另设2项需要监控的候选变量。** ATR/价格在2023和2024的单变量AUC较高，但分布偏移约0.29；市场20日上涨广度方向也一致，但分布偏移约0.34，而且每个月对所有股票取值相同。它们可以作为挑战变量，不能与稳定核心等量看待。20日市场中位收益与上涨广度相关系数为0.95，两者只能择一。
5. **成交活跃度和相对强弱变量暂不优先。** 成交量比与成交额比相关系数为0.99，而且跨时期方向不稳定；相对市场20日收益和20日截面排名在2023、2024均低于随机方向，不适合当前的绝对涨跌标签。
6. **样本量足以支持精简后的正则化逻辑回归，勉强支持浅层树，不适合高自由度模型。** 5,726行对一般表格模型看似充足，但时间维度只有58个月，按标签月内相关性估算的有效记录约254条；验证和开发期各只有11个月。精简到约6项后更合理，复杂模型仍容易把少数市场阶段记成规则。
7. **若继续改进，应采用多年度走步验证。** 可以在2018—2024内部依次用后一年验证，把2025保持为已经完成的最终评价，不再围绕它调整。由于本项目已经看过2025结果，任何新特征组合在2025上的分数都只能称为事后敏感性分析，真正的新检验需要以后追加未使用时间段。
"""
        ),
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, OUTPUT)
    print(f"[done] {OUTPUT}")


if __name__ == "__main__":
    main()
