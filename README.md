# 量化交易：AI大模型辅助的金融交易策略

📈 北京大学光华管理学院商业分析工作坊（光华BA工作坊）课程项目。包含 8 个阶段性任务，从数据引擎搭建到策略路演，覆盖金融数据处理、技术指标构造、策略回测、机器学习预测与模拟实盘部署。

[![Tasks](https://img.shields.io/badge/tasks-8-blue)](https://github.com/RebekahLllimx/quant-trading-ai)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python)](https://www.python.org/)

---

## 📋 任务列表

| # | 官方名称 | 说明 | 状态 |
|---|---------|------|------|
| **1** | [量化交易初体验：从零搭建数据引擎](Task1/) | 获取A股+港股数据，K线可视化看板 | ✅ |
| **2** | [数据炼金术：数据诊断与构造交易指标](Task2/) | 8大技术指标计算与交互看板 | ✅ |
| **3** | 策略首秀：用均线交叉反映市场波动 | 移动平均线交叉 + 均值回归策略回测 | ⏳ |
| **4** | 复刻传奇：海龟交易法则实战演练 | 突破入场、ATR止损、分批止盈、仓位管理 | ⏳ |
| **5** | AI交易引擎：机器学习算法与场景应用 | 线性回归、决策树、KNN 训练与评估 | ⏳ |
| **6** | 智能决策者：用机器学习定制专属策略 | 特征工程 + 涨跌预测 + 策略回测对比 | ⏳ |
| **7** | 实战推演：策略实盘部署与交易实战 | JoinQuant 模拟交易 | ⏳ |
| **8** | 成果展示：专业报告撰写与策略路演 | 综合报告与路演材料 | ⏳ |

---

## 🏗 技术栈

| 领域 | 工具与库 |
|------|---------|
| **数据源** | AKShare（主力）、Tushare Pro（补充），均使用前复权(qfq) |
| **数据处理** | Python 3.10+, pandas, NumPy |
| **金融绘图** | mplfinance |
| **交互看板** | ECharts 5.5（自包含 HTML，无需后端） |
| **报告** | python-docx（宋体 10.5pt，1.5倍行距） |
| **部署** | GitHub Pages（静态文件） |

---

## 📂 目录结构

```
量化交易/
├── index.html                  ← Hub 导航页
├── README.md                   ← 本文件
├── skills.md                   ← 工作流 SOP
├── .gitignore
├── data/                       ← 共享数据
│   ├── csv/                    ←   10只标的 CSV（A股+港股）
│   └── charts/
│       ├── task1/              ←   K线图（20张）
│       └── task2/              ←   指标图（7张）
├── src/                        ← 共享模块
│   ├── indicators.py           ←   8个技术指标计算
│   └── report_utils.py         ←   docx 格式化辅助
├── Task1/
│   ├── Rebecca+Task1.docx
│   ├── dashboard/index.html    ←   K线看板
│   └── scripts/
├── Task2/
│   ├── spec.md                 ←   设计文档
│   ├── Rebecca+Task2.docx
│   ├── dashboard/index.html    ←   指标看板
│   └── scripts/
└── Task3/ ... Task8/           ← 待完成
```

---

## 🚀 快速开始

### 看板（无需安装）
```bash
# 方式A：从 Hub 页进入
open index.html

# 方式B：直接打开各任务看板
open Task1/dashboard/index.html   # K线看板
open Task2/dashboard/index.html   # 技术指标看板
```

### 更新数据
```bash
python Task2/scripts/update_data.py   # 拉取最新行情（AKShare）
```

### 生成报告
```bash
python TaskN/scripts/generate_report.py   # 输出 Rebecca+TaskN.docx
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

所有报告统一使用：宋体(SimSun) 五号(10.5pt)、1.5倍行距、0pt段间距、两端对齐。无封面，标题用 Normal 段落 + 字号区分（14pt Bold / 12pt Bold）。文件名格式：`Rebecca+TaskN.docx`。

---

*课程：北京大学光华管理学院商业分析工作坊（2026.6.28–7.22）*
