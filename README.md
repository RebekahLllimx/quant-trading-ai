# Quantitative Trading Coursework

Eight course projects from the Peking University Guanghua Business Analytics Workshop (June-July 2026). The repository covers market-data preparation, indicators, rule-based backtests, machine-learning case studies, and strategy monitoring. It is a research and teaching archive, **not** a live trading service.

[Open the GitHub Pages hub](https://rebekahlllimx.github.io/quant-trading-ai/) to explore the dashboards, or start with the [Task 7 strategy dashboard](Task7/dashboard/index.html).

## What is here

| Task | Work and entry point |
| --- | --- |
| [1. Data engine](Task1/README.md) | Prepare A-share and Hong Kong market data; build candlestick and cross-market views. |
| [2. Technical indicators](Task2/README.md) | Calculate eight indicator families and explore them in an interactive dashboard. |
| [3. Moving-average strategies](Task3/README.md) | Compare crossover and mean-reversion rules in historical backtests. |
| [4. Turtle strategy](Task4/README.md) | Test breakout entries, ATR-based stops, position sizing, and parameter sensitivity. |
| [5. Machine-learning cases](Task5/README.md) | Evaluate classification examples and examine the limits of transferring them to finance. |
| [6. ML strategy research](Task6/README.md) | Build features, predict price direction, and compare research backtests. |
| [7. Strategy deployment study](Task7/README.md) | Document JoinQuant backtests and private simulated accounts alongside a separate public-data shadow portfolio. |
| [8. Final report](Task8/README.md) | Synthesize the methods, findings, and limits of the preceding tasks. |

The [eight course reports](reports/) retain their original analyses and figures. The [directory guide](docs/directory-structure.md) explains shared data, artifacts, and scripts.

## Explore and verify offline

The published [hub](https://rebekahlllimx.github.io/quant-trading-ai/) and committed dashboards can be viewed without an account. To run the repository's offline checks from its root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python -m unittest discover -s tests -v
python Task7/scripts/validate_results.py
python Task2/scripts/build_dashboard.py
```

The final command rebuilds `Task2/dashboard/index.html` from the committed CSV files and can change that generated file locally. It does not fetch fresh prices. For task-specific experiments, use each task's README before running its scripts.

## Data and execution boundaries

- `data/` contains committed inputs and derived datasets used by the course examples. `artifacts/` holds charts and model outputs; `reports/` holds final PDFs.
- Market-data refresh scripts, including [`Task2/scripts/update_data.py`](Task2/scripts/update_data.py), call external APIs. They are separate from the offline commands above.
- JoinQuant's `jqdata` is supplied by that platform and is not installed by `requirements.txt`. The public Task 7 dashboard reconstructs a **shadow portfolio** from public market data; it is not a record of private account fills or realized profit.
- Historical backtests, platform simulation records, and shadow tracking use different data and execution assumptions. See [Task 7's evidence guide](Task7/README.md) before comparing results.
- None of the results establishes future profitability or constitutes investment advice.

## Repository map

| Path | Purpose |
| --- | --- |
| [`Task1/` to `Task8/`](Task1/) | Task instructions, scripts, dashboards, and analyses. |
| [`data/`](data/) | Raw and processed research data plus metadata. |
| [`artifacts/`](artifacts/) | Generated charts and model artifacts. |
| [`reports/`](reports/) | The eight submitted course reports. |
| [`src/`](src/) | Shared code across tasks. |
| [`docs/`](docs/) | Data and directory conventions. |
