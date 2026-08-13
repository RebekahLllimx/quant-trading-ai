#!/usr/bin/env python3
"""Build a leak-safe month-end panel for 20-trading-day direction prediction."""

from __future__ import annotations

import json
import platform
from datetime import datetime

import numpy as np
import pandas as pd

from experiment2_common import (
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
    average_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    result = 100 - 100 / (1 + relative_strength)
    return result.where(average_loss.ne(0), 100.0)


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


def engineer_symbol(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy().sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)
    numeric = ["Open", "High", "Low", "Close", "Volume", "Amount"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    close = frame["Close"]
    returns = close.pct_change(fill_method=None)

    frame["return_1d"] = returns
    for period in (5, 10, 20):
        frame[f"return_{period}d"] = close.pct_change(period, fill_method=None)
    for period in (5, 20, 60):
        frame[f"ma{period}_gap"] = close / close.rolling(period, min_periods=period).mean() - 1
    frame["rsi14"] = wilder_rsi(close) / 100.0
    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd_pct"] = (ema12 - ema26) / close
    frame["atr14_pct"] = wilder_atr(frame) / close
    frame["volatility20"] = returns.rolling(20, min_periods=20).std(ddof=0)
    frame["volume_ratio20"] = frame["Volume"] / frame["Volume"].rolling(20, min_periods=20).mean()
    frame["amount_ratio20"] = frame["Amount"] / frame["Amount"].rolling(20, min_periods=20).mean()
    frame["intraday_range"] = (frame["High"] - frame["Low"]) / close
    frame["open_close_return"] = close / frame["Open"] - 1

    frame["future_return_20d"] = close.shift(-HORIZON) / close - 1
    frame["label_end_date"] = frame["Date"].shift(-HORIZON)
    return frame


def add_market_features(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    grouped = panel.groupby("Date", sort=False)
    panel["market_median_return_5d"] = grouped["return_5d"].transform("median")
    panel["market_median_return_20d"] = grouped["return_20d"].transform("median")
    panel["market_breadth_20d"] = grouped["return_20d"].transform(lambda values: values.gt(0).mean())
    panel["market_dispersion_20d"] = grouped["return_20d"].transform(lambda values: values.std(ddof=0))
    panel["excess_return_5d"] = panel["return_5d"] - panel["market_median_return_5d"]
    panel["excess_return_20d"] = panel["return_20d"] - panel["market_median_return_20d"]
    panel["return_20d_rank"] = grouped["return_20d"].rank(pct=True, method="average") - 0.5
    return panel


def assign_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    periods = {
        "train": (pd.Timestamp(SAMPLE_START), pd.Timestamp(TRAIN_END)),
        "validation": (pd.Timestamp(VALIDATION_START), pd.Timestamp(VALIDATION_END)),
        "development": (pd.Timestamp(DEVELOPMENT_START), pd.Timestamp(DEVELOPMENT_END)),
        "test": (pd.Timestamp(TEST_START), pd.Timestamp(TEST_END)),
    }
    frame = frame.copy()
    frame["Split"] = ""
    audit: dict[str, int] = {}
    for name, (start, end) in periods.items():
        observed = frame["Date"].between(start, end)
        usable = observed & frame["label_end_date"].le(end)
        frame.loc[usable, "Split"] = name
        audit[f"purged_{name}_boundary_rows"] = int((observed & ~usable).sum())
    return frame, audit


def main() -> None:
    ensure_directories()
    manifest_path = RAW_DIR.parent / "metadata" / "raw_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("缺少第一次实验冻结的 raw_manifest.json。")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    engineered: list[pd.DataFrame] = []
    for item in manifest["files"]:
        raw_path = RAW_DIR / f"{item['symbol'].replace('.', '_')}.csv"
        raw = pd.read_csv(raw_path, parse_dates=["Date"])
        engineered.append(engineer_symbol(raw))

    panel = pd.concat(engineered, ignore_index=True)
    panel = panel[panel["Date"].between(pd.Timestamp(SAMPLE_START), pd.Timestamp(SAMPLE_END))].copy()
    panel = add_market_features(panel)

    global_month_ends = (
        panel.groupby(panel["Date"].dt.to_period("M"), sort=True)["Date"]
        .max()
        .drop_duplicates()
        .sort_values()
    )
    panel = panel[panel["Date"].isin(global_month_ends)].copy()
    pre_drop_rows = len(panel)
    panel.replace([np.inf, -np.inf], np.nan, inplace=True)
    missing_by_feature = panel[FEATURE_COLUMNS].isna().sum().sort_values(ascending=False)
    panel = panel.dropna(subset=FEATURE_COLUMNS + ["future_return_20d", "label_end_date"]).copy()

    coverage = panel.groupby("Date")["Symbol"].nunique()
    valid_dates = coverage[coverage >= 50].index
    panel = panel[panel["Date"].isin(valid_dates)].copy()
    panel["Label"] = (panel["future_return_20d"] > 0).astype(int)
    panel, purge_audit = assign_split(panel)
    unassigned_rows = int(panel["Split"].eq("").sum())
    panel = panel[panel["Split"].ne("")].copy()

    output_columns = [
        "Date",
        "Symbol",
        "Name",
        "label_end_date",
        "Split",
        *FEATURE_COLUMNS,
        "future_return_20d",
        "Label",
    ]
    panel = panel[output_columns].sort_values(["Date", "Symbol"]).reset_index(drop=True)
    dataset_path = PROCESSED_DIR / "task5_experiment2_dataset.csv"
    panel.to_csv(dataset_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    split_order = ["train", "validation", "development", "test"]
    summary = (
        panel.groupby("Split", sort=False)
        .agg(
            rows=("Label", "size"),
            positive=("Label", "sum"),
            symbols=("Symbol", "nunique"),
            months=("Date", "nunique"),
            start=("Date", "min"),
            end=("Date", "max"),
            latest_label_end=("label_end_date", "max"),
        )
        .reindex(split_order)
        .reset_index()
    )
    summary["positive_rate"] = summary["positive"] / summary["rows"]
    summary.to_csv(METADATA_DIR / "split_summary.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")

    yearly = (
        panel.assign(Year=panel["Date"].dt.year)
        .groupby(["Split", "Year"], as_index=False)
        .agg(rows=("Label", "size"), positive=("Label", "sum"), months=("Date", "nunique"))
    )
    yearly["positive_rate"] = yearly["positive"] / yearly["rows"]
    yearly.to_csv(METADATA_DIR / "yearly_label_summary.csv", index=False, encoding="utf-8-sig")

    quality = {
        "created_at": datetime.now().astimezone().isoformat(),
        "experiment": "Task5 experiment 2",
        "grain": "one stock at one global calendar-month-end observation date",
        "target": "future 20-trading-day absolute return greater than zero",
        "split_rule": "2018-2022 train, 2023 validation, 2024 development, 2025 final test; crossing year-end labels purged",
        "horizon_trading_days": HORIZON,
        "feature_information_cutoff": "all features use data available on or before observation Date",
        "pre_drop_rows": int(pre_drop_rows),
        "dropped_for_missing_or_low_coverage": int(pre_drop_rows - len(panel) - unassigned_rows),
        "unassigned_or_purged_rows": unassigned_rows,
        "missing_by_feature_before_drop": {key: int(value) for key, value in missing_by_feature.items()},
        "final_rows": int(len(panel)),
        "symbols": int(panel["Symbol"].nunique()),
        "months": int(panel["Date"].nunique()),
        "duplicate_keys": int(panel.duplicated(["Symbol", "Date"]).sum()),
        "remaining_missing_cells": int(panel.isna().sum().sum()),
        "label_values": sorted(panel["Label"].unique().tolist()),
        "dataset_sha256": sha256_file(dataset_path),
        "split_summary": summary.assign(
            start=summary["start"].astype(str),
            end=summary["end"].astype(str),
            latest_label_end=summary["latest_label_end"].astype(str),
        ).to_dict("records"),
        **purge_audit,
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
    }
    write_json(METADATA_DIR / "data_quality_report.json", quality)
    print(summary.to_string(index=False))
    print(f"[done] {dataset_path}: {len(panel):,} rows, {panel['Date'].nunique()} month-ends")


if __name__ == "__main__":
    main()
