#!/bin/bash
# Development stop script for Taiger API
# This script stops the manually started application

echo "Stopping Taiger API processes..."
pkill -f "uvicorn.*main:app"

echo "Waiting for processes to terminate..."
sleep 3

echo "Checking for remaining processes..."
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo "Some processes are still running, force killing..."
    pkill -9 -f "uvicorn.*main:app"
    sleep 2
fi

if pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo "❌ Failed to stop all Taiger API processes"
    echo "Remaining processes:"
    pgrep -af "uvicorn.*main:app"
    exit 1
else
    echo "✅ All Taiger API processes stopped successfully!"
fi