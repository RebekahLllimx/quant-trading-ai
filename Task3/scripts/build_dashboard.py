#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task3 Phase 2: 构建交互式双均线策略回测看板
读取 data.json，生成自包含的 index.html（嵌入数据 + ECharts + 全部回测逻辑）
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'dashboard', 'data.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'dashboard', 'index.html')

# ─────────────────────────────────────────────
# HTML 模板
# ─────────────────────────────────────────────

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📈 双均线策略回测看板 — Task3</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root {
  --bg: #f5f6fa; --card: #fff; --text: #2d3436; --muted: #636e72;
  --accent: #0984e3; --up: #d63031; --down: #00b894; --border: #dfe6e9;
  --shadow: 0 2px 8px rgba(0,0,0,0.06); --warn: #e17055;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh}
.topbar{background:linear-gradient(135deg,#2d3436 0%,#434a54 100%);color:#fff;
  padding:14px 28px;display:flex;justify-content:space-between;align-items:center}
.topbar h1{font-size:1.3em;font-weight:600}
.topbar .badge{font-size:0.75em;background:var(--accent);padding:4px 10px;border-radius:10px}
.layout{display:flex;height:calc(100vh - 56px)}
.sidebar{width:300px;min-width:300px;background:var(--card);border-right:1px solid var(--border);
  padding:14px;overflow-y:auto;display:flex;flex-direction:column;gap:10px}
.main{flex:1;padding:12px;overflow-y:auto;display:flex;flex-direction:column;gap:10px}
.card{background:var(--card);border-radius:10px;padding:12px 14px;
  box-shadow:var(--shadow);border:1px solid var(--border)}
.card h3{font-size:0.88em;color:var(--accent);margin-bottom:8px;
  padding-bottom:5px;border-bottom:1px solid var(--border)}
label{font-size:0.76em;color:var(--muted);display:block;margin-bottom:2px;font-weight:500}
select,input,button{padding:7px 10px;border:1px solid var(--border);border-radius:6px;
  font-size:0.83em;font-family:inherit}
select:focus,input:focus{outline:2px solid var(--accent)}
select{width:100%;cursor:pointer}
.btn-primary{background:var(--accent);color:#fff;font-weight:600;border:none;cursor:pointer;width:100%}
.btn-primary:hover{background:#0773c5}
.chart-panel{background:var(--card);border-radius:10px;padding:8px;
  box-shadow:var(--shadow);border:1px solid var(--border);flex-shrink:0}
.chart-box{width:100%;height:520px}
.chart-box.half{height:400px}
.param-row{display:flex;align-items:center;justify-content:space-between;gap:4px;
  font-size:0.76em;padding:3px 0}
.param-row span.lbl{color:var(--text);min-width:54px}
.param-row input[type=range]{flex:1;margin:0 3px}
.param-row input[type=number]{width:52px;border:1px solid var(--border);padding:2px 3px;
  border-radius:3px;font-size:0.85em;text-align:center}
.date-row{display:flex;align-items:center;gap:4px;font-size:0.76em;padding:2px 0}
.date-row input[type=date]{flex:1;padding:4px 6px;font-size:0.78em;border:1px solid var(--border);
  border-radius:4px;font-family:inherit}
/* KPI cards */
.kpi-row{display:flex;gap:8px;flex-wrap:wrap}
.kpi-card{flex:1;min-width:100px;background:var(--card);border-radius:10px;padding:12px 10px;
  box-shadow:var(--shadow);border:1px solid var(--border);text-align:center}
.kpi-card .kpi-val{font-size:1.5em;font-weight:700;margin-bottom:2px}
.kpi-card .kpi-lbl{font-size:0.7em;color:var(--muted)}
.kpi-card.pos .kpi-val{color:var(--down)}
.kpi-card.neg .kpi-val{color:var(--up)}
.kpi-card.neutral .kpi-val{color:var(--text)}
/* Trade table */
.trade-table{width:100%;border-collapse:collapse;font-size:0.76em}
.trade-table th{background:#f0f0f0;padding:6px 8px;text-align:center;font-weight:600;
  border-bottom:2px solid var(--border);position:sticky;top:0}
.trade-table td{padding:5px 8px;text-align:center;border-bottom:1px solid var(--border)}
.trade-table tr.win td.ret{color:var(--down)}
.trade-table tr.loss td.ret{color:var(--up)}
.table-wrap{max-height:260px;overflow-y:auto;border:1px solid var(--border);border-radius:6px}
.footer{text-align:center;padding:8px;color:var(--muted);font-size:0.72em;
  border-top:1px solid var(--border);margin-top:4px}
@media(max-width:900px){.layout{flex-direction:column}.sidebar{width:100%;min-width:0}
  .kpi-card{min-width:70px}.kpi-card .kpi-val{font-size:1.1em}}
</style>
</head>
<body>

<div class="topbar">
  <h1>📈 双均线策略回测看板 <span style="font-weight:400;font-size:0.8em;opacity:0.8;">| SMA Crossover · 金叉死叉 · 回测引擎</span></h1>
  <span class="badge">Task3 · Standalone</span>
</div>

<div class="layout">
<div class="sidebar">
  <div class="card">
    <h3>📌 标的选择</h3>
    <label>标的</label>
    <select id="stock-select" onchange="onStockChange()"></select>
    <div id="stock-info" style="font-size:0.72em;color:var(--muted);margin-top:4px;padding:2px 0"></div>
  </div>

  <div class="card">
    <h3>📐 策略参数</h3>
    <div id="params-content">
      <div class="param-row">
        <span class="lbl">短均线周期</span>
        <input type="range" id="ma-short-range" min="2" max="60" value="5"
          oninput="syncRange('ma-short')">
        <input type="number" id="ma-short-num" value="5" min="2" max="60"
          onchange="syncNum('ma-short')">
      </div>
      <div class="param-row">
        <span class="lbl">长均线周期</span>
        <input type="range" id="ma-long-range" min="5" max="120" value="15"
          oninput="syncRange('ma-long')">
        <input type="number" id="ma-long-num" value="15" min="5" max="120"
          onchange="syncNum('ma-long')">
      </div>
    </div>
  </div>

  <div class="card">
    <h3>📅 时间范围</h3>
    <div class="date-row">
      <span style="min-width:36px;color:var(--muted);font-size:0.76em;">起始</span>
      <input type="date" id="date-start" onchange="runAll()">
    </div>
    <div class="date-row" style="margin-top:4px;">
      <span style="min-width:36px;color:var(--muted);font-size:0.76em;">结束</span>
      <input type="date" id="date-end" onchange="runAll()">
    </div>
  </div>

  <div class="card">
    <h3>💰 资金 & 成本</h3>
    <div class="param-row">
      <span class="lbl">初始资金(万)</span>
      <input type="range" id="capital-range" min="1" max="1000" value="100"
        oninput="syncRange('capital')" style="flex:1">
      <input type="number" id="capital-num" value="100" min="1" max="1000"
        onchange="syncNum('capital')" style="width:60px">
    </div>
    <div class="param-row">
      <span class="lbl">手续费率(%)</span>
      <input type="range" id="fee-range" min="0" max="1" value="0.03" step="0.01"
        oninput="syncRange('fee')" style="flex:1">
      <input type="number" id="fee-num" value="0.03" min="0" max="1" step="0.01"
        onchange="syncNum('fee')" style="width:60px">
    </div>
    <div class="param-row">
      <span class="lbl">滑点率(%)</span>
      <input type="range" id="slippage-range" min="0" max="1" value="0.01" step="0.01"
        oninput="syncRange('slippage')" style="flex:1">
      <input type="number" id="slippage-num" value="0.01" min="0" max="1" step="0.01"
        onchange="syncNum('slippage')" style="width:60px">
    </div>
  </div>

  <button class="btn-primary" onclick="runAll()">🔄 开始回测</button>
</div>

<div class="main">
  <!-- KPI 指标卡片 -->
  <div class="kpi-row" id="kpi-row">
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">累计回报</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">年化收益</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">最大回撤(MDD)</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">夏普比率</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">胜率</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">盈亏比</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">交易次数</div></div>
  </div>

  <!-- 图表1: 价格 + 均线 + 交易信号 -->
  <div id="chart-signals" class="chart-box chart-panel"></div>

  <!-- 图表2: 资产曲线对比 -->
  <div id="chart-equity" class="chart-box half chart-panel"></div>

  <!-- 图表3: 回撤曲线 -->
  <div id="chart-drawdown" class="chart-box half chart-panel"></div>

  <!-- 交易明细表 -->
  <div class="card">
    <h3>📋 交易明细</h3>
    <div class="table-wrap" id="trade-table-wrap">
      <table class="trade-table" id="trade-table">
        <thead><tr>
          <th>#</th><th>买入日期</th><th>买入价</th><th>卖出日期</th><th>卖出价</th>
          <th>持有天数</th><th>收益率</th><th>累计收益</th>
        </tr></thead>
        <tbody id="trade-tbody">
          <tr><td colspan="8" style="color:var(--muted);padding:20px;">请选择参数后点击「开始回测」</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
</div>

<div class="footer">Task3 · 双均线策略回测系统 | 数据来源: AKShare 前复权(qfq)日线 | 纯前端计算 · 无后端依赖</div>

<script>
// ═══════════════════════════════════════════════════════════════
// 嵌入数据
// ═══════════════════════════════════════════════════════════════
const STOCKS = __STOCKS_DATA__;

// ═══════════════════════════════════════════════════════════════
// 全局状态
// ═══════════════════════════════════════════════════════════════
let currentCode = '';
let charts = {};
let lastResult = null;

// ═══════════════════════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════════════════════

function calcSMA(arr, period) {
  const result = new Array(arr.length).fill(null);
  if (arr.length < period) return result;
  let sum = 0;
  for (let i = 0; i < period; i++) sum += arr[i];
  result[period - 1] = sum / period;
  for (let i = period; i < arr.length; i++) {
    sum += arr[i] - arr[i - period];
    result[i] = sum / period;
  }
  return result;
}

function parseDate(s) {
  return new Date(s + 'T00:00:00');
}

function fmtDate(d) {
  const dt = new Date(d);
  return dt.getFullYear() + '-' + String(dt.getMonth()+1).padStart(2,'0') + '-' + String(dt.getDate()).padStart(2,'0');
}

function fmtMoney(v) {
  if (Math.abs(v) >= 1e8) return (v/1e8).toFixed(2)+'亿';
  if (Math.abs(v) >= 1e4) return (v/1e4).toFixed(2)+'万';
  return v.toFixed(2);
}

function fmtPct(v) {
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
}

// ═══════════════════════════════════════════════════════════════
// 回测引擎
// ═══════════════════════════════════════════════════════════════

function runBacktest(rawData, shortPeriod, longPeriod, initialCapital, feeRate, slippage) {
  // rawData: [[date, open, close, high, low, volume], ...]
  const n = rawData.length;
  const closes = rawData.map(r => r[2]);

  // 计算均线
  const maShort = calcSMA(closes, shortPeriod);
  const maLong = calcSMA(closes, longPeriod);

  // 回测状态
  let cash = initialCapital;
  let shares = 0;
  let hasPosition = false;
  const trades = [];
  const equityCurve = [];
  const signals = [];  // {date, type: 'buy'|'sell', price}

  const startIdx = Math.max(shortPeriod, longPeriod) + 1;

  for (let t = startIdx; t < n; t++) {
    const price = closes[t];
    const date = rawData[t][0];
    const equity = cash + shares * price;
    equityCurve.push({ date, equity });

    // 信号判断：使用 T-1 和 T-2 均线值（避免未来函数）
    const ma_s1 = maShort[t-1], ma_l1 = maLong[t-1];
    const ma_s2 = maShort[t-2], ma_l2 = maLong[t-2];

    if (ma_s1 == null || ma_l1 == null || ma_s2 == null || ma_l2 == null) continue;

    const goldenCross = (ma_s1 > ma_l1) && (ma_s2 <= ma_l2);
    const deathCross  = (ma_s1 < ma_l1) && (ma_s2 >= ma_l2);

    if (goldenCross && !hasPosition) {
      const buyPrice = price * (1 + slippage);
      const effectiveCost = buyPrice * (1 + feeRate);
      shares = cash / effectiveCost;
      const cost = shares * effectiveCost;
      cash = 0;
      hasPosition = true;
      trades.push({
        buyDate: date, buyPrice: buyPrice, shares: shares, cost: cost,
        sellDate: null, sellPrice: null, revenue: null, returnPct: null
      });
      signals.push({ date, type: 'buy', price: buyPrice });
    } else if (deathCross && hasPosition) {
      const sellPrice = price * (1 - slippage);
      cash = shares * sellPrice * (1 - feeRate);
      const last = trades[trades.length - 1];
      last.sellDate = date;
      last.sellPrice = sellPrice;
      last.revenue = cash;
      last.returnPct = (cash / last.cost - 1) * 100;
      shares = 0;
      hasPosition = false;
      signals.push({ date, type: 'sell', price: sellPrice });
    }
  }

  // 最后一日强制平仓
  if (hasPosition && n > 0) {
    const finalPrice = closes[n-1] * (1 - slippage);
    cash = shares * finalPrice * (1 - feeRate);
    const last = trades[trades.length - 1];
    last.sellDate = rawData[n-1][0];
    last.sellPrice = finalPrice;
    last.revenue = cash;
    last.returnPct = (cash / last.cost - 1) * 100;
    hasPosition = false;
    signals.push({ date: rawData[n-1][0], type: 'sell', price: finalPrice });
    // 更新最后一条权益
    if (equityCurve.length > 0) {
      equityCurve[equityCurve.length-1].equity = cash;
    }
  }

  // 最后一日权益
  const finalEquity = cash + shares * closes[n-1];

  // 买入持有基准
  const bhPrice0 = closes[0] * (1 + slippage) * (1 + feeRate);
  const bhShares = initialCapital / bhPrice0;
  const bhEquityCurve = rawData.map(r => ({
    date: r[0],
    equity: bhShares * r[2]
  }));
  const bhFinalEquity = bhShares * closes[n-1];

  // 计算完整权益曲线（包括回测前的 days）
  const fullEquityCurve = [];
  for (let t = 0; t < startIdx; t++) {
    fullEquityCurve.push({ date: rawData[t][0], equity: initialCapital });
  }
  for (const e of equityCurve) {
    fullEquityCurve.push(e);
  }

  return {
    maShort, maLong, trades, signals,
    equityCurve: fullEquityCurve,
    finalEquity, bhEquityCurve, bhFinalEquity,
    startIdx, dataLength: n
  };
}

// ═══════════════════════════════════════════════════════════════
// 评估指标计算
// ═══════════════════════════════════════════════════════════════

function calcMetrics(result, initialCapital, riskFreeRate) {
  const { trades, equityCurve, finalEquity, startIdx } = result;

  // 累计回报
  const totalReturn = (finalEquity / initialCapital - 1) * 100;

  // 年化收益率
  const validEquity = equityCurve.filter(e => e.equity != null);
  if (validEquity.length < 2) return null;
  const firstDate = parseDate(validEquity[0].date);
  const lastDate = parseDate(validEquity[validEquity.length-1].date);
  const days = Math.max(1, (lastDate - firstDate) / (1000 * 60 * 60 * 24));
  const annualReturn = (Math.pow(finalEquity / initialCapital, 252 / days) - 1) * 100;

  // 最大回撤 (MDD)
  let peak = -Infinity;
  let mdd = 0;
  for (const e of equityCurve) {
    if (e.equity > peak) peak = e.equity;
    const dd = (e.equity - peak) / peak * 100;
    if (dd < mdd) mdd = dd;
  }

  // 日收益率序列
  const dailyReturns = [];
  for (let i = 1; i < equityCurve.length; i++) {
    const prev = equityCurve[i-1].equity;
    const curr = equityCurve[i].equity;
    if (prev > 0) dailyReturns.push(curr / prev - 1);
  }

  // 夏普比率
  let sharpe = 0;
  if (dailyReturns.length > 1) {
    const meanRet = dailyReturns.reduce((a,b) => a+b, 0) / dailyReturns.length;
    const variance = dailyReturns.reduce((s,r) => s + (r-meanRet)*(r-meanRet), 0) / dailyReturns.length;
    const stdRet = Math.sqrt(variance);
    if (stdRet > 0) {
      sharpe = Math.sqrt(252) * (meanRet - riskFreeRate / 252) / stdRet;
    }
  }
  // Limit sharpe to reasonable range
  sharpe = Math.max(-10, Math.min(10, sharpe));

  // 胜率
  const completedTrades = trades.filter(t => t.sellDate != null);
  const wins = completedTrades.filter(t => t.returnPct > 0);
  const winRate = completedTrades.length > 0 ? (wins.length / completedTrades.length * 100) : 0;

  // 盈亏比
  let profitLossRatio = null;
  const avgWin = wins.length > 0 ? wins.reduce((s,t) => s + t.returnPct, 0) / wins.length : 0;
  const losses = completedTrades.filter(t => t.returnPct <= 0);
  const avgLoss = losses.length > 0 ? losses.reduce((s,t) => s + Math.abs(t.returnPct), 0) / losses.length : 0;
  if (avgLoss > 0) profitLossRatio = avgWin / avgLoss;

  // 年化波动率
  let annualVol = 0;
  if (dailyReturns.length > 1) {
    const meanRet2 = dailyReturns.reduce((a,b) => a+b, 0) / dailyReturns.length;
    const variance2 = dailyReturns.reduce((s,r) => s + (r-meanRet2)*(r-meanRet2), 0) / dailyReturns.length;
    annualVol = Math.sqrt(variance2) * Math.sqrt(252) * 100;
  }

  // 买入持有基准
  const bhTotalReturn = (result.bhFinalEquity / initialCapital - 1) * 100;

  return {
    totalReturn, annualReturn, mdd, sharpe,
    winRate, profitLossRatio, annualVol,
    totalTrades: completedTrades.length,
    bhTotalReturn,
    days: Math.round(days),
  };
}

// ═══════════════════════════════════════════════════════════════
// KPI 卡片渲染
// ═══════════════════════════════════════════════════════════════

function renderMetrics(metrics) {
  const container = document.getElementById('kpi-row');
  if (!metrics) {
    container.innerHTML = '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">累计回报</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">年化收益</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">最大回撤(MDD)</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">夏普比率</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">胜率</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">盈亏比</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">交易次数</div></div>';
    return;
  }

  const items = [
    { label: '累计回报', value: fmtPct(metrics.totalReturn), cls: metrics.totalReturn >= 0 ? 'pos' : 'neg' },
    { label: '年化收益', value: fmtPct(metrics.annualReturn), cls: metrics.annualReturn >= 0 ? 'pos' : 'neg' },
    { label: '最大回撤(MDD)', value: metrics.mdd.toFixed(2) + '%', cls: metrics.mdd > -10 ? 'pos' : (metrics.mdd < -20 ? 'neg' : 'neutral') },
    { label: '夏普比率', value: metrics.sharpe.toFixed(2), cls: metrics.sharpe >= 1 ? 'pos' : (metrics.sharpe < 0 ? 'neg' : 'neutral') },
    { label: '胜率', value: metrics.winRate.toFixed(1) + '%', cls: metrics.winRate >= 50 ? 'pos' : 'neutral' },
    { label: '盈亏比', value: metrics.profitLossRatio != null ? metrics.profitLossRatio.toFixed(2) : 'N/A', cls: metrics.profitLossRatio != null && metrics.profitLossRatio >= 2 ? 'pos' : (metrics.profitLossRatio != null && metrics.profitLossRatio < 1 ? 'neg' : 'neutral') },
    { label: '交易次数', value: metrics.totalTrades, cls: 'neutral' },
  ];

  // Add buy-hold comparison
  items.push({ label: '基准(买入持有)', value: fmtPct(metrics.bhTotalReturn), cls: metrics.bhTotalReturn >= 0 ? 'pos' : 'neg' });

  container.innerHTML = items.map(item =>
    `<div class="kpi-card ${item.cls}"><div class="kpi-val">${item.value}</div><div class="kpi-lbl">${item.label}</div></div>`
  ).join('');
}

// ═══════════════════════════════════════════════════════════════
// ECharts 图表渲染
// ═══════════════════════════════════════════════════════════════

function dateAxis(dates) {
  return { type: 'category', data: dates, axisLabel: { fontSize: 10, rotate: 0 },
    axisLine: { lineStyle: { color: '#ccc' } } };
}

function makeGrid(top) {
  return { left: 65, right: 25, top: top || 55, bottom: 40 };
}

function makeLine(name, data, color, width) {
  return { name, type: 'line', data, lineStyle: { color, width: width || 1.5 },
    symbol: 'none', smooth: false, connectNulls: false };
}

// 图表1: 价格 + 均线 + 交易信号
function drawSignals(rawData, result, stockName, stockCode) {
  const dom = document.getElementById('chart-signals');
  if (!result) { disposeChart('signals'); return; }

  const dates = rawData.map(r => r[0]);
  const closes = rawData.map(r => r[2]);
  const { maShort, maLong, signals } = result;

  // 买入/卖出 marker 数据
  const buyScatter = [];
  const sellScatter = [];
  for (const sig of signals) {
    const idx = dates.indexOf(sig.date);
    if (idx >= 0) {
      if (sig.type === 'buy') {
        buyScatter.push({ coord: [idx, sig.price], value: sig.price });
      } else {
        sellScatter.push({ coord: [idx, sig.price], value: sig.price });
      }
    }
  }

  const option = {
    title: { text: `${stockName} (${stockCode}) — 价格 · 均线 · 交易信号`, left: 10, top: 2,
      textStyle: { fontSize: 13, color: '#2d3436' } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['收盘价', 'MA短', 'MA长'], top: 2, right: 10,
      textStyle: { fontSize: 10, color: '#636e72' } },
    grid: makeGrid(62),
    xAxis: dateAxis(dates),
    yAxis: { type: 'value', name: '价格(元)', nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#f0f0f0' } },
      scale: true },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 25, bottom: 6 }
    ],
    series: [
      makeLine('收盘价', closes, '#b2bec3', 0.8),
      makeLine('MA短', maShort, '#0984e3', 1.5),
      makeLine('MA长', maLong, '#e17055', 1.5),
      {
        name: '买入', type: 'scatter',
        data: buyScatter.map(b => b.coord),
        symbol: 'arrow', symbolSize: 14, symbolRotate: 0,
        itemStyle: { color: '#d63031' },
        tooltip: {
          trigger: 'item',
          formatter: function(p) { return '🔴 买入<br/>日期: ' + dates[p.data[0]] + '<br/>价格: ' + p.data[1].toFixed(2); }
        }
      },
      {
        name: '卖出', type: 'scatter',
        data: sellScatter.map(s => s.coord),
        symbol: 'arrow', symbolSize: 14, symbolRotate: 180,
        itemStyle: { color: '#00b894' },
        tooltip: {
          trigger: 'item',
          formatter: function(p) { return '🟢 卖出<br/>日期: ' + dates[p.data[0]] + '<br/>价格: ' + p.data[1].toFixed(2); }
        }
      },
    ]
  };

  initChart('signals').setOption(option, true);
}

// 图表2: 资产曲线对比
function drawEquity(rawData, result, metrics, stockName) {
  const dom = document.getElementById('chart-equity');
  if (!result) { disposeChart('equity'); return; }

  const dates = result.equityCurve.map(e => e.date);
  const strategyData = result.equityCurve.map(e => e.equity);
  const bhDates = result.bhEquityCurve.map(e => e.date);
  const bhData = result.bhEquityCurve.map(e => e.equity);

  const option = {
    title: { text: `${stockName} — 资产曲线对比 (策略 vs 买入持有)`, left: 10, top: 2,
      textStyle: { fontSize: 12, color: '#2d3436' } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['策略资产', '买入持有'], top: 2, right: 10,
      textStyle: { fontSize: 10, color: '#636e72' } },
    grid: makeGrid(58),
    xAxis: dateAxis(dates),
    yAxis: { type: 'value', name: '资产(元)', nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10, formatter: v => fmtMoney(v) },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    dataZoom: [{ type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 25, bottom: 6 }],
    series: [
      makeLine('策略资产', strategyData, '#0984e3', 2),
      { name: '买入持有', type: 'line', data: bhData,
        lineStyle: { color: '#b2bec3', type: 'dashed', width: 1.2 },
        symbol: 'none' },
    ]
  };

  initChart('equity').setOption(option, true);
}

// 图表3: 回撤曲线
function drawDrawdown(rawData, result, metrics, stockName) {
  const dom = document.getElementById('chart-drawdown');
  if (!result) { disposeChart('drawdown'); return; }

  const equityData = result.equityCurve.map(e => e.equity);
  const dates = result.equityCurve.map(e => e.date);
  let peak = -Infinity;
  const ddData = equityData.map(eq => {
    if (eq > peak) peak = eq;
    return ((eq - peak) / peak * 100);
  });

  const option = {
    title: { text: `${stockName} — 回撤曲线 (Max DD: ${metrics ? metrics.mdd.toFixed(2) : '--'}%)`, left: 10, top: 2,
      textStyle: { fontSize: 12, color: '#2d3436' } },
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        return params[0].axisValue + '<br/>回撤: ' + params[0].value.toFixed(2) + '%';
      }
    },
    grid: makeGrid(58),
    xAxis: dateAxis(dates),
    yAxis: { type: 'value', name: '回撤(%)', nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10, formatter: v => v.toFixed(0) + '%' },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      max: 5 },
    dataZoom: [{ type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 25, bottom: 6 }],
    series: [{
      name: '回撤', type: 'line',
      data: ddData,
      lineStyle: { color: '#d63031', width: 1 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(214,48,49,0.12)' },
            { offset: 1, color: 'rgba(214,48,49,0.02)' }
          ]
        }
      },
      symbol: 'none',
      markLine: {
        silent: true,
        data: [{ yAxis: 0, lineStyle: { color: '#666', type: 'dashed', width: 0.6 } }],
        symbol: 'none'
      }
    }]
  };

  initChart('drawdown').setOption(option, true);
}

// 交易明细表
function renderTrades(result) {
  const tbody = document.getElementById('trade-tbody');
  if (!result || result.trades.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--muted);padding:20px;">该参数组合下未产生交易信号</td></tr>';
    return;
  }

  const completed = result.trades.filter(t => t.sellDate != null);
  if (completed.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--muted);padding:20px;">暂无完整交易记录（当前仍持仓）</td></tr>';
    return;
  }

  let cumulativeReturn = 1;
  tbody.innerHTML = completed.map((t, i) => {
    cumulativeReturn *= (1 + t.returnPct / 100);
    const cumRet = (cumulativeReturn - 1) * 100;
    const holdDays = Math.round((parseDate(t.sellDate) - parseDate(t.buyDate)) / (1000*86400));
    const rowClass = t.returnPct > 0 ? 'win' : 'loss';
    return `<tr class="${rowClass}">
      <td>${i + 1}</td>
      <td>${t.buyDate}</td>
      <td>${t.buyPrice.toFixed(2)}</td>
      <td>${t.sellDate}</td>
      <td>${t.sellPrice.toFixed(2)}</td>
      <td>${holdDays}天</td>
      <td class="ret">${fmtPct(t.returnPct)}</td>
      <td class="ret">${fmtPct(cumRet)}</td>
    </tr>`;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════
// ECharts 实例管理
// ═══════════════════════════════════════════════════════════════

function initChart(id) {
  if (charts[id]) { charts[id].dispose(); }
  const dom = document.getElementById('chart-' + id);
  if (!dom) return null;
  const c = echarts.init(dom);
  charts[id] = c;
  return c;
}

function disposeChart(id) {
  if (charts[id]) { charts[id].dispose(); charts[id] = null; }
  document.getElementById('chart-' + id).innerHTML = '';
}

// ═══════════════════════════════════════════════════════════════
// 参数同步
// ═══════════════════════════════════════════════════════════════

function syncRange(id) {
  const rangeEl = document.getElementById(id + '-range');
  const numEl = document.getElementById(id + '-num');
  if (rangeEl && numEl) {
    numEl.value = rangeEl.value;
  }
  runAll();
}

function syncNum(id) {
  const rangeEl = document.getElementById(id + '-range');
  const numEl = document.getElementById(id + '-num');
  if (rangeEl && numEl) {
    rangeEl.value = numEl.value;
  }
  runAll();
}

// ═══════════════════════════════════════════════════════════════
// 主控制器
// ═══════════════════════════════════════════════════════════════

function getParams() {
  return {
    shortPeriod: parseInt(document.getElementById('ma-short-num').value) || 5,
    longPeriod: parseInt(document.getElementById('ma-long-num').value) || 15,
    startDate: document.getElementById('date-start').value,
    endDate: document.getElementById('date-end').value,
    initialCapital: (parseFloat(document.getElementById('capital-num').value) || 100) * 10000,
    feeRate: (parseFloat(document.getElementById('fee-num').value) || 0.03) / 100,
    slippage: (parseFloat(document.getElementById('slippage-num').value) || 0.01) / 100,
    riskFreeRate: 0.02,
  };
}

function onStockChange() {
  const code = document.getElementById('stock-select').value;
  currentCode = code;
  const stock = STOCKS[code];
  if (stock) {
    document.getElementById('date-start').value = stock.dateStart;
    document.getElementById('date-end').value = stock.dateEnd;
    document.getElementById('stock-info').textContent =
      `${stock.code} ${stock.name} (${stock.market}) | ${stock.dateStart} ~ ${stock.dateEnd} | ${stock.count}条`;
  }
  runAll();
}

function runAll() {
  const params = getParams();
  if (!currentCode) return;

  const stock = STOCKS[currentCode];
  if (!stock) return;

  // 截取时间范围
  let rawData = stock.data;
  if (params.startDate) {
    rawData = rawData.filter(r => r[0] >= params.startDate);
  }
  if (params.endDate) {
    rawData = rawData.filter(r => r[0] <= params.endDate);
  }
  if (rawData.length < Math.max(params.shortPeriod, params.longPeriod) + 5) {
    // 数据不足
    renderMetrics(null);
    document.getElementById('chart-signals').innerHTML =
      '<div style="text-align:center;padding:40px;color:var(--muted)">⚠️ 数据不足以计算均线和回测，请扩展时间范围或减少均线周期</div>';
    disposeChart('equity');
    disposeChart('drawdown');
    document.getElementById('trade-tbody').innerHTML =
      '<tr><td colspan="8" style="color:var(--muted);padding:20px;">数据不足</td></tr>';
    return;
  }

  // 运行回测
  const result = runBacktest(
    rawData,
    params.shortPeriod, params.longPeriod,
    params.initialCapital, params.feeRate, params.slippage
  );

  // 计算指标
  const metrics = calcMetrics(result, params.initialCapital, params.riskFreeRate);

  // 渲染
  lastResult = result;
  renderMetrics(metrics);
  drawSignals(rawData, result, stock.name, stock.code);
  drawEquity(rawData, result, metrics, stock.name);
  drawDrawdown(rawData, result, metrics, stock.name);
  renderTrades(result);
}

// ═══════════════════════════════════════════════════════════════
// 初始化
// ═══════════════════════════════════════════════════════════════

function init() {
  const sel = document.getElementById('stock-select');
  const codes = Object.keys(STOCKS).sort();
  codes.forEach(code => {
    const s = STOCKS[code];
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = `${code} ${s.name} (${s.market}) — ${s.count}条`;
    sel.appendChild(opt);
  });

  // 默认选择茅台 (600519)
  const defaultIdx = codes.indexOf('600519');
  sel.selectedIndex = defaultIdx >= 0 ? defaultIdx : 0;
  currentCode = sel.value;

  const stock = STOCKS[currentCode];
  document.getElementById('date-start').value = stock.dateStart;
  document.getElementById('date-end').value = stock.dateEnd;
  document.getElementById('stock-info').textContent =
    `${stock.code} ${stock.name} (${stock.market}) | ${stock.dateStart} ~ ${stock.dateEnd} | ${stock.count}条`;

  // 首次回测
  runAll();

  // resize 处理
  window.addEventListener('resize', function() {
    Object.values(charts).forEach(c => { if (c) c.resize(); });
  });
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>'''


def main():
    print('=' * 60)
    print('  Task3: 构建回测看板 — 生成 index.html')
    print('=' * 60)

    # 读取数据
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        stocks = json.load(f)

    print(f'  📂 加载 {len(stocks)} 只股票数据')

    # 序列化为 JS 对象
    stocks_json = json.dumps(stocks, ensure_ascii=False, indent=2)

    # 嵌入数据
    html = HTML_TEMPLATE.replace('__STOCKS_DATA__', stocks_json)

    # 写入
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f'\n✅ 看板已生成: {OUTPUT_FILE}')
    print(f'   文件大小: {file_size_kb:.1f} KB')
    print(f'   🌐 在浏览器中打开即可使用（无需服务器）')
    print('=' * 60)


if __name__ == '__main__':
    main()
