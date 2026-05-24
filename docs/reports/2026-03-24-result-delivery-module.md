# 三、结果输出（Result Delivery）

本模块将训练后模型能力封装为可调用的在线推理服务，并在用户上传数据后完成“数据校验与修复 → 预测推理 → 收益率还原价格路径 → 行业冲击映射 → 解释层联动 → 报告生成”全链路输出。实现形态以 **FastAPI 编排服务 + Next.js 可视化前端 + OpenAI 兼容模型接口** 为核心，代码主入口为 **backend/huaqibei/oil-risk-orchestrator/app/api/routes/predict.py** 与 **frontend/src/components/**。

## 3.1 呈现形式（在线系统 + JSON 推理接口）

### 3.1.1 模型服务化部署（JSON in / JSON out）

**技术原理简释（1-2句）**：服务化部署的核心是将“离线模型能力”抽象为稳定 JSON 契约，前端与后端仅依赖接口而不依赖训练框架。当前实现采用“编排层（Orchestrator）调用远端模型服务”的解耦架构，编排层负责数据治理、后处理、解释与报告。

**代码实现要点**
- 应用入口与路由注册：**app/main.py::create_app** 注册 **/api/v1/upload、/api/v1/predict、/api/v1/report**，并挂载模型占位路由 **/model/v1/**（文件：**app/api/routes/model_service_placeholder.py**）。
- 模型调用客户端：**app/services/model_client.py::ModelClient.predict**，统一封装远端推理调用、超时、重试、格式归一化。
- 推理协议：
  - 编排层对外：`POST /api/v1/predict`（前端调用）。
  - 编排层对模型层：默认 `POST ${MODEL_API_URL}/predict/returns`（legacy）或 `POST /v1/chat/completions`（openai 兼容模式，自动识别）。
- Mock/Real 切换：**app/api/dependencies.py::get_model_client** 根据环境变量 **USE_MOCK_MODEL** 将 **predict** 动态替换为 **mock_predict**，支撑离线演示与联调。

**接口定义（编排层主接口）**

**请求方式+接口地址**：`POST /api/v1/predict`

**请求体（JSON）**
```json
{
  "file_id": "file_123",
  "horizon": 10,
  "target": "log_return",
  "quantiles": [0.05, 0.5, 0.95],
  "industries": ["aviation", "shipping", "chemical"],
  "include_explainability": true,
  "include_knowledge_graph": true,
  "include_report": true,
  "report_style": "banking"
}
```
- **horizon**：1-60（**PredictRequest** 校验）
- **target**：仅支持 **log_return**
- **file_id / oil_data**：二选一，至少一个存在

**响应体（JSON）**
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "prediction": {},
    "future_path": {},
    "shock_signal": {},
    "explainability": {},
    "knowledge_graph": {},
    "ai_insights": {},
    "factor_selection_reasons": {},
    "report": {},
    "data_processing_log": {}
  },
  "request_id": "uuid"
}
```

**代码实现核心片段（关键路径）**
```python
# app/api/routes/predict.py
model_response = await model_client.predict(
    feature_vector=feature_vector,
    forecast_horizon=request.horizon,
    include_shap=request.include_explainability,
    current_price=current_price,
)
prediction_path = _post_svc.restore_prediction_path(model_response, current_price)
```

**工程化注意事项**
- 统一错误包络：**APIResponse / ErrorResponse**（**app/schemas/report_schema.py**），便于前端稳定解析。
- 全局异常处理：**app/main.py** 中对 **BusinessError / RequestValidationError / Exception** 分层处理。
- 日志规范：**app/core/logger.py** 双通道日志（stdout + `logs/app.log`），定位上传、推理、LLM、图谱链路。
- 性能优化：
  - 模型调用指数退避重试（`2 ** (attempt-1)`）。
  - 解释与报告并发生成（`asyncio.gather`）。
  - 图谱查询单例加载（**GraphQuery.__new__**）避免重复 IO。

**异常处理机制**
- 模型不可用：**predict.py** 捕获 `RuntimeError` 后抛出 **MODEL_UNAVAILABLE(503)**。
- 请求参数错误：Pydantic 校验失败统一返回 **VALIDATION_ERROR(422)**。
- 文件/输入缺失：业务异常 **VALIDATION_ERROR(400)**。

**参数配置细节**
- 关键环境变量（**app/core/settings.py**）：**MODEL_API_URL、MODEL_API_TIMEOUT、MODEL_API_MAX_RETRIES、MODEL_API_KEY**。
- 风险阈值：**RISK_LOW_THRESHOLD=0.03、RISK_MEDIUM_THRESHOLD=0.07**。
- 依赖版本（**requirements.txt**）：**fastapi 0.115.6、httpx 0.28.1、pandas 2.2.3、openai 1.65.2**。

> 与技术路线差异说明：当前仓库未包含 Paddle 静态图导出（`paddle.jit.save`/`save_inference_model`）与本地 Paddle Inference 引擎加载代码；实际采用“远端模型服务 HTTP 调用”落地，契约能力由 **model-service-openapi.yaml** 对齐。

## 3.2 内容模块（用户上传 → 推理 → 可解释报告）

### 3.2.1 Web 网站（用户数据上传与任务触发）

**技术原理简释（1-2句）**：Web 层将业务用户的非结构化上传行为收敛为规范化数据契约，再触发推理任务。该层重点不是模型计算，而是“格式治理 + 参数治理 + 任务编排触发”。

**代码实现要点**
- 前端上传组件：**frontend/src/components/FileUploader.tsx**。
  - 文件类型限制：`accept=".csv,.xlsx,.xls,.parquet"`。
  - 表单字段：**dataset_type/timezone/frequency/strict_mode/encoding**。
  - 接口调用：`fetch(${API_BASE}/upload, { method: 'POST', body: FormData })`。
- 前端预测触发：**frontend/src/components/PredictForm.tsx**。
  - 参数：**horizon、include_explainability、include_knowledge_graph、report_style、industries**。
  - 接口：`POST /predict`。
- 后端上传路由：**app/api/routes/upload.py::upload_dataset**。
  - 显式解析布尔：**_parse_form_bool**（避免 `"false"` 被误判为真）。
- 上传服务：**app/services/upload_service.py::UploadService**。
  - 解析器：**_parse_csv_bytes / _parse_excel_bytes / _parse_parquet_bytes**。
  - 校验与修复：调用 **DataValidator.validate_oil_data** 与 **fill_missing_values_with_log**。

**文件解析与校验规则（代码实装）**
- 扩展名白名单：`.csv/.xlsx/.xls/.parquet`。
- 油价时序必备列：至少 `date` 与 `close`（严格输出 schema 提示 `date/open/high/low/close`）。
- 行数阈值：最少 **30** 行，最多 **5000** 行（**core/constants.py**）。
- 缺失率阈值：`close` 缺失率 > **30%** 判失败。
- 价格合法性：`close <= 0` 判失败。
- 频率参数校验：仅允许 `D/W/M`。

**数据自动修复与日志**
- 缺失修复策略：前向填充优先，无历史值则常量 **0.0**（`FEATURE_NA_FILL_VALUE`）。
- 修复日志字段：**field、strategy、count、severity、before_after_sample**。
- 严格模式：`strict_mode=true` 且存在修复动作时，直接拒绝上传。

**工程化注意事项**
- 当前前端未实现分片上传与实时进度条（状态仅有 **isUploading**）；大文件场景可扩展 `XMLHttpRequest.onprogress` 或分片协议。
- `UploadService._FILE_STORE` 为进程内缓存，已在部署侧固定 `--workers 1` 防止多 worker file_id 不共享。

**异常处理机制**
- 编码错误：CSV decode 抛出 `文件编码错误`。
- 格式错误：不支持扩展名直接 `ValueError`。
- 参数错误：`strict_mode` 非布尔文本返回 **VALIDATION_ERROR(400)**。

**参数配置细节**
- 上传默认值：`dataset_type=oil_price_factors, timezone=UTC, frequency=D, strict_mode=false, encoding=utf-8`。
- 前端行业默认勾选：`aviation/shipping/chemical`。

### 3.2.2 推理结果后处理（从“收益率预测”到“趋势与信号”）

**技术原理简释（1-2句）**：模型输出的是收益率分布，业务决策需要价格路径与行业冲击。后处理层通过收益率-价格变换、行业敏感度映射与不确定区间渲染，将“统计输出”转化为“业务可执行输出”。

**代码实现要点**
- 收益率还原价格：**app/services/postprocess_service.py::restore_prediction_path** 调用 **restore_price_from_return(use_log=True)**。
- 多周期输出：**build_competition_multi_path** 优先用模型返回 `multi_horizon_returns`，否则从 full path 采样 1/3/7/14/30。
- 冲击映射：**app/services/industry_service.py::analyze_impact**。
  - 强度公式：`|median| * base_sensitivity * 10`，并截断到 `[0,1]`。
  - 行业参数：航空 0.85、航运 0.72、化工 0.78、能源 0.90 等。
- 风险等级映射：**predict.py::_to_shock_signal**。
  - `overall_intensity >=0.6 -> HIGH`，`>=0.3 -> MEDIUM`，否则 LOW。

**收益率→价格路径实现细节**
```python
step_median = median / max(horizon, 1)
median_prices = restore_price_from_return(current_price, [step_median] * horizon, use_log=True)
```
- 单位说明：`predicted_return` 为对数收益率（小数），`predicted_price` 为 USD/桶价格。
- 时间轴：前端按 `step` 显示 `N天` 标签（**ResultDisplay.tsx**）。

**不确定区间可视化实现细节**
- 后端输出：`upper_price/lower_price` 与 `upper_return/lower_return`。
- 前端图表：**Recharts LineChart** 三条曲线（中位/上界/下界），风险区间用于表格与摘要卡片。
- 非标准 horizon：前端 **fitPointByHorizon** 采用线性插值拟合摘要点。

**工程化注意事项**
- `current_price` 优先从上传快照中的 Brent/WTI 字段提取；缺失时默认 70.0（**predict.py::_build_feature_vector_from_snapshot**）。
- 冲击方向按 `direction_policy` 与油价方向联合判定，避免单纯按涨跌硬编码。

**异常处理机制**
- full_path 为空时，多周期回退返回空列表。
- 行业 key 不在配置表时记录 warning 并跳过，不阻断全流程。

**参数配置细节**
- 行业别名映射：`refinery->chemical, logistics->shipping, heavy_manufacturing->manufacturing`。
- 风险区间/分位输出字段统一由 **PredictionSummaryV1/FuturePathStep/ShockSignal** 约束。

### 3.2.3 知识图谱解释层（解释“因子传导机制”，补足纯统计筛选的不足）

**技术原理简释（1-2句）**：解释层通过“统计筛选证据 + 模型贡献证据 + 产业链传导证据”形成闭环，避免仅给相关性结论。当前工程以轻量图谱 JSON 实现可解释路径查询，并与 SHAP 与筛选理由联动。

**代码实现要点**
- 图谱加载与查询：**app/knowledge_graph/graph_query.py::GraphQuery**（单例），数据源 **graph_data.json**。
- 节点/边能力：**get_path / get_path_labels / get_edge_weight**。
- 传导叙述：**transmission_mapper.py::build_transmission_narrative** 根据边权符号判“正向提振/负向压制”。
- 三层解释联动：
  1. 统计筛选层：**FactorReasonService.build_factor_selection_reasons**。
  2. 模型解释层：**ShapService.build_explainability**。
  3. 图谱传导层：**predict.py::_to_knowledge_graph_block** 组装路径与节点等级。

**与 Neo4j/Cypher 要求的工程映射说明**
- 当前代码未接入 Neo4j 驱动、Bolt 连接或 Cypher 查询；实现为本地 JSON 图谱查询。
- 可替换挂载点已清晰：将 **GraphQuery.get_path/get_edge_weight** 替换为 Neo4j Repository 即可，无需改动上层 API 契约。

**因子贡献在图谱中的可视化联动**
- SHAP Top 因子来源：**ExplainabilitySection.top_factors**。
- 图谱节点等级来源：**AIInsightService.build_kg_insight** 返回 `node_levels_map`，并在 `knowledge_graph.paths[].node_levels` 回传前端。
- 前端呈现：**ResultDisplay.tsx** 对每个路径节点展示 `{name}:{level}` 标签。

**工程化注意事项**
- 图谱单例预热：**app/main.py::lifespan** 启动时预加载，减少首请求抖动。
- 关系边权缺失时返回 0.0，保证叙述构建可降级。

**异常处理机制**
- 图谱文件缺失/JSON损坏：**GraphQuery._load_graph** 捕获后回退空图，服务不中断。
- 行业路径不存在：`GET /report/knowledge-graph/path/{industry}` 返回 **NOT_FOUND(404)**。

**参数配置细节**
- 图谱路径配置项：**KNOWLEDGE_GRAPH_PATH=app/knowledge_graph/graph_data.json**。
- 图谱数据包含 20 个节点、19 条边、7 类行业路径（见 `graph_data.json`）。

### 3.2.4 LLM 报告生成器（金融专家视角的自动撰写与建议）

**技术原理简释（1-2句）**：报告生成器采用“结构化 Context Pack + 严格 Schema 校验 + 失败降级模板”的受约束生成策略，确保文本可审计、可回溯、可落地。其目标不是替代模型，而是把量化结果转译为银行团队可执行语言。

**代码实现要点**
- 主报告服务：**app/services/report_service.py::ReportService.generate_report**。
- 并发 AI 子模块：**predict.py** 中 `asyncio.gather(risk, industry, kg, report)`。
- Context Pack 构建：**ReportService.build_context_pack**，字段含 `prediction/risk_analysis/top_drivers/industry_impact/knowledge_graph_paths`。
- LLM 调用：
  - 报告：**ReportService.call_llm**。
  - 细分解释：**AIInsightService._call_llm** 与 **IndustryService._call_llm**（可选）。

**接口定义（报告查询）**

**请求方式+接口地址**：`GET /api/v1/report/{report_id}`

**响应体（JSON）**
```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "report_id": "...",
    "schema_version": "risk_report_v1",
    "sections": {
      "executive_summary": "...",
      "trend_and_confidence": "...",
      "key_drivers": "...",
      "industry_impacts": "...",
      "risks_and_limits": "..."
    },
    "provenance": {
      "generation_mode": "llm|template_fallback",
      "provider": "...",
      "model_id": "...",
      "latency_ms": 0,
      "schema_validated": true
    }
  }
}
```

**防幻觉策略（代码实装）**
- 白名单上下文：**_filter_context_whitelist** 仅放行五类字段。
- 输出约束：**ConstrainedReportOutput** 限定 5 个章节键。
- 文本一致性校验：**_validate_llm_output_fields** 要求命中已知因子/行业、包含量化 token，且禁止“外部新闻/据报道”等外部事实注入。
- 重试与降级：首次失败后二次重试；仍失败则 **_rule_based_report** 模板回退，保证接口稳定返回。

**网页可视化与 PDF 导出**
- 前端展示：**ResultDisplay.tsx** 渲染报告摘要 + 风险/行业/KG 弹窗详情。
- PDF 导出：后端 `GET /api/v1/report/{report_id}/pdf` 当前返回 **501 NOT_IMPLEMENTED**（**app/api/routes/report.py**），属于已预留接口、待补齐能力。

**工程化注意事项**
- Provider 兼容：**xf_maas/openai/siliconflow** 通过 **LLM_PROVIDER/LLM_BASE_URL/LLM_MODEL_ID** 切换。
- 生产稳定性：`RateLimit/500/503` 指数退避，鉴权失败直接中止并降级模板。

**异常处理机制**
- LLM 超时：抛出 `_LLMCallError("LLM 调用超时")`，进入模板回退。
- JSON 解析失败：`_parse_and_validate_report_output` 返回 `None`，触发二次调用或模板回退。

**参数配置细节**
- 关键参数：**LLM_JSON_MODE、LLM_MAX_TOKENS、LLM_TEMPERATURE、LLM_TIMEOUT、LLM_MAX_RETRIES**。
- 多模型拆分：**LLM_MODEL_RISK_LEVEL / LLM_MODEL_INDUSTRY_IMPACT / LLM_MODEL_KNOWLEDGE_GRAPH / LLM_MODEL_REPORT_SUMMARY**。

## 结果输出模块技术创新点

1. **编排层与模型层完全解耦的“双契约架构”**：前端只依赖 `/api/v1/*`，编排层只依赖模型服务 JSON 契约（legacy + openai 双模式），显著提升模型替换与跨环境部署效率。
2. **“统计筛选—模型贡献—图谱传导”三层解释闭环**：将 **FactorReasonService + ShapService + GraphQuery/AI KG** 串联，既给出可复现筛选证据，又给出经济机制路径。
3. **LLM 受约束生成 + 审计级回退策略**：通过 Context 白名单、章节 Schema、字段命中校验与模板降级，兼顾报告可读性与风控可审计性。
4. **多周期预测展示工程化适配**：后端支持 `multi_horizon_returns` 与路径采样双轨，前端支持 horizon 插值拟合，满足比赛展示与业务解读统一口径。
5. **端到端异常不阻断设计**：文件上传、模型调用、图谱加载、LLM 生成均具备显式降级路径，确保关键结果块稳定返回。

## 模块工程化部署与运行说明

**1）本地开发运行**
```bash
cd backend/huaqibei/oil-risk-orchestrator
pip install -r requirements.txt
# Windows PowerShell
$env:USE_MOCK_MODEL="true"
$env:DEBUG="false"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
```bash
cd frontend
npm install
npm run dev
```

**2）容器化运行**
```bash
docker-compose up --build
```
- 后端：`http://localhost:18000`
- 前端：`http://localhost:13000`

**3）生产部署要点（Nginx 反代）**
- `deploy/production/nginx.conf` 已将 `/api/` 代理到后端 `/api/v1/`。
- 生产 compose 使用 `NEXT_PUBLIC_API_URL=/api`，避免前端硬编码域名。

**4）关键运维检查**
- 健康检查：`GET /api/v1/health`、`GET /healthz`。
- 回归测试：`backend/.../test_api.py`（upload→predict→report 全链路）。
- 日志路径：`backend/.../logs/app.log`。

**5）当前能力边界（与后续迭代建议）**
- 已预留未实装：`/report/{report_id}/pdf`。
- 当前知识图谱为 JSON 内存查询，后续可平滑替换为 Neo4j 存储与 Cypher 查询层。
- 当前上传进度为状态级反馈，后续可扩展为分片与实时进度条。
