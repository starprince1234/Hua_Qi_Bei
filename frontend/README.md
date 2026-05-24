# Hua Qi Bei Frontend

这是油价风险智能预测系统的 Next.js 前端，负责数据上传、预测参数配置和预测结果可视化展示。

## 技术栈

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- Framer Motion
- Recharts

## 本地运行

```bash
npm install
npm run dev
```

默认访问地址：

```text
http://localhost:3000
```

## 后端 API 地址

前端通过 `NEXT_PUBLIC_API_URL` 指向后端服务。默认值为 `/api`，适合生产环境通过 Nginx 反向代理访问。

本地开发时，如果后端运行在 `http://localhost:8000`，可设置：

```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

cmd 可使用：

```bat
set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## 常用命令

```bash
npm run dev      # 启动开发服务
npm run build    # 构建生产版本
npm run start    # 启动生产服务
npm run lint     # 运行 ESLint
```

## 构建产物

生产构建产物位于 `.next/`，该目录不应提交到 GitHub。

## 更多说明

完整项目复现、后端启动、Docker 和部署说明见根目录 `README.md`。
