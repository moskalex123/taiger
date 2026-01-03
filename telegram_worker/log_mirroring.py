"""
Модуль зеркалирования логов из Telegram бота в TMA.

Каждый лог, отправленный в бот, автоматически зеркалируется в TMA.
В TMA не разделяем на статусные/постоянные - всё остаётся в ленте.
"""
import asyncio
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
            
            # Определяем уровень лога по содержимому сообщения
            level = "info"
            if "❌" in message or "error" in message.lower():
                level = "error"
            elif "⚠️" in message or "warning" in message.lower():
                level = "warning"
            elif "✅" in message or "success" in message.lower():
                level = "success"
            
            # Формируем payload для WebSocket/TMA
            payload = {
                "user_id": self.user_id,
                "log_type": "worker_status",  # Все логи - worker_status
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Отправляем лог в TMA с коротким таймаутом
            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status == 200:
                    self.logger.debug(f"Status mirrored to TMA: {message[:50]}...")
                else:
                    self.logger.debug(f"Failed to mirror status to TMA: HTTP {response.status}")
        
        except asyncio.TimeoutError:
            # Не критично, если TMA недоступен
            self.logger.debug(f"Timeout mirroring status to TMA for user {self.user_id}")
        except Exception as e:
            # Не критично, продолжаем работу
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
            
            # Определяем уровень лога по типу отчёта
            level = report_type if report_type in ["error", "warning", "success"] else "info"
            
            # Формируем payload для WebSocket/TMA
            payload = {
                "user_id": self.user_id,
                "log_type": "worker_status",  # Все логи - worker_status
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Отправляем лог в TMA с коротким таймаутом
            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status == 200:
                    self.logger.debug(f"Report mirrored to TMA: {message[:50]}...")
                else:
                    self.logger.debug(f"Failed to mirror report to TMA: HTTP {response.status}")
        
        except asyncio.TimeoutError:
            # Не критично, если TMA недоступен
            self.logger.debug(f"Timeout mirroring report to TMA for user {self.user_id}")
        except Exception as e:
            # Не критично, продолжаем работу
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
