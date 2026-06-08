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
```powershell
doppler run -- powershell -ExecutionPolicy Bypass -File .\scripts\start_autodl_tunnel.ps1
doppler run -- docker compose up -d --build
docker compose ps
```
- 前端：http://localhost:13000
- 后端：http://localhost:18000
- 模型隧道：http://127.0.0.1:6006；容器内通过 `http://host.docker.internal:6006/v1` 访问。

如果 Windows 把 `13000` 放进 excluded port range，本地 compose 使用 Doppler 字段 `FRONTEND_PORT`，默认 `13289`。

本地 Docker 会从 Doppler 注入 `MODEL_API_URL`、`USE_MOCK_MODEL` 和 `AUTODL_*`，不要创建 `.env` 保存真实密码。

### Doppler 字段（本地 dev_personal）

| Key | 推荐值/来源 |
| --- | --- |
| `USE_MOCK_MODEL` | `false`，让上传 Excel 后调用 AutoDL 真实模型 |
| `MODEL_API_URL` | `http://host.docker.internal:6006/v1` |
| `MODEL_API_TIMEOUT` | `120` |
| `MODEL_API_MAX_RETRIES` | `2` |
| `MODEL_API_KEY` | 模型服务如果不需要鉴权可留空 |
| `MODEL_API_MODEL_ID` | `oil_vol_model` |
| `AUTODL_SSH_HOST` | AutoDL SSH 命令里的主机，如 `region-9.autodl.pro` |
| `AUTODL_SSH_PORT` | AutoDL SSH 命令里的端口，如 `50954` |
| `AUTODL_SSH_USER` | AutoDL SSH 命令里的用户，如 `root` |
| `AUTODL_SSH_PASSWORD` | AutoDL SSH 密码，只放 Doppler |
| `AUTODL_LOCAL_PORT` | `6006` |
| `AUTODL_REMOTE_HOST` | `127.0.0.1` |
| `AUTODL_REMOTE_PORT` | 远端模型实际监听端口，通常 `6006` |
| `AUTODL_PLINK_PATH` | Windows PuTTY plink 路径，如 `D:\PuTTY\plink.exe` |

---

## 3) 本地 E2E 快速验证命令
```bash
curl -i http://localhost:18000/api/v1/health
curl -i http://localhost:18000/model/v1/health
```

上传+预测+报告（PowerShell 示例，Windows）。请把 `sample.csv` 替换为本地测试数据文件，不要使用或提交含敏感业务数据的真实文件：
```powershell
$upload = curl.exe -s -X POST "http://localhost:18000/api/v1/upload" `
  -F "file=@D:\VScodeProjects\Hua_Qi_Bei\test1.xlsx" `
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
# 编辑 .env 填写 MODEL_API_URL / MODEL_API_KEY / LLM_API_KEY / AUTODL_SSH_PASSWORD 等
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
