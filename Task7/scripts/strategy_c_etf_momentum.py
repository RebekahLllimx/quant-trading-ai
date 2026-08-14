# -*- coding: utf-8 -*-
"""TASK7 Strategy C — community-inspired weekly broad ETF momentum."""

from jqdata import *
import math
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
    g.pool = ["510300.XSHG", "510500.XSHG", "159915.XSHE"]
    # 15/20/30日只在开发期与验证期比较；15日的跨阶段稳定性最好。
    g.lookback = 15
    g.target_weight = 0.50
    run_weekly(
        rebalance,
        weekday=3,
        time="10:00",
        reference_security="510300.XSHG",
    )
    run_daily(audit_orders, time="14:55", reference_security="510300.XSHG")


def score(context, security):
    bars = get_bars(
        security,
        count=g.lookback,
        unit="1d",
        fields=("date", "close"),
        include_now=False,
        end_dt=context.previous_date,
    )
    if bars is None or len(bars) < g.lookback:
        return np.nan
    close = np.asarray(bars["close"], dtype=float)
    if np.any(close <= 0):
        return np.nan
    x = np.arange(g.lookback, dtype=float)
    y = np.log(close)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    total = np.sum((y - np.mean(y)) ** 2)
    residual = np.sum((y - fitted) ** 2)
    r_squared = 0 if total <= 0 else max(0, 1 - residual / total)
    annualized = math.exp(slope * 252) - 1
    return float(annualized * r_squared)


def can_trade(security, side):
    data = get_current_data()[security]
    if data.paused or data.last_price is None or data.last_price <= 0:
        return False
    if side == "BUY" and data.last_price >= data.high_limit:
        return False
    if side == "SELL" and data.last_price <= data.low_limit:
        return False
    return True


def rebalance(context):
    scores = {security: score(context, security) for security in g.pool}
    finite = {
        security: value
        for security, value in scores.items()
        if value is not None and np.isfinite(value)
    }
    selected = max(finite, key=finite.get) if finite else None
    if selected is not None and finite[selected] <= 0:
        selected = None

    for security in g.pool:
        holding = context.portfolio.positions[security].total_amount
        if holding > 0 and security != selected and can_trade(security, "SELL"):
            order_target(security, 0)

    if selected is not None and can_trade(selected, "BUY"):
        order_target_value(
            selected, context.portfolio.total_value * g.target_weight
        )

    record(
        score_300=scores.get("510300.XSHG", np.nan),
        score_500=scores.get("510500.XSHG", np.nan),
        score_cyb=scores.get("159915.XSHE", np.nan),
        selected=(g.pool.index(selected) + 1) if selected in g.pool else 0,
    )
    log.info("C | scores=%s selected=%s" % (scores, selected or "CASH"))


def audit_orders(context):
    for order_id, order in get_orders().items():
        log.info(
            "C订单 | id=%s security=%s amount=%s filled=%s status=%s"
            % (
                order_id,
                order.security,
                order.amount,
                order.filled,
                order.status,
            )
        )
