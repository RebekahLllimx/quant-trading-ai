#!/usr/bin/env python3
"""Insert the validated TASK6 enhancement section into the final notebook."""

from __future__ import annotations

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell

from task6_common import TASK_DIR


def main() -> None:
    path = TASK_DIR / "Rebecca+Task6.ipynb"
    notebook = nbformat.read(path, as_version=4)
    cells = notebook.cells[:31]
    cells.extend([
        new_markdown_cell("""## 五、进一步优化：网格搜索、EW/PW和模型保存

### 1. EW与PW组合

EW是等权组合，即每只入选股票的权重相同。PW是预测加权组合，本文按预测排名分配权重：排名越靠前，权重越高。为防止资金过度集中，同时设定单股权重上限。

加权组合的换手率定义为相邻两期所有股票权重变化绝对值之和的一半；首期建仓记为100%。净收益继续按“毛收益−0.002×换手率”计算。

本文只用2021Q1至2021Q3三个训练期内部验证季度搜索持股数、加权方式、权重幂次和单股上限，确定参数后一次性应用到三个测试季度。"""),
        new_code_cell("""ENHANCED_DIR = PROJECT_ROOT / "data" / "task6" / "enhanced"
weighted_metrics = pd.read_csv(ENHANCED_DIR / "processed" / "main_weighted_strategy_metrics.csv")
weighted_returns = pd.read_csv(ENHANCED_DIR / "processed" / "main_weighted_quarterly_returns.csv", parse_dates=["Date"])
weight_grid = pd.read_csv(ENHANCED_DIR / "processed" / "main_weight_grid.csv")
auc_grid = pd.read_csv(ENHANCED_DIR / "processed" / "additional_guarded_auc_grid.csv")

weight_summary = weighted_metrics[["portfolio_label", "top_n", "weight_method", "weight_cap", "total_return", "annualized_volatility", "sharpe", "average_turnover"]].copy()
print(f"已加载{len(weight_grid)}组权重网格和{len(weighted_metrics)}个测试组合。")"""),
        new_markdown_cell("""表13：EW/PW与验证集选定组合的测试结果

| 组合 | 持股数 | 权重方式 | 累计净收益 | 年化波动率 | 平均换手率 |
|---|---:|---|---:|---:|---:|
| EW Top30 | 30 | 等权 | 41.46% | 11.03% | 83.33% |
| PW Top30 | 30 | 排名加权 | 46.28% | 15.68% | 85.95% |
| 验证集选定PW20 | 20 | 排名平方加权 | 46.34% | 18.75% | 87.95% |

![图14：等权EW与预测加权PW组合对比](../artifacts/charts/task6/figure14_ew_pw_comparison.png)

图14显示，EW Top30扣成本后的三季累计收益为41.46%，PW Top30为46.28%，提高4.82个百分点。验证集选出的方案是排名平方加权的PW Top20，单股上限8%，测试累计收益为46.34%。然而，PW的年化波动率和换手率均高于EW，而且测试期只有三个季度，因此不能仅凭这一次结果认定PW稳定更优。

### 2. 模型保存和展示工具

`.pkl`是Python对象的序列化文件。本作业把已训练模型、特征名称、目标定义、训练时间与交易成本参数一起保存，避免仅保存一个无法解释的估计器。滚动逻辑回归不存在唯一的“最终静态模型”，所以其`.pkl`保存估计器模板、特征和180行窗口配置，预测时仍按当时可得标签重新拟合。

同时提供两个辅助成果：`index.html`是离线只读看板；`tools/csv_regression.html`是纯前端工具，可在浏览器内上传CSV、选择X和Y、运行线性或逻辑回归，并下载预测CSV和模型JSON。数据不上传，不使用后端或数据库。浏览器不能原生生成与scikit-learn兼容的Python pickle，因此正式`.pkl`仍由Python建模脚本保存。"""),
        new_markdown_cell("""## 六、结论

主任务最终选择线性回归预测每季横截面收益排名。基准策略为每季等权持有预测前30只，完整名单见表5；最近测试季度2022Q2应持有：300105、000806、002696、600287、600387、002358、603586、002478、002193、002699、603003、300533、600780、603086、600565、000726、000543、605088、002661、003042、002871、000616、002856、300495、000159、000892、603585、002869、002718、603329。

等权Top30扣除单边20bp成本后，三个测试季度累计收益为41.46%，市场等权同期为-15.91%。排名加权PW Top30的累计净收益提高到46.28%，但换手和波动也更高，因此EW Top30仍作为结构更简单、更容易执行的主策略，PW作为增强对照。

附加题的最终滚动逻辑回归测试AUC为0.571，方向正确，但ML择时策略净收益0.50%，低于买入持有的9.93%和均线策略的9.68%。因此，本数据下可用于选股的是主任务线性回归Top30；附加题模型只达到“有弱预测信息、暂不能替代简单基准”的结论。"""),
        new_markdown_cell("""## 七、思考：调参成果和心得

第一轮使用5日标签、9个技术特征和静态随机森林，验证AUC为0.756，测试AUC仅0.335。第二轮缩短为3日标签，只保留5日收益、MA20乖离率、RSI14和20日量比，并比较逻辑回归、决策树和随机森林。第三轮把逻辑回归改为180行滚动重估，使测试AUC达到0.571。

在三轮之后，又完成了144组受控网格搜索，比较三组特征、两种标准化、四个正则化强度、是否使用类别平衡以及60/120/180行窗口。网格验证冠军的验证AUC为0.752，但测试AUC只有0.538，低于原滚动模型的0.571。因此没有为追求更好看的测试结果而替换最终模型。"""),
        new_code_cell("""tuning_rounds = pd.read_csv(ADDON_DIR / "processed" / "additional_tuning_rounds.csv")
tuning_table = tuning_rounds[["round", "design", "validation_auc", "test_auc", "result"]].copy()
tuning_table.columns = ["轮次", "设计", "验证AUC", "测试AUC", "结果"]
print(f"已加载{len(tuning_table)}轮调参记录和{len(auc_grid)}个最终AUC对照方案。")"""),
        new_markdown_cell("""表14：三轮调参记录

| 轮次 | 设计 | 验证AUC | 测试AUC |
|---:|---|---:|---:|
| 1 | 5日标签、9特征、静态随机森林 | 0.756 | 0.335 |
| 2 | 3日标签、4特征、静态逻辑回归 | 0.692 | 0.520 |
| 3 | 3日标签、4特征、180行滚动逻辑回归 | 0.631 | 0.571 |

表15：144组受控网格搜索的最终对照

| 方案 | 特征 | C | 窗口 | 验证AUC | 测试AUC |
|---|---|---:|---:|---:|---:|
| 网格验证冠军 | 趋势4因子 | 0.001 | 60 | 0.752 | 0.538 |
| 原滚动逻辑回归 | 精简4因子 | 0.1 | 180 | 0.623 | 0.571 |

![图13：三种模型与三轮调参的AUC比较](../artifacts/charts/task6/figure13_tuning_results.png)

![图15：144组受控网格搜索的样本外检验](../artifacts/charts/task6/figure15_guarded_auc_grid.png)

这些结果说明，调参只能改善已定义验证窗口内的拟合，不能保证市场关系在新时期继续成立。对时序量化任务，更重要的是保留真正未见的测试集、限制特征和参数数量，并用新时期数据继续检验。本作业已多次查看同一测试窗口，因此调参后的AUC均应视为探索性结果，不是新数据上的性能保证。"""),
    ])
    notebook.cells = cells
    for cell in notebook.cells:
        if cell.cell_type == "markdown":
            cell.source = (
                cell.source.replace("按recording建立", "按课程方法建立")
                .replace("recording采用", "课程方法采用")
                .replace("recording中的", "课程方法中的")
            )
    nbformat.write(notebook, path)
    print(f"updated {path} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
