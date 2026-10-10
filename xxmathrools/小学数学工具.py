#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小学数学工具 —— 主程序（界面）。

分页结构：
    计算    算式计算、分步计算与简便算法、竖式演示、乘方/开方/带余除法
    分数    分数运算、约分与通分、分数小数百分数互化
    数      因数与倍数、质数奇偶与因数、数的认识（近似数与改写）
    比与统计 解比例、按比分配、平均数
    换算    单位换算、复名数互化、时刻与日期
    几何    平面与立体图形、三角形判定
    解方程  一元方程求解与分步求解

窗口顶部是「计算设置」（圆周率取值、保留小数、取整方式、带分数、单位），
底部是「历史记录」。所有计算逻辑都放在 calc.py 里，本文件只负责界面和交互。
"""

import re
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
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

# 竖式要按等宽字体对齐，这里挑一个系统里能找到的
MONOSPACE_FAMILIES = [
    'DejaVu Sans Mono', 'Liberation Mono', 'Noto Sans Mono', 'Noto Sans Mono CJK SC',
    'Ubuntu Mono', 'WenQuanYi Micro Hei Mono', 'Courier New', 'Monospace',
]

# 历史记录最多保留多少条
HISTORY_LIMIT = 200


def make_input(placeholder='', width=INPUT_WIDTH):
    """创建输入框。"""
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    if width:
        edit.setFixedWidth(width)
    return edit


def make_result(placeholder='结果'):
    """创建只读的单行结果框。"""
    edit = QLineEdit()
    edit.setReadOnly(True)
    edit.setPlaceholderText(placeholder)
    return edit


def make_text_result(placeholder='', height=140, monospace=False):
    """创建只读的多行结果框。"""
    edit = QTextEdit()
    edit.setReadOnly(True)
    edit.setPlaceholderText(placeholder)
    edit.setMinimumHeight(height)
    if monospace:
        edit.setFont(make_monospace_font())
    return edit


def make_monospace_font():
    """找一个可用的等宽字体，找不到就用系统默认的等宽字体。"""
    families = set(QFontDatabase().families())
    for name in MONOSPACE_FAMILIES:
        if name in families:
            font = QFont(name)
            font.setStyleHint(QFont.TypeWriter)
            return font
    font = QFont()
    font.setStyleHint(QFont.TypeWriter)
    font.setFixedPitch(True)
    return font


def make_button(text):
    """创建按钮。"""
    return QPushButton(text)


def make_filler():
    return QLabel('')


def add_cells(grid, row, cells):
    """把一行控件放进网格：字符串变成标签，None 变成空标签，布局直接塞进去。"""
    for column, cell in enumerate(cells):
        if isinstance(cell, str):
            grid.addWidget(QLabel(cell), row, column)
        elif cell is None:
            grid.addWidget(make_filler(), row, column)
        elif isinstance(cell, QLayout):
            grid.addLayout(cell, row, column)
        else:
            grid.addWidget(cell, row, column)


class MathWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('小学数学工具')
        self.resize(1000, 900)
        self.setMinimumSize(780, 600)

        self._history = []

        tabs = QTabWidget()
        tabs.addTab(self._build_calculator_tab(), '计算器')
        tabs.addTab(self._build_calc_tab(), '计算')
        tabs.addTab(self._build_fraction_tab(), '分数')
        tabs.addTab(self._build_number_tab(), '数')
        tabs.addTab(self._build_ratio_tab(), '比与统计')
        tabs.addTab(self._build_convert_tab(), '换算')
        tabs.addTab(self._build_geometry_tab(), '几何')
        tabs.addTab(self._build_equation_tab(), '解方程')
        tabs.addTab(self._build_tools_tab(), '更多工具')

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_settings_group())
        layout.addWidget(tabs, 1)
        layout.addWidget(self._build_history_group())

    # ------------------------------------------------------------------ #
    # 计算设置 / 历史记录
    # ------------------------------------------------------------------ #
    def _build_settings_group(self):
        group = QGroupBox('计算设置')
        row = QHBoxLayout(group)

        row.addWidget(QLabel('圆周率'))
        self.pi_combo = QComboBox()
        self.pi_combo.addItems(calc.PI_MODES)
        row.addWidget(self.pi_combo)

        row.addWidget(QLabel('保留小数'))
        self.decimals_combo = QComboBox()
        for digits in calc.DECIMAL_CHOICES:
            self.decimals_combo.addItem('%d 位' % digits, digits)
        row.addWidget(self.decimals_combo)

        row.addWidget(QLabel('取整方式'))
        self.round_combo = QComboBox()
        self.round_combo.addItems(calc.ROUND_MODES)
        row.addWidget(self.round_combo)

        self.mixed_check = QCheckBox('假分数显示成带分数')
        row.addWidget(self.mixed_check)
        self.unit_check = QCheckBox('几何结果显示单位')
        row.addWidget(self.unit_check)

        row.addStretch(1)

        # 用当前设置初始化控件
        self.pi_combo.setCurrentText(calc.SETTINGS['pi_mode'])
        index = self.decimals_combo.findData(calc.SETTINGS['decimals'])
        self.decimals_combo.setCurrentIndex(max(index, 0))
        self.round_combo.setCurrentText(calc.SETTINGS['round_mode'])
        self.mixed_check.setChecked(calc.SETTINGS['mixed_number'])
        self.unit_check.setChecked(calc.SETTINGS['show_unit'])

        for widget in (self.pi_combo, self.decimals_combo, self.round_combo):
            widget.currentIndexChanged.connect(self.on_settings_changed)
        self.mixed_check.toggled.connect(self.on_settings_changed)
        self.unit_check.toggled.connect(self.on_settings_changed)
        return group

    def _build_history_group(self):
        group = QGroupBox('历史记录')
        row = QHBoxLayout(group)
        self.history_view = make_text_result('算过的题目会记在这里', height=90)
        self.history_view.setMaximumHeight(110)
        row.addWidget(self.history_view, 1)
        button = make_button('清空记录')
        button.clicked.connect(self.on_clear_history)
        row.addWidget(button)
        return group

    def on_settings_changed(self, *_args):
        calc.SETTINGS['pi_mode'] = self.pi_combo.currentText()
        calc.SETTINGS['decimals'] = self.decimals_combo.currentData()
        calc.SETTINGS['round_mode'] = self.round_combo.currentText()
        calc.SETTINGS['mixed_number'] = self.mixed_check.isChecked()
        calc.SETTINGS['show_unit'] = self.unit_check.isChecked()
        # 几何结果受设置影响最明显，改设置后立刻按新设置重算
        if self.geometry_result.toPlainText().strip():
            self._run_geometry(log=False)

    def on_clear_history(self):
        self._history = []
        self.history_view.clear()

    def _log(self, text):
        """记一条历史记录。"""
        self._history.append(text)
        del self._history[:-HISTORY_LIMIT]
        self.history_view.setPlainText('\n'.join(self._history))
        scroll = self.history_view.verticalScrollBar()
        scroll.setValue(scroll.maximum())

    # ------------------------------------------------------------------ #
    # 「计算器」页
    # ------------------------------------------------------------------ #
    def _build_calculator_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel('模式'))
        self.calc_mode = QComboBox()
        self.calc_mode.addItems(['标准', '科学'])
        self.calc_mode.currentTextChanged.connect(self._on_calc_mode_changed)
        mode_row.addWidget(self.calc_mode)
        mode_row.addWidget(QLabel('角度'))
        self.calc_angle = QComboBox()
        self.calc_angle.addItems(calc.ANGLE_MODES)
        mode_row.addWidget(self.calc_angle)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        # 显示屏：深色底、右对齐，上方表达式小字、下方结果大字
        display = QFrame()
        display.setStyleSheet(
            'QFrame { background: #1e1e1e; border: 1px solid #3a3a3a; border-radius: 8px; }')
        display_layout = QVBoxLayout(display)
        display_layout.setContentsMargins(12, 6, 12, 8)
        display_layout.setSpacing(2)

        self.calc_expr = QLineEdit()
        self.calc_expr.setPlaceholderText('输入或点击按钮，例如 sin(30)+cos(60)')
        self.calc_expr.returnPressed.connect(self._calc_evaluate)
        self.calc_expr.setAlignment(Qt.AlignRight)
        self.calc_expr.setStyleSheet(
            'QLineEdit { background: transparent; border: none; color: #b8b8b8; font-size: 14px; }')
        display_layout.addWidget(self.calc_expr)

        self.calc_result = make_result('')
        self.calc_result.setText('0')
        self.calc_result.setAlignment(Qt.AlignRight)
        self.calc_result.setStyleSheet(
            'QLineEdit { background: transparent; border: none; color: #ffffff; font-size: 28px; font-weight: bold; }')
        display_layout.addWidget(self.calc_result)
        layout.addWidget(display)

        # 科学按钮区
        self.sci_panel = QWidget()
        sci_grid = QGridLayout(self.sci_panel)
        sci_grid.setSpacing(6)
        sci_buttons = [
            ('sin', 'sin('), ('cos', 'cos('), ('tan', 'tan('), ('√', 'sqrt('),
            ('sin⁻¹', 'asin('), ('cos⁻¹', 'acos('), ('tan⁻¹', 'atan('), ('³√', 'cbrt('),
            ('ln', 'ln('), ('log', 'log('), ('1/x', '1/('), ('x!', 'factorial('),
            ('π', 'pi'), ('e', 'e'), ('x^y', '^('), ('x²', '^2'),
            ('10^x', '10^('), ('^', '^'), ('(', '('), (')', ')'),
        ]
        for index, (label, token) in enumerate(sci_buttons):
            sci_grid.addWidget(self._calc_button(label, token), index // 4, index % 4)
        for col in range(4):
            sci_grid.setColumnStretch(col, 1)
        layout.addWidget(self.sci_panel)

        # 标准按钮区
        std_grid = QGridLayout()
        std_grid.setSpacing(6)
        std_buttons = [
            (0, 0, 'C', 'clear'), (0, 1, '⌫', 'back'), (0, 2, '%', '%'), (0, 3, '÷', '/'),
            (1, 0, '7', '7'), (1, 1, '8', '8'), (1, 2, '9', '9'), (1, 3, '×', '*'),
            (2, 0, '4', '4'), (2, 1, '5', '5'), (2, 2, '6', '6'), (2, 3, '−', '-'),
            (3, 0, '1', '1'), (3, 1, '2', '2'), (3, 2, '3', '3'), (3, 3, '+', '+'),
            (4, 0, '±', 'sign'), (4, 1, '0', '0'), (4, 2, '.', '.'), (4, 3, '=', 'equals'),
        ]
        for row, col, label, action in std_buttons:
            std_grid.addWidget(self._calc_button(label, action), row, col)
        for col in range(4):
            std_grid.setColumnStretch(col, 1)
        layout.addLayout(std_grid)

        layout.addStretch(1)
        self._on_calc_mode_changed(self.calc_mode.currentText())
        return self._finish_page(page)

    def _calc_button(self, label, action):
        button = QPushButton(label)
        button.setMinimumHeight(46)
        font = button.font()
        font.setPointSize(font.pointSize() + 2)
        button.setFont(font)
        if label in ('÷', '×', '−', '+', '='):
            style = ('QPushButton { background: #ff9500; color: white; border: none; '
                     'border-radius: 6px; }\n'
                     'QPushButton:hover { background: #ffa826; }\n'
                     'QPushButton:pressed { background: #d97f00; }')
        elif label.isdigit() or label == '.':
            style = ('QPushButton { background: #f7f7f7; border: 1px solid #d0d0d0; '
                     'border-radius: 6px; }\n'
                     'QPushButton:hover { background: #ffffff; }\n'
                     'QPushButton:pressed { background: #e0e0e0; }')
        else:
            style = ('QPushButton { background: #e8e8e8; border: 1px solid #d0d0d0; '
                     'border-radius: 6px; }\n'
                     'QPushButton:hover { background: #f0f0f0; }\n'
                     'QPushButton:pressed { background: #d0d0d0; }')
        button.setStyleSheet(style)
        if action == 'clear':
            button.clicked.connect(self._calc_clear)
        elif action == 'back':
            button.clicked.connect(self._calc_backspace)
        elif action == 'sign':
            button.clicked.connect(self._calc_toggle_sign)
        elif action == 'equals':
            button.clicked.connect(self._calc_evaluate)
        else:
            button.clicked.connect(lambda _checked=False, token=action: self._calc_append(token))
        return button

    def _calc_append(self, token):
        self.calc_expr.setText(self.calc_expr.text() + token)

    def _calc_clear(self):
        self.calc_expr.clear()
        self.calc_result.setText('0')

    def _calc_backspace(self):
        text = self.calc_expr.text()
        self.calc_expr.setText(text[:-1])

    def _calc_toggle_sign(self):
        text = self.calc_expr.text()
        if not text:
            self.calc_expr.setText('-')
            return
        match = re.search(r'(\d+(?:\.\d+)?)$', text)
        if not match:
            self.calc_expr.setText(text + '-')
            return
        start = match.start()
        number = match.group()
        prefix = text[:start]
        if prefix.endswith('-'):
            self.calc_expr.setText(prefix[:-1] + number)
        else:
            self.calc_expr.setText(prefix + '-' + number)

    def _calc_evaluate(self):
        text = self.calc_expr.text()
        if not text.strip():
            return
        value = self._calc(calc.evaluate_calculator, text, self.calc_angle.currentText(),
                           inputs=(self.calc_expr,))
        if value is None:
            return
        result = calc.format_result(value)
        self.calc_result.setText(result)
        self._log('计算器  %s = %s' % (text.strip(), result))

    def _on_calc_mode_changed(self, mode):
        self.sci_panel.setVisible(mode == '科学')

    # ------------------------------------------------------------------ #
    # 「计算」页
    # ------------------------------------------------------------------ #
    def _build_calc_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_expression_group())
        box.addWidget(self._build_steps_group())
        box.addWidget(self._build_vertical_group())
        box.addWidget(self._build_power_group())
        box.addWidget(self._build_percent_group())
        box.addWidget(self._build_price_group())
        box.addStretch(1)
        return self._finish_page(page)

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

    def _build_steps_group(self):
        group = QGroupBox('分步计算与简便算法')
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel('分步计算：按运算顺序一步步列出来。简便算法：提示能不能凑整、用运算定律。'))

        row = QHBoxLayout()
        self.steps_input = QLineEdit()
        self.steps_input.setPlaceholderText('输入算式，例如 3+5×2-(4÷2) 或 102×15')
        self.steps_input.returnPressed.connect(self.on_steps)
        row.addWidget(self.steps_input, 1)
        button = make_button('分步计算')
        button.clicked.connect(self.on_steps)
        row.addWidget(button)
        button = make_button('简便算法')
        button.clicked.connect(self.on_simplify)
        row.addWidget(button)
        layout.addLayout(row)

        self.steps_result = make_text_result('这里显示每一步', height=150)
        layout.addWidget(self.steps_result)
        return group

    def _build_vertical_group(self):
        group = QGroupBox('竖式演示')
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel('加、减、乘、除都能列竖式（目前支持非负整数，用等宽字体显示）。'))

        row = QHBoxLayout()
        self.vertical_a = make_input('第一个数', NARROW_WIDTH)
        self.vertical_a.returnPressed.connect(self.on_vertical)
        row.addWidget(self.vertical_a)
        self.vertical_op = QComboBox()
        self.vertical_op.addItems(calc.VERTICAL_OPS)
        self.vertical_op.setFixedWidth(60)
        row.addWidget(self.vertical_op)
        self.vertical_b = make_input('第二个数', NARROW_WIDTH)
        self.vertical_b.returnPressed.connect(self.on_vertical)
        row.addWidget(self.vertical_b)
        button = make_button('列竖式')
        button.clicked.connect(self.on_vertical)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)

        self.vertical_result = make_text_result('竖式', height=170, monospace=True)
        layout.addWidget(self.vertical_result)
        return group

    def _build_power_group(self):
        group = QGroupBox('乘方 / 开方 / 带余除法')
        grid = QGridLayout(group)

        # 乘方
        self.power_base = make_input('底数', NARROW_WIDTH)
        self.power_exp = make_input('指数', NARROW_WIDTH)
        self.power_result = make_result('结果')
        button = make_button('计算')
        button.clicked.connect(self.on_power)
        self.power_exp.returnPressed.connect(self.on_power)
        add_cells(grid, 0, ['乘方', self.power_base, '的', self.power_exp, '次方',
                            button, '=', self.power_result])

        # 开方
        self.root_input = make_input('被开方数', NARROW_WIDTH)
        self.root_result = make_result('结果')
        button = make_button('计算')
        button.clicked.connect(self.on_root)
        self.root_input.returnPressed.connect(self.on_root)
        add_cells(grid, 1, ['开方', '√', self.root_input, None, None,
                            button, '=', self.root_result])

        # 带余除法
        self.div_a = make_input('被除数', NARROW_WIDTH)
        self.div_b = make_input('除数', NARROW_WIDTH)
        button = make_button('计算')
        button.clicked.connect(self.on_division)
        self.div_b.returnPressed.connect(self.on_division)

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

        add_cells(grid, 2, ['带余除法', self.div_a, '÷', self.div_b, None,
                            button, '=', remainder_row])
        self.check_result = make_result('验算：商 × 除数 + 余数 = 被除数')
        add_cells(grid, 3, ['验算', None, None, None, None, None, '=', self.check_result])

        grid.setColumnStretch(7, 1)
        return group

    def _build_percent_group(self):
        group = QGroupBox('百分数')
        grid = QGridLayout(group)

        self.pct_a = make_input('例如 200')
        self.pct_b = make_input('例如 15', NARROW_WIDTH)
        self.pct_b.returnPressed.connect(self.on_percent)
        button = make_button('计算')
        button.clicked.connect(self.on_percent)
        self.pct_result = make_result('结果')
        add_cells(grid, 0, [self.pct_a, '的', self.pct_b, '% 是多少', button,
                            '=', self.pct_result])

        self.ratio_a = make_input('例如 30')
        self.ratio_b = make_input('例如 200')
        self.ratio_b.returnPressed.connect(self.on_ratio)
        button = make_button('计算')
        button.clicked.connect(self.on_ratio)
        self.ratio_result = make_result('百分比')
        add_cells(grid, 1, [self.ratio_a, '是', self.ratio_b, '的百分之几', button,
                            '=', self.ratio_result])

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
        self.weight_input.returnPressed.connect(self.on_price)
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
    def _build_fraction_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_fraction_group())
        box.addWidget(self._build_reduce_group())
        box.addWidget(self._build_forms_group())
        box.addStretch(1)
        return self._finish_page(page)

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
        self.frac_b.returnPressed.connect(self.on_fraction)

        layout.addWidget(QLabel('分数'))
        layout.addWidget(self.frac_a)
        layout.addWidget(self.frac_op)
        layout.addWidget(self.frac_b)
        layout.addWidget(button)
        layout.addWidget(QLabel('='))
        layout.addWidget(self.frac_result, 1)
        return group

    def _build_reduce_group(self):
        group = QGroupBox('约分与通分')
        layout = QVBoxLayout(group)
        grid = QGridLayout()

        # 约分
        self.reduce_input = make_input('例如 6/8')
        self.reduce_input.returnPressed.connect(self.on_reduce)
        button = make_button('约分')
        button.clicked.connect(self.on_reduce)
        add_cells(grid, 0, ['约分', self.reduce_input, None, button])

        # 通分
        self.common_a = make_input('例如 1/2')
        self.common_b = make_input('例如 1/3')
        self.common_b.returnPressed.connect(self.on_common)
        button = make_button('通分')
        button.clicked.connect(self.on_common)
        add_cells(grid, 1, ['通分', self.common_a, '和', self.common_b, button])
        grid.setColumnStretch(4, 1)

        layout.addLayout(grid)
        self.fraction_process = make_text_result('约分或通分的过程会显示在这里', height=150)
        layout.addWidget(self.fraction_process)
        return group

    def _build_forms_group(self):
        group = QGroupBox('分数 / 小数 / 百分数互化')
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        self.forms_input = make_input('例如 3/4、0.75 或 75%', 180)
        self.forms_input.returnPressed.connect(self.on_forms)
        row.addWidget(QLabel('数值'))
        row.addWidget(self.forms_input)
        button = make_button('互化')
        button.clicked.connect(self.on_forms)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)

        self.forms_result = make_text_result('三种写法', height=110)
        layout.addWidget(self.forms_result)
        return group

    # ------------------------------------------------------------------ #
    # 「数」页
    # ------------------------------------------------------------------ #
    def _build_number_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_factor_group())
        box.addWidget(self._build_prime_group())
        box.addWidget(self._build_recognition_group())
        box.addStretch(1)
        return self._finish_page(page)

    def _build_factor_group(self):
        group = QGroupBox('因数与倍数')
        grid = QGridLayout(group)

        self.factor_input = make_input('例如 12')
        self.factor_input.returnPressed.connect(self.on_factor)
        button = make_button('分解质因数')
        button.clicked.connect(self.on_factor)
        self.factor_result = make_result('质因数分解结果')
        add_cells(grid, 0, ['整数', self.factor_input, button, '=', self.factor_result])

        self.mult_input = make_input('例如 12,18')
        button = make_button('最大公因数')
        button.clicked.connect(self.on_gcd)
        self.gcd_result = make_result('最大公因数')
        add_cells(grid, 1, ['整数', self.mult_input, button, '=', self.gcd_result])

        button = make_button('最小公倍数')
        button.clicked.connect(self.on_lcm)
        self.lcm_result = make_result('最小公倍数')
        add_cells(grid, 2, [None, None, button, '=', self.lcm_result])

        grid.setColumnStretch(4, 1)
        return group

    def _build_prime_group(self):
        group = QGroupBox('质数、奇偶与因数')
        layout = QVBoxLayout(group)
        grid = QGridLayout()

        self.describe_input = make_input('例如 12')
        self.describe_input.returnPressed.connect(self.on_describe)
        button = make_button('它是奇数还是偶数？是质数吗？')
        button.clicked.connect(self.on_describe)
        add_cells(grid, 0, ['整数', self.describe_input, button])

        self.prime_limit = make_input('100', NARROW_WIDTH)
        self.prime_limit.returnPressed.connect(self.on_prime_table)
        button = make_button('列出质数表')
        button.clicked.connect(self.on_prime_table)
        add_cells(grid, 1, ['范围', self.prime_limit, button, '以内的所有质数'])
        grid.setColumnStretch(3, 1)

        layout.addLayout(grid)
        self.number_detail = make_text_result('详细结果', height=140)
        layout.addWidget(self.number_detail)
        return group

    def _build_recognition_group(self):
        group = QGroupBox('数的认识')
        grid = QGridLayout(group)

        self.approx_input = make_input('例如 123456')
        self.approx_place = QComboBox()
        self.approx_place.addItems(calc.ROUND_PLACES)
        self.approx_place.setCurrentText('万位')
        self.approx_input.returnPressed.connect(self.on_approximate)
        button = make_button('求近似数')
        button.clicked.connect(self.on_approximate)
        self.approx_result = make_result('近似数')
        add_cells(grid, 0, ['近似数', self.approx_input, '精确到', self.approx_place,
                            button, '=', self.approx_result])

        self.rewrite_input = make_input('例如 1234567')
        self.rewrite_unit = QComboBox()
        self.rewrite_unit.addItems(calc.REWRITE_UNITS)
        self.rewrite_input.returnPressed.connect(self.on_rewrite)
        button = make_button('改写')
        button.clicked.connect(self.on_rewrite)
        self.rewrite_result = make_result('改写结果')
        add_cells(grid, 1, ['改写', self.rewrite_input, '改写成用', self.rewrite_unit,
                            button, '=', self.rewrite_result])

        grid.setColumnStretch(6, 1)
        return group

    # ------------------------------------------------------------------ #
    # 「比与统计」页
    # ------------------------------------------------------------------ #
    def _build_ratio_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_proportion_group())
        box.addWidget(self._build_average_group())
        box.addStretch(1)
        return self._finish_page(page)

    def _build_proportion_group(self):
        group = QGroupBox('比与比例')
        layout = QVBoxLayout(group)
        grid = QGridLayout()

        self.proportion_input = make_input('例如 3:4 = 6:x', 240)
        self.proportion_input.returnPressed.connect(self.on_proportion)
        button = make_button('解比例')
        button.clicked.connect(self.on_proportion)
        add_cells(grid, 0, ['比例', self.proportion_input, button])

        self.total_input = make_input('例如 120')
        self.ratio_input = make_input('例如 2:3:5')
        self.ratio_input.returnPressed.connect(self.on_distribute)
        button = make_button('按比分配')
        button.clicked.connect(self.on_distribute)
        add_cells(grid, 1, ['总量', self.total_input, '按比', self.ratio_input, button])
        grid.setColumnStretch(5, 1)

        layout.addLayout(grid)
        self.ratio_process = make_text_result('过程和结果', height=170)
        layout.addWidget(self.ratio_process)
        return group

    def _build_average_group(self):
        group = QGroupBox('平均数')
        layout = QHBoxLayout(group)
        layout.addWidget(QLabel('数据'))
        self.average_input = make_input('例如 12,8,10', 200)
        self.average_input.returnPressed.connect(self.on_average)
        layout.addWidget(self.average_input)
        button = make_button('计算平均数')
        button.clicked.connect(self.on_average)
        layout.addWidget(button)
        layout.addWidget(QLabel('='))
        self.average_result = make_result('平均数')
        layout.addWidget(self.average_result, 1)
        return group

    # ------------------------------------------------------------------ #
    # 「换算」页
    # ------------------------------------------------------------------ #
    def _build_convert_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_unit_group())
        box.addWidget(self._build_compound_group())
        box.addWidget(self._build_datetime_group())
        box.addStretch(1)
        return self._finish_page(page)

    def _build_unit_group(self):
        group = QGroupBox('单位换算')
        layout = QVBoxLayout(group)

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

        self._on_category_changed(self.unit_category.currentText())
        return group

    def _build_compound_group(self):
        group = QGroupBox('复名数互化')
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel('单名数和复名数互相转换，例如 1.5 小时 = 1小时30分、2米5厘米 = 2.05米。'))
        grid = QGridLayout()

        self.compound_category = QComboBox()
        self.compound_category.addItems(calc.compound_categories())
        self.compound_category.currentTextChanged.connect(self._on_compound_category_changed)
        self.compound_value = make_input('例如 1.5', NARROW_WIDTH)
        self.compound_unit = QComboBox()
        self.compound_unit.setFixedWidth(NARROW_WIDTH)
        self.compound_value.returnPressed.connect(self.on_to_compound)
        button = make_button('化成复名数')
        button.clicked.connect(self.on_to_compound)
        self.compound_single_result = make_result('复名数')
        add_cells(grid, 0, ['类别', self.compound_category, '数值', self.compound_value,
                            self.compound_unit, button, '=', self.compound_single_result])

        self.compound_input = make_input('例如 2米5厘米', 160)
        self.compound_input.returnPressed.connect(self.on_from_compound)
        button = make_button('化成单名数')
        button.clicked.connect(self.on_from_compound)
        self.compound_result = make_result('单名数')
        add_cells(grid, 1, ['复名数', self.compound_input, None, None, None, button,
                            '=', self.compound_result])

        grid.setColumnStretch(6, 1)
        layout.addLayout(grid)
        self._on_compound_category_changed(self.compound_category.currentText())
        return group

    def _build_datetime_group(self):
        group = QGroupBox('时刻与日期')
        layout = QVBoxLayout(group)
        grid = QGridLayout()

        self.time_from = make_input('例如 8:30', NARROW_WIDTH)
        self.time_to = make_input('例如 11:15', NARROW_WIDTH)
        self.time_to.returnPressed.connect(self.on_elapsed)
        button = make_button('经过多久')
        button.clicked.connect(self.on_elapsed)
        add_cells(grid, 0, ['从', self.time_from, '到', self.time_to, button])

        self.date_input = make_input('例如 2026-09-14', 140)
        self.date_days = make_input('例如 30', NARROW_WIDTH)
        self.date_days.returnPressed.connect(self.on_date_offset)
        button = make_button('推算日期')
        button.clicked.connect(self.on_date_offset)
        add_cells(grid, 1, ['日期', self.date_input, '过', self.date_days, '天', button])
        grid.setColumnStretch(5, 1)

        layout.addLayout(grid)
        self.datetime_result = make_text_result('结果', height=120)
        layout.addWidget(self.datetime_result)
        return group

    # ------------------------------------------------------------------ #
    # 「几何」页
    # ------------------------------------------------------------------ #
    def _build_geometry_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_shape_group())
        box.addWidget(self._build_triangle_group())
        box.addStretch(1)
        return self._finish_page(page)

    def _build_shape_group(self):
        group = QGroupBox('图形的面积、周长、体积与表面积')
        layout = QVBoxLayout(group)

        row = QHBoxLayout()
        row.addWidget(QLabel('图形'))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(calc.geometry_shape_names())
        self.shape_combo.currentTextChanged.connect(self._on_shape_changed)
        row.addWidget(self.shape_combo, 1)
        row.addWidget(QLabel('单位'))
        self.geometry_unit = QComboBox()
        self.geometry_unit.addItems(calc.geometry_units())
        self.geometry_unit.currentTextChanged.connect(self._on_geometry_unit_changed)
        row.addWidget(self.geometry_unit)
        layout.addLayout(row)

        self.param_box = QGroupBox('参数')
        self.param_grid = QGridLayout(self.param_box)
        layout.addWidget(self.param_box)

        # 参数行预先建好，切换图形时只显示/隐藏，
        # 避免 deleteLater() 延迟销毁导致新旧控件叠在一起
        self.param_rows = []
        max_params = max(len(shape['params']) for shape in calc.GEOMETRY_SHAPES)
        for index in range(max_params):
            label = QLabel()
            edit = make_input()
            edit.returnPressed.connect(self.on_geometry)
            self.param_grid.addWidget(label, index, 0)
            self.param_grid.addWidget(edit, index, 1)
            self.param_rows.append((label, edit))
        self.param_grid.setColumnStretch(1, 1)

        button = make_button('计算')
        button.clicked.connect(self.on_geometry)
        layout.addWidget(button)

        layout.addWidget(QLabel('结果'))
        self.geometry_result = make_text_result('结果', height=160)
        layout.addWidget(self.geometry_result, 1)

        self.param_inputs = {}
        self._on_shape_changed(self.shape_combo.currentText())
        return group

    def _build_triangle_group(self):
        group = QGroupBox('三角形的三边关系')
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(QLabel('三边'))
        self.side_a = make_input('第一条边', NARROW_WIDTH)
        self.side_b = make_input('第二条边', NARROW_WIDTH)
        self.side_c = make_input('第三条边', NARROW_WIDTH)
        for widget in (self.side_a, self.side_b, self.side_c):
            widget.returnPressed.connect(self.on_triangle)
            row.addWidget(widget)
        button = make_button('能不能围成三角形')
        button.clicked.connect(self.on_triangle)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)

        self.triangle_result = make_text_result('结果', height=140)
        layout.addWidget(self.triangle_result)
        return group

    # ------------------------------------------------------------------ #
    # 「解方程」页
    # ------------------------------------------------------------------ #
    def _build_equation_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox('一元方程')
        box = QVBoxLayout(group)
        box.addWidget(QLabel(
            '请输入一元方程（含未知数 x）。\n'
            '支持省略乘号、中文全角符号、^ 表示乘方。例如：2x + 3 = 7、x^2 - 4 = 0'))
        box.addWidget(QLabel('「分步解答」目前只支持一元一次方程，会一步步列出移项、合并和检验。'))

        row = QHBoxLayout()
        row.addWidget(QLabel('方程'))
        self.eq_input = QLineEdit()
        self.eq_input.setPlaceholderText('例如 2x + 3 = 7')
        self.eq_input.returnPressed.connect(self.on_solve)
        row.addWidget(self.eq_input, 1)
        button = make_button('解方程')
        button.clicked.connect(self.on_solve)
        row.addWidget(button)
        button = make_button('分步解答')
        button.clicked.connect(self.on_solve_steps)
        row.addWidget(button)
        box.addLayout(row)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel('解'))
        self.eq_result = make_result('方程的解')
        font = self.eq_result.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        self.eq_result.setFont(font)
        result_row.addWidget(self.eq_result, 1)
        box.addLayout(result_row)

        box.addWidget(QLabel('分步过程'))
        self.eq_steps = make_text_result('点「分步解答」显示每一步', height=170)
        box.addWidget(self.eq_steps)

        layout.addWidget(group)
        layout.addStretch(1)
        return self._finish_page(page)

    # ------------------------------------------------------------------ #
    # 「更多工具」页
    # ------------------------------------------------------------------ #
    def _build_tools_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        box.addWidget(self._build_stats_group())
        box.addWidget(self._build_divisibility_group())
        box.addWidget(self._build_divisors_group())
        box.addWidget(self._build_base_group())
        box.addWidget(self._build_scale_group())
        box.addWidget(self._build_discount_group())
        box.addWidget(self._build_combinatorics_group())
        box.addWidget(self._build_cn_number_group())
        box.addWidget(self._build_polygon_group())
        box.addWidget(self._build_currency_group())
        box.addStretch(1)
        return self._finish_page(page)

    def _build_stats_group(self):
        group = QGroupBox('统计量（中位数、众数、极差、方差、标准差）')
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(QLabel('数据'))
        self.stats_input = make_input('例如 12,8,10,8,9', 220)
        self.stats_input.returnPressed.connect(self.on_statistics)
        row.addWidget(self.stats_input)
        button = make_button('计算统计量')
        button.clicked.connect(self.on_statistics)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        self.stats_result = make_text_result('统计结果', height=170)
        layout.addWidget(self.stats_result)
        return group

    def _build_divisibility_group(self):
        group = QGroupBox('整除特征判断')
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(QLabel('整数'))
        self.div_input = make_input('例如 12345', 160)
        self.div_input.returnPressed.connect(self.on_divisibility)
        row.addWidget(self.div_input)
        button = make_button('判断整除')
        button.clicked.connect(self.on_divisibility)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        self.div_result = make_text_result('判断结果', height=170)
        layout.addWidget(self.div_result)
        return group

    def _build_divisors_group(self):
        group = QGroupBox('约数与倍数表')
        layout = QVBoxLayout(group)
        grid = QGridLayout()

        self.factors_only_input = make_input('例如 12')
        self.factors_only_input.returnPressed.connect(self.on_list_factors)
        button = make_button('列因数')
        button.clicked.connect(self.on_list_factors)
        self.factors_only_result = make_result('全部因数')
        add_cells(grid, 0, ['整数', self.factors_only_input, button, '=', self.factors_only_result])

        self.multiples_input = make_input('例如 7')
        self.multiples_count = make_input('10', NARROW_WIDTH)
        self.multiples_input.returnPressed.connect(self.on_list_multiples)
        button = make_button('列倍数')
        button.clicked.connect(self.on_list_multiples)
        self.multiples_result = make_result('前若干个倍数')
        add_cells(grid, 1, ['整数', self.multiples_input, '前', self.multiples_count,
                            '个倍数', button, '=', self.multiples_result])
        grid.setColumnStretch(7, 1)
        layout.addLayout(grid)

        row = QHBoxLayout()
        row.addWidget(QLabel('两数'))
        self.common_a = make_input('例如 12', NARROW_WIDTH)
        row.addWidget(self.common_a)
        row.addWidget(QLabel('和'))
        self.common_b = make_input('例如 18', NARROW_WIDTH)
        self.common_b.returnPressed.connect(self.on_common_divisors)
        row.addWidget(self.common_b)
        button = make_button('公因数与公倍数')
        button.clicked.connect(self.on_common_divisors)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        self.common_result = make_text_result('公因数与公倍数', height=52)
        layout.addWidget(self.common_result)
        return group

    def _build_base_group(self):
        group = QGroupBox('进制转换（二、八、十、十六进制）')
        grid = QGridLayout(group)
        self.base_value = make_input('例如 1010', 160)
        self.base_value.returnPressed.connect(self.on_base_convert)
        self.base_from = QComboBox()
        self.base_from.addItems([str(b) for b in calc.BASE_CHOICES])
        self.base_from.setCurrentText('2')
        self.base_to = QComboBox()
        self.base_to.addItems([str(b) for b in calc.BASE_CHOICES])
        self.base_to.setCurrentText('10')
        button = make_button('转换')
        button.clicked.connect(self.on_base_convert)
        self.base_result = make_result('转换结果')
        add_cells(grid, 0, ['数值', self.base_value, '从', self.base_from, '进制',
                            '到', self.base_to, '进制', button, '=', self.base_result])
        grid.setColumnStretch(9, 1)
        return group

    def _build_scale_group(self):
        group = QGroupBox('比例尺换算')
        layout = QVBoxLayout(group)
        grid = QGridLayout()
        self.scale_input = make_input('例如 1:50000', 130)
        self.scale_distance = make_input('例如 3', NARROW_WIDTH)
        self.scale_distance.returnPressed.connect(self.on_scale_convert)
        self.scale_unit = QComboBox()
        self.scale_unit.addItems(calc.LENGTH_UNITS)
        self.scale_unit.setCurrentText('厘米')
        self.scale_direction = QComboBox()
        self.scale_direction.addItems(calc.SCALE_DIRECTIONS)
        button = make_button('换算')
        button.clicked.connect(self.on_scale_convert)
        add_cells(grid, 0, ['比例尺', self.scale_input, '距离', self.scale_distance,
                            self.scale_unit, self.scale_direction, button])
        grid.setColumnStretch(6, 1)
        layout.addLayout(grid)
        self.scale_result = make_text_result('换算结果', height=90)
        layout.addWidget(self.scale_result)
        return group

    def _build_discount_group(self):
        group = QGroupBox('折扣、利息与税率')
        layout = QVBoxLayout(group)
        grid = QGridLayout()

        self.discount_price = make_input('原价 例如 200', 130)
        self.discount_rate = make_input('例如 8折', NARROW_WIDTH)
        self.discount_rate.returnPressed.connect(self.on_discount)
        button = make_button('算折扣')
        button.clicked.connect(self.on_discount)
        add_cells(grid, 0, ['原价', self.discount_price, '折扣', self.discount_rate, button])

        self.interest_principal = make_input('本金 例如 10000', 130)
        self.interest_rate = make_input('例如 3.5%', NARROW_WIDTH)
        self.interest_years = make_input('1', NARROW_WIDTH)
        self.interest_years.returnPressed.connect(self.on_interest)
        button = make_button('算利息')
        button.clicked.connect(self.on_interest)
        add_cells(grid, 1, ['本金', self.interest_principal, '年利率', self.interest_rate,
                            '存期(年)', self.interest_years, button])

        self.tax_price = make_input('金额 例如 100', 130)
        self.tax_rate = make_input('例如 13%', NARROW_WIDTH)
        self.tax_rate.returnPressed.connect(self.on_tax)
        button = make_button('算税额')
        button.clicked.connect(self.on_tax)
        add_cells(grid, 2, ['金额', self.tax_price, '税率', self.tax_rate, button])
        grid.setColumnStretch(6, 1)
        layout.addLayout(grid)
        self.discount_result = make_text_result('计算结果', height=120)
        layout.addWidget(self.discount_result)
        return group

    def _build_combinatorics_group(self):
        group = QGroupBox('阶乘与排列组合')
        grid = QGridLayout(group)

        self.factorial_input = make_input('例如 5')
        self.factorial_input.returnPressed.connect(self.on_factorial)
        button = make_button('n! 阶乘')
        button.clicked.connect(self.on_factorial)
        self.factorial_result = make_result('阶乘')
        add_cells(grid, 0, ['n', self.factorial_input, button, '=', self.factorial_result])

        self.perm_n = make_input('例如 5', NARROW_WIDTH)
        self.perm_r = make_input('例如 2', NARROW_WIDTH)
        self.perm_r.returnPressed.connect(self.on_permutation)
        button = make_button('排列 A(n,r)')
        button.clicked.connect(self.on_permutation)
        self.perm_result = make_result('排列数')
        add_cells(grid, 1, ['n', self.perm_n, 'r', self.perm_r, button, '=', self.perm_result])

        self.comb_n = make_input('例如 5', NARROW_WIDTH)
        self.comb_r = make_input('例如 2', NARROW_WIDTH)
        self.comb_r.returnPressed.connect(self.on_combination)
        button = make_button('组合 C(n,r)')
        button.clicked.connect(self.on_combination)
        self.comb_result = make_result('组合数')
        add_cells(grid, 2, ['n', self.comb_n, 'r', self.comb_r, button, '=', self.comb_result])
        grid.setColumnStretch(6, 1)
        return group

    def _build_cn_number_group(self):
        group = QGroupBox('中文数字与人民币大写')
        grid = QGridLayout(group)

        self.cn_number_input = make_input('例如 12345', 160)
        self.cn_number_input.returnPressed.connect(self.on_cn_number)
        button = make_button('读法')
        button.clicked.connect(self.on_cn_number)
        self.cn_number_result = make_result('中文读法')
        add_cells(grid, 0, ['数字', self.cn_number_input, button, '=', self.cn_number_result])

        self.rmb_input = make_input('例如 123.45', 160)
        self.rmb_input.returnPressed.connect(self.on_rmb_upper)
        button = make_button('人民币大写')
        button.clicked.connect(self.on_rmb_upper)
        self.rmb_result = make_result('大写金额')
        add_cells(grid, 1, ['金额', self.rmb_input, button, '=', self.rmb_result])
        grid.setColumnStretch(4, 1)
        return group

    def _build_polygon_group(self):
        group = QGroupBox('多边形内角和')
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(QLabel('边数'))
        self.polygon_input = make_input('例如 5', NARROW_WIDTH)
        self.polygon_input.returnPressed.connect(self.on_polygon)
        row.addWidget(self.polygon_input)
        button = make_button('计算')
        button.clicked.connect(self.on_polygon)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        self.polygon_result = make_text_result('内角和、内外角、对角线', height=110)
        layout.addWidget(self.polygon_result)
        return group

    def _build_currency_group(self):
        group = QGroupBox('货币换算（参考汇率，非实时）')
        layout = QVBoxLayout(group)
        grid = QGridLayout()
        self.currency_amount = make_input('例如 100', 130)
        self.currency_amount.returnPressed.connect(self.on_currency_convert)
        self.currency_from = QComboBox()
        self.currency_from.addItems(calc.currency_categories())
        self.currency_from.setCurrentText('美元')
        self.currency_to = QComboBox()
        self.currency_to.addItems(calc.currency_categories())
        self.currency_to.setCurrentText('人民币')
        button = make_button('换算')
        button.clicked.connect(self.on_currency_convert)
        add_cells(grid, 0, ['金额', self.currency_amount, '从', self.currency_from,
                            '到', self.currency_to, button])
        grid.setColumnStretch(6, 1)
        layout.addLayout(grid)
        self.currency_result = make_text_result('换算结果', height=110)
        layout.addWidget(self.currency_result)
        return group

    # ------------------------------------------------------------------ #
    # 事件处理
    # ------------------------------------------------------------------ #
    def on_expression(self):
        text = self.expr_input.text()
        value = self._calc(calc.evaluate_expression, text, inputs=(self.expr_input,))
        if value is None:
            return
        result = calc.format_expression_result(value, text)
        self.expr_result.setText(result)
        self._log('算式  %s = %s' % (text.strip(), result))

    def on_steps(self):
        text = self.steps_input.text()
        steps = self._calc(calc.expression_steps, text, inputs=(self.steps_input,))
        if steps is None:
            return
        step_list, result = steps
        lines = ['原式  %s' % text.strip()]
        for index, (before, after, current) in enumerate(step_list, 1):
            lines.append('第 %d 步  %s = %s        此时算式：%s'
                         % (index, before, after, current))
        if not step_list:
            lines.append('这个算式已经是最简形式了。')
        lines.append('结果  %s' % calc.format_result(result))
        text_result = '\n'.join(lines)
        self.steps_result.setPlainText(text_result)
        self._log('分步  %s' % text.strip())

    def on_simplify(self):
        text = self.steps_input.text()
        tips = self._calc(calc.simplify_advice, text, inputs=(self.steps_input,))
        if tips is None:
            return
        lines = ['算式  %s' % text.strip()] + ['· ' + tip for tip in tips]
        self.steps_result.setPlainText('\n'.join(lines))
        self._log('简便算法  %s' % text.strip())

    def on_vertical(self):
        first = self.vertical_a.text()
        second = self.vertical_b.text()
        operator = self.vertical_op.currentText()
        content = self._calc(calc.vertical_calculate, operator, first, second,
                             inputs=(self.vertical_a, self.vertical_b))
        if content is None:
            return
        self.vertical_result.setPlainText(content)
        self._log('竖式  %s %s %s' % (first.strip(), operator, second.strip()))

    def on_fraction(self):
        value = self._calc(calc.fraction_operate, self.frac_a.text(),
                           self.frac_op.currentText(), self.frac_b.text(),
                           inputs=(self.frac_a, self.frac_b))
        if value is None:
            return
        result = calc.format_result(value)
        self.frac_result.setText(result)
        self._log('分数  %s %s %s = %s' % (self.frac_a.text().strip(),
                                          self.frac_op.currentText(),
                                          self.frac_b.text().strip(), result))

    def on_reduce(self):
        content = self._calc(calc.reduce_fraction, self.reduce_input.text(),
                             inputs=(self.reduce_input,))
        if content is None:
            return
        self.fraction_process.setPlainText('【约分】\n%s' % content)
        self._log('约分  %s' % self.reduce_input.text().strip())

    def on_common(self):
        content = self._calc(calc.common_denominator, self.common_a.text(),
                             self.common_b.text(),
                             inputs=(self.common_a, self.common_b))
        if content is None:
            return
        self.fraction_process.setPlainText('【通分】\n%s' % content)
        self._log('通分  %s 和 %s' % (self.common_a.text().strip(),
                                    self.common_b.text().strip()))

    def on_forms(self):
        content = self._calc(calc.convert_number_forms, self.forms_input.text(),
                             inputs=(self.forms_input,))
        if content is None:
            return
        self.forms_result.setPlainText(content)
        self._log('互化  %s' % self.forms_input.text().strip())

    def on_factor(self):
        content = self._calc(calc.prime_factorization, self.factor_input.text(),
                             inputs=(self.factor_input,))
        if content is None:
            return
        self.factor_result.setText(content)
        self._log('分解质因数  %s = %s' % (self.factor_input.text().strip(), content))

    def on_gcd(self):
        value = self._calc(calc.greatest_common_divisor, self.mult_input.text(),
                           inputs=(self.mult_input,))
        if value is None:
            return
        self.gcd_result.setText(str(value))
        self._log('最大公因数  %s = %s' % (self.mult_input.text().strip(), value))

    def on_lcm(self):
        value = self._calc(calc.least_common_multiple, self.mult_input.text(),
                           inputs=(self.mult_input,))
        if value is None:
            return
        self.lcm_result.setText(str(value))
        self._log('最小公倍数  %s = %s' % (self.mult_input.text().strip(), value))

    def on_describe(self):
        content = self._calc(calc.describe_number, self.describe_input.text(),
                             inputs=(self.describe_input,))
        if content is None:
            return
        self.number_detail.setPlainText(content)
        self._log('判断  %s' % self.describe_input.text().strip())

    def on_prime_table(self):
        content = self._calc(calc.prime_table, self.prime_limit.text(),
                             inputs=(self.prime_limit,))
        if content is None:
            return
        self.number_detail.setPlainText(content)
        self._log('质数表  %s 以内' % self.prime_limit.text().strip())

    def on_approximate(self):
        content = self._calc(calc.approximate_number, self.approx_input.text(),
                             self.approx_place.currentText(),
                             inputs=(self.approx_input,))
        if content is None:
            return
        self.approx_result.setText(content.splitlines()[0])
        self._log('近似数  %s' % self.approx_input.text().strip())

    def on_rewrite(self):
        content = self._calc(calc.rewrite_number, self.rewrite_input.text(),
                             self.rewrite_unit.currentText(),
                             inputs=(self.rewrite_input,))
        if content is None:
            return
        self.rewrite_result.setText(content)
        self._log('改写  %s' % content)

    def on_average(self):
        content = self._calc(calc.average_text, self.average_input.text(),
                             inputs=(self.average_input,))
        if content is None:
            return
        self.average_result.setText(content)
        self._log('平均数  %s' % content)

    def on_proportion(self):
        content = self._calc(calc.solve_proportion, self.proportion_input.text(),
                             inputs=(self.proportion_input,))
        if content is None:
            return
        self.ratio_process.setPlainText('【解比例】\n%s' % content)
        self._log('解比例  %s' % self.proportion_input.text().strip())

    def on_distribute(self):
        content = self._calc(calc.distribute_by_ratio, self.total_input.text(),
                             self.ratio_input.text(),
                             inputs=(self.total_input, self.ratio_input))
        if content is None:
            return
        self.ratio_process.setPlainText('【按比分配】\n%s' % content)
        self._log('按比分配  %s 按 %s' % (self.total_input.text().strip(),
                                        self.ratio_input.text().strip()))

    def on_power(self):
        value = self._calc(calc.power, self.power_base.text(), self.power_exp.text(),
                           inputs=(self.power_base, self.power_exp))
        if value is None:
            return
        result = calc.format_result(value)
        self.power_result.setText(result)
        self._log('乘方  %s^%s = %s' % (self.power_base.text().strip(),
                                       self.power_exp.text().strip(), result))

    def on_root(self):
        value = self._calc(calc.square_root, self.root_input.text(),
                           inputs=(self.root_input,))
        if value is None:
            return
        result = calc.format_result(value)
        self.root_result.setText(result)
        self._log('开方  √%s = %s' % (self.root_input.text().strip(), result))

    def on_division(self):
        outcome = self._calc(calc.division_with_remainder, self.div_a.text(),
                             self.div_b.text(), inputs=(self.div_a, self.div_b))
        if outcome is None:
            return
        quotient, remainder = outcome
        self.quot_result.setText(str(quotient))
        self.rem_result.setText(str(remainder))
        check = calc.division_check_text(self.div_a.text(), self.div_b.text(),
                                         quotient, remainder)
        self.check_result.setText(check)
        self._log('带余除法  %s ÷ %s = %s 余 %s' % (self.div_a.text().strip(),
                                                  self.div_b.text().strip(),
                                                  quotient, remainder))

    def on_percent(self):
        value = self._calc(calc.percent_of, self.pct_a.text(), self.pct_b.text(),
                           inputs=(self.pct_a, self.pct_b))
        if value is None:
            return
        result = calc.format_decimal(float(value))
        self.pct_result.setText(result)
        self._log('百分数  %s 的 %s%% = %s' % (self.pct_a.text().strip(),
                                             self.pct_b.text().strip(), result))

    def on_ratio(self):
        value = self._calc(calc.percent_ratio, self.ratio_a.text(), self.ratio_b.text(),
                           inputs=(self.ratio_a, self.ratio_b))
        if value is None:
            return
        result = '%s%%' % calc.format_decimal(float(value))
        self.ratio_result.setText(result)
        self._log('百分比  %s 是 %s 的 %s' % (self.ratio_a.text().strip(),
                                            self.ratio_b.text().strip(), result))

    def on_price(self):
        try:
            price = calc.parse_number(self.price_input.text(), '单价')
            weight = calc.parse_number(self.weight_input.text(), '重量')
        except calc.CalcError as exc:
            self._mark_error(exc, (self.price_input, self.weight_input))
            return
        self._clear_marks()
        total = '%.2f' % float(price * weight)
        self.total_result.setText(total)
        self._log('总价  %s 元/千克 × %s 千克 = %s 元'
                  % (self.price_input.text().strip(), self.weight_input.text().strip(),
                     total))

    def on_convert(self):
        value = self._calc(calc.convert_unit,
                           self.unit_category.currentText(),
                           self.unit_value.text(),
                           self.unit_from.currentText(),
                           self.unit_to.currentText(),
                           inputs=(self.unit_value,))
        if value is None:
            return
        result = calc.format_decimal(value)
        self.unit_result.setText(result)
        self._log('换算  %s %s = %s %s' % (self.unit_value.text().strip(),
                                          self.unit_from.currentText(), result,
                                          self.unit_to.currentText()))

    def on_to_compound(self):
        content = self._calc(calc.to_compound_number,
                             self.compound_category.currentText(),
                             self.compound_value.text(),
                             self.compound_unit.currentText(),
                             inputs=(self.compound_value,))
        if content is None:
            return
        self.compound_single_result.setText(content)
        self._log('复名数  %s' % content)

    def on_from_compound(self):
        content = self._calc(calc.from_compound_number,
                             self.compound_category.currentText(),
                             self.compound_input.text(),
                             inputs=(self.compound_input,))
        if content is None:
            return
        self.compound_result.setText(content)
        self._log('单名数  %s' % content)

    def on_elapsed(self):
        content = self._calc(calc.elapsed_time, self.time_from.text(),
                             self.time_to.text(),
                             inputs=(self.time_from, self.time_to))
        if content is None:
            return
        self.datetime_result.setPlainText('【经过时间】\n%s' % content)
        self._log('经过时间  %s 到 %s' % (self.time_from.text().strip(),
                                        self.time_to.text().strip()))

    def on_date_offset(self):
        content = self._calc(calc.date_offset, self.date_input.text(),
                             self.date_days.text(),
                             inputs=(self.date_input, self.date_days))
        if content is None:
            return
        self.datetime_result.setPlainText('【日期推算】\n%s' % content)
        self._log('日期推算  %s' % self.date_input.text().strip())

    def on_geometry(self):
        self._run_geometry(log=True)

    def _run_geometry(self, log=True):
        unit = self.geometry_unit.currentText()
        raw = {key: edit.text() for key, edit in self.param_inputs.items()}
        content = self._calc(calc.geometry_text, self.shape_combo.currentText(), raw, unit,
                             inputs=tuple(self.param_inputs.values()))
        if content is None:
            return
        self.geometry_result.setPlainText(content)
        if log:
            first_line = content.splitlines()[0] if content else ''
            self._log('%s  %s' % (self.shape_combo.currentText(), first_line))

    def on_triangle(self):
        content = self._calc(calc.triangle_check, self.side_a.text(),
                             self.side_b.text(), self.side_c.text(),
                             inputs=(self.side_a, self.side_b, self.side_c))
        if content is None:
            return
        self.triangle_result.setPlainText(content)
        self._log('三角形判断  %s、%s、%s' % (self.side_a.text().strip(),
                                            self.side_b.text().strip(),
                                            self.side_c.text().strip()))

    def on_solve(self):
        answer = self._calc(calc.solve_equation, self.eq_input.text(),
                            inputs=(self.eq_input,))
        if answer is None:
            return
        self.eq_result.setText(answer)
        self._log('解方程  %s → %s' % (self.eq_input.text().strip(), answer))

    def on_solve_steps(self):
        content = self._calc(calc.solve_equation_steps, self.eq_input.text(),
                             inputs=(self.eq_input,))
        if content is None:
            return
        self.eq_steps.setPlainText(content)
        self._log('分步解方程  %s' % self.eq_input.text().strip())

    def on_statistics(self):
        content = self._calc(calc.statistics, self.stats_input.text(),
                             inputs=(self.stats_input,))
        if content is None:
            return
        self.stats_result.setPlainText(content)
        self._log('统计量  %s' % self.stats_input.text().strip())

    def on_divisibility(self):
        content = self._calc(calc.divisibility_test, self.div_input.text(),
                             inputs=(self.div_input,))
        if content is None:
            return
        self.div_result.setPlainText(content)
        self._log('整除判断  %s' % self.div_input.text().strip())

    def on_list_factors(self):
        content = self._calc(calc.list_factors, self.factors_only_input.text(),
                             inputs=(self.factors_only_input,))
        if content is None:
            return
        self.factors_only_result.setText(content)
        self._log('列因数  %s' % content)

    def on_list_multiples(self):
        content = self._calc(calc.list_multiples, self.multiples_input.text(),
                             self.multiples_count.text(),
                             inputs=(self.multiples_input, self.multiples_count))
        if content is None:
            return
        self.multiples_result.setText(content)
        self._log('列倍数  %s' % content)

    def on_common_divisors(self):
        content = self._calc(calc.common_divisors_multiples, self.common_a.text(),
                             self.common_b.text(),
                             inputs=(self.common_a, self.common_b))
        if content is None:
            return
        self.common_result.setPlainText(content)
        self._log('公因数与公倍数  %s 和 %s'
                  % (self.common_a.text().strip(), self.common_b.text().strip()))

    def on_base_convert(self):
        content = self._calc(calc.base_convert, self.base_value.text(),
                             self.base_from.currentText(), self.base_to.currentText(),
                             inputs=(self.base_value,))
        if content is None:
            return
        self.base_result.setText(content)
        self._log('进制转换  %s' % content)

    def on_scale_convert(self):
        content = self._calc(calc.scale_convert, self.scale_input.text(),
                             self.scale_distance.text(), self.scale_unit.currentText(),
                             self.scale_direction.currentText(),
                             inputs=(self.scale_input, self.scale_distance))
        if content is None:
            return
        self.scale_result.setPlainText(content)
        self._log('比例尺  %s' % content)

    def on_discount(self):
        content = self._calc(calc.discount, self.discount_price.text(),
                             self.discount_rate.text(),
                             inputs=(self.discount_price, self.discount_rate))
        if content is None:
            return
        self.discount_result.setPlainText(content)
        self._log('折扣  %s' % content)

    def on_interest(self):
        content = self._calc(calc.interest, self.interest_principal.text(),
                             self.interest_rate.text(), self.interest_years.text(),
                             inputs=(self.interest_principal, self.interest_rate,
                                     self.interest_years))
        if content is None:
            return
        self.discount_result.setPlainText(content)
        self._log('利息  %s' % content)

    def on_tax(self):
        content = self._calc(calc.tax_amount, self.tax_price.text(),
                             self.tax_rate.text(),
                             inputs=(self.tax_price, self.tax_rate))
        if content is None:
            return
        self.discount_result.setPlainText(content)
        self._log('税额  %s' % content)

    def on_factorial(self):
        content = self._calc(calc.factorial_of, self.factorial_input.text(),
                             inputs=(self.factorial_input,))
        if content is None:
            return
        self.factorial_result.setText(content)
        self._log('阶乘  %s' % content)

    def on_permutation(self):
        content = self._calc(calc.permutation, self.perm_n.text(), self.perm_r.text(),
                             inputs=(self.perm_n, self.perm_r))
        if content is None:
            return
        self.perm_result.setText(content)
        self._log('排列  %s' % content)

    def on_combination(self):
        content = self._calc(calc.combination, self.comb_n.text(), self.comb_r.text(),
                             inputs=(self.comb_n, self.comb_r))
        if content is None:
            return
        self.comb_result.setText(content)
        self._log('组合  %s' % content)

    def on_cn_number(self):
        content = self._calc(calc.number_to_chinese, self.cn_number_input.text(),
                             inputs=(self.cn_number_input,))
        if content is None:
            return
        self.cn_number_result.setText(content)
        self._log('中文读法  %s' % content)

    def on_rmb_upper(self):
        content = self._calc(calc.number_to_rmb_upper, self.rmb_input.text(),
                             inputs=(self.rmb_input,))
        if content is None:
            return
        self.rmb_result.setText(content)
        self._log('人民币大写  %s' % content)

    def on_polygon(self):
        content = self._calc(calc.polygon_angles, self.polygon_input.text(),
                             inputs=(self.polygon_input,))
        if content is None:
            return
        self.polygon_result.setPlainText(content)
        self._log('多边形  %s' % content)

    def on_currency_convert(self):
        content = self._calc(calc.currency_convert, self.currency_amount.text(),
                             self.currency_from.currentText(), self.currency_to.currentText(),
                             inputs=(self.currency_amount,))
        if content is None:
            return
        self.currency_result.setPlainText(content)
        self._log('货币换算  %s' % content)

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

    def _on_compound_category_changed(self, category):
        units = calc.compound_units(category)
        self.compound_unit.blockSignals(True)
        self.compound_unit.clear()
        self.compound_unit.addItems(units)
        self.compound_unit.blockSignals(False)
        if units:
            # 默认选一个「中间」的单位，例如长度选厘米、时间选小时
            self.compound_unit.setCurrentIndex(len(units) // 2)
        self.compound_input.setPlaceholderText(
            '例如 %s' % self._compound_example(category))

    @staticmethod
    def _compound_example(category):
        return {'长度': '2米5厘米', '质量': '1千克200克',
                '时间': '1小时30分', '人民币': '3元5角'}.get(category, '2米5厘米')

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

    def _on_geometry_unit_changed(self, _unit):
        if self.geometry_result.toPlainText().strip():
            self._run_geometry(log=False)

    # -- 计算与报错 -------------------------------------------------------- #
    def _calc(self, func, *args, inputs=()):
        """执行计算：先清掉上次的红框，出错时弹窗、标红并返回 None。"""
        self._clear_marks()
        try:
            return func(*args)
        except calc.CalcError as exc:
            self._mark_error(exc, inputs)
            return None

    def _warn(self, message):
        QMessageBox.warning(self, '输入有误', str(message))

    def _mark_error(self, message, inputs):
        """把出问题的那几个输入框标红，并把光标放到第一个空框里。"""
        for widget in inputs:
            widget.setStyleSheet('border: 1px solid #d9534f;')
        for widget in inputs:
            if not widget.text().strip():
                widget.setFocus()
                break
        else:
            if inputs:
                inputs[0].setFocus()
        self._warn(message)

    def _clear_marks(self):
        for widget in self.findChildren(QLineEdit):
            if widget.styleSheet():
                widget.setStyleSheet('')

    # -- 页面收尾 ---------------------------------------------------------- #
    @staticmethod
    def _finish_page(page):
        """收紧边距并套上滚动条，让内容尽量一屏放得下。"""
        for group in page.findChildren(QGroupBox):
            if group.layout() is not None:
                group.layout().setContentsMargins(8, 6, 8, 6)
                group.layout().setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll


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
