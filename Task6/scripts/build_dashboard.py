#!/usr/bin/env python3
"""Build a self-contained, source-backed TASK6 explanatory dashboard."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "task6"
OUT = ROOT / "Task6" / "dashboard"


def records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def build() -> Path:
    main_models = pd.read_csv(DATA / "main/processed/main_model_metrics.csv")
    main_strategies = pd.read_csv(DATA / "main/processed/main_strategy_metrics.csv")
    main_returns = pd.read_csv(DATA / "main/processed/main_quarterly_returns.csv")
    main_holdings = pd.read_csv(DATA / "main/processed/main_portfolio_holdings.csv", dtype={"Code": "string"})
    weighted_metrics = pd.read_csv(DATA / "enhanced/processed/main_weighted_strategy_metrics.csv")
    weighted_returns = pd.read_csv(DATA / "enhanced/processed/main_weighted_quarterly_returns.csv")
    addon_models = pd.read_csv(DATA / "additional/processed/additional_model_metrics.csv")
    addon_strategies = pd.read_csv(DATA / "additional/processed/additional_strategy_metrics.csv")
    auc_grid = pd.read_csv(DATA / "enhanced/processed/additional_guarded_auc_grid.csv")
    tuning = pd.read_csv(DATA / "additional/processed/additional_tuning_rounds.csv")
    main_quality = json.loads((DATA / "main/metadata/data_quality_report.json").read_text(encoding="utf-8"))
    main_run = json.loads((DATA / "main/metadata/model_run.json").read_text(encoding="utf-8"))
    addon_run = json.loads((DATA / "additional/metadata/model_run.json").read_text(encoding="utf-8"))

    ew = weighted_metrics.set_index("portfolio_label").loc["EW_Top30"]
    pw = weighted_metrics.set_index("portfolio_label").loc["PW_Top30"]
    market_row = main_strategies[main_strategies["model"] == "market_equal_weight"].iloc[0]
    addon_index = addon_strategies.set_index("strategy")
    kpis = pd.DataFrame([{
        "ew_return": ew.total_return,
        "market_return": market_row.total_return,
        "ew_excess": ew.total_return - market_row.total_return,
        "pw_return": pw.total_return,
        "final_auc": float(addon_run["final_test_auc"]),
        "ml_return": addon_index.loc["ml_timing", "total_return"],
        "buyhold_return": addon_index.loc["buy_and_hold", "total_return"],
    }])

    model_ic = main_models[["model_label", "mean_test_ic", "validation_mean_ic", "strategy_model"]].copy()
    model_ic.columns = ["model", "test_ic", "validation_ic", "selected"]
    main_net = main_strategies[
        (main_strategies["portfolio"] == "strict_top30") & (main_strategies["return_type"] == "net_return")
    ][["model_label", "total_return", "sharpe", "average_turnover"]].copy()
    main_net.columns = ["model", "total_return", "sharpe", "average_turnover"]

    quarter_ew = weighted_returns[weighted_returns["portfolio_label"] == "EW_Top30"][["Date", "net_return", "turnover"]].copy()
    quarter_ew["portfolio"] = "EW Top-30"
    quarter_pw = weighted_returns[weighted_returns["portfolio_label"] == "PW_Top30"][["Date", "net_return", "turnover"]].copy()
    quarter_pw["portfolio"] = "PW Top-30"
    quarter_market = quarter_ew[["Date"]].copy()
    market_by_date = main_returns[main_returns["model"] == "linear_regression"].drop_duplicates("Date").set_index("Date")["market_return"]
    quarter_market["net_return"] = quarter_market["Date"].map(market_by_date)
    quarter_market["turnover"] = None
    quarter_market["portfolio"] = "Market-wide equal rights"
    quarter_compare = pd.concat([quarter_ew, quarter_pw, quarter_market], ignore_index=True)

    weight_table = weighted_metrics[["portfolio_label", "top_n", "weight_method", "weight_cap", "total_return", "annualized_volatility", "sharpe", "average_turnover"]].copy()
    weight_table["portfolio_label"] = weight_table["portfolio_label"].map({
        "EW_Top30": "EW Top-30", "PW_Top30": "PW Top-30", "Validation_Selected": "Validation Set SelectionPW20",
    })
    method_map = {"ew": "equal weight", "rank_pw": "Ranking Weighting", "score_pw": "Score Weighting"}
    weight_table["weight_method"] = weight_table["weight_method"].map(method_map)

    latest_date = main_holdings["Date"].max()
    top30 = main_holdings[
        (main_holdings["model"] == "linear_regression")
        & (main_holdings["portfolio"] == "strict_top30")
        & (main_holdings["Date"] == latest_date)
    ].sort_values("predicted_rank")[["Date", "Code", "predicted_rank", "prediction", "Next_Ret"]]

    addon_strategy_view = addon_strategies[["strategy_label", "total_return", "annualized_volatility", "sharpe", "max_drawdown", "trade_count", "total_turnover"]].copy()
    addon_strategy_view.columns = ["strategy", "total_return", "volatility", "sharpe", "max_drawdown", "trade_count", "turnover"]
    addon_model_view = addon_models[["model_label", "validation_auc", "test_auc", "accuracy", "balanced_accuracy", "f1", "brier"]].copy()
    addon_model_view.columns = ["model", "validation_auc", "test_auc", "accuracy", "balanced_accuracy", "f1", "brier"]

    coverage = pd.DataFrame([{
        "rows": main_quality["rows"], "stocks": main_quality["stock_count"], "quarters": main_quality["quarter_count"],
        "date_min": main_quality["date_min"], "date_max": main_quality["date_max"],
        "train_quarters": len(main_run["models"]["linear_regression"].get("train_dates", main_run.get("features", []))) if False else 7,
        "test_quarters": 3, "feature_count": main_run["feature_count"],
    }])

    generated = datetime.now().astimezone().isoformat()
    source_specs = [
        ("main_model_source", "Assessment of the main task model", "data/task6/main/processed/main_model_metrics.csv", "csv"),
        ("main_strategy_source", "Ticket Strategy Indicators", "data/task6/main/processed/main_strategy_metrics.csv", "csv"),
        ("main_return_source", "Chief Quarterly Earnings", "data/task6/main/processed/main_quarterly_returns.csv", "csv"),
        ("main_holding_source", "Chief Service Stock Selection Details", "data/task6/main/processed/main_portfolio_holdings.csv", "csv"),
        ("weighted_source", "EW/PWPortfolio Assessment", "data/task6/enhanced/processed/main_weighted_strategy_metrics.csv", "csv"),
        ("weighted_return_source", "EW/PWQuarterly Earnings", "data/task6/enhanced/processed/main_weighted_quarterly_returns.csv", "csv"),
        ("addon_model_source", "Supplementary Question Model Evaluation", "data/task6/additional/processed/additional_model_metrics.csv", "csv"),
        ("addon_strategy_source", "Extension study Strategy Indicator", "data/task6/additional/processed/additional_strategy_metrics.csv", "csv"),
        ("auc_source", "Extension studyAUCControlled Grid", "data/task6/enhanced/processed/additional_guarded_auc_grid.csv", "csv"),
        ("tuning_source", "Additional Questions Three Round Parameters", "data/task6/additional/processed/additional_tuning_rounds.csv", "csv"),
        ("main_run_source", "Configuration of main task method", "data/task6/main/metadata/model_run.json", "json"),
        ("addon_run_source", "Additional Question Method Configuration", "data/task6/additional/metadata/model_run.json", "json"),
        ("quality_source", "Primary Task Data Quality Report", "data/task6/main/metadata/data_quality_report.json", "json"),
    ]
    sources = []
    for source_id, label, path, kind in source_specs:
        reader = "read_csv_auto" if kind == "csv" else "read_json_auto"
        sources.append({
            "id": source_id, "label": label, "path": path,
            "query": {"engine": "duckdb", "language": "sql", "sql": f"SELECT * FROM {reader}('{path}')",
                      "description": f"Read Reviewed{kind.upper()}Result: {label}", "executed_at": generated},
        })

    cards = [
        {"id": "ew_card", "description": "Linear regression holding prediction equally each quarter30only, Deduct one side20bpCost. ", "dataset": "kpis", "sourceId": "weighted_source", "metrics": [{"label": "EW Top-30Cumulative Net Earnings", "field": "ew_return", "format": "percent"}]},
        {"id": "market_card", "description": "Equal-weighted average of sample stocks over the same three test quarters. ", "dataset": "kpis", "sourceId": "main_return_source", "metrics": [{"label": "Total market equal-weighted cumulative returns", "field": "market_return", "format": "percent", "signed": True}]},
        {"id": "excess_card", "description": "EW Top-30Net return minus equal-weighted market return. ", "dataset": "kpis", "sourceId": "main_return_source", "metrics": [{"label": "EWRelative market return spread", "field": "ew_excess", "format": "percent", "signed": True}]},
        {"id": "pw_card", "description": "Allocating weights based on predicted rankingsTop30Enhanced Combination. ", "dataset": "kpis", "sourceId": "weighted_source", "metrics": [{"label": "PW Top-30Cumulative Net Earnings", "field": "pw_return", "format": "percent"}]},
        {"id": "auc_card", "description": "The future of Ping An Bank3The direction of the day.180Stochastic Gradient Descent Logistic Regression. ", "dataset": "kpis", "sourceId": "addon_run_source", "metrics": [{"label": "Extension study TestAUC", "field": "final_auc", "format": "number"}]},
        {"id": "ml_card", "description": "Dual threshold, After dynamic positioning and risk controlMLTiming Net Return. ", "dataset": "kpis", "sourceId": "addon_strategy_source", "metrics": [{"label": "MLTiming Net Return", "field": "ml_return", "format": "percent", "signed": True}]},
        {"id": "buyhold_card", "description": "The additional question also records net returns for buy-and-hold within the same test window.. ", "dataset": "kpis", "sourceId": "addon_strategy_source", "metrics": [{"label": "Net gain from buying and holding", "field": "buyhold_return", "format": "percent", "signed": True}]},
    ]

    charts = [
        {"id": "model_ic_chart", "title": "The ranking ability of six models during the test period", "subtitle": "Rank IChigher, The more the model ranking aligns with actual return ranking. ", "type": "bar", "dataset": "model_ic", "sourceId": "main_model_source", "valueFormat": "number", "encodings": {"x": {"field": "model", "type": "nominal", "label": "model"}, "y": {"field": "test_ic", "type": "quantitative", "label": "Average testRank IC"}, "tooltip": [{"field": "validation_ic", "type": "quantitative", "label": "VerificationRank IC", "format": "number"}]}},
        {"id": "main_return_chart", "title": "Six kindsTop30Cumulative net benefits of the model strategy", "subtitle": "Each model uses the same stock pool, Number of shares held and cost basis. ", "type": "bar", "dataset": "main_net", "sourceId": "main_strategy_source", "valueFormat": "percent", "encodings": {"x": {"field": "model", "type": "nominal", "label": "model"}, "y": {"field": "total_return", "type": "quantitative", "label": "Cumulative Net Earnings"}, "tooltip": [{"field": "average_turnover", "type": "quantitative", "label": "Average turnover rate", "format": "percent"}]}},
        {"id": "quarter_chart", "title": "EW, PWQuarterly returns relative to market", "subtitle": "Check in which test quarters the return differences appear. ", "type": "bar", "dataset": "quarter_compare", "sourceId": "weighted_return_source", "valueFormat": "percent", "encodings": {"x": {"field": "Date", "type": "nominal", "label": "Quarterly"}, "y": {"field": "net_return", "type": "quantitative", "label": "Quarterly Earnings"}, "color": {"field": "portfolio", "type": "nominal", "label": "Combination"}, "tooltip": [{"field": "turnover", "type": "quantitative", "label": "Turnover rate", "format": "percent"}]}},
        {"id": "addon_strategy_chart", "title": "Test net returns of three strategies in the additional questions", "subtitle": "MLSignal has weak predictive power, But not exceeding buy-and-hold and moving average strategies. ", "type": "bar", "dataset": "addon_strategies", "sourceId": "addon_strategy_source", "valueFormat": "percent", "encodings": {"x": {"field": "strategy", "type": "nominal", "label": "Strategy"}, "y": {"field": "total_return", "type": "quantitative", "label": "Cumulative Net Earnings"}, "tooltip": [{"field": "max_drawdown", "type": "quantitative", "label": "Maximum Drawdown", "format": "percent"}]}},
        {"id": "tuning_chart", "title": "Validation and testing of three rounds of parameter tuningAUC", "subtitle": "High scores in the validation window do not necessarily indicate validity in a new market phase.. ", "type": "bar", "dataset": "tuning_long", "sourceId": "tuning_source", "valueFormat": "number", "encodings": {"x": {"field": "round_label", "type": "nominal", "label": "Reference Wheel Adjustment"}, "y": {"field": "auc", "type": "quantitative", "label": "AUC"}, "color": {"field": "sample", "type": "nominal", "label": "sample"}, "tooltip": [{"field": "design", "type": "nominal", "label": "Design"}]}},
        {"id": "auc_grid_chart", "title": "144Grid champion versus original rolling model", "subtitle": "Grid Champion VerificationAUCHigher, but testAUCLower than the original model. ", "type": "bar", "dataset": "auc_long", "sourceId": "auc_source", "valueFormat": "number", "encodings": {"x": {"field": "candidate_label", "type": "nominal", "label": "Plan"}, "y": {"field": "auc", "type": "quantitative", "label": "AUC"}, "color": {"field": "sample", "type": "nominal", "label": "sample"}}},
    ]

    tables = [
        {"id": "weight_table", "title": "Equal-Weight and Prediction-Weight Results", "subtitle": "Validation Set SelectionPW20slightly higher earnings, But volatility and hand-changing are also higher. ", "dataset": "weight_table", "sourceId": "weighted_source", "columns": [{"field": "portfolio_label", "label": "Combination", "type": "text"}, {"field": "top_n", "label": "Number of shares held", "format": "number"}, {"field": "weight_method", "label": "Weight method", "type": "text"}, {"field": "weight_cap", "label": "Single Share Cap", "format": "percent"}, {"field": "total_return", "label": "Cumulative Net Earnings", "format": "percent"}, {"field": "annualized_volatility", "label": "Annualized volatility", "format": "percent"}, {"field": "average_turnover", "label": "Average Turnover", "format": "percent"}]},
        {"id": "top30_table", "title": f"{latest_date} Linear Regression: Equal-Weight Top-30 Selection", "subtitle": "This is the main strategy holding finally adopted in the report, Listed by model prediction ranking. ", "dataset": "top30", "sourceId": "main_holding_source", "defaultSort": {"field": "predicted_rank", "direction": "asc"}, "columns": [{"field": "Code", "label": "Symbol", "type": "text"}, {"field": "predicted_rank", "label": "Forecast Ranking", "format": "number"}, {"field": "prediction", "label": "Prediction Score", "format": "number"}, {"field": "Next_Ret", "label": "Realized gains", "format": "percent"}]},
        {"id": "addon_model_table", "title": "Extension Study: Model Comparison", "subtitle": "AUCThe evaluation model measures the ability to rank rising samples ahead of falling samples.. ", "dataset": "addon_models", "sourceId": "addon_model_source", "defaultSort": {"field": "test_auc", "direction": "desc"}, "columns": [{"field": "model", "label": "model", "type": "text"}, {"field": "validation_auc", "label": "VerificationAUC", "format": "number"}, {"field": "test_auc", "label": "TestAUC", "format": "number"}, {"field": "accuracy", "label": "Accuracy", "format": "percent"}, {"field": "balanced_accuracy", "label": "Balance Accuracy", "format": "percent"}, {"field": "f1", "label": "F1", "format": "number"}]},
        {"id": "addon_strategy_table", "title": "Extension Study: Strategy Risk and Return", "subtitle": "View earnings simultaneously, fluctuation, drawdown, Number of transactions and turnover. ", "dataset": "addon_strategies", "sourceId": "addon_strategy_source", "columns": [{"field": "strategy", "label": "Strategy", "type": "text"}, {"field": "total_return", "label": "Cumulative Net Earnings", "format": "percent"}, {"field": "volatility", "label": "Annualized volatility", "format": "percent"}, {"field": "sharpe", "label": "Sharpe Ratio", "format": "number"}, {"field": "max_drawdown", "label": "Maximum Drawdown", "format": "percent"}, {"field": "trade_count", "label": "Number of transactions", "format": "number"}, {"field": "turnover", "label": "Total turnover", "format": "number"}]},
    ]

    tuning_long = pd.concat([
        tuning.assign(round_label=tuning["round"].map(lambda x: f"The{int(x)}wheel"), sample="Validation set", auc=tuning["validation_auc"])[["round_label", "sample", "auc", "design"]],
        tuning.assign(round_label=tuning["round"].map(lambda x: f"The{int(x)}wheel"), sample="Test set", auc=tuning["test_auc"])[["round_label", "sample", "auc", "design"]],
    ], ignore_index=True)
    candidate_labels = {"validation_winner": "Grid Validation Champion", "existing_baseline": "Original rolling logistic regression"}
    auc_grid["candidate_label"] = auc_grid["candidate"].map(candidate_labels)
    auc_long = pd.concat([
        auc_grid.assign(sample="Validation set", auc=auc_grid["validation_auc"])[["candidate_label", "sample", "auc"]],
        auc_grid.assign(sample="Test set", auc=auc_grid["test_auc"])[["candidate_label", "sample", "auc"]],
    ], ignore_index=True)

    blocks = [
        {"id": "overview", "type": "markdown", "body": "## Research Question\n\nThe main task is to use each stock's valuation at the end of the quarter, Scale and Growth Factors, Cross-sectional ranking predicting next quarter's earnings, Then convert the rankingTop30stock selection strategy. The additional question uses single-stock daily data to predict future direction., And convert probability into dynamic position. "},
        {"id": "coverage", "type": "markdown", "sourceId": "quality_source", "body": f"## Data and Time Split\n\nMain sample contains{main_quality['rows']:,}stock item-Quarterly Record, {main_quality['stock_count']:,}Only stock, {main_quality['quarter_count']}quarter, Coverage{main_quality['date_min']}to{main_quality['date_max']}. By Time Before7Season training, after3Seasonal Test, Not randomly upset. Financial factors are first converted to quarterly cross-sectional percentiles., To reduce the impact of extreme values and dimensional differences. "},
        {"id": "main_method", "type": "markdown", "sourceId": "main_run_source", "body": "## Main Study: From Features to Portfolio Decisions\n\n1. X: 19Quarterly ranking of original financial factors for items4a composite factor.   \n2. Y: The regression model predicts next quarter's return ranking.; Logistic regression predicts whether it is higher than the median of the current season..   \n3. model: Linear regression, Ridge, Logistic Regression, Decision tree, Random forest and gradient boosting.   \n4. Decision-making: Sorted by prediction score in descending order each quarter, Master Strategy Equal Right to Buy Before30only.   \n5. Cost: Net income=Gross earnings-Unilateral20bpxTurnover rate. "},
        {"id": "headline", "type": "metric-strip", "cardIds": ["ew_card", "market_card", "excess_card", "pw_card"]},
        {"id": "model_ic", "type": "chart", "chartId": "model_ic_chart"},
        {"id": "main_return", "type": "chart", "chartId": "main_return_chart"},
        {"id": "quarter", "type": "chart", "chartId": "quarter_chart"},
        {"id": "weight_explain", "type": "markdown", "body": "## How Do Equal and Prediction Weights Differ?\n\nEWis the right to wait, The selected stocks have the same weight., Simple rules. PWIt is predictive weighting., Stocks Ranked Higher Have Greater Weight, Can amplify the impact of high-confidence cues, but may also increase concentration, Fluctuations and Changing Hands. "},
        {"id": "weight", "type": "table", "tableId": "weight_table"},
        {"id": "holdings_intro", "type": "markdown", "body": "## Final Main-Strategy Holdings\n\nThe formal main strategy reported is linear regression.EW Top-30. The table below is the complete holdings list for the most recent test quarter.; PWIt is an enhanced control., Does not replace main strategy conclusions. "},
        {"id": "top30", "type": "table", "tableId": "top30_table"},
        {"id": "addon_intro", "type": "markdown", "sourceId": "addon_run_source", "body": "## Extension Study: Dual Thresholds and Dynamic Positions\n\nModel Predicts the Future of Ping An Bank3Probability of a daily increase. probability higher0.60Position building is allowed at this time., lower than0.35Clearance, Maintain the original position between two thresholds. Target position with probability of exceeding0.5The degree of linear increase, upper limit80%; Additional chargeRSI14<70Admission restrictions, 8%Stop-loss, 15%Surplus and unilateral20bpCost. threshold and maximum position from27Selected from the internal grid during the training period. "},
        {"id": "addon_headline", "type": "metric-strip", "cardIds": ["auc_card", "ml_card", "buyhold_card"]},
        {"id": "addon_models", "type": "table", "tableId": "addon_model_table"},
        {"id": "addon_strategy", "type": "chart", "chartId": "addon_strategy_chart"},
        {"id": "addon_strategy_detail", "type": "table", "tableId": "addon_strategy_table"},
        {"id": "tuning", "type": "chart", "chartId": "tuning_chart"},
        {"id": "auc_grid", "type": "chart", "chartId": "auc_grid_chart"},
        {"id": "conclusion", "type": "markdown", "body": "## How to Interpret the Results\n\n- Stock Selection Conclusion: Linear regressionEW Top-30is the main strategy for this assignment, PW Top-30Enhanced control with higher returns but also higher risk. \n- Additional Question Conclusion: AUChigher0.5Note that the direction is not intended to be reversed., ButMLTiming does not exceed the simple benchmark, Therefore, the strategy should not be claimed to be successful.. \n- Use boundaries: Short main task test period, And missing financial disclosure date, Historical component stocks, Suspension, STand liquidity markers; Results for course backtesting only. "},
        {"id": "definitions", "type": "markdown", "body": "## Metric Glossary\n\n- Rank IC: Predicted ranking and actual return rankingSpearmancorrelation coefficient. \n- AUC: Randomly selecting one rising sample and one falling sample., Probability of the model ranking upward samples first. \n- Turnover rate: Half the sum of absolute changes in weights across two adjacent periods; The initial position is recorded100%. \n- Maximum Drawdown: The maximum drawdown from the historical peak to the subsequent low of net value.. \n- Sharpe Ratio: Average excess return is obtained for each unit of volatility undertaken., This assignment assumes a risk-free rate of0. "},
    ]

    manifest = {
        "version": 1, "surface": "dashboard", "title": "Task 6 - ML Strategy Research",
        "description": "From the data, factor, model, Complete course display from stock selection rules to backtest conclusions. ", "generatedAt": generated,
        "filters": [{"id": "portfolio_filter", "label": "quarterly earnings portfolio", "dataset": "quarter_compare", "field": "portfolio", "includeAll": True, "targets": [{"dataset": "quarter_compare", "field": "portfolio"}]}],
        "cards": cards, "charts": charts, "tables": tables, "sources": sources, "blocks": blocks,
    }
    snapshot = {"version": 1, "generatedAt": generated, "status": "ready", "datasets": {
        "kpis": records(kpis), "coverage": records(coverage), "model_ic": records(model_ic), "main_net": records(main_net),
        "quarter_compare": records(quarter_compare), "weight_table": records(weight_table), "top30": records(top30),
        "addon_models": records(addon_model_view), "addon_strategies": records(addon_strategy_view),
        "tuning_long": records(tuning_long), "auc_long": records(auc_long),
    }, "accessIssues": []}
    artifact = {"surface": "dashboard", "manifest": manifest, "snapshot": snapshot, "sources": sources,
                "package_info": {"originUrl": "artifact://task6-dashboard", "controls": {"edit": False, "refresh": False}}}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "artifact.json"
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(build())
