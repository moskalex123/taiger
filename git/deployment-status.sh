#!/bin/bash
set -e

echo "📊 Deployment Status Report"
echo "============================"
echo ""

# Проверяем текущую ветку
CURRENT_BRANCH=$(git branch --show-current)
echo "🌿 Current branch: $CURRENT_BRANCH"
echo ""

# Проверяем статус веток
echo "📊 Branch Status:"
echo "----------------"
for branch in main develop; do
    echo ""
    echo "🌿 $branch:"
    if [ "$branch" = "$CURRENT_BRANCH" ]; then
        echo "   📍 Currently active"
    fi
    
    # Проверяем коммиты
    LOCAL_COMMIT=$(git rev-parse $branch 2>/dev/null || echo "N/A")
    REMOTE_COMMIT=$(git rev-parse origin/$branch 2>/dev/null || echo "N/A")
    
    if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
        echo "   ✅ Local and remote are in sync"
    else
        echo "   ⚠️  Local and remote are out of sync"
        echo "      Local:  $LOCAL_COMMIT"
        echo "      Remote: $REMOTE_COMMIT"
    fi
    
    # Проверяем коммиты вперед/назад
    COMMITS_BEHIND=$(git log $branch..origin/$branch --oneline 2>/dev/null | wc -l)
    COMMITS_AHEAD=$(git log origin/$branch..$branch --oneline 2>/dev/null | wc -l)
    
    if [ $COMMITS_BEHIND -gt 0 ]; then
        echo "   ⬇️  $COMMITS_BEHIND commits behind origin/$branch"
    fi
    if [ $COMMITS_AHEAD -gt 0 ]; then
        echo "   ⬆️  $COMMITS_AHEAD commits ahead of origin/$branch"
    fi
done

echo ""
echo "🔄 Service Status:"
echo "------------------"
# Проверяем статус сервисов
if systemctl is-active --quiet taiger-api; then
    echo "✅ taiger-api: Running"
else
    echo "❌ taiger-api: Not running"
fi

if systemctl is-active --quiet taiger-worker; then
    echo "✅ taiger-worker: Running"
else
    echo "❌ taiger-worker: Not running"
fi

echo ""
echo "📁 Last 5 commits on current branch:"
echo "------------------------------------"
git log --oneline -5

echo ""
echo "✅ Status check completed!"