#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源建设看板 —— 后端服务
启动: python server.py
浏览器: http://localhost:8765
"""

import json
import io
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
import pandas as pd
import numpy as np

# 尝试从 config.py 读取 Token（回退方案）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from config import TUSHARE_TOKEN as _CONFIG_TOKEN
except ImportError:
    _CONFIG_TOKEN = ""

app = Flask(__name__)

# ── 数据源配置 ──
DATA_SOURCES = {
    "akshare": {
        "name": "AKShare",
        "type": "免费开源",
        "status": "active",
        "desc": "国内开源金融数据接口，覆盖A股/港股/期货/宏观经济，无需注册",
        "markets": ["A股", "港股"],
        "rate_limit": "无限制",
    },
    "tushare": {
        "name": "Tushare Pro",
        "type": "免费+积分制",
        "status": "active",
        "desc": "国内知名金融数据平台，数据质量高，需注册获取Token，积分决定权限",
        "markets": ["A股", "港股"],
        "rate_limit": "视积分等级",
        "token": os.environ.get("TUSHARE_TOKEN", _CONFIG_TOKEN),
    },
}

# ── 工具函数 ──
def fetch_akshare(code, market, start, end):
    import akshare as ak
    if market == 'A股':
        df = ak.stock_zh_a_hist(symbol=code, period='daily',
                                start_date=start, end_date=end, adjust='qfq')
        df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close',
                                '最高': 'high', '最低': 'low', '成交量': 'volume',
                                '成交额': 'amount', '涨跌幅': 'pct_chg', '涨跌额': 'change',
                                '换手率': 'turnover', '振幅': 'amplitude', '股票代码': 'ts_code'})
    else:
        df = ak.stock_hk_hist(symbol=code, period='daily',
                              start_date=start, end_date=end, adjust='qfq')
        df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close',
                                '最高': 'high', '最低': 'low', '成交量': 'volume',
                                '成交额': 'amount', '涨跌幅': 'pct_chg', '涨跌额': 'change',
                                '换手率': 'turnover', '振幅': 'amplitude'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

def fetch_tushare(code, market, start, end):
    import tushare as ts
    token = DATA_SOURCES['tushare']['token']
    ts.set_token(token)
    pro = ts.pro_api()
    suffix = '.SH' if code.startswith(('6','9')) else '.SZ'
    ts_code = code + suffix

    df = pro.daily(ts_code=ts_code, start_date=start, end_date=end)
    df = df.rename(columns={'trade_date': 'date', 'ts_code': 'ts_code',
                            'open': 'open', 'high': 'high', 'low': 'low',
                            'close': 'close', 'pre_close': 'pre_close',
                            'change': 'change', 'pct_chg': 'pct_chg',
                            'vol': 'volume', 'amount': 'amount'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

# ── API 路由 ──

@app.route('/')
def index():
    return send_file('dashboard.html')

@app.route('/api/sources')
def get_sources():
    """获取所有数据源状态"""
    sources = {}
    for key, cfg in DATA_SOURCES.items():
        sources[key] = {
            'name': cfg['name'],
            'type': cfg['type'],
            'status': cfg['status'],
            'desc': cfg['desc'],
            'markets': cfg['markets'],
            'rate_limit': cfg['rate_limit'],
        }
    return jsonify(sources)

@app.route('/api/fetch')
def fetch_data():
    """拉取股票数据"""
    code = request.args.get('code', '000001')
    market = request.args.get('market', 'A股')
    source = request.args.get('source', 'akshare')
    start = request.args.get('start', (datetime.now() - timedelta(days=365)).strftime('%Y%m%d'))
    end = request.args.get('end', datetime.now().strftime('%Y%m%d'))

    try:
        # ── 输入校验：拦截市场与代码不匹配 ──
        code = code.strip()
        is_a = ('a' in market.lower()) or ('A股' in market)
        is_hk = ('港' in market) or ('hk' in market.lower())

        if is_a and (not code.isdigit() or len(code) != 6):
            return jsonify({'error': f'⚠️ A股代码需6位数字，您输入了「{code}」。请确认市场是否选错。'}), 400
        if is_hk:
            code = code.zfill(5)
            if not code.isdigit() or len(code) != 5:
                return jsonify({'error': f'⚠️ 港股代码需5位数字，您输入了「{code}」。请确认市场是否选错。'}), 400

        if source == 'tushare' and is_a:
            df = fetch_tushare(code, market, start, end)
        else:
            df = fetch_akshare(code, market, start, end)

        if df.empty:
            return jsonify({'error': '未获取到数据，请检查代码'}), 400

        # 计算指标
        close = df['close']
        chg = float((close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100)
        rets = close.pct_change().dropna()
        ann_vol = float(rets.std() * np.sqrt(252) * 100)
        max_dd = float(((close.cummax() - close) / close.cummax()).max() * 100)
        win_rate = float((rets > 0).sum() / len(rets) * 100)

        # 准备OHLC数据
        ohlc = []
        for _, row in df.iterrows():
            ohlc.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'open': round(float(row['open']), 2),
                'high': round(float(row['high']), 2),
                'low': round(float(row['low']), 2),
                'close': round(float(row['close']), 2),
                'volume': float(row['volume']),
            })

        return jsonify({
            'code': code,
            'market': market,
            'source': source,
            'records': len(df),
            'start_date': df['date'].min().strftime('%Y-%m-%d'),
            'end_date': df['date'].max().strftime('%Y-%m-%d'),
            'metrics': {
                'chg': round(chg, 2),
                'ann_vol': round(ann_vol, 2),
                'max_dd': round(max_dd, 2),
                'win_rate': round(win_rate, 1),
                'start_price': round(float(close.iloc[0]), 2),
                'end_price': round(float(close.iloc[-1]), 2),
                'max_price': round(float(close.max()), 2),
                'min_price': round(float(close.min()), 2),
                'avg_volume': round(float(df['volume'].mean()), 0),
            },
            'ohlc': ohlc,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export')
def export_csv():
    """导出CSV"""
    code = request.args.get('code', '000001')
    market = request.args.get('market', 'A股')
    source = request.args.get('source', 'akshare')
    start = request.args.get('start', (datetime.now() - timedelta(days=365)).strftime('%Y%m%d'))
    end = request.args.get('end', datetime.now().strftime('%Y%m%d'))

    try:
        if source == 'tushare' and market == 'A股':
            df = fetch_tushare(code, market, start, end)
        else:
            df = fetch_akshare(code, market, start, end)

        buf = io.StringIO()
        df.to_csv(buf, index=False, encoding='utf-8-sig')
        buf.seek(0)
        return send_file(
            io.BytesIO(buf.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{code}_{market}_{source}_daily.csv',
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 55)
    print("  📈 数据源建设看板")
    print("  浏览器打开: http://localhost:8765")
    print("=" * 55)
    app.run(host='0.0.0.0', port=8765, debug=False)
