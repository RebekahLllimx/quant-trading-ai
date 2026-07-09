#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task4: 海龟策略报告图表生成 (matplotlib)
输出 5 张 PNG 到 data/charts/task4/
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# 中文字体
plt.rcParams['font.sans-serif'] = [
    'Heiti SC', 'STHeiti', 'PingFang SC',
    'Arial Unicode MS', 'SimHei', 'sans-serif'
]
plt.rcParams['axes.unicode_minus'] = False

# 导入策略模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turtle_strategy import (
    run_backtest, calc_metrics, calc_donchian,
    calc_atr, load_stock, param_sweep,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
CHART_DIR = os.path.join(BASE_DIR, '..', 'data', 'charts', 'task4')
os.makedirs(CHART_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════
# 图表1: 价格 + 高低通道 + 交易信号
# ═══════════════════════════════════════════════════

def plot_turtle_signals(df, result, stock_name, stock_code,
                         entry_period=20, exit_period=10):
    print('  📊 绘制海龟策略信号图...')
    fig, ax = plt.subplots(figsize=(15, 7))

    dates = df['Date']
    close = df['Close'].astype(float)

    # 收盘价
    ax.plot(dates, close, color='#2d3436', linewidth=1.2, alpha=0.8,
            label='收盘价', zorder=2)

    # 入场通道 (entry_period 日最高/最低)
    entry_high = result['dc_entry']['DC_High']
    entry_low = result['dc_entry']['DC_Low']
    ax.plot(dates, entry_high, color='#e17055', linewidth=1.2, alpha=0.7,
            linestyle='--', label=f'入场通道上轨 (Donchian {entry_period})')
    ax.plot(dates, entry_low, color='#e17055', linewidth=0.6, alpha=0.35,
            linestyle='--')

    # 离场通道 (exit_period 日最低)
    exit_low = result['dc_exit']['DC_Low']
    ax.plot(dates, exit_low, color='#0984e3', linewidth=1.2, alpha=0.7,
            linestyle=':', label=f'离场通道下轨 (Donchian {exit_period})')

    # 填充入场通道区域
    ax.fill_between(dates, entry_high, entry_low,
                    color='#e17055', alpha=0.06)

    # 买入信号 (红色上三角)
    if result['signals_buy']:
        buy_dates, buy_prices = zip(*result['signals_buy'])
        ax.scatter(buy_dates, buy_prices, marker='^', s=140, c='#d63031',
                   zorder=5, edgecolors='white', linewidth=0.8,
                   label=f'买入 (突破入场)')

    # 卖出信号 (绿色下三角) — 包含信号离场和止损
    if result['signals_sell']:
        sell_dates, sell_prices = zip(*result['signals_sell'])
        ax.scatter(sell_dates, sell_prices, marker='v', s=100, c='#00b894',
                   zorder=5, edgecolors='white', linewidth=0.8,
                   label=f'卖出 (止损/离场)')

    # 止损信号特殊标记
    if result['signals_stop']:
        stop_dates, stop_prices = zip(*result['signals_stop'])
        ax.scatter(stop_dates, stop_prices, marker='x', s=80, c='#e17055',
                   zorder=5, linewidth=1.5, alpha=0.8)

    ax.set_title(f'{stock_name} ({stock_code}) — 海龟交易策略信号\n'
                 f'(入场通道={entry_period}日, 离场通道={exit_period}日, '
                 f'止损=2×ATR, '
                 f'{df["Date"].iloc[0].strftime("%Y-%m-%d")} ~ '
                 f'{df["Date"].iloc[-1].strftime("%Y-%m-%d")})',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('日期', fontsize=11)
    ax.set_ylabel('价格 (元)', fontsize=11)
    ax.legend(loc='upper left', fontsize=8.5, framealpha=0.9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_海龟策略信号图.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表2: ATR + N 值变化图
# ═══════════════════════════════════════════════════

def plot_atr_nvalue(df, result, stock_name, stock_code):
    print('  📊 绘制 ATR/N 值走势图...')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 7), sharex=True)

    dates = df['Date']
    close = df['Close'].astype(float)
    n_value = result['n_value']

    # 上: 价格 + 高低通道
    ax1.plot(dates, close, color='#2d3436', linewidth=0.8, alpha=0.7, label='收盘价')
    ax1.plot(dates, result['dc_entry']['DC_High'], color='#e17055', linewidth=0.8,
             alpha=0.6, linestyle='--', label=f'入场通道上轨')
    ax1.plot(dates, result['dc_exit']['DC_Low'], color='#0984e3', linewidth=0.8,
             alpha=0.6, linestyle=':', label=f'离场通道下轨')
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_title(f'{stock_name} ({stock_code}) — 海龟通道与 ATR 波动率分析', fontsize=13, fontweight='bold')

    # 下: N 值 (ATR) — 高波动淡红底、低波动淡蓝底
    n_mean = n_value.mean()
    n_std = n_value.std()
    high_vol_mask = n_value > (n_mean + 0.5 * n_std)
    low_vol_mask = n_value < (n_mean - 0.5 * n_std)

    ax2.fill_between(dates, 0, n_value.max() * 1.1, where=high_vol_mask,
                     color='#d63031', alpha=0.08, label='高波动期')
    ax2.fill_between(dates, 0, n_value.max() * 1.1, where=low_vol_mask,
                     color='#0984e3', alpha=0.08, label='低波动期')
    ax2.fill_between(dates, n_value, 0, color='#0984e3', alpha=0.15)
    ax2.plot(dates, n_value, color='#0984e3', linewidth=1.2, label='N 值 (ATR-20)')
    ax2.set_ylabel('N 值 (元)', fontsize=11, color='#0984e3')
    ax2.set_xlabel('日期', fontsize=11)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(loc='upper left', fontsize=8)

    fig.autofmt_xdate()
    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_ATR分析.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表3: 资产曲线对比 + 回撤
# ═══════════════════════════════════════════════════

def plot_equity_and_drawdown(result, metrics, stock_name, stock_code):
    print('  📊 绘制资产曲线与回撤图...')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1]})

    eq_dates = [e['date'] for e in result['equity_curve']]
    eq_values = [e['equity'] for e in result['equity_curve']]
    bh_dates = [e['date'] for e in result['bh_equity_curve']]
    bh_values = [e['equity'] for e in result['bh_equity_curve']]

    # 资产曲线
    ax1.plot(eq_dates, eq_values, color='#0984e3', linewidth=2, label='海龟策略资产')
    ax1.plot(bh_dates, bh_values, color='#b2bec3', linewidth=1.2,
            linestyle='--', label='买入持有')
    ax1.axhline(y=1_000_000, color='#636e72', linewidth=0.6, linestyle=':',
               alpha=0.5, label='初始资金')

    # 标注买入/卖出区域
    if result['signals_buy']:
        for bd, bp in result['signals_buy']:
            ax1.axvline(x=bd, color='#d63031', linewidth=0.4, alpha=0.3, linestyle='-')
    if result['signals_sell']:
        for sd, sp in result['signals_sell']:
            ax1.axvline(x=sd, color='#00b894', linewidth=0.4, alpha=0.3, linestyle='-')

    ax1.set_title(f'{stock_name} ({stock_code}) — 资产曲线对比 (海龟策略 vs 买入持有)\n'
                 f'策略累计回报: {metrics["total_return"]:.2f}% | '
                 f'买入持有: {metrics["bh_total_return"]:.2f}% | '
                 f'超额收益: {metrics["total_return"] - metrics["bh_total_return"]:.2f}%',
                 fontsize=13, fontweight='bold')
    ax1.set_ylabel('资产 (元)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1e4:.0f}万'))

    # 回撤曲线
    peak = -np.inf
    dd_series = []
    for eq in eq_values:
        if eq > peak:
            peak = eq
        dd_series.append((eq - peak) / peak * 100)

    ax2.fill_between(eq_dates, dd_series, 0, color='#d63031', alpha=0.15)
    ax2.plot(eq_dates, dd_series, color='#d63031', linewidth=1)
    ax2.axhline(y=0, color='#636e72', linewidth=0.6, linestyle='--')
    ax2.axhline(y=-20, color='#e17055', linewidth=0.5, linestyle=':', alpha=0.7,
               label='-20% 警戒线')

    ax2.set_title(f'回撤曲线 — 最大回撤 (MDD): {metrics["mdd"]:.2f}%', fontsize=12, fontweight='bold')
    ax2.set_xlabel('日期', fontsize=11)
    ax2.set_ylabel('回撤 (%)', fontsize=11)
    ax2.legend(loc='lower left', fontsize=8)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))

    fig.autofmt_xdate()
    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_资产曲线与回撤.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表4: 参数敏感性热力图
# ═══════════════════════════════════════════════════

def plot_param_heatmap(df, stock_name, stock_code):
    print('  📊 绘制参数敏感性热力图...')
    entry_periods = [10, 15, 20, 30, 40, 55]
    exit_periods = [5, 10, 15, 20, 25]

    returns_matrix = np.zeros((len(entry_periods), len(exit_periods)))
    sharpe_matrix = np.zeros((len(entry_periods), len(exit_periods)))

    for i, ep in enumerate(entry_periods):
        for j, xp in enumerate(exit_periods):
            if xp >= ep:
                returns_matrix[i, j] = np.nan
                sharpe_matrix[i, j] = np.nan
                continue
            try:
                result = run_backtest(df, entry_period=ep, exit_period=xp)
                m = calc_metrics(result)
                if m and 'error' not in m:
                    returns_matrix[i, j] = m['total_return']
                    sharpe_matrix[i, j] = m['sharpe']
            except Exception:
                returns_matrix[i, j] = np.nan
                sharpe_matrix[i, j] = np.nan

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5))

    # 累计回报热力图
    im1 = ax1.imshow(returns_matrix, cmap='RdYlGn', aspect='auto',
                     vmin=np.nanmin(returns_matrix) if not np.all(np.isnan(returns_matrix)) else -30,
                     vmax=np.nanmax(returns_matrix) if not np.all(np.isnan(returns_matrix)) else 30)
    ax1.set_xticks(range(len(exit_periods)))
    ax1.set_xticklabels(exit_periods)
    ax1.set_yticks(range(len(entry_periods)))
    ax1.set_yticklabels(entry_periods)
    ax1.set_xlabel('离场通道周期', fontsize=11)
    ax1.set_ylabel('入场通道周期', fontsize=11)
    ax1.set_title(f'{stock_name} ({stock_code}) — 累计回报 (%)',
                  fontsize=12, fontweight='bold')
    for i in range(len(entry_periods)):
        for j in range(len(exit_periods)):
            val = returns_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 15 else 'black'
                ax1.text(j, i, f'{val:.1f}', ha='center', va='center',
                        fontsize=8, color=color)
    plt.colorbar(im1, ax=ax1, shrink=0.85)

    # 夏普比率热力图
    im2 = ax2.imshow(sharpe_matrix, cmap='RdYlGn', aspect='auto',
                     vmin=-2, vmax=2)
    ax2.set_xticks(range(len(exit_periods)))
    ax2.set_xticklabels(exit_periods)
    ax2.set_yticks(range(len(entry_periods)))
    ax2.set_yticklabels(entry_periods)
    ax2.set_xlabel('离场通道周期', fontsize=11)
    ax2.set_ylabel('入场通道周期', fontsize=11)
    ax2.set_title(f'{stock_name} ({stock_code}) — 夏普比率',
                  fontsize=12, fontweight='bold')
    for i in range(len(entry_periods)):
        for j in range(len(exit_periods)):
            val = sharpe_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 0.8 else 'black'
                ax2.text(j, i, f'{val:.2f}', ha='center', va='center',
                        fontsize=8, color=color)
    plt.colorbar(im2, ax=ax2, shrink=0.85)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_参数敏感性热力图.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表5: 多股票策略对比
# ═══════════════════════════════════════════════════

def plot_multi_stock(stock_list, entry_period=20, exit_period=10):
    print('  📊 绘制多股票对比图...')
    results = []
    for code, name, market in stock_list:
        try:
            df = load_stock(code, name, market)
            result = run_backtest(df, entry_period=entry_period,
                                  exit_period=exit_period)
            metrics = calc_metrics(result)
            if metrics and 'error' not in metrics:
                results.append({
                    'label': f'{name}\n({code})',
                    'strategy': metrics['total_return'],
                    'bh': metrics['bh_total_return'],
                    'sharpe': metrics['sharpe'],
                    'mdd': metrics['mdd'],
                    'win_rate': metrics['win_rate'],
                    'trades': metrics['total_trades'],
                })
        except Exception as e:
            print(f'    ⚠️ 跳过 {code} {name}: {e}')

    if not results:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5))

    x = np.arange(len(results))
    width = 0.35

    # 累计回报对比
    bars1 = ax1.bar(x - width/2, [r['strategy'] for r in results], width,
                    color='#0984e3', alpha=0.85, label=f'海龟策略 (入场{entry_period}/离场{exit_period})')
    bars2 = ax1.bar(x + width/2, [r['bh'] for r in results], width,
                    color='#b2bec3', alpha=0.7, label='买入持有')
    ax1.set_xticks(x)
    ax1.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax1.set_ylabel('累计回报 (%)', fontsize=11)
    ax1.set_title('多股票海龟策略收益对比 — 累计回报', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax1.axhline(y=0, color='black', linewidth=0.5)
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h,
                 f'{h:.1f}%' if h >= 0 else f'{h:.1f}%',
                 ha='center', va='bottom' if h >= 0 else 'top', fontsize=7.5)

    # 夏普比率 & MDD
    ax2.bar(x - width/2, [r['sharpe'] for r in results], width,
            color='#00b894', alpha=0.8, label='夏普比率')
    ax2_twin = ax2.twinx()
    ax2_twin.bar(x + width/2, [r['mdd'] for r in results], width,
                 color='#d63031', alpha=0.5, label='最大回撤 (%)')
    ax2.set_xticks(x)
    ax2.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax2.set_ylabel('夏普比率', fontsize=11, color='#00b894')
    ax2_twin.set_ylabel('最大回撤 (%)', fontsize=11, color='#d63031')
    ax2.set_title('多股票海龟策略 — 夏普比率 & 最大回撤', fontsize=12, fontweight='bold')
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, '多股票策略对比.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表6: 止损倍数敏感性
# ═══════════════════════════════════════════════════

def plot_stop_sensitivity(df, stock_name, stock_code):
    """止损倍数敏感性 — 单图三线：累计回报 / 夏普 / MDD"""
    print('  📊 绘制止损倍数敏感性图...')
    stop_mults = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
    metrics_list = []

    for sm in stop_mults:
        try:
            result = run_backtest(df, atr_stop_mult=sm)
            m = calc_metrics(result)
            if m and 'error' not in m:
                metrics_list.append({
                    'stop_mult': sm,
                    'total_return': m['total_return'],
                    'sharpe': m['sharpe'],
                    'mdd': m['mdd'],
                })
        except Exception:
            pass

    if not metrics_list:
        return None

    fig, ax1 = plt.subplots(figsize=(12, 5))

    sms = [m['stop_mult'] for m in metrics_list]
    returns = [m['total_return'] for m in metrics_list]
    sharpes = [m['sharpe'] for m in metrics_list]
    mdds = [m['mdd'] for m in metrics_list]

    # 左轴：累计回报 + 夏普比率
    line1 = ax1.plot(sms, returns, 'o-', color='#0984e3', linewidth=2.5, markersize=10, label='累计回报 (%)')
    line2 = ax1.plot(sms, sharpes, 's-', color='#00b894', linewidth=2.5, markersize=10, label='夏普比率')
    ax1.axhline(y=0, color='#636e72', linewidth=0.6, linestyle='--')
    ax1.set_xlabel('止损倍数 (×ATR)', fontsize=12)
    ax1.set_ylabel('累计回报 (%) / 夏普比率', fontsize=11, color='#2d3436')
    ax1.tick_params(axis='y', labelcolor='#2d3436')

    # 右轴：最大回撤
    ax2 = ax1.twinx()
    line3 = ax2.plot(sms, mdds, '^-', color='#d63031', linewidth=2.5, markersize=10, label='最大回撤 (%)')
    ax2.set_ylabel('最大回撤 (%)', fontsize=11, color='#d63031')
    ax2.tick_params(axis='y', labelcolor='#d63031')

    # 合并图例
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')

    ax1.set_title(f'{stock_name} ({stock_code}) — 止损倍数敏感性\n'
                  '止损倍数 ↑ → 回撤 ↑（因为不轻易止损）；止损倍数 ↓ → 收益可能 ↓（被噪音震出）',
                  fontsize=13, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_止损敏感性.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════

def main():
    print('=' * 60)
    print('  Task4: 生成海龟策略报告图表 (6 张)')
    print('=' * 60)

    # 主力标的：贵州茅台
    df_moutai = load_stock('600519', '贵州茅台', 'A股')
    print(f'\n📂 贵州茅台: {len(df_moutai)} 条数据')

    # 回测
    print('\n⏳ 运行海龟策略回测 (入场=20日, 离场=10日, 止损=2×ATR)...')
    result = run_backtest(df_moutai, entry_period=20, exit_period=10,
                          atr_stop_mult=2.0)
    metrics = calc_metrics(result)

    print(f'   累计回报: {metrics["total_return"]:.2f}%')
    print(f'   年化收益: {metrics["annual_return"]:.2f}%')
    print(f'   最大回撤: {metrics["mdd"]:.2f}%')
    print(f'   夏普比率: {metrics["sharpe"]:.4f}')
    print(f'   胜率: {metrics["win_rate"]:.1f}%')
    print(f'   交易次数: {metrics["total_trades"]}')
    print(f'   止损退出: {metrics["stop_exits"]} 次')

    # 生成图表（6 张）
    print('\n📊 生成图表...')
    paths = {}

    # 图1: 交易信号
    paths['signals'] = plot_turtle_signals(df_moutai, result, '贵州茅台', '600519',
                                           entry_period=20, exit_period=10)
    # 图2: ATR/N值走势（高波动红底、低波动蓝底）
    paths['atr'] = plot_atr_nvalue(df_moutai, result, '贵州茅台', '600519')

    # 图3: 资产曲线与回撤（三线对比）
    paths['equity'] = plot_equity_and_drawdown(result, metrics, '贵州茅台', '600519')

    # 图4: 参数热力图
    paths['heatmap'] = plot_param_heatmap(df_moutai, '贵州茅台', '600519')

    # 图5: 止损敏感性（单图三线）
    paths['stop'] = plot_stop_sensitivity(df_moutai, '贵州茅台', '600519')

    # 图6: 多股票对比
    # 注: 510300 数据暂不可用（网络限制），以比亚迪 (002594) 作为第三类标的
    stock_list = [
        ('600519', '贵州茅台', 'A股'),
        ('300750', '宁德时代', 'A股'),
        ('002594', '比亚迪', 'A股'),
        ('601318', '中国平安', 'A股'),
        ('000001', '平安银行', 'A股'),
        ('00700', '腾讯控股', '港股'),
        ('09988', '阿里巴巴', '港股'),
    ]
    paths['multi'] = plot_multi_stock(stock_list, entry_period=20, exit_period=10)

    print(f'\n✅ 图表已保存到: {CHART_DIR}')
    for name, p in paths.items():
        if p:
            print(f'   {name}: {os.path.basename(p)}')
    print('=' * 60)


if __name__ == '__main__':
    main()
