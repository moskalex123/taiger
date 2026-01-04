# План настройки среды для доразработки (Development Environment)

## Обзор решения

Создание изолированной среды для разработки на том же VPS с использованием поддомена `dev.taiger.pro`. Это позволит безопасно разрабатывать и тестировать изменения без риска повредить продакшен.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS (taiger.pro)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ПРОДАКШЕН (Production)                                     │
│  ├── Backend: Python на порту 8000                          │
│  ├── Frontend: /opt/taiger/frontend/dist                    │
│  ├── Database: PostgreSQL (taiger_db)                       │
│  ├── Redis: redis (db 0)                                    │
│  └── Service: taiger-api.service                            │
│                                                              │
│  РАЗРАБОТКА (Development)                                   │
│  ├── Backend: Python на порту 8001                          │
│  ├── Frontend: /opt/taiger/frontend-dev/dist               │
│  ├── Database: PostgreSQL (taiger_db_dev)                  │
│  ├── Redis: redis (db 1)                                    │
│  └── Service: taiger-api-dev.service                        │
│                                                              │
│  NGINX                                                       │
│  ├── taiger.pro → Production (443)                          │
│  └── dev.taiger.pro → Development (443)                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Шаг 1: Создание dev-базы данных PostgreSQL

### 1.1 Создание базы данных для разработки

```bash
# Подключаемся к PostgreSQL
sudo -u postgres psql

# Создаём базу данных для разработки
CREATE DATABASE taiger_db_dev;

# Создаём отдельного пользователя для dev (опционально)
CREATE USER taiger_dev WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE taiger_db_dev TO taiger_dev;

# Выходим
\q
```

### 1.2 Проверка создания базы данных

```bash
# Проверяем список баз данных
sudo -u postgres psql -l

# Должны видеть:
# taiger_db      | taiger | UTF8     | en_US.UTF-8 | en_US.UTF-8 |
# taiger_db_dev  | taiger_dev | UTF8 | en_US.UTF-8 | en_US.UTF-8 |
```

---

## Шаг 2: Создание dev-окружения

### 2.1 Создание директории для dev-фронтенда

```bash
# Клонируем репозиторий в dev-директорию
cd /opt
sudo mkdir -p taiger-dev
sudo chown $USER:$USER taiger-dev
cd taiger-dev

# Копируем текущий проект (или клонируем из git)
cp -r /opt/taiger/* .

# Создаём директорию для dev-фронтенда
mkdir -p frontend-dev
```

### 2.2 Создание конфигурационных файлов для dev

```bash
# Создаём .env.dev для backend
cat > .env.dev << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://taiger_dev:your_secure_password_here@localhost/taiger_db_dev

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# API
API_PORT=8001
API_HOST=0.0.0.0

# Telegram
TELEGRAM_BOT_TOKEN=your_dev_bot_token_here
TELEGRAM_API_ID=your_dev_api_id_here
TELEGRAM_API_HASH=your_dev_api_hash_here

# Frontend
FRONTEND_URL=https://dev.taiger.pro

# S3 (можно использовать те же credentials или отдельные)
S3_ENDPOINT=https://storage.yandexcloud.net
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

# AI APIs (можно использовать те же или тестовые)
OPENROUTER_API_KEY=your_openrouter_key
HYPERBOLIC_API_KEY=your_hyperbolic_key

# JWT
JWT_SECRET=your_dev_jwt_secret_here

# Environment
ENVIRONMENT=development
DEBUG=True
EOF

# Создаём .env.dev для frontend
cat > frontend-dev/.env << 'EOF'
VITE_API_BASE_URL=https://dev.taiger.pro/api
VITE_WS_BASE_URL=wss://dev.taiger.pro/api/ws
VITE_TELEGRAM_WEBAPP_URL=https://dev.taiger.pro
EOF
```

### 2.3 Создание systemd сервиса для dev

```bash
# Создаём файл сервиса
sudo cat > /etc/systemd/system/taiger-api-dev.service << 'EOF'
[Unit]
Description=Taiger API Development Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/taiger-dev
Environment="PATH=/opt/taiger-dev/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/taiger-dev/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/opt/taiger-dev/logs/backend-dev.log
StandardError=append:/opt/taiger-dev/logs/backend-dev-error.log

[Install]
WantedBy=multi-user.target
EOF

# Замените your_username на ваше реальное имя пользователя
# Проверьте имя пользователя командой: whoami

# Создаём директорию для логов
mkdir -p /opt/taiger-dev/logs

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск (но не запускаем пока)
sudo systemctl enable taiger-api-dev.service
```

---

## Шаг 3: Настройка Nginx для dev.taiger.pro

### 3.1 Создание SSL сертификата для dev поддомена

```bash
# Получаем SSL сертификат для dev.taiger.pro
sudo certbot certonly --nginx -d dev.taiger.pro

# Следуйте инструкциям certbot
# Сертификат будет сохранён в /etc/letsencrypt/live/dev.taiger.pro/
```

### 3.2 Создание конфигурации nginx для dev

```bash
# Создаём конфигурацию для dev
sudo cat > /etc/nginx/sites-available/dev.taiger.pro << 'EOF'
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name dev.taiger.pro;
    
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration for dev
server {
    listen 443 ssl http2;
    server_name dev.taiger.pro;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/dev.taiger.pro/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dev.taiger.pro/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers for dev (можно ослабить)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend (dev build)
    location / {
        root /opt/taiger-dev/frontend-dev/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Static assets (dev)
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        root /opt/taiger-dev/frontend-dev/dist;
        expires 1h;
        add_header Cache-Control "public";
    }

    # API endpoints (dev backend on port 8001)
    location /api/ {
        proxy_pass http://localhost:8001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Auth endpoints (dev)
    location /auth/ {
        proxy_pass http://localhost:8001/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    location /auth {
        proxy_pass http://localhost:8001/auth;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # WebSocket (dev)
    location /api/ws/ {
        proxy_pass http://localhost:8001/api/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_set_header Sec-WebSocket-Protocol $http_sec_websocket_protocol;
    }

    # API docs (dev)
    location /api/docs {
        proxy_pass http://localhost:8001/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Avatars (dev)
    location /avatars/ {
        alias /opt/taiger-dev/frontend-dev/dist/avatars/;
        expires 1h;
        add_header Cache-Control "public";
    }
}
EOF

# Создаём символическую ссылку
sudo ln -s /etc/nginx/sites-available/dev.taiger.pro /etc/nginx/sites-enabled/

# Проверяем конфигурацию nginx
sudo nginx -t

# Если всё ок, перезапускаем nginx
sudo systemctl restart nginx
```

---

## Шаг 4: Настройка окружения Python для dev

### 4.1 Создание виртуального окружения

```bash
cd /opt/taiger-dev

# Создаём виртуальное окружение
python3 -m venv .venv

# Активируем и устанавливаем зависимости
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.2 Настройка CORS в main.py для dev

В файле [`main.py`](/opt/taiger-dev/main.py) нужно добавить dev.taiger.pro в CORS origins:

```python
# Настройка CORS (пример кода)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "https://tactically-healing-parrotfish.cloudpub.ru",
        "http://localhost:5174",
        "http://taiger.pro",
        "https://taiger.pro",
        "http://dev.taiger.pro",      # ← Добавить это
        "https://dev.taiger.pro"       # ← И это
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.3 Применение миграций к dev базе данных

```bash
cd /opt/taiger-dev
source .venv/bin/activate

# Устанавливаем переменную окружения для dev
export DATABASE_URL="postgresql+asyncpg://taiger_dev:your_secure_password_here@localhost/taiger_db_dev"

# Применяем миграции
alembic upgrade head

# Или создаём таблицы напрямую (если alembic не настроен)
python -c "from main import create_tables; import asyncio; asyncio.run(create_tables())"
```

---

## Шаг 5: Настройка фронтенда для dev

### 5.1 Установка зависимостей и сборка

```bash
cd /opt/taiger-dev/frontend

# Устанавливаем зависимости (если ещё не установлены)
npm install

# Создаём dev build
npm run build

# Копируем собранные файлы в frontend-dev/dist
mkdir -p ../frontend-dev/dist
cp -r dist/* ../frontend-dev/dist/
```

### 5.2 Обновление API URL в frontend

В файле [`frontend/src/services/tma.ts`](/opt/taiger-dev/frontend/src/services/tma.ts) или аналогичном, убедитесь что используется переменная окружения:

```typescript
// Пример кода
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://taiger.pro/api';
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'wss://taiger.pro/api/ws';
```

---

## Шаг 6: Скрипты для деплоя

### 6.1 Скрипт для деплоя backend на dev

```bash
# Создаём скрипт deploy-dev-backend.sh
cat > /opt/taiger-dev/deploy-dev-backend.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting deployment to dev environment..."

# Переходим в директорию проекта
cd /opt/taiger-dev

# Загружаем последние изменения из git (если используется git)
# git pull origin main

# Или копируем изменения из prod (если не используете git)
# rsync -av --exclude='frontend/dist' --exclude='.venv' --exclude='logs' --exclude='sessions' \
#   /opt/taiger/ /opt/taiger-dev/

# Активируем виртуальное окружение
source .venv/bin/activate

# Устанавливаем зависимости (если изменились)
pip install -r requirements.txt

# Применяем миграции
export DATABASE_URL=$(grep DATABASE_URL .env.dev | cut -d '=' -f2-)
alembic upgrade head

# Перезапускаем сервис
sudo systemctl restart taiger-api-dev

echo "✅ Backend deployed to dev successfully!"
echo "🌐 Dev URL: https://dev.taiger.pro"
EOF

chmod +x /opt/taiger-dev/deploy-dev-backend.sh
```

### 6.2 Скрипт для деплоя frontend на dev

```bash
# Создаём скрипт deploy-dev-frontend.sh
cat > /opt/taiger-dev/deploy-dev-frontend.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting frontend deployment to dev environment..."

# Переходим в директорию фронтенда
cd /opt/taiger-dev/frontend

# Устанавливаем зависимости
npm install

# Собираем фронтенд с dev конфигурацией
npm run build

# Копируем собранные файлы
rm -rf ../frontend-dev/dist/*
cp -r dist/* ../frontend-dev/dist/

echo "✅ Frontend deployed to dev successfully!"
echo "🌐 Dev URL: https://dev.taiger.pro"
EOF

chmod +x /opt/taiger-dev/deploy-dev-frontend.sh
```

### 6.3 Скрипт для полного деплоя на dev

```bash
# Создаём скрипт deploy-dev.sh
cat > /opt/taiger-dev/deploy-dev.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Starting full deployment to dev environment..."

# Деплой backend
/opt/taiger-dev/deploy-dev-backend.sh

# Деплой frontend
/opt/taiger-dev/deploy-dev-frontend.sh

echo "✅ Full deployment to dev completed!"
echo "🌐 Dev URL: https://dev.taiger.pro"
echo "📊 Check status: sudo systemctl status taiger-api-dev"
EOF

chmod +x /opt/taiger-dev/deploy-dev.sh
```

### 6.4 Скрипт для деплоя на продакшен (после тестирования на dev)

```bash
# Создаём скрипт deploy-prod.sh
cat > /opt/taiger-dev/deploy-prod.sh << 'EOF'
#!/bin/bash
set -e

echo "⚠️  WARNING: You are about to deploy to PRODUCTION!"
echo "📝 Please ensure you have tested everything on dev.taiger.pro"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo "🚀 Starting deployment to production..."

# Деплой backend на прод
cd /opt/taiger
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=$(grep DATABASE_URL .env | cut -d '=' -f2-)
alembic upgrade head
sudo systemctl restart taiger-api

# Деплой frontend на прод
cd /opt/taiger/frontend
npm install
npm run build

echo "✅ Production deployment completed!"
echo "🌐 Prod URL: https://taiger.pro"
EOF

chmod +x /opt/taiger-dev/deploy-prod.sh
```

---

## Шаг 7: Скрипты для синхронизации данных (опционально)

### 7.1 Скрипт для копирования данных из prod в dev

```bash
# Создаём скрипт sync-prod-to-dev.sh
cat > /opt/taiger-dev/sync-prod-to-dev.sh << 'EOF'
#!/bin/bash
set -e

echo "🔄 Syncing data from production to development..."

# Останавливаем dev сервис
sudo systemctl stop taiger-api-dev

# Создаём дамп prod базы данных
sudo -u postgres pg_dump taiger_db > /tmp/prod_dump.sql

# Удаляем dev базу данных
sudo -u postgres psql -c "DROP DATABASE IF EXISTS taiger_db_dev;"

# Создаём новую dev базу данных
sudo -u postgres psql -c "CREATE DATABASE taiger_db_dev OWNER taiger_dev;"

# Восстанавливаем данные в dev базу
sudo -u postgres psql taiger_db_dev < /tmp/prod_dump.sql

# Удаляем дамп
rm /tmp/prod_dump.sql

# Запускаем dev сервис
sudo systemctl start taiger-api-dev

echo "✅ Data synced from production to development!"
echo "⚠️  Remember: dev database now contains production data"
EOF

chmod +x /opt/taiger-dev/sync-prod-to-dev.sh
```

---

## Шаг 8: Мониторинг и логирование

### 8.1 Создание скрипта для просмотра логов dev

```bash
# Создаём скрипт view-dev-logs.sh
cat > /opt/taiger-dev/view-dev-logs.sh << 'EOF'
#!/bin/bash

echo "📊 Viewing development logs..."
echo "Press Ctrl+C to exit"
echo ""

# Следим за логами backend dev
sudo journalctl -u taiger-api-dev -f
EOF

chmod +x /opt/taiger-dev/view-dev-logs.sh
```

### 8.2 Создание скрипта для проверки статуса

```bash
# Создаём скрипт check-dev-status.sh
cat > /opt/taiger-dev/check-dev-status.sh << 'EOF'
#!/bin/bash

echo "🔍 Checking development environment status..."
echo ""

# Проверка systemd сервиса
echo "📌 Systemd Service:"
sudo systemctl status taiger-api-dev --no-pager | head -n 10
echo ""

# Проверка порта
echo "📌 Port 8001:"
ss -tulnp | grep 8001 || echo "❌ Port 8001 not listening"
echo ""

# Проверка базы данных
echo "📌 Database:"
sudo -u postgres psql -l | grep taiger_db_dev || echo "❌ Database taiger_db_dev not found"
echo ""

# Проверка nginx
echo "📌 Nginx configuration:"
sudo nginx -t 2>&1 | grep -E "(successful|error)"
echo ""

echo "✅ Status check completed!"
EOF

chmod +x /opt/taiger-dev/check-dev-status.sh
```

---

## Шаг 9: Рабочий процесс разработки

### 9.1 Типичный рабочий процесс

```bash
# 1. Вносим изменения в код на локальном компьютере
# Редактируем файлы в VSCode через SSH

# 2. Тестируем изменения локально (опционально)
# Запускаем локально для быстрой проверки

# 3. Деплоим на dev для тестирования
cd /opt/taiger-dev
./deploy-dev.sh

# 4. Проверяем на dev.taiger.pro
# Открываем https://dev.taiger.pro в браузере
# Тестируем все изменения

# 5. Если всё работает - деплоим на прод
./deploy-prod.sh

# 6. Проверяем на taiger.pro
# Открываем https://taiger.pro в браузере
# Убеждаемся что всё работает
```

### 9.2 Быстрый цикл разработки

Для быстрого тестирования можно использовать hot-reload:

```bash
# Запускаем dev сервер с hot-reload
cd /opt/taiger-dev
source .venv/bin/activate

# Устанавливаем uvicorn с hot-reload
pip install uvicorn[standard]

# Запускаем с auto-reload
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Теперь при изменении файлов Python, сервер автоматически перезагрузится
# Изменения фронтенда нужно пересобирать: npm run build
```

---

## Шаг 10: Безопасность

### 10.1 Ограничение доступа к dev (опционально)

Если хотите ограничить доступ к dev окружению:

```bash
# Добавляем basic auth в nginx для dev
sudo htpasswd -c /etc/nginx/.htpasswd-dev your_username

# Обновляем конфигурацию nginx для dev
# Добавляем в server block:
# auth_basic "Dev Environment";
# auth_basic_user_file /etc/nginx/.htpasswd-dev;

# Перезапускаем nginx
sudo systemctl restart nginx
```

### 10.2 Резервное копирование

```bash
# Создаём скрипт для бэкапа dev базы данных
cat > /opt/taiger-dev/backup-dev-db.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/taiger-dev/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/taiger_db_dev_$DATE.sql"

mkdir -p $BACKUP_DIR

echo "💾 Creating backup of dev database..."
sudo -u postgres pg_dump taiger_db_dev > $BACKUP_FILE

# Сжимаем бэкап
gzip $BACKUP_FILE

echo "✅ Backup created: $BACKUP_FILE.gz"

# Удаляем старые бэкапы (оставляем последние 7)
find $BACKUP_DIR -name "taiger_db_dev_*.sql.gz" -mtime +7 -delete

echo "🧹 Old backups removed"
EOF

chmod +x /opt/taiger-dev/backup-dev-db.sh

# Добавляем в cron для ежедневного бэкапа
# crontab -e
# 0 2 * * * /opt/taiger-dev/backup-dev-db.sh
```

---

## Проверочный чеклист

После выполнения всех шагов проверьте:

- [ ] База данных `taiger_db_dev` создана
- [ ] systemd сервис `taiger-api-dev` создан и включён
- [ ] SSL сертификат для `dev.taiger.pro` получен
- [ ] Nginx конфигурация для `dev.taiger.pro` создана и активирована
- [ ] Backend dev запускается на порту 8001
- [ ] Frontend dev собран и доступен
- [ ] `https://dev.taiger.pro` открывается в браузере
- [ ] API endpoints на dev работают
- [ ] WebSocket на dev работает
- [ ] Скрипты деплоя работают
- [ ] Логи доступны для просмотра

---

## Устранение неполадок

### Проблема: Backend dev не запускается

```bash
# Проверяем логи
sudo journalctl -u taiger-api-dev -n 50

# Проверяем порт
ss -tulnp | grep 8001

# Проверяем базу данных
sudo -u postgres psql -l | grep taiger_db_dev

# Проверяем конфигурацию
cat /opt/taiger-dev/.env.dev
```

### Проблема: Frontend dev не загружается

```bash
# Проверяем nginx конфигурацию
sudo nginx -t

# Проверяем что файлы существуют
ls -la /opt/taiger-dev/frontend-dev/dist/

# Проверяем права доступа
sudo chown -R www-data:www-data /opt/taiger-dev/frontend-dev/dist/
```

### Проблема: WebSocket не работает на dev

```bash
# Проверяем что WebSocket проксируется правильно
curl -I -H "Connection: Upgrade" -H "Upgrade: websocket" https://dev.taiger.pro/api/ws/

# Проверяем логи nginx
sudo tail -f /var/log/nginx/error.log
```

---

## Дополнительные ресурсы

- [Systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Nginx WebSocket Proxying](https://nginx.org/en/docs/http/websocket.html)
- [PostgreSQL Backup](https://www.postgresql.org/docs/current/backup.html)
- [Certbot Documentation](https://certbot.eff.org/docs/)

---

## Заключение

После выполнения всех шагов у вас будет:

1. ✅ Изолированная dev среда на том же VPS
2. ✅ Отдельная база данных для разработки
3. ✅ Безопасный доступ через dev.taiger.pro
4. ✅ Автоматизированные скрипты деплоя
5. ✅ Возможность тестирования без риска для продакшена
6. ✅ Быстрый цикл разработки

Теперь вы можете разрабатывать и тестировать изменения на dev.taiger.pro, не боясь повредить продакшен!
