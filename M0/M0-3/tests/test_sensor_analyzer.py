"""Tests for the M0-3 sensor data script."""

import csv
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sensor_analyzer import calculate_stats, clean_rows, read_rows, write_rows  # noqa: E402


class SensorAnalyzerTests(unittest.TestCase):
    def test_sample_stats_and_both_outlier_sides(self):
        rows = read_rows(ROOT / "sensor_data.csv")
        values = [row[2] for row in rows]
        mean, std = calculate_stats(rows)
        self.assertAlmostEqual(mean, statistics.fmean(values), places=12)
        self.assertAlmostEqual(std, statistics.pstdev(values), places=12)
        self.assertEqual(len(rows), 60)
        cleaned = clean_rows(rows, mean, std)
        self.assertEqual(len(cleaned), 57)
        removed_times = {row[0] for row in rows if row not in cleaned}
        self.assertEqual(removed_times, {"5.80", "5.90", "6.00"})

    def test_preserves_original_csv_text(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            output = Path(directory) / "cleaned.csv"
            write_rows(output, [("0.10", "43.00", 43.0)])
            with output.open(newline="", encoding="utf-8") as file:
                self.assertEqual(list(csv.reader(file)), [["time", "value"], ["0.10", "43.00"]])

    def test_constant_values_are_kept(self):
        rows = [("1", "5", 5.0), ("2", "5", 5.0)]
        mean, std = calculate_stats(rows)
        self.assertEqual((mean, std), (5.0, 0.0))
        self.assertEqual(clean_rows(rows, mean, std), rows)

    def test_empty_file_and_header_only_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            path = Path(directory) / "data.csv"
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CSV 文件为空"):
                read_rows(path)
            path.write_text("time,value\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "没有数据行"):
                read_rows(path)

    def test_missing_column_and_bad_number(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            path = Path(directory) / "data.csv"
            path.write_text("time,Value\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "time 和 value"):
                read_rows(path)
            path.write_text("time,value\n1,not-a-number\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "第 2 行"):
                read_rows(path)

    def test_default_cli_paths(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            folder = Path(directory)
            (folder / "sensor_data.csv").write_text("time,value\n1,5\n2,5\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "sensor_analyzer.py")],
                cwd=folder,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("mean = 5.0", result.stdout)
            self.assertIn("std = 0.0", result.stdout)
            self.assertTrue((folder / "cleaned_data.csv").exists())

    def test_explicit_cli_paths(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            folder = Path(directory)
            source = folder / "new_data.csv"
            output = folder / "result.csv"
            source.write_text("time,value\n1,3\n2,7\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "sensor_analyzer.py"), "--input", str(source), "--output", str(output)],
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8").splitlines(), ["time,value", "1,3", "2,7"])

    def test_missing_file_has_no_traceback(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "sensor_analyzer.py"), "--input", "no-such-data.csv"],
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

