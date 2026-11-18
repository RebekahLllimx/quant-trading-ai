"""Build eight English trading-research reports from structured task content."""

from __future__ import annotations

from html import escape
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports"
FIGURES = OUTPUT / "figures"


REPORTS = {
    1: {
        "title": "Market Data Engineering for Quantitative Research",
        "overview": "This task establishes the data layer used by the later strategy and machine-learning studies. It normalizes daily A-share and Hong Kong equity data, preserves reproducible snapshots, and exposes the same records to Python analysis and a portable browser dashboard.",
        "sections": [
            ("1. Objective and scope", [
                ("p", "A quantitative result is only as reliable as the prices, timestamps, and corporate-action treatment that enter the calculation. The task therefore begins before strategy design: ten liquid securities were selected across banking, insurance, consumer goods, new energy, internet platforms, telecommunications, and exchange services. The frozen snapshots contain 241 A-share trading days and 244 Hong Kong trading days."),
                ("bullets", [
                    "Retrieve daily open, high, low, close, volume, and turnover fields from AKShare, with Tushare as a provider-specific fallback.",
                    "Use forward-adjusted prices so that ex-dividend and split events do not appear as artificial trading signals.",
                    "Map provider-specific names and types to one internal schema before any chart or return calculation.",
                    "Commit stable CSV snapshots so that reports and dashboards remain reproducible without API credentials.",
                ]),
            ]),
            ("2. Data pipeline and contracts", [
                ("p", "The implementation separates acquisition, validation, storage, and presentation. Provider adapters translate external fields into Date, Symbol, Open, High, Low, Close, Volume, Amount, PctChg, and Turnover. Validation checks date order, duplicate dates, numeric OHLCV values, and the price identity Low <= Open/Close <= High. Failed refreshes do not replace the last valid snapshot."),
                ("table", [
                    ["Layer", "Responsibility", "Output"],
                    ["Acquisition", "Provider request, symbol mapping, adjustment mode", "Raw provider frame"],
                    ["Normalization", "Field names, dates, numeric types, sort order", "Canonical OHLCV frame"],
                    ["Validation", "Missing values, duplicates, price bounds", "Accepted or rejected snapshot"],
                    ["Presentation", "Static charts and embedded browser data", "PNG, CSV, and HTML"],
                ], [30, 80, 45]),
            ]),
            ("3. Cross-market profile", [
                ("figure", "task1_normalized_prices.png", "Figure 1. Closing prices rebased to 100 at the start of each available snapshot."),
                ("p", "The normalized paths show why a single-stock example cannot stand in for a portfolio. CATL rose 55.95% over the summarized interval, while Meituan fell 48.72%. Dispersion also appears in risk: annualized volatility ranges from 11.71% for China Mobile to 47.81% for Alibaba. These differences motivate the later use of benchmarks, position limits, and instrument-level analysis."),
                ("figure", "task1_market_comparison.png", "Figure 2. Period return, annualized volatility, and maximum drawdown for the ten securities."),
            ]),
            ("4. Dashboard and reproducibility", [
                ("p", "The static dashboard embeds the normalized records directly in HTML. The browser computes range return, annualized volatility, drawdown, and win rate, and renders candlestick, volume, return-distribution, and cumulative-return views. Because the data are embedded, the published page can be opened without a running server. Refresh scripts remain separate from the offline build so that a network failure cannot change a saved result."),
                ("p", "The key engineering result is a stable interface between acquisition and analysis. Tasks 2-8 can change indicators, models, or portfolio rules without rewriting the market-data layer."),
            ]),
        ],
    },
    2: {
        "title": "Technical Indicators and Market Diagnostics",
        "overview": "This task implements eight indicator families on a shared OHLCV contract and examines how trend, momentum, volatility, and trend-strength measures describe different aspects of the same price history.",
        "sections": [
            ("1. Data and diagnostic baseline", [
                ("p", "The main example is Kweichow Moutai from 29 May 2025 to 3 July 2026, containing 267 trading days. The five core OHLCV fields contain no missing observations in the frozen course sample. Mean daily return is -0.0675%, daily volatility is 1.2819%, annualized volatility is 20.35%, and maximum drawdown is -23.47%."),
                ("p", "The Jarque-Bera statistic is 948.09 with a p-value below 0.001. Together with negative skewness and excess kurtosis, this rejects a normal-return approximation. Thresholds based on standard deviations must therefore be interpreted as descriptive rules rather than exact tail probabilities."),
            ]),
            ("2. Indicator definitions", [
                ("table", [
                    ["Indicator", "Default", "Primary information"],
                    ["MA", "5, 10, 20, 60", "Smoothed price level and trend direction"],
                    ["MACD", "12, 26, 9", "Difference between fast and slow exponential trends"],
                    ["RSI", "14", "Wilder-smoothed balance of gains and losses"],
                    ["KDJ", "9, 3, 3", "Location of the close inside the recent high-low range"],
                    ["Bollinger Bands", "20, 2", "Moving average plus/minus two rolling standard deviations"],
                    ["ATR", "14", "True range including overnight gaps"],
                    ["ADX", "14", "Strength of directional movement, independent of sign"],
                    ["CCI", "20", "Deviation of typical price from its rolling mean"],
                ], [33, 27, 95]),
                ("p", "RSI, ATR, and ADX use Wilder smoothing with alpha = 1/N. MACD uses exponential moving averages with alpha = 2/(N+1). Bollinger Bands use a population rolling standard deviation. Every function preserves the input index and leaves its warm-up region missing instead of replacing unavailable history with zeros."),
            ]),
            ("3. Joint interpretation", [
                ("figure", "task2_indicator_panels.png", "Figure 1. Price and Bollinger envelope, RSI(14), and MACD(12, 26, 9) on the same history."),
                ("p", "The panels should be read together. A price above its moving average describes direction; RSI describes the balance of recent gains and losses; MACD describes the separation and convergence of two trend estimates; Bollinger width describes changing dispersion. None of these quantities is a trade by itself. A strategy must still define the decision time, execution price, position size, exit rule, and transaction cost."),
            ]),
            ("4. Parameter sensitivity and validation", [
                ("bullets", [
                    "Short lookbacks react quickly but generate more sign changes and more potential turnover.",
                    "Long lookbacks suppress noise but delay both entry and exit.",
                    "Indicator values are aligned to the original dates, allowing later code to shift a signal explicitly before execution.",
                    "Unit tests compare formula outputs, index alignment, warm-up length, and behavior on constant or incomplete series.",
                ]),
                ("p", "The task produces a reusable indicator engine rather than a ranking of indicators. Tasks 3 and 4 supply the missing trading contract by connecting selected indicators to positions, costs, and portfolio value."),
                ("p", "The main interpretive lesson is that an indicator parameter represents a time scale, not a universally optimal setting. Short windows increase responsiveness and turnover; long windows trade responsiveness for stability. The original study also suggests treating trend strength as a regime descriptor: a threshold such as ADX 20 or 25 can organize analysis, but it should not be promoted to a fixed law from one large-cap sample."),
            ]),
        ],
    },
    3: {
        "title": "Moving-Average Strategy Design and Backtesting",
        "overview": "This task turns a familiar moving-average crossover into an auditable backtest with explicit timing, costs, benchmark comparison, trade records, and parameter sensitivity.",
        "sections": [
            ("1. Strategy contract", [
                ("bullets", [
                    "Enter long when MA(5) crosses above MA(15); exit when MA(5) crosses below MA(15).",
                    "Compute signals from completed observations and apply the resulting position on the next eligible bar.",
                    "Remain long-only and unlevered; hold cash outside a position.",
                    "Charge 0.03% commission and 0.01% slippage on each side of a trade.",
                    "Compare the net strategy with buy-and-hold over the identical instrument and date range.",
                ]),
                ("p", "Separating signal time from execution time is essential. Using the same close to both confirm a crossover and fill the order would assume information that was unavailable before that close."),
            ]),
            ("2. Signal behavior", [
                ("figure", "task3_signals.png", "Figure 1. MA(5, 15) entries and exits on the frozen Kweichow Moutai sample."),
                ("p", "The rule reduces exposure during sustained declines, but it also trades after the trend has already changed. In range-bound periods the two averages repeatedly cross and reverse, creating small losses and costs. The mechanism is therefore transparent: it exchanges early entry for confirmation and accepts lag as the price of smoothing."),
            ]),
            ("3. Backtest result", [
                ("table", [
                    ["Metric", "MA(5, 15)", "Buy and hold"],
                    ["Cumulative return", "-5.67%", "-18.24%"],
                    ["Maximum drawdown", "-15.20%", "-21.35%"],
                    ["Position rule", "Long or cash", "Continuously long"],
                ], [60, 45, 45]),
                ("p", "The strategy outperformed the benchmark by 12.57 percentage points and reduced drawdown by 6.15 percentage points, but absolute return remained negative. The result supports a narrower claim: exposure control helped in this declining sample. It does not establish that the crossover generates positive returns across instruments or market regimes."),
            ]),
            ("4. Parameter sensitivity", [
                ("figure", "task3_sensitivity.png", "Figure 2. Net-return surface across short and long moving-average windows."),
                ("p", "Most tested combinations remain negative. Better results appear in limited regions rather than across a broad, smooth plateau. A single best pair is therefore less informative than the neighborhood around it. A production research process would select parameters on a development window and evaluate them once on an untouched period."),
            ]),
            ("5. Implementation result", [
                ("p", "The backtest stores positions, cash, trades, turnover, net asset value, and drawdown for each date. The dashboard recomputes the strategy under alternative windows and costs, making the execution assumptions explicit."),
                ("p", "The remaining weakness is structural rather than cosmetic. Fixed position size and a crossover-only exit do not normalize risk across volatility regimes or protect against a sharp move between signals. This limitation motivates the ATR sizing, stops, and stateful accounting introduced in Task 4."),
            ]),
        ],
    },
    4: {
        "title": "Turtle Trading: Rules, Risk, and Sensitivity",
        "overview": "This task implements a stateful breakout system. Donchian channels define entries and exits, ATR converts volatility into position size and stop distance, and the engine tracks pyramiding, cash, exposure, and transaction costs through time.",
        "sections": [
            ("1. Trading rules", [
                ("table", [
                    ["Component", "Rule"],
                    ["Entry", "Break above the prior 20-day high"],
                    ["Exit", "Break below the prior 10-day low or hit an ATR stop"],
                    ["Risk unit", "Risk budget divided by twice the ATR stop distance"],
                    ["Pyramiding", "Add after each favorable half-ATR move, up to four units"],
                    ["Costs", "Commission and slippage deducted at each fill"],
                ], [42, 108]),
                ("p", "Channel values are shifted so that the current high or low cannot define the threshold that it is simultaneously breaking. ATR includes intraday range and gaps from the previous close. These two timing decisions prevent the most common forms of look-ahead in a daily-bar implementation."),
            ]),
            ("2. Stateful implementation", [
                ("p", "The engine maintains cash, shares, average entry price, number of units, last add price, stop level, and the outcome of the preceding breakout. Each bar follows a fixed sequence: update observable inputs, test entry or add conditions, tighten the stop, test stop and channel exits, apply costs, and record equity. The stop can move upward for a long position but cannot loosen."),
                ("bullets", [
                    "Position size falls when ATR rises, keeping estimated loss per unit of capital comparable across volatility regimes.",
                    "Pyramiding uses available cash and recomputes the weighted entry price after each add.",
                    "Forced liquidation at the final bar closes the accounting record for comparison with buy-and-hold.",
                    "Trade records retain entry, adds, exit, price, shares, return, and exit reason.",
                ]),
            ]),
            ("3. Backtest result", [
                ("figure", "task4_equity_drawdown.png", "Figure 1. Turtle equity, buy-and-hold equity, and strategy drawdown on the frozen sample."),
                ("table", [
                    ["Metric", "Turtle strategy", "Buy and hold"],
                    ["Cumulative return", "-2.21%", "-18.24%"],
                    ["Maximum drawdown", "-8.60%", "-21.35%"],
                    ["Annualized volatility", "6.73%", "Not used for rule selection"],
                    ["Completed trades", "5", "1 continuous holding"],
                    ["Win rate", "40.0%", "Not applicable"],
                ], [58, 45, 52]),
                ("p", "The system lost 2.21%, but it reduced the benchmark loss by 16.03 percentage points and limited drawdown through low exposure and stop-based exits. The negative Sharpe ratio (-0.578) and five-trade sample rule out a broad profitability claim; the useful result is the observable link between volatility, position size, and drawdown."),
            ]),
            ("4. Sensitivity and failure modes", [
                ("bullets", [
                    "Short channels react faster but are more vulnerable to false breakouts.",
                    "Wide ATR stops reduce premature exits but increase loss per share and lower position size.",
                    "Risk controls may reduce both drawdown and capital utilization; both must be reported.",
                    "Daily bars cannot guarantee fills at a stop during a gap or liquidity shock.",
                ]),
                ("p", "The strategy demonstrates why risk management is part of the algorithm rather than a note added after backtesting. Entry logic, sizing, stop behavior, and accounting must be tested as one state machine."),
            ]),
        ],
    },
    5: {
        "title": "Machine-Learning Classification and Financial Tests",
        "overview": "This task first builds a complete supervised-classification workflow on a labeled medical dataset, then applies the same validation discipline to three chronological financial labels to test whether the workflow transfers to noisier market data.",
        "sections": [
            ("1. Validation design", [
                ("p", "The primary dataset contains 569 observations and 30 cell-nucleus features. Malignant cases are encoded as the positive class. A stratified 80/20 split produces 455 training observations and 114 test observations. Feature screening is fitted on the training set only, and all models are evaluated on the same untouched test set."),
                ("bullets", [
                    "Compare logistic regression, decision tree, random forest, and gradient boosting.",
                    "Report ROC-AUC, balanced accuracy, recall, F1, Brier score, and confusion matrices.",
                    "Recompute metrics from stored predictions rather than copying displayed values.",
                    "Record random seeds, input hashes, split boundaries, and selected features.",
                ]),
            ]),
            ("2. Primary classification result", [
                ("figure", "task5_medical_roc.png", "Figure 1. Test-set ROC curves for the four primary classifiers."),
                ("table", [
                    ["Model", "Test ROC-AUC", "Interpretation"],
                    ["Logistic regression", "approximately 0.994", "Strong linear probability ranking"],
                    ["Random forest", "approximately 0.994", "Comparable ranking with nonlinear splits"],
                    ["Gradient boosting", "approximately 0.992", "Similar test discrimination"],
                    ["Decision tree", "approximately 0.972", "Lower and less stable than the ensemble models"],
                ], [48, 37, 70]),
                ("p", "The confidence intervals overlap, so differences at the third decimal place do not establish a stable model ranking. The comparison is more useful for showing how evaluation changes with probability calibration, class balance, and threshold selection than for declaring one universal winner."),
                ("p", "Figure 1 also shows why a single accuracy number would be insufficient. The strongest models move rapidly toward the upper-left corner, meaning they preserve high sensitivity while admitting few false positives across a range of thresholds. Choosing an operating point would still require an explicit cost for missed malignant cases and unnecessary follow-up; the ROC curve ranks that trade-off but does not choose it."),
            ]),
            ("3. Financial transfer study", [
                ("p", "Financial labels require chronological splits because randomly mixing dates would expose the model to later market regimes during training. Three designs were tested: cross-sectional ranking, absolute price direction, and a single-stock excess-return label. Their best held-out AUC values were 0.533, 0.529, and 0.524; every confidence interval covered 0.5."),
                ("figure", "task5_financial_auc.png", "Figure 2. Financial model results with bootstrap confidence intervals and the random-ranking baseline."),
                ("p", "Random-label controls remain near 0.5, while a deliberately predictable synthetic label produces a high AUC. These checks show that the metric pipeline can detect signal when signal is present. The weak financial results therefore point to the selected labels, features, horizon, and sample stability rather than a broken AUC implementation."),
                ("p", "In Figure 2, the bars differ only slightly from the 0.5 reference and their intervals cross it. That visual pattern matters more than the ordering of the point estimates: none of the three specifications demonstrates a ranking relationship stable enough to justify a trading rule. The negative result is therefore retained rather than hidden behind the much stronger medical example."),
                ("p", "The original investigation reached a broader conclusion: more variables did not create more information. Many price and indicator features described the same recent path, while omitted fundamentals, disclosure timing, and market events became more important at longer horizons. Target design also changed the effective sample size: overlapping forward windows and market-wide direction labels could make nominally numerous observations behave like far fewer independent cases."),
            ]),
            ("4. Engineering and audit trail", [
                ("p", "The workflow writes cleaned datasets, prediction files, model metrics, feature decisions, and figures to stable paths. Validation scripts check input hashes, label definitions, chronological boundaries, prediction grain, metric recomputation, and required outputs. The dashboard reads these structured artifacts instead of recalculating results in the browser."),
            ]),
            ("5. Conclusion", [
                ("p", "A sound classification pipeline can transfer across domains, but predictive performance does not transfer automatically. In the medical case, independent observations and informative features support high discrimination. In the financial cases, overlapping horizons, regime changes, and a low signal-to-noise ratio make out-of-sample stability the main constraint."),
            ]),
            ("6. Next experiment", [
                ("bullets", [
                    "Choose the economic decision and forecast horizon before expanding the feature set.",
                    "Build point-in-time fundamental and event features using their actual disclosure dates.",
                    "Use nested chronological validation, then evaluate the selected design once on a later untouched period.",
                    "Translate ranking quality into positions only after adding turnover, capacity, and transaction-cost constraints.",
                ]),
            ]),
        ],
    },
    6: {
        "title": "Machine-Learning Signals and Portfolio Construction",
        "overview": "This task connects model output to portfolio decisions. The main study ranks stocks each quarter and forms a top-30 portfolio; an extension predicts a single stock's three-day direction and maps probability to a dynamic position.",
        "sections": [
            ("1. Main study: quarterly ranking", [
                ("p", "The main sample contains 39,616 stock-quarter records, 4,281 securities, and ten quarters from 31 March 2020 to 30 June 2022. Seven quarters are used for model development and three for final testing. Nineteen raw financial factors are transformed into within-quarter percentile ranks, reducing scale differences and the influence of extreme values."),
                ("bullets", [
                    "Regression models predict next-quarter return rank; logistic regression predicts whether return exceeds the quarter median.",
                    "Linear, ridge, logistic, decision-tree, random-forest, and histogram-gradient models share the same chronological split.",
                    "Each quarter, the strategy buys the 30 highest predicted scores at equal weight.",
                    "Net return deducts 0.2% multiplied by one-way turnover.",
                    "A rank buffer tests whether retaining near-cutoff holdings can reduce unnecessary turnover.",
                ]),
            ]),
            ("2. Portfolio results", [
                ("figure", "task6_portfolio_wealth.png", "Figure 1. Cumulative wealth for the main portfolio and benchmark over the test quarters."),
                ("table", [
                    ["Portfolio", "Cumulative net return", "Annualized volatility", "Average turnover"],
                    ["Equal-weight top 30", "41.5%", "11.0%", "83.3%"],
                    ["Prediction-weighted top 30", "46.3%", "15.7%", "85.9%"],
                    ["Market-wide equal weight", "-15.9%", "Benchmark", "Not applicable"],
                ], [50, 38, 38, 36]),
                ("figure", "task6_weighting_comparison.png", "Figure 2. Equal-weight and prediction-weighted portfolio comparison."),
                ("p", "Prediction weighting adds 4.8 percentage points of return but also raises volatility and concentration. The test contains only three quarters, so annualized metrics are mechanically unstable. The result is best read as a portfolio-construction comparison under one held-out interval, not as a long-horizon performance estimate."),
                ("p", "The stepwise wealth paths in Figure 1 are a consequence of quarterly rebalancing rather than daily mark-to-market observations. Figure 2 isolates the weighting choice: both portfolios hold the same ranked names, but prediction weighting concentrates capital in the highest scores. The extra return therefore cannot be separated from the extra concentration without a longer test and position-level risk attribution."),
            ]),
            ("3. Extension: single-stock timing", [
                ("p", "The extension predicts whether Ping An Bank's three-day forward return is positive. A walk-forward logistic model uses a 180-row rolling window. The final test ROC-AUC is 0.571, compared with 0.631 on validation. Probabilities above 0.60 permit entry, probabilities below 0.35 exit, and the target position increases linearly above 0.5 up to an 80% cap."),
                ("table", [
                    ["Strategy", "Net return", "Maximum drawdown", "Days in market"],
                    ["ML timing", "0.50%", "-1.37%", "39.4%"],
                    ["Moving average", "9.68%", "-3.78%", "70.6%"],
                    ["Buy and hold", "9.93%", "-10.61%", "99.1%"],
                ], [48, 35, 38, 35]),
                ("p", "The model's ranking accuracy is above random, but the trading rule does not outperform the two simple benchmarks. Low exposure limits drawdown and return simultaneously. This distinction matters: model AUC, signal thresholds, position sizing, turnover, and realized strategy return are separate stages of the system."),
                ("p", "Three modelling rounds also exposed a validation trap. Shorter labels and fewer features improved the untouched test period even when a wider tuning search produced the best validation AUC. The exercise therefore treats the test window as a one-time audit, not as another surface on which to select the final specification."),
                ("figure", "task6_validation_gap.png", "Figure 3. The specification selected by validation AUC deteriorates sharply on the untouched test, while the frozen rolling baseline transfers more consistently."),
                ("p", "The comparison also changed the interpretation of the model. A 0.571 AUC is evidence of weak ranking information, not evidence that the complete strategy is useful. Entry thresholds left the portfolio in cash for most observations, while the moving-average rule captured more of the favorable price path. A better next experiment would redesign signal, sizing, and benchmark together rather than optimize the classifier in isolation."),
            ]),
            ("4. Data and implementation limits", [
                ("p", "The main study lacks complete point-in-time disclosure metadata, historical index membership, and full suspension, ST, and liquidity flags. The project records these fields as missing rather than silently treating the modern universe as historically complete. Future work should rebuild the universe and fundamentals from timestamped point-in-time sources before extending the test horizon."),
                ("bullets", [
                    "Repeat the portfolio test over more quarters and report performance by market regime.",
                    "Lock the feature set, rolling window, and decision thresholds before opening the next test period.",
                    "Stress higher turnover costs and add liquidity and concentration limits before interpreting scalability.",
                ]),
            ]),
        ],
    },
    7: {
        "title": "ETF Strategy Backtesting and Monitoring",
        "overview": "This task compares three broad-market ETF strategies across JoinQuant backtests, local sensitivity tests, and a public-data shadow portfolio. Each evidence layer is reported separately because its prices, scheduling, and execution rules differ.",
        "sections": [
            ("1. Strategy definitions", [
                ("table", [
                    ["Strategy", "Rule", "Risk control"],
                    ["A", "Hold CSI 300 ETF when close > MA20", "Cash when trend filter is false"],
                    ["B", "MA(10, 30) trend filter", "ATR stop, 1% risk budget, 50% cap, drawdown pause"],
                    ["C", "Rank three ETFs by 15-day log-price slope multiplied by R-squared", "Hold the best positive score at 50%; otherwise cash"],
                ], [28, 70, 67]),
                ("p", "The strategies form a deliberate complexity ladder: a template trend baseline, a single-asset trend system with volatility controls, and a cross-asset momentum selector. Signals use completed price data and are scheduled for the next trading session."),
            ]),
            ("2. JoinQuant platform backtests", [
                ("figure", "task7_platform_comparison.png", "Figure 1. Cumulative return and maximum drawdown from the common JoinQuant backtest interval."),
                ("table", [
                    ["Strategy", "Cumulative return", "Maximum drawdown", "Sharpe", "Beta"],
                    ["A", "-0.66%", "-36.97%", "-0.291", "0.521"],
                    ["B", "2.91%", "-12.31%", "-0.769", "0.164"],
                    ["C", "71.84%", "-16.91%", "0.315", "0.426"],
                ], [31, 38, 38, 28, 28]),
                ("p", "Strategy B achieves its low drawdown largely through low market exposure; the risk statistic must therefore be read with capital utilization. Strategy C produces the strongest return in this interval, but the result is concentrated in particular periods and remains sensitive to turnover, ETF selection, and momentum-window choice."),
            ]),
            ("3. Shadow portfolio", [
                ("figure", "task7_shadow_nav.png", "Figure 2. Deterministic reconstruction from public prices under the frozen strategy rules."),
                ("p", "The shadow engine reconstructs signals from public daily prices, applies the stated costs, and stores positions, orders, and portfolio value. It is useful for continuous observation and regression testing. It is not merged with JoinQuant results because the public feed, fill model, and platform schedule are not identical."),
            ]),
            ("4. Monitoring design", [
                ("bullets", [
                    "The dashboard labels platform backtests, private simulation status, local research, and shadow results by source.",
                    "Validation checks dates, portfolio arithmetic, required result fields, and account-information boundaries.",
                    "Parameter sensitivity is evaluated around the frozen MA and momentum settings rather than replacing them after observing later returns.",
                    "The workflow can refresh prices and rebuild the dashboard without changing the strategy definitions.",
                ]),
                ("p", "The engineering result is the separation of research, deployment evidence, and ongoing observation. Performance numbers remain traceable to a specific data layer and execution model."),
                ("p", "This separation also prevents a common reporting error: a platform backtest, a public-price reconstruction, and a paper-trading observation are not interchangeable simply because they implement similarly named rules. Feed adjustments, fill assumptions, scheduling, and available account state can each change the realized path."),
            ]),
        ],
    },
    8: {
        "title": "Integrated Quantitative Trading Project",
        "overview": "This report synthesizes the preceding tasks as one research system, from market-data contracts and indicator calculations to rule-based strategies, machine-learning portfolios, and monitored execution evidence.",
        "sections": [
            ("1. Research pipeline", [
                ("figure", "task8_pipeline.png", "Figure 1. The six stages of the maintained research pipeline."),
                ("p", "Each stage has an explicit input and output. Market snapshots feed aligned indicators; indicators become signals only after timing and execution rules are defined; model scores become portfolios only after ranking, weighting, and cost rules are specified; deployment evidence is stored separately from historical backtests."),
            ]),
            ("2. What the rule-based studies show", [
                ("table", [
                    ["Study", "Return", "Maximum drawdown", "Primary finding"],
                    ["MA(5, 15)", "-5.67%", "-15.20%", "Reduced loss versus buy-and-hold, with lag and whipsaw"],
                    ["Turtle", "-2.21%", "-8.60%", "ATR sizing and stops lowered exposure and drawdown"],
                    ["Buy and hold", "-18.24%", "-21.35%", "Common benchmark for the same instrument and interval"],
                ], [34, 30, 36, 68]),
                ("p", "Both strategies improved relative performance during a declining sample, but neither produced a positive absolute return. Their value in this project is mechanistic: every entry, exit, cost, and risk decision can be traced to a rule and tested under nearby parameters."),
            ]),
            ("3. What the machine-learning studies show", [
                ("p", "The classification workflow performs strongly on the medical teaching dataset, while three financial classification labels remain near random out of sample. The portfolio study produces a strong three-quarter top-30 result, but its short test horizon and incomplete point-in-time metadata limit generalization. The single-stock extension reaches an AUC of 0.571 yet underperforms simple trading benchmarks."),
                ("p", "These outcomes separate three questions that are often conflated: whether a model ranks labels, whether scores can be converted into positions, and whether the resulting positions outperform after costs. A positive answer at one stage does not guarantee the next."),
            ]),
            ("4. Engineering principles", [
                ("bullets", [
                    "Use one canonical schema and preserve snapshot dates, adjustment rules, and source metadata.",
                    "Make signal time and execution time explicit; shift every feature and label according to information availability.",
                    "Store predictions, holdings, trades, and metrics as structured artifacts that can be recomputed.",
                    "Compare strategies on the same instrument, dates, costs, and benchmark before interpreting differences.",
                    "Separate backtests, platform simulations, and shadow portfolios instead of combining incompatible return series.",
                ]),
            ]),
            ("5. Final assessment", [
                ("p", "The project progresses from using market-data APIs to maintaining an auditable research repository. Its strongest evidence is not a single return number but the ability to connect data contracts, algorithms, portfolio rules, validation, and monitoring. The next research priority is a longer point-in-time dataset with historical membership and liquidity fields, followed by walk-forward evaluation across multiple market regimes."),
                ("p", "The original review suggests an order for future work: improve data governance and out-of-sample design before adding model complexity; then stress transaction costs, liquidity, and execution; finally add regime-aware exposure, portfolio-level risk budgets, and monitored paper trading. This order keeps new sophistication tied to a specific failure mode rather than treating complexity as progress by itself."),
            ]),
        ],
    },
}


def report_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#151719"), spaceAfter=5))
    styles.add(ParagraphStyle(name="Meta", fontName="Helvetica", fontSize=8.7, leading=12, textColor=colors.HexColor("#626870"), spaceAfter=14))
    styles.add(ParagraphStyle(name="Overview", fontName="Helvetica", fontSize=10.5, leading=16, textColor=colors.HexColor("#202428"), spaceAfter=13))
    styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=13.2, leading=18, textColor=colors.HexColor("#17191C"), spaceBefore=11, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10.1, leading=15.4, textColor=colors.HexColor("#22262B"), spaceAfter=7, allowWidows=0, allowOrphans=0))
    styles.add(ParagraphStyle(name="ReportBullet", fontName="Helvetica", fontSize=9.9, leading=14.7, leftIndent=12, firstLineIndent=-7, bulletIndent=2, textColor=colors.HexColor("#22262B"), spaceAfter=4))
    styles.add(ParagraphStyle(name="Caption", fontName="Helvetica-Oblique", fontSize=8.2, leading=11.3, alignment=1, textColor=colors.HexColor("#59616A"), spaceBefore=4, spaceAfter=9))
    styles.add(ParagraphStyle(name="TableHead", fontName="Helvetica-Bold", fontSize=8.2, leading=10.5, textColor=colors.white))
    styles.add(ParagraphStyle(name="TableCell", fontName="Helvetica", fontSize=8.2, leading=10.7, textColor=colors.HexColor("#22262B")))
    return styles


def paragraph(text: str, style) -> Paragraph:
    return Paragraph(escape(text), style)


def figure_parts(path: Path, caption: str, styles):
    with PILImage.open(path) as source:
        width, height = source.size
    max_width, max_height = 163 * mm, 100 * mm
    scale = min(max_width / width, max_height / height)
    image = Image(str(path), width=width * scale, height=height * scale)
    return [image, Paragraph(escape(caption), styles["Caption"])]


def report_table(rows, widths, styles):
    data = []
    for row_index, row in enumerate(rows):
        style = styles["TableHead"] if row_index == 0 else styles["TableCell"]
        data.append([Paragraph(escape(str(cell)), style) for cell in row])
    table = Table(data, colWidths=[width * mm for width in widths], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3E4852")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CED3D8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F6F7")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def block_flowables(block, styles):
    kind = block[0]
    if kind == "p":
        return [KeepTogether([paragraph(block[1], styles["Body"])])]
    if kind == "bullets":
        return [Paragraph(escape(item), styles["ReportBullet"], bulletText="-") for item in block[1]]
    if kind == "table":
        return [KeepTogether([report_table(block[1], block[2], styles), Spacer(1, 4 * mm)])]
    if kind == "figure":
        path = (FIGURES / block[1]).resolve()
        if not path.exists():
            path = (ROOT / block[1]).resolve()
        return [KeepTogether(figure_parts(path, block[2], styles))]
    raise ValueError(kind)


def first_page(canvas, document):
    canvas.saveState(); canvas.restoreState()


def later_page(canvas, document):
    canvas.saveState()
    width, height = A4
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(colors.HexColor("#737980"))
    canvas.drawRightString(width - 20 * mm, 10 * mm, str(document.page))
    canvas.restoreState()


def build_report(task: int) -> Path:
    spec = REPORTS[task]
    styles = report_styles()
    story = [
        Paragraph(escape(spec["title"]), styles["ReportTitle"]),
        Paragraph(f"Quantitative Trading Research - Task {task}<br/>2026", styles["Meta"]),
        Paragraph("Overview", styles["Section"]),
        Paragraph(escape(spec["overview"]), styles["Overview"]),
    ]
    for heading, blocks in spec["sections"]:
        if blocks[0][0] == "figure":
            block = blocks[0]
            path = (FIGURES / block[1]).resolve()
            if not path.exists():
                path = (ROOT / block[1]).resolve()
            story.append(KeepTogether([
                Paragraph(escape(heading), styles["Section"]),
                *figure_parts(path, block[2], styles),
            ]))
            remaining_blocks = blocks[1:]
        elif blocks[0][0] == "table":
            block = blocks[0]
            story.append(KeepTogether([
                Paragraph(escape(heading), styles["Section"]),
                report_table(block[1], block[2], styles),
                Spacer(1, 4 * mm),
            ]))
            remaining_blocks = blocks[1:]
        else:
            story.append(Paragraph(escape(heading), styles["Section"]))
            remaining_blocks = blocks
        for block in remaining_blocks:
            story.extend(block_flowables(block, styles))

    output = OUTPUT / f"Task{task}_Report.pdf"
    document = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=18 * mm, bottomMargin=17 * mm, title=spec["title"],
        author="", subject="Quantitative trading research report",
    )
    document.build(story, onFirstPage=first_page, onLaterPages=later_page)
    return output


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for task_number in range(1, 9):
        print(build_report(task_number))
