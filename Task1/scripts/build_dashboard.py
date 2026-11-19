#!/usr/bin/env python3
"""Refresh the data embedded in the existing Task 1 dashboard."""

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from market_data import INSTRUMENTS, load_prices

OUTPUT = ROOT / 'Task1/dashboard/index.html'


def build_payload():
    stocks = []
    for item in INSTRUMENTS:
        frame = load_prices(item.code)
        close = frame['Close']
        returns = close.pct_change().dropna()
        records = [[row.Date.strftime('%Y-%m-%d'), row.Open, row.High,
                    row.Low, row.Close, row.Volume] for row in frame.itertuples()]
        stocks.append({
            'code': item.code, 'name': item.name, 'market': item.market,
            'volume_unit': item.volume_unit,
            'chg': round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2),
            'ann_vol': round(returns.std() * np.sqrt(252) * 100, 2) if len(returns) > 1 else None,
            'max_dd': round(((close.cummax() - close) / close.cummax()).max() * 100, 2),
            'win_rate': round((returns > 0).mean() * 100, 1) if len(returns) else None, 'days': len(frame),
            'start_close': round(close.iloc[0], 3), 'end_close': round(close.iloc[-1], 3),
            'ohlc': [dict(zip(['d', 'o', 'h', 'l', 'c', 'v'], row)) for row in records],
        })
    return stocks


def replace_payload(html, stocks):
    matches = list(re.finditer(r'^const EMBEDDED =\s*', html, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError('Expected exactly one EMBEDDED binding')
    start = matches[0].end()
    old, length = json.JSONDecoder().raw_decode(html[start:])
    if not isinstance(old, list) or not html[start + length:].lstrip().startswith(';'):
        raise ValueError('Invalid EMBEDDED binding')
    payload = json.dumps(stocks, allow_nan=False).replace('<', '\\u003c')
    return html[:start] + payload + html[start + length:]


def main():
    html = OUTPUT.read_text(encoding='utf-8')
    OUTPUT.write_text(replace_payload(html, build_payload()), encoding='utf-8')
    print(f'Refreshed {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
