#!/usr/bin/env python3
"""Compatibility entry point for the unified, validated market refresh."""

import os
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data', 'csv')
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from update_all_data import main

if __name__ == '__main__':
    raise SystemExit(main())
