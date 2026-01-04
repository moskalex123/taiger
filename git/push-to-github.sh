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