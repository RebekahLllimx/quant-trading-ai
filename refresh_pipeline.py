"""Stage, build, and validate a complete market snapshot before publishing it."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from market_data import INSTRUMENTS, ROOT, canonical_path, merge_prices, validate_prices


BUILD_SCRIPTS = (
    'Task1/scripts/build_dashboard.py',
    'Task2/scripts/build_dashboard.py',
    'Task3/scripts/prepare_data.py',
    'Task3/scripts/build_dashboard.py',
    'Task4/scripts/prepare_data.py',
)
BUILD_INPUTS = (*BUILD_SCRIPTS, 'market_data.py', 'Task4/scripts/turtle_strategy.py',
                'Task1/dashboard/index.html', 'Task2/dashboard/index.html',
                'Task4/dashboard/index.html')
OUTPUTS = (
    'Task1/dashboard/index.html', 'Task2/dashboard/index.html',
    'Task3/dashboard/data.json', 'Task3/dashboard/index.html', 'Task4/dashboard/index.html',
)
MANIFEST = 'data/csv/manifest.json'


def market_date() -> str:
    return datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()


def inspect_inputs(root: Path, *, migrate_legacy=False):
    """Recognize only the canonical names and the previous updater's aliases."""
    data_dir = root / 'data/csv'
    allowed = {item.filename for item in INSTRUMENTS}
    if migrate_legacy:
        allowed.update(item.legacy_filename for item in INSTRUMENTS)
    unexpected = sorted(p.name for p in data_dir.glob('*_daily.csv') if p.name not in allowed)
    if unexpected:
        raise ValueError(f'Unexpected daily snapshots: {unexpected}; review before refreshing')


def read_existing(root: Path, item, *, migrate_legacy=False):
    paths = [canonical_path(item.code, root / 'data/csv')]
    alias = root / 'data/csv' / item.legacy_filename
    if migrate_legacy and alias.exists():
        paths.append(alias)
    frames = [pd.read_csv(path, encoding='utf-8-sig', dtype={'Symbol': str})
              for path in paths if path.exists()]
    if not frames:
        return None
    for frame in frames:
        validate_prices(frame, item.code)
    frames.sort(key=lambda frame: pd.to_datetime(frame['Date']).max())
    combined = frames[0]
    for frame in frames[1:]:
        combined = merge_prices(combined, frame, item.code)
    return combined


def run_builders(root: Path) -> None:
    for script in BUILD_SCRIPTS:
        if not (root / script).is_file():
            raise FileNotFoundError(f'Required dashboard builder missing: {script}')
        print(f'Building {script}', flush=True)
        result = subprocess.run(
            [sys.executable, str(root / script)], cwd=root,
            capture_output=True, text=True, timeout=300,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        )
        if result.returncode:
            raise RuntimeError(f'{script} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}')


def embedded_stocks(path: Path, binding='STOCKS'):
    html = path.read_text(encoding='utf-8')
    matches = list(re.finditer(rf'^\s*const {binding} =\s*', html, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError(f'{path.name}: expected one STOCKS binding')
    value, end = json.JSONDecoder().raw_decode(html, matches[0].end())
    if not html[end:].lstrip().startswith(';'):
        raise ValueError(f'{path.name}: invalid STOCKS binding')
    return value, html


def validate_snapshot(root: Path) -> dict:
    """Check all four pages against CSV values, not just their latest date."""
    inspect_inputs(root)
    manifest = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    entries = manifest['instruments']
    expected_codes = {item.code for item in INSTRUMENTS}
    if set(entries) != expected_codes:
        raise ValueError('Manifest instrument set differs from the registry')
    first, _ = embedded_stocks(root / OUTPUTS[0], 'EMBEDDED')
    second, _ = embedded_stocks(root / OUTPUTS[1])
    third = json.loads((root / OUTPUTS[2]).read_text(encoding='utf-8'))
    third_page, _ = embedded_stocks(root / OUTPUTS[3])
    fourth, _ = embedded_stocks(root / OUTPUTS[4])
    if third != third_page:
        raise ValueError('Task 3 JSON and HTML disagree')
    if not isinstance(first, list) or len(first) != len(INSTRUMENTS):
        raise ValueError('Task 1 has missing or duplicate instruments')
    if {row['code'] for row in first} != expected_codes:
        raise ValueError('Task 1 instrument set differs from the registry')
    for payload in (second, third, fourth):
        if set(payload) != expected_codes:
            raise ValueError('Dashboard instrument set differs from the registry')
    for item in INSTRUMENTS:
        path = canonical_path(item.code, root / 'data/csv')
        frame = pd.read_csv(path, encoding='utf-8-sig', dtype={'Symbol': str})
        validate_prices(frame, item.code, as_of=manifest['as_of'])
        entry = entries[item.code]
        if any(entry.get(key) != value for key, value in {
            'file': item.filename, 'name': item.name, 'market': item.market,
            'currency': item.currency, 'volume_unit': item.volume_unit,
        }.items()):
            raise ValueError(f'{item.code}: manifest identity or units mismatch')
        if (entry['sha256'] != hashlib.sha256(path.read_bytes()).hexdigest()
                or entry['records'] != len(frame)
                or entry['start'] != frame['Date'].min() or entry['end'] != frame['Date'].max()):
            raise ValueError(f'{item.code}: snapshot manifest mismatch')
        records = frame[['Date', 'Open', 'Close', 'High', 'Low', 'Volume']].values.tolist()
        index = next(i for i, row in enumerate(first) if row['code'] == item.code)
        task1 = [[row[c] for c in ['d', 'o', 'c', 'h', 'l', 'v']]
                 for row in first[index]['ohlc']]
        task2 = [[row[0], row[1], row[4], row[2], row[3], row[5]]
                 for row in second[item.code]['data']]
        for label, actual in [('Task 1', task1), ('Task 2', task2),
                              ('Task 3', third[item.code]['data']),
                              ('Task 4', fourth[item.code]['data'])]:
            if len(actual) != len(records) or [r[0] for r in actual] != [r[0] for r in records]:
                raise ValueError(f'{item.code}: {label} date coverage mismatch')
            if not np.allclose(np.asarray(actual)[:, 1:].astype(float),
                               np.asarray(records)[:, 1:].astype(float), rtol=0, atol=1e-8):
                raise ValueError(f'{item.code}: {label} price/volume mismatch')
        for payload in (first[index], second[item.code], third[item.code], fourth[item.code]):
            if payload['name'] != item.name or payload['market'] != item.market:
                raise ValueError(f'{item.code}: incorrect display metadata')
        start, end = frame['Date'].min(), frame['Date'].max()
        summaries = [
            (first[index], {'days': len(frame)}),
            (second[item.code], {'count': len(frame), 'start': start, 'end': end}),
            (third[item.code], {'count': len(frame), 'dateStart': start, 'dateEnd': end}),
            (fourth[item.code], {'records': len(frame), 'dateStart': start, 'dateEnd': end}),
        ]
        for payload, expected in summaries:
            if any(payload.get(key) != value for key, value in expected.items()):
                raise ValueError(f'{item.code}: dashboard date/count summary mismatch')
    return entries


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def publish_bundle(root: Path, files: dict[str, bytes], removals: list[str]) -> None:
    """Replace the validated bundle; restore previous bytes if any write fails."""
    before = {name: (root / name).read_bytes() if (root / name).exists() else None
              for name in [*files, *removals]}
    if removals:
        backup = Path(tempfile.mkdtemp(prefix='legacy-', dir=root / '.refresh-backups'))
        for name, content in before.items():
            if content is not None:
                target = backup / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        print(f'Legacy snapshots backed up in {backup}', flush=True)
    try:
        for name, content in files.items():
            atomic_bytes(root / name, content)
        for name in removals:
            (root / name).unlink()
    except Exception:
        for name, content in before.items():
            if content is None:
                (root / name).unlink(missing_ok=True)
            else:
                atomic_bytes(root / name, content)
        raise


def refresh_snapshot(frames=None, *, root=ROOT, migrate_legacy=False, as_of=None) -> dict:
    root = Path(root)
    as_of = as_of or market_date()
    inspect_inputs(root, migrate_legacy=migrate_legacy)
    if frames is not None and set(frames) != {item.code for item in INSTRUMENTS}:
        raise ValueError('A refresh must supply every registered instrument')
    old_manifest_path = root / MANIFEST
    old_entries = (json.loads(old_manifest_path.read_text(encoding='utf-8'))['instruments']
                   if old_manifest_path.exists() else {})
    removals = []
    with tempfile.TemporaryDirectory(prefix='quant-refresh-') as directory:
        stage = Path(directory)
        for name in BUILD_INPUTS:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, target)
        entries = {}
        for item in INSTRUMENTS:
            existing = read_existing(root, item, migrate_legacy=migrate_legacy)
            recent = frames[item.code] if frames is not None else existing
            if recent is None:
                raise FileNotFoundError(f'No observations for {item.code}')
            validate_prices(recent, item.code, as_of=as_of)
            merged = merge_prices(existing, recent, item.code)
            target = canonical_path(item.code, stage / 'data/csv')
            target.parent.mkdir(parents=True, exist_ok=True)
            merged.to_csv(target, index=False, encoding='utf-8-sig', float_format='%.10g')
            previous = old_entries.get(item.code, {})
            source = recent.attrs.get('source', previous.get('source', 'Legacy snapshot; provider not recorded'))
            adjustment = recent.attrs.get('adjustment', previous.get('adjustment', 'not recorded'))
            if source == 'Legacy snapshot; provider not recorded':
                adjustment = 'not recorded'
            if (recent.attrs.get('adjustment') == 'qfq' and existing is not None
                    and previous.get('adjustment') != 'qfq'
                    and not pd.to_datetime(existing['Date']).isin(pd.to_datetime(recent['Date'])).all()):
                adjustment = 'not recorded'
            entries[item.code] = {
                'file': item.filename, 'name': item.name, 'market': item.market,
                'currency': item.currency, 'volume_unit': item.volume_unit, 'adjustment': adjustment,
                'source': source,
                'records': len(merged), 'start': merged['Date'].min(), 'end': merged['Date'].max(),
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            }
            alias = root / 'data/csv' / item.legacy_filename
            if migrate_legacy and alias.exists():
                removals.append(str(alias.relative_to(root)))
        (stage / MANIFEST).write_text(json.dumps(
            {'schema_version': 1, 'as_of': as_of, 'instruments': entries}, indent=2) + '\n', encoding='utf-8')
        run_builders(stage)
        validate_snapshot(stage)
        names = [MANIFEST, *OUTPUTS, *(f'data/csv/{item.filename}' for item in INSTRUMENTS)]
        bundle = {name: (stage / name).read_bytes() for name in names}
    if removals:
        (root / '.refresh-backups').mkdir(exist_ok=True)
    publish_bundle(root, bundle, removals)
    print('Validated and published 10 price snapshots and all four dashboard payloads.')
    return entries
