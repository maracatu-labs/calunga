FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project --extra dev

COPY . .
RUN uv sync --extra dev

ENV HF_HOME=/opt/hf_cache
RUN mkdir -p /opt/hf_cache && \
    /app/.venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

FROM python:3.12-slim-bookworm

WORKDIR /app

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app \
    && mkdir -p /tmp/dagster /opt/hf_cache \
    && chown appuser:appuser /tmp/dagster /opt/hf_cache

COPY --chown=appuser:appuser --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appuser --from=builder /app/app ./app
COPY --chown=appuser:appuser --from=builder /app/pipeline ./pipeline
COPY --chown=appuser:appuser --from=builder /app/migrations ./migrations
COPY --chown=appuser:appuser --from=builder /app/tests ./tests
COPY --chown=appuser:appuser --from=builder /app/pyproject.toml ./pyproject.toml
COPY --chown=appuser:appuser --from=builder /opt/hf_cache /opt/hf_cache

ENV PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/opt/hf_cache

EXPOSE 8000

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
