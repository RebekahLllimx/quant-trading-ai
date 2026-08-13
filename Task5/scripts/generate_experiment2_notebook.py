#!/usr/bin/env python3
"""Generate the reader-facing, executable Task5 notebook."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Task5" / "Rebecca+Task5.ipynb"


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
# TASK5 AI交易引擎：机器学习算法与场景应用

**姓名：Rebecca**  
**数据对象：沪深A股价格与成交量数据**  
**主要问题：在每个月末，预测一只股票未来20个交易日的绝对收益是否大于0**

本报告依次回答课程任务中的三个问题：先解释分类型机器学习算法，再说明混淆矩阵、ROC与AUC等评价指标，最后用Python完成股票涨跌分类。编程部分按照“准备数据（含探索性分析）→构造标签→选择特征→时间序列划分→训练模型→预测→评估→特征重要性→保存结果”的顺序展开。
"""
        ),
        md(
            """
## 一、分类型机器学习算法

分类型机器学习的目标，是根据一组已经观察到的信息，把样本划分到预先定义的类别中。本任务的类别只有“未来上涨”和“未来不涨”两种，因此属于二分类问题。模型并不是直接记住某一天涨或跌，而是从历史样本中估计特征与结果之间的关系，再对新样本给出上涨概率。

### 1.1 标签与特征的区别

- **标签（应变量）**是模型要预测的结果。本任务用未来20个交易日收益率是否大于0构造0/1标签。
- **特征（自变量）**是观察日已经知道的信息，包括历史收益、均线偏离、波动率、成交量变化、相对市场强弱和同期市场状态。

关键纪律是：特征只能使用观察日及以前的数据，标签则来自观察日之后。若把未来数据放进特征，会造成数据泄漏，使样本外结果失真。

### 1.2 三种分类算法

**逻辑回归。** 逻辑回归先把各项特征按权重相加，再通过Sigmoid函数把结果映射到0到1之间：$p=1/(1+e^{-z})$。输出值可以解释为上涨概率，系数正负则表示在其他条件不变时，该变量与上涨概率的方向关系。逻辑回归训练速度快、结果相对容易解释，也较不容易在小样本中形成过度复杂的规则；不足之处是它主要描述线性关系，若真实规律依赖复杂阈值或变量交互，模型可能无法充分捕捉。

**决策树。** 决策树按照特征阈值逐层切分样本，例如先判断20日收益是否高于某个水平，再判断波动率或市场广度。每次切分都希望让子节点中的类别更集中，常用标准包括基尼不纯度和信息增益。它可以自然表示非线性与变量交互，也不要求特征标准化；但单棵树对样本变化敏感，树过深时容易把偶然噪声写成规则，因此需要限制深度和叶节点最小样本数。

**随机森林。** 随机森林对训练样本进行多次有放回抽样，并在每个节点只考察部分随机特征，由此训练出许多具有差异的决策树，最后对各棵树的概率取平均。样本随机性和特征随机性可以降低单棵树的方差，使结果通常比决策树稳定。它能够表示非线性和交互，但解释性弱于逻辑回归，也不能自动创造原本不存在的信号；如果历史中的复杂关系只是阶段性的，森林仍可能在新市场状态下失效。

| 算法 | 主要优点 | 主要局限 |
|---|---|---|
| 逻辑回归 | 概率含义清楚、速度快、较容易解释 | 主要刻画线性关系 |
| 决策树 | 规则直观、能表达阈值与交互 | 对样本变化敏感，容易过拟合 |
| 随机森林 | 能表达复杂关系，通常比单树稳定 | 解释较困难，复杂关系未必能跨时期延续 |
"""
        ),
        md(
            """
## 二、机器学习模型评价指标

### 2.1 混淆矩阵及常用分类指标

混淆矩阵把实际类别和预测类别交叉排列，可以看出模型究竟错在“把不涨判断成上涨”，还是“漏掉了真正上涨的股票”。四个基本结果如下：

| 结果 | 含义 |
|---|---|
| TN（真负类） | 实际不涨，模型也预测不涨 |
| FP（假正类） | 实际不涨，但模型预测上涨 |
| FN（假负类） | 实际上涨，但模型预测不涨 |
| TP（真正类） | 实际上涨，模型也预测上涨 |

Accuracy衡量全部样本中判断正确的比例；Precision衡量“模型预测上涨”的股票中实际上涨的比例；Recall衡量所有实际上涨股票中被模型识别出来的比例；F1是Precision与Recall的调和平均。当上涨与不涨比例变化较大时，只看Accuracy容易受到多数类别影响，因此需要结合Precision、Recall和F1共同判断。

### 2.2 ROC曲线与AUC

ROC曲线不固定在0.5阈值，而是依次移动分类阈值，观察真正率和假阳性率如何变化。横轴是假阳性率FPR，纵轴是真正率TPR。曲线越靠近左上角，说明模型在识别更多上涨样本的同时，引入的错误上涨判断越少。

AUC是ROC曲线下面积，也可理解为：随机抽取一个上涨样本和一个不涨样本，模型把上涨样本排在更前面的概率。AUC=0.5接近随机排序，AUC=1表示排序完全正确。AUC适合比较概率排序能力，但它不包含收益幅度、交易成本和持仓规则，因此不能直接代表策略收益。
"""
        ),
        md("## 三、Python编程实现"),
        md(
            """
Python部分采用九个步骤完成数据处理、建模和评价，具体安排如下。

| 步骤 | 本次作答的具体做法 |
|---|---|
| 1. 准备数据 | 读取冻结的100只沪深A股API行情；检查日期、重复、缺失和覆盖；进行探索性分析 |
| 2. 构造标签 | 月末收盘后观察，未来20个交易日收益率>0记为1，否则为0 |
| 3. 选择特征 | 15项价格量技术特征 + 7项相对强弱与市场状态特征 |
| 4. 时间序列划分 | 2018-2022训练，2023验证，2024开发，2025最终测试；清除跨界标签 |
| 5. 训练模型 | 逻辑回归、决策树、随机森林；仅用2023和2024选择预设参数 |
| 6. 预测 | 锁定模型对2025年月末样本输出上涨概率 |
| 7. 评估 | AUC、ROC、混淆矩阵、Accuracy、Precision、Recall、F1 |
| 8. 特征重要性 | 逻辑回归标准化系数；随机森林不纯度重要性 |
| 9. 保存结果 | 保存数据集、模型、预测、指标、图表、哈希和33项校验报告 |
"""
        ),
        md("### 3.0 环境与参数"),
        code(
            """
from pathlib import Path
import json
import warnings

warnings.filterwarnings("ignore")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import display
from sklearn.metrics import roc_auc_score, roc_curve, confusion_matrix

pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda value: f"{value:.4f}")
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Songti SC", "STSong", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

START = Path.cwd().resolve()
PROJECT_ROOT = START if (START / "data" / "task5").exists() else START.parent
EXP2_DIR = PROJECT_ROOT / "data" / "task5" / "experiment2"
PROCESSED_DIR = EXP2_DIR / "processed"
METADATA_DIR = EXP2_DIR / "metadata"
RAW_MANIFEST = PROJECT_ROOT / "data" / "task5" / "metadata" / "raw_manifest.json"

HORIZON = 20
RANDOM_SEED = 42
RERUN_TRAINING = False  # 最终测试已经锁定；默认读取冻结模型，避免根据测试结果反复调参
"""
        ),
        md("### 3.1 准备数据与探索性分析"),
        md(
            """
数据来自前序任务所使用的行情接口，并冻结为本地快照。股票池按2018年初流动性选取100只沪深A股，原始窗口覆盖2017-2025年。冻结快照使同一份作业可以重复检查，不会因接口后续修订而悄悄变化。
"""
        ),
        code(
            """
manifest = json.loads(RAW_MANIFEST.read_text(encoding="utf-8"))
dataset = pd.read_csv(
    PROCESSED_DIR / "task5_experiment2_dataset.csv",
    parse_dates=["Date", "label_end_date"],
)
raw_files = pd.DataFrame(manifest["files"])
quality = json.loads((METADATA_DIR / "data_quality_report.json").read_text(encoding="utf-8"))

data_overview = pd.DataFrame({
    "项目": ["原始股票文件", "建模样本", "股票数", "月末观察日", "重复股票-日期键", "剩余缺失单元格"],
    "结果": [
        len(raw_files), len(dataset), dataset["Symbol"].nunique(), dataset["Date"].nunique(),
        dataset.duplicated(["Symbol", "Date"]).sum(), dataset.isna().sum().sum(),
    ],
})
print("表1：数据质量概览")
display(data_overview)
"""
        ),
        code(
            """
yearly_labels = (
    dataset.assign(Year=dataset["Date"].dt.year)
    .groupby("Year", as_index=False)
    .agg(样本数=("Label", "size"), 上涨比例=("Label", "mean"), 未来收益中位数=("future_return_20d", "median"))
)

fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0))
axes[0, 0].hist(raw_files["rows"], bins=12, color="#4C78A8", edgecolor="white")
axes[0, 0].set_title("A. 每只股票的原始交易日覆盖")
axes[0, 0].set_xlabel("原始行数")
axes[0, 0].set_ylabel("股票数")

split_counts = dataset.groupby("Split")["Label"].size().reindex(["train", "validation", "development", "test"])
axes[0, 1].bar(["训练", "验证", "开发", "测试"], split_counts, color=["#4C78A8", "#F2A541", "#59A14F", "#8C8C8C"])
axes[0, 1].set_title("B. 各时间段样本量")
axes[0, 1].set_ylabel("股票-月末样本数")

axes[1, 0].bar(yearly_labels["Year"].astype(str), yearly_labels["上涨比例"], color="#4C78A8")
axes[1, 0].axhline(0.5, color="#666666", linestyle="--", linewidth=1)
axes[1, 0].set_ylim(0.30, 0.65)
axes[1, 0].set_title("C. 未来20日上涨比例的年度变化")
axes[1, 0].set_ylabel("上涨比例")

clipped_returns = dataset["future_return_20d"].clip(
    dataset["future_return_20d"].quantile(0.01), dataset["future_return_20d"].quantile(0.99)
)
axes[1, 1].hist(clipped_returns, bins=45, color="#AFC6E0", edgecolor="white")
axes[1, 1].axvline(0, color="#C44E52", linestyle="--", linewidth=1)
axes[1, 1].set_title("D. 未来20日收益分布（1%-99%截尾展示）")
axes[1, 1].set_xlabel("未来20日收益率")

fig.suptitle("图1：数据覆盖、样本量、标签漂移与目标分布", fontsize=14, y=1.01)
fig.tight_layout()
plt.show()

print("表2：年度标签与收益概览")
display(yearly_labels)
"""
        ),
        md(
            """
**探索发现。** 原始文件覆盖较整齐，最终面板没有重复键和缺失值，因此结果不是由明显的数据破损造成。更重要的是，标签基准率存在显著年度漂移：2023年上涨比例为39.5%，2025年为54.7%。这意味着模型不仅要区分股票，还要面对整体市场方向变化；随机划分会把不同年份混在一起，从而高估真实外推能力。
"""
        ),
        md("### 3.2 构造标签"),
        md(
            """
观察日取每个自然月最后一个有效交易日。对股票 $i$ 在观察日 $t$，未来20日收益率定义为：

$$r_{i,t\\rightarrow t+20}=\\frac{P_{i,t+20}}{P_{i,t}}-1$$

若该收益率大于0，则 $Label_{i,t}=1$；否则为0。这里预测的是**绝对涨跌**，不是截面前30%股票，也没有删除中间样本。
"""
        ),
        code(
            """
label_check = (dataset["future_return_20d"] > 0).astype(int)
assert np.array_equal(label_check.to_numpy(), dataset["Label"].to_numpy())
assert (dataset["label_end_date"] > dataset["Date"]).all()

print("标签值：", sorted(dataset["Label"].unique().tolist()))
print("总体上涨比例：", f"{dataset['Label'].mean():.2%}")
print("观察日到标签结束日的最短自然日：", (dataset["label_end_date"] - dataset["Date"]).dt.days.min())
"""
        ),
        md("### 3.3 选择特征"),
        md(
            """
特征设计遵循三条原则：一是只使用观察日已知信息；二是全部采用比例或排名，避免不同股票价格和成交额量纲不可比；三是在基准方案的15项价格量特征上，补充7项相对市场与市场状态特征，但不引入难以稳定获取的财务数据。

| 特征组 | 变量 | 作用 |
|---|---|---|
| 收益与趋势 | 1/5/10/20日收益，MA5/20/60偏离，RSI14，MACD/价格 | 描述近期方向、趋势强度与均值偏离 |
| 波动与活跃度 | ATR/价格，20日波动率，成交量比，成交额比，日内振幅，开收盘收益 | 描述风险、交易活跃度与当日压力 |
| 相对强弱 | 相对市场5/20日收益，20日收益截面排名 | 区分个股走势与市场共同涨跌 |
| 市场状态 | 市场5/20日中位收益、20日上涨广度、20日收益离散度 | 描述同一观察日的整体环境 |

这些特征在技术分析和横截面动量研究中常见，但“常见”不等于对本样本已经有效。是否有用必须由严格时间外结果决定。
"""
        ),
        code(
            """
FEATURE_COLUMNS = [
    "return_1d", "return_5d", "return_10d", "return_20d",
    "ma5_gap", "ma20_gap", "ma60_gap", "rsi14", "macd_pct", "atr14_pct",
    "volatility20", "volume_ratio20", "amount_ratio20", "intraday_range", "open_close_return",
    "excess_return_5d", "excess_return_20d", "return_20d_rank",
    "market_median_return_5d", "market_median_return_20d",
    "market_breadth_20d", "market_dispersion_20d",
]
assert dataset[FEATURE_COLUMNS].notna().all().all()
assert np.isfinite(dataset[FEATURE_COLUMNS].to_numpy()).all()

correlation = dataset[FEATURE_COLUMNS].corr()
mask = np.triu(np.ones_like(correlation, dtype=bool))
fig, ax = plt.subplots(figsize=(12.0, 9.0))
sns.heatmap(correlation, mask=mask, cmap="vlag", center=0, vmin=-1, vmax=1, linewidths=0.2, cbar_kws={"label": "Pearson相关系数"}, ax=ax)
ax.set_title("图2：22项候选特征的相关性结构", fontsize=14)
plt.tight_layout()
plt.show()

pairs = correlation.where(np.triu(np.ones(correlation.shape), 1).astype(bool)).stack().rename("相关系数")
top_pairs = pairs.reindex(pairs.abs().sort_values(ascending=False).index).head(10).reset_index()
top_pairs.columns = ["特征A", "特征B", "相关系数"]
print("表3：绝对相关性最高的10组特征")
display(top_pairs)
"""
        ),
        md(
            """
**探索发现。** 收益、均线偏离、相对强弱和市场中位收益之间存在明显相关性。相关特征会使逻辑回归系数互相抵消或分摊，也会让随机森林的重要性集中在少数市场状态变量上。因此特征重要性只能用于理解模型依赖，不能解释为某个指标具有独立因果作用。
"""
        ),
        md("### 3.4 时间序列划分"),
        md(
            """
本任务不用随机70/30切分。随机切分会让相邻月份甚至同一市场阶段同时进入训练和测试，产生不符合实际使用的乐观结果。时间划分如下：

- 2018-2022：训练集，用于拟合候选模型；
- 2023：验证集，参与参数选择；
- 2024：开发集，与验证集共同检查参数的跨年稳定性；
- 2025：最终测试集，在设计和参数锁定后只评估一次。

各段年末若未来20日标签越过下一段边界，则整行剔除，避免训练标签偷看下一时期。
"""
        ),
        code(
            """
split_summary = pd.read_csv(METADATA_DIR / "split_summary.csv")
split_view = split_summary.copy()
split_view["观察期"] = split_view["start"] + " 至 " + split_view["end"]
split_view["上涨比例"] = split_view["positive_rate"].map(lambda value: f"{value:.2%}")
split_view = split_view[["Split", "观察期", "rows", "months", "上涨比例"]]
split_view.columns = ["数据段", "观察期", "样本数", "月数", "上涨比例"]
print("表4：时间序列划分")
display(split_view)

monthly = dataset.groupby(["Date", "Split"], as_index=False).size()
palette = {"train": "#4C78A8", "validation": "#F2A541", "development": "#59A14F", "test": "#8C8C8C"}
fig, ax = plt.subplots(figsize=(12.5, 4.5))
for split_name, part in monthly.groupby("Split"):
    ax.bar(part["Date"], part["size"], width=22, color=palette[split_name], label=split_name)
for boundary in ("2023-01-01", "2024-01-01", "2025-01-01"):
    ax.axvline(pd.Timestamp(boundary), color="#333333", linestyle="--", linewidth=1)
ax.set_title("图3：月末样本的训练、验证、开发与测试划分", fontsize=14)
ax.set_xlabel("观察日期")
ax.set_ylabel("每月股票数")
ax.legend(ncol=4)
plt.tight_layout()
plt.show()
"""
        ),
        md("### 3.5 训练模型"),
        md(
            """
候选参数在查看2025测试结果之前预设。每类模型先用2018-2022训练，在2023验证集和2024开发集分别计算AUC，以两期平均AUC选参数；若平均相同，以两期中较低的AUC作为稳定性优先级。选定后在2018-2024合并样本上重新拟合，再对2025预测。

连续特征按拟合样本0.5%和99.5%分位数截尾；逻辑回归再进行标准化。截尾边界和标准化参数均不使用测试数据。
"""
        ),
        code(
            """
candidate_metrics = pd.read_csv(PROCESSED_DIR / "task5_experiment2_candidate_metrics.csv")
selected_candidates = (
    candidate_metrics.sort_values(
        ["model", "selection_score_mean_auc", "selection_score_min_auc", "candidate_order"],
        ascending=[True, False, False, True],
    )
    .groupby("model", as_index=False)
    .first()
)
print("表5：每类模型选定的候选参数")
candidate_view = selected_candidates[["model_label", "candidate", "validation_auc", "development_auc", "selection_score_mean_auc"]].copy()
candidate_view.columns = ["模型", "参数", "2023 AUC", "2024 AUC", "两期平均AUC"]
display(candidate_view.round(4))
"""
        ),
        code(
            """
model_paths = {
    model: PROCESSED_DIR / "models" / f"{model}.joblib"
    for model in ["logistic_regression", "decision_tree", "random_forest"]
}

if RERUN_TRAINING:
    raise RuntimeError(
        "最终测试已经完成。若确需从头复现全部流程，请运行 Task5/scripts/prepare_experiment2.py "
        "和 train_experiment2.py；不要在看过2025结果后修改候选参数。"
    )
else:
    frozen_models = {name: joblib.load(path) for name, path in model_paths.items()}
    print("已加载三份冻结模型；本Notebook不根据2025测试结果重新训练或调参。")
    print({name: type(item["model"]).__name__ for name, item in frozen_models.items()})
"""
        ),
        md("### 3.6 生成预测"),
        md(
            """
三种锁定模型分别对2025年月末样本输出上涨概率。概率用于ROC和AUC；固定0.5阈值只用于生成0/1分类和混淆矩阵。把连续概率先变成0/1再计算AUC会丢失排序信息，因此是不正确的做法。
"""
        ),
        code(
            """
predictions = pd.read_csv(
    PROCESSED_DIR / "task5_experiment2_test_predictions.csv",
    parse_dates=["Date"],
)
assert predictions["probability"].between(0, 1).all()
assert predictions.groupby("model").size().nunique() == 1

print("表6：冻结预测示例（仅展示前8行）")
display(predictions[["Date", "Symbol", "Label", "model_label", "probability", "prediction"]].head(8))
print("每个模型的测试样本数：", predictions.groupby("model").size().to_dict())
"""
        ),
        md("### 3.7 模型评估"),
        code(
            """
model_metrics = pd.read_csv(PROCESSED_DIR / "task5_experiment2_model_metrics.csv")
metric_view = model_metrics[["model_label", "auc", "accuracy", "precision", "recall", "f1"]].copy()
metric_view.insert(2, "95%区间", model_metrics.apply(lambda row: f"[{row['auc_ci_low']:.3f}, {row['auc_ci_high']:.3f}]", axis=1))
metric_view.columns = ["模型", "AUC", "95%区间", "Accuracy", "Precision", "Recall", "F1"]
print("表7：2025年测试集指标")
display(metric_view.round(4))

for model_name, part in predictions.groupby("model"):
    stored_auc = model_metrics.set_index("model").at[model_name, "auc"]
    recalculated_auc = roc_auc_score(part["Label"], part["probability"])
    assert np.isclose(stored_auc, recalculated_auc)
print("三种模型的AUC均已由逐样本上涨概率独立复算。")
"""
        ),
        code(
            """
roc_points = pd.read_csv(PROCESSED_DIR / "task5_experiment2_roc_points.csv")
color_map = {"logistic_regression": "#4C78A8", "decision_tree": "#F28E2B", "random_forest": "#59A14F"}
fig, ax = plt.subplots(figsize=(8.5, 5.4))
for model_name, part in roc_points.groupby("model"):
    row = model_metrics.set_index("model").loc[model_name]
    ax.plot(part["fpr"], part["tpr"], linewidth=1.8, color=color_map[model_name], label=f"{row['model_label']} AUC={row['auc']:.3f}")
ax.plot([0, 1], [0, 1], color="#777777", linestyle="--", label="随机排序 AUC=0.500")
ax.set_title("图4：2025年测试集ROC曲线", fontsize=14)
ax.set_xlabel("假阳性率 FPR")
ax.set_ylabel("真正率 TPR")
ax.legend(loc="lower right")
plt.tight_layout()
plt.show()
"""
        ),
        code(
            """
models = ["logistic_regression", "decision_tree", "random_forest"]
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2))
for ax, model_name in zip(axes, models):
    part = predictions[predictions["model"] == model_name]
    matrix = confusion_matrix(part["Label"], part["prediction"], labels=[0, 1])
    normalized = matrix / matrix.sum(axis=1, keepdims=True)
    sns.heatmap(normalized, annot=False, cmap="Blues", vmin=0, vmax=1, cbar=False, square=True, ax=ax)
    for row in range(2):
        for col in range(2):
            ax.text(col + 0.5, row + 0.5, f"{matrix[row, col]}\\n{normalized[row, col]:.1%}", ha="center", va="center", color="white" if normalized[row, col] > 0.48 else "#222222")
    label = part["model_label"].iloc[0]
    ax.set_title(label)
    ax.set_xlabel("预测标签")
    ax.set_ylabel("实际标签")
    ax.set_xticklabels(["不涨0", "上涨1"])
    ax.set_yticklabels(["不涨0", "上涨1"], rotation=0)
fig.suptitle("图5：2025年测试集混淆矩阵（阈值0.5）", fontsize=14, y=1.03)
fig.tight_layout()
plt.show()
"""
        ),
        md(
            """
**结果解读。** 逻辑回归AUC为0.529，表示它对随机抽取的一对上涨/不涨样本，约有52.9%的概率把上涨样本排在前面。它比随机排序高2.9个百分点，但区间下界约为0.499，因此证据仍然很弱。决策树和随机森林在2025年低于0.5，说明它们在2023-2024捕捉到的非线性结构没有稳定延续。复杂模型表现较差并不意味着算法本身无效，而是说明当前特征、样本量和市场状态下，复杂关系的稳定性不足。
"""
        ),
        md("### 3.8 特征重要性"),
        code(
            """
importance = pd.read_csv(PROCESSED_DIR / "task5_experiment2_feature_importance.csv")
feature_labels = {
    "return_1d": "1日收益", "return_5d": "5日收益", "return_10d": "10日收益", "return_20d": "20日收益",
    "ma5_gap": "价格/MA5-1", "ma20_gap": "价格/MA20-1", "ma60_gap": "价格/MA60-1", "rsi14": "RSI14",
    "macd_pct": "MACD/价格", "atr14_pct": "ATR14/价格", "volatility20": "20日波动率",
    "volume_ratio20": "成交量比20日", "amount_ratio20": "成交额比20日", "intraday_range": "日内振幅",
    "open_close_return": "开收盘收益", "excess_return_5d": "相对市场5日收益",
    "excess_return_20d": "相对市场20日收益", "return_20d_rank": "20日收益截面排名",
    "market_median_return_5d": "市场5日中位收益", "market_median_return_20d": "市场20日中位收益",
    "market_breadth_20d": "市场20日上涨广度", "market_dispersion_20d": "市场20日收益离散度",
}
importance["feature_label"] = importance["feature"].map(feature_labels)

logistic = importance[importance["model"] == "logistic_regression"].nlargest(12, "absolute_importance").sort_values("importance")
forest = importance[importance["model"] == "random_forest"].nlargest(12, "importance").sort_values("importance")

fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.2))
axes[0].barh(logistic["feature_label"], logistic["importance"], color=np.where(logistic["importance"] >= 0, "#4C78A8", "#9E9E9E"))
axes[0].axvline(0, color="#333333", linewidth=1)
axes[0].set_title("逻辑回归：前12项标准化系数")
axes[0].set_xlabel("系数（正值提高上涨概率）")
axes[1].barh(forest["feature_label"], forest["importance"], color="#59A14F")
axes[1].set_title("随机森林：前12项不纯度重要性")
axes[1].set_xlabel("相对重要性")
fig.suptitle("图6：模型特征重要性统计", fontsize=14, y=1.02)
fig.tight_layout()
plt.show()

print("表8：逻辑回归绝对系数最大的特征")
display(logistic[["feature_label", "importance", "absolute_importance"]].sort_values("absolute_importance", ascending=False).head(8))
"""
        ),
        md(
            """
**重要性解读。** 逻辑回归较依赖1日收益、MACD/价格、开收盘收益以及市场状态变量；随机森林把较多重要性分配给市场5日中位收益、市场上涨广度和市场收益离散度。结合年度标签漂移，这说明“当前市场环境”确实影响未来绝对涨跌。但随机森林2025年AUC低于0.5，意味着它对市场状态的复杂切分没有可靠外推。重要性高不等于变量具有稳定交易价值，更不等于因果关系。
"""
        ),
        md("### 3.9 保存结果与复现检查"),
        code(
            """
validation = json.loads((METADATA_DIR / "validation_report.json").read_text(encoding="utf-8"))
saved_outputs = [
    PROCESSED_DIR / "task5_experiment2_dataset.csv",
    PROCESSED_DIR / "task5_experiment2_candidate_metrics.csv",
    PROCESSED_DIR / "task5_experiment2_test_predictions.csv",
    PROCESSED_DIR / "task5_experiment2_model_metrics.csv",
    PROCESSED_DIR / "task5_experiment2_roc_points.csv",
    PROCESSED_DIR / "task5_experiment2_feature_importance.csv",
    METADATA_DIR / "model_run.json",
    METADATA_DIR / "validation_report.json",
    *model_paths.values(),
]
output_inventory = pd.DataFrame({
    "文件": [str(path.relative_to(PROJECT_ROOT)) for path in saved_outputs],
    "存在": [path.exists() for path in saved_outputs],
    "大小KB": [round(path.stat().st_size / 1024, 1) if path.exists() else np.nan for path in saved_outputs],
})
print(f"独立校验：{validation['checks_passed']}/{validation['checks_total']}项通过；状态={validation['overall_assessment']}")
display(output_inventory)
assert output_inventory["存在"].all()
assert validation["checks_passed"] == validation["checks_total"]
"""
        ),
        md(
            """
## 四、两轮方案调整及结果比较

基准方案采用每日样本，预测未来5个交易日涨跌，使用15项价格与成交量特征。考虑到5日方向受短期噪声影响较大，而且相邻交易日的标签高度重叠，调整方案把观察频率降为月末，把预测周期延长到20个交易日，并加入相对市场收益、市场上涨广度和收益离散度等7项市场状态特征。这个调整不是简单增加模型复杂度，而是先改变问题的时间尺度，使预测目标更接近中短期选股中“下个月是否上涨”的判断。

| 模型 | 基准方案AUC：每日预测未来5日 | 调整方案AUC：月末预测未来20日 | 变化 |
|---|---:|---:|---:|
| 逻辑回归 | 0.5210 | 0.5290 | +0.0080 |
| 决策树 | 0.5068 | 0.4904 | -0.0164 |
| 随机森林 | 0.5189 | 0.4920 | -0.0269 |

从结果看，逻辑回归AUC由0.521提高到0.529，说明延长预测周期、降低观察频率并加入市场状态信息后，线性模型的排序能力略有改善。但决策树和随机森林没有同步提高，反而降到0.5以下。这说明调整方案并没有普遍增强所有模型，而是让简单模型保留了少量较稳定的信息，同时暴露出复杂模型对市场状态变化更敏感的问题。

在参数选择阶段，逻辑回归的2023年和2024年AUC分别为0.524和0.577；随机森林分别为0.517和0.577。随机森林在开发阶段看起来并不差，却未能延续到2025年。这一反差表明，只看某一段验证结果很容易高估模型稳定性。参数越多、规则越复杂，越可能把阶段性关系当成可重复规律。
"""
        ),
        md(
            """
## 五、总结与反思

本次任务完成了从数据准备、标签构造、特征选择、时间划分到模型训练、预测、评价和结果保存的完整流程，并比较了逻辑回归、决策树和随机森林三种分类算法。2025年测试结果中，逻辑回归AUC为0.529，决策树为0.490，随机森林为0.492。逻辑回归对上涨与不涨样本的排序略好于随机，但95%区间约为[0.499, 0.587]，仍不能说明已经获得稳定的预测优势。

探索性分析带来的主要发现，是未来20日上涨比例从2023年的39.5%升至2025年的54.7%，说明不同年份的整体市场方向并不相同。随机森林把较多重要性分配给市场5日中位收益、市场上涨广度和收益离散度，说明模型确实在利用市场环境；但它在2025年的AUC低于0.5，又说明这些复杂关系没有稳定延续。因此，特征重要性只能说明模型依赖了哪些变量，不能证明这些变量具有独立、持续或因果性的交易价值。

回顾两轮调整，最有价值的收获并不是把AUC提高了0.008，而是认识到预测目标、观察频率和时间划分往往比盲目增加模型复杂度更重要。当前价格量特征对未来20日绝对方向可能包含少量信息，但这种信息较弱，并且会随市场状态改变。机器学习在这里更适合作为检验特征是否具有稳定统计关系的工具，而不是直接等同于可以盈利的交易策略。

本任务尚未计入手续费、滑点、停牌、涨跌停和组合构建，也没有根据收益幅度区分“大涨”和“微涨”。股票池按2018年初流动性冻结，仍存在成分选择和幸存者偏差。若继续改进，应使用新的时间区间重新设置最终测试期，再考虑加入更稳定的基本面或行业相对特征，并检验概率校准和不同市场状态下的表现，而不应围绕已经看过的2025年结果反复调参。
"""
        ),
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, OUTPUT)
    print(f"[done] notebook -> {OUTPUT}")


if __name__ == "__main__":
    main()
