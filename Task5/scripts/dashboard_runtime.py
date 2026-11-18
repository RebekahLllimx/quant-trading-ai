#!/usr/bin/env python3
"""Locate the optional Data Analytics dashboard packaging runtime."""

from __future__ import annotations

import os
from pathlib import Path


DELIVER_SCRIPT = Path("skills/build-report/scripts/deliver_portable_artifact.mjs")


def data_analytics_plugin_root() -> Path:
    """Return an installed plugin root without relying on a user-specific path."""

    configured = os.environ.get("DATA_ANALYTICS_PLUGIN_ROOT")
    if configured:
        candidates = [Path(configured).expanduser()]
    else:
        cache = Path.home() / ".codex" / "plugins" / "cache" / "openai-curated-remote" / "data-analytics"
        candidates = sorted(
            (path for path in cache.glob("*") if path.is_dir()),
            key=lambda path: path.name,
            reverse=True,
        )

    for candidate in candidates:
        if (candidate / DELIVER_SCRIPT).is_file():
            return candidate

    raise FileNotFoundError(
        "Data Analytics dashboard packaging tools were not found. "
        "Install the plugin or set DATA_ANALYTICS_PLUGIN_ROOT to its version directory. "
    )
