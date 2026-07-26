#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified data update script — fetches latest qfq OHLCV for all 10 stocks.
Runs in GitHub Actions or locally.

Tushare is preferred when TUSHARE_TOKEN is configured. A-shares use
pro_bar(adj="qfq"); HK stocks use hk_daily_adj when the account has access.
Every Tushare failure falls back to AKShare qfq data.

Usage:
    python update_all_data.py           # full fetch
    python update_all_data.py --check   # check if update needed (exit 0=needed, 1=not)
"""

import os
import sys
import time
import argparse
import pandas as pd
from datetime import datetime, timedelta

# ═══════════════ Config ═══════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'csv')
os.makedirs(DATA_DIR, exist_ok=True)

# Never store this value in code. In CI it comes from a GitHub Actions Secret.
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '').strip()

# 10 stocks: code, name, market, akshare symbol
STOCKS = [
    # A-shares
    ('600519', '贵州茅台', 'A股', '600519'),
    ('601318', '中国平安', 'A股', '601318'),
    ('300750', '宁德时代', 'A股', '300750'),
    ('002594', '比亚迪', 'A股', '002594'),
    ('000001', '平安银行', 'A股', '000001'),
    # HK stocks (akshare uses slightly different symbols)
    ('00700', '腾讯控股', '港股', '00700'),
    ('09988', '阿里巴巴', '港股', '09988'),
    ('03690', '美团', '港股', '03690'),
    ('00388', '香港交易所', '港股', '00388'),
    ('00941', '中国移动', '港股', '00941'),
]

# Fetch ~1 year of daily data
START_DATE = (datetime.now() - timedelta(days=400)).strftime('%Y%m%d')
END_DATE = datetime.now().strftime('%Y%m%d')

# ═══════════════ Helpers ═══════════════

def is_trading_day():
    """Rough check: weekday + not obvious holiday."""
    today = datetime.now()
    if today.weekday() >= 5:  # Sat/Sun
        return False
    return True


def needs_update(filepath):
    """Check if CSV needs update (latest date < today and today is trading day)."""
    if not os.path.exists(filepath):
        return True
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        df['Date'] = pd.to_datetime(df['Date'])
        latest = df['Date'].max()
        today = pd.Timestamp.now().normalize()
        # Update if latest < today and today might be a trading day
        return latest < today and is_trading_day()
    except Exception:
        return True


# ═══════════════ Fetch ═══════════════

def a_share_ts_code(code):
    """Convert a six-digit A-share code to Tushare exchange format."""
    if code.startswith(('4', '8')):
        suffix = 'BJ'
    elif code.startswith(('5', '6', '9')):
        suffix = 'SH'
    else:
        suffix = 'SZ'
    return f'{code}.{suffix}'


def _standardize_tushare(df, code, market):
    """Convert Tushare output to the CSV schema consumed by backtests."""
    pct_col = 'pct_chg' if 'pct_chg' in df.columns else 'pct_change'
    df = df.rename(columns={
        'trade_date': 'Date', 'open': 'Open', 'close': 'Close',
        'high': 'High', 'low': 'Low', 'vol': 'Volume',
        'amount': 'Amount', 'change': '涨跌额', pct_col: 'PctChg',
        'turnover_ratio': 'Turnover',
    }).copy()
    df['股票代码'] = code
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

    # Tushare A-share amount is in thousands of CNY; AKShare CSVs use CNY.
    if market == 'A股' and 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce') * 1000

    if {'High', 'Low', 'pre_close'} <= set(df.columns):
        pre_close = pd.to_numeric(df['pre_close'], errors='coerce')
        df['振幅'] = (
            (pd.to_numeric(df['High'], errors='coerce')
             - pd.to_numeric(df['Low'], errors='coerce'))
            / pre_close.replace(0, pd.NA) * 100
        ).round(4)

    keep_cols = ['Date', '股票代码', 'Open', 'Close', 'High', 'Low',
                 'Volume', 'Amount', '振幅', 'PctChg', '涨跌额', 'Turnover']
    return df[[c for c in keep_cols if c in df.columns]].sort_values(
        'Date'
    ).reset_index(drop=True)


def fetch_tushare_a_stock(code, name):
    """Fetch qfq A-share daily data through Tushare."""
    if not TUSHARE_TOKEN:
        return None
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        ts_code = a_share_ts_code(code)
        df = ts.pro_bar(ts_code=ts_code, start_date=START_DATE,
                        end_date=END_DATE, adj='qfq', freq='D')
        if df is None or df.empty:
            raise ValueError('Tushare returned empty data')
        print(f'     ✅ Tushare pro_bar(qfq): {ts_code}')
        return _standardize_tushare(df, code, 'A股')
    except Exception as e:
        print(f'     ⚠️  Tushare failed for {code} {name}: {e}')
        return None


def fetch_tushare_hk_stock(code, name):
    """Fetch adjusted HK daily data through Tushare when permitted."""
    if not TUSHARE_TOKEN:
        return None
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        ts_code = f'{code.zfill(5)}.HK'
        df = pro.hk_daily_adj(ts_code=ts_code, start_date=START_DATE,
                              end_date=END_DATE)
        if df is None or df.empty:
            raise ValueError('Tushare returned empty data')
        print(f'     ✅ Tushare hk_daily_adj: {ts_code}')
        return _standardize_tushare(df, code.zfill(5), '港股')
    except Exception as e:
        print(f'     ⚠️  Tushare unavailable for {code} {name}: {e}')
        return None


def fetch_a_stock(code, name):
    """Fetch A-share daily data via AKShare."""
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(
            symbol=code,
            period='daily',
            start_date=START_DATE,
            end_date=END_DATE,
            adjust='qfq'
        )
        if df is None or df.empty:
            print(f"  ⚠️  {code} {name}: AKShare returned empty")
            return None

        # Rename to standard format
        df = df.rename(columns={
            '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
            '最高': 'High', '最低': 'Low', '成交量': 'Volume',
            '成交额': 'Amount', '振幅': '振幅', '涨跌幅': 'PctChg',
            '涨跌额': '涨跌额', '换手率': 'Turnover',
        })
        df['股票代码'] = code
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

        keep_cols = ['Date', '股票代码', 'Open', 'Close', 'High', 'Low',
                     'Volume', 'Amount', '振幅', 'PctChg', '涨跌额', 'Turnover']
        df = df[[c for c in keep_cols if c in df.columns]]
        return df.sort_values('Date').reset_index(drop=True)
    except Exception as e:
        print(f"     ❌ AKShare failed for {code} {name}: {e}")
        return None


def fetch_hk_stock(code, name):
    """Fetch HK stock daily data via AKShare."""
    try:
        import akshare as ak
        df = ak.stock_hk_hist(
            symbol=code,
            period='daily',
            start_date=START_DATE,
            end_date=END_DATE,
            adjust='qfq'
        )
        if df is None or df.empty:
            print(f"  ⚠️  {code} {name}: AKShare returned empty")
            return None

        # Rename
        df = df.rename(columns={
            '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
            '最高': 'High', '最低': 'Low', '成交量': 'Volume',
            '成交额': 'Amount',
        })
        df['股票代码'] = code
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

        keep_cols = ['Date', '股票代码', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount']
        df = df[[c for c in keep_cols if c in df.columns]]
        return df.sort_values('Date').reset_index(drop=True)
    except Exception as e:
        print(f"     ❌ AKShare failed for {code} {name}: {e}")
        return None


def rebuild_dashboards():
    """Rebuild all dashboard index.html files with updated CSV data."""
    import subprocess
    scripts = [
        'Task3/scripts/build_dashboard.py',
        'Task4/scripts/prepare_data.py',
    ]
    for script in scripts:
        path = os.path.join(BASE_DIR, script)
        if os.path.exists(path):
            print(f"  🔨 Running {script}...")
            result = subprocess.run(
                [sys.executable, path],
                cwd=BASE_DIR,
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                print(f"     ✅ {script} completed")
            else:
                print(f"     ⚠️  {script} error: {result.stderr[:200]}")
        else:
            print(f"  ⚠️  {script} not found, skipping")


# ═══════════════ Main ═══════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Only check if update needed')
    args = parser.parse_args()

    if args.check:
        any_needed = False
        for code, name, market, _ in STOCKS:
            fname = f'{code}_{name}_{market}_daily.csv'
            fpath = os.path.join(DATA_DIR, fname)
            if needs_update(fpath):
                any_needed = True
                break
        sys.exit(0 if any_needed else 1)

    print('=' * 60)
    print('  Update All Stock Data')
    print(f'  Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  Stocks: {len(STOCKS)}')
    preferred = 'Tushare' if TUSHARE_TOKEN else 'AKShare (TUSHARE_TOKEN not set)'
    print(f'  Preferred source: {preferred}')
    print('=' * 60)

    updated = 0
    for code, name, market, ak_symbol in STOCKS:
        fname = f'{code}_{name}_{market}_daily.csv'
        fpath = os.path.join(DATA_DIR, fname)

        if not args.check and not needs_update(fpath) and os.path.exists(fpath):
            print(f'  ⏭️  {code} {name}: up to date')
            continue

        print(f'  📡 {code} {name} ({market})...')
        time.sleep(0.5)  # Rate limit

        if market == 'A股':
            df = fetch_tushare_a_stock(code, name)
            if df is None:
                print('     ↪ Falling back to AKShare qfq')
                df = fetch_a_stock(ak_symbol, name)
        else:
            df = fetch_tushare_hk_stock(code, name)
            if df is None:
                print('     ↪ Falling back to AKShare qfq')
                df = fetch_hk_stock(ak_symbol, name)

        if df is not None and len(df) > 0:
            df.to_csv(fpath, index=False, encoding='utf-8-sig')
            print(f'     ✅ Saved {len(df)} rows to {fname}')
            updated += 1

    print(f'\n📊 Updated: {updated}/{len(STOCKS)} stocks')

    if updated > 0:
        print('\n🔨 Rebuilding dashboards...')
        rebuild_dashboards()

    print('\n✅ Done.')


if __name__ == '__main__':
    main()
