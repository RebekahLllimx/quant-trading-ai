# Quantitative Trading Coursework

Eight projects completed for the Peking University Guanghua Business Analytics Workshop (June-July 2026). Together they form a research pipeline from market-data preparation to indicator calculation, rule-based backtesting, machine-learning experiments, portfolio construction, and strategy monitoring.

[Open the GitHub Pages hub](https://rebekahlllimx.github.io/quant-trading-ai/) to explore the dashboards, or start with the [Task 7 strategy dashboard](Task7/dashboard/index.html).

## What is here

| Task | Work and entry point |
| --- | --- |
| [1. Data engine](Task1/README.md) | Prepare A-share and Hong Kong market data; build candlestick and cross-market views. |
| [2. Technical indicators](Task2/README.md) | Calculate eight indicator families and explore them in an interactive dashboard. |
| [3. Moving-average strategies](Task3/README.md) | Compare crossover and mean-reversion rules in historical backtests. |
| [4. Turtle strategy](Task4/README.md) | Test breakout entries, ATR-based stops, position sizing, and parameter sensitivity. |
| [5. Machine-learning cases](Task5/README.md) | Build and validate a classification workflow, then test the same discipline on financial labels. |
| [6. ML strategy research](Task6/README.md) | Build features, predict price direction, and compare research backtests. |
| [7. Strategy deployment study](Task7/README.md) | Compare three ETF strategies and track their signals through backtests and a public-data shadow portfolio. |
| [8. Final report](Task8/README.md) | Synthesize the methods, findings, and limits of the preceding tasks. |

The [eight English reports](reports/) contain the full analysis for each task. The [directory guide](docs/directory-structure.md) explains shared data, artifacts, and scripts; dashboards and structured outputs provide the underlying figures and metrics.

## Research architecture

```text
frozen market snapshots
        -> validated schemas and indicators
        -> rule-based or statistical signals
        -> positions, costs, and portfolio accounting
        -> structured results and validation checks
        -> static dashboards and generated reports
```

The tasks share data conventions and reporting rules but remain independently reproducible. Structured CSV and JSON outputs are the evidence layer; dashboards and PDFs render those artifacts rather than serving as the only copy of a result.

## Key technical decisions

| Decision | Rationale |
| --- | --- |
| Chronological validation for market models | Random splits would mix later market regimes into training and overstate out-of-sample evidence. |
| Explicit signal and execution time | Indicators use completed observations, and positions take effect on the next eligible bar to prevent look-ahead. |
| Costs inside the portfolio engine | Commission, slippage, and turnover are part of the strategy calculation rather than an adjustment added after performance is observed. |
| Frozen inputs for offline reproduction | Committed snapshots allow the same calculations and dashboards to run without live API credentials or provider drift. |
| Structured predictions and portfolio records | Metrics can be recomputed from saved predictions, holdings, trades, and net asset value instead of copied from charts. |
| Separate evidence layers | Historical backtests, platform simulations, and public-data shadow portfolios remain distinct because their feeds and execution rules differ. |

## Explore and verify offline

The published [hub](https://rebekahlllimx.github.io/quant-trading-ai/) and committed dashboards can be viewed without an account. Run the offline checks from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python -m unittest discover -s tests -v
python Task7/scripts/validate_results.py
python Task2/scripts/build_dashboard.py
```

The final command rebuilds `Task2/dashboard/index.html` from committed CSV files. Task-specific commands are listed in each task README.

## Data and execution boundaries

- `data/` contains committed inputs and derived datasets. `artifacts/` stores charts and model outputs; `reports/` stores the final PDFs.
- Refresh scripts such as [`Task2/scripts/update_data.py`](Task2/scripts/update_data.py) call external market-data APIs. Offline builds use committed snapshots.
- JoinQuant supplies `jqdata` inside its platform. Task 7 also maintains a public-data shadow portfolio; platform results and shadow results remain separate because their data and execution rules differ.

## Repository map

| Path | Purpose |
| --- | --- |
| [`Task1/` to `Task8/`](Task1/) | Task scripts, dashboards, and analyses. |
| [`data/`](data/) | Raw and processed research data plus metadata. |
| [`artifacts/`](artifacts/) | Generated charts and model artifacts. |
| [`reports/`](reports/) | Eight maintained English reports generated from the current project evidence. |
| [`src/`](src/) | Shared code across tasks. |
| [`docs/`](docs/) | Data and directory conventions. |
