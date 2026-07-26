#!/usr/bin/env python3
"""Shared paths and definitions for Task5 experiment 2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = PROJECT_ROOT / "Task5"
BASE_DATA_DIR = PROJECT_ROOT / "data" / "task5"
RAW_DIR = BASE_DATA_DIR / "raw"
EXP2_DIR = BASE_DATA_DIR / "experiment2"
PROCESSED_DIR = EXP2_DIR / "processed"
METADATA_DIR = EXP2_DIR / "metadata"
MODEL_DIR = PROCESSED_DIR / "models"
CHART_DIR = PROJECT_ROOT / "artifacts" / "charts" / "task5" / "experiment2"

SAMPLE_START = "2018-02-01"
SAMPLE_END = "2025-12-31"
TRAIN_END = "2022-12-31"
VALIDATION_START = "2023-01-01"
VALIDATION_END = "2023-12-31"
DEVELOPMENT_START = "2024-01-01"
DEVELOPMENT_END = "2024-12-31"
TEST_START = "2025-01-01"
TEST_END = "2025-12-31"
HORIZON = 20
RANDOM_SEED = 42

FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "ma5_gap",
    "ma20_gap",
    "ma60_gap",
    "rsi14",
    "macd_pct",
    "atr14_pct",
    "volatility20",
    "volume_ratio20",
    "amount_ratio20",
    "intraday_range",
    "open_close_return",
    "excess_return_5d",
    "excess_return_20d",
    "return_20d_rank",
    "market_median_return_5d",
    "market_median_return_20d",
    "market_breadth_20d",
    "market_dispersion_20d",
]

MODEL_LABELS = {
    "logistic_regression": "逻辑回归",
    "decision_tree": "决策树",
    "random_forest": "随机森林",
    "constant_baseline": "常数概率基线",
}


def ensure_directories() -> None:
    for path in (PROCESSED_DIR, METADATA_DIR, MODEL_DIR, CHART_DIR):
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
