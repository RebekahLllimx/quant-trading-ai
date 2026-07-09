#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task4: 将 CSV 数据序列化为 JSON, 嵌入看板 HTML
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
    ('600519', '贵州茅台', 'A股'),
    ('601318', '中国平安', 'A股'),
    ('300750', '宁德时代', 'A股'),
    ('002594', '比亚迪', 'A股'),
    ('000001', '平安银行', 'A股'),
    ('00700', '腾讯控股', '港股'),
    ('09988', '阿里巴巴', '港股'),
    ('03690', '美团', '港股'),
    ('00388', '香港交易所', '港股'),
    ('00941', '中国移动', '港股'),
]


def build_stocks_json():
    """将 10 只股票的 OHLCV 数据序列化为 JSON"""
    stocks = {}
    for code, name, market in STOCKS:
        try:
            df = load_stock(code, name, market)
            # 保留核心列
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
            print(f'  ✅ {code} {name} ({market}): {len(data)} 条')
        except Exception as e:
            print(f'  ⚠️ {code} {name}: {e}')

    return stocks


def main():
    print('=' * 60)
    print('  Task4: 准备看板数据')
    print('=' * 60)

    stocks = build_stocks_json()
    stocks_json = json.dumps(stocks, ensure_ascii=False)

    # 读取 HTML 模板并注入数据
    template_path = os.path.join(DASHBOARD_DIR, 'template.html')
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('/* __STOCKS_DATA_PLACEHOLDER__ */',
                           f'const STOCKS = {stocks_json};')
    else:
        print('  ⚠️ 未找到模板文件, 请先创建 template.html')
        return

    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f'\n✅ 看板已生成: {OUTPUT_FILE} ({file_size/1024:.0f} KB)')
    print('=' * 60)


if __name__ == '__main__':
    main()
