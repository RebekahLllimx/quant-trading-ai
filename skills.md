# Skills & SOP — AI量化交易课程项目

> 适用于 Task 1 到 Task 8，每次新建任务时按此流程执行。

---

## 项目结构

```
量化交易/
├── index.html                  ← Hub 导航页（卡片式入口）
├── README.md                   ← 项目说明
├── skills.md                   ← 本文件
├── .gitignore                  ← 隐藏 config.py、真实姓名、临时文件
├── data/                       ← 共享数据（所有 Task 共用）
│   ├── csv/                    ←   股票 CSV + 汇总文件
│   └── charts/
│       ├── task1/              ←   Task1 图表
│       └── task2/              ←   Task2 图表
├── src/                        ← 共享模块（所有 Task 复用）
│   ├── __init__.py
│   ├── indicators.py           ←   8 个技术指标计算函数
│   └── report_utils.py         ←   python-docx 格式化辅助
├── TaskN/                      ← 每个 Task 独立目录
│   ├── spec.md                 ←   设计文档（可选但推荐）
│   ├── Rebecca+TaskN.docx      ←   最终报告
│   ├── dashboard/
│   │   └── index.html          ←   自包含看板
│   └── scripts/
│       ├── update_data.py      ←   数据获取/更新
│       ├── <core_logic>.py     ←   核心逻辑（指标/策略/模型）
│       ├── plot_*.py           ←   mplfinance 图表生成
│       ├── build_dashboard.py  ←   看板构建（CSV→JSON→HTML）
│       └── generate_report.py  ←   报告生成（→ .docx）
```

---

## 每个 Task 的标准 6 步流程

### Step 1: spec.md（设计文档）

- 阅读任务要求，查阅参考资料
- 写设计文档：术语定义、公式推导、参数选择依据、架构决策
- 用精确的非比喻语言，定义术语后再使用
- 记录关键决策：为什么不选方案 A 而选方案 B

### Step 2: data（数据）

- 数据源：AKShare（主力，免费无限制）+ Tushare Pro（补充，港股 1次/小时限流）
- 统一使用前复权（qfq）
- 输出到 `data/csv/{code}_{name}_{market}_daily.csv`
- 脚本命名：`TaskN/scripts/update_data.py`

### Step 3: core（核心逻辑）

- 实现任务要求的计算/策略/模型逻辑
- 纯函数设计：接收 DataFrame/数组，返回计算结果
- 可复用部分放到 `src/` 目录
- 用 `if __name__ == "__main__"` 块做单元测试

### Step 4: charts（静态图表）

- 使用 mplfinance 绘制专业金融图表
- 配色：中国红涨(#ef5350 或 red)、绿跌(#26a69a 或 green)
- 中文字体：`Heiti SC` / `PingFang SC` 优先
- 图表输出到 `data/charts/taskN/`
- 脚本命名：`TaskN/scripts/plot_*.py`

### Step 5: dashboard（交互看板）

- 自包含 HTML：CSV 数据序列化为 JSON 嵌入页面，无需后端
- ECharts 5.5+ 渲染
- 浅色主题：`--bg:#f5f6fa` `--card:#fff` `--accent:#0984e3`
- 布局：顶部深色渐变栏 + 左侧 300px 边栏 + 右侧图表区
- 侧边栏：标的切换、参数调节、指标显隐
- 每张图有标题：`{标的名称} ({代码}) — {指标类型} (参数)`
- 图表高度：主图 ≥550px，子图 ≥350px，`flex-shrink:0` 防止压缩
- 脚本命名：`TaskN/scripts/build_dashboard.py`
- 输出到：`TaskN/dashboard/index.html`

### Step 6: report（报告）

- 格式：宋体五号(10.5pt)，1.5 倍行距，0 段间距，两端对齐
- 无封面页，直接以任务标题开头
- 标题层次：14pt Bold（章标题）/ 12pt Bold（节标题）— 使用 Normal 段落 + 不同字号，不用 Word Heading 样式
- 代码块：Courier New 9pt
- 图题：9pt Bold 居中
- 表格：Table Grid 样式，9pt，灰色表头(#D9D9D9)
- 文件名：`Rebecca+TaskN.docx`
- 文本去 AI 化检查：
  - 避免：值得注意的是、展示了、可以看出、这一对比验证了、综上所述
  - 避免：英文 em dash（—），中文破折号（——）适度使用
  - 避免：AI 词汇（crucial, pivotal, landscape, showcase, tapestry）
  - 避免：三段式排比、空洞的正面总结
- 从 `src.report_utils` 导入格式化函数
- 脚本命名：`TaskN/scripts/generate_report.py`

---

## 技术选型速查

| 需求 | 选择 | 原因 |
|------|------|------|
| 股票数据 | AKShare + Tushare | 双源互补，qfq 复权 |
| 金融绘图 | mplfinance | 专业 K 线图，多面板，中文支持 |
| 交互看板 | ECharts 5.x 自包含 HTML | 无后端部署，GitHub Pages 兼容 |
| 报告 | python-docx + XML 操作 | CJK 字体控制，精确格式 |
| 数据格式 | CSV (utf-8-sig) | 通用，Excel 兼容 |

---

## 关键注意事项

1. **数据目录**：所有 CSV 和图表放在根级 `data/` 而非 `TaskN/data/`，避免重复
2. **路径引用**：Python 脚本中用相对路径（`os.path.join(BASE_DIR, '..', '..', 'data', 'csv')`）
3. **安全**：`config.py` 已在 `.gitignore` 中，含 API token 绝不提交
4. **文件名**：报告和提交文件用 `Rebecca+TaskN` 格式，不暴露真实中文姓名
5. **GitHub Pages**：`dashboard/index.html` 的链接用明确 `index.html` 文件名（兼容本地 `file://` 协议）
6. **Wilder 平滑**：α=1/N（非 EMA 的 α=2/(N+1)），RSI/ATR/ADX 三个指标必须使用
7. **共享模块**：`src/indicators.py` 和 `src/report_utils.py` 跨 Task 复用，不要在每个 Task 里复制粘贴
