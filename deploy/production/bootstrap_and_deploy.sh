#!/usr/bin/env bash
set -euo pipefail

chmod +x ./setup_autodl_tunnel.sh ./deploy.sh
./setup_autodl_tunnel.sh
./deploy.sh
