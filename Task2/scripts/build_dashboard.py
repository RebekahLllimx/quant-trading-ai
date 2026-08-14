#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4: 构建静态交互看板
  读取 10 只股票 CSV → 序列化为 JSON → 注入 HTML 模板 → 输出 Task2/dashboard/index.html

  用法:
    python build_dashboard.py
    生成 Task2/dashboard/index.html
    双击 HTML 即可在浏览器中交互使用
"""

import os
import json
import pandas as pd

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data', 'csv')
OUTPUT_FILE = os.path.join(BASE_DIR, '..', 'dashboard', 'index.html')
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# 10 只股票配置
STOCKS = [
    {"code": "000001", "name": "平安银行", "market": "A股"},
    {"code": "600519", "name": "贵州茅台", "market": "A股"},
    {"code": "002594", "name": "比亚迪", "market": "A股"},
    {"code": "601318", "name": "中国平安", "market": "A股"},
    {"code": "300750", "name": "宁德时代", "market": "A股"},
    {"code": "00700", "name": "腾讯控股", "market": "港股"},
    {"code": "09988", "name": "阿里巴巴", "market": "港股"},
    {"code": "03690", "name": "美团", "market": "港股"},
    {"code": "00388", "name": "香港交易所", "market": "港股"},
    {"code": "00941", "name": "中国移动", "market": "港股"},
]


def load_all_stocks():
    """加载所有股票数据，返回 { code: { name, market, data: [...] } }"""
    all_data = {}
    for s in STOCKS:
        filename = f"{s['code']}_{s['name']}_{s['market']}_daily.csv"
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  ⚠️ 跳过: {filename} (文件不存在)")
            continue

        df = pd.read_csv(filepath, encoding='utf-8-sig')

        # 转换数据为列表格式 (每行 = [date, open, high, low, close, volume])
        records = []
        for _, row in df.iterrows():
            records.append([
                str(row['Date']),
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                float(row['Volume']),
            ])

        all_data[s['code']] = {
            "code": s['code'],
            "name": s['name'],
            "market": s['market'],
            "data": records,
            "start": records[0][0],
            "end": records[-1][0],
            "count": len(records),
        }
        print(f"  ✅ {s['code']} {s['name']}: {len(records)} 条")

    return all_data


def build_html():
    """生成 Task2/dashboard/index.html"""
    print("=" * 60)
    print("  构建交互看板 dashboard.html")
    print("=" * 60)

    # 加载数据
    print("\n📂 加载股票数据...")
    stocks_data = load_all_stocks()
    print(f"\n  共 {len(stocks_data)} 只股票")

    # 序列化为 JSON
    stocks_json = json.dumps(stocks_data, ensure_ascii=False, indent=None)

    print(f"  JSON 数据大小: {len(stocks_json):,} 字符")

    # 读取 HTML 模板并注入数据
    html_content = HTML_TEMPLATE.replace("__STOCKS_DATA_PLACEHOLDER__", stocks_json)

    # 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

    file_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n✅ 看板已生成!")
    print(f"   路径: {OUTPUT_FILE}")
    print(f"   大小: {file_size_mb:.1f} MB")
    print(f"\n   使用方式:")
    print(f"   1. 双击 Task2/dashboard/index.html 在浏览器中打开")
    print(f"   2. 可部署到 GitHub Pages")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# HTML 模板
# ═══════════════════════════════════════════════════════════════

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📊 量化交易技术指标看板 — Task2</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root {
  --bg: #f5f6fa; --card: #fff; --text: #2d3436; --muted: #636e72;
  --accent: #0984e3; --up: #d63031; --down: #00b894; --border: #dfe6e9;
  --shadow: 0 2px 8px rgba(0,0,0,0.06);
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
select,button{padding:7px 10px;border:1px solid var(--border);border-radius:6px;
  font-size:0.83em;font-family:inherit;cursor:pointer;width:100%}
select:focus{outline:2px solid var(--accent)}
.btn-primary{background:var(--accent);color:#fff;font-weight:600;border:none}
.btn-primary:hover{background:#0773c5}
.chart-panel{background:var(--card);border-radius:10px;padding:8px;
  box-shadow:var(--shadow);border:1px solid var(--border);flex-shrink:0}
.chart-box{width:100%;height:580px}
.chart-box.sub{height:380px}
.stock-info{padding:6px 0;font-size:0.78em;color:var(--muted);display:flex;
  justify-content:space-between;flex-wrap:wrap}
.stock-info .chg{font-weight:600}
.chg.up{color:var(--up)}.chg.down{color:var(--down)}
.param-row{display:flex;align-items:center;justify-content:space-between;gap:4px;
  font-size:0.76em;padding:3px 0}
.param-row span.lbl{color:var(--text);min-width:36px}
.param-row input[type=range]{width:50px;margin:0 3px}
.param-row input[type=number]{width:44px;border:1px solid var(--border);padding:2px 3px;
  border-radius:3px;font-size:0.85em;text-align:center}
.toggle-row{display:flex;align-items:center;gap:4px;font-size:0.78em;cursor:pointer;
  padding:2px 0}
.toggle-row input{margin:0;width:auto}
.footer{text-align:center;padding:8px;color:var(--muted);font-size:0.72em;
  border-top:1px solid var(--border)}
@media(max-width:900px){.layout{flex-direction:column}.sidebar{width:100%;min-width:0}}
</style>
</head>
<body>

<div class="topbar">
  <h1>📊 技术指标分析看板 <span style="font-weight:400;font-size:0.8em;opacity:0.8;">| RSI · MACD · BOLL · ATR · KDJ · MA · CCI · ADX</span></h1>
  <span class="badge">v2.0 · Standalone</span>
</div>

<div class="layout">
<div class="sidebar">
  <div class="card">
    <h3>🔍 标的选择</h3>
    <label>标的</label>
    <select id="stock-select" onchange="switchStock()"></select>
    <div style="margin-top:6px"></div>
    <label>回看天数</label>
    <select id="lookback" onchange="redrawAll()">
      <option value="60">60天</option>
      <option value="120">120天</option>
      <option value="250">250天</option>
      <option value="0" selected>全部</option>
    </select>
    <button class="btn-primary" onclick="redrawAll()" style="margin-top:8px;">🔄 刷新图表</button>
  </div>

  <div id="stock-info" class="stock-info" style="padding:4px 8px;font-size:0.75em;"></div>

  <div class="card" id="params-card">
    <h3>⚙️ 指标参数</h3>
    <div id="params-content"></div>
  </div>

  <div class="card">
    <h3>👁️ 显示切换</h3>
    <div id="toggles-content"></div>
  </div>

  <div class="footer" style="border:none;padding:6px 0;">
    🏠 <a href="../../index.html" style="color:var(--accent);">返回首页</a><br>
    数据: AKShare & Tushare Pro | qfq
  </div>
</div>

<div class="main" id="main-area">
  <div id="chart-kline" class="chart-box chart-panel"></div>
  <div id="chart-volume" class="chart-box sub chart-panel"></div>
  <div id="chart-rsi" class="chart-box sub chart-panel"></div>
  <div id="chart-macd" class="chart-box sub chart-panel"></div>
  <div id="chart-atr" class="chart-box sub chart-panel"></div>
  <div id="chart-kdj" class="chart-box sub chart-panel"></div>
  <div id="chart-cci" class="chart-box sub chart-panel"></div>
  <div id="chart-adx" class="chart-box sub chart-panel"></div>
</div>
</div>

<script>
// ═══════════════════════════════════════════════════════════════
// 数据
// ═══════════════════════════════════════════════════════════════
const STOCKS = __STOCKS_DATA_PLACEHOLDER__;
let currentCode = '';
let currentData = [];  // [{date,open,high,low,close,volume},...]

// ═══════════════════════════════════════════════════════════════
// 参数默认值
// ═══════════════════════════════════════════════════════════════
const PARAMS = {
  rsi_period: 14,
  macd_fast: 12, macd_slow: 26, macd_signal: 9,
  bb_period: 20, bb_k: 2.0,
  atr_period: 14,
  kdj_period: 9, kdj_smooth_k: 3, kdj_smooth_d: 3,
  ma_periods: [5, 10, 20, 60],
  cci_period: 20,
  adx_period: 14,
  showRSI: true, showMACD: true, showKDJ: true,
  showCCI: true, showATR: true, showADX: true,
};

// ═══════════════════════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════════════════════
function EMA(data, period) {
  const k = 2 / (period + 1);
  const result = new Array(data.length).fill(null);
  let sum = 0, count = 0;
  for (let i = 0; i < data.length; i++) {
    if (data[i] != null) {
      sum += data[i]; count++;
      if (count === period) result[i] = sum / period;
      else if (count > period) result[i] = data[i] * k + result[i-1] * (1 - k);
    }
  }
  return result;
}

function WilderSmooth(data, period) {
  const k = 1 / period;
  const result = new Array(data.length).fill(null);
  let sum = 0, count = 0;
  let prev = 0;
  for (let i = 0; i < data.length; i++) {
    if (data[i] != null) {
      sum += data[i]; count++;
      if (count === period) { result[i] = sum / period; prev = result[i]; }
      else if (count > period) { result[i] = data[i] * k + prev * (1 - k); prev = result[i]; }
    }
  }
  return result;
}

function SMA(data, period) {
  const result = new Array(data.length).fill(null);
  let sum = 0, count = 0;
  for (let i = 0; i < data.length; i++) {
    if (data[i] != null) {
      sum += data[i]; count++;
      if (count > period) sum -= data[i - period];
      if (count >= period) result[i] = sum / period;
    }
  }
  return result;
}

function StdDev(data, period) {
  const sma = SMA(data, period);
  const result = new Array(data.length).fill(null);
  for (let i = 0; i < data.length; i++) {
    if (sma[i] != null && i >= period - 1) {
      let sumSq = 0, n = 0;
      for (let j = i - period + 1; j <= i; j++) {
        if (data[j] != null) { sumSq += (data[j] - sma[i]) ** 2; n++; }
      }
      result[i] = Math.sqrt(sumSq / n);
    }
  }
  return result;
}

// ═══════════════════════════════════════════════════════════════
// 指标计算 (纯 JS)
// ═══════════════════════════════════════════════════════════════

function calcRSI(closes, period) {
  const gains = new Array(closes.length).fill(0);
  const losses = new Array(closes.length).fill(0);
  for (let i = 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i-1];
    if (diff > 0) gains[i] = diff;
    else losses[i] = -diff;
  }
  const avgGain = WilderSmooth(gains, period);
  const avgLoss = WilderSmooth(losses, period);
  const rsi = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (avgGain[i] != null && avgLoss[i] != null) {
      if (avgLoss[i] === 0) rsi[i] = 100;
      else rsi[i] = 100 - 100 / (1 + avgGain[i] / avgLoss[i]);
    }
  }
  return rsi;
}

function calcMACD(closes, fast, slow, signal) {
  const emaFast = EMA(closes, fast);
  const emaSlow = EMA(closes, slow);
  const dif = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (emaFast[i] != null && emaSlow[i] != null) dif[i] = emaFast[i] - emaSlow[i];
  }
  const dea = EMA(dif.filter(v => v != null).length > signal ? dif : dif.map(v => v||0), signal);
  // 固定: 基于实际 dif 计算
  const dea2 = EMA(dif.map(v => v != null ? v : 0), signal);
  const bar = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (dif[i] != null && dea2[i] != null && !isNaN(dea2[i])) bar[i] = 2 * (dif[i] - dea2[i]);
  }
  return { dif, dea: dea2, bar };
}

function calcBollinger(closes, period, k) {
  const mid = SMA(closes, period);
  const std = StdDev(closes, period);
  const up = new Array(closes.length).fill(null);
  const dn = new Array(closes.length).fill(null);
  const pctB = new Array(closes.length).fill(null);
  const bandwidth = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (mid[i] != null && std[i] != null) {
      up[i] = mid[i] + k * std[i];
      dn[i] = mid[i] - k * std[i];
      bandwidth[i] = (up[i] - dn[i]) / mid[i] * 100;
      pctB[i] = (closes[i] - dn[i]) / (up[i] - dn[i]);
    }
  }
  return { up, mid, dn, bandwidth, pctB };
}

function calcATR(highs, lows, closes, period) {
  const tr = new Array(closes.length).fill(null);
  tr[0] = highs[0] - lows[0];
  for (let i = 1; i < closes.length; i++) {
    tr[i] = Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i-1]),
      Math.abs(lows[i] - closes[i-1])
    );
  }
  return WilderSmooth(tr, period);
}

function calcKDJ(highs, lows, closes, period, smoothK, smoothD) {
  const rsv = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (i >= period - 1) {
      let hh = -Infinity, ll = Infinity;
      for (let j = i - period + 1; j <= i; j++) {
        hh = Math.max(hh, highs[j]);
        ll = Math.min(ll, lows[j]);
      }
      const range = hh - ll;
      rsv[i] = range > 0 ? (closes[i] - ll) / range * 100 : 50;
    }
  }
  const k_line = EMA(rsv.map(v => v != null ? v : 50), smoothK);
  const d_line = EMA(k_line.map(v => v != null ? v : 50), smoothD);
  const j_line = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (k_line[i] != null && d_line[i] != null) j_line[i] = 3 * k_line[i] - 2 * d_line[i];
  }
  return { k: k_line, d: d_line, j: j_line };
}

function calcCCI(highs, lows, closes, period) {
  const tp = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) tp[i] = (highs[i] + lows[i] + closes[i]) / 3;
  const ma = SMA(tp, period);
  const cci = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (ma[i] != null && i >= period - 1) {
      let sumDev = 0;
      for (let j = i - period + 1; j <= i; j++) sumDev += Math.abs(tp[j] - ma[i]);
      const md = sumDev / period;
      cci[i] = md > 0 ? (tp[i] - ma[i]) / (0.015 * md) : 0;
    }
  }
  return cci;
}

function calcADX(highs, lows, closes, period) {
  const tr = new Array(closes.length).fill(null);
  tr[0] = highs[0] - lows[0];
  const plusDM = new Array(closes.length).fill(0);
  const minusDM = new Array(closes.length).fill(0);
  for (let i = 1; i < closes.length; i++) {
    tr[i] = Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i-1]), Math.abs(lows[i] - closes[i-1]));
    const upMove = highs[i] - highs[i-1];
    const downMove = lows[i-1] - lows[i];
    if (upMove > downMove && upMove > 0) plusDM[i] = upMove;
    else plusDM[i] = 0;
    if (downMove > upMove && downMove > 0) minusDM[i] = downMove;
    else minusDM[i] = 0;
  }
  const atr = WilderSmooth(tr, period);
  const sPDM = WilderSmooth(plusDM, period);
  const sMDM = WilderSmooth(minusDM, period);
  const pdi = new Array(closes.length).fill(null);
  const mdi = new Array(closes.length).fill(null);
  const adx = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (atr[i] != null && atr[i] > 0) {
      pdi[i] = sPDM[i] / atr[i] * 100;
      mdi[i] = sMDM[i] / atr[i] * 100;
    }
  }
  const dx = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    if (pdi[i] != null && mdi[i] != null && (pdi[i] + mdi[i]) > 0) {
      dx[i] = Math.abs(pdi[i] - mdi[i]) / (pdi[i] + mdi[i]) * 100;
    }
  }
  const adxRaw = WilderSmooth(dx.filter(v => v != null).length >= period ? dx : dx.map(v => v||0), period);
  // 重新映射: 用wilder平滑的值
  const adx2 = WilderSmooth(dx.map(v => v != null ? v : 0), period);
  return { adx: adx2, pdi, mdi };
}

// ═══════════════════════════════════════════════════════════════
// 数据预处理 & 指标计算
// ═══════════════════════════════════════════════════════════════

function getFilteredData() {
  const lookback = parseInt(document.getElementById('lookback').value);
  const raw = STOCKS[currentCode].data;
  let slice = raw;
  if (lookback > 0) slice = raw.slice(-lookback);
  return slice.map(r => ({
    date: r[0], open: r[1], high: r[2], low: r[3], close: r[4], volume: r[5]
  }));
}

function computeAll(data) {
  const closes = data.map(d => d.close);
  const highs = data.map(d => d.high);
  const lows = data.map(d => d.low);
  const volumes = data.map(d => d.volume);
  const dates = data.map(d => d.date);

  const p = PARAMS;
  return {
    dates, closes, highs, lows, volumes,
    rsi: calcRSI(closes, p.rsi_period),
    macd: calcMACD(closes, p.macd_fast, p.macd_slow, p.macd_signal),
    bb: calcBollinger(closes, p.bb_period, p.bb_k),
    atr: calcATR(highs, lows, closes, p.atr_period),
    kdj: calcKDJ(highs, lows, closes, p.kdj_period, p.kdj_smooth_k, p.kdj_smooth_d),
    mas: (() => {
      const result = {};
      p.ma_periods.forEach(pp => { result[pp] = SMA(closes, pp); });
      return result;
    })(),
    cci: calcCCI(highs, lows, closes, p.cci_period),
    adx: calcADX(highs, lows, closes, p.adx_period),
  };
}

// ═══════════════════════════════════════════════════════════════
// ECharts 图表
// ═══════════════════════════════════════════════════════════════

const charts = {};
['kline','volume','rsi','macd','kdj','cci','atr','adx'].forEach(id => {
  const dom = document.getElementById('chart-' + id);
  if (dom) charts[id] = echarts.init(dom);
});

function chartTitle(text) {
  return {
    text, left: 'center', top: 2,
    textStyle: { fontSize: 12, fontWeight: 600, color: '#2d3436' },
  };
}

function makeGrid(extraTop = 0) {
  return { left: 70, right: 30, top: 50 + extraTop, bottom: 30 };
}

function dateAxis(dates) {
  return { type: 'category', data: dates, axisLabel: { fontSize: 10, formatter: v => v.slice(5), color: '#636e72' },
    axisLine: { lineStyle: { color: '#dfe6e9' } }, splitLine: { show: false } };
}

function priceAxis(name) {
  return { type: 'value', name, nameTextStyle: { fontSize: 10, color: '#636e72' },
    axisLabel: { fontSize: 10, color: '#636e72' }, splitLine: { lineStyle: { color: '#f0f0f0' } } };
}

function makeCandlestickSeries(ohlc) {
  return {
    name: 'K线', type: 'candlestick',
    data: ohlc.map((d,i) => [d.open, d.close, d.low, d.high]),
    itemStyle: { color: '#ef5350', color0: '#26a69a', borderColor: '#ef5350', borderColor0: '#26a69a' },
  };
}

function makeLineSeries(name, data, color, yAxisIndex = 0, lineStyle = null) {
  const s = { name, type: 'line', data, yAxisIndex, symbol: 'none',
    lineStyle: { color, width: 1 }, itemStyle: { color } };
  if (lineStyle) s.lineStyle = { ...s.lineStyle, ...lineStyle };
  return s;
}

function makeBarSeries(name, data, colors, yAxisIndex = 0) {
  return { name, type: 'bar', data: data.map((v,i) => ({ value: v, itemStyle: { color: v >= 0 ? colors[0] : colors[1] } })),
    yAxisIndex, barWidth: '60%' };
}

// --- K 线主图 (布林带 + MA) ---
function drawKline(d) {
  const s = STOCKS[currentCode];
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — K线 · 布林带 · 移动均线`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: priceAxis('价格'),
    series: [ makeCandlestickSeries(d.data) ],
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K线'], top: 26, right: 10, textStyle: { color: '#636e72', fontSize: 10 } },
  };

  // 布林带
  if (d.bb.up.some(v => v != null)) {
    opt.series.push(makeLineSeries('上轨', d.bb.up, '#7f7f7f', 0, { type: 'dashed', width: 0.7 }));
    opt.series.push(makeLineSeries('中轨', d.bb.mid, '#ff9800', 0));
    opt.series.push(makeLineSeries('下轨', d.bb.dn, '#7f7f7f', 0, { type: 'dashed', width: 0.7 }));
    opt.legend.data.push('上轨','中轨','下轨');
    opt.series.push({
      name: '布林带区域', type: 'line', data: d.bb.up,
      lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(127,127,127,0.05)' },
      symbol: 'none', stack: 'bb', silent: true
    });
  }

  // MA 线 (仅显示 MA20 和 MA60)
  [20, 60].forEach(p => {
    if (d.mas[p] && d.mas[p].some(v => v != null)) {
      opt.series.push(makeLineSeries(`MA${p}`, d.mas[p], p === 20 ? '#ff9800' : '#4caf50', 0));
      opt.legend.data.push(`MA${p}`);
    }
  });

  charts.kline.setOption(opt, true);
}

// --- 成交量 ---
function drawVolume(d) {
  const s = STOCKS[currentCode];
  const colors = d.data.map(dd => dd.close >= dd.open ? '#ef5350' : '#26a69a');
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — 成交量`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: { type: 'value', name: '量(股)', nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10, formatter: v => v >= 1e8 ? (v/1e8).toFixed(1)+'亿' : (v/1e4).toFixed(0)+'万' },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [{
      name: '成交量', type: 'bar',
      data: d.volumes.map((v,i) => ({ value: v, itemStyle: { color: colors[i] } })),
      barWidth: '60%'
    }],
    tooltip: { trigger: 'axis' },
  };
  charts.volume.setOption(opt, true);
}

// --- RSI ---
function drawRSI(d) {
  if (!PARAMS.showRSI) { document.getElementById('chart-rsi').style.display = 'none'; return; }
  document.getElementById('chart-rsi').style.display = '';
  const s = STOCKS[currentCode];
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — RSI (周期=${PARAMS.rsi_period})`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: { type: 'value', name: 'RSI', min: 0, max: 100,
      axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      makeLineSeries('RSI', d.rsi, '#ab47bc'),
      { name: '70线', type: 'line', data: new Array(d.dates.length).fill(70),
        lineStyle: { color: '#ef5350', type: 'dashed', width: 0.6 }, symbol: 'none', silent: true },
      { name: '30线', type: 'line', data: new Array(d.dates.length).fill(30),
        lineStyle: { color: '#26a69a', type: 'dashed', width: 0.6 }, symbol: 'none', silent: true },
      { name: '50线', type: 'line', data: new Array(d.dates.length).fill(50),
        lineStyle: { color: '#666', type: 'solid', width: 0.3 }, symbol: 'none', silent: true },
    ],
    tooltip: { trigger: 'axis' },
    legend: { show: true, data: ['RSI'], top: 26, right: 10, textStyle: { color: '#636e72', fontSize: 10 } },
  };
  charts.rsi.setOption(opt, true);
}

// --- MACD ---
function drawMACD(d) {
  if (!PARAMS.showMACD) { document.getElementById('chart-macd').style.display = 'none'; return; }
  document.getElementById('chart-macd').style.display = '';
  const s = STOCKS[currentCode];
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — MACD (${PARAMS.macd_fast},${PARAMS.macd_slow},${PARAMS.macd_signal})`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: { type: 'value', name: 'MACD', axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      makeLineSeries('DIF', d.macd.dif, '#42a5f5'),
      makeLineSeries('DEA', d.macd.dea, '#ff9800'),
      makeBarSeries('BAR', d.macd.bar, ['#ef5350', '#26a69a']),
      { name: '零轴', type: 'line', data: new Array(d.dates.length).fill(0),
        lineStyle: { color: '#b2bec3', width: 0.4 }, symbol: 'none', silent: true },
    ],
    tooltip: { trigger: 'axis' },
    legend: { show: true, data: ['DIF','DEA','BAR'], top: 26, right: 10, textStyle: { color: '#636e72', fontSize: 10 } },
  };
  charts.macd.setOption(opt, true);
}

// --- KDJ ---
function drawKDJ(d) {
  if (!PARAMS.showKDJ) { document.getElementById('chart-kdj').style.display = 'none'; return; }
  document.getElementById('chart-kdj').style.display = '';
  const s = STOCKS[currentCode];
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — KDJ (${PARAMS.kdj_period},${PARAMS.kdj_smooth_k},${PARAMS.kdj_smooth_d})`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: { type: 'value', name: 'KDJ', axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      makeLineSeries('K', d.kdj.k, '#42a5f5'),
      makeLineSeries('D', d.kdj.d, '#ff9800'),
      makeLineSeries('J', d.kdj.j, '#ef5350', 0, { type: 'dashed', width: 0.8 }),
      { name: '80线', type: 'line', data: new Array(d.dates.length).fill(80),
        lineStyle: { color: '#ef5350', type: 'dashed', width: 0.5 }, symbol: 'none', silent: true },
      { name: '20线', type: 'line', data: new Array(d.dates.length).fill(20),
        lineStyle: { color: '#26a69a', type: 'dashed', width: 0.5 }, symbol: 'none', silent: true },
    ],
    tooltip: { trigger: 'axis' },
    legend: { show: true, data: ['K','D','J'], top: 26, right: 10, textStyle: { color: '#636e72', fontSize: 10 } },
  };
  charts.kdj.setOption(opt, true);
}

// --- CCI ---
function drawCCI(d) {
  if (!PARAMS.showCCI) { document.getElementById('chart-cci').style.display = 'none'; return; }
  document.getElementById('chart-cci').style.display = '';
  const s = STOCKS[currentCode];
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — CCI (周期=${PARAMS.cci_period})`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: { type: 'value', name: 'CCI', axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      makeLineSeries('CCI', d.cci, '#42a5f5'),
      { name: '+100线', type: 'line', data: new Array(d.dates.length).fill(100),
        lineStyle: { color: '#ef5350', type: 'dashed', width: 0.6 }, symbol: 'none', silent: true },
      { name: '-100线', type: 'line', data: new Array(d.dates.length).fill(-100),
        lineStyle: { color: '#26a69a', type: 'dashed', width: 0.6 }, symbol: 'none', silent: true },
      { name: '0线', type: 'line', data: new Array(d.dates.length).fill(0),
        lineStyle: { color: '#b2bec3', width: 0.3 }, symbol: 'none', silent: true },
    ],
    tooltip: { trigger: 'axis' },
    legend: { show: true, data: ['CCI'], top: 26, right: 10, textStyle: { color: '#636e72', fontSize: 10 } },
  };
  charts.cci.setOption(opt, true);
}

// --- ATR ---
function drawATR(d) {
  if (!PARAMS.showATR) { document.getElementById('chart-atr').style.display = 'none'; return; }
  document.getElementById('chart-atr').style.display = '';
  const s = STOCKS[currentCode];
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — ATR (周期=${PARAMS.atr_period})`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: { type: 'value', name: 'ATR', axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [ makeLineSeries('ATR', d.atr, '#ab47bc') ],
    tooltip: { trigger: 'axis' },
    legend: { show: true, data: ['ATR'], top: 26, right: 10, textStyle: { color: '#636e72', fontSize: 10 } },
  };
  charts.atr.setOption(opt, true);
}

// --- ADX ---
function drawADX(d) {
  if (!PARAMS.showADX) { document.getElementById('chart-adx').style.display = 'none'; return; }
  document.getElementById('chart-adx').style.display = '';
  const s = STOCKS[currentCode];
  const opt = {
    title: chartTitle(`${s.name} (${s.code}) — ADX/+DI/−DI (周期=${PARAMS.adx_period})`),
    grid: makeGrid(),
    xAxis: dateAxis(d.dates),
    yAxis: { type: 'value', name: 'ADX/DI', axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      makeLineSeries('ADX', d.adx.adx, '#ef5350', 0, { width: 1.2 }),
      makeLineSeries('+DI', d.adx.pdi, '#26a69a'),
      makeLineSeries('-DI', d.adx.mdi, '#42a5f5'),
      { name: '25线', type: 'line', data: new Array(d.dates.length).fill(25),
        lineStyle: { color: '#b2bec3', type: 'dashed', width: 0.5 }, symbol: 'none', silent: true },
    ],
    tooltip: { trigger: 'axis' },
    legend: { show: true, data: ['ADX','+DI','-DI'], top: 26, right: 10, textStyle: { color: '#636e72', fontSize: 10 } },
  };
  charts.adx.setOption(opt, true);
}

// ═══════════════════════════════════════════════════════════════
// 主流程
// ═══════════════════════════════════════════════════════════════

function redrawAll() {
  if (!currentCode) return;
  const rawData = getFilteredData();
  const ind = computeAll(rawData);
  // 附加原始数据给 candle 用
  ind.data = rawData;

  drawKline(ind);
  drawVolume(ind);
  drawRSI(ind);
  drawMACD(ind);
  drawKDJ(ind);
  drawCCI(ind);
  drawATR(ind);
  drawADX(ind);
  updateStockInfo(rawData);

  // resize
  Object.values(charts).forEach(c => c && c.resize());
}

function updateStockInfo(data) {
  if (data.length < 2) return;
  const first = data[0].close, last = data[data.length-1].close;
  const chg = ((last - first) / first * 100).toFixed(2);
  const s = STOCKS[currentCode];
  document.getElementById('stock-info').innerHTML =
    `<span>${s.code} ${s.name} (${s.market}) | ${data[0].date} ~ ${data[data.length-1].date} | ${data.length}条</span>
     <span class="chg ${chg >= 0 ? 'up' : 'down'}">区间涨跌: ${chg >= 0 ? '+' : ''}${chg}%</span>`;
}

function switchStock() {
  currentCode = document.getElementById('stock-select').value;
  redrawAll();
}

// --- 参数面板 (侧边栏) ---
function buildParamsBar() {
  const paramsDiv = document.getElementById('params-content');
  const togglesDiv = document.getElementById('toggles-content');
  paramsDiv.innerHTML = '';
  togglesDiv.innerHTML = '';

  function slider(label, key, min, max, step, def) {
    const row = document.createElement('div'); row.className = 'param-row';
    row.innerHTML = `<span class="lbl">${label}</span>
      <input type="range" min="${min}" max="${max}" step="${step}" value="${def}"
        oninput="this.nextElementSibling.value=this.value; PARAMS.${key}=${step<1?'parseFloat':'parseInt'}(this.value);redrawAll()">
      <input type="number" value="${def}" min="${min}" max="${max}" step="${step}"
        onchange="this.previousElementSibling.value=this.value; PARAMS.${key}=${step<1?'parseFloat':'parseInt'}(this.value);redrawAll()">`;
    paramsDiv.appendChild(row);
  }

  function section(title, color) {
    const h = document.createElement('div');
    h.style.cssText = `font-size:0.78em;font-weight:600;color:${color};margin-top:8px;margin-bottom:2px;`;
    h.textContent = title;
    paramsDiv.appendChild(h);
  }

  function checkbox(label, key) {
    const row = document.createElement('div'); row.className = 'toggle-row';
    const chk = key ? PARAMS[key] : true;
    row.innerHTML = `<label class="toggle-row"><input type="checkbox" ${chk?'checked':''}
      onchange="PARAMS.${key}=this.checked;redrawAll()"> ${label}</label>`;
    togglesDiv.appendChild(row);
  }

  section('📈 RSI', '#ab47bc');
  slider('周期', 'rsi_period', 2, 30, 1, PARAMS.rsi_period);

  section('📉 MACD', '#42a5f5');
  slider('快线', 'macd_fast', 2, 50, 1, PARAMS.macd_fast);
  slider('慢线', 'macd_slow', 5, 100, 1, PARAMS.macd_slow);
  slider('信号', 'macd_signal', 2, 30, 1, PARAMS.macd_signal);

  section('📊 布林带', '#ff9800');
  slider('周期', 'bb_period', 5, 60, 1, PARAMS.bb_period);
  slider('倍数', 'bb_k', 1.0, 3.0, 0.1, PARAMS.bb_k);

  section('📐 ATR', '#ab47bc');
  slider('周期', 'atr_period', 2, 50, 1, PARAMS.atr_period);

  section('🎯 KDJ', '#ef5350');
  slider('N', 'kdj_period', 3, 30, 1, PARAMS.kdj_period);
  slider('K平滑', 'kdj_smooth_k', 2, 10, 1, PARAMS.kdj_smooth_k);
  slider('D平滑', 'kdj_smooth_d', 2, 10, 1, PARAMS.kdj_smooth_d);

  section('📏 CCI', '#42a5f5');
  slider('周期', 'cci_period', 5, 50, 1, PARAMS.cci_period);

  section('📶 ADX', '#ef5350');
  slider('周期', 'adx_period', 5, 50, 1, PARAMS.adx_period);

  // 显示/隐藏复选框
  checkbox('RSI 指标', 'showRSI');
  checkbox('MACD 指标', 'showMACD');
  checkbox('KDJ 指标', 'showKDJ');
  checkbox('CCI 指标', 'showCCI');
  checkbox('ATR 指标', 'showATR');
  checkbox('ADX 指标', 'showADX');
}

function init() {
  // 填充下拉菜单
  const sel = document.getElementById('stock-select');
  Object.keys(STOCKS).forEach(code => {
    const s = STOCKS[code];
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = `${code} ${s.name} (${s.market}) — ${s.count}条`;
    sel.appendChild(opt);
  });
  currentCode = Object.keys(STOCKS)[0];

  buildParamsBar();
  redrawAll();

  // 窗口 resize
  window.addEventListener('resize', () => {
    Object.values(charts).forEach(c => c && c.resize());
  });
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>'''


if __name__ == "__main__":
    build_html()
