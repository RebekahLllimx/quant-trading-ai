#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Update Script: use AKShare Get the latest stock price data, Coverage data/ downstairs CSV
"""

import os
import sys
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

# Path Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data', 'csv')

END_DATE = datetime.now().strftime("%Y%m%d")  # 20260703
START_DATE = (datetime.now() - timedelta(days=400)).strftime("%Y%m%d")  # ~1 year ago

# AUnderlying stock
A_STOCKS = [
    {"code": "000001", "name": "Ping An Bank"},
    {"code": "600519", "name": "Kweichow Moutai"},
    {"code": "002594", "name": "BYD"},
    {"code": "601318", "name": "Ping An of China"},
    {"code": "300750", "name": "CATL"},
]

# Hong Kong equity targets
HK_STOCKS = [
    {"code": "00700", "name": "Tencent Holdings"},
    {"code": "09988", "name": "Alibaba"},
    {"code": "03690", "name": "Meituan"},
    {"code": "00388", "name": "Hong Kong Exchange"},
    {"code": "00941", "name": "China Mobile"},
]


def fetch_a_stock(code):
    """GetAPre-stock recovery daily data"""
    try:
        df = ak.stock_zh_a_hist(
            symbol=code, period='daily',
            start_date=START_DATE, end_date=END_DATE, adjust='qfq'
        )
        df = df.rename(columns={
            'Date': 'Date', 'Opening': 'Open', 'Close of trading': 'Close',
            'highest': 'High', 'Minimum': 'Low', 'Trading volume': 'Volume',
            'Turnover': 'Amount', 'Return': 'PctChg', 'Turnover rate': 'Turnover',
        })
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('Date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"   A-share {code} Failed to retrieve: {e}")
        return None


def fetch_hk_stock(code):
    """Obtain Hong Kong equity adjusted daily data"""
    try:
        df = ak.stock_hk_hist(
            symbol=code, period='daily',
            start_date=START_DATE, end_date=END_DATE, adjust='qfq'
        )
        df = df.rename(columns={
            'Date': 'Date', 'Opening': 'Open', 'Close of trading': 'Close',
            'highest': 'High', 'Minimum': 'Low', 'Trading volume': 'Volume',
            'Turnover': 'Amount', 'Return': 'PctChg',
        })
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('Date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"   Hong Kong equities {code} Failed to retrieve: {e}")
        return None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 60)
    print("  Update stock price data (AKShare)")
    print(f"  Time range: {START_DATE} ~ {END_DATE}")
    print("=" * 60)

    all_updated = 0

    # Update A stock
    print("\n>>> AShare data update...")
    for s in A_STOCKS:
        print(f"   {s['name']} ({s['code']}) ...", end=" ")
        df = fetch_a_stock(s['code'])
        if df is not None:
            filename = f"{s['code']}_{s['name']}_A-share_daily.csv"
            filepath = os.path.join(DATA_DIR, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f" {len(df)}item  ->  {filename}  (latest: {df['Date'].iloc[-1]})")
            all_updated += 1

    # Update Hong Kong equities
    print("\n>>> Hong Kong Stock Data Update...")
    for s in HK_STOCKS:
        print(f"   {s['name']} ({s['code']}) ...", end=" ")
        df = fetch_hk_stock(s['code'])
        if df is not None:
            filename = f"{s['code']}_{s['name']}_Hong Kong equities_daily.csv"
            filepath = os.path.join(DATA_DIR, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f" {len(df)}item  ->  {filename}  (latest: {df['Date'].iloc[-1]})")
            all_updated += 1

    print(f"\n{'=' * 60}")
    print(f"  Complete! Total update {all_updated}/10 Only stock")
    print(f"  Data Catalog: {DATA_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
