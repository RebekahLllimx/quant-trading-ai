# Task 7 - Strategy Monitoring and Deployment Study

Task 7 compares three ETF strategies through JoinQuant backtests, local sensitivity analysis, and a public-data shadow portfolio. Each result is labeled by its data source and execution model.

## Strategies

1. **A - platform-template baseline:** hold CSI 300 ETF when the completed close is above MA20; otherwise hold cash.
2. **B - moving average plus ATR risk control:** MA(10, 30) trend filter, ATR trailing stop, 1% risk budget, 50% position cap, and drawdown pause.
3. **C - broad-market ETF momentum:** rank three ETFs by 15-day log-price slope multiplied by `R^2`; hold the highest positive score or cash.

## Evidence layers

- **Platform backtests:** fixed JoinQuant interval and execution model.
- **Platform simulation records:** scheduling and execution logs retained separately when available.
- **Local research:** parameter and cost-sensitivity analysis on public price snapshots.
- **Shadow portfolio:** deterministic signal reconstruction from public prices for ongoing observation.

## Offline reproduction

After installing the repository requirements, run from the repository root:

```bash
python Task7/scripts/shadow_engine.py
python Task7/scripts/build_dashboard.py
python Task7/scripts/validate_results.py
```

The engine reads the committed snapshots in `data/task7/raw/`. It replaces derived NAV, trade, sensitivity, metadata, and dashboard-data files. The builder then replaces the HTML dashboard. To check the committed results without rebuilding them, use `python tools/run_all_validations.py`.

## Refresh public prices

The optional command below contacts market-data providers and appends new observations to the local snapshots:

```bash
python Task7/scripts/update_live_data.py --use-existing-on-error
```

`--use-existing-on-error` permits fallback after a failed fetch; it is not an offline switch. After a successful refresh, rerun the offline reproduction commands. Neither path submits broker orders or operates a JoinQuant account.

## Entry points

- [Monitoring dashboard](dashboard/index.html)
- [JoinQuant evidence guide](inputs/joinquant/README.md)
- [English report](../reports/Task7_Report.pdf)
