# GitHub Integration Guide

## Обзор

Интеграция GitHub в стратегию Git-branch based deployment позволит вам:
- Разрабатывать код локально на Windows
- Синхронизировать изменения с VPS
- Использовать GitHub для хранения истории изменений
- Использовать Pull Requests для код-ревью
- Иметь резервную копию кода в облаке

## Архитектура с GitHub

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
│                    (github.com/username/taiger)            │
├─────────────────────────────────────────────────────────────┤
│  main (production)                                          │
│  develop (staging)                                          │
│  feature/* (new features)                                   │
│  hotfix/* (urgent fixes)                                    │
└─────────────────────────────────────────────────────────────┘
                           ↑↓ git push/pull
┌─────────────────────────────────────────────────────────────┐
│              Local Development (Windows PC)                  │
│              VSCode + Git Extension                         │
└─────────────────────────────────────────────────────────────┘
                           ↑↓ git push/pull
┌─────────────────────────────────────────────────────────────┐
│                    VPS (taiger.pro)                         │
│              /opt/taiger/ (production)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Шаг 1: Создание GitHub репозитория

### 1.1 Создание репозитория на GitHub

1. Перейдите на https://github.com/new
2. Введите имя репозитория: `taiger`
3. Выберите:
   - **Public** или **Private** (рекомендую Private для коммерческого проекта)
   - **НЕ** отмечайте "Add a README file" (мы добавим позже)
   - **НЕ** отмечайте "Add .gitignore" (мы уже создали свой)
   - **НЕ** отмечайте "Choose a license" (можно добавить позже)
4. Нажмите "Create repository"

### 1.2 Настройка SSH ключей для GitHub (рекомендуется)

#### На Windows (локальная разработка):

```powershell
# Генерация SSH ключа (если ещё нет)
ssh-keygen -t ed25519 -C "your.email@example.com"

# Добавление ключа в ssh-agent
Get-Service ssh-agent | Set-Service -StartupType Manual
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519

# Копирование публичного ключа
cat $env:USERPROFILE\.ssh\id_ed25519.pub
```

#### На VPS:

```bash
# Генерация SSH ключа (если ещё нет)
ssh-keygen -t ed25519 -C "your.email@example.com"

# Добавление ключа в ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Копирование публичного ключа
cat ~/.ssh/id_ed25519.pub
```

#### Добавление ключа в GitHub:

1. Скопируйте публичный ключ (вывод команды `cat ...pub`)
2. Перейдите на https://github.com/settings/keys
3. Нажмите "New SSH key"
4. Введите заголовок (например: "Windows PC" или "VPS")
5. Вставьте ключ
6. Нажмите "Add SSH key"

### 1.3 Добавление удалённого репозитория

```bash
# На VPS
cd /opt/taiger

# Добавляем GitHub как удалённый репозиторий
git remote add origin git@github.com:yourusername/taiger.git

# Проверяем
git remote -v
```

---

## Шаг 2: Первичный пуш в GitHub

### 2.1 Пуш текущего состояния в GitHub

```bash
# На VPS
cd /opt/taiger

# Пушим main ветку
git push -u origin main

# Пушим develop ветку
git push -u origin develop

# Пушим все ветки
git push --all origin

# Пушим все теги
git push --tags origin
```

### 2.2 Проверка на GitHub

Откройте https://github.com/yourusername/taiger и убедитесь, что:
- Ветка `main` отображается как "main"
- Ветка `develop` отображается как "develop"
- Все файлы проекта видны в репозитории

---

## Шаг 3: Настройка локальной разработки на Windows

### 3.1 Клонирование репозитория на Windows

```powershell
# В PowerShell или Git Bash
cd C:\path\to\your\projects

# Клонируем репозиторий
git clone git@github.com:yourusername/taiger.git

# Переходим в директорию проекта
cd taiger

# Проверяем ветки
git branch -a
```

### 3.2 Настройка локального окружения

#### Создание .env файла для локальной разработки:

```powershell
# Копируем пример .env файла
copy .env.example .env

# Или создаём вручную
```

Содержимое `.env` для локальной разработки:

```env
# Database (используйте SQLite для локальной разработки)
DATABASE_URL=sqlite+aiosqlite:///./taiger_local.db

# Redis (можно использовать локальный Redis или Docker)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API
API_PORT=8000
API_HOST=127.0.0.1

# Telegram (используйте тестовые данные или те же, что на проде)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here

# Frontend
FRONTEND_URL=http://localhost:5173

# S3 (можно использовать те же credentials)
S3_ENDPOINT=https://storage.yandexcloud.net
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

# AI APIs
OPENROUTER_API_KEY=your_openrouter_key
HYPERBOLIC_API_KEY=your_hyperbolic_key

# JWT
JWT_SECRET=your_local_jwt_secret_here

# Environment
ENVIRONMENT=development
DEBUG=True
```

#### Создание .env файла для frontend:

```powershell
cd frontend
copy .env.example .env
```

Содержимое `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000/api/ws
VITE_TELEGRAM_WEBAPP_URL=http://localhost:5173
```

### 3.3 Установка зависимостей на Windows

#### Python зависимости:

```powershell
# Создаём виртуальное окружение
python -m venv .venv

# Активируем виртуальное окружение
.venv\Scripts\activate

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

#### Node.js зависимости:

```powershell
cd frontend

# Устанавливаем зависимости
npm install
```

### 3.4 Запуск локального окружения

#### Backend:

```powershell
# В корне проекта
.venv\Scripts\activate

# Применяем миграции (для SQLite)
alembic upgrade head

# Запускаем сервер
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend:

```powershell
# В директории frontend
cd frontend

# Запускаем dev сервер
npm run dev
```

Теперь приложение доступно по адресу http://localhost:5173

---

## Шаг 4: Рабочий процесс с GitHub

### 4.1 Типичный рабочий процесс

```
┌─────────────────────────────────────────────────────────────┐
│  1. Локальная разработка (Windows PC)                       │
│     - Создаём feature ветку                                 │
│     - Вносим изменения                                      │
│     - Тестируем локально                                    │
│     - Коммитим изменения                                    │
│     - Пушим в GitHub                                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Тестирование на VPS                                    │
│     - Пуллим изменения с GitHub                            │
│     - Переключаемся на develop                              │
│     - Мержим feature ветку                                 │
│     - Переключаем продакшен на develop                     │
│     - Тестируем на продакшене                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Деплой на продакшен                                    │
│     - Если всё работает - мержим в main                    │
│     - Пушим в GitHub                                       │
│     - Переключаем продакшен на main                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Пример рабочего процесса

#### Шаг 1: Локальная разработка

```powershell
# На Windows PC
cd C:\path\to\taiger

# Пуллим последние изменения
git fetch origin
git checkout develop
git pull origin develop

# Создаём feature ветку
git checkout -b feature/add-user-dashboard

# Вносим изменения
# Редактируем файлы в VSCode

# Тестируем локально
# Запускаем backend и frontend

# Коммитим изменения
git add .
git commit -m "Add user dashboard with statistics"

# Пушим в GitHub
git push -u origin feature/add-user-dashboard
```

#### Шаг 2: Тестирование на VPS

```bash
# На VPS
cd /opt/taiger

# Пуллим изменения с GitHub
git fetch origin

# Переключаемся на develop
git checkout develop
git pull origin develop

# Мержим feature ветку
git merge origin/feature/add-user-dashboard

# Переключаем продакшен на develop для тестирования
./switch-to-develop.sh

# Тестируем на https://taiger.pro
```

#### Шаг 3: Деплой на продакшен

```bash
# Если всё работает - деплоим на прод
./deploy-to-production.sh

# Пушим изменения в GitHub (main ветка уже обновлена)
git push origin main

# Удаляем feature ветку (опционально)
git branch -d feature/add-user-dashboard
git push origin --delete feature/add-user-dashboard
```

---

## Шаг 5: Использование Pull Requests (опционально)

### 5.1 Создание Pull Request на GitHub

1. Перейдите на https://github.com/yourusername/taiger
2. Нажмите "Pull requests" → "New pull request"
3. Выберите:
   - **base**: `develop`
   - **compare**: `feature/add-user-dashboard`
4. Просмотрите изменения
5. Нажмите "Create pull request"
6. Добавьте описание изменений
7. Нажмите "Create pull request"

### 5.2 Мержинг Pull Request на VPS

```bash
# На VPS
cd /opt/taiger

# Пуллим изменения из GitHub
git fetch origin

# Переключаемся на develop
git checkout develop
git pull origin develop

# Мержим PR (если он был одобрен на GitHub)
git merge origin/feature/add-user-dashboard

# Переключаем продакшен на develop для тестирования
./switch-to-develop.sh
```

---

## Шаг 6: Автоматизация с GitHub Actions (опционально)

### 6.1 Создание workflow для CI/CD

Создайте файл `.github/workflows/deploy.yml`:

```yaml
name: Deploy to VPS

on:
  push:
    branches:
      - main
      - develop
  pull_request:
    branches:
      - main
      - develop

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run tests (если есть)
        run: |
          pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USERNAME }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/taiger
            git fetch origin
            git checkout main
            git pull origin main
            cd frontend
            npm install
            npm run build
            sudo systemctl restart taiger-api
```

### 6.2 Настройка секретов в GitHub

1. Перейдите на https://github.com/yourusername/taiger/settings/secrets/actions
2. Добавьте следующие секреты:
   - `VPS_HOST`: IP адрес вашего VPS
   - `VPS_USERNAME`: Имя пользователя на VPS
   - `VPS_SSH_KEY`: Приватный SSH ключ для подключения к VPS

---

## Шаг 7: Скрипты для синхронизации с GitHub

### 7.1 Скрипт для пулла изменений с GitHub на VPS

```bash
cat > /opt/taiger/pull-from-github.sh << 'EOF'
#!/bin/bash
set -e

BRANCH=${1:-$(git branch --show-current)}

echo "📥 Pulling changes from GitHub..."
echo "Branch: $BRANCH"
echo ""

# Проверяем, есть ли незакоммиченные изменения
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ You have uncommitted changes!"
    echo "   Please commit or stash them first."
    git status
    exit 1
fi

# Пуллим изменения
echo "🔄 Fetching from origin..."
git fetch origin

# Проверяем, есть ли изменения
if [ -n "$(git log HEAD..origin/$BRANCH --oneline)" ]; then
    echo "📥 Pulling changes..."
    git pull origin $BRANCH
    echo "✅ Changes pulled successfully!"
    
    # Показываем последние коммиты
    echo ""
    echo "📜 New commits:"
    git log --oneline -5
else
    echo "✅ No new changes to pull"
fi
EOF

chmod +x /opt/taiger/pull-from-github.sh
```

### 7.2 Скрипт для пуша изменений в GitHub с VPS

```bash
cat > /opt/taiger/push-to-github.sh << 'EOF'
#!/bin/bash
set -e

BRANCH=${1:-$(git branch --show-current)}

echo "📤 Pushing changes to GitHub..."
echo "Branch: $BRANCH"
echo ""

# Проверяем, есть ли изменения для пуша
if [ -z "$(git log origin/$BRANCH..HEAD --oneline)" ]; then
    echo "✅ No changes to push"
    exit 0
fi

# Показываем изменения
echo "📜 Commits to push:"
git log origin/$BRANCH..HEAD --oneline
echo ""

# Запрашиваем подтверждение
read -p "Do you want to push these changes? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Push cancelled"
    exit 1
fi

# Пушим изменения
echo "📤 Pushing to GitHub..."
git push origin $BRANCH
echo "✅ Changes pushed successfully!"
EOF

chmod +x /opt/taiger/push-to-github.sh
```

### 7.3 Скрипт для синхронизации всех веток

```bash
cat > /opt/taiger/sync-with-github.sh << 'EOF'
#!/bin/bash
set -e

echo "🔄 Syncing with GitHub..."
echo ""

# Пуллим все изменения
echo "📥 Fetching from origin..."
git fetch origin --all
echo "✅ Fetched all branches"
echo ""

# Показываем статус веток
echo "📊 Branch status:"
for branch in main develop; do
    echo ""
    echo "🌿 $branch:"
    if [ "$(git branch --show-current)" = "$branch" ]; then
        COMMITS_BEHIND=$(git log HEAD..origin/$branch --oneline | wc -l)
        COMMITS_AHEAD=$(git log origin/$branch..HEAD --oneline | wc -l)
        if [ $COMMITS_BEHIND -gt 0 ]; then
            echo "   ⬇️  $COMMITS_BEHIND commits behind origin/$branch"
        fi
        if [ $COMMITS_AHEAD -gt 0 ]; then
            echo "   ⬆️  $COMMITS_AHEAD commits ahead of origin/$branch"
        fi
        if [ $COMMITS_BEHIND -eq 0 ] && [ $COMMITS_AHEAD -eq 0 ]; then
            echo "   ✅ Up to date with origin/$branch"
        fi
    else
        COMMITS_BEHIND=$(git log $branch..origin/$branch --oneline | wc -l)
        COMMITS_AHEAD=$(git log origin/$branch..$branch --oneline | wc -l)
        if [ $COMMITS_BEHIND -gt 0 ]; then
            echo "   ⬇️  $COMMITS_BEHIND commits behind origin/$branch"
        fi
        if [ $COMMITS_AHEAD -gt 0 ]; then
            echo "   ⬆️  $COMMITS_AHEAD commits ahead of origin/$branch"
        fi
        if [ $COMMITS_BEHIND -eq 0 ] && [ $COMMITS_AHEAD -eq 0 ]; then
            echo "   ✅ Up to date with origin/$branch"
        fi
    fi
done

echo ""
echo "✅ Sync completed!"
EOF

chmod +x /opt/taiger/sync-with-github.sh
```

---

## Шаг 8: Обновлённый рабочий процесс с GitHub

### 8.1 Полный цикл разработки

```powershell
# ========== НА WINDOWS PC ==========

# 1. Пуллим последние изменения
git fetch origin
git checkout develop
git pull origin develop

# 2. Создаём feature ветку
git checkout -b feature/new-feature

# 3. Вносим изменения
# Редактируем файлы в VSCode

# 4. Тестируем локально
# Запускаем backend: python -m uvicorn main:app --reload
# Запускаем frontend: npm run dev

# 5. Коммитим изменения
git add .
git commit -m "Add new feature"

# 6. Пушим в GitHub
git push -u origin feature/new-feature

# ========== НА VPS ==========

# 7. Пуллим изменения с GitHub
cd /opt/taiger
./pull-from-github.sh

# 8. Переключаемся на develop
git checkout develop
git pull origin develop

# 9. Мержим feature ветку
git merge origin/feature/new-feature

# 10. Переключаем продакшен на develop для тестирования
./switch-to-develop.sh

# 11. Тестируем на https://taiger.pro

# 12. Если всё работает - деплоим на прод
./deploy-to-production.sh

# 13. Пушим изменения в GitHub
./push-to-github.sh

# 14. Удаляем feature ветку
git branch -d feature/new-feature
git push origin --delete feature/new-feature
```

---

## Шаг 9: Резервное копирование в GitHub

### 9.1 Автоматический пуш тегов в GitHub

Добавьте в скрипт `backup.sh`:

```bash
# В конце backup.sh добавьте:
echo "📤 Pushing backup tag to GitHub..."
git push origin $TAG
echo "✅ Backup tag pushed to GitHub"
```

### 9.2 Скрипт для создания бэкапа в GitHub

```bash
cat > /opt/taiger/backup-to-github.sh << 'EOF'
#!/bin/bash

echo "💾 Creating backup to GitHub..."
echo ""

# Создаём тег
TAG="backup-$(date +%Y%m%d-%H%M%S)"
git tag $TAG

# Пушим тег в GitHub
git push origin $TAG

echo "✅ Backup created: $TAG"
echo "📤 Pushed to GitHub"
EOF

chmod +x /opt/taiger/backup-to-github.sh
```

---

## Шаг 10: Устранение неполадок

### 10.1 Проблема: Git не может подключиться к GitHub

```bash
# Проверьте SSH подключение
ssh -T git@github.com

# Если не работает, проверьте SSH ключи
ls -la ~/.ssh/

# Добавьте ключ в ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### 10.2 Проблема: Конфликт при merge

```bash
# Разрешите конфликты вручную
git status

# Откройте файлы с конфликтами и исправьте их
# Затем:
git add .
git commit -m "Resolved merge conflicts"
```

### 10.3 Проблема: Отстающая ветка

```bash
# Пуллим изменения
git pull origin develop

# Или перебазируем
git fetch origin
git rebase origin/develop
```

---

## Преимущества интеграции с GitHub

### ✅ Преимущества:

1. **Резервная копия кода** - весь код хранится в GitHub
2. **Удобная разработка на Windows** - работаете локально, синхронизируете с VPS
3. **История изменений** - полная история коммитов в GitHub
4. **Pull Requests** - возможность код-ревью и обсуждения изменений
5. **Issues** - управление задачами и багами
6. **GitHub Actions** - автоматизация тестирования и деплоя
7. **Коллаборация** - возможность работать в команде
8. **Восстановление** - можно восстановить код из GitHub при проблемах

### ⚠️ Недостатки:

1. **Требует настройки** - нужно настроить SSH ключи и GitHub
2. **Интернет** - нужен доступ к интернету для синхронизации
3. **Приватность** - для приватного проекта нужен платный аккаунт (или Private репозиторий бесплатный)

---

## Проверочный чеклист

После настройки интеграции с GitHub проверьте:

- [ ] GitHub репозиторий создан
- [ ] SSH ключи добавлены в GitHub (для Windows и VPS)
- [ ] Удалённый репозиторий добавлен (`git remote add origin`)
- [ ] Ветки `main` и `develop` запушены в GitHub
- [ ] Локальное окружение на Windows настроено
- [ ] Локальный запуск backend работает
- [ ] Локальный запуск frontend работает
- [ ] Скрипты синхронизации созданы (`pull-from-github.sh`, `push-to-github.sh`)
- [ ] Скрипт `sync-with-github.sh` работает
- [ ] Полный цикл разработки работает (Windows → GitHub → VPS)

---

## Заключение

Интеграция с GitHub добавляет следующие возможности к вашей стратегии деплоя:

1. ✅ **Удобная локальная разработка** - работаете на Windows, синхронизируете с VPS
2. ✅ **Резервная копия в облаке** - весь код хранится в GitHub
3. ✅ **История изменений** - полная история коммитов и тегов
4. ✅ **Pull Requests** - возможность код-ревью
5. ✅ **GitHub Actions** - автоматизация CI/CD (опционально)

Теперь у вас есть полноценная система разработки с GitHub!
