# HUAQIBEI 生产部署说明

本目录用于 Ubuntu 服务器（如阿里云）部署前后端容器，并通过 SSH 隧道接入 AutoDL 模型服务。

## 1. 本地 Windows 构建并推送镜像

在项目根目录执行：

```powershell
# 如未登录
# docker login

powershell -ExecutionPolicy Bypass -File .\deploy\publish-images.ps1 -DockerUser starprince123 -Tag v1 -AlsoLatest
```

会推送：
- starprince123/huaqibei-backend:v1
- starprince123/huaqibei-frontend:v1
- 可选 latest 标签

## 2. 服务器准备

将本目录文件上传到服务器任意目录，例如 /opt/huaqibei/deploy/production。

```bash
mkdir -p /opt/huaqibei/deploy/production
cd /opt/huaqibei/deploy/production
# 把本目录文件上传到这里
```

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 .env（至少填写以下项）：
- BACKEND_TAG=v1
- FRONTEND_TAG=v1
- MODEL_API_URL=http://host.docker.internal:6006
- AUTODL_SSH_PASSWORD=你的 AutoDL 密码
- 如需报告 LLM：LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_ID

## 3. 建立 AutoDL SSH 隧道（服务器端）

```bash
chmod +x setup_autodl_tunnel.sh
./setup_autodl_tunnel.sh
```

该脚本会安装 autossh/sshpass，并创建 systemd 服务 `autodl-tunnel`，将服务器 6006 端口转发到 AutoDL 的 127.0.0.1:6006。

检查状态：

```bash
systemctl status autodl-tunnel --no-pager
```

## 4. 启动业务容器

```bash
chmod +x deploy.sh
./deploy.sh
```

或一键执行（隧道+部署）：

```bash
chmod +x bootstrap_and_deploy.sh
./bootstrap_and_deploy.sh
```

成功后访问：
- 前端: http://你的服务器公网IP/
- 健康检查: http://你的服务器公网IP/healthz

## 5. 常见问题

1. 容器访问不到 6006：
- 确认 `autodl-tunnel` 服务在 running
- 确认 `.env` 的 `MODEL_API_URL=http://host.docker.internal:6006`
- 后端 compose 已配置 `host.docker.internal:host-gateway`

2. 镜像拉取失败：
- 先在服务器执行 `docker login`

3. 更新版本：
- 本地重新推送新 tag
- 服务器修改 `.env` 中 BACKEND_TAG / FRONTEND_TAG
- 重新执行 `./deploy.sh`

## 6. 回滚

将 `.env` 的 BACKEND_TAG / FRONTEND_TAG 改回历史版本后执行：

```bash
./deploy.sh
```
