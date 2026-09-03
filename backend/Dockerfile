# syntax=docker/dockerfile:1
# Shared app image: API (default CMD) and ingest-worker (compose overrides command).

FROM python:3.12-slim-bookworm

ARG TORCH_VERSION=2.13.0+cpu
ARG TORCHVISION_VERSION=0.28.0+cpu
ARG OPENCV_HEADLESS_VERSION=5.0.0.93

ENV UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_HTTP_TIMEOUT=300 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# System libs for OCR / native wheels; non-root runtime user.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

COPY pyproject.toml uv.lock ./
COPY docker/uv-skip-cuda.txt /tmp/uv-skip-cuda.txt

# Lockfile wants CUDA torch + GUI opencv. Skip them, then install CPU / headless wheels.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=ghcr.io/astral-sh/uv:0.8,source=/uv,target=/usr/local/bin/uv \
    uv_skip="$(grep -vE '^(#|$)' /tmp/uv-skip-cuda.txt | sed 's/^/--no-install-package /')" \
    && uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python setuptools wheel \
    && uv sync --frozen --no-dev --no-install-project $uv_skip \
    && uv pip install --python /app/.venv/bin/python \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==${TORCH_VERSION}" "torchvision==${TORCHVISION_VERSION}" \
    && uv pip install --python /app/.venv/bin/python \
        "opencv-python-headless==${OPENCV_HEADLESS_VERSION}" \
    && find /app/.venv \( \
        -type d -name '__pycache__' \
        -o -type d -name 'tests' \
        -o -type d -name 'test' \
    \) -prune -exec rm -rf {} + \
    && find /app/.venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete \
    && rm -rf /tmp/*

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini main.py ./

RUN mkdir -p /var/rag/uploads /var/rag/hf /var/rag/cache \
    && chown -R appuser:appuser /var/rag

# Runtime-only: do not set these before uv sync or caches land in the image.
ENV HF_HOME=/var/rag/hf \
    XDG_CACHE_HOME=/var/rag/cache \
    UPLOAD_TEMP_DIR=/var/rag/uploads

USER appuser
EXPOSE 8000

# Redis holds SSE / run locks / rate limits, so HTTP can use multiple workers.
ENV UVICORN_WORKERS=2
# Caddy terminates TLS and proxies over HTTP. Without these flags uvicorn
# ignores X-Forwarded-Proto and 307s /conversations → http://… (mixed content).
CMD ["sh", "-c", "exec uvicorn app.app:app --host 0.0.0.0 --port 8000 --workers \"$UVICORN_WORKERS\" --proxy-headers --forwarded-allow-ips '*'"]
