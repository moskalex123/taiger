# План локализации сообщений Telegram-воркера

Этот план предназначен для младшей coder-модели. Задача — перенести все текстовые сообщения из кода воркера в централизованный словарь локализации в `telegram_worker/utils.py`.

## 🎯 Цель
Заменить все "хардкод" строки в вызовах `send_status`, `send_report` и `_log_worker_status` на ключи локализации, используя функцию `get_localized_message`.

## 🛠 Инструменты
- **Файл со словарём:** [`telegram_worker/utils.py`](telegram_worker/utils.py)
- **Функция локализации:** `get_localized_message(key, **kwargs)`
- **Методы для замены:**
  - `self.user_logger.send_status("текст")`
  - `self.user_logger.send_report("текст", "тип")`
  - `self._log_worker_status("key", "текст", "level")`

---

## 📋 Шаги выполнения

### 1. Подготовка словаря в `telegram_worker/utils.py`
Нужно добавить недостающие ключи в словарь `messages` внутри функции `get_localized_message`.

**Пример добавления ключа:**
<<<<<<< SEARCH
:start_line:120
-------
        "session_download": "📥 Загрузка сессии из S3..."
    }
=======
        "session_download": "📥 Загрузка сессии из S3...",
        "paused_status": "⏸️ Обработка приостановлена",
        "calculating_schedule": "⏰ Расчёт времени публикации...",
        "ai_error_empty": "Ошибка ИИ: пустой ответ от сервиса",
        "channel_access_denied": "Нет доступа к каналу {channel}: {error}"
    }
>>>>>>> REPLACE

### 2. Замена строк в коде воркера
Заменяйте прямые строки на вызовы функции. Если в строке есть переменные, передавайте их как именованные аргументы.

#### Шаблон замены для `send_status` и `send_report`:
**Было:**
```python
await self.user_logger.send_status("📝 Обработка текста...")
```
**Стало:**
```python
await self.user_logger.send_status(get_localized_message("processing_text"))
```

#### Шаблон замены для `_log_worker_status`:
**Было:**
```python
await self._log_worker_status("insufficient_funds", "Stopping worker due to insufficient funds", "error")
```
**Стало:**
```python
await self._log_worker_status("insufficient_funds", get_localized_message("insufficient_funds_error"), "error")
```

---

## 📝 Список найденных строк для локализации

### `telegram_worker/message_processor.py`
- [ ] `"⏸️ Обработка приостановлена"` -> `paused_status`
- [ ] `"📝 Обработка текста..."` -> `processing_text`
- [ ] `"⏰ Расчёт времени публикации..."` -> `calculating_schedule`
- [ ] `"Пользователь не найден в базе данных"` -> `user_not_found`
- [ ] `"Ошибка ИИ: пустой ответ от сервиса"` -> `ai_error_empty`

### `telegram_worker/hybrid_processor.py`
- [ ] `"Переход к режиму прослушивания..."` -> `switching_to_listening`
- [ ] `"⏸ Режим прослушивания пропущен"` -> `listening_skipped_status`
- [ ] `"Нет доступа к каналу {source_channel}: {str(e)}"` -> `channel_access_denied` (аргументы: `channel`, `error`)
- [ ] `"Ошибка чтения {source_channel}: {str(e)}"` -> `channel_read_error`
- [ ] `"Ошибка обработки альбома {media_group_id}: {str(e)}"` -> `album_error`
- [ ] `"Telegram клиент не готов к прослушиванию"` -> `client_not_ready_listening`

### `telegram_worker/worker.py`
- [ ] `"📥 Session found in S3, downloading..."` -> `session_found_s3`
- [ ] `"📋 Loading channel rules from database..."` -> `loading_rules_db`
- [ ] `"Не удалось запустить: нет подключения"` -> `start_failed_no_connection`

---

## ⚠️ Важные правила (Grace Markup)
При редактировании файлов используйте точные блоки поиска и замены.

[`telegram_worker/message_processor.py`](telegram_worker/message_processor.py:143)
<<<<<<< SEARCH
:start_line:143
-------
                await self.user_logger.send_status("⏸️ Обработка приостановлена")
=======
                await self.user_logger.send_status(get_localized_message("paused_status"))
>>>>>>> REPLACE

[`telegram_worker/hybrid_processor.py`](telegram_worker/hybrid_processor.py:237)
<<<<<<< SEARCH
:start_line:237
-------
                await self.user_logger.send_report(f"Нет доступа к каналу {source_channel}: {str(e)}", "error")
=======
                await self.user_logger.send_report(get_localized_message("channel_access_denied", channel=source_channel, error=str(e)), "error")
>>>>>>> REPLACE

## 🧪 Как проверять
1. Запустить воркер.
2. Убедиться, что в логах бота и консоли сообщения приходят на русском языке (как определено в `utils.py`).
3. Проверить, что переменные (например, названия каналов или ошибки) корректно подставляются в текст.
