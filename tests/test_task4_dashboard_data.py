"""Check embedded-data refresh without changing the dashboard interface."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'Task4' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('task4_prepare_data', SCRIPTS / 'prepare_data.py')
dashboard_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard_data)
sys.path.remove(str(SCRIPTS))


class DashboardDataTest(unittest.TestCase):
    def test_refresh_preserves_layout_and_strategy_code(self):
        prefix = '<h1>Turtle strategy</h1>\n<script>\nconst STOCKS = '
        suffix = ';\nfunction backtest() { return STOCKS; }\n</script>'
        stocks = {'600519': {'records': 2}}
        updated = dashboard_data.replace_stock_payload(prefix + '{"old": {}}' + suffix, stocks)
        self.assertEqual(updated, prefix + json.dumps(stocks) + suffix)
        self.assertEqual(dashboard_data.replace_stock_payload(updated, stocks), updated)

    def test_refresh_handles_multiline_json(self):
        updated = dashboard_data.replace_stock_payload('const STOCKS = {\n"old": {}\n};', {})
        self.assertEqual(updated, 'const STOCKS = {};')

    def test_refresh_escapes_script_delimiters(self):
        stocks = {'name': '</script><script>alert(1)</script>'}
        updated = dashboard_data.replace_stock_payload('const STOCKS = {};', stocks)
        self.assertNotIn('</script>', updated)
        self.assertEqual(json.loads(updated[len('const STOCKS = '):-1]), stocks)

    def test_rejects_missing_or_duplicate_binding(self):
        for html in ('<h1>No data</h1>', 'const STOCKS = {};\nconst STOCKS = {};'):
            with self.subTest(html=html), self.assertRaises(ValueError):
                dashboard_data.replace_stock_payload(html, {})

    def test_rejects_invalid_data_binding(self):
        for html in ('const STOCKS = {broken};', 'const STOCKS = [];', 'const STOCKS = {} + other;'):
            with self.subTest(html=html), self.assertRaises(ValueError):
                dashboard_data.replace_stock_payload(html, {})

    def test_rejects_non_finite_prices(self):
        with self.assertRaises(ValueError):
            dashboard_data.replace_stock_payload('const STOCKS = {};', {'price': float('nan')})

    def test_missing_snapshot_stops_the_refresh(self):
        with patch.object(dashboard_data, 'load_stock', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                dashboard_data.build_stocks_json()

    def test_snapshot_lookup_uses_symbol_and_sorts_dates(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / '600519_kweichow_moutai_a_share_daily.csv'
            snapshot.write_text('Date,Close\n2026-01-02,12\n2026-01-01,11\n', encoding='utf-8')
            frame = dashboard_data.load_stock('600519', 'Kweichow Moutai', 'A-share', directory)
            self.assertEqual(frame['Close'].tolist(), [11, 12])

    def test_snapshot_lookup_rejects_ambiguous_matches(self):
        with TemporaryDirectory() as directory:
            for name in ('600519_a_daily.csv', '600519_b_daily.csv'):
                (Path(directory) / name).write_text('Date,Close\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                dashboard_data.load_stock('600519', 'Moutai', 'A-share', directory)

    def test_snapshot_lookup_reports_missing_instrument(self):
        with TemporaryDirectory() as directory, self.assertRaises(FileNotFoundError):
            dashboard_data.load_stock('600519', 'Moutai', 'A-share', directory)


if __name__ == '__main__':
    unittest.main()
