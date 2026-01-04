- у проекта два режима работы: 1 - основной -  в TMA - полноценная работа с телеграм-сессиями пользователей, при котором пользователи могут настраивать правила ИИ-обработки постов, каналы-источники, каналы-приёмники и интервалы планирования , в этом режиме бот служит только для логирования основного режима работы проекта;  2 - промо - в боте - бесплатная обработка всех входящих постов от пользователя, обработка их через модели ИИ, прописанные в ./env по жёстко заданному правилу и выдача обработанных постов отдельно для каждой модели пользователю в бота.

- Документация проекта структурирована в папке docs/:
  - docs/README.md - главная страница документации
  - docs/setup/ - установка и настройка
  - docs/guides/ - руководства по использованию
  - docs/api/ - API документация
  - docs/development/ - документация для разработчиков
  Основные файлы документации перемещены в docs/, старые файлы с фиксами удалены.

- для отладки в проекте создан отдельный микро-клиент в micro-client-for-self-test- он запускает телеграм-сессию админа и иммет доступ ко всем каналам. используй его для отладки. можешь дорабатывать его под текущие задачи

- Всегда помни, что ты подключен к этому проекту по ssh-remote, твой терминал работает в продакшене, и не нужно никаких деплоев на сторонние серверы.

- после всех изменений в коде, прежде, чем отчитываться о своей успешной работе, перезапусти проект в своём терминале и отследи возможные ошибки. 

- не используй готовые скрипты запуска/перезапуска проекта и его подсистем. используй прямые команды в своём терминале. это нужно для полного контроля над ошибками, которые могут произойти при запуске. перед каждым запуском убедись, что проект полностью остановлен и отсутствуют другие запущенные копии проекта, а также остановлены все воркеры/агенты. не меняй стандартные порты работы подсистем - это сигнал того, что проект не полностью остановлен

- проект теперь работает как systemd сервисы для автоматического запуска и перезапуска. подробнее см. в разделе "Systemd Service Management" ниже

-используй команду python3 вместо python

-тестовый пользователь в проекте - 2.
при любых проблемах с воркером проверяй "/opt/taiger/logs/worker_2_stdout.log" и /opt/taiger/logs/worker_2_stderr.log

-для остановки бэкенда используй 
cd /opt/taiger && kill -9 $(lsof -t -i:8000) 2>/dev/null || echo "No processes found on port 8000"

-для запуска бэкенда используй
cd /opt/taiger && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

-для запуска фронтенда используй
cd /opt/taiger/frontend && npm run dev

## Systemd Service Management

Проект теперь работает как systemd сервисы для автоматического запуска и перезапуска.

### Основные команды управления

#### Запуск всех сервисов
```bash
cd /opt/taiger/ctrl && ./manage_services.sh start
```

#### Остановка всех сервисов
```bash
cd /opt/taiger/ctrl && ./manage_services.sh stop
```

#### Перезапуск всех сервисов
```bash
cd /opt/taiger/ctrl && ./manage_services.sh restart
```

#### Проверка статуса сервисов
```bash
cd /opt/taiger/ctrl && ./manage_services.sh status
```

#### Просмотр логов сервисов
```bash
cd /opt/taiger/ctrl && ./manage_services.sh logs
```

#### Управление отдельным сервисом
```bash
# Запуск только API
cd /opt/taiger/ctrl && ./manage_services.sh start taiger-api

# Остановка только фронтенда
cd /opt/taiger/ctrl && ./manage_services.sh stop taiger-frontend

# Перезапуск API
cd /opt/taiger/ctrl && ./manage_services.sh restart taiger-api

# Статус конкретного сервиса
cd /opt/taiger/ctrl && ./manage_services.sh status taiger-api
```

### Ручной режим (для разработки)

Если нужно запустить проект вручную без systemd:

```bash
# Остановить systemd сервисы
cd /opt/taiger/ctrl && ./manage_services.sh stop

# Запустить бэкенд вручную
cd /opt/taiger && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# Запустить фронтенд вручную
cd /opt/taiger/frontend && npm run dev
```

### Проверка здоровья сервисов

```bash
cd /opt/taiger/ctrl && ./check_services.sh
```

### Прямые команды systemctl

#### Управление сервисами
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
```

#### Просмотр логов
```bash
# Просмотр логов в реальном времени
sudo journalctl -u taiger-api -f

# Просмотр последних 100 строк логов
sudo journalctl -u taiger-api -n 100

# Просмотр логов за сегодня
sudo journalctl -u taiger-api --since today
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
cd /opt/taiger/ctrl && ./manage_services.sh stop

# Убить процессы на портах
cd /opt/taiger && kill -9 $(lsof -t -i:8000) 2>/dev/null || echo "No processes on port 8000"
cd /opt/taiger/frontend && kill -9 $(lsof -t -i:3000) 2>/dev/null || echo "No processes on port 3000"

# Запустить сервисы заново
cd /opt/taiger/ctrl && ./manage_services.sh start
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

#### Ручной режим не работает
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

### Файлы сервисов

- **Backend**: `/etc/systemd/system/taiger-api.service`
- **Frontend**: `/etc/systemd/system/taiger-frontend.service`

### Установка сервисов

```bash
# Копировать файлы сервисов в systemd
sudo cp /opt/taiger/taiger-api.service /etc/systemd/system/
sudo cp /opt/taiger/taiger-frontend.service /etc/systemd/system/

# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable taiger-api
sudo systemctl enable taiger-frontend

# Запустить сервисы
cd /opt/taiger/ctrl && ./manage_services.sh start
```

-если необходимо проверить работу воркера в консоли - используй команду python3 tg_worker.py --user_id 2 --port 8102 --skip-listening

-красный флаг - если общеприрнятый порт занят, то это ненормально. освобождай его. на этом впс крутится только текущий проект. любые конфликты портов - не остановленная старая версия проекта

- прежде, чем докладывать об успешном решении проблем - для тестирования подключений к проекту извне ипрользуй специальный вспомогательный vps. войди на него через ssh:
Host aux-vps
    HostName 92.246.141.38
    User root
    Port 22
    IdentityFile ~/.ssh/id_rsa
    ConnectTimeout 60
    ServerAliveInterval 60
    ServerAliveCountMax 5
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    PreferredAuthentications publickey
и проверь все исправления путём обращения к текущему впс со вспомогательного vps. 
не устанавливай на него tailscale, он должен оставться чистым для полной имитации обычного пользователя.

если пользователь говорит, что изменения в коде не применились:

- При смене метки версии:
  - Установить VITE_APP_VERSION в frontend/.env и APP_VERSION в серверном .env .
  - Пересобрать фронт: npm run build .
  - Перезапустить бэкенд.
- Чтобы изменения всегда доходили:
  - Убедиться, что Nginx не кэширует index.html ( no-store ), а ассеты — с хэшами.
  - Кнопка бота ведёт на TELEGRAM_WEBAPP_URL с параметром ?v=<APP_VERSION> .
- Отладка несоответствия UI:
  - Проверить, какой домен открывается в TMA.
  - Проверить dist/index.html и ссылки на assets/index-*.js .
  - Очистить кэш Telegram Desktop/Android, если нужно.
- Никаких ручных правок строк вида vX — только через окружение и сборку.


- Используй только эти настройки проекта:
# Production Environment Variables
DB_USER=taiger
DB_PASSWORD=Pp969291
DB_HOST=94.141.161.21
DB_PORT=5433
DB_NAME=taigerdb

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30

# Telegram API Credentials
TELEGRAM_API_ID=21118124
TELEGRAM_API_HASH=491b6a7118ccbf3738bebc959ea14e4d

# Hyperbolic API Key
HYPERBOLIC_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtb3NrYWxleEBnbWFpbC5jb20iLCJpYXQiOjE3MzkwOTk1MTd9.a9EJbK9foZzz46ZAP0coX5m6uDwt-vw_S63Mn-2eCN4"

# OpenRouter API Key
OPENROUTER_API_KEY=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


# Yandex Object Storage Configuration
# Secrets are configured in .env file
YC_REGION=ru-central1
YC_ENDPOINT_URL=https://storage.yandexcloud.net
BUCKET_NAME=taiger-sessions
AVATAR_BUCKET_NAME=taiger-avatars

# Worker Configuration
MAX_CONCURRENT_WORKERS=1

# VIP Timeout Settings (in minutes)
VIP_0_TIMEOUT=5
VIP_1_TIMEOUT=10
VIP_2_TIMEOUT=20
VIP_3_TIMEOUT=30

# Payment Contact
PAYMENT_CONTACT=@magellanvs

# API Configuration
API_HOST=localhost
API_PORT=8000

# User Configuration
START_BALANCE=3

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8487827759:AAEr4RxKwoPoFBkT-0RaUVZEHGlxOStWK4o
TELEGRAM_WEBHOOK_URL=https://taiger.pro/api/telegram/webhook
TELEGRAM_BOT_SECRET=my_webhook_secret_Parol969291
TELEGRAM_WEBAPP_URL=https://taiger.pro
DEFAULT_STARTING_BALANCE=1.0

# Hybrid Post Processing
BATCH_PROCESSING_ENABLED=true
BATCH_PROCESSING_INTERVAL=30
FLOOD_WAIT_MULTIPLIER=1.5
MAX_BATCH_SIZE=100
RULE_SWITCH_DELAY=5

# Telegram Chat ID for testing
TELEGRAM_CHAT_ID=499963076

# WebSocket and Logging Configuration
ENABLE_WEBSOCKET_LOGS=true
WEBSOCKET_DEBUG=true
LOG_WEBSOCKET_ERRORS=true
WORKER_API_TIMEOUT=5