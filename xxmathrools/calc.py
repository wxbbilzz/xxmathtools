#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小学数学工具 —— 计算逻辑层。

本模块不依赖 Qt，可以脱离界面单独测试。

包含：
    算式计算与分步计算、简便算法提示、竖式演示
    分数四则运算、约分与通分、分数小数百分数互转
    因数与倍数、质数与奇偶、数的认识（近似数与改写）、平均数
    比与比例（解比例、按比分配）
    乘方 / 开方 / 带余除法
    单位换算与复名数互化、时刻与日期
    平面与立体图形的几何计算、三角形判定
    一元方程求解与分步求解

界面上的「计算设置」面板改的就是本模块顶部的 SETTINGS 字典。
"""

import datetime
import math
import re
from collections import Counter
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, localcontext
from fractions import Fraction

from sympy import (
    Poly,
    Rational,
    acos,
    asin,
    atan,
    cbrt,
    cos,
    divisors,
    exp,
    expand,
    factorint,
    ilcm,
    isprime,
    ln,
    log,
    oo,
    pi,
    primerange,
    simplify,
    sin,
    solve,
    sqrt,
    sympify,
    tan,
    zoo,
)
from sympy import gcd as sym_gcd
from sympy import factorial as sym_factorial
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
# 计算设置（界面上的「计算设置」面板会直接改这里）
# --------------------------------------------------------------------------- #
PI_MODES = ['精确值 π', '取 3.14']
ROUND_MODES = ['四舍五入', '进一法', '去尾法']
DECIMAL_CHOICES = [0, 1, 2, 3, 4, 6]
GEOMETRY_UNITS = ['无单位', '毫米', '厘米', '分米', '米', '千米']

SETTINGS = {
    'pi_mode': PI_MODES[0],      # 几何计算里圆周率怎么取值
    'decimals': 2,               # 保留几位小数
    'round_mode': ROUND_MODES[0],  # 保留小数时怎么取整
    'mixed_number': True,        # 假分数是否显示成带分数
    'show_unit': True,           # 几何结果是否带单位
}


def reset_settings():
    """把设置恢复成默认值。"""
    SETTINGS.update(pi_mode=PI_MODES[0], decimals=2, round_mode=ROUND_MODES[0],
                    mixed_number=True, show_unit=True)


# --------------------------------------------------------------------------- #
# 文本预处理
# --------------------------------------------------------------------------- #
# 全角 → 半角，中文运算符 → 英文运算符
_TABLE = {chr(0xFF10 + i): str(i) for i in range(10)}
_TABLE.update({
    '（': '(', '）': ')', '＝': '=', '＋': '+', '－': '-', '−': '-', '—': '-',
    '×': '*', '÷': '/', '＾': '^', '．': '.', '，': ',', '、': ',',
    '　': ' ', 'ｘ': 'x', 'Ｘ': 'x', '％': '%', '：': ':', '∶': ':',
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
# 数值解析
# --------------------------------------------------------------------------- #
def _parse_value(text, name, kind):
    source = normalize(text)
    if not source:
        raise CalcError('请填写“%s”。' % name)
    try:
        value = parse_expr(source, local_dict={'pi': pi, 'sqrt': sqrt},
                           transformations=_TRANSFORMS, evaluate=True)
    except ZeroDivisionError:
        raise CalcError('“%s”里出现了除以 0。' % source)
    except Exception:
        raise CalcError('“%s”不是有效的%s，请重新填写“%s”。' % (source, kind, name))
    if getattr(value, 'is_infinite', False):
        raise CalcError('“%s”算不出有限的数，请检查有没有除以 0。' % source)
    if getattr(value, 'free_symbols', None) or not getattr(value, 'is_number', False):
        raise CalcError('“%s”不是有效的%s，请重新填写“%s”。' % (source, kind, name))
    return value


def parse_number(text, name='数'):
    """把文本解析成精确数值（分数用 sympy.Rational）。"""
    return _parse_value(text, name, '数字')


def parse_fraction(text, name='数'):
    """解析分数或小数，如 3/4、0.75、2。"""
    return _parse_value(text, name, '分数')


def parse_int(text, name='整数'):
    source = normalize(text)
    if not source:
        raise CalcError('请填写“%s”。' % name)
    try:
        return int(source)
    except ValueError:
        raise CalcError('“%s”不是整数，请填写“%s”。' % (source, name))


def parse_int_list(text, name='整数'):
    source = normalize(text)
    if not source:
        raise CalcError('请填写“%s”。' % name)
    parts = [p for p in re.split(r'[,\s]+', source) if p]
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


def parse_number_list(text, name='数据'):
    """解析用逗号或空格分隔的一串数，支持小数和分数。"""
    source = normalize(text)
    if not source:
        raise CalcError('请填写“%s”。' % name)
    parts = [p for p in re.split(r'[,\s]+', source) if p]
    if not parts:
        raise CalcError('请填写“%s”。' % name)
    return [parse_fraction(p, name) for p in parts]


# --------------------------------------------------------------------------- #
# 数值显示
# --------------------------------------------------------------------------- #
def sympify_number(value):
    return sympify(value)


def round_number(value, ndigits, mode=None):
    """按指定方式把数值保留 ndigits 位小数，返回 Decimal。"""
    mode = mode or SETTINGS['round_mode']
    rounding = {'四舍五入': ROUND_HALF_UP,
                '进一法': ROUND_CEILING,
                '去尾法': ROUND_FLOOR}[mode]
    quantum = Decimal(1).scaleb(-ndigits)
    with localcontext() as ctx:
        ctx.prec = 60
        return Decimal(str(float(value))).quantize(quantum, rounding=rounding)


def format_decimal(value, ndigits=None, mode=None):
    """把数值格式化成简洁的小数字符串。"""
    value = float(value)
    if not math.isfinite(value):
        return str(value)
    if value == 0:
        return '0'
    ndigits = SETTINGS['decimals'] if ndigits is None else ndigits
    rounded = round_number(value, ndigits, mode)
    if rounded == 0:
        # 位数不够，改用有效数字，避免 0.001 被显示成 0.00
        return ('%.*g' % (max(ndigits, 6), value)).replace('e+', '×10^').replace('e-', '×10^-')
    text = '%.*f' % (ndigits, rounded)
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


def format_exact(value, ndigits=None):
    """精确显示：整数原样、分数显示 a/b 或带分数、无理数显示小数。"""
    value = sympify_number(value)
    if value.is_Integer:
        return str(int(value))
    if value.is_Rational:
        numerator, denominator = value.p, value.q
        if denominator == 1:
            return str(numerator)
        if SETTINGS['mixed_number'] and abs(numerator) > denominator:
            whole, remainder = divmod(abs(numerator), denominator)
            sign = '-' if numerator < 0 else ''
            return '%s%d又%d/%d' % (sign, whole, remainder, denominator)
        return '%d/%d' % (numerator, denominator)
    return format_decimal(float(value), ndigits)


def format_result(value, ndigits=None):
    """计算结果：分数同时给出小数，便于对照。"""
    value = sympify_number(value)
    if value.is_Rational and value.q != 1:
        return '%s（≈ %s）' % (format_exact(value), format_decimal(float(value), ndigits))
    return format_exact(value, ndigits)


def format_expression_result(value, source_text):
    """按输入形式决定输出：写小数就回小数，写分数/整数就给精确值。"""
    source = normalize(source_text)
    if '.' in source and '/' not in source:
        return format_decimal(float(value))
    return format_result(value)


def pretty_symbolic(value):
    """把 sympy 表达式显示成适合阅读的样子。"""
    text = str(value)
    text = text.replace('**2', '²').replace('**3', '³').replace('**', '^')
    text = text.replace('*', '×').replace('pi', 'π').replace('sqrt', '√')
    return text


def _term_text(value):
    """算式分步显示用：2*x → 2x。"""
    text = str(value)
    text = text.replace('**', '^')
    text = text.replace('*x', 'x')
    text = text.replace('*', '×')
    text = text.replace('pi', 'π')
    return text


def unit_suffix(unit, dimension=''):
    """几何结果的单位后缀：长度 → 厘米，面积 → 平方厘米，体积 → 立方厘米。"""
    unit = (unit or '').strip()
    if not unit or unit == GEOMETRY_UNITS[0] or not SETTINGS['show_unit']:
        return ''
    if dimension in ('area', 'surface', 'lateral'):
        return '平方' + unit
    if dimension == 'volume':
        return '立方' + unit
    return unit


def format_geometry(value, dimension='', unit=''):
    """几何结果：含 π 的保留 π 形式并附上近似值。"""
    value = sympify_number(value)
    has_pi = bool(getattr(value, 'has', None)) and value.has(pi)
    if has_pi and SETTINGS['pi_mode'] == PI_MODES[1]:
        numeric = value.subs(pi, Rational(314, 100))
        text = '%s = %s' % (pretty_symbolic(value).replace('π', '3.14'),
                            format_decimal(float(numeric)))
    elif has_pi:
        text = '%s ≈ %s' % (pretty_symbolic(value), format_decimal(float(value)))
    else:
        try:
            text = format_decimal(float(value))
        except (TypeError, ValueError):
            text = str(value)
    suffix = unit_suffix(unit, dimension)
    return '%s %s' % (text, suffix) if suffix else text


# --------------------------------------------------------------------------- #
# 1. 算式计算 / 分步计算 / 简便算法
# --------------------------------------------------------------------------- #
def evaluate_expression(text):
    """计算一个完整的算式，如 3+5*2-(4/2)。"""
    expression = normalize(text)
    if not expression:
        raise CalcError('请输入要计算的算式。')
    try:
        result = parse_expr(expression, local_dict={'pi': pi, 'sqrt': sqrt},
                            transformations=_TRANSFORMS, evaluate=True)
    except ZeroDivisionError:
        raise CalcError('算式里有除以 0 的地方，除数不能为 0。')
    except Exception:
        raise CalcError('看不懂这个算式：“%s”，请检查运算符和括号。' % text.strip())
    if getattr(result, 'is_infinite', False) or result in (oo, -oo, zoo):
        raise CalcError('算式里有除以 0 的地方，除数不能为 0。')
    if getattr(result, 'free_symbols', None):
        names = '、'.join(sorted(str(s) for s in result.free_symbols))
        raise CalcError('算式里有未知的字母：%s' % names)
    if not getattr(result, 'is_number', False):
        raise CalcError('这个算式算不出一个数字，请检查。')
    return result


ANGLE_MODES = ['角度', '弧度']


def _calculator_local_dict(angle_mode):
    """科学计算器用的函数表。角度模式下三角函数按「度」来算。"""
    if angle_mode == ANGLE_MODES[0]:
        degree = pi / 180
        return {
            'pi': pi, 'e': exp(1), 'sqrt': sqrt, 'cbrt': cbrt,
            'sin': lambda v: sin(v * degree),
            'cos': lambda v: cos(v * degree),
            'tan': lambda v: tan(v * degree),
            'asin': lambda v: asin(v) / degree,
            'acos': lambda v: acos(v) / degree,
            'atan': lambda v: atan(v) / degree,
            'log': lambda v: log(v, 10),
            'ln': ln, 'exp': exp, 'factorial': sym_factorial,
        }
    return {
        'pi': pi, 'e': exp(1), 'sqrt': sqrt, 'cbrt': cbrt,
        'sin': sin, 'cos': cos, 'tan': tan,
        'asin': asin, 'acos': acos, 'atan': atan,
        'log': lambda v: log(v, 10), 'ln': ln, 'exp': exp,
        'factorial': sym_factorial,
    }


_MAX_RESULT_DIGITS = 50000   # 结果最多约 5 万位
_MAX_RESULT_BITS = 170000    # 对应的二进制位数，用来快速判断整数大小
_HUGE_LIMIT = 10 ** 50       # 结果绝对值上限，超过就报错（也防止格式化大数时崩溃）


def _guard_against_huge(expression):
    """在真正计算前拦截会爆炸的超大数（超大乘方、阶乘）。"""
    # 乘方套乘方（如 2^3^4）会瞬间爆炸，直接拒绝
    if re.search(r'\*\*[^()]*\*\*', expression):
        raise CalcError('乘方套乘方（如 2^3^4）数字会瞬间爆炸，请用括号写清楚。')
    # 显式数字的乘方：估算结果位数，超限提前拦下
    for match in re.finditer(r'(\d+(?:\.\d+)?)\s*\*\*\s*\(?\s*(\d+(?:\.\d+)?)', expression):
        base = float(match.group(1))
        exponent = float(match.group(2))
        if base == 0 and exponent < 0:
            raise CalcError('0 不能做负指数。')
        if base > 1 and exponent > 0 and exponent * math.log10(base) > _MAX_RESULT_DIGITS:
            raise CalcError('数字太大了（乘方结果超过 %d 位），请换小一点的数。'
                            % _MAX_RESULT_DIGITS)
    # 阶乘参数过大
    for match in re.finditer(r'factorial\s*\(\s*(\d+)\s*\)', expression):
        if int(match.group(1)) > 20000:
            raise CalcError('阶乘的数字太大了，请换一个不大于 20000 的数。')


def evaluate_calculator(text, angle_mode='角度'):
    """计算器引擎：四则运算、括号、乘方、开方、三角、对数、指数、阶乘、百分数等。"""
    expression = normalize(text)
    if not expression:
        raise CalcError('请输入要计算的算式。')
    # 紧跟数字的 % 当作除以 100，如 50% → (50/100)
    expression = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1/100)', expression)
    _guard_against_huge(expression)
    try:
        result = parse_expr(expression, local_dict=_calculator_local_dict(angle_mode),
                            transformations=_TRANSFORMS, evaluate=True)
    except ZeroDivisionError:
        raise CalcError('算式里有除以 0 的地方。')
    except CalcError:
        raise
    except Exception:
        raise CalcError('看不懂这个算式：“%s”，请检查运算符和括号。' % text.strip())
    if getattr(result, 'is_infinite', False) or result in (oo, -oo, zoo):
        raise CalcError('结果太大或算不出来（例如 tan 90°），请检查算式。')
    if getattr(result, 'is_real', True) is False:
        raise CalcError('结果是虚数（例如负数开平方），这个计算器暂不支持。')
    if getattr(result, 'is_number', False) and abs(result) > _HUGE_LIMIT:
        raise CalcError('结果太大了（绝对值超过 1e50），请换小一点的数。')
    if getattr(result, 'free_symbols', None):
        names = '、'.join(sorted(str(s) for s in result.free_symbols))
        raise CalcError('算式里有未知的字母：%s' % names)
    if not getattr(result, 'is_number', False):
        raise CalcError('这个算式算不出一个数字，请检查。')
    return result


# ---- 小学算式的分词与语法树 ----
# 分步计算和简便算法都建立在这里自建的语法树上，而不是 sympy 的表达式树上。
# sympy 的未求值表达式会重排项序、还会把减法变成负数项，
# 3+5×2-(4÷2) 会显示成「-4/2 + 3 + 10」这种样子，小学生根本读不懂。
# 自己建树就能原样保留用户写的 × ÷ 和括号顺序。
_DISPLAY_TABLE = {key: value for key, value in _TABLE.items() if key not in ('×', '÷')}
_DISPLAY_TRANSLATE = str.maketrans(_DISPLAY_TABLE)

_NUMBER_RE = re.compile(r'\d+(?:\.\d+)?')

# 每一步的优先级，越大越先算
_PRECEDENCE = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3, 'neg': 3, 'sqrt': 4, 'group': 0}

# 这两种节点只用来「脱括号」「取负号」，本身不作为一步显示出来
_INVISIBLE_STEPS = ('group', 'neg')


def normalize_display(text):
    """分步显示用：只做全角转换，保留 × ÷ ^ √ π 这些写法。"""
    return re.sub(r'\s+', '', text.translate(_DISPLAY_TRANSLATE))


class _Node(object):
    """算式语法树的一个节点。

    op 为空表示这是一个数；否则 op 是运算符，
    text 是这个节点在原始算式里对应的那一段文字。
    """

    __slots__ = ('op', 'left', 'right', 'text', 'start', 'end', 'value')

    def __init__(self, op=None, left=None, right=None, text='', start=0, end=0, value=None):
        self.op = op
        self.left = left
        self.right = right
        self.text = text
        self.start = start
        self.end = end
        self.value = value

    @property
    def is_leaf(self):
        return self.op is None

    def children(self):
        return [child for child in (self.left, self.right) if child is not None]


def _tokenize(source):
    """把算式拆成记号。"""
    tokens = []
    index = 0
    while index < len(source):
        char = source[index]
        match = _NUMBER_RE.match(source, index)
        if match:
            tokens.append(('number', match.group(), index, match.end()))
            index = match.end()
            continue
        if source.startswith('sqrt', index):
            tokens.append(('name', 'sqrt', index, index + 4))
            index += 4
            continue
        if source.startswith('pi', index):
            tokens.append(('name', 'pi', index, index + 2))
            index += 2
            continue
        if source.startswith('**', index):
            tokens.append(('op', '^', index, index + 2))
            index += 2
            continue
        if char == 'π':
            tokens.append(('name', 'pi', index, index + 1))
            index += 1
            continue
        if char == '√':
            tokens.append(('name', 'sqrt', index, index + 1))
            index += 1
            continue
        if char == '×':
            tokens.append(('op', '*', index, index + 1))
            index += 1
            continue
        if char == '÷':
            tokens.append(('op', '/', index, index + 1))
            index += 1
            continue
        if char in '+-*/^()':
            tokens.append(('op', char, index, index + 1))
            index += 1
            continue
        raise CalcError('算式里有看不懂的符号：“%s”。' % char)
    return tokens


class _Parser(object):
    """递归下降：先乘除后加减，同级从左到右，乘方右结合。"""

    def __init__(self, source, tokens):
        self.source = source
        self.tokens = tokens
        self.position = 0

    def parse(self):
        node = self._expression()
        if self.position != len(self.tokens):
            raise CalcError('算式里有看不懂的地方：“%s”。' % self.source)
        return node

    # -- 内部方法 -------------------------------------------------------- #
    def _peek(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def _peek_operator(self):
        token = self._peek()
        if token is not None and token[0] == 'op':
            return token[1]
        return None

    def _next(self):
        token = self.tokens[self.position]
        self.position += 1
        return token

    def _join(self, operator, left, right):
        return _Node(operator, left, right, self.source[left.start:right.end],
                     left.start, right.end)

    def _expression(self):
        node = self._term()
        while self._peek_operator() in ('+', '-'):
            operator = self._next()[1]
            node = self._join(operator, node, self._term())
        return node

    def _term(self):
        node = self._factor()
        while self._peek_operator() in ('*', '/'):
            operator = self._next()[1]
            node = self._join(operator, node, self._factor())
        return node

    def _factor(self):
        node = self._unary()
        if self._peek_operator() == '^':
            self._next()
            node = self._join('^', node, self._factor())  # 乘方右结合
        return node

    def _unary(self):
        operator = self._peek_operator()
        if operator == '+':
            self._next()
            return self._unary()
        if operator == '-':
            token = self._next()
            operand = self._unary()
            text = self.source[token[2]:operand.end]
            if operand.is_leaf:
                # -5 直接并进数字里，免得后面多出一个「-5 = -5」的步骤
                return _Node(None, None, None, text, token[2], operand.end, -operand.value)
            return _Node('neg', operand, None, text, token[2], operand.end)
        return self._primary()

    def _primary(self):
        token = self._peek()
        if token is None:
            raise CalcError('算式不完整，请检查。')
        kind, value, start, end = token
        if kind == 'number':
            self._next()
            return _Node(None, None, None, value, start, end, parse_number(value))
        if kind == 'name':
            self._next()
            if value == 'pi':
                return _Node(None, None, None, self.source[start:end], start, end, pi)
            inner = self._primary()
            return _Node('sqrt', inner, None,
                         self.source[start:inner.end], start, inner.end)
        if kind == 'op' and value == '(':
            self._next()
            inner = self._expression()
            closing = self._peek()
            if closing is None or closing[1] != ')':
                raise CalcError('算式里的括号没有配对。')
            self._next()
            return _Node('group', inner, None,
                         self.source[start:closing[3]], start, closing[3])
        raise CalcError('算式里有看不懂的地方：“%s”。' % value)


def _parse_expression(source):
    tokens = _tokenize(source)
    if not tokens:
        raise CalcError('请输入要计算的算式。')
    return _Parser(source, tokens).parse()


def _node_value(node):
    """算出一段算式（节点）的数值。"""
    return evaluate_expression(node.text)


def _flatten(node, operators):
    """把 a×b×c 这种同级运算展平成操作数列表。"""
    if node.op in operators:
        return _flatten(node.left, operators) + _flatten(node.right, operators)
    return [node]


def _unwrap(node):
    """去掉多余的括号节点。"""
    while node.op == 'group':
        node = node.left
    return node


def _all_number(node):
    children = node.children()
    return bool(children) and all(child.is_leaf for child in children)


def _ready_nodes(node, found):
    """收集所有「操作数都已经是数、可以马上算」的节点。"""
    if node.is_leaf:
        return
    if _all_number(node):
        found.append(node)
        return
    for child in node.children():
        _ready_nodes(child, found)


def _format_step_value(value):
    """插回算式里的数值：分数写成 a/b，不用带分数，否则没法继续往下算。"""
    value = sympify_number(value)
    if value.is_Integer:
        return str(int(value))
    if value.is_Rational:
        return '%d/%d' % (value.p, value.q)
    return format_decimal(float(value), 6)


def expression_steps(text):
    """按运算顺序分步计算，返回 (步骤列表, 最终结果)。

    步骤是 (这一步的式子, 这一步的结果, 走完这一步之后的算式)。
    """
    source = normalize_display(text)
    if not source:
        raise CalcError('请输入要计算的算式。')
    result = evaluate_expression(text)
    current = _parse_expression(source)

    steps = []
    for _ in range(200):        # 兜底，避免死循环
        if current.is_leaf:
            break
        found = []
        _ready_nodes(current, found)
        if not found:
            break
        # 优先级高的先算，同级里取最左边那一个
        node = max(found, key=lambda item: (_PRECEDENCE.get(item.op, 0), -item.start))
        replacement = _format_step_value(_node_value(node))
        new_source = _strip_redundant_parentheses(
            source[:node.start] + replacement + source[node.end:])
        if new_source == source:
            break
        if node.op not in _INVISIBLE_STEPS:
            steps.append((node.text, replacement, new_source))
        source = new_source
        current = _parse_expression(source)
    return steps, result


def _integer_of(value):
    """整数就返回 int，否则返回 None。"""
    value = sympify_number(value)
    if value.is_Integer:
        return int(value)
    return None


def _is_round(value):
    """判断是不是 10、100、1000 这种「整十整百」，用来提示凑整。

    注意 1530 这样能被 10 整除但不是整十的数不算，否则会给出一堆没用的提示。
    """
    number = _integer_of(value)
    if number is None:
        return False
    text = str(abs(number))
    return len(text) >= 2 and text.rstrip('0') == text[0]


# 只包着一个数字的括号，算完就可以去掉了
_SINGLE_NUMBER_RE = re.compile(r'\((\d+(?:\.\d+)?(?:/\d+)?)\)')


def _strip_redundant_parentheses(source):
    """把 3+10-(2) 里的括号去掉，写成 3+10-2。"""
    previous = None
    while previous != source:
        previous = source
        source = _SINGLE_NUMBER_RE.sub(r'\1', source)
    return source


def _signed_terms(node):
    """把加减链展平成 (正负号, 节点) 列表，用来正确写出分配律的展开。"""
    if node.op == '+':
        return _signed_terms(node.left) + _signed_terms(node.right)
    if node.op == '-':
        return _signed_terms(node.left) + [(-sign, item)
                                           for sign, item in _signed_terms(node.right)]
    return [(1, node)]


def simplify_advice(text):
    """给出简便算法的提示，返回文本列表。"""
    source = normalize_display(text)
    if not source:
        raise CalcError('请输入要计算的算式。')
    node = _parse_expression(source)
    total = evaluate_expression(text)
    tips = []

    # 拆数凑整：把因数拆成「整十整百 ± 小数」，例如 102×15 = (100+2)×15
    if node.op == '*':
        operands = _flatten(node, ('*',))
        for operand in operands:
            if not operand.is_leaf:
                continue
            number = _integer_of(operand.value)
            if number is None or number < 20 or number % 10 == 0:
                continue
            digit = number % 10
            if digit <= 3:
                base, sign, extra = number - digit, '＋', digit
            elif 10 - digit <= 3:
                base, sign, extra = number + (10 - digit), '－', 10 - digit
            else:
                continue
            others = '×'.join(item.text for item in operands if item is not operand)
            tips.append('拆数凑整：%d = %d %s %d，所以 %s = (%d %s %d)×%s，'
                        '再用乘法分配律分别相乘。'
                        % (number, base, sign, extra, source, base, sign, extra, others))
            break

    # 乘法交换律 / 结合律：先把能凑整的两个数相乘（三个因数以上才谈得上「先算哪两个」）
    if node.op == '*' and len(_flatten(node, ('*',))) >= 3:
        operands = _flatten(node, ('*',))
        for index in range(len(operands) - 1):
            first, second = operands[index], operands[index + 1]
            product = _node_value(first) * _node_value(second)
            if _is_round(product):
                tips.append('先算 %s×%s = %s（凑成整十整百），再和剩下的数相乘。'
                            % (first.text, second.text, format_exact(product)))
                break

    # 加法交换律：先把能凑整的两个数加起来
    if node.op == '+' and len(_flatten(node, ('+',))) >= 3:
        operands = _flatten(node, ('+',))
        for index in range(len(operands)):
            for other in range(index + 1, len(operands)):
                piece = _node_value(operands[index]) + _node_value(operands[other])
                if _is_round(piece):
                    tips.append('%s 和 %s 先相加得 %s（凑整），再加其它数。'
                                % (operands[index].text, operands[other].text,
                                   format_exact(piece)))
                    break
            if tips:
                break

    # 乘法分配律：一个数乘上「和」或「差」
    if node.op == '*':
        operands = _flatten(node, ('*',))
        for operand in operands:
            inner = _unwrap(operand)
            if inner.op not in ('+', '-'):
                continue
            others = '×'.join(item.text for item in operands if item is not operand)
            pieces = []
            for index, (sign, term) in enumerate(_signed_terms(inner)):
                body = '%s×%s' % (term.text, others)
                if index == 0:
                    pieces.append(('-' if sign < 0 else '') + body)
                else:
                    pieces.append(' %s %s' % ('－' if sign < 0 else '＋', body))
            tips.append('乘法分配律：%s = %s，把括号里的每一项分别乘 %s 再相加减。'
                        % (source, ''.join(pieces), others))
            break

    # 提取公因数：a×c + b×c
    if node.op == '+':
        operands = _flatten(node, ('+',))
        for index in range(len(operands) - 1):
            first_factors = _flatten(operands[index], ('*',))
            second_factors = _flatten(operands[index + 1], ('*',))
            for factor in first_factors:
                partner = next((item for item in second_factors
                                if item.text == factor.text), None)
                if partner is None:
                    continue
                rest = [item.text for item in first_factors + second_factors
                        if item is not factor and item is not partner]
                tips.append('提取公因数 %s：%s = %s×(%s) = %s'
                            % (factor.text, source, factor.text,
                               '＋'.join(rest), format_exact(total)))
                break
            if tips:
                break

    if not tips:
        tips.append('这个算式没有明显的简便算法，按运算顺序一步步算就可以了。')
    return tips


# --------------------------------------------------------------------------- #
# 2. 竖式演示
# --------------------------------------------------------------------------- #
# 竖式用等宽字体显示，所以分隔线用 ASCII 的 '-'，避免中文全角字符把对齐撑歪。
VERTICAL_OPS = ['+', '−', '×', '÷']


def vertical_add(a_text, b_text):
    """加法竖式。"""
    first = parse_int(a_text, '第一个加数')
    second = parse_int(b_text, '第二个加数')
    if first < 0 or second < 0:
        raise CalcError('竖式演示目前只支持非负整数。')
    width = max(len(str(first)), len(str(second)), len(str(first + second)))
    return '\n'.join([
        ' ' * 2 + str(first).rjust(width),
        '+ ' + str(second).rjust(width),
        '-' * (width + 2),
        ' ' * 2 + str(first + second).rjust(width),
    ])


def vertical_subtract(a_text, b_text):
    """减法竖式。"""
    first = parse_int(a_text, '被减数')
    second = parse_int(b_text, '减数')
    if first < 0 or second < 0:
        raise CalcError('竖式演示目前只支持非负整数。')
    if first < second:
        raise CalcError('竖式减法目前只演示被减数不小于减数的情况。')
    width = max(len(str(first)), len(str(second)))
    return '\n'.join([
        ' ' * 2 + str(first).rjust(width),
        '- ' + str(second).rjust(width),
        '-' * (width + 2),
        ' ' * 2 + str(first - second).rjust(width),
    ])


def vertical_multiply(a_text, b_text):
    """乘法竖式，多位数时逐位写出部分积。"""
    first = parse_int(a_text, '第一个因数')
    second = parse_int(b_text, '第二个因数')
    if first < 0 or second < 0:
        raise CalcError('竖式演示目前只支持非负整数。')
    first_text, second_text = str(first), str(second)
    result_text = str(first * second)
    width = max(len(first_text), len(second_text) + 1, len(result_text))
    lines = [
        first_text.rjust(width),
        ('×' + second_text).rjust(width),
        '-' * width,
    ]
    if len(second_text) > 1:
        for shift, digit in enumerate(reversed(second_text)):
            partial = first * int(digit)
            lines.append(str(partial).rjust(width - shift))
        lines.append('-' * width)
    lines.append(result_text.rjust(width))
    return '\n'.join(lines)


def vertical_divide(a_text, b_text):
    """除法竖式（长除法）。"""
    dividend = parse_int(a_text, '被除数')
    divisor = parse_int(b_text, '除数')
    if divisor == 0:
        raise CalcError('除数不能为 0。')
    if dividend < 0 or divisor < 0:
        raise CalcError('竖式演示目前只支持非负整数。')
    if dividend < divisor:
        return '%d ÷ %d = 0 余 %d（被除数比除数小，不够除）' % (dividend, divisor, dividend)

    digits = str(dividend)
    divisor_text = str(divisor)
    prefix = len(divisor_text)

    quotient_chars = {}
    rows = []            # (起始列, 文本, 是不是乘积, 这一步走到哪一位)
    work = 0
    started = False
    first_step = True
    for index, char in enumerate(digits):
        work = work * 10 + int(char)
        if not started and work < divisor:
            continue
        started = True
        quotient_digit = work // divisor
        quotient_chars[index] = str(quotient_digit)
        if quotient_digit:
            if not first_step:
                rows.append((index - len(str(work)) + 1, str(work), False, index))
            product = quotient_digit * divisor
            rows.append((index - len(str(product)) + 1, str(product), True, index))
        work -= quotient_digit * divisor
        first_step = False

    if work:
        rows.append((len(digits) - len(str(work)), str(work), False, len(digits) - 1))
    else:
        rows.append((len(digits) - 1, '0', False, len(digits) - 1))

    quotient = ''.join(quotient_chars.get(i, ' ') for i in range(len(digits)))
    lines = [
        ' ' * (prefix + 1) + quotient,
        ' ' * prefix + '-' * (len(digits) + 1),
        divisor_text + ')' + digits,
    ]
    for column, text, is_product, upto in rows:
        lines.append(' ' * (prefix + 1 + column) + text)
        if is_product:
            lines.append(' ' * (prefix + 1 + column) + '-' * (upto - column + 1))
    return '\n'.join(lines)


def vertical_calculate(operator, a_text, b_text):
    """按运算符选择竖式。"""
    if operator == '+':
        return vertical_add(a_text, b_text)
    if operator in ('−', '-', '－'):
        return vertical_subtract(a_text, b_text)
    if operator in ('×', '*', 'x'):
        return vertical_multiply(a_text, b_text)
    if operator in ('÷', '/'):
        return vertical_divide(a_text, b_text)
    raise CalcError('不支持的运算：%s' % operator)


# --------------------------------------------------------------------------- #
# 3. 分数运算 / 约分通分 / 互化
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


def _as_fraction_parts(text, name='分数'):
    """把 a/b 形式的文本拆成分子分母（不约分），返回 (分子, 分母)。"""
    source = normalize(text)
    if not source:
        raise CalcError('请填写“%s”。' % name)
    if '/' not in source:
        raise CalcError('请把“%s”写成 a/b 的形式，例如 6/8。' % name)
    left, right = source.split('/', 1)
    try:
        numerator = int(left)
        denominator = int(right)
    except ValueError:
        raise CalcError('“%s”不是分数，分子分母都要是整数，例如 6/8。' % source)
    if denominator == 0:
        raise CalcError('分母不能为 0。')
    return numerator, denominator


def reduce_fraction(text):
    """约分，返回分步说明。"""
    numerator, denominator = _as_fraction_parts(text, '分数')
    common = sym_gcd(numerator, denominator)
    lines = ['%d/%d 的分子和分母的最大公因数是 %d' % (numerator, denominator, common)]
    if common == 1:
        lines.append('%d/%d 已经是最简分数，不用再约分。' % (numerator, denominator))
    else:
        lines.append('%d/%d = (%d÷%d)/(%d÷%d) = %d/%d'
                     % (numerator, denominator, numerator, common,
                        denominator, common, numerator // common, denominator // common))
    value = Rational(numerator, denominator)
    if abs(numerator) > denominator and denominator != 1:
        lines.append('化成带分数：%s' % format_exact(value))
    lines.append('结果：%s' % format_exact(value))
    return '\n'.join(lines)


def common_denominator(a_text, b_text, op='+'):
    """通分，返回分步说明和结果（默认做加法）。"""
    p1, q1 = _as_fraction_parts(a_text, '第一个分数')
    p2, q2 = _as_fraction_parts(b_text, '第二个分数')
    if q1 < 0 or q2 < 0:
        raise CalcError('分母要写成正数。')
    common = int(ilcm(q1, q2))
    lines = ['%d/%d 和 %d/%d 的分母的最小公倍数是 %d' % (p1, q1, p2, q2, common)]
    first_times, second_times = common // q1, common // q2
    lines.append('%d/%d = (%d×%d)/(%d×%d) = %d/%d'
                 % (p1, q1, p1, first_times, q1, first_times, p1 * first_times, common))
    lines.append('%d/%d = (%d×%d)/(%d×%d) = %d/%d'
                 % (p2, q2, p2, second_times, q2, second_times, p2 * second_times, common))
    first = Rational(p1, q1)
    second = Rational(p2, q2)
    if op == '+':
        lines.append('通分后相加：%d/%d + %d/%d = %d/%d = %s'
                     % (p1 * first_times, common, p2 * second_times, common,
                        p1 * first_times + p2 * second_times, common,
                        format_exact(first + second)))
    return '\n'.join(lines)


def convert_number_forms(text):
    """分数、小数、百分数之间的互化，返回分步说明。"""
    source = normalize(text)
    if not source:
        raise CalcError('请输入一个数，例如 3/4、0.75 或 75%。')
    is_percent = source.endswith('%')
    if is_percent:
        source = source[:-1]
    value = parse_fraction(source, '数')
    if is_percent:
        value = value / 100

    lines = []
    if value.is_Rational and value.q != 1:
        lines.append('分数  %s' % format_exact(value))
    else:
        lines.append('整数  %s' % format_exact(value))
    lines.append('小数  %s' % format_decimal(float(value)))
    lines.append('百分数  %s%%' % format_decimal(float(value) * 100))
    if is_percent:
        lines.insert(0, '%s%% = %s ÷ 100 = %s' % (source, source, format_decimal(float(value))))
    return '\n'.join(lines)


# --------------------------------------------------------------------------- #
# 4. 因数与倍数 / 质数与奇偶 / 数的认识
# --------------------------------------------------------------------------- #
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


def describe_number(text):
    """描述一个整数：奇偶、质数还是合数、因数有哪些。"""
    number = parse_int(text, '整数')
    lines = []
    if number == 0:
        return '0 是偶数；0 既不是质数也不是合数，也不能分解质因数。'
    lines.append('%d 是%s' % (number, '偶数' if number % 2 == 0 else '奇数'))
    if number < 0:
        lines.append('负数的因数与倍数在小学里不讨论，这里只做奇偶判断。')
        return '\n'.join(lines)
    if number == 1:
        lines.append('1 既不是质数也不是合数。')
    elif isprime(number):
        lines.append('%d 是质数，它的因数只有 1 和它本身。' % number)
    else:
        lines.append('%d 是合数，%d = %s' % (number, number, prime_factorization(text)))
    if 0 < number <= 100000:
        items = divisors(number)
        lines.append('因数：%s（共 %d 个）' % ('、'.join(str(d) for d in items), len(items)))
    return '\n'.join(lines)


def prime_table(limit_text):
    """列出某个范围内的所有质数。"""
    limit = parse_int(limit_text, '范围')
    if limit < 2:
        raise CalcError('请填写一个不小于 2 的整数。')
    if limit > 1000:
        raise CalcError('一次最多列出 1000 以内的质数。')
    primes = list(primerange(2, limit + 1))
    return '%d 以内的质数（共 %d 个）：\n%s' % (
        limit, len(primes), '、'.join(str(p) for p in primes))


ROUND_PLACES = ['个位', '十位', '百位', '千位', '万位',
                '十万位', '百万位', '千万位', '亿位']
REWRITE_UNITS = ['万', '亿']


def _group_digits(number):
    """给整数加上千分位，方便读数。"""
    return '{:,}'.format(int(number))


def approximate_number(text, place_name):
    """求近似数：123456 精确到万位 ≈ 12万。"""
    value = parse_number(text, '数')
    if place_name not in ROUND_PLACES:
        raise CalcError('不支持的数位：%s' % place_name)
    place = ROUND_PLACES.index(place_name)
    factor = 10 ** place
    scaled = float(value) / factor
    if not math.isfinite(scaled):
        raise CalcError('这个数太大了，算不出来。')
    rounded = int(round_number(scaled, 0, SETTINGS['round_mode']))
    result = rounded * factor
    lines = ['%s 精确到%s（%s）：%s'
             % (_group_digits(value) if float(value).is_integer() else format_decimal(float(value)),
                place_name, SETTINGS['round_mode'], _group_digits(result))]
    if place >= 4:
        unit = '万' if place < 8 else '亿'
        lines.append('也可以写成 %s%s'
                     % (format_decimal(result / (10000 if unit == '万' else 100000000), 6), unit))
    return '\n'.join(lines)


def rewrite_number(text, unit_name):
    """把数改写成用「万」或「亿」作单位。"""
    value = parse_number(text, '数')
    if unit_name not in REWRITE_UNITS:
        raise CalcError('不支持的改写单位：%s' % unit_name)
    factor = 10000 if unit_name == '万' else 100000000
    return '%s = %s%s' % (_group_digits(value) if float(value).is_integer()
                          else format_decimal(float(value)),
                          format_decimal(float(value) / factor, 6), unit_name)


# --------------------------------------------------------------------------- #
# 5. 平均数
# --------------------------------------------------------------------------- #
def average(text):
    """求一组数的平均数，返回 (总和, 个数, 平均数)。"""
    values = parse_number_list(text, '数据')
    total = sum(values)
    count = len(values)
    return total, count, total / count


def average_text(text):
    total, count, value = average(text)
    return ('数据共 %d 个，总和 %s，平均数 = %s ÷ %d = %s'
            % (count, format_exact(total), format_exact(total), count, format_result(value)))


# --------------------------------------------------------------------------- #
# 6. 比与比例
# --------------------------------------------------------------------------- #
def solve_proportion(text):
    """解比例，如 3:4 = 6:x。"""
    source = normalize(text)
    if not source:
        raise CalcError('请输入比例，例如 3:4 = 6:x。')
    if '=' not in source:
        raise CalcError('比例要写成 a:b = c:d 的形式，用 x 表示未知项。')
    left, right = source.split('=', 1)

    def split_ratio(part):
        part = part.strip()
        if ':' not in part:
            raise CalcError('比例的每一项之间要用冒号分开，例如 3:4。')
        first, second = part.split(':', 1)
        return first.strip(), second.strip()

    items = list(split_ratio(left)) + list(split_ratio(right))
    if items.count('x') != 1:
        raise CalcError('比例里要有一个、而且只能有一个未知数 x。')
    if any(not item for item in items):
        raise CalcError('比例的每一项都要填写。')

    first, second, third, fourth = [
        x if item == 'x' else parse_fraction(item, '比例的项') for item in items]

    try:
        solutions = solve(first * fourth - second * third, x)
    except Exception:
        raise CalcError('这个比例解不出来，请检查数字。')
    if not solutions:
        raise CalcError('这个比例没有解。')
    value = solutions[0]

    # 内项积 = 外项积：把含 x 的那一项单独拿出来
    if first == x:
        coefficient, known, left_text = fourth, second * third, 'x × %s' % format_exact(fourth)
    elif second == x:
        coefficient, known, left_text = third, first * fourth, '%s × x' % format_exact(third)
    elif third == x:
        coefficient, known, left_text = second, first * fourth, 'x × %s' % format_exact(second)
    else:
        coefficient, known, left_text = first, second * third, '%s × x' % format_exact(first)

    lines = ['%s' % source.replace(':', ':'),
             '根据「内项积 = 外项积」：%s = %s' % (left_text, format_exact(known))]
    if coefficient == 0:
        lines.append('乘 x 的这一项是 0，这个比例没有解。')
    else:
        lines.append('x = %s ÷ %s = %s'
                     % (format_exact(known), format_exact(coefficient), format_exact(value)))
    return '\n'.join(lines)


def distribute_by_ratio(total_text, ratio_text):
    """按比分配，如 120 按 2:3:5 分配。"""
    total = parse_fraction(total_text, '总量')
    source = normalize(ratio_text)
    if not source:
        raise CalcError('请填写比，例如 2:3:5。')
    parts = [p for p in source.split(':') if p.strip()]
    if len(parts) < 2:
        raise CalcError('比至少要有两项，例如 2:3。')
    values = []
    for part in parts:
        try:
            value = int(part)
        except ValueError:
            raise CalcError('比里的每一项都要是整数，例如 2:3:5。')
        if value <= 0:
            raise CalcError('比里的每一项都要大于 0。')
        values.append(value)
    total_parts = sum(values)
    each = total / total_parts
    pieces = [total * value / total_parts for value in values]
    lines = [
        '总量 %s，比 %s' % (format_exact(total), ':'.join(str(v) for v in values)),
        '总份数 %s = %d' % (' + '.join(str(v) for v in values), total_parts),
        '每份 %s ÷ %d = %s' % (format_exact(total), total_parts, format_result(each)),
    ]
    lines.append('各部分：' + '，'.join(
        '%s × %d = %s' % (format_result(each), value, format_result(piece))
        for value, piece in zip(values, pieces)))
    return '\n'.join(lines)


# --------------------------------------------------------------------------- #
# 7. 乘方 / 开方 / 带余除法
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


def division_check_text(a_text, b_text, quotient, remainder):
    """带余除法的验算：商 × 除数 + 余数 = 被除数。"""
    return '%d × %d + %d = %d' % (quotient, int(normalize(b_text)), remainder, int(normalize(a_text)))


# --------------------------------------------------------------------------- #
# 8. 百分数
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
# 9. 单位换算与复名数
# --------------------------------------------------------------------------- #
# 每个单位的换算系数，都是相对于该类别基准单位的倍数
# 除不尽的系数（亩、速度）写成 '分数' 字符串，这样换算是精确的
UNIT_TABLE = {
    '长度': {'毫米': 0.001, '厘米': 0.01, '分米': 0.1, '米': 1, '千米': 1000},
    '面积': {'平方毫米': 1e-6, '平方厘米': 0.0001, '平方分米': 0.01, '平方米': 1,
             '公顷': 10000, '平方千米': 1000000, '亩': '10000/15'},
    '体积与容积': {'立方毫米': 1e-9, '毫升': 1e-6, '立方厘米': 1e-6, '升': 0.001,
                   '立方分米': 0.001, '立方米': 1},
    '质量': {'毫克': 1e-6, '克': 0.001, '千克': 1, '吨': 1000},
    '时间': {'毫秒': 0.001, '秒': 1, '分': 60, '小时': 3600, '天': 86400, '周': 604800},
    '速度': {'米/秒': 1, '米/分': '1/60', '千米/时': '1000/3600'},
    '人民币': {'分': 0.01, '角': 0.1, '元': 1},
}

TEMPERATURE_UNITS = ['摄氏度', '华氏度', '开尔文']

# 复名数互化只做这几类，是因为它们的单位关系最规整、课本上最常考
COMPOUND_CATEGORIES = ['长度', '质量', '时间', '人民币']
_COMPOUND_UNITS = {
    '长度': ['千米', '米', '分米', '厘米', '毫米'],
    '质量': ['吨', '千克', '克', '毫克'],
    '时间': ['天', '小时', '分', '秒'],
    '人民币': ['元', '角', '分'],
}


def unit_categories():
    """返回所有换算类别（温度放在最后）。"""
    return list(UNIT_TABLE.keys()) + ['温度']


def units_of(category):
    if category == '温度':
        return list(TEMPERATURE_UNITS)
    return list(UNIT_TABLE.get(category, {}))


def compound_categories():
    return list(COMPOUND_CATEGORIES)


def compound_units(category):
    return list(_COMPOUND_UNITS.get(category, []))


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
    value = parse_number(value_text, '数值')
    if category == '温度':
        # 温度是公式换算（有 +32、-273.15），保持浮点
        celsius = _temperature_to_celsius(float(value), from_unit)
        return _celsius_to_temperature(celsius, to_unit)
    table = UNIT_TABLE.get(category)
    if not table:
        raise CalcError('不支持的换算类别：%s' % category)
    if from_unit not in table or to_unit not in table:
        raise CalcError('不支持的单位。')
    # 用分数算，否则 1 克 → 毫克 会得到 1000.0000000000001，
    # 再配合「进一法」就会显示成 1001
    return _exact(value) * _exact(table[from_unit]) / _exact(table[to_unit])


def _exact(value):
    """把数值变成精确分数，避免换算时出现 1000.0000000000001。

    系数写成 '1/60' 这样的字符串时也能直接用；万一碰到算不成分数的式子
    （比如 √2），退回浮点，保证不会抛异常。
    """
    if isinstance(value, Fraction):
        return value
    try:
        return Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        return Fraction(float(value))


def to_compound_number(category, value_text, unit):
    """单名数 → 复名数，如 1.5 小时 → 1小时30分。"""
    units = compound_units(category)
    if not units:
        raise CalcError('“%s”暂时不支持复名数互化。' % category)
    if unit not in units:
        raise CalcError('“%s”不在%s的复名数换算范围内。' % (unit, category))
    table = UNIT_TABLE[category]
    value = parse_number(value_text, '数值')
    total = _exact(value) * _exact(table[unit])
    pieces = []
    remaining_units = units[units.index(unit):]
    for index, current in enumerate(remaining_units):
        coefficient = _exact(table[current])
        if index == len(remaining_units) - 1:
            # 最后一个单位保留小数
            if total:
                pieces.append('%s%s' % (format_decimal(total / coefficient), current))
            break
        amount = int(total / coefficient)
        if amount:
            pieces.append('%d%s' % (amount, current))
            total -= amount * coefficient
        if total == 0:
            break
    if not pieces:
        pieces.append('0%s' % unit)
    return '%s%s = %s' % (format_decimal(value), unit, ''.join(pieces))


def from_compound_number(category, text):
    """复名数 → 单名数，如 2米5厘米 → 2.05米。"""
    units = compound_units(category)
    if not units:
        raise CalcError('“%s”暂时不支持复名数互化。' % category)
    source = normalize(text).replace(' ', '')
    if not source:
        raise CalcError('请填写复名数，例如 2米5厘米。')
    # 单位名长的先匹配，免得「厘米」被「米」抢走
    pattern = '|'.join(re.escape(u) for u in sorted(units, key=len, reverse=True))
    matches = re.findall(r'(\d+(?:\.\d+)?)(%s)' % pattern, source)
    if not matches:
        raise CalcError('“%s”里没有找到“数值＋单位”，例如 2米5厘米。' % text.strip())
    if sum(len(value) + len(unit) for value, unit in matches) != len(source):
        raise CalcError('“%s”里有认不出来的内容，请按 2米5厘米 的写法填写。' % text.strip())
    table = UNIT_TABLE[category]
    total = sum(_exact(value) * _exact(table[unit]) for value, unit in matches)
    first_unit = matches[0][1]
    result = total / _exact(table[first_unit])
    return '%s = %s%s' % (source, format_decimal(result), first_unit)


# --------------------------------------------------------------------------- #
# 10. 时刻与日期
# --------------------------------------------------------------------------- #
_WEEKDAYS = '一二三四五六日'


def parse_clock(text, name='时刻'):
    """把 8:30、8时30分、8点30分 都统一成分针数。"""
    source = normalize(text).strip()
    for char in ('小时', '时', '点'):
        source = source.replace(char, ':')
    source = source.replace('分', '').replace('钟', '').replace('秒', '')
    if not source:
        raise CalcError('请填写“%s”。' % name)
    parts = source.split(':')
    try:
        hour = int(parts[0]) if parts[0] else 0
        minute = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    except ValueError:
        raise CalcError('“%s”不是有效的时刻，请写成 8:30 或 8时30分。' % text.strip())
    if not 0 <= hour <= 24 or not 0 <= minute <= 59:
        raise CalcError('“%s”超出了时刻范围。' % text.strip())
    return hour * 60 + minute


def elapsed_time(start_text, end_text):
    """从开始时刻到结束时刻经过多久，跨天自动按次日算。"""
    start = parse_clock(start_text, '开始时刻')
    end = parse_clock(end_text, '结束时刻')
    delta = end - start
    crossed = delta < 0
    if crossed:
        delta += 24 * 60
    days, remaining = divmod(delta, 1440)
    hours, minutes = divmod(remaining, 60)
    parts = []
    if days:
        parts.append('%d天' % days)
    if hours:
        parts.append('%d小时' % hours)
    if minutes:
        parts.append('%d分' % minutes)
    if not parts:
        parts.append('0分')
    lines = ['从 %s 到 %s 经过 %s' % (normalize(start_text), normalize(end_text), ''.join(parts))]
    if crossed:
        lines.append('（结束时刻比开始时刻早，按第二天计算）')
    return '\n'.join(lines)


def _parse_date(text):
    source = normalize(text).strip()
    for char in ('年', '月'):
        source = source.replace(char, '-')
    source = source.replace('日', '').replace('/', '-').replace('.', '-')
    parts = [p for p in source.split('-') if p]
    if len(parts) != 3:
        raise CalcError('请按 2026-09-14 或 2026年9月14日 的格式填写日期。')
    try:
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        raise CalcError('“%s”不是有效的日期。' % text.strip())


def date_offset(date_text, days_text):
    """日期推算：某一天再过 N 天是哪一天、星期几。"""
    start = _parse_date(date_text)
    days = parse_int(days_text, '天数')
    target = start + datetime.timedelta(days=days)
    lines = ['%s 是星期%s' % (start.strftime('%Y年%m月%d日'), _WEEKDAYS[start.weekday()])]
    action = '再过' if days >= 0 else '往前数'
    lines.append('从这一天%s %d 天是 %s，星期%s'
                 % (action, abs(days), target.strftime('%Y年%m月%d日'),
                    _WEEKDAYS[target.weekday()]))
    return '\n'.join(lines)


# --------------------------------------------------------------------------- #
# 11. 几何计算
# --------------------------------------------------------------------------- #
def _positive(params, key, label):
    value = parse_fraction(params.get(key, ''), label)
    if value <= 0:
        raise CalcError('“%s”必须大于 0。' % label)
    return value


def _rectangle(p):
    a, b = _positive(p, 'a', '长'), _positive(p, 'b', '宽')
    return [('面积', a * b, 'area'), ('周长', 2 * (a + b), 'length')]


def _square(p):
    a = _positive(p, 'a', '边长')
    return [('面积', a ** 2, 'area'), ('周长', 4 * a, 'length')]


def _triangle(p):
    a, h = _positive(p, 'a', '底'), _positive(p, 'h', '高')
    return [('面积', a * h / 2, 'area')]


def _parallelogram(p):
    a, h = _positive(p, 'a', '底'), _positive(p, 'h', '高')
    return [('面积', a * h, 'area')]


def _trapezoid(p):
    a, b, h = _positive(p, 'a', '上底'), _positive(p, 'b', '下底'), _positive(p, 'h', '高')
    return [('面积', (a + b) * h / 2, 'area')]


def _circle(p):
    r = _positive(p, 'r', '半径')
    return [('面积', pi * r ** 2, 'area'), ('周长', 2 * pi * r, 'length')]


def _circle_by_diameter(p):
    d = _positive(p, 'd', '直径')
    return [('半径', d / 2, 'length'), ('面积', pi * (d / 2) ** 2, 'area'),
            ('周长', pi * d, 'length')]


def _circle_by_circumference(p):
    c = _positive(p, 'C', '周长')
    r = c / (2 * pi)
    return [('半径', r, 'length'), ('直径', 2 * r, 'length'), ('面积', pi * r ** 2, 'area')]


def _sector(p):
    r = _positive(p, 'r', '半径')
    angle = _positive(p, 'n', '圆心角')
    if angle > 360:
        raise CalcError('圆心角不能大于 360°。')
    arc = 2 * pi * r * angle / 360
    return [('面积', pi * r ** 2 * angle / 360, 'area'),
            ('弧长', arc, 'length'),
            ('周长', arc + 2 * r, 'length')]


def _ring(p):
    outer = _positive(p, 'R', '外半径')
    inner = _positive(p, 'r', '内半径')
    if inner >= outer:
        raise CalcError('内半径必须小于外半径。')
    return [('面积', pi * (outer ** 2 - inner ** 2), 'area'),
            ('外圆周长', 2 * pi * outer, 'length')]


def _cuboid(p):
    a, b, c = _positive(p, 'a', '长'), _positive(p, 'b', '宽'), _positive(p, 'c', '高')
    return [('体积', a * b * c, 'volume'),
            ('表面积', 2 * (a * b + b * c + a * c), 'surface')]


def _cube(p):
    a = _positive(p, 'a', '棱长')
    return [('体积', a ** 3, 'volume'), ('表面积', 6 * a ** 2, 'surface')]


def _cylinder(p):
    r, h = _positive(p, 'r', '底面半径'), _positive(p, 'h', '高')
    return [('体积', pi * r ** 2 * h, 'volume'),
            ('侧面积', 2 * pi * r * h, 'lateral'),
            ('表面积', 2 * pi * r ** 2 + 2 * pi * r * h, 'surface')]


def _cone(p):
    r, h = _positive(p, 'r', '底面半径'), _positive(p, 'h', '高')
    return [('体积', pi * r ** 2 * h / 3, 'volume')]


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
    {'name': '圆（已知直径）', 'group': '平面图形',
     'params': [('d', '直径')], 'func': _circle_by_diameter},
    {'name': '圆（已知周长）', 'group': '平面图形',
     'params': [('C', '周长')], 'func': _circle_by_circumference},
    {'name': '扇形', 'group': '平面图形',
     'params': [('r', '半径'), ('n', '圆心角')], 'func': _sector},
    {'name': '圆环', 'group': '平面图形',
     'params': [('R', '外半径'), ('r', '内半径')], 'func': _ring},
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


def geometry_units():
    return list(GEOMETRY_UNITS)


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


def geometry_text(shape_name, raw_params, unit=''):
    """几何计算并直接生成要显示的文本。"""
    results = geometry_calculate(shape_name, raw_params)
    return '\n'.join('%s = %s' % (label, format_geometry(value, dimension, unit))
                     for label, value, dimension in results)


def triangle_check(a_text, b_text, c_text):
    """判断三条边能不能围成三角形。"""
    sides = [parse_fraction(a_text, '第一条边'), parse_fraction(b_text, '第二条边'),
             parse_fraction(c_text, '第三条边')]
    if any(side <= 0 for side in sides):
        raise CalcError('三角形的边长必须大于 0。')
    first, second, third = sides
    pairs = [(first + second, third, first, second, third),
             (first + third, second, first, third, second),
             (second + third, first, second, third, first)]
    lines = ['三边：%s、%s、%s' % tuple(format_exact(side) for side in sides)]
    for total, other, left, right, _ in pairs:
        lines.append('%s + %s = %s %s %s'
                     % (format_exact(left), format_exact(right), format_exact(total),
                        '>' if total > other else ('=' if total == other else '<'),
                        format_exact(other)))
    if first + second > third and first + third > second and second + third > first:
        if first == second == third:
            shape = '等边三角形'
        elif first == second or first == third or second == third:
            shape = '等腰三角形'
        else:
            shape = '三角形'
        lines.append('任意两边之和都大于第三边，能围成三角形（%s）。' % shape)
    else:
        lines.append('有两边之和不大于第三边，围不成三角形。')
    return '\n'.join(lines)


# --------------------------------------------------------------------------- #
# 12. 一元方程
# --------------------------------------------------------------------------- #
def _parse_equation(text):
    """把方程文本解析成 (左边, 右边)。"""
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
    except ZeroDivisionError:
        raise CalcError('方程里有除以 0 的地方。')
    except Exception:
        raise CalcError('看不懂这个方程：“%s”，请检查括号和运算符。' % text.strip())

    symbols = set(getattr(lhs, 'free_symbols', set())) | set(getattr(rhs, 'free_symbols', set()))
    if x not in symbols:
        raise CalcError('方程里没有找到未知数 x，请检查输入。')
    return lhs, rhs


def solve_equation(text):
    """求解一元方程，返回可直接显示的字符串。"""
    lhs, rhs = _parse_equation(text)

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


def solve_equation_steps(text):
    """一元一次方程的分步求解，返回可直接显示的多行文本。"""
    lhs, rhs = _parse_equation(text)
    try:
        left_poly = Poly(expand(lhs), x)
        right_poly = Poly(expand(rhs), x)
    except Exception:
        raise CalcError('分步解法暂时只支持整式方程，请用「解方程」直接求解。')

    if left_poly.degree() > 1 or right_poly.degree() > 1:
        raise CalcError('分步解法目前只支持一元一次方程，请用「解方程」直接求解。')

    difference = expand(lhs - rhs)
    if difference == 0:
        return '这个方程左右两边完全相同，任意实数都是它的解。'
    if not difference.free_symbols:
        return '这个方程里没有未知数，而且两边不相等，所以无解。'

    coefficients = Poly(difference, x).all_coeffs()  # [a, b] 表示 ax + b
    coefficient, constant = coefficients[0], coefficients[1] if len(coefficients) > 1 else 0
    if coefficient == 0:
        return '这个方程里没有未知数，而且两边不相等，所以无解。'
    right_side = -constant
    solution = right_side / coefficient

    lines = ['原方程        %s = %s' % (_term_text(lhs), _term_text(rhs)),
             '移项并合并同类项  %s = %s'
             % (_term_text(coefficient * x), format_exact(right_side))]
    if coefficient == 1:
        lines.append('x = %s' % format_exact(right_side))
    elif coefficient == -1:
        lines.append('两边同时乘 -1：x = %s' % format_exact(right_side / coefficient))
    else:
        lines.append('两边同时除以 %s' % format_exact(coefficient))
        lines.append('x = %s ÷ %s = %s'
                     % (format_exact(right_side), format_exact(coefficient),
                        format_exact(solution)))

    # 检验：把答案代回原方程
    try:
        left_value = lhs.subs(x, solution)
        right_value = rhs.subs(x, solution)
        lines.append('检验         左边 = %s，右边 = %s，%s'
                     % (_term_text(left_value), _term_text(right_value),
                        '左边 = 右边 ✓' if left_value == right_value else '两边不相等，请检查'))
    except Exception:
        pass
    return '\n'.join(lines)


# --------------------------------------------------------------------------- #
# 10. 更多工具
# --------------------------------------------------------------------------- #
def statistics(text):
    """求一组数据的个数、总和、平均数、中位数、众数、极差、方差、标准差。"""
    values = parse_number_list(text, '数据')
    count = len(values)
    numbers = [float(value) for value in values]
    total = sum(numbers)
    mean = total / count
    ordered = sorted(numbers)
    if count % 2 == 1:
        median = ordered[count // 2]
    else:
        median = (ordered[count // 2 - 1] + ordered[count // 2]) / 2
    tally = Counter(numbers)
    max_count = max(tally.values())
    modes = sorted(key for key, times in tally.items() if times == max_count)
    rng = ordered[-1] - ordered[0]
    variance = sum((value - mean) ** 2 for value in numbers) / count
    std_dev = math.sqrt(variance)

    lines = ['数据（从小到大）：%s' % '、'.join(format_decimal(v) for v in ordered),
             '个数  %d' % count,
             '总和  %s' % format_decimal(total),
             '平均数  %s' % format_decimal(mean),
             '中位数  %s' % format_decimal(median)]
    if max_count == 1:
        lines.append('众数  没有（每个数都只出现一次）')
    else:
        lines.append('众数  %s（各出现 %d 次）'
                     % ('、'.join(format_decimal(v) for v in modes), max_count))
    lines.append('极差  最大值 − 最小值 = %s − %s = %s'
                 % (format_decimal(ordered[-1]), format_decimal(ordered[0]),
                    format_decimal(rng)))
    lines.append('方差  %s' % format_decimal(variance))
    lines.append('标准差  %s' % format_decimal(std_dev))
    return '\n'.join(lines)


def divisibility_test(text):
    """判断一个整数能否被 2/3/4/5/8/9/11 整除，并给出理由。"""
    number = parse_int(text, '整数')
    if number == 0:
        raise CalcError('0 能被任意非 0 整数整除，这里请换一个非 0 的整数。')
    n = abs(number)
    digits = [int(ch) for ch in str(n)]
    lines = ['%d 的整除特征：' % number]

    last = digits[-1]
    ok = last % 2 == 0
    lines.append('· %s被 2 整除（末位 %d %s）'
                 % ('能' if ok else '不能', last, '是偶数' if ok else '不是偶数'))

    digit_sum = sum(digits)
    ok = digit_sum % 3 == 0
    lines.append('· %s被 3 整除（各位数字之和 %s = %d，%s3 的倍数）'
                 % ('能' if ok else '不能', '+'.join(str(d) for d in digits),
                    digit_sum, '是' if ok else '不是'))

    last2 = n % 100
    ok = last2 % 4 == 0
    lines.append('· %s被 4 整除（末两位 %02d %s4 的倍数）'
                 % ('能' if ok else '不能', last2, '是' if ok else '不是'))

    ok = last in (0, 5)
    lines.append('· %s被 5 整除（末位 %d %s0 或 5）'
                 % ('能' if ok else '不能', last, '是' if ok else '不是'))

    last3 = n % 1000
    ok = last3 % 8 == 0
    lines.append('· %s被 8 整除（末三位 %03d %s8 的倍数）'
                 % ('能' if ok else '不能', last3, '是' if ok else '不是'))

    ok = digit_sum % 9 == 0
    lines.append('· %s被 9 整除（各位数字之和 %d %s9 的倍数）'
                 % ('能' if ok else '不能', digit_sum, '是' if ok else '不是'))

    odd_sum = sum(digits[-1::-2])
    even_sum = sum(digits[-2::-2])
    difference = odd_sum - even_sum
    ok = difference % 11 == 0
    lines.append('· %s被 11 整除（奇数位之和 %d − 偶数位之和 %d = %d，%s11 的倍数）'
                 % ('能' if ok else '不能', odd_sum, even_sum, difference,
                    '是' if ok else '不是'))
    return '\n'.join(lines)


def list_factors(text):
    """列出某个整数的全部因数。"""
    number = parse_int(text, '整数')
    if number == 0:
        raise CalcError('0 的因数有无穷多个，请换一个非 0 的整数。')
    n = abs(number)
    items = divisors(n)
    return '%d 的因数：%s（共 %d 个）' % (
        number, '、'.join(str(d) for d in items), len(items))


def list_multiples(text, count_text='10'):
    """列出某个整数的前若干个倍数。"""
    number = parse_int(text, '整数')
    if number == 0:
        raise CalcError('0 的倍数只有 0，请换一个非 0 的整数。')
    count = parse_int(count_text, '个数')
    if count < 1:
        raise CalcError('倍数的个数至少要 1 个。')
    if count > 50:
        raise CalcError('一次最多列 50 个倍数。')
    items = [number * i for i in range(1, count + 1)]
    return '%d 的前 %d 个倍数：%s' % (number, count, '、'.join(str(v) for v in items))


def common_divisors_multiples(a_text, b_text):
    """两个整数的公因数和前几个公倍数。"""
    a = abs(parse_int(a_text, '第一个数'))
    b = abs(parse_int(b_text, '第二个数'))
    if a == 0 or b == 0:
        raise CalcError('0 不参与公因数与公倍数的计算。')
    common = sorted(set(divisors(a)) & set(divisors(b)))
    lcm = ilcm(a, b)
    multiples = [lcm * i for i in range(1, 6)]
    return ('%d 和 %d 的公因数：%s（共 %d 个）\n'
            '%d 和 %d 的最小公倍数是 %d，前 5 个公倍数：%s'
            % (a, b, '、'.join(str(d) for d in common), len(common),
               a, b, lcm, '、'.join(str(m) for m in multiples)))


BASE_CHOICES = [2, 8, 10, 16]


def _format_base(value, base):
    if base == 2:
        return format(value, 'b')
    if base == 8:
        return format(value, 'o')
    if base == 10:
        return str(value)
    return format(value, 'X')


def base_convert(text, from_base, to_base):
    """在不同进制之间转换整数。"""
    source = normalize(text)
    if not source:
        raise CalcError('请填写要转换的数。')
    from_base = int(from_base)
    to_base = int(to_base)
    if from_base == to_base:
        raise CalcError('源进制和目标进制相同，不需要转换。')
    try:
        value = int(source, from_base)
    except ValueError:
        raise CalcError('“%s”不是有效的 %d 进制数。' % (source, from_base))
    result = _format_base(value, to_base)
    return '%d 进制的 %s = %d 进制的 %s' % (from_base, source, to_base, result)


LENGTH_UNITS = ['毫米', '厘米', '分米', '米', '千米']
_LENGTH_TO_METER = {'毫米': Rational(1, 1000), '厘米': Rational(1, 100),
                    '分米': Rational(1, 10), '米': Rational(1), '千米': Rational(1000)}
SCALE_DIRECTIONS = ['图上 → 实际', '实际 → 图上']


def _parse_scale(text):
    source = normalize(text)
    if ':' in source:
        first, second = source.split(':', 1)
    elif '/' in source:
        first, second = source.split('/', 1)
    else:
        raise CalcError('比例尺要写成 1:50000 的形式。')
    a = parse_fraction(first, '比例尺前项')
    b = parse_fraction(second, '比例尺后项')
    if a == 0 or b == 0:
        raise CalcError('比例尺的每一项都不能是 0。')
    return a, b


def scale_convert(scale_text, distance_text, unit_text, direction):
    """按比例尺在图上距离和实际距离之间换算。"""
    a, b = _parse_scale(scale_text)
    distance = parse_fraction(distance_text, '距离')
    if distance < 0:
        raise CalcError('距离不能是负数。')
    if unit_text not in _LENGTH_TO_METER:
        raise CalcError('不支持的长度单位：%s' % unit_text)
    in_meter = distance * _LENGTH_TO_METER[unit_text]
    if direction == SCALE_DIRECTIONS[0]:
        result_meter = in_meter * (b / a)
        from_name, to_name = '图上距离', '实际距离'
        ratio_text = '%s ÷ %s' % (format_exact(b), format_exact(a))
    elif direction == SCALE_DIRECTIONS[1]:
        result_meter = in_meter * (a / b)
        from_name, to_name = '实际距离', '图上距离'
        ratio_text = '%s ÷ %s' % (format_exact(a), format_exact(b))
    else:
        raise CalcError('不支持的换算方向：%s' % direction)

    if result_meter >= 1000:
        result_value, result_unit = result_meter / 1000, '千米'
    elif 0 < result_meter < 1:
        result_value, result_unit = result_meter * 100, '厘米'
    else:
        result_value, result_unit = result_meter, '米'

    return ('比例尺  %s（图上 %s = 实际 %s）\n'
            '%s  %s %s = %s 米\n'
            '%s = %s × (%s) = %s %s'
            % (scale_text, format_exact(a), format_exact(b),
               from_name, format_exact(distance), unit_text, format_exact(in_meter),
               to_name, format_exact(distance), ratio_text,
               format_result(result_value), result_unit))


def _percent_text(rate):
    """把比例显示成百分数，如 0.035 → 3.5%。"""
    return format_decimal(float(rate) * 100) + '%'


def _parse_percent_rate(text, name='利率'):
    """解析百分数：3.5 和 3.5% 都表示 3.5%。"""
    source = normalize(text)
    if not source:
        raise CalcError('请填写“%s”。' % name)
    if source.endswith('%'):
        value = parse_fraction(source[:-1], name) / 100
    else:
        value = parse_fraction(source, name)
        if value > 1:
            value = value / 100
    if value <= 0:
        raise CalcError('“%s”要大于 0。' % name)
    return value


def discount(price_text, discount_text):
    """原价和折扣 → 现价、省了多少钱。"""
    price = parse_fraction(price_text, '原价')
    if price < 0:
        raise CalcError('原价不能是负数。')
    source = normalize(discount_text)
    if not source:
        raise CalcError('请填写折扣，例如 8折、85% 或 0.85。')
    if source.endswith('折'):
        rate = parse_fraction(source[:-1], '折扣') / 10
    elif source.endswith('%'):
        rate = parse_fraction(source[:-1], '折扣') / 100
    else:
        rate = parse_fraction(source, '折扣')
        if rate > 1:
            raise CalcError('折扣请写成“8折”“85%”或小于 1 的小数（如 0.85）。')
    if rate <= 0 or rate > 1:
        raise CalcError('折扣要在 0 到 1 之间（最多 10 折）。')
    current = price * rate
    saved = price - current
    return ('原价 %s，折扣 %s：\n'
            '现价 = %s × %s = %s\n'
            '便宜了 %s − %s = %s'
            % (format_exact(price), source,
               format_exact(price), format_decimal(float(rate)), format_result(current),
               format_exact(price), format_result(current), format_result(saved)))


def interest(principal_text, rate_text, years_text):
    """单利：本金、年利率、存期 → 利息和本息和。"""
    principal = parse_fraction(principal_text, '本金')
    if principal < 0:
        raise CalcError('本金不能是负数。')
    rate = _parse_percent_rate(rate_text, '年利率')
    years = parse_fraction(years_text, '存期')
    if years < 0:
        raise CalcError('存期不能是负数。')
    interest_value = principal * rate * years
    total = principal + interest_value
    return ('本金 %s，年利率 %s，存期 %s 年：\n'
            '利息 = %s × %s × %s = %s\n'
            '本息和 = %s + %s = %s'
            % (format_exact(principal), _percent_text(rate), format_exact(years),
               format_exact(principal), _percent_text(rate), format_exact(years),
               format_result(interest_value),
               format_exact(principal), format_result(interest_value), format_result(total)))


def tax_amount(price_text, rate_text):
    """金额和税率 → 税额、含税总价。"""
    price = parse_fraction(price_text, '金额')
    if price < 0:
        raise CalcError('金额不能是负数。')
    rate = _parse_percent_rate(rate_text, '税率')
    tax = price * rate
    total = price + tax
    return ('金额 %s，税率 %s：\n'
            '税额 = %s × %s = %s\n'
            '含税总价 = %s + %s = %s'
            % (format_exact(price), _percent_text(rate),
               format_exact(price), _percent_text(rate), format_result(tax),
               format_exact(price), format_result(tax), format_result(total)))


def factorial_of(text):
    """计算 n 的阶乘，附上展开过程。"""
    n = parse_int(text, '整数')
    if n < 0:
        raise CalcError('阶乘只对非负整数有意义。')
    if n > 100:
        raise CalcError('这个数太大了，请换一个不大于 100 的数。')
    if n <= 1:
        return '%d! = 1' % n
    if n <= 20:
        expansion = ' × '.join(str(i) for i in range(n, 0, -1))
        return '%d! = %s = %d' % (n, expansion, math.factorial(n))
    return '%d! = %d' % (n, math.factorial(n))


def permutation(n_text, r_text):
    """排列数 A(n, r) = n! / (n - r)!。"""
    n = parse_int(n_text, 'n')
    r = parse_int(r_text, 'r')
    if n < 0 or r < 0:
        raise CalcError('n 和 r 都要是非负整数。')
    if r > n:
        raise CalcError('r 不能大于 n。')
    if n > 100:
        raise CalcError('这个数太大了，请换一个不大于 100 的数。')
    if r == 0:
        return 'A(%d, 0) = %d! / %d! = 1' % (n, n, n)
    value = math.perm(n, r)
    expansion = ' × '.join(str(i) for i in range(n, n - r, -1))
    return 'A(%d, %d) = %d! / %d! = %s = %d' % (n, r, n, n - r, expansion, value)


def combination(n_text, r_text):
    """组合数 C(n, r) = n! / (r! (n - r)!)。"""
    n = parse_int(n_text, 'n')
    r = parse_int(r_text, 'r')
    if n < 0 or r < 0:
        raise CalcError('n 和 r 都要是非负整数。')
    if r > n:
        raise CalcError('r 不能大于 n。')
    if n > 100:
        raise CalcError('这个数太大了，请换一个不大于 100 的数。')
    if r == 0 or r == n:
        return 'C(%d, %d) = 1' % (n, r)
    value = math.comb(n, r)
    return 'C(%d, %d) = %d! / (%d! × %d!) = %d' % (n, r, n, r, n - r, value)


_CN_DIGITS = '零一二三四五六七八九'
_CN_UNITS = ['', '十', '百', '千']
_CN_GROUP_UNITS = ['', '万', '亿', '兆']


def _group_to_chinese(group):
    """把 0~9999 的整数写成中文（组内）。"""
    if group == 0:
        return ''
    digits = '%04d' % group
    text = ''
    pending_zero = False
    for i in range(4):
        d = int(digits[i])
        unit = _CN_UNITS[3 - i]
        if d == 0:
            if text:
                pending_zero = True
        else:
            if pending_zero:
                text += '零'
                pending_zero = False
            if d == 1 and unit == '十' and not text:
                text += '十'
            else:
                text += _CN_DIGITS[d] + unit
    return text


def _int_to_chinese(number):
    """把非负整数写成中文读法。"""
    if number == 0:
        return '零'
    groups = []
    while number > 0:
        groups.append(number % 10000)
        number //= 10000
    parts = []
    for i in range(len(groups) - 1, -1, -1):
        group_text = _group_to_chinese(groups[i])
        if group_text:
            if groups[i] < 1000 and parts and not parts[-1].endswith('零'):
                parts.append('零')
            parts.append(group_text + _CN_GROUP_UNITS[i])
        elif parts and any(groups[j] != 0 for j in range(i)) and not parts[-1].endswith('零'):
            parts.append('零')
    return ''.join(parts)


def number_to_chinese(text):
    """把数字写成中文读法（整数、小数、分数）。"""
    source = normalize(text)
    if not source:
        raise CalcError('请输入一个数。')
    if '/' in source:
        value = parse_fraction(source, '数')
        if getattr(value, 'is_Rational', False) and value.q != 1:
            sign = '负' if value.p < 0 else ''
            p, q = abs(value.p), value.q
            if p > q:
                whole, rest = divmod(p, q)
                return '%s 读作：%s%s又%s分之%s' % (
                    source, sign, _int_to_chinese(whole), _int_to_chinese(q),
                    _int_to_chinese(rest))
            return '%s 读作：%s%s分之%s' % (
                source, sign, _int_to_chinese(q), _int_to_chinese(p))
    negative = source.startswith('-')
    body = source[1:] if negative else source
    if not re.fullmatch(r'\d+(\.\d+)?', body):
        raise CalcError('请填写整数、小数或分数，例如 12345、3.14 或 1/3。')
    if '.' in body:
        int_part, dec_part = body.split('.', 1)
        reading = (_int_to_chinese(int(int_part)) if int(int_part) else '零') + '点'
        reading += ''.join(_CN_DIGITS[int(d)] for d in dec_part)
    else:
        reading = _int_to_chinese(int(body))
    if negative:
        reading = '负' + reading
    return '%s 读作：%s' % (source, reading)


_RMB_DIGITS = '零壹贰叁肆伍陆柒捌玖'
_RMB_UNITS = ['', '拾', '佰', '仟']
_RMB_GROUP_UNITS = ['', '万', '亿']


def _group_to_rmb(group):
    if group == 0:
        return ''
    digits = '%04d' % group
    text = ''
    pending_zero = False
    for i in range(4):
        d = int(digits[i])
        unit = _RMB_UNITS[3 - i]
        if d == 0:
            if text:
                pending_zero = True
        else:
            if pending_zero:
                text += '零'
                pending_zero = False
            text += _RMB_DIGITS[d] + unit
    return text


def _int_to_rmb(number):
    if number == 0:
        return '零'
    groups = []
    while number > 0:
        groups.append(number % 10000)
        number //= 10000
    parts = []
    for i in range(len(groups) - 1, -1, -1):
        group_text = _group_to_rmb(groups[i])
        if group_text:
            if groups[i] < 1000 and parts and not parts[-1].endswith('零'):
                parts.append('零')
            parts.append(group_text + _RMB_GROUP_UNITS[i])
        elif parts and any(groups[j] != 0 for j in range(i)) and not parts[-1].endswith('零'):
            parts.append('零')
    return ''.join(parts)


def number_to_rmb_upper(text):
    """金额转人民币大写。"""
    source = normalize(text)
    if not source:
        raise CalcError('请输入金额。')
    value = parse_number(source, '金额')
    if value < 0:
        raise CalcError('金额请填非负数，负号请单独说明。')
    amount = Decimal(str(float(value))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    integer = int(amount)
    cents = int((amount - integer) * 100)
    jiao, fen = divmod(cents, 10)

    reading = _int_to_rmb(integer) + '元'
    if jiao == 0 and fen == 0:
        reading += '整'
    elif fen == 0:
        reading += _RMB_DIGITS[jiao] + '角'
    elif jiao == 0:
        reading += '零' + _RMB_DIGITS[fen] + '分'
    else:
        reading += _RMB_DIGITS[jiao] + '角' + _RMB_DIGITS[fen] + '分'
    return '%s 的大写：%s' % (source, reading)


def polygon_angles(text):
    """n 边形的内角和、每个内角、外角和对角线数。"""
    n = parse_int(text, '边数')
    if n < 3:
        raise CalcError('多边形至少有 3 条边。')
    if n > 100:
        raise CalcError('边数太大了，请填一个不大于 100 的数。')
    angle_sum = (n - 2) * 180
    each_interior = angle_sum / n
    each_exterior = Rational(360, n)
    diagonals = n * (n - 3) // 2
    return ('%d 边形内角和 = (%d − 2) × 180° = %d°\n'
            '正 %d 边形每个内角 = %d° ÷ %d = %s°\n'
            '每个外角 = 360° ÷ %d = %s°\n'
            '任意多边形的外角和都是 360°\n'
            '对角线 = %d × (%d − 3) ÷ 2 = %d 条'
            % (n, n, angle_sum, n, angle_sum, n, format_result(each_interior),
               n, format_result(each_exterior), n, n, diagonals))


CURRENCY_RATES = {
    '人民币': '1',
    '美元': '7.2',
    '欧元': '7.8',
    '英镑': '9.1',
    '日元': '0.048',
    '港币': '0.92',
    '澳门元': '0.89',
    '新台币': '0.23',
    '韩元': '0.0053',
    '新加坡元': '5.35',
    '澳大利亚元': '4.75',
    '加拿大元': '5.3',
    '瑞士法郎': '8.1',
    '俄罗斯卢布': '0.078',
    '泰铢': '0.20',
    '马来西亚林吉特': '1.55',
    '越南盾': '0.00029',
}


def currency_categories():
    return list(CURRENCY_RATES)


def currency_convert(amount_text, from_currency, to_currency):
    """按参考汇率换算货币。"""
    if from_currency not in CURRENCY_RATES or to_currency not in CURRENCY_RATES:
        raise CalcError('不支持的货币种类。')
    amount = parse_fraction(amount_text, '金额')
    if amount < 0:
        raise CalcError('金额不能是负数。')
    from_rate = parse_fraction(CURRENCY_RATES[from_currency], '汇率')
    to_rate = parse_fraction(CURRENCY_RATES[to_currency], '汇率')
    in_cny = amount * from_rate
    result = in_cny / to_rate
    return ('%s %s = %s × %s = %s 人民币\n'
            '再换成 %s：%s ÷ %s = %s\n'
            '%s %s = %s %s\n'
            '（参考汇率：1 %s = %s 人民币，1 %s = %s 人民币，非实时）'
            % (format_exact(amount), from_currency, format_exact(amount),
               format_decimal(float(from_rate)), format_result(in_cny),
               to_currency, format_result(in_cny), format_decimal(float(to_rate)),
               format_result(result),
               format_exact(amount), from_currency, format_result(result), to_currency,
               from_currency, format_decimal(float(from_rate)),
               to_currency, format_decimal(float(to_rate))))
