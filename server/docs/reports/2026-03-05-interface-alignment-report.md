# 接口对齐检查报告（2026-03-05）

## 基准文件
- `model-service-openapi.yaml`（模型接口预留基准）
- `orchestratoropenapi.yaml`（前后端接口全集基准）

## 检查范围
- 后端 FastAPI 路由实现与 OpenAPI 对齐（路径、方法、状态码声明）
- 前端请求目标路径与参数约束对齐
- Docker 运行时对接口联调的影响

## 一致项清单
1. **编排接口路径/方法一致（含前缀）**
   - 实际后端：`/api/v1/health`、`/api/v1/upload`、`/api/v1/predict`、`/api/v1/report/*`
   - 与 `orchestratoropenapi.yaml` 的路径集合一致（以 `servers.url=/api/v1` 为前缀）
2. **模型占位接口路径/方法一致**
   - 已新增：`/model/v1/health`、`/model/v1/metadata`、`/model/v1/schema`、`/model/v1/predict/returns`
   - 与 `model-service-openapi.yaml` 完整匹配
3. **前端调用路径已对齐**
   - `FileUploader`：`/api/v1/upload`
   - `PredictForm`：`/api/v1/predict`
4. **前端关键参数约束已对齐**
   - `horizon` 最大值改为 `60`
   - 行业枚举改为：`aviation/shipping/chemical/refinery/logistics/heavy_manufacturing`
5. **后端 OpenAPI 声明增强**
   - 在 `upload/predict/report*` 路由补充了 `responses` 状态码声明（400/404/413/415/500/501/503 等）

## 不一致项清单（含修正方案）
1. **OpenAPI 自动生成会附带 `422`**
   - 现象：FastAPI 自动在部分端点增加 `422`（请求体验证错误）
   - 影响：比 `orchestratoropenapi.yaml` 多出一个框架级状态码声明
   - 修正方案（可选）：
     - A. 在 `orchestratoropenapi.yaml` 中显式补充 `422`（推荐，反映真实行为）
     - B. 自定义 OpenAPI 生成逻辑移除自动 `422`（不推荐，维护成本高）
2. **`upload` 端点 413/415 目前主要依赖业务层抛错路径**
   - 现象：OpenAPI 已声明 413/415；实际主要由校验逻辑映射为 400/422
   - 修正方案：在上传服务中对超大文件/不支持格式显式抛 `BusinessError(413/415)`
3. **前端结果页 Recharts 有非阻断 warning**
   - 现象：浏览器控制台出现 chart 尺寸 warning，不影响接口调用与结果展示
   - 修正方案：容器布局稳定后再初始化图表尺寸（可后续优化）

## 已执行的自动化对比证据（摘要）
- 路径方法对比（规格 vs FastAPI）：
  - 规格 8 条操作；后端在 `/api/v1` 前缀下可一一映射
- 状态码对比：
  - 已补充路由 `responses`，剩余差异主要为 FastAPI 自动 `422`

## 结论
- 接口主干已与 `orchestratoropenapi.yaml`、`model-service-openapi.yaml` 对齐，满足联调和上线前置要求。
- 存在 2 个“规范层”可选优化项（自动 422、上传 413/415 显式化），不阻断当前 E2E 与部署流程。
