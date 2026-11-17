#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task3 Phase 2: Build an interactive backtesting dashboard for the dual moving average strategy
Read data.json, generated from the contained index.html (Embed Data + ECharts + All backtest logic)
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'dashboard', 'data.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'dashboard', 'index.html')

#
# HTML Template
#

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title> Dual moving-average strategy backtest dashboard  -  Task3</title>
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
  <h1>Dual Moving-Average Backtest <span style="font-weight:400;font-size:0.8em;opacity:0.8;">| SMA Crossover</span></h1>
</div>

<div class="layout">
<div class="sidebar">
  <div class="card">
    <h3>Target</h3>
    <label>Target</label>
    <select id="stock-select" onchange="onStockChange()"></select>
    <div id="stock-info" style="font-size:0.72em;color:var(--muted);margin-top:4px;padding:2px 0"></div>
  </div>

  <div class="card">
    <h3>Strategy Parameters</h3>
    <div id="params-content">
      <div class="param-row">
        <span class="lbl">Short moving average period</span>
        <input type="range" id="ma-short-range" min="2" max="60" value="5"
          oninput="syncRange('ma-short')">
        <input type="number" id="ma-short-num" value="5" min="2" max="60"
          onchange="syncNum('ma-short')">
      </div>
      <div class="param-row">
        <span class="lbl">Long moving average period</span>
        <input type="range" id="ma-long-range" min="5" max="120" value="15"
          oninput="syncRange('ma-long')">
        <input type="number" id="ma-long-num" value="15" min="5" max="120"
          onchange="syncNum('ma-long')">
      </div>
    </div>
  </div>

  <div class="card">
    <h3> Time range</h3>
    <div class="date-row">
      <span style="min-width:36px;color:var(--muted);font-size:0.76em;">Beginning</span>
      <input type="date" id="date-start" onchange="runAll()">
    </div>
    <div class="date-row" style="margin-top:4px;">
      <span style="min-width:36px;color:var(--muted);font-size:0.76em;">End</span>
      <input type="date" id="date-end" onchange="runAll()">
    </div>
  </div>

  <div class="card">
    <h3> Funds & Cost</h3>
    <div class="param-row">
      <span class="lbl">Initial funding(million)</span>
      <input type="range" id="capital-range" min="1" max="1000" value="100"
        oninput="syncRange('capital')" style="flex:1">
      <input type="number" id="capital-num" value="100" min="1" max="1000"
        onchange="syncNum('capital')" style="width:60px">
    </div>
    <div class="param-row">
      <span class="lbl">Fee rate(%)</span>
      <input type="range" id="fee-range" min="0" max="1" value="0.03" step="0.01"
        oninput="syncRange('fee')" style="flex:1">
      <input type="number" id="fee-num" value="0.03" min="0" max="1" step="0.01"
        onchange="syncNum('fee')" style="width:60px">
    </div>
    <div class="param-row">
      <span class="lbl">slippage rate(%)</span>
      <input type="range" id="slippage-range" min="0" max="1" value="0.01" step="0.01"
        oninput="syncRange('slippage')" style="flex:1">
      <input type="number" id="slippage-num" value="0.01" min="0" max="1" step="0.01"
        onchange="syncNum('slippage')" style="width:60px">
    </div>
  </div>

  <button class="btn-primary" onclick="runAll()">Run Backtest</button>
</div>

<div class="main">
  <!-- KPI Metric Card -->
  <div class="kpi-row" id="kpi-row">
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Cumulative Return</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Annualized return</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Maximum Drawdown(MDD)</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Sharpe Ratio</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Win rate</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Profit/Loss Ratio</div></div>
    <div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Number of transactions</div></div>
  </div>

  <!-- Chart1: Price + Moving average + Trading signals -->
  <div id="chart-signals" class="chart-box chart-panel"></div>

  <!-- Chart2: Asset Curve Comparison -->
  <div id="chart-equity" class="chart-box half chart-panel"></div>

  <!-- Chart3: Drawdown Curve -->
  <div id="chart-drawdown" class="chart-box half chart-panel"></div>

  <!-- Transaction Details -->
  <div class="card">
    <h3>Transactions</h3>
    <div class="table-wrap" id="trade-table-wrap">
      <table class="trade-table" id="trade-table">
        <thead><tr>
          <th>#</th><th>Purchase Date</th><th>Purchase Price</th><th>Sell Date</th><th>Selling Price</th>
          <th>HOLD DAYS</th><th>Yield</th><th>Accumulated income</th>
        </tr></thead>
        <tbody id="trade-tbody">
          <tr><td colspan="8" style="color:var(--muted);padding:20px;">Choose parameters and run the backtest.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
</div>


<script>
//
// Embed Data
//
const STOCKS = __STOCKS_DATA__;

//
// Global Status
//
let currentCode = '';
let charts = {};
let lastResult = null;

//
// Tool Functions
//

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
  if (Math.abs(v) >= 1e8) return (v/1e8).toFixed(2)+'hundred million';
  if (Math.abs(v) >= 1e4) return (v/1e4).toFixed(2)+'million';
  return v.toFixed(2);
}

function fmtPct(v) {
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
}

//
// Backtesting Engine
//

function runBacktest(rawData, shortPeriod, longPeriod, initialCapital, feeRate, slippage) {
  // rawData: [[date, open, close, high, low, volume], ...]
  const n = rawData.length;
  const closes = rawData.map(r => r[2]);

  // Calculate moving average
  const maShort = calcSMA(closes, shortPeriod);
  const maLong = calcSMA(closes, longPeriod);

  // Backtest Status
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

    // Signal Judgment: use T-1 and T-2 Moving average value (Avoid future functions)
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

  // Last-day forced liquidation
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
    // Update the last benefit
    if (equityCurve.length > 0) {
      equityCurve[equityCurve.length-1].equity = cash;
    }
  }

  // Last Day Benefits
  const finalEquity = cash + shares * closes[n-1];

  // Buy-to-hold benchmark
  const bhPrice0 = closes[0] * (1 + slippage) * (1 + feeRate);
  const bhShares = initialCapital / bhPrice0;
  const bhEquityCurve = rawData.map(r => ({
    date: r[0],
    equity: bhShares * r[2]
  }));
  const bhFinalEquity = bhShares * closes[n-1];

  // Calculate the complete equity curve (including pre-backtest days)
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

//
// Evaluation index calculation
//

function calcMetrics(result, initialCapital, riskFreeRate) {
  const { trades, equityCurve, finalEquity, startIdx } = result;

  // Cumulative Return
  const totalReturn = (finalEquity / initialCapital - 1) * 100;

  // Annualized return rate
  const validEquity = equityCurve.filter(e => e.equity != null);
  if (validEquity.length < 2) return null;
  const firstDate = parseDate(validEquity[0].date);
  const lastDate = parseDate(validEquity[validEquity.length-1].date);
  const days = Math.max(1, (lastDate - firstDate) / (1000 * 60 * 60 * 24));
  const annualReturn = (Math.pow(finalEquity / initialCapital, 252 / days) - 1) * 100;

  // Maximum Drawdown (MDD)
  let peak = -Infinity;
  let mdd = 0;
  for (const e of equityCurve) {
    if (e.equity > peak) peak = e.equity;
    const dd = (e.equity - peak) / peak * 100;
    if (dd < mdd) mdd = dd;
  }

  // daily yield series
  const dailyReturns = [];
  for (let i = 1; i < equityCurve.length; i++) {
    const prev = equityCurve[i-1].equity;
    const curr = equityCurve[i].equity;
    if (prev > 0) dailyReturns.push(curr / prev - 1);
  }

  // Sharpe Ratio
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

  // Win rate
  const completedTrades = trades.filter(t => t.sellDate != null);
  const wins = completedTrades.filter(t => t.returnPct > 0);
  const winRate = completedTrades.length > 0 ? (wins.length / completedTrades.length * 100) : 0;

  // Profit/Loss Ratio
  let profitLossRatio = null;
  const avgWin = wins.length > 0 ? wins.reduce((s,t) => s + t.returnPct, 0) / wins.length : 0;
  const losses = completedTrades.filter(t => t.returnPct <= 0);
  const avgLoss = losses.length > 0 ? losses.reduce((s,t) => s + Math.abs(t.returnPct), 0) / losses.length : 0;
  if (avgLoss > 0) profitLossRatio = avgWin / avgLoss;

  // annualized volatility
  let annualVol = 0;
  if (dailyReturns.length > 1) {
    const meanRet2 = dailyReturns.reduce((a,b) => a+b, 0) / dailyReturns.length;
    const variance2 = dailyReturns.reduce((s,r) => s + (r-meanRet2)*(r-meanRet2), 0) / dailyReturns.length;
    annualVol = Math.sqrt(variance2) * Math.sqrt(252) * 100;
  }

  // Buy-to-hold benchmark
  const bhTotalReturn = (result.bhFinalEquity / initialCapital - 1) * 100;

  return {
    totalReturn, annualReturn, mdd, sharpe,
    winRate, profitLossRatio, annualVol,
    finalEquity,
    totalTrades: completedTrades.length,
    bhTotalReturn,
    days: Math.round(days),
  };
}

//
// KPI Card Rendering
//

function renderMetrics(metrics) {
  const container = document.getElementById('kpi-row');
  if (!metrics) {
    container.innerHTML = '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Cumulative Return</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Annualized return</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Maximum Drawdown(MDD)</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Sharpe Ratio</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Win rate</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Profit/Loss Ratio</div></div>'
      + '<div class="kpi-card neutral"><div class="kpi-val">--</div><div class="kpi-lbl">Number of transactions</div></div>';
    return;
  }

  const items = [
    { label: 'Cumulative Return', value: fmtPct(metrics.totalReturn), cls: metrics.totalReturn >= 0 ? 'pos' : 'neg' },
    { label: 'Final interest', value: (metrics.finalEquity / 10000).toFixed(2) + 'million', cls: metrics.totalReturn >= 0 ? 'pos' : 'neg' },
    { label: 'Annualized return', value: fmtPct(metrics.annualReturn), cls: metrics.annualReturn >= 0 ? 'pos' : 'neg' },
    { label: 'Maximum Drawdown(MDD)', value: metrics.mdd.toFixed(2) + '%', cls: metrics.mdd > -10 ? 'pos' : (metrics.mdd < -20 ? 'neg' : 'neutral') },
    { label: 'Sharpe Ratio', value: metrics.sharpe.toFixed(2), cls: metrics.sharpe >= 1 ? 'pos' : (metrics.sharpe < 0 ? 'neg' : 'neutral') },
    { label: 'Win rate', value: metrics.winRate.toFixed(1) + '%', cls: metrics.winRate >= 50 ? 'pos' : 'neutral' },
    { label: 'Profit/Loss Ratio', value: metrics.profitLossRatio != null ? metrics.profitLossRatio.toFixed(2) : 'N/A', cls: metrics.profitLossRatio != null && metrics.profitLossRatio >= 2 ? 'pos' : (metrics.profitLossRatio != null && metrics.profitLossRatio < 1 ? 'neg' : 'neutral') },
    { label: 'Number of transactions', value: metrics.totalTrades, cls: 'neutral' },
  ];

  // Add buy-hold comparison
  items.push({ label: 'Benchmark(Buy and hold)', value: fmtPct(metrics.bhTotalReturn), cls: metrics.bhTotalReturn >= 0 ? 'pos' : 'neg' });

  container.innerHTML = items.map(item =>
    `<div class="kpi-card ${item.cls}"><div class="kpi-val">${item.value}</div><div class="kpi-lbl">${item.label}</div></div>`
  ).join('');
}

//
// ECharts Chart Rendering
//

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

// Chart1: Price + Moving average + Trading signals
function drawSignals(rawData, result, stockName, stockCode) {
  const dom = document.getElementById('chart-signals');
  if (!result) { disposeChart('signals'); return; }

  const dates = rawData.map(r => r[0]);
  const closes = rawData.map(r => r[2]);
  const { maShort, maLong, signals } = result;

  // Buy/Sell marker Data
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
    title: { text: `${stockName} (${stockCode})  -  Price  -  Moving average  -  Trading signals`, left: 10, top: 2,
      textStyle: { fontSize: 13, color: '#2d3436' } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['Close', 'MAshort', 'MAlong'], top: 2, right: 10,
      textStyle: { fontSize: 10, color: '#636e72' } },
    grid: makeGrid(75),
    xAxis: dateAxis(dates),
    yAxis: { type: 'value', name: 'Price(yuan)', nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#f0f0f0' } },
      scale: true },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 25, bottom: 6 }
    ],
    series: [
      makeLine('Close', closes, '#b2bec3', 0.8),
      makeLine('MAshort', maShort, '#0984e3', 1.5),
      makeLine('MAlong', maLong, '#e17055', 1.5),
      {
        name: 'Buy', type: 'scatter',
        data: buyScatter.map(b => b.coord),
        symbol: 'arrow', symbolSize: 14, symbolRotate: 0,
        itemStyle: { color: '#d63031' },
        tooltip: {
          trigger: 'item',
          formatter: function(p) { return ' Buy<br/>Date: ' + dates[p.data[0]] + '<br/>Price: ' + p.data[1].toFixed(2); }
        }
      },
      {
        name: 'Sell', type: 'scatter',
        data: sellScatter.map(s => s.coord),
        symbol: 'arrow', symbolSize: 14, symbolRotate: 180,
        itemStyle: { color: '#00b894' },
        tooltip: {
          trigger: 'item',
          formatter: function(p) { return ' Sell<br/>Date: ' + dates[p.data[0]] + '<br/>Price: ' + p.data[1].toFixed(2); }
        }
      },
    ]
  };

  initChart('signals').setOption(option, true);
}

// Chart2: Asset Curve Comparison
function drawEquity(rawData, result, metrics, stockName) {
  const dom = document.getElementById('chart-equity');
  if (!result) { disposeChart('equity'); return; }

  const dates = result.equityCurve.map(e => e.date);
  const strategyData = result.equityCurve.map(e => e.equity);
  const bhDates = result.bhEquityCurve.map(e => e.date);
  const bhData = result.bhEquityCurve.map(e => e.equity);

  const option = {
    title: { text: `${stockName}  -  Asset Curve Comparison (Strategy vs Buy and hold)`, left: 10, top: 2,
      textStyle: { fontSize: 12, color: '#2d3436' } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['Strategic Assets', 'Buy and hold'], top: 2, right: 10,
      textStyle: { fontSize: 10, color: '#636e72' } },
    grid: makeGrid(70),
    xAxis: dateAxis(dates),
    yAxis: { type: 'value', name: 'Assets(yuan)', nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10, formatter: v => fmtMoney(v) },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    dataZoom: [{ type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 25, bottom: 6 }],
    series: [
      makeLine('Strategic Assets', strategyData, '#0984e3', 2),
      { name: 'Buy and hold', type: 'line', data: bhData,
        lineStyle: { color: '#b2bec3', type: 'dashed', width: 1.2 },
        symbol: 'none' },
    ]
  };

  initChart('equity').setOption(option, true);
}

// Chart3: Drawdown Curve
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
    title: { text: `${stockName}  -  Drawdown Curve (Max DD: ${metrics ? metrics.mdd.toFixed(2) : '--'}%)`, left: 10, top: 2,
      textStyle: { fontSize: 12, color: '#2d3436' } },
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        return params[0].axisValue + '<br/>drawdown: ' + params[0].value.toFixed(2) + '%';
      }
    },
    grid: makeGrid(70),
    xAxis: dateAxis(dates),
    yAxis: { type: 'value', name: 'drawdown(%)', nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10, formatter: v => v.toFixed(0) + '%' },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      max: 5 },
    dataZoom: [{ type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 25, bottom: 6 }],
    series: [{
      name: 'drawdown', type: 'line',
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

// Transaction Details
function renderTrades(result) {
  const tbody = document.getElementById('trade-tbody');
  if (!result || result.trades.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--muted);padding:20px;">No trading signals were generated under this parameter combination</td></tr>';
    return;
  }

  const completed = result.trades.filter(t => t.sellDate != null);
  if (completed.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:var(--muted);padding:20px;">No complete transaction history available yet. (Current Position) </td></tr>';
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
      <td>${holdDays}days</td>
      <td class="ret">${fmtPct(t.returnPct)}</td>
      <td class="ret">${fmtPct(cumRet)}</td>
    </tr>`;
  }).join('');
}

//
// ECharts Instance Management
//

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

//
// Parameter Synchronization
//

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

//
// Main Controller
//

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
      `${stock.code} ${stock.name} (${stock.market}) | ${stock.dateStart} ~ ${stock.dateEnd} | ${stock.count}item`;
  }
  runAll();
}

function runAll() {
  const params = getParams();
  if (!currentCode) return;

  const stock = STOCKS[currentCode];
  if (!stock) return;

  // Interception time range
  let rawData = stock.data;
  if (params.startDate) {
    rawData = rawData.filter(r => r[0] >= params.startDate);
  }
  if (params.endDate) {
    rawData = rawData.filter(r => r[0] <= params.endDate);
  }
  if (rawData.length < Math.max(params.shortPeriod, params.longPeriod) + 5) {
    // Insufficient data
    renderMetrics(null);
    document.getElementById('chart-signals').innerHTML =
      '<div style="text-align:center;padding:40px;color:var(--muted)"> Insufficient Data to Calculate Moving Averages and Perform Backtesting, Please extend the time range or reduce the moving average cycle</div>';
    disposeChart('equity');
    disposeChart('drawdown');
    document.getElementById('trade-tbody').innerHTML =
      '<tr><td colspan="8" style="color:var(--muted);padding:20px;">Insufficient data</td></tr>';
    return;
  }

  // Run Backtest
  const result = runBacktest(
    rawData,
    params.shortPeriod, params.longPeriod,
    params.initialCapital, params.feeRate, params.slippage
  );

  // Calculated metric
  const metrics = calcMetrics(result, params.initialCapital, params.riskFreeRate);

  // rendering
  lastResult = result;
  renderMetrics(metrics);
  drawSignals(rawData, result, stock.name, stock.code);
  drawEquity(rawData, result, metrics, stock.name);
  drawDrawdown(rawData, result, metrics, stock.name);
  renderTrades(result);
}

//
// Initialization
//

function init() {
  const sel = document.getElementById('stock-select');
  const codes = Object.keys(STOCKS).sort();
  codes.forEach(code => {
    const s = STOCKS[code];
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = `${code} ${s.name} (${s.market})  -  ${s.count}item`;
    sel.appendChild(opt);
  });

  // Maotai is selected by default (600519)
  const defaultIdx = codes.indexOf('600519');
  sel.selectedIndex = defaultIdx >= 0 ? defaultIdx : 0;
  currentCode = sel.value;

  const stock = STOCKS[currentCode];
  document.getElementById('date-start').value = stock.dateStart;
  document.getElementById('date-end').value = stock.dateEnd;
  document.getElementById('stock-info').textContent =
    `${stock.code} ${stock.name} (${stock.market}) | ${stock.dateStart} ~ ${stock.dateEnd} | ${stock.count}item`;

  // First backtest (double RAF ensure DOM Layout complete)
  // setTimeout(0) ensure DOM Initialize rendering after layout is completed
  setTimeout(() => {
    requestAnimationFrame(() => {
      Object.values(charts).forEach(c => { if (c) c.resize(); });
      runAll();
    });
  }, 0);

  // resize process
  window.addEventListener('resize', function() {
    Object.values(charts).forEach(c => { if (c) c.resize(); });
  });
}

document.addEventListener('DOMContentLoaded', init);
// Spare: window.load Trigger rendering again (Prevent DOMContentLoaded When the layout is not complete)
window.addEventListener('load', () => { setTimeout(() => { Object.values(charts).forEach(c => { if (c) c.resize(); }); runAll(); }, 100); });
</script>
</body>
</html>'''


def main():
    print('=' * 60)
    print('  Task3: Build a backtest dashboard  -  Generate index.html')
    print('=' * 60)

    # Read data
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        stocks = json.load(f)

    print(f'   Loading {len(stocks)} Stock only data')

    # Serialized as JS object
    stocks_json = json.dumps(stocks, ensure_ascii=False, indent=2)

    # Embed Data
    html = HTML_TEMPLATE.replace('__STOCKS_DATA__', stocks_json)

    # Write
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f'\n Dashboard generated: {OUTPUT_FILE}')
    print(f'   File size: {file_size_kb:.1f} KB')
    print(f'    They can be used by opening them in a browser (No server required) ')
    print('=' * 60)


if __name__ == '__main__':
    main()
