#!/usr/bin/env bash
set -e
cd /opt/huaqibei/deploy/production

echo '===ENV_KEY_PRESENCE===' 
for k in MODEL_API_KEY MODEL_API_URL MODEL_API_MODEL_ID USE_MOCK_MODEL; do
  v=$(grep -E "^${k}=" .env | sed -E "s/^${k}=//" || true)
  if [ -n "$v" ]; then
    echo "$k=SET(len=${#v})"
  else
    echo "$k=EMPTY"
  fi
done

echo '===CONTAINER_KEY_PRESENCE===' 
docker exec huaqibei_prod-backend-1 /bin/sh -lc '
for k in MODEL_API_KEY MODEL_API_URL MODEL_API_MODEL_ID USE_MOCK_MODEL; do
  v=$(printenv "$k")
  if [ -n "$v" ]; then
    echo "$k=SET(len=${#v})"
  else
    echo "$k=EMPTY"
  fi
done
'
