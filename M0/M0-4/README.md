# M0-4 任务调度器

这题我把“先做什么、失败了怎么办、时间不够怎么办”放进了一个命令行程序。它读取 YAML 或 JSON 任务表，检查依赖关系，按顺序模拟执行，最后写出报告。没有用到 ROS。

## 文件和环境

- `scheduler.py`：程序本体。
- `tasks_demo.yaml`、`tasks_demo.json`：同一组 7 个示例任务，分别用两种格式写成。
- `requirements.txt`：运行所需的 PyYAML。
- `report.json`：在虚拟环境中运行示例后得到的一次报告。
- `tests/test_scheduler.py`：调度和错误输入的测试。

在自己的仓库中操作：

```bash
cd ~/smartcar-assessment/M0/M0-4
../../.venv/bin/python -m pip install -r requirements.txt
```

这里的 `../../.venv/bin/python` 指向 `~/smartcar-assessment/.venv`，是 M0-1 用的虚拟环境。安装前可先用 `../../.venv/bin/python -c "import yaml; print(yaml.__version__)"` 检查：如果已经有 PyYAML，就不用重复安装。不要在学长的 `~/22SmartCar` 仓库里提交作业。

## 配置怎么写

一个任务有 `name`（唯一名字）、`duration`（每次尝试模拟花的秒数）、`success_rate`（0 到 1 的成功概率）和 `dependencies`（必须先成功的任务名列表）。最外层的 `timeout` 可选，单位是秒。例如：

```yaml
timeout: 15
tasks:
  - name: Init
    duration: 0.5
    success_rate: 1.0
    dependencies: []
  - name: Navigate
    duration: 2.5
    success_rate: 0.8
    dependencies: [Init]
```

程序会检查空任务表、重名、缺少依赖、依赖成环、错误的数值和配置语法。报错时会显示原因并以非零状态退出，不打印 Python 栈回溯。

## 运行示例

下面的命令都先执行 `cd ~/smartcar-assessment/M0/M0-4`。`--seed 42` 固定随机数，便于再次得到相同的成功和失败结果；实际耗时仍会有一点波动。

**例 1：用 YAML 跑完整示例，并生成交付用报告。**

```bash
../../.venv/bin/python scheduler.py --config tasks_demo.yaml --timeout 15 --report report.json --seed 42
```

我在 VM 上运行时，7 个任务全部成功，总耗时约 11.02 秒。`report.json` 就是这次运行保存的。

**例 2：改用等价的 JSON 配置，另存一份报告。**

```bash
../../.venv/bin/python scheduler.py --config tasks_demo.json --report /tmp/m0-4-json-report.json --seed 42
```

不写 `--timeout` 时，使用配置文件里的 `timeout: 15`。`/tmp` 是练习用位置，不会覆盖作业里的示例报告。

**例 3：把总时间改成 1 秒，观察真正的中断。**

```bash
../../.venv/bin/python scheduler.py --config tasks_demo.json --timeout 1 --report /tmp/m0-4-timeout.yaml --seed 42
```

我实际运行时，`Init` 成功，`Navigate` 做到一半变成 `TIMEOUT`，其余任务也记为 `TIMEOUT`；总耗时约 1 秒。超时是预期结果，程序退出码为 2。报告文件名以 `.yaml` 结尾，所以这里写出 YAML。

**例 4：运行测试。**

```bash
../../.venv/bin/python -m unittest discover -s tests -v
```

在 VM 上运行通过了 10 个测试。

参数表：

| 参数 | 用途 |
| --- | --- |
| `--config 路径` | 必填，读取 `.yaml`、`.yml` 或 `.json` 任务表。 |
| `--timeout 秒数` | 可选，覆盖配置文件的总时限。 |
| `--report 路径` | 可选，默认写 `report.json`；`.yaml` 或 `.yml` 后缀写 YAML，其余写 JSON。 |
| `--seed 整数` | 可选，固定随机结果，方便调试。 |

## 我是怎么处理依赖的

先数每个任务有几个前置任务（入度）。入度为 0 的任务先入队；完成一个任务的排序后，把依赖它的任务入度减 1。只有入度变成 0 才入队。示例中 `Navigate` 后面分成 `DetectQR` 和 `AvoidObstacle` 两路，`Place` 要等 `Grasp` 和 `AvoidObstacle` 都完成。这就是拓扑排序，出现环时无法排完全部任务，程序会报错。

执行时每个任务最多尝试 3 次，也就是首次加 2 次重试。三次都不成功记为 `FAILED`；依赖失败任务的下游记为 `SKIPPED`，和它无关的任务继续执行。总时限用单调时钟计算；每次开始前检查剩余时间，模拟耗时也最多只睡到时限。到时以后，尚未开始的任务也记为 `TIMEOUT`。

终端里 `SUCCESS` 是绿色、`FAILED` 和 `TIMEOUT` 是红色、`RETRY` 是黄色、`SKIPPED` 是蓝色。重定向到文件时不会写入颜色控制字符。报告包括 `timeout`、`total_duration`，以及每个任务的 `name`、`status`、`attempts`、`duration`、`started_at`、`ended_at`。没开始的任务时间字段是 `null`。

## AI 使用记录

我用 Codex 帮忙写了调度器、测试、文档，并让它连接我的 Ubuntu VM 运行和提交。我需要自己看懂拓扑排序、失败传播和超时处理；这份提交不应说成全是我独立手写的。题目和示例配置来自学长的 [22SmartCar M0-4](https://github.com/Blake-John/22SmartCar/tree/main/round1/M0/M0-4)；上游许可见 `../M0-2/LICENSE.upstream`。
