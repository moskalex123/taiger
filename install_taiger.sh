#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
  echo "[install] $1"
}

export DEBIAN_FRONTEND=noninteractive
log "Updating apt cache"
apt-get update -y
log "Installing base packages"
apt-get install -y python3 python3-venv python3-pip python3-dev build-essential libpq-dev postgresql postgresql-contrib redis-server nginx nodejs npm certbot python3-certbot-nginx git curl

log "Setting up Python environment"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [[ -f "$APP_DIR/package.json" ]]; then
  log "Installing root npm dependencies"
  npm install --prefix "$APP_DIR"
fi

if [[ -d "$APP_DIR/frontend" && -f "$APP_DIR/frontend/package.json" ]]; then
  log "Installing frontend npm dependencies"
  npm install --prefix "$APP_DIR/frontend"
  log "Building frontend"
  npm run build --prefix "$APP_DIR/frontend"
fi

if [[ ! -f "$APP_DIR/.env" && -f "$APP_DIR/.env.example" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  log "Created .env from example; update secrets manually"
fi

SERVICE_FILE="/etc/systemd/system/taiger-api.service"
log "Configuring systemd service"
cat <<'EOF' >"$SERVICE_FILE"
[Unit]
Description=Taiger API Service
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
WorkingDirectory=/opt/taiger
Environment="PATH=/opt/taiger/.venv/bin"
ExecStart=/opt/taiger/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable taiger-api.service
systemctl restart taiger-api.service || true

NGINX_CONF_SRC=""
if [[ -f "$APP_DIR/nginx_fixed.conf" ]]; then
  NGINX_CONF_SRC="$APP_DIR/nginx_fixed.conf"
elif [[ -f "$APP_DIR/nginx_current.conf" ]]; then
  NGINX_CONF_SRC="$APP_DIR/nginx_current.conf"
elif [[ -f "$APP_DIR/nginx.conf" ]]; then
  NGINX_CONF_SRC="$APP_DIR/nginx.conf"
fi

if [[ -n "$NGINX_CONF_SRC" ]]; then
  log "Configuring nginx"
  install -m 644 "$NGINX_CONF_SRC" /etc/nginx/sites-available/taiger.conf
  ln -sf /etc/nginx/sites-available/taiger.conf /etc/nginx/sites-enabled/taiger.conf
  if [[ -f /etc/nginx/sites-enabled/default ]]; then
    rm /etc/nginx/sites-enabled/default
  fi
  nginx -t
  systemctl restart nginx
else
  log "nginx config not found in project"
fi

log "Installation script completed"
