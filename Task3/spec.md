# Task3 Spec: 双均线交叉策略回测系统

## 一、数据预处理

### 1.1 数据来源
- 使用 `data/csv/` 下已有 CSV 文件（AKShare 前复权 qfq 日线数据）
- 覆盖 10 只标的：5 只 A 股 + 5 只港股

### 1.2 复权处理
- 所有数据使用**前复权（qfq）**，确保历史价格可比性
- 报告明确说明：不复权会导致分红除权产生虚假跳空缺口，使均线交叉信号失真、收益率计算错误

### 1.3 数据诊断
- 在回测前必须对每只股票进行数据质量检查：
  - 缺失值检查（Open/High/Low/Close/Volume）
  - 日期连续性检查
  - 描述性统计（均值、标准差、偏度、峰度）
  - 日收益率正态性检验（Jarque-Bera）

---

## 二、双均线策略定义

### 2.1 均线计算
- **SMA（简单移动平均）**: SMA_N(t) = mean(Close[t-N+1 : t])
- 短均线周期：默认 5 日
- 长均线周期：默认 15 日
- 均线计算基于**前复权收盘价**

### 2.2 交易信号（避免未来函数）

核心原则：**信号判断使用 T-1 日数据，交易执行在 T 日收盘价。**

```
金叉（买入信号）:
  SMA_short[T-1] > SMA_long[T-1]  AND  SMA_short[T-2] <= SMA_long[T-2]
  → 以 T 日收盘价买入（全仓）

死叉（卖出信号）:
  SMA_short[T-1] < SMA_long[T-1]  AND  SMA_short[T-2] >= SMA_long[T-2]
  → 以 T 日收盘价卖出（全部平仓）
```

说明：
- T-2 和 T-1 的均线值在 T 日开盘前已可计算（它们只依赖 ≤ T-1 的收盘价）
- 因此不存在"未来函数"问题
- 首次信号出现前（前 max(long_period, short_period)+1 天），持有现金

### 2.3 仓位管理
- 初始资金：默认 1,000,000 元（可在看板中调节）
- 全仓进出：买入信号 → 全部资金买入；卖出信号 → 全部卖出
- 不允许做空（只有持仓和空仓两种状态）

### 2.4 交易成本
- 手续费：0.03%（万三），买入/卖出各收一次
- 滑点：0.01%，买入时成交价 = Close × (1 + 0.01%)，卖出时 = Close × (1 - 0.01%)
- 总单边成本 ≈ 0.04%，双边 ≈ 0.08%

### 2.5 风控参数（报告讨论层面）
- 最大回撤阈值：如超过 20% 暂停交易（在报告的风控章节讨论，看板中可选实现）
- 单笔止损：报告层面讨论止损线的意义
- 实际看板中先实现基础版本（无止损），保留扩展空间

---

## 三、回测引擎算法

### 3.1 输入
- 股票日线数据（Date, Open, High, Low, Close, Volume 等）
- 短均线周期 `short_period`
- 长均线周期 `long_period`
- 起始日期 `start_date`
- 结束日期 `end_date`
- 初始资金 `initial_capital`
- 手续费率 `fee_rate`（默认 0.0003）
- 滑点率 `slippage`（默认 0.0001）

### 3.2 输出
- 交易明细列表（每笔交易的买入日/价、卖出日/价、持有天数、收益率）
- 每日持仓状态和资产净值
- 策略评估指标

### 3.3 算法伪码

```
function backtest(df, short_period, long_period, start_date, end_date,
                  initial_capital, fee_rate, slippage):

    // 1. 截取时间范围
    df = df[start_date <= Date <= end_date]

    // 2. 计算均线 (SMA)
    df['MA_short'] = SMA(df.Close, short_period)
    df['MA_long']  = SMA(df.Close, long_period)

    // 3. 初始化
    cash = initial_capital
    shares = 0
    position = False  // 是否持仓
    trades = []
    equity_curve = []  // 每日权益

    // 4. 遍历（从 max_period+1 开始，确保均线已计算）
    for t in range(max(short_period, long_period) + 1, len(df)):
        // 4a. 计算当日权益
        price_t = df.Close[t]
        equity = cash + shares * price_t
        equity_curve.append({date: df.Date[t], equity: equity, cash: cash, shares: shares})

        // 4b. 信号判断（使用 T-1 和 T-2 均线值）
        ma_s_prev  = df.MA_short[t-1]  // T-1
        ma_l_prev  = df.MA_long[t-1]
        ma_s_prev2 = df.MA_short[t-2]  // T-2
        ma_l_prev2 = df.MA_long[t-2]

        golden_cross = (ma_s_prev > ma_l_prev) and (ma_s_prev2 <= ma_l_prev2)
        death_cross  = (ma_s_prev < ma_l_prev) and (ma_s_prev2 >= ma_l_prev2)

        // 4c. 执行交易（T 日收盘价成交）
        if golden_cross and not position:
            buy_price = price_t * (1 + slippage)
            cost = buy_price * (1 + fee_rate)  // 含手续费
            shares = cash / cost
            cash = 0
            position = True
            trades.append({type: 'BUY', date: df.Date[t], price: buy_price, shares: shares, cash: cash})

        elif death_cross and position:
            sell_price = price_t * (1 - slippage)
            cash = shares * sell_price * (1 - fee_rate)  // 扣除手续费
            shares = 0
            position = False
            // 更新最近一笔交易的卖出信息
            trades.last.sell_date = df.Date[t]
            trades.last.sell_price = sell_price
            trades.last.return_pct = (cash / trades.last.cost - 1) * 100

    // 5. 最后一天如果仍持仓，按收盘价强制平仓
    if position:
        final_price = df.Close[-1] * (1 - slippage)
        cash = shares * final_price * (1 - fee_rate)
        shares = 0
        position = False

    // 6. 计算评估指标
    metrics = calculate_metrics(equity_curve, trades, df, initial_capital)

    // 7. 基准（买入持有）
    buy_hold_equity = calculate_buy_hold(df, initial_capital)

    return {trades, equity_curve, metrics, buy_hold_equity, df_with_ma}
```

---

## 四、评估指标计算

### 4.1 累计回报 (Cumulative Return)
```
total_return = (final_equity - initial_capital) / initial_capital × 100%
```

### 4.2 年化收益率 (Annualized Return)
```
days = (end_date - start_date).days
annual_return = ((final_equity / initial_capital) ^ (252 / days) - 1) × 100%
```
注：252 为年交易日数

### 4.3 最大回撤 (Maximum Drawdown, MDD)
```
peak = equity_curve[0].equity
for each day in equity_curve:
    peak = max(peak, day.equity)
    drawdown = (day.equity - peak) / peak × 100%
    MDD = min(MDD, drawdown)  // MDD 为负值，越小回撤越大
```

### 4.4 夏普比率 (Sharpe Ratio)
```
daily_returns = equity_curve[1:].equity / equity_curve[:-1].equity - 1
excess_daily = daily_returns.mean() - risk_free_rate / 252
daily_std = daily_returns.std()
sharpe = sqrt(252) × excess_daily / daily_std
```
- 无风险利率默认 2%（年化）
- 如果 daily_std = 0（现金全程），夏普 = 0

### 4.5 胜率 (Win Rate)
```
win_rate = count(trades with return > 0) / total_trades × 100%
```

### 4.6 盈亏比 (Profit/Loss Ratio)
```
avg_win = mean(正收益交易的 return_pct)
avg_loss = mean(负收益交易的 abs(return_pct))
profit_loss_ratio = avg_win / avg_loss
```
- 如果没有亏损交易，盈亏比 = ∞（显示 "N/A"）

### 4.7 日均收益率标准差（年化波动率）
```
annual_volatility = daily_returns.std() × sqrt(252) × 100%
```

### 4.8 交易次数
```
total_trades = 完整买卖周期数
```

---

## 五、可视化设计

### 5.1 看板图表（ECharts，HTML 内嵌）

按顺序从上到下排列在主内容区：

| 序号 | 图表名称 | 类型 | 内容 |
|------|---------|------|------|
| 1 | 指标卡片行 | Stat Cards | 累计回报、年化收益、MDD、夏普比率、胜率、盈亏比、交易次数 — 每个卡片一个大数字 + 标签，正收益绿底、负收益红底 |
| 2 | 价格与交易信号图 | Line + Scatter | 收盘价折线(灰色) + MA_short(蓝色) + MA_long(橙色) + 买入箭头▲(红色, 朝上) + 卖出箭头▼(绿色, 朝下) |
| 3 | 资产曲线对比图 | Line (双线) | 策略资产曲线(蓝色) vs 买入持有资产曲线(灰色虚线) — X轴日期，Y轴资产金额 |
| 4 | 回撤曲线图 | Area | 回撤百分比面积图，回撤区间填充浅红色，0%基准线 |

### 5.2 图表交互特性
- Tooltip 联动：所有图表共享同一日期轴，悬停显示当日数据
- DataZoom：底部滑块支持缩放时间范围
- 响应式：窗口 resize 自动适配
- 图表间通过 echarts.connect 联动十字光标

### 5.3 报告图表（matplotlib，静态）

生成以下 PNG 用于 .docx 报告：
1. `600519_策略信号图.png` — 价格+双均线+买卖箭头标记
2. `600519_资产曲线对比.png` — 策略 vs 买入持有
3. `600519_回撤曲线.png` — 回撤面积图
4. `参数敏感性热力图.png` — 不同 MA 组合的累计回报矩阵
5. `多股票对比.png` — 多股票策略收益柱状图

---

## 六、交互式回测看板（HTML）

### 6.1 架构
- 纯前端单文件 HTML（和 Task2 一致）
- Python 脚本 (`prepare_data.py`) 将 CSV 数据序列化为 JSON，嵌入 HTML
- 所有回测计算在浏览器端用 JavaScript 完成
- 无需后端服务器，GitHub Pages 可直接部署

### 6.2 布局（沿用 Task2 风格）
```
┌─────────────────────────────────────────────────────┐
│  Topbar: 📈 双均线策略回测看板 | Task3 · Standalone    │
├──────────────┬──────────────────────────────────────┤
│ 侧边栏(300px)│          主内容区(scrollable)          │
│              │                                      │
│ 📌 标的选择   │  [指标卡片行: 累计回报|年化收益|MDD|    │
│ [下拉菜单]   │   夏普比率|胜率|盈亏比|交易次数]        │
│              │                                      │
│ 📐 策略参数   │  [价格与交易信号图]                    │
│ 短均线周期    │                                      │
│ [滑块+输入框] │  [资产曲线对比图]                      │
│ 长均线周期    │                                      │
│ [滑块+输入框] │  [回撤曲线图]                         │
│              │                                      │
│ 📅 时间范围   │  [交易明细表]                         │
│ 起始 [日期]   │                                      │
│ 结束 [日期]   │                                      │
│              │                                      │
│ 💰 初始资金   │                                      │
│ [数字输入框]  │                                      │
│              │                                      │
│ 📊 交易成本   │                                      │
│ [手续费%]    │                                      │
│ [滑点%]      │                                      │
│              │                                      │
│ [🔄 开始回测] │                                      │
└──────────────┴──────────────────────────────────────┘
```

### 6.3 配色方案（白天浅色主题）
```css
--bg: #f5f6fa;
--card: #fff;
--text: #2d3436;
--muted: #636e72;
--accent: #0984e3;
--up: #d63031;      /* 涨/买入 红色 */
--down: #00b894;    /* 跌/卖出 绿色 */
--border: #dfe6e9;
--shadow: 0 2px 8px rgba(0,0,0,0.06);
```

### 6.4 数据嵌入格式
```javascript
const STOCKS = {
  "600519": {
    code: "600519",
    name: "贵州茅台",
    market: "A股",
    data: [
      ["2025-05-29", 1460.42, 1460.42, 1475.42, 1452.42, 21860],
      // [Date, Open, Close, High, Low, Volume]
      ...
    ]
  },
  // ... 其他 9 只股票
};
```

### 6.5 控件默认值
| 参数 | 默认值 | 范围 |
|------|--------|------|
| 标的 | 600519 贵州茅台 | 下拉选择 |
| 短均线周期 | 5 | 2–60 |
| 长均线周期 | 15 | 5–120 |
| 起始日期 | 数据最早日期 | 日期选择 |
| 结束日期 | 数据最晚日期 | 日期选择 |
| 初始资金 | 1,000,000 | 10,000–100,000,000 |
| 手续费率 | 0.03% | 0–1% |
| 滑点率 | 0.01% | 0–1% |

---

## 七、报告结构

格式：宋体五号（10.5pt），1.5 倍行距，0 段间距，两端对齐（复用 `src/report_utils.py`）

### 章节大纲
- **一、数据诊断与复权处理**（数据复权的重要性说明 + 数据质量检查结果）
- **二、双均线策略原理**（金叉/死叉概念 + OMML 公式 + 避免未来函数的实现方案）
- **三、策略回测与评估指标**（回测框架说明 + 模拟交易规则 + MDD/夏普/累计回报等指标定义）
- **四、策略回测结果分析**（以茅台为主标的，展示信号图、资产曲线、回撤曲线、指标表 + 每张图的解读）
- **五、参数敏感性分析**（多组 MA 周期组合对比 + 参数选择讨论 + 过拟合风险提示）
- **六、多标的对比分析**（多股票策略表现对比 + 策略适用场景讨论）
- **七、交互式回测看板**（网站功能介绍 + 部署方式）
- **八、总结与策略评估**（策略优势/局限 + 适用场景 + 改进方向）

---

## 八、文件结构

```
Task3/
├── spec.md                          ← 本文件
├── scripts/
│   ├── prepare_data.py              ← 将 CSV → JSON，嵌入 HTML
│   ├── plot_strategy.py             ← matplotlib 生成报告图表 (PNG)
│   └── generate_report.py           ← 生成 .docx 报告
├── dashboard/
│   └── index.html                   ← 交互式回测看板（内嵌数据）
└── Rebecca+Task3.docx               ← 最终提交物（待转 PDF）
```

---

## 九、待确认项

1. ~~复权问题~~ → ✅ 已确认为前复权 qfq
2. ~~报告结构~~ → ✅ 对齐 Task2 风格
3. ~~网站布局~~ → ✅ 侧边栏+右侧内容区，白天主题
4. 做空支持？→ ❌ 不做空（仅多头+空仓）
5. 止损实现？→ 报告层面讨论，看板中先不做（保持简单）
6. 输出格式：先生成 .docx，最后转 PDF？
