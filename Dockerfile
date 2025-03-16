# Based on these resources:
# - https://docs.astral.sh/uv/guides/integration/docker/ 
# - https://github.com/astral-sh/uv-docker-example/blob/main/Dockerfile
# - https://docs.astral.sh/uv/guides/integration/fastapi/
# - https://github.com/astral-sh/uv-fastapi-example/blob/main/Dockerfile
# - https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile

# Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONPATH=/app
ENV UV_COMPILE_BYTECODE=1
ENV PATH="$PATH:/app/.venv/bin"

COPY ./pyproject.toml ./uv.lock ./scripts/ ./alembic.ini ./prestart.sh /app/
COPY ./app /app/app

RUN cd /app && uv sync --frozen --no-cache

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
