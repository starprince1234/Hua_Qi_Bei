#!/usr/bin/env bash
set -euo pipefail

REL_BASE="/opt/huaqibei/deploy/production/release_v2-gold-20260326-llmfin-en-r1"
WORKDIR="/opt/huaqibei/deploy/production/.hotfix_r3"
PROD_DIR="/opt/huaqibei/deploy/production"

mkdir -p "$WORKDIR/backend" "$WORKDIR/frontend"

cp -f "$REL_BASE/backend/huaqibei/oil-risk-orchestrator/app/core/settings.py" "$WORKDIR/backend/settings.py"
cp -f "$REL_BASE/backend/huaqibei/oil-risk-orchestrator/app/services/risk_service.py" "$WORKDIR/backend/risk_service.py"
cp -f "$REL_BASE/backend/huaqibei/oil-risk-orchestrator/app/knowledge_graph/graph_query.py" "$WORKDIR/backend/graph_query.py"
cp -f "$REL_BASE/backend/huaqibei/oil-risk-orchestrator/app/api/routes/predict.py" "$WORKDIR/backend/predict.py"
cp -f "$REL_BASE/backend/huaqibei/oil-risk-orchestrator/app/services/ai_insight_service.py" "$WORKDIR/backend/ai_insight_service.py"

cat > "$WORKDIR/backend/Dockerfile.hotfix" <<'EOF'
FROM starprince123/huaqibei-backend:v2-gold-20260326-llmfin-en-r2
COPY settings.py /app/app/core/settings.py
COPY risk_service.py /app/app/services/risk_service.py
COPY graph_query.py /app/app/knowledge_graph/graph_query.py
COPY predict.py /app/app/api/routes/predict.py
COPY ai_insight_service.py /app/app/services/ai_insight_service.py
EOF

docker build -f "$WORKDIR/backend/Dockerfile.hotfix" -t starprince123/huaqibei-backend:v2-gold-20260326-llmfin-en-r3 "$WORKDIR/backend"

echo "BACKEND_HOTFIX_BUILD_DONE"

cp -f "$REL_BASE/frontend/src/components/ResultDisplay.tsx" "$WORKDIR/frontend/ResultDisplay.tsx"
cat > "$WORKDIR/frontend/Dockerfile.hotfix" <<'EOF'
FROM starprince123/huaqibei-frontend:v2-gold-20260326-llmfin-en-r2
COPY ResultDisplay.tsx /app/src/components/ResultDisplay.tsx
WORKDIR /app
RUN rm -rf .next && npm run build
EOF

docker build -f "$WORKDIR/frontend/Dockerfile.hotfix" -t starprince123/huaqibei-frontend:v2-gold-20260326-llmfin-en-r3 "$WORKDIR/frontend"

echo "FRONTEND_HOTFIX_BUILD_DONE"

cd "$PROD_DIR"
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

docker compose --env-file .env -f docker-compose.prod.yml up -d --force-recreate
sleep 8
docker compose --env-file .env -f docker-compose.prod.yml ps

curl -fsS http://127.0.0.1/healthz

echo "DEPLOY_R3_DONE"
