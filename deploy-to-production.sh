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