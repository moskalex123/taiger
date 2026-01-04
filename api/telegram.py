import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from telegram_bot.bot import get_telegram_bot
from telegram_bot.auth import TMAAuthenticator
from telegram_bot.update_tracker import update_tracker
from auth import create_jwt_token, get_current_user
from models import User, UserBotLogState
from db import get_db, async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timezone, timedelta
from balance_utils import get_start_balance
from redis_client import redis_get, redis_set, redis_delete
import time

# Cache for recently promoted message IDs to prevent status overwrites
_recently_promoted = {}  # user_id -> {message_id: timestamp}
_PROMOTION_GRACE_PERIOD = 30  # seconds

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()
tma_auth = TMAAuthenticator()

def clean_status_message(raw_message):
    """Функция для очистки сообщения от форматирования"""
    if not raw_message:
        return []
        
    clean_lines = []
    lines = raw_message.split('\n')
    
    # Технические строки, которые нужно пропустить
    skip_patterns = ["worker_id", "session_id", "user_id", "─"]
    # Символы форматирования для удаления
    format_chars = "│├└┌┐┘┤▌▐█▄▀[]"
    # HTML-теги для удаления
    html_tags = ["<b>", "</b>", "<pre>", "</pre>", "<code>", "</code>"]
    
    for line in lines:
        # Пропускаем технические строки
        if any(pattern in line.lower() for pattern in skip_patterns):
            continue
        
        # Удаляем символы форматирования
        for char in format_chars:
            line = line.replace(char, "")
        
        # Удаляем HTML-теги
        for tag in html_tags:
            line = line.replace(tag, "")
        
        # Добавляем только непустые строки
        if line.strip():
            clean_lines.append(line.strip())
            
    return clean_lines

class WebhookUpdate(BaseModel):
    """Telegram webhook update model"""
    update_id: int
    message: Dict[str, Any] | None = None
    callback_query: Dict[str, Any] | None = None
    inline_query: Dict[str, Any] | None = None

class TMAAuthRequest(BaseModel):
    """TMA authentication request model"""
    init_data: str

class TMAAuthResponse(BaseModel):
    """TMA authentication response model"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserLogRequest(BaseModel):
    """User log message request model"""
    user_id: int
    message: str
    log_type: str = "info"
    last_message_id: int | None = None
    is_important: bool = False  # Флаг важности сообщения

class UserStatusUpdateRequest(BaseModel):
    """User status update request model"""
    user_id: int
    message: str
    log_type: str = "info"
    last_message_id: int | None = None


class BotStatusRequest(BaseModel):
    """Request model for transient status messages"""
    user_id: int
    telegram_id: int
    message: str
    last_status_message_id: int | None = None


class BotReportRequest(BaseModel):
    """Request model for permanent report messages"""
    user_id: int
    telegram_id: int
    message: str
    report_type: str = "success"  # success | error | warning
    last_status_message_id: int | None = None


def _status_redis_key(user_id: int) -> str:
    return f"status_message_id:{user_id}"


def _bot_status_redis_key(user_id: int) -> str:
    """Redis key for new bot status system."""
    return f"bot_status_msg:{user_id}"


def _worker_log_redis_key(user_id: int) -> str:
    return f"worker_log_message_id:{user_id}"


def _mark_message_promoted(user_id: int, message_id: int) -> None:
    """Mark a message as recently promoted to prevent status overwrites."""
    now = datetime.now(timezone.utc)
    if user_id not in _recently_promoted:
        _recently_promoted[user_id] = {}
    _recently_promoted[user_id][message_id] = now
    logger.debug(f"Marked message {message_id} as promoted for user {user_id}")


def _is_message_recently_promoted(user_id: int, message_id: int) -> bool:
    """Check if a message was recently promoted and should not be overwritten."""
    if user_id not in _recently_promoted:
        return False

    user_promotions = _recently_promoted[user_id]
    if message_id not in user_promotions:
        return False

    promotion_time = user_promotions[message_id]
    now = datetime.now(timezone.utc)

    # Clean up old entries
    cutoff = now - timedelta(seconds=_PROMOTION_GRACE_PERIOD)
    user_promotions_copy = user_promotions.copy()
    for msg_id, timestamp in user_promotions_copy.items():
        if timestamp < cutoff:
            del user_promotions[msg_id]

    # Check if this message is still within grace period
    if message_id in user_promotions:
        age = (now - user_promotions[message_id]).total_seconds()
        if age <= _PROMOTION_GRACE_PERIOD:
            logger.warning(f"[PROTECTED_MESSAGE] user={user_id} msg_id={message_id} age={age:.1f}s - refusing to delete")
            return True

    return False

@router.post("/telegram/webhook")
async def telegram_webhook(update: WebhookUpdate, request: Request):
    """Handle incoming Telegram webhook updates"""
    try:
        # Verify webhook secret if configured
        webhook_secret = os.getenv("TELEGRAM_BOT_SECRET")
        if webhook_secret:
            secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_header != webhook_secret:
                raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        # Prevent reprocessing of updates
        update_dict = update.dict()
        update_id = update_dict.get('update_id')
        if update_id and update_tracker.is_processed(update_id):
            logger.info(f"Ignoring already processed webhook update {update_id}")
            return {"status": "ok"}
        
        # Mark update as processed
        if update_id:
            update_tracker.mark_processed(update_id)
        
        # Process the update
        telegram_bot = get_telegram_bot()
        await telegram_bot.process_update(update_dict)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

@router.post("/telegram/set-webhook")
async def set_telegram_webhook():
    """Set webhook URL for the bot (admin endpoint)"""
    try:
        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        if not webhook_url:
            raise HTTPException(status_code=400, detail="TELEGRAM_WEBHOOK_URL not configured")
        
        telegram_bot = get_telegram_bot()
        await telegram_bot.set_webhook(webhook_url)
        
        return {"status": "success", "webhook_url": webhook_url}
        
    except Exception as e:
        logger.error(f"Set webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set webhook: {str(e)}")

@router.delete("/telegram/webhook")
async def remove_telegram_webhook():
    """Remove webhook (switch to polling) - admin endpoint"""
    try:
        telegram_bot = get_telegram_bot()
        await telegram_bot.remove_webhook()
        return {"status": "success", "message": "Webhook removed"}
        
    except Exception as e:
        logger.error(f"Remove webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove webhook: {str(e)}")

@router.post("/telegram/auth", response_model=TMAAuthResponse)
async def tma_authenticate(auth_request: TMAAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user via Telegram Mini App data and return JWT token"""
    try:
        # Validate Telegram WebApp init data
        validated_data = tma_auth.validate_telegram_data(auth_request.init_data)
        
        # Extract user information
        user_info = tma_auth.extract_user_info(validated_data)
        telegram_id = user_info["telegram_id"]
        
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Invalid Telegram user data")
        
        # Look for existing user using raw SQL to avoid ORM cache issues
        result = await db.execute(
            text("SELECT * FROM users WHERE telegram_id = :telegram_id"),
            {"telegram_id": int(telegram_id)}
        )
        user_row = result.fetchone()
        
        user_data_dict = None
        if user_row:
            # Just use the raw data without creating ORM objects
            user_data_dict = {
                "id": user_row.id,
                "telegram_id": str(user_row.telegram_id),
                "telegram_user_name": user_row.telegram_user_name,
                "phone_number": user_row.phone_number,
                "balance": float(user_row.balance) if user_row.balance is not None else 0.0,
                "send_report_to": user_row.send_report_to,
                "VIP_level": user_row.VIP_level,
                "username": user_row.username,
                "first_name": user_row.first_name,
                "last_name": user_row.last_name,
                "is_superuser": user_row.is_superuser,
                "avatar_url": user_row.avatar_url,
                "created_at": user_row.created_at,
                "is_active": user_row.is_active,
                "is_newcomer": user_row.is_newcomer,
                "language_code": getattr(user_row, 'language_code', 'en')
            }
        
        # Create new user if doesn't exist
        if not user_data_dict:
            default_balance = get_start_balance()
            
            # Create new user using raw SQL to avoid ORM issues
            result = await db.execute(
                text("""
                INSERT INTO users (telegram_id, telegram_user_name, first_name, last_name, 
                                 balance, "VIP_level", is_active, is_newcomer, created_at)
                VALUES (:telegram_id, :username, :first_name, :last_name, 
                        :balance, 0, true, true, NOW())
                RETURNING id, created_at
                """),
                {
                    "telegram_id": int(telegram_id),
                    "username": user_info.get("username"),
                    "first_name": user_info.get("first_name"),
                    "last_name": user_info.get("last_name"),
                    "balance": default_balance
                }
            )
            new_user_row = result.fetchone()
            if not new_user_row:
                raise HTTPException(status_code=500, detail="Failed to create new user")
            await db.commit()
            
            logger.info(f"New user created via TMA: telegram_id={telegram_id}, username={user_info.get('username')}")
            
            # Set user_data_dict for the new user
            user_data_dict = {
                "id": new_user_row.id,
                "telegram_id": str(telegram_id),
                "telegram_user_name": user_info.get("username"),
                "phone_number": None,
                "balance": default_balance,
                "is_newcomer": True,
                "first_name": user_info.get("first_name"),
                "last_name": user_info.get("last_name"),
                "language_code": user_info.get("language_code", "en"),
                "created_at": new_user_row.created_at,
                "is_active": True,
                "VIP_level": 0,
                "is_superuser": False,
                "avatar_url": None,
                "send_report_to": None
            }
        
        # At this point user_data_dict should always exist
        if not user_data_dict:
            raise HTTPException(status_code=500, detail="Failed to process user data")
        
        # Generate JWT token
        access_token = create_jwt_token(data={"sub": str(user_data_dict["id"])})
        
        # Use the user data dict directly for response
        user_data = {
            "id": user_data_dict["id"],
            "telegram_id": user_data_dict["telegram_id"],
            "telegram_user_name": user_data_dict["telegram_user_name"],
            "phone_number": user_data_dict["phone_number"],
            "balance": user_data_dict["balance"],
            "is_newcomer": user_data_dict["is_newcomer"],
            "first_name": user_data_dict.get("first_name"),
            "last_name": user_data_dict.get("last_name"),
            "language_code": user_data_dict.get("language_code", "en")
        }
        
        return TMAAuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TMA authentication error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.get("/telegram/user")
async def get_telegram_user(current_user: User = Depends(get_current_user)):
    """Get current user info for TMA context"""
    try:
        user_data = {
            "id": current_user.id,
            "telegram_id": current_user.telegram_id,
            "telegram_user_name": current_user.telegram_user_name,
            "phone_number": current_user.phone_number,
            "balance": float(current_user.balance) if current_user.balance is not None else 0.0,  # type: ignore
            "is_newcomer": current_user.is_newcomer,
            "first_name": getattr(current_user, 'first_name', None),
            "last_name": getattr(current_user, 'last_name', None),
            "language_code": getattr(current_user, 'language_code', 'en')
        }
        
        return user_data
        
    except Exception as e:
        logger.error(f"Get telegram user error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user data: {str(e)}")

@router.post("/telegram/init-bot")
async def initialize_telegram_bot():
    """Initialize the Telegram bot (called during app startup)"""
    try:
        telegram_bot = get_telegram_bot()
        await telegram_bot.initialize()
        return {"status": "success", "message": "Telegram bot initialized"}
        
    except Exception as e:
        logger.error(f"Bot initialization error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize bot: {str(e)}")

@router.get("/telegram/bot-info")
async def get_bot_info():
    """Get bot information and status"""
    try:
        telegram_bot = get_telegram_bot()
        if not telegram_bot.bot:
            return {"status": "not_initialized", "message": "Bot instance not created"}

        # Check if bot is initialized
        if not hasattr(telegram_bot.bot, '_initialized') or not telegram_bot.bot._initialized:
            # Try to initialize the bot if not already done
            try:
                await telegram_bot.bot.initialize()
            except Exception as init_error:
                logger.warning(f"Bot initialization failed in bot-info endpoint: {init_error}")
                return {"status": "initialization_failed", "message": f"Bot initialization failed: {str(init_error)}"}

        # Get bot info
        bot_info = await telegram_bot.bot.get_me()  # type: ignore

        return {
            "status": "initialized",
            "bot_info": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "is_bot": bot_info.is_bot,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries
            }
        }

    except Exception as e:
        logger.error(f"Get bot info error: {e}")
        # Return a more graceful error response instead of 500
        return {
            "status": "error",
            "message": f"Failed to get bot info: {str(e)}",
            "error_type": type(e).__name__
        }

@router.post("/internal/send-user-log")
async def send_user_log(log_request: UserLogRequest):
    """Send log message directly to user via Telegram bot"""
    try:
        # Get telegram bot instance
        telegram_bot = get_telegram_bot()
        
        # Get the actual Telegram ID from the database
        from sqlalchemy import select
        from models import User
        
        telegram_id = None
        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == log_request.user_id))
            user = result.scalar_one_or_none()
            if user and user.telegram_id:
                telegram_id = int(user.telegram_id)
            else:
                # Fallback to user_id if we can't get Telegram ID
                telegram_id = log_request.user_id
        
        # Clean the message using the same logic as status messages
        clean_lines = clean_status_message(log_request.message)
        clean_message = "\n".join(clean_lines)
        
        # Если сообщение важное - отправляем как новое постоянное сообщение
        if log_request.is_important:
            logger.info(f"Отправка важного сообщения для пользователя {log_request.user_id} (Telegram ID: {telegram_id})")
            
            # Определяем иконку в зависимости от типа сообщения
            icon = "📝"
            if log_request.log_type == "success":
                icon = "✅"
            elif log_request.log_type == "warning":
                icon = "⚠️"
            elif log_request.log_type == "error":
                icon = "❌"
            elif log_request.log_type == "info":
                icon = "ℹ️"
            
            # Отправляем новое постоянное сообщение
            result = await telegram_bot.bot.send_message(
                chat_id=telegram_id,
                text=f"{icon} {clean_message}",
                disable_notification=True
            )
            
            logger.info(f"Отправлено важное сообщение {result.message_id} для пользователя {log_request.user_id}")
            return {"status": "success", "message": "Important message sent", "message_id": result.message_id}
        
        # Для обычных сообщений используем старую логику с редактированием
        # Try to get the last Worker Log message ID for this user to overwrite it
        last_worker_log_id = await get_last_worker_log_message_id(log_request.user_id)

        # If we have a last_message_id (from status message), try to edit it to Worker Log format
        if log_request.last_message_id and not last_worker_log_id:
            try:
                await telegram_bot.bot.edit_message_text(
                    chat_id=telegram_id,
                    message_id=log_request.last_message_id,
                    text=f"🤖 Worker Log\n{clean_message}"
                )
                logger.info(f"Преобразовано статусное сообщение {log_request.last_message_id} в Worker Log")
                # Save this as the new Worker Log message ID
                await save_last_worker_log_message_id(log_request.user_id, log_request.last_message_id)
                await clear_last_status_message_id(log_request.user_id)
                return {"status": "success", "message": "Status message converted to Worker Log", "message_id": log_request.last_message_id}
            except Exception as edit_error:
                logger.warning(f"Не удалось преобразовать статусное сообщение {log_request.last_message_id}: {edit_error}")
                # Continue to try Worker Log editing or sending new message
        
        if last_worker_log_id:
            # Try to edit the existing Worker Log message
            try:
                await telegram_bot.bot.edit_message_text(
                    chat_id=telegram_id,
                    message_id=last_worker_log_id,
                    text=f"🤖 Worker Log\n{clean_message}"
                )
                logger.info(f"Отредактировано Worker Log сообщение {last_worker_log_id} для пользователя {log_request.user_id}")
                return {"status": "success", "message": "Worker Log message updated", "message_id": last_worker_log_id}
            except Exception as edit_error:
                logger.warning(f"Не удалось отредактировать Worker Log сообщение {last_worker_log_id}: {edit_error}")
        
        # Send new Worker Log message
        result = await telegram_bot.bot.send_message(
            chat_id=telegram_id,
            text=f"🤖 Worker Log\n{clean_message}",
            parse_mode="MarkdownV2",
            disable_notification=True
        )
        
        # Save the new Worker Log message ID
        await save_last_worker_log_message_id(log_request.user_id, result.message_id)
        await clear_last_status_message_id(log_request.user_id)
        
        logger.info(f"Отправлено новое Worker Log сообщение {result.message_id} для пользователя {log_request.user_id}")
        return {"status": "success", "message": "Worker Log sent to user", "message_id": result.message_id}
        
    except Exception as e:
        logger.error(f"Failed to send log to user {log_request.user_id}: {e}")
        logger.error(f"Error type: {type(e).__name__}, Error args: {e.args}")
        # Check if it's a chat not found error
        if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower():
            logger.error(f"User {log_request.user_id} has not started conversation with bot or has blocked it")
            raise HTTPException(status_code=400, detail=f"User has not started conversation with bot or has blocked it: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send log: {str(e)}")

@router.post("/internal/send-user-log-status", response_model=dict)
async def send_user_status_update(status_request: UserStatusUpdateRequest):
    """Send status update to user, editing previous message if possible"""
    try:
        # Get the actual Telegram ID from the database
        from sqlalchemy import select
        from models import User
        
        telegram_id = None
        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == status_request.user_id))
            user = result.scalar_one_or_none()
            if user and user.telegram_id:
                telegram_id = int(user.telegram_id)
            else:
                # Fallback to user_id if we can't get Telegram ID
                telegram_id = status_request.user_id
        
        # Получаем чистый текст сообщения без форматирования
        raw_message = status_request.message if status_request.message else ""
        
        # Определяем иконку в зависимости от типа сообщения
        icon = "🔄"
        if status_request.log_type == "success":
            icon = "✅"
        elif status_request.log_type == "warning":
            icon = "⚠️"
        elif status_request.log_type == "error":
            icon = "❌"
        elif status_request.log_type == "info":
            icon = "ℹ️"
        
        # Очищаем и форматируем сообщение
        clean_lines = clean_status_message(raw_message)
        message_text = f"{icon} Статус агента\n\n" + "\n".join(clean_lines)
        
        # Получаем токен Telegram
        import aiohttp
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        
        async with aiohttp.ClientSession() as session:
            # Получаем ID последнего статусного сообщения
            last_status_id = await get_last_status_message_id(status_request.user_id)
            
            # Удаляем старое статусное сообщение, если оно существует
            if last_status_id:
                try:
                    delete_url = f"https://api.telegram.org/bot{telegram_token}/deleteMessage"
                    delete_payload = {
                        "chat_id": telegram_id,
                        "message_id": last_status_id
                    }
                    async with session.post(delete_url, json=delete_payload) as response:
                        if response.status == 200:
                            logger.info(f"Старое статусное сообщение {last_status_id} успешно удалено")
                        else:
                            # Если бот сообщает, что сообщение не найдено — очищаем ID и продолжаем
                            response_text = await response.text()
                            if "message to delete not found" in response_text:
                                await save_last_status_message_id(status_request.user_id, None)
                                logger.info(f"Старый статус {last_status_id} отсутствует, очищен ID")
                            else:
                                logger.warning(f"Не удалось удалить старый статус {last_status_id}: HTTP {response.status}, {response_text}")
                except Exception as delete_error:
                    # Программно игнорируем ошибку удаления, продолжаем отправку нового статуса
                    logger.warning(f"Ошибка при удалении старого статуса {last_status_id}: {delete_error}")
            
            # Отправляем новое статусное сообщение
            logger.info(f"Отправка нового статусного сообщения для пользователя {status_request.user_id} (Telegram ID: {telegram_id}): {message_text[:50]}...")
            
            send_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            send_payload = {
                "chat_id": telegram_id,
                "text": message_text,
                "parse_mode": "HTML",
                "disable_notification": True
            }
            
            async with session.post(send_url, json=send_payload) as response:
                # Accept both 200 (new message) and 429 (rate limit) without 500 at API level
                response_text = await response.text()
                if response.status == 200:
                    try:
                        response_data = await response.json()
                    except Exception:
                        response_data = {}
                    message_id = (response_data.get("result", {}) or {}).get("message_id")
                    logger.info(f"Новое статусное сообщение отправлено с ID {message_id}")
                    await save_last_status_message_id(status_request.user_id, message_id)
                    await clear_worker_log_message_id(status_request.user_id)
                    return {"status": "success", "message": "Status sent", "message_id": message_id}
                elif response.status == 429:
                    # Parse retry_after and surface to caller; do not error 500
                    retry_after = None
                    try:
                        data = await response.json()
                        retry_after = data.get("parameters", {}).get("retry_after")
                    except Exception:
                        pass
                    logger.warning(f"Telegram rate limit: HTTP 429, retry_after={retry_after}, body={response_text}")
                    return {"status": "rate_limited", "retry_after": retry_after}
                else:
                    logger.error(f"Failed to send message: HTTP {response.status}, {response_text}")
                    return {"status": "error", "message": response_text, "http_status": response.status}
    
    except Exception as e:
        logger.error(f"Error in send_user_status_update: {e}")
        if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower():
            logger.error(f"User {status_request.user_id} has not started conversation with bot or has blocked it")
            raise HTTPException(status_code=400, detail=f"User has not started conversation with bot or has blocked it: {str(e)}")
        return {"status": "error", "message": str(e)}


async def get_last_worker_log_message_id(user_id: int) -> int | None:
    """Get the last Worker Log message ID for a user"""
    redis_value = await redis_get(_worker_log_redis_key(user_id))
    if redis_value and redis_value != "None":
        try:
            return int(redis_value)
        except (TypeError, ValueError):
            logger.debug(f"Invalid worker log ID in Redis for user {user_id}: {redis_value}")
    return None


async def save_last_worker_log_message_id(user_id: int, message_id: int | None) -> None:
    """Persist the last Worker Log message ID for a user"""
    if message_id is None:
        await redis_delete(_worker_log_redis_key(user_id))
    else:
        await redis_set(_worker_log_redis_key(user_id), str(message_id))


async def clear_worker_log_message_id(user_id: int) -> None:
    """Clear the Worker Log message ID when status message overwrites it"""
    await redis_delete(_worker_log_redis_key(user_id))


async def get_last_status_message_id(user_id: int) -> int | None:
    """Get the last status message ID for a user from Redis/DB"""
    redis_value = await redis_get(_status_redis_key(user_id))
    if redis_value and redis_value != "None":
        try:
            return int(redis_value)
        except (TypeError, ValueError):
            logger.debug(f"Invalid status ID in Redis for user {user_id}: {redis_value}")

    # Fallback to database stored value
    try:
        async with async_session() as session:
            result = await session.execute(
                select(UserBotLogState.last_status_message_id).where(UserBotLogState.user_id == user_id)
            )
            db_value = result.scalar_one_or_none()
            if db_value is not None:
                await redis_set(_status_redis_key(user_id), str(db_value))
                return int(db_value)
    except Exception as exc:
        logger.debug(f"Failed to load status message ID from DB for user {user_id}: {exc}")

    return None


async def save_last_status_message_id(user_id: int, message_id: int | None) -> None:
    """Persist the last status message ID in Redis and database"""
    if message_id is None:
        await redis_delete(_status_redis_key(user_id))
    else:
        await redis_set(_status_redis_key(user_id), str(message_id))

    try:
        async with async_session() as session:
            result = await session.execute(select(UserBotLogState).where(UserBotLogState.user_id == user_id))
            state = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)

            if message_id is not None:
                if state:
                    state.last_status_message_id = message_id
                    state.updated_at = now
                else:
                    session.add(
                        UserBotLogState(
                            user_id=user_id,
                            last_status_message_id=message_id,
                            updated_at=now,
                        )
                    )
            else:
                if state:
                    state.last_status_message_id = None
                    state.updated_at = now

            await session.commit()
    except Exception as exc:
        logger.debug(f"Failed to persist status message ID for user {user_id}: {exc}")


async def clear_last_status_message_id(user_id: int) -> None:
    """Clear stored status message ID"""
    await save_last_status_message_id(user_id, None)


# ============================================
# NEW BOT LOGGING ENDPOINTS
# ============================================

@router.post("/internal/bot-status", response_model=dict)
async def send_bot_status(request: BotStatusRequest):
    """
    Send a transient status message.

    Behavior:
    - ALWAYS delete old status message first (if exists) to prevent overwriting reports
    - Send new status message
    - Returns the message_id for future edits
    """
    try:
        import aiohttp
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        telegram_id = request.telegram_id

        # Log incoming status request
        logger.debug(f"API status update: user={request.user_id} last_id={request.last_status_message_id}")

        # Don't add 🔄 prefix if message already starts with an emoji
        raw_message = request.message

        # Check if message starts with an emoji or special character
        # Emojis can be multi-codepoint, so check first few chars
        emoji_prefixes = ("✅", "❌", "⚠️", "🔄", "📋", "🔍", "📨", "⏳", "🎧", "📸",
                         "🚀", "📥", "🔌", "☁️", "🖼️", "💓", "ℹ️", "⏸", "🤖", "💰")
        is_emoji_start = any(raw_message.startswith(prefix) for prefix in emoji_prefixes)

        if is_emoji_start:
            message_text = raw_message
        else:
            message_text = f"🔄 {raw_message}"

        async with aiohttp.ClientSession() as session:
            # Check if old status message is protected before deleting
            if request.last_status_message_id:
                if _is_message_recently_promoted(request.user_id, request.last_status_message_id):
                    # Don't delete protected messages - send new status without deleting old
                    logger.warning(f"Skipping status deletion: user={request.user_id} msg_id={request.last_status_message_id} - message is protected")
                    # Clear the status slot since we're not replacing the old message
                    await save_last_status_message_id(request.user_id, None)
                    # Send new status message without deleting the protected one
                    send_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                    send_payload = {
                        "chat_id": telegram_id,
                        "text": message_text,
                        "disable_notification": True
                    }
                    async with session.post(send_url, json=send_payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            message_id = data.get("result", {}).get("message_id")
                            logger.debug(f"Status sent (protected mode): user={request.user_id} new_msg_id={message_id}")
                            return {
                                "status": "success",
                                "action": "sent_protected",
                                "message_id": message_id
                            }
                        else:
                            response_text = await response.text()
                            logger.error(f"[API_STATUS_SEND_FAILED_PROTECTED] user={request.user_id} http={response.status}")
                            return {"status": "error", "message": response_text}
                else:
                    # Normal deletion for unprotected messages
                    logger.debug(f"Deleting old status: user={request.user_id} msg_id={request.last_status_message_id}")
                    try:
                        delete_url = f"https://api.telegram.org/bot{telegram_token}/deleteMessage"
                        delete_payload = {
                            "chat_id": telegram_id,
                            "message_id": request.last_status_message_id
                        }
                        async with session.post(delete_url, json=delete_payload) as del_resp:
                            if del_resp.status == 200:
                                logger.debug(f"Old status deleted: user={request.user_id} msg_id={request.last_status_message_id}")
                                logger.debug(f"Deleted old status message {request.last_status_message_id}")
                            else:
                                response_text = await del_resp.text()
                                logger.warning(f"[API_STATUS_DELETE_FAILED] user={request.user_id} msg_id={request.last_status_message_id} http={del_resp.status} resp='{response_text[:100]}'")
                                logger.debug(f"Could not delete old status {request.last_status_message_id}: HTTP {del_resp.status}")
                    except Exception as del_e:
                        logger.warning(f"[API_STATUS_DELETE_EXCEPTION] user={request.user_id} msg_id={request.last_status_message_id} error={del_e}")
                        logger.debug(f"Could not delete old status: {del_e}")

            # Send new status message
            logger.debug(f"Sending status: user={request.user_id} text='{message_text[:50]}...'")
            send_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            send_payload = {
                "chat_id": telegram_id,
                "text": message_text,
                "disable_notification": True
            }

            async with session.post(send_url, json=send_payload) as response:
                if response.status == 200:
                    data = await response.json()
                    message_id = data.get("result", {}).get("message_id")
                    logger.debug(f"Status sent: user={request.user_id} new_msg_id={message_id}")
                    logger.debug(f"New status sent: msg_id={message_id}")
                    return {
                        "status": "success",
                        "action": "sent",
                        "message_id": message_id
                    }
                elif response.status == 429:
                    data = await response.json()
                    retry_after = data.get("parameters", {}).get("retry_after")
                    logger.warning(f"Rate limited: user={request.user_id} retry_after={retry_after}")
                    return {"status": "rate_limited", "retry_after": retry_after}
                else:
                    response_text = await response.text()
                    logger.error(f"[API_STATUS_SEND_FAILED] user={request.user_id} http={response.status}")
                    logger.error(f"Failed to send status: HTTP {response.status}, {response_text}")
                    return {"status": "error", "message": response_text}

    except Exception as e:
        logger.error(f"Status update exception: user={request.user_id} error={e}")
        logger.error(f"Error in send_bot_status: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/internal/bot-report", response_model=dict)
async def send_bot_report(request: BotReportRequest):
    """
    Send a permanent report message.

    Behavior:
    - If last_status_message_id exists -> edit it to become the report (promote)
    - If edit fails -> delete old status + send new report message
    - Report messages are PERMANENT - they stay in chat forever
    - ALWAYS clear the status slot after sending to prevent future status from overwriting
    - Returns success without message_id (reports don't need further editing)
    """
    try:
        import aiohttp
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        telegram_id = request.telegram_id

        # Log incoming report request
        logger.debug(f"API report request: user={request.user_id} target_id={request.last_status_message_id} type={request.report_type}")

        # Choose icon based on report type
        icon = "✅" if request.report_type == "success" else "❌" if request.report_type == "error" else "⚠️"
        message_text = f"{icon} {request.message}"

        async with aiohttp.ClientSession() as session:
            # Try to edit existing status message to become the report
            if request.last_status_message_id:
                logger.debug(f"Promoting status to report: user={request.user_id} msg_id={request.last_status_message_id}")
                try:
                    edit_url = f"https://api.telegram.org/bot{telegram_token}/editMessageText"
                    edit_payload = {
                        "chat_id": telegram_id,
                        "message_id": request.last_status_message_id,
                        "text": message_text,
                        "parse_mode": "HTML"
                    }
                    async with session.post(edit_url, json=edit_payload) as response:
                        if response.status == 200:
                            logger.debug(f"Status promoted to report: user={request.user_id} msg_id={request.last_status_message_id}")
                            logger.info(f"Status promoted to report: msg_id={request.last_status_message_id}")
                            # CRITICAL: Mark message as promoted to prevent status overwrites
                            _mark_message_promoted(request.user_id, request.last_status_message_id)
                            # CRITICAL: Clear the status slot immediately after promotion
                            await save_last_status_message_id(request.user_id, None)
                            return {
                                "status": "success",
                                "action": "promoted",
                                "message_id": request.last_status_message_id
                            }
                        else:
                            response_text = await response.text()
                            logger.debug(f"Promote failed: user={request.user_id} msg_id={request.last_status_message_id} http={response.status}")
                            # If old message exists but edit failed, try to delete it
                            if "message to edit not found" not in response_text.lower():
                                try:
                                    delete_url = f"https://api.telegram.org/bot{telegram_token}/deleteMessage"
                                    delete_payload = {
                                        "chat_id": telegram_id,
                                        "message_id": request.last_status_message_id
                                    }
                                    async with session.post(delete_url, json=delete_payload) as del_resp:
                                        if del_resp.status == 200:
                                            logger.debug(f"Deleted old status message {request.last_status_message_id} before report")
                                except Exception as del_e:
                                    logger.debug(f"Could not delete old status before report: {del_e}")
                            logger.debug(f"Promote failed, sending new report: {response_text}")
                except Exception as e:
                    logger.debug(f"Promote exception: user={request.user_id} msg_id={request.last_status_message_id} error={e}")
                    logger.debug(f"Promote exception, sending new report: {e}")
                    # Try to delete old status message
                    try:
                        delete_url = f"https://api.telegram.org/bot{telegram_token}/deleteMessage"
                        delete_payload = {
                            "chat_id": telegram_id,
                            "message_id": request.last_status_message_id
                        }
                        async with session.post(delete_url, json=delete_payload) as del_resp:
                            if del_resp.status == 200:
                                logger.debug(f"Deleted old status message {request.last_status_message_id} before report")
                    except Exception as del_e:
                        logger.debug(f"Could not delete old status before report: {del_e}")

            # Send new report message
            logger.debug(f"Sending report: user={request.user_id} target_id={request.last_status_message_id}")
            send_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            send_payload = {
                "chat_id": telegram_id,
                "text": message_text,
                "parse_mode": "HTML",
                "disable_notification": False  # Reports should notify
            }

            async with session.post(send_url, json=send_payload) as response:
                if response.status == 200:
                    data = await response.json()
                    message_id = data.get("result", {}).get("message_id")
                    logger.debug(f"Report sent: user={request.user_id} new_msg_id={message_id}")
                    logger.info(f"New report sent ({request.report_type}): msg_id={message_id}")
                    # CRITICAL: Mark new report as promoted to prevent status overwrites
                    if message_id:
                        _mark_message_promoted(request.user_id, message_id)
                    # CRITICAL: Clear the status slot after sending new report
                    await save_last_status_message_id(request.user_id, None)
                    return {
                        "status": "success",
                        "action": "sent",
                        "message_id": message_id
                    }
                elif response.status == 429:
                    data = await response.json()
                    retry_after = data.get("parameters", {}).get("retry_after")
                    logger.warning(f"Rate limited: user={request.user_id} retry_after={retry_after}")
                    return {"status": "rate_limited", "retry_after": retry_after}
                else:
                    response_text = await response.text()
                    logger.error(f"[API_REPORT_SEND_FAILED] user={request.user_id} http={response.status}")
                    logger.error(f"Failed to send report: HTTP {response.status}, {response_text}")
                    return {"status": "error", "message": response_text}

    except Exception as e:
        logger.error(f"Report exception: user={request.user_id} error={e}")
        logger.error(f"Error in send_bot_report: {e}")
        return {"status": "error", "message": str(e)}
