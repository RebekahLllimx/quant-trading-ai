#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh the market data embedded in the Turtle strategy dashboard."""

import json
import re
from pathlib import Path

from turtle_strategy import load_stock

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_FILE = BASE_DIR / 'dashboard' / 'index.html'
STOCKS_BINDING = re.compile(r'^\s*const STOCKS =\s*', re.MULTILINE)

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
    """Load the ten instrument snapshots in the dashboard's OHLCV schema."""
    stocks = {}
    for code, name, market in STOCKS:
        df = load_stock(code, name, market)
        df = df[['Date', 'Open', 'Close', 'High', 'Low', 'Volume']].copy()
        if df.empty:
            raise ValueError(f'No market observations for {code}')
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        data = df.values.tolist()
        stocks[code] = {
            'code': code,
            'name': name,
            'market': market,
            'data': data,  # Date, Open, Close, High, Low, Volume.
            'dateStart': data[0][0],
            'dateEnd': data[-1][0],
            'records': len(data),
        }
        print(f'   {code} {name} ({market}): {len(data)} observations')

    return stocks


def replace_stock_payload(html, stocks):
    """Replace one JSON data binding while preserving the surrounding page."""
    matches = list(STOCKS_BINDING.finditer(html))
    if len(matches) != 1:
        raise ValueError('Expected exactly one const STOCKS data binding')
    start = matches[0].end()
    current, length = json.JSONDecoder().raw_decode(html[start:])
    if not isinstance(current, dict) or not html[start + length:].lstrip().startswith(';'):
        raise ValueError('Expected a JSON object followed by a semicolon')
    # Keep data containing HTML delimiters inside the existing script element.
    payload = json.dumps(stocks, ensure_ascii=False, allow_nan=False)
    payload = payload.replace('<', r'\u003c').replace('\u2028', r'\u2028').replace('\u2029', r'\u2029')
    return html[:start] + payload + html[start + length:]


def main():
    html = OUTPUT_FILE.read_text(encoding='utf-8')
    refreshed = replace_stock_payload(html, build_stocks_json())
    if refreshed != html:
        OUTPUT_FILE.write_text(refreshed, encoding='utf-8')
    print(f'Dashboard data ready: {OUTPUT_FILE.relative_to(BASE_DIR)}')

if __name__ == '__main__':
    main()
