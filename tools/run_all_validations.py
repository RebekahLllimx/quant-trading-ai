#!/usr/bin/env python3
"""Run the repository's release validations from one fail-fast entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    [sys.executable, "tools/validate_public_structure.py"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    [sys.executable, "tools/validate_market_snapshot.py"],
    [sys.executable, "Task5/scripts/validate_results.py"],
    [sys.executable, "Task5/scripts/validate_experiment2.py"],
    [sys.executable, "Task6/scripts/validate_results.py"],
    [sys.executable, "Task7/scripts/validate_results.py"],
]
GENERATED_REPORTS = [
    ROOT / "data/task5/experiment2/metadata/validation_report.json",
    ROOT / "data/task5/metadata/validation_report.json",
    ROOT / "data/task6/additional/metadata/validation_report.json",
    ROOT / "data/task6/main/metadata/validation_report.json",
    ROOT / "data/task7/metadata/validation_report.json",
]


def main() -> int:
    # The underlying validators record their run time in tracked JSON files.
    # Preserve those artifacts so a read-only verification does not dirty the
    # repository solely because the clock changed.
    report_snapshots = {
        path: path.read_bytes() for path in GENERATED_REPORTS if path.exists()
    }
    try:
        for command in COMMANDS:
            print(f"\n$ {' '.join(command)}", flush=True)
            completed = subprocess.run(command, cwd=ROOT, check=False)
            if completed.returncode != 0:
                return completed.returncode
    finally:
        for path, content in report_snapshots.items():
            path.write_bytes(content)
    print("\nAll portfolio validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

