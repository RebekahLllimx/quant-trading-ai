#!/usr/bin/env python3
"""Create leak-safe month-end features and a 60-day relative-selection label."""

from __future__ import annotations

import json
import platform
from datetime import datetime

import numpy as np
import pandas as pd

from task5_common import (
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    FEATURE_COLUMNS,
    HORIZON,
    METADATA_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    SAMPLE_END,
    SAMPLE_START,
    TEST_END,
    TEST_START,
    TRAIN_END,
    VALIDATION_END,
    VALIDATION_START,
    ensure_directories,
    sha256_file,
    write_json,
)


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return rsi.where(avg_loss.ne(0), 100.0)


def wilder_atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = frame["Close"].shift(1)
    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous_close).abs(),
            (frame["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rolling_max_drawdown(close: pd.Series, period: int = 60) -> pd.Series:
    def local_drawdown(values: np.ndarray) -> float:
        peaks = np.maximum.accumulate(values)
        return float(np.min(values / peaks - 1.0))

    return close.rolling(period, min_periods=period).apply(local_drawdown, raw=True)


def engineer_symbol(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy().sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)
    numeric = ["Open", "High", "Low", "Close", "Volume", "Amount"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    close = frame["Close"]
    returns = close.pct_change(fill_method=None)

    frame["return_1d"] = returns
    for period in (5, 20, 60, 120):
        frame[f"return_{period}d"] = close.pct_change(period, fill_method=None)
    frame["momentum_12_1"] = close.shift(20) / close.shift(250) - 1
    for period in (20, 60, 120):
        frame[f"ma{period}_gap"] = close / close.rolling(period, min_periods=period).mean() - 1

    frame["rsi14"] = wilder_rsi(close, 14) / 100.0
    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd_pct"] = (ema12 - ema26) / close
    frame["atr14_pct"] = wilder_atr(frame, 14) / close
    frame["volatility20"] = returns.rolling(20, min_periods=20).std(ddof=0)
    frame["volatility60"] = returns.rolling(60, min_periods=60).std(ddof=0)
    frame["downside_volatility60"] = np.sqrt(
        returns.clip(upper=0).pow(2).rolling(60, min_periods=60).mean()
    )
    frame["max_drawdown60"] = rolling_max_drawdown(close, 60)
    frame["volume_ratio20"] = frame["Volume"] / frame["Volume"].rolling(20, min_periods=20).mean()
    amount_mean20 = frame["Amount"].rolling(20, min_periods=20).mean()
    frame["amount_ratio20"] = frame["Amount"] / amount_mean20
    frame["intraday_range"] = (frame["High"] - frame["Low"]) / close
    frame["open_close_return"] = close / frame["Open"] - 1
    frame["amihud20"] = (returns.abs() / frame["Amount"].replace(0, np.nan)).rolling(20, min_periods=20).mean() * 1e8
    frame["amount_mean20_log"] = np.log1p(amount_mean20.clip(lower=0))

    frame["future_return_60d"] = close.shift(-HORIZON) / close - 1
    frame["label_end_date"] = frame["Date"].shift(-HORIZON)
    return frame


def global_month_end_dates(panel: pd.DataFrame) -> pd.Series:
    month = panel["Date"].dt.to_period("M")
    return panel.groupby(month, sort=True)["Date"].max().drop_duplicates().sort_values()


def assign_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    periods = {
        "train": (pd.Timestamp(SAMPLE_START), pd.Timestamp(TRAIN_END)),
        "validation": (pd.Timestamp(VALIDATION_START), pd.Timestamp(VALIDATION_END)),
        "development": (pd.Timestamp(DEVELOPMENT_START), pd.Timestamp(DEVELOPMENT_END)),
        "test": (pd.Timestamp(TEST_START), pd.Timestamp(TEST_END)),
    }
    frame = frame.copy()
    frame["Split"] = ""
    audit = {}
    for name, (start, end) in periods.items():
        natural = frame["Date"].between(start, end)
        usable = natural & frame["label_end_date"].le(end)
        frame.loc[usable, "Split"] = name
        audit[f"purged_{name}_boundary_rows"] = int((natural & ~usable).sum())
    return frame, audit


def raw_quality(frame: pd.DataFrame) -> dict:
    tolerance = 1e-8
    invalid_ohlc = (
        (frame["High"] + tolerance < frame[["Open", "Close", "Low"]].max(axis=1))
        | (frame["Low"] - tolerance > frame[["Open", "Close", "High"]].min(axis=1))
        | (frame[["Open", "High", "Low", "Close"]] <= 0).any(axis=1)
    )
    return {
        "rows": int(len(frame)),
        "duplicates_symbol_date": int(frame.duplicated(["Symbol", "Date"]).sum()),
        "invalid_ohlc_rows": int(invalid_ohlc.sum()),
        "missing_core_cells": int(frame[["Open", "High", "Low", "Close", "Volume", "Amount"]].isna().sum().sum()),
    }


def main() -> None:
    ensure_directories()
    manifest_path = METADATA_DIR / "raw_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("请先运行 fetch_stock_data.py。")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    engineered = []
    raw_frames = []
    coverage = []
    for item in manifest["files"]:
        raw_path = RAW_DIR / f"{item['symbol'].replace('.', '_')}.csv"
        raw = pd.read_csv(raw_path, parse_dates=["Date"])
        raw_frames.append(raw)
        engineered.append(engineer_symbol(raw))
        coverage.append(
            {
                "symbol": item["symbol"],
                "name": item["name"],
                "source": item["source"],
                "raw_rows": int(len(raw)),
                "raw_start": raw["Date"].min().date().isoformat(),
                "raw_end": raw["Date"].max().date().isoformat(),
            }
        )

    panel = pd.concat(engineered, ignore_index=True)
    panel = panel[panel["Date"].between(pd.Timestamp(SAMPLE_START), pd.Timestamp(SAMPLE_END))].copy()
    month_end_dates = global_month_end_dates(panel)
    panel = panel[panel["Date"].isin(month_end_dates)].copy()
    pre_feature_rows = len(panel)
    panel.replace([np.inf, -np.inf], np.nan, inplace=True)
    missing_by_feature = panel[FEATURE_COLUMNS].isna().sum().sort_values(ascending=False).to_dict()
    panel = panel.dropna(subset=FEATURE_COLUMNS + ["future_return_60d", "label_end_date"]).copy()

    counts_before_label = panel.groupby("Date")["Symbol"].nunique()
    valid_dates = counts_before_label[counts_before_label >= 50].index
    panel = panel[panel["Date"].isin(valid_dates)].copy()
    complete_rows = len(panel)

    panel["future_return_rank"] = panel.groupby("Date")["future_return_60d"].rank(pct=True, method="average")
    panel["Label"] = np.select(
        [panel["future_return_rank"].ge(0.70), panel["future_return_rank"].le(0.30)],
        [1, 0],
        default=np.nan,
    )

    # Model inputs are same-date cross-sectional percentile ranks. This makes
    # the problem a stock-selection comparison instead of an absolute-price task.
    panel[FEATURE_COLUMNS] = panel.groupby("Date")[FEATURE_COLUMNS].rank(pct=True, method="average") - 0.5
    panel, purge_audit = assign_split(panel)
    middle_rows = int(panel["Label"].isna().sum())
    unassigned_rows = int((panel["Split"].eq("") & panel["Label"].notna()).sum())
    panel = panel[panel["Split"].ne("") & panel["Label"].notna()].copy()
    panel["Label"] = panel["Label"].astype(int)

    key_duplicates = int(panel.duplicated(["Symbol", "Date"]).sum())
    if key_duplicates:
        raise RuntimeError(f"特征面板存在 {key_duplicates} 条 Symbol-Date 重复记录。")
    if not set(panel["Label"].unique()).issubset({0, 1}):
        raise RuntimeError("标签不是严格的 0/1。")

    columns = [
        "Date",
        "Symbol",
        "Name",
        "label_end_date",
        "Split",
        *FEATURE_COLUMNS,
        "future_return_60d",
        "future_return_rank",
        "Label",
    ]
    panel = panel[columns].sort_values(["Date", "Symbol"]).reset_index(drop=True)
    dataset_path = PROCESSED_DIR / "task5_ml_dataset.csv"
    panel.to_csv(dataset_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    pd.DataFrame(coverage).to_csv(METADATA_DIR / "symbol_coverage.csv", index=False, encoding="utf-8-sig")

    split_order = ["train", "validation", "development", "test"]
    split_summary = (
        panel.groupby("Split", sort=False)
        .agg(
            rows=("Label", "size"),
            positive=("Label", "sum"),
            symbols=("Symbol", "nunique"),
            months=("Date", "nunique"),
            start=("Date", "min"),
            end=("Date", "max"),
        )
        .reindex(split_order)
        .reset_index()
    )
    split_summary["positive_rate"] = split_summary["positive"] / split_summary["rows"]
    split_summary.to_csv(METADATA_DIR / "split_summary.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    yearly = (
        panel.assign(Year=panel["Date"].dt.year)
        .groupby(["Split", "Year"], as_index=False)
        .agg(rows=("Label", "size"), positive=("Label", "sum"), symbols=("Symbol", "nunique"), months=("Date", "nunique"))
    )
    yearly["positive_rate"] = yearly["positive"] / yearly["rows"]
    yearly.to_csv(METADATA_DIR / "yearly_label_summary.csv", index=False, encoding="utf-8-sig")

    quality = {
        "created_at": datetime.now().astimezone().isoformat(),
        "grain": "one stock at one global month-end observation date",
        "observation_rule": "last market date in each calendar month",
        "target": "future 60-trading-day cross-sectional top 30% versus bottom 30%",
        "feature_transform": "same-date cross-sectional percentile rank minus 0.5",
        "raw_quality": raw_quality(pd.concat(raw_frames, ignore_index=True)),
        "pre_feature_rows": int(pre_feature_rows),
        "dropped_for_feature_or_forward_return_missing": int(pre_feature_rows - complete_rows),
        "dropped_middle_40pct_or_ties": middle_rows,
        "unassigned_or_purged_rows": unassigned_rows,
        "missing_by_feature_before_drop": {k: int(v) for k, v in missing_by_feature.items()},
        "final_rows": int(len(panel)),
        "symbols": int(panel["Symbol"].nunique()),
        "months": int(panel["Date"].nunique()),
        "date_start": panel["Date"].min().date().isoformat(),
        "date_end": panel["Date"].max().date().isoformat(),
        "duplicate_keys": key_duplicates,
        "remaining_missing_cells": int(panel.isna().sum().sum()),
        "label_values": sorted(panel["Label"].unique().tolist()),
        "split_summary": split_summary.assign(start=split_summary["start"].astype(str), end=split_summary["end"].astype(str)).to_dict("records"),
        **purge_audit,
        "dataset_sha256": sha256_file(dataset_path),
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
    }
    write_json(METADATA_DIR / "data_quality_report.json", quality)
    print(split_summary.to_string(index=False))
    print(f"Saved {dataset_path} ({len(panel):,} rows, {panel['Date'].nunique()} month-ends)")


if __name__ == "__main__":
    main()
