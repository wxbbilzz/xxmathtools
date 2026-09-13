#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小学数学工具。

功能：
    - 四则运算：加、减、乘、除
    - 价格计算：单价 × 重量 = 总价
    - 温度转换：华氏度 ↔ 摄氏度
    - 一元方程求解：基于 sympy

界面用 Qt Designer 在 Widget.ui 中设计，再由 pyuic5 生成为 UI_Widget.py；
本文件只负责业务逻辑，所有输入都做了校验，不会因为非法输入而崩溃。

修改界面后需要重新生成界面代码：
    pyuic5 Widget.ui -o UI_Widget.py
"""

import sys

from sympy import simplify, solve
from sympy.abc import x
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

from UI_Widget import Ui_Widget


# --------------------------------------------------------------------------- #
# 通用工具
# --------------------------------------------------------------------------- #
class InputError(Exception):
    """用户输入不合法。"""


def parse_number(text, name):
    """把输入框文本转成浮点数，非法时抛出 ``InputError``。"""
    text = text.strip()
    if not text:
        raise InputError('请填写“%s”。' % name)
    try:
        value = float(text)
    except ValueError:
        raise InputError('“%s”不是有效的数字，请重新填写“%s”。' % (text, name))
    if value != value or value in (float('inf'), float('-inf')):
        raise InputError('“%s”不是有效的数字，请重新填写“%s”。' % (text, name))
    return value


def format_number(value, ndigits=6):
    """把计算结果格式化成简洁的字符串，去掉多余的小数位。

    例如：0.1 + 0.2 会得到 ``0.3`` 而不是 ``0.30000000000000004``。
    """
    if isinstance(value, float):
        if value != value or value in (float('inf'), float('-inf')):
            return str(value)
        rounded = round(value, ndigits)
        if abs(rounded) < 1e15 and rounded == int(rounded):
            return str(int(rounded))
        return ('%.*f' % (ndigits, rounded)).rstrip('0').rstrip('.')
    return str(value)


# --------------------------------------------------------------------------- #
# 方程求解
# --------------------------------------------------------------------------- #
# 全角字符 → 半角字符，方便小学生用中文输入法直接输公式
_TRANSLATE_TABLE = {chr(0xFF10 + i): str(i) for i in range(10)}
_TRANSLATE_TABLE.update({
    '（': '(', '）': ')', '＝': '=', '＋': '+', '－': '-', '−': '-',
    '—': '-', '×': '*', '÷': '/', '＾': '^', '．': '.', '，': ',',
    '　': ' ', 'ｘ': 'x', 'Ｘ': 'x', 'Ｘ': 'x',
})
_TRANSLATE = str.maketrans(_TRANSLATE_TABLE)

# 允许省略乘号：2x 会被识别成 2*x
_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


def normalize_equation(text):
    """把用户输入的方程整理成 sympy 能识别的形式。"""
    text = text.translate(_TRANSLATE)
    text = text.replace('^', '**')
    return text.strip()


def format_solution(value):
    """把 sympy 的解格式化成小学生看得懂的样子。"""
    if getattr(value, 'is_Integer', False):
        return str(int(value))
    if getattr(value, 'is_Rational', False):
        numerator, denominator = int(value.p), int(value.q)
        reduced = denominator
        for prime in (2, 5):
            while reduced % prime == 0:
                reduced //= prime
        # 能化成有限小数的就显示小数，否则显示分数
        if reduced == 1:
            return format_number(float(value))
        return '%d/%d' % (numerator, denominator)
    try:
        return format_number(float(value))
    except (TypeError, ValueError):
        return str(value)


def solve_equation(text):
    """求解一元方程，返回可直接显示的字符串。"""
    expression = normalize_equation(text)
    if not expression:
        raise InputError('请先输入要解的方程。')

    try:
        if '=' in expression:
            left, right = expression.split('=', 1)
            lhs = parse_expr(left, local_dict={'x': x}, transformations=_TRANSFORMS)
            rhs = parse_expr(right, local_dict={'x': x}, transformations=_TRANSFORMS)
        else:
            # 没有等号时按“右边为 0”处理
            lhs = parse_expr(expression, local_dict={'x': x}, transformations=_TRANSFORMS)
            rhs = 0
    except Exception:
        raise InputError('看不懂这个方程：“%s”，请检查括号和运算符。' % text.strip())

    symbols = set(getattr(lhs, 'free_symbols', set())) | set(getattr(rhs, 'free_symbols', set()))
    if x not in symbols:
        raise InputError('方程里没有找到未知数 x，请检查输入。')

    # 一律移到一边：左边 - 右边 = 0，注意不能用 Eq(...)，
    # 否则 sympy 会把 x+1 = x+2 直接化归成 False，丢掉未知数信息。
    difference = lhs - rhs
    try:
        difference = simplify(difference)
    except Exception:
        pass

    if difference == 0:
        return '任意实数都是解'
    if not difference.free_symbols:
        return '无解'

    try:
        solutions = solve(difference, x)
    except Exception:
        raise InputError('这个方程比较复杂，暂时解不出来。')

    if not solutions:
        return '无解'

    return '，'.join('x = %s' % format_solution(item) for item in solutions)


# --------------------------------------------------------------------------- #
# 主窗口
# --------------------------------------------------------------------------- #
class MathWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self._connect_signals()

    # -- 信号绑定 ---------------------------------------------------------- #
    def _connect_signals(self):
        ui = self.ui
        ui.btn_add.clicked.connect(self.on_add)
        ui.btn_sub.clicked.connect(self.on_sub)
        ui.btn_mul.clicked.connect(self.on_mul)
        ui.btn_div.clicked.connect(self.on_div)
        ui.btn_price.clicked.connect(self.on_price)
        ui.btn_f2c.clicked.connect(self.on_f2c)
        ui.btn_c2f.clicked.connect(self.on_c2f)
        ui.btn_solve.clicked.connect(self.on_solve)

        # 在输入框里按回车也能直接计算
        for fields, handler in (
            ((ui.add1, ui.add2), self.on_add),
            ((ui.sub1, ui.sub2), self.on_sub),
            ((ui.mul1, ui.mul2), self.on_mul),
            ((ui.div1, ui.div2), self.on_div),
        ):
            for field in fields:
                field.returnPressed.connect(handler)
        ui.eq_input.returnPressed.connect(self.on_solve)

    # -- 四则运算 ---------------------------------------------------------- #
    def on_add(self):
        try:
            first = parse_number(self.ui.add1.text(), '第一个数')
            second = parse_number(self.ui.add2.text(), '第二个数')
        except InputError as exc:
            self._warn(exc)
            return
        self.ui.add_result.setText(format_number(first + second))

    def on_sub(self):
        try:
            first = parse_number(self.ui.sub1.text(), '第一个数')
            second = parse_number(self.ui.sub2.text(), '第二个数')
        except InputError as exc:
            self._warn(exc)
            return
        self.ui.sub_result.setText(format_number(first - second))

    def on_mul(self):
        try:
            first = parse_number(self.ui.mul1.text(), '第一个数')
            second = parse_number(self.ui.mul2.text(), '第二个数')
        except InputError as exc:
            self._warn(exc)
            return
        self.ui.mul_result.setText(format_number(first * second))

    def on_div(self):
        try:
            first = parse_number(self.ui.div1.text(), '被除数')
            second = parse_number(self.ui.div2.text(), '除数')
            if second == 0:
                raise InputError('除数不能为 0，请重新填写除数。')
        except InputError as exc:
            self._warn(exc)
            return
        self.ui.div_result.setText(format_number(first / second))

    # -- 价格计算 ---------------------------------------------------------- #
    def on_price(self):
        total = self.ui.price_spin.value() * self.ui.weight_spin.value()
        self.ui.total_spin.setValue(round(total, 2))

    # -- 温度转换 ---------------------------------------------------------- #
    def on_f2c(self):
        fahrenheit = self.ui.f_spin.value()
        self.ui.c_result.setValue((fahrenheit - 32) * 5 / 9)

    def on_c2f(self):
        celsius = self.ui.c_spin.value()
        self.ui.f_result.setValue(celsius * 9 / 5 + 32)

    # -- 解方程 ------------------------------------------------------------ #
    def on_solve(self):
        try:
            answer = solve_equation(self.ui.eq_input.text())
        except InputError as exc:
            self._warn(exc)
            return
        self.ui.eq_result.setText(answer)

    # -- 提示 -------------------------------------------------------------- #
    def _warn(self, message):
        QMessageBox.warning(self, '输入有误', str(message))


def main():
    # 高分屏下界面不糊（必须在创建 QApplication 之前设置）
    for attribute in ('AA_EnableHighDpiScaling', 'AA_UseHighDpiPixmaps'):
        if hasattr(Qt, attribute):
            QApplication.setAttribute(getattr(Qt, attribute), True)

    app = QApplication(sys.argv)
    app.setApplicationName('小学数学工具')

    window = MathWidget()
    screen = app.primaryScreen()
    if screen is not None:
        geometry = screen.availableGeometry()
        window.move(geometry.center() - window.rect().center())
    window.show()

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
