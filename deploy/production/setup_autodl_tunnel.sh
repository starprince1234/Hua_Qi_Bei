#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "请先在当前目录创建 .env（可从 .env.example 复制）"
  exit 1
fi

set -a
source .env
set +a

: "${AUTODL_SSH_HOST:?AUTODL_SSH_HOST 未设置}"
: "${AUTODL_SSH_PORT:?AUTODL_SSH_PORT 未设置}"
: "${AUTODL_SSH_USER:?AUTODL_SSH_USER 未设置}"
: "${AUTODL_SSH_PASSWORD:?AUTODL_SSH_PASSWORD 未设置}"
: "${AUTODL_LOCAL_PORT:?AUTODL_LOCAL_PORT 未设置}"
: "${AUTODL_REMOTE_HOST:?AUTODL_REMOTE_HOST 未设置}"
: "${AUTODL_REMOTE_PORT:?AUTODL_REMOTE_PORT 未设置}"

sudo apt-get update -y
sudo apt-get install -y autossh sshpass

SERVICE_FILE=/etc/systemd/system/autodl-tunnel.service
SSH_PASSWORD="${AUTODL_SSH_PASSWORD//\'/\'\"\'\"\'}"

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=AutoDL SSH Tunnel (port forward to local ${AUTODL_LOCAL_PORT})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment="AUTOSSH_GATETIME=0"
Environment="AUTOSSH_POLL=30"
Environment="AUTOSSH_FIRST_POLL=30"
ExecStart=/usr/bin/sshpass -p '${SSH_PASSWORD}' /usr/bin/autossh -M 0 -N -C -g \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=no \
  -L 0.0.0.0:${AUTODL_LOCAL_PORT}:${AUTODL_REMOTE_HOST}:${AUTODL_REMOTE_PORT} \
  ${AUTODL_SSH_USER}@${AUTODL_SSH_HOST} -p ${AUTODL_SSH_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now autodl-tunnel
sudo systemctl --no-pager --full status autodl-tunnel

echo "隧道已启动。可在服务器上测试: curl -I http://127.0.0.1:${AUTODL_LOCAL_PORT}"
