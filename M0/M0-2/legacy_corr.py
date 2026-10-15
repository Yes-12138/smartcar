"""Read two CSV columns and report their Pearson correlation."""

import argparse
import csv
import math
from pathlib import Path

import yaml


def load_config(config_path: Path):
    """Return the CSV path and selected column names from a YAML file."""
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    csv_path = Path(config["input_csv"])
    if not csv_path.is_absolute():
        csv_path = config_path.parent / csv_path
    return csv_path, config["columns"]["x"], config["columns"]["y"]


def read_columns(csv_path: Path, column_x: str, column_y: str):
    """Collect the selected columns as pairs of floating point values."""
    xs, ys = [], []
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            xs.append(float(row[column_x]))
            ys.append(float(row[column_y]))
    return xs, ys


def calculate_correlation(xs, ys):
    """Return the count, both means, and the correlation coefficient."""
    n = len(xs)
    mean_x = math.fsum(xs) / n
    mean_y = math.fsum(ys) / n
    centered = [(x - mean_x, y - mean_y) for x, y in zip(xs, ys)]
    dx = math.fsum(x * x for x, _ in centered)
    dy = math.fsum(y * y for _, y in centered)
    product = math.fsum(x * y for x, y in centered)
    return n, mean_x, mean_y, product / (math.sqrt(dx) * math.sqrt(dy))


def main(argv=None):
    """Run the command line tool."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="YAML configuration")
    args = parser.parse_args(argv)
    csv_path, column_x, column_y = load_config(args.config)
    n, mean_x, mean_y, r = calculate_correlation(
        *read_columns(csv_path, column_x, column_y)
    )
    print(f"n = {n}")
    print(f"mean_x = {mean_x}")
    print(f"mean_y = {mean_y}")
    print(f"r = {r}")


if __name__ == "__main__":
    main()
