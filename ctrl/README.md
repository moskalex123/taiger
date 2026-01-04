# Taiger Service Control Scripts

Эта директория содержит скрипты для управления сервисами Taiger через systemd.

## Основные команды

### Запуск всех сервисов
```bash
./manage_services.sh start
```

### Остановка всех сервисов
```bash
./manage_services.sh stop
```

### Перезапуск всех сервисов
```bash
./manage_services.sh restart
```

### Проверка статуса сервисов
```bash
./manage_services.sh status
```

### Просмотр логов сервисов
```bash
./manage_services.sh logs
```

### Управление отдельным сервисом
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

## Ручной режим (для разработки)

### Запуск вручную
```bash
./manage_services.sh manual-start
```

### Остановка ручного режима
```bash
./manage_services.sh manual-stop
```

### Перезапуск ручного режима
```bash
./manage_services.sh manual-restart
```

## Проверка здоровья сервисов

```bash
./check_services.sh
```

## Дополнительные команды

### Включение автозапуска при загрузке
```bash
./manage_services.sh enable
```

### Отключение автозапуска
```bash
./manage_services.sh disable
```

## Прямые команды systemctl

### Управление сервисами
```bash
# Запуск сервиса
sudo systemctl start taiger-api

# Остановка сервиса
sudo systemctl stop taiger-api

# Перезапуск сервиса
sudo systemctl restart taiger-api

# Проверка статуса
sudo systemctl status taiger-api
```

### Просмотр логов
```bash
# Просмотр логов в реальном времени
sudo journalctl -u taiger-api -f

# Просмотр последних 100 строк логов
sudo journalctl -u taiger-api -n 100

# Просмотр логов за сегодня
sudo journalctl -u taiger-api --since today
```

### Автозапуск при загрузке
```bash
# Включение автозапуска
sudo systemctl enable taiger-api

# Отключение автозапуска
sudo systemctl disable taiger-api
```

## Сервисы

### taiger-api
- **Порт**: 8000
- **Команда**: `python3 -m uvicorn main:app --host 0.0.0.0 --port 8000`
- **Рабочая директория**: `/opt/taiger`

### taiger-frontend
- **Порт**: 3000
- **Команда**: `npx serve -s -l 3000`
- **Рабочая директория**: `/opt/taiger/frontend`

## Troubleshooting

### Сервис не запускается
```bash
# Проверить статус
sudo systemctl status taiger-api

# Посмотреть логи
sudo journalctl -u taiger-api -n 50

# Проверить конфигурацию
sudo systemd-analyze verify taiger-api.service
```

### Порт занят
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

### Сервис постоянно перезапускается
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

### Ручной режим не работает
```bash
# Проверить PID файлы
ls -la /tmp/taiger_*_manual.pid

# Проверить процессы
ps aux | grep uvicorn
ps aux | grep npm

# Проверить логи
tail -f /tmp/api_manual.log
tail -f /tmp/frontend_manual.log
```

## Преимущества systemd

1. **Автоматический запуск** - сервисы запускаются автоматически при загрузке сервера
2. **Автоматический перезапуск** - при сбоях сервисы перезапускаются автоматически
3. **Централизованное логирование** - все логи собираются в journalctl
4. **Управление зависимостями** - правильный порядок запуска сервисов
5. **Мониторинг ресурсов** - отслеживание использования ресурсов сервисами

## Файлы сервисов

- **Backend**: `/etc/systemd/system/taiger-api.service`
- **Frontend**: `/etc/systemd/system/taiger-frontend.service`

## Установка сервисов

```bash
# Копировать файлы сервисов в systemd
sudo cp taiger-api.service /etc/systemd/system/
sudo cp taiger-frontend.service /etc/systemd/system/

# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable taiger-api
sudo systemctl enable taiger-frontend

# Запустить сервисы
./manage_services.sh start