#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据更新脚本：用 AKShare 获取最新股价数据，覆盖 data/ 下的 CSV
"""

import os
import sys
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data', 'csv')
os.makedirs(DATA_DIR, exist_ok=True)

END_DATE = datetime.now().strftime("%Y%m%d")  # 20260703
START_DATE = (datetime.now() - timedelta(days=400)).strftime("%Y%m%d")  # ~1 year ago

# A股标的
A_STOCKS = [
    {"code": "000001", "name": "平安银行"},
    {"code": "600519", "name": "贵州茅台"},
    {"code": "002594", "name": "比亚迪"},
    {"code": "601318", "name": "中国平安"},
    {"code": "300750", "name": "宁德时代"},
]

# 港股标的
HK_STOCKS = [
    {"code": "00700", "name": "腾讯控股"},
    {"code": "09988", "name": "阿里巴巴"},
    {"code": "03690", "name": "美团"},
    {"code": "00388", "name": "香港交易所"},
    {"code": "00941", "name": "中国移动"},
]


def fetch_a_stock(code):
    """获取A股前复权日线数据"""
    try:
        df = ak.stock_zh_a_hist(
            symbol=code, period='daily',
            start_date=START_DATE, end_date=END_DATE, adjust='qfq'
        )
        df = df.rename(columns={
            '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
            '最高': 'High', '最低': 'Low', '成交量': 'Volume',
            '成交额': 'Amount', '涨跌幅': 'PctChg', '换手率': 'Turnover',
        })
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('Date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"  ❌ A股 {code} 获取失败: {e}")
        return None


def fetch_hk_stock(code):
    """获取港股前复权日线数据"""
    try:
        df = ak.stock_hk_hist(
            symbol=code, period='daily',
            start_date=START_DATE, end_date=END_DATE, adjust='qfq'
        )
        df = df.rename(columns={
            '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
            '最高': 'High', '最低': 'Low', '成交量': 'Volume',
            '成交额': 'Amount', '涨跌幅': 'PctChg',
        })
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('Date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"  ❌ 港股 {code} 获取失败: {e}")
        return None


def main():
    print("=" * 60)
    print("  更新股价数据 (AKShare)")
    print(f"  时间范围: {START_DATE} ~ {END_DATE}")
    print("=" * 60)

    all_updated = 0

    # 更新 A 股
    print("\n>>> A股数据更新...")
    for s in A_STOCKS:
        print(f"  📡 {s['name']} ({s['code']}) ...", end=" ")
        df = fetch_a_stock(s['code'])
        if df is not None:
            filename = f"{s['code']}_{s['name']}_A股_daily.csv"
            filepath = os.path.join(DATA_DIR, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"✅ {len(df)}条 → {filename}  (最新: {df['Date'].iloc[-1]})")
            all_updated += 1

    # 更新港股
    print("\n>>> 港股数据更新...")
    for s in HK_STOCKS:
        print(f"  📡 {s['name']} ({s['code']}) ...", end=" ")
        df = fetch_hk_stock(s['code'])
        if df is not None:
            filename = f"{s['code']}_{s['name']}_港股_daily.csv"
            filepath = os.path.join(DATA_DIR, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"✅ {len(df)}条 → {filename}  (最新: {df['Date'].iloc[-1]})")
            all_updated += 1

    print(f"\n{'=' * 60}")
    print(f"  完成！共更新 {all_updated}/10 只股票")
    print(f"  数据目录: {DATA_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
