#!/usr/bin/env python3
"""Generate the formal TASK5 notebook from the frozen CATL case outputs."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "Task5"
RESULT = ROOT / "data" / "task5" / "catl" / "results"
OUTPUT = TASK / "Rebecca+Task5.ipynb"


def main() -> None:
    summary = json.loads((RESULT / "summary.json").read_text(encoding="utf-8"))
    metrics = pd.read_csv(RESULT / "model_metrics.csv")
    validation = pd.read_csv(RESULT / "model_tuning.csv")
    validation_best = validation.sort_values(
        ["mean_validation_auc", "std_validation_auc"], ascending=[False, True]
    ).groupby("model", as_index=False).head(1)
    best_test = metrics.sort_values("roc_auc", ascending=False).iloc[0]
    lr_test = metrics.loc[metrics["model"] == "logistic_regression"].iloc[0]
    rf_test = metrics.loc[metrics["model"] == "random_forest"].iloc[0]
    gb_test = metrics.loc[metrics["model"] == "gradient_boosting"].iloc[0]
    lr_valid = validation_best.loc[validation_best["model"] == "logistic_regression", "mean_validation_auc"].iloc[0]
    weekly = pd.read_csv(ROOT / "data" / "task5" / "catl" / "processed" / "weekly_samples.csv", parse_dates=["Date"])
    target_autocorr = weekly["target"].autocorr(1)
    test_target_autocorr = weekly.loc[weekly["Date"].dt.year == 2025, "target"].autocorr(1)

    nb = nbf.v4.new_notebook()
    cells = []

    def md(text: str) -> None:
        cells.append(nbf.v4.new_markdown_cell(text.strip()))

    def code(text: str) -> None:
        cells.append(nbf.v4.new_code_cell(text.strip()))

    md("""
# TASK5 AI交易引擎：机器学习算法与场景应用

**数据对象：宁德时代（300750.SZ）与沪深300**  
**主要问题：每周最后一个交易日收盘后，预测宁德时代未来20个交易日是否跑赢沪深300**

下面先解释分类算法和评价指标，再用Python完成数据检查、标签与特征构造、时间划分、训练和评价。最后一部分单独讨论一个不太理想、但不能回避的结果：为什么测试AUC接近0.5，以及这究竟是代码问题、信息不足，还是研究设计本身的限制。
""")

    md("""
## 一、分类型机器学习算法

分类模型不直接给出未来收益率。这里把“未来20日跑赢沪深300”记为1，未跑赢记为0，模型输出的是Y=1的概率。

### 1.1 标签与特征

- **标签（应变量Y）**是待预测结果，由观察日之后20个交易日的相对收益计算。
- **特征（自变量X）**是观察日收盘时已经知道的量，包括过去收益、均线偏离、波动率、成交活跃度和相对强弱。

时间边界是这道题最容易出错的地方。X只能读到观察日，Y才会用到未来价格；未来涨跌幅或尚未公布的财务信息一旦进入X，得到的高AUC也没有解释价值。

### 1.2 逻辑回归、决策树、随机森林与梯度提升

**逻辑回归。** 标准化后的特征先做线性加权，再经Sigmoid函数映射到0—1。系数保留方向，适合当作小样本基准。它的短处也很清楚：阈值效应和复杂交互不能自动表示。

**决策树。** 决策树按特征阈值逐层切分样本，可以处理非线性，生成的规则也比较直观。单棵树很容易随样本变化，树过深时尤其容易记住噪声，因此训练时限制深度和叶节点样本数。

**随机森林。** 它对样本和特征重复抽样，训练许多不同的树，再对概率取平均。这样通常比单树稳定，但前提仍是X中确实有可重复的信息。树的数量增加并不会创造信号。

**梯度提升。** 后一棵弱树接着修正前面模型的误差，因而能拟合更细的非线性关系。当前样本不大，我没有铺开很宽的参数搜索，只比较浅树、低学习率等少量预设组合。
""")

    md("""
## 二、机器学习模型评价指标

### 2.1 混淆矩阵

混淆矩阵把实际类别与0.5阈值下的预测类别放在一起。TN和TP是两类判断正确的数量；FP表示把未跑赢错判成跑赢，FN则是漏掉真正跑赢的时段。Accuracy看总体正确率，Precision回答“报出的跑赢信号有多少是真的”，Recall回答“实际跑赢时段被找到了多少”，F1在Precision和Recall之间折中。

### 2.2 ROC曲线与AUC

ROC曲线把概率阈值从高到低移动，记录假阳性率FPR和真阳性率TPR。AUC是曲线下面积，也可以理解成一个排序概率：随机拿出一条Y=1和一条Y=0记录，模型把前者排在更高位置的概率。0.5对应随机排序，1表示完全排对。这个指标绕开了单一阈值，却看不到超额收益大小，更没有纳入手续费和仓位，所以不能直接当作策略收益。
""")

    md("""
## 三、Python编程实现

| 步骤 | 本次作答的具体做法 |
|---|---|
| 1. 准备数据 | 用API拉取并冻结宁德时代前复权日线和沪深300指数，检查日期、缺失、重复、OHLC和覆盖率 |
| 2. 构造标签 | 未来20日宁德时代收益减沪深300收益大于0记为1 |
| 3. 选择特征 | 从20项技术面候选变量中，依次检查滚动验证AUC、稳定性、相关性和VIF |
| 4. 时间划分 | 2021—2024扩展窗口验证；2018—2024发展期只用于建模；2025为最终测试 |
| 5. 训练 | 逻辑回归、决策树、随机森林、梯度提升使用同一组特征 |
| 6. 预测 | 锁定特征和参数后，对2025年周度样本输出Y=1概率 |
| 7. 评估 | AUC、ROC、PR-AUC、混淆矩阵、Accuracy、Balanced Accuracy、Precision、Recall、F1与Brier |
| 8. 特征重要性 | 逻辑回归标准化系数；三类树模型的特征重要性 |
| 9. 保存结果 | 保存原始快照、特征表、筛选表、VIF、模型、预测、ROC点、指标、图表和哈希 |
""")

    md("### 3.0 环境与参数")
    code("""
from pathlib import Path
import json, sys, warnings
warnings.filterwarnings("ignore", category=UserWarning)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display

ROOT = Path.cwd().resolve()
if ROOT.name == "Task5":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "Task5" / "scripts"))
from catl_case_analysis import (
    FEATURES, FEATURE_NAMES, MODEL_NAMES, RAW_DIR, RESULT_DIR, PROCESSED_DIR,
    run_and_save,
)

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({
    "font.sans-serif": ["Songti SC", "SimSun", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False, "figure.dpi": 130, "savefig.dpi": 220,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.labelsize": 10,
})
COLORS = {"orange": "#D97706", "green": "#2F855A", "gray": "#64748B", "red": "#B91C1C", "blue": "#2563EB"}
CHART_DIR = ROOT / "artifacts" / "charts" / "task5" / "catl"
CHART_DIR.mkdir(parents=True, exist_ok=True)

bundle = run_and_save()
daily, samples = bundle.daily, bundle.samples
print(f"Python {sys.version.split()[0]} | pandas {pd.__version__} | 固定随机种子 42")
""")

    md("""
### 3.1 准备数据与质量检查

行情通过AKShare的新浪历史接口取得，日期为2018年6月11日至2025年12月31日。宁德时代采用前复权日线，基准使用沪深300指数点位。我也检查了另一个前复权接口，但其中的宁德时代上市初期价格出现负数，因而没有采用。接口能返回数据，并不等于数据可以直接用于建模。
""")
    code("""
manifest = json.loads((ROOT / "data/task5/catl/metadata/raw_manifest.json").read_text(encoding="utf-8"))
quality = pd.DataFrame([
    {"对象": "宁德时代", **{k: manifest["stock"][k] for k in ["rows", "start_date", "end_date", "duplicate_dates", "missing_required_cells", "invalid_ohlc_rows"]}},
    {"对象": "沪深300", **{k: manifest["benchmark"][k] for k in ["rows", "start_date", "end_date", "duplicate_dates", "missing_required_cells", "invalid_ohlc_rows"]}},
]).rename(columns={"rows":"行数", "start_date":"起始日", "end_date":"截止日", "duplicate_dates":"重复日期", "missing_required_cells":"必需缺失值", "invalid_ohlc_rows":"OHLC异常行"})
display(quality)
print("两组数据共同交易日：", manifest["date_coverage"]["common_dates"], "；日期覆盖率：100%")
""")

    md(f"""
宁德时代和沪深300各有 **{summary['daily_rows']:,}** 个交易日，日期逐日匹配；重复日期、必需字段缺失和OHLC逻辑异常都是0。新浪接口没有提供沪深300成交额。后面的基准特征只涉及收益和波动率，我把成交额保留为空值，没有用0代填。
""")

    md("#### 3.1.1 标签分布与样本量")
    code("""
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
counts = samples["target"].value_counts().sort_index()
axes[0].bar(["0 未跑赢", "1 跑赢"], counts.values, color=[COLORS["gray"], COLORS["orange"]])
axes[0].set_ylabel("周度样本数")
axes[0].set_title("图1(a)：Y总体分布")
for i, v in enumerate(counts.values): axes[0].text(i, v + 3, str(v), ha="center")

yearly = samples.groupby("year")["target"].agg(["count", "mean"])
axes[1].bar(yearly.index.astype(str), yearly["mean"], color=[COLORS["green"] if y < 2025 else COLORS["orange"] for y in yearly.index])
axes[1].axhline(0.5, color=COLORS["gray"], ls="--", lw=1)
axes[1].set_ylim(0, 1); axes[1].set_ylabel("Y=1比例"); axes[1].set_title("图1(b)：分年度Y=1比例")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig01_target_distribution.png", bbox_inches="tight"); plt.show()

sample_summary = pd.DataFrame({
    "口径": ["全部周度样本", "2018—2024开发期", "清除跨界标签后最终训练", "2025最终测试", "近似独立20日窗口"],
    "样本数": [len(samples), (samples.Date < "2025-01-01").sum(), ((samples.Date < "2025-01-01") & (samples.label_end_date < "2025-01-01")).sum(), (samples.Date >= "2025-01-01").sum(), round((samples.Date.max()-samples.Date.min()).days/365.25*252/20)],
})
display(sample_summary)
""")

    md(f"""
每个自然周只取最后一个交易日，最终留下 **{summary['weekly_samples']}** 条记录。Y=1在全样本中占 **{summary['positive_rate_overall']:.1%}**，2025年占 **{summary['positive_rate_test']:.1%}**，类别比例本身没有明显失衡。真正的问题是重叠。观察日通常相隔7天，而标签覆盖约28个自然日，相邻Y的相关系数为 **{target_autocorr:.3f}**，2025年也有 **{test_target_autocorr:.3f}**。按20日非重叠窗口粗略折算，全期只有约 **{summary['approx_independent_20d_windows']:.0f}** 个独立时段，2025年则约12个。370不能按370个独立样本理解。
""")

    md("#### 3.1.2 原始候选特征的描述统计")
    code("""
describe = samples[FEATURES].describe().T.rename(columns={"count":"样本数","mean":"均值","std":"标准差","min":"最小值","25%":"25%","50%":"中位数","75%":"75%","max":"最大值"})
describe.insert(0, "特征", [FEATURE_NAMES[f] for f in describe.index])
display(describe)

fig, axes = plt.subplots(4, 5, figsize=(13, 9))
for ax, feature in zip(axes.flat, FEATURES):
    ax.hist(samples[feature], bins=24, color=COLORS["green"], alpha=.78)
    ax.set_title(FEATURE_NAMES[feature], fontsize=9); ax.tick_params(labelsize=7)
fig.suptitle("图2：20项原始候选特征的分布", y=1.01, fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig02_candidate_distributions.png", bbox_inches="tight"); plt.show()
""")

    md("""
图2里，收益率大致分布在0附近；量比、额比、振幅和波动率明显右偏，也能看到少数极端值。1%—99%缩尾、中位数填充和标准化均在每个训练折内估计，再把同一组参数用于对应的验证或测试数据。这样处理是为了避免提前读取未来分布。
""")

    md(r"""
### 3.2 构造标签

对每个观察日 $t$，先计算宁德时代和沪深300从 $t$ 到 $t+20$ 的简单收益，再取差：

$$R^{excess}_{t,t+20}=\left(\frac{P^{CATL}_{t+20}}{P^{CATL}_{t}}-1\right)-\left(\frac{P^{CSI300}_{t+20}}{P^{CSI300}_{t}}-1\right)$$

$$Y_t=\mathbb{1}\left(R^{excess}_{t,t+20}>0\right)$$

这个Y剔除了部分市场共同涨跌，问题也从“股价会不会涨”变成“宁德时代会不会跑赢基准”。经济含义更清楚，不代表更容易预测。二值化还舍弃了超额收益幅度：跑赢0.1%和跑赢10%都被记为1，这是后文必须承认的一项限制。
""")
    code("""
display(samples[["Date", "Close_stock", "Close_benchmark", "stock_future_20d", "benchmark_future_20d", "future_excess_20d", "label_end_date", "target"]].head(8))
""")

    md("""
### 3.3 选择特征

我没有把候选变量直接称为“有效因子”。它们只是一个待检查的技术面变量池。保留变量时看三件事：在后一年度能否排序、方向是否只依赖个别年份，以及计算时有没有越过观察日。
""")

    md("#### 3.3.1 分组描述性分析")
    code("""
grouped = bundle.grouped.copy()
display(grouped.sort_values("direction_free_auc", ascending=False))

plot_grouped = grouped.sort_values("standardized_mean_difference")
fig, ax = plt.subplots(figsize=(8.5, 6.2))
colors = [COLORS["green"] if x > 0 else COLORS["red"] for x in plot_grouped["standardized_mean_difference"]]
ax.barh(plot_grouped["feature_cn"], plot_grouped["standardized_mean_difference"], color=colors)
ax.axvline(0, color=COLORS["gray"], lw=1)
ax.set_xlabel("Y=1与Y=0的标准化均值差")
ax.set_title("图3：开发期特征的分组差异")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig03_grouped_difference.png", bbox_inches="tight"); plt.show()
""")

    md("""
图3只使用2018—2024年数据。标准化均值差能看出Y=0和Y=1两组在样本内是否分开，但它不是因果效应，也不能代替按年向前验证。标签彼此重叠时，某一阶段形成的差异还可能被重复计算。
""")

    md("#### 3.3.2 相关性、滚动验证与稳定性")
    code("""
development = samples[samples.Date < "2025-01-01"]
corr = development[FEATURES].corr()
fig, ax = plt.subplots(figsize=(11, 8.5))
sns.heatmap(corr, cmap="RdYlGn", center=0, vmin=-1, vmax=1, xticklabels=[FEATURE_NAMES[f] for f in FEATURES], yticklabels=[FEATURE_NAMES[f] for f in FEATURES], ax=ax)
ax.set_title("图4：开发期候选特征相关系数热力图")
plt.xticks(rotation=55, ha="right"); plt.yticks(rotation=0)
plt.tight_layout(); plt.savefig(CHART_DIR / "fig04_correlation_heatmap.png", bbox_inches="tight"); plt.show()
""")

    md("""
图4能看到几组明显重复的信息：不同期限收益与均线偏离彼此相关，RSI和MACD也没有完全独立，量比与额比的关系更直接。候选变量虽有20项，独立信息远少于20项。我先按滚动验证AUC排序，再剔除绝对相关系数不低于0.80的重复变量，并把最终规模限制在8项。
""")
    code("""
pivot = bundle.yearly_audit.pivot(index="feature_cn", columns="validation_year", values="auc")
pivot = pivot.loc[bundle.audit["feature_cn"]]
fig, ax = plt.subplots(figsize=(7.5, 8.2))
sns.heatmap(pivot, annot=True, fmt=".2f", cmap="RdYlGn", center=.5, vmin=.3, vmax=.7, ax=ax, cbar_kws={"label":"单变量逻辑回归AUC"})
ax.set_title("图5：候选特征跨年滚动验证AUC")
ax.set_xlabel("验证年"); ax.set_ylabel("")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig05_feature_stability.png", bbox_inches="tight"); plt.show()
display(bundle.audit)
""")

    md("""
单一全期相关系数会把不同年份揉在一起，图5则把关系逐年拆开。1日收益在四个验证年的AUC都高于0.5，平均约0.578；多数变量至少有一年接近或低于0.5。可见这些关系并不稳定。这里的“高于0.5”也经过了20次候选变量比较，存在筛选偏乐观，不能当作正式显著性结论。
""")

    md("#### 3.3.3 最终特征、箱线图与VIF")
    code("""
selection = bundle.decisions.merge(bundle.audit[["feature", "mean_auc", "std_auc", "years_above_0_5"]], on="feature")
display(selection.sort_values(["selected_final", "mean_auc"], ascending=[False, False]))
display(bundle.vif)

selected = bundle.selected
fig, axes = plt.subplots(2, 4, figsize=(13, 6.2))
for ax, feature in zip(axes.flat, selected):
    sns.boxplot(data=development, x="target", y=feature, ax=ax, palette=[COLORS["gray"], COLORS["orange"]], showfliers=False)
    ax.set_title(FEATURE_NAMES[feature]); ax.set_xlabel("Y"); ax.set_ylabel("")
fig.suptitle("图6：最终入选特征按Y分组的箱线图", y=1.02, fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig06_selected_boxplots.png", bbox_inches="tight"); plt.show()
""")

    selected_cn = "、".join([{"return_1d":"1日收益","rsi14":"RSI(14)","return_10d":"10日收益","return_20d":"20日收益","amount_ratio20":"20日额比","return_5d":"5日收益","intraday_range":"日内振幅","benchmark_volatility20":"沪深300 20日波动率"}.get(f, f) for f in summary["selected_features"]])
    md(f"""
按照开发期滚动AUC、相关性和VIF，留下 **{selected_cn}** 8项变量。最大VIF为 {pd.read_csv(RESULT/'final_vif.csv')['vif'].max():.2f}，低于5，只能排除较严重的线性共线性。图6中两类箱体大面积重叠，说明这些X并没有把Y自然分成两组；后面的模型结果不宜抱太高预期。
""")

    md("""
### 3.4 时间划分

数据没有随机打散。若把相邻周分到训练和测试两边，同一段未来20日价格会同时参与两边标签，结果会偏乐观。这里设置2021—2024四个扩展窗口，2025年单独留作最终测试；每一折还要求训练记录的 `label_end_date` 早于验证年起点，以清除边界处的标签重叠。
""")
    code("""
timeline = pd.DataFrame({
    "阶段": ["2021验证", "2022验证", "2023验证", "2024验证", "2025最终测试"],
    "训练截止": ["2020-12-31", "2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31"],
    "评价起点": ["2021-01-01", "2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01"],
    "评价截止": ["2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"],
})
display(timeline)
fig, ax = plt.subplots(figsize=(11, 3.5))
for i, row in timeline.iterrows():
    start = pd.Timestamp("2018-01-01"); train_end = pd.Timestamp(row["训练截止"]); eval_start = pd.Timestamp(row["评价起点"]); eval_end = pd.Timestamp(row["评价截止"])
    ax.barh(i, (train_end-start).days, left=start, color=COLORS["green"], height=.5)
    ax.barh(i, (eval_end-eval_start).days, left=eval_start, color=COLORS["orange"] if i==4 else COLORS["gray"], height=.5)
ax.set_yticks(range(len(timeline)), timeline["阶段"]); ax.invert_yaxis(); ax.set_title("图7：扩展窗口验证与最终测试时间线")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig07_time_split.png", bbox_inches="tight"); plt.show()
""")

    md("""
图7的绿色部分始终早于对应验证年，灰色为2021—2024年的验证窗口，橙色为2025年测试。这样做牺牲了表面上的样本量，却保留了交易问题应有的时间顺序。
""")

    md("""
### 3.5 构建并训练分类模型

四种模型使用同一组特征和滚动窗口。缩尾、缺失处理均在训练折内拟合，逻辑回归再做标准化。参数组合在读取2025年标签前确定，选择标准是四个验证年AUC的平均值。由于参数和特征都参考了这四年，图8只能描述开发过程，不能当作独立的模型成绩。
""")
    code("""
best_tuning = bundle.tuning.sort_values(["mean_validation_auc", "std_validation_auc"], ascending=[False, True]).groupby("model", as_index=False).head(1)
display(best_tuning[["model_cn", "params", "mean_validation_auc", "std_validation_auc", "auc_2021", "auc_2022", "auc_2023", "auc_2024"]].sort_values("mean_validation_auc", ascending=False))

plot = best_tuning.melt(id_vars=["model", "model_cn"], value_vars=["auc_2021","auc_2022","auc_2023","auc_2024"], var_name="year", value_name="auc")
plot["year"] = plot["year"].str[-4:]
fig, ax = plt.subplots(figsize=(8.5, 4.3))
for model, frame in plot.groupby("model_cn"):
    ax.plot(frame["year"], frame["auc"], marker="o", label=model)
ax.axhline(.5, color=COLORS["gray"], ls="--"); ax.set_ylim(.35,.75); ax.set_ylabel("ROC-AUC"); ax.set_xlabel("滚动验证年")
ax.set_title("图8：锁定参数的跨年验证AUC"); ax.legend(ncol=2)
plt.tight_layout(); plt.savefig(CHART_DIR / "fig08_validation_auc.png", bbox_inches="tight"); plt.show()
""")

    md(f"""
图8中逻辑回归平均AUC为 **{lr_valid:.3f}**，是四种模型里最高的一个；逐年曲线却并不平稳，随机森林和梯度提升同样有明显起伏。这个均值已经参与参数选择，带有开发期内的选择偏差。它不能预告2025年的表现。
""")

    md("### 3.6 对测试集进行概率预测")
    code("""
pred_preview = bundle.predictions.pivot(index=["Date", "target", "future_excess_20d"], columns="model", values="probability").reset_index()
display(pred_preview.head(12))
""")
    md("""
输出列是“未来20日跑赢沪深300”的估计概率，不是收益率预测。读取2025年结果以后，我没有再换变量、改参数或把概率方向倒过来；否则这部分就不再是样本外测试。
""")

    md("### 3.7 模型评估：AUC、ROC与混淆矩阵")
    code("""
metrics = bundle.metrics.sort_values("roc_auc", ascending=False)
display(metrics[["model_cn", "roc_auc", "auc_ci_low", "auc_ci_high", "pr_auc", "accuracy", "balanced_accuracy", "precision", "recall", "f1", "brier", "tn", "fp", "fn", "tp"]])

fig, ax = plt.subplots(figsize=(7.2, 5.5))
for key, frame in bundle.roc_points.groupby("model"):
    auc = metrics.loc[metrics.model==key, "roc_auc"].iloc[0]
    ax.plot(frame.fpr, frame.tpr, lw=2, label=f"{MODEL_NAMES[key]}  AUC={auc:.3f}")
ax.plot([0,1],[0,1], ls="--", color=COLORS["gray"], label="随机排序")
ax.set_xlabel("假阳性率 FPR"); ax.set_ylabel("真阳性率 TPR"); ax.set_title("图9：2025年最终测试ROC曲线"); ax.legend(loc="lower right")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig09_roc.png", bbox_inches="tight"); plt.show()
""")

    md(f"""
决策树的测试AUC为 **{best_test['roc_auc']:.3f}**，四周移动时间块Bootstrap区间为 **[{best_test['auc_ci_low']:.3f}, {best_test['auc_ci_high']:.3f}]**，跨过0.5。逻辑回归、随机森林和梯度提升分别为 **{lr_test['roc_auc']:.3f}**、**{rf_test['roc_auc']:.3f}** 和 **{gb_test['roc_auc']:.3f}**。这组数字没有验证出可用的排序能力。逻辑回归低于0.5，可能是关系换向，也可能只是相关样本太少造成的波动；现有测试集不足以把两种解释分开。
""")

    code("""
fig, axes = plt.subplots(2, 2, figsize=(8.2, 7.2))
for ax, key in zip(axes.flat, MODEL_NAMES):
    row = metrics[metrics.model==key].iloc[0]
    cm = np.array([[row.tn, row.fp],[row.fn, row.tp]], dtype=int)
    sns.heatmap(cm, annot=True, fmt="d", cmap="YlGn", cbar=False, ax=ax)
    ax.set_title(f"{MODEL_NAMES[key]} (AUC={row.roc_auc:.3f})"); ax.set_xlabel("预测类别"); ax.set_ylabel("实际类别")
fig.suptitle("图10：2025年测试集混淆矩阵（阈值0.5）", y=1.02, fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig10_confusion_matrices.png", bbox_inches="tight"); plt.show()
""")

    md("""
图10补充了0.5阈值下的错判结构。梯度提升找到了较多Y=1，同时也报出很多FP；决策树Precision较高，Recall只有0.32。Accuracy在类别比例接近一半时仍可参考，却不能替代跨阈值的排序评价。
""")

    md("#### 3.7.1 管线检查：低AUC是否来自代码错误")
    code("""
display(pd.DataFrame([bundle.controls]).T.rename(columns={0:"结果"}))
""")

    md(f"""
我另外核对了计算管线。scikit-learn与Mann–Whitney秩和公式得到的AUC只相差 **{summary['controls']['auc_formula_absolute_difference']:.2e}**；随机打乱训练标签50次，测试AUC均值为 **{summary['controls']['permuted_label_auc_mean']:.3f}**；把一个可由X直接构造的人工标签交给同一管线，AUC为 **{summary['controls']['synthetic_predictable_label_auc']:.3f}**。逐行复算未来收益后，Y错位数也是0。这些检查只排除了AUC算反、标签错位和管线无法学习等机械问题。它们并不能证明当前Y一定适合预测，更不能把低AUC解释成有效信号。
""")

    md("### 3.8 特征系数与重要性")
    code("""
display(bundle.coefficients.sort_values("coefficient", key=np.abs, ascending=False))
display(bundle.importances.sort_values(["model", "importance"], ascending=[True, False]))

fig, axes = plt.subplots(1, 3, figsize=(14, 5.2))
coef = bundle.coefficients.sort_values("coefficient")
axes[0].barh(coef.feature_cn, coef.coefficient, color=[COLORS["green"] if x>0 else COLORS["red"] for x in coef.coefficient])
axes[0].axvline(0, color=COLORS["gray"], lw=1); axes[0].set_title("逻辑回归标准化系数")
for ax, key in zip(axes[1:], ["random_forest", "gradient_boosting"]):
    imp = bundle.importances[bundle.importances.model==key].sort_values("importance")
    ax.barh(imp.feature_cn, imp.importance, color=COLORS["orange"] if key=="gradient_boosting" else COLORS["green"])
    ax.set_title(f"{MODEL_NAMES[key]}特征重要性")
fig.suptitle("图11：入选特征的系数与树模型重要性", y=1.02, fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig11_feature_importance.png", bbox_inches="tight"); plt.show()
""")

    md("""
逻辑回归系数给出其他入选变量不变时的模型方向，树模型重要性记录变量在分裂中的贡献。两者都不是因果效应。测试AUC没有过关时，图11更适合用来检查模型在依赖什么，而不适合据此宣传某个变量有预测力。
""")

    md("### 3.9 四种模型对比")
    code("""
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ordered = metrics.sort_values("roc_auc")
axes[0].barh(ordered.model_cn, ordered.roc_auc, color=COLORS["orange"])
axes[0].axvline(.5, color=COLORS["gray"], ls="--"); axes[0].set_xlim(.3,.65); axes[0].set_xlabel("2025 ROC-AUC"); axes[0].set_title("测试AUC")
compare = metrics.set_index("model_cn")[["accuracy","balanced_accuracy","precision","recall","f1"]]
compare.plot(kind="bar", ax=axes[1], color=["#94A3B8", "#64748B", "#2F855A", "#D97706", "#2563EB"])
axes[1].set_ylim(0,1); axes[1].set_xlabel(""); axes[1].set_title("阈值0.5下的分类指标"); axes[1].legend(fontsize=8, ncol=2)
fig.suptitle("图12：四种模型最终测试结果汇总", y=1.03, fontsize=13, fontweight="bold")
plt.tight_layout(); plt.savefig(CHART_DIR / "fig12_model_comparison.png", bbox_inches="tight"); plt.show()
""")

    md(f"""
图12把四种模型放在同一口径下。决策树的 **{best_test['roc_auc']:.3f}** 只是四个较弱结果中的最高值，不等于模型有效。区间跨过0.5，2025年又只有约12个非重叠20日窗口，当前结果无法支持稳定优于随机的判断。
""")

    md("""
### 3.10 保存结果

下面这些文件保留了从原始行情到最终图表的中间结果：

- `data/task5/catl/raw/`：冻结的宁德时代与沪深300原始CSV；
- `data/task5/catl/metadata/raw_manifest.json`：数据源、日期、质量结果和SHA-256；
- `data/task5/catl/processed/`：日频特征与周度建模样本；
- `data/task5/catl/results/`：描述统计、特征筛选、VIF、调参、预测、指标、ROC点和解释表；
- `artifacts/models/task5/catl/`：四个锁定后的分类模型；
- `artifacts/charts/task5/catl/`：报告图表。
""")
    code("""
saved = []
for folder in [ROOT/"data/task5/catl/raw", ROOT/"data/task5/catl/processed", ROOT/"data/task5/catl/results", ROOT/"artifacts/models/task5/catl", CHART_DIR]:
    for path in sorted(folder.glob("*")):
        if path.is_file(): saved.append({"文件": str(path.relative_to(ROOT)), "KB": round(path.stat().st_size/1024, 1)})
display(pd.DataFrame(saved))
""")

    md("""
## 四、结果应该怎样理解

### 4.1 标签没有算错，但当前设计的识别力很弱

逐行复算确认，Y确实等于宁德时代未来20日收益减去沪深300同期收益，日期也没有错位。问题出在另一个层面。单只股票在2018—2025年只有一条时间路径；周度取样后虽然有370行，20日持有期使相邻标签大量重叠，全期约91个非重叠窗口，2025年约12个。二值标签还把超额收益幅度丢掉了。目标有经济含义，却未必适合用这点数据和一组技术指标稳定识别。

宁德时代的相对收益还会受产业景气、原材料价格、政策、财报和公司公告影响，当前X只有价格与成交，遗漏信息很多。低AUC既可能来自信号弱，也可能来自数据覆盖和标签粒度，不能全归因于算法。

### 4.2 0.524本身没有预测意义

决策树AUC为0.524，区间为[0.349, 0.691]。这个点估计既没有统计上的区分度，也看不出经济价值。其余三个模型低于0.5，也不能据此断言存在稳定反向规律；48条相关测试记录太少，关系换向与抽样波动都说得通。换句话说，这次没有得到一个可用模型。

管线检查只回答标签是否排反、日期是否错位、模型能否学习。三项检查通过后，可以说计算过程基本正常，却不能证明Y适合预测。AUC不是“错误码”；在当前设计下，它表示模型没有通过测试。

### 4.3 前面的调整改善了问题表述，没有改善预测

早期多股票绝对涨跌口径下，2025年随机森林AUC约0.533；把持有期延长并修改时间验证后，逻辑回归约0.529。改成宁德时代相对沪深300的20日分类后，开发期逻辑回归平均AUC为0.587，2025年最高却只有0.524。三组数据和Y都不同，不能直接排名。能确认的只有一点：相对收益比绝对涨跌更接近“是否超配宁德时代”的问题，但更清楚的目标并没有自动带来更高AUC。

2025年，RSI、10日收益、20日收益和额比的单变量AUC约为0.362、0.405、0.350和0.381，沪深300波动率约为0.689。方向变化可能来自市场状态，也可能只是抽样波动。按测试结果倒转概率会造成信息泄漏，因此没有这样处理。

### 4.4 若重新设计，应先动数据和Y

继续增加同类动量指标的作用有限。下一版应先补行业指数、产业链景气、估值、财报公告和公司事件，再决定预测方向、幅度，还是足以覆盖成本的阈值。单股案例需要更长历史或更少重叠的窗口；扩展到多股票时，则要先确定股票池并处理行业与个股差异。模型调参应排在这些工作之后。
""")

    md("""
## 五、总结

宁德时代与沪深300共有1,837个匹配交易日，转成周度后得到370条记录；由于20日标签重叠，独立信息量远小于表面行数。特征选择和调参只使用2018—2024年，2025年留作测试。最终最高AUC为0.524，置信区间跨过0.5，四种模型都没有达到可用标准。

公式复算、随机标签和人工标签检查没有发现程序性错误，但这并不能挽救研究设计。当前Y舍弃收益幅度，样本来自单只股票的一条历史路径，X又缺少行业与公司事件信息；在这些条件下，低AUC更应被理解为模型未通过测试。若继续做，优先补数据和重新考虑Y，而不是围绕2025年结果继续调参。
""")

    nb.cells = cells
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    }
    nbf.write(nb, OUTPUT)
    print(f"Wrote {OUTPUT} with {len(cells)} cells")


if __name__ == "__main__":
    main()
