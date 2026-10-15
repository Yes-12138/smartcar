"""Tests for configuration and dependency ordering."""

import sys
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scheduler import read_config, run_scheduler, topological_order, validate_config  # noqa: E402


class FakeClock:
    def __init__(self):
        self.seconds = 0.0

    def monotonic(self):
        return self.seconds

    def time(self):
        return 1700000000.0 + self.seconds

    def sleep(self, seconds):
        self.seconds += seconds


class ConfigurationTests(unittest.TestCase):
    def test_demo_yaml_and_json_are_equivalent(self):
        yaml_tasks, yaml_timeout = read_config(ROOT / "tasks_demo.yaml")
        json_tasks, json_timeout = read_config(ROOT / "tasks_demo.json")
        self.assertEqual(yaml_tasks, json_tasks)
        self.assertEqual((yaml_timeout, json_timeout), (15.0, 15.0))

    def test_forks_and_joins_have_valid_order(self):
        tasks, _ = read_config(ROOT / "tasks_demo.yaml")
        order = topological_order(tasks)
        self.assertEqual(len(order), len(tasks))
        for task in tasks:
            for dependency in task["dependencies"]:
                self.assertLess(order.index(dependency), order.index(task["name"]))

    def test_cycle_and_missing_dependency(self):
        first = {"name": "A", "duration": 0, "success_rate": 1, "dependencies": ["B"]}
        second = {"name": "B", "duration": 0, "success_rate": 1, "dependencies": ["A"]}
        with self.assertRaisesRegex(ValueError, "环"):
            validate_config({"tasks": [first, second]})
        with self.assertRaisesRegex(ValueError, "不存在"):
            validate_config({"tasks": [first]})

    def test_empty_duplicate_and_bad_rate(self):
        with self.assertRaisesRegex(ValueError, "非空列表"):
            validate_config({"tasks": []})
        task = {"name": "A", "duration": 0, "success_rate": 1, "dependencies": []}
        with self.assertRaisesRegex(ValueError, "重复"):
            validate_config({"tasks": [task, task]})
        with self.assertRaisesRegex(ValueError, "不能大于 1"):
            validate_config({"tasks": [{**task, "success_rate": 1.1}]})


class SchedulerTests(unittest.TestCase):
    def run_with_fake_clock(self, tasks, timeout=None, seed=42):
        fake = FakeClock()
        output = StringIO()
        with redirect_stdout(output):
            report = run_scheduler(
                tasks,
                timeout,
                seed=seed,
                sleep_fn=fake.sleep,
                clock=fake.monotonic,
                timestamp=fake.time,
            )
        return report, output.getvalue()

    def test_failure_skips_descendants_but_independent_task_runs(self):
        tasks = [
            {"name": "A", "duration": 0.1, "success_rate": 0, "dependencies": []},
            {"name": "B", "duration": 0.1, "success_rate": 1, "dependencies": ["A"]},
            {"name": "C", "duration": 0.2, "success_rate": 1, "dependencies": []},
            {"name": "D", "duration": 0.1, "success_rate": 1, "dependencies": ["B"]},
        ]
        report, text = self.run_with_fake_clock(tasks)
        records = {item["name"]: item for item in report["tasks"]}
        self.assertEqual([records[name]["status"] for name in "ABCD"],
                         ["FAILED", "SKIPPED", "SUCCESS", "SKIPPED"])
        self.assertEqual([records[name]["attempts"] for name in "ABCD"], [3, 0, 1, 0])
        self.assertAlmostEqual(report["total_duration"], 0.5)
        self.assertFalse(report["timeout"])
        self.assertIn("A: RETRY", text)
        self.assertNotIn("\033[", text)  # Redirected output has no ANSI color codes.

    def test_timeout_stops_current_sleep_and_marks_remaining_tasks(self):
        tasks = [
            {"name": "Long", "duration": 2, "success_rate": 1, "dependencies": []},
            {"name": "Next", "duration": 0, "success_rate": 1, "dependencies": ["Long"]},
        ]
        report, _ = self.run_with_fake_clock(tasks, timeout=1)
        self.assertTrue(report["timeout"])
        self.assertEqual(report["total_duration"], 1)
        self.assertEqual([item["status"] for item in report["tasks"]], ["TIMEOUT", "TIMEOUT"])
        self.assertEqual([item["attempts"] for item in report["tasks"]], [1, 0])
        self.assertEqual(report["tasks"][0]["duration"], 1)

    def test_seed_reproduces_success_after_two_retries(self):
        tasks = [{"name": "Try", "duration": 0, "success_rate": 0.5, "dependencies": []}]
        first, _ = self.run_with_fake_clock(tasks, seed=2)
        second, _ = self.run_with_fake_clock(tasks, seed=2)
        self.assertEqual(first["tasks"][0]["status"], "SUCCESS")
        self.assertEqual(first["tasks"][0]["attempts"], 3)
        self.assertEqual(first["tasks"][0]["status"], second["tasks"][0]["status"])
        self.assertEqual(first["tasks"][0]["attempts"], second["tasks"][0]["attempts"])


class CommandLineTests(unittest.TestCase):
    def test_json_cli_writes_complete_report(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            folder = Path(directory)
            config = folder / "tasks.json"
            report_path = folder / "report.json"
            config.write_text(json.dumps({"tasks": [
                {"name": "Init", "duration": 0, "success_rate": 1, "dependencies": []},
                {"name": "Next", "duration": 0, "success_rate": 1, "dependencies": ["Init"]},
            ]}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scheduler.py"), "--config", str(config),
                 "--report", str(report_path), "--seed", "42"],
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["timeout"])
            self.assertEqual([item["status"] for item in report["tasks"]], ["SUCCESS", "SUCCESS"])
            for item in report["tasks"]:
                self.assertEqual(item["attempts"], 1)
                self.assertIsNotNone(item["started_at"])
                self.assertIsNotNone(item["ended_at"])
                self.assertIn("duration", item)

    def test_override_timeout_marks_every_task(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            folder = Path(directory)
            config = folder / "tasks.json"
            report_path = folder / "report.json"
            config.write_text(json.dumps({"timeout": 10, "tasks": [
                {"name": "A", "duration": 0, "success_rate": 1, "dependencies": []},
                {"name": "B", "duration": 0, "success_rate": 1, "dependencies": ["A"]},
            ]}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scheduler.py"), "--config", str(config),
                 "--timeout", "0", "--report", str(report_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["timeout"])
            self.assertEqual([item["status"] for item in report["tasks"]], ["TIMEOUT", "TIMEOUT"])
            self.assertEqual([item["attempts"] for item in report["tasks"]], [0, 0])

    def test_invalid_cycle_is_readable_without_traceback(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            folder = Path(directory)
            config = folder / "tasks.json"
            config.write_text(json.dumps({"tasks": [
                {"name": "A", "duration": 0, "success_rate": 1, "dependencies": ["A"]},
            ]}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scheduler.py"), "--config", str(config)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("环", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
