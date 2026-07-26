# 项目目录结构与文件生命周期

## 一、总体原则

`Task1`至`Task8`保留在项目根目录，作为课程提交和GitHub Pages的稳定入口。目录重构不改变这些公开路径，主要解决数据、分析产物、正式提交件和临时构建文件混放的问题。

文件按生命周期分为四类。`data/`保存原始数据、处理后数据和元数据；`artifacts/`保存能够由代码重新生成的图表和模型；`output/submissions/`集中保存正式PDF镜像；`build/`保存渲染页面、LaTeX日志、旧草稿和QA中间文件，整个目录不进入Git。

## 二、标准结构

```text
量化交易/
├── Task1/ ... Task8/
├── data/
│   ├── csv/                    # 早期任务共享行情，后续可迁移至shared/
│   ├── task5/
│   └── task6/
├── artifacts/
│   ├── charts/task1...task8/
│   └── models/task5...task6/
├── output/submissions/
├── build/
├── docs/
├── src/
├── index.html
└── README.md
```

## 三、每个Task的结构

```text
TaskN/
├── README.md
├── spec.md
├── 可编辑报告母版.docx或Rebecca+TaskN.ipynb
├── 正式提交版PDF
├── dashboard/
│   ├── index.html
│   └── tools/                  # 可选的独立小工具
├── scripts/
├── inputs/                         # 仅放任务自带或冻结的输入
├── references/                     # 课程截图、文献和方法参考
└── reporting/templates/            # 可选的报告模板
```

`README.md`是读者入口，`spec.md`记录冻结的研究口径，正式报告与PDF直接位于Task根目录。Dashboard的统一入口是`dashboard/index.html`，附加工具放在`dashboard/tools/`，避免根目录同时出现多个不明确的HTML入口。

## 四、数据与分析产物

`data/taskN/`内部优先使用`raw/`、`interim/`、`processed/`和`metadata/`四个阶段。原始数据只做必要的版本冻结，不直接覆盖；处理数据与模型结果由脚本生成；`metadata/`记录数据日期、行数、参数、环境和文件哈希。

图表不再放入`data/`，统一使用`artifacts/charts/taskN/`。保存模型使用`artifacts/models/taskN/`，同一估计器避免同时保存内容等价的`.pkl`与`.joblib`。需要保存特征名称、目标定义和策略参数时，可以使用完整`.pkl`模型包并配套`manifest.json`。

## 五、正式提交与临时构建

每个Task的正式PDF以任务根目录中的提交文件为主版，文件名遵循当次提交要求；`output/submissions/Rebecca+TaskN.pdf`保存统一命名的集中镜像。交付前需比较两份PDF的SHA-256哈希，确保内容完全一致。

`build/`可以随时由脚本重新生成，其中包括PDF逐页PNG、接触表、XeLaTeX中间文件、旧草稿和已完成的临时审计。不在README或Notebook中引用`build/`下的文件，避免清理构建目录后破坏正式交付。

## 六、迁移与新任务规则

已完成Task的公开入口路径尽量保持不变。目录迁移必须同步更新路径常量、Notebook图片链接、Dashboard入口、README、spec和验证脚本，并至少完成一次关键任务的端到端复现。

新Task从一开始就按本文结构创建，不再把图表放入`data/`，不再把QA渲染页放入Task目录，也不为Dashboard主页使用任务特有文件名。
