#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task3 Phase 1: 将 CSV 数据序列化为 JSON，供 HTML 看板嵌入使用
输出: Task3/dashboard/data.json (内嵌到 index.html 的 STOCKS 对象)
"""

import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'dashboard')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'data.json')

# 需要排除的非标的数据文件
EXCLUDE = [
    '_embedded_data.json',
    'multi_stock_summary.csv',
    'AH_summary.csv',
]


def load_all_stocks():
    """读取所有股票 CSV 文件，返回 STOCKS 字典"""
    stocks = {}

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.csv') or fname in EXCLUDE:
            continue

        filepath = os.path.join(DATA_DIR, fname)
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)

        # 提取股票代码和名称
        # 文件名格式: 600519_贵州茅台_A股_daily.csv
        parts = fname.replace('.csv', '').split('_')
        code = parts[0]
        name = parts[1]
        market = parts[2]  # A股 或 港股

        # 提取核心字段: [Date, Open, Close, High, Low, Volume]
        records = []
        for _, row in df.iterrows():
            records.append([
                row['Date'].strftime('%Y-%m-%d'),
                round(float(row['Open']), 2),
                round(float(row['Close']), 2),
                round(float(row['High']), 2),
                round(float(row['Low']), 2),
                int(row['Volume']),
            ])

        stocks[code] = {
            'code': code,
            'name': name,
            'market': market,
            'data': records,
            'count': len(records),
            'dateStart': records[0][0],
            'dateEnd': records[-1][0],
        }

        print(f'  ✅ {code} {name} ({market}): {len(records)} 条, '
              f'{records[0][0]} ~ {records[-1][0]}')

    return stocks


def main():
    print('=' * 60)
    print('  Task3: 数据准备 — CSV → JSON')
    print('=' * 60)
    print(f'  数据目录: {DATA_DIR}')
    print()

    stocks = load_all_stocks()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)

    file_size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f'\n✅ 已输出 {len(stocks)} 只股票 → {OUTPUT_FILE}')
    print(f'   文件大小: {file_size_kb:.1f} KB')
    print('=' * 60)


if __name__ == '__main__':
    main()
