"""
Unified Messenger - Единая система сообщений для воркера
Объединяет внутреннее логирование и пользовательские уведомления
"""
import os
import logging
from enum import Enum
from typing import Optional
import asyncio
import aiohttp
from datetime import datetime, timezone
from sqlalchemy import select

from db import async_session
from models import User, UserBotLogState
from redis_client import redis_get, redis_set, redis_delete
from .utils import get_api_base_url, get_localized_message
from .log_mirroring import get_log_mirror


class MessageRole(Enum):
    """Роли сообщений определяют аудиторию и способ доставки"""
    INTERNAL_LOG = "internal_log"      # Внутреннее логирование для разработчиков (бот)
    WEBSOCKET_LOG = "websocket_log"    # Логи для WebSocket/TMA (не бот)
    USER_STATUS = "user_status"        # Временный статус для пользователя (можно заменить)
    USER_REPORT = "user_report"        # Постоянный отчёт пользователю (нельзя заменить)


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
        
        # Log mirroring to TMA
        self.log_mirror = get_log_mirror(user_id)

    def _status_redis_key(self) -> str:
        """Redis key for storing last status message ID."""
        return f"bot_status_msg:{self.user_id}"

    async def _ensure_status_loaded(self):
        """Load last status message ID from Redis/DB if not already loaded."""
        if self._status_loaded:
            return

        # Try Redis first
        stored_id = await redis_get(self._status_redis_key())
        if stored_id is not None and stored_id != "None":
            try:
                self.last_status_message_id = int(stored_id)
                self._status_loaded = True
                return
            except (TypeError, ValueError):
                pass

        # Fallback to database
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(UserBotLogState.last_status_message_id).where(
                        UserBotLogState.user_id == self.user_id
                    )
                )
                db_value = result.scalar_one_or_none()
                if db_value is not None:
                    self.last_status_message_id = int(db_value)
                else:
                    self.last_status_message_id = None
        except Exception as e:
            self.logger.debug(f"Failed to load status message ID from DB: {e}")
            self.last_status_message_id = None

        self._status_loaded = True

    async def _save_status_message_id(self, message_id: Optional[int]) -> None:
        """Save last status message ID to Redis and database."""
        self.last_status_message_id = message_id

        # Update Redis
        try:
            if message_id is not None:
                await redis_set(self._status_redis_key(), str(message_id))
            else:
                await redis_delete(self._status_redis_key())
        except Exception as e:
            self.logger.debug(f"Failed to save status ID in Redis: {e}")

        # Update database
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(UserBotLogState).where(UserBotLogState.user_id == self.user_id)
                )
                state = result.scalar_one_or_none()
                now = datetime.now(timezone.utc)

                if state:
                    state.last_status_message_id = message_id
                    state.updated_at = now
                elif message_id is not None:
                    session.add(UserBotLogState(
                        user_id=self.user_id,
                        last_status_message_id=message_id,
                        updated_at=now,
                    ))

                await session.commit()
        except Exception as e:
            self.logger.debug(f"Failed to save status ID in DB: {e}")

    async def _clear_status_slot(self) -> None:
        """Clear the status message slot (after converting to report)."""
        await self._save_status_message_id(None)

    async def _get_telegram_id(self) -> int:
        """Get Telegram ID for the user from database."""
        if self.telegram_id is not None:
            return self.telegram_id

        try:
            async with async_session() as session:
                stmt = select(User).where(User.id == self.user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                if user and user.telegram_id:
                    self.telegram_id = int(user.telegram_id)
                    return self.telegram_id
        except Exception as e:
            self.logger.error(f"Failed to get Telegram ID for user {self.user_id}: {e}")

        return self.user_id

    async def _get_user_language(self) -> str:
        """Get user's language preference."""
        try:
            async with async_session() as session:
                user = await session.get(User, self.user_id)
                if user and user.language_code:
                    return user.language_code
        except Exception as e:
            self.logger.debug(f"Failed to get user language: {e}")
        return 'en'  # Default to English

    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.http_session is None or self.http_session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
        return self.http_session

    async def _close_http_session(self):
        """Close HTTP session."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            self.http_session = None

    async def send(self, key: str, role: MessageRole, level: str = "info", **kwargs):
        """
        Отправить сообщение в зависимости от роли.
        """
        try:
            # grace: Use cached language or load it
            if not hasattr(self, '_user_lang') or self._user_lang is None:
                self._user_lang = await self._get_user_language()
            user_lang = self._user_lang
            self.logger.debug(f"DEBUG LOCALIZATION: user_lang={user_lang}, key={key}, kwargs={kwargs}")
            message = get_localized_message(key, lang=user_lang, **kwargs)
            self.logger.debug(f"DEBUG LOCALIZATION: localized message='{message}'")

            if role == MessageRole.INTERNAL_LOG:
                await self._send_internal_log(message, level, **kwargs)
            elif role == MessageRole.WEBSOCKET_LOG:
                await self._send_websocket_log(message, level, **kwargs)
            elif role == MessageRole.USER_STATUS:
                await self._send_user_status(message)
            elif role == MessageRole.USER_REPORT:
                await self._send_user_report(message, level)
            else:
                self.logger.error(f"Unknown message role: {role}")

        except Exception as e:
            self.logger.error(f"Failed to send message {key} with role {role}: {e}")

    async def _send_websocket_log(self, message: str, level: str, **kwargs):
        """Отправить лог-сообщение в WebSocket/TMA."""
        try:
            session = await self._get_http_session()
            api_url = f"{get_api_base_url()}/api/internal/log"

            # Determine log_type based on level
            log_type = "worker_status"  # Default for worker logs
            if level in ["error", "critical"]:
                log_type = "worker_error"
            elif level == "success":
                log_type = "worker_success"

            payload = {
                "user_id": self.user_id,
                "log_type": log_type,
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status != 200:
                    self.logger.debug(f"Failed to send WebSocket log: HTTP {response.status}")
        except Exception as e:
            self.logger.debug(f"Failed to send WebSocket log: {e}")

    async def _send_internal_log(self, message: str, level: str, **kwargs):
        """Отправить внутреннее лог-сообщение."""
        # Используем тот же механизм, что и для пользовательских сообщений
        # Отправляем через бот API как "системное сообщение"
        try:
            telegram_id = await self._get_telegram_id()
            session = await self._get_http_session()
            api_url = f"{get_api_base_url()}/api/internal/bot-log"

            # Определяем тип сообщения по уровню
            log_type = "info"
            if level in ["error", "critical"]:
                log_type = "error"
            elif level in ["warning"]:
                log_type = "warning"
            elif level in ["debug"]:
                log_type = "debug"

            payload = {
                "user_id": self.user_id,
                "telegram_id": telegram_id,
                "message": f"[SYSTEM] {message}",
                "log_type": log_type,
                "level": level
            }

            async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    self.logger.debug(f"Internal log sent: {message[:50]}...")
                else:
                    text = await response.text()
                    self.logger.warning(f"Failed to send internal log: HTTP {response.status}, {text}")
                    # Don't spam logs with repeated failures - just log once per session

        except aiohttp.ClientError as e:
            # Network-related errors - log once and continue
            self.logger.warning(f"Network error sending internal log (will retry later): {e}")
        except asyncio.TimeoutError:
            # Timeout - log once and continue
            self.logger.warning("Timeout sending internal log (will retry later)")
        except Exception as e:
            # Other unexpected errors - log once and continue
            self.logger.warning(f"Unexpected error sending internal log: {e}")
            # Fallback to standard logging only for critical messages
            if level in ["error", "critical"]:
                log_method = getattr(self.logger, level, self.logger.info)
                log_method(f"[FALLBACK] {message}")

    async def _send_user_status(self, message: str):
        """Отправить временный статус пользователю."""
        async with self._status_lock:
            try:
                await self._ensure_status_loaded()
                telegram_id = await self._get_telegram_id()

                session = await self._get_http_session()
                api_url = f"{get_api_base_url()}/api/internal/bot-status"

                # grace: Log status send attempt
                self.logger.info(f"grace: [STATUS_START] user={self.user_id} last_id={self.last_status_message_id} text='{message[:50]}...'")

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
                            self.logger.info(f"grace: [STATUS_SUCCESS] user={self.user_id} new_msg_id={new_message_id}")
                        self.logger.debug(f"User status sent: {message[:50]}...")
                        
                        # Mirror status to TMA
                        await self.log_mirror.mirror_status(message)
                    else:
                        text = await response.text()
                        self.logger.error(f"grace: [STATUS_FAILED] user={self.user_id} last_id={self.last_status_message_id} http={response.status}")
                        self.logger.error(f"Failed to send user status: HTTP {response.status}, {text}")

            except asyncio.TimeoutError:
                self.logger.error(f"grace: [STATUS_TIMEOUT] user={self.user_id} last_id={self.last_status_message_id}")
                self.logger.error(f"Timeout sending status to user {self.user_id}")
            except Exception as e:
                self.logger.error(f"grace: [STATUS_ERROR] user={self.user_id} last_id={self.last_status_message_id} error={e}")
                self.logger.error(f"Failed to send user status: {e}")

    async def _send_user_report(self, message: str, report_type: str = "success"):
        """Отправить постоянный отчёт пользователю."""
        async with self._status_lock:
            try:
                await self._ensure_status_loaded()
                telegram_id = await self._get_telegram_id()

                session = await self._get_http_session()
                api_url = f"{get_api_base_url()}/api/internal/bot-report"

                # grace: Capture ID and clear locally BEFORE network call to prevent race condition
                target_id = self.last_status_message_id
                self.logger.info(f"grace: [REPORT_START] user={self.user_id} target_id={target_id} type={report_type}")

                payload = {
                    "user_id": self.user_id,
                    "telegram_id": telegram_id,
                    "message": message,
                    "report_type": report_type,
                    "last_status_message_id": target_id
                }

                async with session.post(api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        # Clear status slot - report is now permanent
                        await self._clear_status_slot()
                        # CRITICAL: Also clear local state to prevent next status from using old ID
                        self.last_status_message_id = None
                        self._status_loaded = False
                        self.logger.info(f"grace: [REPORT_SUCCESS] user={self.user_id} cleared_id={target_id}")
                        self.logger.debug(f"User report sent ({report_type}): {message[:50]}...")
                        
                        # Mirror report to TMA
                        await self.log_mirror.mirror_report(message, report_type)
                    else:
                        text = await response.text()
                        self.logger.error(f"grace: [REPORT_FAILED] user={self.user_id} target_id={target_id} http={response.status}")
                        self.logger.error(f"Failed to send user report: HTTP {response.status}, {text}")

            except asyncio.TimeoutError:
                self.logger.error(f"grace: [REPORT_TIMEOUT] user={self.user_id} target_id={target_id}")
                self.logger.error(f"Timeout sending report to user {self.user_id}")
            except Exception as e:
                self.logger.error(f"grace: [REPORT_ERROR] user={self.user_id} target_id={target_id} error={e}")
                self.logger.error(f"Failed to send user report: {e}")

    async def send_report(self, message: str, report_type: str = "success"):
        """Compatibility method for old user_logger.send_report calls."""
        await self._send_user_report(message, report_type)

    async def send_status(self, message: str):
        """Compatibility method for old user_logger.send_status calls."""
        await self._send_user_status(message)

    async def close(self):
        """Close resources."""
        await self._close_http_session()
        # Close log mirror
        await self.log_mirror.close()


# Глобальный кэш инстансов
_unified_messengers: dict[int, UnifiedMessenger] = {}


def get_unified_messenger(user_id: int) -> UnifiedMessenger:
    """Get or create UnifiedMessenger instance for user."""
    if user_id not in _unified_messengers:
        _unified_messengers[user_id] = UnifiedMessenger(user_id)
    return _unified_messengers[user_id]


def remove_unified_messenger(user_id: int) -> None:
    """Remove UnifiedMessenger instance for user."""
    if user_id in _unified_messengers:
        del _unified_messengers[user_id]