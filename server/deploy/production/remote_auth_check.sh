#!/usr/bin/env bash
set -e
cd /opt/huaqibei/deploy/production

echo '===ENV_AUTODL===' 
if [ -f .env ]; then
  grep -E '^AUTODL_(SSH_HOST|SSH_PORT|SSH_USER|SSH_PASSWORD)=' .env || true
else
  echo '.env missing'
fi

echo '===UNIT_FILE===' 
sed -n '1,220p' /etc/systemd/system/autodl-tunnel.service || true

echo '===MANUAL_AUTH_TEST===' 
AUTODL_SSH_PASSWORD=$(grep -E '^AUTODL_SSH_PASSWORD=' .env | sed -E 's/^AUTODL_SSH_PASSWORD=//')
AUTODL_SSH_USER=$(grep -E '^AUTODL_SSH_USER=' .env | sed -E 's/^AUTODL_SSH_USER=//')
AUTODL_SSH_HOST=$(grep -E '^AUTODL_SSH_HOST=' .env | sed -E 's/^AUTODL_SSH_HOST=//')
AUTODL_SSH_PORT=$(grep -E '^AUTODL_SSH_PORT=' .env | sed -E 's/^AUTODL_SSH_PORT=//')
sshpass -p "$AUTODL_SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -p "$AUTODL_SSH_PORT" "$AUTODL_SSH_USER@$AUTODL_SSH_HOST" 'echo AUTH_OK' || true
