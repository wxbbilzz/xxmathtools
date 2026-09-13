#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小学数学工具 —— 计算逻辑层。

本模块不依赖 Qt，可以脱离界面单独测试。
包含：算式计算、分数运算、因数与倍数、乘方/开方/带余除法、
百分数、单位换算、几何计算、一元方程求解。
"""

import math
import re

from sympy import factorint, ilcm, pi, simplify, solve, sqrt
from sympy import gcd as sym_gcd
from sympy.abc import x
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    rationalize,
    standard_transformations,
)


class CalcError(Exception):
    """输入不合法或无法计算。"""


# --------------------------------------------------------------------------- #
# 文本预处理
# --------------------------------------------------------------------------- #
# 全角 → 半角，中文运算符 → 英文运算符
_TABLE = {chr(0xFF10 + i): str(i) for i in range(10)}
_TABLE.update({
    '（': '(', '）': ')', '＝': '=', '＋': '+', '－': '-', '−': '-', '—': '-',
    '×': '*', '÷': '/', '＾': '^', '．': '.', '，': ',', '、': ',',
    '　': ' ', 'ｘ': 'x', 'Ｘ': 'x', '％': '%',
})
_TRANSLATE = str.maketrans(_TABLE)
_TRANSFORMS = standard_transformations + (rationalize, implicit_multiplication_application)

# 把 √16、√(16) 之类写法转成 sqrt(16)
_SQRT_RE = re.compile(r'√\s*(\d+(?:\.\d+)?|\([^()]*\))')


def normalize(text):
    """统一全角、中文运算符等写法。"""
    text = text.translate(_TRANSLATE)
    text = text.replace('^', '**')
    text = text.replace('π', 'pi')
    text = _SQRT_RE.sub(r'sqrt(\1)', text)
    return text.strip()


# --------------------------------------------------------------------------- #
# 数值解析与显示
# --------------------------------------------------------------------------- #
def parse_number(text, name='数'):
    """把文本解析成精确数值（分数用 sympy.Rational）。"""
    text = normalize(text)
    if not text:
        raise CalcError('请填写“%s”。' % name)
    try:
        value = parse_expr(text, local_dict={'pi': pi, 'sqrt': sqrt},
                           transformations=_TRANSFORMS, evaluate=True)
    except Exception:
        raise CalcError('“%s”不是有效的数字，请重新填写“%s”。' % (text, name))
    if getattr(value, 'free_symbols', None) or not getattr(value, 'is_number', False):
        raise CalcError('“%s”不是有效的数字，请重新填写“%s”。' % (text, name))
    return value


def parse_fraction(text, name='数'):
    """解析分数或小数，如 3/4、0.75、2。"""
    text = normalize(text)
    if not text:
        raise CalcError('请填写“%s”。' % name)
    try:
        value = parse_expr(text, local_dict={'pi': pi, 'sqrt': sqrt},
                           transformations=_TRANSFORMS, evaluate=True)
    except Exception:
        raise CalcError('“%s”不是有效的分数，请写成 3/4 或 0.75 的形式。' % text)
    if getattr(value, 'free_symbols', None) or not getattr(value, 'is_number', False):
        raise CalcError('“%s”不是有效的分数，请写成 3/4 或 0.75 的形式。' % text)
    return value


def parse_int(text, name='整数'):
    text = normalize(text)
    if not text:
        raise CalcError('请填写“%s”。' % name)
    try:
        return int(text)
    except ValueError:
        raise CalcError('“%s”不是整数，请填写“%s”。' % (text, name))


def format_decimal(value, ndigits=6):
    """把浮点数格式化成简洁的小数字符串。"""
    if not math.isfinite(value):
        return str(value)
    if value == 0:
        return '0'
    rounded = round(value, ndigits)
    if rounded == 0:
        return '%.*g' % (ndigits, value)
    if abs(rounded) < 1e15 and rounded == int(rounded):
        return str(int(rounded))
    return ('%.*f' % (ndigits, rounded)).rstrip('0').rstrip('.')


def format_exact(value, ndigits=6):
    """精确显示：整数原样、分数显示 a/b、无理数显示小数。"""
    value = sympify_number(value)
    if value.is_Integer:
        return str(int(value))
    if value.is_Rational:
        if value.q == 1:
            return str(int(value.p))
        return '%d/%d' % (value.p, value.q)
    return format_decimal(float(value), ndigits)


def format_result(value, ndigits=6):
    """计算结果：分数同时给出小数，便于对照。"""
    value = sympify_number(value)
    if value.is_Rational and value.q != 1:
        return '%s（≈ %s）' % (format_exact(value), format_decimal(float(value), ndigits))
    return format_exact(value, ndigits)


def sympify_number(value):
    from sympy import sympify
    return sympify(value)


def format_geometry(value, ndigits=4):
    """几何结果：含 π 的保留 π 形式并附上近似值。"""
    value = sympify_number(value)
    if getattr(value, 'has', None) and value.has(pi):
        return '%s ≈ %s' % (pretty_symbolic(value), format_decimal(float(value), ndigits))
    if value.is_Rational:
        return format_decimal(float(value), ndigits)
    try:
        return format_decimal(float(value), ndigits)
    except (TypeError, ValueError):
        return str(value)


def pretty_symbolic(value):
    """把 sympy 表达式显示成适合阅读的样子。"""
    text = str(value)
    text = text.replace('**2', '²').replace('**3', '³').replace('**', '^')
    text = text.replace('*', '×').replace('pi', 'π').replace('sqrt', '√')
    return text


def format_expression_result(value, source_text):
    """按输入形式决定输出：写小数就回小数，写分数/整数就给精确值。"""
    source = normalize(source_text)
    if '.' in source and '/' not in source:
        return format_decimal(float(value))
    return format_result(value)


# --------------------------------------------------------------------------- #
# 1. 算式计算
# --------------------------------------------------------------------------- #
def evaluate_expression(text):
    """计算一个完整的算式，如 3+5*2-(4/2)。"""
    expression = normalize(text)
    if not expression:
        raise CalcError('请输入要计算的算式。')
    try:
        result = parse_expr(expression, local_dict={'pi': pi, 'sqrt': sqrt},
                            transformations=_TRANSFORMS, evaluate=True)
    except Exception:
        raise CalcError('看不懂这个算式：“%s”，请检查运算符和括号。' % text.strip())
    if getattr(result, 'free_symbols', None):
        names = '、'.join(sorted(str(s) for s in result.free_symbols))
        raise CalcError('算式里有未知的字母：%s' % names)
    if not getattr(result, 'is_number', False):
        raise CalcError('这个算式算不出一个数字，请检查。')
    return result


# --------------------------------------------------------------------------- #
# 2. 分数运算
# --------------------------------------------------------------------------- #
FRACTION_OPS = ['+', '−', '×', '÷']


def fraction_operate(a_text, op, b_text):
    first = parse_fraction(a_text, '第一个数')
    second = parse_fraction(b_text, '第二个数')
    if op == '+':
        return first + second
    if op == '−' or op == '-':
        return first - second
    if op == '×' or op == '*':
        return first * second
    if op == '÷' or op == '/':
        if second == 0:
            raise CalcError('除数不能为 0。')
        return first / second
    raise CalcError('不支持的运算：%s' % op)


# --------------------------------------------------------------------------- #
# 3. 因数与倍数
# --------------------------------------------------------------------------- #
def parse_int_list(text, name='整数'):
    text = normalize(text)
    if not text:
        raise CalcError('请填写“%s”。' % name)
    parts = [p for p in re.split(r'[,\s]+', text) if p]
    values = []
    for part in parts:
        try:
            value = int(part)
        except ValueError:
            raise CalcError('“%s”不是整数，请用逗号分隔整数。' % part)
        if value == 0:
            raise CalcError('0 不能参与因数与倍数的计算。')
        values.append(value)
    return values


def prime_factorization(text):
    """质因数分解，如 12 → 2²×3。"""
    number = abs(parse_int(text, '整数'))
    if number < 2:
        raise CalcError('请填写一个大于 1 的整数。')
    factors = factorint(number)
    parts = []
    for prime in sorted(factors):
        exponent = factors[prime]
        if exponent > 1:
            parts.append('%d^%d' % (prime, exponent))
        else:
            parts.append('%d' % prime)
    return ' × '.join(parts).replace('^2', '²').replace('^3', '³')


def greatest_common_divisor(text):
    values = parse_int_list(text)
    if len(values) < 2:
        raise CalcError('请至少输入两个整数。')
    result = values[0]
    for value in values[1:]:
        result = sym_gcd(result, value)
    return result


def least_common_multiple(text):
    values = parse_int_list(text)
    if len(values) < 2:
        raise CalcError('请至少输入两个整数。')
    try:
        return ilcm(*values)
    except Exception:
        raise CalcError('这些数太大了，算不出来。')


# --------------------------------------------------------------------------- #
# 4. 乘方 / 开方 / 带余除法
# --------------------------------------------------------------------------- #
def power(base_text, exponent_text):
    base = parse_fraction(base_text, '底数')
    exponent = parse_int(exponent_text, '指数')
    if abs(exponent) > 300:
        raise CalcError('指数太大了，请换一个小一点的数。')
    if base == 0 and exponent < 0:
        raise CalcError('0 不能做负指数。')
    return base ** exponent


def square_root(text):
    value = parse_fraction(text, '被开方数')
    if value < 0:
        raise CalcError('负数不能开平方。')
    return sqrt(value)


def division_with_remainder(a_text, b_text):
    dividend = parse_int(a_text, '被除数')
    divisor = parse_int(b_text, '除数')
    if divisor == 0:
        raise CalcError('除数不能为 0。')
    quotient, remainder = divmod(dividend, divisor)
    return quotient, remainder


# --------------------------------------------------------------------------- #
# 5. 百分数
# --------------------------------------------------------------------------- #
def percent_of(a_text, percent_text):
    """A 的 B% 是多少。"""
    value = parse_fraction(a_text, '数值')
    percent = parse_fraction(percent_text, '百分数')
    return value * percent / 100


def percent_ratio(a_text, b_text):
    """A 是 B 的百分之几。"""
    a = parse_fraction(a_text, '第一个数')
    b = parse_fraction(b_text, '第二个数')
    if b == 0:
        raise CalcError('第二个数不能为 0。')
    return a / b * 100


# --------------------------------------------------------------------------- #
# 6. 单位换算
# --------------------------------------------------------------------------- #
# 每个单位的换算系数，都是相对于该类别基准单位的倍数
UNIT_TABLE = {
    '长度': {'毫米': 0.001, '厘米': 0.01, '分米': 0.1, '米': 1, '千米': 1000},
    '面积': {'平方厘米': 0.0001, '平方分米': 0.01, '平方米': 1,
             '公顷': 10000, '平方千米': 1000000, '亩': 10000 / 15},
    '体积与容积': {'毫升': 1e-6, '立方厘米': 1e-6, '升': 0.001,
                   '立方分米': 0.001, '立方米': 1},
    '质量': {'克': 0.001, '千克': 1, '吨': 1000},
    '时间': {'秒': 1, '分': 60, '小时': 3600, '天': 86400},
    '人民币': {'分': 0.01, '角': 0.1, '元': 1},
}

TEMPERATURE_UNITS = ['摄氏度', '华氏度', '开尔文']


def unit_categories():
    """返回所有换算类别（温度放在最后）。"""
    return list(UNIT_TABLE.keys()) + ['温度']


def units_of(category):
    if category == '温度':
        return list(TEMPERATURE_UNITS)
    return list(UNIT_TABLE.get(category, {}))


def _temperature_to_celsius(value, unit):
    if unit == '摄氏度':
        return value
    if unit == '华氏度':
        return (value - 32) * 5 / 9
    if unit == '开尔文':
        return value - 273.15
    raise CalcError('不支持的温度单位：%s' % unit)


def _celsius_to_temperature(value, unit):
    if unit == '摄氏度':
        return value
    if unit == '华氏度':
        return value * 9 / 5 + 32
    if unit == '开尔文':
        return value + 273.15
    raise CalcError('不支持的温度单位：%s' % unit)


def convert_unit(category, value_text, from_unit, to_unit):
    value = float(parse_number(value_text, '数值'))
    if category == '温度':
        celsius = _temperature_to_celsius(value, from_unit)
        return _celsius_to_temperature(celsius, to_unit)
    table = UNIT_TABLE.get(category)
    if not table:
        raise CalcError('不支持的换算类别：%s' % category)
    if from_unit not in table or to_unit not in table:
        raise CalcError('不支持的单位。')
    return value * table[from_unit] / table[to_unit]


# --------------------------------------------------------------------------- #
# 7. 几何计算
# --------------------------------------------------------------------------- #
def _positive(params, key, label):
    value = parse_fraction(params.get(key, ''), label)
    if value <= 0:
        raise CalcError('“%s”必须大于 0。' % label)
    return value


def _rectangle(p):
    a, b = _positive(p, 'a', '长'), _positive(p, 'b', '宽')
    return [('面积', a * b), ('周长', 2 * (a + b))]


def _square(p):
    a = _positive(p, 'a', '边长')
    return [('面积', a ** 2), ('周长', 4 * a)]


def _triangle(p):
    a, h = _positive(p, 'a', '底'), _positive(p, 'h', '高')
    return [('面积', a * h / 2)]


def _parallelogram(p):
    a, h = _positive(p, 'a', '底'), _positive(p, 'h', '高')
    return [('面积', a * h)]


def _trapezoid(p):
    a, b, h = _positive(p, 'a', '上底'), _positive(p, 'b', '下底'), _positive(p, 'h', '高')
    return [('面积', (a + b) * h / 2)]


def _circle(p):
    r = _positive(p, 'r', '半径')
    return [('面积', pi * r ** 2), ('周长', 2 * pi * r)]


def _cuboid(p):
    a, b, c = _positive(p, 'a', '长'), _positive(p, 'b', '宽'), _positive(p, 'c', '高')
    return [('体积', a * b * c), ('表面积', 2 * (a * b + b * c + a * c))]


def _cube(p):
    a = _positive(p, 'a', '棱长')
    return [('体积', a ** 3), ('表面积', 6 * a ** 2)]


def _cylinder(p):
    r, h = _positive(p, 'r', '底面半径'), _positive(p, 'h', '高')
    return [('体积', pi * r ** 2 * h),
            ('侧面积', 2 * pi * r * h),
            ('表面积', 2 * pi * r ** 2 + 2 * pi * r * h)]


def _cone(p):
    r, h = _positive(p, 'r', '底面半径'), _positive(p, 'h', '高')
    return [('体积', pi * r ** 2 * h / 3)]


GEOMETRY_SHAPES = [
    {'name': '长方形', 'group': '平面图形',
     'params': [('a', '长'), ('b', '宽')], 'func': _rectangle},
    {'name': '正方形', 'group': '平面图形',
     'params': [('a', '边长')], 'func': _square},
    {'name': '三角形', 'group': '平面图形',
     'params': [('a', '底'), ('h', '高')], 'func': _triangle},
    {'name': '平行四边形', 'group': '平面图形',
     'params': [('a', '底'), ('h', '高')], 'func': _parallelogram},
    {'name': '梯形', 'group': '平面图形',
     'params': [('a', '上底'), ('b', '下底'), ('h', '高')], 'func': _trapezoid},
    {'name': '圆', 'group': '平面图形',
     'params': [('r', '半径')], 'func': _circle},
    {'name': '长方体', 'group': '立体图形',
     'params': [('a', '长'), ('b', '宽'), ('c', '高')], 'func': _cuboid},
    {'name': '正方体', 'group': '立体图形',
     'params': [('a', '棱长')], 'func': _cube},
    {'name': '圆柱', 'group': '立体图形',
     'params': [('r', '底面半径'), ('h', '高')], 'func': _cylinder},
    {'name': '圆锥', 'group': '立体图形',
     'params': [('r', '底面半径'), ('h', '高')], 'func': _cone},
]


def geometry_shape_names():
    return [shape['name'] for shape in GEOMETRY_SHAPES]


def geometry_params(shape_name):
    shape = _find_shape(shape_name)
    return list(shape['params'])


def _find_shape(shape_name):
    for shape in GEOMETRY_SHAPES:
        if shape['name'] == shape_name:
            return shape
    raise CalcError('不支持的图形：%s' % shape_name)


def geometry_calculate(shape_name, raw_params):
    shape = _find_shape(shape_name)
    return shape['func'](dict(raw_params))


# --------------------------------------------------------------------------- #
# 8. 一元方程
# --------------------------------------------------------------------------- #
def solve_equation(text):
    """求解一元方程，返回可直接显示的字符串。"""
    expression = normalize(text)
    if not expression:
        raise CalcError('请先输入要解的方程。')

    try:
        if '=' in expression:
            left, right = expression.split('=', 1)
            lhs = parse_expr(left, local_dict={'x': x}, transformations=_TRANSFORMS)
            rhs = parse_expr(right, local_dict={'x': x}, transformations=_TRANSFORMS)
        else:
            lhs = parse_expr(expression, local_dict={'x': x}, transformations=_TRANSFORMS)
            rhs = 0
    except Exception:
        raise CalcError('看不懂这个方程：“%s”，请检查括号和运算符。' % text.strip())

    symbols = set(getattr(lhs, 'free_symbols', set())) | set(getattr(rhs, 'free_symbols', set()))
    if x not in symbols:
        raise CalcError('方程里没有找到未知数 x，请检查输入。')

    # 一律移到一边：左边 - 右边 = 0。
    # 注意不能用 Eq(...)，否则 sympy 会把 x+1 = x+2 直接化归成 False，丢掉未知数。
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
        raise CalcError('这个方程比较复杂，暂时解不出来。')

    if not solutions:
        return '无解'
    return '，'.join('x = %s' % format_exact(item) for item in solutions)
