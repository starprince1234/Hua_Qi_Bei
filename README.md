# Hua Qi Bei Oil Risk Intelligence

Hua Qi Bei Oil Risk Intelligence 是一个油价风险预测与行业冲击分析系统。项目由 FastAPI 编排后端和 Next.js 可视化前端组成，支持上传油价相关数据、调用模型服务生成预测、展示因子贡献、行业传导路径和结构化风险报告。

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [常用命令](#常用命令)
- [测试](#测试)
- [构建](#构建)
- [部署](#部署)
- [Docker 运行方式](#docker-运行方式)
- [API 文档](#api-文档)
- [数据库说明](#数据库说明)
- [复现检查清单](#复现检查清单)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [License](#license)

## 功能特性

- 上传 CSV、XLSX、Parquet 数据文件，并进行字段校验、预览和标准化处理。
- 调用油价模型服务，生成多周期油价/收益率预测、置信区间和风险分级。
- 输出因子贡献、行业冲击、知识图谱传导路径和结构化风险报告。
- 前端提供上传、预测配置、结果图表和报告展示流程。
- 支持本地开发、Docker Compose 联调和生产 Docker Compose + Nginx 部署。

## 技术栈

- 前端：Next.js 16、React 19、TypeScript、Tailwind CSS 4、Framer Motion、Recharts
- 后端：Python、FastAPI、Uvicorn、Pydantic Settings、httpx
- 数据处理：pandas、pyarrow、openpyxl
- AI / LLM：OpenAI SDK，兼容 SiliconFlow / OpenAI 风格 Chat Completions API
- 部署：Docker、Docker Compose、Nginx

## 项目结构

```text
.
├── backend/
│   └── huaqibei/
│       └── oil-risk-orchestrator/
│           ├── app/                    # FastAPI 应用源码
│           ├── data/                   # 运行所需的内置数据与模板
│           ├── docker/                 # 后端 Docker 配置
│           ├── .env.example            # 后端环境变量模板
│           ├── requirements.txt        # Python 依赖
│           └── test_api.py             # 后端 E2E 契约测试脚本
├── deploy/
│   └── production/                     # 生产 Docker Compose、Nginx 和部署脚本
├── docs/                               # 部署记录、接口对齐和交付报告
├── frontend/
│   ├── public/                         # 前端静态资源
│   ├── src/                            # Next.js 应用和组件
│   ├── Dockerfile                      # 前端 Dockerfile
│   ├── package-lock.json               # npm 锁文件
│   └── package.json                    # 前端依赖与脚本
├── .env.example                        # 根目录 Docker Compose 环境变量模板
├── .gitignore                          # 仓库忽略规则
├── docker-compose.yml                  # 本地全栈 Docker Compose
├── model-service-openapi.yaml          # 模型服务 OpenAPI 说明
├── orchestratoropenapi.yaml            # 编排服务 OpenAPI 说明
└── README.md                           # 项目复现说明
```

## 环境要求

- Git
- Docker 和 Docker Compose Plugin
- Node.js >= 20.9，建议 Node.js 20 LTS
- npm，随 Node.js 安装
- Python >= 3.11，建议使用虚拟环境

说明：后端 Dockerfile 使用 `python:3.11-slim`，前端 Dockerfile 使用 `node:20-alpine`。

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/starprince1234/Hua_Qi_Bei.git
cd Hua_Qi_Bei
git checkout 服务器代码
```

如果你使用的是其他 fork 或私有仓库，请把 URL 替换为你的仓库地址。

### 2. 配置环境变量

根目录 Docker Compose 使用根目录 `.env`：

```bash
cp .env.example .env
```

后端本地开发使用后端 `.env`：

```bash
cp backend/huaqibei/oil-risk-orchestrator/.env.example backend/huaqibei/oil-risk-orchestrator/.env
```

本地快速体验可以保留 `USE_MOCK_MODEL=true`，这会使用后端内置的模型占位接口。需要接入真实模型服务时，请配置：

- `MODEL_API_URL`
- `MODEL_API_KEY`，如果模型服务需要鉴权
- `MODEL_API_MODEL_ID`，如果模型服务需要模型 ID

需要 LLM 生成报告时，请配置：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_ID`

不要把真实 `.env`、API Key、token、SSH 密码提交到 GitHub。

### 3. 使用 Docker Compose 启动全栈

```bash
docker compose up --build
```

启动后访问：

- 前端：http://localhost:13000
- 后端健康检查：http://localhost:18000/api/v1/health
- 后端 Swagger 文档：http://localhost:18000/docs

停止服务：

```bash
docker compose down
```

### 4. 本地开发启动后端

```bash
cd backend/huaqibei/oil-risk-orchestrator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Windows PowerShell 之外的 shell 请使用对应的虚拟环境激活命令，例如 macOS/Linux：

```bash
source .venv/bin/activate
```

后端访问地址：

```text
http://localhost:8000
```

### 5. 本地开发启动前端

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认访问：

```text
http://localhost:3000
```

如需让前端指向本地后端，可在启动前设置：

```bash
set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

PowerShell 可使用：

```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

## 环境变量

### 根目录 `.env.example`

| 变量名 | 必填 | 默认值 | 说明 |
| ------ | ---- | ------ | ---- |
| `LLM_API_KEY` | 否 | `your_llm_api_key_here` | Docker Compose 本地运行时传给后端的 LLM Key。生产环境应放入 GitHub Secrets 或部署平台环境变量。 |

### 后端 `backend/huaqibei/oil-risk-orchestrator/.env.example`

| 变量名 | 必填 | 默认值 | 说明 |
| ------ | ---- | ------ | ---- |
| `APP_NAME` | 否 | `Oil Risk Intelligence Orchestrator` | 应用名称 |
| `APP_VERSION` | 否 | `1.0.0` | 应用版本 |
| `DEBUG` | 否 | `false` | 是否启用调试模式 |
| `ENVIRONMENT` | 否 | `development` | 运行环境 |
| `HOST` | 否 | `0.0.0.0` | 后端监听地址 |
| `PORT` | 否 | `8000` | 后端监听端口 |
| `MODEL_API_URL` | 是 | `http://localhost:9000/predict` | 真实模型服务地址；部署时建议作为环境变量配置 |
| `MODEL_API_TIMEOUT` | 否 | `30` | 模型服务请求超时秒数 |
| `MODEL_API_MAX_RETRIES` | 否 | `3` | 模型服务最大重试次数 |
| `MODEL_API_KEY` | 否 | `your_model_api_key_here` | 模型服务 Bearer Token；如启用应放入 GitHub Secrets 或部署平台环境变量 |
| `USE_MOCK_MODEL` | 否 | `true` | 是否使用 mock 模型结果 |
| `LLM_PROVIDER` | 否 | `siliconflow` | LLM Provider 标识 |
| `LLM_BASE_URL` | 否 | `https://api.siliconflow.cn/v1` | OpenAI 兼容 API Base URL |
| `LLM_API_KEY` | 否 | `your_llm_api_key_here` | LLM API Key；如启用应放入 GitHub Secrets 或部署平台环境变量 |
| `LLM_MODEL_ID` | 否 | `Pro/deepseek-ai/DeepSeek-V3.2` | 默认报告模型 |
| `LLM_JSON_MODE` | 否 | `true` | 是否要求 JSON 输出 |
| `LLM_LORA_ID` | 否 | 空 | 可选 LoRA ID |
| `LLM_SEARCH_DISABLE` | 否 | `true` | 是否关闭联网搜索能力 |
| `LLM_ENABLE_THINKING` | 否 | `false` | 是否启用 thinking 参数 |
| `LLM_THINKING_BUDGET` | 否 | `4096` | thinking token 预算 |
| `LLM_TOP_P` | 否 | `0.7` | 采样参数 |
| `LLM_TOP_K` | 否 | `50` | 采样参数 |
| `LLM_FREQUENCY_PENALTY` | 否 | `0.2` | 频率惩罚 |
| `LLM_MAX_TOKENS` | 否 | `1500` | 输出 token 上限 |
| `LLM_TEMPERATURE` | 否 | `0.3` | 温度参数 |
| `LLM_TIMEOUT` | 否 | `60` | LLM 请求超时秒数 |
| `LLM_MAX_RETRIES` | 否 | `1` | LLM 最大重试次数 |
| `INDUSTRY_LLM_ENABLED` | 否 | `false` | 是否启用行业分析 LLM 增强 |
| `LLM_MODEL_RISK_LEVEL` | 否 | 示例模型名 | 风险等级模块模型 |
| `LLM_MODEL_INDUSTRY_IMPACT` | 否 | 示例模型名 | 行业影响模块模型 |
| `LLM_MODEL_KNOWLEDGE_GRAPH` | 否 | 示例模型名 | 知识图谱模块模型 |
| `LLM_MODEL_REPORT_SUMMARY` | 否 | 示例模型名 | 报告摘要模块模型 |
| `LLM_MODEL_FINANCING_RECOMMENDATION` | 否 | 示例模型名 | 融资建议模块模型 |
| `RISK_LOW_THRESHOLD` | 否 | `0.03` | 低风险阈值 |
| `RISK_MEDIUM_THRESHOLD` | 否 | `0.07` | 中风险阈值 |

### 生产部署 `deploy/production/.env.example`

| 变量名 | 必填 | 默认值 | 说明 |
| ------ | ---- | ------ | ---- |
| `BACKEND_TAG` | 是 | `v1` | 后端镜像 tag |
| `FRONTEND_TAG` | 是 | `v1` | 前端镜像 tag |
| `MODEL_API_URL` | 是 | `http://host.docker.internal:6006/v1` | 生产模型服务地址 |
| `MODEL_API_KEY` | 否 | 空 | 模型服务密钥，建议放入 GitHub Secrets 或服务器 `.env` |
| `MODEL_API_MODEL_ID` | 否 | `oil_vol_model` | 模型 ID |
| `LLM_API_KEY` | 否 | `your_llm_api_key_here` | LLM 密钥，建议放入 GitHub Secrets 或服务器 `.env` |
| `LLM_BASE_URL` | 否 | `https://api.siliconflow.cn/v1` | LLM API Base URL |
| `LLM_MODEL_ID` | 否 | 示例模型名 | LLM 模型 ID |
| `NEXT_PUBLIC_API_URL` | 否 | `/api` | 前端公开 API 基址，不是密钥 |
| `AUTODL_SSH_HOST` | 是 | 示例主机 | AutoDL SSH 隧道主机 |
| `AUTODL_SSH_PORT` | 是 | 示例端口 | AutoDL SSH 端口 |
| `AUTODL_SSH_USER` | 是 | `root` | AutoDL SSH 用户 |
| `AUTODL_SSH_PASSWORD` | 是 | 空 | AutoDL SSH 密码，必须只放在服务器 `.env` 或 Secrets |
| `AUTODL_LOCAL_PORT` | 是 | `6006` | 本地转发端口 |
| `AUTODL_REMOTE_HOST` | 是 | `127.0.0.1` | 远端服务地址 |
| `AUTODL_REMOTE_PORT` | 是 | `6006` | 远端服务端口 |

## 常用命令

```bash
# 根目录：启动本地全栈 Docker 服务
docker compose up --build

# 根目录：停止本地全栈 Docker 服务
docker compose down

# 后端：启动开发服务
cd backend/huaqibei/oil-risk-orchestrator
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 后端：运行 E2E 契约测试
python test_api.py

# 前端：安装依赖
cd frontend
npm install

# 前端：启动开发服务
npm run dev

# 前端：构建生产版本
npm run build

# 前端：启动生产构建
npm run start

# 前端：代码检查
npm run lint
```

## 测试

后端提供一个基于 FastAPI `TestClient` 的 E2E 契约测试脚本：

```bash
cd backend/huaqibei/oil-risk-orchestrator
python test_api.py
```

该脚本会设置 `USE_MOCK_MODEL=true`，并覆盖健康检查、上传、预测、报告查询和错误输入场景。

前端当前没有配置自动化测试脚本，可运行 lint：

```bash
cd frontend
npm run lint
```

## 构建

前端生产构建：

```bash
cd frontend
npm run build
```

构建产物位于 `frontend/.next/`，该目录是构建产物，不应提交到 GitHub。

Docker 镜像构建可直接使用根目录 Compose：

```bash
docker compose build
```

## 部署

生产部署文件位于 `deploy/production/`，包含：

- `docker-compose.prod.yml`
- `nginx.conf`
- `deploy.sh`
- `setup_autodl_tunnel.sh`
- `.env.example`

基本流程：

```bash
cd deploy/production
cp .env.example .env
```

编辑 `.env`，至少确认：

- `BACKEND_TAG`
- `FRONTEND_TAG`
- `MODEL_API_URL`
- `MODEL_API_KEY`，如模型服务需要
- `LLM_API_KEY`，如启用 LLM 报告
- `AUTODL_SSH_*`，如需要 AutoDL 隧道

部署：

```bash
chmod +x deploy.sh setup_autodl_tunnel.sh bootstrap_and_deploy.sh
./deploy.sh
```

当前项目暂未提供 GitHub Actions。若后续增加 CI/CD，建议把以下变量配置到 GitHub Secrets 或部署平台环境变量：

- `MODEL_API_URL`
- `MODEL_API_KEY`
- `MODEL_API_MODEL_ID`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_ID`
- `AUTODL_SSH_HOST`
- `AUTODL_SSH_PORT`
- `AUTODL_SSH_USER`
- `AUTODL_SSH_PASSWORD`

## Docker 运行方式

本地全栈：

```bash
cp .env.example .env
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
```

停止：

```bash
docker compose down
```

## API 文档

本地后端启动后可访问：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

Docker Compose 启动后端口为：

- Swagger UI：http://localhost:18000/docs
- ReDoc：http://localhost:18000/redoc

主要接口前缀为 `/api/v1`：

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| `GET` | `/api/v1/health` | 健康检查 |
| `POST` | `/api/v1/upload` | 上传 CSV/XLSX/Parquet 数据文件 |
| `POST` | `/api/v1/predict` | 基于上传文件或输入数据执行预测 |
| `GET` | `/api/v1/report/{report_id}` | 查询结构化报告 |
| `GET` | `/api/v1/report/{report_id}/pdf` | 查询报告 PDF，当前可能返回 501 |
| `GET` | `/api/v1/report/factors` | 获取因子字典 |
| `GET` | `/api/v1/report/factors/reasons` | 获取因子筛选理由 |
| `GET` | `/api/v1/report/knowledge-graph/path/{industry}` | 查询行业知识图谱传导路径 |

健康检查示例：

```bash
curl http://localhost:8000/api/v1/health
```

上传示例：

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@sample.csv" \
  -F "dataset_type=oil_price_factors" \
  -F "timezone=UTC" \
  -F "frequency=D" \
  -F "strict_mode=false" \
  -F "encoding=utf-8"
```

预测示例：

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "替换为上传接口返回的 file_id",
    "horizon": 5,
    "target": "log_return",
    "quantiles": [0.05, 0.5, 0.95],
    "industries": ["aviation", "shipping", "chemical"],
    "include_explainability": true,
    "include_knowledge_graph": true,
    "include_report": true,
    "report_style": "banking"
  }'
```

## 数据库说明

当前项目未发现数据库迁移工具、数据库连接配置或必须初始化的数据库。后端运行依赖仓库内置的 `data/` 和 `app/knowledge_graph/graph_data.json` 等文件。

不要提交真实数据库文件、数据库 dump 或含业务敏感信息的数据集。若后续引入数据库，请补充连接方式、迁移命令、种子数据和备份恢复说明。

## 复现检查清单

- [ ] 已安装 Git、Docker、Node.js 和 Python
- [ ] 已 clone 仓库并切换到目标分支
- [ ] 已安装前端依赖或准备使用 Docker
- [ ] 已复制 `.env.example` 为 `.env`
- [ ] 已复制后端 `.env.example` 为后端 `.env`
- [ ] 已填写必要环境变量
- [ ] 已确认是否使用 `USE_MOCK_MODEL=true`
- [ ] 已运行后端测试或健康检查
- [ ] 已启动项目并访问前端页面

## 常见问题

### 端口被占用怎么办？

根目录 Docker Compose 默认使用前端 `13000`、后端 `18000`。如端口被占用，修改 `docker-compose.yml` 中的端口映射后重启。

### 后端健康检查失败怎么办？

先确认后端是否启动：

```bash
curl http://localhost:8000/api/v1/health
```

Docker Compose 场景使用：

```bash
curl http://localhost:18000/api/v1/health
```

### 模型服务连接失败怎么办？

本地体验可先设置 `USE_MOCK_MODEL=true`。接入真实模型时检查 `MODEL_API_URL`、`MODEL_API_KEY` 和模型服务网络连通性。

### LLM API Key 未配置怎么办？

`LLM_API_KEY` 为空时，后端部分报告能力会使用规则模板 fallback。需要 LLM 报告时，在 `.env` 中配置有效的 `LLM_API_KEY`。

### 前端请求地址不对怎么办？

设置 `NEXT_PUBLIC_API_URL`。例如本地后端为 `http://localhost:8000` 时：

```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

### 依赖安装失败怎么办？

优先确认 Node.js >= 20.9、Python >= 3.11。前端建议使用 lock 文件复现：

```bash
cd frontend
npm ci
```

## 贡献指南

这是个人/课程项目，暂未开放完整贡献流程。如需协作，请先提交 issue 或联系维护者。提交前请至少运行后端契约测试和前端 lint。

## License

当前仓库未发现独立 `LICENSE` 文件。公开发布前请确认许可证类型；如果需要开源，建议补充 `LICENSE` 文件并在本节引用。
