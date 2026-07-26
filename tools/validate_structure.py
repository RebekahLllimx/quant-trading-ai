#!/usr/bin/env python3
"""Validate the public task layout after directory refactors."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASKS = {
    1: {"editable": "Rebecca+Task1.docx", "pdf": "Rebecca+Task1.pdf", "dashboard": True},
    2: {"editable": "Rebecca+Task2.docx", "pdf": "Rebecca+Task2.pdf", "dashboard": True},
    3: {"editable": "Rebecca+Task3.docx", "pdf": "Rebecca+Task3.pdf", "dashboard": True},
    4: {"editable": "Rebecca+Task4.docx", "pdf": "Rebecca+Task4.pdf", "dashboard": True},
    5: {"editable": "Rebecca+Task5.ipynb", "pdf": "Rebecca+Task5.pdf", "dashboard": True},
    6: {"editable": "Rebecca+Task6.ipynb", "pdf": "Rebecca+Task6.pdf", "dashboard": True},
    7: {"editable": "Rebecca+Task7.docx", "pdf": "李沐晓+TASK7.pdf", "dashboard": True},
    8: {
        "editable": "从数据到执行_量化交易策略与机器学习应用综合实践报告.docx",
        "pdf": "李沐晓+TASK8.pdf",
        "dashboard": False,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append((name, passed, detail))

    for task_id, task_spec in TASKS.items():
        task = ROOT / f"Task{task_id}"
        add(f"task{task_id}_directory", task.is_dir(), str(task))
        add(f"task{task_id}_readme", (task / "README.md").is_file(), "README.md")
        add(f"task{task_id}_spec", (task / "spec.md").is_file(), "spec.md")
        if task_spec["dashboard"]:
            add(f"task{task_id}_dashboard", (task / "dashboard" / "index.html").is_file(), "dashboard/index.html")
        add(f"task{task_id}_scripts", (task / "scripts").is_dir(), "scripts/")

        editable = task / task_spec["editable"]
        report = task / task_spec["pdf"]
        mirror = ROOT / "output" / "submissions" / f"Rebecca+Task{task_id}.pdf"
        add(f"task{task_id}_editable", editable.is_file(), editable.name)
        add(f"task{task_id}_pdf", report.is_file(), report.name)
        same_pdf = report.is_file() and mirror.is_file() and sha256(report) == sha256(mirror)
        add(f"task{task_id}_submission_mirror", same_pdf, mirror.name)

    expected_directories = (
        ROOT / "artifacts" / "charts",
        ROOT / "artifacts" / "models",
        ROOT / "data",
        ROOT / "docs",
        ROOT / "output" / "submissions",
        ROOT / "src",
    )
    for path in expected_directories:
        add(f"directory_{path.relative_to(ROOT)}", path.is_dir(), str(path.relative_to(ROOT)))

    retired_paths = (
        ROOT / "tmp",
        ROOT / "models",
        ROOT / "data" / "charts",
        ROOT / "output" / "pdf",
        ROOT / "Task6" / "data",
        ROOT / "Task6" / "recording",
        ROOT / "Task7" / "Rebecca+Task7.draft.docx",
    )
    for path in retired_paths:
        add(f"retired_{path.relative_to(ROOT)}", not path.exists(), str(path.relative_to(ROOT)))

    add(
        "task6_regression_tool",
        (ROOT / "Task6" / "dashboard" / "tools" / "csv_regression.html").is_file(),
        "Task6/dashboard/tools/csv_regression.html",
    )
    add("directory_document", (ROOT / "docs" / "directory-structure.md").is_file(), "docs/directory-structure.md")

    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    local_links = [
        value
        for value in re.findall(r'href=["\']([^"\']+)["\']', hub)
        if not value.startswith(("http://", "https://", "#", "mailto:"))
    ]
    missing_links = [link for link in local_links if not (ROOT / link).exists()]
    add("hub_local_links", not missing_links, ", ".join(missing_links) if missing_links else f"{len(local_links)} links")

    failed = [item for item in checks if not item[1]]
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    print(f"\nstructure validation: {len(checks) - len(failed)}/{len(checks)} passed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
