#!/bin/bash
# Taiger Service Health Check Script

echo "=== Taiger Service Health Check ==="
echo ""

SERVICES=("taiger-api" "taiger-frontend")

for service in "${SERVICES[@]}"; do
    echo "Checking $service..."
    if systemctl is-active --quiet $service; then
        echo "✓ $service is running"
        
        # Check if port is listening
        if [ "$service" == "taiger-api" ]; then
            if nc -z localhost 8000 2>/dev/null; then
                echo "✓ API port 8000 is listening"
            else
                echo "✗ API port 8000 is NOT listening"
            fi
        elif [ "$service" == "taiger-frontend" ]; then
            if nc -z localhost 3000 2>/dev/null; then
                echo "✓ Frontend port 3000 is listening"
            else
                echo "✗ Frontend port 3000 is NOT listening"
            fi
        fi
        
        # Check service status details
        echo "  Status: $(systemctl show $service --property=ActiveState --value)"
        echo "  SubState: $(systemctl show $service --property=SubState --value)"
        echo "  PID: $(systemctl show $service --property=MainPID --value)"
        
    else
        echo "✗ $service is NOT running"
        echo "  Status: $(systemctl show $service --property=ActiveState --value)"
        echo "  SubState: $(systemctl show $service --property=SubState --value)"
    fi
    echo ""
done

# Check manual services
echo "=== Manual Services Check ==="
if [ -f /tmp/taiger_api_manual.pid ]; then
    API_PID=$(cat /tmp/taiger_api_manual.pid)
    if kill -0 $API_PID 2>/dev/null; then
        echo "✓ Manual API is running (PID $API_PID)"
    else
        echo "✗ Manual API is NOT running"
    fi
else
    echo "No manual API PID file found"
fi

if [ -f /tmp/taiger_frontend_manual.pid ]; then
    FRONTEND_PID=$(cat /tmp/taiger_frontend_manual.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "✓ Manual Frontend is running (PID $FRONTEND_PID)"
    else
        echo "✗ Manual Frontend is NOT running"
    fi
else
    echo "No manual Frontend PID file found"
fi

echo ""
echo "=== Port Status ==="
echo "Port 8000 (API): $(lsof -i :8000 2>/dev/null | grep LISTEN | wc -l) listening process(es)"
echo "Port 3000 (Frontend): $(lsof -i :3000 2>/dev/null | grep LISTEN | wc -l) listening process(es)"

echo ""
echo "=== End of Health Check ==="