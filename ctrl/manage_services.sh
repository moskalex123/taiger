#!/bin/bash
# Taiger Service Management Script
# Usage: ./manage_services.sh {start|stop|restart|status|enable|disable} [service]

set -e

SERVICES=("taiger-api" "taiger-frontend")

print_usage() {
    echo "Usage: $0 {start|stop|restart|status|enable|disable} [service]"
    echo ""
    echo "Services: ${SERVICES[*]}"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start all services"
    echo "  $0 stop taiger-api    # Stop specific service"
    echo "  $0 restart            # Restart all services"
    echo "  $0 status             # Show status of all services"
    echo "  $0 logs               # Show logs of all services"
    echo ""
    echo "Manual mode commands:"
    echo "  $0 manual-start       # Start services in manual mode (no systemd)"
    echo "  $0 manual-stop        # Stop manual services"
    echo "  $0 manual-restart     # Restart manual services"
}

start_service() {
    local service=$1
    echo "Starting $service..."
    systemctl start $service
    systemctl enable $service
    echo "✓ $service started and enabled"
}

stop_service() {
    local service=$1
    echo "Stopping $service..."
    systemctl stop $service
    systemctl disable $service
    echo "✓ $service stopped and disabled"
}

restart_service() {
    local service=$1
    echo "Restarting $service..."
    systemctl restart $service
    echo "✓ $service restarted"
}

show_status() {
    local service=$1
    echo "=== $service Status ==="
    systemctl status $service --no-pager || true
    echo ""
}

show_logs() {
    local service=$1
    echo "=== $service Logs (last 50 lines) ==="
    journalctl -u $service -n 50 --no-pager || true
    echo ""
}

manual_start() {
    echo "Starting services in manual mode..."
    
    # Stop systemd services first
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet $service; then
            echo "Stopping $service systemd service..."
            systemctl stop $service
        fi
    done
    
    # Start API manually
    echo "Starting API manually..."
    cd /opt/taiger
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/api_manual.log 2>&1 &
    API_PID=$!
    echo "API started with PID $API_PID"
    
    # Start Frontend manually
    echo "Starting Frontend manually..."
    cd /opt/taiger/frontend
    nohup npm run dev > /tmp/frontend_manual.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend started with PID $FRONTEND_PID"
    
    # Save PIDs for later stopping
    echo "$API_PID" > /tmp/taiger_api_manual.pid
    echo "$FRONTEND_PID" > /tmp/taiger_frontend_manual.pid
    
    echo "✓ Manual services started"
    echo "API logs: tail -f /tmp/api_manual.log"
    echo "Frontend logs: tail -f /tmp/frontend_manual.log"
}

manual_stop() {
    echo "Stopping manual services..."
    
    # Stop API
    if [ -f /tmp/taiger_api_manual.pid ]; then
        API_PID=$(cat /tmp/taiger_api_manual.pid)
        if kill -0 $API_PID 2>/dev/null; then
            echo "Stopping API (PID $API_PID)..."
            kill $API_PID
            rm -f /tmp/taiger_api_manual.pid
            echo "✓ API stopped"
        else
            echo "API process not running"
        fi
    fi
    
    # Stop Frontend
    if [ -f /tmp/taiger_frontend_manual.pid ]; then
        FRONTEND_PID=$(cat /tmp/taiger_frontend_manual.pid)
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            echo "Stopping Frontend (PID $FRONTEND_PID)..."
            kill $FRONTEND_PID
            rm -f /tmp/taiger_frontend_manual.pid
            echo "✓ Frontend stopped"
        else
            echo "Frontend process not running"
        fi
    fi
    
    # Kill any remaining processes on ports
    echo "Cleaning up any remaining processes..."
    kill -9 $(lsof -t -i:8000) 2>/dev/null || true
    kill -9 $(lsof -t -i:3000) 2>/dev/null || true
    
    echo "✓ Manual services stopped"
}

manual_restart() {
    echo "Restarting manual services..."
    manual_stop
    sleep 2
    manual_start
}

# Main script logic
case "$1" in
    start)
        if [ -z "$2" ]; then
            for service in "${SERVICES[@]}"; do
                start_service $service
            done
        else
            start_service $2
        fi
        ;;
    stop)
        if [ -z "$2" ]; then
            for service in "${SERVICES[@]}"; do
                stop_service $service
            done
        else
            stop_service $2
        fi
        ;;
    restart)
        if [ -z "$2" ]; then
            for service in "${SERVICES[@]}"; do
                restart_service $service
            done
        else
            restart_service $2
        fi
        ;;
    status)
        if [ -z "$2" ]; then
            for service in "${SERVICES[@]}"; do
                show_status $service
            done
        else
            show_status $2
        fi
        ;;
    logs)
        if [ -z "$2" ]; then
            for service in "${SERVICES[@]}"; do
                show_logs $service
            done
        else
            show_logs $2
        fi
        ;;
    enable)
        if [ -z "$2" ]; then
            for service in "${SERVICES[@]}"; do
                systemctl enable $service
                echo "✓ $service enabled"
            done
        else
            systemctl enable $2
            echo "✓ $2 enabled"
        fi
        ;;
    disable)
        if [ -z "$2" ]; then
            for service in "${SERVICES[@]}"; do
                systemctl disable $service
                echo "✓ $service disabled"
            done
        else
            systemctl disable $2
            echo "✓ $2 disabled"
        fi
        ;;
    manual-start)
        manual_start
        ;;
    manual-stop)
        manual_stop
        ;;
    manual-restart)
        manual_restart
        ;;
    *)
        print_usage
        exit 1
        ;;
esac

echo "✓ Operation completed successfully"