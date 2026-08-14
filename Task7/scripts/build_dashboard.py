#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the TASK7 static dashboard with an offline fallback snapshot."""

from __future__ import annotations

from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = TASK_DIR / "dashboard" / "template.html"
DATA = TASK_DIR / "dashboard" / "data" / "dashboard.json"
OUTPUT = TASK_DIR / "dashboard" / "index.html"


def main() -> int:
    if not TEMPLATE.exists() or not DATA.exists():
        raise FileNotFoundError("Run shadow_engine.py before build_dashboard.py")
    html = TEMPLATE.read_text(encoding="utf-8")
    payload = DATA.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    marker = "/*__TASK7_FALLBACK__*/null"
    if marker not in html:
        raise ValueError("Dashboard fallback marker is missing")
    html = html.replace(marker, payload, 1)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"✅ Built {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
