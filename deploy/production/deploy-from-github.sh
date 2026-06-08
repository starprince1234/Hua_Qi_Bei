#!/usr/bin/env bash
set -euo pipefail

: "${DOPPLER_TOKEN:?DOPPLER_TOKEN is required}"
: "${REPO_URL:?REPO_URL is required}"
: "${DEPLOY_BRANCH:=main}"
: "${DEPLOY_PATH:=/opt/huaqibei/app}"

export DOPPLER_TOKEN

if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git ca-certificates curl
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required on the deployment server." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is required on the deployment server." >&2
  exit 1
fi

if ! command -v doppler >/dev/null 2>&1; then
  curl -Ls https://cli.doppler.com/install.sh | bash
fi

mkdir -p "$(dirname "$DEPLOY_PATH")"

if [ -d "$DEPLOY_PATH/.git" ]; then
  git -C "$DEPLOY_PATH" remote set-url origin "$REPO_URL"
  git -C "$DEPLOY_PATH" fetch --prune origin "$DEPLOY_BRANCH"
  git -C "$DEPLOY_PATH" checkout "$DEPLOY_BRANCH"
  git -C "$DEPLOY_PATH" reset --hard "origin/$DEPLOY_BRANCH"
else
  if [ -e "$DEPLOY_PATH" ]; then
    mv "$DEPLOY_PATH" "${DEPLOY_PATH}.bak.$(date +%Y%m%d%H%M%S)"
  fi
  git clone --branch "$DEPLOY_BRANCH" "$REPO_URL" "$DEPLOY_PATH"
fi

cd "$DEPLOY_PATH"

doppler run --project huaqibei --config prd -- \
  docker compose -f deploy/production/docker-compose.prod.yml build

doppler run --project huaqibei --config prd -- \
  docker compose -f deploy/production/docker-compose.prod.yml up -d --remove-orphans

docker image prune -f --filter "until=168h" >/dev/null || true

sleep 8
curl -fsS http://127.0.0.1/healthz
echo
docker compose -f deploy/production/docker-compose.prod.yml ps
