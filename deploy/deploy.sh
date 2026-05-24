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
#   EC2_HOST=1.2.3.4 TIKTOK_HTTP_PORT=5002 SSH_KEY=~/.ssh/key.pem bash deploy/deploy.sh
#
# Optional env vars:
#   EC2_HOST          Target host (default: localhost)
#   EC2_USER          SSH user for remote deploy (default: ec2-user)
#   SSH_KEY           Path to SSH private key for remote deploy
#   APP_DIR           App directory on remote host (default: /opt/tiktok)
#   TIKTOK_HTTP_PORT  Public nginx port (default: 80; use 5002 on shared hosts)

EC2_HOST="${EC2_HOST:-localhost}"
EC2_USER="${EC2_USER:-ec2-user}"
APP_DIR="${APP_DIR:-/opt/tiktok}"
SSH_KEY="${SSH_KEY:-}"
TIKTOK_HTTP_PORT="${TIKTOK_HTTP_PORT:-80}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export TIKTOK_HTTP_PORT

is_local_deploy() {
  case "$EC2_HOST" in
    localhost|127.0.0.1|::1) return 0 ;;
    *) return 1 ;;
  esac
}

print_security_group_reminder() {
  local host="$1"
  local port="$2"
  echo
  echo "If you cannot reach the app from your browser, open the EC2 security group:"
  echo "  - TCP ${port} from your IP (tiktok nginx)"
  echo
  if [ "$port" = "80" ]; then
    echo "Then use: http://${host}/"
  else
    echo "Then use: http://${host}:${port}/"
  fi
}

app_url() {
  local host="$1"
  local port="$2"
  if [ "$port" = "80" ]; then
    echo "http://${host}/"
  else
    echo "http://${host}:${port}/"
  fi
}

verify_deployment() {
  local host="$1"
  local port="$2"
  echo "==> Verifying deployment on the server"

  if docker compose -f docker-compose.prod.yml exec -T app curl -fsS "http://127.0.0.1:5001/openapi.json" >/dev/null 2>&1; then
    echo "    app health check OK (internal :5001)"
  else
    echo "    WARNING: app not responding internally on :5001"
    return 1
  fi

  if curl -fsS "http://127.0.0.1:${port}/openapi.json" >/dev/null; then
    echo "    nginx health check OK (localhost:${port})"
  else
    echo "    WARNING: nginx not responding on localhost:${port}"
    return 1
  fi

  print_security_group_reminder "$host" "$port"
}

verify_external_access() {
  local host="$1"
  local port="$2"
  local url

  echo "==> Checking external access to ${host}"

  if [ "$port" = "80" ]; then
    url="http://${host}/openapi.json"
  else
    url="http://${host}:${port}/openapi.json"
  fi

  if curl -fsS --connect-timeout 5 "$url" >/dev/null; then
    echo "    external nginx check OK (${host}:${port})"
  else
    echo "    WARNING: cannot reach ${url} from this machine"
    print_security_group_reminder "$host" "$port"
    return 1
  fi
}

print_completion() {
  local host="$1"
  local port="$2"
  local base_url
  base_url="$(app_url "$host" "$port")"

  echo
  echo "Deployment complete."
  echo "App URL:   ${base_url}"
  echo "Swagger:   ${base_url}docs"
}

deploy_local() {
  cd "$ROOT_DIR"

  if [ ! -f .env ]; then
    cp .env.example .env
  fi

  echo "==> Building and starting containers locally (nginx on port ${TIKTOK_HTTP_PORT})"
  docker compose -f docker-compose.prod.yml up -d --build
  docker compose -f docker-compose.prod.yml ps
  verify_deployment "localhost" "$TIKTOK_HTTP_PORT"
  print_completion "localhost" "$TIKTOK_HTTP_PORT"
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

  echo "==> Building and starting containers on ${EC2_HOST} (nginx on port ${TIKTOK_HTTP_PORT})"
  "${SSH_CMD[@]}" "$REMOTE" bash -s <<EOF
set -euo pipefail
cd '$APP_DIR'
export TIKTOK_HTTP_PORT='${TIKTOK_HTTP_PORT}'

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps

echo "==> Verifying deployment on the server"
docker compose -f docker-compose.prod.yml exec -T app curl -fsS http://127.0.0.1:5001/openapi.json >/dev/null
echo "    app health check OK (internal :5001)"
curl -fsS "http://127.0.0.1:\${TIKTOK_HTTP_PORT}/openapi.json" >/dev/null
echo "    nginx health check OK (localhost:\${TIKTOK_HTTP_PORT})"
EOF

  verify_external_access "${EC2_HOST}" "$TIKTOK_HTTP_PORT" || true
  print_completion "${EC2_HOST}" "$TIKTOK_HTTP_PORT"
}

if is_local_deploy; then
  deploy_local
else
  deploy_remote
fi
