"""
Основной класс TelegramWorker
"""
import os
import sys
import asyncio
import logging
import tempfile
import json
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Dict

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from pyrogram.client import Client
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.types import Message
from pyrogram.errors import (
    UserDeactivated, AuthKeyUnregistered, UserBlocked,
    ChatWriteForbidden, FloodWait, PeerIdInvalid
)
from pyrogram.raw.functions.messages.get_scheduled_history import GetScheduledHistory
from pyrogram.raw.types.input_peer_channel import InputPeerChannel
from pyrogram.sync import idle

from pythonjsonlogger import jsonlogger
from dotenv import load_dotenv

from sqlalchemy import select, update as sql_update
from sqlalchemy.orm import selectinload

from db import async_session, get_db_session
from models import (
    ChannelPair, Worker, TelegramSession, WorkerError, 
    User, ScheduledPost, Model
)
from s3_session_manager import S3SessionManager
from s3_avatar_manager import S3AvatarManager

from .utils import get_api_base_url, get_localized_message
from .ai_processor import AIProcessor
from .balance_manager import BalanceManager
from .notification_manager import NotificationManager
from .scheduler import MessageScheduler
from .media_handler import MediaHandler
from .message_processor import MessageProcessor
from .hybrid_processor import HybridProcessor
# Import unified messenger
from .unified_messenger import get_unified_messenger, MessageRole

load_dotenv()

# Import worker registry for tracking active workers
from worker_registry import worker_registry

# Admin notification settings
PAYMENT_CONTACT = os.getenv('PAYMENT_CONTACT', '@magellanvs')


class TelegramWorker:
    """Основной класс для работы с Telegram"""
    
    def __init__(self, user_id: int):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")

        if not self.api_id or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are required")

        self.user_id = user_id
        self.logger = self._setup_logging(user_id)

        # Log worker initialization start
        self.logger.info(f"🚀 Initializing TelegramWorker for user {user_id}")

        # Initialize unified messenger for all communication
        self.messenger = get_unified_messenger(user_id)
        self.messenger.logger = self.logger  # Set logger
        self.user_logger = self.messenger  # Compatibility alias
        self.logger.info("📱 Unified messenger initialized for all communication")

        self.channel_rules = []
        self.auto_scheduled = False
        self.http_session = None
        self.is_processing = True  # Flag to control message processing

        # Log S3 managers initialization
        self.logger.info("☁️ Initializing S3 managers...")
        self.s3_manager = S3SessionManager()
        self.s3_avatar_manager = S3AvatarManager()
        self.logger.info("✅ S3 managers initialized successfully")

        # Log processors initialization
        self.logger.info("🧠 Initializing AI and processing components...")
        self.ai_processor = AIProcessor(self.logger, self._log_worker_status)
        self.balance_manager = BalanceManager(self.logger)
        self.notification_manager = NotificationManager(
            user_id, self.logger, self._get_http_session, self._send_websocket_log
        )
        self.scheduler = MessageScheduler(
            None,
            self.logger,
            self._notify_admin_critical_error,
            self._log_worker_status,
            self.handle_flood_wait
        )
        self.media_handler = MediaHandler(
            user_id, None, self.logger,
            self._process_text_content_for_album,
            self._get_last_pending_scheduled_time,
            self._resolve_channel_identifier,
            self._deduct_balance_async,
            self._notify_admin_critical_error,
            self._process_with_hyperbolic_async
        )
        self.logger.info("✅ Processing components initialized successfully")

        # Initialize heartbeat tracking
        self.heartbeat_interval = 300  # 5 minutes
        self.last_heartbeat = datetime.now(timezone.utc)
        self.heartbeat_task = None
        self.stats = {
            'messages_processed': 0,
            'rules_executed': 0,
            'errors_count': 0,
            'last_activity': None,
            'start_time': datetime.now(timezone.utc)
        }
        self.logger.info("💓 Heartbeat monitoring initialized")

        # Session and client will be initialized later
        self.session_dir = None
        self.session_file = None
        self.client = None

        # Client warm-up tracking
        self._client_warmed_up = False

        # Send initialization status (will be replaced by next status in async initialize)
        # Add AI processing callback to media handler
        self.media_handler._process_with_hyperbolic_callback = self._process_with_hyperbolic_async
        self.message_processor = MessageProcessor(
            user_id, self.logger,
            self.media_handler, self.ai_processor, self.balance_manager,
            self.scheduler, self.notification_manager,
            self._resolve_channel_identifier, self._log_worker_status,
            self._update_worker_activity, self._get_message_via_raw_api,
            self._log_scheduled_post, self._log_insufficient_funds_post,
            self._log_worker_error, self._send_websocket_log,
            self._update_stats  # Add stats update callback
        )
        # Add AI processing callback to message processor
        self.message_processor._process_with_hyperbolic_callback = self._process_with_hyperbolic_async

        # Initialize hybrid processor
        self.hybrid_processor = HybridProcessor(self)
        self.logger.info("✅ All processing components initialized successfully")

        # Session setup - добавляем PID для уникальности
        import os as os_module
        process_id = os_module.getpid()
        self.session_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
        self.session_path = os.path.join(self.session_dir, f"{user_id}_{process_id}.session")
        os.makedirs(self.session_dir, exist_ok=True)

        self.logger.info(f"📁 Session directory: {self.session_dir}")
        self.logger.info(f"📄 Session file: {os.path.basename(self.session_path)}")

        # Download session from S3
        self.logger.info("☁️ Checking for existing session in S3...")
        if self.s3_manager.session_exists(user_id):
            self.logger.info("📥 Session found in S3, downloading...")
            # Note: We can't await here because __init__ is not async
            # Will send status update in async initialize method
            self.s3_manager.download_session(user_id, self.session_path)
            self.logger.info("✅ Session downloaded successfully from S3")
        else:
            error_msg = f"No session found in S3 for user {user_id}"
            self.logger.error(error_msg)
            raise ValueError(f"No session found for user {user_id}. Authorization required.")

        self.logger.info("🔧 Creating Telegram client...")
        self.client = Client(
            name=os.path.splitext(os.path.basename(self.session_path))[0],
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=self.session_dir
        )

        # Update processors with client
        self.scheduler.client = self.client
        self.media_handler.client = self.client

        self.logger.info("🎯 TelegramWorker initialization completed successfully")
        # Note: We can't await here because __init__ is not async
        # Will send initialization complete log in async initialize method

    async def initialize(self):
        """Async initialization that must be called after object creation"""
        # Send status updates that we couldn't send in __init__
        if self.s3_manager.session_exists(self.user_id):
            await self.messenger.send("session_found_s3", MessageRole.INTERNAL_LOG, level="info")
        
        # No need for success report here - will be sent when connected to Telegram

    def _setup_logging(self, user_id: int):
        """Sets up structured JSON logging for the worker."""
        worker_logger = logging.getLogger(f"worker_{user_id}")
        worker_logger.setLevel(logging.INFO)

        if worker_logger.handlers:
            worker_logger.handlers.clear()

        log_handler = logging.StreamHandler()
        # Fix JsonFormatter import issue
        from pythonjsonlogger.json import JsonFormatter
        formatter = JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(user_id)s'
        )
        log_handler.setFormatter(formatter)
        worker_logger.addHandler(log_handler)

        adapter = logging.LoggerAdapter(worker_logger, {'user_id': user_id})
        return adapter

    async def _load_rules_from_db(self):
        """Load channel rules from database"""
        try:
            self.logger.info("📋 Loading channel rules from database...")
            await self.messenger.send("loading_rules_db", MessageRole.INTERNAL_LOG, level="info")
            
            # Get database connection using context manager for proper cleanup
            async with async_session() as db_session:  # type: ignore
                # Query rules for this user with selectinload for model relationship
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                stmt = select(ChannelPair).where(ChannelPair.user_id == self.user_id).options(selectinload(ChannelPair.model))
                result = await db_session.execute(stmt)
                rules = result.scalars().all()
                
                self.channel_rules = rules
                
                # Log detailed statistics
                total_rules = len(rules)
                
                self.logger.info(f"✅ Loaded {total_rules} channel rules from database")
                
                # Status only - no permanent report for loading rules
            
        except Exception as e:
            error_msg = f"Failed to load rules from database: {str(e)}"
            self.logger.error(error_msg)
            await self.messenger.send("rules_loading_error", MessageRole.USER_REPORT,
                               report_type="error", error=str(e))
            raise

    async def reload_rules(self):
        """Reload channel rules from database."""
        await self._load_rules_from_db()
        return len(self.channel_rules)

    def pause_processing(self):
        """Pause message processing."""
        self.is_processing = False
        self.logger.info(get_localized_message("processing_paused", message_id=""))

    def resume_processing(self):
        """Resume message processing."""
        self.is_processing = True
        self.logger.info(get_localized_message("processing_resumed"))

    async def get_status(self) -> Dict[str, Any]:
        """Get current worker status."""
        balance = None
        last_activity = None
        
        # Get last activity from worker_registry
        worker_info = worker_registry.get_worker_info(self.user_id)
        if worker_info:
            last_activity = worker_info.get('last_activity')
        
        async with async_session() as db:  # type: ignore
            # Get user balance
            user = await db.get(User, self.user_id)
            if user:
                balance = float(user.balance)
        
        return {
            "user_id": self.user_id,
            "status": "active" if self.is_connected() else "disconnected",
            "is_connected": self.is_connected(),
            "is_processing": self.is_processing,
            "rules_count": len(self.channel_rules),
            "last_activity": last_activity,
            "current_balance": balance,
            "auto_scheduled": getattr(self, "auto_scheduled", False)
        }

    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Get localized message for logging."""
        return get_localized_message(key, **kwargs)

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

    async def _get_http_session(self):
        """Get or create HTTP session."""
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(json_serialize=json.dumps)
        return self.http_session

    async def _close_http_session(self):
        """Close HTTP session."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            self.http_session = None

    # Delegate methods to processors
    async def _notify_admin_critical_error(self, error_type: str, error_message: str, user_info: Optional[dict] = None):
        """Send critical error notification to admin."""
        await self.notification_manager.notify_admin_critical_error(error_type, error_message, user_info if user_info is not None else {})

    async def _process_with_hyperbolic_async(self, system_content: str, user_content: str,
                                             model_name: str, temperature: float,
                                             top_p: float, max_tokens: int) -> Optional[str]:
        """Process text with Hyperbolic API."""
        session = await self._get_http_session()
        return await self.ai_processor.process_with_hyperbolic(
            system_content, user_content, model_name, temperature, 
            top_p, max_tokens, session
        )

    async def _get_last_pending_scheduled_time(self, target_channel_id: int) -> Optional[datetime]:
        """Gets the datetime of the last scheduled message in the target channel."""
        return await self.scheduler.get_last_pending_scheduled_time(target_channel_id)

    async def _deduct_balance_async(self, db_session, user_id: int, model_id: Optional[int] = None) -> bool:
        """Deduct balance from user account."""
        return await self.balance_manager.deduct_balance(db_session, user_id, model_id)

    async def _send_insufficient_balance_notification(self, rule, target_channel_id: int, notification_message: str):
        """Send insufficient balance notification after successful post that resulted in negative balance."""
        await self.balance_manager.send_insufficient_balance_notification(
            self.client, rule, target_channel_id, notification_message, self._determine_schedule_time
        )

    async def _send_auth_required_signal(self, error_type: str, message: str):
        """Send signal to parent process that auth is required."""
        await self.notification_manager.send_auth_required_signal(error_type, message)

    async def _determine_schedule_time(self, rule, target_channel_id: int) -> datetime:
        """Calculate scheduled time for post."""
        return await self.scheduler.determine_schedule_time(rule, target_channel_id)

    async def _schedule_text_message(self, text: str, target_channel_id: int,
                                     schedule_time: datetime) -> Optional[Message]:
        """Schedule text message to target channel."""
        return await self.scheduler.schedule_text_message(
            text, target_channel_id, schedule_time, 
            self._update_worker_status, self.disconnect
        )

    async def _handle_media_group(self, message: Message, rule):
        """Handle media group (album) messages."""
        return await self.media_handler.handle_media_group(message, rule)

    async def _process_text_content_for_album(self, rule, text: str) -> tuple[str, bool]:
        """Process text content for album with fallback handling."""
        return await self.media_handler.process_text_content_for_album(rule, text)

    async def _on_new_message(self, client: Client, message: Message):
        """Main handler for new messages."""
        
        # Update message statistics
        self._update_stats('messages_processed')
        
        # Add debugging to ensure we're receiving messages
        try:
            bot_username = None
            # Attempt to get bot username via API base
            # We rely on bot to store its username in the bot application, not here
            # Basic filter: ignore messages from bot account by username if present
            if hasattr(message, 'from_user') and message.from_user:
                from_username = getattr(message.from_user, 'username', None)
                if from_username and from_username.lower().startswith('taiger'):
                    self.logger.info("Ignoring message from bot-like username to prevent loop")
                    return
        except Exception:
            pass
        self.logger.info(f"📥 Message received by handler: {message.id} from chat {message.chat.id}")
        
        # Mark processing start to prevent timeout during AI processing
        await self._notify_processing_start(message.id)

        try:
            await self.message_processor.on_new_message(client, message, self.channel_rules, self.is_processing)
        finally:
            # Always mark processing as finished, even if an error occurred
            await self._notify_processing_finish()

    # Placeholder methods that need to be implemented or moved
    async def _update_worker_activity(self):
        """Update worker activity timestamps in database and registry."""
        # This method is quite complex and should be moved to a separate component
        # For now, keeping a simplified version
        worker_registry.update_last_activity(self.user_id)

    async def _update_worker_status(self, status: str, error_msg: Optional[str] = None):
        """Update worker status - only critical statuses go to DB."""
        self.logger.info(f"Worker status: {status}")

        # Register worker in registry when active
        if status == 'active':
            import os as os_module

            # Get VIP level from database
            vip_level = 0
            try:
                async with async_session() as db_session:  # type: ignore
                    user = await db_session.get(User, self.user_id)
                    if user:
                        vip_level = user.VIP_level
            except Exception as e:
                self.logger.error(f"Failed to get VIP level: {e}")

            # FIX: Register in local registry with proper error handling
            try:
                worker_registry.add_worker(self.user_id, os_module.getpid(), vip_level, auto_scheduled=getattr(self, "auto_scheduled", False))
                self.logger.info(f"Worker {self.user_id} registered in WorkerRegistry with PID {os_module.getpid()}, VIP {vip_level}")
                # Store VIP level in worker instance for later use
                self.vip_level = vip_level
            except Exception as e:
                self.logger.error(f"Failed to register worker in local registry: {e}")
                return  # Don't proceed if local registration fails

            # DIAGNOSTIC: Check if worker is actually registered
            is_registered = worker_registry.is_worker_running(self.user_id)
            worker_info = worker_registry.get_worker_info(self.user_id)
            self.logger.info(f"DIAGNOSTIC: Worker {self.user_id} registration check - is_running: {is_registered}, info: {worker_info}")

            # FIX: Verify registration was successful
            if not is_registered:
                self.logger.error(f"CRITICAL: Worker {self.user_id} registration failed - not found in registry after registration")
                return

            # Also register in API server through HTTP (in background)
            asyncio.create_task(self._register_worker_in_api())
            self.logger.info("🔄 Worker registration started in background")

    async def _log_worker_status(self, status_type: str, message_key: str, level: str = "info", **params):
        """Redirect to UnifiedMessenger to prevent duplication and fix localization."""
        # Use WEBSOCKET_LOG for WebSocket/TMA logs, not bot logs
        await self.messenger.send(message_key, MessageRole.WEBSOCKET_LOG, level=level, **params)

    async def _send_websocket_log(self, log_type: str, message_key: str, level: str = "info", **params):
        """Redirect to UnifiedMessenger to prevent duplication and fix localization."""
        # Use WEBSOCKET_LOG for WebSocket/TMA logs
        await self.messenger.send(message_key, MessageRole.WEBSOCKET_LOG, level=level, **params)

    async def handle_flood_wait(self, wait_seconds: int, context: str):
        """Centralized flood wait handling with user and dashboard logging."""
        safe_wait = max(int(wait_seconds), 1)
        message = f"⏳ Flood wait {safe_wait}s during {context}. Retrying after delay."

        self.logger.warning(message)

        await self._log_worker_status(
            "telegram_flood_wait",
            "log_telegram_flood_wait",
            "warning",
            time=safe_wait,
            context=context
        )

        await self._send_websocket_log(
            "flood_wait",
            message,
            "warning",
            context=context,
            seconds=safe_wait
        )

        # Send status update (transient)
        try:
            await self._log_worker_status("flood_wait", f"⏳ Flood wait: {safe_wait} seconds", "warning")
        except Exception as e:
            self.logger.debug(f"Failed to send flood wait status to user: {e}")

        await asyncio.sleep(safe_wait)

    async def _get_message_via_raw_api(self, message: Message) -> str:
        """Try to get message text using raw Telegram API."""
        # Simplified version - return empty string for now
        return ""

    async def _log_scheduled_post(self, db_session, rule_id: int, message: Message,
                                  target_channel_id: int, scheduled_msg: Message,
                                  scheduled_time: datetime, text_content: str,
                                  balance_after: Optional[float] = None):
        """Log scheduled post to database."""
        # Simplified version - basic logging
        try:
            post = ScheduledPost(
                user_id=self.user_id,
                channel_pair_id=rule_id,
                source_channel_id=str(message.chat.id),
                target_channel_id=str(target_channel_id),
                content=text_content,
                media_type="text",
                original_message_id=message.id,
                scheduled_at=scheduled_time,
                message_id=scheduled_msg.id if scheduled_msg else None,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(post)
            await db_session.commit()
        except Exception as e:
            self.logger.error(f"Failed to log scheduled post: {e}")

    async def _log_insufficient_funds_post(self, db_session, rule, message: Message, error_msg: str):
        """Log insufficient funds as a post in the journal."""
        # Simplified version
        self.logger.warning(f"Insufficient funds: {error_msg}")

    async def _log_worker_error(self, db_session, rule, message: Message, error_type: str, error_msg: str):
        """Log worker error to database."""
        # Simplified version
        self.logger.error(f"Worker error: {error_type} - {error_msg}")

    async def _resolve_channel_identifier(self, channel_id: Any) -> Optional[int]:
        """Convert channel identifier to Telegram ID."""
        try:
            self.logger.info(f"🔍 Resolving channel identifier: {channel_id} (type: {type(channel_id)})")
            # Send status update to user only for important cases
            # Removed technical status update to reduce noise
        # await self.user_logger.send_status_update(f"🔍 Resolving channel: {channel_id}", "info")
            
            # Если это уже число 
            if isinstance(channel_id, int):
                resolved_id = int(channel_id)
                self.logger.info(f"✅ Resolved numeric channel: {channel_id} → {resolved_id}")
                # Send status update to user only for important cases
                # Removed technical status update to reduce noise
                # await self.user_logger.send_status_update(f"✅ Resolved numeric channel: {channel_id}", "info")
                return resolved_id
            
            # Если это строка 
            if isinstance(channel_id, str):
                # Проверяем, является ли строка числом (включая отрицательные)
                try:
                    resolved_id = int(channel_id)
                    self.logger.info(f"✅ Resolved numeric string channel: {channel_id} → {resolved_id}")
                    # Removed technical status update to reduce noise
                    # await self.user_logger.send_status_update(f"✅ Resolved numeric string channel: {channel_id}", "info")
                    return resolved_id
                except ValueError:
                    pass  # Не число, продолжаем проверку username
            
            # Используем username
            if isinstance(channel_id, str) and channel_id.startswith('@'):
                self.logger.info(f"🔍 Looking up username: {channel_id}")
                try:
                    chat = await self.client.get_chat(channel_id)
                    chat_id = getattr(chat, 'id', None)
                    chat_title = getattr(chat, 'title', 'Unknown')
                    if chat_id is not None:
                        self.logger.info(f"✅ Resolved username: {channel_id} → {chat_id} ({chat_title})")
                        return chat_id
                except PeerIdInvalid:
                    self.logger.warning(f"⚠️ PEER_ID_INVALID при резолвинге username {channel_id}. Пробуем прогреть сессию...")
                    # Прогреваем сессию и пытаемся снова
                    await self._warm_up_client(limit=5)
                    try:
                        chat = await self.client.get_chat(channel_id)
                        chat_id = getattr(chat, 'id', None)
                        chat_title = getattr(chat, 'title', 'Unknown')
                        if chat_id is not None:
                            self.logger.info(f"✅ Повторное разрешение username: {channel_id} → {chat_id}")
                            return chat_id
                    except Exception as e2:
                        self.logger.error(f"❌ Повторная попытка не удалась: {e2}")
                        user_lang = await self.user_logger._get_user_language()
                        error_message = get_localized_message(
                            "channel_not_found",
                            lang=user_lang,
                            channel=channel_id,
                            error=str(e2)
                        )
                        await self.user_logger.send_report(error_message, "error")
                        return None
                except Exception as e:
                    self.logger.error(f"❌ Failed to resolve username {channel_id}: {e}")
                    user_lang = await self.user_logger._get_user_language()
                    error_message = get_localized_message(
                        "channel_not_found",
                        lang=user_lang,
                        channel=channel_id,
                        error=str(e)
                    )
                    await self.user_logger.send_report(error_message, "error")
                    return None
            
            self.logger.warning(f"⚠️ Unknown channel identifier format: {channel_id}")
            user_lang = await self.user_logger._get_user_language()
            error_message = get_localized_message(
                "channel_unknown_format",
                lang=user_lang,
                channel=channel_id
            )
            await self.user_logger.send_report(error_message, "warning")
            return None
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ Failed to resolve channel {channel_id}: {error_msg}")
            user_lang = await self.user_logger._get_user_language()
            error_message = get_localized_message(
                "channel_access_error",
                lang=user_lang,
                channel=channel_id,
                error=error_msg
            )
            await self.user_logger.send_report(error_message, "error")
            return None

    async def connect(self):
        """Connect to Telegram"""
        try:
            self.logger.info("🔌 Connecting to Telegram...")
            await self._log_worker_status("connecting", "🔌 Connecting to Telegram...", "info")
            
            await self.client.start()
            
            # Get user info after connection
            me = await self.client.get_me()
            self.logger.info(f"✅ Connected to Telegram as @{me.username} (ID: {me.id})")
            
            # Update user avatar if needed
            self.logger.info("🖼️ Checking user avatar...")
            # Запускаем загрузку аватара в фоновом режиме
            asyncio.create_task(self._update_user_avatar_background())
            self.logger.info("🔄 Avatar update started in background")
            
            # Send connection status (transient - can be overwritten)
            await self.messenger.send("connected_as", MessageRole.USER_STATUS, username=me.username)
            
        except Exception as e:
            # Update error statistics
            self._update_stats('errors_count')
            
            error_type = type(e).__name__
            error_msg = str(e)
            self.logger.error(f"Failed to connect to Telegram: {error_msg}", exc_info=True)
            
            # Determine error context and recommendations
            recommendations = []
            context = {
                "error_type": error_type,
                "session_file": os.path.basename(self.session_path),
                "user_id": str(self.user_id)
            }
            
            # Provide more specific error messages based on the actual error
            if "AuthKeyUnregistered" in error_type or "AuthKeyUnregistered" in error_msg:
                recommendations.extend([
                    "Сессия устарела или была отозвана",
                    "Необходимо пройти повторную авторизацию через Telegram",
                    "Удалите текущую сессию и создайте новую"
                ])
                context["issue"] = "session_expired"
                context["solution"] = "Пожалуйста, авторизуйтесь заново через Telegram"
            elif "UserDeactivated" in error_type or "UserDeactivated" in error_msg:
                recommendations.extend([
                    "Аккаунт Telegram заблокирован или деактивирован",
                    "Проверьте статус аккаунта в официальном приложении Telegram",
                    "Обратитесь в поддержку Telegram если необходимо"
                ])
                context["issue"] = "account_blocked"
                context["solution"] = "Проверьте статус вашего аккаунта в Telegram"
            elif "FloodWait" in error_type or "FloodWait" in error_msg:
                import re
                wait_time_match = re.search(r"(\d+)", error_msg)
                wait_time = wait_time_match.group(1) if wait_time_match else "несколько"
                recommendations.extend([
                    f"Превышен лимит запросов к API Telegram",
                    f"Подождите {wait_time} секунд перед повторной попыткой",
                    "Уменьшите частоту операций"
                ])
                context["issue"] = "rate_limit"
                context["wait_time"] = wait_time
                context["solution"] = f"Подождите {wait_time} секунд и попробуйте снова"
            elif "PhoneNumberUnoccupied" in error_type or "PhoneNumberUnoccupied" in error_msg:
                recommendations.extend([
                    "Номер телефона не зарегистрирован в Telegram",
                    "Проверьте правильность введенного номера",
                    "Убедитесь, что у вас есть аккаунт Telegram"
                ])
                context["issue"] = "phone_not_registered"
                context["solution"] = "Проверьте номер телефона и убедитесь, что у вас есть аккаунт Telegram"
            elif "ApiIdInvalid" in error_type or "ApiIdInvalid" in error_msg:
                recommendations.extend([
                    "Неверные учетные данные API Telegram",
                    "Свяжитесь с технической поддержкой"
                ])
                context["issue"] = "invalid_api_credentials"
                context["solution"] = "Свяжитесь с технической поддержкой"
            elif "ConnectionError" in error_msg or "timeout" in error_msg.lower():
                recommendations.extend([
                    "Проблемы с сетевым подключением",
                    "Проверьте интернет-соединение",
                    "Попробуйте перезапустить воркер через несколько минут"
                ])
                context["issue"] = "network_error"
                context["solution"] = "Проверьте интернет-соединение и попробуйте снова"
            elif "SessionPasswordNeeded" in error_type or "SessionPasswordNeeded" in error_msg:
                recommendations.extend([
                    "Требуется двухфакторная аутентификация",
                    "Введите ваш пароль двухфакторной аутентификации"
                ])
                context["issue"] = "2fa_required"
                context["solution"] = "Введите ваш пароль двухфакторной аутентификации"
            else:
                recommendations.extend([
                    "Неизвестная ошибка подключения к Telegram",
                    "Проверьте логи для получения дополнительной информации",
                    "Обратитесь в техническую поддержку"
                ])
                context["issue"] = "unknown_error"
                context["solution"] = "Обратитесь в техническую поддержку"
            
            # Send error report to user (permanent)
            solution = context.get("solution", "Обратитесь в поддержку")
            await self.user_logger.send_report(f"Ошибка подключения: {error_msg}\n{solution}", "error")
            raise

    async def _update_user_avatar(self):
        """Update user avatar in S3"""
        try:
            self.logger.info("📸 Updating user avatar...")
            # Get current user info
            me = await self.client.get_me()
            
            if me and me.photo:
                # Download avatar photo
                avatar_data = await self.client.download_media(me.photo.big_file_id, in_memory=True)
                if avatar_data:
                    # Handle different types of avatar data
                    if isinstance(avatar_data, bytes):
                        avatar_bytes = avatar_data
                    elif hasattr(avatar_data, 'getbuffer'):
                        # BytesIO object
                        avatar_bytes = bytes(avatar_data.getbuffer())
                    elif hasattr(avatar_data, 'read'):
                        # Reset position and read all data
                        avatar_data.seek(0)
                        avatar_bytes = avatar_data.read()
                    elif isinstance(avatar_data, memoryview):
                        # Convert memoryview to bytes
                        avatar_bytes = bytes(avatar_data)
                    else:
                        # Try to convert to bytes
                        avatar_bytes = bytes(avatar_data)
                    
                    # Upload avatar to S3 only if we have actual data
                    if avatar_bytes and len(avatar_bytes) > 0:
                        result = self.s3_avatar_manager.update_user_avatar(self.user_id, avatar_bytes)
                        if result:
                            self.logger.info("✅ User avatar updated successfully")
                        else:
                            self.logger.info("ℹ️ Failed to update avatar in S3")
                    else:
                        self.logger.info("ℹ️ Failed to download avatar or avatar is empty")
                else:
                    self.logger.info("ℹ️ Failed to download avatar or avatar is empty")
            else:
                self.logger.info("ℹ️ No avatar to update")
                
        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"⚠️ Failed to update user avatar: {e}"
            self.logger.warning(error_msg, exc_info=True)
            
            # Determine error context and recommendations
            recommendations = []
            context = {
                "error_type": error_type,
                "user_id": str(self.user_id),
                "operation": "avatar_update"
            }
            
            if "ConnectionError" in error_type or "timeout" in str(e).lower():
                recommendations.extend([
                    "Проблемы с сетевым подключением при обновлении аватара",
                    "Аватар будет обновлен при следующем подключении",
                    "Это не критическая ошибка"
                ])
                context["issue"] = "network_avatar"
            elif "PermissionError" in error_type or "Forbidden" in str(e):
                recommendations.extend([
                    "Недостаточно прав для получения информации о пользователе",
                    "Проверьте настройки приватности аккаунта",
                    "Аватар не будет обновлен"
                ])
                context["issue"] = "permission_avatar"
            elif "S3" in str(e) or "AWS" in str(e):
                recommendations.extend([
                    "Ошибка загрузки аватара в облачное хранилище",
                    "Проверьте настройки S3",
                    "Аватар не будет сохранен"
                ])
                context["issue"] = "s3_avatar"
            else:
                recommendations.extend([
                    "Неизвестная ошибка при обновлении аватара",
                    "Аватар не будет обновлен",
                    "Это не влияет на основную функциональность"
                ])
                context["issue"] = "unknown_avatar"
            
            # Non-critical - don't send report, just log
            # Don't raise exception as this is not critical

    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client and self.client.is_connected:
            try:
                self.logger.info("🔌 Disconnecting from Telegram...")
                await self.client.stop()
                self.logger.info("✅ Client disconnected successfully")
            except Exception as e:
                # Update error statistics
                self._update_stats('errors_count')
                self.logger.error(f"❌ Error stopping client: {e}", exc_info=True)
                # Non-critical disconnect error - don't report
        await self._close_http_session()
        
        # Close user logger session as well
        try:
            await self.messenger.close()
        except Exception as e:
            self.logger.debug(f"Failed to close unified messenger session: {e}")

        # Clear the unified messenger instance to prevent reuse
        from .unified_messenger import remove_unified_messenger
        remove_unified_messenger(self.user_id)

    def is_connected(self):
        """Check if client is connected"""
        return self.client and self.client.is_connected

    async def start_listening(self):
        """Start listening for messages"""
        self.logger.info("🎧 Starting message listening...")
        
        if not self.is_connected():
            await self.connect()
        
        if self.is_connected():
            # Load rules from database
            await self._load_rules_from_db()
            
            # Add message handler with proper filters to ensure all messages are received
            from pyrogram import filters
            self.client.add_handler(MessageHandler(self._on_new_message, filters.all))
            
            self.logger.info("listening_started")
            
            # Send individual status messages (temporary, will be overwritten)
            await self.messenger.send("agent_ready", MessageRole.USER_STATUS)

            # Check if we have batch processing results from hybrid_processor
            batch_info = getattr(self.hybrid_processor, '_batch_processed_count', None)
            batch_rules = getattr(self.hybrid_processor, '_batch_rules_count', None)
            if batch_info is not None and batch_rules is not None:
                await self.messenger.send("batch_processing_summary", MessageRole.USER_STATUS,
                                        posts=batch_info, rules=batch_rules)
                # Clear the batch info after using
                self.hybrid_processor._batch_processed_count = None
                self.hybrid_processor._batch_rules_count = None

            # Send tracking rules status
            await self.messenger.send("tracking_rules", MessageRole.USER_STATUS,
                                    count=len(self.channel_rules))
            
            # Then show waiting status (transient)
            await self.messenger.send("agent_waiting_status", MessageRole.INTERNAL_LOG, level="info")
        else:
            self.logger.error("❌ Worker failed to connect")
            await self.messenger.send("start_failed_no_connection", MessageRole.USER_REPORT, report_type="error")

    async def start_message_listener(self):
        """Запуск прослушивания новых сообщений (для гибридной обработки)"""
        await self.start_listening()
    
    async def get_messages_after_id(self, channel_id: str, after_id: int, limit: int = 100) -> list[Message]:
        """Получение сообщений после определенного ID"""
        try:
            # Проверяем подключение к Telegram
            if not self.is_connected():
                await self.log_message(f"❌ Ошибка получения сообщений из {channel_id}: Client has not been started yet")
                return []

            # Резолвим канал (включая прогрев при необходимости)
            resolved_channel_id = await self._resolve_channel_identifier(channel_id)
            if not resolved_channel_id:
                await self.log_message(f"❌ Не удалось разрешить канал {channel_id}")
                return []

            await self.log_message(f"🔍 Канал {channel_id} разрешен в ID: {resolved_channel_id} (тип: {type(resolved_channel_id)})")

            # Прогреваем клиент перед любыми вызовами
            await self._warm_up_client(limit=5)

            # Определяем original_identifier до вызова get_chat
            original_identifier = channel_id if (isinstance(channel_id, str) and channel_id.startswith('@')) else resolved_channel_id

            # Получаем объект Chat для прогрузки access_hash
            chat_id_for_history = resolved_channel_id  # Значение по умолчанию
            try:
                chat = await self.client.get_chat(original_identifier)
                chat_id = getattr(chat, 'id', None)
                chat_title = getattr(chat, 'title', 'Unknown')
                if chat_id is not None:
                    chat_id_for_history = chat_id
                    await self.log_message(f"✅ get_chat успешен: {chat_title} (id={chat_id}). Использование chat.id для истории: {chat_id}")
            except Exception as ge:
                await self.log_message(f"⚠️ Не удалось выполнить get_chat для {original_identifier}: {str(ge)}. Продолжаем с resolved ID.")
                # Используем исходный ID как есть

            # Получаем историю сообщений
            messages = []
            await self.log_message(f"🔍 Начинаем получение истории чата для {chat_id_for_history}...")

            # Пытаемся получить сообщения
            try:
                async for message in self.client.get_chat_history(  # type: ignore
                    chat_id_for_history,
                    limit=limit * 2  # Запас, т.к. будем фильтровать
                ):
                    if message.id <= after_id:
                        break
                    
                    # Фильтруем только сообщения с текстом или медиа с подписью
                    if message.text or (message.media and message.caption):
                        messages.append(message)
                    
                    if len(messages) >= limit:
                        break

                # Сортируем по ID (от старых к новым)
                messages.sort(key=lambda x: x.id)
                await self.log_message(f"✅ Успешно получено {len(messages)} сообщений из канала {chat_id_for_history}")
                return messages

            except Exception as history_error:
                if "PEER_ID_INVALID" in str(history_error):
                    await self.log_message(f"⚠️ Канал {channel_id} недоступен (PEER_ID_INVALID). Возможно, не загружен access_hash.")
                    return []
                else:
                    await self.log_message(f"❌ Ошибка получения истории сообщений из {channel_id}: {str(history_error)}")
                    return []

        except Exception as e:
            await self.log_message(f"❌ Общая ошибка получения сообщений из {channel_id}: {str(e)}")
            return []

    async def get_channel_pairs(self):
        """Получение правил обработки каналов из БД"""
        async with async_session() as db_session:  # type: ignore
            result = await db_session.execute(
                select(ChannelPair)
                .where(ChannelPair.user_id == self.user_id)
                .options(selectinload(ChannelPair.model))
            )
            return result.scalars().all()
    
    async def process_single_message(self, message, channel_pair):
        """Обработка одного сообщения (для гибридной обработки)"""
        try:
            # Используем существующий message_processor
            return await self.message_processor.process_message(message, channel_pair, self.client)
        except Exception as e:
            self.logger.error(f"Error processing message {message.id}: {e}")
            return False
    
    async def _warm_up_client(self, limit: int = 10):
        """Прогревает клиент — грузит несколько диалогов."""
        if self._client_warmed_up:
            self.logger.debug("🔄 Клиент уже прогрет, пропускаем")
            return True

        try:
            self.logger.info("🔄 Прогрев клиента: загрузка диалогов...")
            count = 0
            async for dialog in self.client.get_dialogs(limit=limit):  # type: ignore
                count += 1
                if count >= limit:
                    break
            self.logger.info(f"✅ Прогрето {count} диалогов")
            self._client_warmed_up = True
            return True
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка прогрева: {e}")
            return False
    
    async def log_message(self, message: str):
        """Логирование сообщения в журнал агента"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Отправляем через WebSocket
        await self._send_websocket_log("worker_log", log_entry, "info")
        
        # Также логируем в обычный лог
        self.logger.info(message)
        
        # Don't send to Telegram bot - this is for debug/websocket only

    async def _start_heartbeat(self):
        """Start periodic heartbeat logging."""
        self.logger.info("💓 Starting heartbeat monitoring")
        
        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(self.heartbeat_interval)
                    await self._send_heartbeat()
                except asyncio.CancelledError:
                    self.logger.info("💓 Heartbeat monitoring stopped")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Error in heartbeat loop: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        self.heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    async def _send_heartbeat(self):
        """Send heartbeat log with worker statistics."""
        current_time = datetime.now(timezone.utc)
        uptime = current_time - self.stats['start_time']
        
        # Calculate uptime in human-readable format
        uptime_hours = int(uptime.total_seconds() // 3600)
        uptime_minutes = int((uptime.total_seconds() % 3600) // 60)
        uptime_str = f"{uptime_hours}h {uptime_minutes}m"
        
        # Get current balance
        current_balance = None
        try:
            async with async_session() as session:
                user = await session.get(User, self.user_id)
                if user:
                    current_balance = user.balance
        except Exception as e:
            self.logger.warning(f"⚠️ Could not fetch balance for heartbeat: {e}")
        
        # Prepare heartbeat message
        heartbeat_msg = (
            f"💓 Worker heartbeat - Uptime: {uptime_str}, "
            f"Messages: {self.stats['messages_processed']}, "
            f"Rules: {self.stats['rules_executed']}, "
            f"Errors: {self.stats['errors_count']}"
        )
        
        if current_balance is not None:
            heartbeat_msg += f", Balance: ${{current_balance:.2f}}"
        
        # Log heartbeat
        self.logger.info(heartbeat_msg)
        
        # Don't send heartbeat to Telegram bot - too noisy
        # Heartbeat is for internal monitoring only
        
        # Update last heartbeat time
        self.last_heartbeat = current_time
        # Note: last_activity is updated via heartbeat API call to the backend
    
    def _update_stats(self, stat_type: str):
        """Update worker statistics."""
        if stat_type in self.stats:
            self.stats[stat_type] += 1
        self.stats['last_activity'] = datetime.now(timezone.utc)
    
    async def _notify_processing_start(self, message_id: int):
        """Notify API server that processing has started"""
        try:
            session = await self._get_http_session()
            async with session.post(
                f"{get_api_base_url()}/api/internal/worker-start-processing",
                json={
                    "user_id": self.user_id,
                    "message_id": message_id
                },
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    self.logger.debug(f"✅ Notified API server: processing started for message {message_id}")
                else:
                    self.logger.warning(f"⚠️ Failed to notify API server: HTTP {response.status}")
        except Exception as e:
            self.logger.debug(f"⚠️ Failed to notify processing start: {e}")

    async def _notify_processing_finish(self):
        """Notify API server that processing has finished"""
        try:
            session = await self._get_http_session()
            async with session.post(
                f"{get_api_base_url()}/api/internal/worker-finish-processing",
                json={
                    "user_id": self.user_id
                },
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status == 200:
                    self.logger.debug("✅ Notified API server: processing finished")
                else:
                    self.logger.warning(f"⚠️ Failed to notify API server: HTTP {response.status}")
        except Exception as e:
            self.logger.debug(f"⚠️ Failed to notify processing finish: {e}")
    async def _stop_heartbeat(self):
        """Stop heartbeat monitoring."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
            self.logger.info("💓 Heartbeat monitoring stopped")


    async def _register_worker_in_api(self):
        """Register worker in API server - non-critical, runs in background"""
        try:
            import aiohttp
            import os as os_module
            session = await self._get_http_session()
            async with session.post(
                f"{get_api_base_url()}/api/internal/register-worker",
                json={
                    "user_id": self.user_id,
                    "pid": os_module.getpid(),
                    "vip_level": self.vip_level
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self.logger.info(f"✅ Worker {self.user_id} registered in API server")
                else:
                    self.logger.warning(f"⚠️ Failed to register in API server: HTTP {response.status}")
        except Exception as e:
            self.logger.error(f"❌ Failed to register worker in API server: {e}")

    async def _update_user_avatar_background(self):
        """Update user avatar in background - non-critical operation"""
        try:
            await self._update_user_avatar()
        except Exception as e:
            self.logger.warning(f"⚠️ Background avatar update failed (non-critical): {e}")


__all__ = ['TelegramWorker']

