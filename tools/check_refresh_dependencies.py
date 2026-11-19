#!/usr/bin/env python3
"""Check the installed refresh API surface without making network calls."""

import inspect
import sys

import akshare as ak

if sys.version_info < (3, 11, 5):
    raise RuntimeError('AKShare 1.20.65 requires Python >= 3.11.5')
if ak.__version__ != '1.20.65':
    raise RuntimeError('Install requirements-refresh.txt for the tested provider API')
for name, parameters in {
    'stock_zh_a_hist_em': {'symbol', 'period', 'start_date', 'end_date', 'adjust'},
    'stock_hk_hist_em': {'symbol', 'period', 'start_date', 'end_date', 'adjust'},
    'index_zh_daily_em': {'symbol', 'start_date', 'end_date'},
    'index_zh_daily_sina': {'symbol'},
    'fund_etf_hist_sina': {'symbol'},
}.items():
    if not parameters <= set(inspect.signature(getattr(ak, name)).parameters):
        raise RuntimeError(f'Provider signature changed: {name}')
print('Refresh dependency and API-surface checks passed (no network calls).')
