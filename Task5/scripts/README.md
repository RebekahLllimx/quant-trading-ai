# TASK5 脚本索引

## 正式乳腺癌主案例

- `cancer_case_analysis.py`：数据检查、特征筛选、模型训练、评价与结果保存。

## 四页 Dashboard

- `build_task5_dashboard.py`：总入口。
- `build_overview_dashboard.py`：项目总览页。
- `build_cancer_dashboard.py`：乳腺癌主案例页。
- `build_finance_dashboard.py`：此前交易数据预测结果页。
- `build_catl_dashboard.py`：宁德时代案例页。

四页构建脚本会自动查找本机已安装的Data Analytics打包工具；非默认安装位置可通过`DATA_ANALYTICS_PLUGIN_ROOT`指定插件版本目录。

## 金融市场补充分析

- `catl_case_analysis.py`、`fetch_catl_case.py`：宁德时代相对沪深300案例。
- `experiment2_common.py` 及文件名含 `experiment2` 的脚本：A股20日涨跌口径。
- `task5_common.py`、`fetch_stock_data.py`、`prepare_ml_data.py`、`train_classifiers.py`、`plot_evaluation.py`、`validate_results.py`：A股截面分类的早期流程。

## 执行顺序与结果位置

建议先运行数据获取或准备脚本，再执行分类训练与验证，最后构建Dashboard。最终报告见[`reports/Task5_Report.pdf`](../../reports/Task5_Report.pdf)。乳腺癌主案例的结果写入`data/task5/breast_cancer/results/`，金融市场实验分别写入`data/task5/course_model/`、`data/task5/experiment2/`和宁德时代案例目录。图表与模型进入项目级`artifacts/`，页面脚本只读取已经生成的结果，不重新选择模型参数。
