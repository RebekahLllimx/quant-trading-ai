#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务3：获取沪深股市股票交易数据、绘制收盘价曲线图、保存CSV
使用 Tushare Pro API（主方案）+ akshare（备选方案）
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# ==================== 配置区域 ====================
# 从 config.py 读取 Tushare Token（config.py 已被 gitignore 排除）
# 复制 config.example.py 为 config.py 并填入真实 Token
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = ""  # 未配置则仅使用 AKShare

# 股票代码（示例：000001.SZ = 平安银行, 600519.SH = 贵州茅台）
STOCK_CODE = "000001"       # 股票代码（不带交易所后缀）
STOCK_NAME = "平安银行"     # 股票名称

# 数据时间范围：过去一年
END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

# 输出文件路径（输出到 ../data/ 和 ../data/charts/）
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(OUTPUT_DIR, '..', 'data')
CHART_DIR = os.path.join(OUTPUT_DIR, '..', 'data', 'charts')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)
CSV_FILE = os.path.join(DATA_DIR, f"{STOCK_CODE}_{STOCK_NAME}_A股_daily.csv")
CHART_FILE = os.path.join(CHART_DIR, f"{STOCK_CODE}_{STOCK_NAME}_close_price.png")

# ==================== 方案A：使用 Tushare Pro ====================
def fetch_data_tushare():
    """使用 Tushare Pro API 获取股票日线数据"""
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()

        # 拼接交易所后缀：深交所 .SZ，上交所 .SH
        if STOCK_CODE.startswith(('6', '9')):
            ts_code = f"{STOCK_CODE}.SH"
        else:
            ts_code = f"{STOCK_CODE}.SZ"

        print(f"[Tushare] 正在获取 {ts_code} ({STOCK_NAME}) 的数据...")
        print(f"[Tushare] 时间范围: {START_DATE} ~ {END_DATE}")

        # 获取日线行情数据
        df = pro.daily(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)

        if df is None or df.empty:
            raise ValueError("Tushare 返回空数据，请检查 Token 是否有效")

        # 按日期升序排列
        df = df.sort_values('trade_date').reset_index(drop=True)

        # 重命名列为中文
        df = df.rename(columns={
            'trade_date': '日期',
            'ts_code': '股票代码',
            'open': '开盘价',
            'high': '最高价',
            'low': '最低价',
            'close': '收盘价',
            'pre_close': '前收盘价',
            'change': '涨跌额',
            'pct_chg': '涨跌幅',
            'vol': '成交量(手)',
            'amount': '成交额(千元)',
        })

        # 数据类型转换
        df['日期'] = pd.to_datetime(df['日期'])
        df['成交量(手)'] = df['成交量(手)'].astype(float)
        df['成交额(千元)'] = df['成交额(千元)'].astype(float)

        print(f"[Tushare] 成功获取 {len(df)} 条交易数据")
        return df

    except Exception as e:
        print(f"[Tushare] 获取失败: {e}")
        return None


# ==================== 方案B：使用 akshare（免费免注册） ====================
def fetch_data_akshare():
    """使用 akshare 获取股票日线数据（免费无需注册）"""
    try:
        import akshare as ak

        print(f"[AKShare] 正在获取 {STOCK_CODE} ({STOCK_NAME}) 的数据...")
        print(f"[AKShare] 时间范围: {START_DATE} ~ {END_DATE}")

        # 获取A股历史日线数据（前复权）
        df = ak.stock_zh_a_hist(
            symbol=STOCK_CODE,
            period='daily',
            start_date=START_DATE,
            end_date=END_DATE,
            adjust='qfq'  # 前复权
        )

        if df is None or df.empty:
            raise ValueError("AKShare 返回空数据")

        # 重命名列为中文标准名称
        df = df.rename(columns={
            '日期': '日期',
            '股票代码': '股票代码',
            '开盘': '开盘价',
            '最高': '最高价',
            '最低': '最低价',
            '收盘': '收盘价',
            '成交量': '成交量(手)',
            '成交额': '成交额',
            '振幅': '振幅',
            '涨跌幅': '涨跌幅',
            '涨跌额': '涨跌额',
            '换手率': '换手率',
        })

        # 日期转换
        df['日期'] = pd.to_datetime(df['日期'])

        # 保留核心列
        core_cols = ['日期', '股票代码', '开盘价', '最高价', '最低价', '收盘价',
                     '成交量(手)', '成交额', '涨跌幅', '涨跌额', '换手率']
        df = df[core_cols]

        print(f"[AKShare] 成功获取 {len(df)} 条交易数据")
        return df

    except Exception as e:
        print(f"[AKShare] 获取失败: {e}")
        return None


# ==================== 数据获取（自动选择可用方案） ====================
def get_stock_data():
    """获取股票数据，优先使用 Tushare，不可用时回退到 akshare"""
    df = None

    # 尝试 Tushare（仅当用户已配置 Token）
    if TUSHARE_TOKEN and TUSHARE_TOKEN not in ("YOUR_TUSHARE_TOKEN_HERE", ""):
        print(">>> 尝试使用 Tushare Pro API...")
        df = fetch_data_tushare()

    # 回退到 akshare
    if df is None:
        print(">>> 使用 AKShare（免费数据源）...")
        df = fetch_data_akshare()

    if df is None or df.empty:
        raise RuntimeError("所有数据源均获取失败，请检查网络连接")

    return df


# ==================== 绘制收盘价曲线图 ====================
def plot_close_price(df):
    """绘制每日收盘价曲线图，并标注关键统计信息"""
    # 设置中文字体（macOS 系统字体）
    plt.rcParams['font.sans-serif'] = ['Heiti SC', 'STHeiti', 'PingFang SC',
                                        'Arial Unicode MS', 'SimHei', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    # 修复 DejaVu Sans Mono 无法显示中文的问题
    plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']

    fig, ax = plt.subplots(figsize=(14, 7))

    dates = df['日期']
    close_prices = df['收盘价']

    # 绘制收盘价曲线
    ax.plot(dates, close_prices, color='#1f77b4', linewidth=1.5,
            marker='', markersize=2, label='每日收盘价')

    # 添加移动平均线
    if len(df) >= 20:
        ma20 = close_prices.rolling(window=20).mean()
        ax.plot(dates, ma20, color='#ff7f0e', linewidth=1.2, linestyle='--',
                alpha=0.8, label='20日均线')

    if len(df) >= 60:
        ma60 = close_prices.rolling(window=60).mean()
        ax.plot(dates, ma60, color='#2ca02c', linewidth=1.2, linestyle='--',
                alpha=0.8, label='60日均线')

    # 标注最高点和最低点
    max_idx = close_prices.idxmax()
    min_idx = close_prices.idxmin()
    ax.annotate(f'最高: {close_prices[max_idx]:.2f}',
                xy=(dates[max_idx], close_prices[max_idx]),
                xytext=(0, 15), textcoords='offset points',
                fontsize=9, color='red', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='red', alpha=0.6),
                ha='center')

    ax.annotate(f'最低: {close_prices[min_idx]:.2f}',
                xy=(dates[min_idx], close_prices[min_idx]),
                xytext=(0, -20), textcoords='offset points',
                fontsize=9, color='green', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='green', alpha=0.6),
                ha='center')

    # 图表格式
    ax.set_xlabel('日期', fontsize=12)
    ax.set_ylabel('收盘价（元）', fontsize=12)
    ax.set_title(f'图1：{STOCK_NAME}（{STOCK_CODE}）过去一年每日收盘价走势图',
                 fontsize=14, fontweight='bold')

    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')

    # 日期格式
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # 添加统计信息文本框
    stats_text = (
        f"数据区间: {dates.iloc[0].strftime('%Y-%m-%d')} ~ {dates.iloc[-1].strftime('%Y-%m-%d')}\n"
        f"交易天数: {len(df)} 天\n"
        f"期初收盘价: {close_prices.iloc[0]:.2f} 元\n"
        f"期末收盘价: {close_prices.iloc[-1]:.2f} 元\n"
        f"最高收盘价: {close_prices.max():.2f} 元\n"
        f"最低收盘价: {close_prices.min():.2f} 元\n"
        f"均值: {close_prices.mean():.2f} 元\n"
        f"标准差: {close_prices.std():.2f} 元\n"
    )
    # 计算涨跌幅
    change_pct = (close_prices.iloc[-1] - close_prices.iloc[0]) / close_prices.iloc[0] * 100
    stats_text += f"区间涨跌幅: {change_pct:+.2f}%"

    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8)
    # 统计分析放在右上角，图例在左上角，互不遮挡
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right',
            family='monospace', bbox=props)

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=150, bbox_inches='tight')
    print(f"[绘图] 收盘价曲线图已保存至: {CHART_FILE}")
    plt.close()


# ==================== 保存CSV数据 ====================
def save_to_csv(df):
    """将数据保存为CSV文件"""
    # 格式化日期列
    df_to_save = df.copy()
    df_to_save['日期'] = df_to_save['日期'].dt.strftime('%Y-%m-%d')

    # 按日期升序保存
    df_to_save = df_to_save.sort_values('日期')

    df_to_save.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
    print(f"[CSV] 数据已保存至: {CSV_FILE}")
    print(f"[CSV] 共 {len(df_to_save)} 条记录")
    print(f"[CSV] 列名: {', '.join(df_to_save.columns.tolist())}")


# ==================== 数据概览 ====================
def print_summary(df):
    """打印数据概览"""
    print("\n" + "=" * 60)
    print(f"  {STOCK_NAME}（{STOCK_CODE}）数据概览")
    print("=" * 60)
    print(f"  数据范围: {df['日期'].min().strftime('%Y-%m-%d')} ~ {df['日期'].max().strftime('%Y-%m-%d')}")
    print(f"  交易日数: {len(df)} 天")
    print(f"  开盘价范围: {df['开盘价'].min():.2f} ~ {df['开盘价'].max():.2f}")
    print(f"  收盘价范围: {df['收盘价'].min():.2f} ~ {df['收盘价'].max():.2f}")
    print(f"  最高价范围: {df['最高价'].min():.2f} ~ {df['最高价'].max():.2f}")
    print(f"  最低价范围: {df['最低价'].min():.2f} ~ {df['最低价'].max():.2f}")
    print(f"  日成交量均值: {df['成交量(手)'].mean():,.0f} 手")
    # 找到成交额列（Tushare: '成交额(千元)', AKShare: '成交额'）
    amount_col = '成交额(千元)' if '成交额(千元)' in df.columns else '成交额'
    print(f"  日成交额均值: {df[amount_col].mean():,.0f} 元")
    print("=" * 60)

    # 展示前5行和后5行
    print("\n前5个交易日数据:")
    print(df.head(5).to_string(index=False))
    print("\n后5个交易日数据:")
    print(df.tail(5).to_string(index=False))


# ==================== 主程序 ====================
if __name__ == "__main__":
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"股票: {STOCK_NAME} ({STOCK_CODE})")
    print(f"时间范围: {START_DATE} ~ {END_DATE}\n")

    # 1. 获取数据
    df = get_stock_data()

    # 2. 打印概览
    print_summary(df)

    # 3. 保存CSV
    save_to_csv(df)

    # 4. 绘制图表
    plot_close_price(df)

    print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("任务3全部完成！")
