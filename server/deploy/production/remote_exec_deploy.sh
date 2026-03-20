set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

cd /opt/huaqibei/deploy/production
mkdir -p certs
cp -f .env.example .env
sed -i 's|^AUTODL_SSH_PASSWORD=.*|AUTODL_SSH_PASSWORD=dRk91zvQiwM0|' .env
chmod +x bootstrap_and_deploy.sh
./bootstrap_and_deploy.sh

docker compose --env-file .env -f docker-compose.prod.yml ps
