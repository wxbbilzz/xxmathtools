#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小学数学工具 —— 主程序（界面）。

分页结构：
   计算   算式计算、分数运算、因数与倍数、乘方/开方/带余除法、百分数、价格计算
   换算   长度、面积、体积与容积、质量、时间、人民币、温度
   几何   平面图形的面积与周长、立体图形的体积与表面积
   解方程 一元方程求解

所有计算逻辑都放在 calc.py 里，本文件只负责界面和交互。
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import calc

# 小输入框的统一宽度
INPUT_WIDTH = 110
NARROW_WIDTH = 88


def make_input(placeholder='', width=INPUT_WIDTH):
    """创建输入框。"""
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    if width:
        edit.setFixedWidth(width)
    return edit


def make_result(placeholder='结果'):
    """创建只读的结果框。"""
    edit = QLineEdit()
    edit.setReadOnly(True)
    edit.setPlaceholderText(placeholder)
    return edit


def make_button(text):
    """创建按钮。"""
    return QPushButton(text)


def make_filler():
    return QLabel('')


class MathWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('小学数学工具')
        self.resize(980, 820)
        self.setMinimumSize(760, 560)

        tabs = QTabWidget()
        tabs.addTab(self._build_calc_tab(), '计算')
        tabs.addTab(self._build_convert_tab(), '换算')
        tabs.addTab(self._build_geometry_tab(), '几何')
        tabs.addTab(self._build_equation_tab(), '解方程')

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

    # ------------------------------------------------------------------ #
    # 「计算」页
    # ------------------------------------------------------------------ #
    def _build_calc_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_expression_group())
        box.addWidget(self._build_fraction_group())
        box.addWidget(self._build_factor_group())
        box.addWidget(self._build_power_group())
        box.addWidget(self._build_percent_group())
        box.addWidget(self._build_price_group())
        box.addStretch(1)

        # 收紧一点边距，让内容尽量一屏放得下
        box.setSpacing(8)
        for group in page.findChildren(QGroupBox):
            group.layout().setContentsMargins(8, 6, 8, 6)
            group.layout().setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    def _build_expression_group(self):
        group = QGroupBox('算式计算')
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel('支持 + − × ÷ 和括号，按运算顺序计算。例如：3+5×2-(4÷2)'))

        row = QHBoxLayout()
        self.expr_input = QLineEdit()
        self.expr_input.setPlaceholderText('输入算式，例如 3+5×2-(4÷2)')
        self.expr_input.returnPressed.connect(self.on_expression)
        row.addWidget(self.expr_input, 1)
        button = make_button('计算')
        button.clicked.connect(self.on_expression)
        row.addWidget(button)
        layout.addLayout(row)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel('结果'))
        self.expr_result = make_result('计算结果')
        font = self.expr_result.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        self.expr_result.setFont(font)
        result_row.addWidget(self.expr_result, 1)
        layout.addLayout(result_row)
        return group

    def _build_fraction_group(self):
        group = QGroupBox('分数运算')
        layout = QHBoxLayout(group)

        self.frac_a = make_input('3/4')
        self.frac_op = QComboBox()
        self.frac_op.addItems(calc.FRACTION_OPS)
        self.frac_op.setFixedWidth(60)
        self.frac_b = make_input('1/2')
        self.frac_result = make_result('结果')
        button = make_button('计算')
        button.clicked.connect(self.on_fraction)

        layout.addWidget(QLabel('分数'))  # 占位，保持和其它行对齐
        layout.addWidget(self.frac_a)
        layout.addWidget(self.frac_op)
        layout.addWidget(self.frac_b)
        layout.addWidget(button)
        layout.addWidget(QLabel('='))
        layout.addWidget(self.frac_result, 1)
        return group

    def _build_factor_group(self):
        group = QGroupBox('因数与倍数')
        grid = QGridLayout(group)

        grid.addWidget(QLabel('整数'), 0, 0)
        self.factor_input = make_input('例如 12')
        grid.addWidget(self.factor_input, 0, 1)
        button = make_button('分解质因数')
        button.clicked.connect(self.on_factor)
        grid.addWidget(button, 0, 2)
        grid.addWidget(QLabel('='), 0, 3)
        self.factor_result = make_result('质因数分解结果')
        grid.addWidget(self.factor_result, 0, 4)

        grid.addWidget(QLabel('整数'), 1, 0)
        self.mult_input = make_input('例如 12,18')
        grid.addWidget(self.mult_input, 1, 1)
        button = make_button('最大公因数')
        button.clicked.connect(self.on_gcd)
        grid.addWidget(button, 1, 2)
        grid.addWidget(QLabel('='), 1, 3)
        self.gcd_result = make_result('最大公因数')
        grid.addWidget(self.gcd_result, 1, 4)

        grid.addWidget(make_filler(), 2, 0)
        grid.addWidget(make_filler(), 2, 1)
        button = make_button('最小公倍数')
        button.clicked.connect(self.on_lcm)
        grid.addWidget(button, 2, 2)
        grid.addWidget(QLabel('='), 2, 3)
        self.lcm_result = make_result('最小公倍数')
        grid.addWidget(self.lcm_result, 2, 4)

        grid.setColumnStretch(4, 1)
        return group

    def _build_power_group(self):
        group = QGroupBox('乘方 / 开方 / 带余除法')
        grid = QGridLayout(group)

        # 乘方
        grid.addWidget(QLabel('乘方'), 0, 0)
        self.power_base = make_input('底数', NARROW_WIDTH)
        grid.addWidget(self.power_base, 0, 1)
        grid.addWidget(QLabel('的'), 0, 2)
        self.power_exp = make_input('指数', NARROW_WIDTH)
        grid.addWidget(self.power_exp, 0, 3)
        grid.addWidget(QLabel('次方'), 0, 4)
        button = make_button('计算')
        button.clicked.connect(self.on_power)
        grid.addWidget(button, 0, 5)
        grid.addWidget(QLabel('='), 0, 6)
        self.power_result = make_result('结果')
        grid.addWidget(self.power_result, 0, 7)

        # 开方
        grid.addWidget(QLabel('开方'), 1, 0)
        grid.addWidget(QLabel('√'), 1, 1)
        self.root_input = make_input('被开方数', NARROW_WIDTH)
        grid.addWidget(self.root_input, 1, 2)
        button = make_button('计算')
        button.clicked.connect(self.on_root)
        grid.addWidget(button, 1, 5)
        grid.addWidget(QLabel('='), 1, 6)
        self.root_result = make_result('结果')
        grid.addWidget(self.root_result, 1, 7)

        # 带余除法
        grid.addWidget(QLabel('带余除法'), 2, 0)
        self.div_a = make_input('被除数', NARROW_WIDTH)
        grid.addWidget(self.div_a, 2, 1)
        grid.addWidget(QLabel('÷'), 2, 2)
        self.div_b = make_input('除数', NARROW_WIDTH)
        grid.addWidget(self.div_b, 2, 3)
        button = make_button('计算')
        button.clicked.connect(self.on_division)
        grid.addWidget(button, 2, 5)
        grid.addWidget(QLabel('='), 2, 6)

        remainder_row = QHBoxLayout()
        remainder_row.addWidget(QLabel('商'))
        self.quot_result = make_result('商')
        self.quot_result.setFixedWidth(NARROW_WIDTH)
        remainder_row.addWidget(self.quot_result)
        remainder_row.addWidget(QLabel('余'))
        self.rem_result = make_result('余数')
        self.rem_result.setFixedWidth(NARROW_WIDTH)
        remainder_row.addWidget(self.rem_result)
        remainder_row.addStretch(1)
        grid.addLayout(remainder_row, 2, 7)

        grid.setColumnStretch(7, 1)
        return group

    def _build_percent_group(self):
        group = QGroupBox('百分数')
        grid = QGridLayout(group)

        self.pct_a = make_input('例如 200')
        grid.addWidget(self.pct_a, 0, 0)
        grid.addWidget(QLabel('的'), 0, 1)
        self.pct_b = make_input('例如 15', NARROW_WIDTH)
        grid.addWidget(self.pct_b, 0, 2)
        grid.addWidget(QLabel('% 是多少'), 0, 3)
        button = make_button('计算')
        button.clicked.connect(self.on_percent)
        grid.addWidget(button, 0, 4)
        grid.addWidget(QLabel('='), 0, 5)
        self.pct_result = make_result('结果')
        grid.addWidget(self.pct_result, 0, 6)

        self.ratio_a = make_input('例如 30')
        grid.addWidget(self.ratio_a, 1, 0)
        grid.addWidget(QLabel('是'), 1, 1)
        self.ratio_b = make_input('例如 200')
        grid.addWidget(self.ratio_b, 1, 2)
        grid.addWidget(QLabel('的百分之几'), 1, 3)
        button = make_button('计算')
        button.clicked.connect(self.on_ratio)
        grid.addWidget(button, 1, 4)
        grid.addWidget(QLabel('='), 1, 5)
        self.ratio_result = make_result('百分比')
        grid.addWidget(self.ratio_result, 1, 6)

        grid.setColumnStretch(6, 1)
        return group

    def _build_price_group(self):
        group = QGroupBox('价格计算')
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel('单价'))
        self.price_input = make_input('单价', NARROW_WIDTH)
        layout.addWidget(self.price_input)
        layout.addWidget(QLabel('元/千克 × 重量'))
        self.weight_input = make_input('重量', NARROW_WIDTH)
        layout.addWidget(self.weight_input)
        layout.addWidget(QLabel('千克'))
        button = make_button('计算总价')
        button.clicked.connect(self.on_price)
        layout.addWidget(button)
        layout.addWidget(QLabel('='))
        self.total_result = make_result('总价')
        layout.addWidget(self.total_result, 1)
        layout.addWidget(QLabel('元'))
        return group

    # ------------------------------------------------------------------ #
    # 「换算」页
    # ------------------------------------------------------------------ #
    def _build_convert_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        grid = QGridLayout()
        grid.addWidget(QLabel('类别'), 0, 0)
        self.unit_category = QComboBox()
        self.unit_category.addItems(calc.unit_categories())
        self.unit_category.currentTextChanged.connect(self._on_category_changed)
        grid.addWidget(self.unit_category, 0, 1)

        grid.addWidget(QLabel('数值'), 1, 0)
        self.unit_value = QLineEdit()
        self.unit_value.setPlaceholderText('请输入数值，例如 1')
        self.unit_value.returnPressed.connect(self.on_convert)
        grid.addWidget(self.unit_value, 1, 1)

        grid.addWidget(QLabel('从'), 2, 0)
        self.unit_from = QComboBox()
        grid.addWidget(self.unit_from, 2, 1)

        grid.addWidget(QLabel('到'), 3, 0)
        self.unit_to = QComboBox()
        grid.addWidget(self.unit_to, 3, 1)

        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        button = make_button('换算')
        button.clicked.connect(self.on_convert)
        layout.addWidget(button)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel('结果'))
        self.unit_result = make_result('换算结果')
        font = self.unit_result.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        self.unit_result.setFont(font)
        result_row.addWidget(self.unit_result, 1)
        layout.addLayout(result_row)

        layout.addStretch(1)
        self._on_category_changed(self.unit_category.currentText())
        return page

    # ------------------------------------------------------------------ #
    # 「几何」页
    # ------------------------------------------------------------------ #
    def _build_geometry_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        row = QHBoxLayout()
        row.addWidget(QLabel('图形'))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(calc.geometry_shape_names())
        self.shape_combo.currentTextChanged.connect(self._on_shape_changed)
        row.addWidget(self.shape_combo, 1)
        layout.addLayout(row)

        self.param_box = QGroupBox('参数')
        self.param_grid = QGridLayout(self.param_box)
        layout.addWidget(self.param_box)

        # 参数行预先建好，切换图形时只显示/隐藏，
        # 避免 deleteLater() 延迟销毁导致新旧控件叠在一起
        self.param_rows = []
        max_params = max(len(shape['params']) for shape in calc.GEOMETRY_SHAPES)
        for row in range(max_params):
            label = QLabel()
            edit = make_input()
            self.param_grid.addWidget(label, row, 0)
            self.param_grid.addWidget(edit, row, 1)
            self.param_rows.append((label, edit))
        self.param_grid.setColumnStretch(1, 1)

        button = make_button('计算')
        button.clicked.connect(self.on_geometry)
        layout.addWidget(button)

        layout.addWidget(QLabel('结果'))
        self.geometry_result = QTextEdit()
        self.geometry_result.setReadOnly(True)
        layout.addWidget(self.geometry_result, 1)

        self.param_inputs = {}
        self._on_shape_changed(self.shape_combo.currentText())
        return page

    # ------------------------------------------------------------------ #
    # 「解方程」页
    # ------------------------------------------------------------------ #
    def _build_equation_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel(
            '请输入一元方程（含未知数 x）。\n'
            '支持省略乘号、中文全角符号、^ 表示乘方。例如：2x + 3 = 7、x^2 - 4 = 0'))

        row = QHBoxLayout()
        row.addWidget(QLabel('方程'))
        self.eq_input = QLineEdit()
        self.eq_input.setPlaceholderText('例如 2x + 3 = 7')
        self.eq_input.returnPressed.connect(self.on_solve)
        row.addWidget(self.eq_input, 1)
        layout.addLayout(row)

        button = make_button('解方程')
        button.clicked.connect(self.on_solve)
        layout.addWidget(button)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel('解'))
        self.eq_result = make_result('方程的解')
        font = self.eq_result.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        self.eq_result.setFont(font)
        result_row.addWidget(self.eq_result, 1)
        layout.addLayout(result_row)

        layout.addStretch(1)
        return page

    # ------------------------------------------------------------------ #
    # 事件处理
    # ------------------------------------------------------------------ #
    def on_expression(self):
        text = self.expr_input.text()
        try:
            value = calc.evaluate_expression(text)
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.expr_result.setText(calc.format_expression_result(value, text))

    def on_fraction(self):
        try:
            value = calc.fraction_operate(
                self.frac_a.text(), self.frac_op.currentText(), self.frac_b.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.frac_result.setText(calc.format_result(value))

    def on_factor(self):
        try:
            text = calc.prime_factorization(self.factor_input.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.factor_result.setText(text)

    def on_gcd(self):
        try:
            value = calc.greatest_common_divisor(self.mult_input.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.gcd_result.setText(str(value))

    def on_lcm(self):
        try:
            value = calc.least_common_multiple(self.mult_input.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.lcm_result.setText(str(value))

    def on_power(self):
        try:
            value = calc.power(self.power_base.text(), self.power_exp.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.power_result.setText(calc.format_result(value))

    def on_root(self):
        try:
            value = calc.square_root(self.root_input.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.root_result.setText(calc.format_result(value))

    def on_division(self):
        try:
            quotient, remainder = calc.division_with_remainder(
                self.div_a.text(), self.div_b.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.quot_result.setText(str(quotient))
        self.rem_result.setText(str(remainder))

    def on_percent(self):
        try:
            value = calc.percent_of(self.pct_a.text(), self.pct_b.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.pct_result.setText(calc.format_decimal(float(value)))

    def on_ratio(self):
        try:
            value = calc.percent_ratio(self.ratio_a.text(), self.ratio_b.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.ratio_result.setText('%s%%' % calc.format_decimal(float(value)))

    def on_price(self):
        try:
            price = calc.parse_number(self.price_input.text(), '单价')
            weight = calc.parse_number(self.weight_input.text(), '重量')
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.total_result.setText('%.2f' % float(price * weight))

    def on_convert(self):
        try:
            value = calc.convert_unit(
                self.unit_category.currentText(),
                self.unit_value.text(),
                self.unit_from.currentText(),
                self.unit_to.currentText())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.unit_result.setText(calc.format_decimal(value))

    def on_geometry(self):
        raw = {key: edit.text() for key, edit in self.param_inputs.items()}
        try:
            results = calc.geometry_calculate(self.shape_combo.currentText(), raw)
        except calc.CalcError as exc:
            self._warn(exc)
            return
        lines = ['%s = %s' % (label, calc.format_geometry(value))
                 for label, value in results]
        self.geometry_result.setPlainText('\n'.join(lines))

    def on_solve(self):
        try:
            answer = calc.solve_equation(self.eq_input.text())
        except calc.CalcError as exc:
            self._warn(exc)
            return
        self.eq_result.setText(answer)

    # -- 界面联动 ---------------------------------------------------------- #
    def _on_category_changed(self, category):
        units = calc.units_of(category)
        for combo in (self.unit_from, self.unit_to):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(units)
            combo.blockSignals(False)
        if len(units) > 1:
            self.unit_to.setCurrentIndex(1)

    def _on_shape_changed(self, shape_name):
        params = calc.geometry_params(shape_name)
        self.param_inputs = {}
        for index, (label, edit) in enumerate(self.param_rows):
            if index < len(params):
                key, text = params[index]
                label.setText(text)
                label.show()
                edit.clear()
                edit.setPlaceholderText('请输入%s' % text)
                edit.show()
                self.param_inputs[key] = edit
            else:
                label.hide()
                edit.hide()
        self.geometry_result.clear()

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
        # 屏幕不够大时自动缩小，避免窗口超出屏幕
        window.resize(min(window.width(), geometry.width() - 60),
                      min(window.height(), geometry.height() - 60))
        window.move(geometry.center() - window.rect().center())
    window.show()

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
