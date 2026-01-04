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