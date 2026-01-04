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