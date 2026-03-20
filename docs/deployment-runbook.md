# Oil Risk Orchestrator — Deployment Runbook

> **Document version:** 1.0  
> **Last updated:** 2026-03-05  
> **Owner:** Platform Engineering

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Backend Deploy](#3-backend-deploy)
4. [Frontend Deploy](#4-frontend-deploy)
5. [Health Checks](#5-health-checks)
6. [Rollback](#6-rollback)
7. [Monitoring](#7-monitoring)

---

## 1. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.13 | Use `pyenv` or system package manager |
| Node.js | ≥ 20 LTS | Required for frontend build |
| Docker | ≥ 24 | Optional but recommended for containerised deploy |
| Git | any | For cloning the repository |

Ensure the following environment variables are available before deploying:

```
MODEL_SERVICE_URL   # URL of the remote model microservice
API_KEY             # (Optional) Secret key for X-API-Key header auth
BACKEND_URL         # Used by Next.js proxy (e.g. http://orchestrator:8000)
LLM_API_KEY         # (Optional) OpenAI-compatible LLM key for AI insights
```

---

## 2. Environment Setup

### Clone the repository

```bash
git clone https://github.com/your-org/Hua_Qi_Bei.git
cd Hua_Qi_Bei
```

### Backend Python environment

```bash
cd backend/huaqibei/oil-risk-orchestrator
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn[standard] pydantic pydantic-settings \
            httpx pandas numpy openpyxl pyarrow
```

### Frontend Node environment

```bash
cd frontend
npm ci
```

### Create `.env` file (backend)

```dotenv
MODEL_SERVICE_URL=http://model-service:8001
API_KEY=your-secret-key
LOG_LEVEL=INFO
UPLOAD_DIR=/var/oil_risk/uploads
MAX_UPLOAD_MB=50
CORS_ORIGINS=["https://your-frontend.example.com"]
LLM_API_KEY=sk-...
```

---

## 3. Backend Deploy

### Run with Uvicorn (development)

```bash
cd backend/huaqibei/oil-risk-orchestrator
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run with Gunicorn + Uvicorn workers (production)

```bash
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  -b 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### Docker (recommended)

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings \
        httpx pandas numpy openpyxl pyarrow
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t oil-risk-orchestrator:latest .
docker run -d \
  --name orchestrator \
  -p 8000:8000 \
  --env-file .env \
  -v /var/oil_risk/uploads:/tmp/oil_risk_uploads \
  oil-risk-orchestrator:latest
```

---

## 4. Frontend Deploy

### Development server

```bash
cd frontend
BACKEND_URL=http://localhost:8000 npm run dev
```

### Production build

```bash
cd frontend
npm run build
npm start
```

### Vercel (recommended for production)

```bash
npx vercel --prod
```

Set the `BACKEND_URL` environment variable in the Vercel project settings to point to your deployed backend.

---

## 5. Health Checks

### Backend

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "1.0.0", ...}
```

### Model service placeholder

```bash
curl http://localhost:8000/model-placeholder/status
```

### Full smoke test

```bash
cd backend/huaqibei/oil-risk-orchestrator
python test_api.py --base-url http://localhost:8000
```

---

## 6. Rollback

### Docker rollback

```bash
# List available images
docker images oil-risk-orchestrator

# Stop current container
docker stop orchestrator && docker rm orchestrator

# Start previous image
docker run -d \
  --name orchestrator \
  -p 8000:8000 \
  --env-file .env \
  oil-risk-orchestrator:<previous-tag>
```

### Git rollback

```bash
git log --oneline -10        # find the target commit
git checkout <commit-sha>    # detach HEAD to stable commit
# rebuild and redeploy
```

---

## 7. Monitoring

### Structured logs

The backend emits JSON-structured logs to stdout. Pipe to your log aggregator (e.g. Datadog, Elasticsearch):

```bash
docker logs -f orchestrator | jq .
```

Key log fields:

| Field | Description |
|---|---|
| `level` | Log level: INFO / WARNING / ERROR |
| `logger` | Python module name |
| `message` | Human-readable message |
| `file_id` | Uploaded file being processed |
| `horizon` | Prediction horizon |

### Metrics (recommended additions)

- Expose `/metrics` via `prometheus-fastapi-instrumentator`
- Track: `http_request_duration_seconds`, `upload_count_total`, `predict_count_total`

### Alerts

| Alert | Threshold | Action |
|---|---|---|
| Backend non-200 rate | > 5 % over 5 min | Page on-call, check model service connectivity |
| Upload dir disk usage | > 80 % | Archive old uploads, expand storage |
| Model service latency | > 30 s | Check model service scaling, activate placeholder |
