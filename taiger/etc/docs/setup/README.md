# Установка и настройка

Этот раздел содержит руководства по установке и настройке проекта Taiger.

## Содержание

1. [Локальная разработка](LOCAL_SETUP.md) - Настройка локального окружения для разработки
2. [Конфигурация](CONFIGURATION.md) - Настройка переменных окружения
3. [VPS Setup](VPS_SETUP.md) - Настройка на VPS сервере
4. [Устранение неполадок](TROUBLESHOOTING.md) - Решение типичных проблем

## Быстрый старт

### Требования

- Python 3.11+
- Node.js 24+ (для фронтенда)
- PostgreSQL 14+
- Redis 6+
- Telegram API credentials (API_ID, API_HASH)

> В репозитории есть файлы [.nvmrc](../../.nvmrc) и [.node-version](../../.node-version) — можно быстро переключить версию Node через nvm/asdf.

### Установка

```bash
# Клонировать репозиторий
git clone <repository-url>
cd taiger

# Установить Python зависимости
pip install -r requirements.txt

# Установить Frontend зависимости
cd frontend
npm install
cd ..

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env файл

# Инициализировать базу данных
alembic upgrade head

# Запустить приложение
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Следующие шаги

После установки:
1. Настройте [конфигурацию](CONFIGURATION.md)
2. Изучите [руководства](../guides/README.md)
3. Начните [разработку](../development/README.md)
