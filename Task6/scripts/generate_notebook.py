#!/usr/bin/env python3
"""Generate the reader-facing and executable TASK6 notebook."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Task6" / "Rebecca+Task6.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def main() -> None:
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.9"},
    }
    notebook["cells"] = [
        md(
            r"""
# TASK6 智能决策者：用机器学习定制专属策略

本文按题目的三个问题依次作答，并完成一个单股机器学习择时的附加题。
"""
        ),
        md(
            r"""
## 一、基于机器学习模型的交易策略

### 1. 核心理念

这类策略先用历史数据学习自变量$X$与未来结果$Y$的关系，然后把模型输出转换为可执行的交易规则。模型给出的分数、排名或概率本身不是买卖指令，还需要配合选股数量、仓位、阈值、调仓频率和风险控制。

本作业的主策略在每个季末计算股票的估值、规模和成长类因子，预测下季度收益在当期股票池中的相对位置，再等权买入排名前30只。下一个季度使用新数据重新排序和调仓。整个过程依次连接季末可观察因子、未来收益排名、Top 30组合和下季度实现收益。

### 2. 优点和缺点

| 方面 | 优点 | 缺点 |
|---|---|---|
| 信息处理 | 可以同时利用多个因子，树模型还能捕捉非线性和交互关系 | 当数据本身没有稳定信息时，增加模型复杂度并不会自动产生有效信号 |
| 规则一致性 | 同样的数据和参数可以复现同样的决策 | 数据泄漏、幸存者偏差和反复试验可能制造虚假的稳定性 |
| 模型更新 | 可以通过滚动训练吸收新数据 | 市场状态会变化，早期样本中有效的关系未必能够延续 |
| 交易执行 | 概率可以转换为动态仓位，也能加入双阈值、止损和止盈 | 手续费、滑点、停牌、涨跌停和容量限制会使实盘结果低于理想回测 |
| 解释性 | 线性系数和特征重要性可以帮助检查模型 | 重要性反映模型对变量的依赖，不能直接解释为因果关系 |
"""
        ),
        md(
            r"""
## 二、量化交易模型中的自变量和应变量

### 1. 常见自变量因子

| 因子类型 | 常用指标 | 基本定义 |
|---|---|---|
| 估值 | PE、PB、PS、EV/EBITDA、PCF、股息率 | 描述股价相对于盈利、净资产、收入或现金流的高低 |
| 规模 | 总市值、流通市值及其对数 | 表示公司的权益市场价值 |
| 质量 | ROE、毛利率、资产负债率、经营现金流 | 衡量盈利能力、财务结构和利润的现金支持 |
| 成长 | 收入、净利润、EPS、资产和现金流增长率 | 衡量公司经营指标相对上年同期的变化 |
| 动量与趋势 | 过去1、5、20、60日收益、均线偏离、MACD、RSI | 描述价格在近期的方向、速度和超买超卖程度 |
| 风险与流动性 | 波动率、ATR、Beta、换手率、成交量比、买卖价差 | 描述价格不确定性、交易活跃度和交易难度 |

### 2. 常见应变量

应变量必须与投资持有期对齐。回归任务可以预测未来$h$期原始收益$r_{i,t\rightarrow t+h}$、超额收益$r_{i,t\rightarrow t+h}-r_{b,t\rightarrow t+h}$或横截面收益排名。分类任务可以定义为未来收益是否为正、是否跑赢基准，或是否进入当期股票池的前30%。风险模型则常预测未来波动率、最大回撤或极端下跌事件。

本作业的目标是为每季股票排序，因此主回归应变量定义为同季度`Next_Ret`的百分位排名，再居中到$[-0.5,0.5]$。这个设计保留高低顺序，又不让单个极端收益控制模型。线性回归、Ridge、决策树、随机森林和梯度提升预测这个连续排名。逻辑回归虽然名称中有回归，实际是分类模型，它的$Y$是`Next_Ret`是否高于同季度中位数。所有模型最终都按预测分数排序，组合收益仍用未转换的`Next_Ret`计算。
"""
        ),
        md(
            r"""
## 三、Python编程实现

### 1. 加载已存储的模型样本

主任务读取课程提供的`model_data.csv`，每行表示某只股票在一个季末的因子和下期收益。整理后的样本包含39,616条股票季度记录，涉及4,281只股票和10个季度。加载后先检查股票代码与日期组合是否唯一、数值列是否缺失，再进行因子衍生和时间划分。固定随机种子为42，使随机森林等模型在重复运行时产生一致结果，便于核对模型比较和回测指标。

原始文件没有提供财务报表的实际披露日期，也缺少历史成分股、ST、停牌和流动性标记。因此，季末财务因子能否在当时完整取得无法独立验证，样本中也可能存在时点可得性偏差、幸存者偏差和实际交易限制。后文的模型指标与组合收益主要用于课程中的方法比较，不能直接外推为未来实盘收益，也不构成投资建议。
"""
        ),
        code(
            """
from pathlib import Path
import json
import sys
import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display

START = Path.cwd().resolve()
PROJECT_ROOT = START if (START / "Task6").exists() else START.parent
SCRIPT_DIR = PROJECT_ROOT / "Task6" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from main_pipeline import run_main_pipeline
from additional_pipeline import run_additional_pipeline
from plot_results import main as build_plots

pd.set_option("display.max_columns", 20)
pd.set_option("display.float_format", lambda value: f"{value:.4f}")
RUN_PIPELINE = True
TRANSACTION_COST = 0.002
TOP_N = 30
BUFFER_RANK = 50
RANDOM_SEED = 42

if RUN_PIPELINE:
    run_main_pipeline()
    run_additional_pipeline()
    build_plots()
    print("TASK6主任务、附加题和13张图已重新生成。")
"""
        ),
        code(
            """
MAIN_DIR = PROJECT_ROOT / "data" / "task6" / "main"
ADDON_DIR = PROJECT_ROOT / "data" / "task6" / "additional"
CHART_DIR = PROJECT_ROOT / "artifacts" / "charts" / "task6"

main_dataset = pd.read_csv(
    MAIN_DIR / "processed" / "main_model_dataset.csv",
    parse_dates=["Date"], dtype={"Code": "string"}
)
main_quality = json.loads(
    (MAIN_DIR / "metadata" / "data_quality_report.json").read_text(encoding="utf-8")
)

quality_table = pd.DataFrame({
    "检查项目": ["样本行数", "季度数", "股票代码数", "重复股票季度键", "原始缺失单元格", "训练行数", "测试行数"],
    "结果": [
        main_quality["rows"], main_quality["quarter_count"], main_quality["stock_count"],
        main_quality["duplicate_code_date_rows"], main_quality["missing_raw_cells"],
        main_quality["train_rows"], main_quality["test_rows"],
    ],
})
print("表1：主任务数据检查")
display(quality_table)

assert main_quality["duplicate_code_date_rows"] == 0
assert main_quality["missing_raw_cells"] == 0
assert main_dataset.duplicated(["Code", "Date"]).sum() == 0
"""
        ),
        md(
            r"""
![图1：季度样本数和未来收益分布](../artifacts/charts/task6/figure01_data_profile.png)

图1显示，季度样本数从2020Q1的3,627条增加到2022Q2的4,262条。`Next_Ret`的右尾很长，最大值超过600%。这正是排名目标比直接拟合原始收益更合适的一个原因。回测时不会删除这些实现收益，因为它们确实影响组合结果。
"""
        ),
        md(
            r"""
### 2. 衍生自变量并设计应变量

原始数据含19项估值、规模、股息和成长指标。PE、PCF等比率可以为负，又有较大极值，所以先在每个季度内转换为横截面百分位排名：

$$RankX_{i,t}=PctRank_t(x_{i,t})-0.5$$

处理后的特征主要位于$[-0.5,0.5]$。在19个排名特征之外，又计算价值、成长、利润增长和现金流四个复合因子，共有23个自变量。主回归目标同样是当季度内`Next_Ret`的百分位排名：

$$Y^{rank}_{i,t}=PctRank_t(Next\_Ret_{i,t})-0.5$$

逻辑回归的二元目标是：

$$Y^{class}_{i,t}=1[Next\_Ret_{i,t}>Median_t(Next\_Ret)]$$

如果直接用已做季度横截面排名的$X$去预测原始收益数值，季度整体涨跌会混入点预测误差，与题目关心的股票顺序不完全一致。本次因此把模型目标和交易目标对齐到排名。
"""
        ),
        code(
            """
split_table = (
    main_dataset.groupby(["Split", "Date"], as_index=False)
    .agg(样本数=("Code", "size"), 平均原始收益=("Next_Ret", "mean"), 排名目标均值=("Next_Ret_Rank", "mean"))
)
split_table["季度"] = split_table["Date"].dt.year.astype(str) + "Q" + split_table["Date"].dt.quarter.astype(str)
split_table["数据集"] = split_table["Split"].map({"train": "训练集", "test": "测试集"})
print("表2：7:3时间划分与应变量")
display(split_table[["数据集", "季度", "样本数", "平均原始收益", "排名目标均值"]])
print("模型特征数：", len(main_quality["model_features"]))
print("排名目标范围：", main_dataset["Next_Ret_Rank"].min(), "至", main_dataset["Next_Ret_Rank"].max())
"""
        ),
        md(
            r"""
![图2：主任务的7:3时间划分](../artifacts/charts/task6/figure02_time_split.png)

图2中，2020Q1至2021Q3的7个季度用于训练，共26,953条记录；2021Q4至2022Q2的3个季度留作最终测试，共12,663条。数据没有随机打乱。训练期内的参数比较采用扩展窗口，分别验证2021Q1、2021Q2和2021Q3。
"""
        ),
        md(
            r"""
### 3. 划分训练集、测试集，构建并训练模型

本次比较六种模型：普通线性回归、Ridge回归、逻辑回归、决策树、随机森林和直方图梯度提升。线性回归能提供直观基准，Ridge用正则化减轻多重共线性，决策树用于检查单树的非线性分割，随机森林和梯度提升则比较集成模型的效果。逻辑回归输出高于季度中位数的概率，用概率排名参与统一比较。

候选参数先在训练期扩展窗口中比较。Rank IC是预测排名与实际收益排名的Spearman相关系数，大于0表示预测方向正确，数值越大则排序能力越强。本任务以各验证季度的Rank IC均值选参。主策略另设定一条简约规则：当简单模型的验证IC与最高值相差不超过0.01时，优先用更简单的模型。

$R^2$用于评价回归模型，表示模型对应变量波动的解释程度，大于0表示模型优于直接使用样本均值。AUC用于评价分类模型对正负样本的排序能力，0.5相当于随机排序，大于0.5才说明分类概率具有正向识别能力。
"""
        ),
        code(
            """
model_metrics = pd.read_csv(MAIN_DIR / "processed" / "main_model_metrics.csv")

candidate_short = {
    "ordinary least squares": "OLS",
    "alpha=10": "alpha=10",
    "C=0.01": "C=0.01",
    "depth=4,leaf=250": "d4,l250",
    "depth=5,leaf=20,features=0.5": "d5,l20,f0.5",
    "leaves=15,l2=10": "l15,L2=10",
}

def native_result(row):
    if row["task_type"] == "classification":
        return f"测试AUC={row['auc']:.3f}"
    return f"测试R²={row['r2']:.3f}"

model_table = pd.DataFrame({
    "模型": model_metrics["model_label"],
    "任务": model_metrics["task_type"].map({"rank_regression": "排名回归", "classification": "分类"}),
    "入选参数": model_metrics["selected_candidate"].map(candidate_short),
    "验证平均IC": model_metrics["validation_mean_ic"],
    "本任务指标": model_metrics.apply(native_result, axis=1),
    "测试平均IC": model_metrics["mean_test_ic"],
    "主策略": model_metrics["strategy_model"].map({True: "是", False: ""}),
})
print("表3：六种模型的样本外结果")
display(model_table)
"""
        ),
        md(
            r"""
![图3：六种模型的训练期验证Rank IC](../artifacts/charts/task6/figure03_validation_ic.png)

图3中的验证平均IC介于0.114和0.132之间。Ridge的0.132最高，普通线性回归为0.129，两者差0.003，落在0.01的简约容差内。因此主策略按预先制定的规则选择普通线性回归。

![图4：六种模型在测试季度的Rank IC](../artifacts/charts/task6/figure04_test_ic.png)

图4显示18个模型季度组合的IC都为正。线性回归的测试平均IC为0.273，Ridge为0.274，决策树最低，为0.235。五个排名回归模型的测试$R^2$介于0.050和0.068之间，逻辑回归的测试AUC为0.633。两类指标都大于各自的基准值。
"""
        ),
        md(
            r"""
### 4. 基于模型建立交易策略

在每个测试季度，先按模型分数从高到低排序，再等权持有前30只。组合毛收益和市场等权收益分别为：

$$R^{Top30}_{t+1}=\frac{1}{30}\sum_{i\in Top30_t}Next\_Ret_{i,t}$$

$$R^{Market}_{t+1}=\frac{1}{N_t}\sum_{i=1}^{N_t}Next\_Ret_{i,t}$$

换手率是本期调仓时发生变化的仓位占组合的比例。例如，30只股票中替换9只，单边换手率为30%。交易成本采用已确认的单边20bp，即按实际变动的仓位扣0.20%。设换手率为$Turnover_t$，则：

$$R^{net}_t=R^{gross}_t-0.002\times Turnover_t$$

首次建仓的换手率记为100%。之后严格Top 30的单边换手率为$1-|H_t\cap H_{t-1}|/30$。
"""
        ),
        code(
            """
quarterly_returns = pd.read_csv(
    MAIN_DIR / "processed" / "main_quarterly_returns.csv", parse_dates=["Date"]
)
main_metadata = json.loads(
    (MAIN_DIR / "metadata" / "model_run.json").read_text(encoding="utf-8")
)
strategy_model = main_metadata["strategy_model"]

main_quarterly = quarterly_returns[
    (quarterly_returns["model"] == strategy_model)
    & (quarterly_returns["portfolio"] == "strict_top30")
].copy()
main_quarterly["季度"] = main_quarterly["Date"].dt.year.astype(str) + "Q" + main_quarterly["Date"].dt.quarter.astype(str)
main_quarterly = main_quarterly[["季度", "gross_return", "net_return", "market_return", "gross_excess", "turnover"]]
main_quarterly.columns = ["季度", "Top30毛收益", "Top30净收益", "市场平均", "毛超额", "单边换手率"]
print("表4：线性回归Top 30在三个测试季度的收益")
display(main_quarterly)
"""
        ),
        code(
            """
holdings = pd.read_csv(
    MAIN_DIR / "processed" / "main_portfolio_holdings.csv",
    parse_dates=["Date"], dtype={"Code": "string"}
)
selected_holdings = holdings[
    (holdings["model"] == strategy_model)
    & (holdings["portfolio"] == "strict_top30")
].sort_values(["Date", "predicted_rank"])

quarter_dates = [pd.Timestamp(date) for date in sorted(selected_holdings["Date"].unique())]
quarter_labels = [f"{date.year}Q{date.quarter}" for date in quarter_dates]
quarter_codes = []
for date in quarter_dates:
    codes = selected_holdings.loc[selected_holdings["Date"] == date, "Code"].tolist()
    quarter_codes.append(["、".join(codes[i:i + 3]) for i in range(0, 30, 3)])

holdings_table = pd.DataFrame({"组别": range(1, 11)})
for label, codes in zip(quarter_labels, quarter_codes):
    holdings_table[label] = codes
print("表5：线性回归主策略每个测试季度选中的30只股票代码")
display(holdings_table)
"""
        ),
        md(
            r"""
表5给出了实际选股结果，每列共30只，代码从上到下按预测排名排列。原始样本只提供六位股票代码，没有证券简称，因此本文不自行补写名称。其中，最近的测试季度2022Q2的30只就是当期应持有的股票。
"""
        ),
        md(
            r"""
![图5：六种Top 30策略与市场平均的季度收益](../artifacts/charts/task6/figure05_quarterly_returns.png)

线性回归Top 30在2021Q4、2022Q1和2022Q2的毛收益分别为15.17%、16.25%和6.12%，同期市场平均为-8.37%、1.07%和-9.20%。三季超额都为正。其他五种模型也采用同样的Top 30规则，因而组合差异来自模型排序，而不是回测口径不同。

![图6：六种Top 30策略与市场平均的累计净值](../artifacts/charts/task6/figure06_cumulative_wealth.png)

三季复利后，线性回归Top 30毛收益为42.08%，市场等权平均为-15.91%。随机森林在这一测试窗口的毛收益最高，为51.39%，但不能因为看到测试期收益后再把它改为主策略。否则，测试集就变成了选模型的一部分。
"""
        ),
        md(
            r"""
### 5. 回测策略，计算指标并绘图

累计收益是各期收益连乘后的总增长；年化收益是把回测期收益折算为一年口径；年化波动率衡量收益波动的大小。夏普比率是年化收益均值与年化波动率的比值，本文假设无风险利率为0，数值越高表示每承担一单位波动获得的收益越多。最大回撤是净值从历史高点到之后低点的最大跌幅；胜率是收益为正的期数占比。

表6统一给出上述指标和平均换手率。主测试集只有3个季度，因此年化结果和夏普比率只用于统一口径的比较，不能当成长期稳定参数。
"""
        ),
        code(
            """
strategy_metrics = pd.read_csv(MAIN_DIR / "processed" / "main_strategy_metrics.csv")

gross_summary = strategy_metrics[
    (strategy_metrics["portfolio"] == "strict_top30")
    & (strategy_metrics["return_type"] == "gross_return")
][["model_label", "average_turnover", "total_return", "annualized_return", "annualized_volatility", "sharpe", "max_drawdown", "win_rate"]].copy()
gross_summary.columns = ["模型", "平均换手", "累计收益", "年化收益", "年化波动", "夏普比率", "最大回撤", "季度胜率"]
print("表6：六种Top 30策略的毛收益指标")
display(gross_summary)

selected_summary = strategy_metrics[strategy_metrics["model"] == strategy_model][
    ["portfolio", "return_type", "average_turnover", "total_return", "sharpe", "max_drawdown"]
].copy()
selected_summary["组合"] = selected_summary["portfolio"].map({"strict_top30": "严格Top 30", "buffer_top30_top50": "Top 50缓冲"})
selected_summary["口径"] = selected_summary["return_type"].map({"gross_return": "毛收益", "net_return": "扣20bp后"})
print("表7：主策略的交易成本和缓冲换仓检查")
display(selected_summary[["组合", "口径", "average_turnover", "total_return", "sharpe", "max_drawdown"]])
"""
        ),
        md(
            r"""
![图7：20bp成本与缓冲换仓的敏感性](../artifacts/charts/task6/figure07_cost_buffer.png)

严格Top 30的平均单边换手率为83.33%，扣除20bp后，累计收益从42.08%降到41.46%。Top 50缓冲规则会保留上期持仓中仍位于预测前50的股票，再用新股补足30只。它将平均换手率降至77.78%，但扣成本的累计收益也降到36.79%。在这三季中，减少换手没有弥补排名纯度下降带来的收益损失。

![图8：正则化线性模型与树模型的特征依赖](../artifacts/charts/task6/figure08_feature_importance.png)

图8用Ridge系数展示线性方向，避免普通最小二乘系数在高相关因子下过度放大。右侧是随机森林的特征重要性。两种表达方式都显示模型较多使用盈利和成长信息，但这些结果不能作为因果解释。
"""
        ),
        md(
            r"""
### 6. 六种模型的效果比较

线性回归和Ridge的排名指标几乎相同，说明在当前样本中，主要信息用较简单的线性组合已经能表达。逻辑回归的AUC为0.633，并且排名IC为0.263，说明二元分类概率也可以用来排序。决策树的测试IC和组合收益在六个模型中较低，单树对样本分割比较敏感。随机森林和梯度提升缓解了这一问题，但验证IC没有显示出稳定的复杂模型优势。

主策略选择线性回归，依据是训练期内部验证和简约规则，不是测试集中谁的最终收益最高。这一点比事后选出51.39%的随机森林更重要，因为它保留了测试的样本外含义。
"""
        ),
        md(
            r"""
## 四、附加题：平安银行机器学习择时

### 1. 数据、特征和最终模型

附加题使用项目中的日线数据。文件名中写着平安集团，但证券代码`000001.SZ`对应平安银行，因此本文按证券代码记为平安银行。样本从2024年1月2日到2025年7月17日，共372个交易日。

最终使用四个特征：5日收益率表示近期动量；MA20偏离是收盘价相对20日均线的高低；RSI14是14日相对强弱指标，本文将其缩放到0至1；20日成交量比是当日成交量与20日平均成交量的比值。应变量定义为未来3个交易日的收益是否大于0。

可用建模样本按70%和30%严格按时间划分，分界处清除3行，使训练标签的结束日早于测试起点。最终模型是180行滚动逻辑回归。“滚动”指每到一个新日期，只用当时已知结果的最近180条数据重新训练，再预测当日，这样既不使用未来标签，也能逐步更新近期关系。
"""
        ),
        code(
            """
addon_quality = json.loads(
    (ADDON_DIR / "metadata" / "data_quality_report.json").read_text(encoding="utf-8")
)
addon_metadata = json.loads(
    (ADDON_DIR / "metadata" / "model_run.json").read_text(encoding="utf-8")
)
addon_metrics = pd.read_csv(ADDON_DIR / "processed" / "additional_model_metrics.csv")

addon_quality_table = pd.DataFrame({
    "项目": ["原始交易日", "可用建模行", "训练行", "边界清除行", "测试行", "重复日期", "OHLC逻辑异常"],
    "结果": [addon_quality["rows"], addon_quality["usable_model_rows"], addon_quality["train_rows"], addon_quality["purged_boundary_rows"], addon_quality["test_rows"], addon_quality["duplicate_dates"], addon_quality["ohlc_inconsistent_rows"]],
})
print("表8：附加题数据检查与时间划分")
display(addon_quality_table)

addon_model_table = addon_metrics[["model_label", "test_auc", "accuracy", "balanced_accuracy", "brier"]].copy()
addon_model_table.columns = ["模型", "静态模型测试AUC", "准确率", "平衡准确率", "Brier分数"]
print("表9：相同3日标签和4特征下的三种静态分类模型")
display(addon_model_table)
print(f"最终180行滚动逻辑回归：验证AUC={addon_metadata['final_validation_auc']:.3f}，测试AUC={addon_metadata['final_test_auc']:.3f}。")
"""
        ),
        md(
            r"""
![图9：平安银行价格、均线和RSI](../artifacts/charts/task6/figure09_additional_indicators.png)

图9覆盖了上涨、回落和横盘阶段。MA5和MA20用于构造对比策略，RSI用于限制模型策略在过热区入场。在相同的3日标签和4个特征下，表9中逻辑回归、决策树和随机森林的测试AUC分别为0.520、0.509和0.559，均高于0.5。最终滚动逻辑回归的测试AUC进一步提高到0.571，说明正类概率已经具有正向的区分能力。
"""
        ),
        md(
            r"""
### 2. 按recording建立双阈值和动态仓位策略

模型概率只表示对未来3日上涨可能性的估计，还需要转换成仓位。仓位是投入股票的资金占组合总资产的比例，例如0.8表示80%资金持有股票，其余20%保持现金。

recording采用双阈值：概率高于买入阈值时允许建仓，低于卖出阈值时清仓，两者之间保持原仓位，以减少概率在单一分界附近波动带来的反复交易。买入阈值在0.55、0.60和0.65中选择，卖出阈值在0.35、0.40和0.45中选择，最大仓位在0.6、0.8和1.0中选择，共27种组合。参数只在训练期内部验证段按夏普比率比较，最终为买入0.60、卖出0.35、最大仓位0.8。

目标仓位使用recording中的概率映射：

$$Position_t=\min(MaxPos,\max(0,(p_t-0.5)\times2\times MaxPos))$$

当概率越高，仓位越大，但不超过80%。入场时还要求RSI14低于0.70，避免在过热区追高。最终规则不再同时要求MA5高于MA20，因为这会与模型中的趋势信息重复，并过度压缩交易机会。风险控制使用8%止损和15%止盈，每次仓位变动都按单边20bp扣费。
"""
        ),
        code(
            """
signal = addon_metadata["signal"]
signal_table = pd.DataFrame({
    "买入阈值": [signal["buy_threshold"]],
    "卖出阈值": [signal["sell_threshold"]],
    "最大仓位": [signal["max_position"]],
    "RSI入场限制": ["RSI14 < 0.70"],
    "止损": [signal["stop_loss"]],
    "止盈": [signal["take_profit"]],
    "单边成本": [signal["transaction_cost"]],
})
print("表10：附加题最终交易规则")
display(signal_table)
"""
        ),
        md(
            r"""
![图10：滚动逻辑回归概率、双阈值和实际仓位](../artifacts/charts/task6/figure10_additional_probability_position.png)

图10展示了概率到仓位的转换。测试期内共有1次从空仓进入持仓，之后因模型概率低于0.35退出，没有触发止损或止盈。持仓日占比为39.45%，说明双阈值让策略在信号不明确时保留了较多现金。
"""
        ),
        md(
            r"""
### 3. 多策略回测比较

买入持有是在测试期开始买入并一直持有，作为不择时的基准。均线策略在MA5高于MA20时持有80%仓位，否则空仓，用来代表简单趋势规则。ML择时策略使用上述滚动逻辑回归概率。三种策略都按仓位变化扣除单边20bp成本。
"""
        ),
        code(
            """
addon_strategy_metrics = pd.read_csv(
    ADDON_DIR / "processed" / "additional_strategy_metrics.csv"
)
addon_strategy_table = addon_strategy_metrics[[
    "strategy_label", "total_return", "annualized_return", "sharpe", "max_drawdown",
    "trade_count", "total_turnover", "days_in_market_ratio"
]].copy()
addon_strategy_table.columns = ["策略", "累计收益", "年化收益", "夏普比率", "最大回撤", "入场次数", "总换手", "持仓日占比"]
print("表11：附加题三种策略的测试期结果")
display(addon_strategy_table)
"""
        ),
        md(
            r"""
![图11：附加题三种策略的测试期净值](../artifacts/charts/task6/figure11_additional_wealth.png)

在109个回测交易日中，ML择时策略扣成本后收益为0.50%，年化波动率为2.09%，最大回撤为-1.37%。买入持有和均线策略的收益分别为9.93%和9.68%。最终ML策略实现了正收益，但没有跑赢两个简单对照，因此不能得出“机器学习策略更好”的结论。

![图12：附加题三种策略的回撤路径](../artifacts/charts/task6/figure12_additional_drawdown.png)

图12显示，买入持有的最大回撤为-10.61%，均线策略为-3.78%，ML策略仅为-1.37%。ML的回撤较小，与其只有39.45%的时间持仓有直接关系。它在本期更像一个低暴露策略，收益稳定性还需要更长样本检验。
"""
        ),
        md(
            r"""
## 五、结论

主任务最终选择线性回归每季持有预测排名前30的股票，完整名单见表5。最近的测试季度2022Q2应持有：300105、000806、002696、600287、600387、002358、603586、002478、002193、002699、603003、300533、600780、603086、600565、000726、000543、605088、002661、003042、002871、000616、002856、300495、000159、000892、603585、002869、002718和603329。

五个排名回归模型的测试$R^2$都为正，六种模型的三个测试季度IC也都为正。线性回归Top 30的三季毛收益为42.08%，扣除单边20bp成本后为41.46%，同期市场等权平均为-15.91%。这一样本内结果支持用估值、规模和成长类因子进行季度横截面选股。

附加题中，最终180行滚动逻辑回归的测试AUC为0.571，已高于随机排序的0.5。据此建立的双阈值策略扣成本后收益为0.50%，但低于买入持有的9.93%和均线策略的9.68%。所以，最终模型通过了方向性的最低检验，但还没有证明能够带来超额收益。

主任务只有3个测试季度，附加题只有单只股票约1.5年数据。原始数据还缺少财务报表实际披露日、历史股票池、ST、停牌、涨跌停和流动性标记，因此时点可得性、幸存者偏差和实际可交易性仍然是主要限制。

本作业仅用于课程研究，不构成投资建议。
"""
        ),
        md(
            r"""
## 六、思考：三轮调参的结果和心得

第一轮直接使用5日标签、9个技术特征和静态随机森林，验证AUC为0.756，但测试AUC仅0.335。验证好而测试失败，说明高维特征和非线性树模型记住了训练阶段的关系，但没有迁移到新时期。

第二轮把预测期缩短为3日，只保留5日收益、MA20偏离、RSI14和20日成交量比，并改用结构更简单的逻辑回归。测试AUC上升到0.520，说明缩短预测期和减少变量后，模型不再完全依赖早期样本中的复杂分割。

第三轮保留第二轮的标签和特征，改为180行滚动训练，测试AUC进一步提高到0.571。策略层面去掉与模型趋势信息重复的均线入场条件，并将止损从5%放宽到8%，最终测试收益从负值改善为扣成本后0.50%。
"""
        ),
        code(
            """
tuning_rounds = pd.read_csv(
    ADDON_DIR / "processed" / "additional_tuning_rounds.csv"
)
tuning_table = tuning_rounds[["round", "design", "validation_auc", "test_auc", "result", "selected"]].copy()
tuning_table.columns = ["轮次", "设计", "验证AUC", "测试AUC", "结果", "最终使用"]
tuning_table["最终使用"] = tuning_table["最终使用"].map({True: "是", False: ""})
print("表12：附加题三轮调参结果")
display(tuning_table)
"""
        ),
        md(
            r"""
![图13：三种模型与三轮调参的AUC比较](../artifacts/charts/task6/figure13_tuning_results.png)

这三轮的主要收获是，单只股票的短样本不适合一味增加特征和模型复杂度。更短的标签周期、更精简的变量和滚动更新更适合当前数据。但三轮尝试已经查看过同一测试窗口，因此最终AUC 0.571和收益0.50%应视为调参后的探索性结果，而不是全新样本外证据。如果后续数据的AUC再次长期低于0.5，就不应继续追加参数，而应考虑训练期学到的市场模式已变，机器学习所依赖的稳定关系前提已经失效。
"""
        ),
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, OUTPUT)
    print(f"[notebook] wrote {OUTPUT}")


if __name__ == "__main__":
    main()
