#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股与港股代表性格股对比分析 —— K线图（蜡烛图）+ 多维度对比
使用 mplfinance 绘制标准K线图，覆盖沪深A股与港股
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ==================== 配置 ====================
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(OUTPUT_DIR, '..', '..', 'data', 'charts', 'task1')
DATA_DIR  = os.path.join(OUTPUT_DIR, '..', '..', 'data', 'csv')
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

END_DATE = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

# A股（沪深）
A_STOCKS = [
    {"code": "000001", "name": "平安银行", "sector": "银行金融", "market": "深交所主板"},
    {"code": "600519", "name": "贵州茅台", "sector": "白酒消费", "market": "上交所主板"},
    {"code": "002594", "name": "比亚迪",   "sector": "新能源汽车", "market": "深交所主板"},
    {"code": "601318", "name": "中国平安", "sector": "保险金融", "market": "上交所主板"},
    {"code": "300750", "name": "宁德时代", "sector": "电池储能", "market": "创业板"},
]

# 港股（香港联交所）
HK_STOCKS = [
    {"code": "00700", "name": "腾讯控股",   "sector": "互联网科技", "market": "恒生指数成分股"},
    {"code": "09988", "name": "阿里巴巴",   "sector": "电商云计算", "market": "恒生指数成分股"},
    {"code": "03690", "name": "美团",       "sector": "本地生活",   "market": "恒生指数成分股"},
    {"code": "00388", "name": "香港交易所", "sector": "金融基础设施", "market": "恒生指数成分股"},
    {"code": "00941", "name": "中国移动",   "sector": "电信运营",   "market": "恒生指数成分股"},
]

# 中文字体
plt.rcParams['font.sans-serif'] = ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.monospace'] = ['Heiti SC', 'STHeiti', 'sans-serif']

# ==================== 数据获取 ====================

def fetch_a_stock(code):
    """获取A股前复权日线数据"""
    import akshare as ak
    df = ak.stock_zh_a_hist(symbol=code, period='daily',
                            start_date=START_DATE, end_date=END_DATE, adjust='qfq')
    df = df.rename(columns={
        '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
        '最高': 'High', '最低': 'Low', '成交量': 'Volume',
        '成交额': 'Amount', '涨跌幅': 'PctChg', '换手率': 'Turnover',
    })
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


def fetch_hk_stock(code):
    """获取港股前复权日线数据"""
    import akshare as ak
    df = ak.stock_hk_hist(symbol=code, period='daily',
                          start_date=START_DATE, end_date=END_DATE, adjust='qfq')
    df = df.rename(columns={
        '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
        '最高': 'High', '最低': 'Low', '成交量': 'Volume',
        '成交额': 'Amount', '涨跌幅': 'PctChg',
    })
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df


# ==================== K线图绘制 (mplfinance) ====================

def plot_candlestick(df, title, save_path, stock_info, show_ma=True):
    """使用 mplfinance 绘制标准K线蜡烛图 + 成交量"""
    # 准备数据：mplfinance 需要 Date, Open, High, Low, Close, Volume 列
    ohlc_df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    ohlc_df = ohlc_df.set_index('Date')
    # 成交量单位转换（A股手->万股，港股股->万股）
    ohlc_df['Volume'] = ohlc_df['Volume'] / 10000

    # 计算均线
    if show_ma:
        ma20 = ohlc_df['Close'].rolling(20).mean()
        ma60 = ohlc_df['Close'].rolling(60).mean()

    # 自定义颜色方案：红涨绿跌（A股习惯）
    mc = mpf.make_marketcolors(
        up='red', down='green',
        edge='inherit', wick='inherit',
        volume={'up': 'red', 'down': 'green'},
        alpha=0.85
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle='--', gridaxis='both',
        facecolor='white', figcolor='white',
        y_on_right=False,
        rc={
            'font.sans-serif': ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif'],
            'font.monospace': ['Heiti SC', 'STHeiti', 'sans-serif'],
            'axes.unicode_minus': False,
        }
    )

    # 构建均线叠加
    add_plots = []
    if show_ma and len(df) >= 20:
        add_plots.append(mpf.make_addplot(ma20, color='#ff7f0e', width=1.0, linestyle='--', label='MA20'))
    if show_ma and len(df) >= 60:
        add_plots.append(mpf.make_addplot(ma60, color='#2ca02c', width=1.0, linestyle='--', label='MA60'))

    # 构建K线图
    chg = (ohlc_df['Close'].iloc[-1] - ohlc_df['Close'].iloc[0]) / ohlc_df['Close'].iloc[0] * 100
    subtitle = f"{stock_info['market']} | {stock_info['sector']} | 涨跌幅: {chg:+.2f}%"

    fig, axes = mpf.plot(
        ohlc_df,
        type='candle',          # 蜡烛图
        style=s,
        addplot=add_plots if add_plots else None,
        volume=True,            # 成交量副图
        title=title,
        ylabel='价格',
        ylabel_lower='成交量(万股)',
        figsize=(16, 9),
        panel_ratios=(3, 1),    # 主图:成交量 = 3:1
        returnfig=True,
        datetime_format='%Y-%m',
        xrotation=30,
        show_nontrading=False,
        warn_too_much_data=300,
    )

    # 添加副标题（统计信息）
    ax_main = axes[0]
    close = ohlc_df['Close']
    stats_lines = [
        f"{subtitle}",
        f"期初: {close.iloc[0]:.2f} → 期末: {close.iloc[-1]:.2f}",
        f"最高: {close.max():.2f}  最低: {close.min():.2f}",
        f"均值: {close.mean():.2f}  标准差: {close.std():.2f}",
        f"区间天数: {len(ohlc_df)} 交易日",
    ]
    stats_text = "\n".join(stats_lines)
    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.9)
    ax_main.text(0.98, 0.98, stats_text, transform=ax_main.transAxes,
                 fontsize=9, verticalalignment='top', horizontalalignment='right',
                 family='monospace', bbox=props)

    # 图例
    if add_plots:
        legend_labels = ['MA20', 'MA60'] if len(add_plots) == 2 else ['MA20']
        ax_main.legend(legend_labels, loc='upper left', fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [K线图] 已保存: {os.path.basename(save_path)}")


def plot_candlestick_recent(df, title, save_path, months=3):
    """绘制近N个月的K线图（放大细节）"""
    cutoff = df['Date'].max() - pd.DateOffset(months=months)
    df_recent = df[df['Date'] >= cutoff].copy()
    if len(df_recent) < 20:
        df_recent = df.tail(60).copy()

    ohlc_df = df_recent[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
    ohlc_df = ohlc_df.set_index('Date')
    ohlc_df['Volume'] = ohlc_df['Volume'] / 10000

    mc = mpf.make_marketcolors(
        up='red', down='green', edge='inherit', wick='inherit',
        volume={'up': 'red', 'down': 'green'}, alpha=0.85)
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', gridaxis='both',
                           facecolor='white', figcolor='white', y_on_right=False,
                           rc={'font.sans-serif': ['Heiti SC', 'STHeiti', 'PingFang SC', 'Arial Unicode MS', 'SimHei', 'sans-serif'],
                               'font.monospace': ['Heiti SC', 'STHeiti', 'sans-serif'],
                               'axes.unicode_minus': False})

    ma10 = ohlc_df['Close'].rolling(10).mean()
    ma30 = ohlc_df['Close'].rolling(30).mean()
    add_plots = [
        mpf.make_addplot(ma10, color='#ff7f0e', width=1.2, linestyle='--', label='MA10'),
        mpf.make_addplot(ma30, color='#2ca02c', width=1.2, linestyle='--', label='MA30'),
    ]

    fig, axes = mpf.plot(
        ohlc_df, type='candle', style=s, addplot=add_plots,
        volume=True, title=title, ylabel='价格', ylabel_lower='成交量(万股)',
        figsize=(16, 9), panel_ratios=(3, 1), returnfig=True,
        datetime_format='%m-%d', xrotation=30, show_nontrading=False,
        warn_too_much_data=300,
    )
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [K线图-近期] 已保存: {os.path.basename(save_path)}")


# ==================== 综合对比图 ====================

def plot_ah_comparison(a_data, hk_data):
    """A股 vs 港股 综合对比大图（4个子图）"""
    fig, axes = plt.subplots(2, 2, figsize=(20, 13))
    fig.suptitle('图2：A股与港股代表性格股综合对比分析', fontsize=18, fontweight='bold', y=0.99)

    colors_a = ['#d62728', '#c49c48', '#2ca02c', '#1f77b4', '#ff7f0e']
    colors_hk = ['#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']

    ax1, ax2, ax3, ax4 = axes[0,0], axes[0,1], axes[1,0], axes[1,1]

    # ── 子图1: A股归一化收盘价 ──
    for i, (name, df) in enumerate(a_data.items()):
        norm = df['Close'] / df['Close'].iloc[0] * 100
        ax1.plot(df['Date'], norm, color=colors_a[i], linewidth=1.4, label=name)
    ax1.axhline(y=100, color='gray', linestyle=':', alpha=0.4)
    ax1.set_title('(a) A股归一化收盘价（基准=100）', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8, ncol=2)
    ax1.set_ylabel('归一化价格', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    # ── 子图2: 港股归一化收盘价 ──
    for i, (name, df) in enumerate(hk_data.items()):
        norm = df['Close'] / df['Close'].iloc[0] * 100
        ax2.plot(df['Date'], norm, color=colors_hk[i], linewidth=1.4, label=name)
    ax2.axhline(y=100, color='gray', linestyle=':', alpha=0.4)
    ax2.set_title('(b) 港股归一化收盘价（基准=100）', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=8, ncol=2)
    ax2.set_ylabel('归一化价格', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)

    # ── 子图3: 涨跌幅对比 ──
    all_names = []
    all_chg = []
    all_colors = []
    all_markets = []
    for name, df in a_data.items():
        chg = (df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100
        all_names.append(f"{name} (A)")
        all_chg.append(chg)
        all_colors.append('#d62728' if chg < 0 else '#2ca02c')
        all_markets.append('A股')
    for name, df in hk_data.items():
        chg = (df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100
        all_names.append(f"{name} (HK)")
        all_chg.append(chg)
        all_colors.append('#e377c2' if chg < 0 else '#2ca02c')
        all_markets.append('港股')

    bars = ax3.barh(all_names[::-1], all_chg[::-1], color=all_colors[::-1],
                    height=0.55, edgecolor='white')
    ax3.axvline(x=0, color='black', linewidth=0.8)
    ax3.set_title('(c) 区间涨跌幅（%）', fontsize=14, fontweight='bold')
    for bar, val in zip(bars, all_chg[::-1]):
        offset = 0.3 if val >= 0 else -0.3
        ha = 'left' if val >= 0 else 'right'
        ax3.text(bar.get_width() + offset, bar.get_y() + bar.get_height()/2,
                 f'{val:+.1f}%', va='center', fontsize=9, ha=ha, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='x')

    # ── 子图4: A股 vs 港股 平均表现对比（箱型：涨跌幅范围） ──
    a_chg_list = []
    hk_chg_list = []
    for name, df in a_data.items():
        a_chg_list.append((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100)
    for name, df in hk_data.items():
        hk_chg_list.append((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100)

    ax4.bar([0.6, 1.6], [np.mean(a_chg_list), np.mean(hk_chg_list)],
            width=0.5, color=['#d62728', '#9467bd'], edgecolor='white',
            yerr=[np.std(a_chg_list), np.std(hk_chg_list)],
            capsize=10, error_kw={'linewidth': 2})
    # 散点叠加
    for v in a_chg_list:
        ax4.scatter(0.6 + np.random.uniform(-0.15, 0.15), v, color='#d62728', s=60, alpha=0.7, zorder=5)
    for v in hk_chg_list:
        ax4.scatter(1.6 + np.random.uniform(-0.15, 0.15), v, color='#9467bd', s=60, alpha=0.7, zorder=5)
    ax4.axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    ax4.set_xticks([0.6, 1.6])
    ax4.set_xticklabels(['A股样本\n(5只)', '港股样本\n(5只)'], fontsize=11)
    ax4.set_title('(d) 涨跌幅均值±标准差对比', fontsize=14, fontweight='bold')
    ax4.set_ylabel('区间涨跌幅（%）', fontsize=11)
    ax4.grid(True, alpha=0.3, axis='y')
    # 标注均值
    ax4.text(0.6, np.mean(a_chg_list) + 1, f'A股均值:\n{np.mean(a_chg_list):+.1f}%',
             ha='center', fontsize=10, fontweight='bold', color='#d62728')
    ax4.text(1.6, np.mean(hk_chg_list) + 1, f'港股均值:\n{np.mean(hk_chg_list):+.1f}%',
             ha='center', fontsize=10, fontweight='bold', color='#9467bd')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    save_path = os.path.join(CHART_DIR, "AH_comparison.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n[对比图] A股vs港股已保存: AH_comparison.png")
    return a_chg_list, hk_chg_list


# ==================== CSRC 统计汇总 ====================

def build_summary(a_data, hk_data):
    """构建A股+港股统计汇总表"""
    rows = []
    for name, df in a_data.items():
        close = df['Close']
        chg = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
        ret = close.pct_change()
        ann_vol = ret.std() * np.sqrt(252) * 100
        max_dd = ((close.cummax() - close) / close.cummax()).max() * 100
        rows.append({
            '市场': 'A股', '名称': name, '交易日': len(df),
            '期初': close.iloc[0], '期末': close.iloc[-1],
            '最高': close.max(), '最低': close.min(),
            '涨跌幅(%)': round(chg, 2), '年化波动(%)': round(ann_vol, 2),
            '最大回撤(%)': round(max_dd, 2),
        })
    for name, df in hk_data.items():
        close = df['Close']
        chg = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
        ret = close.pct_change()
        ann_vol = ret.std() * np.sqrt(252) * 100
        max_dd = ((close.cummax() - close) / close.cummax()).max() * 100
        rows.append({
            '市场': '港股', '名称': name, '交易日': len(df),
            '期初': close.iloc[0], '期末': close.iloc[-1],
            '最高': close.max(), '最低': close.min(),
            '涨跌幅(%)': round(chg, 2), '年化波动(%)': round(ann_vol, 2),
            '最大回撤(%)': round(max_dd, 2),
        })
    return pd.DataFrame(rows)


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("=" * 65)
    print("  A股 vs 港股 代表性格股K线图分析与对比")
    print(f"  时间范围: {START_DATE} ~ {END_DATE}")
    print("=" * 65)

    # ═══ 步骤1: 获取数据 ═══
    print("\n>>> 步骤1: 批量获取A股数据...")
    a_data = {}
    for s in A_STOCKS:
        try:
            a_data[s['name']] = fetch_a_stock(s['code'])
            print(f"  A股 {s['name']}({s['code']}): {len(a_data[s['name']])} 条")
        except Exception as e:
            print(f"  A股 {s['name']} 获取失败: {e}")

    print("\n>>> 步骤2: 批量获取港股数据...")
    hk_data = {}
    for s in HK_STOCKS:
        try:
            hk_data[s['name']] = fetch_hk_stock(s['code'])
            print(f"  港股 {s['name']}({s['code']}): {len(hk_data[s['name']])} 条")
        except Exception as e:
            print(f"  港股 {s['name']} 获取失败: {e}")

    # ═══ 步骤3: 绘制A股K线蜡烛图 ═══
    print("\n>>> 步骤3: 绘制A股K线蜡烛图 (mplfinance)...")
    for s in A_STOCKS:
        name = s['name']
        if name not in a_data:
            continue
        print(f"  正在绘制 {name}...")
        df = a_data[name]
        # 全年K线图
        title = f"{name}（{s['code']}）过去一年日K线图"
        save_path = os.path.join(CHART_DIR, f"{s['code']}_{name}_candle.png")
        plot_candlestick(df, title, save_path, s)

    # ═══ 步骤4: 绘制港股K线蜡烛图 ═══
    print("\n>>> 步骤4: 绘制港股K线蜡烛图 (mplfinance)...")
    for s in HK_STOCKS:
        name = s['name']
        if name not in hk_data:
            continue
        print(f"  正在绘制 {name}...")
        df = hk_data[name]
        title = f"{name}（{s['code']}.HK）过去一年日K线图"
        save_path = os.path.join(CHART_DIR, f"{s['code']}_{name}_candle.png")
        plot_candlestick(df, title, save_path, s)

    # ═══ 步骤5: 选两只代表性股票画近期K线细节 ═══
    print("\n>>> 步骤5: 绘制近期K线细节放大图...")
    # A股代表：宁德时代
    if '宁德时代' in a_data:
        df = a_data['宁德时代']
        title = '宁德时代（300750）近3个月日K线图'
        save_path = os.path.join(CHART_DIR, "300750_宁德时代_recent_candle.png")
        plot_candlestick_recent(df, title, save_path, months=3)
    # 港股代表：腾讯控股
    if '腾讯控股' in hk_data:
        df = hk_data['腾讯控股']
        title = '腾讯控股（00700.HK）近3个月日K线图'
        save_path = os.path.join(CHART_DIR, "00700_腾讯控股_recent_candle.png")
        plot_candlestick_recent(df, title, save_path, months=3)

    # ═══ 步骤6: A股vs港股综合对比 ═══
    print("\n>>> 步骤6: 绘制A股vs港股综合对比图...")
    a_chgs, hk_chgs = plot_ah_comparison(a_data, hk_data)

    # ═══ 步骤7: 统计汇总 ═══
    print("\n>>> 步骤7: 生成统计汇总表...")
    summary = build_summary(a_data, hk_data)
    summary_path = os.path.join(DATA_DIR, "AH_summary.csv")
    summary.to_csv(summary_path, index=False, encoding='utf-8-sig')
    print(summary.to_string(index=False))
    print(f"\n统计汇总已保存: AH_summary.csv")

    # ═══ 步骤8: 保存CSV ═══
    print("\n>>> 步骤8: 保存所有个股CSV...")
    all_stocks = [(A_STOCKS, a_data, 'A股'), (HK_STOCKS, hk_data, '港股')]
    for stock_list, data_dict, mkt in all_stocks:
        for s in stock_list:
            name = s['name']
            if name in data_dict:
                df_out = data_dict[name].copy()
                df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')
                csv_path = os.path.join(DATA_DIR, f"{s['code']}_{name}_{mkt}_daily.csv")
                df_out.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"  [{mkt}股] {name} → {os.path.basename(csv_path)}")

    print("\n" + "=" * 65)
    print(f"  全部完成！")
    print(f"  A股 {len(a_data)} 只 + 港股 {len(hk_data)} 只，共 {len(a_data)+len(hk_data)} 只股票")
    print(f"  • 10 张K线蜡烛图（含2张近期细节放大图）")
    print(f"  • 1 张A股vs港股综合对比图")
    print(f"  • 1 份统计汇总表 + 10 份个股CSV")
    print("=" * 65)
