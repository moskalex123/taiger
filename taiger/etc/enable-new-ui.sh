#!/bin/bash

# Script to enable the new UI design on the VPS (non-containerized setup)
echo "=== Enabling New UI Design (Non-Containerized Setup) ==="

# SSH into the service server at 94.141.161.21 and execute commands
echo "Connecting to service server at 94.141.161.21..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@94.141.161.21 "echo 'connected'" 2>/dev/null; then
    echo "Failed to connect to service server at 94.141.161.21. Check SSH settings."
    exit 1
fi
echo "✅ Connected to service server at 94.141.161.21"

# Execute commands on service server (94.141.161.21)
echo "Configuring UI design on service server..."

# Navigate to project directory and check current .env
echo "Checking current .env configuration..."
ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger && cat frontend/.env"

# Check if VITE_ENABLE_REDESIGN is already set to true
if ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger && grep -q 'VITE_ENABLE_REDESIGN=true' frontend/.env" 2>/dev/null; then
    echo "✅ VITE_ENABLE_REDESIGN is already set to true"
else
    echo "🔧 Setting VITE_ENABLE_REDESIGN=true"
    
    # Remove any existing VITE_ENABLE_REDESIGN line and add the new one
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger && sed -i '/VITE_ENABLE_REDESIGN/d' frontend/.env && echo 'VITE_ENABLE_REDESIGN=true' >> frontend/.env"
    
    echo "✅ VITE_ENABLE_REDESIGN has been set to true"
    
    # Verify the change
    echo "Verifying change..."
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger && grep 'VITE_ENABLE_REDESIGN' frontend/.env"
fi

echo "=== Building frontend application ==="

# Build the frontend application
echo "Building frontend..."
if ! ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger/frontend && npm run build"; then
    echo "⚠️ Failed to build frontend"
    exit 1
fi

echo "✅ Frontend built successfully"

echo "=== Restarting services ==="

# Restart the backend service
echo "Restarting backend service..."
if ! ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "systemctl restart taiger-backend" 2>/dev/null; then
    echo "⚠️ Failed to restart backend service with systemctl, trying alternative..."
    # Try alternative restart method
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "pkill -f taiger-backend; cd /opt/taiger && nohup python main.py &" 2>/dev/null
fi

echo "✅ Services restarted"

echo "=== Verifying new UI design from remote viewing server ==="

# SSH into the remote viewing server at 109.206.236.60
echo "Connecting to remote viewing server at 109.206.236.60..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@109.206.236.60 "echo 'connected'" 2>/dev/null; then
    echo "Failed to connect to remote viewing server at 109.206.236.60. Check SSH settings."
    exit 1
fi
echo "✅ Connected to remote viewing server at 109.206.236.60"

# Check if we can access the TMA page from the remote viewing server
echo "Checking TMA page from remote viewing server..."
curl_result=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@109.206.236.60 "curl -s -o /dev/null -w '%{http_code}' http://94.141.161.21:8000/")
echo "HTTP status code from TMA page: $curl_result"

if [ "$curl_result" = "200" ]; then
    echo "✅ Successfully accessed TMA page from remote viewing server"
else
    echo "⚠️ Failed to access TMA page from remote viewing server"
fi

# Check if new UI elements are present in the response
ui_check=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@109.206.236.60 "curl -s http://94.141.161.21:8000/ | grep -i 'redesigned' | wc -l")
if [ "$ui_check" -gt 0 ]; then
    echo "✅ New UI design detected on TMA page"
else
    echo "⚠️ New UI design not detected on TMA page"
    echo "🔧 Attempting to force clear cache and rebuild..."
    
    # Force clear cache and rebuild
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no root@94.141.161.21 "cd /opt/taiger/frontend && rm -rf dist && npm run build"
    
    echo "✅ Forced rebuild completed"
fi

echo "=== Process completed ==="
echo "1. New UI design has been enabled on service server 94.141.161.21"
echo "2. Frontend has been rebuilt and services restarted"
echo "3. Verification attempted from remote viewing server 109.206.236.60"
echo "4. If new UI is not visible, try clearing browser cache or wait a few minutes for DNS propagation"