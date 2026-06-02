# -*- coding: utf-8 -*-
"""
Информационный барьер (IB-filter).

Проверяет запрос, уходящий в открытый контур (облачную LLM), на конкретику объекта:
IP-адреса, теги SCADA, номера установок, ФИО, давления, ключи/пароли.
Если найдено — отправка наружу блокируется (см. router/cloud.py).

Это первый барьер из двух (второй — материализация на бумаге), описанных в статье
«Две машины и бумага между ними». Здесь — минимальная программная реализация.
"""
from __future__ import annotations

import re

FORBIDDEN = {
    "ip":       re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "scada":    re.compile(r"\b[A-Z]{2,}_[A-Z0-9_]{3,}\b"),
    "object":   re.compile(r"(?i)(?:насос|установк\w*|агрегат|линия|цех)\s*№?\s*\d+"),
    "pressure": re.compile(r"\b\d+[.,]\d+\s*(?:МПа|бар|кПа|атм)\b"),
    "name":     re.compile(r"\b[А-Я][а-я]+\s+[А-Я]\.\s*[А-Я]\."),
    "creds":    re.compile(r"(?i)(?:password|passwd|token|api[_-]?key|secret)\s*[:=]\s*\S+"),
}


def screen(text: str) -> list[tuple[str, str]]:
    """
    Возвращает список найденных нарушений [(категория, совпадение), ...].
    Пустой список — запрос можно отправлять наружу.
    """
    found = []
    for cat, pat in FORBIDDEN.items():
        for m in pat.finditer(text):
            found.append((cat, m.group()))
    return found


def is_safe_to_send(text: str) -> bool:
    return not screen(text)
