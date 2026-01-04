# API Документация

## Основные endpoints

### Авторизация
- `POST /auth/login` - Вход через Telegram
- `POST /auth/logout` - Выход
- `POST /auth/request_telegram_code` - Запрос кода подтверждения
- `POST /auth/submit_code` - Подтверждение кода

### Пользователи
- `GET /api/users/me` - Текущий пользователь
- `PUT /api/users/me` - Обновление профиля

### Сессии
- `GET /api/sessions` - Список сессий
- `POST /api/sessions` - Создание сессии
- `DELETE /api/sessions/{id}` - Удаление сессии

### Воркеры
- `POST /api/workers/start` - Запуск воркера
- `POST /api/workers/stop` - Остановка воркера
- `GET /api/workers/status` - Статус воркера
- `GET /api/workers/logs` - Логи воркера

### Каналы
- `GET /api/channel_pairs` - Список правил обработки
- `POST /api/channel_pairs` - Создание правила
- `PUT /api/channel_pairs/{id}` - Обновление правила
- `DELETE /api/channel_pairs/{id}` - Удаление правила

### Очередь
- `GET /api/queue/info` - Информация об очереди
- `GET /api/queue/service-status` - Статус сервиса

### WebSocket
- `WS /api/ws/{user_id}` - WebSocket для логов в реальном времени

## Документация API

Интерактивная документация доступна по адресу:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Аутентификация

Большинство endpoints требуют JWT токен в заголовке:
```
Authorization: Bearer <token>
```

Токен получается при авторизации через `/auth/login`.

