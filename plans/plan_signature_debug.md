# План отладки вставки подписи (Signature Debug Plan)

## Диагностика проблемы
На основе анализа кода [`telegram_worker/message_processor.py`](telegram_worker/message_processor.py) и [`telegram_worker/media_handler.py`](telegram_worker/media_handler.py), логика вставки подписи из `channel_pairs.caption_text` и `channel_pairs.caption_url` полностью отсутствует в текущей реализации.

### Вероятные причины неудачи предыдущей попытки:
1. **Отсутствие кода**: Логика не была интегрирована в основные методы обработки текста (`process_text_content`).
2. **Конфликт с ИИ**: Если подпись добавлялась до обработки ИИ, модель могла её удалить или исказить.
3. **Лимиты Telegram**: В альбомах (медиагруппах) лимит подписи — 1024 символа. Добавление длинной подписи могло приводить к обрезке основного контента.
4. **Форматирование**: Для кликабельности ссылки требуется HTML-разметка `<a href="...">...</a>`, которая могла быть некорректно обработана или экранирована.

---

## Шаг 1: Добавление логов для проверки данных
Необходимо убедиться, что данные `caption_text` и `caption_url` доходят до воркера и корректно извлекаются из БД.

### В [`telegram_worker/message_processor.py`](telegram_worker/message_processor.py)
Добавить логи в начало `process_text_content`:

```python
# grace: debug_logs_signature
async def process_text_content(self, rule: ChannelPair, message: Message, client: Client) -> tuple[str, bool]:
    # ... существующий код получения текста ...
    
    # DEBUG: Проверка наличия данных подписи
    self.logger.info(f"🔍 [SIGNATURE_DEBUG] Rule ID: {rule.id}")
    self.logger.info(f"🔍 [SIGNATURE_DEBUG] Raw caption_text: '{rule.caption_text}'")
    self.logger.info(f"🔍 [SIGNATURE_DEBUG] Raw caption_url: '{rule.caption_url}'")
    
    # ... остальной код ...
```

---

## Шаг 2: Проверка формирования HTML-ссылки
Подпись должна формироваться как HTML-ссылка. Нужно проверить, как она выглядит перед отправкой в планировщик.

### Образец кода для вставки (для grok-code-fast-1):
Логика должна быть добавлена **ПОСЛЕ** обработки ИИ и **ПОСЛЕ** удаления лишнего текста, но **ДО** финальной обрезки сообщения.

```python
# grace: signature_insertion_logic
def apply_signature(text: str, caption_text: Optional[str], caption_url: Optional[str]) -> str:
    if not caption_text:
        return text
        
    signature = caption_text
    if caption_url:
        # Формируем кликабельную ссылку
        signature = f'<a href="{caption_url}">{caption_text}</a>'
    
    # Добавляем в конец с разделителем
    return f"{text}\n\n{signature}"
```

---

## Шаг 3: Валидация в планировщике
Нужно убедиться, что `scheduler.py` использует `ParseMode.HTML` и не ломает разметку при разделении длинных сообщений.

### В [`telegram_worker/scheduler.py`](telegram_worker/scheduler.py)
Добавить лог перед `send_message`/`send_photo`:

```python
# grace: scheduler_debug
self.logger.info(f"📤 [SCHEDULER_DEBUG] Final text to send (first 100 chars): {text[:100]}")
self.logger.info(f"📤 [SCHEDULER_DEBUG] Signature present in text: {'<a href=' in text}")
```

---

## Резюме плана действий:
1. **Подтвердить**, что `rule.caption_text` и `rule.caption_url` не `None` во время выполнения.
2. **Внедрить** функцию `apply_signature` в `MessageProcessor.process_text_content` и `MediaHandler.process_text_content_for_album`.
3. **Убедиться**, что вставка происходит после ИИ, чтобы ИИ не "галлюцинировал" на ссылке.
4. **Проверить**, что `ParseMode.HTML` активен во всех методах отправки в `scheduler.py`.
