# Task 2 - Technical Indicator Engine

Task 2 implements eight technical-indicator families in Python and exposes their parameters in a portable dashboard. The analysis focuses on formula choices, warm-up behavior, parameter sensitivity, and differences between trend, momentum, volatility, and strength measures.

## Indicators

| Family | Implementations |
| --- | --- |
| Trend | simple moving averages, MACD |
| Momentum | RSI, KDJ |
| Volatility | ATR, Bollinger Bands |
| Trend strength and extremes | ADX, CCI |

## Implementation details

- RSI, ATR, and ADX use Wilder smoothing with `alpha = 1 / n`, not the standard EMA convention.
- Rolling calculations retain a warm-up period instead of filling missing values with zero.
- Indicator functions accept validated OHLCV frames, preserve the input index, and return aligned series.
- Dashboard controls recompute parameterized overlays in the browser from embedded data.

## Entry points

- [Interactive dashboard](dashboard/index.html)
- [`scripts/indicators.py`](scripts/indicators.py) - task-level indicator functions
- [`../src/indicators.py`](../src/indicators.py) - shared implementation
- [`scripts/build_dashboard.py`](scripts/build_dashboard.py) - static dashboard build
- [English report](../reports/Task2_Report.pdf)

## Reproduce and validate

```bash
python Task2/scripts/build_dashboard.py
python -m unittest discover -s tests -v
```

The dashboard compares indicator behavior on the same price history; strategy performance is evaluated separately in Tasks 3 and 4.
