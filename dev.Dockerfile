# Based on these resources:
# - https://docs.astral.sh/uv/guides/integration/docker/ 
# - https://github.com/astral-sh/uv-docker-example/blob/main/Dockerfile
# - https://docs.astral.sh/uv/guides/integration/fastapi/
# - https://github.com/astral-sh/uv-fastapi-example/blob/main/Dockerfile
# - https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile

# Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

ENV PYTHONPATH=/api
ENV UV_COMPILE_BYTECODE=1
ENV PATH="$PATH:/api/.venv/bin"

COPY ./pyproject.toml ./uv.lock ./scripts/ ./alembic.ini ./prestart.sh ./Makefile ./run_local.sh /api/
COPY ./app /api/app

RUN cd /api && uv sync --frozen --no-cache

WORKDIR /api

CMD ["make", "run_local", "PRESTART=true"]
