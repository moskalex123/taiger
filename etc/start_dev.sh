#!/bin/bash
# Development startup script for Taiger API
# This script starts the application manually without systemd

echo "Stopping any existing Taiger API processes..."
pkill -f "uvicorn.*main:app"

echo "Waiting for processes to terminate..."
sleep 3

echo "Starting Taiger API on port 8000..."
cd /opt/taiger
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/taiger-api.log 2>&1 &

echo "Waiting for application to start..."
sleep 5

echo "Checking if application is running..."
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Taiger API started successfully!"
    echo "Logs are available at: /tmp/taiger-api.log"
    echo "To view logs: tail -f /tmp/taiger-api.log"
else
    echo "❌ Failed to start Taiger API"
    echo "Check logs at: /tmp/taiger-api.log"
    exit 1
fi