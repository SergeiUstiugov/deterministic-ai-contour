# -*- coding: utf-8 -*-
"""
Аудитор золотых меток бенчмарка sound-оракулом.

Принцип (см. статью, раздел про аудит данных): там, где задача разрешима, не доверяйте
вероятностной оценке меток — проверьте их детерминированным sound-инструментом.
Sound-оракул не «предполагает», а доказывает, поэтому даёт ноль ложных тревог.

Здесь — демонстрация на простой разрешимой задаче: проверка достижимости в графе.
Золотая метка датасета сравнивается с результатом sound-алгоритма (BFS). Любое
расхождение — это систематическая ошибка генератора меток, а не «возможная» ошибка.

В реальном аудите (RegexPSPACE: найдено 1.13% неверных меток) оракулом служили
автоматы/FAdo. Здесь, чтобы не тянуть зависимости, оракул — BFS на чистом Python.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from dataclasses import dataclass


def reachable(edges: list[tuple[int, int]], src: int, dst: int, directed: bool = True) -> bool:
    """Sound-оракул: достижим ли dst из src. BFS, точный ответ для конечного графа."""
    adj: dict[int, list[int]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        if not directed:
            adj.setdefault(b, []).append(a)
    if src == dst:
        return True
    seen = {src}
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj.get(u, []):
            if v == dst:
                return True
            if v not in seen:
                seen.add(v)
                q.append(v)
    return False


@dataclass
class AuditFinding:
    index: int
    src: int
    dst: int
    golden_label: bool
    oracle_label: bool


def audit(dataset: list[dict], directed: bool = True) -> list[AuditFinding]:
    """
    dataset — список примеров вида:
      {"edges": [[0,1],[1,2]], "src": 0, "dst": 2, "label": true}
    Возвращает список расхождений золотой метки с sound-оракулом.
    """
    findings = []
    for i, item in enumerate(dataset):
        edges = [tuple(e) for e in item["edges"]]
        oracle = reachable(edges, item["src"], item["dst"], directed=directed)
        golden = bool(item["label"])
        if oracle != golden:
            findings.append(AuditFinding(i, item["src"], item["dst"], golden, oracle))
    return findings


def main(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    findings = audit(data)
    total = len(data)
    bad = len(findings)
    print(f"Проверено примеров: {total}")
    print(f"Систематических ошибок меток: {bad} ({bad / total * 100:.2f}%)" if total else "пусто")
    for f_ in findings:
        print(f"  #{f_.index}: src={f_.src} dst={f_.dst} "
              f"золотая={f_.golden_label} оракул={f_.oracle_label} -> метка неверна")
    if bad == 0:
        print("Чистый ноль — метки согласуются с sound-оракулом (как GraphWiz/NLGraph в статье).")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "audit/sample_dataset.json")
