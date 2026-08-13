#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified data update script — fetches latest qfq OHLCV for all 10 stocks.
Runs in GitHub Actions or locally.

Scheduled runs use Tencent Finance first and AKShare as a bounded fallback.
Manual runs may opt into Tushare with ``--prefer-tushare``; A-shares then use
pro_bar(adj="qfq") and HK stocks use hk_daily_adj when permitted.

Usage:
    python update_all_data.py           # full fetch
    python update_all_data.py --check   # check if update needed (exit 0=needed, 1=not)
    python update_all_data.py --force   # fetch even outside a trading day
    python update_all_data.py --prefer-tushare  # optional manual high-quality source
"""

import os
import sys
import time
import argparse
import pandas as pd
import requests
from datetime import datetime, timedelta

# ═══════════════ Config ═══════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'csv')
os.makedirs(DATA_DIR, exist_ok=True)

# Never store this value in code. In CI it comes from a GitHub Actions Secret.
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '').strip()
TUSHARE_MARKET_ENABLED = {
    'A股': bool(TUSHARE_TOKEN),
    '港股': bool(TUSHARE_TOKEN),
}

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
MAX_FETCH_ATTEMPTS = 3

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

def tencent_symbol(code, market):
    if market == '港股':
        return f'hk{code}'
    exchange = 'sh' if code.startswith(('5', '6', '9')) else 'sz'
    return f'{exchange}{code}'


def fetch_tencent_stock(code, name, market):
    """Fetch recent daily bars from Tencent Finance."""
    try:
        symbol = tencent_symbol(code, market)
        response = requests.get(
            'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get',
            params={'param': f'{symbol},day,,,320,qfq'},
            timeout=45,
            headers={'User-Agent': 'Mozilla/5.0 quant-trading-ai'},
        )
        response.raise_for_status()
        payload = response.json()
        node = payload.get('data', {}).get(symbol, {})
        rows = node.get('qfqday') or node.get('day') or []
        if payload.get('code') != 0 or not rows:
            raise ValueError(
                f'Tencent returned no rows: {payload.get("msg", "")}'
            )

        df = pd.DataFrame(
            [row[:6] for row in rows],
            columns=['Date', 'Open', 'Close', 'High', 'Low', 'Volume'],
        )
        df['Date'] = pd.to_datetime(df['Date'])
        for column in ['Open', 'Close', 'High', 'Low', 'Volume']:
            df[column] = pd.to_numeric(df[column], errors='coerce')
        df = df.dropna(subset=['Date', 'Open', 'Close', 'High', 'Low'])
        df = df[
            (df['Date'] >= pd.to_datetime(START_DATE))
            & (df['Date'] <= pd.to_datetime(END_DATE))
        ].copy()
        previous_close = df['Close'].shift(1)
        df['股票代码'] = code
        df['Amount'] = pd.NA
        df['振幅'] = ((df['High'] - df['Low']) / previous_close * 100).round(4)
        df['PctChg'] = df['Close'].pct_change().mul(100).round(4)
        df['涨跌额'] = df['Close'].diff().round(4)
        df['Turnover'] = pd.NA
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        keep_cols = [
            'Date', '股票代码', 'Open', 'Close', 'High', 'Low',
            'Volume', 'Amount', '振幅', 'PctChg', '涨跌额', 'Turnover',
        ]
        series_name = 'qfqday' if node.get('qfqday') else 'day'
        print(f'     ✅ Tencent {series_name}: {symbol}')
        return df[keep_cols].sort_values('Date').reset_index(drop=True)
    except Exception as e:
        print(f'     ⚠️  Tencent failed for {code} {name}: {e}')
        return None


def a_share_ts_code(code):
    """Convert a six-digit A-share code to Tushare exchange format."""
    if code.startswith(('4', '8')):
        suffix = 'BJ'
    elif code.startswith(('5', '6', '9')):
        suffix = 'SH'
    else:
        suffix = 'SZ'
    return f'{code}.{suffix}'


def _is_permanent_tushare_error(error):
    """Identify errors that retries cannot fix during the current run."""
    message = str(error).lower()
    hints = (
        'token', 'permission', 'forbidden', 'unauthorized', '401', '403',
        '权限', '积分', '抱歉', '无权', '访问该接口',
    )
    return any(hint in message for hint in hints)


def _record_tushare_error(market, code, name, error):
    if _is_permanent_tushare_error(error):
        TUSHARE_MARKET_ENABLED[market] = False
        print(
            f'     ⚠️  Tushare disabled for {market} this run after '
            f'{code} {name}: {error}'
        )
    else:
        print(f'     ⚠️  Tushare failed for {code} {name}: {error}')


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
    if not TUSHARE_MARKET_ENABLED['A股']:
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
        _record_tushare_error('A股', code, name, e)
        return None


def fetch_tushare_hk_stock(code, name):
    """Fetch adjusted HK daily data through Tushare when permitted."""
    if not TUSHARE_MARKET_ENABLED['港股']:
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
        _record_tushare_error('港股', code, name, e)
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


def fetch_with_retry(fetcher, code, name, *extra):
    """Fetch one stock with bounded retries for transient provider failures."""
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        df = fetcher(code, name, *extra)
        if df is not None and not df.empty:
            return df

        if attempt < MAX_FETCH_ATTEMPTS:
            delay = 2 ** (attempt - 1)
            print(
                f"     ↻ Retry {attempt + 1}/{MAX_FETCH_ATTEMPTS} "
                f"in {delay}s..."
            )
            time.sleep(delay)

    return None


def fetch_tushare_with_retry(fetcher, code, name, market):
    """Retry transient Tushare failures, but stop on auth/permission errors."""
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        if not TUSHARE_MARKET_ENABLED[market]:
            return None

        df = fetcher(code, name)
        if df is not None and not df.empty:
            return df
        if not TUSHARE_MARKET_ENABLED[market]:
            return None

        if attempt < MAX_FETCH_ATTEMPTS:
            delay = 2 ** (attempt - 1)
            print(
                f'     ↻ Tushare retry {attempt + 1}/{MAX_FETCH_ATTEMPTS} '
                f'in {delay}s...'
            )
            time.sleep(delay)

    return None


def validate_stock_data(df, code):
    """Reject malformed provider responses before replacing a good CSV."""
    required = {'Date', 'Open', 'Close', 'High', 'Low', 'Volume'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'missing columns: {sorted(missing)}')
    if df.empty:
        raise ValueError('empty data')

    dates = pd.to_datetime(df['Date'], errors='coerce')
    if dates.isna().any() or dates.duplicated().any():
        raise ValueError('invalid or duplicate dates')

    prices = df[['Open', 'Close', 'High', 'Low']].apply(
        pd.to_numeric, errors='coerce'
    )
    if prices.isna().any().any() or (prices <= 0).any().any():
        raise ValueError('invalid OHLC prices')
    if (
        (prices['High'] < prices[['Open', 'Close', 'Low']].max(axis=1)).any()
        or (prices['Low'] > prices[['Open', 'Close', 'High']].min(axis=1)).any()
    ):
        raise ValueError('inconsistent OHLC bounds')

    if '股票代码' in df.columns:
        codes = df['股票代码'].astype(str).str.zfill(len(code)).unique()
        if len(codes) != 1 or codes[0] != code:
            raise ValueError(f'unexpected stock code: {codes.tolist()}')


def save_validated_csv(df, filepath, code):
    """Validate and atomically replace a CSV, preserving the old file on error."""
    validate_stock_data(df, code)
    temp_path = f'{filepath}.tmp'
    try:
        df.to_csv(temp_path, index=False, encoding='utf-8-sig')
        os.replace(temp_path, filepath)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


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
    parser.add_argument(
        '--force',
        action='store_true',
        help='Fetch all symbols even when the calendar check says no update is needed',
    )
    parser.add_argument(
        '--prefer-tushare',
        action='store_true',
        help='Try adjusted Tushare data before credential-free sources',
    )
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
    if args.prefer_tushare and TUSHARE_TOKEN:
        preferred = 'Tushare > Tencent > AKShare (manual opt-in)'
    elif args.prefer_tushare:
        preferred = 'Tencent > AKShare (--prefer-tushare ignored: token not set)'
    else:
        preferred = 'Tencent > AKShare'
    print(f'  Preferred source: {preferred}')
    print('=' * 60)

    updated = 0
    attempted = 0
    failures = []
    for code, name, market, ak_symbol in STOCKS:
        fname = f'{code}_{name}_{market}_daily.csv'
        fpath = os.path.join(DATA_DIR, fname)

        if (
            not args.force
            and not needs_update(fpath)
            and os.path.exists(fpath)
        ):
            print(f'  ⏭️  {code} {name}: up to date')
            continue

        print(f'  📡 {code} {name} ({market})...')
        attempted += 1
        time.sleep(0.5)  # Rate limit

        df = None
        if args.prefer_tushare and TUSHARE_TOKEN:
            if market == 'A股':
                df = fetch_tushare_with_retry(
                    fetch_tushare_a_stock, code, name, market
                )
            else:
                df = fetch_tushare_with_retry(
                    fetch_tushare_hk_stock, code, name, market
                )

        if df is None:
            if args.prefer_tushare:
                print('     ↪ Using Tencent qfq')
            df = fetch_with_retry(fetch_tencent_stock, code, name, market)
        if df is None:
            print('     ↪ Falling back to AKShare')
            if market == 'A股':
                df = fetch_with_retry(fetch_a_stock, ak_symbol, name)
            else:
                df = fetch_with_retry(fetch_hk_stock, ak_symbol, name)

        if df is None or len(df) == 0:
            failures.append(f'{code} {name}')
            continue

        try:
            save_validated_csv(df, fpath, code)
            print(f'     ✅ Validated and saved {len(df)} rows to {fname}')
            updated += 1
        except Exception as exc:
            print(f'     ❌ Rejected provider data; kept existing CSV: {exc}')
            failures.append(f'{code} {name}')

    print(f'\n📊 Updated: {updated}/{attempted} attempted stocks')

    if failures:
        print(f'❌ All public sources failed: {", ".join(failures)}')
        print('No dashboards were rebuilt; failing the workflow to avoid a false success.')
        sys.exit(1)

    if updated > 0:
        print('\n🔨 Rebuilding dashboards...')
        rebuild_dashboards()

    print('\n✅ Done.')


if __name__ == '__main__':
    main()
