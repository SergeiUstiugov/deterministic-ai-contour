"""Правила «программы-сторожа» (замкнутый контур, класс B1).

Каждое правило смотрит на разобранную модель ST и возвращает находки.
Тяжесть: BLOCK — изменение не пройдёт; WARN — предупреждение.
Правила детерминированы: один и тот же код всегда даёт один и тот же вердикт.
Соответствие статье: примеры по нормам безопасности (аварийный сигнал, лимиты,
ограничение интегратора). Соответствие приложению A: §8, §10.
"""
import re
from dataclasses import dataclass

BLOCK = "BLOCK"
WARN = "WARN"


@dataclass
class Finding:
    rule: str
    severity: str
    line: int
    message: str


_IDENT = re.compile(r"[A-Za-z_]\w*")
_ASSIGN = re.compile(r"^\s*([A-Za-z_]\w*)\s*:=")
_NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
_SELF_INC = re.compile(r"\b(\w+)\s*:=\s*\1\s*\+")
_CLAMP_KW = ("MIN", "MAX", "LIMIT")
_ESTOP_KW = ("ESTOP", "E_STOP", "EMERGENCY", "FAULT", "TRIP")
_PROTECTED = re.compile(r"^(ESD_|SAFE_|SIS_)", re.I)


def r_init(model):
    """R-INIT: внутренняя переменная без начального значения используется
    до присваивания (неопределённое состояние)."""
    out, assigned = [], set()
    no_init = {n for n, has in model.locals_init.items() if not has}
    for lineno, line in model.body:
        m = _ASSIGN.match(line)
        lhs = m.group(1) if m else None
        rhs = line.split(":=", 1)[1] if ":=" in line else line
        for tok in _IDENT.findall(rhs):
            if tok in no_init and tok not in assigned:
                out.append(Finding("R-INIT", BLOCK, lineno,
                    f"переменная '{tok}' используется до инициализации"))
        if lhs:
            assigned.add(lhs)
    return out


def r_antiwindup(model):
    """R-ANTI-WINDUP: интегратор вида x := x + ... без ограничения (зажима)."""
    out = []
    text = "\n".join(l for _, l in model.body)
    for lineno, line in model.body:
        m = _SELF_INC.search(line)
        if not m:
            continue
        var = m.group(1)
        clamped = any(kw in text.upper() for kw in _CLAMP_KW)
        # либо переменную где-то переприсваивают к границе (OUT_MAX/OUT_MIN и т.п.)
        rebind = re.search(rf"\b{var}\s*:=\s*\w*(MAX|MIN)\w*", text, re.I)
        if not clamped and not rebind:
            out.append(Finding("R-ANTI-WINDUP", BLOCK, lineno,
                f"интегратор '{var}' растёт без ограничения (нет anti-windup)"))
    return out


def r_limit(model):
    """R-LIMIT: у выхода есть верхний предел, но нет нижнего (или наоборот)."""
    out = []
    text = "\n".join(l for _, l in model.body)
    has_upper = bool(re.search(r">\s*[\w.]+", text)) or "MAX" in text.upper()
    has_lower = bool(re.search(r"<\s*[\w.]+", text)) or "MIN" in text.upper()
    if has_upper != has_lower:
        miss = "нижний" if has_upper else "верхний"
        out.append(Finding("R-LIMIT", WARN, model.body[0][0] if model.body else 0,
            f"задан только один предел выхода; отсутствует {miss} лимит"))
    return out


def r_magic(model):
    """R-MAGIC: числовые литералы в теле (кроме 0 и 1) — выносить в константы."""
    out = []
    for lineno, line in model.body:
        for num in _NUM.findall(line):
            if float(num) not in (0.0, 1.0):
                out.append(Finding("R-MAGIC", WARN, lineno,
                    f"магическое число {num} — вынесите в именованную константу"))
    return out


def r_estop(model):
    """R-ESTOP: логика мотора/насоса без ссылки на аварийный сигнал."""
    name_blob = (model.program_name + " " + " ".join(model.declared)).upper()
    if not any(k in name_blob for k in ("PUMP", "MOTOR", "DRIVE", "НАСОС", "МОТОР")):
        return []
    blob = (name_blob + " " + " ".join(l for _, l in model.body)).upper()
    if any(k in blob for k in _ESTOP_KW):
        return []
    return [Finding("R-ESTOP", WARN, 0,
        "управление приводом без обработки аварийного сигнала (E-STOP/Fault)")]


def r_safewrite(model):
    """R-SAFEWRITE: прямая запись в защищённый тег (ESD_/SAFE_/SIS_)."""
    out = []
    for lineno, line in model.body:
        m = _ASSIGN.match(line)
        if m and _PROTECTED.match(m.group(1)):
            out.append(Finding("R-SAFEWRITE", BLOCK, lineno,
                f"прямая запись в защищённый тег '{m.group(1)}' запрещена"))
    return out


ALL_RULES = [r_init, r_antiwindup, r_limit, r_magic, r_estop, r_safewrite]
