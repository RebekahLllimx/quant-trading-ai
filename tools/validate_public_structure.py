#!/usr/bin/env python3
"""Validate the public portfolio's durable entry points."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    required = [
        ROOT / "README.md",
        ROOT / "index.html",
        ROOT / "requirements.txt",
        ROOT / "docs/directory-structure.md",
    ]
    for task_number in range(1, 9):
        task = ROOT / f"Task{task_number}"
        required.append(task / "README.md")
        required.append(ROOT / "reports" / f"Task{task_number}_Report.pdf")
    for task_number in range(1, 8):
        required.append(ROOT / f"Task{task_number}" / "dashboard" / "index.html")

    missing = [path.relative_to(ROOT) for path in required if not path.is_file()]
    if missing:
        for path in missing:
            print(f"[FAIL] missing: {path}")
        return 1

    print(f"[PASS] public structure: {len(required)}/{len(required)} entry points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

