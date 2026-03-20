# 油价风险智能预测系统

## 项目概述

油价风险智能预测系统是一个基于先进机器学习模型的油价预测和风险分析平台，为用户提供精准的油价预测、风险评估和行业冲击分析。

### 核心功能

- **数据上传**：支持 CSV、XLSX 和 Parquet 格式的数据文件上传，自动进行数据校验和预览
- **智能预测**：基于云端训练的机器学习模型，提供多维度的油价预测和风险评估
- **数据分析**：详细的预测结果分析，包括行业冲击评估、因子贡献分析和知识图谱增强的决策支持
- **可视化展示**：直观的图表展示预测路径、因子贡献和行业冲击

## 技术栈

### 前端
- **框架**：Next.js 16
- **样式**：Tailwind CSS 4
- **动效**：Framer Motion
- **图表**：Recharts

### 后端
- **框架**：FastAPI
- **语言**：Python 3.13
- **数据处理**：Pandas、NumPy
- **模型服务**：自定义机器学习模型

## 快速开始

### 前置条件

- Docker 和 Docker Compose
- Node.js 18+
- Python 3.13+

### 安装和运行

#### 使用 Docker Compose（推荐）

1. 克隆项目仓库

2. 配置环境变量
   - 编辑 `backend/huaqibei/oil-risk-orchestrator/.env` 文件，设置 API_KEY 和其他必要的环境变量
   - 编辑 `docker-compose.yml` 文件，设置模型服务的镜像地址

3. 启动服务

```bash
docker-compose up --build
```

4. 访问应用
   - 前端：http://localhost:3000
   - 后端 API：http://localhost:8000

#### 本地开发

1. 启动后端服务

```bash
cd backend/huaqibei/oil-risk-orchestrator
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

3. 访问应用
   - 前端：http://localhost:3000
   - 后端 API：http://localhost:8000

## 业务流程

1. **数据上传**：用户按照指定格式上传数据表
2. **模型推理**：后端服务器转发给云端推理模型
3. **结果展示**：后端处理后通过前端图表展示

## 项目结构

```
.
├── backend/                  # 后端代码
│   └── huaqibei/             # 项目名称
│       └── oil-risk-orchestrator/  # 后端服务
│           ├── app/          # 应用代码
│           ├── docker/       # Docker 配置
│           └── requirements.txt  # 依赖
├── frontend/                 # 前端代码
│   ├── src/                  # 源代码
│   │   ├── app/              # Next.js 应用
│   │   └── components/       # 组件
│   ├── Dockerfile            # 前端 Dockerfile
│   └── package.json          # 前端依赖
├── docker-compose.yml        # Docker Compose 配置
└── README.md                 # 项目说明
```

## API 文档

### 上传 API
- **路径**：`/upload`
- **方法**：POST
- **功能**：上传数据集文件（CSV/XLSX/Parquet）
- **参数**：
  - `file`：文件（CSV/XLSX/Parquet）
  - `dataset_type`：数据集类型（默认：oil_price_factors）
  - `timezone`：时区（默认：UTC）
  - `frequency`：频率（D/W/M，默认：D）
  - `strict_mode`：是否严格模式（默认：false）
  - `encoding`：文件编码（默认：utf-8）

### 预测 API
- **路径**：`/predict`
- **方法**：POST
- **功能**：油价风险智能预测
- **参数**：
  - `file_id`：上传文件的 ID
  - `horizon`：预测天数
  - `include_explainability`：是否包含因子解释
  - `include_knowledge_graph`：是否包含知识图谱
  - `report_style`：报告风格（detailed/summary）
  - `industries`：目标行业列表

### 报告 API
- **路径**：`/report/knowledge-graph/path/{industry}`
- **方法**：GET
- **功能**：查询行业传导路径

- **路径**：`/report/factors`
- **方法**：GET
- **功能**：获取全量因子字典

- **路径**：`/report/factors/reasons`
- **方法**：GET
- **功能**：获取统计筛选理由标签

- **路径**：`/report/{report_id}`
- **方法**：GET
- **功能**：按 report_id 获取结构化报告

## 前端功能

1. **首页**：展示系统介绍、核心功能和业务流程
2. **数据上传**：支持文件上传和参数配置
3. **预测配置**：设置预测参数和目标行业
4. **结果展示**：展示预测摘要、预测路径、因子贡献、行业冲击和知识图谱

## 设计特点

- **极致科技感**：采用深色背景、金色强调色，营造高端商务氛围
- **金属渐变**：文字标题使用金属渐变效果，配合缓慢的反光动画
- **聚焦效果**：卡片在鼠标悬停时，有一个跟随鼠标位置的微弱金色光晕
- **噪点纹理**：背景叠加一层极淡的动态噪点，防止大面积黑色产生色带
- **微交互**：按钮在悬停时增加字间距和边框发光亮度的微调
- **分层悬浮设计**：元素之间有明显的深度感，使用大面积留白

## 注意事项

1. 确保后端服务和模型服务正常运行
2. 上传的数据文件需要符合指定格式
3. 预测过程可能需要一定时间，取决于数据量和模型复杂度
4. 如需修改模型服务地址，请更新 `docker-compose.yml` 文件中的 `MODEL_SERVICE_URL` 环境变量

## 许可证

MIT License
