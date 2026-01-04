# Systemd Service Implementation Plan

## Overview
Implement automatic startup and restart of the Taiger project as systemd services, replacing the current manual startup process.

## Current State Analysis

### Existing Configuration
- **Backend Service File**: [`taiger-api.service`](taiger-api.service) - Already exists with basic configuration
- **Manual Startup**: Currently using direct commands in terminal
- **Prohibition**: Line 19 in [`README_for_AI.md`](README_for_AI.md) explicitly forbids systemd usage

### Current taiger-api.service Configuration
```ini
[Unit]
Description=Taiger API Service
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/taiger
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## Implementation Plan

### Phase 1: Update Service Configuration
**File**: [`taiger-api.service`](taiger-api.service)

Enhance the existing service file with:
- Better logging configuration
- Environment file loading
- Proper restart policies
- Health check integration

```ini
[Unit]
Description=Taiger API Service
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/taiger
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=-/opt/taiger/.env
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=taiger-api

[Install]
WantedBy=multi-user.target
```

### Phase 2: Create Frontend Service
**File**: `taiger-frontend.service`

Create a new service for the frontend:

```ini
[Unit]
Description=Taiger Frontend Service
After=network.target taiger-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/taiger/frontend
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/npx serve -s -l 3000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=taiger-frontend

[Install]
WantedBy=multi-user.target
```

### Phase 3: Create Helper Scripts

#### Script 1: Service Management Script
**File**: `manage_services.sh`

```bash
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
    *)
        print_usage
        exit 1
        ;;
esac

echo "✓ Operation completed successfully"
```

#### Script 2: Service Health Check
**File**: `check_services.sh`

```bash
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
    else
        echo "✗ $service is NOT running"
    fi
    echo ""
done

echo "=== End of Health Check ==="
```

### Phase 4: Update README_for_AI.md

Remove the prohibition on line 19 and add comprehensive systemd instructions:

**Remove line 19**:
```
- убедись, что проект не запускается как системный процесс, убери его нахуй из systemd services и не запускай его через systemctl. Ты заебал уже прописывать его в системные процессы, а потом по пол-часа его останавливать и нихуя не понимать, чо происходит!!!. хоть мы и на продакшене, но проект в массы ещё не запущен,   поэтому на время доразработки отключи это. нам нужен сейчас полный твой контроль проекта
```

**Add new section** after line 34:

```markdown
## Systemd Service Management

Проект теперь работает как systemd сервисы для автоматического запуска и перезапуска.

### Основные команды управления

#### Запуск всех сервисов
```bash
./manage_services.sh start
```

#### Остановка всех сервисов
```bash
./manage_services.sh stop
```

#### Перезапуск всех сервисов
```bash
./manage_services.sh restart
```

#### Проверка статуса сервисов
```bash
./manage_services.sh status
```

#### Просмотр логов сервисов
```bash
./manage_services.sh logs
```

#### Управление отдельным сервисом
```bash
# Запуск только API
./manage_services.sh start taiger-api

# Остановка только фронтенда
./manage_services.sh stop taiger-frontend

# Перезапуск API
./manage_services.sh restart taiger-api

# Статус конкретного сервиса
./manage_services.sh status taiger-api
```

### Ручное управление через systemctl

#### Прямые команды systemctl
```bash
# Запуск сервиса
sudo systemctl start taiger-api

# Остановка сервиса
sudo systemctl stop taiger-api

# Перезапуск сервиса
sudo systemctl restart taiger-api

# Проверка статуса
sudo systemctl status taiger-api

# Включение автозапуска при загрузке
sudo systemctl enable taiger-api

# Отключение автозапуска
sudo systemctl disable taiger-api

# Просмотр логов в реальном времени
sudo journalctl -u taiger-api -f

# Просмотр последних 100 строк логов
sudo journalctl -u taiger-api -n 100
```

### Проверка здоровья сервисов

```bash
# Запуск проверки здоровья
./check_services.sh
```

### Ручной режим (для разработки)

Если нужно запустить проект вручную без systemd:

```bash
# Остановить systemd сервисы
./manage_services.sh stop

# Запустить бэкенд вручную
cd /opt/taiger && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# Запустить фронтенд вручную
cd /opt/taiger/frontend && npm run dev
```

### Преимущества systemd

1. **Автоматический запуск** - сервисы запускаются автоматически при загрузке сервера
2. **Автоматический перезапуск** - при сбоях сервисы перезапускаются автоматически
3. **Централизованное логирование** - все логи собираются в journalctl
4. **Управление зависимостями** - правильный порядок запуска сервисов
5. **Мониторинг ресурсов** - отслеживание использования ресурсов сервисами

### Troubleshooting

#### Сервис не запускается
```bash
# Проверить статус
sudo systemctl status taiger-api

# Посмотреть логи
sudo journalctl -u taiger-api -n 50

# Проверить конфигурацию
sudo systemd-analyze verify taiger-api.service
```

#### Порт занят
```bash
# Проверить, что занимает порт
sudo lsof -i :8000
sudo lsof -i :3000

# Остановить сервисы
./manage_services.sh stop

# Убить процессы на портах
cd /opt/taiger && kill -9 $(lsof -t -i:8000) 2>/dev/null || echo "No processes on port 8000"
cd /opt/taiger/frontend && kill -9 $(lsof -t -i:3000) 2>/dev/null || echo "No processes on port 3000"

# Запустить сервисы заново
./manage_services.sh start
```

#### Сервис постоянно перезапускается
```bash
# Проверить логи на ошибки
sudo journalctl -u taiger-api -n 100

# Отключить автоматический перезапуск для отладки
sudo systemctl edit taiger-api
# Добавить: Restart=no

# Перезагрузить конфигурацию
sudo systemctl daemon-reload
sudo systemctl restart taiger-api
```
```

### Phase 5: Installation and Setup

#### Step 1: Install Service Files
```bash
# Копировать файлы сервисов в systemd
sudo cp taiger-api.service /etc/systemd/system/
sudo cp taiger-frontend.service /etc/systemd/system/

# Перезагрузить systemd
sudo systemctl daemon-reload
```

#### Step 2: Make Helper Scripts Executable
```bash
chmod +x manage_services.sh
chmod +x check_services.sh
```

#### Step 3: Enable Services
```bash
# Включить автозапуск
sudo systemctl enable taiger-api
sudo systemctl enable taiger-frontend

# Запустить сервисы
./manage_services.sh start
```

#### Step 4: Verify Installation
```bash
# Проверить статус
./manage_services.sh status

# Проверить здоровье
./check_services.sh
```

## Implementation Steps

1. ✅ **Analyze current configuration** - Reviewed existing [`taiger-api.service`](taiger-api.service)
2. ⏳ **Update service files** - Enhance backend and create frontend service
3. ⏳ **Create helper scripts** - Build [`manage_services.sh`](manage_services.sh) and [`check_services.sh`](check_services.sh)
4. ⏳ **Update documentation** - Modify [`README_for_AI.md`](README_for_AI.md)
5. ⏳ **Install and test** - Deploy services and verify functionality
6. ⏳ **Create deployment guide** - Document the complete setup process

## Benefits of This Implementation

1. **Reliability**: Automatic restart on failures
2. **Monitoring**: Centralized logging via journalctl
3. **Convenience**: Simple commands for service management
4. **Production-ready**: Standard Linux service management
5. **Flexibility**: Easy to switch between manual and automatic modes

## Risk Mitigation

- Keep manual startup commands in documentation for fallback
- Provide clear rollback instructions
- Include comprehensive troubleshooting section
- Test thoroughly before enabling auto-start on boot
