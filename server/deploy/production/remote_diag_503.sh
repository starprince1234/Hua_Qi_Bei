#!/usr/bin/env bash
set -e

docker logs --tail 120 huaqibei_prod-backend-1 || true
echo '===ENV==='
docker exec huaqibei_prod-backend-1 /bin/sh -lc "env | grep -E 'USE_MOCK_MODEL|MODEL_API_URL|MODEL_API_MODEL_ID|ENVIRONMENT' | sort" || true
echo '===MODEL_CHECK==='
docker exec huaqibei_prod-backend-1 /bin/sh -lc "curl -sS -m 8 -i http://host.docker.internal:6006/v1/models || true" || true
echo '===PORT_6006==='
ss -ltnp | grep 6006 || true
