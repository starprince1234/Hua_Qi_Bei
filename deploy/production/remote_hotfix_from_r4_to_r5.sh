#!/usr/bin/env bash
set -euo pipefail

REL_BASE="/opt/huaqibei/deploy/production/release_v2-gold-20260326-llmfin-en-r1"
WORKDIR="/opt/huaqibei/deploy/production/.hotfix_r5"
PROD_DIR="/opt/huaqibei/deploy/production"

mkdir -p "$WORKDIR/backend" "$WORKDIR/frontend"

cp -f "$REL_BASE/backend/huaqibei/oil-risk-orchestrator/app/services/report_service.py" "$WORKDIR/backend/report_service.py"

cat > "$WORKDIR/backend/Dockerfile.hotfix" <<'EOF'
FROM starprince123/huaqibei-backend:v2-gold-20260326-llmfin-en-r4
COPY report_service.py /app/app/services/report_service.py
EOF

docker build -f "$WORKDIR/backend/Dockerfile.hotfix" -t starprince123/huaqibei-backend:v2-gold-20260326-llmfin-en-r5 "$WORKDIR/backend"

echo "BACKEND_HOTFIX_BUILD_DONE"

cp -f "$REL_BASE/frontend/src/components/PredictForm.tsx" "$WORKDIR/frontend/PredictForm.tsx"

cat > "$WORKDIR/frontend/Dockerfile.hotfix" <<'EOF'
FROM starprince123/huaqibei-frontend:v2-gold-20260326-llmfin-en-r4
COPY PredictForm.tsx /app/src/components/PredictForm.tsx
WORKDIR /app
RUN rm -rf .next && npm run build
EOF

docker build -f "$WORKDIR/frontend/Dockerfile.hotfix" -t starprince123/huaqibei-frontend:v2-gold-20260326-llmfin-en-r5 "$WORKDIR/frontend"

echo "FRONTEND_HOTFIX_BUILD_DONE"

cd "$PROD_DIR"
if grep -q '^BACKEND_TAG=' .env; then
  sed -i 's/^BACKEND_TAG=.*/BACKEND_TAG=v2-gold-20260326-llmfin-en-r5/' .env
else
  echo 'BACKEND_TAG=v2-gold-20260326-llmfin-en-r5' >> .env
fi
if grep -q '^FRONTEND_TAG=' .env; then
  sed -i 's/^FRONTEND_TAG=.*/FRONTEND_TAG=v2-gold-20260326-llmfin-en-r5/' .env
else
  echo 'FRONTEND_TAG=v2-gold-20260326-llmfin-en-r5' >> .env
fi

docker compose --env-file .env -f docker-compose.prod.bt.yml up -d --force-recreate
sleep 8
docker compose --env-file .env -f docker-compose.prod.bt.yml ps

curl -fsS http://127.0.0.1:18080/healthz

echo "DEPLOY_R5_DONE"
