#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Technical Indicator Calculation Module
Support 8 an indicator: RSI, MACD, Bollinger Bands, ATR, KDJ, MA, CCI, ADX
All functions receive pandas DataFrame (Must include Date, Open, High, Low, Close, Volume column)
Return to Original DataFrame Additional Indicator Columns, or directly return the indicator sequence.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict


#
# auxiliary function
#

def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average (EMA), alpha = 2/(N+1)"""
    return series.ewm(span=period, min_periods=period, adjust=False).mean()


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder Smooth (alpha = 1/N), used for RSI/ATR/ADX"""
    return series.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    """simple moving average"""
    return series.rolling(window=period, min_periods=period).mean()


def _std(series: pd.Series, period: int) -> pd.Series:
    """rolling standard deviation"""
    return series.rolling(window=period, min_periods=period).std(ddof=0)


#
# 1. RSI  -  relative strength index
#

def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    calculation RSI (Relative Strength Index)

    Parameters:
        df: Contains Close of the column DataFrame
        period: Calculation period, Default 14 (Wilder Original parameters)

    Returns:
        pd.Series: RSI sequence [0, 100]
    """
    close = df['Close'].astype(float)
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # seed: former N period&#39;s SMA
    avg_gain = gain.copy()
    avg_loss = loss.copy()

    # Wilder Smooth: alpha = 1/N
    avg_gain.iloc[period:] = gain.iloc[period:].ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss.iloc[period:] = loss.iloc[period:].ewm(alpha=1.0 / period, adjust=False).mean()

    # For initial seed SMA
    avg_gain.iloc[:period] = np.nan
    avg_loss.iloc[:period] = np.nan

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi.name = 'RSI'

    return rsi.round(4)


#
# 2. MACD  -  Exponential smoothing moving average
#

def calc_macd(df: pd.DataFrame,
              fast: int = 12,
              slow: int = 26,
              signal: int = 9) -> pd.DataFrame:
    """
    calculation MACD

    Parameters:
        df: Contains Close of the column DataFrame
        fast: Express Line EMA cycle, Default 12
        slow: Slow line EMA cycle, Default 26
        signal: Signal line EMA cycle, Default 9

    Returns:
        pd.DataFrame: Contains DIF, DEA, BAR 3 columns
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


#
# 3. Bollinger Bands  -  Bollinger Bands
#

def calc_bollinger(df: pd.DataFrame,
                   period: int = 20,
                   k: float = 2.0) -> pd.DataFrame:
    """
    Calculating Bollinger Bands (Bollinger Bands)

    Parameters:
        df: Contains Close of the column DataFrame
        period: mid-rail period, Default 20
        k: Standard deviation multiplier, Default 2.0

    Returns:
        pd.DataFrame: Contains MID, UP, DN, BandWidth, %b Five columns
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


#
# 4. ATR  -  Average True Range
#

def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    calculation ATR (Average True Range)

    Parameters:
        df: Contains High, Low, Close of the column DataFrame
        period: Calculation period, Default 14

    Returns:
        pd.Series: ATR sequence
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


#
# 5. KDJ  -  Stochastic Indicator
#

def calc_kdj(df: pd.DataFrame,
             period: int = 9,
             smooth_k: int = 3,
             smooth_d: int = 3) -> pd.DataFrame:
    """
    calculation KDJ Stochastic Indicator

    Parameters:
        df: Contains High, Low, Close of the column DataFrame
        period: RSV Calculation period, Default 9
        smooth_k: K Value Smoothing Period, Default 3 (EMA Equivalent)
        smooth_d: D Value Smoothing Period, Default 3 (EMA Equivalent)

    Returns:
        pd.DataFrame: Contains K, D, J 3 columns [0, 100], J Can be out of range
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


#
# 6. MA  -  Multi-period moving average
#

def calc_ma(df: pd.DataFrame,
            periods: List[int] = [5, 10, 20, 60, 120, 250],
            ma_type: str = 'SMA') -> pd.DataFrame:
    """
    Calculate a multi-period moving average

    Parameters:
        df: Contains Close of the column DataFrame
        periods: Cycle List, Default [5, 10, 20, 60, 120, 250]
        ma_type: 'SMA' (Simple) or 'EMA' (index)

    Returns:
        pd.DataFrame: The column name is MA{N} of DataFrame
    """
    close = df['Close'].astype(float)
    result = pd.DataFrame(index=df.index)

    calc_fn = _sma if ma_type == 'SMA' else _ema

    for p in periods:
        result[f'MA{p}'] = calc_fn(close, p).round(4)

    return result


#
# 7. CCI  -  Commodity Channel Index
#

def calc_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    calculation CCI (Commodity Channel Index)

    Parameters:
        df: Contains High, Low, Close of the column DataFrame
        period: Calculation period, Default 20

    Returns:
        pd.Series: CCI sequence (Boundless)
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


#
# 8. ADX  -  average trend index
#

def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    calculation ADX / +DI / -DI (Wilder trending motion system)

    Parameters:
        df: Contains High, Low, Close of the column DataFrame
        period: Calculation period, Default 14

    Returns:
        pd.DataFrame: Contains ADX, PDI(+DI), MDI(-DI) 3 columns
    """
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)

    # Step one: calculation True Range
    tr = pd.concat([
        (high - low),
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    # Step two: Compute trend motion (+DM, -DM)
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=df.index)
    minus_dm = pd.Series(0.0, index=df.index)

    mask_plus = (up_move > down_move) & (up_move > 0)
    mask_minus = (down_move > up_move) & (down_move > 0)

    plus_dm[mask_plus] = up_move[mask_plus]
    minus_dm[mask_minus] = down_move[mask_minus]

    # Step 3: Wilder Smooth
    atr = _wilder_smooth(tr, period)
    smoothed_plus_dm = _wilder_smooth(plus_dm, period)
    smoothed_minus_dm = _wilder_smooth(minus_dm, period)

    # Step Four: calculation DI
    pdi = (smoothed_plus_dm / atr) * 100.0
    mdi = (smoothed_minus_dm / atr) * 100.0

    # Step Five: calculation DX  ->  ADX
    dx = (pdi - mdi).abs() / (pdi + mdi) * 100.0
    adx = _wilder_smooth(dx, period)

    result = pd.DataFrame({
        'ADX': adx.round(4),
        'PDI': pdi.round(4),
        'MDI': mdi.round(4),
    })
    return result


#
# Convenience functions: Calculate all metrics at once
#

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
    Calculate all at once 8 an indicator, Returns the merged DataFrame

    Returns:
        pd.DataFrame: Original OHLCV Data + All Metric Columns
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


#
# Data Diagnostics
#

def data_diagnosis(df: pd.DataFrame, stock_name: str = "") -> Dict:
    """
    data diagnostic analysis: Missing value, Descriptive Statistics

    Parameters:
        df: Contains OHLCV of the column DataFrame
        stock_name: Name of Stock (for printout)

    Returns:
        dict: Diagnostic Result Dictionary
    """
    result = {'stock_name': stock_name, 'rows': len(df)}

    # 1. Missing Value Check
    cols_to_check = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing = {}
    for col in cols_to_check:
        if col in df.columns:
            n_missing = df[col].isna().sum()
            if n_missing > 0:
                missing[col] = n_missing
    result['missing_values'] = missing

    # 2. Date continuity
    if 'Date' in df.columns:
        dates = pd.to_datetime(df['Date'])
        date_range = (dates.max() - dates.min()).days
        result['date_range_days'] = date_range
        result['date_start'] = dates.min().strftime('%Y-%m-%d')
        result['date_end'] = dates.max().strftime('%Y-%m-%d')

    # 3. Descriptive Statistics (Close)
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

        # daily rate of return
        ret = close.pct_change().dropna()
        result['return_stats'] = {
            'daily_mean_pct': round(ret.mean() * 100, 4),
            'daily_std_pct': round(ret.std() * 100, 4),
            'annual_vol_pct': round(ret.std() * np.sqrt(252) * 100, 2),
        }

        # Maximum Drawdown
        cummax = close.cummax()
        drawdown = (close - cummax) / cummax
        result['max_drawdown_pct'] = round(drawdown.min() * 100, 2)

        # Jarque-Bera normality test
        from scipy import stats as scipy_stats
        jb_stat, jb_pvalue = scipy_stats.jarque_bera(ret.dropna())
        result['jarque_bera'] = {
            'statistic': round(jb_stat, 4),
            'p_value': round(jb_pvalue, 6),
            'is_normal': jb_pvalue > 0.05,
        }

    # 4. outlier detection (3sigma)
    if 'Close' in df.columns:
        close = df['Close'].astype(float)
        mean_c, std_c = close.mean(), close.std()
        outliers = close[(close < mean_c - 3 * std_c) | (close > mean_c + 3 * std_c)]
        result['outliers_3sigma'] = len(outliers)

    # 5. Volume Analysis
    if 'Volume' in df.columns:
        vol = df['Volume'].astype(float)
        result['volume_stats'] = {
            'mean': round(vol.mean(), 0),
            'max': round(vol.max(), 0),
            'max_date': str(df.loc[vol.idxmax(), 'Date']) if 'Date' in df.columns else '',
        }

    return result


def print_diagnosis(diag: Dict):
    """Format Print Diagnostic Results"""
    print(f"\n{'='*60}")
    print(f"  Data Diagnostics: {diag.get('stock_name', '')}")
    print(f"{'='*60}")
    print(f"  Number of records: {diag['rows']}")
    print(f"  Date Range: {diag.get('date_start', 'N/A')} ~ {diag.get('date_end', 'N/A')} "
          f"({diag.get('date_range_days', 'N/A')} days)")

    # Missing value
    missing = diag.get('missing_values', {})
    if missing:
        print(f"\n   Missing value:")
        for col, n in missing.items():
            print(f"    {col}: {n} one ({n/diag['rows']*100:.1f}%)")
    else:
        print(f"\n   No missing value")

    # Closing Price Statistics
    cs = diag.get('close_stats', {})
    if cs:
        print(f"\n   Closing Price Descriptive Statistics ")
        print(f"    Mean: {cs['mean']:.2f}  Standard deviation: {cs['std']:.2f}")
        print(f"    smallest: {cs['min']:.2f}  Maximum: {cs['max']:.2f}")
        print(f"    Skewness(Skewness): {cs['skewness']:.4f}  (just in time=Right, Negative Values=Left deviation)")
        print(f"    Kurtosis(Kurtosis): {cs['kurtosis']:.4f}  (just in time=Spike Thick Tail)")

    # Yield Statistics
    rs = diag.get('return_stats', {})
    if rs:
        print(f"\n   Daily Rate of Return Statistics ")
        print(f"    average daily rate of return: {rs['daily_mean_pct']:.4f}%")
        print(f"    daily volatility: {rs['daily_std_pct']:.4f}%")
        print(f"    annualized volatility: {rs['annual_vol_pct']:.2f}%")
        print(f"    Maximum Drawdown: {diag.get('max_drawdown_pct', 'N/A'):.2f}%")

    # normality test
    jb = diag.get('jarque_bera', {})
    if jb:
        print(f"\n   Jarque-Bera normality test ")
        print(f"    JBStatistic: {jb['statistic']:.4f}")
        print(f"    p-value: {jb['p_value']:.6f}")
        normality = " Follows a normal distribution (p > 0.05)" if jb['is_normal'] else " reject normal distribution (p <= 0.05), Yield Distribution Exhibits Non-Normal Characteristics"
        print(f"    Conclusion: {normality}")

    # Outlier
    print(f"\n   outlier detection ")
    print(f"    3sigma Number of outliers: {diag.get('outliers_3sigma', 'N/A')}")

    # Trading volume
    vs = diag.get('volume_stats', {})
    if vs:
        print(f"\n   Trading volume ")
        print(f"    Average daily trading volume: {vs['mean']:.0f}")
        print(f"    Maximum trading volume: {vs['max']:.0f} (Date: {vs.get('max_date', 'N/A')})")

    print(f"{'='*60}\n")


#
# Main Program Entry (Self-check)
#
