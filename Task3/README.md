# Task 3 - Moving-Average Crossover Backtest

Task 3 implements a moving-average crossover strategy with explicit signal timing, transaction costs, benchmark comparison, trade records, and parameter sensitivity.

## Strategy contract

- Enter long when the short moving average crosses above the long moving average.
- Exit when the short moving average crosses below the long moving average.
- Compute the signal from completed observations and execute on the next eligible bar.
- Remain long-only; do not use leverage or short selling.
- Deduct commission and slippage from every trade.

## Reference analysis

For the frozen Kweichow Moutai example from May 2025 to July 2026, the default MA(5, 15) rule returned `-5.67%`, compared with `-18.24%` for buy-and-hold. Maximum drawdown was `-15.20%` versus `-21.35%`. The strategy reduced exposure during a declining period, but did not produce a positive absolute return.

The parameter grid shows the trade-off between short lookbacks, which create more turnover in range-bound markets, and long lookbacks, which respond later to a trend change.

## Entry points

- [Interactive dashboard](dashboard/index.html)
- [`scripts/prepare_data.py`](scripts/prepare_data.py) - normalized backtest inputs
- [`scripts/plot_strategy.py`](scripts/plot_strategy.py) - backtest and sensitivity analysis
- [`scripts/build_dashboard.py`](scripts/build_dashboard.py) - static dashboard build
- [English report](../reports/Task3_Report.pdf)

## Rebuild from stored prices

After the repository-level environment setup, run from the repository root:

```bash
python Task3/scripts/prepare_data.py
python Task3/scripts/build_dashboard.py
python Task3/scripts/plot_strategy.py
```

The first two commands rebuild `dashboard/data.json` and `dashboard/index.html` from `data/csv/`. The last regenerates analysis figures under `artifacts/charts/task3/`. These commands overwrite generated files and do not refresh market data.

The dashboard computes the equity curve, drawdown, trades, and parameter grid over the current shared snapshots. Scheduled updates can change that interval. The PDF report preserves the reference analysis above; compare metrics only over matching dates.
