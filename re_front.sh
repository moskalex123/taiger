#!/bin/bash

set -e  # Exit on any error

echo "🛑 Stopping frontend dev servers and npm processes..."

# Kill dev server by port (Vite default: 5173)
kill -9 $(lsof -t -i:5173) 2>/dev/null || true

# Kill any lingering npm/vite/node processes related to frontend
pkill -f "npm run dev" 2>/dev/null || true
pkill -f vite 2>/dev/null || true
pkill -f "/opt/taiger/frontend" 2>/dev/null || true

sleep 2
echo "✅ All frontend processes stopped."

cd /opt/taiger/frontend

echo "🔨 Building production frontend..."
npm run build

if [ $? -ne 0 ]; then
  echo "❌ Build failed!"
  exit 1
fi

echo "✅ Build successful."

echo "🔄 Reloading Nginx..."
nginx -s reload 2>/dev/null || systemctl reload nginx 2>/dev/null || true

echo "🎉 Frontend restart complete! New build deployed via Nginx."
