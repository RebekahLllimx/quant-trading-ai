"""Exercise plotting adapters without loading optional rendering packages."""

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from market_data import INSTRUMENTS, canonical_path, load_prices, volume_in_shares

ROOT = Path(__file__).resolve().parents[1]


def function_from_script(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[name]


class CompatibilityLoaderTest(unittest.TestCase):
    def test_plot_loaders_use_canonical_snapshots(self):
        with TemporaryDirectory() as directory:
            item = INSTRUMENTS[0]
            pd.DataFrame({'Date': ['2026-11-18'], 'Symbol': [item.code],
                          'Open': [10.0], 'High': [12.0], 'Low': [9.0],
                          'Close': [11.0], 'Volume': [200.0]}).to_csv(
                              canonical_path(item.code, directory), index=False)
            for path, function, arguments in [
                ('Task1/scripts/plot_candlestick.py', 'fetch_a_stock', (item.code,)),
                ('Task1/scripts/plot_candlestick.py', 'fetch_hk_stock', (item.code,)),
                ('Task2/scripts/plot_indicators.py', 'load_stock', (item.code, item.name, item.market)),
                ('Task3/scripts/plot_strategy.py', 'load_stock', (item.code, item.name, item.market)),
            ]:
                with self.subTest(path=path, function=function):
                    load = function_from_script(path, function, {'DATA_DIR': directory, 'load_prices': load_prices})
                    self.assertEqual(load(*arguments)['Close'].tolist(), [11.0])
            load = function_from_script('Task1/scripts/plot_multi_stock.py', 'fetch_stock_data',
                                        {'DATA_DIR': directory, 'load_prices': load_prices})
            self.assertEqual(load(item.code)['ts_code'].tolist(), [item.code])

    def test_cross_market_volume_conversion(self):
        frame = pd.DataFrame({'Volume': [200.0]})
        self.assertEqual(volume_in_shares(frame, '600519').iloc[0], 20_000.0)
        self.assertEqual(volume_in_shares(frame, '00700').iloc[0], 200.0)

    def test_indicator_plot_volume_uses_millions_of_shares(self):
        prepare = function_from_script('Task2/scripts/plot_indicators.py', 'prepare_ohlc',
                                       {'volume_in_shares': volume_in_shares})
        frame = pd.DataFrame({'Date': pd.to_datetime(['2026-11-18']), 'Symbol': ['00700'],
                              'Open': [10], 'High': [12], 'Low': [9], 'Close': [11],
                              'Volume': [2_000_000]})
        self.assertEqual(prepare(frame)['Volume'].iloc[0], 2.0)

    def test_summary_drawdown_is_relative_to_each_running_peak(self):
        summarize = function_from_script('Task1/scripts/plot_multi_stock.py', 'build_statistics_table', {'pd': pd})
        frame = pd.DataFrame({'close': [100.0, 50.0, 200.0, 150.0], 'vol': [100.0] * 4})
        info = {'Example': {'code': '600519', 'sector': 'Example', 'market': 'A-share'}}
        result = summarize({'Example': frame}, info)
        self.assertEqual(result.iloc[0]['Maximum Drawdown(%)'], '50.00')


if __name__ == '__main__':
    unittest.main()
