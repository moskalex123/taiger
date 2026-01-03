#!/bin/bash
# Скрипт для сборки фронтенда с автоматическим исправлением прав доступа

set -e

echo "🔨 Запуск сборки фронтенда..."
npm run build

echo "🔧 Исправление прав доступа..."
sudo chown -R www-data:www-data dist/

echo "✅ Сборка завершена успешно!"
echo "📁 Файлы в dist/ принадлежат www-data:www-data"

