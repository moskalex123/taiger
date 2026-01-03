#!/bin/bash

set -e  # Exit on any error

echo "🛑 Stopping backend (uvicorn) on port 8000..."

# Kill backend by port 8000
kill -9 $(lsof -t -i:8000) 2>/dev/null || true

# Additional kill for uvicorn processes
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "python3 -m uvicorn main:app" 2>/dev/null || true

sleep 2
echo "✅ All backend processes stopped."

cd /opt/taiger

echo "🚀 Starting backend..."
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

echo "🎉 Backend restart complete!"