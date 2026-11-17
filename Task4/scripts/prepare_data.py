#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task4: will CSV Data serialized JSON, Embed Dashboard HTML
"""

import os, sys, json
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turtle_strategy import load_stock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
DASHBOARD_DIR = os.path.join(BASE_DIR, 'dashboard')
OUTPUT_FILE = os.path.join(DASHBOARD_DIR, 'index.html')

STOCKS = [
    ('600519', 'Kweichow Moutai', 'A-share'),
    ('601318', 'Ping An of China', 'A-share'),
    ('300750', 'CATL', 'A-share'),
    ('002594', 'BYD', 'A-share'),
    ('000001', 'Ping An Bank', 'A-share'),
    ('00700', 'Tencent Holdings', 'Hong Kong equities'),
    ('09988', 'Alibaba', 'Hong Kong equities'),
    ('03690', 'Meituan', 'Hong Kong equities'),
    ('00388', 'Hong Kong Exchange', 'Hong Kong equities'),
    ('00941', 'China Mobile', 'Hong Kong equities'),
]


def build_stocks_json():
    """will 10 Only the stock OHLCV Data serialized JSON"""
    stocks = {}
    for code, name, market in STOCKS:
        try:
            df = load_stock(code, name, market)
            # Keep Core Columns
            df = df[['Date', 'Open', 'Close', 'High', 'Low', 'Volume']].copy()
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            data = df.values.tolist()
            stocks[code] = {
                'code': code,
                'name': name,
                'market': market,
                'data': data,  # [[Date, Open, Close, High, Low, Volume], ...]
                'dateStart': data[0][0] if data else '',
                'dateEnd': data[-1][0] if data else '',
                'records': len(data),
            }
            print(f'   {code} {name} ({market}): {len(data)} item')
        except Exception as e:
            print(f'   {code} {name}: {e}')

    return stocks


def main():
    print('=' * 60)
    print('  Task4: Prepare dashboard data')
    print('=' * 60)

    stocks = build_stocks_json()
    stocks_json = json.dumps(stocks, ensure_ascii=False)

    # Read HTML Template and inject data
    template_path = os.path.join(DASHBOARD_DIR, 'template.html')
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('/* __STOCKS_DATA_PLACEHOLDER__ */',
                           f'const STOCKS = {stocks_json};')
    else:
        print('   Template file not found, Please create first template.html')
        return

    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f'\n Dashboard generated: {OUTPUT_FILE} ({file_size/1024:.0f} KB)')
    print('=' * 60)


if __name__ == '__main__':
    main()
