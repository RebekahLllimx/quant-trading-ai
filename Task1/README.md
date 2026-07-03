# Task 1: 量化交易初体验 — 从零搭建数据引擎

## 📋 任务说明

1. 解释量化交易相较于传统手工操作交易的优势
2. 定义基本概念：K线、基本面分析、技术分析
3. 使用 AKShare/Tushare 获取A股+港股数据，绘制K线图，保存为CSV

## 📂 目录结构

```
Task1/
├── Rebecca+Task1.docx          # 完整报告（宋体/五号/1.5行距）
├── dashboard/
│   ├── index.html              # 自包含看板（GitHub Pages 兼容）
│   ├── server.py               # Flask 后端
│   └── requirements.txt        # Python 依赖
└── scripts/
    ├── update_data.py          # 单股数据获取 + 收盘价图 + CSV
    ├── plot_multi_stock.py     # 5只A股对比分析（mplfinance图表）
    ├── plot_candlestick.py     # A股+港股K线分析（mplfinance）
    ├── generate_report.py      # Word报告生成（python-docx）
    └── build_dashboard.py      # 看板HTML生成

数据文件: ../data/csv/*.csv
图表输出: ../data/charts/task1/*.png
```

## 🚀 使用

### 看板（无需后端）
```bash
open dashboard/index.html       # 双击打开即可
```

### Flask 后端（实时数据）
```bash
cd dashboard
pip install -r requirements.txt
python server.py                # http://localhost:8765
```

### 脚本
```bash
cd scripts
python update_data.py           # 单股数据分析
python plot_multi_stock.py  # 多股对比
python plot_candlestick.py  # A+H K线分析
```

## 📊 看板功能

- **10只标的**: 5只A股（沪深）+ 5只港股（恒生成分股）
- **交互K线**: ECharts 蜡烛图 + MA20/MA60 + 成交量
- **指标**: 收益率、年化波动率、最大回撤、胜率
- **分析**: 日收益分布直方图 + 累计收益曲线
- **导出**: 下载 OHLC 数据为 CSV

## 🛠 技术栈

| 层 | 技术 |
|---|------|
| 数据 | AKShare（主力）、Tushare Pro（补充），qfq 前复权 |
| 脚本图表 | mplfinance, matplotlib |
| 看板前端 | ECharts 5.x, vanilla JS |
| 看板后端 | Flask REST API |
| 报告 | python-docx |
| 部署 | GitHub Pages（静态HTML） |
