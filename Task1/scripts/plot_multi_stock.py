#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multiple Shanghai and ShenzhenAStock data acquisition, Visualization and Analysis
use Tushare Pro API, Covering the main board of Shanghai Stock Exchange, Shenzhen Stock Exchange Main Board, GEM and other different sectors
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import tushare as ts

# ==================== Configuration ====================
# From config.py Read Tushare Token (config.py Has been gitignore Exclude)
try:
    from config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = ""  # If not configured, use A-shareKShare

# Curated5Only represents different industries and sectors in Shanghai and Shenzhen.A-share
STOCKS = [
    {"code": "000001", "name": "Ping An Bank", "sector": "Bank Finance", "market": "Shenzhen Stock Exchange Main Board"},
    {"code": "600519", "name": "Kweichow Moutai", "sector": "liquor consumption", "market": "SSE Main Board"},
    {"code": "002594", "name": "BYD",   "sector": "New energy vehicles", "market": "Shenzhen Stock Exchange Main Board"},
    {"code": "601318", "name": "Ping An of China", "sector": "Insurance Finance", "market": "SSE Main Board"},
    {"code": "300750", "name": "CATL", "sector": "Battery energy storage", "market": "GEM"},
]

END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(OUTPUT_DIR, '..', '..', 'artifacts', 'charts', 'task1')
DATA_DIR  = os.path.join(OUTPUT_DIR, '..', '..', 'data', 'csv')
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
CHART_COMPARE = os.path.join(CHART_DIR, "multi_stock_compare.png")

# Chinese fonts
plt.rcParams['font.sans-serif'] = ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']


def fetch_stock_data(code):
    """Obtain stock adjusted daily data (AKShareforward-adjusted, TushareSpare) """
    # PlanA: AKShare forward-adjusted (Properly handling stock splits and dividend adjustments)
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code, period='daily',
                                start_date=START_DATE, end_date=END_DATE, adjust='qfq')
        if df is not None and len(df) > 0:
            df = df.rename(columns={
                'Date': 'trade_date', 'Opening': 'open', 'Close of trading': 'close',
                'highest': 'high', 'Minimum': 'low', 'Trading volume': 'vol', 'Turnover': 'amount',
                'Return': 'pct_chg', 'Price change': 'change', 'Turnover rate': 'turnover',
                'Symbol': 'ts_code', 'Amplitude': 'amplitude',
            })
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date').reset_index(drop=True)
            print(f"  Fetching... {code} (AKShareforward-adjusted)...", end=" ")
            print(f"{len(df)} records")
            return df
    except Exception as e:
        print(f"  AKShareFailure({str(e)[:50]}), FallbackTushare...", end=" ")

    # PlanB: Tushare Pro
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    if code.startswith(('6', '9')):
        ts_code = f"{code}.SH"
    else:
        ts_code = f"{code}.SZ"

    df = pro.daily(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
    df = df.sort_values('trade_date').reset_index(drop=True)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    print(f"{len(df)} records (Tushare)")
    return df


def normalize_price_series(df, base=100):
    """Normalize the closing price series to a baseline value. (For multi-strand contrast) """
    return df['close'] / df['close'].iloc[0] * base


def plot_multi_stock_comparison(stocks_data):
    """Multi-strand comparison chart: 4subgraph"""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Figure2: Multiple Shanghai and ShenzhenAComparison analysis of stock performance over the past year', fontsize=16, fontweight='bold', y=0.98)

    colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd']
    ax1, ax2, ax3, ax4 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    #  Subgraph1: Normalized Closing Price Comparison (All stocks from the same benchmark100Departure)
    for i, (s, df) in enumerate(stocks_data.items()):
        norm = normalize_price_series(df, base=100)
        ax1.plot(df['trade_date'], norm, color=colors[i], linewidth=1.4, label=f"{s}({list(df['ts_code'])[0][:6]})")
    ax1.axhline(y=100, color='gray', linestyle=':', alpha=0.5)
    ax1.set_title('(a) Normalized Closing Price Comparison (Benchmark=100) ', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Normalized Price', fontsize=11)
    ax1.legend(loc='upper left', fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    #  Subgraph2: Actual closing price trend
    for i, (s, df) in enumerate(stocks_data.items()):
        ax2.plot(df['trade_date'], df['close'], color=colors[i], linewidth=1.2, alpha=0.85, label=s)
    ax2.set_title('(b) Actual closing price trend', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Close (yuan) ', fontsize=11)
    ax2.legend(loc='upper right', fontsize=8, ncol=2)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    #  Subgraph3: Range rise and fall histogram
    stocks_names = []
    changes_pct = []
    bar_colors = []
    for i, (s, df) in enumerate(stocks_data.items()):
        stocks_names.append(s)
        chg = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100
        changes_pct.append(chg)
        bar_colors.append('#d62728' if chg < 0 else '#2ca02c')

    bars = ax3.barh(stocks_names[::-1], changes_pct[::-1], color=bar_colors[::-1], height=0.5, edgecolor='white')
    ax3.axvline(x=0, color='black', linewidth=0.8)
    ax3.set_title('(c) Range change rate (%) ', fontsize=13, fontweight='bold')
    ax3.set_xlabel('Return (%) ', fontsize=11)
    for bar, val in zip(bars, changes_pct[::-1]):
        ax3.text(bar.get_width() + (0.3 if val >= 0 else -0.3), bar.get_y() + bar.get_height()/2,
                 f'{val:+.1f}%', va='center', fontsize=10,
                 ha='left' if val >= 0 else 'right', fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='x')
    ax3.tick_params(axis='y', labelsize=10)

    #  Subgraph4: Volatility (Standard deviation) Comparison
    vol_stocks = []
    std_values = []
    for i, (s, df) in enumerate(stocks_data.items()):
        vol_stocks.append(s)
        # Standard deviation of daily returns (Annualized) = standard deviation of daily returns * sqrt(252)
        df_copy = df.copy()
        df_copy['return'] = df_copy['close'].pct_change()
        daily_std = df_copy['return'].std()
        annual_std = daily_std * (252 ** 0.5) * 100  # annualized volatility(%)
        std_values.append(annual_std)

    bars2 = ax4.barh(vol_stocks[::-1], std_values[::-1],
                     color=['#ff7f0e' if v > 30 else '#1f77b4' for v in std_values[::-1]],
                     height=0.5, edgecolor='white')
    ax4.set_title('(d) annualized volatility (%) ', fontsize=13, fontweight='bold')
    ax4.set_xlabel('annualized volatility (%) ', fontsize=11)
    for bar, val in zip(bars2, std_values[::-1]):
        ax4.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                 f'{val:.1f}%', va='center', fontsize=10, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='x')
    ax4.tick_params(axis='y', labelsize=10)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(CHART_COMPARE, dpi=150, bbox_inches='tight')
    print(f"\n[Drawing] Multi-strand comparison chart saved: {CHART_COMPARE}")
    plt.close()


def plot_individual_charts(stocks_data, stocks_info):
    """Plot separately for each stockKLine Diagram"""
    chart_paths = {}
    for s_name, df in stocks_data.items():
        info = stocks_info[s_name]

        fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'Figure: {s_name} ({info["code"]}) Daily chart trend over the past year',
                     fontsize=14, fontweight='bold')

        dates = df['trade_date']
        close_p = df['close']

        # up: Close + Moving average
        ax1 = axes[0]
        ax1.plot(dates, close_p, color='#1f77b4', linewidth=1.2, label='Close')
        if len(df) >= 20:
            ma20 = close_p.rolling(20).mean()
            ax1.plot(dates, ma20, color='#ff7f0e', linewidth=1.0, linestyle='--', alpha=0.8, label='MA20')
        if len(df) >= 60:
            ma60 = close_p.rolling(60).mean()
            ax1.plot(dates, ma60, color='#2ca02c', linewidth=1.0, linestyle='--', alpha=0.8, label='MA60')

        # High and Low Callout
        max_idx = close_p.idxmax()
        min_idx = close_p.idxmin()
        ax1.annotate(f'{close_p[max_idx]:.2f}', xy=(dates[max_idx], close_p[max_idx]),
                     fontsize=8, color='red', fontweight='bold', ha='center', va='bottom')
        ax1.annotate(f'{close_p[min_idx]:.2f}', xy=(dates[min_idx], close_p[min_idx]),
                     fontsize=8, color='green', fontweight='bold', ha='center', va='top')

        # Statistics Panel (Top right corner)
        chg_pct = (close_p.iloc[-1] - close_p.iloc[0]) / close_p.iloc[0] * 100
        stats = (f"Interval: {dates.iloc[0].strftime('%Y-%m-%d')} ~ {dates.iloc[-1].strftime('%Y-%m-%d')}\n"
                 f"Transaction Days: {len(df)}\n"
                 f"Beginning of Period: {close_p.iloc[0]:.2f}  End of term: {close_p.iloc[-1]:.2f}\n"
                 f"highest: {close_p.max():.2f}  Minimum: {close_p.min():.2f}\n"
                 f"Mean: {close_p.mean():.2f}  Standard deviation: {close_p.std():.2f}\n"
                 f"Return: {chg_pct:+.2f}%")
        props = dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.85)
        ax1.text(0.98, 0.98, stats, transform=ax1.transAxes, fontsize=8,
                 verticalalignment='top', horizontalalignment='right',
                 family='monospace', bbox=props)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.set_ylabel('Price (yuan) ', fontsize=11)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

        # down: Trading volume
        ax2 = axes[1]
        vol = df['vol'] / 10000  # Hand to hand
        colors_vol = ['#d62728' if df['close'].iloc[i] >= df['open'].iloc[i] else '#2ca02c'
                      for i in range(len(df))]
        ax2.bar(dates, vol, color=colors_vol, alpha=0.6, width=1)
        ax2.set_ylabel('Trading volume (Ten thousand hands) ', fontsize=11)
        ax2.set_xlabel('Date', fontsize=11)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

        chart_path = os.path.join(CHART_DIR, f"{info['code']}_{s_name}_chart.png")
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        chart_paths[s_name] = chart_path
        print(f"[Drawing] {s_name} Stock chart saved: {chart_path}")

    return chart_paths


def build_statistics_table(stocks_data, stocks_info):
    """Generate statistical summary DataFrame"""
    rows = []
    for s_name, df in stocks_data.items():
        info = stocks_info[s_name]
        close_p = df['close']
        chg = (close_p.iloc[-1] - close_p.iloc[0]) / close_p.iloc[0] * 100
        df_copy = df.copy()
        df_copy['ret'] = close_p.pct_change()
        daily_std = df_copy['ret'].std()
        annual_vol = daily_std * (252 ** 0.5) * 100
        max_dd = (close_p.cummax() - close_p).max() / close_p.cummax().max() * 100

        rows.append({
            'Name of Stock': s_name,
            'code': info['code'],
            'Industry': info['sector'],
            'plate': info['market'],
            'Number of trading days': len(df),
            'Opening Closing Price': f"{close_p.iloc[0]:.2f}",
            'Close at end of period': f"{close_p.iloc[-1]:.2f}",
            'highest interval': f"{close_p.max():.2f}",
            'interval lowest': f"{close_p.min():.2f}",
            'Range change rate(%)': f"{chg:+.2f}",
            'annualized volatility(%)': f"{annual_vol:.2f}",
            'Maximum Drawdown(%)': f"{max_dd:.2f}",
            'Average daily trading volume(Ten thousand hands)': f"{df['vol'].mean()/10000:,.0f}",
        })
    return pd.DataFrame(rows)


def save_csv_files(stocks_data, stocks_info):
    """Save each stock&#39;sCSV"""
    for s_name, df in stocks_data.items():
        info = stocks_info[s_name]
        csv_path = os.path.join(DATA_DIR, f"{info['code']}_{s_name}_daily.csv")
        df_out = df.copy()
        df_out['trade_date'] = df_out['trade_date'].dt.strftime('%Y-%m-%d')
        df_out.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"[CSV] {s_name} Data saved: {csv_path}")


# ==================== Main program ====================
if __name__ == "__main__":
    print("=" * 65)
    print("  Multiple Shanghai and ShenzhenABulk acquisition and analysis of historical stock trading data")
    print(f"  Time range: {START_DATE} ~ {END_DATE}")
    print("=" * 65)

    # 1. Get data in bulk
    stocks_data = {}
    stocks_info = {}
    print("\n>>> Steps1: Get data in bulk")
    for stock in STOCKS:
        code = stock["code"]
        name = stock["name"]
        stocks_info[name] = stock
        try:
            stocks_data[name] = fetch_stock_data(code)
        except Exception as e:
            print(f"  Failed to retrieve: {e}")

    print(f"\nSuccessfully obtained {len(stocks_data)}/{len(STOCKS)} Stock only data")

    # 2. SaveCSV
    print("\n>>> Steps2: SaveCSVFile")
    save_csv_files(stocks_data, stocks_info)

    # 3. Generate statistical summary table
    print("\n>>> Steps3: Statistical Summary")
    stats_df = build_statistics_table(stocks_data, stocks_info)
    stats_csv = os.path.join(DATA_DIR, "multi_stock_summary.csv")
    stats_df.to_csv(stats_csv, index=False, encoding='utf-8-sig')
    print(stats_df.to_string(index=False))
    print(f"\nStatistical summary saved: {stats_csv}")

    # 4. Draw a multi-strand comparison chart
    print("\n>>> Steps4: Draw a multi-strand comparison chart")
    plot_multi_stock_comparison(stocks_data)

    # 5. Drawing individual stock charts
    print("\n>>> Steps5: Plot a stock chart")
    individual_charts = plot_individual_charts(stocks_data, stocks_info)

    print("\n" + "=" * 65)
    print("  All completed! Symbiotic: ")
    print(f"   {len(stocks_data)} Only the stock CSV Data File")
    print(f"   {len(stocks_data)} Individual stock chart")
    print("   1 Zhang multi-strand comparison chart")
    print("   1 Statistical summary table")
    print("=" * 65)
