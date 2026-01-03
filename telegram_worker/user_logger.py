"""
Module for sending worker logs directly to users via Telegram bot.

Architecture:
- Status messages: transient, each new status replaces the previous one (edit or delete+send)
- Report messages: permanent, never replaced. Can "promote" current status to report.

Flow:
1. send_status("Processing...") -> creates/edits status message
2. send_status("Scheduling...") -> edits the same status message
3. send_report("✅ Scheduled successfully") -> converts status to permanent report, clears status slot
4. send_status("Waiting...") -> creates new status message
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional
import asyncio
import aiohttp
from telegram_worker.utils import get_api_base_url
from telegram_worker.log_mirroring import get_log_mirror
from db import async_session
from sqlalchemy import select
from models import User, UserBotLogState
from redis_client import redis_get, redis_set, redis_delete


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
    
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.http_session is None or self.http_session.closed:
            # DIAGNOSTIC: Log when creating new HTTP session
            self.logger.info(f"🔧 [DIAGNOSTIC] Creating new HTTP session for user {self.user_id}")
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
        else:
            # DIAGNOSTIC: Log when reusing existing session
            self.logger.debug(f"🔄 [DIAGNOSTIC] Reusing existing HTTP session for user {self.user_id}")
        return self.http_session
    
    async def _close_http_session(self):
        """Close HTTP session."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            self.http_session = None

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

                # DIAGNOSTIC: Log HTTP session state and message details
                self.logger.info(f"📊 [DIAGNOSTIC] send_status called: message='{message[:50]}...', "
                               f"session_closed={getattr(session, 'closed', 'unknown')}, "
                               f"last_status_id={self.last_status_message_id}")

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
                        
                        # Mirror status to TMA
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

                # DIAGNOSTIC: Log HTTP session state and report details
                self.logger.info(f"📊 [DIAGNOSTIC] send_report called: type={report_type}, "
                               f"message='{message[:50]}...', "
                               f"session_closed={getattr(session, 'closed', 'unknown')}, "
                               f"last_status_id={self.last_status_message_id}")

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
                        
                        # Mirror report to TMA
                        await self.log_mirror.mirror_report(message, report_type)
                    else:
                        text = await response.text()
                        self.logger.error(f"Failed to send report: HTTP {response.status}, {text}")

            except asyncio.TimeoutError:
                self.logger.error(f"Timeout sending report to user {self.user_id}")
            except Exception as e:
                self.logger.error(f"Failed to send report: {e}")

    # === LEGACY METHODS FOR COMPATIBILITY ===
    # These will be removed after full migration
    
    async def send_status_update(self, message: str, log_type: str = "info", details=None):
        """
        DEPRECATED: Use send_status() instead.
        Kept for backward compatibility during migration.
        """
        await self.send_status(message)
    
    async def send_log_to_user(self, message: str, log_type: str = "info", *,
                               details=None, include_metadata: bool = True):
        """
        DEPRECATED: Use send_report() instead.
        Kept for backward compatibility during migration.
        """
        report_type = "success" if log_type == "success" else log_type
        await self.send_report(message, report_type)
    
    async def close(self):
        """Close resources."""
        await self._close_http_session()
        # Close log mirror
        await self.log_mirror.close()


# Global instances cache
_user_loggers: dict[int, UserLogger] = {}


def get_user_logger(user_id: int) -> UserLogger:
    """Get or create UserLogger instance for user."""
    if user_id not in _user_loggers:
        _user_loggers[user_id] = UserLogger(user_id)
    return _user_loggers[user_id]


def remove_user_logger(user_id: int) -> None:
    """Remove UserLogger instance for user."""
    if user_id in _user_loggers:
        del _user_loggers[user_id]