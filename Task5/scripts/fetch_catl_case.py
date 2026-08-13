#!/usr/bin/env python3
"""Fetch and freeze CATL and CSI 300 daily data for the TASK5 case study."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import akshare as ak

from task5_common import sha256_file


ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / "data" / "task5" / "catl"
RAW_DIR = CASE_DIR / "raw"
METADATA_DIR = CASE_DIR / "metadata"
STOCK_PATH = RAW_DIR / "300750_SZ.csv"
BENCHMARK_PATH = RAW_DIR / "000300_SH.csv"
MANIFEST_PATH = METADATA_DIR / "raw_manifest.json"

START_DATE = "20180611"
END_DATE = "20251231"
STANDARD_COLUMNS = ["Date", "Symbol", "Name", "Open", "High", "Low", "Close", "Volume", "Amount"]


def normalize_stock(frame: pd.DataFrame, symbol: str, name: str) -> pd.DataFrame:
    out = frame.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
            "amount": "Amount",
        }
    ).copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["Symbol"] = symbol
    out["Name"] = name
    for column in ["Open", "High", "Low", "Close", "Volume", "Amount"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out[STANDARD_COLUMNS].sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)


def normalize_benchmark(frame: pd.DataFrame, symbol: str, name: str) -> pd.DataFrame:
    out = frame.rename(
        columns={
            "date": "Date", "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        }
    ).copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["Symbol"] = symbol
    out["Name"] = name
    out["Amount"] = np.nan  # Sina index history does not publish turnover amount.
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out[STANDARD_COLUMNS].sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)


def quality_profile(frame: pd.DataFrame, amount_required: bool) -> dict:
    prices = ["Open", "High", "Low", "Close"]
    tolerance = 1e-8
    invalid_ohlc = (
        (frame["High"] + tolerance < frame[["Open", "Close", "Low"]].max(axis=1))
        | (frame["Low"] - tolerance > frame[["Open", "Close", "High"]].min(axis=1))
        | frame[prices].le(0).any(axis=1)
    )
    return {
        "rows": int(len(frame)),
        "start_date": frame["Date"].min().date().isoformat(),
        "end_date": frame["Date"].max().date().isoformat(),
        "duplicate_dates": int(frame["Date"].duplicated().sum()),
        "missing_required_cells": int(frame[["Date", "Symbol", "Name", *prices, "Volume"]].isna().sum().sum())
        + (int(frame["Amount"].isna().sum()) if amount_required else 0),
        "missing_optional_amount_cells": int(frame["Amount"].isna().sum()) if not amount_required else 0,
        "nonfinite_numeric_cells": int((~np.isfinite(frame[[*prices, "Volume"]])).sum().sum())
        + (int((~np.isfinite(frame["Amount"])).sum()) if amount_required else 0),
        "invalid_ohlc_rows": int(invalid_ohlc.sum()),
        "negative_volume_or_amount_rows": int(frame[["Volume"]].lt(0).any(axis=1).sum())
        + (int(frame[["Amount"]].lt(0).any(axis=1).sum()) if amount_required else 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    if not args.overwrite and STOCK_PATH.exists() and BENCHMARK_PATH.exists() and MANIFEST_PATH.exists():
        print(f"Frozen files already exist under {RAW_DIR}")
        return

    # The Eastmoney qfq endpoint returned negative early-history prices for this
    # symbol during validation, so the Sina-backed endpoint is used instead.
    stock_raw = ak.stock_zh_a_daily(
        symbol="sz300750",
        start_date=START_DATE,
        end_date=END_DATE,
        adjust="qfq",
    )
    benchmark_raw = ak.stock_zh_index_daily(symbol="sh000300")
    benchmark_dates = pd.to_datetime(benchmark_raw["date"])
    benchmark_raw = benchmark_raw[
        (benchmark_dates >= pd.to_datetime(START_DATE))
        & (benchmark_dates <= pd.to_datetime(END_DATE))
    ].copy()
    if stock_raw is None or stock_raw.empty or benchmark_raw is None or benchmark_raw.empty:
        raise RuntimeError("Tushare returned an empty stock or benchmark frame")

    stock = normalize_stock(stock_raw, "300750.SZ", "宁德时代")
    benchmark = normalize_benchmark(benchmark_raw, "000300.SH", "沪深300")
    stock_quality = quality_profile(stock, amount_required=True)
    benchmark_quality = quality_profile(benchmark, amount_required=False)
    common_dates = pd.Index(stock["Date"]).intersection(benchmark["Date"])
    coverage = {
        "stock_dates": int(stock["Date"].nunique()),
        "benchmark_dates": int(benchmark["Date"].nunique()),
        "common_dates": int(len(common_dates)),
        "stock_common_coverage": float(len(common_dates) / stock["Date"].nunique()),
        "benchmark_common_coverage": float(len(common_dates) / benchmark["Date"].nunique()),
    }

    for label, profile in [("stock", stock_quality), ("benchmark", benchmark_quality)]:
        failures = {key: value for key, value in profile.items() if key in {
            "duplicate_dates", "missing_required_cells", "nonfinite_numeric_cells",
            "invalid_ohlc_rows", "negative_volume_or_amount_rows",
        } and value != 0}
        if failures:
            raise RuntimeError(f"{label} data quality failures: {failures}")
    if coverage["stock_common_coverage"] < 0.99 or coverage["benchmark_common_coverage"] < 0.99:
        raise RuntimeError(f"Insufficient date coverage: {coverage}")

    stock.to_csv(STOCK_PATH, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    benchmark.to_csv(BENCHMARK_PATH, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    manifest = {
        "case": "CATL relative to CSI 300",
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "query_start": START_DATE,
        "query_end": END_DATE,
        "source": "AKShare (Sina stock and index history endpoints)",
        "stock_adjustment": "qfq",
        "benchmark_adjustment": "index level, no adjustment",
        "amount_unit": "stock CNY; benchmark unavailable from source",
        "stock": {"path": str(STOCK_PATH.relative_to(ROOT)), **stock_quality},
        "benchmark": {"path": str(BENCHMARK_PATH.relative_to(ROOT)), **benchmark_quality},
        "date_coverage": coverage,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "akshare": ak.__version__,
        },
    }
    manifest["stock"]["sha256"] = sha256_file(STOCK_PATH)
    manifest["benchmark"]["sha256"] = sha256_file(BENCHMARK_PATH)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "stock": stock_quality,
        "benchmark": benchmark_quality,
        "coverage": coverage,
        "manifest": str(MANIFEST_PATH),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
