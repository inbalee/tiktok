#!/usr/bin/env bash
set -euo pipefail

# Example EC2 user-data for Amazon Linux 2023.
# Use this when launching the instance to auto-install Docker on first boot.

APP_DIR="/opt/tiktok"
APP_REPO="${APP_REPO:-}"

dnf update -y
dnf install -y docker git curl
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

mkdir -p /usr/local/lib/docker/cli-plugins
arch="$(uname -m)"
case "$arch" in
  x86_64) compose_arch="x86_64" ;;
  aarch64|arm64) compose_arch="aarch64" ;;
esac
curl -fsSL \
  "https://github.com/docker/compose/releases/download/v2.24.7/docker-compose-linux-${compose_arch}" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

mkdir -p "$APP_DIR"
chown ec2-user:ec2-user "$APP_DIR"

if [ -n "$APP_REPO" ]; then
  sudo -u ec2-user git clone "$APP_REPO" "$APP_DIR"
  cd "$APP_DIR"
  cp .env.example .env
  sudo -u ec2-user docker compose -f docker-compose.prod.yml up -d --build
fi
