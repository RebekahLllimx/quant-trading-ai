#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task3: Obtain stock trading data of Shanghai and Shenzhen markets, Plot the closing price curve, SaveCSV
use Tushare Pro API (Main Programme) + akshare (Alternative plan)
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# ==================== Configuration Area ====================
# CI From TUSHARE_TOKEN Environment variable reading; Local can be rolled back to gitignore excluded config.py.
try:
    from config import TUSHARE_TOKEN as _CONFIG_TOKEN
except ImportError:
    _CONFIG_TOKEN = ""
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", _CONFIG_TOKEN).strip()

# Symbol (Example: 000001.SZ = Ping An Bank, 600519.SH = Kweichow Moutai)
STOCK_CODE = "000001"       # Symbol (Without Exchange Suffix)
STOCK_NAME = "Ping An Bank"     # Name of Stock

# Data Time Range: The past year
END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

# Output file path (Output to ../data/ and ../artifacts/charts/)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(OUTPUT_DIR, '..', '..', 'data', 'csv')
CHART_DIR = os.path.join(OUTPUT_DIR, '..', '..', 'artifacts', 'charts', 'task1')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)
CSV_FILE = os.path.join(DATA_DIR, f"{STOCK_CODE}_{STOCK_NAME}_A-share_daily.csv")
CHART_FILE = os.path.join(CHART_DIR, f"{STOCK_CODE}_{STOCK_NAME}_close_price.png")

# ==================== PlanA: use Tushare Pro ====================
def fetch_data_tushare():
    """use Tushare Pro API Get stock daily data"""
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        # Splice Exchange Suffix: Shenzhen Stock Exchange .SZ, SSE .SH
        if STOCK_CODE.startswith(('6', '9')):
            ts_code = f"{STOCK_CODE}.SH"
        else:
            ts_code = f"{STOCK_CODE}.SZ"

        print(f"[Tushare] Fetching... {ts_code} ({STOCK_NAME}) data of...")
        print(f"[Tushare] Time range: {START_DATE} ~ {END_DATE}")

        # Use the former power recovery day line, with existing CSV Consistent with backtest price caliber.
        df = ts.pro_bar(ts_code=ts_code, start_date=START_DATE,
                        end_date=END_DATE, adj="qfq", freq="D")

        if df is None or df.empty:
            raise ValueError("Tushare return empty data, Please check. Token Is it valid?")

        # In ascending order by date
        df = df.sort_values('trade_date').reset_index(drop=True)

        # Rename column to Chinese
        df = df.rename(columns={
            'trade_date': 'Date',
            'ts_code': 'Symbol',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'pre_close': 'Previous Close',
            'change': 'Price change',
            'pct_chg': 'Return',
            'vol': 'Volume',
            'amount': 'Turnover',
        })

        # Data Type Conversion
        df['Date'] = pd.to_datetime(df['Date'])
        df['Volume'] = df['Volume'].astype(float)
        # Tushare A The turnover of shares is thousands of CNY., Convert to and AKShare consistent CNY.
        df['Turnover'] = df['Turnover'].astype(float) * 1000

        print(f"[Tushare] Successfully obtained {len(df)} transaction data")
        return df

    except Exception as e:
        print(f"[Tushare] Failed to retrieve: {e}")
        return None


# ==================== PlanB: use akshare (Free registration-free)  ====================
def fetch_data_akshare():
    """use akshare Get stock daily data (Free without registration) """
    try:
        import akshare as ak

        print(f"[AKShare] Fetching... {STOCK_CODE} ({STOCK_NAME}) data of...")
        print(f"[AKShare] Time range: {START_DATE} ~ {END_DATE}")

        # GetAStock history daily data (forward-adjusted)
        df = ak.stock_zh_a_hist(
            symbol=STOCK_CODE,
            period='daily',
            start_date=START_DATE,
            end_date=END_DATE,
            adjust='qfq'  # forward-adjusted
        )

        if df is None or df.empty:
            raise ValueError("AKShare return empty data")

        # Rename columns to standard Chinese names
        df = df.rename(columns={
            'Date': 'Date',
            'Symbol': 'Symbol',
            'Opening': 'Open',
            'highest': 'High',
            'Minimum': 'Low',
            'Close of trading': 'Close',
            'Trading volume': 'Volume',
            'Turnover': 'Turnover',
            'Amplitude': 'Amplitude',
            'Return': 'Return',
            'Price change': 'Price change',
            'Turnover rate': 'Turnover rate',
        })

        # Date Conversion
        df['Date'] = pd.to_datetime(df['Date'])

        # Keep Core Columns
        core_cols = ['Date', 'Symbol', 'Open', 'High', 'Low', 'Close',
                     'Volume', 'Turnover', 'Return', 'Price change', 'Turnover rate']
        df = df[core_cols]

        print(f"[AKShare] Successfully obtained {len(df)} transaction data")
        return df

    except Exception as e:
        print(f"[AKShare] Failed to retrieve: {e}")
        return None


# ==================== Data Acquisition (Automatically select available scenarios)  ====================
def get_stock_data():
    """Get Stock Data, Prioritize use Tushare, Falls back to when unavailable akshare"""
    df = None

    # try Tushare (Only if the user has configured Token)
    if TUSHARE_TOKEN and TUSHARE_TOKEN not in ("YOUR_TUSHARE_TOKEN_HERE", ""):
        print(">>> Try using Tushare Pro API...")
        df = fetch_data_tushare()

    # Revert to akshare
    if df is None:
        print(">>> use AKShare (Free data sources) ...")
        df = fetch_data_akshare()

    if df is None or df.empty:
        raise RuntimeError("Fail to get all data sources, Please check the network connection")

    return df


# ==================== Plot the closing price curve ====================
def plot_close_price(df):
    """Plot the daily closing price curve, and annotate key statistics"""
    # Set Chinese font (macOS System Font)
    plt.rcParams['font.sans-serif'] = ['Heiti SC', 'STHeiti', 'PingFang SC',
                                        'Arial Unicode MS', 'SimHei', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    # Fix DejaVu Sans Mono Unable to display problems in Chinese
    plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']

    fig, ax = plt.subplots(figsize=(14, 7))

    dates = df['Date']
    close_prices = df['Close']

    # Plot the closing price curve
    ax.plot(dates, close_prices, color='#1f77b4', linewidth=1.5,
            marker='', markersize=2, label='Daily Closing Price')

    # Add Moving Average
    if len(df) >= 20:
        ma20 = close_prices.rolling(window=20).mean()
        ax.plot(dates, ma20, color='#ff7f0e', linewidth=1.2, linestyle='--',
                alpha=0.8, label='20daily moving average')

    if len(df) >= 60:
        ma60 = close_prices.rolling(window=60).mean()
        ax.plot(dates, ma60, color='#2ca02c', linewidth=1.2, linestyle='--',
                alpha=0.8, label='60daily moving average')

    # Mark Highest and Lowest Points
    max_idx = close_prices.idxmax()
    min_idx = close_prices.idxmin()
    ax.annotate(f'highest: {close_prices[max_idx]:.2f}',
                xy=(dates[max_idx], close_prices[max_idx]),
                xytext=(0, 15), textcoords='offset points',
                fontsize=9, color='red', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='red', alpha=0.6),
                ha='center')

    ax.annotate(f'Minimum: {close_prices[min_idx]:.2f}',
                xy=(dates[min_idx], close_prices[min_idx]),
                xytext=(0, -20), textcoords='offset points',
                fontsize=9, color='green', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='green', alpha=0.6),
                ha='center')

    # Chart Format
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Close (yuan) ', fontsize=12)
    ax.set_title(f'Figure1: {STOCK_NAME} ({STOCK_CODE}) Daily closing price trend chart of the past year',
                 fontsize=14, fontweight='bold')

    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Date format
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Add Statistics Text Box
    stats_text = (
        f"Data Range: {dates.iloc[0].strftime('%Y-%m-%d')} ~ {dates.iloc[-1].strftime('%Y-%m-%d')}\n"
        f"Transaction Days: {len(df)} days\n"
        f"Opening Closing Price: {close_prices.iloc[0]:.2f} CNY\n"
        f"Close at end of period: {close_prices.iloc[-1]:.2f} CNY\n"
        f"Highest closing price: {close_prices.max():.2f} CNY\n"
        f"Lowest closing price: {close_prices.min():.2f} CNY\n"
        f"Mean: {close_prices.mean():.2f} CNY\n"
        f"Standard deviation: {close_prices.std():.2f} CNY\n"
    )
    # Calculate the percentage change
    change_pct = (close_prices.iloc[-1] - close_prices.iloc[0]) / close_prices.iloc[0] * 100
    stats_text += f"Range change rate: {change_pct:+.2f}%"

    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8)
    # Statistical analysis in the upper right corner, Legend in upper left corner, mutual non-occlusion
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right',
            family='monospace', bbox=props)

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=150, bbox_inches='tight')
    print(f"[Drawing] Close graph saved: {CHART_FILE}")
    plt.close()


# ==================== SaveCSVData ====================
def save_to_csv(df):
    """Save dataCSVFile"""
    # Format date column
    df_to_save = df.copy()
    df_to_save['Date'] = df_to_save['Date'].dt.strftime('%Y-%m-%d')

    # Save in ascending order by date
    df_to_save = df_to_save.sort_values('Date')

    df_to_save.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
    print(f"[CSV] Data saved: {CSV_FILE}")
    print(f"[CSV] total {len(df_to_save)} records")
    print(f"[CSV] Column name: {', '.join(df_to_save.columns.tolist())}")


# ==================== Data Overview ====================
def print_summary(df):
    """Print Data Overview"""
    print("\n" + "=" * 60)
    print(f"  {STOCK_NAME} ({STOCK_CODE}) Data Overview")
    print("=" * 60)
    print(f"  Data Range: {df['Date'].min().strftime('%Y-%m-%d')} ~ {df['Date'].max().strftime('%Y-%m-%d')}")
    print(f"  Number of trading days: {len(df)} days")
    print(f"  Open range: {df['Open'].min():.2f} ~ {df['Open'].max():.2f}")
    print(f"  Close range: {df['Close'].min():.2f} ~ {df['Close'].max():.2f}")
    print(f"  High range: {df['High'].min():.2f} ~ {df['High'].max():.2f}")
    print(f"  Low range: {df['Low'].min():.2f} ~ {df['Low'].max():.2f}")
    print(f"  Average daily volume: {df['Volume'].mean():,.0f} hand")
    print(f"  Average daily turnover: {df['Turnover'].mean():,.0f} CNY")
    print("=" * 60)

    # Before presentation5Line and after5row
    print("\nformer5Trading Day Data:")
    print(df.head(5).to_string(index=False))
    print("\nafter5Trading Day Data:")
    print(df.tail(5).to_string(index=False))


# ==================== Main program ====================
if __name__ == "__main__":
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"stock: {STOCK_NAME} ({STOCK_CODE})")
    print(f"Time range: {START_DATE} ~ {END_DATE}\n")

    # 1. Get data
    df = get_stock_data()

    # 2. Printing Overview
    print_summary(df)

    # 3. SaveCSV
    save_to_csv(df)

    # 4. Create a chart
    plot_close_price(df)

    print(f"\nCompletion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Task3All completed! ")
