# -*- coding: utf-8 -*-
"""
Интерфейс к облачной LLM (TIER 2) для открытого контура.

КРИТИЧНО ПО БЕЗОПАСНОСТИ: наружу уходит только ОБОБЩЕНИЕ, не конкретика объекта.
Перед любым вызовом запрос обязан пройти информационный барьер (см. audit/ib_filter.py).
Архитектура барьера разобрана в статье «Две машины и бумага между ними».

По умолчанию реального вызова нет — функция возвращает заглушку, чтобы репозиторий
запускался без ключа. Для боевого режима задайте PERPLEXITY_API_KEY (или свой провайдер)
и раскомментируйте соответствующую реализацию.
"""
from __future__ import annotations

import os
from typing import Optional

from audit.ib_filter import screen  # барьер: вырезает конкретику


class LeakError(Exception):
    """Запрос содержит конкретику объекта — наружу отправлять нельзя."""


def make_cloud_call(provider: str = "stub"):
    """
    Возвращает функцию cloud_call(prompt) -> str.
    Перед отправкой ВСЕГДА прогоняет запрос через информационный барьер.
    """
    def guarded(prompt: str) -> str:
        violations = screen(prompt)
        if violations:
            cats = ", ".join(sorted({c for c, _ in violations}))
            raise LeakError(
                f"Запрос содержит конкретику ({cats}) — наружу нельзя. "
                f"Переформулируйте как обобщение."
            )
        return _send(prompt, provider)
    return guarded


def _send(prompt: str, provider: str) -> str:
    if provider == "stub":
        return ("[заглушка облачной LLM] Запрос прошёл барьер и был бы отправлен в облако. "
                "Задайте провайдера и ключ для реального вызова.")

    if provider == "perplexity":
        key = os.environ.get("PERPLEXITY_API_KEY")
        if not key:
            raise RuntimeError("PERPLEXITY_API_KEY не задан в окружении")
        # Боевой вызов (раскомментируйте и поставьте зависимость requests):
        # import requests
        # resp = requests.post(
        #     "https://api.perplexity.ai/chat/completions",
        #     headers={"Authorization": f"Bearer {key}"},
        #     json={"model": "sonar-pro",
        #           "messages": [{"role": "user", "content": prompt}]},
        #     timeout=60,
        # )
        # resp.raise_for_status()
        # return resp.json()["choices"][0]["message"]["content"]
        raise NotImplementedError("Раскомментируйте боевой вызов Perplexity в _send().")

    raise ValueError(f"Неизвестный провайдер: {provider}")
