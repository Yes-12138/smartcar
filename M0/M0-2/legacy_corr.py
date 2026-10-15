"""Read two CSV columns and report their Pearson correlation."""

import argparse
import csv
from itertools import chain
import math
import sys
from pathlib import Path

import yaml


class InputError(ValueError):
    """An input file or selected data column cannot be used."""


def load_config(config_path: Path):
    """Return the CSV path and selected column names from a YAML file."""
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise InputError("配置文件必须是包含 input_csv 和 columns 的 YAML 映射")
    columns = config.get("columns")
    if not isinstance(columns, dict):
        raise InputError("配置项 columns 必须包含 x 和 y 两个列名")
    for key, value in (
        ("input_csv", config.get("input_csv")),
        ("columns.x", columns.get("x")),
        ("columns.y", columns.get("y")),
    ):
        if not isinstance(value, str) or not value.strip():
            raise InputError(f"配置项 {key} 必须是非空字符串")
    csv_path = Path(config["input_csv"])
    if not csv_path.is_absolute():
        csv_path = config_path.parent / csv_path
    task = config.get("task", {})
    if not isinstance(task, dict):
        raise InputError("配置项 task 必须是映射")
    verbose = task.get("verbose", True)
    if not isinstance(verbose, bool):
        raise InputError("配置项 task.verbose 必须是 true 或 false")
    return csv_path, columns["x"], columns["y"], verbose


def read_columns(csv_path: Path, column_x: str, column_y: str):
    """Collect the selected columns as pairs of floating point values."""
    xs, ys = [], []
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise InputError(f"CSV 文件为空：{csv_path}")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise InputError("CSV 表头有重复列名")
        missing = [name for name in (column_x, column_y) if name not in reader.fieldnames]
        if missing:
            raise InputError(f"CSV 缺少指定列：{', '.join(missing)}")
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise InputError(f"CSV 第 {line_number} 行的字段数多于表头")
            values = []
            for name in (column_x, column_y):
                raw = row[name]
                if raw is None or not raw.strip():
                    raise InputError(f"CSV 第 {line_number} 行的 {name} 列为空")
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise InputError(
                        f"CSV 第 {line_number} 行的 {name} 列不是数字：{raw!r}"
                    ) from exc
                if not math.isfinite(value):
                    raise InputError(f"CSV 第 {line_number} 行的 {name} 列必须是有限数字")
                values.append(value)
            xs.append(values[0])
            ys.append(values[1])
    if not xs:
        raise InputError(f"CSV 没有数据行：{csv_path}")
    return xs, ys


def calculate_correlation(xs, ys):
    """Return the count, both means, and the correlation coefficient."""
    if len(xs) != len(ys) or not xs:
        raise InputError("两列数据长度必须相同且不能为空")
    if any(not math.isfinite(value) for value in chain(xs, ys)):
        raise InputError("参与计算的值必须是有限数字")
    n = len(xs)
    mean_x = math.fsum(xs) / n
    mean_y = math.fsum(ys) / n
    centered = [(x - mean_x, y - mean_y) for x, y in zip(xs, ys)]
    dx = math.fsum(x * x for x, _ in centered)
    dy = math.fsum(y * y for _, y in centered)
    if dx == 0 or dy == 0:
        raise InputError("某列取值恒定，方差为 0，相关系数无定义")
    product = math.fsum(x * y for x, y in centered)
    r = product / (math.sqrt(dx) * math.sqrt(dy))
    return n, mean_x, mean_y, max(-1.0, min(1.0, r))


def main(argv=None):
    """Run the command line tool."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_path", nargs="?", type=Path, help="YAML configuration")
    parser.add_argument("--config", type=Path, help="YAML configuration")
    args = parser.parse_args(argv)
    config_path = args.config or args.config_path
    if config_path is None:
        parser.error("需要通过 --config 指定 YAML 配置文件")
    try:
        csv_path, column_x, column_y, verbose = load_config(config_path)
        n, mean_x, mean_y, r = calculate_correlation(
            *read_columns(csv_path, column_x, column_y)
        )
    except FileNotFoundError as exc:
        print(f"错误：文件不存在：{exc.filename}", file=sys.stderr)
        return 1
    except (InputError, OSError, UnicodeError, csv.Error, yaml.YAMLError, OverflowError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    if verbose:
        print(f"n = {n}")
        print(f"mean_x = {mean_x}")
        print(f"mean_y = {mean_y}")
    print(f"r = {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
