#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script for Amazon Linux 2023 / Ubuntu EC2 instances.
# Installs Docker, Docker Compose plugin, and prepares the app directory.

APP_DIR="${APP_DIR:-/opt/tiktok}"
APP_USER="${APP_USER:-ec2-user}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo bash deploy/ec2-setup.sh"
  exit 1
fi

install_compose_plugin() {
  if docker compose version >/dev/null 2>&1; then
    return
  fi

  mkdir -p /usr/local/lib/docker/cli-plugins
  arch="$(uname -m)"
  case "$arch" in
    x86_64) compose_arch="x86_64" ;;
    aarch64|arm64) compose_arch="aarch64" ;;
    *) echo "Unsupported architecture: $arch"; exit 1 ;;
  esac

  curl -fsSL \
    "https://github.com/docker/compose/releases/download/v2.24.7/docker-compose-linux-${compose_arch}" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
}

if command -v dnf >/dev/null 2>&1; then
  dnf update -y
  dnf install -y docker git curl
  systemctl enable docker
  systemctl start docker
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y docker.io docker-compose-plugin git curl
  systemctl enable docker
  systemctl start docker
else
  echo "Unsupported OS. Install Docker manually."
  exit 1
fi

install_compose_plugin

if id "$APP_USER" >/dev/null 2>&1; then
  usermod -aG docker "$APP_USER"
fi

mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

cat <<EOF

EC2 setup complete.

Next steps:
1. Copy the project to $APP_DIR
2. cd $APP_DIR
3. cp .env.example .env
4. docker compose -f docker-compose.prod.yml up -d --build

If you are not root, log out and back in so Docker group membership applies.

EOF
