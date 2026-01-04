# План локализации воркера (v3)

Этот план предназначен для модели `grok-code-fast-1`. Задача — завершить локализацию всех захардкоженных сообщений в воркере и убедиться, что логи в TMA тоже локализованы.

## 🔍 Причины необходимости нового плана

1. **Незавершенная локализация**: В предыдущих планах были заменены не все места использования `get_localized_message` на `messenger.send`.
2. **Логи в TMA**: Нужно убедиться, что все логи, отправляемые в TMA (Telegram Mini App), тоже локализованы.
3. **Остаточные хардкоды**: Некоторые сообщения все еще захардкожены в коде.

## 🎯 Цели

1. Заменить все оставшиеся `get_localized_message` на `messenger.send` с соответствующими ключами.
2. Убедиться, что все логи в TMA локализованы.
3. Проверить, что нет захардкоженных сообщений.

## 🛠 Шаги реализации

### 1. Замена в `telegram_worker/message_processor.py`

Все места использования `get_localized_message` заменить на `messenger.send`:

- `user_not_found` → `messenger.send("user_not_found", MessageRole.USER_REPORT, report_type="error")`
- `processing_album_status` → `messenger.send("processing_album_status", MessageRole.USER_STATUS, album_id=message.media_group_id)`
- `processing_text` → `messenger.send("processing_text", MessageRole.USER_STATUS)`
- `text_processing_error` → `messenger.send("text_processing_error", MessageRole.USER_REPORT, report_type="error", error=str(e))`
- `target_channel_not_found` → `messenger.send("target_channel_not_found", MessageRole.USER_REPORT, report_type="error", channel=rule.target_channel)`
- `calculating_schedule` → `messenger.send("calculating_schedule", MessageRole.USER_STATUS)`
- `schedule_calculation_error` → `messenger.send("schedule_calculation_error", MessageRole.USER_REPORT, report_type="error", error=str(e))`
- `scheduling_message_status` → `messenger.send("scheduling_message_status", MessageRole.USER_STATUS, time=scheduled_time.strftime('%H:%M'))`
- `scheduling_failed` → `messenger.send("scheduling_failed", MessageRole.USER_REPORT, report_type="error", detailed_error=detailed_error)`
- `scheduling_error` → `messenger.send("scheduling_error", MessageRole.USER_REPORT, report_type="error", error=str(e), detailed_error=detailed_error)`
- `ai_error_empty` → `messenger.send("ai_error_empty", MessageRole.USER_REPORT, report_type="warning")`

### 2. Замена в `telegram_worker/hybrid_processor.py`

Все места использования `get_localized_message` заменить на `messenger.send`:

- `client_not_ready` → `messenger.send("client_not_ready", MessageRole.INTERNAL_LOG, level="error")`
- `batch_disabled` → `messenger.send("batch_disabled", MessageRole.INTERNAL_LOG, level="info")`
- `listening_skipped` → `messenger.send("listening_skipped", MessageRole.INTERNAL_LOG, level="info")`
- `batch_start` → `messenger.send("batch_start", MessageRole.INTERNAL_LOG, level="info")`
- `batch_complete` → `messenger.send("batch_complete", MessageRole.INTERNAL_LOG, level="success", processed=processed_count)`
- `switching_to_listening` → `messenger.send("switching_to_listening", MessageRole.USER_STATUS)`
- `listening_skipped_status` → `messenger.send("listening_skipped_status", MessageRole.USER_STATUS)`
- `hybrid_error` → `messenger.send("hybrid_error", MessageRole.INTERNAL_LOG, level="error", error=str(e))`
- `no_rules` → `messenger.send("no_rules", MessageRole.INTERNAL_LOG, level="info")`
- `processing_rules` → `messenger.send("processing_rules", MessageRole.INTERNAL_LOG, level="info", rules_count=len(channel_pairs))`
- `rule_processed` → `messenger.send("rule_processed", MessageRole.INTERNAL_LOG, level="success", rule_index=i+1, posts_count=posts_count)`
- `rule_no_posts` → `messenger.send("rule_no_posts", MessageRole.INTERNAL_LOG, level="info", rule_index=i+1)`
- `rule_error` → `messenger.send("rule_error", MessageRole.INTERNAL_LOG, level="error", rule_index=i+1, error=str(e))`
- `client_not_connected` → `messenger.send("client_not_connected", MessageRole.INTERNAL_LOG, level="error", rule_id=channel_pair.id)`
- `channel_not_ready` → `messenger.send("channel_not_ready", MessageRole.INTERNAL_LOG, level="warning", channel=source_channel)`
- `channel_access_error` → `messenger.send("channel_access_error", MessageRole.INTERNAL_LOG, level="error", channel=source_channel, error=str(e))`
- `no_new_messages` → `messenger.send("no_new_messages", MessageRole.INTERNAL_LOG, level="info", channel=source_channel, last_id=last_processed_id)`
- `found_new_messages` → `messenger.send("found_new_messages", MessageRole.INTERNAL_LOG, level="info", messages_count=len(new_messages), channel=source_channel)`
- `get_messages_error` → `messenger.send("get_messages_error", MessageRole.INTERNAL_LOG, level="error", channel=source_channel, error=str(e))`
- `album_processing_error` → `messenger.send("album_processing_error", MessageRole.INTERNAL_LOG, level="error", album_id=media_group_id, error=str(e))`
- `message_processing_error` → `messenger.send("message_processing_error", MessageRole.INTERNAL_LOG, level="error", message_id=message.id, error=str(e))`
- `batch_processing_error` → `messenger.send("batch_processing_error", MessageRole.INTERNAL_LOG, level="error", error=str(e))`
- `client_not_ready_listening` → `messenger.send("client_not_ready_listening", MessageRole.USER_REPORT, report_type="error")`

### 3. Замена в `telegram_worker/worker.py`

Все места использования `get_localized_message` заменить на `messenger.send`:

- `session_found_s3` → `messenger.send("session_found_s3", MessageRole.INTERNAL_LOG, level="info")`
- `loading_rules_db` → `messenger.send("loading_rules_db", MessageRole.INTERNAL_LOG, level="info")`
- `rules_loading_error` → `messenger.send("rules_loading_error", MessageRole.USER_REPORT, report_type="error", error=str(e))`
- `listening_started` → просто лог, не нужно менять
- `agent_waiting_status` → `messenger.send("agent_waiting_status", MessageRole.INTERNAL_LOG, level="info")`
- `start_failed_no_connection` → `messenger.send("start_failed_no_connection", MessageRole.USER_REPORT, report_type="error")`

### 4. Проверка локализации в TMA

Убедиться, что все логи, отправляемые через WebSocket в TMA, тоже локализованы. Проверить:

- `_log_worker_status` - должен использовать локализованные ключи
- `_send_websocket_log` - должен использовать локализованные сообщения
- Все статусы и отчеты должны проходить через `messenger.send`

### 5. Добавление недостающих ключей локализации

В `telegram_worker/utils.py` добавить недостающие ключи:

```python
"client_not_ready": {
    "ru": "Клиент не готов к обработке",
    "en": "Client not ready for processing"
},
"batch_disabled": {
    "ru": "Пакетная обработка отключена",
    "en": "Batch processing disabled"
},
"listening_skipped": {
    "ru": "Прослушивание пропущено",
    "en": "Listening skipped"
},
"batch_start": {
    "ru": "Начало пакетной обработки",
    "en": "Batch processing started"
},
"batch_complete": {
    "ru": "Пакетная обработка завершена",
    "en": "Batch processing completed"
},
"switching_to_listening": {
    "ru": "Переход в режим прослушивания",
    "en": "Switching to listening mode"
},
"listening_skipped_status": {
    "ru": "Прослушивание пропущено",
    "en": "Listening skipped"
},
"hybrid_error": {
    "ru": "Ошибка гибридной обработки",
    "en": "Hybrid processing error"
},
"no_rules": {
    "ru": "Правила не найдены",
    "en": "No rules found"
},
"processing_rules": {
    "ru": "Обработка правил",
    "en": "Processing rules"
},
"rule_processed": {
    "ru": "Правило обработано",
    "en": "Rule processed"
},
"rule_no_posts": {
    "ru": "Правило без постов",
    "en": "Rule with no posts"
},
"rule_error": {
    "ru": "Ошибка правила",
    "en": "Rule error"
},
"client_not_connected": {
    "ru": "Клиент не подключен",
    "en": "Client not connected"
},
"channel_not_ready": {
    "ru": "Канал не готов",
    "en": "Channel not ready"
},
"channel_access_error": {
    "ru": "Ошибка доступа к каналу",
    "en": "Channel access error"
},
"no_new_messages": {
    "ru": "Новых сообщений нет",
    "en": "No new messages"
},
"found_new_messages": {
    "ru": "Найдены новые сообщения",
    "en": "Found new messages"
},
"get_messages_error": {
    "ru": "Ошибка получения сообщений",
    "en": "Get messages error"
},
"album_processing_error": {
    "ru": "Ошибка обработки альбома",
    "en": "Album processing error"
},
"message_processing_error": {
    "ru": "Ошибка обработки сообщения",
    "en": "Message processing error"
},
"batch_processing_error": {
    "ru": "Ошибка пакетной обработки",
    "en": "Batch processing error"
},
"client_not_ready_listening": {
    "ru": "Клиент не готов к прослушиванию",
    "en": "Client not ready for listening"
},
"session_found_s3": {
    "ru": "Сессия найдена в S3",
    "en": "Session found in S3"
},
"loading_rules_db": {
    "ru": "Загрузка правил из БД",
    "en": "Loading rules from database"
},
"rules_loading_error": {
    "ru": "Ошибка загрузки правил",
    "en": "Rules loading error"
},
"listening_started": {
    "ru": "Прослушивание начато",
    "en": "Listening started"
},
"agent_waiting_status": {
    "ru": "Агент ожидает сообщений",
    "en": "Agent waiting for messages"
},
"start_failed_no_connection": {
    "ru": "Не удалось запустить: нет подключения",
    "en": "Start failed: no connection"
}
```

## 🧪 Верификация

1. Установить пользователю `language_code = 'en'` в БД.
2. Запустить воркер и проверить все логи в TMA - должны быть на английском.
3. Проверить все уведомления в Telegram - должны быть на английском.
4. Проверить логи в консоли - должны быть на английском.

## ⚠️ Важное замечание

- Все логи в TMA должны проходить через `messenger.send` с соответствующими ключами.
- Нужно убедиться, что `MessageRole.INTERNAL_LOG` используется для логов, а `MessageRole.USER_REPORT` для уведомлений пользователю.
- Все параметры должны передаваться правильно в `messenger.send`.</content>
</xai:function_call"> 

<xai:function_call name="apply_diff">
<parameter name="path">telegram_worker/utils.py