FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY ui ./ui
COPY benchmarks ./benchmarks
COPY docs ./docs
COPY demo ./demo

RUN uv sync --locked --no-dev

EXPOSE 8000 7860

CMD ["uv", "run", "uvicorn", "app.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
