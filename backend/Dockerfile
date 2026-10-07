# API (FastAPI) e ingestão: a mesma imagem serve para os dois.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN useradd --create-home panoptico && mkdir -p data/raw data/processed \
    && chown -R panoptico data
USER panoptico

EXPOSE 8000
# Aplica as migrações e sobe a API atrás do proxy, que publica em /api.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --root-path /api --proxy-headers --forwarded-allow-ips='*' --workers 2"]
