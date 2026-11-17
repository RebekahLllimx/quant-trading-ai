#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AComparison and Analysis of Character Stocks Between A-Shares and Hong Kong Stocks  -  -  KLine Diagram (Candlestick chart) + multi-dimensional contrast
use mplfinance Drawing StandardsKLine Diagram, Covering Shanghai and ShenzhenA-shares and Hong Kong equities
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ==================== Configuration ====================
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(OUTPUT_DIR, '..', '..', 'artifacts', 'charts', 'task1')
DATA_DIR  = os.path.join(OUTPUT_DIR, '..', '..', 'data', 'csv')
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

# A-share (Shanghai and Shenzhen)
A_STOCKS = [
    {"code": "000001", "name": "Ping An Bank", "sector": "Bank Finance", "market": "Shenzhen Stock Exchange Main Board"},
    {"code": "600519", "name": "Kweichow Moutai", "sector": "liquor consumption", "market": "SSE Main Board"},
    {"code": "002594", "name": "BYD",   "sector": "New energy vehicles", "market": "Shenzhen Stock Exchange Main Board"},
    {"code": "601318", "name": "Ping An of China", "sector": "Insurance Finance", "market": "SSE Main Board"},
    {"code": "300750", "name": "CATL", "sector": "Battery energy storage", "market": "GEM"},
]

# Hong Kong equities (Hong Kong Stock Exchange)
HK_STOCKS = [
    {"code": "00700", "name": "Tencent Holdings",   "sector": "Internet technology", "market": "Hang Seng Index constituents"},
    {"code": "09988", "name": "Alibaba",   "sector": "E-commerce Cloud Computing", "market": "Hang Seng Index constituents"},
    {"code": "03690", "name": "Meituan",       "sector": "Local Life",   "market": "Hang Seng Index constituents"},
    {"code": "00388", "name": "Hong Kong Exchange", "sector": "Financial Infrastructure", "market": "Hang Seng Index constituents"},
    {"code": "00941", "name": "China Mobile",   "sector": "Telecommunications Operations",   "market": "Hang Seng Index constituents"},
]

# Chinese fonts
plt.rcParams['font.sans-serif'] = ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']

# ==================== Data Acquisition ====================

def fetch_a_stock(code):
    """GetAPre-stock recovery daily data"""
    import akshare as ak
    df = ak.stock_zh_a_hist(symbol=code, period='daily',
                            start_date=START_DATE, end_date=END_DATE, adjust='qfq')
    df = df.rename(columns={
        'Date': 'Date', 'Opening': 'Open', 'Close of trading': 'Close',
        'highest': 'High', 'Minimum': 'Low', 'Trading volume': 'Volume',
        'Turnover': 'Amount', 'Return': 'PctChg', 'Turnover rate': 'Turnover',
    })
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


def fetch_hk_stock(code):
    """Obtain Hong Kong equity adjusted daily data"""
    import akshare as ak
    df = ak.stock_hk_hist(symbol=code, period='daily',
                          start_date=START_DATE, end_date=END_DATE, adjust='qfq')
    df = df.rename(columns={
        'Date': 'Date', 'Opening': 'Open', 'Close of trading': 'Close',
        'highest': 'High', 'Minimum': 'Low', 'Trading volume': 'Volume',
        'Turnover': 'Amount', 'Return': 'PctChg',
    })
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


# ==================== Kline graph drawing (mplfinance) ====================

def plot_candlestick(df, title, save_path, stock_info, show_ma=True):
    """use mplfinance Drawing StandardsKLine Candle Chart + Trading volume"""
    # Prepare data: mplfinance need Date, Open, High, Low, Close, Volume column
    ohlc_df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    ohlc_df = ohlc_df.set_index('Date')
    # Volume Unit Conversion (AHands.->million shares, Hong Kong equity->million shares)
    ohlc_df['Volume'] = ohlc_df['Volume'] / 10000

    # Calculate moving average
    if show_ma:
        ma20 = ohlc_df['Close'].rolling(20).mean()
        ma60 = ohlc_df['Close'].rolling(60).mean()

    # Custom color scheme: Red rises, green falls (A-share habit)
    mc = mpf.make_marketcolors(
        up='red', down='green',
        edge='inherit', wick='inherit',
        volume={'up': 'red', 'down': 'green'},
        alpha=0.85
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle='--', gridaxis='both',
        facecolor='white', figcolor='white',
        y_on_right=False,
        rc={
            'font.sans-serif': ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif'],
            'font.monospace': ['Heiti SC', 'STHeiti', 'sans-serif'],
            'axes.unicode_minus': False,
        }
    )

    # Building a moving average overlay
    add_plots = []
    if show_ma and len(df) >= 20:
        add_plots.append(mpf.make_addplot(ma20, color='#ff7f0e', width=1.0, linestyle='--', label='MA20'))
    if show_ma and len(df) >= 60:
        add_plots.append(mpf.make_addplot(ma60, color='#2ca02c', width=1.0, linestyle='--', label='MA60'))

    # BuildKLine Diagram
    chg = (ohlc_df['Close'].iloc[-1] - ohlc_df['Close'].iloc[0]) / ohlc_df['Close'].iloc[0] * 100
    subtitle = f"{stock_info['market']} | {stock_info['sector']} | Return: {chg:+.2f}%"

    fig, axes = mpf.plot(
        ohlc_df,
        type='candle',          # Candlestick chart
        style=s,
        addplot=add_plots if add_plots else None,
        volume=True,            # Volume Sub-Chart
        title=title,
        ylabel='Price',
        ylabel_lower='Trading volume(million shares)',
        figsize=(16, 9),
        panel_ratios=(3, 1),    # Main image:Trading volume = 3:1
        returnfig=True,
        datetime_format='%Y-%m',
        xrotation=30,
        show_nontrading=False,
        warn_too_much_data=300,
    )

    # Add Subtitle (Statistical Information)
    ax_main = axes[0]
    close = ohlc_df['Close']
    stats_lines = [
        f"{subtitle}",
        f"Beginning of Period: {close.iloc[0]:.2f}  ->  End of term: {close.iloc[-1]:.2f}",
        f"highest: {close.max():.2f}  Minimum: {close.min():.2f}",
        f"Mean: {close.mean():.2f}  Standard deviation: {close.std():.2f}",
        f"Interval Days: {len(ohlc_df)} Trading day",
    ]
    stats_text = "\n".join(stats_lines)
    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.9)
    ax_main.text(0.98, 0.98, stats_text, transform=ax_main.transAxes,
                 fontsize=9, verticalalignment='top', horizontalalignment='right',
                 family='monospace', bbox=props)

    # Legend
    if add_plots:
        legend_labels = ['MA20', 'MA60'] if len(add_plots) == 2 else ['MA20']
        ax_main.legend(legend_labels, loc='upper left', fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [KLine Diagram] Saved: {os.path.basename(save_path)}")


def plot_candlestick_recent(df, title, save_path, months=3):
    """Draw nearNmonths ofKLine Diagram (Zoom in on details) """
    cutoff = df['Date'].max() - pd.DateOffset(months=months)
    df_recent = df[df['Date'] >= cutoff].copy()
    if len(df_recent) < 20:
        df_recent = df.tail(60).copy()

    ohlc_df = df_recent[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    ohlc_df = ohlc_df.set_index('Date')
    ohlc_df['Volume'] = ohlc_df['Volume'] / 10000

    mc = mpf.make_marketcolors(
        up='red', down='green', edge='inherit', wick='inherit',
        volume={'up': 'red', 'down': 'green'}, alpha=0.85)
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', gridaxis='both',
                           facecolor='white', figcolor='white', y_on_right=False,
                           rc={'font.sans-serif': ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif'],
                               'font.monospace': ['Heiti SC', 'STHeiti', 'sans-serif'],
                               'axes.unicode_minus': False})

    ma10 = ohlc_df['Close'].rolling(10).mean()
    ma30 = ohlc_df['Close'].rolling(30).mean()
    add_plots = [
        mpf.make_addplot(ma10, color='#ff7f0e', width=1.2, linestyle='--', label='MA10'),
        mpf.make_addplot(ma30, color='#2ca02c', width=1.2, linestyle='--', label='MA30'),
    ]

    fig, axes = mpf.plot(
        ohlc_df, type='candle', style=s, addplot=add_plots,
        volume=True, title=title, ylabel='Price', ylabel_lower='Trading volume(million shares)',
        figsize=(16, 9), panel_ratios=(3, 1), returnfig=True,
        datetime_format='%m-%d', xrotation=30, show_nontrading=False,
        warn_too_much_data=300,
    )
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [KLine Diagram-Recently] Saved: {os.path.basename(save_path)}")


# ==================== Comprehensive Comparison Chart ====================

def plot_ah_comparison(a_data, hk_data):
    """A-share vs Hong Kong equities Comprehensive Comparison Large Chart (4subgraph) """
    fig, axes = plt.subplots(2, 2, figsize=(20, 13))
    fig.suptitle('Figure2: AComprehensive comparative analysis of representative A-shares and Hong Kong equities.', fontsize=18, fontweight='bold', y=0.99)

    colors_a = ['#d62728', '#c49c48', '#2ca02c', '#1f77b4', '#ff7f0e']
    colors_hk = ['#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']

    ax1, ax2, ax3, ax4 = axes[0,0], axes[0,1], axes[1,0], axes[1,1]

    #  Subgraph1: ANormalized closing price of the stock
    for i, (name, df) in enumerate(a_data.items()):
        norm = df['Close'] / df['Close'].iloc[0] * 100
        ax1.plot(df['Date'], norm, color=colors_a[i], linewidth=1.4, label=name)
    ax1.axhline(y=100, color='gray', linestyle=':', alpha=0.4)
    ax1.set_title('(a) ANormalized closing price of the stock (Benchmark=100) ', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8, ncol=2)
    ax1.set_ylabel('Normalized Price', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    #  Subgraph2: Normalized closing price of Hong Kong equities
    for i, (name, df) in enumerate(hk_data.items()):
        norm = df['Close'] / df['Close'].iloc[0] * 100
        ax2.plot(df['Date'], norm, color=colors_hk[i], linewidth=1.4, label=name)
    ax2.axhline(y=100, color='gray', linestyle=':', alpha=0.4)
    ax2.set_title('(b) Normalized closing price of Hong Kong equities (Benchmark=100) ', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=8, ncol=2)
    ax2.set_ylabel('Normalized Price', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    #  Subgraph3: Gain/Loss Comparison
    all_names = []
    all_chg = []
    all_colors = []
    all_markets = []
    for name, df in a_data.items():
        chg = (df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100
        all_names.append(f"{name} (A)")
        all_chg.append(chg)
        all_colors.append('#d62728' if chg < 0 else '#2ca02c')
        all_markets.append('A-share')
    for name, df in hk_data.items():
        chg = (df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100
        all_names.append(f"{name} (HK)")
        all_chg.append(chg)
        all_colors.append('#e377c2' if chg < 0 else '#2ca02c')
        all_markets.append('Hong Kong equities')

    bars = ax3.barh(all_names[::-1], all_chg[::-1], color=all_colors[::-1],
                    height=0.55, edgecolor='white')
    ax3.axvline(x=0, color='black', linewidth=0.8)
    ax3.set_title('(c) Range change rate (%) ', fontsize=14, fontweight='bold')
    for bar, val in zip(bars, all_chg[::-1]):
        offset = 0.3 if val >= 0 else -0.3
        ha = 'left' if val >= 0 else 'right'
        ax3.text(bar.get_width() + offset, bar.get_y() + bar.get_height()/2,
                 f'{val:+.1f}%', va='center', fontsize=9, ha=ha, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='x')

    #  Subgraph4: A-share vs Hong Kong equities Average Performance Comparison (Box type: Price fluctuation range)
    a_chg_list = []
    hk_chg_list = []
    for name, df in a_data.items():
        a_chg_list.append((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100)
    for name, df in hk_data.items():
        hk_chg_list.append((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100)

    ax4.bar([0.6, 1.6], [np.mean(a_chg_list), np.mean(hk_chg_list)],
            width=0.5, color=['#d62728', '#9467bd'], edgecolor='white',
            yerr=[np.std(a_chg_list), np.std(hk_chg_list)],
            capsize=10, error_kw={'linewidth': 2})
    # Scatter overlay
    for v in a_chg_list:
        ax4.scatter(0.6 + np.random.uniform(-0.15, 0.15), v, color='#d62728', s=60, alpha=0.7, zorder=5)
    for v in hk_chg_list:
        ax4.scatter(1.6 + np.random.uniform(-0.15, 0.15), v, color='#9467bd', s=60, alpha=0.7, zorder=5)
    ax4.axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    ax4.set_xticks([0.6, 1.6])
    ax4.set_xticklabels(['A-share sample\n(5only)', 'Hong Kong equity sample\n(5only)'], fontsize=11)
    ax4.set_title('(d) Average price changeStandard Deviation Comparison', fontsize=14, fontweight='bold')
    ax4.set_ylabel('Range change rate (%) ', fontsize=11)
    ax4.grid(True, alpha=0.3, axis='y')
    # Labeling mean
    ax4.text(0.6, np.mean(a_chg_list) + 1, f'AShare mean:\n{np.mean(a_chg_list):+.1f}%',
             ha='center', fontsize=10, fontweight='bold', color='#d62728')
    ax4.text(1.6, np.mean(hk_chg_list) + 1, f'Average of Hong Kong equities:\n{np.mean(hk_chg_list):+.1f}%',
             ha='center', fontsize=10, fontweight='bold', color='#9467bd')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    save_path = os.path.join(CHART_DIR, "AH_comparison.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n[Comparison chart] A-sharevsHong Kong equity saved: AH_comparison.png")
    return a_chg_list, hk_chg_list


# ==================== CSRC Statistical Summary ====================

def build_summary(a_data, hk_data):
    """BuildA-share+Hong Kong Stock Market Summary Table"""
    rows = []
    for name, df in a_data.items():
        close = df['Close']
        chg = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
        ret = close.pct_change()
        ann_vol = ret.std() * np.sqrt(252) * 100
        max_dd = ((close.cummax() - close) / close.cummax()).max() * 100
        rows.append({
            'Market': 'A-share', 'Name': name, 'Trading day': len(df),
            'Beginning of Period': close.iloc[0], 'End of term': close.iloc[-1],
            'highest': close.max(), 'Minimum': close.min(),
            'Return(%)': round(chg, 2), 'Annualized volatility(%)': round(ann_vol, 2),
            'Maximum Drawdown(%)': round(max_dd, 2),
        })
    for name, df in hk_data.items():
        close = df['Close']
        chg = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
        ret = close.pct_change()
        ann_vol = ret.std() * np.sqrt(252) * 100
        max_dd = ((close.cummax() - close) / close.cummax()).max() * 100
        rows.append({
            'Market': 'Hong Kong equities', 'Name': name, 'Trading day': len(df),
            'Beginning of Period': close.iloc[0], 'End of term': close.iloc[-1],
            'highest': close.max(), 'Minimum': close.min(),
            'Return(%)': round(chg, 2), 'Annualized volatility(%)': round(ann_vol, 2),
            'Maximum Drawdown(%)': round(max_dd, 2),
        })
    return pd.DataFrame(rows)


# ==================== Main program ====================

if __name__ == "__main__":
    print("=" * 65)
    print("  A-share vs Hong Kong equities Representative stock of personalityKline graph analysis and comparison")
    print(f"  Time range: {START_DATE} ~ {END_DATE}")
    print("=" * 65)

    #  Steps1: Get data
    print("\n>>> Steps1: Batch AcquisitionA-share data...")
    a_data = {}
    for s in A_STOCKS:
        try:
            a_data[s['name']] = fetch_a_stock(s['code'])
            print(f"  A-share {s['name']}({s['code']}): {len(a_data[s['name']])} item")
        except Exception as e:
            print(f"  A-share {s['name']} Failed to retrieve: {e}")

    print("\n>>> Steps2: Obtain Hong Kong Stock Data in Batch...")
    hk_data = {}
    for s in HK_STOCKS:
        try:
            hk_data[s['name']] = fetch_hk_stock(s['code'])
            print(f"  Hong Kong equities {s['name']}({s['code']}): {len(hk_data[s['name']])} item")
        except Exception as e:
            print(f"  Hong Kong equities {s['name']} Failed to retrieve: {e}")

    #  Steps3: DrawA-shareKLine Candle Chart
    print("\n>>> Steps3: DrawA-shareKLine Candle Chart (mplfinance)...")
    for s in A_STOCKS:
        name = s['name']
        if name not in a_data:
            continue
        print(f"  Drawing {name}...")
        df = a_data[name]
        # Year-roundKLine Diagram
        title = f"{name} ({s['code']}) Day of the past yearKLine Diagram"
        save_path = os.path.join(CHART_DIR, f"{s['code']}_{name}_candle.png")
        plot_candlestick(df, title, save_path, s)

    #  Steps4: Plotting Hong Kong StocksKLine Candle Chart
    print("\n>>> Steps4: Plotting Hong Kong StocksKLine Candle Chart (mplfinance)...")
    for s in HK_STOCKS:
        name = s['name']
        if name not in hk_data:
            continue
        print(f"  Drawing {name}...")
        df = hk_data[name]
        title = f"{name} ({s['code']}.HK) Day of the past yearKLine Diagram"
        save_path = os.path.join(CHART_DIR, f"{s['code']}_{name}_candle.png")
        plot_candlestick(df, title, save_path, s)

    #  Steps5: Select two representative stocks to draw recent trendsKLine Detail
    print("\n>>> Steps5: Plotting RecentKClose-up of thread details...")
    # AUnit Representative: CATL
    if 'CATL' in a_data:
        df = a_data['CATL']
        title = 'CATL (300750) near3Month DayKLine Diagram'
        save_path = os.path.join(CHART_DIR, "300750_CATL_recent_candle.png")
        plot_candlestick_recent(df, title, save_path, months=3)
    # Hong Kong Stock Representative: Tencent Holdings
    if 'Tencent Holdings' in hk_data:
        df = hk_data['Tencent Holdings']
        title = 'Tencent Holdings (00700.HK) near3Month DayKLine Diagram'
        save_path = os.path.join(CHART_DIR, "00700_Tencent Holdings_recent_candle.png")
        plot_candlestick_recent(df, title, save_path, months=3)

    #  Steps6: A-sharevsComprehensive comparison of Hong Kong equities
    print("\n>>> Steps6: DrawA-sharevsHong Kong Stock Comprehensive Comparison Chart...")
    a_chgs, hk_chgs = plot_ah_comparison(a_data, hk_data)

    #  Steps7: Statistical Summary
    print("\n>>> Steps7: Generate statistical summary table...")
    summary = build_summary(a_data, hk_data)
    summary_path = os.path.join(DATA_DIR, "AH_summary.csv")
    summary.to_csv(summary_path, index=False, encoding='utf-8-sig')
    print(summary.to_string(index=False))
    print(f"\nStatistical summary saved: AH_summary.csv")

    #  Steps8: SaveCSV
    print("\n>>> Steps8: Save all stocksCSV...")
    all_stocks = [(A_STOCKS, a_data, 'A-share'), (HK_STOCKS, hk_data, 'Hong Kong equities')]
    for stock_list, data_dict, mkt in all_stocks:
        for s in stock_list:
            name = s['name']
            if name in data_dict:
                df_out = data_dict[name].copy()
                df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')
                csv_path = os.path.join(DATA_DIR, f"{s['code']}_{name}_{mkt}_daily.csv")
                df_out.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"  [{mkt}stock] {name}  ->  {os.path.basename(csv_path)}")

    print("\n" + "=" * 65)
    print(f"  All completed! ")
    print(f"  A-share {len(a_data)} only + Hong Kong equities {len(hk_data)} only, total {len(a_data)+len(hk_data)} Only stock")
    print(f"   10 ZhangKLine Candle Chart (Contains2Zhang Recent Details Enlarged) ")
    print(f"   1 ZhangA-sharevsHong Kong Stock Comprehensive Comparison Chart")
    print(f"   1 Statistical summary table + 10 Share of individual stocksCSV")
    print("=" * 65)
