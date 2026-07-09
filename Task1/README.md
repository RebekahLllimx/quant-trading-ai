# 量化交易初体验 — 从零搭建 A 股+港股数据引擎

> **核心交付**：一条自动化数据管线，从 API 拉取 → pandas 清洗 → CSV 存储 → K 线可视化 → 自包含交互看板。覆盖 10 只标的（5 A 股 + 5 港股），后续 Task2-8 的所有策略回测和指标计算都依赖本 Task 搭建的数据基础。

---

## 📖 Overview（项目概述）

- **项目类型**：数据管线（Data Pipeline）+ 可视化看板
- **解决的问题**：量化交易的第一步——"数据从哪来、怎么存、怎么看"
- **核心能力**：AKShare API → pandas 清洗 → mplfinance K 线图 → ECharts 交互看板

---

## 🏗 Architecture（数据架构）

```
AKShare API (主力) / Tushare Pro (补充)
        │
        ▼
  update_data.py          ← 数据获取（前复权 qfq）+ 收盘价图
        │
        ├──► data/csv/{code}_{name}_{market}_daily.csv   ← 10 只标的
        │
        ▼
  plot_candlestick.py     ← K 线图（mplfinance）
  plot_multi_stock.py     ← 5 只 A 股对比分析
        │
        ▼
  build_dashboard.py      ← CSV → JSON → 自包含 HTML
        │
        ▼
  dashboard/index.html    ← 交互看板（ECharts 5.5，无需服务器）
```

### 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据源 | AKShare 主力 + Tushare 补充 | AKShare 免费无限制、无需注册 |
| 复权方式 | 前复权 (qfq) | 当前价格真实，历史价格向后调整，适合技术分析 |
| 看板架构 | 自包含 HTML（CSV→JSON→内嵌） | 无需后端服务器，GitHub Pages 直接部署 |
| CSV 编码 | utf-8-sig | Excel 直接打开不乱码 |
| 绘图库 | mplfinance | 专业金融 K 线图，中文兼容，多面板支持 |

---

## 📊 Dashboard（交互看板）

- **10 只标的**：5 只 A 股 + 5 只港股，侧边栏分组展示，点击切换
- **K 线图**：含 MA5/MA10/MA20 均线 + 成交量柱状图，支持缩放拖拽
- **数据分析**：日收益直方图 + 正态拟合曲线 + 累计收益曲线
- **数据下载**：一键下载当前标的 OHLC 数据为 CSV
- **部署**：GitHub Pages 静态文件，双击 `.html` 即可本地打开

---

## 📈 标的覆盖

| 市场 | 代码 | 名称 | 选取逻辑 |
|------|------|------|---------|
| A 股 | 000001 | 平安银行 | 金融蓝筹 |
| A 股 | 002594 | 比亚迪 | 新能源龙头 |
| A 股 | 300750 | 宁德时代 | 创业板权重 |
| A 股 | 600519 | 贵州茅台 | 消费标杆 |
| A 股 | 601318 | 中国平安 | 保险龙头 |
| 港股 | 00388 | 香港交易所 | 交易所稀缺标的 |
| 港股 | 00700 | 腾讯控股 | 互联网巨头 |
| 港股 | 00941 | 中国移动 | 电信蓝筹 |
| 港股 | 03690 | 美团 | 新经济代表 |
| 港股 | 09988 | 阿里巴巴 | 电商巨头 |

选取原则：行业分散、市值靠前、流动性充足、AH 各有代表性。

---

## 💡 Key Findings（关键收获）

1. **前复权是数据管线的基础决策**：不复权时，分红除权产生的跳空缺口会被技术指标误判为趋势转折。前复权以当前股本为基准向后调整历史价格，保证了所有后续 Task 中技术分析和回测的正确性。
2. **自包含 HTML 架构降低了展示门槛**：无需安装依赖、无需启动服务器，双击 `.html` 即可查看完整看板。GitHub Pages 部署后任何人可访问——这对课程作品集展示非常关键。
3. **AKShare 作为主力数据源足够可靠**：覆盖 A 股和港股日线数据，免费无频率限制。唯一局限是部分港股历史数据长度有限（约 2–3 年）。

---

## 🔗 相关文件

- 完整报告：[Rebecca+Task1.docx](Rebecca+Task1.docx)
- 交互看板：[dashboard/index.html](dashboard/index.html)
- 数据获取：[scripts/update_data.py](scripts/update_data.py)
- K 线图：[scripts/plot_candlestick.py](scripts/plot_candlestick.py)
