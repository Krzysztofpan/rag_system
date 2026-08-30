# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

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

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

# PyPI lock pulls CUDA torch + nvidia-* on Linux. Skip those and install CPU wheels.
# RapidOCR depends on GUI opencv-python (Qt/xcb/Mesa). Headless provides the same cv2.
ENV UV_SKIP_CUDA="\
--no-install-package torch \
--no-install-package torchvision \
--no-install-package triton \
--no-install-package cuda-bindings \
--no-install-package cuda-pathfinder \
--no-install-package cuda-toolkit \
--no-install-package nvidia-cublas \
--no-install-package nvidia-cuda-cupti \
--no-install-package nvidia-cuda-nvrtc \
--no-install-package nvidia-cuda-runtime \
--no-install-package nvidia-cudnn-cu13 \
--no-install-package nvidia-cufft \
--no-install-package nvidia-cufile \
--no-install-package nvidia-curand \
--no-install-package nvidia-cusolver \
--no-install-package nvidia-cusparse \
--no-install-package nvidia-cusparselt-cu13 \
--no-install-package nvidia-nccl-cu13 \
--no-install-package nvidia-nvjitlink \
--no-install-package nvidia-nvshmem-cu13 \
--no-install-package nvidia-nvtx \
--no-install-package opencv-python"

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=ghcr.io/astral-sh/uv:0.8,source=/uv,target=/usr/local/bin/uv \
    uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python setuptools wheel \
    && uv sync --frozen --no-dev --no-install-project $UV_SKIP_CUDA \
    && uv pip install --python /app/.venv/bin/python \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0+cpu torchvision==0.28.0+cpu \
    && uv pip install --python /app/.venv/bin/python opencv-python-headless==5.0.0.93 \
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

# Runtime-only: do not set these before uv sync or caches land in the image.
ENV HF_HOME=/tmp/hf \
    XDG_CACHE_HOME=/tmp/cache

USER appuser
EXPOSE 8000
# SSE broker and run locks live in Redis, so HTTP can run in more than one process.
ENV UVICORN_WORKERS=2
CMD ["sh", "-c", "exec uvicorn app.app:app --host 0.0.0.0 --port 8000 --workers \"$UVICORN_WORKERS\""]
