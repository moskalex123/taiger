"""
Утилитарные функции для Telegram Worker
"""
import os
from typing import Optional


def format_signature(caption_text: Optional[str], caption_url: Optional[str]) -> str:
    if not caption_text and not caption_url:
        return ""

    if caption_text and caption_url:
        return f'<a href="{caption_url}">{caption_text}</a>'
    elif caption_text:
        return caption_text
    else:
        return f'<a href="{caption_url}">{caption_url}</a>'


def get_api_base_url():
    """Get the API base URL from environment or default to localhost"""
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8000")
    return f"http://{api_host}:{api_port}"


def smart_truncate_message(text: str, max_length: int = 1000, logger=None) -> str:
    """
    Умная обрезка текста с сохранением целостности предложений.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина (по умолчанию 1000 символов для Telegram)
        logger: Логгер для записи информации об обрезке
    
    Returns:
        Обрезанный текст
    """
    if not text or len(text) <= max_length:
        return text
    
    # Обрезаем с запасом для "..."
    truncated = text[:max_length - 3]
    
    # Ищем последнюю точку, восклицательный или вопросительный знак
    sentence_endings = ['.', '!', '?', '…']
    last_sentence_end = -1
    
    for ending in sentence_endings:
        pos = truncated.rfind(ending)
        if pos > last_sentence_end:
            last_sentence_end = pos
    
    # Если нашли границу предложения и она не слишком близко к началу
    if last_sentence_end > max_length * 0.7:
        result = truncated[:last_sentence_end + 1]
        if logger:
            logger.info(f"📝 Text truncated at sentence boundary: {len(text)} -> {len(result)} chars")
        return result
    else:
        # Ищем последний пробел, чтобы не разрывать слова
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.5:  # Если пробел не слишком близко к началу
            result = truncated[:last_space] + "..."
            if logger:
                logger.info(f"✂️ Text truncated at word boundary: {len(text)} -> {len(result)} chars")
            return result
        else:
            # В крайнем случае просто обрезаем и добавляем "..."
            result = truncated + "..."
            if logger:
                logger.warning(f"⚠️ Text truncated forcefully: {len(text)} -> {len(result)} chars")
            return result


def split_long_message(text: str, max_length: int = 1000, logger=None) -> list[str]:
    """
    Разбивает длинный текст на несколько частей с сохранением целостности предложений.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина одной части (по умолчанию 1000 символов для Telegram)
        logger: Логгер для записи информации о разбивке
    
    Returns:
        Список частей текста
    """
    if not text or len(text) <= max_length:
        return [text] if text else []
    
    parts = []
    remaining_text = text
    part_number = 1
    
    while remaining_text and len(remaining_text) > max_length:
        # Обрезаем с запасом
        truncated = remaining_text[:max_length]
        
        # Ищем последнюю точку, восклицательный или вопросительный знак
        sentence_endings = ['.', '!', '?', '…']
        last_sentence_end = -1
        
        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos
        
        # Если нашли границу предложения и она не слишком близко к началу
        if last_sentence_end > max_length * 0.6:
            split_point = last_sentence_end + 1
            part = remaining_text[:split_point].strip()
            if logger:
                logger.info(f"📝 Part {part_number} split at sentence boundary: {len(part)} chars")
        else:
            # Ищем последний пробел, чтобы не разрывать слова
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.5:
                split_point = last_space
                part = remaining_text[:split_point].strip()
                if logger:
                    logger.info(f"✂️ Part {part_number} split at word boundary: {len(part)} chars")
            else:
                # В крайнем случае просто обрезаем
                split_point = max_length - 10  # Оставляем запас
                part = remaining_text[:split_point].strip()
                if logger:
                    logger.warning(f"⚠️ Part {part_number} split forcefully: {len(part)} chars")
        
        if part:
            parts.append(part)
            part_number += 1
        
        remaining_text = remaining_text[split_point:].strip()
    
    # Добавляем оставшуюся часть
    if remaining_text:
        parts.append(remaining_text)
        if logger:
            logger.info(f"📝 Final part {part_number}: {len(remaining_text)} chars")
    
    if logger and len(parts) > 1:
        logger.info(f"📚 Text split into {len(parts)} parts (original: {len(text)} chars)")
    
    return parts


def get_localized_message(key: str, lang: str = 'ru', **kwargs) -> str:
    """Get localized message for logging.

    Args:
        key: Message key
        lang: Language code ('ru' or 'en')
        **kwargs: Format parameters
    """

    # НЕ ГЕНЕРИРУЕМ ПУСТЫЕ СООБЩЕНИЯ!
    if not key or key.strip() == '':
        print(f"[WARNING] Empty message key provided: '{key}'")
        return ""  # Возвращаем пустую строку для совместимости

    # Словарь локализованных сообщений с поддержкой мультиязычности
    messages = {
        "checking_rule": {
            "ru": "Проверка правила {rule_id}: {source} → {target}",
            "en": "Checking rule {rule_id}: {source} → {target}"
        },
        "processing_enabled": {
            "ru": "Обработка включена для сообщения {message_id}",
            "en": "Processing enabled for message {message_id}"
        },
        "message_details": {
            "ru": "Сообщение {message_id}: тип={media_type}, текст={text_len} симв., подпись={caption_len} симв.",
            "en": "Message {message_id}: type={media_type}, text={text_len} chars, caption={caption_len} chars"
        },
        "worker_alive": {
            "ru": "Агент активен: обработка={processing}, правил={rules_count}",
            "en": "Agent active: processing={processing}, rules={rules_count}"
        },
        "new_message": {
            "ru": "Новое сообщение {message_id} из {channel}",
            "en": "New message {message_id} from {channel}"
        },
        "rule_matched": {
            "ru": "Сообщение {message_id} соответствует правилу {rule_id}",
            "en": "Message {message_id} matches rule {rule_id}"
        },
        "processing_message": {
            "ru": "Обработка сообщения {message_id}",
            "en": "Processing message {message_id}"
        },
        "message_sent": {
            "ru": "Сообщение отправлено в {target_channel}",
            "en": "Message sent to {target_channel}"
        },
        "message_scheduled": {
            "ru": "Сообщение запланировано на {schedule_time}",
            "en": "Message scheduled for {schedule_time}"
        },
        "worker_connected": {
            "ru": "Подключен к Telegram как @{username}",
            "en": "Connected to Telegram as @{username}"
        },
        "worker_ready": {
            "ru": "Агент готов и ожидает новые сообщения",
            "en": "Agent ready and waiting for new messages"
        },
        "rules_loaded": {
            "ru": "Загружено {count} правил обработки",
            "en": "Loaded {count} processing rules"
        },
        "processing_paused": {
            "ru": "Обработка приостановлена, пропускаем сообщение {message_id}",
            "en": "Processing paused, skipping message {message_id}"
        },
        "processing_resumed": {
            "ru": "Обработка сообщений возобновлена",
            "en": "Message processing resumed"
        },
        "no_rules": {
            "ru": "Правила каналов не настроены",
            "en": "Channel rules not configured"
        },
        "listening_started": {
            "ru": "Начато прослушивание сообщений",
            "en": "Message listening started"
        },
        "loading_rules": {
            "ru": "Загрузка правил каналов...",
            "en": "Loading channel rules..."
        },
        "downloading_session": {
            "ru": "Загрузка сессии из S3",
            "en": "Downloading session from S3"
        },
        # Status messages from hybrid_processor.py
        "batch_start": {
            "ru": "🔄 Запуск пакетной обработки накопленных постов",
            "en": "🔄 Starting batch processing of accumulated posts"
        },
        "processing_rules": {
            "ru": "🔄 Обработка {rules_count} правил каналов",
            "en": "🔄 Processing {rules_count} channel rules"
        },
        "rule_processed": {
            "ru": "✅ Правило {rule_index}: обработано {posts_count} постов",
            "en": "✅ Rule {rule_index}: processed {posts_count} posts"
        },
        "rule_no_posts": {
            "ru": "ℹ️ Правило {rule_index}: новых постов не найдено",
            "en": "ℹ️ Rule {rule_index}: no new posts found"
        },
        "no_new_messages": {
            "ru": "ℹ️ Новых сообщений в {channel} после ID {last_id} не найдено",
            "en": "ℹ️ No new messages in {channel} after ID {last_id} found"
        },
        "found_new_messages": {
            "ru": "📨 Найдено {messages_count} новых сообщений в {channel}",
            "en": "📨 Found {messages_count} new messages in {channel}"
        },
        "rule_error": {
            "ru": "❌ Ошибка правила {rule_index}: {error}",
            "en": "❌ Rule {rule_index} error: {error}"
        },
        "batch_complete": {
            "ru": "✅ Пакетная обработка завершена",
            "en": "✅ Batch processing completed"
        },
        "batch_processing_error": {
            "ru": "❌ Ошибка пакетной обработки: {error}",
            "en": "❌ Batch processing error: {error}"
        },
        "client_not_connected": {
            "ru": "❌ Клиент не подключен для правила {rule_id}",
            "en": "❌ Client not connected for rule {rule_id}"
        },
        "client_not_ready": {
            "ru": "❌ Клиент не готов к обработке",
            "en": "❌ Client not ready for processing"
        },
        "batch_disabled": {
            "ru": "ℹ️ Пакетная обработка отключена, поведение прослушивания зависит от конфигурации",
            "en": "ℹ️ Batch processing disabled, listening behavior depends on configuration"
        },
        "listening_skipped": {
            "ru": "⏸ Прослушивание пропущено для запланированного воркера",
            "en": "⏸ Listening skipped for scheduled worker"
        },
        "hybrid_error": {
            "ru": "❌ Ошибка гибридной обработки: {error}",
            "en": "❌ Hybrid processing error: {error}"
        },
        "channel_not_ready": {
            "ru": "⚠️ Канал {channel} недоступен, пропускаем",
            "en": "⚠️ Channel {channel} unavailable, skipping"
        },
        "channel_not_accessible": {
            "ru": "❌ Канал {channel} недоступен или не найден",
            "en": "❌ Channel {channel} inaccessible or not found"
        },
        "channel_access_failed": {
            "ru": "❌ Невозможно получить доступ к каналу {channel}: {error}",
            "en": "❌ Cannot access channel {channel}: {error}"
        },
        "channel_access_error": {
            "ru": "❌ Невозможно получить доступ к каналу {channel}: {error}",
            "en": "❌ Cannot access channel {channel}: {error}"
        },
        "get_messages_error": {
            "ru": "❌ Ошибка получения сообщений из {channel}: {error}",
            "en": "❌ Error getting messages from {channel}: {error}"
        },
        "album_processing_error": {
            "ru": "❌ Ошибка обработки альбома {album_id}: {error}",
            "en": "❌ Album processing error {album_id}: {error}"
        },
        "message_processing_error": {
            "ru": "❌ Ошибка обработки сообщения {message_id}: {error}",
            "en": "❌ Message processing error {message_id}: {error}"
        },
        "channel_accessible_direct": {
            "ru": "✅ Канал {channel} доступен через get_chat (ID: {channel_id})",
            "en": "✅ Channel {channel} accessible via get_chat (ID: {channel_id})"
        },
        "channel_accessible_resolved": {
            "ru": "✅ Канал {channel} доступен как ID {resolved_id}",
            "en": "✅ Channel {channel} accessible as ID {resolved_id}"
        },
        "channel_verification_error": {
            "ru": "❌ Ошибка проверки канала {channel}: {error}",
            "en": "❌ Channel verification error {channel}: {error}"
        },
        "dialog_search_error": {
            "ru": "⚠️ Ошибка поиска диалогов: {error}",
            "en": "⚠️ Dialog search error: {error}"
        },
        "channel_found_by_title": {
            "ru": "✅ Найден похожий канал: '{title}' (ID: {channel_id}) для поиска '{search}'",
            "en": "✅ Found similar channel: '{title}' (ID: {channel_id}) for search '{search}'"
        },
        "listening": {
            "ru": "🎧 Прослушивание сообщений",
            "en": "🎧 Listening for messages"
        },
        "connection_error": {
            "ru": "❌ Невозможно начать прослушивание: клиент не подключен",
            "en": "❌ Cannot start listening: client not connected"
        },
        # User-facing messages for bot communication
        "agent_ready": {
            "ru": "Агент готов",
            "en": "Agent ready"
        },
        "waiting_for_messages": {
            "ru": "⏳ Ожидание новых сообщений...",
            "en": "⏳ Waiting for new messages..."
        },
        "initialization": {
            "ru": "🚀 Инициализация воркера...",
            "en": "🚀 Initializing worker..."
        },
        "connecting": {
            "ru": "🔌 Подключение к Telegram...",
            "en": "🔌 Connecting to Telegram..."
        },
        "processing_channel": {
            "ru": "🔍 Чтение канала: {channel}",
            "en": "🔍 Reading channel: {channel}"
        },
        "rule_processing": {
            "ru": "📋 Правило {index}/{total}: {source} → {target}",
            "en": "📋 Rule {index}/{total}: {source} → {target}"
        },
        "flood_wait": {
            "ru": "⏳ Ожидание {seconds}с (ограничение Telegram)...",
            "en": "⏳ Waiting {seconds}s (Telegram limit)..."
        },
        "connected_as": {
            "ru": "Подключен к Telegram как @{username}",
            "en": "Connected to Telegram as @{username}"
        },
        "agent_ready_full": {
            "ru": "Агент готов и ожидает новые сообщения",
            "en": "Agent ready and waiting for new messages"
        },
        "client_disconnected": {
            "ru": "Клиент отключен для правила {rule_id}",
            "en": "Client disconnected for rule {rule_id}"
        },
        "tracking_rules": {
            "ru": "Отслеживание {count} правил",
            "en": "Tracking {count} rules"
        },
        "session_download": {
            "ru": "📥 Загрузка сессии из S3...",
            "en": "📥 Downloading session from S3..."
        },
        "paused_status": {
            "ru": "⏸️ Обработка приостановлена",
            "en": "⏸️ Processing paused"
        },
        "processing_text": {
            "ru": "📝 Обработка текста...",
            "en": "📝 Processing text..."
        },
        "calculating_schedule": {
            "ru": "⏰ Расчёт времени публикации...",
            "en": "⏰ Calculating publication time..."
        },
        "user_not_found": {
            "ru": "Пользователь не найден в базе данных",
            "en": "User not found in database"
        },
        "ai_error_empty": {
            "ru": "Ошибка ИИ: пустой ответ от сервиса",
            "en": "AI error: empty response from service"
        },
        "switching_to_listening": {
            "ru": "Переход к режиму прослушивания...",
            "en": "Switching to listening mode..."
        },
        "listening_skipped_status": {
            "ru": "⏸ Режим прослушивания пропущен",
            "en": "⏸ Listening mode skipped"
        },
        "channel_access_denied": {
            "ru": "Нет доступа к каналу {channel}: {error}",
            "en": "No access to channel {channel}: {error}"
        },
        "channel_read_error": {
            "ru": "Ошибка чтения {channel}: {error}",
            "en": "Channel read error {channel}: {error}"
        },
        "album_error": {
            "ru": "Ошибка обработки альбома {album_id}: {error}",
            "en": "Album processing error {album_id}: {error}"
        },
        "client_not_ready_listening": {
            "ru": "Telegram клиент не готов к прослушиванию",
            "en": "Telegram client not ready for listening"
        },
        "session_found_s3": {
            "ru": "📥 Session found in S3, downloading...",
            "en": "📥 Session found in S3, downloading..."
        },
        "loading_rules_db": {
            "ru": "📋 Loading channel rules from database...",
            "en": "📋 Loading channel rules from database..."
        },
        "start_failed_no_connection": {
            "ru": "Не удалось запустить: нет подключения",
            "en": "Failed to start: no connection"
        },
        "insufficient_funds_error": {
            "ru": "Остановка агента из-за недостатка средств",
            "en": "Stopping worker due to insufficient funds"
        },
        # Новые ключи для уведомлений об остановке воркера
        "worker_stopping_manual": {
            "ru": "⛔️ Агент останавливается: остановка по запросу пользователя",
            "en": "⛔️ Agent stopping: manual stop request"
        },
        "worker_stopped_final": {
            "ru": "🟥 Агент остановлен.",
            "en": "🟥 Agent stopped."
        },
        # Новые ключи для hybrid_processor.py
        "rule_processing_status": {
            "ru": "📋 Правило {index}/{total}: {source} → {target}",
            "en": "📋 Rule {index}/{total}: {source} → {target}"
        },
        "rule_error_report": {
            "ru": "Ошибка правила {index} ({source}): {error}",
            "en": "Rule {index} error ({source}): {error}"
        },
        "processing_channel_status": {
            "ru": "🔍 Чтение канала: {channel}",
            "en": "🔍 Reading channel: {channel}"
        },
        "found_messages_status": {
            "ru": "📨 Найдено {count} новых сообщений в {channel}",
            "en": "📨 Found {count} new messages in {channel}"
        },
        "processing_album_status": {
            "ru": "📸 Обработка альбома {album_id}...",
            "en": "📸 Processing album {album_id}..."
        },
        "processing_message_status": {
            "ru": "🔄 Сообщение {index}/{total} (ID: {message_id})",
            "en": "🔄 Message {index}/{total} (ID: {message_id})"
        },
        "waiting_for_messages_status": {
            "ru": "⏳ Ожидание новых сообщений...",
            "en": "⏳ Waiting for new messages..."
        },
        "starting_listening_status": {
            "ru": "🎧 Запуск режима прослушивания...",
            "en": "🎧 Starting listening mode..."
        },
        # Новые ключи для worker.py
        "rules_loading_error": {
            "ru": "Ошибка загрузки правил: {error}",
            "en": "Rules loading error: {error}"
        },
        "batch_processing_summary": {
            "ru": "Обработано {posts} постов по {rules} правилам",
            "en": "Processed {posts} posts by {rules} rules"
        },
        "agent_waiting_status": {
            "ru": "⏳ Агент готов и ожидает новые сообщения",
            "en": "⏳ Agent ready and waiting for new messages"
        },
        # Новые ключи для message_processor.py
        "processing_message_status": {
            "ru": "🔄 Обработка поста #{message_id} из {channel}...",
            "en": "🔄 Processing post #{message_id} from {channel}..."
        },
        "rules_found_status": {
            "ru": "🎯 Найдено {count} правил для поста #{message_id}",
            "en": "🎯 Found {count} rules for post #{message_id}"
        },
        "applying_rule_status": {
            "ru": "📋 Применяю правило: {source} → {target}",
            "en": "📋 Applying rule: {source} → {target}"
        },
        "rule_processing_error_report": {
            "ru": "Ошибка обработки правила {source} → {target}: {error}",
            "en": "Rule processing error {source} → {target}: {error}"
        },
        "critical_handler_error": {
            "ru": "Критическая ошибка обработчика: {error}",
            "en": "Critical handler error: {error}"
        },
        "processing_album_status": {
            "ru": "📸 Обработка альбома #{album_id}...",
            "en": "📸 Processing album #{album_id}..."
        },
        "text_processing_error": {
            "ru": "Ошибка обработки текста: {error}",
            "en": "Text processing error: {error}"
        },
        "target_channel_not_found": {
            "ru": "Не удалось найти целевой канал: {channel}",
            "en": "Target channel not found: {channel}"
        },
        "schedule_calculation_error": {
            "ru": "Ошибка расчёта времени: {error}",
            "en": "Schedule calculation error: {error}"
        },
        "scheduling_message_status": {
            "ru": "📅 Планирование на {time}...",
            "en": "📅 Scheduling for {time}..."
        },
        "scheduling_failed": {
            "ru": "Не удалось запланировать пост",
            "en": "Failed to schedule post"
        },
        "scheduling_error": {
            "ru": "Ошибка планирования: {error}",
            "en": "Scheduling error: {error}"
        },
        # Дополнительные ключи для полной локализации
        "channel_access_denied": {
            "ru": "Нет доступа к каналу {channel}: {error}",
            "en": "No access to channel {channel}: {error}"
        },
        "channel_read_error": {
            "ru": "Ошибка чтения {channel}: {error}",
            "en": "Channel read error {channel}: {error}"
        },
        "album_error": {
            "ru": "Ошибка обработки альбома {album_id}: {error}",
            "en": "Album processing error {album_id}: {error}"
        },
        "client_not_ready_listening": {
            "ru": "Telegram клиент не готов к прослушиванию",
            "en": "Telegram client not ready for listening"
        },
        "session_found_s3": {
            "ru": "📥 Session found in S3, downloading...",
            "en": "📥 Session found in S3, downloading..."
        },
        "loading_rules_db": {
            "ru": "📋 Loading channel rules from database...",
            "en": "📋 Loading channel rules from database..."
        },
        "start_failed_no_connection": {
            "ru": "Не удалось запустить: нет подключения",
            "en": "Failed to start: no connection"
        },
        "insufficient_funds_error": {
            "ru": "Остановка агента из-за недостатка средств",
            "en": "Stopping worker due to insufficient funds"
        },
        "worker_stopping_manual": {
            "ru": "⛔️ Агент останавливается: остановка по запросу пользователя",
            "en": "⛔️ Agent stopping: manual stop request"
        },
        "worker_stopped_final": {
            "ru": "🟥 Агент остановлен.",
            "en": "🟥 Agent stopped."
        },
        "rule_processing_status": {
            "ru": "📋 Правило {index}/{total}: {source} → {target}",
            "en": "📋 Rule {index}/{total}: {source} → {target}"
        },
        "rule_error_report": {
            "ru": "Ошибка правила {index} ({source}): {error}",
            "en": "Rule {index} error ({source}): {error}"
        },
        "processing_channel_status": {
            "ru": "🔍 Чтение канала: {channel}",
            "en": "🔍 Reading channel: {channel}"
        },
        "found_messages_status": {
            "ru": "📨 Найдено {count} новых сообщений в {channel}",
            "en": "📨 Found {count} new messages in {channel}"
        },
        "processing_album_status": {
            "ru": "📸 Обработка альбома #{album_id}...",
            "en": "📸 Processing album #{album_id}..."
        },
        "processing_message_status": {
            "ru": "🔄 Сообщение {index}/{total} (ID: {message_id})",
            "en": "🔄 Message {index}/{total} (ID: {message_id})"
        },
        "waiting_for_messages_status": {
            "ru": "⏳ Ожидание новых сообщений...",
            "en": "⏳ Waiting for new messages..."
        },
        "starting_listening_status": {
            "ru": "🎧 Запуск режима прослушивания...",
            "en": "🎧 Starting listening mode..."
        },
        "rules_loading_error": {
            "ru": "Ошибка загрузки правил: {error}",
            "en": "Rules loading error: {error}"
        },
        "batch_processing_summary": {
            "ru": "Обработано {posts} постов по {rules} правилам",
            "en": "Processed {posts} posts by {rules} rules"
        },
        "agent_waiting_status": {
            "ru": "⏳ Агент готов и ожидает новые сообщения",
            "en": "⏳ Agent ready and waiting for new messages"
        },
        "processing_message_status": {
            "ru": "🔄 Обработка поста #{message_id} из {channel}...",
            "en": "🔄 Processing post #{message_id} from {channel}..."
        },
        "rules_found_status": {
            "ru": "🎯 Найдено {count} правил для поста #{message_id}",
            "en": "🎯 Found {count} rules for post #{message_id}"
        },
        "applying_rule_status": {
            "ru": "📋 Применяю правило: {source} → {target}",
            "en": "📋 Applying rule: {source} → {target}"
        },
        "rule_processing_error_report": {
            "ru": "Ошибка обработки правила {source} → {target}: {error}",
            "en": "Rule processing error {source} → {target}: {error}"
        },
        "critical_handler_error": {
            "ru": "Критическая ошибка обработчика: {error}",
            "en": "Critical handler error: {error}"
        },
        "text_processing_error": {
            "ru": "Ошибка обработки текста: {error}",
            "en": "Text processing error: {error}"
        },
        "target_channel_not_found": {
            "ru": "Не удалось найти целевой канал: {channel}",
            "en": "Target channel not found: {channel}"
        },
        "schedule_calculation_error": {
            "ru": "Ошибка расчёта времени: {error}",
            "en": "Schedule calculation error: {error}"
        },
        "scheduling_message_status": {
            "ru": "📅 Планирование на {time}...",
            "en": "📅 Scheduling for {time}..."
        },
        "scheduling_failed": {
            "ru": "Не удалось запланировать пост",
            "en": "Failed to schedule post"
        },
        "user_not_found": {
            "ru": "Пользователь не найден в базе данных",
            "en": "User not found in database"
        },
        "ai_error_empty": {
            "ru": "Ошибка ИИ: пустой ответ от сервиса",
            "en": "AI error: empty response from service"
        },
        "switching_to_listening": {
            "ru": "Переход к режиму прослушивания...",
            "en": "Switching to listening mode..."
        },
        "listening_skipped_status": {
            "ru": "⏸ Режим прослушивания пропущен",
            "en": "⏸ Listening mode skipped"
        },
        "channel_access_denied": {
            "ru": "Нет доступа к каналу {channel}: {error}",
            "en": "No access to channel {channel}: {error}"
        },
        "channel_read_error": {
            "ru": "Ошибка чтения {channel}: {error}",
            "en": "Channel read error {channel}: {error}"
        },
        "album_error": {
            "ru": "Ошибка обработки альбома {album_id}: {error}",
            "en": "Album processing error {album_id}: {error}"
        },
        "client_not_ready_listening": {
            "ru": "Telegram клиент не готов к прослушиванию",
            "en": "Telegram client not ready for listening"
        },
        "session_found_s3": {
            "ru": "📥 Session found in S3, downloading...",
            "en": "📥 Session found in S3, downloading..."
        },
        "loading_rules_db": {
            "ru": "📋 Loading channel rules from database...",
            "en": "📋 Loading channel rules from database..."
        },
        "start_failed_no_connection": {
            "ru": "Не удалось запустить: нет подключения",
            "en": "Failed to start: no connection"
        },
        "insufficient_funds_error": {
            "ru": "Остановка агента из-за недостатка средств",
            "en": "Stopping worker due to insufficient funds"
        },
        "worker_stopping_manual": {
            "ru": "⛔️ Агент останавливается: остановка по запросу пользователя",
            "en": "⛔️ Agent stopping: manual stop request"
        },
        "worker_stopped_final": {
            "ru": "🟥 Агент остановлен.",
            "en": "🟥 Agent stopped."
        },
        "rule_processing_status": {
            "ru": "📋 Правило {index}/{total}: {source} → {target}",
            "en": "📋 Rule {index}/{total}: {source} → {target}"
        },
        "rule_error_report": {
            "ru": "Ошибка правила {index} ({source}): {error}",
            "en": "Rule {index} error ({source}): {error}"
        },
        "processing_channel_status": {
            "ru": "🔍 Чтение канала: {channel}",
            "en": "🔍 Reading channel: {channel}"
        },
        "found_messages_status": {
            "ru": "📨 Найдено {count} новых сообщений в {channel}",
            "en": "📨 Found {count} new messages in {channel}"
        },
        "processing_album_status": {
            "ru": "📸 Обработка альбома #{album_id}...",
            "en": "📸 Processing album #{album_id}..."
        },
        "processing_message_status": {
            "ru": "🔄 Сообщение {index}/{total} (ID: {message_id})",
            "en": "🔄 Message {index}/{total} (ID: {message_id})"
        },
        "waiting_for_messages_status": {
            "ru": "⏳ Ожидание новых сообщений...",
            "en": "⏳ Waiting for new messages..."
        },
        "starting_listening_status": {
            "ru": "🎧 Запуск режима прослушивания...",
            "en": "🎧 Starting listening mode..."
        },
        "rules_loading_error": {
            "ru": "Ошибка загрузки правил: {error}",
            "en": "Rules loading error: {error}"
        },
        "batch_processing_summary": {
            "ru": "Обработано {posts} постов по {rules} правилам",
            "en": "Processed {posts} posts by {rules} rules"
        },
        "agent_waiting_status": {
            "ru": "⏳ Агент готов и ожидает новые сообщения",
            "en": "⏳ Agent ready and waiting for new messages"
        },
        "processing_message_status": {
            "ru": "🔄 Обработка поста #{message_id} из {channel}...",
            "en": "🔄 Processing post #{message_id} from {channel}..."
        },
        "rules_found_status": {
            "ru": "🎯 Найдено {count} правил для поста #{message_id}",
            "en": "🎯 Found {count} rules for post #{message_id}"
        },
        "applying_rule_status": {
            "ru": "📋 Применяю правило: {source} → {target}",
            "en": "📋 Applying rule: {source} → {target}"
        },
        "rule_processing_error_report": {
            "ru": "Ошибка обработки правила {source} → {target}: {error}",
            "en": "Rule processing error {source} → {target}: {error}"
        },
        "critical_handler_error": {
            "ru": "Критическая ошибка обработчика: {error}",
            "en": "Critical handler error: {error}"
        },
        "text_processing_error": {
            "ru": "Ошибка обработки текста: {error}",
            "en": "Text processing error: {error}"
        },
        "target_channel_not_found": {
            "ru": "Не удалось найти целевой канал: {channel}",
            "en": "Target channel not found: {channel}"
        },
        "schedule_calculation_error": {
            "ru": "Ошибка расчёта времени: {error}",
            "en": "Schedule calculation error: {error}"
        },
        "scheduling_message_status": {
            "ru": "📅 Планирование на {time}...",
            "en": "📅 Scheduling for {time}..."
        },
        "scheduling_failed": {
            "ru": "Не удалось запланировать пост",
            "en": "Failed to schedule post"
        },
        "user_not_found": {
            "ru": "Пользователь не найден в базе данных",
            "en": "User not found in database"
        },
        "ai_error_empty": {
            "ru": "Ошибка ИИ: пустой ответ от сервиса",
            "en": "AI error: empty response from service"
        },
        "switching_to_listening": {
            "ru": "Переход к режиму прослушивания...",
            "en": "Switching to listening mode..."
        },
        "listening_skipped_status": {
            "ru": "⏸ Режим прослушивания пропущен",
            "en": "⏸ Listening mode skipped"
        },
        # Новые ключи для локализации сообщений из message_processor.py
        "success_report": {
            "ru": "✅ Пост запланирован на {time}\n\n{text}\n\n💸 Списано: {deducted:.1f}🔋\n💰 Баланс: {balance:.1f}🔋",
            "en": "✅ Post scheduled for {time}\n\n{text}\n\n💸 Deducted: {deducted:.1f}🔋\n💰 Balance: {balance:.1f}🔋"
        },
        "negative_balance_report": {
            "ru": "💸 Отрицательный баланс: {balance:.1f}🔋\nДля пополнения: {contact}",
            "en": "💸 Negative balance: {balance:.1f}🔋\nFor top-up: {contact}"
        },
        "insufficient_funds_future": {
            "ru": "⚠️ Недостаточно средств для будущих постов. Обратитесь к {contact} для пополнения баланса.",
            "en": "⚠️ Insufficient funds for future posts. Please contact {contact} to top up your balance."
        },
        "ai_model_not_found": {
            "ru": "Модель #{model_id} не найдена",
            "en": "Model #{model_id} not found"
        },
        "ai_error_empty": {
            "ru": "Ошибка ИИ: пустой ответ от сервиса",
            "en": "AI error: empty response from service"
        },
        "ai_error_detailed": {
            "ru": "Ошибка ИИ: {error}",
            "en": "AI error: {error}"
        },
        "channel_not_found": {
            "ru": "Не удалось найти канал {channel}: {error}",
            "en": "Failed to find channel {channel}: {error}"
        },
        "channel_access_error": {
            "ru": "Ошибка доступа к каналу {channel}: {error}",
            "en": "Channel access error {channel}: {error}"
        },
        "channel_unknown_format": {
            "ru": "Неизвестный формат канала: {channel}",
            "en": "Unknown channel format: {channel}"
        },
        # VIP3 scheduled posts report messages
        "vip3_scheduled_posts_header": {
            "ru": "📊 Оставшиеся запланированные посты:",
            "en": "📊 Remaining scheduled posts:"
        },
        "vip3_scheduled_posts_item": {
            "ru": "• {channel_name}: {count} постов",
            "en": "• {channel_name}: {count} posts"
        },
        "vip3_no_scheduled_posts": {
            "ru": "ℹ️ Нет запланированных постов",
            "en": "ℹ️ No scheduled posts"
        },
        "vip3_channel_not_accessible": {
            "ru": "⚠️ Канал {channel} недоступен",
            "en": "⚠️ Channel {channel} not accessible"
        }
    }

    # Проверяем наличие ключа
    if key not in messages:
        print(f"[WARNING] Unknown message key: '{key}' - using key as message")
        return key.format(**kwargs) if kwargs else key

    # Получаем сообщение для указанного языка (по умолчанию 'ru')
    message_data = messages[key]
    if isinstance(message_data, dict):
        # Мультиязычная структура
        message = message_data.get(lang, message_data.get('ru', key))
    else:
        # Обратная совместимость со старой структурой
        message = message_data

    try:
        return message.format(**kwargs)
    except KeyError as e:
        print(f"[ERROR] Missing parameter {e} for message key '{key}'")
        return message  # Возвращаем без форматирования