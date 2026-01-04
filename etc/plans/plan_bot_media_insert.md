# План восстановления отправки медиа в боте

## Проблема
В текущей реализации `telegram_bot/handlers.py` при отправке пользователем поста с медиа (фото, видео и т.д.), бот обрабатывает текст двумя моделями, но возвращает пользователю только обработанный текст без исходных медиафайлов.

## Анализ
1.  **Одиночные медиа**: В `text_message_handler` (строки 1171-1221) есть блоки `if message.photo`, `elif message.video` и т.д., но внутри них вызывается `processor.send_split_response`, который отправляет только текст.
2.  **Альбомы (Media Groups)**: В `_process_media_group` (строки 1364-1379) логика формирования `media_list` уже присутствует, но она не учитывает все типы медиа корректно и может быть улучшена.

## Предлагаемое решение

### 1. Изменения в `text_message_handler`
Для одиночных медиафайлов необходимо заменить вызов `send_split_response` на отправку соответствующего медиа-объекта с обработанным текстом в качестве подписи.

**Пример кода (grace):**
```python
# [telegram_bot/handlers.py:1171]
if message.photo:
    photo = message.photo[-1]
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo.file_id,
        caption=f"{formatted_text}\n\n{info_text}",
        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
        parse_mode="HTML"
    )
elif message.video:
    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=message.video.file_id,
        caption=f"{formatted_text}\n\n{info_text}",
        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
        parse_mode="HTML"
    )
# ... аналогично для других типов (document, audio, animation)
```

### 2. Изменения в `_process_media_group`
В `_process_media_group` логика уже почти готова, но нужно убедиться, что `media_list` правильно собирается и отправляется для каждой модели.

**Пример кода (grace):**
```python
# [telegram_bot/handlers.py:1364]
media_list = []
for i, msg in enumerate(messages):
    # Подпись ставим только к первому элементу альбома
    caption = f"{formatted_text}\n\n{info_text}" if i == 0 else ""
    if msg.photo:
        media_list.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption, parse_mode="HTML"))
    elif msg.video:
        media_list.append(InputMediaVideo(media=msg.video.file_id, caption=caption, parse_mode="HTML"))
    # ... и так далее
if media_list:
    await context.bot.send_media_group(chat_id=chat_id, media=media_list)
```

## План действий
1.  **Модификация `text_message_handler`**:
    *   Обновить блоки обработки `photo`, `video`, `document`, `audio`, `animation`.
    *   Вместо `processor.send_split_response` использовать `context.bot.send_photo`, `send_video` и т.д.
    *   Добавить проверку длины подписи (Telegram ограничивает подпись 1024 символами). Если текст длиннее, отправлять медиа с частью текста, а остальное — отдельным сообщением.

2.  **Модификация `_process_media_group`**:
    *   Исправить формирование `media_list`.
    *   Добавить `parse_mode="HTML"` в `InputMedia` объекты.
    *   Убедиться, что `info_text` включен в подпись.

3.  **Тестирование**:
    *   Отправить боту одиночное фото с текстом.
    *   Отправить боту альбом (2+ фото) с текстом.
    *   Проверить, что приходят два ответа (от двух моделей) с сохранением медиа.

## Риски
*   **Лимиты Telegram**: Подпись к медиа ограничена 1024 символами. Нужно использовать `_truncate_caption` или логику разделения сообщения, если текст от ИИ слишком длинный.
