#!/usr/bin/env python3
"""Run simulated tasks after their dependencies finish."""

from collections import deque
import json
import math
from pathlib import Path
import random
import sys
import time

import yaml


def read_config(path):
    """Read YAML or JSON, then check every task before scheduling it."""
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as file:
        if suffix == ".json":
            config = json.load(file)
        elif suffix in (".yaml", ".yml"):
            config = yaml.safe_load(file)
        else:
            raise ValueError("配置文件必须是 .yaml、.yml 或 .json")
    return validate_config(config)


def finite_number(value, field, minimum=None, maximum=None):
    """Reject booleans, text, NaN, infinity, and out-of-range numbers."""
    if type(value) not in (int, float):
        raise ValueError(f"{field} 必须是有限数字")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} 必须是有限数字") from exc
    if not math.isfinite(value):
        raise ValueError(f"{field} 必须是有限数字")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} 不能小于 {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} 不能大于 {maximum}")
    return value


def validate_config(config):
    """Return normalized tasks and the optional global timeout."""
    if not isinstance(config, dict):
        raise ValueError("配置文件最外层必须是映射")
    raw_tasks = config.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError("tasks 必须是非空列表")

    tasks = []
    names = set()
    for index, raw in enumerate(raw_tasks, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"第 {index} 个任务必须是映射")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"第 {index} 个任务的 name 必须是非空字符串")
        if name in names:
            raise ValueError(f"任务名重复：{name}")
        names.add(name)
        duration = finite_number(raw.get("duration"), f"{name}.duration", minimum=0)
        success_rate = finite_number(
            raw.get("success_rate"), f"{name}.success_rate", minimum=0, maximum=1
        )
        dependencies = raw.get("dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(item, str) or not item.strip() for item in dependencies
        ):
            raise ValueError(f"{name}.dependencies 必须是任务名列表")
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"{name}.dependencies 不能重复")
        tasks.append(
            {
                "name": name,
                "duration": duration,
                "success_rate": success_rate,
                "dependencies": dependencies,
            }
        )

    for task in tasks:
        for dependency in task["dependencies"]:
            if dependency not in names:
                raise ValueError(f"任务 {task['name']} 依赖不存在的任务：{dependency}")

    timeout = config.get("timeout")
    if timeout is not None:
        timeout = finite_number(timeout, "timeout", minimum=0)
    topological_order(tasks)  # An invalid dependency cycle is a config error.
    return tasks, timeout


def topological_order(tasks):
    """Return names in dependency order, including forks and joins."""
    indegree = {task["name"]: len(task["dependencies"]) for task in tasks}
    dependents = {task["name"]: [] for task in tasks}
    for task in tasks:
        for dependency in task["dependencies"]:
            dependents[dependency].append(task["name"])

    ready = deque(name for name in indegree if indegree[name] == 0)
    order = []
    while ready:
        name = ready.popleft()
        order.append(name)
        for follower in dependents[name]:
            indegree[follower] -= 1
            if indegree[follower] == 0:
                ready.append(follower)

    if len(order) != len(tasks):
        raise ValueError("依赖关系存在环，无法安排任务顺序")
    return order


COLORS = {
    "SUCCESS": "\033[32m",
    "FAILED": "\033[31m",
    "RETRY": "\033[33m",
    "SKIPPED": "\033[34m",
    "TIMEOUT": "\033[31m",
}


def show_status(name, status, detail=""):
    """Print status immediately, with color only in an interactive terminal."""
    message = f"{name}: {status}"
    if detail:
        message += f" ({detail})"
    if sys.stdout.isatty():
        message = f"{COLORS[status]}{message}\033[0m"
    print(message, flush=True)


def run_scheduler(tasks, timeout, seed=None, sleep_fn=None, clock=None, timestamp=None):
    """Run tasks once dependencies succeed; allow two retries per task."""
    sleep_fn = sleep_fn or time.sleep
    clock = clock or time.monotonic
    timestamp = timestamp or time.time
    rng = random.Random(seed)
    tasks_by_name = {task["name"]: task for task in tasks}
    order = topological_order(tasks)
    records = {
        task["name"]: {
            "name": task["name"],
            "status": "PENDING",
            "attempts": 0,
            "duration": 0.0,
            "started_at": None,
            "ended_at": None,
        }
        for task in tasks
    }
    start = clock()
    deadline = None if timeout is None else start + timeout
    timed_out = False

    for name in order:
        task = tasks_by_name[name]
        record = records[name]
        if deadline is not None and clock() >= deadline:
            timed_out = True
            break
        if any(records[dependency]["status"] != "SUCCESS" for dependency in task["dependencies"]):
            record["status"] = "SKIPPED"
            show_status(name, "SKIPPED", "前置任务未成功")
            continue

        for attempt in range(1, 4):
            remaining = None if deadline is None else deadline - clock()
            if remaining is not None and remaining <= 0:
                record["status"] = "TIMEOUT"
                timed_out = True
                show_status(name, "TIMEOUT")
                break

            record["attempts"] = attempt
            if record["started_at"] is None:
                record["started_at"] = timestamp()
            print(f"开始 {name}：第 {attempt} 次尝试", flush=True)
            attempt_start = clock()
            sleep_seconds = task["duration"] if remaining is None else min(task["duration"], remaining)
            sleep_fn(sleep_seconds)
            record["duration"] += max(0.0, clock() - attempt_start)
            record["ended_at"] = timestamp()

            if deadline is not None and clock() >= deadline:
                record["status"] = "TIMEOUT"
                timed_out = True
                show_status(name, "TIMEOUT", "已到总时限")
                break
            if rng.random() < task["success_rate"]:
                record["status"] = "SUCCESS"
                show_status(name, "SUCCESS", f"尝试 {attempt} 次")
                break
            if attempt < 3:
                show_status(name, "RETRY", f"第 {attempt} 次失败")
            else:
                record["status"] = "FAILED"
                show_status(name, "FAILED", "已尝试 3 次")

        if timed_out:
            break

    if timed_out:
        for record in records.values():
            if record["status"] == "PENDING":
                record["status"] = "TIMEOUT"
                show_status(record["name"], "TIMEOUT", "未开始")

    for record in records.values():
        record["duration"] = round(record["duration"], 6)
    return {
        "timeout": timed_out,
        "total_duration": round(clock() - start, 6),
        "tasks": list(records.values()),
    }
