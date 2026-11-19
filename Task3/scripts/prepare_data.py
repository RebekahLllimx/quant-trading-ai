#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serialize canonical OHLCV snapshots for the Task 3 backtesting dashboard."""

import os
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from market_data import INSTRUMENTS, load_prices

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data', 'csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'dashboard')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'data.json')

def load_all_stocks():
    """Read every registered instrument with its display metadata."""
    stocks = {}

    for item in INSTRUMENTS:
        code, name, market = item.code, item.name, item.market
        df = load_prices(code, DATA_DIR)

        # Extract core fields: [Date, Open, Close, High, Low, Volume]
        records = []
        for _, row in df.iterrows():
            records.append([
                row['Date'].strftime('%Y-%m-%d'),
                float(row['Open']),
                float(row['Close']),
                float(row['High']),
                float(row['Low']),
                float(row['Volume']),
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
        json.dump(stocks, f, allow_nan=False, indent=2)

    file_size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f'\n Already output {len(stocks)} Only stock  ->  {OUTPUT_FILE}')
    print(f'   File size: {file_size_kb:.1f} KB')
    print('=' * 60)


if __name__ == '__main__':
    main()
