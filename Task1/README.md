# Task 1: Quantitative Trading Foundations & Data Dashboard

## 📋 Tasks

1. **Explain the advantages of quantitative trading** over traditional manual trading
2. **Define basic concepts**: K-line (candlestick), fundamental analysis, technical analysis
3. **Register on Tushare Pro**, obtain an API token, and use Python to:
   - Fetch one year of daily trading data for a CSI stock
   - Plot the daily closing price chart
   - Save data as CSV

## 📂 Structure

```
Task1/
├── Rebecca+Task1.docx          # Full report (Chinese, 宋体/五号/1.5行距)
├── dashboard/
│   ├── index.html              # Standalone dashboard (GitHub Pages compatible)
│   ├── server.py               # Flask backend for live data fetching
│   └── requirements.txt        # Python dependencies
├── scripts/
│   ├── task3_stock_data.py     # Basic single-stock fetch + plot + CSV
│   ├── multi_stock_analysis.py # 5 A-stock comparison (mplfinance charts)
│   ├── candlestick_analysis.py # A+H K-line analysis with mplfinance
│   ├── generate_report.py      # Word report generator (python-docx)
│   └── build_dashboard.py      # Dashboard HTML generator
└── data/
    ├── AH_summary.csv          # Summary statistics for 10 stocks
    ├── multi_stock_summary.csv # 5 A-stock summary
    ├── _embedded_data.json     # Embedded OHLC data for standalone dashboard
    ├── *_daily.csv             # Individual stock daily data (10 files)
    └── charts/                 # PNG chart exports
```

## 🚀 Usage

### Live Dashboard (local)
```bash
cd dashboard
pip install -r requirements.txt
python server.py
# Open http://localhost:8765
```

### Standalone Dashboard (no backend)
Open `dashboard/index.html` directly in a browser. Contains embedded data for 10 stocks.

### Scripts
```bash
cd scripts
python task3_stock_data.py      # Single A-stock analysis
python multi_stock_analysis.py  # 5 A-stock comparison
python candlestick_analysis.py  # A+H K-line analysis
```

## 📊 Dashboard Features

- **10 stocks**: 5 A-shares (CSI) + 5 HK stocks (HSI constituents)
- **Interactive K-line**: ECharts candlestick chart with MA20/MA60 + volume
- **Metrics**: Return, annualized volatility, max drawdown, win rate
- **Analysis**: Daily return distribution histogram + cumulative return curve
- **Export**: Download OHLC data as CSV
- **Input validation**: Auto-detects market/code mismatches

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Data | AKShare (primary), Tushare Pro (secondary) |
| Charts (scripts) | mplfinance, matplotlib |
| Dashboard frontend | ECharts 5.x, vanilla JS |
| Dashboard backend | Flask REST API |
| Report | python-docx |
| Deployment | GitHub Pages (standalone HTML) |

## 📈 Sample Stocks

| Market | Code | Name | Sector | Return |
|--------|------|------|--------|--------|
| A股 | 000001 | 平安银行 | Banking | -10.81% |
| A股 | 600519 | 贵州茅台 | Liquor | -13.92% |
| A股 | 002594 | 比亚迪 | EV | -28.46% |
| A股 | 300750 | 宁德时代 | Battery | +55.95% |
| A股 | 601318 | 中国平安 | Insurance | -10.52% |
| 港股 | 00700 | 腾讯控股 | Internet | -17.26% |
| 港股 | 09988 | 阿里巴巴 | E-commerce | -17.72% |
| 港股 | 03690 | 美团 | Local Services | -48.72% |
| 港股 | 00388 | 香港交易所 | Exchange | -10.85% |
| 港股 | 00941 | 中国移动 | Telecom | -5.41% |
