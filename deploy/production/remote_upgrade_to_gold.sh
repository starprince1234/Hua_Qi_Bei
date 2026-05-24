#!/usr/bin/env bash
set -euo pipefail

cd /opt/huaqibei/deploy/production

docker load -i huaqibei-backend-v2-gold-20260314.tar
docker load -i huaqibei-frontend-v2-gold-20260314.tar

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

sed -i "s/^BACKEND_TAG=.*/BACKEND_TAG=v2-gold-20260314/" .env
sed -i "s/^FRONTEND_TAG=.*/FRONTEND_TAG=v2-gold-20260314/" .env

if grep -q '^NEXT_PUBLIC_API_URL=' .env; then
  sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=/api|" .env
else
  echo "NEXT_PUBLIC_API_URL=/api" >> .env
fi

docker compose --env-file .env -f docker-compose.prod.yml up -d --force-recreate

docker compose --env-file .env -f docker-compose.prod.yml ps
