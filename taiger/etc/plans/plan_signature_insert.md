# План реализации вставки подписи (Signature Implementation Plan)

## Обзор задачи
Необходимо реализовать автоматическую вставку подписи в конец постов. Подпись берется из полей `caption_text` и `caption_url` таблицы `channel_pairs`.

### Требования:
1. **Формат подписи**:
   - Если есть `caption_text` и `caption_url` -> `<a href="url">text</a>`.
   - Если есть только `caption_text` -> `text`.
   - Если есть только `caption_url` -> `<a href="url">url</a>`.
2. **Место вставки**:
   - Всегда в самый конец контента.
   - Если пост разделяется на части (сплитуется), подпись должна быть **только в последней части**.
3. **Управление длиной**:
   - Если итоговый текст превышает лимиты Telegram (4096 для текста, 1024 для медиа), основной текст должен быть обрезан так, чтобы подпись гарантированно влезла.

---

## Шаг 1: Универсальная функция формирования подписи
Добавить в [`telegram_worker/utils.py`](telegram_worker/utils.py):

```python
# grace: signature_formatter
def format_signature(caption_text: Optional[str], caption_url: Optional[str]) -> str:
    if not caption_text and not caption_url:
        return ""
    
    if caption_text and caption_url:
        return f'<a href="{caption_url}">{caption_text}</a>'
    elif caption_text:
        return caption_text
    else:
        return f'<a href="{caption_url}">{caption_url}</a>'
```

---

## Шаг 2: Интеграция в MessageProcessor
В [`telegram_worker/message_processor.py`](telegram_worker/message_processor.py) необходимо изменить `process_text_content`, чтобы она возвращала текст без подписи, а подпись добавлялась на этапе планирования.

Однако, проще всего добавить подпись прямо в `process_text_content` в самом конце, учитывая лимиты.

```python
# grace: message_processor_signature_integration
# Внутри process_text_content, перед финальным return:

signature = format_signature(rule.caption_text, rule.caption_url)
if signature:
    # Определяем лимит (1024 для медиа, 4096 для текста)
    # Для простоты и безопасности используем 1000/4000
    limit = 1024 if (message.photo or message.video or message.document) else 4096
    
    # Резервируем место под подпись и разделитель (\n\n)
    max_text_len = limit - len(signature) - 2
    
    if len(text) > max_text_len:
        text = smart_truncate_message(text, max_text_len, self.logger)
    
    text = f"{text}\n\n{signature}"
```

---

## Шаг 3: Обработка сплитования (Разделения сообщений)
В [`telegram_worker/scheduler.py`](telegram_worker/scheduler.py) логика сплитования находится в `schedule_message`. Сейчас она просто делит текст на части. Нужно изменить её так, чтобы подпись не дублировалась.

**Вариант А (Рекомендуемый)**: Передавать подпись отдельно в `schedule_message`.

```python
# grace: scheduler_split_logic_fix
# В schedule_message добавить параметр signature: Optional[str] = None

async def schedule_message(self, text: str, ..., signature: Optional[str] = None):
    # ...
    text_parts = split_long_message(formatted_text, 1000, self.logger)
    
    # Если есть подпись, добавляем её ТОЛЬКО в последнюю часть
    if signature and text_parts:
        last_part = text_parts[-1]
        # Проверяем, не превысим ли лимит части (1000)
        if len(last_part) + len(signature) + 2 > 1000:
            # Если не влезает, обрезаем последнюю часть еще сильнее
            last_part = last_part[:(1000 - len(signature) - 5)] + "..."
        text_parts[-1] = f"{last_part}\n\n{signature}"
```

---

## Шаг 4: Обработка альбомов (Media Groups)
В [`telegram_worker/media_handler.py`](telegram_worker/media_handler.py) в методе `send_album` подпись также должна добавляться в конец.

```python
# grace: media_handler_signature
# В send_album:
text_parts = split_long_message(processed_text, 1024, self.logger)
# Если сплитуется, подпись уже должна быть в последнем элементе text_parts
# (если мы добавили её в process_text_content_for_album)
```

---

## Рекомендации по реализации:
1. **Использовать HTML**: Всегда использовать `ParseMode.HTML`, так как подпись содержит теги `<a>`.
2. **Порядок**: Сначала AI-обработка -> потом вставка подписи. Это гарантирует, что ИИ не удалит ссылку.
3. **Тестирование**: Проверить на постах длиной > 1024 символов с картинкой (должно сплитоваться, подпись в конце текстового сообщения).
