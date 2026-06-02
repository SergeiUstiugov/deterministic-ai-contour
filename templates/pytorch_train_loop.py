# -*- coding: utf-8 -*-
"""
Пример шаблона для «дыры» в покрытии модели.

Когда бенчмарк показал, что модель не справляется с задачей (низкий pass-rate),
вместо генерации с нуля используется проверенный шаблон. На один шаблон уходит
~30 минут: описание -> генерация -> smoke test -> чеклист обязательных элементов.

Здесь — шаблон обучающего цикла PyTorch как образец структуры.
"""

# --- метаданные шаблона ---
TEMPLATE_META = {
    "id": "pytorch_train_loop",
    "title": "Базовый обучающий цикл PyTorch",
    "difficulty_covered": "medium",
    # required_substrings — детерминированный чеклист: эти элементы ОБЯЗАНЫ присутствовать
    "required_substrings": ["torch", "optimizer", "loss", "backward", "step"],
}

TEMPLATE_CODE = '''\
import torch
from torch import nn


def train(model: nn.Module, loader, epochs: int = 10, lr: float = 1e-3, device: str = "cpu"):
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()
    for epoch in range(epochs):
        model.train()
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = loss_fn(out, y)
            loss.backward()
            optimizer.step()
    return model
'''


def smoke_test() -> bool:
    """Минимальная детерминированная проверка: шаблон парсится и содержит чеклист."""
    import ast
    ast.parse(TEMPLATE_CODE)  # синтаксис
    return all(s in TEMPLATE_CODE for s in TEMPLATE_META["required_substrings"])


if __name__ == "__main__":
    print("smoke test:", "OK" if smoke_test() else "FAIL")
