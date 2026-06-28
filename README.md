# AI Quantitative Trading Course — Homework Repository

📈 **`ai_quant_course_hw`** — Coursework repository for the AI Quantitative Strategy course (8 assignments), covering financial data engineering, quantitative strategy development, and AI-driven trading systems.

[![Tasks](https://img.shields.io/badge/tasks-8-blue)](https://github.com/RebekahLllimx/ai_quant_course_hw)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 📚 Assignments

| # | Task | Description | Status |
|---|------|-------------|--------|
| **1** | [Foundations & Data Dashboard](Task1/) | Quant trading fundamentals, Tushare data pipeline, K-line candlestick dashboard (A+H stocks) | ✅ Done |
| 2 | TBD | — | ⏳ |
| 3 | TBD | — | ⏳ |
| 4 | TBD | — | ⏳ |
| 5 | TBD | — | ⏳ |
| 6 | TBD | — | ⏳ |
| 7 | TBD | — | ⏳ |
| 8 | TBD | — | ⏳ |

---

## 🏗 Tech Stack

| Domain | Tools & Libraries |
|--------|-------------------|
| **Data Sources** | [AKShare](https://github.com/akfamily/akshare), [Tushare Pro](https://tushare.pro/) |
| **Data Processing** | Python 3.10+, pandas, NumPy |
| **Visualization** | ECharts 5.x, mplfinance, matplotlib |
| **Dashboard** | Flask REST API + standalone HTML (GitHub Pages) |
| **Reporting** | python-docx (Word documents) |
| **Deployment** | GitHub Pages |

---

## 📂 Repository Structure

```
ai_quant_course_hw/
├── README.md                    # ← You are here
├── Task1/                       # Foundations & Data Dashboard
│   ├── README.md                # Task 1 details
│   ├── Rebecca+Task1.docx       # Full report (Chinese)
│   ├── dashboard/               # Standalone dashboard (GitHub Pages)
│   │   ├── index.html           #   Static version with embedded data
│   │   ├── server.py            #   Flask backend for live fetching
│   │   └── requirements.txt     #   Python dependencies
│   ├── scripts/                 # Analysis scripts
│   │   ├── task3_stock_data.py
│   │   ├── multi_stock_analysis.py
│   │   └── candlestick_analysis.py
│   └── data/                    # CSV data + chart exports
├── Task2/                       # (upcoming)
├── Task3/                       # (upcoming)
...
└── Task8/                       # (upcoming)
```

---

## 🚀 Quick Start — Task 1 Dashboard

### Option A: Live Dashboard (local Python server)
```bash
cd Task1/dashboard
pip install -r requirements.txt
python server.py
# Open http://localhost:8765
```

### Option B: Standalone Dashboard (no installation)
Open [`Task1/dashboard/index.html`](Task1/dashboard/index.html) directly in any browser. Contains pre-loaded data for 10 stocks (5 A-shares + 5 HK stocks).

### Option C: GitHub Pages
Visit `https://rebekahlllimx.github.io/ai_quant_course_hw/` after deployment.

---

## 📊 Task 1 Highlights

- **Quantitative trading fundamentals**: Data-driven execution, backtesting, systematic risk control
- **K-line candlestick charts**: Interactive ECharts OHLC visualization with MA20/MA60 overlays
- **Cross-market analysis**: 5 A-shares (CSI) vs 5 HK stocks (HSI constituents)
- **10 metrics**: Return, annualized volatility, max drawdown, win rate, skewness, and more
- **Dual data sources**: AKShare (free) + Tushare Pro (token-gated, higher quality)
- **Forward-adjusted (qfq) prices**: Eliminates distortion from stock splits and dividends

---

## 🔑 Key Concepts Covered

1. **Quantitative vs Manual Trading**: Scalability, consistency, backtesting, automated risk control
2. **K-line (Candlestick)**: OHLC structure, bullish/bearish patterns, shadow interpretation
3. **Fundamental Analysis**: Macro → Industry → Company three-layer framework
4. **Technical Analysis**: Trend indicators (MA, MACD), oscillators (RSI, KDJ), chart patterns
5. **Data Pipeline**: API integration → pandas processing → visualization → CSV export
6. **Dashboard Engineering**: Flask REST API, ECharts interactive charts, input validation, responsive design

---

## 📝 Report

The complete Word report for Task 1 is available at [`Task1/Rebecca+Task1.docx`](Task1/Rebecca+Task1.docx), formatted in 宋体 (SimSun) 10.5pt with 1.5× line spacing, containing detailed analysis, charts with captions, and interpretations.

---

## 🤝 Academic Context

This repository is part of an AI Quantitative Strategy graduate-level course. The curriculum progresses from data foundations through strategy development to AI-powered trading models:

```
Task 1-2: Data Engineering & Visualization
Task 3-4: Factor Research & Alpha Discovery
Task 5-6: Strategy Backtesting & Risk Management
Task 7-8: ML/DL Models & Live Trading Systems
```

---

*Maintained by [@RebekahLllimx](https://github.com/RebekahLllimx)*
