# TASK8 成果展示：专业学习报告

TASK8综合TASK1至TASK7的学习与实践，形成量化交易策略和机器学习应用的期末专业报告。本任务只提交报告，不制作策略路演。

## 正式文件

- [`reports/Task8_Report.pdf`](../reports/Task8_Report.pdf)：22页综合报告，覆盖TASK1至TASK7的主要结果、风险边界和学习总结。
- `artifacts/charts/task8/`：报告引用的跨任务对比图，包括任务方法图谱、策略风险收益比较、机器学习结果比较和部署证据层级。

## 目录说明

```text
Task8/
└── README.md                   # 报告范围与复核说明

reports/
└── Task8_Report.pdf            # 最终报告

artifacts/charts/task8/
├── task_method_map.png         # TASK1至TASK7的方法与产出
├── strategy_risk_return.png    # 策略风险收益比较
├── ml_result_comparison.png    # 机器学习结果比较
└── deployment_evidence.png     # 部署证据层级
```

报告按照数据基础、技术指标、规则策略、机器学习和平台部署的顺序串联前七项任务。图表来源、指标定义和策略参数均可回到相应Task的README、结构化结果和分析脚本核对。

## 重新生成

TASK8本身汇总已经冻结的跨任务结果。若上游数据或模型发生变化，应先运行对应Task的分析与验证脚本，再检查`artifacts/charts/task8/`中的比较图是否仍与结构化结果一致。报告中的历史数值不会随Dashboard自动更新，持续运行结果以TASK7 Dashboard为准。
