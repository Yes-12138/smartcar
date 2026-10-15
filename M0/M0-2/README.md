# M0-2：CSV 两列的皮尔逊相关系数

本工具读取 YAML 配置指定的 CSV 文件，手写计算两列数值的皮尔逊相关系数。起始脚本、配置和样例数据来自 [22SmartCar M0-2 题目](https://github.com/Blake-John/22SmartCar/tree/main/round1/M0/M0-2)；原仓库许可证见 `LICENSE.upstream`。

## 运行

在作业仓库根目录执行：

```bash
# 如果当前 Python 环境还没有 PyYAML，先安装依赖；已有依赖时可跳过。
./.venv/bin/python -m pip install -r M0/M0-2/requirements.txt

# 从仓库根目录运行，CSV 路径会相对配置文件解析。
./.venv/bin/python M0/M0-2/legacy_corr.py --config M0/M0-2/config.yaml
```

如果系统的 `python3` 已安装 PyYAML，也可直接使用现场验收命令：

```bash
python3 M0/M0-2/legacy_corr.py --config M0/M0-2/config.yaml
```

进入 `M0/M0-2` 后，`python3 legacy_corr.py --config config.yaml` 同样可用。还支持位置参数 `python3 legacy_corr.py config.yaml`。

## 输入格式

YAML 至少需要 `input_csv`、`columns.x` 和 `columns.y`：

```yaml
input_csv: sample_data.csv
columns:
  x: sensor_a
  y: sensor_b
task:
  verbose: true
```

- `input_csv` 是 CSV 文件路径。相对路径以 YAML 文件所在目录为基准；绝对路径也可使用。
- `columns.x` 和 `columns.y` 是要计算的 CSV 列名，必须与表头**完全一致**，包括大小写和空格。其他 CSV 列会被忽略。
- `task.verbose` 可选，默认为 `true`。设为 `false` 时只打印 `r`；`task.name` 等其他元数据不参与计算。
- CSV 第一行必须是表头，后面至少有两行数据；选中的每个单元格必须是有限数字，不能留空、写入 `NaN` 或无穷大。两列都必须有变化，否则相关系数无定义。
- UTF-8 和带 BOM 的 UTF-8 CSV 均可读取。CSV 表头不能有重复列名。

## 输出与错误

样例输出：

```text
n = 40
mean_x = 49.437825
mean_y = 43.310725000000005
r = 0.5634747254524841
```

`n` 是参与计算的成对数据行数；`mean_x`、`mean_y` 分别是两列的算术平均值；`r` 是皮尔逊相关系数，范围为 `[-1, 1]`。接近 `1` 表示强正线性关系，接近 `-1` 表示强负线性关系，接近 `0` 表示线性关系弱。`r` 不能说明因果关系。

文件不存在、空 CSV、列名不匹配、非法数字和零方差等输入错误会写到 stderr，并以非零状态退出，不会向使用者显示 Python 栈回溯。

## 测试

在作业仓库根目录执行：

```bash
python3 -m unittest discover -s M0/M0-2/tests -v
```

测试覆盖正相关、负相关、异常输入、命令行调用及配置文件相对路径。若当前环境已安装 NumPy，还会用 `numpy.corrcoef` 独立校验样例结果；NumPy 仅用于验证，不参与工具的核心计算。

## AI 使用说明

函数拆分、公式修正、异常处理、单元测试和本 README 由 Codex 辅助编写。Codex 已在 Ubuntu VM 上运行样例与单元测试，并与 `numpy.corrcoef` 比对样例结果。截至本次提交，仓库所有者尚未向 Codex 确认自己已逐行研究和验证代码，因此这里不声称已由本人逐行复核。答辩前应亲自逐行检查，并能解释均值、离差平方和、零方差以及每类错误的处理方式。
