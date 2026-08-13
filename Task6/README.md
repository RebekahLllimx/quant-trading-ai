# TASK6 使用说明

本目录的最终提交文件为：

- `Rebecca+Task6.ipynb`：可复现的完整作业，包含正文、代码、表格、图形与结论。
- `Rebecca+Task6.pdf`：按提交要求排版的正式文档。

课程提供的原始工作簿保存在 `inputs/科技股近一年数据.xlsx`；可复现流水线读取同目录中的规范化CSV输入。

## 分析设计

- 主任务：使用 `inputs/model_data.csv` 构建季度横截面收益排序模型。
- 时间划分：按季度顺序 7:3 划分训练集与测试集，不随机打乱。
- 模型：线性回归、Ridge回归、逻辑回归、决策树、随机森林、直方图梯度提升。
- 目标：回归模型预测同季度未来收益排名；逻辑回归预测是否高于同季度中位数。组合回测仍使用原始实现收益。
- 选股策略：每季度买入预测收益排名前 30 只股票并等权持有，notebook中列出三个测试季度的完整股票代码。
- 基准：同季度样本股票等权平均收益率。
- 交易成本：净收益 = 毛收益 − 0.002 × 单边换手率。
- 稳健性：增加“持仓缓冲区至预测排名 50”的低换手版本。
- 权重扩展：比较等权EW Top30、排名加权PW Top30和训练期内部验证选定的PW Top20。
- 网格搜索：附加题比较144组特征、标准化、正则化、类别平衡和滚动窗口配置，只按验证集选参数。
- 附加题：使用平安银行 `000001.SZ` 日线数据预测未来3日方向。最终采用4个特征和180行滚动逻辑回归，测试AUC为0.571。按课程方法实现双阈值、动态仓位、RSI过滤、止损止盈和27组验证网格，并对比买入持有、均线和ML择时三种策略。

## 复现方法

在项目根目录依次运行：

```bash
python Task6/scripts/main_pipeline.py
python Task6/scripts/additional_pipeline.py
python Task6/scripts/enhanced_pipeline.py
python Task6/scripts/plot_results.py
python Task6/scripts/update_notebook_enhancements.py
jupyter nbconvert --execute --to notebook --inplace Task6/Rebecca+Task6.ipynb
python Task6/scripts/audit_language.py
python Task6/scripts/build_dashboard.py
python Task6/scripts/build_pdf.py
python Task6/scripts/validate_results.py
```

`build_dashboard.py`生成可复核的`dashboard/artifact.json`，仓库同时保留已经打包完成的`dashboard/index.html`。如需重新打包HTML，可在安装Data Analytics插件后使用其`deliver_portable_artifact.mjs`工具。

模型同时保存为`.joblib`和`.pkl`，位于 `../artifacts/models/task6/`。结构化结果保存在 `../data/task6/`，图形保存在 `../artifacts/charts/task6/`。只读看板和纯前端CSV回归HTML工具位于`dashboard/`。固定随机种子为 42。

## 解释边界

主任务测试期只有 3 个季度，因此累计收益、年化收益和夏普比率均为教学性样本描述，不能作为未来表现保证。原始样本缺少财务数据实际披露日、历史指数成分、停牌、ST 与流动性标记，仍可能存在时点可得性和幸存者偏差。附加题经三轮调参后的测试AUC为0.571，但三轮尝试查看了同一测试窗口，所以该结果仍属于探索性结果，需要用全新数据再验证。
