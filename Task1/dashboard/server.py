#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Source Construction Dashboard  -  -  Backend Service
Start: python server.py
browser: http://localhost:8765
"""

import json
import io
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
import pandas as pd
import numpy as np

# Try from config.py Read Token (Fallback plan)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
try:
    from config import TUSHARE_TOKEN as _CONFIG_TOKEN
except ImportError:
    _CONFIG_TOKEN = ""

app = Flask(__name__)

#  Data Source Configuration
DATA_SOURCES = {
    "akshare": {
        "name": "AKShare",
        "type": "Free Open Source",
        "status": "active",
        "desc": "Domestic open source financial data interface, CoverageA-share/Hong Kong equities/Futures/Macroeconomic, No need to register",
        "markets": ["A-share", "Hong Kong equities"],
        "rate_limit": "Unlimited",
    },
    "tushare": {
        "name": "Tushare Pro",
        "type": "Free+Points system",
        "status": "active",
        "desc": "Domestic well-known financial data platform, High data quality, Registration required to obtainToken, Points to determine authority",
        "markets": ["A-share", "Hong Kong equities"],
        "rate_limit": "visual integral grade",
        "token": os.environ.get("TUSHARE_TOKEN", _CONFIG_TOKEN),
    },
}

#  Tool Functions
def fetch_akshare(code, market, start, end):
    import akshare as ak
    if market == 'A-share':
        df = ak.stock_zh_a_hist(symbol=code, period='daily',
                                start_date=start, end_date=end, adjust='qfq')
        df = df.rename(columns={'Date': 'date', 'Opening': 'open', 'Close of trading': 'close',
                                'highest': 'high', 'Minimum': 'low', 'Trading volume': 'volume',
                                'Turnover': 'amount', 'Return': 'pct_chg', 'Price change': 'change',
                                'Turnover rate': 'turnover', 'Amplitude': 'amplitude', 'Symbol': 'ts_code'})
    else:
        df = ak.stock_hk_hist(symbol=code, period='daily',
                              start_date=start, end_date=end, adjust='qfq')
        df = df.rename(columns={'Date': 'date', 'Opening': 'open', 'Close of trading': 'close',
                                'highest': 'high', 'Minimum': 'low', 'Trading volume': 'volume',
                                'Turnover': 'amount', 'Return': 'pct_chg', 'Price change': 'change',
                                'Turnover rate': 'turnover', 'Amplitude': 'amplitude'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

def fetch_tushare(code, market, start, end):
    import tushare as ts
    token = DATA_SOURCES['tushare']['token']
    if not token:
        raise RuntimeError('TUSHARE_TOKEN Not configured')
    ts.set_token(token)
    if market == 'Hong Kong equities':
        pro = ts.pro_api()
        ts_code = code.zfill(5) + '.HK'
        df = pro.hk_daily_adj(ts_code=ts_code, start_date=start, end_date=end)
        pct_col = 'pct_change'
    else:
        suffix = '.SH' if code.startswith(('5','6','9')) else '.SZ'
        ts_code = code + suffix
        df = ts.pro_bar(ts_code=ts_code, start_date=start, end_date=end,
                        adj='qfq', freq='D')
        pct_col = 'pct_chg'
    if df is None or df.empty:
        raise ValueError('Tushare No data returned')
    df = df.rename(columns={'trade_date': 'date', 'ts_code': 'ts_code',
                            'open': 'open', 'high': 'high', 'low': 'low',
                            'close': 'close', 'pre_close': 'pre_close',
                            'change': 'change', pct_col: 'pct_chg',
                            'vol': 'volume', 'amount': 'amount'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df


def fetch_with_fallback(code, market, start, end, source):
    """Use Tushare when requested and fall back to AKShare on any failure."""
    if source in ('tushare', 'auto'):
        try:
            return fetch_tushare(code, market, start, end), 'tushare'
        except Exception as exc:
            app.logger.warning('Tushare failed for %s: %s; using AKShare', code, exc)
    return fetch_akshare(code, market, start, end), 'akshare'

#  API Routing

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(__file__), 'index.html'))

@app.route('/api/sources')
def get_sources():
    """Get all data source status"""
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
    """Pull stock data"""
    code = request.args.get('code', '000001')
    market = request.args.get('market', 'A-share')
    source = request.args.get('source', 'auto')
    start = request.args.get('start', (datetime.now() - timedelta(days=365)).strftime('%Y%m%d'))
    end = request.args.get('end', datetime.now().strftime('%Y%m%d'))

    try:
        #  Input validation: The intercept market does not match the code
        code = code.strip()
        is_a = ('a' in market.lower()) or ('A-share' in market)
        is_hk = ('Hong Kong' in market) or ('hk' in market.lower())

        if is_a and (not code.isdigit() or len(code) != 6):
            return jsonify({'error': f' ASymbol required6digit, You entered{code}. Please confirm whether the market is wrong.. '}), 400
        if is_hk:
            code = code.zfill(5)
            if not code.isdigit() or len(code) != 5:
                return jsonify({'error': f' Hong Kong Stock Code Required5digit, You entered{code}. Please confirm whether the market is wrong.. '}), 400

        df, actual_source = fetch_with_fallback(code, market, start, end, source)

        if df.empty:
            return jsonify({'error': 'No data retrieved, Please check the code'}), 400

        # Calculated metric
        close = df['close']
        chg = float((close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100)
        rets = close.pct_change().dropna()
        ann_vol = float(rets.std() * np.sqrt(252) * 100)
        max_dd = float(((close.cummax() - close) / close.cummax()).max() * 100)
        win_rate = float((rets > 0).sum() / len(rets) * 100)

        # PrepareOHLCData
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
            'source': actual_source,
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
    """ExportCSV"""
    code = request.args.get('code', '000001')
    market = request.args.get('market', 'A-share')
    source = request.args.get('source', 'auto')
    start = request.args.get('start', (datetime.now() - timedelta(days=365)).strftime('%Y%m%d'))
    end = request.args.get('end', datetime.now().strftime('%Y%m%d'))

    try:
        df, actual_source = fetch_with_fallback(code, market, start, end, source)

        buf = io.StringIO()
        df.to_csv(buf, index=False, encoding='utf-8-sig')
        buf.seek(0)
        return send_file(
            io.BytesIO(buf.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{code}_{market}_{actual_source}_daily.csv',
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 55)
    print("   Data Source Construction Dashboard")
    print("  Open in browser: http://localhost:8765")
    print("=" * 55)
    app.run(host='0.0.0.0', port=8765, debug=False)
