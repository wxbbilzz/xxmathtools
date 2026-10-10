#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""calc.py 的单元测试。

只依赖 calc.py 本身（需要 sympy），不需要 PyQt5，所以可以脱离界面运行：

    cd xxmathrools
    python3 -m unittest test_calc -v

注意：涉及浮点比较的地方都用了 assertAlmostEqual，
涉及显示文本的地方只断言关键片段，避免因为格式微调而误报。
"""

import unittest

import calc


class CalcTestCase(unittest.TestCase):
    def setUp(self):
        # 每个用例都从默认设置开始，避免相互影响
        calc.reset_settings()


# --------------------------------------------------------------------------- #
# 输入归一化与格式化
# --------------------------------------------------------------------------- #
class TestNormalizeAndFormat(CalcTestCase):
    def test_normalize_fullwidth(self):
        self.assertEqual(calc.normalize('（3＋5）×2'), '(3+5)*2')
        self.assertEqual(calc.normalize('6÷2－1'), '6/2-1')
        self.assertEqual(calc.normalize('3：4'), '3:4')

    def test_normalize_symbols(self):
        self.assertEqual(calc.normalize('2^10'), '2**10')
        self.assertEqual(calc.normalize('√144'), 'sqrt(144)')
        self.assertEqual(calc.normalize('2π'), '2pi')

    def test_normalize_number_list(self):
        self.assertEqual(calc.parse_int_list('12，18、24'), [12, 18, 24])

    def test_format_decimal_default_two_digits(self):
        self.assertEqual(calc.format_decimal(1 / 3), '0.33')
        self.assertEqual(calc.format_decimal(12), '12')
        self.assertEqual(calc.format_decimal(100.0), '100')
        self.assertEqual(calc.format_decimal(0.0), '0')
        self.assertEqual(calc.format_decimal(-3.456), '-3.46')

    def test_format_decimal_keeps_small_values(self):
        # 保留 2 位时 0.001 会变成 0.00，这里应该退回有效数字
        self.assertEqual(calc.format_decimal(0.001), '0.001')

    def test_format_decimal_zero_digits(self):
        # 0 位小数不能把 100 截成 1
        self.assertEqual(calc.format_decimal(100.0, 0), '100')
        self.assertEqual(calc.format_decimal(12.7, 0), '13')

    def test_round_modes(self):
        self.assertEqual(calc.format_decimal(0.125, 2, '四舍五入'), '0.13')
        self.assertEqual(calc.format_decimal(1.001, 0, '进一法'), '2')
        self.assertEqual(calc.format_decimal(1.999, 0, '去尾法'), '1')

    def test_mixed_number(self):
        self.assertEqual(calc.format_exact(calc.Rational(7, 3)), '2又1/3')
        calc.SETTINGS['mixed_number'] = False
        self.assertEqual(calc.format_exact(calc.Rational(7, 3)), '7/3')

    def test_format_result_with_decimal(self):
        self.assertEqual(calc.format_result(calc.Rational(3, 4)), '3/4（≈ 0.75）')


# --------------------------------------------------------------------------- #
# 算式计算与分步
# --------------------------------------------------------------------------- #
class TestExpression(CalcTestCase):
    def test_operator_order(self):
        self.assertEqual(calc.evaluate_expression('3+5×2-(4÷2)'), 11)
        self.assertEqual(calc.evaluate_expression('2^10'), 1024)
        self.assertEqual(calc.evaluate_expression('√144'), 12)

    def test_exact_fraction(self):
        self.assertEqual(calc.format_expression_result(
            calc.evaluate_expression('1/3'), '1/3'), '1/3（≈ 0.33）')

    def test_division_by_zero_is_reported_clearly(self):
        with self.assertRaises(calc.CalcError) as ctx:
            calc.evaluate_expression('1÷0')
        self.assertIn('除数不能为 0', str(ctx.exception))

    def test_unknown_letter(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_expression('2a+1')

    def test_bad_syntax(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_expression('3+')

    def test_steps_follow_order(self):
        steps, result = calc.expression_steps('3+5×2-(4÷2)')
        self.assertEqual(result, 11)
        # 先乘除后加减，每一步算一个小结果
        self.assertEqual(len(steps), 4)
        self.assertEqual(steps[-1][1], '11')

    def test_steps_keep_original_operators(self):
        # 分步过程要原样保留用户写的 × ÷，不能变成 sympy 那种 -4/2 + 3 + 10
        steps, _ = calc.expression_steps('3+5×2-(4÷2)')
        self.assertEqual([item[0] for item in steps], ['5×2', '4÷2', '3+10', '13-2'])
        self.assertEqual(steps[0][2], '3+10-(4÷2)')
        self.assertEqual(steps[-1][2], '11')

    def test_steps_left_to_right(self):
        steps, _ = calc.expression_steps('10-2-3')
        self.assertEqual([item[0] for item in steps], ['10-2', '8-3'])

    def test_steps_drop_redundant_parentheses(self):
        steps, _ = calc.expression_steps('3+2×(1+4)')
        self.assertEqual(steps[0][2], '3+2×5')
        self.assertEqual(steps[1][2], '3+10')

    def test_steps_fullwidth_expression(self):
        steps, result = calc.expression_steps('（3＋5）×2')
        self.assertEqual(result, 16)
        # 全角符号会被转成半角，× 保留
        self.assertEqual(steps[0][0], '3+5')
        self.assertEqual(steps[1][0], '8×2')

    def test_steps_division_by_zero(self):
        with self.assertRaises(calc.CalcError):
            calc.expression_steps('1÷0')

    def test_steps_power(self):
        steps, result = calc.expression_steps('2^3+1')
        self.assertEqual(result, 9)
        self.assertEqual(steps[0][0], '2^3')

    def test_steps_result_matches_direct(self):
        for text in ('1+2×3', '(1+2)×3', '10-2-3', '2×3+4×5', '100÷4÷5',
                     '12÷(2+4)', '2+3×4-5÷5', '3+5×2-(4÷2)'):
            steps, result = calc.expression_steps(text)
            self.assertEqual(result, calc.evaluate_expression(text), text)
            self.assertTrue(steps, text)

    def test_simplify_advice_finds_round_numbers(self):
        tips = ' '.join(calc.simplify_advice('25×4×8'))
        self.assertIn('100', tips)

    def test_simplify_advice_splits_number(self):
        tips = ' '.join(calc.simplify_advice('102×15'))
        self.assertIn('100', tips)
        self.assertIn('(100 ＋ 2)×15', tips)

    def test_simplify_advice_no_false_positive(self):
        # 102×15 = 1530 能被 10 整除，但不是整十整百，不该提示「凑整」
        self.assertNotIn('凑成整十整百', ' '.join(calc.simplify_advice('102×15')))
        # 两个数相乘也没法「先算哪两个」
        self.assertNotIn('凑成整十整百', ' '.join(calc.simplify_advice('15×20')))

    def test_simplify_advice_distributive(self):
        tips = ' '.join(calc.simplify_advice('(100+2)×15'))
        self.assertIn('100×15 ＋ 2×15', tips)

    def test_simplify_advice_distributive_with_minus(self):
        # 括号里带减号时，展开的符号也要对
        tips = ' '.join(calc.simplify_advice('(3+4-2)×5'))
        self.assertIn('3×5 ＋ 4×5 － 2×5', tips)

    def test_simplify_advice_common_factor(self):
        tips = ' '.join(calc.simplify_advice('36×5+64×5'))
        self.assertIn('提取公因数', tips)
        self.assertIn('5×(36＋64)', tips)

    def test_simplify_advice_plain_expression(self):
        tips = calc.simplify_advice('3+5+7')
        self.assertTrue(tips)


# --------------------------------------------------------------------------- #
# 竖式
# --------------------------------------------------------------------------- #
class TestVertical(CalcTestCase):
    def test_addition(self):
        self.assertEqual(calc.vertical_add('356', '278'),
                         '  356\n+ 278\n-----\n  634')

    def test_subtraction(self):
        self.assertEqual(calc.vertical_subtract('502', '278'),
                         '  502\n- 278\n-----\n  224')

    def test_subtraction_refuses_negative(self):
        with self.assertRaises(calc.CalcError):
            calc.vertical_subtract('3', '5')

    def test_multiplication(self):
        self.assertEqual(calc.vertical_multiply('123', '45'),
                         ' 123\n ×45\n----\n 615\n492\n----\n5535')

    def test_multiplication_single_digit(self):
        self.assertEqual(calc.vertical_multiply('123', '4'),
                         '123\n ×4\n---\n492')

    def test_division(self):
        self.assertEqual(calc.vertical_divide('615', '5'),
                         '  123\n ----\n5)615\n  5\n  -\n  11\n  10\n  --\n'
                         '   15\n   15\n   --\n    0')

    def test_division_with_zero_quotient_digit(self):
        self.assertEqual(calc.vertical_divide('1234', '12'),
                         '    102\n  -----\n12)1234\n   12\n   --\n     34\n'
                         '     24\n     --\n     10')

    def test_division_by_zero(self):
        with self.assertRaises(calc.CalcError):
            calc.vertical_divide('10', '0')

    def test_division_not_enough(self):
        self.assertIn('不够除', calc.vertical_divide('3', '5'))

    def test_lines_never_exceed_width(self):
        for text in (calc.vertical_add('9', '8'), calc.vertical_multiply('99', '99'),
                     calc.vertical_divide('1000', '300')):
            lines = text.splitlines()
            self.assertLessEqual(max(len(line) for line in lines),
                                 max(len(line.rstrip()) for line in lines))

    def test_dispatch(self):
        self.assertEqual(calc.vertical_calculate('+', '1', '2'),
                         calc.vertical_add('1', '2'))
        self.assertEqual(calc.vertical_calculate('÷', '6', '2'),
                         calc.vertical_divide('6', '2'))


# --------------------------------------------------------------------------- #
# 分数
# --------------------------------------------------------------------------- #
class TestFraction(CalcTestCase):
    def test_operate(self):
        self.assertEqual(calc.fraction_operate('1/2', '+', '1/3'), calc.Rational(5, 6))
        self.assertEqual(calc.fraction_operate('1/2', '×', '2/3'), calc.Rational(1, 3))
        self.assertEqual(calc.format_result(calc.fraction_operate('1/2', '+', '1/2')), '1')

    def test_divide_by_zero(self):
        with self.assertRaises(calc.CalcError):
            calc.fraction_operate('1/2', '÷', '0')

    def test_reduce(self):
        text = calc.reduce_fraction('6/8')
        self.assertIn('最大公因数是 2', text)
        self.assertIn('3/4', text)

    def test_reduce_already_simple(self):
        self.assertIn('已经是最简', calc.reduce_fraction('3/4'))

    def test_reduce_needs_slash(self):
        with self.assertRaises(calc.CalcError):
            calc.reduce_fraction('0.75')

    def test_common_denominator(self):
        text = calc.common_denominator('1/2', '1/3')
        self.assertIn('最小公倍数是 6', text)
        self.assertIn('3/6', text)
        self.assertIn('2/6', text)
        self.assertIn('5/6', text)

    def test_forms(self):
        text = calc.convert_number_forms('3/4')
        self.assertIn('3/4', text)
        self.assertIn('0.75', text)
        self.assertIn('75%', text)

    def test_forms_percent_input(self):
        self.assertIn('75%', calc.convert_number_forms('75%'))


# --------------------------------------------------------------------------- #
# 因数、质数、数的认识
# --------------------------------------------------------------------------- #
class TestNumbers(CalcTestCase):
    def test_prime_factorization(self):
        self.assertEqual(calc.prime_factorization('12'), '2² × 3')
        self.assertEqual(calc.prime_factorization('7'), '7')
        self.assertEqual(calc.prime_factorization('360'), '2³ × 3² × 5')

    def test_prime_factorization_needs_gt_one(self):
        with self.assertRaises(calc.CalcError):
            calc.prime_factorization('1')

    def test_gcd_lcm(self):
        self.assertEqual(calc.greatest_common_divisor('12,18'), 6)
        self.assertEqual(calc.least_common_multiple('12,18'), 36)
        self.assertEqual(calc.greatest_common_divisor('4,6,8'), 2)

    def test_gcd_needs_two_numbers(self):
        with self.assertRaises(calc.CalcError):
            calc.greatest_common_divisor('12')

    def test_zero_rejected(self):
        with self.assertRaises(calc.CalcError):
            calc.greatest_common_divisor('0,5')

    def test_describe_number(self):
        text = calc.describe_number('12')
        self.assertIn('偶数', text)
        self.assertIn('合数', text)
        self.assertIn('因数', text)
        self.assertIn('1', text)

    def test_describe_prime(self):
        text = calc.describe_number('7')
        self.assertIn('奇数', text)
        self.assertIn('质数', text)

    def test_describe_one(self):
        self.assertIn('既不是质数也不是合数', calc.describe_number('1'))

    def test_prime_table(self):
        text = calc.prime_table('10')
        self.assertIn('2、3、5、7', text)
        self.assertIn('共 4 个', text)

    def test_prime_table_limit(self):
        with self.assertRaises(calc.CalcError):
            calc.prime_table('2000')

    def test_approximate_number(self):
        text = calc.approximate_number('123456', '万位')
        self.assertIn('120,000', text)
        self.assertIn('12万', text)

    def test_approximate_number_ten(self):
        # 123456 精确到十万位：看万位上的 2，不满 5 舍去，得 10万
        self.assertIn('100,000', calc.approximate_number('123456', '十万位'))
        # 160000 精确到十万位：万位是 6，满 5 进一，得 20万
        self.assertIn('200,000', calc.approximate_number('160000', '十万位'))

    def test_rewrite_number(self):
        self.assertIn('123.4567万', calc.rewrite_number('1234567', '万'))

    def test_average(self):
        total, count, value = calc.average('12,8,10')
        self.assertEqual(total, 30)
        self.assertEqual(count, 3)
        self.assertEqual(value, 10)
        self.assertIn('30 ÷ 3 = 10', calc.average_text('12,8,10'))

    def test_average_with_decimals(self):
        total, count, value = calc.average('1.5,2.5')
        self.assertEqual(total, 4)
        self.assertEqual(value, 2)


# --------------------------------------------------------------------------- #
# 比与比例
# --------------------------------------------------------------------------- #
class TestRatio(CalcTestCase):
    def test_proportion_last_term(self):
        text = calc.solve_proportion('3:4 = 6:x')
        self.assertIn('x = 24 ÷ 3 = 8', text)

    def test_proportion_first_term(self):
        text = calc.solve_proportion('x:4 = 6:8')
        self.assertIn('24 ÷ 8 = 3', text)
        self.assertIn('x × 8 = 24', text)

    def test_proportion_needs_one_x(self):
        with self.assertRaises(calc.CalcError):
            calc.solve_proportion('3:4 = 6:8')

    def test_proportion_needs_colon(self):
        with self.assertRaises(calc.CalcError):
            calc.solve_proportion('3 = 6:x')

    def test_distribute(self):
        text = calc.distribute_by_ratio('120', '2:3:5')
        self.assertIn('总份数 2 + 3 + 5 = 10', text)
        self.assertIn('24', text)
        self.assertIn('36', text)
        self.assertIn('60', text)

    def test_distribute_rejects_non_positive(self):
        with self.assertRaises(calc.CalcError):
            calc.distribute_by_ratio('120', '2:0')


# --------------------------------------------------------------------------- #
# 乘方 / 开方 / 带余除法 / 百分数
# --------------------------------------------------------------------------- #
class TestPowerAndPercent(CalcTestCase):
    def test_power(self):
        self.assertEqual(calc.power('2', '10'), 1024)
        self.assertEqual(calc.power('2', '-1'), calc.Rational(1, 2))

    def test_power_limits(self):
        with self.assertRaises(calc.CalcError):
            calc.power('0', '-1')
        with self.assertRaises(calc.CalcError):
            calc.power('2', '400')

    def test_root(self):
        self.assertEqual(calc.square_root('144'), 12)
        with self.assertRaises(calc.CalcError):
            calc.square_root('-4')

    def test_remainder(self):
        self.assertEqual(calc.division_with_remainder('17', '5'), (3, 2))
        with self.assertRaises(calc.CalcError):
            calc.division_with_remainder('17', '0')

    def test_remainder_check(self):
        self.assertEqual(calc.division_check_text('17', '5', 3, 2), '3 × 5 + 2 = 17')

    def test_percent(self):
        self.assertEqual(calc.percent_of('200', '15'), 30)
        self.assertEqual(calc.percent_ratio('30', '200'), 15)
        with self.assertRaises(calc.CalcError):
            calc.percent_ratio('30', '0')


# --------------------------------------------------------------------------- #
# 单位换算与复名数
# --------------------------------------------------------------------------- #
class TestUnit(CalcTestCase):
    def test_length(self):
        self.assertEqual(calc.convert_unit('长度', '1', '米', '厘米'), 100)
        self.assertEqual(calc.convert_unit('长度', '1', '千米', '米'), 1000)

    def test_new_units(self):
        self.assertEqual(calc.convert_unit('面积', '1', '平方米', '平方毫米'), 1000000)
        self.assertEqual(calc.convert_unit('质量', '1', '克', '毫克'), 1000)
        self.assertEqual(calc.convert_unit('体积与容积', '1', '升', '立方毫米'), 1000000)

    def test_convert_is_exact_not_float(self):
        # 浮点算 0.001/1e-6 会得到 1000.0000000000001，
        # 再配合「进一法 + 保留 0 位」就会显示成 1001
        calc.SETTINGS['decimals'] = 0
        calc.SETTINGS['round_mode'] = '进一法'
        self.assertEqual(calc.format_decimal(calc.convert_unit('质量', '1', '克', '毫克')), '1000')
        self.assertEqual(calc.format_decimal(calc.convert_unit('长度', '100', '厘米', '米')), '1')

    def test_mu(self):
        # 1 亩 = 10000/15 平方米，用分数算才不会有误差
        self.assertEqual(calc.convert_unit('面积', '3', '亩', '平方米'), 2000)

    def test_speed(self):
        self.assertAlmostEqual(calc.convert_unit('速度', '1', '米/秒', '千米/时'), 3.6)

    def test_time(self):
        self.assertEqual(calc.convert_unit('时间', '1', '小时', '分'), 60)
        self.assertEqual(calc.convert_unit('时间', '1', '周', '天'), 7)

    def test_temperature(self):
        self.assertAlmostEqual(calc.convert_unit('温度', '100', '摄氏度', '华氏度'), 212)
        self.assertAlmostEqual(calc.convert_unit('温度', '0', '摄氏度', '开尔文'), 273.15)

    def test_bad_unit(self):
        with self.assertRaises(calc.CalcError):
            calc.convert_unit('长度', '1', '米', '千克')

    def test_to_compound(self):
        self.assertEqual(calc.to_compound_number('时间', '1.5', '小时'), '1.5小时 = 1小时30分')
        self.assertEqual(calc.to_compound_number('长度', '2.05', '米'), '2.05米 = 2米5厘米')

    def test_from_compound(self):
        self.assertEqual(calc.from_compound_number('长度', '2米5厘米'), '2米5厘米 = 2.05米')
        self.assertEqual(calc.from_compound_number('时间', '1小时30分'), '1小时30分 = 1.5小时')

    def test_from_compound_rejects_junk(self):
        with self.assertRaises(calc.CalcError):
            calc.from_compound_number('长度', '2米5')

    def test_compound_categories(self):
        self.assertEqual(calc.compound_categories(), ['长度', '质量', '时间', '人民币'])
        self.assertTrue(calc.compound_units('长度'))


# --------------------------------------------------------------------------- #
# 时刻与日期
# --------------------------------------------------------------------------- #
class TestDateTime(CalcTestCase):
    def test_clock_variants(self):
        self.assertEqual(calc.parse_clock('8:30'), 510)
        self.assertEqual(calc.parse_clock('8时30分'), 510)
        self.assertEqual(calc.parse_clock('8点'), 480)

    def test_clock_range(self):
        with self.assertRaises(calc.CalcError):
            calc.parse_clock('25:00')
        with self.assertRaises(calc.CalcError):
            calc.parse_clock('8:70')

    def test_elapsed(self):
        self.assertIn('2小时45分', calc.elapsed_time('8:30', '11:15'))

    def test_elapsed_cross_day(self):
        self.assertIn('3小时30分', calc.elapsed_time('22:00', '1:30'))

    def test_elapsed_same(self):
        self.assertIn('0分', calc.elapsed_time('8:00', '8:00'))

    def test_date_offset(self):
        text = calc.date_offset('2026-09-14', '30')
        self.assertIn('2026年10月14日', text)
        self.assertIn('星期', text)

    def test_date_offset_negative(self):
        self.assertIn('2026年08月25日', calc.date_offset('2026年9月14日', '-20'))

    def test_bad_date(self):
        with self.assertRaises(calc.CalcError):
            calc.date_offset('2026-13-01', '1')


# --------------------------------------------------------------------------- #
# 几何
# --------------------------------------------------------------------------- #
class TestGeometry(CalcTestCase):
    def test_square_with_unit(self):
        text = calc.geometry_text('正方形', {'a': '3'}, '厘米')
        self.assertIn('面积 = 9 平方厘米', text)
        self.assertIn('周长 = 12 厘米', text)

    def test_unit_can_be_hidden(self):
        calc.SETTINGS['show_unit'] = False
        self.assertIn('面积 = 9', calc.geometry_text('正方形', {'a': '3'}, '厘米'))
        self.assertNotIn('平方厘米', calc.geometry_text('正方形', {'a': '3'}, '厘米'))

    def test_trapezoid(self):
        results = dict((label, value) for label, value, _ in
                       calc.geometry_calculate('梯形', {'a': '3', 'b': '5', 'h': '4'}))
        self.assertEqual(results['面积'], 16)

    def test_circle_keeps_pi(self):
        text = calc.geometry_text('圆', {'r': '2'}, '')
        self.assertIn('π', text)
        self.assertIn('12.57', text)

    def test_circle_with_pi_3_14(self):
        calc.SETTINGS['pi_mode'] = '取 3.14'
        text = calc.geometry_text('圆', {'r': '2'}, '')
        self.assertIn('12.56', text)
        self.assertIn('3.14', text)

    def test_circle_by_diameter(self):
        results = dict((label, value) for label, value, _ in
                       calc.geometry_calculate('圆（已知直径）', {'d': '6'}))
        self.assertEqual(results['半径'], 3)
        self.assertEqual(results['周长'], 6 * calc.pi)

    def test_circle_by_circumference(self):
        results = dict((label, value) for label, value, _ in
                       calc.geometry_calculate('圆（已知周长）', {'C': str(4 * float(calc.pi))}))
        self.assertAlmostEqual(float(results['半径']), 2, places=6)

    def test_sector(self):
        text = calc.geometry_text('扇形', {'r': '2', 'n': '90'}, '')
        self.assertIn('弧长', text)
        self.assertIn('π', text)

    def test_sector_angle_limit(self):
        with self.assertRaises(calc.CalcError):
            calc.geometry_calculate('扇形', {'r': '2', 'n': '400'})

    def test_ring(self):
        text = calc.geometry_text('圆环', {'R': '3', 'r': '1'}, '')
        self.assertIn('面积', text)

    def test_ring_inner_must_be_smaller(self):
        with self.assertRaises(calc.CalcError):
            calc.geometry_calculate('圆环', {'R': '1', 'r': '3'})

    def test_cylinder(self):
        labels = [label for label, _, _ in
                  calc.geometry_calculate('圆柱', {'r': '2', 'h': '5'})]
        self.assertEqual(labels, ['体积', '侧面积', '表面积'])

    def test_must_be_positive(self):
        with self.assertRaises(calc.CalcError):
            calc.geometry_calculate('正方形', {'a': '0'})

    def test_triangle_check_ok(self):
        self.assertIn('能围成三角形', calc.triangle_check('3', '4', '5'))

    def test_triangle_check_equilateral(self):
        self.assertIn('等边三角形', calc.triangle_check('5', '5', '5'))

    def test_triangle_check_fail(self):
        self.assertIn('围不成三角形', calc.triangle_check('1', '2', '5'))


# --------------------------------------------------------------------------- #
# 解方程
# --------------------------------------------------------------------------- #
class TestEquation(CalcTestCase):
    def test_linear(self):
        self.assertEqual(calc.solve_equation('2x + 3 = 7'), 'x = 2')

    def test_unknown_on_both_sides(self):
        self.assertEqual(calc.solve_equation('3x + 1 = x + 5'), 'x = 2')

    def test_fullwidth(self):
        self.assertEqual(calc.solve_equation('（x＋1）×2＝8'), 'x = 3')

    def test_without_equal_sign(self):
        self.assertEqual(calc.solve_equation('2x - 6'), 'x = 3')

    def test_quadratic(self):
        text = calc.solve_equation('x^2 - 4 = 0')
        self.assertIn('x = -2', text)
        self.assertIn('x = 2', text)

    def test_no_solution(self):
        self.assertEqual(calc.solve_equation('x + 1 = x + 2'), '无解')

    def test_identity(self):
        self.assertEqual(calc.solve_equation('x = x'), '任意实数都是解')

    def test_missing_x(self):
        with self.assertRaises(calc.CalcError):
            calc.solve_equation('1 + 2 = 3')

    def test_steps_linear(self):
        text = calc.solve_equation_steps('2x + 3 = 7')
        self.assertIn('2x = 4', text)
        self.assertIn('x = 4 ÷ 2 = 2', text)
        self.assertIn('检验', text)

    def test_steps_coefficient_one(self):
        self.assertIn('x = 4', calc.solve_equation_steps('x + 3 = 7'))

    def test_steps_rejects_quadratic(self):
        with self.assertRaises(calc.CalcError):
            calc.solve_equation_steps('x^2 - 4 = 0')

    def test_steps_identity_and_no_solution(self):
        self.assertIn('任意实数', calc.solve_equation_steps('x + 1 = x + 1'))
        self.assertIn('无解', calc.solve_equation_steps('x + 1 = x + 2'))


# --------------------------------------------------------------------------- #
# 更多工具
# --------------------------------------------------------------------------- #
class TestStatistics(CalcTestCase):
    def test_basic(self):
        text = calc.statistics('12,8,10,8,9')
        self.assertIn('平均数  9.4', text)
        self.assertIn('中位数  9', text)
        self.assertIn('众数  8', text)
        self.assertIn('极差', text)
        self.assertIn('方差', text)
        self.assertIn('标准差', text)

    def test_even_count_median(self):
        self.assertIn('中位数  2.5', calc.statistics('1,2,3,4'))

    def test_no_mode(self):
        self.assertIn('没有', calc.statistics('1,2,3'))

    def test_empty(self):
        with self.assertRaises(calc.CalcError):
            calc.statistics('')


class TestDivisibility(CalcTestCase):
    def test_12345(self):
        text = calc.divisibility_test('12345')
        self.assertIn('能被 3 整除', text)
        self.assertIn('能被 5 整除', text)
        self.assertIn('不能被 2 整除', text)

    def test_72(self):
        text = calc.divisibility_test('72')
        self.assertIn('能被 2 整除', text)
        self.assertIn('能被 3 整除', text)
        self.assertIn('能被 8 整除', text)
        self.assertIn('能被 9 整除', text)

    def test_eleven(self):
        self.assertIn('能被 11 整除', calc.divisibility_test('121'))

    def test_zero(self):
        with self.assertRaises(calc.CalcError):
            calc.divisibility_test('0')


class TestDivisorsMultiples(CalcTestCase):
    def test_factors(self):
        self.assertEqual(calc.list_factors('12'), '12 的因数：1、2、3、4、6、12（共 6 个）')

    def test_factors_zero(self):
        with self.assertRaises(calc.CalcError):
            calc.list_factors('0')

    def test_multiples(self):
        self.assertEqual(calc.list_multiples('7', '5'), '7 的前 5 个倍数：7、14、21、28、35')

    def test_multiples_count_too_big(self):
        with self.assertRaises(calc.CalcError):
            calc.list_multiples('7', '51')

    def test_common(self):
        text = calc.common_divisors_multiples('12', '18')
        self.assertIn('公因数：1、2、3、6', text)
        self.assertIn('最小公倍数是 36', text)


class TestBaseConvert(CalcTestCase):
    def test_bin_to_dec(self):
        self.assertEqual(calc.base_convert('1010', 2, 10), '2 进制的 1010 = 10 进制的 10')

    def test_dec_to_hex(self):
        self.assertEqual(calc.base_convert('255', 10, 16), '10 进制的 255 = 16 进制的 FF')

    def test_hex_to_dec(self):
        self.assertEqual(calc.base_convert('FF', 16, 10), '16 进制的 FF = 10 进制的 255')

    def test_same_base(self):
        with self.assertRaises(calc.CalcError):
            calc.base_convert('10', 2, 2)

    def test_invalid_digit(self):
        with self.assertRaises(calc.CalcError):
            calc.base_convert('102', 2, 10)


class TestScale(CalcTestCase):
    def test_map_to_real(self):
        text = calc.scale_convert('1:50000', '3', '厘米', '图上 → 实际')
        self.assertIn('千米', text)
        self.assertIn('1.5', text)

    def test_real_to_map(self):
        text = calc.scale_convert('1:50000', '1500', '米', '实际 → 图上')
        self.assertIn('3 厘米', text)

    def test_bad_scale(self):
        with self.assertRaises(calc.CalcError):
            calc.scale_convert('50000', '3', '厘米', '图上 → 实际')


class TestDiscountInterestTax(CalcTestCase):
    def test_discount(self):
        text = calc.discount('200', '8折')
        self.assertIn('现价', text)
        self.assertIn('160', text)
        self.assertIn('40', text)

    def test_discount_percent(self):
        self.assertIn('170', calc.discount('200', '85%'))

    def test_discount_bad(self):
        with self.assertRaises(calc.CalcError):
            calc.discount('200', '12折')

    def test_interest(self):
        text = calc.interest('10000', '3.5%', '2')
        self.assertIn('700', text)
        self.assertIn('10700', text)

    def test_interest_rate_without_percent(self):
        self.assertIn('350', calc.interest('10000', '3.5', '1'))

    def test_tax(self):
        text = calc.tax_amount('100', '13%')
        self.assertIn('113', text)


class TestCombinatorics(CalcTestCase):
    def test_factorial(self):
        self.assertEqual(calc.factorial_of('5'), '5! = 5 × 4 × 3 × 2 × 1 = 120')

    def test_factorial_zero_and_one(self):
        self.assertEqual(calc.factorial_of('0'), '0! = 1')
        self.assertEqual(calc.factorial_of('1'), '1! = 1')

    def test_factorial_negative(self):
        with self.assertRaises(calc.CalcError):
            calc.factorial_of('-1')

    def test_permutation(self):
        self.assertIn('= 20', calc.permutation('5', '2'))

    def test_permutation_r_zero(self):
        self.assertIn('= 1', calc.permutation('5', '0'))

    def test_permutation_r_gt_n(self):
        with self.assertRaises(calc.CalcError):
            calc.permutation('3', '5')

    def test_combination(self):
        self.assertIn('= 10', calc.combination('5', '2'))

    def test_combination_edge(self):
        self.assertIn('= 1', calc.combination('5', '5'))


class TestChineseNumber(CalcTestCase):
    def test_integer(self):
        self.assertIn('一万二千三百四十五', calc.number_to_chinese('12345'))

    def test_decimal(self):
        self.assertIn('三点一四', calc.number_to_chinese('3.14'))

    def test_fraction(self):
        self.assertIn('三分之一', calc.number_to_chinese('1/3'))

    def test_zero(self):
        self.assertIn('零', calc.number_to_chinese('0'))

    def test_ten(self):
        self.assertIn('十', calc.number_to_chinese('10'))

    def test_rmb(self):
        self.assertIn('壹佰贰拾叁元肆角伍分', calc.number_to_rmb_upper('123.45'))

    def test_rmb_integer(self):
        self.assertIn('整', calc.number_to_rmb_upper('100'))

    def test_rmb_negative(self):
        with self.assertRaises(calc.CalcError):
            calc.number_to_rmb_upper('-1')


class TestPolygon(CalcTestCase):
    def test_triangle(self):
        text = calc.polygon_angles('3')
        self.assertIn('180°', text)
        self.assertIn('对角线 = 3 × (3 − 3) ÷ 2 = 0 条', text)

    def test_pentagon(self):
        text = calc.polygon_angles('5')
        self.assertIn('540°', text)
        self.assertIn('108°', text)

    def test_too_few_sides(self):
        with self.assertRaises(calc.CalcError):
            calc.polygon_angles('2')


class TestCurrency(CalcTestCase):
    def test_usd_to_cny(self):
        self.assertIn('720', calc.currency_convert('100', '美元', '人民币'))

    def test_same_currency(self):
        self.assertIn('100', calc.currency_convert('100', '人民币', '人民币'))

    def test_negative(self):
        with self.assertRaises(calc.CalcError):
            calc.currency_convert('-1', '美元', '人民币')


class TestCalculator(CalcTestCase):
    def test_arithmetic(self):
        self.assertEqual(calc.evaluate_calculator('3+5×2-(4÷2)'), 11)

    def test_angle_mode_sin_cos(self):
        self.assertEqual(calc.evaluate_calculator('sin(30)+cos(60)', '角度'), 1)

    def test_radian_mode(self):
        self.assertEqual(calc.evaluate_calculator('sin(pi/2)', '弧度'), 1)

    def test_roots(self):
        self.assertEqual(calc.evaluate_calculator('sqrt(144)+cbrt(27)'), 15)

    def test_log_ln(self):
        self.assertEqual(calc.evaluate_calculator('log(100)'), 2)
        self.assertEqual(calc.evaluate_calculator('ln(e)'), 1)

    def test_power(self):
        self.assertEqual(calc.evaluate_calculator('2^10'), 1024)

    def test_factorial(self):
        self.assertEqual(calc.evaluate_calculator('factorial(5)'), 120)

    def test_percent(self):
        self.assertEqual(calc.evaluate_calculator('50%+3'), calc.Rational(7, 2))

    def test_tan_45(self):
        self.assertEqual(calc.evaluate_calculator('tan(45)', '角度'), 1)

    def test_asin_degrees(self):
        self.assertEqual(calc.evaluate_calculator('asin(0.5)', '角度'), 30)

    def test_imaginary(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_calculator('sqrt(-1)')

    def test_division_by_zero(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_calculator('1/0')

    def test_unknown_symbol(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_calculator('x+1')

    def test_huge_power_rejected(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_calculator('99999^99999')

    def test_power_tower_rejected(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_calculator('2^3^4')

    def test_huge_factorial_rejected(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_calculator('factorial(30000)')

    def test_huge_result_rejected(self):
        with self.assertRaises(calc.CalcError):
            calc.evaluate_calculator('10^51')

    def test_large_but_ok(self):
        self.assertEqual(calc.evaluate_calculator('999999^2'), 999998000001)


if __name__ == '__main__':
    unittest.main(verbosity=2)
