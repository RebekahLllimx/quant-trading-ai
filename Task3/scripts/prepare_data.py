#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task3 Phase 1: will CSV Data serialized JSON, supply HTML Dashboard Embedded Use
Output: Task3/dashboard/data.json (embedded index.html of STOCKS object)
"""

import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'dashboard')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'data.json')

# Non-standard data files that need to be excluded
EXCLUDE = [
    '_embedded_data.json',
    'multi_stock_summary.csv',
    'AH_summary.csv',
]


def load_all_stocks():
    """Read All Stocks CSV File, Return STOCKS dictionary"""
    stocks = {}

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.csv') or fname in EXCLUDE:
            continue

        filepath = os.path.join(DATA_DIR, fname)
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)

        # Extract symbol and name
        # File name format: 600519_Kweichow Moutai_A-share_daily.csv
        parts = fname.replace('.csv', '').split('_')
        code = parts[0]
        name = parts[1]
        market = parts[2]  # A-share or Hong Kong equities

        # Extract core fields: [Date, Open, Close, High, Low, Volume]
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

        print(f'   {code} {name} ({market}): {len(records)} item, '
              f'{records[0][0]} ~ {records[-1][0]}')

    return stocks


def main():
    print('=' * 60)
    print('  Task3: Data Preparation  -  CSV  ->  JSON')
    print('=' * 60)
    print(f'  Data Catalog: {DATA_DIR}')
    print()

    stocks = load_all_stocks()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)

    file_size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f'\n Already output {len(stocks)} Only stock  ->  {OUTPUT_FILE}')
    print(f'   File size: {file_size_kb:.1f} KB')
    print('=' * 60)


if __name__ == '__main__':
    main()
