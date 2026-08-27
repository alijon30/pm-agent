FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /srv
ENV UV_PROJECT_ENVIRONMENT=/srv/.venv PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
COPY fixtures ./fixtures
RUN uv sync --frozen --no-dev
ENV PATH="/srv/.venv/bin:$PATH" PORT=8080
CMD ["sh", "-c", "uvicorn app.main:create_default_app --factory --host 0.0.0.0 --port ${PORT}"]
