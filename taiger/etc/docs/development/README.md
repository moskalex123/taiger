# Разработка

Этот раздел содержит информацию для разработчиков проекта.

## Содержание

1. [Настройка окружения разработки](DEVELOPMENT_SETUP.md) - Настройка для разработки
2. [Тестирование](TESTING.md) - Инструкции по тестированию
3. [Архитектура проекта](ARCHITECTURE.md) - Обзор архитектуры

## Быстрый старт для разработчиков

### Требования

- Python 3.11+
- Node.js 24+ (см. [.nvmrc](../../.nvmrc) / [.node-version](../../.node-version))

```bash
# Клонировать репозиторий
git clone <repository-url>
cd taiger

# Установить зависимости
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Настроить .env
cp .env.example .env
# Отредактировать .env

# Запустить в режиме разработки
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Полезные команды

```bash
# Запуск бэкенда
cd /opt/taiger && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000

# Запуск фронтенда
cd /opt/taiger/frontend && npm run dev

# Остановка бэкенда
kill -9 $(lsof -t -i:8000) 2>/dev/null || echo "No processes found on port 8000"
```

## Стандарты кода

- Python: PEP 8
- TypeScript: ESLint конфигурация
- Коммиты: Conventional Commits
