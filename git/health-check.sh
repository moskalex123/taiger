#!/bin/bash
set -e

echo "🏥 System Health Check"
echo "====================="
echo ""

# Проверяем дисковое пространство
echo "💾 Disk Usage:"
df -h / | tail -1
echo ""

# Проверяем использование памяти
echo "🧠 Memory Usage:"
free -h | grep Mem
echo ""

# Проверяем загрузку CPU
echo "⚡ CPU Load:"
uptime
echo ""

# Проверяем статус сервисов
echo "🔄 Service Status:"
echo "------------------"
SERVICES=("taiger-api" "taiger-worker" "nginx" "redis-server")

for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        echo "✅ $service: Running"
    else
        echo "❌ $service: Not running"
    fi
done

echo ""

# Проверяем логи на ошибки
echo "📋 Recent Errors (last 10):"
echo "----------------------------"
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        echo ""
        echo "🔍 $service errors:"
        journalctl -u $service --no-pager -n 10 | grep -i error || echo "   No errors found"
    fi
done

echo ""
echo "✅ Health check completed!"