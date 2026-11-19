#!/usr/bin/env python3
"""Refresh Task 2 prices while preserving the dashboard's indicator engine."""

import json
import os
import re
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data', 'csv')
OUTPUT_FILE = Path(BASE_DIR).parent / 'dashboard/index.html'
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from market_data import INSTRUMENTS, load_prices


def load_all_stocks():
    stocks = {}
    for item in INSTRUMENTS:
        frame = load_prices(item.code, DATA_DIR)
        frame['Date'] = frame['Date'].dt.strftime('%Y-%m-%d')
        records = frame[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].values.tolist()
        stocks[item.code] = {
            'code': item.code, 'name': item.name, 'market': item.market,
            'data': records, 'start': records[0][0], 'end': records[-1][0],
            'count': len(records),
        }
    return stocks


def replace_payload(html, stocks):
    matches = list(re.finditer(r'^\s*const STOCKS =\s*', html, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError('Expected exactly one STOCKS binding')
    start = matches[0].end()
    old, length = json.JSONDecoder().raw_decode(html[start:])
    if not isinstance(old, dict) or not html[start + length:].lstrip().startswith(';'):
        raise ValueError('Invalid STOCKS binding')
    payload = json.dumps(stocks, allow_nan=False).replace('<', '\\u003c')
    return html[:start] + payload + html[start + length:]


def build_html():
    html = OUTPUT_FILE.read_text(encoding='utf-8')
    OUTPUT_FILE.write_text(replace_payload(html, load_all_stocks()), encoding='utf-8')
    print(f'Refreshed {OUTPUT_FILE}')


if __name__ == '__main__':
    build_html()
