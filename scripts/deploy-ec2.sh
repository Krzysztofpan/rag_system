#!/usr/bin/env bash
# Pull ECR images and recreate the prod stack. Secrets stay in ENV_FILE on the host
# (default /opt/rag/.env), not in the Actions checkout — git clean would delete them.
# Requires: Docker Compose v2 plugin, AWS CLI, EC2 instance profile
# with ecr:GetAuthorizationToken + ecr:BatchGetImage / GetDownloadUrlForLayer.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${BACKEND_IMAGE:?Set BACKEND_IMAGE to the backend ECR URI:tag}"
: "${FRONTEND_IMAGE:?Set FRONTEND_IMAGE to the frontend ECR URI:tag}"
: "${AWS_REGION:?Set AWS_REGION}"

ENV_FILE="${ENV_FILE:-/opt/rag/.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing $ENV_FILE — copy .env.example, fill secrets, set DOMAIN and ACME_EMAIL" >&2
  exit 1
fi
if [[ "$ENV_FILE" != "$ROOT/.env" ]]; then
  ln -sfn "$ENV_FILE" "$ROOT/.env"
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose (v2 plugin) is required; the old docker-compose binary is not enough" >&2
  exit 1
fi

registry="${BACKEND_IMAGE%%/*}"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$registry"

export BACKEND_IMAGE FRONTEND_IMAGE
compose=(docker compose -f docker-compose.prod.yml)
# Redis image/config does not change with app deploys. Pulling redis:7-alpine
# every time can move the tag and recreate the broker (SSE, rate-limit counters).
app_services=(backend ingest-worker frontend)

"${compose[@]}" pull "${app_services[@]}"
"${compose[@]}" run --rm --no-deps backend alembic upgrade head
"${compose[@]}" up -d --no-build --remove-orphans --wait --wait-timeout 180 \
  "${app_services[@]}"
