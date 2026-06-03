"""Golden-тесты правил сторожа (концепт класса B3 из приложения A).

Класс B3 — «правило может устареть»; значит, сами правила нужно проверять на
эталонных примерах. Здесь для КАЖДОГО правила заданы пары «эталонов»:
- код, на котором правило ДОЛЖНО сработать;
- код, на котором правило срабатывать НЕ должно.

Если поведение правила поменяется (например, при доработке), тест это поймает.

Запуск из корня репозитория:
    python -m unittest tests.test_rules -v
Без внешних зависимостей (стандартная библиотека Python 3.10+).
"""
import sys
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from checker.st_parser import parse                                   # noqa: E402
from checker.rules import (                                           # noqa: E402
    r_init, r_antiwindup, r_limit, r_magic, r_estop, r_safewrite,
)


def wrap(decls_inputs="", decls="", body=""):
    """Собирает минимальную ST-программу для проверки правила."""
    parts = ["PROGRAM P"]
    if decls_inputs:
        parts += ["VAR_INPUT", decls_inputs, "END_VAR"]
    if decls:
        parts += ["VAR", decls, "END_VAR"]
    parts += [body, "END_PROGRAM"]
    return "\n".join(parts)


# (правило, описание, код, должно_ли_сработать)
GOLDEN = [
    # R-INIT
    (r_init, "переменная без init читается до записи",
     wrap(decls="u : REAL;", body="    u := u + 1.0;"), True),
    (r_init, "переменная с init — ок",
     wrap(decls="u : REAL := 0.0;", body="    u := u + 1.0;"), False),

    # R-ANTI-WINDUP
    (r_antiwindup, "интегратор без ограничения",
     wrap(decls="integral : REAL := 0.0;", body="    integral := integral + 1.0;"), True),
    (r_antiwindup, "интегратор с зажимом по OUT_MAX",
     wrap(decls="integral : REAL := 0.0;\n    OUT_MAX : REAL := 100.0;",
          body="    integral := integral + 1.0;\n    IF integral > OUT_MAX THEN\n        integral := OUT_MAX;\n    END_IF;"), False),

    # R-LIMIT
    (r_limit, "задан только верхний предел",
     wrap(decls="u : REAL := 0.0;", body="    IF u > 100.0 THEN\n        u := 100.0;\n    END_IF;"), True),
    (r_limit, "заданы оба предела",
     wrap(decls="u : REAL := 0.0;\n    OUT_MAX : REAL := 100.0;\n    OUT_MIN : REAL := 0.0;",
          body="    IF u > OUT_MAX THEN\n        u := OUT_MAX;\n    ELSIF u < OUT_MIN THEN\n        u := OUT_MIN;\n    END_IF;"), False),

    # R-MAGIC
    (r_magic, "магическое число в теле",
     wrap(decls="x : REAL := 0.0;", body="    x := 42.0;"), True),
    (r_magic, "только именованные константы и 0/1",
     wrap(decls="x : REAL := 0.0;\n    OUT_MAX : REAL := 100.0;", body="    x := OUT_MAX;"), False),

    # R-ESTOP
    (r_estop, "насос без аварийного сигнала",
     "PROGRAM PumpControl\nVAR\n    x : REAL := 0.0;\nEND_VAR\n    x := x;\nEND_PROGRAM", True),
    (r_estop, "насос с обработкой EStop",
     "PROGRAM PumpControl\nVAR_INPUT\n    EStop : BOOL;\nEND_VAR\nVAR\n    x : REAL := 0.0;\nEND_VAR\n    IF EStop THEN\n        x := 0.0;\n    END_IF;\nEND_PROGRAM", False),
    (r_estop, "не привод — правило не применяется",
     wrap(decls="x : REAL := 0.0;", body="    x := x;"), False),

    # R-SAFEWRITE
    (r_safewrite, "запись в защищённый тег ESD_",
     wrap(body="    ESD_Valve := TRUE;"), True),
    (r_safewrite, "запись в обычный тег",
     wrap(body="    Valve := TRUE;"), False),
]


class TestRulesGolden(unittest.TestCase):
    def test_golden(self):
        for rule, desc, code, should_fire in GOLDEN:
            with self.subTest(rule=rule.__name__, case=desc):
                model = parse(code)
                findings = rule(model)
                fired = len(findings) > 0
                self.assertEqual(
                    fired, should_fire,
                    f"{rule.__name__}: ожидалось fire={should_fire} на «{desc}», "
                    f"получено {fired} (находки: {[f.rule for f in findings]})",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
