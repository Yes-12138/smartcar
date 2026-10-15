"""Tests for configuration and dependency ordering."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scheduler import read_config, topological_order, validate_config  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
