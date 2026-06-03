"""Самопроверка прототипа: правила сторожа, маршрутизатор, conformal.

Запуск из корня репозитория:
    python -m unittest discover -s tests -v
или:
    python tests/test_checker.py
Без внешних зависимостей (стандартная библиотека Python 3.10+).
"""
import sys
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checker import validate_file, validate_text   # noqa: E402
from router import route                           # noqa: E402
from calibration import quantile_threshold         # noqa: E402

EX = ROOT / "examples"


class TestChecker(unittest.TestCase):
    def test_bad_pump_blocked(self):
        v = validate_file(EX / "bad_pump.st")
        self.assertEqual(v.status, "BLOCK")
        self.assertEqual(v.exit_code, 1)
        rules = {f.rule for f in v.findings}
        for expected in ("R-INIT", "R-ANTI-WINDUP", "R-SAFEWRITE"):
            self.assertIn(expected, rules, f"ожидалось правило {expected}")

    def test_good_pump_ok(self):
        v = validate_file(EX / "good_pump.st")
        self.assertEqual(v.status, "OK")
        self.assertEqual(v.exit_code, 0)
        self.assertEqual(v.findings, [])

    def test_default_deny_on_broken_code(self):
        # незакрытый VAR -> структура повреждена -> запрет по умолчанию
        v = validate_text("PROGRAM X\nVAR\n a : REAL;")
        self.assertEqual(v.status, "BLOCK")
        self.assertEqual(v.exit_code, 1)


class TestRouter(unittest.TestCase):
    def test_soft_to_open_loop(self):
        self.assertEqual(route({"kind": "soft"}), "A")

    def test_hard_with_oracle(self):
        self.assertEqual(route({"kind": "hard", "has_cheap_oracle": True}), "B1")

    def test_hard_without_oracle(self):
        self.assertEqual(route({"kind": "hard", "has_cheap_oracle": False}), "B2")

    def test_hard_stale_rule(self):
        self.assertEqual(
            route({"kind": "hard", "has_cheap_oracle": True, "rule_may_be_stale": True}),
            "B3",
        )


class TestConformal(unittest.TestCase):
    def test_quantile_threshold(self):
        scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        # n=10, delta=0.1 -> k=ceil(11*0.9)=10 -> 10-й балл = 10
        self.assertEqual(quantile_threshold(scores, 0.1), 10)
        # delta=0.5 -> k=ceil(11*0.5)=6 -> 6-й балл = 6
        self.assertEqual(quantile_threshold(scores, 0.5), 6)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            quantile_threshold([], 0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
