# M0-2：计算两列数据的相关系数

题目给的 `legacy_corr.py` 能读配置和 CSV，但样例算出来的 `r` 只有 `0.00015648828136792707`。检查计算部分后发现，原脚本把分母写成了 `dx * dy`；皮尔逊相关系数的分母应该是 `sqrt(dx) * sqrt(dy)`。改完后，同一份样例得到 `0.5634747254524841`。

这次还把读配置、读 CSV、计算相关系数拆成了函数。文件或列有问题时，程序会给出错误信息并退出，不再直接显示一大段 traceback。

## 怎么运行

在自己的作业仓库根目录运行：

```bash
./.venv/bin/python -m pip install -r M0/M0-2/requirements.txt
./.venv/bin/python M0/M0-2/legacy_corr.py --config M0/M0-2/config.yaml
```

如果 `python3` 已安装 PyYAML，也可以直接用考核时的命令：

```bash
python3 M0/M0-2/legacy_corr.py --config M0/M0-2/config.yaml
```

在 `M0/M0-2` 目录里可写成 `python3 legacy_corr.py --config config.yaml`。程序也接受 `python3 legacy_corr.py config.yaml` 这种位置参数写法。

## 配置和 CSV

配置文件至少要有下面三个值：

```yaml
input_csv: sample_data.csv
columns:
  x: sensor_a
  y: sensor_b
```

`input_csv` 是 CSV 路径。如果写相对路径，程序会从配置文件所在目录找。`x`、`y` 要填 CSV 表头里真实存在的列名，大小写和空格都必须一致。CSV 第一行是表头，后面至少有两行数据；选中的两列必须是有限数字，不能有空值、`NaN` 或无穷大。两列中只要有一列始终不变，`r` 就没有定义，程序会报错。CSV 中其他列不会影响计算。



## 输出怎么看

```text
n = 40
mean_x = 49.437825
mean_y = 43.310725000000005
r = 0.5634747254524841
```

`n` 是数据行数，`mean_x` 和 `mean_y` 是两列的平均值。`r` 在 `-1` 到 `1` 之间：越接近 `1`，正线性关系越明显；越接近 `-1`，负线性关系越明显；接近 `0` 表示线性关系弱。相关不等于因果。


## AI 使用说明

这次用 Codex 辅助拆分函数、修公式、补错误处理、写测试和整理 README。程序和测试已在 Ubuntu VM 上运行过；但我还没有完成自己的逐行复核，不能把 AI 跑通测试当作我已经理解了每一行。提交答辩前，我需要自己再看一遍公式、异常处理和测试，并能解释它们。


