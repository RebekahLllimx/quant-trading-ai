#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task4: Turtle Strategy Report Chart Generation (matplotlib)
Output 5 PNG files to artifacts/charts/task4/
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Chinese fonts
plt.rcParams['font.sans-serif'] = [
    'Heiti SC', 'STHeiti', 'PingFang SC',
    'Arial Unicode MS', 'SimHei', 'sans-serif'
]
plt.rcParams['axes.unicode_minus'] = False

# Import Policy Module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turtle_strategy import (
    run_backtest, calc_metrics, calc_donchian,
    calc_atr, load_stock, param_sweep,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
CHART_DIR = os.path.join(BASE_DIR, '..', 'artifacts', 'charts', 'task4')
os.makedirs(CHART_DIR, exist_ok=True)


#
# Chart1: Price + high and low channel + Trading signals
#

def plot_turtle_signals(df, result, stock_name, stock_code,
                         entry_period=20, exit_period=10):
    print('   Mapping the Turtle Strategy Signals...')
    fig, ax = plt.subplots(figsize=(15, 7))

    dates = df['Date']
    close = df['Close'].astype(float)

    # Close
    ax.plot(dates, close, color='#2d3436', linewidth=1.2, alpha=0.8,
            label='Close', zorder=2)

    # Admission channel (entry_period Day Highest/Minimum)
    entry_high = result['dc_entry']['DC_High']
    entry_low = result['dc_entry']['DC_Low']
    ax.plot(dates, entry_high, color='#e17055', linewidth=1.2, alpha=0.7,
            linestyle='--', label=f'Entrance channel on rail (Donchian {entry_period})')
    ax.plot(dates, entry_low, color='#e17055', linewidth=0.6, alpha=0.35,
            linestyle='--')

    # Exit passage (exit_period Daily minimum)
    exit_low = result['dc_exit']['DC_Low']
    ax.plot(dates, exit_low, color='#0984e3', linewidth=1.2, alpha=0.7,
            linestyle=':', label=f'Departing channel lower rail (Donchian {exit_period})')

    # Fill the entrance passage area
    ax.fill_between(dates, entry_high, entry_low,
                    color='#e17055', alpha=0.06)

    # Buy signal (red upper triangle)
    if result['signals_buy']:
        buy_dates, buy_prices = zip(*result['signals_buy'])
        ax.scatter(buy_dates, buy_prices, marker='^', s=140, c='#d63031',
                   zorder=5, edgecolors='white', linewidth=0.8,
                   label=f'Buy (Breakout Entry)')

    # Bin signal (Orange Diamond)
    if result.get('signals_add'):
        add_dates, add_prices = zip(*result['signals_add'])
        ax.scatter(add_dates, add_prices, marker='D', s=80, c='#fdcb6e',
                   zorder=5, edgecolors='white', linewidth=0.8,
                   label='Increase position (Pyramid)')

    # Sell signal (Green lower triangle)  -  Contains signal exit and stop loss
    if result['signals_sell']:
        sell_dates, sell_prices = zip(*result['signals_sell'])
        ax.scatter(sell_dates, sell_prices, marker='v', s=100, c='#00b894',
                   zorder=5, edgecolors='white', linewidth=0.8,
                   label=f'Sell (Stop-loss/Departing)')

    # Special Marker for Stop-Loss Signals
    if result['signals_stop']:
        stop_dates, stop_prices = zip(*result['signals_stop'])
        ax.scatter(stop_dates, stop_prices, marker='x', s=80, c='#e17055',
                   zorder=5, linewidth=1.5, alpha=0.8)

    ax.set_title(f'{stock_name} ({stock_code})  -  Turtle Trading Strategy Signals\n'
                 f'(Admission channel={entry_period}day, Exit passage={exit_period}day, '
                 f'Stop-loss=2xATR, '
                 f'{df["Date"].iloc[0].strftime("%Y-%m-%d")} ~ '
                 f'{df["Date"].iloc[-1].strftime("%Y-%m-%d")})',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('Price (yuan)', fontsize=11)
    ax.legend(loc='upper left', fontsize=8.5, framealpha=0.9, ncol=3)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_Turtle strategy signal diagram.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart2: ATR + N Value change graph
#

def plot_atr_nvalue(df, result, stock_name, stock_code):
    print('   Draw ATR/N Value Chart...')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 7), sharex=True)

    dates = df['Date']
    close = df['Close'].astype(float)
    n_value = result['n_value']

    # up: Price + high and low channel
    ax1.plot(dates, close, color='#2d3436', linewidth=0.8, alpha=0.7, label='Close')
    ax1.plot(dates, result['dc_entry']['DC_High'], color='#e17055', linewidth=0.8,
             alpha=0.6, linestyle='--', label=f'Entrance channel on rail')
    ax1.plot(dates, result['dc_exit']['DC_Low'], color='#0984e3', linewidth=0.8,
             alpha=0.6, linestyle=':', label=f'Departing channel lower rail')
    ax1.set_ylabel('Price (yuan)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_title(f'{stock_name} ({stock_code})  -  Turtle Crossing and ATR Volatility Analysis', fontsize=13, fontweight='bold')

    # down: N value (ATR)  -  high fluctuation light red bottom, low fluctuation light blue bottom
    n_mean = n_value.mean()
    n_std = n_value.std()
    high_vol_mask = n_value > (n_mean + 0.5 * n_std)
    low_vol_mask = n_value < (n_mean - 0.5 * n_std)

    ax2.fill_between(dates, 0, n_value.max() * 1.1, where=high_vol_mask,
                     color='#d63031', alpha=0.08, label='period of high volatility')
    ax2.fill_between(dates, 0, n_value.max() * 1.1, where=low_vol_mask,
                     color='#0984e3', alpha=0.08, label='Low Volatility Period')
    ax2.fill_between(dates, n_value, 0, color='#0984e3', alpha=0.15)
    ax2.plot(dates, n_value, color='#0984e3', linewidth=1.2, label='N value (ATR-20)')
    ax2.set_ylabel('N value (yuan)', fontsize=11, color='#0984e3')
    ax2.set_xlabel('Date', fontsize=11)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(loc='upper left', fontsize=8)

    fig.autofmt_xdate()
    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_ATRAnalysis.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart3: Asset Curve Comparison + drawdown
#

def plot_equity_and_drawdown(result, metrics, stock_name, stock_code):
    print('   Plotting the Equity Curve and Drawdown Chart...')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1]})

    eq_dates = [e['date'] for e in result['equity_curve']]
    eq_values = [e['equity'] for e in result['equity_curve']]
    bh_dates = [e['date'] for e in result['bh_equity_curve']]
    bh_values = [e['equity'] for e in result['bh_equity_curve']]

    # Asset curve
    ax1.plot(eq_dates, eq_values, color='#0984e3', linewidth=2, label='Turtle Strategy Asset')
    ax1.plot(bh_dates, bh_values, color='#b2bec3', linewidth=1.2,
            linestyle='--', label='Buy and hold')
    ax1.axhline(y=1_000_000, color='#636e72', linewidth=0.6, linestyle=':',
               alpha=0.5, label='Initial funding')

    # Mark Buy/Selling area
    if result['signals_buy']:
        for bd, bp in result['signals_buy']:
            ax1.axvline(x=bd, color='#d63031', linewidth=0.4, alpha=0.3, linestyle='-')
    if result['signals_sell']:
        for sd, sp in result['signals_sell']:
            ax1.axvline(x=sd, color='#00b894', linewidth=0.4, alpha=0.3, linestyle='-')

    ax1.set_title(f'{stock_name} ({stock_code})  -  Asset Curve Comparison (Turtle Strategy vs Buy and hold)\n'
                 f'Strategy Cumulative Returns: {metrics["total_return"]:.2f}% | '
                 f'Buy and hold: {metrics["bh_total_return"]:.2f}% | '
                 f'Excess return: {metrics["total_return"] - metrics["bh_total_return"]:.2f}%',
                 fontsize=13, fontweight='bold')
    ax1.set_ylabel('Assets (yuan)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1e4:.0f}million'))

    # Drawdown Curve
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
               label='-20% Cordon')

    ax2.set_title(f'Drawdown Curve  -  Maximum Drawdown (MDD): {metrics["mdd"]:.2f}%', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=11)
    ax2.set_ylabel('drawdown (%)', fontsize=11)
    ax2.legend(loc='lower left', fontsize=8)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))

    fig.autofmt_xdate()
    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_Asset Curve and drawdown.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart4: Parameter Sensitivity Heatmap
#

def plot_param_heatmap(df, stock_name, stock_code):
    print('   Draw parameter sensitivity heat map...')
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

    # Cumulative return heatmap
    im1 = ax1.imshow(returns_matrix, cmap='RdYlGn', aspect='auto',
                     vmin=np.nanmin(returns_matrix) if not np.all(np.isnan(returns_matrix)) else -30,
                     vmax=np.nanmax(returns_matrix) if not np.all(np.isnan(returns_matrix)) else 30)
    ax1.set_xticks(range(len(exit_periods)))
    ax1.set_xticklabels(exit_periods)
    ax1.set_yticks(range(len(entry_periods)))
    ax1.set_yticklabels(entry_periods)
    ax1.set_xlabel('Departing Channel Cycle', fontsize=11)
    ax1.set_ylabel('Admission channel cycle', fontsize=11)
    ax1.set_title(f'{stock_name} ({stock_code})  -  Cumulative Return (%)',
                  fontsize=12, fontweight='bold')
    for i in range(len(entry_periods)):
        for j in range(len(exit_periods)):
            val = returns_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 15 else 'black'
                ax1.text(j, i, f'{val:.1f}', ha='center', va='center',
                        fontsize=8, color=color)
    plt.colorbar(im1, ax=ax1, shrink=0.85)

    # Sharpe Ratio Heatmap
    im2 = ax2.imshow(sharpe_matrix, cmap='RdYlGn', aspect='auto',
                     vmin=-2, vmax=2)
    ax2.set_xticks(range(len(exit_periods)))
    ax2.set_xticklabels(exit_periods)
    ax2.set_yticks(range(len(entry_periods)))
    ax2.set_yticklabels(entry_periods)
    ax2.set_xlabel('Departing Channel Cycle', fontsize=11)
    ax2.set_ylabel('Admission channel cycle', fontsize=11)
    ax2.set_title(f'{stock_name} ({stock_code})  -  Sharpe Ratio',
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
    path = os.path.join(CHART_DIR, f'{stock_code}_Parameter Sensitivity Heatmap.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart5: Multi-Stock Strategy Comparison
#

def plot_multi_stock(stock_list, entry_period=20, exit_period=10):
    print('   Draw a multi-stock comparison chart....')
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
            print(f'     Skip {code} {name}: {e}')

    if not results:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5))

    x = np.arange(len(results))
    width = 0.35

    # Cumulative Return Comparison
    bars1 = ax1.bar(x - width/2, [r['strategy'] for r in results], width,
                    color='#0984e3', alpha=0.85, label=f'Turtle Strategy (Admission{entry_period}/Departing{exit_period})')
    bars2 = ax1.bar(x + width/2, [r['bh'] for r in results], width,
                    color='#b2bec3', alpha=0.7, label='Buy and hold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax1.set_ylabel('Cumulative Return (%)', fontsize=11)
    ax1.set_title('Comparison of returns of the multi-stock turtle strategy  -  Cumulative Return', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax1.axhline(y=0, color='black', linewidth=0.5)
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h,
                 f'{h:.1f}%' if h >= 0 else f'{h:.1f}%',
                 ha='center', va='bottom' if h >= 0 else 'top', fontsize=7.5)

    # Sharpe Ratio & MDD
    ax2.bar(x - width/2, [r['sharpe'] for r in results], width,
            color='#00b894', alpha=0.8, label='Sharpe Ratio')
    ax2_twin = ax2.twinx()
    ax2_twin.bar(x + width/2, [r['mdd'] for r in results], width,
                 color='#d63031', alpha=0.5, label='Maximum Drawdown (%)')
    ax2.set_xticks(x)
    ax2.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax2.set_ylabel('Sharpe Ratio', fontsize=11, color='#00b894')
    ax2_twin.set_ylabel('Maximum Drawdown (%)', fontsize=11, color='#d63031')
    ax2.set_title('Multi-Stock Turtle Strategy  -  Sharpe Ratio & Maximum Drawdown', fontsize=12, fontweight='bold')
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'Multi-Stock Strategy Comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart6: Stop-Loss Multiplier Sensitivity
#

def plot_stop_sensitivity(df, stock_name, stock_code):
    """Stop-Loss Multiplier Sensitivity  -  Single Figure Three Line: Cumulative Return / Sharp / MDD"""
    print('   Plotting Stop Loss Multiples Sensitivity...')
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

    # Left Axis: Cumulative Return + Sharpe Ratio
    line1 = ax1.plot(sms, returns, 'o-', color='#0984e3', linewidth=2.5, markersize=10, label='Cumulative Return (%)')
    line2 = ax1.plot(sms, sharpes, 's-', color='#00b894', linewidth=2.5, markersize=10, label='Sharpe Ratio')
    ax1.axhline(y=0, color='#636e72', linewidth=0.6, linestyle='--')
    ax1.set_xlabel('Stop Loss Multiples (xATR)', fontsize=12)
    ax1.set_ylabel('Cumulative Return (%) / Sharpe Ratio', fontsize=11, color='#2d3436')
    ax1.tick_params(axis='y', labelcolor='#2d3436')

    # Right axis: Maximum Drawdown
    ax2 = ax1.twinx()
    line3 = ax2.plot(sms, mdds, '^-', color='#d63031', linewidth=2.5, markersize=10, label='Maximum Drawdown (%)')
    ax2.set_ylabel('Maximum Drawdown (%)', fontsize=11, color='#d63031')
    ax2.tick_params(axis='y', labelcolor='#d63031')

    # Merge Legend
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')

    ax1.set_title(f'{stock_name} ({stock_code}) - Stop-Loss Multiplier Sensitivity\n'
                  'Wider stops can reduce forced exits but may deepen drawdowns; tighter stops may exit on noise.',
                  fontsize=13, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_Stop Loss Sensitivity.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Main program
#

def main():
    print('=' * 60)
    print('  Task4: Generate Turtle Strategy Report Chart (6 Zhang)')
    print('=' * 60)

    # Main target: Kweichow Moutai
    df_moutai = load_stock('600519', 'Kweichow Moutai', 'A-share')
    print(f'\n Kweichow Moutai: {len(df_moutai)} data item')

    # backtest
    print('\n Run Turtle Strategy Backtest (Admission=20day, Departing=10day, Stop-loss=2xATR)...')
    result = run_backtest(df_moutai, entry_period=20, exit_period=10,
                          atr_stop_mult=2.0)
    metrics = calc_metrics(result)

    print(f'   Cumulative Returns: {metrics["total_return"]:.2f}%')
    print(f'   Annualized return: {metrics["annual_return"]:.2f}%')
    print(f'   Maximum Drawdown: {metrics["mdd"]:.2f}%')
    print(f'   Sharpe Ratio: {metrics["sharpe"]:.4f}')
    print(f'   Win rate: {metrics["win_rate"]:.1f}%')
    print(f'   Number of transactions: {metrics["total_trades"]}')
    print(f'   Stop Loss Exit: {metrics["stop_exits"]} Next')

    # Generate Chart (6 Zhang)
    print('\n Generate Chart...')
    paths = {}

    # Figure1: Trading signals
    paths['signals'] = plot_turtle_signals(df_moutai, result, 'Kweichow Moutai', '600519',
                                           entry_period=20, exit_period=10)
    # Figure2: ATR/NValue trend (high fluctuation red bottom, Low volatility blue background)
    paths['atr'] = plot_atr_nvalue(df_moutai, result, 'Kweichow Moutai', '600519')

    # Figure3: Asset Curve and drawdown (Three-line comparison)
    paths['equity'] = plot_equity_and_drawdown(result, metrics, 'Kweichow Moutai', '600519')

    # Figure4: parametric heat diagram
    paths['heatmap'] = plot_param_heatmap(df_moutai, 'Kweichow Moutai', '600519')

    # Figure5: Stop Loss Sensitivity (Single Figure Three Line)
    paths['stop'] = plot_stop_sensitivity(df_moutai, 'Kweichow Moutai', '600519')

    # Figure6: Multi-stock comparison
    # Note: 510300 Data is currently unavailable. (Network Restrictions) , By BYD (002594) As the subject of Class III
    stock_list = [
        ('600519', 'Kweichow Moutai', 'A-share'),
        ('300750', 'CATL', 'A-share'),
        ('002594', 'BYD', 'A-share'),
        ('601318', 'Ping An of China', 'A-share'),
        ('000001', 'Ping An Bank', 'A-share'),
        ('00700', 'Tencent Holdings', 'Hong Kong equities'),
        ('09988', 'Alibaba', 'Hong Kong equities'),
    ]
    paths['multi'] = plot_multi_stock(stock_list, entry_period=20, exit_period=10)

    print(f'\n Chart saved: {CHART_DIR}')
    for name, p in paths.items():
        if p:
            print(f'   {name}: {os.path.basename(p)}')
    print('=' * 60)


if __name__ == '__main__':
    main()
