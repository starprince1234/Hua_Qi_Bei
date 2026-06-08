# 新闻面板、回测验证与因子历史贡献需求文档

## 1. 背景与问题

当前 Hua Qi Bei Oil Risk Intelligence 已经具备“上传数据 -> 预测配置 -> 结果展示”的完整链路，后端由 FastAPI 编排模型、解释层、行业冲击、知识图谱和 LLM 报告，前端由 Next.js + Recharts 展示预测路径、因子贡献、行业冲击和报告摘要。

现有首界面以上传预测为唯一主入口，适合完成推理闭环，但对比赛演示来说信息密度偏低：评委进入系统后只能看到“上传再预测”，不容易立刻感知系统的数据来源、历史有效性和差异化解释能力。用户提供的新需求本质上是在现有预测系统之上补三类能力：

1. 新闻事件面板：用 GDELT + LLM 形成油价事件驱动信号，并在 GDELT 管道不可用时用 NewsAPI 兜底。
2. 回测验证：展示模型在历史窗口中的方向准确率、RMSE、MAPE、风险区间命中率，以及重大事件节点表现。
3. 因子历史贡献分析：把当前单日因子贡献扩展成按时间变化的堆叠面积图，解释不同行情阶段的主导因素。

核心问题不是“再加几个图表”，而是把系统从单次预测工具升级为“预测、解释、验证、事件监控”一体化工作台。

## 2. 项目现状分析

### 2.1 已有能力

- 前端：首页 `page.tsx` 当前有初始首屏、上传步骤、预测步骤、结果步骤，状态由 `step` 控制。
- 前端图表：`ResultDisplay.tsx` 已使用 Recharts 的折线图、柱状图、饼图，后续回测图和堆叠面积图可复用 Recharts，不需要引入新图表库。
- 后端接口：已有 `/api/v1/upload`、`/api/v1/predict`、`/api/v1/report/*`，统一返回 `APIResponse` 包络。
- 后端架构：路由层、Service 层、Schema 层清晰；预测链路已包含模型调用、后处理、风险分级、行业冲击、SHAP/代理因子贡献、知识图谱、LLM 报告。
- 数据库现状：README 明确当前未发现数据库迁移工具或数据库连接配置，运行主要依赖内置数据与进程内缓存。
- 部署现状：本地和生产均使用 Docker Compose，环境变量通过 Compose `environment` 注入。

### 2.2 需要补齐的能力

- 持久化存储：新闻事件、LLM 增强结果、回测曲线、指标汇总、历史因子贡献都不适合只放进进程内存。建议新增 PostgreSQL 作为主存储。
- 定时任务：新闻事件抓取需要 30 分钟周期任务；回测和因子历史贡献可离线生成后入库。
- API 扩展：新增面向前端工作台的只读接口，避免前端直接访问 BigQuery、NewsAPI 或模型服务。
- 首页导航：首界面应从“营销首屏 + 上传按钮”改为“风险情报工作台”，把上传预测、新闻事件、回测验证、因子历史贡献作为同级入口。

## 3. 总体方案

推荐采用渐进式方案：

第一阶段先完成前端工作台入口、Mock/样例数据接口和回测/历史贡献静态展示，保证比赛演示稳定可用。

第二阶段接入 PostgreSQL、定时新闻任务和真实 GDELT BigQuery 查询，把新闻面板从样例数据升级为真实事件流。

第三阶段把 NewsAPI 作为 fallback，当 GDELT、BigQuery 凭据、数据库或 LLM 增强链路不可用时，仍能展示基本新闻列表。

整体数据流：

```text
GDELT BigQuery / NewsAPI fallback
        |
        v
后端定时任务：清洗、去重、油价关键词筛选
        |
        v
LLM 增强：方向、强度、置信度、影响行业、摘要
        |
        v
PostgreSQL 缓存
        |
        v
GET /api/v1/events
        |
        v
前端新闻事件卡片
```

回测与因子历史贡献数据流：

```text
离线回测作业 / 模型训练产物 / 样例数据
        |
        v
PostgreSQL 或仓库内置 demo JSON
        |
        v
GET /api/v1/backtest/summary
GET /api/v1/backtest/series
GET /api/v1/factors/history
        |
        v
前端“回测验证”和“历史因子贡献”图表
```

## 4. 首界面融入方案

### 4.1 首页定位

首界面建议改为“Oil Risk Intelligence 工作台”，第一屏直接呈现系统四个能力入口：

- 上传预测：进入现有上传、预测、结果流程。
- 新闻事件：查看近 24 小时高影响油价事件，以及看涨/看跌/强度/置信度。
- 回测验证：查看模型历史准确性、误差、区间命中率和重大事件表现。
- 因子历史：查看库存、地缘、宏观、供需、技术等因子贡献随时间变化。

这样可以解决“首界面只有一个上传预测太单调”的问题，也能让评委在没有上传文件前就理解系统价值。

### 4.2 首页信息架构

第一屏建议由三部分组成：

- 顶部状态栏：系统名称、当前数据更新时间、模型版本、新闻源状态。
- 核心入口区：四个 8px 圆角以内的功能卡片或紧凑面板，卡片内展示关键摘要数字，而不是大段功能介绍。
- 下方预览区：显示一个“今日风险摘要”，包含一条高影响新闻、一个回测关键指标、一个当前主导因子。

建议首屏文案减少营销表达，改为面向演示的操作型信息，例如：

- 今日高影响事件：3 条
- 方向准确率：72.3%
- 当前主导因子：地缘事件 31%
- 下一步：上传数据生成预测

### 4.3 页面层级

建议保留单页状态流，先用 tab/section 切换完成，不必立即引入 Next.js 多路由。

```text
Home
  - overview 工作台
  - upload 上传
  - predict 预测配置
  - result 预测结果
  - events 新闻面板
  - backtest 回测验证
  - factorHistory 因子历史贡献
```

后续如果功能继续扩大，再拆成 `/events`、`/backtest`、`/factors/history` 独立路由。

## 5. 新闻事件面板需求

### 5.1 数据源策略

首选方案：后端查询 GDELT BigQuery，然后缓存到 PostgreSQL。

需要修正一点：GDELT 并非完全没有任何 API，它有面向 DOC/GKG/GEO 等能力的接口和网页工具，但对本需求最关键的 `gdelt-bq.gdeltv2.events` 事件表，不适合让前端直接用 REST 方式查询。前端也不应直连 BigQuery。

不让前端直接查 BigQuery的原因：

- 不能暴露 Google Cloud 凭据。
- BigQuery 查询有费用和配额风险。
- 原始 GDELT 事件不含面向比赛展示的中文标题、看涨/看跌、强度、置信度和行业影响。
- 查询延迟通常高于前端列表接口可接受范围。
- 后端需要统一做去重、关键词过滤、LLM 增强、缓存和降级。

兜底方案：NewsAPI。

NewsAPI 是 JSON REST API，适合在比赛演示时快速展示新闻标题、摘要和来源。它不提供 GDELT 的事件编码和结构化冲突/事件指标，因此只能作为新闻列表兜底，不能替代“事件影响分析”。

### 5.2 用户故事

1. 作为评委，我想在首页直接看到高影响油价事件，所以能立即理解系统不是只做时间序列预测。
2. 作为业务用户，我想按影响方向筛选新闻，所以能快速查看看涨、看跌或中性事件。
3. 作为业务用户，我想按影响强度筛选新闻，所以能优先处理强度 7/10 以上的事件。
4. 作为业务用户，我想看到事件置信度，所以能区分模型强判断和弱判断。
5. 作为业务用户，我想看到事件影响行业，所以能判断航空、航运、化工等行业的传导风险。
6. 作为演示人员，我想在 GDELT 管道不可用时自动使用 NewsAPI fallback，所以比赛现场不会出现空白面板。
7. 作为开发者，我想所有外部新闻请求都由后端完成，所以前端不需要也不能持有 BigQuery 或 NewsAPI 密钥。
8. 作为开发者，我想新闻结果入库缓存，所以页面加载时不需要等待 BigQuery 或 LLM。

### 5.3 前端展示

入口位置：

- 首页四大入口之一：“新闻事件”。
- 预测结果页可增加右侧或底部模块：“相关事件驱动”。

列表卡片字段：

- 事件标题，优先中文；没有中文时显示英文标题。
- 发布时间。
- 来源：GDELT 或 NewsAPI。
- 影响方向：看涨、看跌、中性。
- 强度：0-10。
- 置信度：0-100%。
- 影响行业：航空、航运、化工、炼化、物流等。
- 事件摘要。
- 原文链接。

筛选器：

- 影响方向：全部、看涨、看跌、中性。
- 强度：全部、高影响、中影响、低影响。
- 时间范围：24 小时、7 天、30 天。
- 关键词：OPEC、库存、制裁、战争、EIA、需求、美元等。

### 5.4 后端 API

新增接口建议：

```text
GET /api/v1/events
```

查询参数：

```text
impact_direction=bullish|bearish|neutral
impact_level=high|medium|low
source=gdelt|newsapi|all
limit=20
offset=0
from_date=2026-06-01
to_date=2026-06-07
keyword=opec
```

响应数据：

```json
{
  "success": true,
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "event_id": "evt_20260607_001",
        "published_at": "2026-06-07T08:30:00Z",
        "source": "gdelt",
        "provider_event_id": "gdelt_...",
        "title": "沙特减产预期升温",
        "summary": "事件摘要",
        "url": "https://example.com/news",
        "impact_direction": "bullish",
        "impact_score": 8,
        "confidence": 0.82,
        "affected_industries": ["aviation", "shipping", "chemical"],
        "tags": ["OPEC", "supply"],
        "llm_model_id": "Pro/deepseek-ai/DeepSeek-V3.2"
      }
    ],
    "updated_at": "2026-06-07T08:40:00Z",
    "provider_status": "gdelt_cached"
  },
  "request_id": "uuid"
}
```

### 5.5 数据表建议

`news_events`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | uuid/text | 内部事件 ID |
| provider | text | gdelt/newsapi/manual/demo |
| provider_event_id | text | 外部事件 ID，用于去重 |
| published_at | timestamptz | 发布时间 |
| title | text | 标题 |
| title_cn | text | 中文标题，可由 LLM 生成 |
| summary | text | 摘要 |
| url | text | 原文链接 |
| raw_payload | jsonb | 原始数据，便于审计 |
| created_at | timestamptz | 入库时间 |
| updated_at | timestamptz | 更新时间 |

`news_event_analysis`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| event_id | text | 关联 news_events |
| impact_direction | text | bullish/bearish/neutral |
| impact_score | int | 0-10 |
| confidence | numeric | 0-1 |
| affected_industries | jsonb | 行业数组 |
| factor_tags | jsonb | supply/demand/macro/geo/inventory/technical |
| rationale | text | LLM 解释 |
| llm_model_id | text | 模型 ID |
| analysis_version | text | 分析版本 |

### 5.6 定时任务

任务频率：每 30 分钟执行一次。

任务步骤：

1. 查询 GDELT BigQuery，筛选 oil、crude、Brent、WTI、OPEC、EIA、sanction、conflict 等关键词。
2. 事件去重，按 URL、标题相似度、provider_event_id 去重。
3. 调用 LLM 生成结构化分析：方向、强度、置信度、行业、标签、中文摘要。
4. 写入 PostgreSQL。
5. 若 GDELT 失败且 `NEWS_PROVIDER=hybrid`，调用 NewsAPI 兜底。
6. 若外部源都失败，保留最近一次缓存，并在接口返回 `provider_status=stale_cache`。

### 5.7 降级策略

- GDELT 查询失败：使用最近缓存。
- BigQuery 凭据缺失：跳过 GDELT，返回 demo 或 NewsAPI。
- LLM 失败：返回新闻原文 + 规则关键词方向判断，并标记 `analysis_version=rule_fallback`。
- NewsAPI 配额耗尽：返回最近缓存并显示更新时间。
- 数据库不可用：第一阶段可从内置 demo JSON 返回演示数据。

## 6. 回测验证需求

### 6.1 目标

新增与“预测”同级的 Tab：“回测验证”。它的作用是回答评委最关心的问题：模型历史上到底准不准，在哪些行情阶段表现好，在哪些阶段表现会下降。

### 6.2 用户故事

1. 作为评委，我想看到方向准确率，所以能判断模型是否显著优于随机猜测。
2. 作为评委，我想看到 RMSE 和 MAPE，所以能判断价格预测误差大小。
3. 作为评委，我想看到风险区间命中率，所以能判断不确定性区间是否可靠。
4. 作为业务用户，我想看到预测与实际走势叠加图，所以能直观看到预测是否贴近实际价格。
5. 作为业务用户，我想看到重大事件节点标注，所以能判断模型在极端行情下是否仍有解释力。
6. 作为开发者，我想回测数据由后端统一返回，所以前端不需要计算核心指标。
7. 作为演示人员，我想先使用内置 demo 回测结果，所以真实离线回测未接入时也能稳定展示。

### 6.3 前端展示

页面结构：

第一块：关键指标卡片，顶部一行四张卡片。

- 方向准确率：72.3%，说明“高于随机 50%”。
- RMSE：$3.21，说明“越小越好”。
- MAPE：4.8%，说明“越小越好”。
- 风险区间命中率：高风险 85% / 中 76% / 低 80%。

每张卡片可展示相较上一年度或上一训练版本的变化，例如 `+3.2%`。

第二块：预测 vs 实际走势对比图。

- 灰色实线：实际 Brent/WTI 价格。
- 蓝色虚线：模型回测预测值。
- 浅蓝透明带：预测置信区间。
- 关键事件标注：2020-04 负油价、2022-02 俄乌战争、2023-10 巴以冲突等。

第三块：预测误差分布。

- 横轴：误差区间。
- 纵轴：频次。
- 目标形态：大部分误差集中在 0 附近，两侧尾部较短。

第四块：分阶段表现表格。

| 行情阶段 | 方向准确率 | RMSE |
| --- | --- | --- |
| 平稳期（2015-2019） | 78% | $2.1 |
| 高波动期（2020-2022） | 65% | $5.8 |
| 恢复期（2023-2025） | 74% | $3.0 |

### 6.4 后端 API

建议提供三个接口，便于前端局部加载：

```text
GET /api/v1/backtest/summary
GET /api/v1/backtest/series
GET /api/v1/backtest/errors
```

`GET /api/v1/backtest/summary` 响应：

```json
{
  "success": true,
  "code": 200,
  "data": {
    "target": "Brent",
    "window": "2015-01-01/2025-12-31",
    "metrics": {
      "direction_accuracy": 0.723,
      "rmse": 3.21,
      "mape": 0.048,
      "interval_hit_rate": {
        "high": 0.85,
        "medium": 0.76,
        "low": 0.80
      }
    },
    "stage_metrics": [
      {
        "stage": "平稳期（2015-2019）",
        "direction_accuracy": 0.78,
        "rmse": 2.1
      }
    ]
  }
}
```

`GET /api/v1/backtest/series` 响应：

```json
{
  "success": true,
  "code": 200,
  "data": {
    "points": [
      {
        "date": "2022-02-24",
        "actual_price": 96.84,
        "predicted_price": 94.21,
        "lower_price": 89.30,
        "upper_price": 101.70
      }
    ],
    "events": [
      {
        "date": "2022-02-24",
        "label": "俄乌战争爆发",
        "hit_interval": true,
        "actual_return_7d": 0.097,
        "predicted_return_7d": 0.082
      }
    ]
  }
}
```

`GET /api/v1/backtest/errors` 响应：

```json
{
  "success": true,
  "code": 200,
  "data": {
    "bins": [
      { "range": "-5~-3", "count": 12 },
      { "range": "-3~-1", "count": 38 },
      { "range": "-1~1", "count": 96 }
    ]
  }
}
```

### 6.5 数据表建议

`backtest_runs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| run_id | text | 回测批次 |
| model_version | text | 模型版本 |
| target | text | Brent/WTI |
| start_date | date | 开始日期 |
| end_date | date | 结束日期 |
| metrics | jsonb | 汇总指标 |
| created_at | timestamptz | 创建时间 |

`backtest_points`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| run_id | text | 回测批次 |
| date | date | 日期 |
| actual_price | numeric | 实际价格 |
| predicted_price | numeric | 预测价格 |
| lower_price | numeric | 下界 |
| upper_price | numeric | 上界 |
| actual_return | numeric | 实际收益 |
| predicted_return | numeric | 预测收益 |
| risk_level | text | 风险等级 |

`backtest_event_marks`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| run_id | text | 回测批次 |
| date | date | 事件日期 |
| label | text | 标注名称 |
| description | text | 说明 |
| hit_interval | bool | 是否命中区间 |
| actual_return_7d | numeric | 7 天实际收益 |
| predicted_return_7d | numeric | 7 天预测收益 |

## 7. 因子历史贡献分析需求

### 7.1 目标

现有结果页展示的是“当前一次预测的 Top 因子贡献”，适合解释单次预测。新增历史贡献图后，系统能说明不同行情阶段的驱动因素如何切换，形成更完整的模型解释闭环。

### 7.2 用户故事

1. 作为评委，我想看到因子贡献随时间变化，所以能理解模型不是黑盒输出。
2. 作为业务用户，我想看到库存、地缘、宏观、供需、技术因子的占比，所以能判断当前行情由什么主导。
3. 作为业务用户，我想在鼠标悬停时看到某天的贡献分解，所以能解释重大事件当天的预测逻辑。
4. 作为演示人员，我想用 2020、2022、2023 等事件讲故事，所以能把模型结果和宏观事实连接起来。
5. 作为开发者，我想复用现有因子类别字典，所以不需要另建一套解释标签体系。

### 7.3 前端展示

推荐展示位置：

- 方案一：在预测结果页现有“Factor Contribution”模块增加 Tab：“今日贡献 / 历史变化”。
- 方案二：在“回测验证”Tab 的下半部分展示。

最佳实践建议：两处都给入口，但主展示放在“回测验证”Tab 下方；预测结果页只做轻量入口，避免单次预测结果页过长。

唯一核心图表：因子贡献堆叠面积图。

图表要求：

- 横轴：日期或年份。
- 纵轴：百分比，所有因子类别之和为 100%。
- 分类：库存因子、地缘事件因子、宏观因子、供需因子、技术因子。
- 鼠标悬停显示该日期贡献分解、模型预测、实际走势和是否命中区间。

Tooltip 示例：

```text
2022年2月24日 - 俄乌战争爆发
地缘事件因子：48%
库存因子：18%
宏观因子：15%
供需因子：12%
技术因子：7%
模型预测：7天 +8.2% [区间 +3.1% ~ +14.5%]
实际走势：7天 +9.7%，命中区间
```

### 7.4 后端 API

```text
GET /api/v1/factors/history
```

查询参数：

```text
target=Brent
from_date=2015-01-01
to_date=2025-12-31
granularity=month
```

响应：

```json
{
  "success": true,
  "code": 200,
  "data": {
    "categories": ["inventory", "geo", "macro", "supply_demand", "technical"],
    "points": [
      {
        "date": "2022-02-24",
        "inventory": 0.18,
        "geo": 0.48,
        "macro": 0.15,
        "supply_demand": 0.12,
        "technical": 0.07,
        "event_label": "俄乌战争爆发",
        "predicted_return_7d": 0.082,
        "lower_return_7d": 0.031,
        "upper_return_7d": 0.145,
        "actual_return_7d": 0.097,
        "hit_interval": true
      }
    ]
  }
}
```

### 7.5 数据表建议

`factor_contribution_history`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| run_id | text | 回测或模型批次 |
| date | date | 日期 |
| target | text | Brent/WTI |
| factor_category | text | inventory/geo/macro/supply_demand/technical |
| contribution_pct | numeric | 贡献占比，0-1 |
| raw_contribution | numeric | 原始贡献值，可选 |
| top_factors | jsonb | 该类下 Top 因子 |

## 8. 最佳实践与工程决策

### 8.1 架构决策

- 前端只调用后端 `/api/v1/*`，不直接访问 BigQuery、NewsAPI、LLM 或模型服务。
- 后端保持现有分层风格，新增 `events`、`backtest`、`factor_history` 路由与对应 Service。
- 所有接口继续使用 `APIResponse` 统一包络。
- 第一阶段允许内置 demo JSON，保证演示稳定；第二阶段引入数据库和定时任务。
- 真实新闻增强必须缓存，页面加载不等待外部 API 和 LLM。
- NewsAPI 仅作为 fallback，不作为主事件解释来源。
- LLM 输出必须结构化校验，失败时使用规则 fallback。
- 因子历史贡献优先按类别聚合，避免图表出现过多单因子导致不可读。

### 8.2 前端设计决策

- 首屏从大 hero 改为信息工作台，上传预测仍为主 CTA，但不是唯一入口。
- 回测 Tab 与预测 Tab 平级，强调模型可信度。
- 卡片半径保持 8px 或更小，符合现有金融工具气质。
- 图表使用 Recharts，复用现有依赖。
- 文案使用中英混合时需保持一致性；比赛展示建议关键指标中文、专业字段英文缩写保留。
- 图表颜色避免单一金色系，建议灰、蓝、红、绿、金组合，提高可读性。

### 8.3 后端设计决策

- 新增配置集中到 `Settings`，并同步 `.env.example`、生产 `.env.example`。
- BigQuery 查询设置最大扫描字节，避免费用失控。
- 定时任务建议先用 FastAPI lifespan 启动后台任务或 APScheduler；生产长期建议拆独立 worker。
- 数据库迁移建议引入 Alembic，但第一阶段可用 SQL 初始化脚本或 demo JSON。
- API 默认返回最近缓存，并明确 `updated_at` 和 `provider_status`。

### 8.4 安全与环境变量

本次需求涉及新增配置：

| 变量名 | 说明 | 目标环境 |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL 连接串 | Development -> dev_personal；Production -> prd |
| `NEWS_PROVIDER` | `mock`、`gdelt`、`newsapi`、`hybrid` | Development -> dev_personal；Production -> prd |
| `NEWS_REFRESH_INTERVAL_MINUTES` | 新闻刷新周期，默认 30 | Development -> dev_personal；Production -> prd |
| `GDELT_BIGQUERY_PROJECT_ID` | Google Cloud 项目 ID | Development -> dev_personal；Production -> prd |
| `GDELT_BIGQUERY_MAX_BYTES_BILLED` | BigQuery 单次查询最大扫描字节 | Development -> dev_personal；Production -> prd |
| `NEWSAPI_API_KEY` | NewsAPI 密钥，仅 fallback 使用 | Development -> dev_personal；Production -> prd |

注意：

- 本地不得创建真实 `.env` 文件。
- 真实值必须录入 Doppler。
- Docker Compose 通过 `${VAR}` 从宿主进程读取 Doppler 注入值。
- example 文件只能保留占位值。

## 9. 实施里程碑

### M1：演示稳定版

- 首页改为工作台入口。
- 新增“新闻事件”“回测验证”“因子历史”前端视图。
- 后端新增三个只读路由，先返回内置 demo 数据。
- 完成 Recharts 折线图、误差分布图、堆叠面积图。
- 前端 lint 通过。

验收标准：

- 用户打开首页即可看到四个功能入口。
- 不上传文件也能进入新闻、回测、因子历史页面。
- 断网或无外部密钥时演示页面不空白。

### M2：数据库与真实缓存

- 引入 PostgreSQL 连接和迁移。
- 新增新闻事件、回测点、因子历史贡献表。
- 后端接口改为优先读数据库，数据库为空时读 demo。
- 增加种子数据导入脚本。

验收标准：

- 重启后新闻和回测数据仍可读取。
- 接口返回 `updated_at`、`provider_status`。
- 数据库不可用时有明确降级。

### M3：GDELT + LLM 新闻管道

- 后端实现 GDELT BigQuery 查询。
- 定时任务每 30 分钟拉取、去重、增强、入库。
- LLM 生成方向、强度、置信度、行业和中文摘要。
- NewsAPI fallback 生效。

验收标准：

- `NEWS_PROVIDER=gdelt` 时可读取 GDELT 增强事件。
- `NEWS_PROVIDER=hybrid` 且 GDELT 失败时自动 fallback 到 NewsAPI。
- 不暴露任何外部服务密钥到前端。

### M4：真实回测与因子历史接入

- 从离线回测产物导入真实指标和序列。
- 重大事件节点可配置。
- 因子历史贡献按模型 SHAP 或代理贡献聚合入库。
- 前端支持 target、时间范围、粒度切换。

验收标准：

- 回测指标与离线结果一致。
- 阶段表格、走势图、误差分布来自同一 `run_id`。
- Tooltip 能展示指定事件日的因子贡献、预测和实际走势。

## 10. 测试决策

后端测试：

- 使用 FastAPI TestClient 测试新增 API 的响应包络、字段完整性、筛选参数和空数据降级。
- 测试 GDELT/NewsAPI service 时 mock 外部 HTTP/BigQuery 客户端，不访问真实外部服务。
- 测试 LLM 增强失败时是否进入规则 fallback。
- 测试数据库为空、数据库不可用、缓存过期的返回状态。

前端测试：

- 现阶段至少运行 `npm run lint`。
- 后续建议增加组件级测试，重点覆盖 tab 切换、空状态、图表数据转换。
- 如引入 Playwright，覆盖首页四入口、新闻筛选、回测图表渲染、因子 tooltip。

数据质量测试：

- 新闻去重：同 URL、近似标题、同 provider_event_id 不重复入库。
- 回测指标：方向准确率、RMSE、MAPE、区间命中率计算口径固定。
- 因子贡献：同一日期各类别 contribution_pct 之和应接近 1。

## 11. 非目标范围

- 不在本阶段实现前端直连 BigQuery。
- 不在本阶段把 NewsAPI 作为主数据源。
- 不在本阶段重训油价预测模型。
- 不在本阶段引入复杂权限系统。
- 不在本阶段实现完整报告 PDF 导出。
- 不在本阶段把知识图谱迁移到 Neo4j。

## 12. 外部资料核对

- GDELT 官网数据页说明其数据可通过下载、查询和分析方式使用，并提供 GDELT 2.0 Events 下载入口与 BigQuery 相关入口：https://www.gdeltproject.org/data.html
- GDELT 2.0 介绍页提到 Events、Mentions、Global Knowledge Graph 可在 Google BigQuery 中访问：https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
- NewsAPI 官网说明其提供新闻 JSON REST API：https://newsapi.org/
- NewsAPI pricing 页显示 Developer 计划为 100 requests/day，且用于开发和测试：https://newsapi.org/pricing

## 13. Doppler 录入指引

### [操作指引] 需要在 Doppler 中录入新环境变量

发现新功能需要使用环境变量，请前往 Doppler 官网进行配置。

#### 1. 访问链接

- 请点击打开 Doppler 控制台：[Doppler Dashboard](https://dashboard.doppler.com/)

#### 2. 配置详情

| 推荐字段名 (Key) | 建议值/说明 (Value Description) | 适用环境 (Target Config) |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL 连接串；开发环境可使用开发库 | `Development -> dev_personal` |
| `DATABASE_URL` | PostgreSQL 生产连接串 | `Production -> prd` |
| `NEWS_PROVIDER` | 开发建议先填 `mock` 或 `hybrid` | `Development -> dev_personal` |
| `NEWS_PROVIDER` | 生产建议填 `gdelt` 或 `hybrid` | `Production -> prd` |
| `NEWS_REFRESH_INTERVAL_MINUTES` | 建议填 `30` | `Development -> dev_personal` |
| `NEWS_REFRESH_INTERVAL_MINUTES` | 建议填 `30` | `Production -> prd` |
| `GDELT_BIGQUERY_PROJECT_ID` | Google Cloud 项目 ID，不是密钥，但仍建议托管 | `Development -> dev_personal` |
| `GDELT_BIGQUERY_PROJECT_ID` | 生产 Google Cloud 项目 ID | `Production -> prd` |
| `GDELT_BIGQUERY_MAX_BYTES_BILLED` | 建议填 `1073741824`，约 1 GiB | `Development -> dev_personal` |
| `GDELT_BIGQUERY_MAX_BYTES_BILLED` | 按生产预算设置上限 | `Production -> prd` |
| `NEWSAPI_API_KEY` | NewsAPI 开发 key，仅 fallback 使用 | `Development -> dev_personal` |
| `NEWSAPI_API_KEY` | NewsAPI 生产 key，仅 fallback 使用 | `Production -> prd` |

#### 3. 绝对防护警告（防污染）

在 **Production (`prd`)** 环境中保存此变量时，Doppler 可能会弹窗提示：

> "Please Confirm: Do you want to sync these secrets to other environments?"

请绝对不要勾选 Development 或 Staging，保持所有框为空，直接点击确认，确保生产密钥不会污染本地开发环境。

#### 4. 骨架文件已更新

我已为您自动更新本地 `.env.example` 系列文件，确保结构完整。

本地 Docker 启动建议使用：

```bash
doppler run -- docker compose up -d
```

不依赖 Docker 的本地后端启动建议使用：

```bash
doppler run -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
