# -*- coding: utf-8 -*-
"""
Бенчмарк «где модель справляется».

Прогоняет набор задач кодогенерации через генеративную модель и считает pass-rate
по уровням сложности. Цель — НЕ «реклама модели», а демонстрация ПРИНЦИПА:
где модель справляется — оставляем ей (soft); где нет — закрываем шаблонами/правилами.
Ключевое наблюдение из статьи: модель почти не ошибается синтаксически (0 AST-ошибок),
но падает на runtime (shape, import) — это и есть граница ∀ / E[·].

Проверка результата идёт детерминированным контуром (router.tier0):
  - синтаксис (AST) — sound;
  - smoke-критерии задачи (required_substrings) — детерминированная проверка.

Модель подключается через generate(prompt) -> code. По умолчанию — заглушка-эхо,
чтобы скрипт запускался без ключа и показывал механику. Для реального прогона
подставьте вызов облачной модели (см. router/cloud.py) или локальный раннер.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from router.router import check_syntax  # noqa: E402


def stub_generate(prompt: str) -> str:
    """Заглушка: возвращает синтаксически валидный, но бессодержательный код."""
    return "def solution():\n    pass  # заглушка генерации\n"


def passes_task(code: str, task: dict) -> tuple[bool, str]:
    """
    Детерминированная проверка одной задачи:
    1) код парсится (AST, sound);
    2) присутствуют обязательные подстроки (smoke-критерий задачи).
    """
    syn = check_syntax(code)
    if not syn.ok:
        return False, "AST: " + "; ".join(syn.findings)
    missing = [s for s in task.get("required_substrings", []) if s not in code]
    if missing:
        return False, "не хватает: " + ", ".join(missing)
    return True, "ok"


def run(tasks: list[dict], generate: Callable[[str], str]) -> dict:
    by_diff_total = defaultdict(int)
    by_diff_pass = defaultdict(int)
    ast_errors = 0
    details = []

    for t in tasks:
        code = generate(t["prompt"])
        ok, reason = passes_task(code, t)
        diff = t.get("difficulty", "unknown")
        by_diff_total[diff] += 1
        if ok:
            by_diff_pass[diff] += 1
        if not check_syntax(code).ok:
            ast_errors += 1
        details.append({"id": t.get("id"), "difficulty": diff, "pass": ok, "reason": reason})

    total = len(tasks)
    passed = sum(by_diff_pass.values())
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "ast_errors": ast_errors,
        "by_difficulty": {
            d: {"pass": by_diff_pass[d], "total": by_diff_total[d]}
            for d in sorted(by_diff_total)
        },
        "details": details,
    }


def print_report(rep: dict):
    print(f"Задач: {rep['total']}   Pass: {rep['passed']}   "
          f"Pass-rate: {rep['pass_rate']:.0%}")
    print(f"Синтаксических (AST) ошибок: {rep['ast_errors']} "
          f"{'(подтверждает: модель не падает на синтаксисе)' if rep['ast_errors'] == 0 else ''}")
    print("Распределение по сложности:")
    for d, v in rep["by_difficulty"].items():
        rate = v["pass"] / v["total"] if v["total"] else 0
        print(f"  {d:<12} {v['pass']}/{v['total']} ({rate:.0%})")


def main():
    ap = argparse.ArgumentParser(description="Бенчмарк 'где модель справляется'")
    ap.add_argument("--tasks", default="tasks/tasks_ml.json", help="JSON с задачами")
    ap.add_argument("--out", default=None, help="куда сохранить отчёт (JSON)")
    args = ap.parse_args()

    with open(args.tasks, encoding="utf-8") as f:
        tasks = json.load(f)

    # Здесь подключите реальную модель вместо stub_generate:
    #   from router.cloud import make_cloud_call
    #   generate = make_cloud_call("perplexity")
    rep = run(tasks, generate=stub_generate)
    print_report(rep)
    if args.out:
        Path(args.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Отчёт сохранён: {args.out}")


if __name__ == "__main__":
    main()
