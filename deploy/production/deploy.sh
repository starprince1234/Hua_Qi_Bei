#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "请先在当前目录创建 .env（可从 .env.example 复制）"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "未检测到 docker，请先安装 Docker Engine"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "未检测到 docker compose"
  exit 1
fi

echo "使用 compose 命令: $COMPOSE"

echo "[1/4] 拉取镜像..."
$COMPOSE --env-file .env -f docker-compose.prod.yml pull

echo "[2/4] 启动服务..."
$COMPOSE --env-file .env -f docker-compose.prod.yml up -d

echo "[3/4] 查看容器状态..."
$COMPOSE -f docker-compose.prod.yml ps

echo "[4/4] 健康检查..."
sleep 5
curl -fsS http://127.0.0.1/healthz && echo

echo "部署完成。"
