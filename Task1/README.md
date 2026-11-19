# Task 1 - Market Data Engine

Task 1 builds the shared market-data layer. It retrieves adjusted daily prices, maps provider-specific fields to one schema, stores CSV snapshots, and embeds candlestick and cross-market views in a standalone dashboard.

## Pipeline

```text
Tencent / AKShare / optional Tushare
        |
        v
provider adapter -> schema validation -> adjusted-price CSV
        |                                  |
        v                                  v
static charts                     embedded dashboard data
```

The tracked universe contains five A-share equities and five Hong Kong equities. Downstream tasks use the normalized fields `Date`, `Symbol`, `Open`, `High`, `Low`, `Close`, `Volume`, and optional amount/change/turnover fields. The [market-data guide](../docs/market-data.md) defines units, continuity checks, and the complete refresh procedure.

## Engineering decisions

- **Forward-adjusted prices:** prevent ex-dividend gaps from becoming false signals.
- **Provider adapters:** isolate external field names from the internal schema; exact API response keys stay inside the adapter.
- **Schema checks:** validate dates, numeric OHLCV fields, ordering, and missing values before export.
- **Committed snapshots:** allow dashboards and later tasks to run without API credentials.
- **Portable dashboard:** embed the selected data directly in HTML.

## Entry points

- [Interactive dashboard](dashboard/index.html)
- [`scripts/update_data.py`](scripts/update_data.py) - market-data refresh
- [`scripts/build_dashboard.py`](scripts/build_dashboard.py) - static dashboard build
- [`scripts/plot_candlestick.py`](scripts/plot_candlestick.py) - candlestick views
- [English report](../reports/Task1_Report.pdf)

## Reproduce

```bash
python Task1/scripts/build_dashboard.py
```

Price refresh uses the separate Python 3.12 environment and `requirements-refresh.txt`. The committed dashboard runs offline. `scripts/update_data.py` forwards to the shared updater, which refreshes all four stock-price pages together.
