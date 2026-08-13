# TASK5 脚本索引

## 正式乳腺癌主案例

- `cancer_case_analysis.py`：数据检查、特征筛选、模型训练、评价与结果保存。
- `generate_cancer_notebook.py`：生成正式 Notebook 母版。
- `patch_notebook_tex.py`：修正 Notebook 导出 PDF 时的中文字体、段落和代码块版式。

## 四页 Dashboard

- `build_task5_dashboard.py`：总入口。
- `build_overview_dashboard.py`：项目总览页。
- `build_cancer_dashboard.py`：乳腺癌主案例页。
- `build_finance_dashboard.py`：此前交易数据预测结果页。
- `build_catl_dashboard.py`：宁德时代案例页。

四页构建脚本会自动查找本机已安装的Data Analytics打包工具；非默认安装位置可通过`DATA_ANALYTICS_PLUGIN_ROOT`指定插件版本目录。

## 金融市场补充分析

- `catl_case_analysis.py`、`fetch_catl_case.py`、`generate_catl_notebook.py`：宁德时代相对沪深300案例。
- `experiment2_common.py` 及文件名含 `experiment2` 的脚本：A股20日涨跌口径。
- `task5_common.py`、`fetch_stock_data.py`、`prepare_ml_data.py`、`train_classifiers.py`、`plot_evaluation.py`、`validate_results.py`：A股截面分类的早期流程。

## 已停止使用的报告脚手架

- `generate_report.py`：早期 Word 生成器。
- `generate_course_stock_notebook.py`、`generate_feature_audit_notebook.py`：归档 Notebook 的生成器。

这些脚本保留用于追溯分析过程；正式提交只需要 `Rebecca+Task5.ipynb` 和 `Rebecca+Task5.pdf`。
