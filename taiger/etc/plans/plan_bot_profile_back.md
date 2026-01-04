# План исправления ошибки при переходе Назад из Профиля

## Описание проблемы
При нажатии кнопки **Профиль** в главном меню, а затем кнопки **Назад** (callback_data: `main_menu`), бот выдает ошибку:
`ERROR:telegram_bot.handlers:Error in callback query handler: Single '}' encountered in format string`

## Причина ошибки
Ошибка возникает в файле [`telegram_bot/handlers.py`](telegram_bot/handlers.py:427) внутри `callback_query_handler` при обработке `data == "main_menu"`.
Метод `MessageTemplates.welcome_existing_user` использует `I18n.get`, который в свою очередь вызывает `.format(**kwargs)` для строки из локализации.

В файле [`locales/ru.json`](locales/ru.json:29) (и `en.json`) строка `welcome_back` содержит:
`... Воркер: <code>{worker_status}</code}{recent_activity} ...`

Здесь `</code}{recent_activity}` содержит одиночную закрывающую фигурную скобку `}` перед `{recent_activity}`, что ломает парсер `.format()`.

## План действий

1.  **Исправить файлы локализации**
    Необходимо исправить опечатку в `locales/ru.json` и `locales/en.json`, удалив лишнюю закрывающую скобку.

    **Образец (ru.json):**
    ```json
    "welcome_back": "👋 <b>Добро пожаловать обратно!</b>\n\n💰 Баланс: <code>{balance:.1f}</code>🔋\n{status_emoji} Воркер: <code>{worker_status}</code>{recent_activity}\n\n🤖 <b>Бот ожидает текст для обработки</b>"
    ```

2.  **Улучшить обработку ошибок в I18n**
    Добавить проверку в [`telegram_bot/i18n.py`](telegram_bot/i18n.py:21), чтобы ошибки форматирования не приводили к падению всего хендлера.

    **Образец кода:**
    ```python
    try:
        return val.format(**kwargs) if isinstance(val, str) else val
    except (KeyError, ValueError) as e:
        logger.error(f"I18n format error for key {key}: {e}")
        return val # Возвращаем сырую строку, если форматирование не удалось
    ```

3.  **Проверить логику `callback_query_handler`**
    Убедиться, что при `data == "main_menu"` переменная `message` и `keyboard` корректно устанавливаются и используются в конце функции для `query.edit_message_text`.

    **Образец логики (handlers.py):**
    ```python
    if data == "main_menu":
        # ... получение данных пользователя ...
        message = MessageTemplates.welcome_existing_user(balance, worker_status, recent_logs, lang)
        keyboard = BotKeyboards.main_menu(telegram_id)
    # ...
    await query.edit_message_text(text=message, reply_markup=keyboard, parse_mode="HTML")
    ```

## Схема взаимодействия (Mermaid)

```mermaid
graph TD
    A[Пользователь] -->|Нажимает Профиль| B(Bot)
    B -->|Показывает Профиль| A
    A -->|Нажимает Назад| C{Callback: main_menu}
    C --> D[MessageTemplates.welcome_existing_user]
    D --> E[I18n.get]
    E --> F[locales/ru.json: welcome_back]
    F -->|Ошибка: Single '}'| G[Exception]
    G --> H[Бот пишет: Something went wrong]
```

## Ожидаемый результат
После исправления опечатки в JSON, переход "Назад" будет корректно отображать главное меню с балансом и статусом воркера без ошибок.
