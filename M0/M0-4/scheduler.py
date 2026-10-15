#!/usr/bin/env python3
"""Run simulated tasks after their dependencies finish."""

from collections import deque
import json
import math
from pathlib import Path

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
