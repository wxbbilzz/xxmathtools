# xxmathtools

一个用 PyQt5 写的小学数学小工具。

## 功能

| 模块 | 说明 |
| --- | --- |
| 四则运算 | 加、减、乘、除，支持小数；在输入框里按回车可直接计算 |
| 价格计算 | 单价 × 重量 = 总价 |
| 温度转换 | 华氏度 ↔ 摄氏度 |
| 解方程 | 一元方程求解，支持 `2x + 3 = 7`、`x^2 - 4 = 0` 等写法 |

## 运行

需要 Python 3，以及 PyQt5、sympy 两个库。

系统包方式（Debian / Deepin / UOS）：

```bash
sudo apt install python3-pyqt5 python3-sympy
cd xxmathrools
python3 小学数学工具.py
```

虚拟环境方式：

```bash
python3 -m venv venv
source venv/bin/activate
pip install PyQt5 sympy -i https://pypi.tuna.tsinghua.edu.cn/simple
cd xxmathrools
python 小学数学工具.py
```

> 注意：必须在 `xxmathrools` 目录下运行。程序要从同目录导入 `UI_Widget`，换到别的目录会报 `ModuleNotFoundError`。

启动时如果出现 `Could not find the Qt platform plugin "dxcb"`，这是 Deepin / UOS 上的常见提示，会自动回退，不影响使用。

## 打包成可执行文件

```bash
pip install pyinstaller
pyinstaller -w -n 小学数学工具 小学数学工具.py
```

打包结果在 `dist/` 目录下。

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `小学数学工具.py` | 程序逻辑：界面事件绑定、计算、输入校验 |
| `Widget.ui` | Qt Designer 界面文件（用布局排版，可自由缩放） |
| `UI_Widget.py` | 由 `Widget.ui` 自动生成，**不要手动修改** |
| `Widget.cpp` / `Widget.h` / `main.cpp` / `jisuanqi.pro` | 早期 Qt C++ 空壳，没有实现任何功能，可以忽略 |

修改界面后需要重新生成界面代码：

```bash
pyuic5 Widget.ui -o UI_Widget.py
```

## 输入说明

- **四则运算**：输入框留空或填了非数字，会弹出提示而不是崩溃；除数为 0 会给出提示。
- **解方程**：支持省略乘号（`2x`）、中文全角符号（`（x＋1）×2＝8`）、用 `^` 表示乘方；
  没有等号时按“右边为 0”处理；无解显示「无解」，恒等式显示「任意实数都是解」。

## 许可证

MIT License，详见 [LICENSE](LICENSE)。
