#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turtle Trading Strategy Backtesting Engine (Turtle Trading Strategy Backtest Engine)

Core Components:
  1. High and low price channel (Donchian Channel)  -  Breakout Entry Signal
  2. ATR (Average True Range)  -  Volatility Measurement, Position calculation, Stop Loss Basis
  3. Trading signal generation  -  Admission/Increase position/Stop-loss/Departing
  4. Backtesting Engine  -  Simulated trading, Cost Calculation
  5. Performance appraisal  -  Cumulative Return, Annualized return, MDD, Sharpe Ratio, Win rate, Profit/Loss Ratio

Reference: Richard Dennis & William Eckhardt, "The Original Turtle Trading Rules" (1983)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


#
# 1. Metric Calculation
#

def calc_donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Calculate the Donchian channel (Donchian Channel)  -  High and low price channel

    Parameters:
        df: Contains High, Low of the column DataFrame
        period: Channel Cycle, Default 20 (sea turtle System 1 Entry cycle)

    Returns:
        pd.DataFrame: Contains DC_High (On track), DC_Low (Lower rail), DC_Mid (Middle rail) 3 columns
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
    calculation ATR (Average True Range)  -  Average True Range

    True Range = max(
        High - Low,              # Intraday amplitude
        |High - PrevClose|,      # Today&#39;s High and Yesterday&#39;s Gap (Upward gap)
        |Low - PrevClose|        # Today&#39;s Low and Yesterday&#39;s Gap (Downward gap)
    )
    ATR = WilderSmooth(TR, N)    # alpha = 1/N exponential smoothing

    Parameters:
        df: Contains High, Low, Close of the column DataFrame
        period: ATR cycle, Default 14

    Returns:
        pd.Series: ATR sequence
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

    # Wilder Smooth: alpha = 1/N
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    atr.name = 'ATR'
    return atr.round(4)


def calc_n_value(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    calculation N value (Core volatility measurement of the Turtle strategy)

    N value is period of the cycle ATR, but used in the original turtle 20 day.
    N Value Usage:
      - Position size = (Account x 1%) / N
      - Stop Loss Distance = 2 x N
      - Bin adding interval = 0.5 x N

    Parameters:
        df: Contains High, Low, Close of the column DataFrame
        period: N Value period, Default 20

    Returns:
        pd.Series: N value sequence
    """
    return calc_atr(df, period=period)


#
# 2. Trading signal generation
#

def generate_signals(df: pd.DataFrame,
                     entry_period: int = 20,
                     exit_period: int = 10,
                     atr_period: int = 20,
                     atr_stop_mult: float = 2.0,
                     use_filter: bool = True) -> pd.DataFrame:
    """
    Generate Turtle Strategy Trading Signals

    Turtle Trading Rules (Simplified version, Just do more):
      1. Admission: Close breaks above entry_period Upper rail of the daily high price channel  ->  Buy
      2. Increase position: Every increase in price 0.5xATR, Add warehouse once (at most 4 Next)
      3. Stop-loss: Price falls below entry price - atr_stop_mult x ATR  ->  Stop Loss Sell
      4. Departing: The closing price fell below exit_period Lower rail of the daily low price channel  ->  Sell
      5. filter: If the last breakout was a loss, Skip the next time System 1 Entry signal (Optional)

    Avoid future functions:
      - admission signal based on T-1 Channel data of day (T It was already known before the market opened.)
      - T Trading on the day at the closing price

    Parameters:
        df: Contains OHLC of the data DataFrame
        entry_period: Admission channel cycle, Default 20 (sea turtle System 1)
        exit_period: Departing Channel Cycle, Default 10 (sea turtle System 1)
        atr_period: ATR cycle, Default 20
        atr_stop_mult: Stop-loss ATR multiple, Default 2.0
        use_filter: Use loss filtering rules

    Returns:
        pd.DataFrame: Additional signal columns DataFrame
    """
    result = df.copy()
    close = result['Close'].astype(float)
    high = result['High'].astype(float)
    low = result['Low'].astype(float)

    # Calculation channel
    dc_entry = calc_donchian(result, period=entry_period)
    dc_exit = calc_donchian(result, period=exit_period)
    n_value = calc_n_value(result, period=atr_period)

    result['Entry_High'] = dc_entry['DC_High']
    result['Exit_Low'] = dc_exit['DC_Low']
    result['N_Value'] = n_value

    # Signal Column Initialization
    result['Signal'] = ''          # BUY / ADD / STOP / EXIT
    result['Signal_Price'] = np.nan

    # Traversal Generates Signal
    max_period = max(entry_period, exit_period, atr_period)
    last_trade_lost = False  # Turtle Filtering Rules
    # Position Addition Tracking
    in_position = False
    last_signal_price = 0.0
    units_count = 0

    for t in range(max_period + 2, len(result)):
        # T-1 Channel value of the day (Avoid future functions)
        entry_high_prev = result['Entry_High'].iloc[t - 1]
        exit_low_prev = result['Exit_Low'].iloc[t - 1]
        entry_high_prev2 = result['Entry_High'].iloc[t - 2]

        if pd.isna(entry_high_prev) or pd.isna(exit_low_prev):
            continue

        # Entry signal: Close breaks above entry_period Day Highest
        price_prev = close.iloc[t - 1]
        price_prev2 = close.iloc[t - 2]

        breakout_up = (price_prev > entry_high_prev and
                       price_prev2 <= entry_high_prev2)

        if breakout_up:
            if use_filter and last_trade_lost:
                # Skip this signal (but record)
                result.loc[result.index[t], 'Signal'] = 'FILTERED_BUY'
                last_trade_lost = False
                in_position = False
            else:
                result.loc[result.index[t], 'Signal'] = 'BUY'
                result.loc[result.index[t], 'Signal_Price'] = close.iloc[t]
                in_position = True
                last_signal_price = close.iloc[t]
                units_count = 1

        # Bin signal: In position, Price more recently bought/Increase in position price >= 0.5xN
        if in_position and units_count < 4:
            n_val = result['N_Value'].iloc[t]
            if (not pd.isna(n_val) and n_val > 0 and
                    close.iloc[t] >= last_signal_price + 0.5 * n_val):
                result.loc[result.index[t], 'Signal'] = 'ADD'
                result.loc[result.index[t], 'Signal_Price'] = close.iloc[t]
                last_signal_price = close.iloc[t]
                units_count += 1

    return result


#
# 3. Backtesting Engine
#

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
    Turtle Strategy Backtesting Engine (Just do more)

    Turtle Trading System Core Logic:
      1. Admission: Price Breakout entry_period Day High Point  ->  Full Buy
      2. Dynamic Stop Loss: Stop loss price during position = Admission price - atr_stop_mult x ATR_t (Move up only, not down)
      3. Departing: Prices fall below exit_period Day Low  ->  Sell Entry
      4. Position: Initial position based on N value  -  shares = (capital x risk%) / N
      5. Forced liquidation: If still holding positions on the last day of backtesting, sell at the closing price.

    Avoid future functions:
      - All signal judgments are based on T-1 Daily data
      - T Execute trades at the closing price on the day.

    Parameters:
        df: OHLCV Data
        entry_period: Admission channel cycle (sea turtle System 1 = 20)
        exit_period: Departing Channel Cycle (sea turtle System 1 = 10)
        atr_period: ATR/N Value Calculation Period (Default 20)
        atr_stop_mult: Stop Loss Multiples (Default 2.0)
        risk_percent: Single-Trade Risk Ratio (Default 2%)
        initial_capital: Initial funding
        fee_rate: Fee rate (Default 0.03%)
        slippage: slippage rate (Default 0.01%)
        use_filter: Use loss filtering rules
        max_units: Maximum number of additional positions
        pyramid_atr_mult: Bin adding interval ATR multiple

    Returns:
        dict: {
            'df': Additional signal columns DataFrame,
            'trades': Transaction Detail List,
            'equity_curve': Daily Benefits,
            'signals_buy': Buy Signal List,
            'signals_sell': List of Sell Signals,
            'signals_stop': List of Stop Loss Signals,
            'final_equity': Final interest,
            'bh_equity_curve': Buy and hold equity curve,
            'bh_final_equity': BUY-HOLD FINAL INTEREST,
        }
    """
    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    # Calculated metric
    dc_entry = calc_donchian(df, period=entry_period)
    dc_exit = calc_donchian(df, period=exit_period)
    n_value = calc_n_value(df, period=atr_period)

    # Initialization State
    cash = initial_capital
    shares = 0
    has_position = False
    entry_price = 0.0
    stop_price = 0.0  # Dynamic Stop Price
    units_held = 0  # Current number of position increases
    last_add_price = 0.0  # The most recent price of the additional purchase (Pyramid plus warehouse benchmark)
    last_trade_lost = False

    trades = []
    equity_curve = []
    signals_buy = []
    signals_sell = []
    signals_stop = []
    signals_add = []  # Pyramid plus bin signal

    start_idx = max(entry_period, exit_period, atr_period) + 2

    for t in range(start_idx, len(df)):
        price_t = close.iloc[t]
        date_t = df['Date'].iloc[t]
        n_t = n_value.iloc[t]
        high_t = high.iloc[t]
        low_t = low.iloc[t]

        # Calculate the day&#39;s equity
        equity = cash + shares * price_t
        equity_curve.append({
            'date': date_t,
            'equity': equity,
            'cash': cash,
            'shares': shares,
        })

        # ---- Signal Judgment (Original Turtle Version: T Hidaka/Low-price trigger T-1 Day Channel) ----
        # T-1 The channel value on the day is in T Known before the opening of the day., T day high/Low Price Trigger Deal
        entry_high_prev = dc_entry['DC_High'].iloc[t - 1]
        exit_low_prev = dc_exit['DC_Low'].iloc[t - 1]

        if pd.isna(entry_high_prev) or pd.isna(exit_low_prev) or pd.isna(n_t):
            continue

        # Entry signal: T Daily high breaks above T-1 Daily admission channel on rail (Original Turtle Version Stop Order)
        # At the same time, it requires T-1 The closing price does not exceed T-2 Channel (Avoid consecutive breakthroughs)
        prev2_high = dc_entry['DC_High'].iloc[t - 2]
        prev_close = close.iloc[t - 1]
        breakout_up = (high_t > entry_high_prev and
                       (pd.isna(prev2_high) or prev_close <= prev2_high))

        # Exit Signal: T The daily low fell below T-1 Lower rail of the daily exit passage
        exit_signal = low_t < exit_low_prev

        # Stop Loss Judgment: Holding period, The lowest price of the day touched the stop loss price.
        stop_hit = False
        if has_position and stop_price > 0:
            stop_hit = low_t <= stop_price

        # ---- Execute Trade ----
        if breakout_up and not has_position:
            # Filtering Rules: Skip if last loss occurs
            if use_filter and last_trade_lost:
                last_trade_lost = False
                continue

            # Buy
            buy_price = price_t * (1 + slippage)
            # Position: Strictly derived version  -  Shares = RiskAmount / (k x N)
            # RiskAmount = Cash x risk_percent
            # StopDistance = atr_stop_mult x N_t (Stop Loss Distance Per Share)
            # When the stop loss is triggered, Actual loss approximately RiskAmount
            if n_t > 0:
                risk_amount = cash * risk_percent
                stop_distance = atr_stop_mult * n_t
                safe_shares = risk_amount / stop_distance
                # No more than available funds
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
            last_add_price = buy_price

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
            # Dynamic Stop Price Move Up (Move up only, not down  -  Turtle Stop Loss Iron Law)
            if n_t > 0 and not pd.isna(n_t):
                new_stop = entry_price - atr_stop_mult * n_t
                # For profitable positions, Consider using a tighter stop loss
                if price_t > entry_price:
                    trailing_stop = price_t - atr_stop_mult * n_t
                    new_stop = max(new_stop, trailing_stop)
                stop_price = max(stop_price, new_stop)

            # Pyramid plus warehouse: Every increase in price pyramid_atr_mult x N, Add one unit to the position.
            if (units_held < max_units and n_t > 0 and not pd.isna(n_t) and
                    price_t >= last_add_price + pyramid_atr_mult * n_t):
                add_price = price_t * (1 + slippage)
                # Position calculation: The same formula as the initial entry
                if n_t > 0:
                    risk_amount = cash * risk_percent
                    stop_distance = atr_stop_mult * n_t
                    safe_shares = risk_amount / stop_distance
                    max_shares_buy = cash / (add_price * (1 + fee_rate))
                    add_shares = min(safe_shares, max_shares_buy)
                else:
                    add_shares = 0

                if add_shares > 0:
                    add_cost = add_shares * add_price * (1 + fee_rate)
                    if add_cost <= cash:
                        cash -= add_cost
                        # Updated weighted average entry price
                        total_cost_basis = shares * entry_price + add_shares * add_price
                        shares += add_shares
                        entry_price = total_cost_basis / shares
                        units_held += 1
                        last_add_price = add_price
                        # Original Turtle Version: After adding positions, the stop loss is tightened to the latest added price. - kxN
                        stop_price = add_price - atr_stop_mult * n_t

                        # Update trade Record
                        trades[-1].setdefault('pyramid_adds', []).append({
                            'add_date': date_t,
                            'add_price': round(add_price, 4),
                            'add_shares': round(add_shares, 2),
                            'add_cost': round(add_cost, 2),
                        })
                        trades[-1]['shares'] = round(shares, 2)
                        trades[-1]['cost'] = round(trades[-1]['cost'] + add_cost, 2)

                        signals_add.append((date_t, add_price))

            # Check Stop Loss
            if stop_hit:
                sell_price = stop_price * (1 - slippage)
                cash += shares * sell_price * (1 - fee_rate)
                trades[-1]['sell_date'] = date_t
                trades[-1]['sell_price'] = round(sell_price, 4)
                trades[-1]['return_pct'] = round(
                    (shares * sell_price * (1 - fee_rate) / trades[-1]['cost'] - 1) * 100, 2
                )
                trades[-1]['exit_reason'] = 'Stop-loss'
                last_trade_lost = trades[-1]['return_pct'] < 0
                shares = 0
                has_position = False
                stop_price = 0
                units_held = 0
                signals_stop.append((date_t, sell_price))
                signals_sell.append((date_t, sell_price))

            # Check departure signal
            elif exit_signal:
                sell_price = price_t * (1 - slippage)
                cash += shares * sell_price * (1 - fee_rate)
                trades[-1]['sell_date'] = date_t
                trades[-1]['sell_price'] = round(sell_price, 4)
                trades[-1]['return_pct'] = round(
                    (shares * sell_price * (1 - fee_rate) / trades[-1]['cost'] - 1) * 100, 2
                )
                trades[-1]['exit_reason'] = 'Exit Signal'
                last_trade_lost = trades[-1]['return_pct'] < 0
                shares = 0
                has_position = False
                stop_price = 0
                units_held = 0
                signals_sell.append((date_t, sell_price))

    # Forced liquidation
    if has_position:
        final_price = close.iloc[-1] * (1 - slippage)
        cash += shares * final_price * (1 - fee_rate)
        trades[-1]['sell_date'] = df['Date'].iloc[-1]
        trades[-1]['sell_price'] = round(final_price, 4)
        trades[-1]['return_pct'] = round(
            (shares * final_price * (1 - fee_rate) / trades[-1]['cost'] - 1) * 100, 2
        )
        trades[-1]['exit_reason'] = 'Forced liquidation'

    # complete equity curve (former start_idx Days to hold cash)
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

    # Buy-to-hold benchmark
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
        'signals_add': signals_add,  # Pyramid plus bin signal
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


#
# 4. Performance evaluation indicators
#

def calc_metrics(result: Dict,
                 initial_capital: float = 1_000_000,
                 risk_free_rate: float = 0.02) -> Dict:
    """
    Calculating Strategy Performance Evaluation Metrics

    Indicator:
      - Cumulative Return (Cumulative Return)
      - Annualized return rate (Annualized Return, 252 Trading day/year)
      - Maximum Drawdown (Maximum Drawdown, MDD)
      - Sharpe Ratio (Sharpe Ratio)
      - Win rate (Win Rate)
      - Profit/Loss Ratio (Profit/Loss Ratio)
      - Average daily yield standard deviation / annualized volatility
      - Number of transactions
      - Buy-to-hold benchmark comparison

    Parameters:
        result: run_backtest() The returned dictionary
        initial_capital: Initial funding
        risk_free_rate: Risk-free rate (Default 2%)

    Returns:
        dict: Metric Dictionary
    """
    trades = [t for t in result['trades'] if t['sell_date'] is not None]
    equity_values = [e['equity'] for e in result['equity_curve']]

    if len(equity_values) < 2:
        return {'error': 'Insufficient data, Unable to calculate indicator'}

    final_equity = result['final_equity']

    # Cumulative Return
    total_return = (final_equity / initial_capital - 1) * 100

    # Annualized return rate
    days = max(1, (result['equity_curve'][-1]['date'] -
                   result['equity_curve'][0]['date']).days)
    annual_return = (np.power(final_equity / initial_capital, 252.0 / days) - 1) * 100

    # Maximum Drawdown (MDD)
    peak = -np.inf
    mdd = 0
    for eq in equity_values:
        if eq > peak:
            peak = eq
        dd = (eq - peak) / peak * 100
        if dd < mdd:
            mdd = dd

    # daily yield series
    daily_rets = []
    for i in range(1, len(equity_values)):
        if equity_values[i - 1] > 0:
            daily_rets.append(equity_values[i] / equity_values[i - 1] - 1)

    # Sharpe Ratio
    sharpe = 0.0
    annual_vol = 0.0
    if len(daily_rets) > 1:
        mean_ret = np.mean(daily_rets)
        std_ret = np.std(daily_rets, ddof=0)
        annual_vol = std_ret * np.sqrt(252) * 100
        if std_ret > 0:
            sharpe = np.sqrt(252) * (mean_ret - risk_free_rate / 252) / std_ret

    # Win rate
    wins = [t for t in trades if t['return_pct'] > 0]
    losses = [t for t in trades if t['return_pct'] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0

    # Profit/Loss Ratio
    avg_win = np.mean([t['return_pct'] for t in wins]) if wins else 0
    avg_loss = np.mean([abs(t['return_pct']) for t in losses]) if losses else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else None

    # Buy and hold
    bh_total_return = (result['bh_final_equity'] / initial_capital - 1) * 100

    # Stop Loss Statistics
    stop_trades = [t for t in trades if t.get('exit_reason') == 'Stop-loss']
    signal_trades = [t for t in trades if t.get('exit_reason') == 'Exit Signal']

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


#
# 5. Parameter Scan
#

def param_sweep(df: pd.DataFrame,
                entry_periods: List[int] = None,
                exit_periods: List[int] = None,
                atr_stop_mults: List[float] = None) -> pd.DataFrame:
    """
    parameter sensitivity scan  -  Strategy performance under different parameter combinations in grid search.

    Parameters:
        df: OHLCV Data
        entry_periods: Entry cycle list
        exit_periods: Departing Period List
        atr_stop_mults: List of Stop Loss Multiples

    Returns:
        pd.DataFrame: Performance indicators for each row of parameter combinations
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
                continue  # Exit period must be shorter than entry period
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


#
# 6. Tool Functions
#

def load_stock(code: str, name: str, market: str,
               data_dir: str = None) -> pd.DataFrame:
    """Load Stock CSV Data"""
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
    """Format Print Policy Indicator"""
    header = f"  Strategy Performance: {stock_name}" if stock_name else "  Strategy Performance"
    print(f"\n{'='*55}")
    print(header)
    print(f"{'='*55}")
    print(f"  Cumulative Returns:     {metrics['total_return']:>10.2f}%")
    print(f"  Annualized return rate:   {metrics['annual_return']:>10.2f}%")
    print(f"  Maximum Drawdown:     {metrics['mdd']:>10.2f}%")
    print(f"  Sharpe Ratio:     {metrics['sharpe']:>10.4f}")
    print(f"  annualized volatility:   {metrics['annual_volatility']:>10.2f}%")
    print(f"  Win rate:         {metrics['win_rate']:>10.1f}%")
    plr_str = f'{metrics["profit_loss_ratio"]:.2f}' if metrics['profit_loss_ratio'] else 'N/A'
    print(f"  Profit/Loss Ratio:       {plr_str:>10s}")
    print(f"  Number of transactions:     {metrics['total_trades']:>10d}")
    print(f"  Stop Loss Exit:     {metrics['stop_exits']:>10d} Next")
    print(f"  Signal Exit:     {metrics['signal_exits']:>10d} Next")
    print(f"  Buy and hold:     {metrics['bh_total_return']:>10.2f}%")
    print(f"{'='*55}\n")


#
# Main program (Self-check)
#

def main():
    print('=' * 60)
    print('  Turtle Strategy Backtesting Engine  -  Self-check')
    print('=' * 60)

    # Load Kweichow Moutai data
    df = load_stock('600519', 'Kweichow Moutai', 'A-share')
    print(f'\n Kweichow Moutai: {len(df)} data item')
    print(f'   Date Range: {df["Date"].iloc[0].date()} ~ {df["Date"].iloc[-1].date()}')

    # Run Backtest
    print('\n Run Turtle Strategy Backtest (entry=20, exit=10, ATRStop-loss=2.0)...')
    result = run_backtest(df)
    metrics = calc_metrics(result)

    print_metrics(metrics, 'Kweichow Moutai (600519)')

    # Transaction details
    completed = [t for t in result['trades'] if t['sell_date'] is not None]
    print(f'\n Transaction details (total {len(completed)} Complete transaction with pen):')
    print(f'{"#":>3s}  {"Buying Day":>12s}  {"Purchase Price":>10s}  {"Sell Day":>12s}  {"Selling Price":>10s}  {"Revenue":>8s}  {"Reason"}')
    print('-' * 80)
    for i, t in enumerate(completed):
        print(f'{i+1:>3d}  {str(t["buy_date"].date()):>12s}  {t["buy_price"]:>10.2f}  '
              f'{str(t["sell_date"].date()):>12s}  {t["sell_price"]:>10.2f}  '
              f'{t["return_pct"]:>7.2f}%  {t.get("exit_reason", "N/A")}')

    # Signal Statistics
    print(f'\n Signal Statistics:')
    print(f'   Buy signal: {len(result["signals_buy"])} Next')
    print(f'   Bin signal: {len(result["signals_add"])} Next')
    print(f'   Sell signal: {len(result["signals_sell"])} Next')
    print(f'   Stop Loss Trigger: {len(result["signals_stop"])} Next')

    print('\n Backtesting complete')


if __name__ == '__main__':
    main()
