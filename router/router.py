# -*- coding: utf-8 -*-
"""
Маршрутизатор TIER 0/1/2 для двухконтурной схемы.

Идея (см. статью): требование «в каждом случае» (hard) проверяем детерминированно,
требование «можно иногда нарушить» (soft) отдаём генеративной модели.

  TIER 0 — детерминированная проверка (AST, словарь, security-паттерны). Гарантия (B1).
  TIER 1 — быстрый эвристик с числом уверенности. Без гарантии, только оценка (B2).
  TIER 2 — облачная LLM (GPT + RAG). Только для soft-классов.

Детерминированный контур (TIER 0/1) ни от какой модели не зависит и работает на CPU.
TIER 2 здесь представлен интерфейсом: реальный вызов облака подключается отдельно
(см. router/cloud.py), по умолчанию используется заглушка, чтобы код запускался без ключа.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class Tier(Enum):
    T0 = "TIER0_deterministic"
    T1 = "TIER1_heuristic"
    T2 = "TIER2_cloud_llm"


class Guarantee(Enum):
    POINTWISE = "поточечная (B1)"          # доказано
    CONFIDENCE = "оценка уверенности (B2)"  # не доказано, измерено
    SOFT = "вероятностная (soft)"           # отдано модели


@dataclass
class Result:
    tier: Tier
    guarantee: Guarantee
    ok: bool                     # для TIER0: прошла ли детерминированная проверка
    confidence: Optional[float]  # для TIER1: число уверенности [0..1], иначе None
    findings: list = field(default_factory=list)
    note: str = ""


# ---------------------------------------------------------------------------
# TIER 0 — детерминированные проверки (sound для своего класса свойств)
# ---------------------------------------------------------------------------

# Словарь известных маппингов «модуль импорта -> пакет PyPI».
# Это B1: lookup даёт поточечный ответ, ошибиться негде.
IMPORT_MAP = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "Crypto": "pycryptodome",
}

# Security-паттерны. ВАЖНО: regex здесь — это B1 только для КОНКРЕТНОГО паттерна
# (разрешимое подсвойство). Свойство «код безопасен» в общем виде — это B2,
# regex его НЕ гарантирует. В проде эти проверки стоит заменить на AST/Semgrep.
SECURITY_PATTERNS = {
    "os.system": re.compile(r"\bos\.system\s*\("),
    "subprocess_shell_true": re.compile(r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True"),
    "eval": re.compile(r"\beval\s*\("),
    "exec": re.compile(r"\bexec\s*\("),
    "hardcoded_password": re.compile(r"(?i)\b(password|passwd|secret|token|api_key)\s*=\s*['\"][^'\"]+['\"]"),
    "sql_format": re.compile(r"(?i)(execute|cursor\.execute)\s*\(\s*['\"].*%s"),
}


def check_syntax(code: str) -> Result:
    """100 Syntax — AST-парсер. Sound: либо код парсится, либо нет."""
    try:
        ast.parse(code)
        return Result(Tier.T0, Guarantee.POINTWISE, ok=True, confidence=None,
                      note="код синтаксически валиден")
    except SyntaxError as e:
        return Result(Tier.T0, Guarantee.POINTWISE, ok=False, confidence=None,
                      findings=[f"SyntaxError: {e.msg} (строка {e.lineno})"],
                      note="синтаксическая ошибка")


def check_imports(code: str) -> Result:
    """300 Import — словарь известных опечаток/маппингов. B1."""
    findings = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return Result(Tier.T0, Guarantee.POINTWISE, ok=False, confidence=None,
                      note="нельзя проверить импорты: код не парсится")
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]
        for n in names:
            if n in IMPORT_MAP:
                findings.append(f"импорт '{n}' ставится как пакет '{IMPORT_MAP[n]}'")
    return Result(Tier.T0, Guarantee.POINTWISE, ok=(not findings),
                  confidence=None, findings=findings,
                  note="импорты разрешаются" if not findings else "проверьте имена пакетов")


def check_security(code: str) -> Result:
    """Security — паттерны. B1 для конкретного паттерна, НЕ гарантия «безопасности»."""
    findings = [name for name, pat in SECURITY_PATTERNS.items() if pat.search(code)]
    return Result(Tier.T0, Guarantee.POINTWISE, ok=(not findings),
                  confidence=None, findings=findings,
                  note="известных опасных паттернов нет" if not findings
                       else "найдены потенциально опасные паттерны (это не полная проверка безопасности)")


def tier0(code: str) -> list[Result]:
    """Полный детерминированный контур TIER 0."""
    return [check_syntax(code), check_imports(code), check_security(code)]


# ---------------------------------------------------------------------------
# TIER 1 — быстрый эвристик с числом уверенности (B2, без гарантии)
# ---------------------------------------------------------------------------

# Ключевые слова -> класс риска. Это НЕ sound: даёт лишь оценку уверенности.
# Число уверенности здесь грубое; в проде его калибруют (см. audit/README и THEORY).
RUNTIME_HINTS = {
    "shape_mismatch": (re.compile(r"\.view\(|\.reshape\(|\.transpose\("), 0.80),
    "missing_device": (re.compile(r"\.cuda\(\)|\.to\(['\"]?cuda"), 0.75),
    "index_risk": (re.compile(r"\[[^\]]*\b\w+\s*-\s*1\s*\]"), 0.70),
}


def tier1(code: str) -> Result:
    """Эвристик по ключевым словам. Возвращает максимальную уверенность среди сработавших."""
    findings = []
    conf = 0.0
    for name, (pat, c) in RUNTIME_HINTS.items():
        if pat.search(code):
            findings.append(f"{name} (confidence~{c:.0%})")
            conf = max(conf, c)
    if not findings:
        return Result(Tier.T1, Guarantee.CONFIDENCE, ok=True, confidence=None,
                      note="эвристик рисков не нашёл (отсутствие сигнала ≠ гарантия)")
    return Result(Tier.T1, Guarantee.CONFIDENCE, ok=False, confidence=conf, findings=findings,
                  note="это ОЦЕНКА уверенности, не доказательство — проверьте вручную")


# ---------------------------------------------------------------------------
# TIER 2 — облачная LLM (только soft). Интерфейс; реализация в cloud.py
# ---------------------------------------------------------------------------

def tier2(prompt: str, cloud_call: Optional[Callable[[str], str]] = None) -> Result:
    """
    Отдаём soft-задачу облачной модели. cloud_call — функция, делающая реальный вызов
    (см. router/cloud.py). По умолчанию заглушка, чтобы код запускался без ключа.
    ВАЖНО: наружу должно уходить только ОБОБЩЕНИЕ, без конкретики объекта (см. audit/ib_filter.py).
    """
    if cloud_call is None:
        return Result(Tier.T2, Guarantee.SOFT, ok=True, confidence=None,
                      note="[заглушка] здесь был бы ответ облачной LLM на обобщённый запрос")
    answer = cloud_call(prompt)
    return Result(Tier.T2, Guarantee.SOFT, ok=True, confidence=None,
                  findings=[answer], note="ответ облачной модели — soft, требует проверки контуром")


# ---------------------------------------------------------------------------
# Маршрутизация
# ---------------------------------------------------------------------------

def route(code: str) -> dict:
    """
    Прогоняет код через TIER 0 -> TIER 1.
    TIER 2 не вызывается автоматически: облако — для генерации soft, не для проверки hard.
    """
    t0 = tier0(code)
    blocking = [r for r in t0 if not r.ok]
    report = {"tier0": t0, "tier1": None, "decision": ""}

    if blocking:
        report["decision"] = "BLOCK на TIER 0 (детерминированно, с гарантией): " + \
                             "; ".join(f"{r.note}" for r in blocking)
        return report

    t1 = tier1(code)
    report["tier1"] = t1
    if not t1.ok:
        report["decision"] = (f"TIER 1: риск с уверенностью ~{t1.confidence:.0%} "
                              f"(это оценка, не гарантия). Рекомендуется ручная проверка.")
    else:
        report["decision"] = "TIER 0 чисто, TIER 1 рисков не нашёл. Гарантия — только по TIER 0."
    return report
