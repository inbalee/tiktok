#!/usr/bin/env bash
set -euo pipefail

# Deploy the production Docker stack locally or to a remote EC2 instance.
#
# Local (default):
#   bash deploy/deploy.sh
#   EC2_HOST=localhost bash deploy/deploy.sh
#
# Remote EC2:
#   EC2_HOST=1.2.3.4 SSH_KEY=~/.ssh/key.pem bash deploy/deploy.sh
#
# Optional env vars:
#   EC2_HOST   Target host (default: localhost)
#   EC2_USER   SSH user for remote deploy (default: ec2-user)
#   SSH_KEY    Path to SSH private key for remote deploy
#   APP_DIR    App directory on remote host (default: /opt/tiktok)

EC2_HOST="${EC2_HOST:-localhost}"
EC2_USER="${EC2_USER:-ec2-user}"
APP_DIR="${APP_DIR:-/opt/tiktok}"
SSH_KEY="${SSH_KEY:-}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

is_local_deploy() {
  case "$EC2_HOST" in
    localhost|127.0.0.1|::1) return 0 ;;
    *) return 1 ;;
  esac
}

deploy_local() {
  cd "$ROOT_DIR"

  if [ ! -f .env ]; then
    cp .env.example .env
  fi

  echo "==> Building and starting containers locally"
  docker compose -f docker-compose.prod.yml up -d --build
  docker compose -f docker-compose.prod.yml ps

  echo
  echo "Deployment complete."
  echo "App URL: http://localhost/"
  echo "Swagger: http://localhost/docs"
}

deploy_remote() {
  SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
  if [ -n "$SSH_KEY" ]; then
    SSH_OPTS+=(-i "$SSH_KEY")
  fi

  REMOTE="${EC2_USER}@${EC2_HOST}"
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

  echo "==> Building and starting containers on ${EC2_HOST}"
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
}

if is_local_deploy; then
  deploy_local
else
  deploy_remote
fi
