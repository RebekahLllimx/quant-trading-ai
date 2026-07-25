#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch and validate public daily data for the TASK7 shadow portfolios.

Tencent's daily K-line API is the primary source because it is reachable from
GitHub Actions without a private token. Yahoo remains an ETF fallback and
AKShare remains a benchmark fallback. Recent observations are merged into the
stored long-history snapshots before the strategies are rebuilt.

No JoinQuant credential, private link, cookie or password is read or stored.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from task7_common import (
    METADATA_DIR,
    RAW_DIR,
    SYMBOLS,
    ensure_dirs,
    sha256_file,
    write_json,
)


START_DATE = "2015-01-01"
TENCENT_ROWS = 320


def tencent_symbol(code: str) -> str:
    if code == "000300" or code.startswith(("5", "6", "9")):
        return f"sh{code}"
    return f"sz{code}"


def fetch_tencent(code: str, *, benchmark: bool = False) -> pd.DataFrame:
    symbol = tencent_symbol(code)
    if benchmark:
        url = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
        query = f"{symbol},day,,,{TENCENT_ROWS}"
    else:
        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        query = f"{symbol},day,,,{TENCENT_ROWS},qfq"

    response = requests.get(
        url,
        params={"param": query},
        timeout=45,
        headers={"User-Agent": "Mozilla/5.0 TASK7 research"},
    )
    response.raise_for_status()
    payload = response.json()
    node = payload.get("data", {}).get(symbol, {})
    rows = node.get("qfqday") or node.get("day") or []
    if payload.get("code") != 0 or not rows:
        raise ValueError(
            f"Tencent returned no rows for {symbol}: {payload.get('msg', '')}"
        )

    frame = pd.DataFrame(
        [row[:6] for row in rows],
        columns=["Date", "Open", "Close", "High", "Low", "Volume"],
    )
    frame["Date"] = pd.to_datetime(frame["Date"])
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["Source"] = (
        "Tencent Finance daily index API (unadjusted)"
        if benchmark
        else (
            "Tencent Finance qfq daily API"
            if node.get("qfqday")
            else "Tencent Finance daily API (unadjusted)"
        )
    )
    return frame.dropna(subset=["Date", "Open", "High", "Low", "Close"])


def merge_existing_snapshot(path: Path, recent: pd.DataFrame) -> pd.DataFrame:
    if not path.exists():
        return recent
    existing = pd.read_csv(path)
    existing["Date"] = pd.to_datetime(existing["Date"])
    if "Source" not in existing:
        existing["Source"] = "Existing validated snapshot"
    # Published backtests must remain reproducible. Keep the previously
    # validated value for overlapping dates and append only genuinely new
    # trading days from the live provider.
    new_rows = recent.loc[recent["Date"] > existing["Date"].max()].copy()
    return (
        pd.concat([existing, new_rows], ignore_index=True, sort=False)
        .sort_values("Date")
        .reset_index(drop=True)
    )


def fetch_etf(code: str) -> pd.DataFrame:
    errors = []
    try:
        return fetch_tencent(code)
    except Exception as exc:
        errors.append(f"Tencent: {exc}")
    try:
        return fetch_yahoo(SYMBOLS[code]["yahoo"])
    except Exception as exc:
        errors.append(f"Yahoo: {exc}")
    raise RuntimeError("; ".join(errors))


def fetch_yahoo(symbol: str, start: str = START_DATE) -> pd.DataFrame:
    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_ts = int((pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=2)).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?period1={start_ts}&period2={end_ts}&interval=1d&events=div%2Csplits"
    )
    response = requests.get(
        url, timeout=45, headers={"User-Agent": "Mozilla/5.0 TASK7 research"}
    )
    response.raise_for_status()
    payload = response.json()["chart"]["result"][0]
    quote = payload["indicators"]["quote"][0]
    adjusted = payload["indicators"].get("adjclose", [{}])[0].get(
        "adjclose", quote["close"]
    )
    raw = pd.DataFrame(
        {
            "Date": pd.to_datetime(payload["timestamp"], unit="s", utc=True)
            .tz_convert("Asia/Shanghai")
            .date,
            "RawOpen": quote["open"],
            "RawHigh": quote["high"],
            "RawLow": quote["low"],
            "RawClose": quote["close"],
            "AdjClose": adjusted,
            "Volume": quote["volume"],
        }
    )
    for column in ["RawOpen", "RawHigh", "RawLow", "RawClose", "AdjClose", "Volume"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    factor = raw["AdjClose"] / raw["RawClose"]
    result = pd.DataFrame(
        {
            "Date": pd.to_datetime(raw["Date"]),
            "Open": raw["RawOpen"] * factor,
            "High": raw["RawHigh"] * factor,
            "Low": raw["RawLow"] * factor,
            "Close": raw["AdjClose"],
            "Volume": raw["Volume"],
            "Source": "Yahoo Finance chart API (adjusted)",
        }
    )
    result = result.dropna(subset=["Date", "Open", "High", "Low", "Close"])

    # Yahoo occasionally contains an isolated bad OHLC field while adjusted close
    # and volume remain correct (observed for 510300 on 2019-01-07). Repair only
    # objectively invalid bars with Sina's raw OHLC and Yahoo's adjustment factor.
    invalid = (
        (result["High"] < result[["Open", "Close", "Low"]].max(axis=1))
        | (result["Low"] > result[["Open", "Close", "High"]].min(axis=1))
    )
    if invalid.any():
        import akshare as ak

        sina_symbol = (
            f"sh{symbol.split('.')[0]}"
            if symbol.endswith(".SS")
            else f"sz{symbol.split('.')[0]}"
        )
        sina = ak.fund_etf_hist_sina(symbol=sina_symbol).rename(
            columns={
                "date": "Date",
                "open": "SinaOpen",
                "high": "SinaHigh",
                "low": "SinaLow",
                "close": "SinaClose",
            }
        )
        sina["Date"] = pd.to_datetime(sina["Date"])
        replacement = result.loc[invalid, ["Date", "Close"]].merge(
            sina[["Date", "SinaOpen", "SinaHigh", "SinaLow", "SinaClose"]],
            on="Date",
            how="left",
        )
        for item in replacement.itertuples(index=False):
            if not np.isfinite(item.SinaClose) or item.SinaClose <= 0:
                continue
            factor_item = item.Close / item.SinaClose
            mask = result["Date"].eq(item.Date)
            result.loc[mask, ["Open", "High", "Low"]] = [
                item.SinaOpen * factor_item,
                item.SinaHigh * factor_item,
                item.SinaLow * factor_item,
            ]
            result.loc[mask, "Source"] = (
                "Yahoo adjusted close + Sina OHLC repair"
            )
    return result


def fetch_benchmark_akshare() -> pd.DataFrame:
    import akshare as ak

    today = pd.Timestamp.today().strftime("%Y%m%d")
    try:
        frame = ak.stock_zh_index_daily_em(
            symbol="sh000300",
            start_date=START_DATE.replace("-", ""),
            end_date=today,
        )
        source = "Eastmoney via AKShare (unadjusted index)"
    except Exception as primary_error:
        frame = ak.stock_zh_index_daily(symbol="sh000300")
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame[
            (frame["date"] >= START_DATE)
            & (frame["date"] <= pd.Timestamp.today().normalize())
        ]
        source = (
            "Sina via AKShare (unadjusted index); "
            f"Eastmoney unavailable: {type(primary_error).__name__}"
        )
    frame = frame.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
            "amount": "Amount",
        }
    )
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame["Source"] = source
    keep = ["Date", "Open", "High", "Low", "Close", "Volume", "Amount", "Source"]
    return frame[[column for column in keep if column in frame.columns]]


def fetch_benchmark() -> pd.DataFrame:
    try:
        return fetch_tencent("000300", benchmark=True)
    except Exception as primary_error:
        frame = fetch_benchmark_akshare()
        frame["Source"] = (
            frame["Source"].astype(str)
            + f"; Tencent unavailable: {type(primary_error).__name__}"
        )
        return frame


def validate_frame(symbol: str, frame: pd.DataFrame) -> dict:
    numeric = ["Open", "High", "Low", "Close", "Volume"]
    report = {
        "symbol": symbol,
        "rows": int(len(frame)),
        "first_date": frame["Date"].min().strftime("%Y-%m-%d"),
        "last_date": frame["Date"].max().strftime("%Y-%m-%d"),
        "duplicate_dates": int(frame["Date"].duplicated().sum()),
        "missing_ohlc": int(frame[["Open", "High", "Low", "Close"]].isna().sum().sum()),
        "nonpositive_ohlc": int((frame[["Open", "High", "Low", "Close"]] <= 0).sum().sum()),
        "invalid_high_low": int(
            (
                (frame["High"] < frame[["Open", "Close", "Low"]].max(axis=1))
                | (frame["Low"] > frame[["Open", "Close", "High"]].min(axis=1))
            ).sum()
        ),
        "monotonic_dates": bool(frame["Date"].is_monotonic_increasing),
        "source_counts": (
            {
                str(label): int(count)
                for label, count in frame["Source"].value_counts().items()
            }
            if "Source" in frame.columns
            else {}
        ),
    }
    report["status"] = (
        "pass"
        if report["duplicate_dates"] == 0
        and report["missing_ohlc"] == 0
        and report["nonpositive_ohlc"] == 0
        and report["invalid_high_low"] == 0
        and report["monotonic_dates"]
        else "fail"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--use-existing-on-error",
        action="store_true",
        help="Keep the last successful CSV if a network source is temporarily unavailable.",
    )
    args = parser.parse_args()
    ensure_dirs()
    reports = []
    files = []

    for code in ["510300", "510500", "159915"]:
        path = RAW_DIR / f"{code}.csv"
        try:
            frame = merge_existing_snapshot(path, fetch_etf(code))
            frame = (
                frame.sort_values("Date")
                .drop_duplicates("Date", keep="last")
                .reset_index(drop=True)
            )
            report = validate_frame(code, frame)
            if report["status"] != "pass":
                raise ValueError(f"Data quality failure for {code}: {report}")
            frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.8f")
            print(f"✅ {code}: {len(frame)} rows through {report['last_date']}")
        except Exception as exc:
            if args.use_existing_on_error and path.exists():
                frame = pd.read_csv(path)
                frame["Date"] = pd.to_datetime(frame["Date"])
                report = validate_frame(code, frame)
                report["status"] = "stale_fallback"
                report["fetch_error"] = str(exc)
                print(f"⚠️ {code}: kept existing snapshot ({exc})")
            else:
                raise
        report["sha256"] = sha256_file(path)
        reports.append(report)
        files.append(path)
        time.sleep(0.5)

    benchmark_path = RAW_DIR / "000300.csv"
    try:
        benchmark = merge_existing_snapshot(benchmark_path, fetch_benchmark())
        benchmark = (
            benchmark.sort_values("Date")
            .drop_duplicates("Date", keep="last")
            .reset_index(drop=True)
        )
        report = validate_frame("000300", benchmark)
        if report["status"] != "pass":
            raise ValueError(f"Data quality failure for 000300: {report}")
        benchmark.to_csv(
            benchmark_path, index=False, encoding="utf-8-sig", float_format="%.8f"
        )
        print(
            f"✅ 000300: {len(benchmark)} rows through {report['last_date']}"
        )
    except Exception as exc:
        if args.use_existing_on_error and benchmark_path.exists():
            benchmark = pd.read_csv(benchmark_path)
            benchmark["Date"] = pd.to_datetime(benchmark["Date"])
            report = validate_frame("000300", benchmark)
            report["status"] = "stale_fallback"
            report["fetch_error"] = str(exc)
            print(f"⚠️ 000300: kept existing snapshot ({exc})")
        else:
            raise
    report["sha256"] = sha256_file(benchmark_path)
    reports.append(report)
    files.append(benchmark_path)

    latest_dates = [pd.Timestamp(item["last_date"]) for item in reports]
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_common_date": min(latest_dates).strftime("%Y-%m-%d"),
        "adjustment": {
            "etfs": (
                "Tencent qfq daily data; Yahoo adjusted data is used only "
                "when Tencent is unavailable"
            ),
            "benchmark": "Price index; no adjustment required",
        },
        "privacy": "No JoinQuant account, link, password, cookie or token is used.",
        "sources": reports,
    }
    write_json(METADATA_DIR / "market_data_manifest.json", manifest)
    if any(item["status"] == "fail" for item in reports):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
