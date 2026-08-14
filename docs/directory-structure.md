# 项目目录结构与文件生命周期

## 一、总体原则

`Task1`至`Task8`保留在项目根目录，用于集中展示课程成果，并保持GitHub Pages访问路径稳定。目录调整不改变这些路径，重点是让任务说明、可复现代码、数据、模型、图表、Dashboard和最终报告各自承担清楚的职责。

文件按用途分为四类：`TaskN/`保存单项任务说明、Dashboard及其专属代码；`data/`保存原始数据、处理数据和结构化结果；`artifacts/`保存图表与模型；`reports/`集中保存八份最终PDF。

## 二、标准结构

```text
量化交易/
├── Task1/ ... Task8/           # 任务说明、Dashboard、脚本与专属输入
├── data/
│   ├── csv/                    # 早期任务共享行情
│   ├── task5/                  # 机器学习数据、预测与评价结果
│   ├── task6/                  # 选股和择时数据、回测与验证结果
│   └── task7/                  # 影子组合、Dashboard数据与更新记录
├── artifacts/
│   ├── charts/task1...task8/   # 报告和分析使用的图表
│   └── models/task5...task6/   # 保存的机器学习模型
├── reports/                    # Task1至Task8最终PDF
├── docs/                       # 目录等项目说明
├── src/                        # 跨任务共享模块
├── .github/                    # GitHub Actions工作流
├── index.html                  # GitHub Pages总入口
└── README.md
```

这个结构保留了各Task原有的访问方式，同时把跨任务共用的数据和成果移到固定位置。项目主页负责总览，各Task README解释方法和发现，Dashboard负责交互展示，`reports/`提供完整报告。

## 三、每个Task的结构

```text
TaskN/
├── README.md                   # 任务目标、方法、结果、边界和复现方式
├── dashboard/
│   ├── index.html              # 该任务的主要交互页面
│   └── tools/                  # 可选的独立分析工具
├── scripts/                    # 数据、分析、策略、验证与页面构建代码
├── inputs/                     # 任务专属且允许提交的冻结输入
└── output/                     # 必须随任务保留的结构化输出；无需要时省略
```

不同任务不必机械复制全部目录。TASK1至TASK4以行情、指标和策略可视化为主；TASK5和TASK6还会在项目级`data/`与`artifacts/models/`保存模型结果；TASK7包含平台回测摘要、影子跟踪和自动更新页面；TASK8主要指向综合报告与跨任务图表。

Dashboard统一从`dashboard/index.html`打开。附加工具放在`dashboard/tools/`，避免同一任务根目录出现多个含义不清的HTML文件。任务报告统一链接到`reports/TaskN_Report.pdf`，不在Task目录保存内容相同的重复副本。

## 四、数据与分析产物

`data/taskN/`根据需要使用`raw/`、`interim/`、`processed/`、`results/`和`metadata/`：

- `raw/`保存首次取得的原始输入，除必要修正外不直接覆盖；
- `interim/`保存清洗、匹配或特征处理中间结果；
- `processed/`保存模型和回测可直接读取的数据；
- `results/`保存预测、评价指标、持仓和策略收益；
- `metadata/`记录日期范围、样本行数、参数、文件哈希与验证状态。

图表统一放入`artifacts/charts/taskN/`，模型统一放入`artifacts/models/taskN/`。同一估计器避免同时保存内容等价的`.pkl`与`.joblib`；需要完整保存预处理、特征名称、目标定义和参数时，使用模型包并配套`manifest.json`，使读取者能够确认输入字段和适用范围。

CSV和JSON优先保存可复核的数值结果，HTML只承担展示。Dashboard中的关键指标应能追溯到结构化文件，页面更新不能单独改写收益、样本区间或模型评价值。

## 五、报告与平台数据

八份最终PDF使用`reports/TaskN_Report.pdf`的统一命名。Task README和项目主页直接链接这一位置，减少副本不一致和失效链接。PDF保留最终提交版的章节、图表、技术细节和结论。

JoinQuant平台订单、成交、持仓和净值与公开行情影子跟踪属于不同数据层级。平台导出记录策略研究所需的日期、代码、订单、成交、持仓、资产和日志字段，Dashboard不包含账号连接信息。

## 六、迁移与新任务规则

已完成Task的页面路径尽量保持不变。目录迁移时同步更新路径常量、Dashboard访问路径、README、结构化数据清单和验证脚本，并至少完成一次相关任务的端到端复现。

新增任务时先确定数据、代码和输出分别属于Task专属目录还是项目共享目录。图表进入`artifacts/charts/`，模型进入`artifacts/models/`，最终报告进入`reports/`。任务输入应与复现目标直接相关，平台数据继续沿用TASK7的数据层级定义。
