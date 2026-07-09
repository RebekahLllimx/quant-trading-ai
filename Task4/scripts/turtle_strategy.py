#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海龟交易策略回测引擎 (Turtle Trading Strategy Backtest Engine)

核心组件:
  1. 高低价格通道 (Donchian Channel) — 突破入场信号
  2. ATR (平均真实波幅) — 波动率度量, 仓位计算, 止损依据
  3. 交易信号生成 — 入场/加仓/止损/离场
  4. 回测引擎 — 模拟交易, 成本计算
  5. 绩效评估 — 累计回报, 年化收益, MDD, 夏普比率, 胜率, 盈亏比

参考: Richard Dennis & William Eckhardt, "The Original Turtle Trading Rules" (1983)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


# ═══════════════════════════════════════════════════════════════
# 1. 指标计算
# ═══════════════════════════════════════════════════════════════

def calc_donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    计算唐奇安通道 (Donchian Channel) — 高低价格通道

    参数:
        df: 包含 High, Low 列的 DataFrame
        period: 通道周期, 默认 20 (海龟 System 1 入场周期)

    返回:
        pd.DataFrame: 包含 DC_High (上轨), DC_Low (下轨), DC_Mid (中轨) 三列
    """
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    dc_high = high.rolling(window=period, min_periods=period).max()
    dc_low = low.rolling(window=period, min_periods=period).min()
    dc_mid = (dc_high + dc_low) / 2.0

    return pd.DataFrame({
        'DC_High': dc_high.round(4),
        'DC_Low': dc_low.round(4),
        'DC_Mid': dc_mid.round(4),
    })


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    计算 ATR (Average True Range) — 平均真实波幅

    True Range = max(
        High - Low,              # 当日振幅
        |High - PrevClose|,      # 今高与昨收缺口 (向上跳空)
        |Low - PrevClose|        # 今低与昨收缺口 (向下跳空)
    )
    ATR = WilderSmooth(TR, N)    # α = 1/N 的指数平滑

    参数:
        df: 包含 High, Low, Close 列的 DataFrame
        period: ATR 周期, 默认 14

    返回:
        pd.Series: ATR 序列
    """
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)
    close_prev = close.shift(1)

    tr = pd.concat([
        (high - low),
        (high - close_prev).abs(),
        (low - close_prev).abs(),
    ], axis=1).max(axis=1)

    # Wilder 平滑: α = 1/N
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    atr.name = 'ATR'
    return atr.round(4)


def calc_n_value(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    计算 N 值 (海龟策略的核心波动率度量)

    N 值就是 period 周期的 ATR, 但在海龟原版中用 20 日.
    N 值用途:
      - 仓位大小 = (账户 × 1%) / N
      - 止损距离 = 2 × N
      - 加仓间隔 = 0.5 × N

    参数:
        df: 包含 High, Low, Close 列的 DataFrame
        period: N 值周期, 默认 20

    返回:
        pd.Series: N 值序列
    """
    return calc_atr(df, period=period)


# ═══════════════════════════════════════════════════════════════
# 2. 交易信号生成
# ═══════════════════════════════════════════════════════════════

def generate_signals(df: pd.DataFrame,
                     entry_period: int = 20,
                     exit_period: int = 10,
                     atr_period: int = 20,
                     atr_stop_mult: float = 2.0,
                     use_filter: bool = True) -> pd.DataFrame:
    """
    生成海龟策略交易信号

    海龟交易规则 (简化版, 仅做多):
      1. 入场: 收盘价突破 entry_period 日最高价通道上轨 → 买入
      2. 加仓: 价格每上涨 0.5×ATR, 加仓一次 (最多 4 次)
      3. 止损: 价格跌破入场价 − atr_stop_mult × ATR → 止损卖出
      4. 离场: 收盘价跌破 exit_period 日最低价通道下轨 → 卖出
      5. 过滤: 如果上一次突破是亏损的, 跳过下一次 System 1 入场信号 (可选)

    避免未来函数:
      - 入场信号基于 T-1 日的通道数据 (T 日开盘前已可知)
      - T 日以收盘价成交

    参数:
        df: 包含 OHLC 数据的 DataFrame
        entry_period: 入场通道周期, 默认 20 (海龟 System 1)
        exit_period: 离场通道周期, 默认 10 (海龟 System 1)
        atr_period: ATR 周期, 默认 20
        atr_stop_mult: 止损 ATR 倍数, 默认 2.0
        use_filter: 是否使用亏损过滤规则

    返回:
        pd.DataFrame: 附加信号列的 DataFrame
    """
    result = df.copy()
    close = result['Close'].astype(float)
    high = result['High'].astype(float)
    low = result['Low'].astype(float)

    # 计算通道
    dc_entry = calc_donchian(result, period=entry_period)
    dc_exit = calc_donchian(result, period=exit_period)
    n_value = calc_n_value(result, period=atr_period)

    result['Entry_High'] = dc_entry['DC_High']
    result['Exit_Low'] = dc_exit['DC_Low']
    result['N_Value'] = n_value

    # 信号列初始化
    result['Signal'] = ''          # BUY / ADD / STOP / EXIT
    result['Signal_Price'] = np.nan

    # 遍历生成信号
    max_period = max(entry_period, exit_period, atr_period)
    last_trade_lost = False  # 海龟过滤规则

    for t in range(max_period + 2, len(result)):
        # T-1 日的通道值 (避免未来函数)
        entry_high_prev = result['Entry_High'].iloc[t - 1]
        exit_low_prev = result['Exit_Low'].iloc[t - 1]
        entry_high_prev2 = result['Entry_High'].iloc[t - 2]

        if pd.isna(entry_high_prev) or pd.isna(exit_low_prev):
            continue

        # 入场信号: 收盘价突破 entry_period 日最高
        price_prev = close.iloc[t - 1]
        price_prev2 = close.iloc[t - 2]

        breakout_up = (price_prev > entry_high_prev and
                       price_prev2 <= entry_high_prev2)

        if breakout_up:
            if use_filter and last_trade_lost:
                # 跳过此次信号 (但记录)
                result.loc[result.index[t], 'Signal'] = 'FILTERED_BUY'
                last_trade_lost = False
            else:
                result.loc[result.index[t], 'Signal'] = 'BUY'
                result.loc[result.index[t], 'Signal_Price'] = close.iloc[t]

    return result


# ═══════════════════════════════════════════════════════════════
# 3. 回测引擎
# ═══════════════════════════════════════════════════════════════

def run_backtest(df: pd.DataFrame,
                 entry_period: int = 20,
                 exit_period: int = 10,
                 atr_period: int = 20,
                 atr_stop_mult: float = 2.0,
                 risk_percent: float = 0.02,
                 initial_capital: float = 1_000_000,
                 fee_rate: float = 0.0003,
                 slippage: float = 0.0001,
                 use_filter: bool = True,
                 max_units: int = 4,
                 pyramid_atr_mult: float = 0.5) -> Dict:
    """
    海龟策略回测引擎 (仅做多)

    海龟交易系统核心逻辑:
      1. 入场: 价格突破 entry_period 日高点 → 全仓买入
      2. 动态止损: 持仓期间止损价 = 入场价 − atr_stop_mult × ATR_t (只上移不下移)
      3. 离场: 价格跌破 exit_period 日低点 → 卖出入场
      4. 仓位: 初始仓位基于 N 值 — shares = (capital × risk%) / N
      5. 强制平仓: 回测最后一日若仍持仓则按收盘价卖出

    避免未来函数:
      - 所有信号判断基于 T-1 日数据
      - T 日以收盘价执行交易

    参数:
        df: OHLCV 数据
        entry_period: 入场通道周期 (海龟 System 1 = 20)
        exit_period: 离场通道周期 (海龟 System 1 = 10)
        atr_period: ATR/N 值计算周期 (默认 20)
        atr_stop_mult: 止损倍数 (默认 2.0)
        risk_percent: 单笔风险比例 (默认 2%)
        initial_capital: 初始资金
        fee_rate: 手续费率 (默认 0.03%)
        slippage: 滑点率 (默认 0.01%)
        use_filter: 是否使用亏损过滤规则
        max_units: 最大加仓次数
        pyramid_atr_mult: 加仓间隔 ATR 倍数

    返回:
        dict: {
            'df': 附加信号列的 DataFrame,
            'trades': 交易明细列表,
            'equity_curve': 每日权益,
            'signals_buy': 买入信号列表,
            'signals_sell': 卖出信号列表,
            'signals_stop': 止损信号列表,
            'final_equity': 最终权益,
            'bh_equity_curve': 买入持有权益曲线,
            'bh_final_equity': 买入持有最终权益,
        }
    """
    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    # 计算指标
    dc_entry = calc_donchian(df, period=entry_period)
    dc_exit = calc_donchian(df, period=exit_period)
    n_value = calc_n_value(df, period=atr_period)

    # 初始化状态
    cash = initial_capital
    shares = 0
    has_position = False
    entry_price = 0.0
    stop_price = 0.0  # 动态止损价
    units_held = 0  # 当前加仓次数
    last_trade_lost = False

    trades = []
    equity_curve = []
    signals_buy = []
    signals_sell = []
    signals_stop = []

    start_idx = max(entry_period, exit_period, atr_period) + 2

    for t in range(start_idx, len(df)):
        price_t = close.iloc[t]
        date_t = df['Date'].iloc[t]
        n_t = n_value.iloc[t]
        high_t = high.iloc[t]
        low_t = low.iloc[t]

        # 计算当日权益
        equity = cash + shares * price_t
        equity_curve.append({
            'date': date_t,
            'equity': equity,
            'cash': cash,
            'shares': shares,
        })

        # ---- 信号判断 (海龟原版: T 日高/低价触发 T-1 日通道) ----
        # T-1 日的通道值在 T 日开盘前已知, T 日盘中高/低价触发即成交
        entry_high_prev = dc_entry['DC_High'].iloc[t - 1]
        exit_low_prev = dc_exit['DC_Low'].iloc[t - 1]

        if pd.isna(entry_high_prev) or pd.isna(exit_low_prev) or pd.isna(n_t):
            continue

        # 入场信号: T 日最高价突破 T-1 日入场通道上轨 (海龟原版 Stop Order)
        # 同时要求 T-1 收盘价未超过 T-2 通道 (避免连续突破)
        prev2_high = dc_entry['DC_High'].iloc[t - 2]
        prev_close = close.iloc[t - 1]
        breakout_up = (high_t > entry_high_prev and
                       (pd.isna(prev2_high) or prev_close <= prev2_high))

        # 离场信号: T 日最低价跌破 T-1 日离场通道下轨
        exit_signal = low_t < exit_low_prev

        # 止损判断: 持仓期间, 当日最低价触及止损价
        stop_hit = False
        if has_position and stop_price > 0:
            stop_hit = low_t <= stop_price

        # ---- 执行交易 ----
        if breakout_up and not has_position:
            # 过滤规则: 上一笔亏损则跳过
            if use_filter and last_trade_lost:
                last_trade_lost = False
                continue

            # 买入
            buy_price = price_t * (1 + slippage)
            # 仓位: 严格推导版 — Shares = RiskAmount / (k × N)
            # RiskAmount = Cash × risk_percent
            # StopDistance = atr_stop_mult × N_t (每股止损距离)
            # 当止损触发时, 实际亏损 ≈ RiskAmount
            if n_t > 0:
                risk_amount = cash * risk_percent
                stop_distance = atr_stop_mult * n_t
                safe_shares = risk_amount / stop_distance
                # 不超过可用资金
                max_shares = cash / (buy_price * (1 + fee_rate))
                shares = min(safe_shares, max_shares)
            else:
                shares = cash / (buy_price * (1 + fee_rate))

            cost = shares * buy_price * (1 + fee_rate)
            if cost > cash:
                shares = cash / (buy_price * (1 + fee_rate))
                cost = cash

            cash -= cost
            entry_price = buy_price
            stop_price = entry_price - atr_stop_mult * n_t
            has_position = True
            units_held = 1

            trades.append({
                'buy_date': date_t,
                'buy_price': round(buy_price, 4),
                'shares': round(shares, 2),
                'cost': round(cost, 2),
                'sell_date': None,
                'sell_price': None,
                'return_pct': None,
                'exit_reason': None,
            })
            signals_buy.append((date_t, buy_price))

        elif has_position:
            # 动态止损价上移 (只上移不下移 — 海龟止损铁律)
            if n_t > 0 and not pd.isna(n_t):
                new_stop = entry_price - atr_stop_mult * n_t
                # 对于盈利头寸, 考虑使用更紧的止损
                if price_t > entry_price:
                    trailing_stop = price_t - atr_stop_mult * n_t
                    new_stop = max(new_stop, trailing_stop)
                stop_price = max(stop_price, new_stop)

            # 检查止损
            if stop_hit:
                sell_price = stop_price * (1 - slippage)
                cash += shares * sell_price * (1 - fee_rate)
                trades[-1]['sell_date'] = date_t
                trades[-1]['sell_price'] = round(sell_price, 4)
                trades[-1]['return_pct'] = round(
                    (shares * sell_price * (1 - fee_rate) / trades[-1]['cost'] - 1) * 100, 2
                )
                trades[-1]['exit_reason'] = '止损'
                last_trade_lost = trades[-1]['return_pct'] < 0
                shares = 0
                has_position = False
                stop_price = 0
                units_held = 0
                signals_stop.append((date_t, sell_price))
                signals_sell.append((date_t, sell_price))

            # 检查离场信号
            elif exit_signal:
                sell_price = price_t * (1 - slippage)
                cash += shares * sell_price * (1 - fee_rate)
                trades[-1]['sell_date'] = date_t
                trades[-1]['sell_price'] = round(sell_price, 4)
                trades[-1]['return_pct'] = round(
                    (shares * sell_price * (1 - fee_rate) / trades[-1]['cost'] - 1) * 100, 2
                )
                trades[-1]['exit_reason'] = '离场信号'
                last_trade_lost = trades[-1]['return_pct'] < 0
                shares = 0
                has_position = False
                stop_price = 0
                units_held = 0
                signals_sell.append((date_t, sell_price))

    # 强制平仓
    if has_position:
        final_price = close.iloc[-1] * (1 - slippage)
        cash += shares * final_price * (1 - fee_rate)
        trades[-1]['sell_date'] = df['Date'].iloc[-1]
        trades[-1]['sell_price'] = round(final_price, 4)
        trades[-1]['return_pct'] = round(
            (shares * final_price * (1 - fee_rate) / trades[-1]['cost'] - 1) * 100, 2
        )
        trades[-1]['exit_reason'] = '强制平仓'

    # 完整权益曲线 (前 start_idx 天持有现金)
    full_equity = []
    for i in range(start_idx):
        full_equity.append({
            'date': df['Date'].iloc[i],
            'equity': initial_capital,
            'cash': initial_capital,
            'shares': 0,
        })
    full_equity.extend(equity_curve)

    final_equity = cash + shares * close.iloc[-1]

    # 买入持有基准
    bh_price0 = close.iloc[0] * (1 + slippage) * (1 + fee_rate)
    bh_shares = initial_capital / bh_price0
    bh_equity = [{'date': d, 'equity': bh_shares * p}
                 for d, p in zip(df['Date'], close)]
    bh_final = bh_shares * close.iloc[-1]

    return {
        'df': df,
        'dc_entry': dc_entry,
        'dc_exit': dc_exit,
        'n_value': n_value,
        'trades': trades,
        'equity_curve': full_equity,
        'signals_buy': signals_buy,
        'signals_sell': signals_sell,
        'signals_stop': signals_stop,
        'final_equity': final_equity,
        'bh_equity_curve': bh_equity,
        'bh_final_equity': bh_final,
        'params': {
            'entry_period': entry_period,
            'exit_period': exit_period,
            'atr_period': atr_period,
            'atr_stop_mult': atr_stop_mult,
            'risk_percent': risk_percent,
            'use_filter': use_filter,
        },
    }


# ═══════════════════════════════════════════════════════════════
# 4. 绩效评估指标
# ═══════════════════════════════════════════════════════════════

def calc_metrics(result: Dict,
                 initial_capital: float = 1_000_000,
                 risk_free_rate: float = 0.02) -> Dict:
    """
    计算策略绩效评估指标

    指标:
      - 累计回报 (Cumulative Return)
      - 年化收益率 (Annualized Return, 252 交易日/年)
      - 最大回撤 (Maximum Drawdown, MDD)
      - 夏普比率 (Sharpe Ratio)
      - 胜率 (Win Rate)
      - 盈亏比 (Profit/Loss Ratio)
      - 日均收益率标准差 / 年化波动率
      - 交易次数
      - 买入持有基准对比

    参数:
        result: run_backtest() 返回的字典
        initial_capital: 初始资金
        risk_free_rate: 无风险利率 (默认 2%)

    返回:
        dict: 指标字典
    """
    trades = [t for t in result['trades'] if t['sell_date'] is not None]
    equity_values = [e['equity'] for e in result['equity_curve']]

    if len(equity_values) < 2:
        return {'error': '数据不足, 无法计算指标'}

    final_equity = result['final_equity']

    # 累计回报
    total_return = (final_equity / initial_capital - 1) * 100

    # 年化收益率
    days = max(1, (result['equity_curve'][-1]['date'] -
                   result['equity_curve'][0]['date']).days)
    annual_return = (np.power(final_equity / initial_capital, 252.0 / days) - 1) * 100

    # 最大回撤 (MDD)
    peak = -np.inf
    mdd = 0
    for eq in equity_values:
        if eq > peak:
            peak = eq
        dd = (eq - peak) / peak * 100
        if dd < mdd:
            mdd = dd

    # 日收益率序列
    daily_rets = []
    for i in range(1, len(equity_values)):
        if equity_values[i - 1] > 0:
            daily_rets.append(equity_values[i] / equity_values[i - 1] - 1)

    # 夏普比率
    sharpe = 0.0
    annual_vol = 0.0
    if len(daily_rets) > 1:
        mean_ret = np.mean(daily_rets)
        std_ret = np.std(daily_rets, ddof=0)
        annual_vol = std_ret * np.sqrt(252) * 100
        if std_ret > 0:
            sharpe = np.sqrt(252) * (mean_ret - risk_free_rate / 252) / std_ret

    # 胜率
    wins = [t for t in trades if t['return_pct'] > 0]
    losses = [t for t in trades if t['return_pct'] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0

    # 盈亏比
    avg_win = np.mean([t['return_pct'] for t in wins]) if wins else 0
    avg_loss = np.mean([abs(t['return_pct']) for t in losses]) if losses else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else None

    # 买入持有
    bh_total_return = (result['bh_final_equity'] / initial_capital - 1) * 100

    # 止损统计
    stop_trades = [t for t in trades if t.get('exit_reason') == '止损']
    signal_trades = [t for t in trades if t.get('exit_reason') == '离场信号']

    return {
        'total_return': round(total_return, 2),
        'annual_return': round(annual_return, 2),
        'mdd': round(mdd, 2),
        'sharpe': round(sharpe, 4),
        'win_rate': round(win_rate, 1),
        'profit_loss_ratio': round(profit_loss_ratio, 2) if profit_loss_ratio else None,
        'annual_volatility': round(annual_vol, 2),
        'total_trades': len(trades),
        'stop_exits': len(stop_trades),
        'signal_exits': len(signal_trades),
        'bh_total_return': round(bh_total_return, 2),
        'days': days,
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
    }


# ═══════════════════════════════════════════════════════════════
# 5. 参数扫描
# ═══════════════════════════════════════════════════════════════

def param_sweep(df: pd.DataFrame,
                entry_periods: List[int] = None,
                exit_periods: List[int] = None,
                atr_stop_mults: List[float] = None) -> pd.DataFrame:
    """
    参数敏感性扫描 — 网格搜索不同参数组合的策略表现

    参数:
        df: OHLCV 数据
        entry_periods: 入场周期列表
        exit_periods: 离场周期列表
        atr_stop_mults: 止损倍数列表

    返回:
        pd.DataFrame: 每行一组参数组合的绩效指标
    """
    if entry_periods is None:
        entry_periods = [10, 15, 20, 30, 40, 55]
    if exit_periods is None:
        exit_periods = [5, 10, 15, 20, 25]
    if atr_stop_mults is None:
        atr_stop_mults = [1.0, 1.5, 2.0, 2.5, 3.0]

    results = []
    total = len(entry_periods) * len(exit_periods) * len(atr_stop_mults)
    count = 0

    for ep in entry_periods:
        for xp in exit_periods:
            if xp >= ep:
                continue  # 离场周期必须小于入场周期
            for sm in atr_stop_mults:
                count += 1
                try:
                    bt = run_backtest(df, entry_period=ep, exit_period=xp,
                                      atr_stop_mult=sm)
                    m = calc_metrics(bt)
                    if m and 'error' not in m:
                        results.append({
                            'entry_period': ep,
                            'exit_period': xp,
                            'atr_stop_mult': sm,
                            'total_return': m['total_return'],
                            'annual_return': m['annual_return'],
                            'mdd': m['mdd'],
                            'sharpe': m['sharpe'],
                            'win_rate': m['win_rate'],
                            'total_trades': m['total_trades'],
                        })
                except Exception:
                    pass

    return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════
# 6. 工具函数
# ═══════════════════════════════════════════════════════════════

def load_stock(code: str, name: str, market: str,
               data_dir: str = None) -> pd.DataFrame:
    """加载股票 CSV 数据"""
    import os
    if data_dir is None:
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'data', 'csv'
        )
    filename = f"{code}_{name}_{market}_daily.csv"
    filepath = os.path.join(data_dir, filename)
    df = pd.read_csv(filepath, encoding='utf-8-sig')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


def print_metrics(metrics: Dict, stock_name: str = ''):
    """格式化打印策略指标"""
    header = f"  策略绩效: {stock_name}" if stock_name else "  策略绩效"
    print(f"\n{'='*55}")
    print(header)
    print(f"{'='*55}")
    print(f"  累计回报:     {metrics['total_return']:>10.2f}%")
    print(f"  年化收益率:   {metrics['annual_return']:>10.2f}%")
    print(f"  最大回撤:     {metrics['mdd']:>10.2f}%")
    print(f"  夏普比率:     {metrics['sharpe']:>10.4f}")
    print(f"  年化波动率:   {metrics['annual_volatility']:>10.2f}%")
    print(f"  胜率:         {metrics['win_rate']:>10.1f}%")
    plr_str = f'{metrics["profit_loss_ratio"]:.2f}' if metrics['profit_loss_ratio'] else 'N/A'
    print(f"  盈亏比:       {plr_str:>10s}")
    print(f"  交易次数:     {metrics['total_trades']:>10d}")
    print(f"  止损退出:     {metrics['stop_exits']:>10d} 次")
    print(f"  信号退出:     {metrics['signal_exits']:>10d} 次")
    print(f"  买入持有:     {metrics['bh_total_return']:>10.2f}%")
    print(f"{'='*55}\n")


# ═══════════════════════════════════════════════════════════════
# 主程序 (自检)
# ═══════════════════════════════════════════════════════════════

def main():
    print('=' * 60)
    print('  海龟策略回测引擎 — 自检')
    print('=' * 60)

    # 加载贵州茅台数据
    df = load_stock('600519', '贵州茅台', 'A股')
    print(f'\n📂 贵州茅台: {len(df)} 条数据')
    print(f'   日期范围: {df["Date"].iloc[0].date()} ~ {df["Date"].iloc[-1].date()}')

    # 运行回测
    print('\n⏳ 运行海龟策略回测 (entry=20, exit=10, ATR止损=2.0)...')
    result = run_backtest(df)
    metrics = calc_metrics(result)

    print_metrics(metrics, '贵州茅台 (600519)')

    # 交易明细
    completed = [t for t in result['trades'] if t['sell_date'] is not None]
    print(f'\n📋 交易明细 (共 {len(completed)} 笔完整交易):')
    print(f'{"#":>3s}  {"买入日":>12s}  {"买入价":>10s}  {"卖出日":>12s}  {"卖出价":>10s}  {"收益":>8s}  {"原因"}')
    print('-' * 80)
    for i, t in enumerate(completed):
        print(f'{i+1:>3d}  {str(t["buy_date"].date()):>12s}  {t["buy_price"]:>10.2f}  '
              f'{str(t["sell_date"].date()):>12s}  {t["sell_price"]:>10.2f}  '
              f'{t["return_pct"]:>7.2f}%  {t.get("exit_reason", "N/A")}')

    # 信号统计
    print(f'\n📊 信号统计:')
    print(f'   买入信号: {len(result["signals_buy"])} 次')
    print(f'   卖出信号: {len(result["signals_sell"])} 次')
    print(f'   止损触发: {len(result["signals_stop"])} 次')

    print('\n✅ 回测完成')


if __name__ == '__main__':
    main()
