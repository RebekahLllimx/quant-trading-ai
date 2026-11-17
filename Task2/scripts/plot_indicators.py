#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3: Visualization of technical indicators (mplfinance)
Kweichow Moutai (600519) Main display target, Draw comprehensive index map + Parameter Comparison Chart
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import mplfinance as mpf

# Add scripts To Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import (
    calc_all_indicators, calc_rsi, calc_macd, calc_bollinger,
    calc_atr, calc_kdj, calc_ma, calc_cci, calc_adx,
    data_diagnosis, print_diagnosis,
)

#
# Configuration
#

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
CHART_DIR = os.path.join(BASE_DIR, '..', 'artifacts', 'charts', 'task2')
os.makedirs(CHART_DIR, exist_ok=True)

# Chinese fonts
plt.rcParams['font.sans-serif'] = [
    'Heiti SC', 'STHeiti', 'PingFang SC',
    'Arial Unicode MS', 'SimHei', 'sans-serif'
]
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']

# mplfinance style
MC = mpf.make_marketcolors(
    up='red', down='green', edge='inherit', wick='inherit',
    volume={'up': 'red', 'down': 'green'}, alpha=0.85
)
STYLE = mpf.make_mpf_style(
    marketcolors=MC, gridstyle='--', gridaxis='both',
    facecolor='white', figcolor='white', y_on_right=False,
    rc={
        'font.sans-serif': ['Heiti SC', 'STHeiti', 'PingFang SC',
                            'Arial Unicode MS', 'SimHei', 'sans-serif'],
        'font.monospace': ['Heiti SC', 'STHeiti', 'sans-serif'],
        'axes.unicode_minus': False,
    }
)


def load_stock(code, name, market):
    """Load Stock CSV Data"""
    filename = f"{code}_{name}_{market}_daily.csv"
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file does not exist: {filepath}")
    df = pd.read_csv(filepath, encoding='utf-8-sig')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


def prepare_ohlc(df):
    """Prepare mplfinance Needed OHLCV DataFrame"""
    ohlc = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    ohlc = ohlc.set_index('Date')
    ohlc['Volume'] = ohlc['Volume'].astype(float)
    # turnover to tens of thousands of shares
    ohlc['Volume'] = ohlc['Volume'] / 10000
    return ohlc


#
# Figure1: Comprehensive index overview (Kline + Bollinger Bands + Trading volume + RSI + MACD + KDJ)
#

def plot_comprehensive(df, stock_info, save_path):
    """
    Comprehensive indicator chart: Kline(Bollinger Bands) + Trading volume + RSI + MACD + KDJ
    6 Panel (mplfinance panel_ratios)
    """
    ohlc = prepare_ohlc(df)

    # Calculate all indicators
    ind = calc_all_indicators(df)
    ind['Date'] = df['Date']
    ind = ind.set_index('Date')

    # Build add_plots
    add_plots = []

    # Panel 0 (Main image): Bollinger Bands three rails
    add_plots.append(mpf.make_addplot(
        ind['BB_UP'], color='#7f7f7f', width=0.8, linestyle='--', panel=0, label='On track'
    ))
    add_plots.append(mpf.make_addplot(
        ind['BB_MID'], color='#ff7f0e', width=1.0, linestyle='-', panel=0, label='Middle rail(MA20)'
    ))
    add_plots.append(mpf.make_addplot(
        ind['BB_DN'], color='#7f7f7f', width=0.8, linestyle='--', panel=0, label='Lower rail'
    ))
    add_plots.append(mpf.make_addplot(
        ind['MA60'], color='#2ca02c', width=1.0, linestyle='-', panel=0, label='MA60'
    ))

    # Panel 2: RSI
    add_plots.append(mpf.make_addplot(
        ind['RSI'], color='#9467bd', width=1.0, panel=2, ylabel='RSI'
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(70, index=ind.index), color='#d62728', width=0.5, linestyle=':', panel=2
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(30, index=ind.index), color='#2ca02c', width=0.5, linestyle=':', panel=2
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(50, index=ind.index), color='gray', width=0.3, linestyle='-', panel=2
    ))

    # Panel 3: MACD
    colors_bar = ['#d62728' if v >= 0 else '#2ca02c' for v in ind['BAR'].fillna(0)]
    add_plots.append(mpf.make_addplot(
        ind['DIF'], color='#1f77b4', width=1.0, panel=3, ylabel='MACD', label='DIF'
    ))
    add_plots.append(mpf.make_addplot(
        ind['DEA'], color='#ff7f0e', width=1.0, panel=3, label='DEA'
    ))
    add_plots.append(mpf.make_addplot(
        ind['BAR'], type='bar', color=colors_bar, width=0.8, panel=3, alpha=0.7, label='BAR'
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(0, index=ind.index), color='gray', width=0.3, panel=3
    ))

    # Panel 4: KDJ
    add_plots.append(mpf.make_addplot(
        ind['K'], color='#1f77b4', width=0.8, panel=4, ylabel='KDJ', label='K'
    ))
    add_plots.append(mpf.make_addplot(
        ind['D'], color='#ff7f0e', width=0.8, panel=4, label='D'
    ))
    add_plots.append(mpf.make_addplot(
        ind['J'], color='#d62728', width=0.8, linestyle='--', panel=4, label='J'
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(80, index=ind.index), color='#d62728', width=0.5, linestyle=':', panel=4
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(20, index=ind.index), color='#2ca02c', width=0.5, linestyle=':', panel=4
    ))

    code = stock_info['code']
    name = stock_info['name']
    market = stock_info['market']

    title = (
        f"Figure1: {name} ({code}) Comprehensive analysis of technical indicators\n"
        f"{market} | Daily Line | forward-adjusted | {df['Date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['Date'].iloc[-1].strftime('%Y-%m-%d')}"
    )

    fig, axes = mpf.plot(
        ohlc, type='candle', style=STYLE, addplot=add_plots,
        volume=True, ylabel='Price(yuan)', ylabel_lower='Trading volume(million shares)',
        figsize=(20, 18), panel_ratios=(3, 1, 1.2, 1.2, 1.2),
        title=title, returnfig=True,
        datetime_format='%Y-%m', xrotation=30,
        show_nontrading=False, warn_too_much_data=300,
    )

    # Legend
    ax_main = axes[0]
    handles, labels = ax_main.get_legend_handles_labels()
    # Deduplication
    by_label = dict(zip(labels, handles))
    ax_main.legend(by_label.values(), by_label.keys(), loc='upper left',
                   fontsize=8, ncol=2, framealpha=0.7)

    # Add Statistics Text Box
    close = df['Close'].astype(float)
    chg = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
    stats = (
        f"Beginning of Period: {close.iloc[0]:.2f}  ->  End of term: {close.iloc[-1]:.2f} | Return: {chg:+.2f}%\n"
        f"highest: {close.max():.2f} | Minimum: {close.min():.2f} | Mean: {close.mean():.2f}\n"
        f"Annualized volatility: {close.pct_change().std() * np.sqrt(252) * 100:.2f}% | "
        f"Maximum Drawdown: {((close.cummax() - close) / close.cummax()).min() * 100:.2f}%"
    )
    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.85)
    ax_main.text(0.99, 0.99, stats, transform=ax_main.transAxes,
                 fontsize=8, verticalalignment='top', horizontalalignment='right',
                 family='monospace', bbox=props)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Comprehensive indicator chart has been saved: {os.path.basename(save_path)}")


#
# Figure2: CCI + ATR + ADX Supplementary indicators
#

def plot_supplementary(df, stock_info, save_path):
    """Supplementary Indicator Chart: CCI + ATR + ADX"""
    ohlc = prepare_ohlc(df)
    ind = calc_all_indicators(df)
    ind['Date'] = df['Date']
    ind = ind.set_index('Date')

    add_plots = []

    # Panel 0 (Main image): Kline + MA20
    add_plots.append(mpf.make_addplot(
        ind['MA20'], color='#ff7f0e', width=1.0, panel=0, label='MA20'
    ))

    # Panel 1: CCI
    add_plots.append(mpf.make_addplot(
        ind['CCI'], color='#1f77b4', width=1.0, panel=1, ylabel='CCI'
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(100, index=ind.index), color='#d62728', width=0.5, linestyle=':', panel=1
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(-100, index=ind.index), color='#2ca02c', width=0.5, linestyle=':', panel=1
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(0, index=ind.index), color='gray', width=0.3, panel=1
    ))

    # Panel 2: ATR
    add_plots.append(mpf.make_addplot(
        ind['ATR'], color='#9467bd', width=1.2, panel=2, ylabel='ATR'
    ))

    # Panel 3: ADX + DI
    add_plots.append(mpf.make_addplot(
        ind['ADX'], color='#d62728', width=1.2, panel=3, ylabel='ADX/DI', label='ADX'
    ))
    add_plots.append(mpf.make_addplot(
        ind['PDI'], color='#2ca02c', width=0.8, panel=3, label='+DI'
    ))
    add_plots.append(mpf.make_addplot(
        ind['MDI'], color='#1f77b4', width=0.8, panel=3, label='-DI'
    ))
    add_plots.append(mpf.make_addplot(
        pd.Series(25, index=ind.index), color='gray', width=0.5, linestyle='--', panel=3
    ))

    code = stock_info['code']
    name = stock_info['name']
    market = stock_info['market']

    title = (
        f"Figure2: {name} ({code}) Supplementary technical indicators\n"
        f"{market} | CCI + ATR + ADX | "
        f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['Date'].iloc[-1].strftime('%Y-%m-%d')}"
    )

    fig, axes = mpf.plot(
        ohlc, type='candle', style=STYLE, addplot=add_plots,
        volume=False, ylabel='Price(yuan)',
        figsize=(20, 16), panel_ratios=(3, 1.2, 1.2, 1.2),
        title=title, returnfig=True,
        datetime_format='%Y-%m', xrotation=30,
        show_nontrading=False, warn_too_much_data=300,
    )

    # Legend (panels: 0=Main image, 1=CCI, 2=ATR, 3=ADX)
    for ax_idx in [0, 1, 3]:
        if ax_idx < len(axes):
            handles, labels = axes[ax_idx].get_legend_handles_labels()
            if handles:
                by_label = dict(zip(labels, handles))
                axes[ax_idx].legend(by_label.values(), by_label.keys(),
                                   loc='upper left', fontsize=8, framealpha=0.7)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Supplementary indicator chart saved: {os.path.basename(save_path)}")


#
# Figure3: RSI Comparison of parameters (N=7, 14, 21)
#

def plot_rsi_comparison(df, stock_info, save_path):
    """RSI Comparison of Different Parameters: period=7, 14, 21"""
    code = stock_info['code']
    name = stock_info['name']

    fig, axes = plt.subplots(3, 1, figsize=(20, 12), sharex=True)
    fig.suptitle(
        f"Figure3: {name} ({code}) RSI Parameter Evolution Comparison  -  cycle N=7, 14, 21",
        fontsize=16, fontweight='bold', y=0.98
    )

    close = df['Close'].astype(float)
    periods = [7, 14, 21]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    axes_used = []

    for i, (p, c) in enumerate(zip(periods, colors)):
        ax = axes[i]
        axes_used.append(ax)
        rsi = calc_rsi(df, period=p)
        ax.plot(df['Date'], rsi, color=c, linewidth=1.0, label=f'RSI({p})')
        ax.axhline(y=70, color='#d62728', linestyle=':', linewidth=0.8)
        ax.axhline(y=30, color='#2ca02c', linestyle=':', linewidth=0.8)
        ax.axhline(y=50, color='gray', linestyle='-', linewidth=0.4)
        ax.fill_between(df['Date'], 70, 100, alpha=0.05, color='#d62728')
        ax.fill_between(df['Date'], 0, 30, alpha=0.05, color='#2ca02c')
        ax.set_ylim(0, 100)
        ax.set_ylabel(f'N={p}', fontsize=11, fontweight='bold')
        ax.legend(loc='upper left', fontsize=9)

        # Marking Overbought/Oversold Days
        overbought_days = (rsi > 70).sum()
        oversold_days = (rsi < 30).sum()
        ax.text(0.99, 0.95,
                f'RSI>70: {overbought_days}days | RSI<30: {oversold_days}days '
                f'| Mean: {rsi.mean():.1f}',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        ax.grid(True, alpha=0.3)

    # Bottom price stacking
    ax_price = axes[2].twinx()
    ax_price.plot(df['Date'], close, color='#9467bd', linewidth=0.8, alpha=0.6, label='Close')
    ax_price.set_ylabel('Close(yuan)', fontsize=10, color='#9467bd')
    ax_price.legend(loc='upper right', fontsize=8)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   RSIParameter comparison chart saved: {os.path.basename(save_path)}")


#
# Figure4: MACD Comparison of parameters
#

def plot_macd_comparison(df, stock_info, save_path):
    """MACD Comparison of Different Parameters: (6,13,5) vs (12,26,9) vs (21,55,13)"""
    code = stock_info['code']
    name = stock_info['name']

    params = [
        (6, 13, 5, '(6,13,5) Short-term'),
        (12, 26, 9, '(12,26,9) Classic'),
        (21, 55, 13, '(21,55,13) Long-term'),
    ]
    colors_dif = ['#1f77b4', '#ff7f0e', '#2ca02c']

    fig, axes = plt.subplots(3, 1, figsize=(20, 12), sharex=True)
    fig.suptitle(
        f"Figure4: {name} ({code}) MACD Parameter Evolution Comparison",
        fontsize=16, fontweight='bold', y=0.98
    )

    for i, ((fast, slow, sig, label), c) in enumerate(zip(params, colors_dif)):
        ax = axes[i]
        macd = calc_macd(df, fast=fast, slow=slow, signal=sig)

        ax.plot(df['Date'], macd['DIF'], color=c, linewidth=1.0, label=f'DIF({label})')
        ax.plot(df['Date'], macd['DEA'], color='#d62728', linewidth=0.8, label=f'DEA({label})')

        # BAR Bar chart
        bar_colors = ['#d62728' if v >= 0 else '#2ca02c' for v in macd['BAR'].fillna(0)]
        ax.bar(df['Date'], macd['BAR'], color=bar_colors, width=0.8, alpha=0.4)

        ax.axhline(y=0, color='gray', linewidth=0.5)

        # Statistical Golden Fork/Number of death crosss
        dif_arr = macd['DIF'].values
        dea_arr = macd['DEA'].values
        cross_up = 0
        cross_down = 0
        for j in range(1, len(dif_arr)):
            if pd.notna(dif_arr[j]) and pd.notna(dea_arr[j]) and \
               pd.notna(dif_arr[j-1]) and pd.notna(dea_arr[j-1]):
                if dif_arr[j-1] <= dea_arr[j-1] and dif_arr[j] > dea_arr[j]:
                    cross_up += 1
                elif dif_arr[j-1] >= dea_arr[j-1] and dif_arr[j] < dea_arr[j]:
                    cross_down += 1

        ax.set_ylabel(label, fontsize=11, fontweight='bold')
        ax.legend(loc='upper left', fontsize=8, ncol=2)
        ax.text(0.99, 0.95,
                f'Golden Cross: {cross_up}Next | death cross: {cross_down}Next',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   MACDParameter comparison chart saved: {os.path.basename(save_path)}")


#
# Figure5: Bollinger Bands Parameter Comparison
#

def plot_bollinger_comparison(df, stock_info, save_path):
    """Comparison of different parameters of Bollinger Bands: (10,1.5) vs (20,2.0) vs (50,2.5)"""
    code = stock_info['code']
    name = stock_info['name']

    param_sets = [
        (10, 1.5, '(10, 1.5) Short-term'),
        (20, 2.0, '(20, 2.0) Classic'),
        (50, 2.5, '(50, 2.5) Long-term'),
    ]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

    fig, axes = plt.subplots(3, 1, figsize=(20, 14), sharex=True)
    fig.suptitle(
        f"Figure5: {name} ({code}) Bollinger Bands Parameter Evolution Contrast",
        fontsize=16, fontweight='bold', y=0.98
    )

    close = df['Close'].astype(float)

    for i, ((period, k, label), c) in enumerate(zip(param_sets, colors)):
        ax = axes[i]
        bb = calc_bollinger(df, period=period, k=k)

        ax.plot(df['Date'], close, color='black', linewidth=0.8, alpha=0.7, label='Close')
        ax.plot(df['Date'], bb['UP'], color=c, linewidth=0.8, linestyle='--', label=f'On track({k}sigma)')
        ax.plot(df['Date'], bb['MID'], color=c, linewidth=1.0, label=f'Middle rail(SMA{period})')
        ax.plot(df['Date'], bb['DN'], color=c, linewidth=0.8, linestyle='--', label=f'Lower rail({k}sigma)')
        ax.fill_between(df['Date'], bb['UP'], bb['DN'], alpha=0.05, color=c)

        # Count the number of times the track is touched
        touch_up = (close > bb['UP']).sum()
        touch_dn = (close < bb['DN']).sum()
        avg_bandwidth = bb['BandWidth'].mean()

        ax.set_ylabel(label, fontsize=11, fontweight='bold')
        ax.legend(loc='upper left', fontsize=8, ncol=2)
        ax.text(0.99, 0.95,
                f'Breakout above the upper rail: {touch_up}Next | Falling below the lower rail: {touch_dn}Next | Average Bandwidth: {avg_bandwidth:.1f}%',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Bollinger Bands parameter comparison chart has been saved: {os.path.basename(save_path)}")


#
# Figure6: KDJ Comparison of parameters
#

def plot_kdj_comparison(df, stock_info, save_path):
    """KDJ Comparison of Different Parameters: (5,2,2) vs (9,3,3) vs (14,5,5)"""
    code = stock_info['code']
    name = stock_info['name']

    param_sets = [
        (5, 2, 2, '(5,2,2) Ultra-short term'),
        (9, 3, 3, '(9,3,3) Standard'),
        (14, 5, 5, '(14,5,5) Long-term'),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(20, 13), sharex=True)
    fig.suptitle(
        f"Figure6: {name} ({code}) KDJ Parameter Evolution Comparison",
        fontsize=16, fontweight='bold', y=0.98
    )

    for i, (period, sk, sd, label) in enumerate(param_sets):
        ax = axes[i]
        kdj = calc_kdj(df, period=period, smooth_k=sk, smooth_d=sd)

        ax.plot(df['Date'], kdj['K'], color='#1f77b4', linewidth=1.0, label=f'K({period},{sk},{sd})')
        ax.plot(df['Date'], kdj['D'], color='#ff7f0e', linewidth=1.0, label=f'D')
        ax.plot(df['Date'], kdj['J'], color='#d62728', linewidth=0.7, linestyle='--', label=f'J')

        ax.axhline(y=80, color='#d62728', linestyle=':', linewidth=0.8)
        ax.axhline(y=20, color='#2ca02c', linestyle=':', linewidth=0.8)
        ax.fill_between(df['Date'], 80, 120, alpha=0.05, color='#d62728')
        ax.fill_between(df['Date'], -20, 20, alpha=0.05, color='#2ca02c')

        # J line extreme value statistics
        j_above_100 = (kdj['J'] > 100).sum()
        j_below_0 = (kdj['J'] < 0).sum()

        ax.set_ylabel(label, fontsize=11, fontweight='bold')
        ax.legend(loc='upper left', fontsize=8)
        ax.set_ylim(-20, 120)
        ax.text(0.99, 0.95,
                f'J>100: {j_above_100}days | J<0: {j_below_0}days',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   KDJParameter comparison chart saved: {os.path.basename(save_path)}")


#
# Figure7: MA multi-period resonance
#

def plot_ma_resonance(df, stock_info, save_path):
    """Multi-period moving average resonance diagram"""
    code = stock_info['code']
    name = stock_info['name']

    ohlc = prepare_ohlc(df)
    ind = calc_all_indicators(df)
    ind['Date'] = df['Date']
    ind = ind.set_index('Date')

    ma_colors = {
        'MA5': '#1f77b4', 'MA10': '#ff7f0e', 'MA20': '#2ca02c',
        'MA60': '#d62728', 'MA120': '#9467bd', 'MA250': '#8c564b',
    }

    add_plots = []
    for ma_col, color in ma_colors.items():
        if ma_col in ind.columns:
            add_plots.append(mpf.make_addplot(
                ind[ma_col], color=color, width=1.0, panel=0, label=ma_col
            ))

    title = (
        f"Figure7: {name} ({code}) Multi-period moving average resonance analysis\n"
        f"MA5/10/20/60/120/250 | multi-head arrangement=Short-term moving average on top | "
        f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['Date'].iloc[-1].strftime('%Y-%m-%d')}"
    )

    fig, axes = mpf.plot(
        ohlc, type='candle', style=STYLE, addplot=add_plots,
        volume=True, ylabel='Price(yuan)', ylabel_lower='Trading volume(million shares)',
        figsize=(20, 12), panel_ratios=(3, 1),
        title=title, returnfig=True,
        datetime_format='%Y-%m', xrotation=30,
        show_nontrading=False, warn_too_much_data=300,
    )

    ax_main = axes[0]
    handles, labels = ax_main.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax_main.legend(by_label.values(), by_label.keys(),
                   loc='upper left', fontsize=8, ncol=3, framealpha=0.7)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   MAMulti-period resonance map saved: {os.path.basename(save_path)}")


#
# Main program
#

if __name__ == "__main__":
    print("=" * 60)
    print("  Visualization of technical indicators (mplfinance)")
    print("  Main exhibit item: Kweichow Moutai (600519)")
    print("=" * 60)

    # Loading Moutai data
    stock_info = {"code": "600519", "name": "Kweichow Moutai", "market": "SSE Main Board"}
    df = load_stock("600519", "Kweichow Moutai", "A-share")
    print(f"\n Data loading: {len(df)} item, {df['Date'].iloc[0]} ~ {df['Date'].iloc[-1]}")

    # Data Diagnostics
    diag = data_diagnosis(df, 'Kweichow Moutai(600519)')
    print_diagnosis(diag)

    # Generate Chart
    print("\n>>> Start generating the chart...")

    plot_comprehensive(df, stock_info,
                       os.path.join(CHART_DIR, "600519_comprehensive index analysis.png"))

    plot_supplementary(df, stock_info,
                       os.path.join(CHART_DIR, "600519_Supplementary indicators_CCI_ATR_ADX.png"))

    plot_rsi_comparison(df, stock_info,
                        os.path.join(CHART_DIR, "600519_RSIComparison of parameters.png"))

    plot_macd_comparison(df, stock_info,
                         os.path.join(CHART_DIR, "600519_MACDComparison of parameters.png"))

    plot_bollinger_comparison(df, stock_info,
                              os.path.join(CHART_DIR, "600519_Bollinger Bands Parameter Comparison.png"))

    plot_kdj_comparison(df, stock_info,
                        os.path.join(CHART_DIR, "600519_KDJComparison of parameters.png"))

    plot_ma_resonance(df, stock_info,
                      os.path.join(CHART_DIR, "600519_MAmulti-period resonance.png"))

    print(f"\n{'=' * 60}")
    print(f"   Complete all chart generation! total 7 Zhang")
    print(f"  Output Directory: {CHART_DIR}")
    print(f"{'=' * 60}")
