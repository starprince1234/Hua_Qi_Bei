#!/usr/bin/env bash
set -e

systemctl restart autodl-tunnel
sleep 2

echo '===TUNNEL_STATUS===' 
systemctl status autodl-tunnel --no-pager -n 30 || true

echo '===PORT_6006===' 
ss -ltnp | grep 6006 || true

echo '===BACKEND_TO_MODEL===' 
docker exec huaqibei_prod-backend-1 /bin/sh -lc "apk add --no-cache curl >/dev/null 2>&1 || true; curl -sS -m 10 -i http://host.docker.internal:6006/v1/models || true"
