# -- Builder stage -----------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# -- Runtime stage -----------------------------------------------------------
FROM python:3.13-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY main.py database.py models.py schemas.py ./
COPY crud/ crud/
COPY services/ services/
COPY templates/ templates/
COPY static/ static/

ENV PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL=postgresql+asyncpg://booktrackerAdmin:changeme@localhost:5432/booktrackerdb

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
