"""Проверка округления и вывода чисел."""
import unittest

from ibtrain.utils import fmt_num, fmt_pct, round_half_up


class UtilsTest(unittest.TestCase):
    def test_half_up(self):
        self.assertEqual(round_half_up(23.35, 1), 23.4)
        self.assertEqual(round_half_up(2.5, 0), 3.0)
        self.assertEqual(round_half_up(66.666, 1), 66.7)

    def test_format(self):
        self.assertEqual(fmt_num(100.0), "100")
        self.assertEqual(fmt_num(88.8), "88,8")
        self.assertEqual(fmt_num(5), "5")
        self.assertEqual(fmt_pct(87.5), "87,5 %")


if __name__ == "__main__":
    unittest.main()
