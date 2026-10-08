"""Check Task 2 output paths without importing its network dependencies."""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def script_data_dir(name):
    script = ROOT / "Task2" / "scripts" / name
    tree = ast.parse(script.read_text(encoding="utf-8"))
    statements = [node for node in tree.body if isinstance(node, ast.Assign)]
    expressions = {
        target.id: node.value
        for node in statements
        for target in node.targets
        if isinstance(target, ast.Name) and target.id in {"BASE_DIR", "DATA_DIR"}
    }
    # Evaluate only the two path definitions with a controlled __file__.
    import os
    namespace = {"os": os, "__file__": str(script)}
    module = ast.Module(body=[ast.Assign(targets=[ast.Name(id=key, ctx=ast.Store())], value=value) for key, value in expressions.items()], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(script), "exec"), namespace)
    return Path(namespace["DATA_DIR"]).resolve()


class Task2PathsTest(unittest.TestCase):
    def test_update_and_build_use_repository_data(self):
        expected = ROOT / "data" / "csv"
        self.assertEqual(script_data_dir("update_data.py"), expected)
        self.assertEqual(script_data_dir("build_dashboard.py"), expected)


if __name__ == "__main__":
    unittest.main()
