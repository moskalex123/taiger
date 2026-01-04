# Taiger - Система автоматической обработки Telegram-постов с ИИ

Серверное приложение для управления Telegram-воркерами через веб-интерфейс и Telegram Mini App (TMA).

## 🚀 Быстрый старт

```bash
# Установка зависимостей
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Настройка окружения
cp .env.example .env
# Отредактируйте .env файл

# Запуск
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

## 📚 Документация

Полная документация находится в папке [docs/](docs/README.md):

- [Установка и настройка](docs/setup/README.md)
- [Руководства](docs/guides/README.md)
- [API документация](docs/api/README.md)
- [Разработка](docs/development/README.md)

## 🎯 Режимы работы

### 1. Основной режим (TMA)
Полноценная работа с телеграм-сессиями пользователей через Telegram Mini App:
- Настройка правил ИИ-обработки постов
- Управление каналами-источниками и каналами-приёмниками
- Планирование интервалов публикации

### 2. Промо-режим (в боте)
Бесплатная обработка всех входящих постов через модели ИИ.

## 🛠 Технологии

- **Backend**: FastAPI (Python 3), SQLAlchemy, Pyrogram
- **Frontend**: Vue 3 + TypeScript, Vite
- **База данных**: PostgreSQL
- **Кэш**: Redis
- **Хранилище**: Yandex Object Storage
- **ИИ**: OpenRouter API, Hyperbolic API

## 📝 Важные файлы

- [README_for_AI.md](README_for_AI.md) - Инструкции для AI-ассистентов
- [requirements.txt](requirements.txt) - Python зависимости
- [.env](.env) - Переменные окружения (не в репозитории)

## 🔗 Полезные ссылки

- [Документация FastAPI](https://fastapi.tiangolo.com/)
- [Документация Pyrogram](https://docs.pyrogram.org/)
- [Документация Vue 3](https://vuejs.org/)

---

*Последнее обновление: 2024*
