"""一键计算两列 CSV 数据的皮尔逊相关系数。

把本文件放在 config.yaml 旁边，直接用 VS Code 的运行按钮执行即可。
"""

import csv
import math
from pathlib import Path

import yaml


# 配置文件的位置写在程序里，不需要再输入 --config。
CONFIG_FILE = Path(__file__).resolve().parent / "config.yaml"


def read_config():
    """从固定位置读取 CSV 文件名和列名。"""
    with CONFIG_FILE.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("config.yaml 的内容必须是 YAML 映射")
    columns = config.get("columns")
    if not isinstance(columns, dict):
        raise ValueError("config.yaml 缺少 columns")

    filename = config.get("input_csv")
    x_name = columns.get("x")
    y_name = columns.get("y")
    for label, value in (("input_csv", filename), ("columns.x", x_name), ("columns.y", y_name)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"配置项 {label} 必须是非空文字")

    csv_file = Path(filename)
    if not csv_file.is_absolute():
        csv_file = CONFIG_FILE.parent / csv_file
    return csv_file, x_name, y_name


def read_data(csv_file, x_name, y_name):
    """从 CSV 的指定两列读取数字。"""
    xs, ys = [], []
    with csv_file.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError("CSV 文件为空")
        for name in (x_name, y_name):
            if name not in reader.fieldnames:
                raise ValueError(f"CSV 找不到列：{name}")

        for line_number, row in enumerate(reader, start=2):
            pair = []
            for name in (x_name, y_name):
                raw = row[name]
                if raw is None or not raw.strip():
                    raise ValueError(f"CSV 第 {line_number} 行的 {name} 为空")
                try:
                    number = float(raw)
                except ValueError as error:
                    raise ValueError(f"CSV 第 {line_number} 行的 {name} 不是数字：{raw}") from error
                if not math.isfinite(number):
                    raise ValueError(f"CSV 第 {line_number} 行的 {name} 不是有限数字")
                pair.append(number)
            xs.append(pair[0])
            ys.append(pair[1])

    if not xs:
        raise ValueError("CSV 没有数据行")
    return xs, ys


def calculate(xs, ys):
    """返回行数、两列均值、皮尔逊相关系数。"""
    n = len(xs)
    mean_x = math.fsum(xs) / n
    mean_y = math.fsum(ys) / n
    differences = [(x - mean_x, y - mean_y) for x, y in zip(xs, ys)]

    numerator = math.fsum(dx * dy for dx, dy in differences)
    sum_x2 = math.fsum(dx * dx for dx, _ in differences)
    sum_y2 = math.fsum(dy * dy for _, dy in differences)
    if sum_x2 == 0 or sum_y2 == 0:
        raise ValueError("某一列的值都相同，无法计算相关系数")

    r = numerator / (math.sqrt(sum_x2) * math.sqrt(sum_y2))
    return n, mean_x, mean_y, max(-1.0, min(1.0, r))


def main():
    try:
        csv_file, x_name, y_name = read_config()
        xs, ys = read_data(csv_file, x_name, y_name)
        n, mean_x, mean_y, r = calculate(xs, ys)
    except (OSError, ValueError, yaml.YAMLError, csv.Error) as error:
        print(f"错误：{error}")
        return

    print(f"n = {n}")
    print(f"mean_x = {mean_x}")
    print(f"mean_y = {mean_y}")
    print(f"r = {r}")


if __name__ == "__main__":
    main()