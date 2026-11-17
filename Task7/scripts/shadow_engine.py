#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run TASK7 backtests, sensitivity checks and the latest shadow snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from task7_common import (
    BASE_COST,
    DASHBOARD_DATA_DIR,
    METADATA_DIR,
    PERIODS,
    PROCESSED_DIR,
    SYMBOLS,
    add_drawdown,
    benchmark_series,
    ensure_dirs,
    load_market_data,
    performance_metrics,
    run_all,
    run_strategy_b,
    run_strategy_c,
    write_json,
)

TASK_DIR = Path(__file__).resolve().parents[1]
JOINQUANT_SUMMARY_PATH = (
    TASK_DIR / "inputs" / "joinquant" / "backtest_summary.json"
)


def summarize_runs(runs, benchmark):
    metrics = {}
    for strategy, (frame, trades) in runs.items():
        metrics[strategy] = {
            period: performance_metrics(
                frame, trades, benchmark, start=start, end=end
            )
            for period, (start, end) in PERIODS.items()
        }
    return metrics


def latest_card(strategy, frame, metrics, platform_status):
    latest = frame.iloc[-1]
    full = metrics[strategy]["full"]
    return {
        "strategy": strategy,
        "name": {
            "A": "platform-template baseline",
            "B": "dual moving-average + ATRRisk control",
            "C": "broad-marketETFmomentum rotation",
        }[strategy],
        "as_of": latest["Date"],
        "signal": latest["Signal"],
        "selected": latest["Selected"],
        "selected_name": (
            SYMBOLS.get(str(latest["Selected"]), {}).get("name", "Cash")
        ),
        "exposure": latest["Exposure"],
        "nav": latest["NAV"],
        "cumulative_return": latest["NAV"] / frame.iloc[0]["NAV"] - 1.0,
        "max_drawdown": full.get("max_drawdown"),
        "annualized_volatility": full.get("annualized_volatility"),
        "beta": full.get("beta"),
        "trade_orders": full.get("trade_orders"),
        "data_layer": "Automatic shadow tracking",
        "joinquant_actual_status": platform_status,
    }


def main() -> int:
    ensure_dirs()
    market = load_market_data()
    benchmark = benchmark_series(market)
    runs = run_all(market)
    metrics = summarize_runs(runs, benchmark)
    joinquant_summary = (
        json.loads(JOINQUANT_SUMMARY_PATH.read_text(encoding="utf-8"))
        if JOINQUANT_SUMMARY_PATH.exists()
        else {}
    )
    joinquant_actual = joinquant_summary.get(
        "simulation_status",
        {
            "status": "not_imported",
            "message": "The simulation panel remains private.; After creation, supplement evidence via screenshots or field exports. ",
            "actual_performance_available": False,
        },
    )
    platform_status = {
        "deployed_waiting_data": "Deployed, Waiting for platform data",
        "not_imported": "Pending creation / Import",
    }.get(joinquant_actual.get("status"), joinquant_actual.get("status", "Unknown"))

    stress_cost = dict(BASE_COST)
    stress_cost["commission_rate"] *= 2
    stress_cost["slippage_rate"] *= 2
    stress_runs = run_all(market, costs=stress_cost)
    stress_metrics = summarize_runs(stress_runs, benchmark)

    nav_long = []
    trades_long = []
    for strategy, (frame, trades) in runs.items():
        frame = add_drawdown(frame)
        frame.to_csv(
            PROCESSED_DIR / f"strategy_{strategy.lower()}_daily.csv",
            index=False,
            encoding="utf-8-sig",
            float_format="%.8f",
        )
        trades.to_csv(
            PROCESSED_DIR / f"strategy_{strategy.lower()}_trades.csv",
            index=False,
            encoding="utf-8-sig",
            float_format="%.8f",
        )
        nav_long.append(frame)
        if not trades.empty:
            trades_long.append(trades)

    benchmark.to_csv(
        PROCESSED_DIR / "benchmark_daily.csv",
        index=False,
        encoding="utf-8-sig",
        float_format="%.8f",
    )

    b_sensitivity = []
    for fast, slow in [(5, 20), (10, 30), (20, 60)]:
        frame, trades = run_strategy_b(
            market, ma_fast=fast, ma_slow=slow
        )
        for period in ["development", "validation"]:
            start, end = PERIODS[period]
            row = performance_metrics(
                frame, trades, benchmark, start=start, end=end
            )
            row.update(
                {
                    "strategy": "B",
                    "ma_fast": fast,
                    "ma_slow": slow,
                    "period": period,
                }
            )
            b_sensitivity.append(row)

    c_sensitivity = []
    for lookback in [15, 20, 30]:
        frame, trades = run_strategy_c(market, lookback=lookback)
        for period in ["development", "validation"]:
            start, end = PERIODS[period]
            row = performance_metrics(
                frame, trades, benchmark, start=start, end=end
            )
            row.update(
                {
                    "strategy": "C",
                    "lookback": lookback,
                    "period": period,
                }
            )
            c_sensitivity.append(row)

    pd.DataFrame(b_sensitivity).to_csv(
        PROCESSED_DIR / "strategy_b_parameter_sensitivity.csv",
        index=False,
        encoding="utf-8-sig",
        float_format="%.8f",
    )
    pd.DataFrame(c_sensitivity).to_csv(
        PROCESSED_DIR / "strategy_c_parameter_sensitivity.csv",
        index=False,
        encoding="utf-8-sig",
        float_format="%.8f",
    )

    latest_common = min(
        pd.to_datetime(frame["Date"]).max() for frame, _ in runs.values()
    ).strftime("%Y-%m-%d")
    cards = [
        latest_card(strategy, frame, metrics, platform_status)
        for strategy, (frame, _) in runs.items()
    ]

    jq_settings = joinquant_summary.get("backtest_settings", {})
    jq_start = jq_settings.get("start")
    jq_end = jq_settings.get("end")
    comparable_shadow = {}
    if jq_start and jq_end:
        for strategy, (frame, trades) in runs.items():
            comparable_shadow[strategy] = performance_metrics(
                frame,
                trades,
                benchmark,
                start=jq_start,
                end=jq_end,
            )

    chart_start = pd.Timestamp("2024-01-01")
    chart_dates = sorted(
        set.intersection(
            *[
                set(
                    pd.to_datetime(frame["Date"])[
                        pd.to_datetime(frame["Date"]) >= chart_start
                    ].dt.strftime("%Y-%m-%d")
                )
                for frame, _ in runs.values()
            ]
        )
    )
    series = {}
    drawdowns = {}
    exposures = {}
    for strategy, (frame, _) in runs.items():
        working = add_drawdown(frame)
        working["Date"] = pd.to_datetime(working["Date"]).dt.strftime("%Y-%m-%d")
        working = working.set_index("Date").reindex(chart_dates)
        base = working["NAV"].dropna().iloc[0]
        series[strategy] = (working["NAV"] / base * 100).round(4).tolist()
        drawdowns[strategy] = (working["Drawdown"] * 100).round(4).tolist()
        exposures[strategy] = (working["Exposure"] * 100).round(2).tolist()

    bench = benchmark.copy()
    bench["Date"] = pd.to_datetime(bench["Date"]).dt.strftime("%Y-%m-%d")
    bench = bench.set_index("Date").reindex(chart_dates)
    benchmark_base = bench["BenchmarkNAV"].dropna().iloc[0]
    series["Benchmark"] = (
        bench["BenchmarkNAV"] / benchmark_base * 100
    ).round(4).tolist()

    recent_trades = (
        pd.concat(trades_long, ignore_index=True)
        .sort_values("date", ascending=False)
        .head(40)
        .to_dict("records")
        if trades_long
        else []
    )

    payload = {
        "title": "TASK7  -  3 strategy continuous observation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_complete_date": latest_common,
        "data_status": (
            "Shadow data updated; Three timesJoinQuantTest back completed; "
            "Three private simulated accounts have been deployed and are awaiting the first batch of running data."
            if joinquant_summary
            else "Shadow data updated; JoinQuantActual Simulation Data Awaiting User Import"
        ),
        "privacy": "Public page does not containJoinQuantAccount, Private Link, password, Cookieor mobile number. ",
        "method": {
            "initial_capital": 500_000,
            "signal_timing": "Use onlyT-1and earlier data, To be executed at the open of the next trading day",
            "cost": BASE_COST,
            "actual_vs_shadow": (
                "Current page returns are all historical reconstructions based on public market data./Shadow result, "
                "No.JoinQuantActual Transaction Results. "
            ),
        },
        "cards": cards,
        "metrics": metrics,
        "stress_metrics": stress_metrics,
        "dates": chart_dates,
        "nav_series": series,
        "drawdown_series": drawdowns,
        "exposure_series": exposures,
        "recent_trades": recent_trades,
        "joinquant_backtest_settings": jq_settings,
        "joinquant_backtests": joinquant_summary.get("backtests", []),
        "joinquant_shadow_comparison": comparable_shadow,
        "joinquant_short_window_settings": joinquant_summary.get(
            "short_window_settings", {}
        ),
        "joinquant_short_window_backtests": joinquant_summary.get(
            "short_window_backtests", []
        ),
        "simulation_deployments": joinquant_summary.get(
            "simulation_deployments", []
        ),
        "joinquant_actual": joinquant_actual,
    }
    write_json(DASHBOARD_DATA_DIR / "dashboard.json", payload)
    write_json(METADATA_DIR / "backtest_metrics.json", metrics)
    write_json(METADATA_DIR / "cost_stress_metrics.json", stress_metrics)
    print(f" TASK7 shadow results through {latest_common}")
    for card in cards:
        print(
            f"  {card['strategy']} {card['signal']:>5} "
            f"NAV={card['nav']:.2f} return={card['cumulative_return']:.2%} "
            f"MDD={card['max_drawdown']:.2%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
