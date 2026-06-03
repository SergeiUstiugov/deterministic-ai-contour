"""Мини-разбор Structured Text (ST).

Это НЕ полноценный парсер IEC 61131-3, а простой структурный сканер строк:
он отделяет секции объявлений (VAR / VAR_INPUT / VAR_OUTPUT) от тела программы
и собирает, какие переменные объявлены и у каких есть начальное значение.
Этого достаточно, чтобы показать идею «программы-сторожа» из статьи.
Соответствие приложению A: §8 (надёжный проверяющий, soundness в рамках демо).
"""
import re
from dataclasses import dataclass, field


@dataclass
class Model:
    program_name: str = ""
    inputs: set = field(default_factory=set)     # VAR_INPUT
    outputs: set = field(default_factory=set)    # VAR_OUTPUT
    locals_init: dict = field(default_factory=dict)  # имя -> есть ли ":=" в объявлении
    body: list = field(default_factory=list)     # [(номер_строки, текст)]
    declared: set = field(default_factory=set)   # все объявленные имена


_BLOCK_COMMENT = re.compile(r"\(\*.*?\*\)", re.S)
_DECL = re.compile(r"^\s*([A-Za-z_]\w*)\s*:\s*[A-Za-z]")
_VAR_OPEN = re.compile(r"^\s*VAR(_INPUT|_OUTPUT|_GLOBAL)?\b", re.I)
_VAR_END = re.compile(r"^\s*END_VAR\b", re.I)
_PROG = re.compile(r"^\s*(PROGRAM|FUNCTION_BLOCK|FUNCTION)\s+([A-Za-z_]\w*)", re.I)


def _strip_comments(text: str) -> str:
    text = _BLOCK_COMMENT.sub(" ", text)
    out = []
    for line in text.splitlines():
        out.append(line.split("//", 1)[0])
    return "\n".join(out)


def parse(text: str) -> Model:
    """Разбирает текст ST. Бросает ValueError при грубом нарушении структуры
    (это сознательно: на вход замкнутого контура действует «запрет по умолчанию»)."""
    clean = _strip_comments(text)
    m = Model()
    section = None  # None | 'VAR' | 'VAR_INPUT' | 'VAR_OUTPUT'
    open_var = 0
    for i, raw in enumerate(clean.splitlines(), start=1):
        line = raw.rstrip()
        if not line.strip():
            continue
        pm = _PROG.match(line)
        if pm:
            m.program_name = pm.group(2)
            continue
        if re.match(r"^\s*END_(PROGRAM|FUNCTION_BLOCK|FUNCTION)\b", line, re.I):
            continue
        vo = _VAR_OPEN.match(line)
        if vo:
            open_var += 1
            suff = (vo.group(1) or "").upper()
            section = "VAR" + suff if suff else "VAR"
            continue
        if _VAR_END.match(line):
            open_var -= 1
            section = None
            continue
        if section:  # строка объявления переменной
            dm = _DECL.match(line)
            if dm:
                name = dm.group(1)
                has_init = ":=" in line
                m.declared.add(name)
                if section == "VAR_INPUT":
                    m.inputs.add(name)
                elif section == "VAR_OUTPUT":
                    m.outputs.add(name)
                else:
                    m.locals_init[name] = has_init
            continue
        # иначе это тело
        m.body.append((i, line.strip()))

    if open_var != 0:
        raise ValueError("незакрытый VAR / END_VAR — структура повреждена")
    return m
