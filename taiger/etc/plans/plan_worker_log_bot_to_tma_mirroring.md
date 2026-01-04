# План: Зеркалирование логов из бота в TMA

## Обзор задачи

**Проблема:** Воркер бэкенда логирует свои действия в двух местах:
1. **Telegram бот** - нравится пользователю (хорошая реализация)
2. **TMA (Telegram Mini App)** - не нравится пользователю (плохая реализация)

**Решение:** Отзеркалить логи из бота в TMA. Каждый раз, когда воркер пишет лог в бот - точно такой же лог нужно отправить в TMA.

**Особенность бота:** Два вида сообщений:
- **Статусные** (transient) - не остаются в ленте, заменяются следующими
- **Постоянные** (permanent) - остаются в ленте навсегда

**Требование к TMA:** Не разделять на статусные/постоянные - всё остаётся в ленте (удалится само при закрытии TMA).

---

## Архитектура текущей системы

### 1. Bot Logging (нравится)

**Файлы:**
- [`telegram_worker/user_logger.py`](../telegram_worker/user_logger.py) - класс `UserLogger`
- [`api/telegram.py`](../api/telegram.py) - эндпоинты `/internal/bot-status` и `/internal/bot-report`

**Методы:**
```python
# Статусное сообщение (временное)
await user_logger.send_status("🔄 Processing post...")

# Постоянное сообщение (отчёт)
await user_logger.send_report("✅ Scheduled successfully", "success")
```

**API эндпоинты:**
- `POST /api/internal/bot-status` - отправка статусных сообщений
- `POST /api/internal/bot-report` - отправка постоянных отчётов

### 2. TMA Logging (не нравится)

**Файлы:**
- [`telegram_worker/unified_messenger.py`](../telegram_worker/unified_messenger.py) - класс `UnifiedMessenger`
- [`api/websocket.py`](../api/websocket.py) - эндпоинт `/internal/log`

**Методы:**
```python
# Лог в TMA через UnifiedMessenger
await messenger.send("processing_post", MessageRole.WEBSOCKET_LOG, level="info")
```

**API эндпоинт:**
- `POST /api/internal/log` - отправка логов в WebSocket/TMA

---

## План реализации

### Шаг 1: Создать модуль зеркалирования логов

**Файл:** `telegram_worker/log_mirroring.py`

**Назначение:** Централизованный модуль для зеркалирования всех логов из бота в TMA.

**Ключевые принципы:**
- Перехватывать все вызовы `send_status()` и `send_report()` из `UserLogger`
- Отправлять зеркальные логи в TMA через WebSocket API
- Не разделять на статусные/постоянные - всё в ленту
- Использовать ту же локализацию, что и в боте

---

## Детальная реализация с кодом

### Шаг 1.1: Создать модуль зеркалирования

```python
# grace: Создаём новый модуль для зеркалирования логов
# grace: Этот модуль будет перехватывать все логи из бота и отправлять их в TMA

"""
Модуль зеркалирования логов из Telegram бота в TMA.

Каждый лог, отправленный в бот, автоматически зеркалируется в TMA.
В TMA не разделяем на статусные/постоянные - всё остаётся в ленте.
"""
import logging
from typing import Optional
import aiohttp
from datetime import datetime, timezone

from telegram_worker.utils import get_api_base_url


class LogMirror:
    """
    Зеркалирование логов из бота в TMA.
    
    Использование:
        mirror = LogMirror(user_id)
        await mirror.mirror_status("🔄 Processing post...")
        await mirror.mirror_report("✅ Scheduled successfully", "success")
    """
    
    def __init__(self, user_id: int, logger=None):
        self.user_id = user_id
        self.logger = logger or logging.getLogger(__name__)
        self.http_session: Optional[aiohttp.ClientSession] = None
    
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию."""
        if self.http_session is None or self.http_session.closed:
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
        return self.http_session
    
    async def _close_http_session(self):
        """Закрыть HTTP сессию."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            self.http_session = None
    
    async def mirror_status(self, message: str) -> None:
        """
        Зеркалировать статусное сообщение в TMA.
        
        В TMA статусные сообщения тоже остаются в ленте (в отличие от бота).
        
        Args:
            message: Текст сообщения (например, "🔄 Processing post...")
        """
        try:
            session = await self._get_http_session()
            api_url = f"{get_api_base_url()}/api/internal/log"
            
            # grace: Определяем уровень лога по содержимому сообщения
            level = "info"
            if "❌" in message or "error" in message.lower():
                level = "error"
            elif "⚠️" in message or "warning" in message.lower():
                level = "warning"
            elif "✅" in message or "success" in message.lower():
                level = "success"
            
            # grace: Формируем payload для WebSocket/TMA
            payload = {
                "user_id": self.user_id,
                "log_type": "worker_status",  # Все логи - worker_status
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # grace: Отправляем лог в TMA с коротким таймаутом
            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status == 200:
                    self.logger.debug(f"Status mirrored to TMA: {message[:50]}...")
                else:
                    self.logger.debug(f"Failed to mirror status to TMA: HTTP {response.status}")
        
        except asyncio.TimeoutError:
            # grace: Не критично, если TMA недоступен
            self.logger.debug(f"Timeout mirroring status to TMA for user {self.user_id}")
        except Exception as e:
            # grace: Не критично, продолжаем работу
            self.logger.debug(f"Failed to mirror status to TMA: {e}")
    
    async def mirror_report(self, message: str, report_type: str = "success") -> None:
        """
        Зеркалировать постоянный отчёт в TMA.
        
        В TMA отчёты тоже остаются в ленте (как и все сообщения).
        
        Args:
            message: Текст отчёта (например, "✅ Scheduled successfully")
            report_type: "success" | "error" | "warning"
        """
        try:
            session = await self._get_http_session()
            api_url = f"{get_api_base_url()}/api/internal/log"
            
            # grace: Определяем уровень лога по типу отчёта
            level = report_type if report_type in ["error", "warning", "success"] else "info"
            
            # grace: Формируем payload для WebSocket/TMA
            payload = {
                "user_id": self.user_id,
                "log_type": "worker_status",  # Все логи - worker_status
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # grace: Отправляем лог в TMA с коротким таймаутом
            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status == 200:
                    self.logger.debug(f"Report mirrored to TMA: {message[:50]}...")
                else:
                    self.logger.debug(f"Failed to mirror report to TMA: HTTP {response.status}")
        
        except asyncio.TimeoutError:
            # grace: Не критично, если TMA недоступен
            self.logger.debug(f"Timeout mirroring report to TMA for user {self.user_id}")
        except Exception as e:
            # grace: Не критично, продолжаем работу
            self.logger.debug(f"Failed to mirror report to TMA: {e}")
    
    async def close(self):
        """Закрыть ресурсы."""
        await self._close_http_session()


# Глобальный кэш инстансов
_log_mirrors: dict[int, LogMirror] = {}


def get_log_mirror(user_id: int) -> LogMirror:
    """Получить или создать LogMirror для пользователя."""
    if user_id not in _log_mirrors:
        _log_mirrors[user_id] = LogMirror(user_id)
    return _log_mirrors[user_id]


def remove_log_mirror(user_id: int) -> None:
    """Удалить LogMirror для пользователя."""
    if user_id in _log_mirrors:
        del _log_mirrors[user_id]
```

---

### Шаг 1.2: Интегрировать зеркалирование в UserLogger

**Файл:** `telegram_worker/user_logger.py`

**Изменения:** Добавить зеркалирование в методы `send_status()` и `send_report()`.

```python
# grace: Добавляем импорт в начало файла
from .log_mirroring import get_log_mirror


class UserLogger:
    """
    Send logs directly to user via Telegram bot.
    
    Two types of messages:
    - Status: transient, always replaces previous status
    - Report: permanent, never replaced (success reports, errors)
    """
    
    def __init__(self, user_id: int, logger=None):
        self.user_id = user_id
        self.telegram_id = None
        self.logger = logger or logging.getLogger(__name__)
        self.http_session: Optional[aiohttp.ClientSession] = None
        # Store the last status message ID for editing
        self.last_status_message_id: Optional[int] = None
        self._status_lock = asyncio.Lock()
        self._status_loaded = False
        
        # grace: Получаем инстанс зеркалирования для этого пользователя
        self.log_mirror = get_log_mirror(user_id)
    
    async def send_status(self, message: str) -> None:
        """
        Send a transient status message.

        Behavior:
        - If there's an existing status message -> edit it
        - If no existing status -> send new message and save its ID
        - Status messages can always be replaced by next status or report

        Args:
            message: Status text to display (e.g., "🔄 Processing post...")
        """
        async with self._status_lock:
            try:
                await self._ensure_status_loaded()
                telegram_id = await self._get_telegram_id()

                session = await self._get_http_session()
                api_url = f"{get_api_base_url()}/api/internal/bot-status"

                payload = {
                    "user_id": self.user_id,
                    "telegram_id": telegram_id,
                    "message": message,
                    "last_status_message_id": self.last_status_message_id
                }

                async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        new_message_id = data.get("message_id")
                        if new_message_id:
                            await self._save_status_message_id(int(new_message_id))
                        self.logger.debug(f"Status sent: {message[:50]}...")
                        
                        # grace: Зеркалируем статус в TMA
                        await self.log_mirror.mirror_status(message)
                    else:
                        text = await response.text()
                        self.logger.error(f"Failed to send status: HTTP {response.status}, {text}")

            except asyncio.TimeoutError:
                self.logger.error(f"Timeout sending status to user {self.user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send status: {e}")
    
    async def send_report(self, message: str, report_type: str = "success") -> None:
        """
        Send a permanent report message.

        Behavior:
        - If there's an existing status message -> edit it to become the report (promote)
        - If no existing status -> send new report message
        - After sending, clear the status slot so reports are never overwritten

        Args:
            message: Report text (e.g., "✅ Post scheduled at 15:30. Balance: 10.5🔋")
            report_type: "success" | "error" | "warning"
        """
        async with self._status_lock:
            try:
                await self._ensure_status_loaded()
                telegram_id = await self._get_telegram_id()

                session = await self._get_http_session()
                api_url = f"{get_api_base_url()}/api/internal/bot-report"

                payload = {
                    "user_id": self.user_id,
                    "telegram_id": telegram_id,
                    "message": message,
                    "report_type": report_type,
                    "last_status_message_id": self.last_status_message_id
                }

                async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        # Clear status slot - report is now permanent
                        await self._clear_status_slot()
                        self.logger.debug(f"Report sent ({report_type}): {message[:50]}...")
                        
                        # grace: Зеркалируем отчёт в TMA
                        await self.log_mirror.mirror_report(message, report_type)
                    else:
                        text = await response.text()
                        self.logger.error(f"Failed to send report: HTTP {response.status}, {text}")

            except asyncio.TimeoutError:
                self.logger.error(f"Timeout sending report to user {self.user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send report: {e}")
    
    async def close(self):
        """Close resources."""
        await self._close_http_session()
        # grace: Закрываем зеркалирование
        await self.log_mirror.close()
```

---

### Шаг 1.3: Интегрировать зеркалирование в UnifiedMessenger

**Файл:** `telegram_worker/unified_messenger.py`

**Изменения:** Добавить зеркалирование в методы `_send_user_status()` и `_send_user_report()`.

```python
# grace: Добавляем импорт в начало файла
from .log_mirroring import get_log_mirror


class UnifiedMessenger:
    """
    Единая система сообщений, заменяющая _log_worker_status и user_logger.

    Архитектура:
    - Все сообщения используют локализацию
    - Ролевая модель определяет поведение
    - Единая точка конфигурации
    """

    def __init__(self, user_id: int, logger=None):
        self.user_id = user_id
        self.logger = logger or logging.getLogger(__name__)
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.telegram_id = None
        self._status_lock = asyncio.Lock()
        self._status_loaded = False
        self.last_status_message_id: Optional[int] = None
        
        # grace: Получаем инстанс зеркалирования для этого пользователя
        self.log_mirror = get_log_mirror(user_id)
    
    async def _send_user_status(self, message: str):
        """Отправить временный статус пользователю."""
        async with self._status_lock:
            try:
                await self._ensure_status_loaded()
                telegram_id = await self._get_telegram_id()

                session = await self._get_http_session()
                api_url = f"{get_api_base_url()}/api/internal/bot-status"

                payload = {
                    "user_id": self.user_id,
                    "telegram_id": telegram_id,
                    "message": message,
                    "last_status_message_id": self.last_status_message_id
                }

                async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        new_message_id = data.get("message_id")
                        if new_message_id:
                            await self._save_status_message_id(int(new_message_id))
                        self.logger.debug(f"User status sent: {message[:50]}...")
                        
                        # grace: Зеркалируем статус в TMA
                        await self.log_mirror.mirror_status(message)
                    else:
                        text = await response.text()
                        self.logger.error(f"Failed to send user status: HTTP {response.status}, {text}")

            except asyncio.TimeoutError:
                self.logger.error(f"Timeout sending status to user {self.user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send user status: {e}")
    
    async def _send_user_report(self, message: str, report_type: str = "success"):
        """Отправить постоянный отчёт пользователю."""
        async with self._status_lock:
            try:
                await self._ensure_status_loaded()
                telegram_id = await self._get_telegram_id()

                session = await self._get_http_session()
                api_url = f"{get_api_base_url()}/api/internal/bot-report"

                payload = {
                    "user_id": self.user_id,
                    "telegram_id": telegram_id,
                    "message": message,
                    "report_type": report_type,
                    "last_status_message_id": self.last_status_message_id
                }

                async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        # Clear status slot - report is now permanent
                        await self._clear_status_slot()
                        self.logger.debug(f"User report sent ({report_type}): {message[:50]}...")
                        
                        # grace: Зеркалируем отчёт в TMA
                        await self.log_mirror.mirror_report(message, report_type)
                    else:
                        text = await response.text()
                        self.logger.error(f"Failed to send user report: HTTP {response.status}, {text}")

            except asyncio.TimeoutError:
                self.logger.error(f"Timeout sending report to user {self.user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send user report: {e}")
    
    async def close(self):
        """Close resources."""
        await self._close_http_session()
        # grace: Закрываем зеркалирование
        await self.log_mirror.close()
```

---

## Проверка реализации

### Тестовый сценарий

```python
# grace: Тестовый пример использования
from telegram_worker.user_logger import get_user_logger

async def test_mirroring():
    """Тест зеркалирования логов."""
    user_id = 1
    
    # grace: Получаем UserLogger
    user_logger = get_user_logger(user_id)
    
    # grace: Отправляем статус - должен появиться и в боте, и в TMA
    await user_logger.send_status("🔄 Processing post...")
    
    # grace: Отправляем отчёт - должен появиться и в боте, и в TMA
    await user_logger.send_report("✅ Scheduled successfully", "success")
    
    # grace: Закрываем ресурсы
    await user_logger.close()
```

### Ожидаемый результат

1. **В боте:**
   - Статусное сообщение "🔄 Processing post..." (заменяется следующим)
   - Постоянный отчёт "✅ Scheduled successfully" (остаётся навсегда)

2. **В TMA:**
   - Оба сообщения появляются в ленте
   - Оба сообщения остаются в ленте (не удаляются автоматически)
   - При закрытии TMA все сообщения исчезают (как и должно быть)

---

## Резюме изменений

### Новые файлы

1. **`telegram_worker/log_mirroring.py`** - модуль зеркалирования логов
   - Класс `LogMirror` для зеркалирования логов в TMA
   - Функции `get_log_mirror()` и `remove_log_mirror()` для управления инстансами

### Изменённые файлы

1. **`telegram_worker/user_logger.py`**
   - Добавлен импорт `get_log_mirror`
   - В `__init__()` создан инстанс `self.log_mirror`
   - В `send_status()` добавлено зеркалирование через `self.log_mirror.mirror_status()`
   - В `send_report()` добавлено зеркалирование через `self.log_mirror.mirror_report()`
   - В `close()` добавлено закрытие зеркалирования

2. **`telegram_worker/unified_messenger.py`**
   - Добавлен импорт `get_log_mirror`
   - В `__init__()` создан инстанс `self.log_mirror`
   - В `_send_user_status()` добавлено зеркалирование через `self.log_mirror.mirror_status()`
   - В `_send_user_report()` добавлено зеркалирование через `self.log_mirror.mirror_report()`
   - В `close()` добавлено закрытие зеркалирования

---

## Преимущества решения

1. **Минимальные изменения:** Только 3 файла (1 новый, 2 изменённых)
2. **Централизация:** Вся логика зеркалирования в одном модуле
3. **Прозрачность:** Зеркалирование происходит автоматически, без изменений в коде воркера
4. **Надёжность:** Ошибки зеркалирования не влияют на работу бота
5. **Производительность:** Короткие таймауты для TMA, чтобы не блокировать работу бота
6. **Единый стиль:** Используем ту же локализацию и форматирование, что и в боте

---

## Возможные улучшения (опционально)

1. **Конфигурация:** Добавить флаг для включения/выключения зеркалирования
2. **Фильтрация:** Добавить возможность фильтровать какие логи зеркалировать
3. **Батчинг:** Отправлять логи пачками для уменьшения количества запросов
4. **Кэширование:** Кэшировать HTTP сессии для уменьшения накладных расходов

---

## Заключение

Этот план обеспечивает полное зеркалирование всех логов из Telegram бота в TMA с минимальными изменениями в коде. Каждое сообщение, отправленное в бот, автоматически появляется в TMA, обеспечивая пользователю единый опыт логирования в обоих интерфейсах.
