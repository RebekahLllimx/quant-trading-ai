#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3: 技术指标可视化 (mplfinance)
以贵州茅台 (600519) 为主展示标的，绘制综合指标图 + 参数对比图
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

# 添加 scripts 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import (
    calc_all_indicators, calc_rsi, calc_macd, calc_bollinger,
    calc_atr, calc_kdj, calc_ma, calc_cci, calc_adx,
    data_diagnosis, print_diagnosis,
)

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
CHART_DIR = os.path.join(BASE_DIR, '..', 'data', 'charts', 'task2')
os.makedirs(CHART_DIR, exist_ok=True)

# 中文字体
plt.rcParams['font.sans-serif'] = [
    'Heiti SC', 'STHeiti', 'PingFang SC',
    'Arial Unicode MS', 'SimHei', 'sans-serif'
]
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']

# mplfinance 风格
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
    """加载股票 CSV 数据"""
    filename = f"{code}_{name}_{market}_daily.csv"
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"数据文件不存在: {filepath}")
    df = pd.read_csv(filepath, encoding='utf-8-sig')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


def prepare_ohlc(df):
    """准备 mplfinance 需要的 OHLCV DataFrame"""
    ohlc = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    ohlc = ohlc.set_index('Date')
    ohlc['Volume'] = ohlc['Volume'].astype(float)
    # 成交量转万股
    ohlc['Volume'] = ohlc['Volume'] / 10000
    return ohlc


# ═══════════════════════════════════════════════════════════════
# 图1: 综合指标全览 (K线 + 布林带 + 成交量 + RSI + MACD + KDJ)
# ═══════════════════════════════════════════════════════════════

def plot_comprehensive(df, stock_info, save_path):
    """
    综合指标图: K线(布林带) + 成交量 + RSI + MACD + KDJ
    6 个面板 (mplfinance panel_ratios)
    """
    ohlc = prepare_ohlc(df)

    # 计算所有指标
    ind = calc_all_indicators(df)
    ind['Date'] = df['Date']
    ind = ind.set_index('Date')

    # 构建 add_plots
    add_plots = []

    # Panel 0 (主图): 布林带三轨
    add_plots.append(mpf.make_addplot(
        ind['BB_UP'], color='#7f7f7f', width=0.8, linestyle='--', panel=0, label='上轨'
    ))
    add_plots.append(mpf.make_addplot(
        ind['BB_MID'], color='#ff7f0e', width=1.0, linestyle='-', panel=0, label='中轨(MA20)'
    ))
    add_plots.append(mpf.make_addplot(
        ind['BB_DN'], color='#7f7f7f', width=0.8, linestyle='--', panel=0, label='下轨'
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
        f"图1：{name}（{code}）技术指标综合分析\n"
        f"{market} | 日线 | 前复权 | {df['Date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['Date'].iloc[-1].strftime('%Y-%m-%d')}"
    )

    fig, axes = mpf.plot(
        ohlc, type='candle', style=STYLE, addplot=add_plots,
        volume=True, ylabel='价格(元)', ylabel_lower='成交量(万股)',
        figsize=(20, 18), panel_ratios=(3, 1, 1.2, 1.2, 1.2),
        title=title, returnfig=True,
        datetime_format='%Y-%m', xrotation=30,
        show_nontrading=False, warn_too_much_data=300,
    )

    # 图例
    ax_main = axes[0]
    handles, labels = ax_main.get_legend_handles_labels()
    # 去重
    by_label = dict(zip(labels, handles))
    ax_main.legend(by_label.values(), by_label.keys(), loc='upper left',
                   fontsize=8, ncol=2, framealpha=0.7)

    # 添加统计信息文本框
    close = df['Close'].astype(float)
    chg = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
    stats = (
        f"期初: {close.iloc[0]:.2f} → 期末: {close.iloc[-1]:.2f} | 涨跌幅: {chg:+.2f}%\n"
        f"最高: {close.max():.2f} | 最低: {close.min():.2f} | 均值: {close.mean():.2f}\n"
        f"年化波动: {close.pct_change().std() * np.sqrt(252) * 100:.2f}% | "
        f"最大回撤: {((close.cummax() - close) / close.cummax()).min() * 100:.2f}%"
    )
    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.85)
    ax_main.text(0.99, 0.99, stats, transform=ax_main.transAxes,
                 fontsize=8, verticalalignment='top', horizontalalignment='right',
                 family='monospace', bbox=props)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ 综合指标图已保存: {os.path.basename(save_path)}")


# ═══════════════════════════════════════════════════════════════
# 图2: CCI + ATR + ADX 补充指标
# ═══════════════════════════════════════════════════════════════

def plot_supplementary(df, stock_info, save_path):
    """补充指标图: CCI + ATR + ADX"""
    ohlc = prepare_ohlc(df)
    ind = calc_all_indicators(df)
    ind['Date'] = df['Date']
    ind = ind.set_index('Date')

    add_plots = []

    # Panel 0 (主图): K线 + MA20
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

    # Panel 3: ADX + ±DI
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
        f"图2：{name}（{code}）补充技术指标\n"
        f"{market} | CCI + ATR + ADX | "
        f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['Date'].iloc[-1].strftime('%Y-%m-%d')}"
    )

    fig, axes = mpf.plot(
        ohlc, type='candle', style=STYLE, addplot=add_plots,
        volume=False, ylabel='价格(元)',
        figsize=(20, 16), panel_ratios=(3, 1.2, 1.2, 1.2),
        title=title, returnfig=True,
        datetime_format='%Y-%m', xrotation=30,
        show_nontrading=False, warn_too_much_data=300,
    )

    # 图例 (panels: 0=主图, 1=CCI, 2=ATR, 3=ADX)
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
    print(f"  ✅ 补充指标图已保存: {os.path.basename(save_path)}")


# ═══════════════════════════════════════════════════════════════
# 图3: RSI 参数对比 (N=7, 14, 21)
# ═══════════════════════════════════════════════════════════════

def plot_rsi_comparison(df, stock_info, save_path):
    """RSI 不同参数对比: period=7, 14, 21"""
    code = stock_info['code']
    name = stock_info['name']

    fig, axes = plt.subplots(3, 1, figsize=(20, 12), sharex=True)
    fig.suptitle(
        f"图3：{name}（{code}）RSI 参数演化对比 — 周期 N=7, 14, 21",
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

        # 标注超买/超卖天数
        overbought_days = (rsi > 70).sum()
        oversold_days = (rsi < 30).sum()
        ax.text(0.99, 0.95,
                f'RSI>70: {overbought_days}天 | RSI<30: {oversold_days}天 '
                f'| 均值: {rsi.mean():.1f}',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        ax.grid(True, alpha=0.3)

    # 底部价格叠加
    ax_price = axes[2].twinx()
    ax_price.plot(df['Date'], close, color='#9467bd', linewidth=0.8, alpha=0.6, label='收盘价')
    ax_price.set_ylabel('收盘价(元)', fontsize=10, color='#9467bd')
    ax_price.legend(loc='upper right', fontsize=8)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ RSI参数对比图已保存: {os.path.basename(save_path)}")


# ═══════════════════════════════════════════════════════════════
# 图4: MACD 参数对比
# ═══════════════════════════════════════════════════════════════

def plot_macd_comparison(df, stock_info, save_path):
    """MACD 不同参数对比: (6,13,5) vs (12,26,9) vs (21,55,13)"""
    code = stock_info['code']
    name = stock_info['name']

    params = [
        (6, 13, 5, '(6,13,5) 短线'),
        (12, 26, 9, '(12,26,9) 经典'),
        (21, 55, 13, '(21,55,13) 长线'),
    ]
    colors_dif = ['#1f77b4', '#ff7f0e', '#2ca02c']

    fig, axes = plt.subplots(3, 1, figsize=(20, 12), sharex=True)
    fig.suptitle(
        f"图4：{name}（{code}）MACD 参数演化对比",
        fontsize=16, fontweight='bold', y=0.98
    )

    for i, ((fast, slow, sig, label), c) in enumerate(zip(params, colors_dif)):
        ax = axes[i]
        macd = calc_macd(df, fast=fast, slow=slow, signal=sig)

        ax.plot(df['Date'], macd['DIF'], color=c, linewidth=1.0, label=f'DIF({label})')
        ax.plot(df['Date'], macd['DEA'], color='#d62728', linewidth=0.8, label=f'DEA({label})')

        # BAR 柱状图
        bar_colors = ['#d62728' if v >= 0 else '#2ca02c' for v in macd['BAR'].fillna(0)]
        ax.bar(df['Date'], macd['BAR'], color=bar_colors, width=0.8, alpha=0.4)

        ax.axhline(y=0, color='gray', linewidth=0.5)

        # 统计金叉/死叉次数
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
                f'金叉: {cross_up}次 | 死叉: {cross_down}次',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ MACD参数对比图已保存: {os.path.basename(save_path)}")


# ═══════════════════════════════════════════════════════════════
# 图5: 布林带参数对比
# ═══════════════════════════════════════════════════════════════

def plot_bollinger_comparison(df, stock_info, save_path):
    """布林带不同参数对比: (10,1.5) vs (20,2.0) vs (50,2.5)"""
    code = stock_info['code']
    name = stock_info['name']

    param_sets = [
        (10, 1.5, '(10, 1.5) 短线'),
        (20, 2.0, '(20, 2.0) 经典'),
        (50, 2.5, '(50, 2.5) 长线'),
    ]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

    fig, axes = plt.subplots(3, 1, figsize=(20, 14), sharex=True)
    fig.suptitle(
        f"图5：{name}（{code}）布林带参数演化对比",
        fontsize=16, fontweight='bold', y=0.98
    )

    close = df['Close'].astype(float)

    for i, ((period, k, label), c) in enumerate(zip(param_sets, colors)):
        ax = axes[i]
        bb = calc_bollinger(df, period=period, k=k)

        ax.plot(df['Date'], close, color='black', linewidth=0.8, alpha=0.7, label='收盘价')
        ax.plot(df['Date'], bb['UP'], color=c, linewidth=0.8, linestyle='--', label=f'上轨(±{k}σ)')
        ax.plot(df['Date'], bb['MID'], color=c, linewidth=1.0, label=f'中轨(SMA{period})')
        ax.plot(df['Date'], bb['DN'], color=c, linewidth=0.8, linestyle='--', label=f'下轨(±{k}σ)')
        ax.fill_between(df['Date'], bb['UP'], bb['DN'], alpha=0.05, color=c)

        # 统计触及轨道次数
        touch_up = (close > bb['UP']).sum()
        touch_dn = (close < bb['DN']).sum()
        avg_bandwidth = bb['BandWidth'].mean()

        ax.set_ylabel(label, fontsize=11, fontweight='bold')
        ax.legend(loc='upper left', fontsize=8, ncol=2)
        ax.text(0.99, 0.95,
                f'突破上轨: {touch_up}次 | 跌破下轨: {touch_dn}次 | 平均带宽: {avg_bandwidth:.1f}%',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ 布林带参数对比图已保存: {os.path.basename(save_path)}")


# ═══════════════════════════════════════════════════════════════
# 图6: KDJ 参数对比
# ═══════════════════════════════════════════════════════════════

def plot_kdj_comparison(df, stock_info, save_path):
    """KDJ 不同参数对比: (5,2,2) vs (9,3,3) vs (14,5,5)"""
    code = stock_info['code']
    name = stock_info['name']

    param_sets = [
        (5, 2, 2, '(5,2,2) 极短线'),
        (9, 3, 3, '(9,3,3) 标准'),
        (14, 5, 5, '(14,5,5) 长线'),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(20, 13), sharex=True)
    fig.suptitle(
        f"图6：{name}（{code}）KDJ 参数演化对比",
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

        # J 线极值统计
        j_above_100 = (kdj['J'] > 100).sum()
        j_below_0 = (kdj['J'] < 0).sum()

        ax.set_ylabel(label, fontsize=11, fontweight='bold')
        ax.legend(loc='upper left', fontsize=8)
        ax.set_ylim(-20, 120)
        ax.text(0.99, 0.95,
                f'J>100: {j_above_100}天 | J<0: {j_below_0}天',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ KDJ参数对比图已保存: {os.path.basename(save_path)}")


# ═══════════════════════════════════════════════════════════════
# 图7: MA 多周期共振
# ═══════════════════════════════════════════════════════════════

def plot_ma_resonance(df, stock_info, save_path):
    """多周期均线共振图"""
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
        f"图7：{name}（{code}）多周期均线共振分析\n"
        f"MA5/10/20/60/120/250 | 多头排列=短期均线在上 | "
        f"{df['Date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['Date'].iloc[-1].strftime('%Y-%m-%d')}"
    )

    fig, axes = mpf.plot(
        ohlc, type='candle', style=STYLE, addplot=add_plots,
        volume=True, ylabel='价格(元)', ylabel_lower='成交量(万股)',
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
    print(f"  ✅ MA多周期共振图已保存: {os.path.basename(save_path)}")


# ═══════════════════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  技术指标可视化 (mplfinance)")
    print("  主展示标的: 贵州茅台 (600519)")
    print("=" * 60)

    # 加载茅台数据
    stock_info = {"code": "600519", "name": "贵州茅台", "market": "上交所主板"}
    df = load_stock("600519", "贵州茅台", "A股")
    print(f"\n📂 数据加载: {len(df)} 条, {df['Date'].iloc[0]} ~ {df['Date'].iloc[-1]}")

    # 数据诊断
    diag = data_diagnosis(df, '贵州茅台(600519)')
    print_diagnosis(diag)

    # 生成图表
    print("\n>>> 开始生成图表...")

    plot_comprehensive(df, stock_info,
                       os.path.join(CHART_DIR, "600519_综合指标分析.png"))

    plot_supplementary(df, stock_info,
                       os.path.join(CHART_DIR, "600519_补充指标_CCI_ATR_ADX.png"))

    plot_rsi_comparison(df, stock_info,
                        os.path.join(CHART_DIR, "600519_RSI参数对比.png"))

    plot_macd_comparison(df, stock_info,
                         os.path.join(CHART_DIR, "600519_MACD参数对比.png"))

    plot_bollinger_comparison(df, stock_info,
                              os.path.join(CHART_DIR, "600519_布林带参数对比.png"))

    plot_kdj_comparison(df, stock_info,
                        os.path.join(CHART_DIR, "600519_KDJ参数对比.png"))

    plot_ma_resonance(df, stock_info,
                      os.path.join(CHART_DIR, "600519_MA多周期共振.png"))

    print(f"\n{'=' * 60}")
    print(f"  ✅ 全部图表生成完成！共 7 张")
    print(f"  输出目录: {CHART_DIR}")
    print(f"{'=' * 60}")
