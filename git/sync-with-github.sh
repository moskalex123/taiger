#!/bin/bash
set -e

echo "🔄 Syncing with GitHub..."
echo ""

# Пуллим все изменения
echo "📥 Fetching from origin..."
git fetch origin
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