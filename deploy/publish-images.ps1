param(
    [string]$DockerUser = "starprince123",
    [string]$Tag = "v1",
    [switch]$AlsoLatest
)

$ErrorActionPreference = "Stop"

Write-Host "[1/5] 检查 Docker 登录状态..."
$null = docker info

Write-Host "[2/5] 构建后端镜像..."
docker build `
  -t "$DockerUser/huaqibei-backend:$Tag" `
  -f "backend/huaqibei/oil-risk-orchestrator/docker/Dockerfile" `
  "backend/huaqibei/oil-risk-orchestrator"

Write-Host "[3/5] 构建前端镜像..."
docker build `
  -t "$DockerUser/huaqibei-frontend:$Tag" `
  --build-arg NEXT_PUBLIC_API_URL=/api `
  -f "frontend/Dockerfile" `
  "frontend"

if ($AlsoLatest) {
    Write-Host "为 latest 打标签..."
    docker tag "$DockerUser/huaqibei-backend:$Tag" "$DockerUser/huaqibei-backend:latest"
    docker tag "$DockerUser/huaqibei-frontend:$Tag" "$DockerUser/huaqibei-frontend:latest"
}

Write-Host "[4/5] 推送后端镜像..."
docker push "$DockerUser/huaqibei-backend:$Tag"
if ($AlsoLatest) {
    docker push "$DockerUser/huaqibei-backend:latest"
}

Write-Host "[5/5] 推送前端镜像..."
docker push "$DockerUser/huaqibei-frontend:$Tag"
if ($AlsoLatest) {
    docker push "$DockerUser/huaqibei-frontend:latest"
}

Write-Host "完成:"
Write-Host "  $DockerUser/huaqibei-backend:$Tag"
Write-Host "  $DockerUser/huaqibei-frontend:$Tag"
