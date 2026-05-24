#!/usr/bin/env bash
set -euo pipefail

BASE="/opt/huaqibei/deploy/production/release_v2-gold-20260326-llmfin-en-r1"
TS="$(date +%Y%m%d%H%M%S)"
BACKUP_DIR="$BASE/_backup_$TS"

mkdir -p "$BACKUP_DIR/backend" "$BACKUP_DIR/frontend"

cp -a "$BASE/backend/huaqibei/oil-risk-orchestrator/app/core/settings.py" "$BACKUP_DIR/backend/"
cp -a "$BASE/backend/huaqibei/oil-risk-orchestrator/app/services/risk_service.py" "$BACKUP_DIR/backend/"
cp -a "$BASE/backend/huaqibei/oil-risk-orchestrator/app/knowledge_graph/graph_query.py" "$BACKUP_DIR/backend/"
cp -a "$BASE/backend/huaqibei/oil-risk-orchestrator/app/api/routes/predict.py" "$BACKUP_DIR/backend/"
cp -a "$BASE/backend/huaqibei/oil-risk-orchestrator/app/services/ai_insight_service.py" "$BACKUP_DIR/backend/"
cp -a "$BASE/frontend/src/components/ResultDisplay.tsx" "$BACKUP_DIR/frontend/"

echo "BACKUP_DIR=$BACKUP_DIR"

cd "$BASE/backend/huaqibei/oil-risk-orchestrator"
docker build -f docker/Dockerfile -t starprince123/huaqibei-backend:v2-gold-20260326-llmfin-en-r3 .

echo "BACKEND_BUILD_DONE"

cd "$BASE/frontend"
docker build -f Dockerfile -t starprince123/huaqibei-frontend:v2-gold-20260326-llmfin-en-r3 --build-arg NEXT_PUBLIC_API_URL=/api .

echo "FRONTEND_BUILD_DONE"

cd /opt/huaqibei/deploy/production
if grep -q '^BACKEND_TAG=' .env; then
  sed -i 's/^BACKEND_TAG=.*/BACKEND_TAG=v2-gold-20260326-llmfin-en-r3/' .env
else
  echo 'BACKEND_TAG=v2-gold-20260326-llmfin-en-r3' >> .env
fi
if grep -q '^FRONTEND_TAG=' .env; then
  sed -i 's/^FRONTEND_TAG=.*/FRONTEND_TAG=v2-gold-20260326-llmfin-en-r3/' .env
else
  echo 'FRONTEND_TAG=v2-gold-20260326-llmfin-en-r3' >> .env
fi

docker save starprince123/huaqibei-backend:v2-gold-20260326-llmfin-en-r3 -o backend_v2-gold-20260326-llmfin-en-r3.tar
docker save starprince123/huaqibei-frontend:v2-gold-20260326-llmfin-en-r3 -o frontend_v2-gold-20260326-llmfin-en-r3.tar

docker compose --env-file .env -f docker-compose.prod.yml up -d --force-recreate
sleep 6
docker compose --env-file .env -f docker-compose.prod.yml ps

echo "DEPLOY_DONE"
