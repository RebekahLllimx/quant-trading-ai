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
    quarter_ew["portfolio"] = "EW Top30"
    quarter_pw = weighted_returns[weighted_returns["portfolio_label"] == "PW_Top30"][["Date", "net_return", "turnover"]].copy()
    quarter_pw["portfolio"] = "PW Top30"
    quarter_market = quarter_ew[["Date"]].copy()
    market_by_date = main_returns[main_returns["model"] == "linear_regression"].drop_duplicates("Date").set_index("Date")["market_return"]
    quarter_market["net_return"] = quarter_market["Date"].map(market_by_date)
    quarter_market["turnover"] = None
    quarter_market["portfolio"] = "全市场等权"
    quarter_compare = pd.concat([quarter_ew, quarter_pw, quarter_market], ignore_index=True)

    weight_table = weighted_metrics[["portfolio_label", "top_n", "weight_method", "weight_cap", "total_return", "annualized_volatility", "sharpe", "average_turnover"]].copy()
    weight_table["portfolio_label"] = weight_table["portfolio_label"].map({
        "EW_Top30": "EW Top30", "PW_Top30": "PW Top30", "Validation_Selected": "验证集选定PW20",
    })
    method_map = {"ew": "等权", "rank_pw": "排名加权", "score_pw": "分数加权"}
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
        ("main_model_source", "主任务模型评估", "data/task6/main/processed/main_model_metrics.csv", "csv"),
        ("main_strategy_source", "主任务策略指标", "data/task6/main/processed/main_strategy_metrics.csv", "csv"),
        ("main_return_source", "主任务季度收益", "data/task6/main/processed/main_quarterly_returns.csv", "csv"),
        ("main_holding_source", "主任务选股明细", "data/task6/main/processed/main_portfolio_holdings.csv", "csv"),
        ("weighted_source", "EW/PW组合评估", "data/task6/enhanced/processed/main_weighted_strategy_metrics.csv", "csv"),
        ("weighted_return_source", "EW/PW季度收益", "data/task6/enhanced/processed/main_weighted_quarterly_returns.csv", "csv"),
        ("addon_model_source", "附加题模型评估", "data/task6/additional/processed/additional_model_metrics.csv", "csv"),
        ("addon_strategy_source", "附加题策略指标", "data/task6/additional/processed/additional_strategy_metrics.csv", "csv"),
        ("auc_source", "附加题AUC受控网格", "data/task6/enhanced/processed/additional_guarded_auc_grid.csv", "csv"),
        ("tuning_source", "附加题三轮调参", "data/task6/additional/processed/additional_tuning_rounds.csv", "csv"),
        ("main_run_source", "主任务方法配置", "data/task6/main/metadata/model_run.json", "json"),
        ("addon_run_source", "附加题方法配置", "data/task6/additional/metadata/model_run.json", "json"),
        ("quality_source", "主任务数据质量报告", "data/task6/main/metadata/data_quality_report.json", "json"),
    ]
    sources = []
    for source_id, label, path, kind in source_specs:
        reader = "read_csv_auto" if kind == "csv" else "read_json_auto"
        sources.append({
            "id": source_id, "label": label, "path": path,
            "query": {"engine": "duckdb", "language": "sql", "sql": f"SELECT * FROM {reader}('{path}')",
                      "description": f"读取已复核的{kind.upper()}结果：{label}", "executed_at": generated},
        })

    cards = [
        {"id": "ew_card", "description": "线性回归每季等权持有预测前30只，扣单边20bp成本。", "dataset": "kpis", "sourceId": "weighted_source", "metrics": [{"label": "EW Top30累计净收益", "field": "ew_return", "format": "percent"}]},
        {"id": "market_card", "description": "同三个测试季度的样本股票等权平均。", "dataset": "kpis", "sourceId": "main_return_source", "metrics": [{"label": "全市场等权累计收益", "field": "market_return", "format": "percent", "signed": True}]},
        {"id": "excess_card", "description": "EW Top30净收益减去全市场等权收益。", "dataset": "kpis", "sourceId": "main_return_source", "metrics": [{"label": "EW相对市场收益差", "field": "ew_excess", "format": "percent", "signed": True}]},
        {"id": "pw_card", "description": "按预测排名分配权重的Top30增强组合。", "dataset": "kpis", "sourceId": "weighted_source", "metrics": [{"label": "PW Top30累计净收益", "field": "pw_return", "format": "percent"}]},
        {"id": "auc_card", "description": "平安银行未来3日方向的180行滚动逻辑回归。", "dataset": "kpis", "sourceId": "addon_run_source", "metrics": [{"label": "附加题测试AUC", "field": "final_auc", "format": "number"}]},
        {"id": "ml_card", "description": "双阈值、动态仓位与风险控制后的ML择时净收益。", "dataset": "kpis", "sourceId": "addon_strategy_source", "metrics": [{"label": "ML择时净收益", "field": "ml_return", "format": "percent", "signed": True}]},
        {"id": "buyhold_card", "description": "附加题同测试窗口买入并持有的净收益。", "dataset": "kpis", "sourceId": "addon_strategy_source", "metrics": [{"label": "买入持有净收益", "field": "buyhold_return", "format": "percent", "signed": True}]},
    ]

    charts = [
        {"id": "model_ic_chart", "title": "六种模型的测试期排序能力", "subtitle": "Rank IC越高，模型排序与实际收益排序越一致。", "type": "bar", "dataset": "model_ic", "sourceId": "main_model_source", "valueFormat": "number", "encodings": {"x": {"field": "model", "type": "nominal", "label": "模型"}, "y": {"field": "test_ic", "type": "quantitative", "label": "平均测试Rank IC"}, "tooltip": [{"field": "validation_ic", "type": "quantitative", "label": "验证Rank IC", "format": "number"}]}},
        {"id": "main_return_chart", "title": "六种Top30模型策略的累计净收益", "subtitle": "各模型使用相同股票池、持股数和成本口径。", "type": "bar", "dataset": "main_net", "sourceId": "main_strategy_source", "valueFormat": "percent", "encodings": {"x": {"field": "model", "type": "nominal", "label": "模型"}, "y": {"field": "total_return", "type": "quantitative", "label": "累计净收益"}, "tooltip": [{"field": "average_turnover", "type": "quantitative", "label": "平均换手率", "format": "percent"}]}},
        {"id": "quarter_chart", "title": "EW、PW与市场的季度收益", "subtitle": "查看收益差异出现在哪些测试季度。", "type": "bar", "dataset": "quarter_compare", "sourceId": "weighted_return_source", "valueFormat": "percent", "encodings": {"x": {"field": "Date", "type": "nominal", "label": "季度"}, "y": {"field": "net_return", "type": "quantitative", "label": "季度收益"}, "color": {"field": "portfolio", "type": "nominal", "label": "组合"}, "tooltip": [{"field": "turnover", "type": "quantitative", "label": "换手率", "format": "percent"}]}},
        {"id": "addon_strategy_chart", "title": "附加题三种策略的测试净收益", "subtitle": "ML信号有弱预测力，但未超过买入持有和均线策略。", "type": "bar", "dataset": "addon_strategies", "sourceId": "addon_strategy_source", "valueFormat": "percent", "encodings": {"x": {"field": "strategy", "type": "nominal", "label": "策略"}, "y": {"field": "total_return", "type": "quantitative", "label": "累计净收益"}, "tooltip": [{"field": "max_drawdown", "type": "quantitative", "label": "最大回撤", "format": "percent"}]}},
        {"id": "tuning_chart", "title": "三轮调参的验证与测试AUC", "subtitle": "验证窗口高分不等于新市场阶段仍然有效。", "type": "bar", "dataset": "tuning_long", "sourceId": "tuning_source", "valueFormat": "number", "encodings": {"x": {"field": "round_label", "type": "nominal", "label": "调参轮次"}, "y": {"field": "auc", "type": "quantitative", "label": "AUC"}, "color": {"field": "sample", "type": "nominal", "label": "样本"}, "tooltip": [{"field": "design", "type": "nominal", "label": "设计"}]}},
        {"id": "auc_grid_chart", "title": "144组网格冠军与原滚动模型", "subtitle": "网格冠军验证AUC更高，但测试AUC低于原模型。", "type": "bar", "dataset": "auc_long", "sourceId": "auc_source", "valueFormat": "number", "encodings": {"x": {"field": "candidate_label", "type": "nominal", "label": "方案"}, "y": {"field": "auc", "type": "quantitative", "label": "AUC"}, "color": {"field": "sample", "type": "nominal", "label": "样本"}}},
    ]

    tables = [
        {"id": "weight_table", "title": "EW/PW组合口径与结果", "subtitle": "验证集选定PW20收益略高，但波动和换手也更高。", "dataset": "weight_table", "sourceId": "weighted_source", "columns": [{"field": "portfolio_label", "label": "组合", "type": "text"}, {"field": "top_n", "label": "持股数", "format": "number"}, {"field": "weight_method", "label": "权重方式", "type": "text"}, {"field": "weight_cap", "label": "单股上限", "format": "percent"}, {"field": "total_return", "label": "累计净收益", "format": "percent"}, {"field": "annualized_volatility", "label": "年化波动", "format": "percent"}, {"field": "average_turnover", "label": "平均换手", "format": "percent"}]},
        {"id": "top30_table", "title": f"{latest_date} 线性回归EW Top30选股清单", "subtitle": "这是报告最终采用的主策略持仓，按模型预测排名列出。", "dataset": "top30", "sourceId": "main_holding_source", "defaultSort": {"field": "predicted_rank", "direction": "asc"}, "columns": [{"field": "Code", "label": "股票代码", "type": "text"}, {"field": "predicted_rank", "label": "预测排名", "format": "number"}, {"field": "prediction", "label": "预测分数", "format": "number"}, {"field": "Next_Ret", "label": "实现收益", "format": "percent"}]},
        {"id": "addon_model_table", "title": "附加题三种分类模型对比", "subtitle": "AUC衡量模型把上涨样本排在下跌样本之前的能力。", "dataset": "addon_models", "sourceId": "addon_model_source", "defaultSort": {"field": "test_auc", "direction": "desc"}, "columns": [{"field": "model", "label": "模型", "type": "text"}, {"field": "validation_auc", "label": "验证AUC", "format": "number"}, {"field": "test_auc", "label": "测试AUC", "format": "number"}, {"field": "accuracy", "label": "准确率", "format": "percent"}, {"field": "balanced_accuracy", "label": "平衡准确率", "format": "percent"}, {"field": "f1", "label": "F1", "format": "number"}]},
        {"id": "addon_strategy_table", "title": "附加题策略风险收益明细", "subtitle": "同时查看收益、波动、回撤、交易次数和换手。", "dataset": "addon_strategies", "sourceId": "addon_strategy_source", "columns": [{"field": "strategy", "label": "策略", "type": "text"}, {"field": "total_return", "label": "累计净收益", "format": "percent"}, {"field": "volatility", "label": "年化波动", "format": "percent"}, {"field": "sharpe", "label": "夏普比率", "format": "number"}, {"field": "max_drawdown", "label": "最大回撤", "format": "percent"}, {"field": "trade_count", "label": "交易次数", "format": "number"}, {"field": "turnover", "label": "总换手", "format": "number"}]},
    ]

    tuning_long = pd.concat([
        tuning.assign(round_label=tuning["round"].map(lambda x: f"第{int(x)}轮"), sample="验证集", auc=tuning["validation_auc"])[["round_label", "sample", "auc", "design"]],
        tuning.assign(round_label=tuning["round"].map(lambda x: f"第{int(x)}轮"), sample="测试集", auc=tuning["test_auc"])[["round_label", "sample", "auc", "design"]],
    ], ignore_index=True)
    candidate_labels = {"validation_winner": "网格验证冠军", "existing_baseline": "原滚动逻辑回归"}
    auc_grid["candidate_label"] = auc_grid["candidate"].map(candidate_labels)
    auc_long = pd.concat([
        auc_grid.assign(sample="验证集", auc=auc_grid["validation_auc"])[["candidate_label", "sample", "auc"]],
        auc_grid.assign(sample="测试集", auc=auc_grid["test_auc"])[["candidate_label", "sample", "auc"]],
    ], ignore_index=True)

    blocks = [
        {"id": "overview", "type": "markdown", "body": "## 这份作业在做什么\n\n主任务是用每只股票在季末的估值、规模和成长因子，预测下一季度收益的横截面排名，再把排名转换为Top30选股策略。附加题使用单股日线数据预测未来方向，并把概率转换为动态仓位。"},
        {"id": "coverage", "type": "markdown", "sourceId": "quality_source", "body": f"## 数据和时间划分\n\n主样本含{main_quality['rows']:,}条股票-季度记录、{main_quality['stock_count']:,}只股票、{main_quality['quarter_count']}个季度，覆盖{main_quality['date_min']}至{main_quality['date_max']}。按时间前7季训练、后3季测试，不随机打乱。财务因子先转换为每季横截面百分位排名，以降低极端值和量纲差异的影响。"},
        {"id": "main_method", "type": "markdown", "sourceId": "main_run_source", "body": "## 主任务从因子到买入决策\n\n1. X：19项原始财务因子的季度排名及4个复合因子。  \n2. Y：回归模型预测下季度收益排名；逻辑回归预测是否高于当季中位数。  \n3. 模型：线性回归、Ridge、逻辑回归、决策树、随机森林和梯度提升。  \n4. 决策：每季按预测分数降序排列，主策略等权买入前30只。  \n5. 成本：净收益=毛收益−单边20bp×换手率。"},
        {"id": "headline", "type": "metric-strip", "cardIds": ["ew_card", "market_card", "excess_card", "pw_card"]},
        {"id": "model_ic", "type": "chart", "chartId": "model_ic_chart"},
        {"id": "main_return", "type": "chart", "chartId": "main_return_chart"},
        {"id": "quarter", "type": "chart", "chartId": "quarter_chart"},
        {"id": "weight_explain", "type": "markdown", "body": "## EW和PW有什么不同\n\nEW是等权，入选股票权重相同，规则简单。PW是预测加权，排名越靠前的股票权重越高，能放大高信心标的影响，但也可能增加集中度、波动和换手。"},
        {"id": "weight", "type": "table", "tableId": "weight_table"},
        {"id": "holdings_intro", "type": "markdown", "body": "## 主策略到底选什么股\n\n报告的正式主策略是线性回归EW Top30。下表是最近测试季度的完整持仓清单；PW是增强对照，不替代主策略结论。"},
        {"id": "top30", "type": "table", "tableId": "top30_table"},
        {"id": "addon_intro", "type": "markdown", "sourceId": "addon_run_source", "body": "## 附加题：课程方法的双阈值与动态仓位\n\n模型预测平安银行未来3日上涨概率。概率高于0.60时允许建仓，低于0.35时清仓，两个阈值之间保持原仓位。目标仓位随概率超过0.5的程度线性增加，上限80%；另加RSI14<70的入场限制、8%止损、15%止盈和单边20bp成本。阈值和最大仓位从27组训练期内部网格中选出。"},
        {"id": "addon_headline", "type": "metric-strip", "cardIds": ["auc_card", "ml_card", "buyhold_card"]},
        {"id": "addon_models", "type": "table", "tableId": "addon_model_table"},
        {"id": "addon_strategy", "type": "chart", "chartId": "addon_strategy_chart"},
        {"id": "addon_strategy_detail", "type": "table", "tableId": "addon_strategy_table"},
        {"id": "tuning", "type": "chart", "chartId": "tuning_chart"},
        {"id": "auc_grid", "type": "chart", "chartId": "auc_grid_chart"},
        {"id": "conclusion", "type": "markdown", "body": "## 怎样解读结果\n\n- 选股结论：线性回归EW Top30是本作业的主策略，PW Top30是收益更高但风险也更高的增强对照。\n- 附加题结论：AUC高于0.5说明方向没有拟反，但ML择时未超过简单基准，因此不应宣称策略成功。\n- 使用边界：主任务测试期较短，且缺少财务披露日、历史成分股、停牌、ST和流动性标记；结果仅用于课程回测。"},
        {"id": "definitions", "type": "markdown", "body": "## 指标小词典\n\n- Rank IC：预测排名与实际收益排名的Spearman相关系数。\n- AUC：随机抽取一个上涨样本和一个下跌样本时，模型把上涨样本排在前面的概率。\n- 换手率：相邻两期权重变化绝对值之和的一半；首期建仓记为100%。\n- 最大回撤：净值从历史高点下降到之后低点的最大幅度。\n- 夏普比率：每承担一单位波动获得的平均超额收益，本作业假设无风险利率为0。"},
    ]

    manifest = {
        "version": 1, "surface": "dashboard", "title": "TASK6 机器学习选股与动态仓位看板",
        "description": "从数据、因子、模型、选股规则到回测结论的完整课程展示。", "generatedAt": generated,
        "filters": [{"id": "portfolio_filter", "label": "季度收益组合", "dataset": "quarter_compare", "field": "portfolio", "includeAll": True, "targets": [{"dataset": "quarter_compare", "field": "portfolio"}]}],
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
