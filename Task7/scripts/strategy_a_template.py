# -*- coding: utf-8 -*-
"""TASK7 Strategy A — JoinQuant template baseline.

Paste this file into a JoinQuant strategy editor. The strategy intentionally
keeps the template's high market exposure so that it can serve as a baseline.
"""

from jqdata import *


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
    g.ma_window = 20
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


def can_trade(security, side):
    data = get_current_data()[security]
    if data.paused or data.last_price is None or data.last_price <= 0:
        log.warning("%s不可交易：停牌或价格无效" % security)
        return False
    if side == "BUY" and data.last_price >= data.high_limit:
        log.warning("%s涨停，取消买单" % security)
        return False
    if side == "SELL" and data.last_price <= data.low_limit:
        log.warning("%s跌停，取消卖单" % security)
        return False
    return True


def trade(context):
    bars = previous_bars(context, g.ma_window)
    if bars is None or len(bars) < g.ma_window:
        log.warning("历史数据不足，跳过")
        return
    close = float(bars["close"][-1])
    ma20 = float(bars["close"].mean())
    holding = context.portfolio.positions[g.security].total_amount
    if close > ma20:
        if can_trade(g.security, "BUY"):
            order_target_value(g.security, context.portfolio.total_value)
        signal = 1
    else:
        if holding > 0 and can_trade(g.security, "SELL"):
            order_target(g.security, 0)
        signal = 0
    record(signal=signal, ma20=ma20, exposure=holding * close / context.portfolio.total_value)
    log.info("A | T-1 close=%.3f MA20=%.3f signal=%s" % (close, ma20, signal))


def audit_orders(context):
    for order_id, order in get_orders().items():
        log.info(
            "A订单 | id=%s security=%s amount=%s filled=%s status=%s"
            % (
                order_id,
                order.security,
                order.amount,
                order.filled,
                order.status,
            )
        )
