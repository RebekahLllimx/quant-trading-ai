#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared data, backtest, metric and export helpers for TASK7.

The local engine is deliberately simple and conservative:

* signals only use information available at the previous close;
* orders execute at the next open;
* ETF commission, minimum commission, proportional slippage and 100-share lots
  are applied explicitly;
* the generated results are labelled as historical backtests or shadow
  reconstructions, never as JoinQuant actual fills.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "task7"
RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"
METADATA_DIR = DATA_ROOT / "metadata"
DASHBOARD_DATA_DIR = ROOT / "Task7" / "dashboard" / "data"

SYMBOLS = {
    "510300": {"jq": "510300.XSHG", "yahoo": "510300.SS", "name": "沪深300ETF"},
    "510500": {"jq": "510500.XSHG", "yahoo": "510500.SS", "name": "中证500ETF"},
    "159915": {"jq": "159915.XSHE", "yahoo": "159915.SZ", "name": "创业板ETF"},
    "000300": {"jq": "000300.XSHG", "yahoo": "000300.SS", "name": "沪深300"},
}

INITIAL_CAPITAL = 500_000.0
LOT_SIZE = 100
BASE_COST = {
    "commission_rate": 0.0003,
    "min_commission": 5.0,
    "slippage_rate": 0.001,
}
PERIODS = {
    "development": ("2016-01-01", "2023-12-31"),
    "validation": ("2024-01-01", "2025-12-31"),
    "oos": ("2026-01-01", "2099-12-31"),
    "full": ("2016-01-01", "2099-12-31"),
}


@dataclass
class Trade:
    date: str
    strategy: str
    symbol: str
    side: str
    shares: int
    raw_price: float
    fill_price: float
    gross_value: float
    commission: float
    slippage_cost: float
    reason: str


def ensure_dirs() -> None:
    for path in (RAW_DIR, PROCESSED_DIR, METADATA_DIR, DASHBOARD_DATA_DIR):
        path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_price_csv(symbol: str) -> pd.DataFrame:
    path = RAW_DIR / f"{symbol}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing TASK7 market data: {path}")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    numeric = ["Open", "High", "Low", "Close", "Volume"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return (
        df.sort_values("Date")
        .drop_duplicates("Date", keep="last")
        .set_index("Date")
    )


def load_market_data() -> Dict[str, pd.DataFrame]:
    return {symbol: read_price_csv(symbol) for symbol in SYMBOLS}


def true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["Close"].shift(1)
    return pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _commission(value: float, rate: float, minimum: float) -> float:
    if value <= 0:
        return 0.0
    return max(value * rate, minimum)


def _buy(
    *,
    date: pd.Timestamp,
    strategy: str,
    symbol: str,
    shares: int,
    raw_price: float,
    cash: float,
    costs: Mapping[str, float],
    reason: str,
) -> Tuple[int, float, Optional[Trade]]:
    shares = int(max(0, shares) // LOT_SIZE * LOT_SIZE)
    fill = raw_price * (1.0 + costs["slippage_rate"])
    while shares > 0:
        gross = shares * fill
        commission = _commission(
            gross, costs["commission_rate"], costs["min_commission"]
        )
        if gross + commission <= cash + 1e-8:
            break
        shares -= LOT_SIZE
    if shares <= 0:
        return 0, cash, None
    gross = shares * fill
    commission = _commission(
        gross, costs["commission_rate"], costs["min_commission"]
    )
    trade = Trade(
        date=date.strftime("%Y-%m-%d"),
        strategy=strategy,
        symbol=symbol,
        side="BUY",
        shares=shares,
        raw_price=float(raw_price),
        fill_price=float(fill),
        gross_value=float(gross),
        commission=float(commission),
        slippage_cost=float(shares * (fill - raw_price)),
        reason=reason,
    )
    return shares, cash - gross - commission, trade


def _sell(
    *,
    date: pd.Timestamp,
    strategy: str,
    symbol: str,
    shares: int,
    raw_price: float,
    cash: float,
    costs: Mapping[str, float],
    reason: str,
) -> Tuple[int, float, Optional[Trade]]:
    shares = int(max(0, shares) // LOT_SIZE * LOT_SIZE)
    if shares <= 0:
        return 0, cash, None
    fill = raw_price * (1.0 - costs["slippage_rate"])
    gross = shares * fill
    commission = _commission(
        gross, costs["commission_rate"], costs["min_commission"]
    )
    trade = Trade(
        date=date.strftime("%Y-%m-%d"),
        strategy=strategy,
        symbol=symbol,
        side="SELL",
        shares=shares,
        raw_price=float(raw_price),
        fill_price=float(fill),
        gross_value=float(gross),
        commission=float(commission),
        slippage_cost=float(shares * (raw_price - fill)),
        reason=reason,
    )
    return 0, cash + gross - commission, trade


def _target_shares(
    equity: float, weight: float, raw_price: float, costs: Mapping[str, float]
) -> int:
    if raw_price <= 0 or equity <= 0 or weight <= 0:
        return 0
    budget = equity * weight
    estimated_fill = raw_price * (1.0 + costs["slippage_rate"])
    return int(budget / estimated_fill // LOT_SIZE * LOT_SIZE)


def _row(
    *,
    date: pd.Timestamp,
    strategy: str,
    cash: float,
    positions: Mapping[str, int],
    prices: Mapping[str, float],
    signal: str,
    selected: str,
    stop: Optional[float] = None,
    extra: Optional[Mapping[str, object]] = None,
) -> Dict[str, object]:
    market_value = sum(
        int(positions.get(symbol, 0)) * float(prices[symbol])
        for symbol in positions
        if symbol in prices and np.isfinite(prices[symbol])
    )
    nav = cash + market_value
    result: Dict[str, object] = {
        "Date": date.strftime("%Y-%m-%d"),
        "Strategy": strategy,
        "Cash": float(cash),
        "MarketValue": float(market_value),
        "NAV": float(nav),
        "Exposure": float(market_value / nav) if nav > 0 else 0.0,
        "Signal": signal,
        "Selected": selected,
        "Stop": float(stop) if stop is not None and np.isfinite(stop) else None,
    }
    if extra:
        result.update(extra)
    return result


def run_strategy_a(
    market: Mapping[str, pd.DataFrame],
    costs: Optional[Mapping[str, float]] = None,
    ma_window: int = 20,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Template baseline: previous close above MA -> 100%, otherwise cash."""
    costs = dict(costs or BASE_COST)
    prices = market["510300"].copy()
    prices["MA"] = prices["Close"].rolling(ma_window).mean()
    cash = INITIAL_CAPITAL
    shares = 0
    rows: List[Dict[str, object]] = []
    trades: List[Trade] = []

    for i in range(ma_window, len(prices)):
        date = prices.index[i]
        today = prices.iloc[i]
        previous = prices.iloc[i - 1]
        if date < pd.Timestamp("2016-01-01"):
            continue
        desired = bool(previous["Close"] > previous["MA"])
        equity_open = cash + shares * float(today["Open"])
        target = _target_shares(equity_open, 1.0 if desired else 0.0, today["Open"], costs)
        reason = "T-1收盘价高于MA20" if desired else "T-1收盘价不高于MA20"
        if target < shares:
            sell_shares = shares - target
            _, cash, trade = _sell(
                date=date,
                strategy="A",
                symbol="510300",
                shares=sell_shares,
                raw_price=float(today["Open"]),
                cash=cash,
                costs=costs,
                reason=reason,
            )
            shares -= sell_shares
            if trade:
                trades.append(trade)
        elif target > shares:
            bought, cash, trade = _buy(
                date=date,
                strategy="A",
                symbol="510300",
                shares=target - shares,
                raw_price=float(today["Open"]),
                cash=cash,
                costs=costs,
                reason=reason,
            )
            shares += bought
            if trade:
                trades.append(trade)
        rows.append(
            _row(
                date=date,
                strategy="A",
                cash=cash,
                positions={"510300": shares},
                prices={"510300": float(today["Close"])},
                signal="LONG" if desired else "CASH",
                selected="510300" if shares else "CASH",
                extra={"MAFast": None, "MASlow": float(previous["MA"])},
            )
        )
    return pd.DataFrame(rows), pd.DataFrame([trade.__dict__ for trade in trades])


def run_strategy_b(
    market: Mapping[str, pd.DataFrame],
    costs: Optional[Mapping[str, float]] = None,
    ma_fast: int = 10,
    ma_slow: int = 30,
    atr_window: int = 20,
    atr_multiple: float = 2.0,
    risk_budget: float = 0.01,
    max_weight: float = 0.50,
    drawdown_limit: float = 0.05,
    cooldown_days: int = 5,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """MA trend with ATR position sizing, trailing stop and account cooldown."""
    costs = dict(costs or BASE_COST)
    prices = market["510300"].copy()
    prices["MAFast"] = prices["Close"].rolling(ma_fast).mean()
    prices["MASlow"] = prices["Close"].rolling(ma_slow).mean()
    prices["ATR"] = true_range(prices).rolling(atr_window).mean()
    cash = INITIAL_CAPITAL
    shares = 0
    stop: Optional[float] = None
    rows: List[Dict[str, object]] = []
    trades: List[Trade] = []
    peak_nav = INITIAL_CAPITAL
    previous_nav = INITIAL_CAPITAL
    cooldown_remaining = 0

    warmup = max(ma_slow, atr_window) + 1
    for i in range(warmup, len(prices)):
        date = prices.index[i]
        today = prices.iloc[i]
        previous = prices.iloc[i - 1]
        if date < pd.Timestamp("2016-01-01"):
            continue

        drawdown = 1.0 - previous_nav / peak_nav if peak_nav > 0 else 0.0
        risk_pause = drawdown >= drawdown_limit and cooldown_remaining == 0
        if risk_pause:
            cooldown_remaining = cooldown_days

        trend_on = bool(previous["MAFast"] > previous["MASlow"])
        stop_hit = bool(
            shares > 0
            and stop is not None
            and float(previous["Close"]) <= float(stop)
        )
        if cooldown_remaining > 0:
            desired = False
            reason = f"账户回撤保护，剩余{cooldown_remaining}日"
        elif stop_hit:
            desired = False
            reason = "T-1收盘价触发ATR移动止损"
        elif not trend_on:
            desired = False
            reason = "MA10不高于MA30"
        else:
            desired = True
            reason = "MA10高于MA30且风控允许"

        if not desired and shares > 0:
            old_shares = shares
            shares, cash, trade = _sell(
                date=date,
                strategy="B",
                symbol="510300",
                shares=old_shares,
                raw_price=float(today["Open"]),
                cash=cash,
                costs=costs,
                reason=reason,
            )
            stop = None
            if trade:
                trades.append(trade)
        elif desired and shares == 0 and np.isfinite(previous["ATR"]):
            equity_open = cash
            risk_shares = int(
                equity_open * risk_budget
                / (atr_multiple * float(previous["ATR"]))
                // LOT_SIZE
                * LOT_SIZE
            )
            cap_shares = _target_shares(
                equity_open, max_weight, float(today["Open"]), costs
            )
            planned = min(risk_shares, cap_shares)
            shares, cash, trade = _buy(
                date=date,
                strategy="B",
                symbol="510300",
                shares=planned,
                raw_price=float(today["Open"]),
                cash=cash,
                costs=costs,
                reason=reason,
            )
            if shares > 0:
                entry = trade.fill_price if trade else float(today["Open"])
                stop = entry - atr_multiple * float(previous["ATR"])
            if trade:
                trades.append(trade)

        if shares > 0 and np.isfinite(previous["ATR"]):
            candidate = float(previous["Close"]) - atr_multiple * float(previous["ATR"])
            stop = candidate if stop is None else max(stop, candidate)

        row = _row(
            date=date,
            strategy="B",
            cash=cash,
            positions={"510300": shares},
            prices={"510300": float(today["Close"])},
            signal=(
                "PAUSE"
                if cooldown_remaining > 0
                else ("LONG" if shares > 0 else "CASH")
            ),
            selected="510300" if shares else "CASH",
            stop=stop,
            extra={
                "MAFast": float(previous["MAFast"]),
                "MASlow": float(previous["MASlow"]),
                "ATR": float(previous["ATR"]),
                "Cooldown": int(cooldown_remaining),
            },
        )
        rows.append(row)
        previous_nav = float(row["NAV"])
        peak_nav = max(peak_nav, previous_nav)
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            if cooldown_remaining == 0:
                peak_nav = previous_nav

    return pd.DataFrame(rows), pd.DataFrame([trade.__dict__ for trade in trades])


def momentum_score(close: pd.Series, lookback: int) -> float:
    values = close.dropna().tail(lookback).astype(float).values
    if len(values) < lookback or np.any(values <= 0):
        return float("nan")
    x = np.arange(lookback, dtype=float)
    y = np.log(values)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    residual = np.sum((y - fitted) ** 2)
    total = np.sum((y - y.mean()) ** 2)
    r_squared = 0.0 if total <= 0 else max(0.0, 1.0 - residual / total)
    annualized = math.exp(slope * 252.0) - 1.0
    return float(annualized * r_squared)


def run_strategy_c(
    market: Mapping[str, pd.DataFrame],
    costs: Optional[Mapping[str, float]] = None,
    lookback: int = 20,
    weekday: int = 2,
    target_weight: float = 0.50,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Weekly broad-ETF momentum rotation with a cash fallback."""
    costs = dict(costs or BASE_COST)
    pool = ["510300", "510500", "159915"]
    common_dates = market[pool[0]].index
    for symbol in pool[1:]:
        common_dates = common_dates.intersection(market[symbol].index)
    common_dates = common_dates.sort_values()
    cash = INITIAL_CAPITAL
    positions: Dict[str, int] = {symbol: 0 for symbol in pool}
    selected = "CASH"
    rows: List[Dict[str, object]] = []
    trades: List[Trade] = []
    last_scores: Dict[str, float] = {symbol: float("nan") for symbol in pool}

    for i in range(lookback + 1, len(common_dates)):
        date = common_dates[i]
        if date < pd.Timestamp("2016-01-01"):
            continue
        previous_date = common_dates[i - 1]
        opens = {
            symbol: float(market[symbol].loc[date, "Open"]) for symbol in pool
        }
        closes = {
            symbol: float(market[symbol].loc[date, "Close"]) for symbol in pool
        }

        if date.weekday() == weekday:
            for symbol in pool:
                history = market[symbol].loc[:previous_date, "Close"]
                last_scores[symbol] = momentum_score(history, lookback)
            finite_scores = {
                symbol: score
                for symbol, score in last_scores.items()
                if np.isfinite(score)
            }
            candidate = (
                max(finite_scores, key=finite_scores.get) if finite_scores else "CASH"
            )
            desired = (
                candidate
                if candidate != "CASH" and finite_scores[candidate] > 0
                else "CASH"
            )
            reason = (
                f"周度动量最高：{desired}"
                if desired != "CASH"
                else "三只ETF动量均不为正"
            )

            for symbol in pool:
                if positions[symbol] > 0 and symbol != desired:
                    old = positions[symbol]
                    positions[symbol], cash, trade = _sell(
                        date=date,
                        strategy="C",
                        symbol=symbol,
                        shares=old,
                        raw_price=opens[symbol],
                        cash=cash,
                        costs=costs,
                        reason=reason,
                    )
                    if trade:
                        trades.append(trade)

            equity_open = cash + sum(
                positions[symbol] * opens[symbol] for symbol in pool
            )
            if desired != "CASH":
                target = _target_shares(
                    equity_open, target_weight, opens[desired], costs
                )
                current = positions[desired]
                if target < current:
                    reduce_by = current - target
                    _, cash, trade = _sell(
                        date=date,
                        strategy="C",
                        symbol=desired,
                        shares=reduce_by,
                        raw_price=opens[desired],
                        cash=cash,
                        costs=costs,
                        reason="周度再平衡至50%目标仓位",
                    )
                    positions[desired] -= reduce_by
                    if trade:
                        trades.append(trade)
                elif target > current:
                    bought, cash, trade = _buy(
                        date=date,
                        strategy="C",
                        symbol=desired,
                        shares=target - current,
                        raw_price=opens[desired],
                        cash=cash,
                        costs=costs,
                        reason=reason,
                    )
                    positions[desired] += bought
                    if trade:
                        trades.append(trade)
            selected = desired

        row = _row(
            date=date,
            strategy="C",
            cash=cash,
            positions=positions,
            prices=closes,
            signal="LONG" if selected != "CASH" else "CASH",
            selected=selected,
            extra={
                "Score510300": (
                    float(last_scores["510300"])
                    if np.isfinite(last_scores["510300"])
                    else None
                ),
                "Score510500": (
                    float(last_scores["510500"])
                    if np.isfinite(last_scores["510500"])
                    else None
                ),
                "Score159915": (
                    float(last_scores["159915"])
                    if np.isfinite(last_scores["159915"])
                    else None
                ),
            },
        )
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame([trade.__dict__ for trade in trades])


def benchmark_series(market: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    benchmark = market["000300"][["Close"]].copy()
    benchmark = benchmark.loc[benchmark.index >= pd.Timestamp("2016-01-01")]
    benchmark["BenchmarkNAV"] = (
        INITIAL_CAPITAL * benchmark["Close"] / benchmark["Close"].iloc[0]
    )
    return benchmark.reset_index().rename(columns={"index": "Date"})


def add_drawdown(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["Date"] = pd.to_datetime(result["Date"])
    result["Return"] = result["NAV"].pct_change().fillna(0.0)
    result["PeakNAV"] = result["NAV"].cummax()
    result["Drawdown"] = result["NAV"] / result["PeakNAV"] - 1.0
    return result


def _period_slice(frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    dated = frame.copy()
    dated["Date"] = pd.to_datetime(dated["Date"])
    return dated[(dated["Date"] >= start) & (dated["Date"] <= end)].copy()


def performance_metrics(
    frame: pd.DataFrame,
    trades: pd.DataFrame,
    benchmark: pd.DataFrame,
    *,
    start: str,
    end: str,
) -> Dict[str, object]:
    sample = _period_slice(frame, start, end)
    if sample.empty:
        return {"status": "no_data", "start": start, "end": end}
    sample = add_drawdown(sample)
    first_nav = float(sample["NAV"].iloc[0])
    last_nav = float(sample["NAV"].iloc[-1])
    returns = sample["Return"]
    count = max(len(sample) - 1, 1)
    annual_return = (last_nav / first_nav) ** (252.0 / count) - 1.0
    annual_vol = float(returns.std(ddof=1) * math.sqrt(252.0))
    sharpe = (
        float(returns.mean() / returns.std(ddof=1) * math.sqrt(252.0))
        if returns.std(ddof=1) > 0
        else None
    )
    period_trades = trades.copy()
    if not period_trades.empty:
        period_trades["date"] = pd.to_datetime(period_trades["date"])
        period_trades = period_trades[
            (period_trades["date"] >= start) & (period_trades["date"] <= end)
        ]
    costs = (
        float(
            period_trades.get("commission", pd.Series(dtype=float)).sum()
            + period_trades.get("slippage_cost", pd.Series(dtype=float)).sum()
        )
        if not period_trades.empty
        else 0.0
    )
    turnover = (
        float(period_trades["gross_value"].sum() / sample["NAV"].mean())
        if not period_trades.empty
        else 0.0
    )

    bench = benchmark.copy()
    bench["Date"] = pd.to_datetime(bench["Date"])
    bench = bench[(bench["Date"] >= start) & (bench["Date"] <= end)]
    beta = None
    correlation = None
    benchmark_return = None
    if len(bench) > 1:
        benchmark_return = float(
            bench["BenchmarkNAV"].iloc[-1] / bench["BenchmarkNAV"].iloc[0] - 1.0
        )
        joined = sample[["Date", "Return"]].merge(
            bench[["Date", "BenchmarkNAV"]], on="Date", how="inner"
        )
        joined["BenchmarkReturn"] = joined["BenchmarkNAV"].pct_change()
        joined = joined.dropna()
        if len(joined) > 2 and joined["BenchmarkReturn"].var() > 0:
            beta = float(
                joined[["Return", "BenchmarkReturn"]].cov().iloc[0, 1]
                / joined["BenchmarkReturn"].var()
            )
            correlation = float(
                joined["Return"].corr(joined["BenchmarkReturn"])
            )

    return {
        "status": "ok",
        "start": sample["Date"].iloc[0].strftime("%Y-%m-%d"),
        "end": sample["Date"].iloc[-1].strftime("%Y-%m-%d"),
        "observations": int(len(sample)),
        "cumulative_return": float(last_nav / first_nav - 1.0),
        "annualized_return": float(annual_return),
        "annualized_volatility": annual_vol,
        "sharpe": sharpe,
        "max_drawdown": float(sample["Drawdown"].min()),
        "positive_day_rate": float((returns > 0).mean()),
        "average_exposure": float(sample["Exposure"].mean()),
        "max_exposure": float(sample["Exposure"].max()),
        "cash_day_rate": float((sample["Exposure"] < 0.01).mean()),
        "trade_orders": int(len(period_trades)),
        "one_way_turnover": turnover / 2.0,
        "estimated_cost": costs,
        "benchmark_return": benchmark_return,
        "excess_return": (
            float(last_nav / first_nav - 1.0 - benchmark_return)
            if benchmark_return is not None
            else None
        ),
        "beta": beta,
        "correlation": correlation,
    }


def run_all(
    market: Mapping[str, pd.DataFrame],
    costs: Optional[Mapping[str, float]] = None,
    b_fast: int = 10,
    b_slow: int = 30,
    c_lookback: int = 15,
) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
    return {
        "A": run_strategy_a(market, costs=costs),
        "B": run_strategy_b(
            market, costs=costs, ma_fast=b_fast, ma_slow=b_slow
        ),
        "C": run_strategy_c(market, costs=costs, lookback=c_lookback),
    }


def json_ready(value):
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_ready(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
