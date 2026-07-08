#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task3 Phase 3: 生成报告用静态图表 (matplotlib)
输出 5 张 PNG 到 data/charts/task3/
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch

# 中文字体
plt.rcParams['font.sans-serif'] = [
    'Heiti SC', 'STHeiti', 'PingFang SC',
    'Arial Unicode MS', 'SimHei', 'sans-serif'
]
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
CHART_DIR = os.path.join(BASE_DIR, '..', 'data', 'charts', 'task3')
os.makedirs(CHART_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════

def load_stock(code, name, market):
    filename = f"{code}_{name}_{market}_daily.csv"
    filepath = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(filepath, encoding='utf-8-sig')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


def calc_sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def run_backtest(df, short_period=5, long_period=15, initial_capital=1_000_000,
                 fee_rate=0.0003, slippage=0.0001):
    """双均线策略回测（避免未来函数）"""
    close = df['Close'].astype(float)
    ma_short = calc_sma(close, short_period)
    ma_long = calc_sma(close, long_period)

    cash = initial_capital
    shares = 0
    has_position = False
    trades = []
    equity_curve = []
    signals_buy = []
    signals_sell = []

    start_idx = max(short_period, long_period) + 1

    for t in range(start_idx, len(df)):
        price = close.iloc[t]
        date = df['Date'].iloc[t]
        equity = cash + shares * price
        equity_curve.append({'date': date, 'equity': equity})

        # 信号判断用 T-1 和 T-2 均线（避免未来函数）
        ma_s1 = ma_short.iloc[t-1]
        ma_l1 = ma_long.iloc[t-1]
        ma_s2 = ma_short.iloc[t-2]
        ma_l2 = ma_long.iloc[t-2]

        if pd.isna(ma_s1) or pd.isna(ma_l1) or pd.isna(ma_s2) or pd.isna(ma_l2):
            continue

        golden_cross = (ma_s1 > ma_l1) and (ma_s2 <= ma_l2)
        death_cross = (ma_s1 < ma_l1) and (ma_s2 >= ma_l2)

        if golden_cross and not has_position:
            buy_price = price * (1 + slippage)
            effective_cost = buy_price * (1 + fee_rate)
            shares = cash / effective_cost
            cost = shares * effective_cost
            cash = 0
            has_position = True
            trades.append({
                'buy_date': date, 'buy_price': buy_price,
                'shares': shares, 'cost': cost,
                'sell_date': None, 'sell_price': None, 'return_pct': None
            })
            signals_buy.append((date, buy_price))

        elif death_cross and has_position:
            sell_price = price * (1 - slippage)
            cash = shares * sell_price * (1 - fee_rate)
            trades[-1]['sell_date'] = date
            trades[-1]['sell_price'] = sell_price
            trades[-1]['return_pct'] = (cash / trades[-1]['cost'] - 1) * 100
            shares = 0
            has_position = False
            signals_sell.append((date, sell_price))

    # 强制平仓
    if has_position:
        final_price = close.iloc[-1] * (1 - slippage)
        cash = shares * final_price * (1 - fee_rate)
        trades[-1]['sell_date'] = df['Date'].iloc[-1]
        trades[-1]['sell_price'] = final_price
        trades[-1]['return_pct'] = (cash / trades[-1]['cost'] - 1) * 100

    # 完整权益曲线
    full_equity = []
    for t in range(start_idx):
        full_equity.append({'date': df['Date'].iloc[t], 'equity': initial_capital})
    full_equity.extend(equity_curve)

    final_equity = cash + shares * close.iloc[-1]

    # 买入持有基准
    bh_price0 = close.iloc[0] * (1 + slippage) * (1 + fee_rate)
    bh_shares = initial_capital / bh_price0
    bh_equity = [{'date': d, 'equity': bh_shares * p}
                 for d, p in zip(df['Date'], close)]
    bh_final = bh_shares * close.iloc[-1]

    return {
        'ma_short': ma_short, 'ma_long': ma_long,
        'trades': trades, 'signals_buy': signals_buy, 'signals_sell': signals_sell,
        'equity_curve': full_equity, 'final_equity': final_equity,
        'bh_equity_curve': bh_equity, 'bh_final_equity': bh_final,
    }


def calc_metrics(result, initial_capital=1_000_000, risk_free_rate=0.02):
    trades = [t for t in result['trades'] if t['sell_date'] is not None]
    equity = [e['equity'] for e in result['equity_curve']]

    if len(equity) < 2:
        return None

    final_equity = result['final_equity']
    total_return = (final_equity / initial_capital - 1) * 100

    days = max(1, (result['equity_curve'][-1]['date'] - result['equity_curve'][0]['date']).days)
    annual_return = (np.power(final_equity / initial_capital, 252.0 / days) - 1) * 100

    peak = -np.inf
    mdd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (e - peak) / peak * 100
        if dd < mdd:
            mdd = dd

    daily_rets = []
    for i in range(1, len(equity)):
        if equity[i-1] > 0:
            daily_rets.append(equity[i] / equity[i-1] - 1)

    sharpe = 0
    if len(daily_rets) > 1:
        mean_ret = np.mean(daily_rets)
        std_ret = np.std(daily_rets, ddof=0)
        if std_ret > 0:
            sharpe = np.sqrt(252) * (mean_ret - risk_free_rate / 252) / std_ret

    wins = [t for t in trades if t['return_pct'] > 0]
    losses = [t for t in trades if t['return_pct'] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = np.mean([t['return_pct'] for t in wins]) if wins else 0
    avg_loss = np.mean([abs(t['return_pct']) for t in losses]) if losses else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else None

    bh_total_return = (result['bh_final_equity'] / initial_capital - 1) * 100

    return {
        'total_return': total_return, 'annual_return': annual_return,
        'mdd': mdd, 'sharpe': sharpe, 'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio, 'total_trades': len(trades),
        'bh_total_return': bh_total_return, 'days': days,
    }


# ═══════════════════════════════════════════════════
# 图表1: 价格 + 双均线 + 交易信号
# ═══════════════════════════════════════════════════

def plot_strategy_signals(df, result, stock_name, stock_code, short_period=5, long_period=15):
    print('  📊 绘制策略信号图...')
    fig, ax = plt.subplots(figsize=(14, 7))

    dates = df['Date']
    close = df['Close'].astype(float)

    ax.plot(dates, close, color='#b2bec3', linewidth=1.0, alpha=0.7, label='收盘价')
    ax.plot(dates, result['ma_short'], color='#0984e3', linewidth=1.5, label=f'MA{short_period} (短均线)')
    ax.plot(dates, result['ma_long'], color='#e17055', linewidth=1.5, label=f'MA{long_period} (长均线)')

    # 买入信号（红色上箭头）
    if result['signals_buy']:
        buy_dates, buy_prices = zip(*result['signals_buy'])
        ax.scatter(buy_dates, buy_prices, marker='^', s=120, c='#d63031',
                   zorder=5, edgecolors='white', linewidth=0.5, label='买入(金叉)')

    # 卖出信号（绿色下箭头）
    if result['signals_sell']:
        sell_dates, sell_prices = zip(*result['signals_sell'])
        ax.scatter(sell_dates, sell_prices, marker='v', s=120, c='#00b894',
                   zorder=5, edgecolors='white', linewidth=0.5, label='卖出(死叉)')

    ax.set_title(f'{stock_name} ({stock_code}) — 双均线交叉策略交易信号\n'
                 f'(MA{short_period} & MA{long_period}, 前复权日线, '
                 f'{df["Date"].iloc[0].strftime("%Y-%m-%d")} ~ {df["Date"].iloc[-1].strftime("%Y-%m-%d")})',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('日期', fontsize=11)
    ax.set_ylabel('价格 (元)', fontsize=11)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_策略信号图.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表2: 资产曲线对比
# ═══════════════════════════════════════════════════

def plot_equity_comparison(result, metrics, stock_name, stock_code):
    print('  📊 绘制资产曲线对比图...')
    fig, ax = plt.subplots(figsize=(14, 5.5))

    eq_dates = [e['date'] for e in result['equity_curve']]
    eq_values = [e['equity'] for e in result['equity_curve']]
    bh_dates = [e['date'] for e in result['bh_equity_curve']]
    bh_values = [e['equity'] for e in result['bh_equity_curve']]

    ax.plot(eq_dates, eq_values, color='#0984e3', linewidth=2, label='策略资产')
    ax.plot(bh_dates, bh_values, color='#b2bec3', linewidth=1.2,
            linestyle='--', label='买入持有')
    ax.axhline(y=1_000_000, color='#636e72', linewidth=0.6, linestyle=':',
               alpha=0.5, label='初始资金')

    ax.set_title(f'{stock_name} ({stock_code}) — 资产曲线对比 (策略 vs 买入持有)\n'
                 f'策略累计回报: {metrics["total_return"]:.2f}% | '
                 f'买入持有: {metrics["bh_total_return"]:.2f}% | '
                 f'超额收益: {metrics["total_return"] - metrics["bh_total_return"]:.2f}%',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('日期', fontsize=11)
    ax.set_ylabel('资产 (元)', fontsize=11)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1e4:.0f}万'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_资产曲线对比.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表3: 回撤曲线
# ═══════════════════════════════════════════════════

def plot_drawdown(result, metrics, stock_name, stock_code):
    print('  📊 绘制回撤曲线图...')
    fig, ax = plt.subplots(figsize=(14, 5))

    equity_values = [e['equity'] for e in result['equity_curve']]
    dates = [e['date'] for e in result['equity_curve']]

    peak = -np.inf
    dd_series = []
    for eq in equity_values:
        if eq > peak:
            peak = eq
        dd_series.append((eq - peak) / peak * 100)

    ax.fill_between(dates, dd_series, 0, color='#d63031', alpha=0.15)
    ax.plot(dates, dd_series, color='#d63031', linewidth=1)
    ax.axhline(y=0, color='#636e72', linewidth=0.6, linestyle='--')

    ax.set_title(f'{stock_name} ({stock_code}) — 回撤曲线\n'
                 f'最大回撤 (MDD): {metrics["mdd"]:.2f}%',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('日期', fontsize=11)
    ax.set_ylabel('回撤 (%)', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_回撤曲线.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表4: 参数敏感性热力图
# ═══════════════════════════════════════════════════

def plot_param_heatmap(df, stock_name, stock_code):
    print('  📊 绘制参数敏感性热力图...')
    short_periods = [3, 5, 10, 15, 20, 30]
    long_periods = [10, 15, 20, 30, 40, 60]

    returns_matrix = np.zeros((len(short_periods), len(long_periods)))
    sharpe_matrix = np.zeros((len(short_periods), len(long_periods)))

    for i, sp in enumerate(short_periods):
        for j, lp in enumerate(long_periods):
            if sp >= lp:
                returns_matrix[i, j] = np.nan
                sharpe_matrix[i, j] = np.nan
                continue
            result = run_backtest(df, short_period=sp, long_period=lp)
            m = calc_metrics(result)
            if m:
                returns_matrix[i, j] = m['total_return']
                sharpe_matrix[i, j] = m['sharpe']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5))

    # 累计回报热力图
    im1 = ax1.imshow(returns_matrix, cmap='RdYlGn', aspect='auto', vmin=-30, vmax=30)
    ax1.set_xticks(range(len(long_periods)))
    ax1.set_xticklabels(long_periods)
    ax1.set_yticks(range(len(short_periods)))
    ax1.set_yticklabels(short_periods)
    ax1.set_xlabel('长均线周期', fontsize=11)
    ax1.set_ylabel('短均线周期', fontsize=11)
    ax1.set_title(f'{stock_name} ({stock_code}) — 累计回报 (%)', fontsize=12, fontweight='bold')
    for i in range(len(short_periods)):
        for j in range(len(long_periods)):
            val = returns_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 15 else 'black'
                ax1.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=8, color=color)
    plt.colorbar(im1, ax=ax1, shrink=0.85)

    # 夏普比率热力图
    im2 = ax2.imshow(sharpe_matrix, cmap='RdYlGn', aspect='auto', vmin=-2, vmax=2)
    ax2.set_xticks(range(len(long_periods)))
    ax2.set_xticklabels(long_periods)
    ax2.set_yticks(range(len(short_periods)))
    ax2.set_yticklabels(short_periods)
    ax2.set_xlabel('长均线周期', fontsize=11)
    ax2.set_ylabel('短均线周期', fontsize=11)
    ax2.set_title(f'{stock_name} ({stock_code}) — 夏普比率', fontsize=12, fontweight='bold')
    for i in range(len(short_periods)):
        for j in range(len(long_periods)):
            val = sharpe_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 0.8 else 'black'
                ax2.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=8, color=color)
    plt.colorbar(im2, ax=ax2, shrink=0.85)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_参数敏感性热力图.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 图表5: 多股票策略收益对比
# ═══════════════════════════════════════════════════

def plot_multi_stock(stock_list, short_period=5, long_period=15):
    print('  📊 绘制多股票对比图...')
    results = []
    for code, name, market in stock_list:
        try:
            df = load_stock(code, name, market)
            result = run_backtest(df, short_period=short_period, long_period=long_period)
            metrics = calc_metrics(result)
            if metrics:
                results.append({
                    'label': f'{name}\n({code})',
                    'strategy': metrics['total_return'],
                    'bh': metrics['bh_total_return'],
                    'sharpe': metrics['sharpe'],
                    'mdd': metrics['mdd'],
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
                    color='#0984e3', alpha=0.85, label=f'双均线策略 (MA{short_period}/{long_period})')
    bars2 = ax1.bar(x + width/2, [r['bh'] for r in results], width,
                    color='#b2bec3', alpha=0.7, label='买入持有')
    ax1.set_xticks(x)
    ax1.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax1.set_ylabel('累计回报 (%)', fontsize=11)
    ax1.set_title('多股票策略收益对比 — 累计回报', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax1.axhline(y=0, color='black', linewidth=0.5)
    # 标注数值
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h,
                 f'{h:.1f}%' if h >= 0 else f'{h:.1f}%',
                 ha='center', va='bottom' if h >= 0 else 'top', fontsize=7.5)

    # 夏普比率 & MDD
    x2 = np.arange(len(results))
    ax2.bar(x2 - width/2, [r['sharpe'] for r in results], width,
            color='#00b894', alpha=0.8, label='夏普比率')
    ax2_twin = ax2.twinx()
    ax2_twin.bar(x2 + width/2, [r['mdd'] for r in results], width,
                 color='#d63031', alpha=0.5, label='最大回撤 (%)')
    ax2.set_xticks(x2)
    ax2.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax2.set_ylabel('夏普比率', fontsize=11, color='#00b894')
    ax2_twin.set_ylabel('最大回撤 (%)', fontsize=11, color='#d63031')
    ax2.set_title('多股票策略 — 夏普比率 & 最大回撤', fontsize=12, fontweight='bold')

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, '多股票策略对比.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ═══════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════

def main():
    print('=' * 60)
    print('  Task3: 生成报告图表')
    print('=' * 60)

    # 主力标的：贵州茅台
    df_moutai = load_stock('600519', '贵州茅台', 'A股')
    print(f'\n📂 贵州茅台: {len(df_moutai)} 条数据')

    # 回测
    print('\n⏳ 运行回测 (MA5 & MA15)...')
    global short_period, long_period
    short_period, long_period = 5, 15
    result = run_backtest(df_moutai, short_period, long_period)
    metrics = calc_metrics(result)

    print(f'   累计回报: {metrics["total_return"]:.2f}%')
    print(f'   年化收益: {metrics["annual_return"]:.2f}%')
    print(f'   最大回撤: {metrics["mdd"]:.2f}%')
    print(f'   夏普比率: {metrics["sharpe"]:.2f}')
    print(f'   胜率: {metrics["win_rate"]:.1f}%')
    print(f'   交易次数: {metrics["total_trades"]}')

    # 生成图表
    print('\n📊 生成图表...')
    paths = {}

    paths['signals'] = plot_strategy_signals(df_moutai, result, '贵州茅台', '600519', short_period, long_period)
    paths['equity'] = plot_equity_comparison(result, metrics, '贵州茅台', '600519')
    paths['drawdown'] = plot_drawdown(result, metrics, '贵州茅台', '600519')
    paths['heatmap'] = plot_param_heatmap(df_moutai, '贵州茅台', '600519')

    # 多股票对比
    stock_list = [
        ('600519', '贵州茅台', 'A股'),
        ('601318', '中国平安', 'A股'),
        ('300750', '宁德时代', 'A股'),
        ('002594', '比亚迪', 'A股'),
        ('00700', '腾讯控股', '港股'),
        ('09988', '阿里巴巴', '港股'),
    ]
    paths['multi'] = plot_multi_stock(stock_list, short_period=5, long_period=15)

    print(f'\n✅ 图表已保存到: {CHART_DIR}')
    for name, p in paths.items():
        if p:
            print(f'   {name}: {os.path.basename(p)}')
    print('=' * 60)


if __name__ == '__main__':
    main()
