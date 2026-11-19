#!/usr/bin/env python3
"""Refresh daily prices and publish a validated, complete dashboard snapshot.

Tencent qfq bars are the primary source, with AKShare as a bounded fallback.
Tushare is opt-in. Use requirements-refresh.txt with Python 3.12; offline
research and saved-model reproduction retain their Python 3.10 environment.
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from market_data import CSV_COLUMNS, INSTRUMENTS, ROOT, canonical_path, merge_prices, validate_prices
from refresh_pipeline import (
    atomic_bytes, inspect_inputs, market_date, read_existing, refresh_snapshot,
)

BASE_DIR = str(ROOT)
DATA_DIR = str(ROOT / 'data/csv')
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '').strip()
TUSHARE_MARKET_ENABLED = {market: bool(TUSHARE_TOKEN)
                          for market in ('A-share', 'Hong Kong equities')}
STOCKS = [(s.code, s.name, s.market, s.code) for s in INSTRUMENTS]
END_DATE = market_date().replace('-', '')
START_DATE = (pd.Timestamp(END_DATE) - timedelta(days=400)).strftime('%Y%m%d')
MAX_FETCH_ATTEMPTS = 3


class ProviderRateLimited(RuntimeError):
    """The provider requires a cooldown; do not retry or continue the run."""


class ProviderContractError(ValueError):
    """A repeat request cannot repair a missing or incompatible response schema."""


def stop_on_rate_limit(error, provider):
    status = getattr(getattr(error, 'response', None), 'status_code', None)
    message = str(error).lower()
    limited = any(hint in message for hint in (
        'too many requests', 'rate limit', '每分钟最多', '每小时最多', '每天最多', '访问频次',
    ))
    if type(error).__name__ == 'Push2RateLimitError' or status == 429 or limited:
        raise ProviderRateLimited(f'{provider} rate limit: stop this run and allow a cooldown') from None

# Provider field names are protocol keys, not prose to be translated.
AKSHARE_COLUMNS = {
    '日期': 'Date', '股票代码': 'Symbol', '开盘': 'Open', '收盘': 'Close',
    '最高': 'High', '最低': 'Low', '成交量': 'Volume', '成交额': 'Amount',
    '振幅': 'Amplitude', '涨跌幅': 'PctChg', '涨跌额': 'Price change', '换手率': 'Turnover',
}


def is_trading_day(as_of=None):
    """Weekday scheduling hint, not an exchange-holiday calendar."""
    return pd.Timestamp(as_of or market_date()).weekday() < 5


def needs_update(filepath, as_of=None):
    if not Path(filepath).is_file():
        return True
    frame = pd.read_csv(filepath, encoding='utf-8-sig', dtype={'Symbol': str})
    code = Path(filepath).name.split('_', 1)[0]
    validate_prices(frame, code)
    return is_trading_day(as_of) and pd.to_datetime(frame['Date']).max() < pd.Timestamp(as_of or market_date())


def normalize_frame(frame, code, source):
    frame = frame.copy()
    # Validate before formatting: invalid dates or observations must not disappear.
    for column in ['Open', 'Close', 'High', 'Low', 'Volume', 'Amount']:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors='coerce')
    validate_prices(frame, code, as_of=pd.Timestamp(END_DATE))
    frame['Symbol'] = code
    frame['Date'] = pd.to_datetime(frame['Date']).dt.strftime('%Y-%m-%d')
    for column in CSV_COLUMNS:
        if column not in frame:
            frame[column] = np.nan
    frame = frame[CSV_COLUMNS].sort_values('Date').reset_index(drop=True)
    frame.attrs.update(source=source, adjustment='qfq')
    return frame


def tencent_symbol(code, market):
    if market == 'Hong Kong equities':
        return f'hk{code}'
    return f'{"sh" if code.startswith(("5", "6", "9")) else "sz"}{code}'


def fetch_tencent_stock(code, name, market):
    try:
        symbol = tencent_symbol(code, market)
        response = requests.get(
            'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get',
            params={'param': f'{symbol},day,,,320,qfq'}, timeout=45,
            headers={'User-Agent': 'Mozilla/5.0 quant-trading-ai'},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('code') == 429:
            raise ProviderRateLimited('Tencent rate limit: stop this run and allow a cooldown')
        if payload.get('code') != 0:
            stop_on_rate_limit(RuntimeError(str(payload.get('msg', ''))), 'Tencent')
        rows = payload.get('data', {}).get(symbol, {}).get('qfqday')
        if payload.get('code') != 0 or not rows:
            raise ProviderContractError('No qfq series returned; unadjusted day bars are not a substitute')
        frame = pd.DataFrame([row[:6] for row in rows],
                             columns=['Date', 'Open', 'Close', 'High', 'Low', 'Volume'])
        return normalize_frame(frame, code, 'Tencent Finance qfq daily API')
    except (ProviderContractError, ProviderRateLimited):
        raise
    except Exception as error:
        stop_on_rate_limit(error, 'Tencent')
        print(f'Tencent unavailable for {code} {name}: {type(error).__name__}: {error}')
        return None


def _standardize_akshare(frame, code):
    required = {'日期', '开盘', '收盘', '最高', '最低', '成交量'}
    if not required <= set(frame.columns):
        raise ProviderContractError(f'AKShare schema changed: missing {sorted(required - set(frame.columns))}')
    return normalize_frame(frame.rename(columns=AKSHARE_COLUMNS), code, 'Eastmoney via AKShare (qfq)')


def _fetch_akshare(code, name, market):
    try:
        import akshare as ak
        # The pinned 1.20 API names are explicit; old aliases were removed upstream.
        fetch = ak.stock_zh_a_hist_em if market == 'A-share' else ak.stock_hk_hist_em
        frame = fetch(symbol=code, period='daily', start_date=START_DATE,
                      end_date=END_DATE, adjust='qfq')
        return _standardize_akshare(frame, code)
    except ProviderContractError:
        raise
    except Exception as error:
        stop_on_rate_limit(error, 'AKShare')
        print(f'AKShare unavailable for {code} {name}: {type(error).__name__}: {error}')
        return None


def fetch_a_stock(code, name):
    return _fetch_akshare(code, name, 'A-share')


def fetch_hk_stock(code, name):
    return _fetch_akshare(code, name, 'Hong Kong equities')


def a_share_ts_code(code):
    suffix = 'BJ' if code.startswith(('4', '8')) else ('SH' if code.startswith(('5', '6', '9')) else 'SZ')
    return f'{code}.{suffix}'


def _standardize_tushare(frame, code, market):
    frame = frame.copy()
    if market == 'Hong Kong equities':
        if 'adj_factor' not in frame:
            raise ValueError('Tushare HK response is missing its price-adjustment factor')
        factor = pd.to_numeric(frame['adj_factor'], errors='coerce')
        if not np.isfinite(factor).all() or (factor <= 0).any():
            raise ValueError('Invalid HK price-adjustment factor')
        for column in ['open', 'close', 'high', 'low']:
            frame[column] = pd.to_numeric(frame[column], errors='coerce') * factor
    frame = frame.rename(columns={
        'trade_date': 'Date', 'open': 'Open', 'close': 'Close', 'high': 'High',
        'low': 'Low', 'vol': 'Volume', 'amount': 'Amount', 'change': 'Price change',
        'pct_chg': 'PctChg', 'pct_change': 'PctChg', 'turnover_ratio': 'Turnover',
    }).copy()
    if market == 'A-share' and 'Amount' in frame:
        frame['Amount'] = pd.to_numeric(frame['Amount'], errors='coerce') * 1000
    return normalize_frame(frame, code, f'Tushare {"pro_bar(qfq)" if market == "A-share" else "hk_daily_adj"}')


def _is_permanent_tushare_error(error):
    message = str(error).lower()
    return any(hint in message for hint in (
        'token', 'permission', 'forbidden', 'unauthorized', '401', '403', '权限', '积分',
    ))


def _fetch_tushare(code, name, market):
    if not TUSHARE_MARKET_ENABLED[market]:
        return None
    try:
        import tushare as ts
        api = ts.pro_api(token=TUSHARE_TOKEN)
        if market == 'A-share':
            frame = ts.pro_bar(api=api, ts_code=a_share_ts_code(code), start_date=START_DATE,
                              end_date=END_DATE, adj='qfq', freq='D')
        else:
            frame = api.hk_daily_adj(ts_code=f'{code}.HK',
                                     start_date=START_DATE, end_date=END_DATE)
        return _standardize_tushare(frame, code, market)
    except Exception as error:
        stop_on_rate_limit(error, 'Tushare')
        if _is_permanent_tushare_error(error):
            TUSHARE_MARKET_ENABLED[market] = False
        # Provider errors can echo credentials. Never print raw Tushare messages.
        print(f'Tushare unavailable for {code} {name}: {type(error).__name__}')
        return None


def fetch_tushare_a_stock(code, name):
    return _fetch_tushare(code, name, 'A-share')


def fetch_tushare_hk_stock(code, name):
    return _fetch_tushare(code, name, 'Hong Kong equities')


def fetch_with_retry(fetcher, code, name, *extra):
    for attempt in range(MAX_FETCH_ATTEMPTS):
        try:
            frame = fetcher(code, name, *extra)
        except ProviderContractError as error:
            print(f'{code}: {error}')
            return None
        if frame is not None and not frame.empty:
            return frame
        if attempt + 1 < MAX_FETCH_ATTEMPTS:
            time.sleep(2 ** attempt)
    return None


def fetch_tushare_with_retry(fetcher, code, name, market):
    def enabled_fetch(symbol, display_name):
        if TUSHARE_MARKET_ENABLED[market]:
            return fetcher(symbol, display_name)
        return None
    for attempt in range(MAX_FETCH_ATTEMPTS):
        frame = enabled_fetch(code, name)
        if frame is not None and not frame.empty:
            return frame
        if not TUSHARE_MARKET_ENABLED[market]:
            break
        if attempt + 1 < MAX_FETCH_ATTEMPTS:
            time.sleep(2 ** attempt)
    return None


def validate_stock_data(frame, code):
    validate_prices(frame, code)


def save_validated_csv(frame, filepath, code):
    validate_prices(frame, code)
    atomic_bytes(Path(filepath), frame.to_csv(index=False).encode('utf-8-sig'))


def rebuild_dashboards():
    return refresh_snapshot(root=Path(BASE_DIR))


def main(argv=None):
    global START_DATE, END_DATE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Exit 0 if refresh is needed, 1 otherwise')
    parser.add_argument('--force', action='store_true', help='Fetch even on weekends or with a current snapshot')
    parser.add_argument('--prefer-tushare', action='store_true', help='Try configured Tushare before public sources')
    parser.add_argument('--rebuild-only', action='store_true', help='Rebuild from committed CSVs without network access')
    parser.add_argument('--migrate-legacy', action='store_true', help='Reconcile legacy aliases, preserving backups')
    parser.add_argument('--as-of', default=market_date(), help='Snapshot date, YYYY-MM-DD, Asia/Shanghai')
    args = parser.parse_args(argv)
    as_of = pd.Timestamp(args.as_of).date().isoformat()
    END_DATE = as_of.replace('-', '')
    root = Path(BASE_DIR)
    try:
        inspect_inputs(root, migrate_legacy=args.migrate_legacy)
        if args.check:
            return 0 if any(needs_update(canonical_path(s.code, root / 'data/csv'), as_of)
                            for s in INSTRUMENTS) else 1
        if args.rebuild_only:
            refresh_snapshot(root=root, migrate_legacy=args.migrate_legacy, as_of=as_of)
            return 0
        existing = {s.code: read_existing(root, s, migrate_legacy=args.migrate_legacy) for s in INSTRUMENTS}
        starts = [pd.Timestamp(as_of) - timedelta(days=400)]
        starts.extend(pd.to_datetime(f['Date']).min() for f in existing.values() if f is not None)
        START_DATE = min(starts).strftime('%Y%m%d')
        frames, failures = {}, []
        for item in INSTRUMENTS:
            path = canonical_path(item.code, root / 'data/csv')
            if not args.force and not needs_update(path, as_of):
                frames[item.code] = existing[item.code]
                continue
            print(f'Fetching {item.code} {item.name}', flush=True)
            time.sleep(0.5)
            sources = []
            if args.prefer_tushare and TUSHARE_TOKEN:
                fetcher = fetch_tushare_a_stock if item.market == 'A-share' else fetch_tushare_hk_stock
                sources.append(('Tushare', fetch_tushare_with_retry,
                                (fetcher, item.code, item.name, item.market)))
            sources.append(('Tencent', fetch_with_retry,
                            (fetch_tencent_stock, item.code, item.name, item.market)))
            fetcher = fetch_a_stock if item.market == 'A-share' else fetch_hk_stock
            sources.append(('AKShare', fetch_with_retry, (fetcher, item.code, item.name)))
            frame = None
            for source, retry, arguments in sources:
                candidate = retry(*arguments)
                if candidate is None:
                    continue
                try:
                    merge_prices(existing[item.code], candidate, item.code)
                    frame = candidate
                    break
                except ValueError as error:
                    print(f'{item.code}: {source} history cannot be reconciled: {error}')
            if frame is None:
                failures.append(item.code)
            else:
                frames[item.code] = frame
        if failures:
            raise RuntimeError(f'All sources failed for {failures}; no files were replaced')
        refresh_snapshot(frames, root=root, migrate_legacy=args.migrate_legacy, as_of=as_of)
        return 0
    except Exception as error:
        print(f'Refresh aborted: {type(error).__name__}: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
