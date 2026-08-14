# 量化交易：AI大模型辅助的金融交易策略

📈 北京大学光华管理学院商业分析工作坊（光华BA工作坊）课程项目。包含8个阶段性任务，从数据引擎搭建到专业学习报告，覆盖金融数据处理、技术指标构造、策略回测、机器学习预测与模拟交易部署。

[![Tasks](https://img.shields.io/badge/tasks-8-blue)](https://github.com/RebekahLllimx/quant-trading-ai)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python)](https://www.python.org/)

---

## 📋 任务列表

| # | 官方名称 | 说明 | 状态 |
|---|---------|------|------|
| **1** | [量化交易初体验：从零搭建数据引擎](Task1/) | 获取A股+港股数据，K线可视化看板 | ✅ |
| **2** | [数据炼金术：数据诊断与构造交易指标](Task2/) | 8大技术指标计算与交互看板 | ✅ |
| **3** | [策略首秀：用均线交叉反映市场波动](Task3/) | 移动平均线交叉 + 均值回归策略回测 | ✅ |
| **4** | [复刻传奇：海龟交易法则实战演练](Task4/) | 突破入场、ATR止损、分批止盈、仓位管理 | ✅ |
| **5** | [AI交易引擎：机器学习算法与场景应用](Task5/) | 乳腺癌二分类、特征筛选、ROC/AUC与金融尝试反思 | ✅ |
| **6** | [智能决策者：用机器学习定制专属策略](Task6/) | 特征工程 + 涨跌预测 + 策略回测对比 | ✅ |
| **7** | [实战推演：策略实盘部署与交易实战](Task7/) | JoinQuant 三策略、参数检验、私有模拟盘与自动更新Dashboard | 🚧 |
| **8** | [成果展示：专业学习报告](Task8/) | 前七项任务综合分析、个人思考与研究展望 | ✅ |

---

## 🏗 技术栈

| 领域 | 工具与库 |
|------|---------|
| **数据源** | AKShare（主力）、Tushare Pro（补充），均使用前复权（qfq) |
| **数据处理** | Python 3.10+, pandas, NumPy |
| **金融绘图** | mplfinance |
| **交互看板** | ECharts 5.5（自包含 HTML，无需后端） |
| **报告** | 统一排版的最终PDF，集中收录于 `reports/` |
| **部署** | GitHub Pages（静态文件） |

---

## 📂 目录结构

```
量化交易/
├── Task1/ ... Task8/           ← 稳定的任务入口：说明、Dashboard与分析脚本
├── data/                       ← 原始、处理后数据与元数据
├── artifacts/
│   ├── charts/task1...task8/  ← 可重新生成的图表
│   └── models/task5...task6/  ← 已保存模型
├── reports/                    ← 八个Task的最终PDF
├── docs/                       ← 目录与文件组织说明
├── src/                        ← 跨任务共享模块
├── index.html                  ← GitHub Pages Hub
└── README.md
```

完整的目录职责和新Task模板见 [`docs/directory-structure.md`](docs/directory-structure.md)。

---

## 🚀 快速开始

### 看板（无需安装）
```bash
# 方式A：从 Hub 页进入
open index.html

# 方式B：直接打开各任务看板
open Task1/dashboard/index.html   # K线看板
open Task2/dashboard/index.html   # 技术指标看板
open Task3/dashboard/index.html   # 双均线交叉策略看板
open Task4/dashboard/index.html   # 海龟交易策略看板
open Task5/dashboard/index.html   # 机器学习模型评估看板
open Task6/dashboard/index.html   # 机器学习选股与择时看板
open Task7/dashboard/index.html   # 三策略部署与影子跟踪看板
```

### 更新数据
```bash
python Task2/scripts/update_data.py   # 拉取最新行情（AKShare）
python Task7/scripts/update_live_data.py --use-existing-on-error
python Task7/scripts/shadow_engine.py
python Task7/scripts/build_dashboard.py
python Task7/scripts/validate_results.py
```

### 复现TASK5分析
```bash
python Task5/scripts/cancer_case_analysis.py
python Task5/scripts/build_task5_dashboard.py
```

---

## 🔑 课程涵盖概念

1. **数据管道**：API 获取 → pandas 清洗 → CSV 存储 → 可视化
2. **技术指标**：RSI（Wilder平滑）、MACD、布林带、ATR、KDJ、MA、CCI、ADX
3. **均线策略**：多周期均线交叉与均值回归
4. **海龟交易**：突破入场、ATR 动态止损、仓位管理
5. **机器学习**：scikit-learn 训练、评估、特征重要性
6. **模拟实盘**：JoinQuant 平台、initialize/handle_data
7. **研究表达**：结构化报告、图表规范、结论审慎

---

## 📝 报告格式

八份最终报告统一收录于[`reports/`](reports/)。报告保留课程提交时的章节、图表、技术说明和结论，文件名按Task编号统一，便于从任务页或项目主页直接查阅。

- [TASK1](reports/Task1_Report.pdf)与[TASK2](reports/Task2_Report.pdf)记录数据引擎、数据质量和八类技术指标。
- [TASK3](reports/Task3_Report.pdf)与[TASK4](reports/Task4_Report.pdf)比较双均线和海龟策略的信号、收益、回撤及参数敏感性。
- [TASK5](reports/Task5_Report.pdf)与[TASK6](reports/Task6_Report.pdf)覆盖分类模型、时间划分、特征选择、模型评价和策略回测。
- [TASK7](reports/Task7_Report.pdf)记录JoinQuant回测、模拟部署与风险暴露；[TASK8](reports/Task8_Report.pdf)汇总前七项任务的方法、发现和局限。

---

*课程：北京大学光华管理学院商业分析工作坊（2026.6.28–7.22）*
