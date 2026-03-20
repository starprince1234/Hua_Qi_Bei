# 1. 项目简介

## 项目目标
Oil Risk Intelligence Orchestrator 用于将“原油时序数据 + 宏观因子 + 云端模型推理 + 解释与报告生成”编排为统一 API，交付给前端与对接系统直接调用。

## 系统定位（Model Orchestrator）
本项目不训练模型，核心职责是**模型编排层（Orchestrator）**：

- 接收并校验输入
- 构建特征并调用云端模型
- 后处理风险结果
- 生成可解释输出（SHAP/知识图谱/因子筛选原因）
- 生成结构化报告（含 LLM provenance）

## 架构说明（前端 -> Orchestrator -> 云端模型）
```text
Frontend / External System
        |
        v
/api/v1/upload   -> 文件校验与修复日志
/api/v1/predict  -> 特征工程 -> 云端模型 -> 后处理 -> 解释 -> 报告
/api/v1/report/* -> 报告查询/知识图谱/因子字典
        |
        v
Cloud Model Service (/predict/returns)
```

---

# 2. 技术栈

- **FastAPI**：API 路由与服务框架
- **Pydantic / pydantic-settings**：请求响应模型、环境配置
- **HTTPX**：云端模型 HTTP 调用
- **Docker / docker-compose**：容器化部署
- **LLM Provider（OpenAI 兼容 / 讯飞 MaaS）**：风险报告文本生成
- **OpenAPI 3.1**：接口契约（`D:\桌面\orchestratoropenapi.yaml`）

---

# 3. 目录结构说明

- `app/api`：API 层，路由与依赖注入（不承载业务计算）
- `app/schemas`：请求/响应/中间结果 Schema（Pydantic）
- `app/services`：业务编排层（特征、模型调用、风险、行业、解释、报告、上传）
- `app/pipeline`：特征工程细分组件（校验、as-of 对齐、lag、交互特征）
- `app/explainability`：因子字典、贡献解析、叙述生成
- `app/knowledge_graph`：行业传导图谱查询与映射
- `app/core`：全局配置、常量、错误码、日志
- `app/utils`：JSON、数学、HTTP 工具函数

---

# 4. API 总览

> 基础前缀：`/api/v1`（与 OpenAPI 一致）

| 标签 | 方法 | 路径 | 说明 |
|---|---|---|---|
| Health | GET | `/health` | 存活检查 |
| Upload | POST | `/upload` | 上传数据文件并返回校验/修复/预览 |
| Predict | POST | `/predict` | 主编排预测接口 |
| Report | GET | `/report/{report_id}` | 按报告 ID 获取结构化报告 |
| Report | GET | `/report/{report_id}/pdf` | 报告 PDF（当前实现返回 501） |
| KnowledgeGraph | GET | `/report/knowledge-graph/path/{industry}` | 行业传导路径 |
| Factors | GET | `/report/factors` | 因子字典 |
| Factors | GET | `/report/factors/reasons` | 因子筛选原因标签字典 |

---

# 5. 详细 API 文档

## 5.0 统一响应与错误结构

### 成功响应包（统一）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {},
  "request_id": "optional-or-null"
}
```

### 错误响应包（统一）
```json
{
  "success": false,
  "code": 422,
  "message": "VALIDATION_ERROR",
  "details": {},
  "request_id": "uuid"
}
```

---

## 5.1 健康检查

- **请求方法**：`GET`
- **路径**：`/api/v1/health`
- **请求参数**：无

### 请求示例（JSON）
```json
{}
```

### 成功响应示例（实测）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "status": "ok",
    "version": "1.0.0"
  },
  "request_id": null
}
```

### 错误响应示例
```json
{
  "success": false,
  "code": 500,
  "message": "INTERNAL_SERVER_ERROR",
  "details": {
    "message": "服务器内部错误，请联系管理员"
  },
  "request_id": "req_xxx"
}
```

---

## 5.2 上传数据集

- **请求方法**：`POST`
- **路径**：`/api/v1/upload`
- **请求参数（multipart/form-data）**
  - `file`（**必填**，binary）
  - `dataset_type`（可选，默认 `oil_price_factors`）
  - `timezone`（可选，默认 `UTC`）
  - `frequency`（可选，`D/W/M`，默认 `D`）
  - `strict_mode`（可选，默认 `false`，后端显式按 bool 解析）
  - `encoding`（可选，默认 `utf-8`）
  - Header：`Idempotency-Key`（可选）

### 请求示例（JSON，表示表单字段）
```json
{
  "dataset_type": "oil_price_factors",
  "timezone": "UTC",
  "frequency": "D",
  "strict_mode": "false",
  "encoding": "utf-8",
  "file": "<binary>"
}
```

### 成功响应示例（实测）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "file_id": "file_19f7be0ddb51",
    "detected_format": "csv",
    "validation": {
      "passed": true,
      "row_count": 30,
      "date_range": null,
      "frequency_detected": null,
      "required_columns_missing": [],
      "warnings": []
    },
    "repair_log": [],
    "preview": [
      {
        "date": "2026-01-01",
        "open": "70.0",
        "high": "71.0",
        "low": "69.0",
        "close": "70.5",
        "volume": "1000000"
      }
    ],
    "schema_hint": {
      "required_columns": ["date", "open", "high", "low", "close"],
      "optional_columns": ["volume"]
    }
  },
  "request_id": null
}
```

### 错误响应示例
```json
{
  "success": false,
  "code": 400,
  "message": "VALIDATION_ERROR",
  "details": {
    "message": "frequency 仅支持 D/W/M"
  },
  "request_id": "req_xxx"
}
```

---

## 5.3 主预测接口

- **请求方法**：`POST`
- **路径**：`/api/v1/predict`
- **请求参数（application/json）**
  - `horizon`（**必填**，1~60）
  - `quantiles`（**必填**，数组，值在 `[0,1]`）
  - `file_id`（条件必填：`file_id` 与 `oil_data` 二选一）
  - `oil_data`（条件必填：`file_id` 与 `oil_data` 二选一）
  - `target`（可选，默认 `log_return`）
  - `industries`（可选）
  - `include_explainability`（可选，默认 `true`）
  - `include_knowledge_graph`（可选，默认 `true`）
  - `include_report`（可选，默认 `true`）
  - `report_style`（可选，`banking|concise|verbose`）
  - `strict_mode`（可选）
  - Header：`Idempotency-Key`（可选）

### 请求示例（JSON）
```json
{
  "file_id": "file_19f7be0ddb51",
  "horizon": 5,
  "target": "log_return",
  "quantiles": [0.05, 0.5, 0.95],
  "industries": ["aviation", "shipping", "chemical"],
  "include_explainability": true,
  "include_knowledge_graph": true,
  "include_report": true,
  "report_style": "banking"
}
```

### 成功响应示例（实测）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "prediction": {
      "horizon": 5,
      "return_quantiles": {
        "0.05": -0.031025,
        "0.5": -0.014344,
        "0.95": 0.002832
      },
      "confidence_score": 0.755,
      "risk_level": "LOW",
      "model_version": "mock-v1.0",
      "feature_config_version": "v1",
      "scaler_version": "v1"
    },
    "future_path": {
      "steps": [
        { "step": 1, "median_price": 73.1897, "upper_price": 73.4415, "lower_price": 72.9388 },
        { "step": 2, "median_price": 72.9801, "upper_price": 73.4831, "lower_price": 72.4805 }
      ]
    },
    "shock_signal": {
      "overall_intensity": 0.1123,
      "alert_level": "LOW",
      "top_affected_industries": [
        { "industry": "aviation", "direction": "positive", "magnitude": 0.122 }
      ]
    },
    "explainability": {
      "top_factors": [
        { "factor": "return_lag_1", "contribution": 0.01282 }
      ],
      "method": "shap_or_proxy"
    },
    "knowledge_graph": {
      "paths": [
        {
          "industry": "aviation",
          "path_nodes": ["crude_oil", "jet_fuel", "aviation_cost", "aviation_profit"],
          "path_labels": ["原油价格", "航煤价格", "航空运营成本", "航空业盈利"],
          "arrow_path": "原油价格 → 航煤价格 → 航空运营成本 → 航空业盈利"
        }
      ]
    },
    "factor_selection_reasons": {
      "selected": [
        {
          "factor": "return_lag_1",
          "reason_tag": "rolling_ic_positive",
          "evidence": { "matched_top_factor": true }
        }
      ],
      "rejected": [
        {
          "factor": "macro_unknown_x",
          "reason_tag": "high_missing_ratio",
          "evidence": { "matched_top_factor": false }
        }
      ]
    },
    "report": {
      "report_id": "16eeae3e-c822-424d-8d84-b63d21acd952",
      "schema_version": "risk_report_v1",
      "sections": {
        "executive_summary": "系统预测未来 5 天油价将震荡至约 $72.35，收益率变化幅度 1.43%，风险等级评定为低风险，模型置信度 76%。",
        "trend_and_confidence": "本次预测由1日滞后收益率、10日滞后收益率、3日滞后收益率等核心因子驱动...",
        "key_drivers": "本次预测由1日滞后收益率、10日滞后收益率、3日滞后收益率等核心因子驱动...",
        "industry_impacts": "aviation:positive:0.12:预测油价下跌 1.43%...",
        "risks_and_limits": "1. 当前风险可控..."
      },
      "provenance": {
        "generation_mode": "template_fallback",
        "provider": "xf_maas",
        "model_id": "xopkimik25",
        "latency_ms": 0,
        "schema_validated": true,
        "request_id": null,
        "usage": null,
        "template": "banking"
      }
    },
    "data_processing_log": {
      "validation_passed": true,
      "repair_actions": [],
      "asof_alignment": false,
      "lag_features_built": true
    }
  },
  "request_id": "b2654d1c-05dd-4ab8-a472-14b24f266754"
}
```

### 错误响应示例（实测：缺少 file_id/oil_data）
```json
{
  "success": false,
  "code": 422,
  "message": "VALIDATION_ERROR",
  "details": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, file_id 与 oil_data 至少提供一个",
      "input": {
        "horizon": 5,
        "target": "log_return",
        "quantiles": [0.05, 0.5, 0.95]
      },
      "ctx": {
        "error": "file_id 与 oil_data 至少提供一个"
      }
    }
  ],
  "request_id": "78575172-1af9-4f0e-85e9-0d2150be882a"
}
```

### 字段必填/可选与来源标注（Predict）

#### 请求体字段
| 字段 | 必填性 | 来源 |
|---|---|---|
| horizon | 必填 | 编排层输入 |
| quantiles | 必填 | 编排层输入 |
| file_id | 条件必填（二选一） | upload 输出 |
| oil_data | 条件必填（二选一） | 前端/调用方输入 |
| target | 可选 | 编排层输入 |
| industries | 可选 | 编排层输入 |
| include_explainability | 可选 | 编排层输入 |
| include_knowledge_graph | 可选 | 编排层输入 |
| include_report | 可选 | 编排层输入 |
| report_style | 可选 | 编排层输入 |
| strict_mode | 可选 | 编排层输入 |

#### 响应体字段（data）
| 字段 | 必填性 | 来源 |
|---|---|---|
| prediction.return_quantiles / confidence_score / model_version | 必有 | **模型层**（ModelClient + 后处理） |
| future_path | 必有 | **编排层**（PostprocessService） |
| shock_signal | 必有 | **编排层**（IndustryService 汇总） |
| explainability.top_factors / method | 必有 | **解释层**（ShapService） |
| knowledge_graph.paths | 必有 | **解释层 + 编排层**（GraphQuery/映射） |
| factor_selection_reasons | 必有 | **解释层**（FactorReasonService） |
| report.sections / report.provenance | 必有 | **编排层 + LLM层**（ReportService） |
| data_processing_log | 必有 | **编排层**（Validator/Pipeline） |

---

## 5.4 获取结构化报告

- **请求方法**：`GET`
- **路径**：`/api/v1/report/{report_id}`
- **请求参数**
  - Path：`report_id`（**必填**）

### 请求示例（JSON）
```json
{
  "report_id": "16eeae3e-c822-424d-8d84-b63d21acd952"
}
```

### 成功响应示例（实测）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "report_id": "16eeae3e-c822-424d-8d84-b63d21acd952",
    "schema_version": "risk_report_v1",
    "sections": {
      "executive_summary": "系统预测未来 5 天油价将震荡至约 $72.35...",
      "trend_and_confidence": "本次预测由1日滞后收益率...",
      "key_drivers": "本次预测由1日滞后收益率...",
      "industry_impacts": "aviation:positive:0.12:预测油价下跌...",
      "risks_and_limits": "1. 当前风险可控..."
    },
    "provenance": {
      "generation_mode": "template_fallback",
      "provider": "xf_maas",
      "model_id": "xopkimik25",
      "latency_ms": 0,
      "schema_validated": true,
      "request_id": null,
      "usage": null,
      "template": "banking"
    }
  },
  "request_id": null
}
```

### 错误响应示例（实测）
```json
{
  "success": false,
  "code": 404,
  "message": "NOT_FOUND",
  "details": {
    "resource": "report",
    "id": "not-exists"
  },
  "request_id": "e48d7010-c353-48f7-8bad-b210ff181cb4"
}
```

---

## 5.5 报告 PDF 下载

- **请求方法**：`GET`
- **路径**：`/api/v1/report/{report_id}/pdf`
- **请求参数**
  - Path：`report_id`（**必填**）

### 请求示例（JSON）
```json
{
  "report_id": "16eeae3e-c822-424d-8d84-b63d21acd952"
}
```

### 成功响应示例（契约）
- `200 application/pdf`（二进制内容）

### 错误响应示例（实测）
```json
{
  "success": false,
  "code": 501,
  "message": "NOT_IMPLEMENTED",
  "details": {
    "resource": "report_pdf",
    "id": "16eeae3e-c822-424d-8d84-b63d21acd952"
  },
  "request_id": "da151ca9-27bd-4fd0-85cf-00dc0e2ebfa1"
}
```

---

## 5.6 行业知识图谱路径

- **请求方法**：`GET`
- **路径**：`/api/v1/report/knowledge-graph/path/{industry}`
- **请求参数**
  - Path：`industry`（**必填**，枚举：`aviation|shipping|chemical|refinery|logistics|heavy_manufacturing`）

### 请求示例（JSON）
```json
{
  "industry": "aviation"
}
```

### 成功响应示例（实测）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "industry": "aviation",
    "industry_mapped": "aviation",
    "path_nodes": ["crude_oil", "jet_fuel", "aviation_cost", "aviation_profit"],
    "path_labels": ["原油价格", "航煤价格", "航空运营成本", "航空业盈利"],
    "arrow_path": "原油价格 → 航煤价格 → 航空运营成本 → 航空业盈利"
  },
  "request_id": null
}
```

### 错误响应示例
```json
{
  "success": false,
  "code": 404,
  "message": "NOT_FOUND",
  "details": {
    "message": "未找到行业路径"
  },
  "request_id": "req_xxx"
}
```

---

## 5.7 因子字典

- **请求方法**：`GET`
- **路径**：`/api/v1/report/factors`
- **请求参数**：无

### 请求示例（JSON）
```json
{}
```

### 成功响应示例（实测，节选）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "total": 13,
    "factors": [
      {
        "factor_name": "return_lag_1",
        "name_cn": "1日滞后收益率",
        "category": "technical",
        "definition": "前1日原油对数收益率，捕捉短期动量效应",
        "unit": "无量纲"
      }
    ]
  },
  "request_id": null
}
```

### 错误响应示例
```json
{
  "success": false,
  "code": 500,
  "message": "INTERNAL_SERVER_ERROR",
  "details": {
    "message": "服务器内部错误，请联系管理员"
  },
  "request_id": "req_xxx"
}
```

---

## 5.8 因子筛选原因标签字典

- **请求方法**：`GET`
- **路径**：`/api/v1/report/factors/reasons`
- **请求参数**：无

### 请求示例（JSON）
```json
{}
```

### 成功响应示例（实测，节选）
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "total": 10,
    "reason_tags": [
      {
        "reason_tag": "rolling_ic_positive",
        "name_cn": "rolling_ic_positive",
        "description": "rolling_ic_positive 规则命中",
        "severity": "info"
      }
    ]
  },
  "request_id": null
}
```

### 错误响应示例
```json
{
  "success": false,
  "code": 500,
  "message": "INTERNAL_SERVER_ERROR",
  "details": {
    "message": "服务器内部错误，请联系管理员"
  },
  "request_id": "req_xxx"
}
```

---

# 6. 数据流说明（upload -> predict -> report）

1. **upload**
   - 解析 `csv/xlsx/xls/parquet`
   - 执行字段检查与缺失修复
   - 返回 `file_id`、`validation`、`repair_log`、`preview`

2. **predict**
   - 通过 `file_id` 取缓存数据或直接读取 `oil_data`
   - `DataValidator` 校验 -> `AsofAligner` 对齐 -> `LagBuilder` -> `InteractionBuilder`
   - `ModelClient` 调用云端模型 `/predict/returns`
   - `PostprocessService` 还原路径，`RiskService` 风险分级，`IndustryService` 冲击映射
   - `ShapService` 解释，`GraphQuery` 路径增强，`FactorReasonService` 筛选原因
   - `ReportService` 产出结构化报告与 provenance

3. **report**
   - 通过 `report_id` 读取内存报告并返回 `ReportResult`
   - `pdf` 当前返回 501（未实现）

---

# 7. LLM 说明

## LLM Provider 配置方式
由环境变量控制：

- `LLM_PROVIDER`：`xf_maas` / `openai`（OpenAI 兼容协议）
- `LLM_BASE_URL`：LLM API 基地址
- `LLM_MODEL_ID`：模型 ID
- `LLM_API_KEY`：鉴权 Key
- `LLM_JSON_MODE`：是否启用 JSON mode

## 降级逻辑
- 当 `LLM_API_KEY` 为空：直接走**规则模板报告**（template fallback）
- 当 LLM 调用失败或输出不符合约束：重试一次；仍失败则降级规则模板
- API 保证始终返回结构化 `report` 字段

## provenance 字段说明（`data.report.provenance`）
- `generation_mode`：`llm` / `template_fallback`
- `provider`：LLM 提供方
- `model_id`：模型标识
- `latency_ms`：调用耗时（降级时为 0）
- `schema_validated`：输出结构是否通过校验
- `request_id`：上游 LLM 请求 ID（可能为 null）
- `usage`：Token 使用信息（可能为 null）
- `template`：报告模板（如 `banking`）

---

# 8. 环境变量说明

## 核心对接变量
- `MODEL_API_URL`：云端模型地址（默认 `http://localhost:9000/predict/returns`）
- `MODEL_API_TIMEOUT`：模型调用超时（秒）
- `MODEL_API_MAX_RETRIES`：模型调用重试次数
- `MODEL_API_KEY`：模型服务 Bearer Token（可选）

- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_MODEL_ID`
- `LLM_API_KEY`
- `LLM_JSON_MODE`
- `LLM_LORA_ID`
- `LLM_SEARCH_DISABLE`

## 运行控制变量
- `USE_MOCK_MODEL`：`true` 时不调用真实模型，返回 mock 预测
- `APP_NAME` / `APP_VERSION`
- `ENVIRONMENT` / `DEBUG`
- `HOST` / `PORT`
- `ALLOWED_ORIGINS`

## 风险阈值变量
- `RISK_LOW_THRESHOLD`
- `RISK_MEDIUM_THRESHOLD`

---

# 9. 启动方式

## 本地启动（推荐开发联调）
```bash
pip install -r requirements.txt
```

### Windows PowerShell
```powershell
$env:USE_MOCK_MODEL="true"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Linux/macOS
```bash
export USE_MOCK_MODEL=true
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Docker 启动
```bash
cd docker
docker-compose up -d --build
```

---

# 10. 对接注意事项

## 字段稳定性说明
- 所有接口统一 envelope：`success/code/message/data/request_id`
- `report.schema_version` 当前固定为 `risk_report_v1`
- `report.sections` 五段文本字段固定存在
- 错误结构统一：`success=false + code + message + details + request_id`

## 不可改字段说明（前后端联调依赖）
- 路径前缀：`/api/v1`
- 关键字段名：
  - `data.prediction`
  - `data.future_path`
  - `data.shock_signal`
  - `data.explainability`
  - `data.knowledge_graph`
  - `data.factor_selection_reasons`
  - `data.report`
  - `data.data_processing_log`
- `report.report_id`、`report.schema_version`、`report.sections`、`report.provenance`

## 版本号说明
- 应用版本：`1.0.0`
- OpenAPI：`3.1.0`
- 当前交付契约：`D:\桌面\orchestratoropenapi.yaml`

## 接口兼容策略
- 保持 URL 与现有字段不破坏（向后兼容）
- 新增能力采用“新增字段/新增可选参数”，不删除既有字段
- 错误码采用稳定业务码（如 `VALIDATION_ERROR`、`NOT_FOUND`、`NOT_IMPLEMENTED`、`MODEL_UNAVAILABLE`）
- 建议调用方容忍 `request_id` 为 `null`（成功场景）或字符串（错误场景）