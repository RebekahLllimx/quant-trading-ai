#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多只沪深A股数据获取、可视化与分析
使用 Tushare Pro API，覆盖沪市主板、深市主板、创业板等不同板块
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import tushare as ts

# ==================== 配置 ====================
# 从 config.py 读取 Tushare Token（config.py 已被 gitignore 排除）
try:
    from config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = ""  # 未配置则仅使用 AKShare

# 精选5只代表不同行业和板块的沪深A股
STOCKS = [
    {"code": "000001", "name": "平安银行", "sector": "银行金融", "market": "深交所主板"},
    {"code": "600519", "name": "贵州茅台", "sector": "白酒消费", "market": "上交所主板"},
    {"code": "002594", "name": "比亚迪",   "sector": "新能源汽车", "market": "深交所主板"},
    {"code": "601318", "name": "中国平安", "sector": "保险金融", "market": "上交所主板"},
    {"code": "300750", "name": "宁德时代", "sector": "电池储能", "market": "创业板"},
]

END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(OUTPUT_DIR, '..', '..', 'data', 'charts', 'task1')
DATA_DIR  = os.path.join(OUTPUT_DIR, '..', '..', 'data', 'csv')
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
CHART_COMPARE = os.path.join(CHART_DIR, "multi_stock_compare.png")

# 中文字体
plt.rcParams['font.sans-serif'] = ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']


def fetch_stock_data(code):
    """获取股票前复权日线数据（AKShare前复权，Tushare备用）"""
    # 方案A：AKShare 前复权（正确处理除权除息）
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code, period='daily',
                                start_date=START_DATE, end_date=END_DATE, adjust='qfq')
        if df is not None and len(df) > 0:
            df = df.rename(columns={
                '日期': 'trade_date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'vol', '成交额': 'amount',
                '涨跌幅': 'pct_chg', '涨跌额': 'change', '换手率': 'turnover',
                '股票代码': 'ts_code', '振幅': 'amplitude',
            })
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date').reset_index(drop=True)
            print(f"  正在获取 {code} (AKShare前复权)...", end=" ")
            print(f"{len(df)} 条记录")
            return df
    except Exception as e:
        print(f"  AKShare失败({str(e)[:50]})，回退至Tushare...", end=" ")

    # 方案B：Tushare Pro
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    if code.startswith(('6', '9')):
        ts_code = f"{code}.SH"
    else:
        ts_code = f"{code}.SZ"

    df = pro.daily(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
    df = df.sort_values('trade_date').reset_index(drop=True)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    print(f"{len(df)} 条记录 (Tushare)")
    return df


def normalize_price_series(df, base=100):
    """将收盘价序列归一化为基准值（用于多股对比）"""
    return df['close'] / df['close'].iloc[0] * base


def plot_multi_stock_comparison(stocks_data):
    """多股对比图：4个子图"""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('图2：多只沪深A股过去一年走势对比分析', fontsize=16, fontweight='bold', y=0.98)

    colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd']
    ax1, ax2, ax3, ax4 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # ── 子图1：归一化收盘价对比（所有股票从同一基准100出发）──
    for i, (s, df) in enumerate(stocks_data.items()):
        norm = normalize_price_series(df, base=100)
        ax1.plot(df['trade_date'], norm, color=colors[i], linewidth=1.4, label=f"{s}({list(df['ts_code'])[0][:6]})")
    ax1.axhline(y=100, color='gray', linestyle=':', alpha=0.5)
    ax1.set_title('(a) 归一化收盘价对比（基准=100）', fontsize=13, fontweight='bold')
    ax1.set_ylabel('归一化价格', fontsize=11)
    ax1.legend(loc='upper left', fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    # ── 子图2：实际收盘价走势 ──
    for i, (s, df) in enumerate(stocks_data.items()):
        ax2.plot(df['trade_date'], df['close'], color=colors[i], linewidth=1.2, alpha=0.85, label=s)
    ax2.set_title('(b) 实际收盘价走势', fontsize=13, fontweight='bold')
    ax2.set_ylabel('收盘价（元）', fontsize=11)
    ax2.legend(loc='upper right', fontsize=8, ncol=2)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    # ── 子图3：区间涨跌幅柱状图 ──
    stocks_names = []
    changes_pct = []
    bar_colors = []
    for i, (s, df) in enumerate(stocks_data.items()):
        stocks_names.append(s)
        chg = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100
        changes_pct.append(chg)
        bar_colors.append('#d62728' if chg < 0 else '#2ca02c')

    bars = ax3.barh(stocks_names[::-1], changes_pct[::-1], color=bar_colors[::-1], height=0.5, edgecolor='white')
    ax3.axvline(x=0, color='black', linewidth=0.8)
    ax3.set_title('(c) 区间涨跌幅（%）', fontsize=13, fontweight='bold')
    ax3.set_xlabel('涨跌幅（%）', fontsize=11)
    for bar, val in zip(bars, changes_pct[::-1]):
        ax3.text(bar.get_width() + (0.3 if val >= 0 else -0.3), bar.get_y() + bar.get_height()/2,
                 f'{val:+.1f}%', va='center', fontsize=10,
                 ha='left' if val >= 0 else 'right', fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='x')
    ax3.tick_params(axis='y', labelsize=10)

    # ── 子图4：波动率（标准差）对比 ──
    vol_stocks = []
    std_values = []
    for i, (s, df) in enumerate(stocks_data.items()):
        vol_stocks.append(s)
        # 用日收益率标准差（年化）= 日收益标准差 * sqrt(252)
        df_copy = df.copy()
        df_copy['return'] = df_copy['close'].pct_change()
        daily_std = df_copy['return'].std()
        annual_std = daily_std * (252 ** 0.5) * 100  # 年化波动率(%)
        std_values.append(annual_std)

    bars2 = ax4.barh(vol_stocks[::-1], std_values[::-1],
                     color=['#ff7f0e' if v > 30 else '#1f77b4' for v in std_values[::-1]],
                     height=0.5, edgecolor='white')
    ax4.set_title('(d) 年化波动率（%）', fontsize=13, fontweight='bold')
    ax4.set_xlabel('年化波动率（%）', fontsize=11)
    for bar, val in zip(bars2, std_values[::-1]):
        ax4.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                 f'{val:.1f}%', va='center', fontsize=10, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='x')
    ax4.tick_params(axis='y', labelsize=10)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(CHART_COMPARE, dpi=150, bbox_inches='tight')
    print(f"\n[绘图] 多股对比图已保存至: {CHART_COMPARE}")
    plt.close()


def plot_individual_charts(stocks_data, stocks_info):
    """为每只股票单独绘制K线图"""
    chart_paths = {}
    for s_name, df in stocks_data.items():
        info = stocks_info[s_name]

        fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'图：{s_name}（{info["code"]}）过去一年日线走势',
                     fontsize=14, fontweight='bold')

        dates = df['trade_date']
        close_p = df['close']

        # 上：收盘价 + 均线
        ax1 = axes[0]
        ax1.plot(dates, close_p, color='#1f77b4', linewidth=1.2, label='收盘价')
        if len(df) >= 20:
            ma20 = close_p.rolling(20).mean()
            ax1.plot(dates, ma20, color='#ff7f0e', linewidth=1.0, linestyle='--', alpha=0.8, label='MA20')
        if len(df) >= 60:
            ma60 = close_p.rolling(60).mean()
            ax1.plot(dates, ma60, color='#2ca02c', linewidth=1.0, linestyle='--', alpha=0.8, label='MA60')

        # 高低点标注
        max_idx = close_p.idxmax()
        min_idx = close_p.idxmin()
        ax1.annotate(f'{close_p[max_idx]:.2f}', xy=(dates[max_idx], close_p[max_idx]),
                     fontsize=8, color='red', fontweight='bold', ha='center', va='bottom')
        ax1.annotate(f'{close_p[min_idx]:.2f}', xy=(dates[min_idx], close_p[min_idx]),
                     fontsize=8, color='green', fontweight='bold', ha='center', va='top')

        # 统计面板（右上角）
        chg_pct = (close_p.iloc[-1] - close_p.iloc[0]) / close_p.iloc[0] * 100
        stats = (f"区间: {dates.iloc[0].strftime('%Y-%m-%d')} ~ {dates.iloc[-1].strftime('%Y-%m-%d')}\n"
                 f"交易天数: {len(df)}\n"
                 f"期初: {close_p.iloc[0]:.2f}  期末: {close_p.iloc[-1]:.2f}\n"
                 f"最高: {close_p.max():.2f}  最低: {close_p.min():.2f}\n"
                 f"均值: {close_p.mean():.2f}  标准差: {close_p.std():.2f}\n"
                 f"涨跌幅: {chg_pct:+.2f}%")
        props = dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.85)
        ax1.text(0.98, 0.98, stats, transform=ax1.transAxes, fontsize=8,
                 verticalalignment='top', horizontalalignment='right',
                 family='monospace', bbox=props)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.set_ylabel('价格（元）', fontsize=11)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

        # 下：成交量
        ax2 = axes[1]
        vol = df['vol'] / 10000  # 手转万手
        colors_vol = ['#d62728' if df['close'].iloc[i] >= df['open'].iloc[i] else '#2ca02c'
                      for i in range(len(df))]
        ax2.bar(dates, vol, color=colors_vol, alpha=0.6, width=1)
        ax2.set_ylabel('成交量（万手）', fontsize=11)
        ax2.set_xlabel('日期', fontsize=11)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

        chart_path = os.path.join(CHART_DIR, f"{info['code']}_{s_name}_chart.png")
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        chart_paths[s_name] = chart_path
        print(f"[绘图] {s_name} 个股图已保存: {chart_path}")

    return chart_paths


def build_statistics_table(stocks_data, stocks_info):
    """生成统计汇总 DataFrame"""
    rows = []
    for s_name, df in stocks_data.items():
        info = stocks_info[s_name]
        close_p = df['close']
        chg = (close_p.iloc[-1] - close_p.iloc[0]) / close_p.iloc[0] * 100
        df_copy = df.copy()
        df_copy['ret'] = close_p.pct_change()
        daily_std = df_copy['ret'].std()
        annual_vol = daily_std * (252 ** 0.5) * 100
        max_dd = (close_p.cummax() - close_p).max() / close_p.cummax().max() * 100

        rows.append({
            '股票名称': s_name,
            '代码': info['code'],
            '行业': info['sector'],
            '板块': info['market'],
            '交易日数': len(df),
            '期初收盘价': f"{close_p.iloc[0]:.2f}",
            '期末收盘价': f"{close_p.iloc[-1]:.2f}",
            '区间最高': f"{close_p.max():.2f}",
            '区间最低': f"{close_p.min():.2f}",
            '区间涨跌幅(%)': f"{chg:+.2f}",
            '年化波动率(%)': f"{annual_vol:.2f}",
            '最大回撤(%)': f"{max_dd:.2f}",
            '日均成交量(万手)': f"{df['vol'].mean()/10000:,.0f}",
        })
    return pd.DataFrame(rows)


def save_csv_files(stocks_data, stocks_info):
    """保存每只股票的CSV"""
    for s_name, df in stocks_data.items():
        info = stocks_info[s_name]
        csv_path = os.path.join(DATA_DIR, f"{info['code']}_{s_name}_daily.csv")
        df_out = df.copy()
        df_out['trade_date'] = df_out['trade_date'].dt.strftime('%Y-%m-%d')
        df_out.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"[CSV] {s_name} 数据已保存: {csv_path}")


# ==================== 主程序 ====================
if __name__ == "__main__":
    print("=" * 65)
    print("  多只沪深A股历史交易数据批量获取与分析")
    print(f"  时间范围: {START_DATE} ~ {END_DATE}")
    print("=" * 65)

    # 1. 批量获取数据
    stocks_data = {}
    stocks_info = {}
    print("\n>>> 步骤1: 批量获取数据")
    for stock in STOCKS:
        code = stock["code"]
        name = stock["name"]
        stocks_info[name] = stock
        try:
            stocks_data[name] = fetch_stock_data(code)
        except Exception as e:
            print(f"  获取失败: {e}")

    print(f"\n成功获取 {len(stocks_data)}/{len(STOCKS)} 只股票数据")

    # 2. 保存CSV
    print("\n>>> 步骤2: 保存CSV文件")
    save_csv_files(stocks_data, stocks_info)

    # 3. 生成统计汇总表
    print("\n>>> 步骤3: 统计汇总")
    stats_df = build_statistics_table(stocks_data, stocks_info)
    stats_csv = os.path.join(DATA_DIR, "multi_stock_summary.csv")
    stats_df.to_csv(stats_csv, index=False, encoding='utf-8-sig')
    print(stats_df.to_string(index=False))
    print(f"\n统计汇总已保存: {stats_csv}")

    # 4. 绘制多股对比图
    print("\n>>> 步骤4: 绘制多股对比图")
    plot_multi_stock_comparison(stocks_data)

    # 5. 绘制个股图
    print("\n>>> 步骤5: 绘制个股走势图")
    individual_charts = plot_individual_charts(stocks_data, stocks_info)

    print("\n" + "=" * 65)
    print("  全部完成！共生成：")
    print(f"  • {len(stocks_data)} 只股票的 CSV 数据文件")
    print(f"  • {len(stocks_data)} 张个股走势图")
    print("  • 1 张多股对比图")
    print("  • 1 份统计汇总表")
    print("=" * 65)
