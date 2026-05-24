#!/usr/bin/env bash
set -euo pipefail

cd /opt/huaqibei/deploy/production

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

sed -i 's/^BACKEND_TAG=.*/BACKEND_TAG=v2-gold-20260314/' .env
sed -i 's/^FRONTEND_TAG=.*/FRONTEND_TAG=v2-gold-20260314/' .env

if grep -q '^NEXT_PUBLIC_API_URL=' .env; then
  sed -i 's|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=/api|' .env
else
  echo 'NEXT_PUBLIC_API_URL=/api' >> .env
fi

if ! grep -q '^AUTODL_SSH_PASSWORD=.' .env; then
  echo "请先在 .env 中填写 AUTODL_SSH_PASSWORD，再重新执行部署脚本。"
  exit 1
fi

chmod +x setup_autodl_tunnel.sh deploy.sh bootstrap_and_deploy.sh
./deploy.sh

docker compose --env-file .env -f docker-compose.prod.yml ps
