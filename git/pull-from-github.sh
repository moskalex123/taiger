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