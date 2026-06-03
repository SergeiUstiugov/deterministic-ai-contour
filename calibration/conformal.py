"""Класс B2: честная оценка уверенности (conformal prediction) — чистый Python.

Идея (приложение A, §6): вместо «модель уверена на 85%» даём интервал,
который накрывает истину с вероятностью не ниже 1-delta — но только пока
данные «обмениваемы». При сдвиге распределения гарантия теряется
(это демонстрирует функция _demo).
"""
import math
import random


def quantile_threshold(scores, delta):
    """Порог q = ceil((n+1)(1-delta))-й по возрастанию балл несоответствия."""
    n = len(scores)
    if n == 0:
        raise ValueError("нужна непустая калибровочная выборка")
    s = sorted(scores)
    k = math.ceil((n + 1) * (1 - delta))
    k = max(1, min(k, n))
    return s[k - 1]


def interval(point, q):
    """Интервал-предсказание вокруг точечной оценки."""
    return (point - q, point + q)


def _demo():
    rng = random.Random(42)
    delta = 0.10
    calib = [abs(rng.gauss(0, 1)) for _ in range(1000)]
    q = quantile_threshold(calib, delta)

    test_same = [abs(rng.gauss(0, 1)) for _ in range(2000)]
    cov_same = sum(1 for s in test_same if s <= q) / len(test_same)

    test_shift = [abs(rng.gauss(0, 2)) for _ in range(2000)]
    cov_shift = sum(1 for s in test_shift if s <= q) / len(test_shift)

    print("Класс B2 — честная оценка (conformal prediction)")
    print(f"  delta = {delta}  ->  целевое покрытие >= {1-delta:.0%}")
    print(f"  порог q = {q:.3f}")
    print(f"  покрытие БЕЗ сдвига:  {cov_same:.1%}  (гарантия выполняется)")
    print(f"  покрытие СО сдвигом:  {cov_shift:.1%}  (гарантия НАРУШЕНА)")
    print("  вывод: B2 честна только при контроле сдвига распределения.")


if __name__ == "__main__":
    _demo()
