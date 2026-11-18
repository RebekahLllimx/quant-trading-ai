# Quantitative Trading Research

Compare rule-based and machine-learning trading strategies using explicit execution timing, transaction costs, and chronological validation. Eight connected studies cover market-data preparation, indicators, backtesting, predictive models, portfolio construction, and strategy monitoring.

[Open the GitHub Pages hub](https://rebekahlllimx.github.io/quant-trading-ai/) to explore the dashboards, or start with the [Task 7 strategy dashboard](Task7/dashboard/index.html).

Developed for the Peking University Guanghua Business Analytics Workshop (June-July 2026).

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

The [eight English reports](reports/) summarize the methods and findings for each task. The [directory guide](docs/directory-structure.md) explains shared data, artifacts, and scripts; dashboards and structured outputs provide the underlying figures and metrics.

## Research architecture

```text
frozen market snapshots
        -> validated schemas and indicators
        -> rule-based or statistical signals
        -> positions, costs, and portfolio accounting
        -> structured results and validation checks
        -> static dashboards and generated reports
```

The tasks share data conventions and reporting rules, with separate research entry points. Structured CSV and JSON outputs preserve predictions, trades, and metrics. Task READMEs distinguish offline checks, model reruns, and dashboard builds.

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

The published [hub](https://rebekahlllimx.github.io/quant-trading-ai/) and committed dashboards can be viewed without an account. For local checks, use Python 3.10 (the CI version) and the pinned NumPy, pandas, and scikit-learn versions in `requirements.txt`. The saved Task 6 model bundles record those versions; loading them with a different scikit-learn release is not the validated reproduction path.

Run from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python tools/run_all_validations.py
```

The validation command checks repository structure, regression tests, and saved Task 5-7 results without refreshing market data or retraining models. It restores timestamp-only validation artifacts after checking. Task-specific build commands are listed in each README; builders overwrite their documented generated outputs.

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
| [`reports/`](reports/) | Eight English reports covering methods, results, and interpretation. |
| [`src/`](src/) | Shared code across tasks. |
| [`docs/`](docs/) | Data and directory conventions. |
