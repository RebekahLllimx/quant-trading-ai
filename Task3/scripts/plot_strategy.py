#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task3 Phase 3: Generate static charts for reports (matplotlib)
Output 5 PNG files to artifacts/charts/task3/
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

# Chinese fonts
plt.rcParams['font.sans-serif'] = [
    'Heiti SC', 'STHeiti', 'PingFang SC',
    'Arial Unicode MS', 'SimHei', 'sans-serif'
]
plt.rcParams['axes.unicode_minus'] = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
CHART_DIR = os.path.join(BASE_DIR, '..', 'artifacts', 'charts', 'task3')
os.makedirs(CHART_DIR, exist_ok=True)

#
# Tool Functions
#

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
    """Double-moving-average strategy backtest (Avoid future functions) """
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

        # For signal judgment T-1 and T-2 Moving average (Avoid future functions)
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

    # Forced liquidation
    if has_position:
        final_price = close.iloc[-1] * (1 - slippage)
        cash = shares * final_price * (1 - fee_rate)
        trades[-1]['sell_date'] = df['Date'].iloc[-1]
        trades[-1]['sell_price'] = final_price
        trades[-1]['return_pct'] = (cash / trades[-1]['cost'] - 1) * 100

    # complete equity curve
    full_equity = []
    for t in range(start_idx):
        full_equity.append({'date': df['Date'].iloc[t], 'equity': initial_capital})
    full_equity.extend(equity_curve)

    final_equity = cash + shares * close.iloc[-1]

    # Buy-to-hold benchmark
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


#
# Chart1: Price + dual moving-average + Trading signals
#

def plot_strategy_signals(df, result, stock_name, stock_code, short_period=5, long_period=15):
    print('   Draw strategy signal diagram...')
    fig, ax = plt.subplots(figsize=(14, 7))

    dates = df['Date']
    close = df['Close'].astype(float)

    ax.plot(dates, close, color='#b2bec3', linewidth=1.0, alpha=0.7, label='Close')
    ax.plot(dates, result['ma_short'], color='#0984e3', linewidth=1.5, label=f'MA{short_period} (short moving average)')
    ax.plot(dates, result['ma_long'], color='#e17055', linewidth=1.5, label=f'MA{long_period} (Long-term moving average)')

    # Buy signal (Red upward arrow)
    if result['signals_buy']:
        buy_dates, buy_prices = zip(*result['signals_buy'])
        ax.scatter(buy_dates, buy_prices, marker='^', s=120, c='#d63031',
                   zorder=5, edgecolors='white', linewidth=0.5, label='Buy(Golden Cross)')

    # Sell signal (Green Down Arrow)
    if result['signals_sell']:
        sell_dates, sell_prices = zip(*result['signals_sell'])
        ax.scatter(sell_dates, sell_prices, marker='v', s=120, c='#00b894',
                   zorder=5, edgecolors='white', linewidth=0.5, label='Sell(death cross)')

    ax.set_title(f'{stock_name} ({stock_code})  -  Dual moving-average crossover strategy trading signals\n'
                 f'(MA{short_period} & MA{long_period}, Adjusted Close Daily Chart, '
                 f'{df["Date"].iloc[0].strftime("%Y-%m-%d")} ~ {df["Date"].iloc[-1].strftime("%Y-%m-%d")})',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('Price (yuan)', fontsize=11)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_Strategy Signal Chart.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart2: Asset Curve Comparison
#

def plot_equity_comparison(result, metrics, stock_name, stock_code):
    print('   Draw asset curve comparison chart...')
    fig, ax = plt.subplots(figsize=(14, 5.5))

    eq_dates = [e['date'] for e in result['equity_curve']]
    eq_values = [e['equity'] for e in result['equity_curve']]
    bh_dates = [e['date'] for e in result['bh_equity_curve']]
    bh_values = [e['equity'] for e in result['bh_equity_curve']]

    ax.plot(eq_dates, eq_values, color='#0984e3', linewidth=2, label='Strategic Assets')
    ax.plot(bh_dates, bh_values, color='#b2bec3', linewidth=1.2,
            linestyle='--', label='Buy and hold')
    ax.axhline(y=1_000_000, color='#636e72', linewidth=0.6, linestyle=':',
               alpha=0.5, label='Initial funding')

    ax.set_title(f'{stock_name} ({stock_code})  -  Asset Curve Comparison (Strategy vs Buy and hold)\n'
                 f'Strategy Cumulative Returns: {metrics["total_return"]:.2f}% | '
                 f'Buy and hold: {metrics["bh_total_return"]:.2f}% | '
                 f'Excess return: {metrics["total_return"] - metrics["bh_total_return"]:.2f}%',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('Assets (yuan)', fontsize=11)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1e4:.0f}million'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_Asset Curve Comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart3: Drawdown Curve
#

def plot_drawdown(result, metrics, stock_name, stock_code):
    print('   Plot the pullback curve...')
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

    ax.set_title(f'{stock_name} ({stock_code})  -  Drawdown Curve\n'
                 f'Maximum Drawdown (MDD): {metrics["mdd"]:.2f}%',
                 fontsize=13, fontweight='bold')
    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('drawdown (%)', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
    fig.autofmt_xdate()

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_Drawdown Curve.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart4: Parameter Sensitivity Heatmap
#

def plot_param_heatmap(df, stock_name, stock_code):
    print('   Draw parameter sensitivity heat map...')
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

    # Cumulative return heatmap
    im1 = ax1.imshow(returns_matrix, cmap='RdYlGn', aspect='auto', vmin=-30, vmax=30)
    ax1.set_xticks(range(len(long_periods)))
    ax1.set_xticklabels(long_periods)
    ax1.set_yticks(range(len(short_periods)))
    ax1.set_yticklabels(short_periods)
    ax1.set_xlabel('Long moving average period', fontsize=11)
    ax1.set_ylabel('Short moving average period', fontsize=11)
    ax1.set_title(f'{stock_name} ({stock_code})  -  Cumulative Return (%)', fontsize=12, fontweight='bold')
    for i in range(len(short_periods)):
        for j in range(len(long_periods)):
            val = returns_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 15 else 'black'
                ax1.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=8, color=color)
    plt.colorbar(im1, ax=ax1, shrink=0.85)

    # Sharpe Ratio Heatmap
    im2 = ax2.imshow(sharpe_matrix, cmap='RdYlGn', aspect='auto', vmin=-2, vmax=2)
    ax2.set_xticks(range(len(long_periods)))
    ax2.set_xticklabels(long_periods)
    ax2.set_yticks(range(len(short_periods)))
    ax2.set_yticklabels(short_periods)
    ax2.set_xlabel('Long moving average period', fontsize=11)
    ax2.set_ylabel('Short moving average period', fontsize=11)
    ax2.set_title(f'{stock_name} ({stock_code})  -  Sharpe Ratio', fontsize=12, fontweight='bold')
    for i in range(len(short_periods)):
        for j in range(len(long_periods)):
            val = sharpe_matrix[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 0.8 else 'black'
                ax2.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=8, color=color)
    plt.colorbar(im2, ax=ax2, shrink=0.85)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, f'{stock_code}_Parameter Sensitivity Heatmap.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Chart5: Multi-stock strategy returns comparison.
#

def plot_multi_stock(stock_list, short_period=5, long_period=15):
    print('   Draw a multi-stock comparison chart....')
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
            print(f'     Skip {code} {name}: {e}')

    if not results:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5))

    x = np.arange(len(results))
    width = 0.35

    # Cumulative Return Comparison
    bars1 = ax1.bar(x - width/2, [r['strategy'] for r in results], width,
                    color='#0984e3', alpha=0.85, label=f'dual moving-average strategy (MA{short_period}/{long_period})')
    bars2 = ax1.bar(x + width/2, [r['bh'] for r in results], width,
                    color='#b2bec3', alpha=0.7, label='Buy and hold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax1.set_ylabel('Cumulative Return (%)', fontsize=11)
    ax1.set_title('Multi-stock strategy returns comparison.  -  Cumulative Return', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax1.axhline(y=0, color='black', linewidth=0.5)
    # Dimension Value
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h,
                 f'{h:.1f}%' if h >= 0 else f'{h:.1f}%',
                 ha='center', va='bottom' if h >= 0 else 'top', fontsize=7.5)

    # Sharpe Ratio & MDD
    x2 = np.arange(len(results))
    ax2.bar(x2 - width/2, [r['sharpe'] for r in results], width,
            color='#00b894', alpha=0.8, label='Sharpe Ratio')
    ax2_twin = ax2.twinx()
    ax2_twin.bar(x2 + width/2, [r['mdd'] for r in results], width,
                 color='#d63031', alpha=0.5, label='Maximum Drawdown (%)')
    ax2.set_xticks(x2)
    ax2.set_xticklabels([r['label'] for r in results], fontsize=9)
    ax2.set_ylabel('Sharpe Ratio', fontsize=11, color='#00b894')
    ax2_twin.set_ylabel('Maximum Drawdown (%)', fontsize=11, color='#d63031')
    ax2.set_title('Multi-Stock Strategy  -  Sharpe Ratio & Maximum Drawdown', fontsize=12, fontweight='bold')

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    plt.tight_layout()
    path = os.path.join(CHART_DIR, 'Multi-Stock Strategy Comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


#
# Main program
#

def main():
    print('=' * 60)
    print('  Task3: Generate report charts')
    print('=' * 60)

    # Main target: Kweichow Moutai
    df_moutai = load_stock('600519', 'Kweichow Moutai', 'A-share')
    print(f'\n Kweichow Moutai: {len(df_moutai)} data item')

    # backtest
    print('\n Run Backtest (MA5 & MA15)...')
    global short_period, long_period
    short_period, long_period = 5, 15
    result = run_backtest(df_moutai, short_period, long_period)
    metrics = calc_metrics(result)

    print(f'   Cumulative Returns: {metrics["total_return"]:.2f}%')
    print(f'   Annualized return: {metrics["annual_return"]:.2f}%')
    print(f'   Maximum Drawdown: {metrics["mdd"]:.2f}%')
    print(f'   Sharpe Ratio: {metrics["sharpe"]:.2f}')
    print(f'   Win rate: {metrics["win_rate"]:.1f}%')
    print(f'   Number of transactions: {metrics["total_trades"]}')

    # Generate Chart
    print('\n Generate Chart...')
    paths = {}

    paths['signals'] = plot_strategy_signals(df_moutai, result, 'Kweichow Moutai', '600519', short_period, long_period)
    paths['equity'] = plot_equity_comparison(result, metrics, 'Kweichow Moutai', '600519')
    paths['drawdown'] = plot_drawdown(result, metrics, 'Kweichow Moutai', '600519')
    paths['heatmap'] = plot_param_heatmap(df_moutai, 'Kweichow Moutai', '600519')

    # Multi-stock comparison
    stock_list = [
        ('600519', 'Kweichow Moutai', 'A-share'),
        ('601318', 'Ping An of China', 'A-share'),
        ('300750', 'CATL', 'A-share'),
        ('002594', 'BYD', 'A-share'),
        ('00700', 'Tencent Holdings', 'Hong Kong equities'),
        ('09988', 'Alibaba', 'Hong Kong equities'),
    ]
    paths['multi'] = plot_multi_stock(stock_list, short_period=5, long_period=15)

    print(f'\n Chart saved: {CHART_DIR}')
    for name, p in paths.items():
        if p:
            print(f'   {name}: {os.path.basename(p)}')
    print('=' * 60)


if __name__ == '__main__':
    main()
