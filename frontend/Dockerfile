# 使用 Node.js 20 作为基础镜像（Next.js 16 要求 >=20.9）
FROM node:20-alpine

# 设置工作目录
WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://localhost:18000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 构建生产版本
RUN rm -rf .next && npm run build

# 暴露端口
EXPOSE 3000

# 启动应用
CMD ["npm", "start"]
