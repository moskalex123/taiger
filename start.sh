#!/bin/bash

# Скрипт запуска приложения в Docker контейнере

set -e

echo "Запуск приложения Taiger..."

# Инициализация базы данных
echo "Инициализация базы данных..."
python3 init_db.py

if [ $? -ne 0 ]; then
    echo "Ошибка инициализации базы данных"
    exit 1
fi

# Создание необходимых директорий
mkdir -p /app/logs
mkdir -p /app/sessions

# Запуск основного приложения
echo "Запуск основного приложения..."
exec python3 main.py