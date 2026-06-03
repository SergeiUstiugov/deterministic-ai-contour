# Двухконтурный маршрутизатор — образ без внешних зависимостей.
FROM python:3.12-slim

WORKDIR /app
COPY . /app

# По умолчанию: прогон тестов и бенчмарка.
# Переопределяется: docker run --rm two-loop-router python -m checker.engine examples/bad_pump.st
CMD ["sh", "-c", "python -m unittest discover -s tests && python benchmark.py"]
