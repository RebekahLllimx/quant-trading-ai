# Task 4 - Turtle Trading Strategy

Task 4 implements a stateful breakout strategy with ATR-based position sizing, pyramiding, trailing stops, transaction costs, and parameter sensitivity.

## System design

- **Entry:** break above a prior Donchian-channel high.
- **Exit:** break below the exit channel or trigger an ATR-based stop.
- **Position sizing:** divide a fixed risk budget by the ATR stop distance.
- **Pyramiding:** add units only after favorable movement, subject to a unit cap.
- **State:** track units, average entry price, stop level, cash, and portfolio value.
- **Validation:** compare parameter grids, drawdowns, trades, and multiple instruments.

Channel levels use prior completed bars, so the current high or low cannot trigger a breakout against a range that already includes that observation. Commission and slippage are deducted from each trade.

## Entry points

- [Interactive dashboard](dashboard/index.html)
- [`scripts/turtle_strategy.py`](scripts/turtle_strategy.py) - stateful strategy engine
- [`scripts/plot_turtle.py`](scripts/plot_turtle.py) - regenerate the strategy figures
- [`scripts/prepare_data.py`](scripts/prepare_data.py) - refresh the dashboard's embedded market data
- [English report](../reports/Task4_Report.pdf)

Parameter scans compare channel lengths, stop multiples, risk budgets, and instrument-level behavior under the same execution rules.

## Run the backtest and figures

After the repository-level environment setup, run from the repository root:

```bash
python Task4/scripts/turtle_strategy.py
python Task4/scripts/plot_turtle.py
```

These scripts read the shared snapshots in `data/csv/`; the plotting command replaces figures in `artifacts/charts/task4/`. The committed dashboard is a standalone page that can be opened directly.

Local runs and the dashboard use the date range in the shared CSV snapshots. Scheduled refreshes update the dashboard's inputs. The PDF report preserves its reference-period analysis; compare strategy metrics over matching dates.

To update the dashboard after changing the shared snapshots, run `python Task4/scripts/prepare_data.py`. It replaces only the embedded stock data, preserving the page layout and browser-side strategy code.
