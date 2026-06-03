"""Замкнутый контур: прогон правил по коду ST и вынесение вердикта.

OK     — находок нет;
WARN   — есть только предупреждения;
BLOCK  — есть хотя бы одна блокирующая находка (или код не разобрался).

Принцип «запрет по умолчанию» (приложение A, §8): если разбор не удался,
вердикт — BLOCK, а не «пропустить».
"""
from dataclasses import dataclass
from pathlib import Path

from .st_parser import parse
from .rules import ALL_RULES, BLOCK, WARN


@dataclass
class Verdict:
    status: str          # OK | WARN | BLOCK
    findings: list       # список Finding
    exit_code: int       # 0 если OK/WARN, 1 если BLOCK


def validate_text(text: str) -> Verdict:
    try:
        model = parse(text)
    except Exception as e:  # запрет по умолчанию
        from .rules import Finding
        f = Finding("R-PARSE", BLOCK, 0, f"код не разобран: {e}")
        return Verdict(BLOCK, [f], 1)

    findings = []
    for rule in ALL_RULES:
        findings.extend(rule(model))

    if any(f.severity == BLOCK for f in findings):
        status, code = BLOCK, 1
    elif any(f.severity == WARN for f in findings):
        status, code = WARN, 0
    else:
        status, code = "OK", 0
    return Verdict(status, findings, code)


def validate_file(path) -> Verdict:
    return validate_text(Path(path).read_text(encoding="utf-8"))


def _format(v: Verdict, name: str) -> str:
    lines = [f"[{v.status}] {name}"]
    for f in sorted(v.findings, key=lambda x: x.line):
        where = f" (строка {f.line})" if f.line else ""
        lines.append(f"   {f.severity:5} {f.rule}: {f.message}{where}")
    if not v.findings:
        lines.append("   нарушений не найдено")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("использование: python -m checker.engine <файл.st>")
        sys.exit(2)
    v = validate_file(sys.argv[1])
    print(_format(v, sys.argv[1]))
    sys.exit(v.exit_code)
