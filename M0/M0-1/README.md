## M0-1 环境搭建与踩坑记录

我在 VMware 中搭建了 Ubuntu 22.04、ROS2 Humble 和 Python 开发环境。最初从桌面运行检查脚本，因当前目录不是 Git 仓库而失败；进入自己的 `smartcar-assessment` 仓库后解决。使用 uv 激活虚拟环境时又遇到 `pip 不可用`，在该环境中运行 `uv pip install pip` 后解决。SSH 公钥已生成，实际登录开发板仍待完成。排查过程和本文整理使用了 ChatGPT 辅助，检查结果均以本人终端输出为准。
