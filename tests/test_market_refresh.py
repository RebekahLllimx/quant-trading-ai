"""Offline provider contracts and full snapshot publication regressions."""

import contextlib
import io
import json
import re
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import market_data as market
import refresh_pipeline as pipeline
import update_all_data as updater


def bars(code, dates=('2026-11-17', '2026-11-18')):
    return pd.DataFrame({
        'Date': list(dates), 'Symbol': code, 'Open': 10.125, 'Close': 10.375,
        'High': 11.125, 'Low': 9.875, 'Volume': 200.0,
    })


def fixture_root(root):
    for name in pipeline.BUILD_INPUTS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, path)
    for item in market.INSTRUMENTS:
        path = market.canonical_path(item.code, root / 'data/csv')
        path.parent.mkdir(parents=True, exist_ok=True)
        bars(item.code).to_csv(path, index=False)


def snapshot_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and '.refresh-backups' not in p.parts}


class PriceContractTest(unittest.TestCase):
    def test_registry_identity_is_independent_of_display_name(self):
        self.assertEqual(market.canonical_path('601318').name, '601318_ping_an_a_share_daily.csv')
        self.assertEqual(market.BY_CODE['00700'].volume_unit, 'shares')
        self.assertEqual(market.BY_CODE['600519'].volume_unit, '100-share lots')

    def test_validation_rejects_invalid_bars(self):
        for column, value in [('Volume', -1), ('Volume', float('inf')),
                               ('Close', float('nan')), ('High', 9.0), ('Symbol', '999999')]:
            frame = bars('600519')
            frame.loc[0, column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                market.validate_prices(frame, '600519')
        with self.assertRaises(ValueError):
            market.validate_prices(bars('600519'), '600519', as_of='2026-11-17')

    def test_merge_retains_oldest_and_newest_observations(self):
        old = bars('600519', ('2026-11-16', '2026-11-17'))
        recent = bars('600519')
        result = market.merge_prices(old, recent, '600519')
        self.assertEqual(result['Date'].tolist(), ['2026-11-16', '2026-11-17', '2026-11-18'])

    def test_numeric_strings_are_normalized_before_history_calculations(self):
        old = bars('600519', ('2026-11-16', '2026-11-17')).astype(str)
        recent = bars('600519').astype(str)
        result = market.merge_prices(old, recent, '600519')
        self.assertEqual(result['Volume'].tolist(), [200.0, 200.0, 200.0])
        self.assertEqual(result['Price change'].dropna().tolist(), [0.0, 0.0])

    def test_partial_rebase_is_rejected_but_full_revision_is_allowed(self):
        old = bars('600519', ('2026-11-16', '2026-11-17'))
        recent = bars('600519')
        recent[market.PRICE_COLUMNS] *= 0.5
        with self.assertRaisesRegex(ValueError, 'mixed bases'):
            market.merge_prices(old, recent, '600519')
        complete = bars('600519', ('2026-11-16', '2026-11-17', '2026-11-18'))
        complete[market.PRICE_COLUMNS] *= 0.5
        result = market.merge_prices(old, complete, '600519')
        self.assertTrue((result['Close'] == 5.1875).all())

    def test_older_or_disjoint_data_is_rejected(self):
        for dates in [('2026-11-16',), ('2026-11-19',)]:
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                market.merge_prices(bars('600519'), bars('600519', dates), '600519')


class ProviderAdapterTest(unittest.TestCase):
    def provider_frame(self):
        return pd.DataFrame({'日期': ['2026-11-18'], '开盘': [10], '收盘': [11],
                             '最高': [12], '最低': [9], '成交量': [100], '成交额': [10000]})

    def test_documented_akshare_columns_for_both_markets(self):
        provider = SimpleNamespace(stock_zh_a_hist_em=Mock(return_value=self.provider_frame()),
                                   stock_hk_hist_em=Mock(return_value=self.provider_frame()))
        with patch.dict(sys.modules, {'akshare': provider}):
            for code, fetch in [('600519', updater.fetch_a_stock), ('00700', updater.fetch_hk_stock)]:
                result = fetch(code, 'name')
                self.assertIsNotNone(result)
                self.assertEqual(result['Symbol'].iloc[0], code)
                self.assertEqual(result['Volume'].iloc[0], 100)
                self.assertEqual(result['Amount'].iloc[0], 10000)
        provider.stock_zh_a_hist_em.assert_called_once()
        self.assertEqual(provider.stock_hk_hist_em.call_args.kwargs['adjust'], 'qfq')

    def test_changed_provider_schema_is_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, 'schema changed'):
            updater._standardize_akshare(self.provider_frame().rename(columns={'日期': 'day'}), '600519')

    def test_provider_symbol_mismatch_is_rejected(self):
        frame = self.provider_frame()
        frame['股票代码'] = '999999'
        with self.assertRaisesRegex(ValueError, 'symbols'):
            updater._standardize_akshare(frame, '600519')

    def test_hk_tushare_factor_is_required_and_applied(self):
        raw = pd.DataFrame({'trade_date': ['20261118'], 'open': [10], 'close': [11],
                            'high': [12], 'low': [9], 'vol': [100], 'amount': [500],
                            'adj_factor': [0.5]})
        frame = updater._standardize_tushare(raw, '00700', 'Hong Kong equities')
        self.assertEqual(frame['Close'].iloc[0], 5.5)
        self.assertEqual(frame['Volume'].iloc[0], 100)
        with self.assertRaisesRegex(ValueError, 'factor'):
            updater._standardize_tushare(raw.drop(columns='adj_factor'), '00700', 'Hong Kong equities')

    def test_unadjusted_tencent_fallback_is_rejected(self):
        response = Mock()
        response.json.return_value = {'code': 0, 'data': {'sh600519': {
            'day': [['2026-11-18', 10, 11, 12, 9, 100]]}}}
        with patch.object(updater.requests, 'get', return_value=response):
            with self.assertRaises(updater.ProviderContractError):
                updater.fetch_tencent_stock('600519', 'name', 'A-share')

    def test_rate_limit_stops_without_retry(self):
        rate_error = type('Push2RateLimitError', (RuntimeError,), {})('cooldown required')
        provider = SimpleNamespace(stock_zh_a_hist_em=Mock(side_effect=rate_error))
        with patch.dict(sys.modules, {'akshare': provider}), patch.object(updater.time, 'sleep') as sleep:
            with self.assertRaises(updater.ProviderRateLimited):
                updater.fetch_with_retry(updater.fetch_a_stock, '600519', 'name')
        provider.stock_zh_a_hist_em.assert_called_once()
        sleep.assert_not_called()

    def test_contract_failure_falls_back_without_retry(self):
        provider = Mock(side_effect=updater.ProviderContractError('missing qfq series'))
        with patch.object(updater.time, 'sleep') as sleep:
            self.assertIsNone(updater.fetch_with_retry(provider, '600519', 'name'))
        provider.assert_called_once()
        sleep.assert_not_called()

    def test_http_and_service_rate_limit_signals_are_respected(self):
        error = RuntimeError('network response')
        error.response = SimpleNamespace(status_code=429)
        for candidate in (error, RuntimeError('Too many requests'), RuntimeError('每分钟最多访问 200 次')):
            with self.subTest(error=str(candidate)), self.assertRaises(updater.ProviderRateLimited):
                updater.stop_on_rate_limit(candidate, 'provider')

    def test_tencent_rate_limit_in_a_successful_http_response_is_not_retried(self):
        for payload in ({'code': 429}, {'code': -1, 'msg': 'Too many requests'}):
            response = Mock()
            response.json.return_value = payload
            with self.subTest(payload=payload), \
                    patch.object(updater.requests, 'get', return_value=response) as get, \
                    patch.object(updater.time, 'sleep') as sleep:
                with self.assertRaises(updater.ProviderRateLimited):
                    updater.fetch_with_retry(updater.fetch_tencent_stock, '600519', 'name', 'A-share')
                get.assert_called_once()
                sleep.assert_not_called()

    def test_tencent_qfq_and_tushare_amount_units(self):
        response = Mock()
        response.json.return_value = {'code': 0, 'data': {'sh600519': {
            'qfqday': [['2026-11-18', '10', '11', '12', '9', '100']]}}}
        with patch.object(updater.requests, 'get', return_value=response):
            frame = updater.fetch_tencent_stock('600519', 'name', 'A-share')
            self.assertEqual(frame['Close'].iloc[0], 11)
        raw = pd.DataFrame({'trade_date': ['20261118'], 'open': [10], 'close': [11],
                            'high': [12], 'low': [9], 'vol': [100], 'amount': [5]})
        frame = updater._standardize_tushare(raw, '600519', 'A-share')
        self.assertEqual(frame['Amount'].iloc[0], 5000)

    def test_retry_is_bounded(self):
        provider = Mock(return_value=None)
        with patch.object(updater.time, 'sleep'):
            self.assertIsNone(updater.fetch_with_retry(provider, '600519', 'name'))
        self.assertEqual(provider.call_count, updater.MAX_FETCH_ATTEMPTS)


class SnapshotIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        fixture_root(self.root)

    def refresh(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return pipeline.refresh_snapshot(root=self.root, as_of='2026-11-19', **kwargs)

    def test_full_build_matches_every_input_and_is_idempotent(self):
        self.refresh()
        entries = pipeline.validate_snapshot(self.root)
        self.assertEqual(entries['600519']['end'], '2026-11-18')
        before = snapshot_bytes(self.root)
        self.refresh()
        self.assertEqual(snapshot_bytes(self.root), before)
        manifest = json.loads((self.root / pipeline.MANIFEST).read_text())
        self.assertEqual(manifest['instruments']['00700']['name'], 'Tencent Holdings')
        self.assertEqual(manifest['instruments']['00700']['adjustment'], 'not recorded')

    def test_builder_failure_leaves_the_entire_checkout_unchanged(self):
        script = self.root / pipeline.BUILD_SCRIPTS[-1]
        script.write_text('raise RuntimeError("deliberate test failure")\n', encoding='utf-8')
        before = snapshot_bytes(self.root)
        with self.assertRaisesRegex(RuntimeError, 'deliberate test failure'):
            self.refresh()
        self.assertEqual(snapshot_bytes(self.root), before)

    def test_refresh_preserves_dashboard_layout_and_indicator_functions(self):
        def without_data(name):
            html = (self.root / name).read_text(encoding='utf-8')
            match = re.search(r'const (?:STOCKS|EMBEDDED) =\s*', html)
            _, end = json.JSONDecoder().raw_decode(html, match.end())
            return html[:match.end()] + '<DATA>' + html[end:]
        pages = [name for name in pipeline.OUTPUTS if name.endswith('.html')]
        # Task 3 is generated from its maintained template, so build it once first.
        self.refresh()
        before = {name: without_data(name) for name in pages}
        self.refresh(frames={s.code: bars(s.code, ('2026-11-18', '2026-11-19'))
                             for s in market.INSTRUMENTS})
        self.assertEqual({name: without_data(name) for name in pages}, before)

    def test_missing_builder_is_an_error(self):
        (self.root / pipeline.BUILD_SCRIPTS[0]).unlink()
        before = snapshot_bytes(self.root)
        with self.assertRaises(FileNotFoundError):
            self.refresh()
        self.assertEqual(snapshot_bytes(self.root), before)

    def test_failed_write_restores_previous_bundle(self):
        before = snapshot_bytes(self.root)
        original = pipeline.atomic_bytes
        calls = 0
        def fail_once(path, content):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('deliberate write failure')
            return original(path, content)
        with patch.object(pipeline, 'atomic_bytes', side_effect=fail_once), self.assertRaises(OSError):
            self.refresh()
        self.assertEqual(snapshot_bytes(self.root), before)

    def test_mocked_live_refresh_updates_all_dashboard_payloads(self):
        def fetch(fetcher, code, name, *extra):
            return bars(code, ('2026-11-18', '2026-11-19'))
        with patch.object(updater, 'BASE_DIR', str(self.root)), \
                patch.object(updater, 'fetch_with_retry', side_effect=fetch), \
                patch.object(updater.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            result = updater.main(['--force', '--as-of', '2026-11-19'])
        self.assertEqual(result, 0)
        self.assertTrue(all(e['end'] == '2026-11-19' for e in pipeline.validate_snapshot(self.root).values()))

    def test_duplicate_alias_requires_explicit_migration_and_has_backup(self):
        item = market.INSTRUMENTS[0]
        alias = self.root / 'data/csv' / item.legacy_filename
        bars(item.code, ('2026-11-18', '2026-11-19')).to_csv(alias, index=False)
        old_alias = alias.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            self.refresh()
        self.refresh(migrate_legacy=True)
        frame = market.load_prices(item.code, self.root / 'data/csv')
        self.assertEqual(len(frame), 3)
        self.assertFalse(alias.exists())
        backups = list((self.root / '.refresh-backups').glob(f'*/data/csv/{item.legacy_filename}'))
        self.assertEqual(backups[0].read_bytes(), old_alias)

    def test_validator_rejects_stale_dashboard_and_modified_csv(self):
        self.refresh()
        page = self.root / 'Task3/dashboard/data.json'
        original = page.read_text()
        page.write_text(original.replace('10.375', '10.37'), encoding='utf-8')
        with self.assertRaises(ValueError):
            pipeline.validate_snapshot(self.root)
        page.write_text(original, encoding='utf-8')
        path = market.canonical_path('600519', self.root / 'data/csv')
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'manifest mismatch'):
            pipeline.validate_snapshot(self.root)

    def test_date_summary_and_manifest_identity_must_match_inputs(self):
        self.refresh()
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('task2_data_test', ROOT / 'Task2/scripts/build_dashboard.py')
        builder = module_from_spec(spec)
        spec.loader.exec_module(builder)
        path = self.root / 'Task2/dashboard/index.html'
        stocks, _ = pipeline.embedded_stocks(path)
        stocks['600519']['end'] = '2026-01-01'
        original = path.read_text(encoding='utf-8')
        path.write_text(builder.replace_payload(original, stocks), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'summary mismatch'):
            pipeline.validate_snapshot(self.root)
        path.write_text(original, encoding='utf-8')
        manifest_path = self.root / pipeline.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest['instruments']['00700']['volume_unit'] = '100-share lots'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'units mismatch'):
            pipeline.validate_snapshot(self.root)

    def test_adjustment_label_does_not_verify_an_uncovered_legacy_prefix(self):
        frames = {item.code: bars(item.code, ('2026-11-18', '2026-11-19'))
                  for item in market.INSTRUMENTS}
        for frame in frames.values():
            frame.attrs.update(source='Test adjusted provider', adjustment='qfq')
        entries = self.refresh(frames=frames)
        self.assertTrue(all(entry['adjustment'] == 'not recorded' for entry in entries.values()))
        frames = {item.code: bars(item.code, ('2026-11-17', '2026-11-18', '2026-11-19'))
                  for item in market.INSTRUMENTS}
        for frame in frames.values():
            frame.attrs.update(source='Test adjusted provider', adjustment='qfq')
        entries = self.refresh(frames=frames)
        self.assertTrue(all(entry['adjustment'] == 'qfq' for entry in entries.values()))

    def test_no_partial_publication_when_one_provider_fails(self):
        before = snapshot_bytes(self.root)
        with patch.object(updater, 'BASE_DIR', str(self.root)), \
                patch.object(updater, 'fetch_with_retry', return_value=None), \
                patch.object(updater.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(updater.main(['--force', '--as-of', '2026-11-19']), 1)
        self.assertEqual(snapshot_bytes(self.root), before)

    def test_rate_limit_aborts_all_symbols_without_partial_publication(self):
        before = snapshot_bytes(self.root)
        with patch.object(updater, 'BASE_DIR', str(self.root)), \
                patch.object(updater, 'fetch_with_retry', side_effect=updater.ProviderRateLimited('cooldown')) as fetch, \
                patch.object(updater.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(updater.main(['--force', '--as-of', '2026-11-19']), 1)
        fetch.assert_called_once()
        self.assertEqual(snapshot_bytes(self.root), before)


if __name__ == '__main__':
    unittest.main()
