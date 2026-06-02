# -*- coding: utf-8 -*-
"""
Тесты, проверяющие, что детерминированный контур и аудитор работают.
Запуск:  python -m pytest tests/  (или просто python tests/test_core.py)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router.router import check_syntax, check_imports, check_security, tier1, route
from audit.ib_filter import screen, is_safe_to_send
from audit.label_auditor import reachable, audit


# --- TIER 0: синтаксис ---
def test_syntax_ok():
    assert check_syntax("x = 1\n").ok is True

def test_syntax_bad():
    assert check_syntax("def f(:\n").ok is False


# --- TIER 0: импорты ---
def test_import_mapping_detected():
    r = check_imports("import cv2\n")
    assert r.ok is False and any("opencv-python" in f for f in r.findings)

def test_import_clean():
    assert check_imports("import os\n").ok is True


# --- TIER 0: security (паттерн = B1, не полная безопасность) ---
def test_security_os_system():
    r = check_security("import os\nos.system('rm -rf /')\n")
    assert r.ok is False and "os.system" in r.findings

def test_security_clean():
    assert check_security("x = 1\n").ok is True


# --- TIER 1: эвристик даёт оценку, не гарантию ---
def test_tier1_confidence():
    r = tier1("y = t.view(-1, 10)\n")
    assert r.confidence is not None and 0 < r.confidence <= 1


# --- маршрутизация: блокировка на TIER 0 ---
def test_route_blocks_on_security():
    rep = route("import os\nos.system('x')\n")
    assert "BLOCK" in rep["decision"]


# --- IB-фильтр: конкретика блокируется, обобщение проходит ---
def test_ib_blocks_concrete():
    assert screen("PID для насоса № 47, давление 6.4 МПа")  # есть нарушения

def test_ib_allows_generic():
    assert is_safe_to_send("PID-регулятор для центробежного насоса по SIL 2")


# --- аудитор: sound-оракул ловит неверную метку ---
def test_oracle_reachability():
    assert reachable([(0, 1), (1, 2)], 0, 2, directed=True) is True
    assert reachable([(0, 1), (1, 2)], 2, 0, directed=True) is False

def test_audit_finds_mislabel():
    data = [{"edges": [[0, 1], [1, 2]], "src": 2, "dst": 0, "label": True}]  # неверно
    findings = audit(data, directed=True)
    assert len(findings) == 1


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); ok += 1; print(f"PASS  {fn.__name__}")
        except Exception:
            print(f"FAIL  {fn.__name__}"); traceback.print_exc()
    print(f"\n{ok}/{len(fns)} тестов прошло")
    sys.exit(0 if ok == len(fns) else 1)
