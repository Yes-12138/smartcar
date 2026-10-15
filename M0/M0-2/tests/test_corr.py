"""Regression tests for the M0-2 correlation command."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legacy_corr import InputError, calculate_correlation, read_columns  # noqa: E402

try:
    import numpy as np
except ImportError:  # NumPy is only used for optional independent verification.
    np = None


class CorrelationTests(unittest.TestCase):
    def test_perfect_positive_correlation(self):
        self.assertAlmostEqual(calculate_correlation([1, 2, 3], [2, 4, 6])[3], 1.0)

    def test_perfect_negative_correlation(self):
        self.assertAlmostEqual(calculate_correlation([1, 2, 3], [6, 4, 2])[3], -1.0)

    @unittest.skipIf(np is None, "NumPy is not installed")
    def test_sample_matches_numpy(self):
        xs, ys = read_columns(ROOT / "sample_data.csv", "sensor_a", "sensor_b")
        actual = calculate_correlation(xs, ys)[3]
        expected = float(np.corrcoef(xs, ys)[0, 1])
        self.assertAlmostEqual(actual, expected, places=12)

    def test_constant_column_is_undefined(self):
        with self.assertRaisesRegex(InputError, "方差为 0"):
            calculate_correlation([1, 1, 1], [2, 3, 4])

    def test_empty_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.csv"
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(InputError, "CSV 文件为空"):
                read_columns(path, "x", "y")

    def test_header_only_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "headers.csv"
            path.write_text("x,y\n", encoding="utf-8")
            with self.assertRaisesRegex(InputError, "没有数据行"):
                read_columns(path, "x", "y")

    def test_missing_column(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "columns.csv"
            path.write_text("x,z\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(InputError, "缺少指定列：y"):
                read_columns(path, "x", "y")

    def test_invalid_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            path.write_text("x,y\n1,not-a-number\n", encoding="utf-8")
            with self.assertRaisesRegex(InputError, "第 2 行"):
                read_columns(path, "x", "y")

    def test_command_uses_csv_relative_to_config(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "data.csv").write_text("a,b\n1,2\n2,4\n3,6\n", encoding="utf-8")
            (folder / "config.yaml").write_text(
                "input_csv: data.csv\ncolumns:\n  x: a\n  y: b\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "legacy_corr.py"), "--config", str(folder / "config.yaml")],
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            r_line = next(line for line in result.stdout.splitlines() if line.startswith("r = "))
            self.assertAlmostEqual(float(r_line.removeprefix("r = ")), 1.0, places=12)

    def test_missing_config_exits_without_traceback(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "legacy_corr.py"), "--config", "does-not-exist.yaml"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("文件不存在", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
