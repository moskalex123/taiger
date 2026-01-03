# План локализации воркера (v2)

Этот план предназначен для модели `grok-code-fast-1`. Задача — исправить проблему, при которой воркер игнорирует настройки языка пользователя (пишет на русском при выбранном `en`) и окончательно перевести все уведомления на систему `UnifiedMessenger` с поддержкой локализации.

## 🔍 Причины неудач предыдущих попыток
1. **Хардкод в `worker_manager.py`**: Функции `stop_worker` и `notify_worker_stopping` используют прямые строки на русском языке, игнорируя `language_code` пользователя.
2. **Отсутствие передачи `lang`**: Функция `get_localized_message` в `utils.py` имеет параметр `lang`, но во многих местах он не передается или передается некорректно.
3. **Разрыв контекста**: `worker_manager.py` работает "снаружи" процесса воркера и не всегда имеет доступ к инстансу воркера, который знает язык пользователя.

## 🎯 Цели
1. Добавить все недостающие строки в `get_localized_message`.
2. Исправить `worker_manager.py`, чтобы он учитывал язык пользователя из БД.
3. Перевести `worker_manager.py` на использование ключей локализации.

## 🛠 Шаги реализации

### 1. Обновление словаря в `telegram_worker/utils.py`
Добавить ключи для уведомлений об остановке.

```python
# grace: telegram_worker/utils.py
<<<<<<< SEARCH
        "start_failed_no_connection": "Не удалось запустить: нет подключения",
        "insufficient_funds_error": "Stopping worker due to insufficient funds"
    }
=======
        "start_failed_no_connection": "Не удалось запустить: нет подключения",
        "insufficient_funds_error": "Stopping worker due to insufficient funds",
        "worker_stopping_manual": "⛔️ Агент останавливается: остановка по запросу пользователя",
        "worker_stopped_final": "🟥 Агент остановлен."
    }
>>>>>>> REPLACE
```
*Примечание: В `messages` внутри `get_localized_message` нужно добавить английские версии или логику выбора.*

### 2. Исправление `worker_manager.py`
Нужно научить функции `stop_worker` и `notify_worker_stopping` определять язык пользователя.

```python
# grace: worker_manager.py
<<<<<<< SEARCH
async def notify_worker_stopping(user_id: int, reason: str) -> None:
    """Send a bot notification that the worker is about to stop."""
    try:
        from telegram_worker.user_logger import get_user_logger  # Local import to avoid cycles

        user_logger = get_user_logger(user_id)
        message = f"⛔️ Агент останавливается: {reason}"
        await user_logger.send_status_update(message, "warning")
=======
async def notify_worker_stopping(user_id: int, key: str = "worker_stopping_manual") -> None:
    """Send a bot notification that the worker is about to stop."""
    try:
        from telegram_worker.unified_messenger import get_unified_messenger, MessageRole
        from telegram_worker.utils import get_localized_message
        from db import async_session
        from models import User

        # Получаем язык пользователя напрямую из БД
        lang = 'en'
        async with async_session() as session:
            user = await session.get(User, user_id)
            if user and user.language_code:
                lang = user.language_code

        messenger = get_unified_messenger(user_id)
        message = get_localized_message(key, lang=lang)
        await messenger.send_report(message, "warning")
>>>>>>> REPLACE
```

### 3. Обновление `stop_worker` в `worker_manager.py`
```python
# grace: worker_manager.py
<<<<<<< SEARCH
    # Send final status message after successful stop
    if stop_result:
        try:
            from telegram_worker.user_logger import get_user_logger
            user_logger = get_user_logger(user_id)
            await user_logger.send_status_update("🟥 Агент остановлен.", "success")
=======
    # Send final status message after successful stop
    if stop_result:
        try:
            from telegram_worker.unified_messenger import get_unified_messenger
            from telegram_worker.utils import get_localized_message
            from db import async_session
            from models import User

            lang = 'en'
            async with async_session() as session:
                user = await session.get(User, user_id)
                if user and user.language_code:
                    lang = user.language_code

            messenger = get_unified_messenger(user_id)
            message = get_localized_message("worker_stopped_final", lang=lang)
            await messenger.send_report(message, "success")
>>>>>>> REPLACE
```

## 🧪 Верификация
1. Установить пользователю `language_code = 'en'` в БД.
2. Вызвать остановку воркера.
3. Убедиться, что в Telegram пришло сообщение "Worker stopped." (или аналогичное на английском), а не "Агент остановлен".

## ⚠️ Важное замечание для Coder-модели
В `telegram_worker/utils.py` функция `get_localized_message` сейчас содержит только русский хардкод в словаре `messages`. Необходимо расширить этот словарь, чтобы он поддерживал вложенность или имел префиксы для языков, либо загружал данные из JSON файлов локализации.
