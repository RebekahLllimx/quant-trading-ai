#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标计算模块
支持 8 个指标: RSI, MACD, Bollinger Bands, ATR, KDJ, MA, CCI, ADX
所有函数接收 pandas DataFrame (需包含 Date, Open, High, Low, Close, Volume 列)
返回原始 DataFrame 附加指标列，或直接返回指标序列。
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _ema(series: pd.Series, period: int) -> pd.Series:
    """指数移动平均 (EMA)，α = 2/(N+1)"""
    return series.ewm(span=period, min_periods=period, adjust=False).mean()


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder 平滑 (α = 1/N)，用于 RSI/ATR/ADX"""
    return series.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    """简单移动平均"""
    return series.rolling(window=period, min_periods=period).mean()


def _std(series: pd.Series, period: int) -> pd.Series:
    """滚动标准差"""
    return series.rolling(window=period, min_periods=period).std(ddof=0)


# ═══════════════════════════════════════════════════════════════
# 1. RSI — 相对强弱指数
# ═══════════════════════════════════════════════════════════════

def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    计算 RSI (Relative Strength Index)

    参数:
        df: 包含 Close 列的 DataFrame
        period: 计算周期，默认 14 (Wilder 原始参数)

    返回:
        pd.Series: RSI 序列 [0, 100]
    """
    close = df['Close'].astype(float)
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # 种子: 前 N 期的 SMA
    avg_gain = gain.copy()
    avg_loss = loss.copy()

    # Wilder 平滑: α = 1/N
    avg_gain.iloc[period:] = gain.iloc[period:].ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss.iloc[period:] = loss.iloc[period:].ewm(alpha=1.0 / period, adjust=False).mean()

    # 初始种子用 SMA
    avg_gain.iloc[:period] = np.nan
    avg_loss.iloc[:period] = np.nan

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi.name = 'RSI'

    return rsi.round(4)


# ═══════════════════════════════════════════════════════════════
# 2. MACD — 指数平滑异同移动平均线
# ═══════════════════════════════════════════════════════════════

def calc_macd(df: pd.DataFrame,
              fast: int = 12,
              slow: int = 26,
              signal: int = 9) -> pd.DataFrame:
    """
    计算 MACD

    参数:
        df: 包含 Close 列的 DataFrame
        fast: 快线 EMA 周期，默认 12
        slow: 慢线 EMA 周期，默认 26
        signal: 信号线 EMA 周期，默认 9

    返回:
        pd.DataFrame: 包含 DIF, DEA, BAR 三列
    """
    close = df['Close'].astype(float)

    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)

    dif = ema_fast - ema_slow
    dea = _ema(dif, signal)
    bar = 2.0 * (dif - dea)

    result = pd.DataFrame({
        'DIF': dif.round(4),
        'DEA': dea.round(4),
        'BAR': bar.round(4),
    })
    return result


# ═══════════════════════════════════════════════════════════════
# 3. Bollinger Bands — 布林带
# ═══════════════════════════════════════════════════════════════

def calc_bollinger(df: pd.DataFrame,
                   period: int = 20,
                   k: float = 2.0) -> pd.DataFrame:
    """
    计算布林带 (Bollinger Bands)

    参数:
        df: 包含 Close 列的 DataFrame
        period: 中轨周期，默认 20
        k: 标准差倍数，默认 2.0

    返回:
        pd.DataFrame: 包含 MID, UP, DN, BandWidth, %b 五列
    """
    close = df['Close'].astype(float)

    mid = _sma(close, period)
    sigma = _std(close, period)

    up = mid + k * sigma
    dn = mid - k * sigma
    bandwidth = (up - dn) / mid * 100.0
    pct_b = (close - dn) / (up - dn)

    result = pd.DataFrame({
        'MID': mid.round(4),
        'UP': up.round(4),
        'DN': dn.round(4),
        'BandWidth': bandwidth.round(4),
        'PctB': pct_b.round(4),
    })
    return result


# ═══════════════════════════════════════════════════════════════
# 4. ATR — 平均真实波幅
# ═══════════════════════════════════════════════════════════════

def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    计算 ATR (Average True Range)

    参数:
        df: 包含 High, Low, Close 列的 DataFrame
        period: 计算周期，默认 14

    返回:
        pd.Series: ATR 序列
    """
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)
    close_prev = close.shift(1)

    tr = pd.concat([
        (high - low),
        (high - close_prev).abs(),
        (low - close_prev).abs(),
    ], axis=1).max(axis=1)

    atr = _wilder_smooth(tr, period)
    atr.name = 'ATR'
    return atr.round(4)


# ═══════════════════════════════════════════════════════════════
# 5. KDJ — 随机指标
# ═══════════════════════════════════════════════════════════════

def calc_kdj(df: pd.DataFrame,
             period: int = 9,
             smooth_k: int = 3,
             smooth_d: int = 3) -> pd.DataFrame:
    """
    计算 KDJ 随机指标

    参数:
        df: 包含 High, Low, Close 列的 DataFrame
        period: RSV 计算周期，默认 9
        smooth_k: K 值平滑周期，默认 3 (EMA 等效)
        smooth_d: D 值平滑周期，默认 3 (EMA 等效)

    返回:
        pd.DataFrame: 包含 K, D, J 三列 [0, 100]，J 可超出范围
    """
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)

    low_n = low.rolling(window=period, min_periods=period).min()
    high_n = high.rolling(window=period, min_periods=period).max()

    rsv = (close - low_n) / (high_n - low_n) * 100.0
    rsv = rsv.clip(0, 100)

    # K = EMA(RSV, smooth_k), D = EMA(K, smooth_d)
    k = _ema(rsv, smooth_k)
    d = _ema(k, smooth_d)
    j = 3.0 * k - 2.0 * d

    result = pd.DataFrame({
        'K': k.round(4),
        'D': d.round(4),
        'J': j.round(4),
    })
    return result


# ═══════════════════════════════════════════════════════════════
# 6. MA — 多周期移动平均线
# ═══════════════════════════════════════════════════════════════

def calc_ma(df: pd.DataFrame,
            periods: List[int] = [5, 10, 20, 60, 120, 250],
            ma_type: str = 'SMA') -> pd.DataFrame:
    """
    计算多周期移动平均线

    参数:
        df: 包含 Close 列的 DataFrame
        periods: 周期列表，默认 [5, 10, 20, 60, 120, 250]
        ma_type: 'SMA' (简单) 或 'EMA' (指数)

    返回:
        pd.DataFrame: 列名为 MA{N} 的 DataFrame
    """
    close = df['Close'].astype(float)
    result = pd.DataFrame(index=df.index)

    calc_fn = _sma if ma_type == 'SMA' else _ema

    for p in periods:
        result[f'MA{p}'] = calc_fn(close, p).round(4)

    return result


# ═══════════════════════════════════════════════════════════════
# 7. CCI — 商品通道指数
# ═══════════════════════════════════════════════════════════════

def calc_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    计算 CCI (Commodity Channel Index)

    参数:
        df: 包含 High, Low, Close 列的 DataFrame
        period: 计算周期，默认 20

    返回:
        pd.Series: CCI 序列 (无界)
    """
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)

    tp = (high + low + close) / 3.0
    ma_tp = _sma(tp, period)
    md = (tp - ma_tp).abs().rolling(window=period, min_periods=period).mean()

    cci = (tp - ma_tp) / (0.015 * md)
    cci.name = 'CCI'
    return cci.round(4)


# ═══════════════════════════════════════════════════════════════
# 8. ADX — 平均趋向指数
# ═══════════════════════════════════════════════════════════════

def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算 ADX / +DI / -DI (Wilder 趋向运动系统)

    参数:
        df: 包含 High, Low, Close 列的 DataFrame
        period: 计算周期，默认 14

    返回:
        pd.DataFrame: 包含 ADX, PDI(+DI), MDI(-DI) 三列
    """
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)

    # 第一步: 计算 True Range
    tr = pd.concat([
        (high - low),
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    # 第二步: 计算趋向运动 (+DM, -DM)
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)

    mask_plus = (up_move > down_move) & (up_move > 0)
    mask_minus = (down_move > up_move) & (down_move > 0)

    plus_dm[mask_plus] = up_move[mask_plus]
    minus_dm[mask_minus] = down_move[mask_minus]

    # 第三步: Wilder 平滑
    atr = _wilder_smooth(tr, period)
    smoothed_plus_dm = _wilder_smooth(plus_dm, period)
    smoothed_minus_dm = _wilder_smooth(minus_dm, period)

    # 第四步: 计算 ±DI
    pdi = (smoothed_plus_dm / atr) * 100.0
    mdi = (smoothed_minus_dm / atr) * 100.0

    # 第五步: 计算 DX → ADX
    dx = (pdi - mdi).abs() / (pdi + mdi) * 100.0
    adx = _wilder_smooth(dx, period)

    result = pd.DataFrame({
        'ADX': adx.round(4),
        'PDI': pdi.round(4),
        'MDI': mdi.round(4),
    })
    return result


# ═══════════════════════════════════════════════════════════════
# 便利函数: 一次计算所有指标
# ═══════════════════════════════════════════════════════════════

def calc_all_indicators(df: pd.DataFrame,
                        rsi_period: int = 14,
                        macd_params: Tuple[int, int, int] = (12, 26, 9),
                        bb_params: Tuple[int, float] = (20, 2.0),
                        atr_period: int = 14,
                        kdj_params: Tuple[int, int, int] = (9, 3, 3),
                        ma_periods: List[int] = [5, 10, 20, 60],
                        cci_period: int = 20,
                        adx_period: int = 14) -> pd.DataFrame:
    """
    一次性计算所有 8 个指标，返回合并后的 DataFrame

    返回:
        pd.DataFrame: 原始 OHLCV 数据 + 所有指标列
    """
    result = df.copy()
    result['Date'] = pd.to_datetime(result['Date'])

    # RSI
    rsi = calc_rsi(result, period=rsi_period)
    result['RSI'] = rsi

    # MACD
    macd = calc_macd(result, fast=macd_params[0], slow=macd_params[1], signal=macd_params[2])
    result['DIF'] = macd['DIF']
    result['DEA'] = macd['DEA']
    result['BAR'] = macd['BAR']

    # Bollinger Bands
    bb = calc_bollinger(result, period=bb_params[0], k=bb_params[1])
    result['BB_UP'] = bb['UP']
    result['BB_MID'] = bb['MID']
    result['BB_DN'] = bb['DN']
    result['BB_BandWidth'] = bb['BandWidth']
    result['BB_PctB'] = bb['PctB']

    # ATR
    result['ATR'] = calc_atr(result, period=atr_period)

    # KDJ
    kdj = calc_kdj(result, period=kdj_params[0], smooth_k=kdj_params[1], smooth_d=kdj_params[2])
    result['K'] = kdj['K']
    result['D'] = kdj['D']
    result['J'] = kdj['J']

    # MA
    ma_df = calc_ma(result, periods=ma_periods, ma_type='SMA')
    for col in ma_df.columns:
        result[col] = ma_df[col]

    # CCI
    result['CCI'] = calc_cci(result, period=cci_period)

    # ADX
    adx = calc_adx(result, period=adx_period)
    result['ADX'] = adx['ADX']
    result['PDI'] = adx['PDI']
    result['MDI'] = adx['MDI']

    return result


# ═══════════════════════════════════════════════════════════════
# 数据诊断
# ═══════════════════════════════════════════════════════════════

def data_diagnosis(df: pd.DataFrame, stock_name: str = "") -> Dict:
    """
    数据诊断分析: 缺失值、描述性统计

    参数:
        df: 包含 OHLCV 列的 DataFrame
        stock_name: 股票名称 (用于打印输出)

    返回:
        dict: 诊断结果字典
    """
    result = {'stock_name': stock_name, 'rows': len(df)}

    # 1. 缺失值检查
    cols_to_check = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = {}
    for col in cols_to_check:
        if col in df.columns:
            n_missing = df[col].isna().sum()
            if n_missing > 0:
                missing[col] = n_missing
    result['missing_values'] = missing

    # 2. 日期连续性
    if 'Date' in df.columns:
        dates = pd.to_datetime(df['Date'])
        date_range = (dates.max() - dates.min()).days
        result['date_range_days'] = date_range
        result['date_start'] = dates.min().strftime('%Y-%m-%d')
        result['date_end'] = dates.max().strftime('%Y-%m-%d')

    # 3. 描述性统计 (Close)
    if 'Close' in df.columns:
        close = df['Close'].astype(float)
        result['close_stats'] = {
            'mean': round(close.mean(), 2),
            'std': round(close.std(), 2),
            'min': round(close.min(), 2),
            'max': round(close.max(), 2),
            'skewness': round(close.skew(), 4),
            'kurtosis': round(close.kurtosis(), 4),
        }

        # 日收益率
        ret = close.pct_change().dropna()
        result['return_stats'] = {
            'daily_mean_pct': round(ret.mean() * 100, 4),
            'daily_std_pct': round(ret.std() * 100, 4),
            'annual_vol_pct': round(ret.std() * np.sqrt(252) * 100, 2),
        }

        # 最大回撤
        cummax = close.cummax()
        drawdown = (close - cummax) / cummax
        result['max_drawdown_pct'] = round(drawdown.min() * 100, 2)

        # Jarque-Bera 正态性检验
        from scipy import stats as scipy_stats
        jb_stat, jb_pvalue = scipy_stats.jarque_bera(ret.dropna())
        result['jarque_bera'] = {
            'statistic': round(jb_stat, 4),
            'p_value': round(jb_pvalue, 6),
            'is_normal': jb_pvalue > 0.05,
        }

    # 4. 异常值检测 (3σ)
    if 'Close' in df.columns:
        close = df['Close'].astype(float)
        mean_c, std_c = close.mean(), close.std()
        outliers = close[(close < mean_c - 3 * std_c) | (close > mean_c + 3 * std_c)]
        result['outliers_3sigma'] = len(outliers)

    # 5. 成交量分析
    if 'Volume' in df.columns:
        vol = df['Volume'].astype(float)
        result['volume_stats'] = {
            'mean': round(vol.mean(), 0),
            'max': round(vol.max(), 0),
            'max_date': str(df.loc[vol.idxmax(), 'Date']) if 'Date' in df.columns else '',
        }

    return result


def print_diagnosis(diag: Dict):
    """格式化打印诊断结果"""
    print(f"\n{'='*60}")
    print(f"  数据诊断: {diag.get('stock_name', '')}")
    print(f"{'='*60}")
    print(f"  记录数: {diag['rows']}")
    print(f"  日期范围: {diag.get('date_start', 'N/A')} ~ {diag.get('date_end', 'N/A')} "
          f"({diag.get('date_range_days', 'N/A')} 天)")

    # 缺失值
    missing = diag.get('missing_values', {})
    if missing:
        print(f"\n  ⚠️ 缺失值:")
        for col, n in missing.items():
            print(f"    {col}: {n} 个 ({n/diag['rows']*100:.1f}%)")
    else:
        print(f"\n  ✅ 无缺失值")

    # 收盘价统计
    cs = diag.get('close_stats', {})
    if cs:
        print(f"\n  ── 收盘价描述性统计 ──")
        print(f"    均值: {cs['mean']:.2f}  标准差: {cs['std']:.2f}")
        print(f"    最小: {cs['min']:.2f}  最大: {cs['max']:.2f}")
        print(f"    偏度(Skewness): {cs['skewness']:.4f}  (正值=右偏, 负值=左偏)")
        print(f"    峰度(Kurtosis): {cs['kurtosis']:.4f}  (正值=尖峰厚尾)")

    # 收益率统计
    rs = diag.get('return_stats', {})
    if rs:
        print(f"\n  ── 日收益率统计 ──")
        print(f"    日均收益率: {rs['daily_mean_pct']:.4f}%")
        print(f"    日波动率: {rs['daily_std_pct']:.4f}%")
        print(f"    年化波动率: {rs['annual_vol_pct']:.2f}%")
        print(f"    最大回撤: {diag.get('max_drawdown_pct', 'N/A'):.2f}%")

    # 正态性检验
    jb = diag.get('jarque_bera', {})
    if jb:
        print(f"\n  ── Jarque-Bera 正态性检验 ──")
        print(f"    JB统计量: {jb['statistic']:.4f}")
        print(f"    p-value: {jb['p_value']:.6f}")
        normality = "✅ 服从正态分布 (p > 0.05)" if jb['is_normal'] else "❌ 拒绝正态分布 (p ≤ 0.05)，收益率分布具有非正态特征"
        print(f"    结论: {normality}")

    # 异常值
    print(f"\n  ── 异常值检测 ──")
    print(f"    3σ 异常值数量: {diag.get('outliers_3sigma', 'N/A')}")

    # 成交量
    vs = diag.get('volume_stats', {})
    if vs:
        print(f"\n  ── 成交量 ──")
        print(f"    日均成交量: {vs['mean']:.0f}")
        print(f"    最大成交量: {vs['max']:.0f} (日期: {vs.get('max_date', 'N/A')})")

    print(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════════
# 主程序入口 (自检)
# ═══════════════════════════════════════════════════════════════
