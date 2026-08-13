#!/usr/bin/env python3
"""Shared constants and helpers for the Task5 machine-learning workflow."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = PROJECT_ROOT / "Task5"
DATA_DIR = PROJECT_ROOT / "data" / "task5"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
CHART_DIR = PROJECT_ROOT / "artifacts" / "charts" / "task5"
DASHBOARD_DIR = TASK_DIR / "dashboard"

RAW_START = "20170101"
RAW_END = "20251231"
UNIVERSE_START = "20180101"
UNIVERSE_END = "20180131"
SAMPLE_START = "20180201"
SAMPLE_END = "20251231"
TRAIN_END = "20221231"
VALIDATION_START = "20230101"
VALIDATION_END = "20231231"
DEVELOPMENT_START = "20240101"
DEVELOPMENT_END = "20241231"
TEST_START = "20250101"
TEST_END = "20251231"
HORIZON = 60
UNIVERSE_SIZE = 100
RANDOM_SEED = 42

FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_20d",
    "return_60d",
    "return_120d",
    "momentum_12_1",
    "ma20_gap",
    "ma60_gap",
    "ma120_gap",
    "rsi14",
    "macd_pct",
    "atr14_pct",
    "volatility20",
    "volatility60",
    "downside_volatility60",
    "max_drawdown60",
    "volume_ratio20",
    "amount_ratio20",
    "intraday_range",
    "open_close_return",
    "amihud20",
    "amount_mean20_log",
]

MODEL_LABELS = {
    "logistic_regression": "逻辑回归",
    "decision_tree": "决策树",
    "random_forest": "随机森林",
    "majority_baseline": "多数类基线",
}


def ensure_directories() -> None:
    for path in (RAW_DIR, PROCESSED_DIR, METADATA_DIR, CHART_DIR, DASHBOARD_DIR):
        path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)


def load_tushare_token() -> str:
    """Read the token without ever logging it."""
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if token:
        return token

    config_path = PROJECT_ROOT / "Task1" / "scripts" / "config.py"
    if not config_path.exists():
        return ""

    namespace: dict[str, Any] = {}
    exec(compile(config_path.read_text(encoding="utf-8"), str(config_path), "exec"), namespace)
    return str(namespace.get("TUSHARE_TOKEN", "")).strip()
