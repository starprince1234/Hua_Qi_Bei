# HUAQIBEI 部署与上线手册（按门禁顺序）

## 0. 顺序门禁（必须按序）
1. 接口预留完成（`/model/v1/*`）
2. 接口对齐检查完成（见 `docs/reports/2026-03-05-interface-alignment-report.md`）
3. 本地 E2E 100% 通过（见 `docs/reports/2026-03-05-e2e-report.md`）
4. 才允许镜像推送
5. 才允许生产部署

---

## 1) 模型接口占位连通性 curl（仅连通，不测业务）
```bash
curl -i http://localhost:18000/model/v1/health
curl -i http://localhost:18000/model/v1/metadata
curl -i http://localhost:18000/model/v1/schema
curl -i -X POST http://localhost:18000/model/v1/predict/returns \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: req_connectivity" \
  -d '{
    "request_id":"req_connectivity",
    "as_of":"2026-03-05",
    "horizon":3,
    "quantiles":[0.05,0.5,0.95],
    "target":"log_return",
    "feature_names":["f1"],
    "timestamps":["2026-03-01"],
    "X":[[1.0]],
    "model_version":"m1",
    "feature_config_version":"fc1",
    "scaler_version":"s1"
  }'
```

---

## 2) 本地一键启动（Docker Desktop）
在项目根目录执行：
```bash
docker compose up -d --build
docker compose ps
```
- 前端：http://localhost:13000
- 后端：http://localhost:18000

---

## 3) 本地 E2E 快速验证命令
```bash
curl -i http://localhost:18000/api/v1/health
curl -i http://localhost:18000/model/v1/health
```

上传+预测+报告（PowerShell 示例，Windows）：
```powershell
$upload = curl.exe -s -X POST "http://localhost:18000/api/v1/upload" `
  -F "file=@backend/huaqibei/oil-risk-orchestrator/temp_oil.csv" `
  -F "dataset_type=oil_price_factors" -F "timezone=UTC" -F "frequency=D" `
  -F "strict_mode=false" -F "encoding=utf-8" | ConvertFrom-Json

$predictBody = @{ file_id=$upload.data.file_id; horizon=5; target='log_return'; quantiles=@(0.05,0.5,0.95); industries=@('aviation','shipping','chemical'); include_explainability=$true; include_knowledge_graph=$true; include_report=$true; report_style='banking' } | ConvertTo-Json -Depth 8
$predict = Invoke-RestMethod -Uri "http://localhost:18000/api/v1/predict" -Method Post -ContentType "application/json" -Body $predictBody
Invoke-RestMethod -Uri "http://localhost:18000/api/v1/report/$($predict.data.report.report_id)" -Method Get
```

---

## 4) 镜像推送（仅 E2E 通过后）
```bash
# 登录 DockerHub
docker login

# 构建（可复用 compose）
docker compose build

# 打 tag
docker tag huaqibei-backend:latest  starprince/huaqibei-backend:v1
docker tag huaqibei-frontend:latest starprince/huaqibei-frontend:v1

# 推送
docker push starprince/huaqibei-backend:v1
docker push starprince/huaqibei-frontend:v1
```

---

## 5) 生产部署（云服务器）
将 `deploy/production` 上传到服务器并配置 `.env`：
```bash
cp .env.example .env
# 编辑 .env 填写 MODEL_API_URL / 密钥等
```

启动：
```bash
docker compose -f docker-compose.prod.yml --env-file .env pull
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

连通性验证：
```bash
curl -i http://<你的域名>/healthz
curl -i http://<你的域名>/api/health
curl -i http://<你的域名>/model/v1/health
```

> 说明：`/api/*` 由 Nginx 反向代理到后端 `/api/v1/*`；`/` 代理到前端；已包含端口映射与域名反代骨架。
