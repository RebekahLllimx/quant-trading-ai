#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-fast validation for TASK7 data, outputs and privacy boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from task7_common import (
    DASHBOARD_DATA_DIR,
    METADATA_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    ensure_dirs,
    write_json,
)


FORBIDDEN_PATTERNS = [
    re.compile(r"password\s*[:=]\s*['\"][^'\"]+", re.I),
    re.compile(r"cookie\s*[:=]\s*['\"][^'\"]+", re.I),
    # Match a standalone mainland mobile number, not an 11-digit substring
    # inside a long floating-point metric.
    re.compile(r"(?<![\d.])1[3-9]\d{9}(?![\d.])"),
]


def main() -> int:
    ensure_dirs()
    checks = []
    failures = []

    for symbol in ["510300", "510500", "159915", "000300"]:
        path = RAW_DIR / f"{symbol}.csv"
        if not path.exists():
            failures.append(f"missing raw data {path}")
            continue
        frame = pd.read_csv(path)
        frame["Date"] = pd.to_datetime(frame["Date"])
        duplicate = int(frame["Date"].duplicated().sum())
        missing = int(frame[["Open", "High", "Low", "Close"]].isna().sum().sum())
        invalid = int(
            (
                (frame["High"] < frame[["Open", "Close", "Low"]].max(axis=1))
                | (frame["Low"] > frame[["Open", "Close", "High"]].min(axis=1))
            ).sum()
        )
        status = duplicate == 0 and missing == 0 and invalid == 0
        checks.append(
            {
                "check": f"raw_{symbol}",
                "status": "pass" if status else "fail",
                "rows": len(frame),
                "duplicates": duplicate,
                "missing_ohlc": missing,
                "invalid_high_low": invalid,
                "latest": frame["Date"].max().strftime("%Y-%m-%d"),
            }
        )
        if not status:
            failures.append(f"raw data quality failure: {symbol}")

    for strategy in ["a", "b", "c"]:
        path = PROCESSED_DIR / f"strategy_{strategy}_daily.csv"
        if not path.exists():
            failures.append(f"missing result {path}")
            continue
        frame = pd.read_csv(path)
        frame["Date"] = pd.to_datetime(frame["Date"])
        status = (
            frame["Date"].is_monotonic_increasing
            and frame["Date"].duplicated().sum() == 0
            and frame["NAV"].notna().all()
            and (frame["NAV"] > 0).all()
            and frame["Exposure"].between(-1e-9, 1.01).all()
        )
        checks.append(
            {
                "check": f"strategy_{strategy}",
                "status": "pass" if status else "fail",
                "rows": len(frame),
                "latest": frame["Date"].max().strftime("%Y-%m-%d"),
                "min_nav": float(frame["NAV"].min()),
                "max_exposure": float(frame["Exposure"].max()),
            }
        )
        if not status:
            failures.append(f"strategy result failure: {strategy}")

    payload_path = DASHBOARD_DATA_DIR / "dashboard.json"
    if not payload_path.exists():
        failures.append("missing dashboard.json")
    else:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        status = (
            len(payload.get("cards", [])) == 3
            and bool(payload.get("latest_complete_date"))
            and "不是JoinQuant实际成交结果"
            in payload.get("method", {}).get("actual_vs_shadow", "")
        )
        checks.append(
            {
                "check": "dashboard_contract",
                "status": "pass" if status else "fail",
            }
        )
        if not status:
            failures.append("dashboard layer labels are incomplete")

    scan_paths = [payload_path]
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = [
            pattern.pattern for pattern in FORBIDDEN_PATTERNS if pattern.search(text)
        ]
        status = not matches
        checks.append(
            {
                "check": f"privacy_{path.name}",
                "status": "pass" if status else "fail",
                "matches": matches,
            }
        )
        if not status:
            failures.append(f"possible credential or phone data in {path}")

    report = {
        "status": "pass" if not failures else "fail",
        "checks": checks,
        "failures": failures,
    }
    write_json(METADATA_DIR / "validation_report.json", report)
    if failures:
        print("❌ TASK7 validation failed")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"✅ TASK7 validation passed ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
