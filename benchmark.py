"""Бенчмарк двухконтурной архитектуры.

Берёт список задач (examples/tasks.json), для каждой определяет контур
(A / B1 / B2 / B3) и, если у задачи есть код ST, прогоняет его через
программу-сторожа. В конце печатает долю задач, закрываемых детерминированно
(B1 / B3), и долю, где нужен ИИ или оценка (A / B2).

Это и есть обещанная в статье таблица «детерминированно / нужен ИИ».
Замените examples/tasks.json своими задачами — получите свою таблицу.

Запуск:  python benchmark.py
Без внешних зависимостей (только стандартная библиотека Python 3.10+).
"""
import json
from pathlib import Path

from router import route, LABELS
from checker import validate_file

ROOT = Path(__file__).parent


def main():
    data = json.loads((ROOT / "examples" / "tasks.json").read_text(encoding="utf-8"))
    tasks = data["tasks"]

    print("=" * 78)
    print("ДВУХКОНТУРНЫЙ МАРШРУТИЗАТОР — бенчмарк")
    print("=" * 78)
    rows = []
    det = 0          # B1 + B3 — закрывается детерминированно
    needs_ai = 0     # A + B2 — нужен ИИ / оценка
    for t in tasks:
        cls = route(t)
        if cls in ("B1", "B3"):
            det += 1
        else:
            needs_ai += 1
        check = ""
        if "code" in t and cls in ("B1", "B3"):
            v = validate_file(ROOT / t["code"])
            nblock = sum(1 for f in v.findings if f.severity == "BLOCK")
            nwarn = sum(1 for f in v.findings if f.severity == "WARN")
            check = f"{v.status} (BLOCK={nblock}, WARN={nwarn})"
        rows.append((t["name"], t["kind"], cls, check))

    w = max(len(r[0]) for r in rows)
    print(f"{'Задача':<{w}}  {'тип':5}  {'контур':6}  проверка кода")
    print("-" * 78)
    for name, kind, cls, check in rows:
        print(f"{name:<{w}}  {kind:5}  {cls:6}  {check}")

    n = len(tasks)
    print("-" * 78)
    print(f"Всего задач: {n}")
    print(f"  детерминированно (B1/B3): {det:2}  ({det/n:.0%})")
    print(f"  нужен ИИ / оценка (A/B2): {needs_ai:2}  ({needs_ai/n:.0%})")
    print("=" * 78)
    print("Контуры:", "; ".join(f"{k} — {v}" for k, v in LABELS.items()))


if __name__ == "__main__":
    main()
