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
- [`scripts/plot_turtle.py`](scripts/plot_turtle.py) - analysis and plots
- [`scripts/prepare_data.py`](scripts/prepare_data.py) - normalized input preparation
- [English report](../reports/Task4_Report.pdf)

Parameter scans compare channel lengths, stop multiples, risk budgets, and instrument-level behavior under the same execution rules.
