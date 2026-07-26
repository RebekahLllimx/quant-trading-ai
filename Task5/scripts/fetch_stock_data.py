#!/usr/bin/env python3
"""Build a point-in-time A-share universe and freeze adjusted daily API data.

The universe is selected using January 2018 trading amount, which was observable
before the first modeling sample on 2018-02-01. Tushare is the primary price
source; AKShare is a per-symbol fallback. Every file is hashed in the manifest.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from task5_common import (
    METADATA_DIR,
    RAW_DIR,
    RAW_END,
    RAW_START,
    SAMPLE_START,
    UNIVERSE_END,
    UNIVERSE_SIZE,
    UNIVERSE_START,
    ensure_directories,
    load_tushare_token,
    sha256_file,
    write_json,
)


STANDARD_COLUMNS = ["Date", "Symbol", "Name", "Open", "High", "Low", "Close", "Volume", "Amount"]
INITIAL_SOURCE_OVERRIDES = {
    "601318.SH": "Tushare Pro qfq (initial API snapshot)",
    "000725.SZ": "AKShare qfq fallback (initial API snapshot)",
    "600030.SH": "AKShare qfq fallback (initial API snapshot)",
}


def retry_call(func, *, attempts: int = 4, base_wait: float = 1.2):
    last_error = None
    for attempt in range(attempts):
        try:
            return func()
        except Exception as exc:  # API errors vary by provider
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(base_wait * (2**attempt))
    raise last_error


def get_pro():
    import tushare as ts

    token = load_tushare_token()
    if not token or token == "YOUR_TUSHARE_TOKEN_HERE":
        raise RuntimeError("未配置 Tushare Token，无法构造历史时点股票池。")
    return ts.pro_api(token)


def stock_master(pro) -> pd.DataFrame:
    fields = "ts_code,symbol,name,area,industry,market,exchange,list_status,list_date,delist_date"
    try:
        frame = pro.stock_basic(exchange="", list_status="L", fields=fields)
        if frame is not None and not frame.empty:
            return frame.drop_duplicates("ts_code", keep="first")
    except Exception as exc:
        print(f"[fallback] Tushare stock_basic failed: {type(exc).__name__}")

    # Names are optional metadata. Returning an empty keyed frame keeps the
    # historical liquidity selection usable even when provider name lists fail.
    return pd.DataFrame(columns=["ts_code", "symbol", "name", "list_date"])


def open_dates(pro) -> list[str]:
    # Candidate weekdays avoid repeated trade_cal calls on low-frequency accounts;
    # closed days simply return an empty daily frame and are ignored below.
    return pd.bdate_range(UNIVERSE_START, UNIVERSE_END).strftime("%Y%m%d").tolist()


def build_universe(pro, size: int) -> pd.DataFrame:
    """Select a liquid point-in-time universe using only January 2018 data."""
    frames = []
    for idx, trade_date in enumerate(open_dates(pro), start=1):
        daily = retry_call(
            lambda d=trade_date: pro.daily(
                trade_date=d,
                fields="ts_code,trade_date,close,vol,amount",
            )
        )
        if daily is not None and not daily.empty:
            frames.append(daily)
        print(f"[universe] {idx:02d} {trade_date}: {0 if daily is None else len(daily)} rows")
        time.sleep(0.08)

    panel = pd.concat(frames, ignore_index=True)
    panel = panel[panel["ts_code"].str.endswith((".SH", ".SZ"), na=False)].copy()
    panel["amount"] = pd.to_numeric(panel["amount"], errors="coerce")
    summary = (
        panel.groupby("ts_code", as_index=False)
        .agg(
            median_amount=("amount", "median"),
            mean_amount=("amount", "mean"),
            observed_days=("trade_date", "nunique"),
        )
        .query("observed_days >= 10 and median_amount > 0")
    )

    master = stock_master(pro)
    summary = summary.merge(master, on="ts_code", how="left")
    summary["list_date"] = summary["list_date"].fillna("").astype(str)
    summary = summary[summary["list_date"].le("20180131") | summary["list_date"].eq("")]
    summary = summary[~summary["name"].fillna("").str.contains(r"ST|退", regex=True)]
    summary = summary.sort_values(["median_amount", "mean_amount"], ascending=False).head(size).copy()
    summary.insert(0, "universe_rank", np.arange(1, len(summary) + 1))
    summary["selection_window"] = "2018-01"
    summary["selection_metric"] = "median_daily_amount_thousand_cny"

    if len(summary) < max(50, size // 2):
        raise RuntimeError(f"符合条件的股票仅 {len(summary)} 只，低于研究所需数量。")
    return summary


def normalize_tushare(frame: pd.DataFrame, symbol: str, name: str) -> pd.DataFrame:
    out = frame.rename(
        columns={
            "trade_date": "Date",
            "ts_code": "Symbol",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "vol": "Volume",
            "amount": "Amount",
        }
    ).copy()
    out["Date"] = pd.to_datetime(out["Date"], format="%Y%m%d")
    out["Symbol"] = symbol
    out["Name"] = name
    out["Amount"] = pd.to_numeric(out["Amount"], errors="coerce") * 1000.0
    out = out[STANDARD_COLUMNS].sort_values("Date").drop_duplicates("Date", keep="last")
    return out.reset_index(drop=True)


def normalize_tushare_return_index(frame: pd.DataFrame, symbol: str, name: str) -> pd.DataFrame:
    """Create a corporate-action-consistent OHLC index from Tushare pct_chg.

    Tushare pct_chg uses the provider's previous-close convention. Compounding
    it removes split/dividend discontinuities for the ratio features used here.
    The price level is an index; only scale-free features are modeled.
    """
    out = frame.sort_values("trade_date").reset_index(drop=True).copy()
    for column in ("open", "high", "low", "close", "vol", "amount", "pct_chg"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    growth = (1.0 + out["pct_chg"].fillna(0.0) / 100.0).clip(lower=0.001)
    growth.iloc[0] = 1.0
    adjusted_close = out.loc[0, "close"] * growth.cumprod()
    scale = adjusted_close / out["close"].replace(0, np.nan)
    for column in ("open", "high", "low", "close"):
        out[column] = out[column] * scale
    out["close"] = adjusted_close
    return normalize_tushare(out, symbol, name)


def normalize_akshare(frame: pd.DataFrame, symbol: str, name: str) -> pd.DataFrame:
    code = symbol.split(".")[0]
    out = frame.rename(
        columns={
            "日期": "Date",
            "开盘": "Open",
            "最高": "High",
            "最低": "Low",
            "收盘": "Close",
            "成交量": "Volume",
            "成交额": "Amount",
        }
    ).copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["Symbol"] = symbol
    out["Name"] = name
    out = out[STANDARD_COLUMNS].sort_values("Date").drop_duplicates("Date", keep="last")
    return out.reset_index(drop=True)


def fetch_symbol(pro, symbol: str, name: str) -> tuple[pd.DataFrame, str]:
    try:
        frame = retry_call(
            lambda: pro.daily(
                ts_code=symbol,
                start_date=RAW_START,
                end_date=RAW_END,
                fields="ts_code,trade_date,open,high,low,close,pre_close,pct_chg,vol,amount",
            ),
            attempts=3,
            base_wait=2.0,
        )
        if frame is None or frame.empty:
            raise ValueError("Tushare returned an empty frame")
        return normalize_tushare_return_index(frame, symbol, name), "Tushare adjusted return index"
    except Exception as tushare_error:
        print(f"[fallback] {symbol} Tushare failed: {type(tushare_error).__name__}")
        import akshare as ak

        code = symbol.split(".")[0]
        frame = retry_call(
            lambda: ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=RAW_START,
                end_date=RAW_END,
                adjust="qfq",
            ),
            attempts=4,
            base_wait=2.0,
        )
        if frame is None or frame.empty:
            raise RuntimeError(f"两种数据源均未返回 {symbol} 的行情。")
        return normalize_akshare(frame, symbol, name), "AKShare qfq fallback"


def validate_raw(frame: pd.DataFrame) -> dict:
    numeric = ["Open", "High", "Low", "Close", "Volume", "Amount"]
    for col in numeric:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    duplicate_dates = int(frame["Date"].duplicated().sum())
    missing_required = int(frame[STANDARD_COLUMNS].isna().sum().sum())
    tolerance = 1e-8
    invalid_ohlc = int(
        (
            (frame["High"] + tolerance < frame[["Open", "Close", "Low"]].max(axis=1))
            | (frame["Low"] - tolerance > frame[["Open", "Close", "High"]].min(axis=1))
            | (frame[["Open", "High", "Low", "Close"]] <= 0).any(axis=1)
        ).sum()
    )
    return {
        "rows": int(len(frame)),
        "start_date": frame["Date"].min().date().isoformat(),
        "end_date": frame["Date"].max().date().isoformat(),
        "duplicate_dates": duplicate_dates,
        "missing_required_cells": missing_required,
        "invalid_ohlc_rows": invalid_ohlc,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe-size", type=int, default=UNIVERSE_SIZE)
    parser.add_argument("--reuse-universe", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    ensure_directories()
    pro = get_pro()
    universe_path = METADATA_DIR / "universe.csv"
    if args.reuse_universe and universe_path.exists():
        universe = pd.read_csv(universe_path, dtype={"symbol": str, "ts_code": str})
        if "symbol" in universe and "ts_code" not in universe:
            universe = universe.rename(columns={"symbol": "ts_code"})
        print(f"[universe] reuse {len(universe)} symbols from {universe_path}")
    else:
        universe = build_universe(pro, args.universe_size)
        universe.to_csv(universe_path, index=False, encoding="utf-8-sig")
        print(f"[universe] froze {len(universe)} symbols -> {universe_path}")

    if "name" not in universe or universe["name"].isna().all():
        master = stock_master(pro)[["ts_code", "name"]].drop_duplicates("ts_code")
        if not master.empty:
            universe = universe.drop(columns=["name"], errors="ignore").merge(master, on="ts_code", how="left")
            universe.to_csv(universe_path, index=False, encoding="utf-8-sig")
            print(f"[universe] enriched {universe['name'].notna().sum()} company names")

    prior_sources = {}
    prior_manifest_path = METADATA_DIR / "raw_manifest.json"
    if prior_manifest_path.exists():
        prior_manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
        prior_sources = {item["symbol"]: item.get("source", "frozen local snapshot") for item in prior_manifest.get("files", [])}

    records = []
    failures = []
    for index, row in universe.reset_index(drop=True).iterrows():
        symbol = str(row["ts_code"])
        raw_name = row.get("name", symbol)
        name = symbol if pd.isna(raw_name) or not str(raw_name).strip() else str(raw_name)
        raw_path = RAW_DIR / f"{symbol.replace('.', '_')}.csv"
        reused_snapshot = raw_path.exists() and not args.overwrite
        if reused_snapshot:
            frame = pd.read_csv(raw_path, parse_dates=["Date"])
            source = prior_sources.get(symbol, INITIAL_SOURCE_OVERRIDES.get(symbol, "frozen local snapshot from API"))
            if source.startswith("frozen local snapshot") and symbol in INITIAL_SOURCE_OVERRIDES:
                source = INITIAL_SOURCE_OVERRIDES[symbol]
            if name != symbol and frame["Name"].astype(str).eq(symbol).all():
                frame["Name"] = name
                frame.to_csv(raw_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
        else:
            try:
                frame, source = fetch_symbol(pro, symbol, name)
                frame.to_csv(raw_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
            except Exception as exc:
                failures.append({"symbol": symbol, "name": name, "error": str(exc)[:500]})
                print(f"[error] {symbol} {name}: {exc}")
                continue

        quality = validate_raw(frame)
        record = {
            "symbol": symbol,
            "name": name,
            "source": source,
            "file": raw_path.relative_to(RAW_DIR.parent.parent).as_posix(),
            "sha256": sha256_file(raw_path),
            **quality,
        }
        records.append(record)
        print(f"[prices] {index + 1:03d}/{len(universe)} {symbol} {name}: {quality['rows']} rows ({source})")
        # Tushare daily is limited to 50 calls/minute on the configured account.
        if not reused_snapshot:
            time.sleep(1.30 if source.startswith("Tushare") else 0.20)

    manifest = {
        "task": "TASK5",
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "raw_window": {"start": RAW_START, "end": RAW_END},
        "sample_start": SAMPLE_START,
        "universe_definition": {
            "window": f"{UNIVERSE_START}-{UNIVERSE_END}",
            "metric": "median daily trading amount",
            "requested_size": args.universe_size,
            "actual_size": len(universe),
            "reason": "point-in-time liquid A-share universe selected before model samples",
        },
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
        },
        "files": records,
        "failures": failures,
    }
    write_json(METADATA_DIR / "raw_manifest.json", manifest)
    print(f"[done] {len(records)} successful, {len(failures)} failed")
    if len(records) < max(50, args.universe_size // 2):
        raise RuntimeError("成功下载的股票数量不足，停止后续建模。")


if __name__ == "__main__":
    main()
