#!/usr/bin/env python3
"""Shared paths, labels, metrics, and serialization helpers for TASK6."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = ROOT / "Task6"
SOURCE_DIR = TASK_DIR / "inputs"
DATA_DIR = ROOT / "data" / "task6"
MAIN_DIR = DATA_DIR / "main"
ADDON_DIR = DATA_DIR / "additional"
MAIN_PROCESSED_DIR = MAIN_DIR / "processed"
MAIN_METADATA_DIR = MAIN_DIR / "metadata"
ADDON_PROCESSED_DIR = ADDON_DIR / "processed"
ADDON_METADATA_DIR = ADDON_DIR / "metadata"
ENHANCED_DIR = DATA_DIR / "enhanced"
ENHANCED_PROCESSED_DIR = ENHANCED_DIR / "processed"
ENHANCED_METADATA_DIR = ENHANCED_DIR / "metadata"
MODEL_DIR = ROOT / "artifacts" / "models" / "task6"
MAIN_MODEL_DIR = MODEL_DIR / "main"
ADDON_MODEL_DIR = MODEL_DIR / "additional"
ENHANCED_MODEL_DIR = MODEL_DIR / "enhanced"
CHART_DIR = ROOT / "artifacts" / "charts" / "task6"
PDF_OUTPUT_DIR = ROOT / "output" / "submissions"
TMP_PDF_DIR = ROOT / "build" / "task6" / "pdf"

RANDOM_SEED = 42
TOP_N = 30
BUFFER_RANK = 50
ONE_WAY_COST = 0.002

MODEL_LABELS = {
    "linear_regression": "线性回归",
    "ridge": "Ridge回归",
    "decision_tree": "决策树",
    "random_forest": "随机森林",
    "hist_gradient_boosting": "梯度提升",
    "logistic_regression": "逻辑回归",
    "market_equal_weight": "全市场等权",
    "buy_and_hold": "买入持有",
    "moving_average": "均线策略",
    "ml_timing": "ML择时策略",
}


def ensure_directories() -> None:
    for path in (
        MAIN_PROCESSED_DIR,
        MAIN_METADATA_DIR,
        ADDON_PROCESSED_DIR,
        ADDON_METADATA_DIR,
        ENHANCED_PROCESSED_DIR,
        ENHANCED_METADATA_DIR,
        MAIN_MODEL_DIR,
        ADDON_MODEL_DIR,
        ENHANCED_MODEL_DIR,
        CHART_DIR,
        PDF_OUTPUT_DIR,
        TMP_PDF_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_relative(path: Path) -> str:
    """Serialize a project file as a portable POSIX-style relative path."""

    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def safe_spearman(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    left = pd.Series(np.asarray(actual, dtype=float))
    right = pd.Series(np.asarray(predicted, dtype=float))
    if left.nunique(dropna=True) < 2 or right.nunique(dropna=True) < 2:
        return 0.0
    return float(left.corr(right, method="spearman"))


def wealth_and_drawdown(returns: pd.Series) -> tuple[pd.Series, pd.Series]:
    values = (1.0 + pd.Series(returns, dtype=float).fillna(0.0)).cumprod()
    drawdown = values / values.cummax() - 1.0
    return values, drawdown


def quarterly_performance(returns: pd.Series) -> dict[str, float]:
    series = pd.Series(returns, dtype=float).dropna()
    if series.empty:
        return {
            "total_return": np.nan,
            "annualized_return": np.nan,
            "annualized_volatility": np.nan,
            "sharpe": np.nan,
            "max_drawdown": np.nan,
            "win_rate": np.nan,
            "quarter_count": 0,
        }
    wealth, drawdown = wealth_and_drawdown(series)
    total_return = float(wealth.iloc[-1] - 1.0)
    annualized_return = float(wealth.iloc[-1] ** (4.0 / len(series)) - 1.0)
    annualized_volatility = float(series.std(ddof=1) * np.sqrt(4.0)) if len(series) > 1 else np.nan
    sharpe = float(series.mean() / series.std(ddof=1) * np.sqrt(4.0)) if len(series) > 1 and series.std(ddof=1) > 0 else np.nan
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "win_rate": float(series.gt(0).mean()),
        "quarter_count": int(len(series)),
    }


def daily_performance(returns: pd.Series, periods_per_year: int = 252) -> dict[str, float]:
    series = pd.Series(returns, dtype=float).dropna()
    if series.empty:
        return {
            "total_return": np.nan,
            "annualized_return": np.nan,
            "annualized_volatility": np.nan,
            "sharpe": np.nan,
            "max_drawdown": np.nan,
            "win_rate": np.nan,
            "trading_days": 0,
        }
    wealth, drawdown = wealth_and_drawdown(series)
    total_return = float(wealth.iloc[-1] - 1.0)
    annualized_return = float(wealth.iloc[-1] ** (periods_per_year / len(series)) - 1.0)
    annualized_volatility = float(series.std(ddof=1) * np.sqrt(periods_per_year)) if len(series) > 1 else np.nan
    sharpe = float(series.mean() / series.std(ddof=1) * np.sqrt(periods_per_year)) if len(series) > 1 and series.std(ddof=1) > 0 else np.nan
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "win_rate": float(series.gt(0).mean()),
        "trading_days": int(len(series)),
    }
