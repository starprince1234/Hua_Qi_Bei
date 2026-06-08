#!/usr/bin/env bash
set -euo pipefail

: "${DOPPLER_SECRETS_JSON_B64:?DOPPLER_SECRETS_JSON_B64 is required}"

if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git ca-certificates curl
fi

if ! command -v python3 >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required on the deployment server." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is required on the deployment server." >&2
  exit 1
fi

eval "$(
  python3 -c '
import base64
import json
import os
import shlex

payload = base64.b64decode(os.environ["DOPPLER_SECRETS_JSON_B64"]).decode("utf-8")
secrets = json.loads(payload)
for key, value in secrets.items():
    if key.startswith("DOPPLER_"):
        continue
    if value is None:
        value = ""
    print(f"export {key}={shlex.quote(str(value))}")
'
)"

: "${REPO_URL:?REPO_URL is required}"
: "${DEPLOY_BRANCH:=main}"
: "${DEPLOY_PATH:=/opt/huaqibei/app}"
: "${IMAGE_ARCHIVE:=/tmp/huaqibei-images.tar}"

without_proxy() {
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy "$@"
}

mkdir -p "$(dirname "$DEPLOY_PATH")"

if [ -d "$DEPLOY_PATH/.git" ]; then
  without_proxy git -C "$DEPLOY_PATH" remote set-url origin "$REPO_URL"
  without_proxy git -C "$DEPLOY_PATH" fetch --prune origin "$DEPLOY_BRANCH"
  without_proxy git -C "$DEPLOY_PATH" checkout "$DEPLOY_BRANCH"
  without_proxy git -C "$DEPLOY_PATH" reset --hard "origin/$DEPLOY_BRANCH"
else
  if [ -e "$DEPLOY_PATH" ]; then
    mv "$DEPLOY_PATH" "${DEPLOY_PATH}.bak.$(date +%Y%m%d%H%M%S)"
  fi
  without_proxy git clone --branch "$DEPLOY_BRANCH" "$REPO_URL" "$DEPLOY_PATH"
fi

cd "$DEPLOY_PATH"

if [ -f "$IMAGE_ARCHIVE" ]; then
  docker load -i "$IMAGE_ARCHIVE"
fi

docker compose -f deploy/production/docker-compose.prod.yml up -d --no-build --remove-orphans

docker image prune -f --filter "until=168h" >/dev/null || true

sleep 8
without_proxy curl -fsS http://127.0.0.1/healthz
echo
docker compose -f deploy/production/docker-compose.prod.yml ps
