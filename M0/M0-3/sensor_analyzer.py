#!/usr/bin/env python3
"""Read sensor values, remove 2-standard-deviation outliers, and save a CSV."""

import argparse
import csv
import math
import sys
from pathlib import Path


def read_rows(path):
    """Keep the original CSV text and a numeric copy of each value."""
    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError("CSV 文件为空")
        if "time" not in reader.fieldnames or "value" not in reader.fieldnames:
            raise ValueError("CSV 表头必须包含 time 和 value 两列")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV 表头不能有重复列名")

        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"第 {line_number} 行的字段数多于表头")
            time_text = row["time"]
            value_text = row["value"]
            if not time_text or not time_text.strip():
                raise ValueError(f"第 {line_number} 行的 time 为空")
            if not value_text or not value_text.strip():
                raise ValueError(f"第 {line_number} 行的 value 为空")
            try:
                value = float(value_text)
            except ValueError as exc:
                raise ValueError(f"第 {line_number} 行的 value 不是数字：{value_text!r}") from exc
            if not math.isfinite(value):
                raise ValueError(f"第 {line_number} 行的 value 必须是有限数字")
            rows.append((time_text, value_text, value))

    if not rows:
        raise ValueError("CSV 没有数据行")
    return rows


def calculate_stats(rows):
    """Use the original values to calculate the population mean and std."""
    mean = math.fsum(row[2] for row in rows) / len(rows)
    variance = math.fsum((row[2] - mean) ** 2 for row in rows) / len(rows)
    return mean, math.sqrt(variance)


def clean_rows(rows, mean, std):
    """Keep values within two standard deviations, including the boundary."""
    return [row for row in rows if abs(row[2] - mean) <= 2 * std]


def write_rows(path, rows):
    """Save the original time and value text for rows that remain."""
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["time", "value"])
        for time_text, value_text, _ in rows:
            writer.writerow([time_text, value_text])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("sensor_data.csv"))
    parser.add_argument("--output", type=Path, default=Path("cleaned_data.csv"))
    args = parser.parse_args(argv)

    try:
        rows = read_rows(args.input)
        mean, std = calculate_stats(rows)
        cleaned = clean_rows(rows, mean, std)
        write_rows(args.output, cleaned)
    except FileNotFoundError as exc:
        print(f"错误：文件不存在：{exc.filename}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, csv.Error, ValueError, OverflowError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print("=== 传感器数据分析 ===")
    print(f"共读取 {len(rows)} 条数据")
    print(f"均值 mean = {mean}")
    print(f"标准差 std = {std}")
    print(f"清洗后剩余 {len(cleaned)} 条")
    print(f"已保存到 {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
