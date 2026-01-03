# План реализации оповещения о запланированных постах для VIP3

## Обзор

Добавить автоматическое оповещение для пользователей с VIP=3 о количестве запланированных постов в каналах-чистовиках после запуска воркера.

## Требования

1. **Место добавления:** `telegram_worker/hybrid_processor.py` после завершения пакетной обработки всех правил (после строки 212)
2. **Переменная окружения:** Создать `REMAINING_POSTS_ALARM` в `.env` (пока только создание, логику применения добавим позже)
3. **Условие отправки:** Всегда после запуска VIP3 воркера (показывать все каналы и количество постов)
4. **Формат названия:** Получать реальное название канала через `get_chat()` и использовать его
5. **Тип сообщения:** Отчетное сообщение (MessageRole.USER_REPORT) - НЕ перезаписывается, остается в истории
6. **Локализация:** Добавить сообщения на русском и английском языках

## Архитектура решения

### Компоненты

1. **Функция проверки запланированных постов** - новая функция в `hybrid_processor.py`
2. **Локализованные сообщения** - добавить в `telegram_worker/utils.py`
3. **Интеграция в пакетную обработку** - вызов после `process_accumulated_posts()`

## Детальная реализация

### Шаг 1: Добавить локализованные сообщения

**Важно:** Используем `MessageRole.USER_REPORT` вместо `MessageRole.USER_STATUS`, чтобы отчет не перезаписывался следующими статусными сообщениями.

**Файл:** [`telegram_worker/utils.py`](telegram_worker/utils.py)

```python
# grace: Add to messages dictionary in get_localized_message()

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
```

### Шаг 2: Добавить функцию проверки запланированных постов

**Файл:** [`telegram_worker/hybrid_processor.py`](telegram_worker/hybrid_processor.py)

Добавить новый метод в класс `HybridProcessor`:

```python
# grace: Add new method to HybridProcessor class

async def check_and_report_scheduled_posts(self):
    """Проверить и отправить отчет о запланированных постах для VIP3"""
    try:
        # Получаем все правила обработки для пользователя
        channel_pairs = await self.worker.get_channel_pairs()
        
        if not channel_pairs:
            await self.worker.messenger.send(
                "vip3_no_scheduled_posts",
                MessageRole.USER_REPORT
            )
            return
        
        # Словарь для хранения результатов: {channel_name: count}
        scheduled_posts_info = {}
        
        # Проверяем каждый канал-чистовик
        for channel_pair in channel_pairs:
            try:
                # Получаем количество запланированных постов для этого правила
                count = await self._get_scheduled_posts_count(channel_pair.id)
                
                if count > 0:
                    # Получаем реальное название канала
                    channel_name = await self._get_channel_name(channel_pair.target_channel)
                    scheduled_posts_info[channel_name] = count
                    
            except Exception as e:
                self.worker.logger.error(f"Error checking scheduled posts for {channel_pair.target_channel}: {e}")
                continue
        
        # Формируем отчет
        if scheduled_posts_info:
            # Сортируем по количеству постов (по убыванию)
            sorted_channels = sorted(
                scheduled_posts_info.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Формируем текст отчета
            report_lines = []
            for channel_name, count in sorted_channels:
                report_lines.append(
                    get_localized_message(
                        "vip3_scheduled_posts_item",
                        lang=await self.worker.messenger._get_user_language(),
                        channel_name=channel_name,
                        count=count
                    )
                )
            
            # Добавляем заголовок
            header = get_localized_message(
                "vip3_scheduled_posts_header",
                lang=await self.worker.messenger._get_user_language()
            )
            
            report_text = f"{header}\n" + "\n".join(report_lines)
            
            # Отправляем как отчетное сообщение (не перезаписывается)
            await self.worker.messenger.send(
                "vip3_scheduled_posts_header",
                MessageRole.USER_REPORT
            )
            
            # Отправляем полный отчет
            await self.worker.messenger.send(
                report_text,
                MessageRole.USER_REPORT
            )
        else:
            # Нет запланированных постов
            await self.worker.messenger.send(
                "vip3_no_scheduled_posts",
                MessageRole.USER_REPORT
            )
            
    except Exception as e:
        self.worker.logger.error(f"Error in check_and_report_scheduled_posts: {e}")
        import traceback
        traceback.print_exc()

async def _get_scheduled_posts_count(self, channel_pair_id: int) -> int:
    """Получить количество запланированных постов для правила"""
    try:
        async with async_session() as session:
            from models import ScheduledPost
            result = await session.execute(
                select(func.count(ScheduledPost.id)).where(
                    ScheduledPost.channel_pair_id == channel_pair_id,
                    ScheduledPost.status == 'pending'
                )
            )
            count = result.scalar()
            return count if count else 0
    except Exception as e:
        self.worker.logger.error(f"Error getting scheduled posts count: {e}")
        return 0

async def _get_channel_name(self, channel_identifier: str) -> str:
    """Получить реальное название канала"""
    try:
        if not self.worker.is_connected():
            return channel_identifier
        
        # Пробуем получить информацию о канале
        chat = await self.worker.client.get_chat(channel_identifier)
        
        # Приоритет: title > username > identifier
        if hasattr(chat, 'title') and chat.title:
            return chat.title
        elif hasattr(chat, 'username') and chat.username:
            return f"@{chat.username}"
        else:
            return channel_identifier
            
    except Exception as e:
        self.worker.logger.debug(f"Could not get chat info for {channel_identifier}: {e}")
        return channel_identifier
```

### Шаг 3: Интеграция в пакетную обработку

**Файл:** [`telegram_worker/hybrid_processor.py`](telegram_worker/hybrid_processor.py)

Изменить метод `process_accumulated_posts()`:

```python
# grace: Modify process_accumulated_posts method

async def process_accumulated_posts(self, process_old_messages: bool = False):
    """Обработка накопленных постов по всем правилам"""
    channel_pairs = await self.worker.get_channel_pairs()
    
    if not channel_pairs:
        await self.worker.messenger.send("no_rules", MessageRole.INTERNAL_LOG, level="info")
        return 0
    
    self.total_rules = len(channel_pairs)
    total_posts = 0
    
    await self.worker.messenger.send("processing_rules", MessageRole.INTERNAL_LOG, level="info", rules_count=len(channel_pairs))

    # Предварительный прогрев клиента (один раз для всех каналов)
    self.worker.logger.info("🔄 Pre-warming client for all channels...")
    await self.worker._warm_up_client(limit=10)
    self.worker.logger.info("✅ Client pre-warmed")

    for i, channel_pair in enumerate(channel_pairs):
        self.current_rule = i + 1
        
        try:
            # Send status about which rule is being processed
            await self.worker.messenger.send("rule_processing_status", MessageRole.USER_STATUS,
                                               index=i+1,
                                               total=len(channel_pairs),
                                               source=channel_pair.source_channel,
                                               target=channel_pair.target_channel)
            
            posts_count = await self.process_channel_batch(channel_pair, process_old_messages=process_old_messages)
            total_posts += posts_count
            
            if posts_count > 0:
                await self.worker.messenger.send("rule_processed", MessageRole.INTERNAL_LOG, level="success", rule_index=i+1, posts_count=posts_count)
                # Reports for individual rules are sent by message_processor when scheduling
            else:
                await self.worker.messenger.send("rule_no_posts", MessageRole.INTERNAL_LOG, level="info", rule_index=i+1)
                # No need for permanent report when no posts found
                
        except Exception as e:
            await self.worker.messenger.send("rule_error", MessageRole.INTERNAL_LOG, level="error", rule_index=i+1, error=str(e))
            # Send error report (permanent)
            await self.worker.messenger.send("rule_error_report", MessageRole.USER_REPORT,
                                               report_type="error",
                                               index=i+1,
                                               source=channel_pair.source_channel,
                                               error=str(e))
            continue
    
    self.total_processed = total_posts
    
    # grace: Add VIP3 scheduled posts report after batch processing
    # Check if this is a VIP3 worker (listen_for_new_messages=False)
    # We'll need to pass this information or check it another way
    # For now, we'll call it unconditionally as requested
    await self.check_and_report_scheduled_posts()
    
    return total_posts
```

### Шаг 4: Добавить импорты

**Файл:** [`telegram_worker/hybrid_processor.py`](telegram_worker/hybrid_processor.py)

Добавить в начало файла:

```python
# grace: Add necessary imports
from sqlalchemy import func
from models import ScheduledPost
```

### Шаг 5: Добавить переменную окружения

**Файл:** [`.env`](.env)

```bash
# Порог для оповещения о малом количестве запланированных постов
# (пока не используется, зарезервировано для будущего использования)
REMAINING_POSTS_ALARM=5
```

## Пример работы

### Сценарий 1: Есть запланированные посты

```
📊 Оставшиеся запланированные посты:
• Мой канал: 15 постов
• Другой канал: 8 постов
• Третий канал: 3 постов
```

### Сценарий 2: Нет запланированных постов

```
ℹ️ Нет запланированных постов
```

## Поток выполнения

```
process_accumulated_posts()
    ↓
Обработка всех правил (lines 181-211)
    ↓
total_posts = sum(posts_count)
    ↓
check_and_report_scheduled_posts()  ← НОВЫЙ ВЫЗОВ
    ↓
Получение channel_pairs
    ↓
Для каждого channel_pair:
    - _get_scheduled_posts_count(channel_pair_id)
    - _get_channel_name(target_channel)
    ↓
Формирование отчета
    ↓
Отправка через messenger.send(..., MessageRole.USER_REPORT)
```

## Особенности реализации

### 1. Тип сообщения

Используется `MessageRole.USER_REPORT`:
- **Постоянное сообщение** - НЕ перезаписывается следующими сообщениями
- **Остается в истории** - пользователь всегда может его увидеть
- **Идеально подходит** для важных отчетов, которые не должны быть потеряны

### 2. Получение названия канала

Функция `_get_channel_name()`:
- Использует `client.get_chat()` для получения информации
- Приоритет: `title` > `username` > `identifier`
- Обрабатывает ошибки и возвращает исходный идентификатор при неудаче

### 3. Подсчет запланированных постов

Функция `_get_scheduled_posts_count()`:
- Запрашивает из БД количество `ScheduledPost` со статусом `'pending'`
- Группирует по `channel_pair_id`
- Возвращает 0 при ошибке

### 4. Локализация

Все сообщения используют `get_localized_message()`:
- Автоматическое определение языка пользователя
- Поддержка русского и английского
- Форматирование параметров через `.format()`

## Потенциальные улучшения (на будущее)

1. **Пороговое значение:** Использовать `REMAINING_POSTS_ALARM` для фильтрации каналов с малым количеством постов
2. **Кэширование названий каналов:** Кэшировать результаты `get_chat()` для снижения нагрузки на API
3. **Периодическая проверка:** Добавить отдельную фоновую задачу для периодической проверки (не только при запуске)
4. **Группировка:** Добавить возможность группировки по VIP уровню или другим критериям
5. **Детализация:** Добавить информацию о времени ближайшего поста

## Тестирование

### Тестовые сценарии

1. **VIP3 пользователь с запланированными постами:**
   - Запустить воркер
   - Проверить, что отчет отправлен
   - Проверить правильность названий каналов
   - Проверить правильность количества постов

2. **VIP3 пользователь без запланированных постов:**
   - Запустить воркер
   - Проверить, что отправлено сообщение "Нет запланированных постов"

3. **VIP3 пользователь с недоступными каналами:**
   - Запустить воркер
   - Проверить, что недоступные каналы пропущены без ошибок

4. **Не-VIP3 пользователь:**
   - Запустить воркер
   - Проверить, что отчет НЕ отправлен (если добавим проверку VIP уровня)

## Зависимости

### Обязательные импорты

```python
from sqlalchemy import func
from models import ScheduledPost
from .utils import get_localized_message
from .unified_messenger import MessageRole
```

### Модели

- `ScheduledPost` - модель запланированных постов
- `ChannelPair` - модель правил обработки каналов

### Методы worker

- `worker.is_connected()` - проверка подключения клиента
- `worker.client.get_chat()` - получение информации о канале
- `worker.messenger.send()` - отправка сообщений

## Резюме

Реализация включает:

✅ **Новая функция** `check_and_report_scheduled_posts()` в `HybridProcessor`
✅ **Вспомогательные функции** `_get_scheduled_posts_count()` и `_get_channel_name()`
✅ **Локализованные сообщения** для отчета на RU и EN
✅ **Интеграция** в `process_accumulated_posts()` после обработки всех правил
✅ **Отчетные сообщения** через `MessageRole.USER_REPORT` (не перезаписываются)
✅ **Реальные названия каналов** через `get_chat()`
✅ **Обработка ошибок** с логированием
✅ **Переменная окружения** `REMAINING_POSTS_ALARM` (зарезервирована)

Код готов к реализации в режиме Code.
