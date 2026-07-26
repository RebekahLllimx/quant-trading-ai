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
| **数据源** | AKShare（主力）、Tushare Pro（补充），均使用前复权(qfq) |
| **数据处理** | Python 3.10+, pandas, NumPy |
| **金融绘图** | mplfinance |
| **交互看板** | ECharts 5.5（自包含 HTML，无需后端） |
| **报告** | python-docx / Jupyter Notebook / XeLaTeX（宋体五号，1.5倍行距） |
| **部署** | GitHub Pages（静态文件） |

---

## 📂 目录结构

```
量化交易/
├── Task1/ ... Task8/           ← 稳定的任务入口：报告、Dashboard、spec与scripts
├── data/                       ← 原始、处理后数据与元数据
├── artifacts/
│   ├── charts/task1...task8/  ← 可重新生成的图表
│   └── models/task5...task6/  ← 已保存模型
├── output/submissions/         ← 八个Task正式PDF的项目级镜像
├── build/                      ← 本地构建、PDF渲染和QA中间文件（Git忽略）
├── docs/                       ← 协作、研究、写作和目录规范
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
python Task8/scripts/build_figures.py
python Task8/scripts/generate_report.py
```

### 复现TASK5分析
```bash
python Task5/scripts/cancer_case_analysis.py
jupyter nbconvert --to notebook --execute --inplace Task5/Rebecca+Task5.ipynb
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

课程报告统一使用宋体五号、1.5倍行距、0pt段间距和两端对齐。TASK5采用可执行Notebook作为可编辑母版，TASK8采用Word作为综合报告母版；提交前逐页检查图号、标题、解读和分页。完整语言要求见[`docs/report-writing-guidelines.md`](docs/report-writing-guidelines.md)。

---

*课程：北京大学光华管理学院商业分析工作坊（2026.6.28–7.22）*
