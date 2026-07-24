# -*- coding: utf-8 -*-
"""TASK7 Strategy B — MA10/30 + ATR risk budget for JoinQuant."""

from jqdata import *
import numpy as np


def initialize(context):
    set_benchmark("000300.XSHG")
    set_option("use_real_price", True)
    set_option("avoid_future_data", True)
    set_slippage(PriceRelatedSlippage(0.001))
    set_order_cost(
        OrderCost(
            open_tax=0,
            close_tax=0,
            open_commission=0.0003,
            close_commission=0.0003,
            close_today_commission=0,
            min_commission=5,
        ),
        type="fund",
    )
    g.security = "510300.XSHG"
    g.ma_fast = 10
    g.ma_slow = 30
    g.atr_window = 20
    g.atr_multiple = 2.0
    g.risk_budget = 0.01
    g.max_weight = 0.50
    g.drawdown_limit = 0.05
    g.cooldown_days = 5
    g.cooldown_remaining = 0
    g.stop_price = None
    g.peak_value = context.portfolio.total_value
    run_daily(trade, time="09:35", reference_security=g.security)
    run_daily(audit_orders, time="14:55", reference_security=g.security)


def previous_bars(context, count):
    return get_bars(
        g.security,
        count=count,
        unit="1d",
        fields=("date", "open", "high", "low", "close"),
        include_now=False,
        end_dt=context.previous_date,
    )


def calculate_atr(bars):
    high = np.asarray(bars["high"], dtype=float)
    low = np.asarray(bars["low"], dtype=float)
    close = np.asarray(bars["close"], dtype=float)
    previous_close = close[:-1]
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(
            np.abs(high[1:] - previous_close),
            np.abs(low[1:] - previous_close),
        ),
    )
    return float(np.mean(tr[-g.atr_window :]))


def can_trade(security, side):
    data = get_current_data()[security]
    if data.paused or data.last_price is None or data.last_price <= 0:
        return False
    if side == "BUY" and data.last_price >= data.high_limit:
        return False
    if side == "SELL" and data.last_price <= data.low_limit:
        return False
    return True


def trade(context):
    required = max(g.ma_slow, g.atr_window + 1)
    bars = previous_bars(context, required)
    if bars is None or len(bars) < required:
        log.warning("B | 历史数据不足")
        return

    closes = np.asarray(bars["close"], dtype=float)
    close = float(closes[-1])
    ma_fast = float(np.mean(closes[-g.ma_fast :]))
    ma_slow = float(np.mean(closes[-g.ma_slow :]))
    atr = calculate_atr(bars)
    position = context.portfolio.positions[g.security]
    holding = int(position.total_amount)
    total_value = float(context.portfolio.total_value)
    g.peak_value = max(g.peak_value, total_value)
    drawdown = 1.0 - total_value / g.peak_value if g.peak_value > 0 else 0

    if drawdown >= g.drawdown_limit and g.cooldown_remaining == 0:
        g.cooldown_remaining = g.cooldown_days
        log.warning("B | 账户回撤达到5%%，暂停新开仓%d日" % g.cooldown_days)

    if holding > 0:
        candidate = close - g.atr_multiple * atr
        g.stop_price = candidate if g.stop_price is None else max(g.stop_price, candidate)

    stop_hit = holding > 0 and g.stop_price is not None and close <= g.stop_price
    trend_on = ma_fast > ma_slow
    allow_entry = trend_on and not stop_hit and g.cooldown_remaining == 0

    if not allow_entry and holding > 0:
        if can_trade(g.security, "SELL"):
            order_target(g.security, 0)
        g.stop_price = None
    elif allow_entry and holding == 0:
        current = get_current_data()[g.security]
        if can_trade(g.security, "BUY"):
            risk_shares = int(
                total_value * g.risk_budget / (g.atr_multiple * atr) / 100
            ) * 100
            cap_shares = int(
                total_value * g.max_weight / current.last_price / 100
            ) * 100
            target_shares = min(risk_shares, cap_shares)
            if target_shares >= 100:
                order_target(g.security, target_shares)
                g.stop_price = current.last_price - g.atr_multiple * atr

    signal = -1 if g.cooldown_remaining > 0 else (1 if allow_entry else 0)
    record(
        signal=signal,
        ma_fast=ma_fast,
        ma_slow=ma_slow,
        atr=atr,
        stop=g.stop_price or np.nan,
        drawdown=drawdown,
    )
    log.info(
        "B | close=%.3f MA10=%.3f MA30=%.3f ATR=%.3f stop=%s cooldown=%d"
        % (
            close,
            ma_fast,
            ma_slow,
            atr,
            ("%.3f" % g.stop_price) if g.stop_price is not None else "NA",
            g.cooldown_remaining,
        )
    )

    if g.cooldown_remaining > 0:
        g.cooldown_remaining -= 1
        if g.cooldown_remaining == 0:
            g.peak_value = context.portfolio.total_value


def audit_orders(context):
    for order_id, order in get_orders().items():
        log.info(
            "B订单 | id=%s security=%s amount=%s filled=%s status=%s"
            % (
                order_id,
                order.security,
                order.amount,
                order.filled,
                order.status,
            )
        )
