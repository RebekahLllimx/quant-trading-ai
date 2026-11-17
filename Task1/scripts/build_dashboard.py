#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate an interactive visualization website  -  -  A-share+Hong Kong equitiesKline graph analysis
use Plotly Implement an interactive candlestick chart, Multi-strand contrast, Market Switch
Output single independent HTML File, No server required
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "Task1"
DATA_DIR = PROJECT_ROOT / "data" / "csv"
HTML_FILE = OUTPUT_DIR / "stock_dashboard.html"

# Read allCSVData
STOCKS = []
csv_dir = DATA_DIR
for f in sorted(os.listdir(csv_dir)):
    if f.endswith('_daily.csv') and ('A_daily' in f or 'HK_daily' in f):
        # Parse File Name: code_Name_Market_daily.csv
        parts = f.replace('_daily.csv', '').rsplit('_', 1)
        mkt = parts[-1]  # A or HK
        name_code = parts[0]
        code = name_code[:5] if name_code[:5].isdigit() else name_code[:6]
        name = name_code[len(code)+1:] if len(name_code) > len(code) else name_code
        csv_path = os.path.join(csv_dir, f)
        try:
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            market = 'A-share' if mkt == 'A' else 'Hong Kong equities'

            # Calculated metric
            close = df['Close']
            chg = round((close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100, 2)
            ret = close.pct_change()
            ann_vol = round(ret.std() * np.sqrt(252) * 100, 2)
            max_dd = round(((close.cummax() - close) / close.cummax()).max() * 100, 2)

            STOCKS.append({
                'code': code, 'name': name, 'market': market, 'file': csv_path,
                'days': len(df), 'chg': chg, 'ann_vol': ann_vol, 'max_dd': max_dd,
                'start_close': round(close.iloc[0], 2),
                'end_close': round(close.iloc[-1], 2),
                'max_close': round(close.max(), 2), 'min_close': round(close.min(), 2),
                'data': df,
            })
        except Exception as e:
            print(f"  Skip {f}: {e}")

print(f"Read {len(STOCKS)} Stock only data")

# separationA-shares and Hong Kong equities
a_stocks = [s for s in STOCKS if s['market'] == 'A-share']
hk_stocks = [s for s in STOCKS if s['market'] == 'Hong Kong equities']

# ==================== Build HTML ====================
html = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A-shares and Hong Kong equitiesKLine Diagram Interactive Analysis Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root {
  --bg: #0f1923; --card: #1a2634; --border: #2a3a4a;
  --text: #e0e6ed; --muted: #8899aa; --accent: #4fc3f7;
  --up: #ef5350; --down: #26a69a; --gold: #ffd54f;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
       background: var(--bg); color: var(--text); min-height: 100vh; }
.header { background: linear-gradient(135deg, #1a2634 0%, #0d2137 100%);
          border-bottom: 2px solid var(--accent); padding: 18px 30px;
          display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 1.6em; color: var(--accent); }
.header .subtitle { color: var(--muted); font-size: 0.85em; }
.tabs { display: flex; gap: 4px; background: var(--card); padding: 6px 20px;
        border-bottom: 1px solid var(--border); }
.tab-btn { padding: 10px 22px; border: none; background: transparent; color: var(--muted);
           cursor: pointer; border-radius: 6px; font-size: 0.95em; transition: all 0.2s; }
.tab-btn:hover { color: var(--text); background: rgba(255,255,255,0.05); }
.tab-btn.active { background: var(--accent); color: #0f1923; font-weight: 600; }
.tab-content { display: none; padding: 20px; }
.tab-content.active { display: block; }
.grid { display: grid; gap: 20px; }
.grid-2 { grid-template-columns: 1fr 1fr; }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
        padding: 18px; }
.card h3 { color: var(--accent); margin-bottom: 10px; font-size: 1.05em; }
.stat-box { text-align: center; padding: 14px; }
.stat-value { font-size: 1.8em; font-weight: 700; }
.stat-label { color: var(--muted); font-size: 0.85em; margin-top: 4px; }
.up { color: var(--up); } .down { color: var(--down); }
.plot-container { width: 100%; min-height: 450px; }
table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--accent); font-weight: 600; position: sticky; top:0; background: var(--card); }
tr:hover { background: rgba(255,255,255,0.03); }
.pill { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }
.pill-a { background: rgba(239,83,80,0.15); color: #ef5350; }
.pill-hk { background: rgba(148,103,189,0.15); color: #b39ddb; }
select, button { padding: 8px 16px; border-radius: 6px; border: 1px solid var(--border);
                 background: var(--card); color: var(--text); font-size: 0.9em; cursor: pointer; }
select:focus, button:focus { outline: 2px solid var(--accent); }
.footer { text-align: center; padding: 20px; color: var(--muted); font-size: 0.8em;
          border-top: 1px solid var(--border); }
@media (max-width: 1200px) { .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<div class="header">
  <div>
    <h1> A-share vs Hong Kong equities Kline graph interaction analysis</h1>
    <div class="subtitle">Data Source: Tushare Pro / AKShare | Adjusted price | ''' + \
    f'{STOCKS[0]["data"]["Date"].min().strftime("%Y-%m-%d")} ~ {STOCKS[0]["data"]["Date"].max().strftime("%Y-%m-%d")}'
html2 = r'''</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:1.2em;font-weight:700;">''' + str(len(STOCKS)) + r'''</div>
    <div style="color:var(--muted);font-size:0.8em;">Only stock coverage</div>
  </div>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('overview')"> Overview</button>
  <button class="tab-btn" onclick="switchTab('astock')"> AStock Details</button>
  <button class="tab-btn" onclick="switchTab('hkstock')"> Hong Kong Stock Details</button>
  <button class="tab-btn" onclick="switchTab('compare')"> Market Comparison</button>
</div>

<!--  Overview  -->
<div id="tab-overview" class="tab-content active">
  <div class="grid grid-2">
    <div class="card">
      <h3> Statistical Summary Table</h3>
      <div style="max-height:420px;overflow-y:auto;" id="summary-table"></div>
    </div>
    <div class="card">
      <h3> Gain/Loss Comparison</h3>
      <div class="plot-container" id="plot-bar-chg"></div>
    </div>
  </div>
  <div class="grid grid-2" style="margin-top:20px;">
    <div class="card">
      <h3> Risk-return quadrant (Volatility vs Return) </h3>
      <div class="plot-container" id="plot-risk-return"></div>
    </div>
    <div class="card">
      <h3> Maximum drawdown comparison</h3>
      <div class="plot-container" id="plot-bar-dd"></div>
    </div>
  </div>
</div>

<!--  AStock Details  -->
<div id="tab-astock" class="tab-content">
  <div style="margin-bottom:16px;">
    <label style="color:var(--muted);margin-right:8px;">Select Stock: </label>
    <select id="a-stock-selector" onchange="updateAStockChart()"></select>
  </div>
  <div class="grid grid-2">
    <div class="card" style="grid-column:1/-1;">
      <h3> dayKLine Candle Chart + Trading volume</h3>
      <div class="plot-container" id="plot-a-candle"></div>
    </div>
  </div>
  <div class="grid grid-2" style="margin-top:20px;">
    <div class="card">
      <h3> Daily Return Distribution</h3>
      <div class="plot-container" id="plot-a-return-dist"></div>
    </div>
    <div class="card">
      <h3> cumulative yield curve</h3>
      <div class="plot-container" id="plot-a-cumret"></div>
    </div>
  </div>
</div>

<!--  Hong Kong Stock Details  -->
<div id="tab-hkstock" class="tab-content">
  <div style="margin-bottom:16px;">
    <label style="color:var(--muted);margin-right:8px;">Select Stock: </label>
    <select id="hk-stock-selector" onchange="updateHKStockChart()"></select>
  </div>
  <div class="grid grid-2">
    <div class="card" style="grid-column:1/-1;">
      <h3> dayKLine Candle Chart + Trading volume</h3>
      <div class="plot-container" id="plot-hk-candle"></div>
    </div>
  </div>
  <div class="grid grid-2" style="margin-top:20px;">
    <div class="card">
      <h3> Daily Return Distribution</h3>
      <div class="plot-container" id="plot-hk-return-dist"></div>
    </div>
    <div class="card">
      <h3> cumulative yield curve</h3>
      <div class="plot-container" id="plot-hk-cumret"></div>
    </div>
  </div>
</div>

<!--  Market Comparison  -->
<div id="tab-compare" class="tab-content">
  <div class="grid grid-2">
    <div class="card" style="grid-column:1/-1;">
      <h3> A-share vs Hong Kong equities normalized price comparison (Benchmark=100) </h3>
      <div class="plot-container" id="plot-norm-compare"></div>
    </div>
  </div>
  <div class="grid grid-2" style="margin-top:20px;">
    <div class="card">
      <h3>AStock sector rise and fall distribution</h3>
      <div class="plot-container" id="plot-a-pie"></div>
    </div>
    <div class="card">
      <h3>Hong Kong equity sector rise and fall distribution</h3>
      <div class="plot-container" id="plot-hk-pie"></div>
    </div>
  </div>
  <div class="grid grid-2" style="margin-top:20px;">
    <div class="card">
      <h3> Comparison of average indicators of two markets</h3>
      <div class="plot-container" id="plot-mkt-compare"></div>
    </div>
    <div class="card">
      <h3> Key Findings</h3>
      <div style="font-size:0.9em;line-height:1.8;" id="insights-text"></div>
    </div>
  </div>
</div>

<div class="footer">
  Data Source: Tushare Pro & AKShare | Adjusted price | Generation time: ''' + datetime.now().strftime('%Y-%m-%d %H:%M') + r''' | Quantitative Trading Course Assignments
</div>

<script>
// ==================== DATA ====================
const STOCKS = ''' + json.dumps([{k: s[k] for k in ['code','name','market','days','chg','ann_vol','max_dd','start_close','end_close','max_close','min_close']} for s in STOCKS], ensure_ascii=False) + r''';
'''

# embedOHLCData
for i, s in enumerate(STOCKS):
    df_json = s['data'][['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    df_json['Date'] = df_json['Date'].dt.strftime('%Y-%m-%d')
    records = df_json.to_dict('records')
    html += f"STOCKS[{i}]['ohlc'] = {json.dumps(records, ensure_ascii=False)};\n"

# A-share/HKStock Index
a_idx = [i for i, s in enumerate(STOCKS) if s['market'] == 'A-share']
hk_idx = [i for i, s in enumerate(STOCKS) if s['market'] == 'Hong Kong equities']
html += f"const A_IDX = {json.dumps(a_idx)};\n"
html += f"const HK_IDX = {json.dumps(hk_idx)};\n"

html += r'''
// ==================== PLOTLY CONFIG ====================
const LAYOUT_DARK = {
  paper_bgcolor: '#1a2634', plot_bgcolor: '#1a2634',
  font: { color: '#e0e6ed', family: 'PingFang SC, Microsoft YaHei, sans-serif' },
  xaxis: { gridcolor: '#2a3a4a', zerolinecolor: '#2a3a4a' },
  yaxis: { gridcolor: '#2a3a4a', zerolinecolor: '#2a3a4a' },
  margin: { l: 60, r: 30, t: 50, b: 60 },
  hovermode: 'x unified',
};

const COLORS = ['#4fc3f7','#ef5350','#26a69a','#ffd54f','#ab47bc','#ff7043','#42a5f5','#66bb6a','#ec407a','#8d6e63'];

// ==================== TAB SWITCHING ====================
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  event.target.classList.add('active');
  if (tab === 'astock') updateAStockChart();
  if (tab === 'hkstock') updateHKStockChart();
}

// ==================== OVERVIEW ====================
function buildSummaryTable() {
  let html = '<table><thead><tr><th>code</th><th>Name</th><th>Market</th><th>Return</th><th>Annualized volatility</th><th>Maximum Drawdown</th><th>Beginning of Period</th><th>End of term</th></tr></thead><tbody>';
  STOCKS.forEach(s => {
    const mktClass = s.market === 'A-share' ? 'pill-a' : 'pill-hk';
    const chgClass = s.chg >= 0 ? 'up' : 'down';
    html += `<tr>
      <td>${s.code}</td><td><strong>${s.name}</strong></td>
      <td><span class="pill ${mktClass}">${s.market}</span></td>
      <td class="${chgClass}" style="font-weight:700;">${s.chg >= 0 ? '+' : ''}${s.chg.toFixed(2)}%</td>
      <td>${s.ann_vol.toFixed(2)}%</td><td>${s.max_dd.toFixed(2)}%</td>
      <td>${s.start_close.toFixed(2)}</td><td>${s.end_close.toFixed(2)}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('summary-table').innerHTML = html;
}

function plotBarChg() {
  const names = STOCKS.map(s => s.name + ' (' + (s.market === 'A-share' ? 'A' : 'HK') + ')');
  const chgs = STOCKS.map(s => s.chg);
  const colors = chgs.map(c => c >= 0 ? '#26a69a' : '#ef5350');
  const data = [{ type: 'bar', x: chgs, y: names, orientation: 'h', marker: { color: colors },
    text: chgs.map(c => (c>=0?'+':'') + c.toFixed(2) + '%'), textposition: 'outside',
    textfont: { color: '#e0e6ed' }, hovertemplate: '%{y}: %{x:.2f}%<extra></extra>' }];
  const layout = { ...LAYOUT_DARK, height: 420, xaxis: { ...LAYOUT_DARK.xaxis, title: 'Return(%)' },
    yaxis: { ...LAYOUT_DARK.yaxis, autorange: 'reversed' } };
  Plotly.newPlot('plot-bar-chg', data, layout, { responsive: true, displayModeBar: false });
}

function plotRiskReturn() {
  const traces = [];
  ['A-share','Hong Kong equities'].forEach(mkt => {
    const subset = STOCKS.filter(s => s.market === mkt);
    traces.push({
      type: 'scatter', mode: 'markers+text',
      x: subset.map(s => s.ann_vol), y: subset.map(s => s.chg),
      text: subset.map(s => s.name), textposition: 'top center',
      textfont: { size: 11, color: '#e0e6ed' },
      marker: { size: subset.map(s => Math.abs(s.chg) * 1.5 + 10),
        color: mkt === 'A-share' ? '#ef5350' : '#ab47bc', opacity: 0.75 },
      name: mkt, hovertemplate: '%{text}<br>fluctuation: %{x:.1f}%<br>Ups and downs: %{y:.2f}%<extra></extra>'
    });
  });
  // Four-quadrant reference line
  traces.push({ type: 'scatter', x: [0, 60], y: [0, 0], mode: 'lines',
    line: { color: '#555', dash: 'dash', width: 1 }, showlegend: false, hoverinfo: 'none' });
  const layout = { ...LAYOUT_DARK, height: 420, xaxis: { ...LAYOUT_DARK.xaxis, title: 'annualized volatility(%)' },
    yaxis: { ...LAYOUT_DARK.yaxis, title: 'Return(%)' } };
  Plotly.newPlot('plot-risk-return', traces, layout, { responsive: true, displayModeBar: false });
}

function plotBarDD() {
  const names = STOCKS.map(s => s.name + ' (' + (s.market === 'A-share' ? 'A' : 'HK') + ')');
  const dds = STOCKS.map(s => s.max_dd);
  const data = [{ type: 'bar', x: dds, y: names, orientation: 'h',
    marker: { color: dds.map(d => d > 30 ? '#ef5350' : '#ffd54f') },
    text: dds.map(d => d.toFixed(2) + '%'), textposition: 'outside',
    textfont: { color: '#e0e6ed' }, hovertemplate: '%{y}: Maximum Drawdown %{x:.2f}%<extra></extra>' }];
  const layout = { ...LAYOUT_DARK, height: 420, xaxis: { ...LAYOUT_DARK.xaxis, title: 'Maximum Drawdown(%)' },
    yaxis: { ...LAYOUT_DARK.yaxis, autorange: 'reversed' } };
  Plotly.newPlot('plot-bar-dd', data, layout, { responsive: true, displayModeBar: false });
}

// ==================== A-share/HKstock Stock Details ====================
function buildStockSelector(selectorId, idxList) {
  const sel = document.getElementById(selectorId);
  sel.innerHTML = idxList.map(i => `<option value="${i}">${STOCKS[i].code} ${STOCKS[i].name}</option>`).join('');
}

function updateStockChart(stockIdx, candleDiv, retDiv, cumDiv) {
  const s = STOCKS[stockIdx];
  const ohlc = s.ohlc;
  const dates = ohlc.map(d => d.Date);
  const opens = ohlc.map(d => d.Open);
  const highs = ohlc.map(d => d.High);
  const lows = ohlc.map(d => d.Low);
  const closes = ohlc.map(d => d.Close);
  const vols = ohlc.map(d => d.Volume / 10000);

  // Candlestick chart
  const candle = {
    type: 'candlestick', name: s.name,
    x: dates, open: opens, high: highs, low: lows, close: closes,
    increasing: { line: { color: '#ef5350' }, fillcolor: '#ef5350' },
    decreasing: { line: { color: '#26a69a' }, fillcolor: '#26a69a' },
    hovertext: dates.map((d,i) =>
      `${d}<br>O:${opens[i].toFixed(2)} H:${highs[i].toFixed(2)} L:${lows[i].toFixed(2)} C:${closes[i].toFixed(2)}<br>Ups and downs: ${((closes[i]-opens[i])/opens[i]*100).toFixed(2)}%`),
    hoverinfo: 'text',
  };
  // Trading volume
  const volBars = {
    type: 'bar', x: dates, y: vols, name: 'Trading volume',
    marker: { color: dates.map((d,i) => closes[i] >= opens[i] ? 'rgba(239,83,80,0.5)' : 'rgba(38,166,154,0.5)') },
    yaxis: 'y2', hovertemplate: 'Trading volume: %{y:.0f}million shares<extra></extra>',
  };
  // Moving average
  const ma20 = calcMA(closes, 20);
  const ma60 = calcMA(closes, 60);
  const ma20Line = { type: 'scatter', x: dates, y: ma20, mode: 'lines',
    line: { color: '#ffd54f', width: 1.2, dash: 'dash' }, name: 'MA20',
    hovertemplate: 'MA20: %{y:.2f}<extra></extra>' };
  const ma60Line = { type: 'scatter', x: dates, y: ma60, mode: 'lines',
    line: { color: '#4fc3f7', width: 1.2, dash: 'dot' }, name: 'MA60',
    hovertemplate: 'MA60: %{y:.2f}<extra></extra>' };

  const layout = {
    ...LAYOUT_DARK, height: 550,
    title: `${s.name} (${s.code})  -  ${s.market} | Return: ${s.chg>=0?'+':''}${s.chg.toFixed(2)}% | fluctuation: ${s.ann_vol.toFixed(2)}% | Maximum Drawdown: ${s.max_dd.toFixed(2)}%`,
    xaxis: { ...LAYOUT_DARK.xaxis, rangeslider: { visible: false }, type: 'date' },
    yaxis: { ...LAYOUT_DARK.yaxis, title: 'Price', side: 'left' },
    yaxis2: { title: 'Trading volume(million shares)', overlaying: 'y', side: 'right', showgrid: false,
      gridcolor: 'rgba(0,0,0,0)', range: [0, Math.max(...vols) * 3.5] },
    legend: { x: 0.01, y: 0.99, bgcolor: 'rgba(26,38,52,0.8)' },
  };
  Plotly.newPlot(candleDiv, [candle, volBars, ma20Line, ma60Line], layout,
    { responsive: true, modeBarButtonsToRemove: ['lasso2d','select2d'] });

  // Yield Distribution
  const rets = [];
  for (let i = 1; i < closes.length; i++) rets.push((closes[i] - closes[i-1]) / closes[i-1] * 100);
  const retData = [{ type: 'histogram', x: rets, nbinsx: 40,
    marker: { color: 'rgba(79,195,247,0.7)', line: { color: '#4fc3f7', width: 1 } },
    hovertemplate: 'yield range: %{x:.2f}%<br>Frequency: %{y}<extra></extra>' }];
  const retLayout = { ...LAYOUT_DARK, height: 350,
    title: `Daily Return Distribution (Mean: ${(rets.reduce((a,b)=>a+b,0)/rets.length).toFixed(3)}%, Standard deviation: ${(Math.sqrt(rets.reduce((a,b)=>a+Math.pow(b-rets.reduce((c,d)=>c+d,0)/rets.length,2),0)/rets.length)).toFixed(3)}%)`,
    xaxis: { ...LAYOUT_DARK.xaxis, title: 'daily rate of return(%)' },
    yaxis: { ...LAYOUT_DARK.yaxis, title: 'Frequency' } };
  Plotly.newPlot(retDiv, retData, retLayout, { responsive: true, displayModeBar: false });

  // Cumulative rate of return
  const cumRet = [0];
  for (let i = 1; i < closes.length; i++) cumRet.push(cumRet[i-1] + (closes[i]-closes[i-1])/closes[i-1]*100);
  const cumData = [{ type: 'scatter', x: dates, y: cumRet, mode: 'lines', fill: 'tozeroy',
    line: { color: cumRet[cumRet.length-1] >= 0 ? '#ef5350' : '#26a69a', width: 2 },
    fillcolor: cumRet[cumRet.length-1] >= 0 ? 'rgba(239,83,80,0.1)' : 'rgba(38,166,154,0.1)',
    hovertemplate: '%{x}<br>Accumulated income: %{y:.2f}%<extra></extra>' }];
  const cumLayout = { ...LAYOUT_DARK, height: 350,
    title: `Cumulative rate of return (total: ${cumRet[cumRet.length-1].toFixed(2)}%)`,
    xaxis: { ...LAYOUT_DARK.xaxis, title: 'Date' },
    yaxis: { ...LAYOUT_DARK.yaxis, title: 'Cumulative rate of return(%)' } };
  Plotly.newPlot(cumDiv, cumData, cumLayout, { responsive: true, displayModeBar: false });
}

function updateAStockChart() {
  const idx = parseInt(document.getElementById('a-stock-selector').value);
  updateStockChart(idx, 'plot-a-candle', 'plot-a-return-dist', 'plot-a-cumret');
}
function updateHKStockChart() {
  const idx = parseInt(document.getElementById('hk-stock-selector').value);
  updateStockChart(idx, 'plot-hk-candle', 'plot-hk-return-dist', 'plot-hk-cumret');
}

// ==================== Market Comparison ====================
function plotNormCompare() {
  const traces = [];
  STOCKS.forEach((s, i) => {
    const closes = s.ohlc.map(d => d.Close);
    const norm = closes.map(c => c / closes[0] * 100);
    traces.push({
      type: 'scatter', x: s.ohlc.map(d => d.Date), y: norm, mode: 'lines',
      name: `${s.name}(${s.market})`, line: { width: 1.5, color: COLORS[i % COLORS.length] },
      hovertemplate: '%{fullData.name}<br>%{x}<br>Normalization: %{y:.1f}<extra></extra>',
    });
  });
  traces.push({ type: 'scatter',
    x: [STOCKS[0].ohlc[0].Date, STOCKS[0].ohlc[STOCKS[0].ohlc.length-1].Date],
    y: [100, 100], mode: 'lines', line: { color: '#555', dash: 'dash', width: 1 },
    showlegend: false, hoverinfo: 'none' });
  const layout = { ...LAYOUT_DARK, height: 480,
    xaxis: { ...LAYOUT_DARK.xaxis, title: 'Date' },
    yaxis: { ...LAYOUT_DARK.yaxis, title: 'Normalized Price(Benchmark=100)' },
    legend: { x: 0.01, y: 0.99, bgcolor: 'rgba(26,38,52,0.8)', font: { size: 10 } } };
  Plotly.newPlot('plot-norm-compare', traces, layout, { responsive: true, displayModeBar: false });
}

function plotPieCharts() {
  const aSubset = A_IDX.map(i => STOCKS[i]);
  const hkSubset = HK_IDX.map(i => STOCKS[i]);
  // A-share
  Plotly.newPlot('plot-a-pie', [{
    type: 'pie', labels: aSubset.map(s => s.name), values: aSubset.map(s => Math.abs(s.chg)),
    textinfo: 'label+percent', hole: 0.4,
    marker: { colors: aSubset.map(s => s.chg >= 0 ? '#26a69a' : '#ef5350') },
    textfont: { color: '#e0e6ed', size: 12 },
    hovertemplate: '%{label}<br>Return: %{value:.2f}%<extra></extra>',
  }], { ...LAYOUT_DARK, height: 350 }, { responsive: true, displayModeBar: false });
  // Hong Kong equities
  Plotly.newPlot('plot-hk-pie', [{
    type: 'pie', labels: hkSubset.map(s => s.name), values: hkSubset.map(s => Math.abs(s.chg)),
    textinfo: 'label+percent', hole: 0.4,
    marker: { colors: hkSubset.map(s => s.chg >= 0 ? '#26a69a' : '#ef5350') },
    textfont: { color: '#e0e6ed', size: 12 },
    hovertemplate: '%{label}<br>Return: %{value:.2f}%<extra></extra>',
  }], { ...LAYOUT_DARK, height: 350 }, { responsive: true, displayModeBar: false });
}

function plotMktCompare() {
  const aChgs = A_IDX.map(i => STOCKS[i].chg);
  const hkChgs = HK_IDX.map(i => STOCKS[i].chg);
  const aVols = A_IDX.map(i => STOCKS[i].ann_vol);
  const hkVols = HK_IDX.map(i => STOCKS[i].ann_vol);
  const aDDs = A_IDX.map(i => STOCKS[i].max_dd);
  const hkDDs = HK_IDX.map(i => STOCKS[i].max_dd);

  const mean = arr => arr.reduce((a,b) => a+b, 0) / arr.length;
  const traces = [
    { type: 'bar', x: ['Average Gain/Loss','average volatility','Average Maximum drawdown'], y: [mean(aChgs), mean(aVols), mean(aDDs)],
      name: 'A-share', marker: { color: '#ef5350' }, text: [mean(aChgs).toFixed(2)+'%', mean(aVols).toFixed(2)+'%', mean(aDDs).toFixed(2)+'%'],
      textposition: 'outside', textfont: { color: '#e0e6ed' } },
    { type: 'bar', x: ['Average Gain/Loss','average volatility','Average Maximum drawdown'], y: [mean(hkChgs), mean(hkVols), mean(hkDDs)],
      name: 'Hong Kong equities', marker: { color: '#ab47bc' }, text: [mean(hkChgs).toFixed(2)+'%', mean(hkVols).toFixed(2)+'%', mean(hkDDs).toFixed(2)+'%'],
      textposition: 'outside', textfont: { color: '#e0e6ed' } },
  ];
  const layout = { ...LAYOUT_DARK, height: 350, barmode: 'group',
    yaxis: { ...LAYOUT_DARK.yaxis, title: 'percentage(%)' } };
  Plotly.newPlot('plot-mkt-compare', traces, layout, { responsive: true, displayModeBar: false });
}

const insightsHtml = `'''

# Generate Insights
a_avg_chg = np.mean([s['chg'] for s in STOCKS if s['market'] == 'A-share'])
hk_avg_chg = np.mean([s['chg'] for s in STOCKS if s['market'] == 'Hong Kong equities'])
a_best = max([s for s in STOCKS if s['market'] == 'A-share'], key=lambda x: x['chg'])
a_worst = min([s for s in STOCKS if s['market'] == 'A-share'], key=lambda x: x['chg'])
hk_best = max([s for s in STOCKS if s['market'] == 'Hong Kong equities'], key=lambda x: x['chg'])
hk_worst = min([s for s in STOCKS if s['market'] == 'Hong Kong equities'], key=lambda x: x['chg'])
a_avg_vol = np.mean([s['ann_vol'] for s in STOCKS if s['market'] == 'A-share'])
hk_avg_vol = np.mean([s['ann_vol'] for s in STOCKS if s['market'] == 'Hong Kong equities'])

insights = f"""
<p> <b>Sample Overview: </b>A-share5only (Bank Coverage, Baijiu, New energy, Insurance, battery) , Hong Kong equities5only (the Internet, E-commerce, Local Life, Exchange, Telecommunications) . </p>
<p> <b>Average performance: </b>ASample mean of stocks <span style="color:{'#26a69a' if a_avg_chg>=0 else '#ef5350'};font-weight:700;">{a_avg_chg:+.2f}%</span>,
Sample mean of Hong Kong equities <span style="color:{'#26a69a' if hk_avg_chg>=0 else '#ef5350'};font-weight:700;">{hk_avg_chg:+.2f}%</span>. </p>
<p> <b>ABest unit: </b>{a_best['name']} ({a_best['code']}) <span style="color:#26a69a;">+{a_best['chg']:.2f}%</span>, The new energy battery sector stands out as a leader. </p>
<p> <b>AThe worst stock: </b>{a_worst['name']} ({a_worst['code']}) <span style="color:#ef5350;">{a_worst['chg']:.2f}%</span>, New energy vehicle competition intensifies. </p>
<p> <b>Best Hong Kong Stock: </b>{hk_best['name']} ({hk_best['code']}) <span style="color:#26a69a;">{hk_best['chg']:.2f}%</span>, Defensive Telecom Blue Chip. </p>
<p> <b>Hong Kong equities are the worst: </b>{hk_worst['name']} ({hk_worst['code']}) <span style="color:#ef5350;">{hk_worst['chg']:.2f}%</span>, Local life track valuation hit hard. </p>
<p> <b>Volatility Characteristics: </b>AAverage stock volatility {a_avg_vol:.1f}%, Hong Kong equities {hk_avg_vol:.1f}% -  - Hong Kong tech stocks show significantly higher volatility. </p>
<p> <b>Core revelation: </b>Diversified investment across markets can reduce portfolio volatility; ANew energy stocks have shown a standout independent market performance.; Hong Kong equities high volatility high drawdown, Need more risk tolerance. </p>
"""
html += f"const insightsHtml = `{insights}`;\n"

html += r'''
document.getElementById('insights-text').innerHTML = insightsHtml;

// ==================== HELPER ====================
function calcMA(arr, window) {
  return arr.map((_, i) => {
    if (i < window - 1) return null;
    let sum = 0;
    for (let j = i - window + 1; j <= i; j++) sum += arr[j];
    return sum / window;
  });
}

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', () => {
  buildSummaryTable();
  plotBarChg();
  plotRiskReturn();
  plotBarDD();
  buildStockSelector('a-stock-selector', A_IDX);
  buildStockSelector('hk-stock-selector', HK_IDX);
  updateAStockChart();
  updateHKStockChart();
  plotNormCompare();
  plotPieCharts();
  plotMktCompare();
});
</script>
</body>
</html>
'''

# SaveHTML
with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Interactive Web site generated: {HTML_FILE}")
print(f"File size: {os.path.getsize(HTML_FILE) / 1024 / 1024:.1f} MB")
print("Open with browser to use! ")
