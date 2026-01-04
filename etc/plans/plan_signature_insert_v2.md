# План реализации вставки подписи V2 (Signature Implementation Plan v2)

## Почему предыдущий план мог не сработать:
1. **Сплитование**: Если подпись добавлялась в `process_text_content`, то при разделении длинного сообщения на части (`split_long_message`) подпись могла оказаться в первой части или быть разорванной.
2. **Лимиты**: При добавлении подписи в начало процесса, последующие трансформации могли её удалить или некорректно обрезать.
3. **Дублирование**: В альбомах подпись могла добавиться и к медиа, и к последующим текстовым сообщениям.

---

## Шаг 1: Формирование подписи (Utils)
Убедиться, что в [`telegram_worker/utils.py`](telegram_worker/utils.py) есть корректная функция:

```python
# grace: signature_formatter_v2
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

## Шаг 2: Изменение MessageProcessor
В [`telegram_worker/message_processor.py`](telegram_worker/message_processor.py) метод `process_text_content` должен возвращать текст **БЕЗ** подписи, но мы должны подготовить подпись отдельно.

```python
# grace: message_processor_logic_v2
# В process_rule:
processed_text, has_ai_error = await self.process_text_content(rule, message, client)
signature = format_signature(rule.caption_text, rule.caption_url)

# Передаем signature в scheduler.schedule_message
scheduled_msg = await self.scheduler.schedule_message(
    processed_text, target_channel_id, scheduled_time, message,
    signature=signature  # НОВЫЙ ПАРАМЕТР
)
```

---

## Шаг 3: Логика в Scheduler (Критически важно)
В [`telegram_worker/scheduler.py`](telegram_worker/scheduler.py) реализуем вставку подписи **ТОЛЬКО в последнюю часть** сообщения.

```python
# grace: scheduler_signature_logic_v2
async def schedule_message(self, text: str, ..., signature: Optional[str] = None):
    # ... (внутри метода)
    formatted_text = markdown_to_telegram_html(text)
    
    # Лимит для первой части (с медиа) - 1024, для текста - 4096
    first_part_limit = 1024 if original_message and (original_message.photo or ...) else 4000
    
    text_parts = split_long_message(formatted_text, 1000, self.logger) # Используем 1000 для запаса
    
    if signature and text_parts:
        # Добавляем подпись ТОЛЬКО к последней части
        last_part = text_parts[-1]
        
        # Проверяем лимит последней части (обычно это текстовое сообщение, лимит 4096)
        # Но если сообщение всего одно и оно с медиа, лимит 1024
        current_limit = 1024 if len(text_parts) == 1 and media_type else 4000
        
        if len(last_part) + len(signature) + 2 > current_limit:
            # Обрезаем основной текст части, чтобы влезла подпись
            available_space = current_limit - len(signature) - 5
            last_part = last_part[:available_space] + "..."
            
        text_parts[-1] = f"{last_part}\n\n{signature}"
    
    # Далее отправляем части как обычно
    # ...
```

---

## Шаг 4: Поддержка Альбомов
В [`telegram_worker/media_handler.py`](telegram_worker/media_handler.py) метод `_process_media_group` также должен извлекать подпись и передавать её в `send_album`.

```python
# grace: media_handler_v2
# В _process_media_group:
signature = format_signature(rule.caption_text, rule.caption_url)
sent_messages = await self.send_album(..., signature=signature)

# В send_album:
# Аналогично scheduler.py, добавляем signature в последнюю часть text_parts
```

---

## Итоговая схема:
1. Текст обрабатывается ИИ (чистый контент).
2. Подпись формируется отдельно.
3. Планировщик делит текст на куски.
4. Планировщик берет **последний** кусок и приклеивает к нему подпись.
5. Если кусок с подписью слишком большой — кусок обрезается.
