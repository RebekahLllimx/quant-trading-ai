# TASK8 成果展示：专业学习报告

TASK8综合TASK1至TASK7的学习与实践，形成量化交易策略和机器学习应用的期末专业报告。本任务只提交报告，不制作策略路演。

## 正式文件

- `从数据到执行_量化交易策略与机器学习应用综合实践报告.docx`：可编辑报告母版
- `李沐晓+TASK8.pdf`：正式提交版PDF
- `spec.md`：研究范围、证据口径、写作结构和格式要求

正式PDF在项目级`output/submissions/Rebecca+Task8.pdf`保留内容一致的集中镜像。

## 目录说明

```text
Task8/
├── README.md
├── spec.md
├── 从数据到执行_量化交易策略与机器学习应用综合实践报告.docx
├── 李沐晓+TASK8.pdf
├── references/
│   ├── course/                 # TASK8课程PPT截图
│   └── style/                  # 前期报告风格复用约定
└── scripts/                    # 图表和报告生成脚本
```

报告使用的可再生成图表位于`artifacts/charts/task8/`。旧稿、逐页渲染、接触表和QA记录统一归档到被Git忽略的`build/task8/`，不作为正式提交内容。

## 重新生成

```bash
python Task8/scripts/build_figures.py
python Task8/scripts/generate_report.py
```

重新生成后需按照`docs/report-writing-guidelines.md`和`spec.md`核对摘要、目录、图表编号、字体、分页和结论口径。
