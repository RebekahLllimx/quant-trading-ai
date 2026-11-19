#!/usr/bin/env python3
"""Compatibility entry point for the unified, validated market refresh."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from update_all_data import main

if __name__ == '__main__':
    raise SystemExit(main())
