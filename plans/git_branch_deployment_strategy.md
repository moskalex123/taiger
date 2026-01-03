# Git-Branch Based Deployment Strategy

## Обзор решения

Стратегия деплоя на основе Git-веток, которая позволяет безопасно разрабатывать и тестировать изменения без дублирования файлов на диске. Это идеальное решение для VPS с ограниченным дисковым пространством.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS (taiger.pro)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Git Repository: /opt/taiger/                               │
│  ├── main (production)                                      │
│  ├── develop (staging/testing)                              │
│  ├── feature/fix-bug-123 (новые функции)                    │
│  └── hotfix/critical-fix (срочные исправления)              │
│                                                              │
│  Environment:                                                │
│  ├── Active branch: main (по умолчанию)                     │
│  ├── Database: taiger_db (одна база)                        │
│  ├── Redis: redis (db 0)                                    │
│  └── Service: taiger-api.service                            │
│                                                              │
│  Deployment:                                                 │
│  ├── git checkout <branch>                                  │
│  ├── npm run build (frontend)                               │
│  ├── systemctl restart taiger-api (backend)                │
│  └── rollback: git checkout previous-branch                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Стратегия веток (Git Branching Strategy)

```
main (production)
  ↑
  │ merge (after testing)
  │
develop (staging)
  ↑
  │ merge
  │
feature/* (new features)
hotfix/* (urgent fixes)
```

### Описание веток:

- **`main`** - продакшен-ветка, всегда стабильная
- **`develop`** - ветка для тестирования изменений
- **`feature/*`** - ветки для разработки новых функций
- **`hotfix/*`** - ветки для срочных исправлений

---

## Шаг 1: Инициализация Git-репозитория

### 1.1 Проверка текущего состояния Git

```bash
cd /opt/taiger

# Проверяем, есть ли уже git репозиторий
git status

# Если git не инициализирован:
git init

# Если уже есть, проверяем ветки
git branch -a
```

### 1.2 Создание базовой структуры веток

```bash
# Переименовываем текущую ветку в main (если нужно)
git branch -M main

# Создаём ветку develop
git checkout -b develop

# Возвращаемся в main
git checkout main

# Проверяем ветки
git branch
# Должно показать:
# * main
#   develop
```

### 1.3 Настройка .gitignore

```bash
cat > /opt/taiger/.gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/
*.egg-info/
dist/
build/

# Environment variables
.env
.env.local
.env.*.local
.secrets.env

# Logs
*.log
logs/
*.session

# Database
*.db
*.db-journal
*.dump
*.sql

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*

# Frontend build
frontend/dist/
frontend-dev/dist/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
*.tar.gz

# Session files
*.session
*.session-journal

# Downloads
downloads/

# Alembic (опционально - можно включить)
# alembic/versions/*.pyc

# Testing
.pytest_cache/
.coverage
htmlcov/

# Misc
.project
.settings/
.kilocode/
.qoder/
.trae/
EOF
```

### 1.4 Создание первого коммита

```bash
# Добавляем все файлы
git add .

# Создаём первый коммит
git commit -m "Initial commit: production setup"

# Проверяем статус
git status
git log --oneline -5
```

---

## Шаг 2: Настройка Git конфигурации

### 2.1 Настройка пользователя Git

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Или локально для этого репозитория
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 2.2 Настройка удалённого репозитория (опционально)

```bash
# Если хотите использовать удалённый репозиторий (GitHub/GitLab/Bitbucket)
git remote add origin https://github.com/yourusername/taiger.git

# Или с SSH
git remote add origin git@github.com:yourusername/taiger.git

# Пушим текущее состояние
git push -u origin main
git push -u origin develop
```

---

## Шаг 3: Создание скриптов для деплоя

### 3.1 Скрипт для переключения на develop ветку

```bash
cat > /opt/taiger/switch-to-develop.sh << 'EOF'
#!/bin/bash
set -e

echo "🔄 Switching to develop branch..."
echo "⚠️  This will restart the production service with develop code!"
echo ""

# Запрашиваем подтверждение
read -p "Are you sure you want to switch to develop? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Operation cancelled"
    exit 1
fi

# Сохраняем текущее состояние (если есть незакоммиченные изменения)
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Saving uncommitted changes..."
    git stash push -m "Auto-stash before switching to develop"
    echo "✅ Changes stashed. Use 'git stash pop' to restore them."
fi

# Переключаемся на develop
git checkout develop

# Проверяем, нужно ли подтянуть изменения
if [ -n "$(git log origin/develop..develop)" ]; then
    echo "📥 Pulling latest changes from origin/develop..."
    git pull origin develop
fi

# Собираем фронтенд
echo "🔨 Building frontend..."
cd /opt/taiger/frontend
npm run build

# Перезапускаем сервис
echo "🚀 Restarting service..."
sudo systemctl restart taiger-api

# Проверяем статус сервиса
sleep 3
if sudo systemctl is-active --quiet taiger-api; then
    echo "✅ Successfully switched to develop branch!"
    echo "🌐 Current URL: https://taiger.pro (running develop code)"
else
    echo "❌ Service failed to start! Rolling back..."
    git checkout main
    cd /opt/taiger/frontend
    npm run build
    sudo systemctl restart taiger-api
    echo "🔄 Rolled back to main branch"
    exit 1
fi

# Показываем текущую ветку
echo ""
echo "📊 Current branch: $(git branch --show-current)"
echo "📝 Last commit: $(git log -1 --oneline)"
EOF

chmod +x /opt/taiger/switch-to-develop.sh
```

### 3.2 Скрипт для переключения на main ветку

```bash
cat > /opt/taiger/switch-to-main.sh << 'EOF'
#!/bin/bash
set -e

echo "🔄 Switching to main branch..."
echo ""

# Запрашиваем подтверждение
read -p "Are you sure you want to switch to main? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Operation cancelled"
    exit 1
fi

# Сохраняем текущее состояние (если есть незакоммиченные изменения)
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Saving uncommitted changes..."
    git stash push -m "Auto-stash before switching to main"
    echo "✅ Changes stashed. Use 'git stash pop' to restore them."
fi

# Переключаемся на main
git checkout main

# Проверяем, нужно ли подтянуть изменения
if [ -n "$(git log origin/main..main)" ]; then
    echo "📥 Pulling latest changes from origin/main..."
    git pull origin main
fi

# Собираем фронтенд
echo "🔨 Building frontend..."
cd /opt/taiger/frontend
npm run build

# Перезапускаем сервис
echo "🚀 Restarting service..."
sudo systemctl restart taiger-api

# Проверяем статус сервиса
sleep 3
if sudo systemctl is-active --quiet taiger-api; then
    echo "✅ Successfully switched to main branch!"
    echo "🌐 Current URL: https://taiger.pro (running production code)"
else
    echo "❌ Service failed to start!"
    exit 1
fi

# Показываем текущую ветку
echo ""
echo "📊 Current branch: $(git branch --show-current)"
echo "📝 Last commit: $(git log -1 --oneline)"
EOF

chmod +x /opt/taiger/switch-to-main.sh
```

### 3.3 Скрипт для создания feature ветки

```bash
cat > /opt/taiger/create-feature-branch.sh << 'EOF'
#!/bin/bash

if [ -z "$1" ]; then
    echo "❌ Usage: $0 <feature-name>"
    echo "   Example: $0 add-user-dashboard"
    exit 1
fi

FEATURE_NAME=$1
BRANCH_NAME="feature/$FEATURE_NAME"

echo "🌟 Creating feature branch: $BRANCH_NAME"
echo ""

# Проверяем, существует ли уже такая ветка
if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
    echo "❌ Branch $BRANCH_NAME already exists!"
    echo "   Use: git checkout $BRANCH_NAME"
    exit 1
fi

# Создаём ветку от develop
git checkout develop
git checkout -b $BRANCH_NAME

echo "✅ Feature branch created: $BRANCH_NAME"
echo ""
echo "📝 Next steps:"
echo "   1. Make your changes"
echo "   2. Test changes locally"
echo "   3. Commit changes: git add . && git commit -m 'Description'"
echo "   4. Switch to develop: git checkout develop"
echo "   5. Merge feature: git merge $BRANCH_NAME"
echo "   6. Delete feature: git branch -d $BRANCH_NAME"
echo ""
echo "📊 Current branch: $(git branch --show-current)"
EOF

chmod +x /opt/taiger/create-feature-branch.sh
```

### 3.4 Скрипт для деплоя изменений из develop в main

```bash
cat > /opt/taiger/deploy-to-production.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Deploying to production..."
echo "⚠️  This will merge develop into main and restart production!"
echo ""

# Проверяем, что мы в develop
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "develop" ]; then
    echo "❌ You must be in develop branch to deploy to production!"
    echo "   Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Проверяем, есть ли незакоммиченные изменения
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ You have uncommitted changes!"
    echo "   Please commit or stash them first."
    git status
    exit 1
fi

# Запрашиваем подтверждение
read -p "Are you sure you want to deploy to production? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Создаём бэкап текущего состояния
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
echo "💾 Creating backup tag: $BACKUP_TAG"
git tag $BACKUP_TAG

# Мержим develop в main
echo "🔄 Merging develop into main..."
git checkout main
git merge develop --no-ff -m "Merge develop into main - deployment $BACKUP_TAG"

# Собираем фронтенд
echo "🔨 Building frontend..."
cd /opt/taiger/frontend
npm run build

# Перезапускаем сервис
echo "🚀 Restarting service..."
sudo systemctl restart taiger-api

# Проверяем статус сервиса
sleep 3
if sudo systemctl is-active --quiet taiger-api; then
    echo "✅ Successfully deployed to production!"
    echo "🌐 Current URL: https://taiger.pro (running production code)"
    echo ""
    echo "📊 Current branch: $(git branch --show-current)"
    echo "📝 Last commit: $(git log -1 --oneline)"
    echo ""
    echo "💾 Backup tag: $BACKUP_TAG"
    echo "   To rollback: git checkout $BACKUP_TAG && ./switch-to-main.sh"
else
    echo "❌ Service failed to start! Rolling back..."
    git checkout $BACKUP_TAG
    cd /opt/taiger/frontend
    npm run build
    sudo systemctl restart taiger-api
    echo "🔄 Rolled back to $BACKUP_TAG"
    exit 1
fi
EOF

chmod +x /opt/taiger/deploy-to-production.sh
```

### 3.5 Скрипт для быстрого отката (rollback)

```bash
cat > /opt/taiger/rollback.sh << 'EOF'
#!/bin/bash

if [ -z "$1" ]; then
    echo "❌ Usage: $0 <commit-hash-or-tag>"
    echo "   Example: $0 backup-20240103-150000"
    echo "   Example: $0 abc1234"
    echo ""
    echo "📋 Available backup tags:"
    git tag -l "backup-*" | sort -r | head -10
    exit 1
fi

TARGET=$1

echo "🔄 Rolling back to: $TARGET"
echo "⚠️  This will revert the production to a previous state!"
echo ""

# Проверяем, что цель существует
if ! git rev-parse $TARGET >/dev/null 2>&1; then
    echo "❌ Target $TARGET not found!"
    exit 1
fi

# Запрашиваем подтверждение
read -p "Are you sure you want to rollback? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Rollback cancelled"
    exit 1
fi

# Создаём бэкап перед откатом
BACKUP_TAG="pre-rollback-$(date +%Y%m%d-%H%M%S)"
echo "💾 Creating pre-rollback backup: $BACKUP_TAG"
git tag $BACKUP_TAG

# Откатываемся
echo "🔄 Rolling back to $TARGET..."
git checkout $TARGET
git checkout -b rollback-$BACKUP_TAG

# Собираем фронтенд
echo "🔨 Building frontend..."
cd /opt/taiger/frontend
npm run build

# Перезапускаем сервис
echo "🚀 Restarting service..."
sudo systemctl restart taiger-api

# Проверяем статус сервиса
sleep 3
if sudo systemctl is-active --quiet taiger-api; then
    echo "✅ Successfully rolled back to $TARGET!"
    echo "🌐 Current URL: https://taiger.pro (running rollback code)"
    echo ""
    echo "📊 Current branch: $(git branch --show-current)"
    echo "📝 Current commit: $(git log -1 --oneline)"
    echo ""
    echo "💾 Pre-rollback backup: $BACKUP_TAG"
else
    echo "❌ Service failed to start!"
    echo "💾 Pre-rollback backup: $BACKUP_TAG"
    echo "   To restore: git checkout $BACKUP_TAG && ./switch-to-main.sh"
    exit 1
fi
EOF

chmod +x /opt/taiger/rollback.sh
```

### 3.6 Скрипт для просмотра статуса

```bash
cat > /opt/taiger/deployment-status.sh << 'EOF'
#!/bin/bash

echo "📊 Deployment Status"
echo "===================="
echo ""

# Текущая ветка
echo "🌿 Current branch: $(git branch --show-current)"
echo ""

# Последний коммит
echo "📝 Last commit:"
git log -1 --oneline --decorate
echo ""

# Статус изменений
echo "📋 Git status:"
git status --short
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "⚠️  You have uncommitted changes!"
fi
echo ""

# Статус сервиса
echo "🔧 Service status:"
sudo systemctl status taiger-api --no-pager | head -n 5
echo ""

# Доступные бэкапы
echo "💾 Available backups:"
git tag -l "backup-*" | sort -r | head -5
if [ -z "$(git tag -l "backup-*")" ]; then
    echo "   (no backups yet)"
fi
echo ""

# Разница между ветками
echo "📊 Branch differences:"
if [ "$(git branch --show-current)" = "main" ]; then
    COMMITS_BEHIND=$(git log main..develop --oneline | wc -l)
    if [ $COMMITS_BEHIND -gt 0 ]; then
        echo "   Main is $COMMITS_BEHIND commits behind develop"
        echo "   New commits in develop:"
        git log main..develop --oneline | head -5
    else
        echo "   ✅ Main is up to date with develop"
    fi
else
    COMMITS_AHEAD=$(git log develop..$(git branch --show-current) --oneline | wc -l)
    if [ $COMMITS_AHEAD -gt 0 ]; then
        echo "   Current branch is $COMMITS_AHEAD commits ahead of develop"
    else
        echo "   Current branch is up to date with develop"
    fi
fi
echo ""

# Последние коммиты
echo "📜 Recent commits:"
git log --oneline --graph --all -10
EOF

chmod +x /opt/taiger/deployment-status.sh
```

---

## Шаг 4: Рабочий процесс разработки

### 4.1 Типичный рабочий процесс

```bash
# 1. Начинаем с develop
cd /opt/taiger
git checkout develop

# 2. Создаём feature ветку
./create-feature-branch.sh add-new-feature

# 3. Вносим изменения
# Редактируем файлы в VSCode

# 4. Тестируем изменения локально
# Запускаем локально для проверки

# 5. Коммитим изменения
git add .
git commit -m "Add new feature: description"

# 6. Переключаемся на develop для тестирования
git checkout develop
git merge feature/add-new-feature

# 7. Переключаем продакшен на develop для тестирования
./switch-to-develop.sh

# 8. Тестируем на продакшене (https://taiger.pro)
# Проверяем все изменения

# 9. Если всё работает - деплоим на прод
./deploy-to-production.sh

# 10. Удаляем feature ветку
git branch -d feature/add-new-feature
```

### 4.2 Быстрый цикл разработки (для мелких исправлений)

```bash
# 1. Переключаемся на develop
git checkout develop

# 2. Вносим изменения
# Редактируем файлы

# 3. Коммитим
git add .
git commit -m "Fix bug: description"

# 4. Переключаем продакшен на develop
./switch-to-develop.sh

# 5. Тестируем

# 6. Если всё ок - деплоим
./deploy-to-production.sh
```

### 4.3 Срочные исправления (hotfix)

```bash
# 1. Создаём hotfix ветку от main
git checkout main
git checkout -b hotfix/critical-bug-fix

# 2. Вносим исправления
# Редактируем файлы

# 3. Коммитим
git add .
git commit -m "Hotfix: critical bug fix"

# 4. Мержим в main
git checkout main
git merge hotfix/critical-bug-fix

# 5. Собираем и перезапускаем
cd /opt/taiger/frontend
npm run build
sudo systemctl restart taiger-api

# 6. Мержим hotfix в develop
git checkout develop
git merge hotfix/critical-bug-fix

# 7. Удаляем hotfix ветку
git branch -d hotfix/critical-bug-fix
```

---

## Шаг 5: Работа с незакоммиченными изменениями

### 5.1 Сохранение изменений без коммита (git stash)

```bash
# Вносим изменения для тестирования
# Редактируем файлы

# Сохраняем изменения в stash
git stash push -m "Test changes for feature X"

# Переключаемся на develop для тестирования
./switch-to-develop.sh

# Тестируем

# Возвращаемся к изменениям
git checkout feature/add-new-feature
git stash pop

# Продолжаем работу
```

### 5.2 Просмотр сохранённых изменений

```bash
# Список всех stash
git stash list

# Просмотр содержимого stash
git stash show -p stash@{0}

# Применение конкретного stash
git stash apply stash@{0}
```

---

## Шаг 6: Управление миграциями базы данных

### 6.1 Безопасное применение миграций

```bash
# Перед применением миграций всегда делайте бэкап
sudo -u postgres pg_dump taiger_db > /tmp/taiger_db_backup_$(date +%Y%m%d_%H%M%S).sql

# Применяем миграции
alembic upgrade head

# Если что-то пошло не так - откатываем миграцию
alembic downgrade -1

# Или восстанавливаем бэкап
sudo -u postgres psql taiger_db < /tmp/taiger_db_backup_YYYYMMDD_HHMMSS.sql
```

### 6.2 Скрипт для безопасного деплоя с миграциями

```bash
cat > /opt/taiger/deploy-with-migrations.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Deploying with database migrations..."
echo ""

# Проверяем, есть ли новые миграции
if [ -z "$(alembic current)" ] || [ "$(alembic current)" != "$(alembic heads | awk '{print $1}')" ]; then
    echo "📊 New migrations detected!"
    echo ""
    
    # Показываем новые миграции
    echo "📋 Pending migrations:"
    alembic current
    echo "↓"
    alembic heads
    echo ""
    
    # Создаём бэкап базы данных
    BACKUP_FILE="/tmp/taiger_db_backup_$(date +%Y%m%d_%H%M%S).sql"
    echo "💾 Creating database backup: $BACKUP_FILE"
    sudo -u postgres pg_dump taiger_db > $BACKUP_FILE
    echo "✅ Backup created"
    echo ""
    
    # Запрашиваем подтверждение
    read -p "Do you want to apply migrations? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Migration cancelled"
        exit 1
    fi
    
    # Применяем миграции
    echo "🔄 Applying migrations..."
    alembic upgrade head
    echo "✅ Migrations applied"
else
    echo "✅ No new migrations to apply"
fi

# Собираем фронтенд
echo ""
echo "🔨 Building frontend..."
cd /opt/taiger/frontend
npm run build

# Перезапускаем сервис
echo "🚀 Restarting service..."
sudo systemctl restart taiger-api

# Проверяем статус сервиса
sleep 3
if sudo systemctl is-active --quiet taiger-api; then
    echo "✅ Deployment completed successfully!"
else
    echo "❌ Service failed to start!"
    echo "💾 Backup: $BACKUP_FILE"
    echo "   To restore: sudo -u postgres psql taiger_db < $BACKUP_FILE"
    exit 1
fi
EOF

chmod +x /opt/taiger/deploy-with-migrations.sh
```

---

## Шаг 7: Мониторинг и логирование

### 7.1 Скрипт для просмотра логов

```bash
cat > /opt/taiger/view-logs.sh << 'EOF'
#!/bin/bash

echo "📊 Viewing logs..."
echo "Press Ctrl+C to exit"
echo ""

# Показываем последние 50 строк логов
sudo journalctl -u taiger-api -n 50 --no-pager

echo ""
echo "🔄 Following logs (press Ctrl+C to exit)..."
sudo journalctl -u taiger-api -f
EOF

chmod +x /opt/taiger/view-logs.sh
```

### 7.2 Скрипт для проверки здоровья системы

```bash
cat > /opt/taiger/health-check.sh << 'EOF'
#!/bin/bash

echo "🏥 System Health Check"
echo "======================"
echo ""

# Проверка сервиса
echo "🔧 Service status:"
if sudo systemctl is-active --quiet taiger-api; then
    echo "   ✅ taiger-api is running"
else
    echo "   ❌ taiger-api is NOT running"
fi
echo ""

# Проверка порта
echo "🌐 Port 8000:"
if ss -tulnp | grep -q 8000; then
    echo "   ✅ Port 8000 is listening"
else
    echo "   ❌ Port 8000 is NOT listening"
fi
echo ""

# Проверка базы данных
echo "💾 Database:"
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw taiger_db; then
    echo "   ✅ Database taiger_db exists"
else
    echo "   ❌ Database taiger_db NOT found"
fi
echo ""

# Проверка Redis
echo "🔴 Redis:"
if redis-cli ping >/dev/null 2>&1; then
    echo "   ✅ Redis is running"
else
    echo "   ❌ Redis is NOT running"
fi
echo ""

# Проверка дискового пространства
echo "💿 Disk space:"
df -h /opt/taiger | tail -n 1 | awk '{print "   Used: " $3 " / " $2 " (" $5 ")"}'
echo ""

# Проверка памяти
echo "🧠 Memory:"
free -h | grep Mem | awk '{print "   Used: " $3 " / " $2}'
echo ""

# Проверка Git статуса
echo "📊 Git status:"
CURRENT_BRANCH=$(git branch --show-current)
echo "   Branch: $CURRENT_BRANCH"
if [ -n "$(git status --porcelain)" ]; then
    echo "   ⚠️  Uncommitted changes detected"
    git status --short | head -5
else
    echo "   ✅ Working directory clean"
fi
echo ""

echo "✅ Health check completed!"
EOF

chmod +x /opt/taiger/health-check.sh
```

---

## Шаг 8: Резервное копирование

### 8.1 Скрипт для создания бэкапа

```bash
cat > /opt/taiger/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/taiger/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

echo "💾 Creating backup..."
echo "Date: $DATE"
echo ""

# Создаём Git тег
TAG="backup-$DATE"
git tag $TAG
echo "✅ Git tag created: $TAG"

# Бэкап базы данных
DB_BACKUP="$BACKUP_DIR/taiger_db_$DATE.sql"
echo "💾 Creating database backup..."
sudo -u postgres pg_dump taiger_db > $DB_BACKUP
gzip $DB_BACKUP
echo "✅ Database backup created: ${DB_BACKUP}.gz"

# Бэкап .env файла (без секретов)
ENV_BACKUP="$BACKUP_DIR/env_$DATE.txt"
grep -v "SECRET\|PASSWORD\|TOKEN\|KEY" /opt/taiger/.env > $ENV_BACKUP
echo "✅ Environment backup created: $ENV_BACKUP"

# Удаляем старые бэкапы (оставляем последние 7 дней)
find $BACKUP_DIR -name "taiger_db_*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "env_*.txt" -mtime +7 -delete
echo "🧹 Old backups removed"

# Удаляем старые Git теги (оставляем последние 10)
git tag -l "backup-*" | sort -r | tail -n +11 | xargs -r git tag -d
echo "🧹 Old Git tags removed"

echo ""
echo "✅ Backup completed!"
echo "📁 Backup directory: $BACKUP_DIR"
echo "🏷️  Git tag: $TAG"
EOF

chmod +x /opt/taiger/backup.sh
```

### 8.2 Добавление в cron для автоматического бэкапа

```bash
# Редактируем crontab
crontab -e

# Добавляем строку для ежедневного бэкапа в 2 часа ночи
0 2 * * * /opt/taiger/backup.sh >> /opt/taiger/backups/backup.log 2>&1
```

---

## Шаг 9: Быстрые команды (Cheatsheet)

### 9.1 Создание файла с быстрыми командами

```bash
cat > /opt/taiger/QUICK_COMMANDS.md << 'EOF'
# Quick Commands Reference

## Git Operations

### View current status
```bash
./deployment-status.sh
```

### Switch to develop (testing)
```bash
./switch-to-develop.sh
```

### Switch to main (production)
```bash
./switch-to-main.sh
```

### Deploy to production
```bash
./deploy-to-production.sh
```

### Create feature branch
```bash
./create-feature-branch.sh feature-name
```

### Rollback to previous version
```bash
./rollback.sh backup-20240103-150000
```

### View logs
```bash
./view-logs.sh
```

### Health check
```bash
./health-check.sh
```

### Create backup
```bash
./backup.sh
```

## Manual Git Commands

### View all branches
```bash
git branch -a
```

### View recent commits
```bash
git log --oneline --graph --all -10
```

### View differences between branches
```bash
git diff main develop
```

### Stash uncommitted changes
```bash
git stash push -m "Description"
```

### Restore stashed changes
```bash
git stash pop
```

### View stash list
```bash
git stash list
```

### Merge feature branch
```bash
git checkout develop
git merge feature/branch-name
git branch -d feature/branch-name
```

## Service Management

### Restart service
```bash
sudo systemctl restart taiger-api
```

### View service status
```bash
sudo systemctl status taiger-api
```

### View service logs
```bash
sudo journalctl -u taiger-api -f
```

## Database Operations

### Create backup
```bash
sudo -u postgres pg_dump taiger_db > backup.sql
```

### Restore backup
```bash
sudo -u postgres psql taiger_db < backup.sql
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

## Frontend Operations

### Build frontend
```bash
cd /opt/taiger/frontend
npm run build
```

### Install dependencies
```bash
cd /opt/taiger/frontend
npm install
```

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u taiger-api -n 50

# Check port
ss -tulnp | grep 8000

# Check database connection
sudo -u postgres psql -l
```

### Frontend not loading
```bash
# Check nginx config
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log

# Rebuild frontend
cd /opt/taiger/frontend
npm run build
```

### Git merge conflict
```bash
# Resolve conflicts manually
# Then:
git add .
git commit -m "Resolved merge conflicts"
```

### Migration failed
```bash
# Rollback migration
alembic downgrade -1

# Restore database backup
sudo -u postgres psql taiger_db < backup.sql
```
EOF
```

---

## Шаг 10: Проверочный чеклист

После выполнения всех шагов проверьте:

- [ ] Git репозиторий инициализирован
- [ ] Ветки `main` и `develop` созданы
- [ ] `.gitignore` настроен
- [ ] Все скрипты деплоя созданы и исполняемы
- [ ] Скрипт `switch-to-develop.sh` работает
- [ ] Скрипт `switch-to-main.sh` работает
- [ ] Скрипт `deploy-to-production.sh` работает
- [ ] Скрипт `rollback.sh` работает
- [ ] Скрипт `deployment-status.sh` работает
- [ ] Скрипт `health-check.sh` работает
- [ ] Скрипт `backup.sh` работает
- [ ] Автоматический бэкап добавлен в cron
- [ ] Файл `QUICK_COMMANDS.md` создан

---

## Примеры использования

### Пример 1: Добавление новой функции

```bash
# 1. Создаём feature ветку
./create-feature-branch.sh add-user-dashboard

# 2. Вносим изменения
# Редактируем файлы в VSCode

# 3. Коммитим
git add .
git commit -m "Add user dashboard with statistics"

# 4. Переключаемся на develop
git checkout develop
git merge feature/add-user-dashboard

# 5. Переключаем продакшен на develop для тестирования
./switch-to-develop.sh

# 6. Тестируем на https://taiger.pro

# 7. Если всё работает - деплоим на прод
./deploy-to-production.sh

# 8. Удаляем feature ветку
git branch -d feature/add-user-dashboard
```

### Пример 2: Исправление бага

```bash
# 1. Переключаемся на develop
git checkout develop

# 2. Вносим исправления
# Редактируем файлы

# 3. Коммитим
git add .
git commit -m "Fix: incorrect balance calculation"

# 4. Переключаем продакшен на develop
./switch-to-develop.sh

# 5. Тестируем

# 6. Деплоим на прод
./deploy-to-production.sh
```

### Пример 3: Быстрое тестирование изменений без коммита

```bash
# 1. Вносим изменения
# Редактируем файлы

# 2. Сохраняем в stash
git stash push -m "Test changes"

# 3. Переключаемся на develop
./switch-to-develop.sh

# 4. Тестируем

# 5. Если нужно вернуть изменения
git checkout feature/branch-name
git stash pop

# 6. Если изменения не нужны - просто удаляем stash
git stash drop
```

### Пример 4: Откат после неудачного деплоя

```bash
# 1. Проверяем доступные бэкапы
./deployment-status.sh

# 2. Откатываемся к предыдущей версии
./rollback.sh backup-20240103-150000

# 3. Проверяем, что всё работает
./health-check.sh

# 4. Если нужно - исправляем проблему в develop
git checkout develop
# Вносим исправления
git add .
git commit -m "Fix deployment issue"

# 5. Деплоим снова
./deploy-to-production.sh
```

---

## Преимущества этой стратегии

### ✅ Преимущества:

1. **Не требует дополнительного места на диске** - все изменения в одном репозитории
2. **Быстрое переключение между версиями** - git checkout занимает секунды
3. **Простая история изменений** - git log показывает всё
4. **Безопасный откат** - git tags для бэкапов
5. **Гибкость** - можно создавать любые ветки для экспериментов
6. **Нет проблем с Docker/nginx/websocket** - используется текущая конфигурация
7. **Простота** - не нужно настраивать дополнительные сервисы
8. **Минимальные изменения** - только Git и несколько скриптов

### ⚠️ Недостатки:

1. **Тестирование на продакшене** - нужно переключать продакшен на develop
2. **Одна база данных** - нужно быть осторожным с миграциями
3. **Требует дисциплины** - нужно всегда коммитить изменения перед переключением

---

## Дополнительные рекомендации

### 1. Всегда делайте бэкапы перед деплоем

```bash
./backup.sh
```

### 2. Проверяйте здоровье системы перед деплоем

```bash
./health-check.sh
```

### 3. Используйте stash для временных изменений

```bash
git stash push -m "Temporary test"
```

### 4. Создавайте теги для важных версий

```bash
git tag v1.0.0
git push origin v1.0.0
```

### 5. Регулярно очищайте старые бэкапы

```bash
# Скрипт backup.sh автоматически удаляет старые бэкапы
# Но можно проверить вручную
ls -lh /opt/taiger/backups/
```

---

## Заключение

Эта стратегия идеально подходит для вашей ситуации:

- ✅ Не требует дополнительного места на диске
- ✅ Использует текущую конфигурацию (nginx, websocket и т.д.)
- ✅ Позволяет безопасно тестировать изменения
- ✅ Обеспечивает быстрый откат при проблемах
- ✅ Проста в использовании и настройке

Теперь вы можете разрабатывать и тестировать изменения, используя Git ветки, не боясь повредить продакшен!
