#!/usr/bin/env python3
"""Validate committed CSVs, their manifest, and all four dashboard payloads."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from refresh_pipeline import validate_snapshot

if __name__ == '__main__':
    entries = validate_snapshot(ROOT)
    print(f'Market snapshot passed: {len(entries)} instruments; all dashboard OHLCV values match.')
