#!/usr/bin/env bash
set -euo pipefail

# Deploy the app to a remote EC2 instance over SSH.
#
# Required env vars:
#   EC2_HOST   Public IP or DNS of the EC2 instance
#
# Optional env vars:
#   EC2_USER   SSH user (default: ec2-user)
#   SSH_KEY    Path to SSH private key
#   APP_DIR    Remote app directory (default: /opt/tiktok)

EC2_HOST="${EC2_HOST:?Set EC2_HOST to your instance public IP or DNS}"
EC2_USER="${EC2_USER:-ec2-user}"
APP_DIR="${APP_DIR:-/opt/tiktok}"
SSH_KEY="${SSH_KEY:-}"

SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
if [ -n "$SSH_KEY" ]; then
  SSH_OPTS+=(-i "$SSH_KEY")
fi

REMOTE="${EC2_USER}@${EC2_HOST}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SSH_CMD=(ssh "${SSH_OPTS[@]}")

echo "==> Syncing project to ${REMOTE}:${APP_DIR}"
"${SSH_CMD[@]}" "$REMOTE" "sudo mkdir -p '$APP_DIR' && sudo chown -R ${EC2_USER}:${EC2_USER} '$APP_DIR'"

RSYNC_SSH=""
for opt in "${SSH_OPTS[@]}"; do
  RSYNC_SSH+=" $(printf '%q' "$opt")"
done

rsync -az --delete \
  --exclude '.git' \
  --exclude 'venv' \
  --exclude '__pycache__' \
  --exclude '.env' \
  --exclude 'scraper/.git' \
  -e "ssh${RSYNC_SSH}" \
  "$ROOT_DIR/" "$REMOTE:$APP_DIR/"

echo "==> Building and starting containers"
"${SSH_CMD[@]}" "$REMOTE" bash -s <<EOF
set -euo pipefail
cd '$APP_DIR'

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
EOF

echo
echo "Deployment complete."
echo "App URL: http://${EC2_HOST}/"
echo "Swagger: http://${EC2_HOST}/docs"
