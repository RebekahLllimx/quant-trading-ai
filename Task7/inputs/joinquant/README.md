# JoinQuant imports

`backtest_summary.json` supplies the dashboard's platform results. Its `backtest_settings` define the interval, starting capital, and frequency; `backtests` holds the strategy summaries; `short_window_settings` and `short_window_backtests` describe the separate short-window replay. Returns are fractional values, so `0.0291` means 2.91%.

The `evidence_file` fields identify the original screenshot records; they are provenance labels, not links to files shipped in this directory. The local shadow engine reads these imported summaries but cannot recreate a JoinQuant platform backtest.

The simulation-status fields distinguish deployment from exported execution results. A deployed account without exported fills is `deployed_waiting_data`. The public-data shadow portfolio has a separate feed and execution model, so its results remain separate from platform-performance fields. Imports contain research summaries only; credentials and private account information are excluded.
