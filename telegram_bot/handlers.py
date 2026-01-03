import logging
import re
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio, InputMediaAnimation
try:
    from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup
except Exception:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    CopyTextButton = None
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler
from telegram.constants import MessageLimit
from .messages import MessageTemplates
from .keyboards import BotKeyboards
from .utils import get_default_balance, format_user_display_name
from .update_tracker import update_tracker
from .i18n import I18n
import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
import httpx
import time
import aiohttp
from uni_text_processor.universal_processor import UniversalAIProcessor
from uni_text_processor.db_utils import DatabaseUtils
from uni_text_processor.text_formatting import markdown_to_telegram_html

# Add parent directory to path to import models and services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import actual services
from models import User, Worker, Model, Payment
from db import async_session
from sqlalchemy import select
from worker_registry import worker_registry
from queue_manager import get_queue_manager
import worker_manager as wm
import secrets

# Global rate limiter for OpenRouter API requests
# Ensures only one request every 5 seconds across all users (increased from 3 to handle rate limits better)
_openrouter_rate_limiter_lock = asyncio.Lock()
_openrouter_last_request_time = 0

async def _openrouter_rate_limited_request():
    """Global rate limiter for OpenRouter API requests - ensures only one request every 5 seconds"""
    global _openrouter_last_request_time
    async with _openrouter_rate_limiter_lock:
        current_time = time.time()
        time_since_last_request = current_time - _openrouter_last_request_time
        
        # If less than 5 seconds have passed since the last request, wait
        if time_since_last_request < 5:
            sleep_time = 5 - time_since_last_request
            logger.info(f"Rate limiting: Waiting {sleep_time:.2f} seconds before next OpenRouter request")
            await asyncio.sleep(sleep_time)
        
        # Update the last request time
        _openrouter_last_request_time = time.time()
        logger.info(f"Proceeding with OpenRouter request at {_openrouter_last_request_time}")

def get_all_button_texts():
    """Get all possible button texts for all languages to use in filters"""
    texts = []
    for lang in ['ru', 'en']:
        texts.append(I18n.get(lang, "buttons.settings"))
        texts.append(I18n.get(lang, "buttons.tma"))
        texts.append(I18n.get(lang, "buttons.profile"))
    return texts


logger = logging.getLogger(__name__)


def convert_markdown_to_html(text: str) -> str:
    """
    Безопасно конвертирует Markdown-подобное форматирование в Telegram HTML.
    Сначала экранирует все потенциальные HTML-символы, затем вставляет только
    допустимые теги (<b>, <i>, <u>, <s>) на основе **, *, __, ~~.
    """
    import re

    if text is None:
        return ""

    # Экранируем HTML, чтобы не допустить незакрытых/сырых тегов из модели
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Конвертация markdown-паттернов в безопасные HTML-теги
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text, flags=re.S)
    text = re.sub(r"\*([^\*\n]+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"__(.*?)__", r"<u>\1</u>", text, flags=re.S)
    text = re.sub(r"~~(.*?)~~", r"<s>\1</s>", text, flags=re.S)

    return text

def _truncate_caption(text: str) -> str:
    max_len = MessageLimit.CAPTION_LENGTH
    if not text:
        return text
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"

async def get_or_create_user(telegram_id: int, user_data: dict) -> User:
    """Get existing user or create new one from Telegram data"""
    session = async_session()
    try:
        # Try to find existing user
        # Convert telegram_id to integer for comparison with bigint column
        result = await session.execute(
            select(User).where(User.telegram_id == int(telegram_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            balance = get_default_balance()
            user_language = user_data.get('language_code', 'en')
            if user_language not in ['ru', 'en']:
                user_language = 'en'
            try:
                processor = UniversalAIProcessor(logger)
                bot_system_content = processor.get_default_system_prompt(user_language)
            except Exception:
                bot_system_content = None

            from dotenv import load_dotenv
            load_dotenv()
            bot_model_1 = None
            bot_model_2 = None
            try:
                m1 = os.getenv('PROD_MODELS_1') or os.getenv('PROD_MODEL_1')
                m2 = os.getenv('PROD_MODELS_2') or os.getenv('PROD_MODEL_2')
                bot_model_1 = int(m1) if m1 else None
                bot_model_2 = int(m2) if m2 else None
            except Exception:
                pass

            user = User(
                telegram_id=int(telegram_id),
                telegram_user_name=user_data.get('username'),
                phone_number=None,
                balance=balance,
                is_newcomer=True,
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                language_code=user_language,
                bot_model_1=bot_model_1,
                bot_model_2=bot_model_2,
                bot_system_content=bot_system_content,
                created_at=datetime.now(timezone.utc)
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user via Telegram bot: {telegram_id}")

        return user
    finally:
        await session.close()

async def get_user_worker_status(user_id: int) -> tuple[str, dict]:
    """Get worker status and additional info for user"""
    session = async_session()
    try:
        result = await session.execute(
            select(Worker).where(Worker.user_id == user_id)
        )
        worker = result.scalar_one_or_none()
        
        if not worker:
            return "stopped", {}
        
        # Check if worker is actually running
        if worker.status in ['running', 'active'] and worker.pid:
            if worker_registry.is_worker_running(user_id):
                runtime_info = worker_registry.get_worker_runtime(user_id)
                return worker.status, {"runtime": runtime_info}
            else:
                # Worker process died, update status
                worker.status = "stopped"
                worker.pid = None
                await session.commit()
                return "stopped", {}
        
        return worker.status, {}
    finally:
        await session.close()

async def get_user_recent_logs(user_id: int, limit: int = 5) -> list:
    """Get recent logs for user - placeholder implementation"""
    # TODO: Implement actual log retrieval from database or log files
    # For now, return empty list
    return []

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.info("DEBUG: start_command called")
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        telegram_id = user.id
        
        # Get or create user
        user_data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code or 'en'
        }
        
        db_user = await get_or_create_user(telegram_id, user_data)
        
        # Get worker status and recent logs
        worker_status, worker_info = await get_user_worker_status(db_user.id)
        recent_logs = await get_user_recent_logs(db_user.id, 3)
        
        message = I18n.get(db_user.language_code if db_user else 'en', "messages.start_message")

        keyboard = BotKeyboards.main_menu(telegram_id)
        reply_keyboard = BotKeyboards.reply_keyboard(db_user.language_code if db_user else 'en')

        image_path = os.path.join(os.path.dirname(__file__), "media", "tAIger-2modes17.jpg")
        await update.message.reply_photo(
            photo=open(image_path, "rb"),
            caption=message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        # Send the reply keyboard as a separate message
        await update.message.reply_text(
            I18n.get(db_user.language_code if db_user else 'en', "messages.send_message_prompt"),
            reply_markup=reply_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        # Get user language for error message
        user = update.effective_user
        telegram_id = user.id
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
            db_user = result.scalar_one_or_none()
        finally:
            await session.close()
        await update.message.reply_text(
            "❌ Sorry, something went wrong. Please try again.",
            reply_markup=BotKeyboards.back_to_main(db_user.language_code if db_user else 'en')
        )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    try:
        user = update.effective_user
        telegram_id = user.id
        
        # Get user from database
        user_data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code or 'en'
        }
        
        db_user = await get_or_create_user(telegram_id, user_data)
        
        message = MessageTemplates.balance_info(float(db_user.balance))
        keyboard = BotKeyboards.balance_menu()
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in balance command: {e}")
        await update.message.reply_text("❌ Could not fetch balance. Please try again.")

async def worker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /worker command"""
    try:
        user = update.effective_user
        telegram_id = user.id
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
            db_user = result.scalar_one_or_none()
        finally:
            await session.close()
        status = "stopped"
        queue_position = None
        runtime = None
        if db_user:
            if worker_registry.is_worker_running(db_user.id):
                status = "active"
            else:
                qm = get_queue_manager()
                pos = await qm.get_queue_position(db_user.id)
                if pos:
                    status = "pending"
                    queue_position = pos
        user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
        message = MessageTemplates.worker_status(status, queue_position, runtime)
        keyboard = BotKeyboards.worker_controls(user_lang)
        
        image_path = os.path.join(os.path.dirname(__file__), "media", "tAIger-2modes17.jpg")
        print(f"DEBUG: Attempting to send photo with path: {image_path}", flush=True)
        try:
            await update.message.reply_photo(
                photo=open(image_path, "rb"),
                caption=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            print("DEBUG: Photo sent successfully", flush=True)
        except Exception as photo_error:
            print(f"DEBUG: Failed to send photo: {photo_error}", flush=True)
            # Fallback to text message
            image_path = os.path.join(os.path.dirname(__file__), "media", "tAIger-2modes17.jpg")
            logger.info(f"DEBUG: Attempting to send photo with path: {image_path}")
            try:
                await update.message.reply_photo(
                    photo=open(image_path, "rb"),
                    caption=message,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                logger.info("DEBUG: Photo sent successfully")
            except Exception as photo_error:
                logger.error(f"DEBUG: Failed to send photo: {photo_error}")
                # Fallback to text message
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        
    except Exception as e:
        logger.error(f"Error in worker command: {e}")
        await update.message.reply_text("❌ Could not fetch worker status. Please try again.")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logs command"""
    try:
        user = update.effective_user
        telegram_id = user.id
        
        # TODO: Get actual logs from database
        logs = []  # Placeholder

        message = MessageTemplates.logs_display(logs)
        user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
        keyboard = BotKeyboards.logs_menu(user_lang)
        
        await update.message.reply_photo(
            photo=open("telegram_bot/media/tAIger-2modes17.jpg", "rb"),
            caption=message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in logs command: {e}")
        await update.message.reply_text("❌ Could not fetch logs. Please try again.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    try:
        message = MessageTemplates.help_message()
        keyboard = BotKeyboards.back_to_main()
        
        image_path = os.path.join(os.path.dirname(__file__), "media", "tAIger-2modes17.jpg")
        logger.info(f"DEBUG: Attempting to send photo with path: {image_path}")
        try:
            await update.message.reply_photo(
                photo=image_path,
                caption=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info("DEBUG: Photo sent successfully")
        except Exception as photo_error:
            logger.error(f"DEBUG: Failed to send photo: {photo_error}")
            # Fallback to text message
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("❌ Could not show help. Please try again.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the user message."""
    print(f"DEBUG: Received message: {update.message.text}")
    await update.message.reply_text(update.message.text)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = update.effective_user
        telegram_id = user.id
        
        if data == "main_menu":
            # Show main menu
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()

            if db_user:
                worker_status, _ = await get_user_worker_status(db_user.id)
                recent_logs = await get_user_recent_logs(db_user.id, 3)
                balance = float(db_user.balance) if db_user.balance is not None else get_default_balance()
                message = MessageTemplates.welcome_existing_user(balance, worker_status, recent_logs, db_user.language_code if db_user else 'en')
            else:
                balance = get_default_balance()
                message = MessageTemplates.welcome_new_user(balance, 'en')

            # Remove inline keyboard and show main menu message
            await query.edit_message_text(
                text=message,
                reply_markup=None,  # Remove inline keyboard
                parse_mode="HTML"
            )

            # Send the reply keyboard as a separate message
            reply_keyboard = BotKeyboards.reply_keyboard(db_user.language_code if db_user else 'en')
            await query.message.reply_text(
                I18n.get(db_user.language_code if db_user else 'en', "messages.send_message_prompt"),
                reply_markup=reply_keyboard
            )
            return  # Exit early since we handled the response

            
        elif data == "buy_battery":
            # Показать меню покупки батареек
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            message = I18n.get(user_lang, "messages.payment_methods") + "\n\n" + I18n.get(user_lang, "messages.buy_batteries_description")
            keyboard = BotKeyboards.buy_batteries_menu(user_lang)

        elif data.startswith("buy_battery:"):
            # Обработка выбора количества батареек
            try:
                _, batteries_str = data.split(":")
                batteries_count = int(batteries_str)
            except ValueError:
                await query.answer("❌ Invalid batteries count")
                return

            # Получаем пользователя
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()

            if not db_user:
                await query.answer("❌ User not found")
                return

            user_lang = db_user.language_code if db_user.language_code in ['ru', 'en'] else 'en'

            # Создаём запись о платеже в БД
            session = async_session()
            try:
                # Генерируем уникальный pre_checkout_id
                pre_checkout_id = f"payment_{db_user.id}_{secrets.token_hex(8)}"

                payment = Payment(
                    user_id=db_user.id,
                    currency_type='stars',
                    amount=float(batteries_count),  # 1 звезда = 1 батарейка
                    batteries_received=float(batteries_count),
                    status='pending',
                    telegram_pre_checkout_id=pre_checkout_id,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(payment)
                await session.commit()
                await session.refresh(payment)
            except Exception as db_error:
                logger.error(f"Error creating payment in DB: {db_error}")
                await session.rollback()
                await query.answer("❌ Database error")
                return
            finally:
                await session.close()

            # Отправляем invoice через Telegram Stars API
            try:
                # Создаём invoice для Telegram Stars
                invoice_title = f"{batteries_count} Batteries" if user_lang == 'en' else f"{batteries_count} Батареек"
                invoice_description = f"Buy {batteries_count} batteries for tAIger bot" if user_lang == 'en' else f"Купить {batteries_count} батареек для бота tAIger"

                # Отправляем invoice БЕЗ reply_markup (Telegram сам добавит кнопку Pay)
                await query.message.reply_invoice(
                    title=invoice_title,
                    description=invoice_description,
                    payload=pre_checkout_id,  # Используем как payload
                    provider_token="",  # Пустой для Telegram Stars
                    currency="XTR",  # XTR - код валюты Telegram Stars
                    prices=[{"label": f"{batteries_count} batteries" if user_lang == 'en' else f"{batteries_count} батареек", "amount": batteries_count}],
                    max_tip_amount=0,
                    start_parameter="buy-batteries"
                    # reply_markup НЕ используется - Telegram сам добавит кнопку Pay
                )

                logger.info(f"Invoice sent successfully for payment {pre_checkout_id}")
                return

            except Exception as e:
                logger.error(f"Error creating invoice: {e}")
                await query.answer(f"❌ Error: {str(e)}")
                # Отправляем сообщение об ошибке
                await query.message.reply_text(
                    "❌ Something went wrong. Please try again.",
                    reply_markup=BotKeyboards.back_to_main(user_lang)
                )
                return


        elif data == "balance":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()

            balance = float(db_user.balance) if db_user and db_user.balance is not None else get_default_balance()
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'

            # Обновлённое сообщение с информацией о способах оплаты
            message = I18n.get(user_lang, "messages.payment_methods") + "\n\n" + I18n.get(user_lang, "messages.balance_info", emoji="💰", balance=balance)
            keyboard = BotKeyboards.balance_menu(user_lang)

        elif data == "profile":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                if db_user:
                    worker_status, _ = await get_user_worker_status(db_user.id)
                    message = I18n.get(db_user.language_code or 'en', "messages.profile_info", tg_id=db_user.telegram_id, balance=db_user.balance, status=worker_status)
                else:
                    message = "❌ Пользователь не найден"
            finally:
                await session.close()
            keyboard = BotKeyboards.profile_menu(db_user.language_code if db_user else 'en')
            
        elif data == "worker":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            status = "stopped"
            queue_position = None
            runtime = None
            if db_user:
                if worker_registry.is_worker_running(db_user.id):
                    status = "active"
                else:
                    qm = get_queue_manager()
                    pos = await qm.get_queue_position(db_user.id)
                    if pos:
                        status = "pending"
                        queue_position = pos
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            message = MessageTemplates.worker_status(status, queue_position, runtime)
            keyboard = BotKeyboards.worker_controls(user_lang)
            
        elif data == "worker_start":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            if db_user:
                qm = get_queue_manager()
                entry = await qm.add_to_queue(db_user.id, 0)
                pos = await qm.get_queue_position(db_user.id)
                message = MessageTemplates.worker_started(pos)
            else:
                message = MessageTemplates.worker_error("user_not_found")
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            keyboard = BotKeyboards.worker_controls(user_lang)
            
        elif data == "worker_stop":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            message = I18n.get(user_lang, "messages.worker_stop_confirm", default="⚠️ Are you sure you want to stop the worker?")
            keyboard = BotKeyboards.confirm_worker_stop(user_lang)
            
        elif data == "worker_stop_confirm":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            if db_user:
                success = await wm.stop_worker(db_user.id)
                if success:
                    message = MessageTemplates.worker_stopped()
                else:
                    message = MessageTemplates.worker_error("stop_failed")
            else:
                message = MessageTemplates.worker_error("user_not_found")
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            keyboard = BotKeyboards.worker_controls(user_lang)
            
        elif data == "worker_status":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            status = "stopped"
            queue_position = None
            runtime = None
            if db_user:
                if worker_registry.is_worker_running(db_user.id):
                    status = "active"
                else:
                    qm = get_queue_manager()
                    pos = await qm.get_queue_position(db_user.id)
                    if pos:
                        status = "pending"
                        queue_position = pos
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            message = MessageTemplates.worker_status(status, queue_position, runtime)
            keyboard = BotKeyboards.worker_controls(user_lang)
            
        elif data == "worker_restart":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            if db_user:
                await wm.stop_worker(db_user.id)
                qm = get_queue_manager()
                await qm.remove_from_queue(db_user.id)
                entry = await qm.add_to_queue(db_user.id, 0)
                pos = await qm.get_queue_position(db_user.id)
                message = f"🔄 Worker restart initiated...\n📍 Queue position: <code>{pos}</code>"
            else:
                message = MessageTemplates.worker_error("user_not_found")
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            keyboard = BotKeyboards.worker_controls(user_lang)
            
        elif data == "logs":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            logs = []  # TODO: Get from database
            message = MessageTemplates.logs_display(logs)
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            keyboard = BotKeyboards.logs_menu(user_lang)
            
        elif data == "help":
            db_user = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()
            message = MessageTemplates.help_message(db_user.language_code if db_user else 'en')
            keyboard = BotKeyboards.back_to_main(db_user.language_code if db_user else 'en')
            
        elif data == "bot_settings":
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                if db_user:
                    # Get user language
                    user_lang = db_user.language_code or 'en'

                    # Send explanatory message with image first
                    explanation_text = I18n.get(user_lang, "messages.bot_mode_explanation")
                    image_path = os.path.join(os.path.dirname(__file__), "media", "tAIger-bot_mode.jpg")
                    await query.message.reply_photo(
                        photo=open(image_path, "rb"),
                        caption=explanation_text,
                        parse_mode="HTML"
                    )

                    # Now prepare and send the settings message
                    m1_label = "нет"
                    m2_label = "нет"
                    if getattr(db_user, 'bot_model_1', None):
                        res1 = await session.execute(select(Model).where(Model.id == int(db_user.bot_model_1)))
                        mdl1 = res1.scalar_one_or_none()
                        if mdl1:
                            name1 = mdl1.model_visible_name or mdl1.model
                            price1 = f" (🔋{mdl1.api_price})" if mdl1.api_price is not None else ""
                            m1_label = f"{name1}{price1}"
                        else:
                            m1_label = str(db_user.bot_model_1)
                    if getattr(db_user, 'bot_model_2', None):
                        res2 = await session.execute(select(Model).where(Model.id == int(db_user.bot_model_2)))
                        mdl2 = res2.scalar_one_or_none()
                        if mdl2:
                            name2 = mdl2.model_visible_name or mdl2.model
                            price2 = f" (🔋{mdl2.api_price})" if mdl2.api_price is not None else ""
                            m2_label = f"{name2}{price2}"
                        else:
                            m2_label = str(db_user.bot_model_2)
                    processor = UniversalAIProcessor(logger)
                    current_prompt = getattr(db_user, 'bot_system_content', '') or processor.get_default_system_prompt(user_lang)
                    title = "Current Bot Settings" if user_lang == 'en' else "Текущие настройки бота"
                    message = (
                        f"⚙️ <b>{title}</b>\n\n" +
                        f"{I18n.get(user_lang, 'messages.model_1_label')} {m1_label}\n"
                        f"{I18n.get(user_lang, 'messages.model_2_label')} {m2_label}\n"
                        f"{I18n.get(user_lang, 'messages.instruction_label')} <code>{current_prompt}</code>"
                    )
                    keyboard = BotKeyboards.settings_menu(user_lang)

                    # Send the settings message as a separate message
                    await query.message.reply_text(
                        text=message,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )

                    # Edit the original callback query message to be empty (or we could delete it)
                    await query.edit_message_text(text=" ")
                    return  # Exit early since we've handled the response

                else:
                    message = I18n.get('en', "messages.bot_settings_title") + I18n.get('en', "messages.user_not_found")
                    keyboard = BotKeyboards.settings_menu('en')

                    # Send the error message as a separate message
                    await query.message.reply_text(
                        text=message,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )

                    # Edit the original callback query message to be empty
                    await query.edit_message_text(text=" ")
                    return  # Exit early since we've handled the response
            finally:
                await session.close()

        elif data == "bot_settings_ai":
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                m1_label = "нет"
                m2_label = "нет"
                if db_user and getattr(db_user, 'bot_model_1', None):
                    res1 = await session.execute(select(Model).where(Model.id == int(db_user.bot_model_1)))
                    mdl1 = res1.scalar_one_or_none()
                    if mdl1:
                        name1 = mdl1.model_visible_name or mdl1.model
                        price1 = f" (🔋{mdl1.api_price})" if mdl1.api_price is not None else ""
                        m1_label = f"{name1}{price1}"
                    else:
                        m1_label = str(db_user.bot_model_1)
                if db_user and getattr(db_user, 'bot_model_2', None):
                    res2 = await session.execute(select(Model).where(Model.id == int(db_user.bot_model_2)))
                    mdl2 = res2.scalar_one_or_none()
                    if mdl2:
                        name2 = mdl2.model_visible_name or mdl2.model
                        price2 = f" (🔋{mdl2.api_price})" if mdl2.api_price is not None else ""
                        m2_label = f"{name2}{price2}"
                    else:
                        m2_label = str(db_user.bot_model_2)
            finally:
                await session.close()
            user_lang = db_user.language_code or 'en'
            message = I18n.get(user_lang, "messages.choose_slot")
            keyboard = BotKeyboards.ai_slots_menu(m1_label, m2_label, user_lang)

        elif data == "change_model_1" or data == "change_model_2" or data == "choose_slot_1" or data == "choose_slot_2":
            slot_index = 1 if data.endswith("_1") else 2
            # Get user for language
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
            finally:
                await session.close()

            # Load visible models
            session = async_session()
            try:
                res = await session.execute(select(Model).where(Model.visible >= 0))
                models = res.scalars().all()
            finally:
                await session.close()
            options = [(
                f"{(m.model_visible_name or m.model)}{(' (🔋'+str(m.api_price)+')') if m.api_price is not None else ''}",
                str(m.id)
            ) for m in models]
            message = I18n.get(db_user.language_code or 'en' if db_user else 'en', "messages.choose_model_for_slot", slot_index=slot_index)
            keyboard = BotKeyboards.models_for_slot_menu(options, slot_index, db_user.language_code or 'en' if db_user else 'en')

        elif data.startswith("set_model:"):
            try:
                _, slot_str, model_id_str = data.split(":")
                slot_index = int(slot_str)
                model_id = int(model_id_str)
            except Exception:
                slot_index = 1
                model_id = None
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                if slot_index == 1:
                    db_user.bot_model_1 = model_id
                else:
                    db_user.bot_model_2 = model_id
                await session.commit()
            finally:
                await session.close()
            message = I18n.get(db_user.language_code or 'en', "messages.slot_updated", slot_index=slot_index)
            keyboard = BotKeyboards.settings_menu(db_user.language_code or 'en')

        elif data.startswith("set_none:"):
            try:
                _, slot_str = data.split(":")
                slot_index = int(slot_str)
            except Exception:
                slot_index = 1
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                if slot_index == 1:
                    db_user.bot_model_1 = None
                else:
                    db_user.bot_model_2 = None
                await session.commit()
            finally:
                await session.close()
            message = I18n.get(db_user.language_code or 'en', "messages.slot_disabled", slot_index=slot_index)
            keyboard = BotKeyboards.settings_menu(db_user.language_code or 'en')

        elif data == "bot_settings_prompt":
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                processor = UniversalAIProcessor(logger)
                current_prompt_raw = getattr(db_user, 'bot_system_content', '') if db_user else ''
                current_prompt = current_prompt_raw or processor.get_default_system_prompt((db_user.language_code if db_user else 'en') or 'en')
            finally:
                await session.close()
            await query.message.reply_text(I18n.get(db_user.language_code or 'en', "messages.current_instruction"))
            if CopyTextButton:
                kb_copy = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Копировать", copy_text=CopyTextButton(current_prompt[:256] if current_prompt else ""))]])
                await query.message.reply_text(current_prompt or "—", reply_markup=kb_copy)
            else:
                await query.message.reply_text(current_prompt or "—")
            kb_back = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
            await query.message.reply_text(I18n.get(db_user.language_code or 'en', "messages.enter_new_instruction"), reply_markup=kb_back)
            if context.user_data is not None:
                context.user_data['awaiting_prompt_update'] = True
            return

        elif data == "earn_battery":
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                if db_user:
                    import os

                    earned_total = float(db_user.free_batteries_total or 0.0)
                    last_earned = db_user.time_of_last_earned_battery

                    rest_hours = int(os.getenv('REST_HOURS_BETWEEN_EARNED_BATTERY', '8'))
                    earned_battery = float(os.getenv('EARNED_BATTERY', '0.5'))

                    now = datetime.now(timezone.utc)
                    can_claim = True
                    time_until_next = None

                    if last_earned:
                        next_available = last_earned + timedelta(hours=rest_hours)
                        if now < next_available:
                            can_claim = False
                            time_until_next = next_available - now

                    user_lang = db_user.language_code or 'en'
                    if can_claim:
                        if user_lang == 'ru':
                            message = f"🔋 <b>Заработать батарейки</b>\n\n"
                            message += f"Всего заработано: <code>{earned_total:.1f}</code>🔋\n"
                            message += f"✅ Вы можете получить батарейку прямо сейчас!\n"
                            message += f"Размер награды: <code>{earned_battery:.1f}</code>🔋"
                        else:
                            message = f"🔋 <b>Earn Batteries</b>\n\n"
                            message += f"Total earned: <code>{earned_total:.1f}</code>🔋\n"
                            message += f"✅ You can claim a battery right now!\n"
                            message += f"Reward amount: <code>{earned_battery:.1f}</code>🔋"
                        keyboard = BotKeyboards.earn_battery_menu(user_lang)
                    else:
                        hours = int(time_until_next.total_seconds() // 3600)
                        minutes = int((time_until_next.total_seconds() % 3600) // 60)
                        if user_lang == 'ru':
                            message = f"⏰ <b>Нужно подождать ещё</b>\n\n"
                            message += f"Следующая батарейка будет доступна через: <code>{hours}ч {minutes}м</code>"
                        else:
                            message = f"⏰ <b>Need to wait more</b>\n\n"
                            message += f"Next battery available in: <code>{hours}h {minutes}m</code>"
                        keyboard = BotKeyboards.balance_menu(user_lang)
                else:
                    message = "❌ User not found"
                    keyboard = BotKeyboards.back_to_main('en')
            finally:
                await session.close()

        elif data == "claim_battery":
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                if db_user:
                    import os

                    rest_hours = int(os.getenv('REST_HOURS_BETWEEN_EARNED_BATTERY', '8'))
                    earned_battery = float(os.getenv('EARNED_BATTERY', '0.5'))

                    now = datetime.utcnow()
                    last_earned = db_user.time_of_last_earned_battery

                    can_claim = True
                    if last_earned:
                        next_available = last_earned + timedelta(hours=rest_hours)
                        if now < next_available:
                            can_claim = False

                    if can_claim:
                        # Update user balance and stats
                        db_user.balance = (db_user.balance or 0.0) + earned_battery
                        db_user.free_batteries_total = (db_user.free_batteries_total or 0.0) + earned_battery
                        db_user.time_of_last_earned_battery = now
                        await session.commit()

                        user_lang = db_user.language_code or 'en'
                        if user_lang == 'ru':
                            message = f"✅ <b>Батарейка получена!</b>\n\n"
                            message += f"Получено: <code>+{earned_battery:.1f}</code>🔋\n"
                            message += f"Текущий баланс: <code>{db_user.balance:.1f}</code>🔋"
                        else:
                            message = f"✅ <b>Battery claimed!</b>\n\n"
                            message += f"Received: <code>+{earned_battery:.1f}</code>🔋\n"
                            message += f"Current balance: <code>{db_user.balance:.1f}</code>🔋"

                        keyboard = BotKeyboards.balance_menu(user_lang)
                    else:
                        # Calculate remaining time
                        next_available = last_earned + timedelta(hours=rest_hours)
                        time_until_next = next_available - now
                        hours = int(time_until_next.total_seconds() // 3600)
                        minutes = int((time_until_next.total_seconds() % 3600) // 60)

                        user_lang = db_user.language_code or 'en'
                        if user_lang == 'ru':
                            message = f"⏰ <b>Нужно подождать ещё</b>\n\n"
                            message += f"Следующая батарейка будет доступна через: <code>{hours}ч {minutes}м</code>"
                        else:
                            message = f"⏰ <b>Need to wait more</b>\n\n"
                            message += f"Next battery available in: <code>{hours}h {minutes}m</code>"
                        keyboard = BotKeyboards.balance_menu(user_lang)
                else:
                    message = "❌ User not found"
                    keyboard = BotKeyboards.back_to_main('en')
            finally:
                await session.close()

        elif data.startswith("set_lang_"):
            new_lang = data.replace("set_lang_", "")
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                if db_user:
                    old_lang = db_user.language_code or 'en'
                    if old_lang != new_lang:
                        db_user.language_code = new_lang
                        await session.commit()
                        # Re-render profile with new language
                        worker_status, _ = await get_user_worker_status(db_user.id)
                        balance = float(db_user.balance) if db_user.balance is not None else 0.0
                        if new_lang == 'ru':
                            message = f"👤 <b>Профиль</b>\n\nID: <code>{db_user.telegram_id}</code>\nБаланс: <code>{balance:.1f}</code>🔋\nВоркер: <code>{worker_status}</code>"
                        else:
                            message = f"👤 <b>Profile</b>\n\nID: <code>{db_user.telegram_id}</code>\nBalance: <code>{balance:.1f}</code>🔋\nWorker: <code>{worker_status}</code>"
                        keyboard = BotKeyboards.profile_menu(new_lang)
                        await query.edit_message_text(
                            text=message,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                        # Send updated reply keyboard as a separate message
                        reply_kb = BotKeyboards.reply_keyboard(new_lang)
                        await query.message.reply_text(
                            I18n.get(new_lang, "messages.language_updated", lang=new_lang.upper()),
                            reply_markup=reply_kb
                        )
                    else:
                        # Language is already set, just acknowledge
                        await query.answer("Language is already set to " + new_lang.upper())
            finally:
                await session.close()

        else:
            message = "❓ Unknown command"
            keyboard = BotKeyboards.back_to_main(db_user.language_code if db_user else 'en')
        
        try:
            await query.edit_message_text(
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as edit_error:
            if "not modified" in str(edit_error).lower():
                # Message content is the same, just acknowledge
                await query.answer(f"Language changed to {new_lang.upper()}")
            else:
                raise edit_error
        
    except Exception as e:
        logger.error(f"Error in callback query handler: {e}")
        try:
            # Get user language for error message
            user = update.effective_user
            telegram_id = user.id
            session = async_session()
            try:
                result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
                db_user = result.scalar_one_or_none()
                user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
            finally:
                await session.close()
            await query.edit_message_text(
                "❌ Something went wrong. Please try again.",
                reply_markup=BotKeyboards.back_to_main(user_lang)
            )
        except:
            pass

async def reply_keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages from reply keyboard buttons"""
    logger.info(f"reply_keyboard_handler called with update: {update}")
    text = update.message.text

    # Get user's language to properly identify button
    user = update.effective_user
    session = async_session()
    try:
        result = await session.execute(select(User).where(User.telegram_id == int(user.id)))
        db_user = result.scalar_one_or_none()
        user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
    finally:
        await session.close()

    # Check if text matches any button using I18n
    if text == I18n.get(user_lang, "buttons.tma") or text in [I18n.get('ru', "buttons.tma"), I18n.get('en', "buttons.tma")]:
        # Send explanatory message with image first
        explanation_text = I18n.get(user_lang, "messages.agent_mode_explanation")
        image_path = os.path.join(os.path.dirname(__file__), "media", "tAIger-agent_mode.jpg")
        await update.message.reply_photo(
            photo=open(image_path, "rb"),
            caption=explanation_text,
            parse_mode="HTML"
        )

        # Show TMA launch menu with Mini App and Worker buttons
        await update.message.reply_text(
            I18n.get(user_lang, "messages.tma_launch_title") + "\n\n" + I18n.get(user_lang, "messages.tma_launch_description"),
            reply_markup=BotKeyboards.tma_menu(user_lang)
        )
    elif text == I18n.get(user_lang, "buttons.settings") or text in [I18n.get('ru', "buttons.settings"), I18n.get('en', "buttons.settings")]:
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(update.effective_user.id)))
            db_user = result.scalar_one_or_none()
            if db_user:
                # Get user language
                user_lang = db_user.language_code or 'en'

                # Send explanatory message with image first
                explanation_text = I18n.get(user_lang, "messages.bot_mode_explanation")
                image_path = os.path.join(os.path.dirname(__file__), "media", "tAIger-bot_mode.jpg")
                await update.message.reply_photo(
                    photo=open(image_path, "rb"),
                    caption=explanation_text,
                    parse_mode="HTML"
                )

                # Now prepare and send the settings message
                m1_label = "нет"
                m2_label = "нет"
                if getattr(db_user, 'bot_model_1', None):
                    res1 = await session.execute(select(Model).where(Model.id == int(db_user.bot_model_1)))
                    mdl1 = res1.scalar_one_or_none()
                    if mdl1:
                        name1 = mdl1.model_visible_name or mdl1.model
                        price1 = f" (🔋{mdl1.api_price})" if mdl1.api_price is not None else ""
                        m1_label = f"{name1}{price1}"
                    else:
                        m1_label = str(db_user.bot_model_1)
                if getattr(db_user, 'bot_model_2', None):
                    res2 = await session.execute(select(Model).where(Model.id == int(db_user.bot_model_2)))
                    mdl2 = res2.scalar_one_or_none()
                    if mdl2:
                        name2 = mdl2.model_visible_name or mdl2.model
                        price2 = f" (🔋{mdl2.api_price})" if mdl2.api_price is not None else ""
                        m2_label = f"{name2}{price2}"
                    else:
                        m2_label = str(db_user.bot_model_2)
                processor = UniversalAIProcessor(logger)
                current_prompt = getattr(db_user, 'bot_system_content', '') or processor.get_default_system_prompt(user_lang)
                title = "Current Bot Settings" if user_lang == 'en' else "Текущие настройки бота"
                msg = (
                    f"⚙️ <b>{title}</b>\n\n" +
                    f"{I18n.get(user_lang, 'messages.model_1_label')} {m1_label}\n"
                    f"{I18n.get(user_lang, 'messages.model_2_label')} {m2_label}\n"
                    f"{I18n.get(user_lang, 'messages.instruction_label')} <code>{current_prompt}</code>"
                )

                # Send the settings message as a separate message
                await update.message.reply_text(
                    msg,
                    reply_markup=BotKeyboards.settings_menu(user_lang),
                    parse_mode="HTML"
                )
            else:
                msg = I18n.get('en', "messages.bot_settings_title") + I18n.get('en', "messages.user_not_found")
                await update.message.reply_text(
                    msg,
                    reply_markup=BotKeyboards.settings_menu('en'),
                    parse_mode="HTML"
                )
        finally:
            await session.close()
    elif text == I18n.get(user_lang, "buttons.profile") or text in [I18n.get('ru', "buttons.profile"), I18n.get('en', "buttons.profile")]:
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(update.effective_user.id)))
            db_user = result.scalar_one_or_none()
            if db_user:
                worker_status, _ = await get_user_worker_status(db_user.id)
                msg = f"👤 <b>Профиль</b>\n\nID: <code>{db_user.telegram_id}</code>\nБаланс: <code>{db_user.balance:.1f}</code>🔋\nСтатус воркера: <code>{worker_status}</code>"
            else:
                msg = "❌ Пользователь не найден"
        finally:
            await session.close()
        await update.message.reply_text(
            msg,
            reply_markup=BotKeyboards.profile_menu(db_user.language_code if db_user else 'en'),
            parse_mode="HTML"
        )
    else:
        # If it's not a reply keyboard button, let the general text handler process it
        # This shouldn't happen because of the filter setup, but just in case
        logger.info(f"reply_keyboard_handler forwarding to text_message_handler")
        await text_message_handler(update, context)

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message sent by user (including forwarded posts and media)"""
    try:
        # Prevent reprocessing of updates
        if update_tracker.is_processed(update.update_id):
            logger.info(f"Ignoring already processed update {update.update_id}")
            return
            
        # Mark update as processed
        update_tracker.mark_processed(update.update_id)

        logger.info(f"text_message_handler called with update: {update}")
        user = update.effective_user
        chat_id = update.effective_chat.id
        message = update.message

        logger.info(f"Message type: {type(message)}")
        logger.info(f"Message content: text={getattr(message, 'text', 'None')}, caption={getattr(message, 'caption', 'None')}")
        logger.info(f"Message media: photo={hasattr(message, 'photo') and message.photo}, media_group_id={getattr(message, 'media_group_id', 'None')}")

        # Check if this message is from the bot itself to prevent feedback loop
        bot_id = context.bot_data.get('bot_id') if context.bot_data else None
        if bot_id and user.id == bot_id:
            logger.info("Ignoring message from bot itself to prevent feedback loop")
            return

        # Also check if the message is from the bot by username to be extra safe
        bot_username = context.bot.username if context.bot else None
        if bot_username and user.username == bot_username:
            logger.info("Ignoring message from bot itself (username match) to prevent feedback loop")
            return

        # Check if this is a forwarded message
        is_forwarded = hasattr(message, 'forward_date') and message.forward_date is not None

        # Check if this is a media group (album) message
        is_media_group = hasattr(message, 'media_group_id') and message.media_group_id is not None

        # Get the text content
        text_content = message.text or ""

        # If there's no text but there are captions (e.g., photos with captions)
        if not text_content and hasattr(message, 'caption') and message.caption:
            text_content = message.caption

        # Check if this is a simulated callback query from micro-client
        if text_content.startswith("CALLBACK:"):
            callback_data = text_content[9:]  # Remove "CALLBACK:" prefix
            logger.info(f"Simulated callback query with data: {callback_data}")
            # Create a mock CallbackQuery
            from telegram import CallbackQuery
            mock_query = CallbackQuery(
                id="simulated_" + str(update.update_id),
                from_user=user,
                chat_instance=str(chat_id),
                data=callback_data,
                message=message
            )
            # Create a mock update for callback query
            from telegram import Update
            mock_update = Update(update_id=update.update_id, callback_query=mock_query)
            # Call the callback query handler
            await callback_query_handler(mock_update, context)
            return
        
        logger.info(f"Text content to process: '{text_content}'")
        logger.info(f"Is media group: {is_media_group}")
        logger.info(f"Is forwarded: {is_forwarded}")
        
        # Handle media group messages
        if is_media_group:
            logger.info(f"Processing as media group with ID: {message.media_group_id}")
            # Store media group info in context for later processing
            media_group_id = message.media_group_id
            if 'media_groups' not in context.bot_data:
                context.bot_data['media_groups'] = {}
                
            if media_group_id not in context.bot_data['media_groups']:
                context.bot_data['media_groups'][media_group_id] = {
                    'messages': [],
                    'processed': False
                }
            
            # Add this message to the media group
            context.bot_data['media_groups'][media_group_id]['messages'].append(message)
            
            # If this is the first message in the group, schedule processing after a delay
            if len(context.bot_data['media_groups'][media_group_id]['messages']) == 1:
                logger.info(f"First message in group, scheduling processing")
                # Schedule processing after 2 seconds to allow all messages to arrive
                async def process_media_group():
                    await asyncio.sleep(2)
                    await _process_media_group(context, media_group_id, user, chat_id)
                
                # Create task to process media group
                asyncio.create_task(process_media_group())
            
            # Don't process this message further, wait for the group processing
            return
        
        # Check if user is entering new system prompt
        if context.user_data and context.user_data.get('awaiting_prompt_update'):
            # First check if the input is actually a system button - if so, process it as a button instead
            button_texts = get_all_button_texts()
            if text_content in button_texts:
                # This is actually a button press, not text input, so process as button
                # We need to call reply_keyboard_handler to handle this button
                await reply_keyboard_handler(update, context)
                return

            new_prompt = text_content.strip()
            if new_prompt:
                session = async_session()
                try:
                    result = await session.execute(select(User).where(User.telegram_id == int(user.id)))
                    db_user = result.scalar_one_or_none()
                    if db_user:
                        db_user.bot_system_content = new_prompt
                        await session.commit()
                        await update.message.reply_text(I18n.get(db_user.language_code, "messages.instruction_updated"), reply_markup=BotKeyboards.reply_keyboard(db_user.language_code))
                    else:
                        await update.message.reply_text("❌ Пользователь не найден", reply_markup=BotKeyboards.reply_keyboard('en'))
                finally:
                    await session.close()
            else:
                await update.message.reply_text(I18n.get(db_user.language_code, "messages.empty_instruction_rejected"), reply_markup=BotKeyboards.reply_keyboard(db_user.language_code))
            context.user_data['awaiting_prompt_update'] = False
            return

        # Per-user bot processing using bot_model_1/2 and bot_system_content
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(user.id)))
            db_user = result.scalar_one_or_none()
        finally:
            await session.close()
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден", reply_markup=BotKeyboards.reply_keyboard('en'))
            return
        if db_user.balance is None or float(db_user.balance) < 0:
            await update.message.reply_text("❌ Недостаточный баланс", reply_markup=BotKeyboards.reply_keyboard('en'))
            return
        system_prompt = getattr(db_user, 'bot_system_content', None) or UniversalAIProcessor(logger).get_default_system_prompt(db_user.language_code or 'en')
        selected_models = []
        if getattr(db_user, 'bot_model_1', None):
            selected_models.append(int(db_user.bot_model_1))
        if getattr(db_user, 'bot_model_2', None):
            selected_models.append(int(db_user.bot_model_2))
        if not selected_models:
            await update.message.reply_text("ℹ️ Модели не выбраны. Зайдите в 🛠Настройки бота → 📲Выбор ИИ", reply_markup=BotKeyboards.reply_keyboard(db_user.language_code))
            return
        for idx, model_id in enumerate(selected_models):
            try:
                # Send processing message before starting processing
                if idx == 0:  # First model (Model #1)
                    processing_msg = await update.message.reply_text(
                        I18n.get(db_user.language_code, "messages.processing_model_1"),
                        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                    )
                else:  # Second model (Model #2)
                    processing_msg = await update.message.reply_text(
                        I18n.get(db_user.language_code, "messages.processing_model_2"),
                        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                    )

                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model(text_content, system_prompt, model_id)

                # Delete the processing message after processing is complete
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                except:
                    # If deletion fails, edit the message to clear it
                    try:
                        await processing_msg.edit_text(" ")
                    except:
                        pass  # If both fail, just continue

                formatted_text = convert_markdown_to_html(enhanced_text)
                # Initialize UniversalAIProcessor for splitting long responses
                processor = UniversalAIProcessor(logger)

                # Define info_text for model metadata
                info_text = f"🤖 {model_name} | ⏱ {processing_time:.1f}s"

                full_response_text = formatted_text
                if message.photo:
                    photo = message.photo[-1]
                    if len(full_response_text) <= 1024:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=photo.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=photo.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                        )
                        await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                elif message.video:
                    if len(full_response_text) <= 1024:
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=message.video.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=message.video.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                        )
                        await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                elif message.document:
                    if len(full_response_text) <= 1024:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=message.document.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=message.document.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                        )
                        await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                elif message.audio:
                    if len(full_response_text) <= 1024:
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=message.audio.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=message.audio.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                        )
                        await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                elif message.animation:
                    if len(full_response_text) <= 1024:
                        await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=message.animation.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=message.animation.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                        )
                        await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                else:
                    # Split and send long text responses as multiple messages
                    logger.info(f"DEBUG: About to send split response. model_name={model_name}, processing_time={processing_time}")
                    try:
                        logger.info(f"DEBUG: info_text status: {'info_text' in locals()}")
                    except Exception as e:
                        logger.error(f"DEBUG: Error checking info_text: {e}")
                        
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        formatted_text,
                        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                        parse_mode="HTML"
                    )
            except Exception as e:
                # Try to delete the processing message in case of error
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                except:
                    pass
                await update.message.reply_text(f"❌ Ошибка обработки моделью {model_id}: {e}", reply_markup=BotKeyboards.reply_keyboard(db_user.language_code))
        return
        
        
    except Exception as e:
        logger.error(f"Error in text message handler: {e}", exc_info=True)
        error_message = f"❌ Sorry, something went wrong while processing your message. Please try again.\n\nDetailed error: {str(e)}"
        await update.message.reply_text(
            error_message,
            reply_markup=BotKeyboards.reply_keyboard()
        )

async def _process_media_group(context: ContextTypes.DEFAULT_TYPE, media_group_id: str, user, chat_id):
    """Process a complete media group (album)"""
    try:
        logger.info(f"_process_media_group called for media_group_id: {media_group_id}")
        
        # Check if this message is from the bot itself to prevent feedback loop
        bot_id = context.bot_data.get('bot_id') if context.bot_data else None
        if bot_id and user.id == bot_id:
            logger.info("Ignoring media group from bot itself to prevent feedback loop")
            # Clean up and return immediately
            if media_group_id in context.bot_data.get('media_groups', {}):
                del context.bot_data['media_groups'][media_group_id]
                logger.info(f"Cleaned up media group {media_group_id} from context")
            return
            
        # Also check by username
        bot_username = context.bot.username if context.bot else None
        if bot_username and user.username == bot_username:
            logger.info("Ignoring media group from bot itself (username match) to prevent feedback loop")
            # Clean up and return immediately
            if media_group_id in context.bot_data.get('media_groups', {}):
                del context.bot_data['media_groups'][media_group_id]
                logger.info(f"Cleaned up media group {media_group_id} from context")
            return
        
        # Check if already processed
        if (media_group_id not in context.bot_data.get('media_groups', {}) or 
            context.bot_data['media_groups'][media_group_id]['processed']):
            logger.info(f"Media group {media_group_id} already processed or not found")
            # Clean up and return
            if media_group_id in context.bot_data.get('media_groups', {}):
                del context.bot_data['media_groups'][media_group_id]
                logger.info(f"Cleaned up media group {media_group_id} from context")
            return
            
        # Mark as processed
        context.bot_data['media_groups'][media_group_id]['processed'] = True
        
        # Get all messages in the group
        messages = context.bot_data['media_groups'][media_group_id]['messages']
        logger.info(f"Processing media group with {len(messages)} messages")
        
        # Sort messages by message ID to maintain order
        messages.sort(key=lambda m: m.message_id)
        
        # Extract text from the first message with caption or any message with text
        album_text = ""
        for msg in messages:
            if msg.caption:
                album_text = msg.caption
                logger.info(f"Found caption in message {msg.message_id}: '{album_text}'")
                break
            elif msg.text:
                album_text = msg.text
                logger.info(f"Found text in message {msg.message_id}: '{album_text}'")
                break
        
        # If no text found, create a default message
        if not album_text.strip():
            album_text = "📸 Альбом фотографий"
            logger.info(f"No text found, using default: '{album_text}'")
        else:
            logger.info(f"Using album text: '{album_text}'")
        
        # Per-user bot processing using bot_model_1/2 and bot_system_content for media group
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(user.id)))
            db_user = result.scalar_one_or_none()
        finally:
            await session.close()
        if not db_user:
            await context.bot.send_message(chat_id=chat_id, text="❌ Пользователь не найден", reply_markup=BotKeyboards.reply_keyboard())
            return
        if db_user.balance is None or float(db_user.balance) < 0:
            await context.bot.send_message(chat_id=chat_id, text="❌ Недостаточный баланс", reply_markup=BotKeyboards.reply_keyboard())
            return
        system_prompt = getattr(db_user, 'bot_system_content', None) or UniversalAIProcessor(logger).get_default_system_prompt(db_user.language_code or 'en')
        selected_models = []
        if getattr(db_user, 'bot_model_1', None):
            selected_models.append(int(db_user.bot_model_1))
        if getattr(db_user, 'bot_model_2', None):
            selected_models.append(int(db_user.bot_model_2))
        if not selected_models:
            await context.bot.send_message(chat_id=chat_id, text="ℹ️ Модели не выбраны. Зайдите в 🛠Настройки бота → 📲Выбор ИИ", reply_markup=BotKeyboards.reply_keyboard())
            return

        for idx, model_id in enumerate(selected_models):
            try:
                # Send processing message before starting processing
                if idx == 0:  # First model (Model #1)
                    processing_msg = await context.bot.send_message(
                        chat_id=chat_id,
                        text=I18n.get(db_user.language_code, "messages.processing_model_1"),
                        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                    )
                else:  # Second model (Model #2)
                    processing_msg = await context.bot.send_message(
                        chat_id=chat_id,
                        text=I18n.get(db_user.language_code, "messages.processing_model_2"),
                        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code)
                    )

                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model(album_text, system_prompt, model_id)

                # Delete the processing message after processing is complete
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
                except:
                    # If deletion fails, edit the message to clear it
                    try:
                        await processing_msg.edit_text(" ")
                    except:
                        pass  # If both fail, just continue

                formatted_text = convert_markdown_to_html(enhanced_text)
                full_response_text = formatted_text
                
                media_list = []
                # Telegram caption limit for media group is 1024
                caption_for_group = full_response_text if len(full_response_text) <= 1024 else ""
                
                for i, msg in enumerate(messages):
                    caption = caption_for_group if i == 0 else ""
                    if msg.photo:
                        photo = msg.photo[-1]
                        media_list.append(InputMediaPhoto(media=photo.file_id, caption=caption, parse_mode="HTML"))
                    elif msg.video:
                        media_list.append(InputMediaVideo(media=msg.video.file_id, caption=caption, parse_mode="HTML"))
                    elif msg.document:
                        media_list.append(InputMediaDocument(media=msg.document.file_id, caption=caption, parse_mode="HTML"))
                    elif msg.audio:
                        media_list.append(InputMediaAudio(media=msg.audio.file_id, caption=caption, parse_mode="HTML"))
                    elif msg.animation:
                        media_list.append(InputMediaAnimation(media=msg.animation.file_id, caption=caption, parse_mode="HTML"))
                
                if media_list:
                    sent_messages = await context.bot.send_media_group(chat_id=chat_id, media=media_list)
                    # If text was too long for caption, send it separately
                    if not caption_for_group:
                        processor = UniversalAIProcessor(logger)
                        await processor.send_split_response(
                            context.bot,
                            chat_id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                            parse_mode="HTML"
                        )
                else:
                    processor = UniversalAIProcessor(logger)
                    await processor.send_split_response(
                        context.bot,
                        chat_id,
                        full_response_text,
                        reply_markup=BotKeyboards.reply_keyboard(db_user.language_code),
                        parse_mode="HTML"
                    )
            except Exception as e:
                # Try to delete the processing message in case of error
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
                except:
                    pass
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка обработки моделью {model_id}: {e}", reply_markup=BotKeyboards.reply_keyboard(db_user.language_code))
            
            # Add the sent message ID to prevent processing in feedback loop
            if hasattr(context, 'bot_data') and context.bot_data:
                if 'sent_message_ids' not in context.bot_data:
                    context.bot_data['sent_message_ids'] = set()
                context.bot_data['sent_message_ids'].add(sent_message.message_id)
        
    except Exception as e:
        logger.error(f"Error processing media group {media_group_id}: {e}", exc_info=True)
        # Send a simple text message with detailed error as fallback
        try:
            error_message = f"❌ Sorry, something went wrong while processing your media album. Please try again.\n\nDetailed error: {str(e)}"
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=error_message,
                reply_markup=BotKeyboards.reply_keyboard()
            )
            
            # Add the sent message ID to prevent processing in feedback loop
            if hasattr(context, 'bot_data') and context.bot_data:
                if 'sent_message_ids' not in context.bot_data:
                    context.bot_data['sent_message_ids'] = set()
                context.bot_data['sent_message_ids'].add(sent_message.message_id)
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")
    finally:
        # Clean up
        if media_group_id in context.bot_data.get('media_groups', {}):
            del context.bot_data['media_groups'][media_group_id]
            logger.info(f"Cleaned up media group {media_group_id} from context")

async def process_media_group_test_mode_immediate(text: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int, media_group_id: str):
    """Process media group text with multiple models in test mode and send responses immediately"""
    try:
        import os
        import asyncio
        from dotenv import load_dotenv
        from .keyboards import BotKeyboards
        load_dotenv()
        
        # Get test models from environment (support live reload and alias)
        test_models_str = os.getenv("TEST_MODELS") or os.getenv("TEST_MODEL") or ""
        if not test_models_str:
            error_message = "❌ TEST_MODELS not configured in environment"
            await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Parse test models
        try:
            test_model_ids = [int(model_id.strip()) for model_id in test_models_str.split(",")]
        except ValueError:
            error_message = "❌ Invalid TEST_MODELS format. Should be comma-separated integers."
            await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        if not test_model_ids:
            error_message = "❌ No test models configured"
            await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Prepare the prompt for text enhancement (from environment)
        system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful assistant. Improve the text by adding reasonable formatting and emojis. Respond in the same language as the input text. Make the text more engaging and well-structured."
        )
        
        # Process text with each model and send response immediately
        for i, model_id in enumerate(test_model_ids):
            try:
                # Fetch model name from database
                model_name = await get_model_name_from_db(model_id)
                if not model_name:
                    error_response = f"❌ Model ID {model_id}: Model not found in database"
                    await context.bot.send_message(chat_id=chat_id, text=error_response, reply_markup=BotKeyboards.reply_keyboard())
                    continue
                
                # Call OpenRouter API for text enhancement with specific model
                logger.info(f"Enhancing text with model {model_id} ({model_name}): {text}")
                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model(text, system_prompt, model_id)
                
                # Convert markdown to HTML and add model info and processing time to the result
                formatted_text = convert_markdown_to_html(enhanced_text)
                caption_text = _truncate_caption(formatted_text)
                logger.info(f"Successfully enhanced text with model {model_id}, sending response")

                # Send the response immediately as a text message with HTML parsing
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=formatted_text,
                    reply_markup=BotKeyboards.reply_keyboard(),
                    parse_mode="HTML"
                )
                logger.info(f"Sent test mode response {i+1} as separate message")
                
            except Exception as e:
                # Reply with error and continue to next model
                logger.error(f"Error processing text with model {model_id}: {e}", exc_info=True)
                error_response = f"❌ Model ID {model_id}: Error - {str(e)}"
                logger.info(f"Continuing after error for model {model_id}")
                await context.bot.send_message(chat_id=chat_id, text=error_response, reply_markup=BotKeyboards.reply_keyboard())
        
    except Exception as e:
        logger.error(f"Error in process_media_group_test_mode_immediate: {e}", exc_info=True)
        error_message = f"❌ Error in test mode processing: {str(e)}"
        await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
    finally:
        # Clean up media group data to prevent reprocessing
        if media_group_id and 'media_groups' in context.bot_data and media_group_id in context.bot_data['media_groups']:
            del context.bot_data['media_groups'][media_group_id]
            logger.info(f"Cleaned up media group {media_group_id} from context in test mode")

async def process_media_group_production_mode_immediate(text: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int, media_group_id: str):
    """Process media group text with multiple production models and send responses immediately"""
    try:
        import os
        import asyncio
        from dotenv import load_dotenv
        from .keyboards import BotKeyboards
        load_dotenv()
        
        # Get production models from environment
        prod_models_str = os.getenv("PROD_MODELS") or ""
        if not prod_models_str:
            error_message = "❌ PROD_MODELS not configured in environment"
            await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Parse production models
        try:
            prod_model_ids = [int(model_id.strip()) for model_id in prod_models_str.split(",")]
        except ValueError:
            error_message = "❌ Invalid PROD_MODELS format. Should be comma-separated integers."
            await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        if not prod_model_ids:
            error_message = "❌ No production models configured"
            await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Prepare the prompt for text enhancement (from environment)
        system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful assistant. Improve the text by adding reasonable formatting and emojis. Respond in the same language as the input text. Make the text more engaging and well-structured."
        )
        
        # Process text with each model and send response immediately
        for i, model_id in enumerate(prod_model_ids):
            try:
                # Fetch model name from database
                model_name = await get_model_name_from_db(model_id)
                if not model_name:
                    error_response = f"❌ Model ID {model_id}: Model not found in database"
                    await context.bot.send_message(chat_id=chat_id, text=error_response, reply_markup=BotKeyboards.reply_keyboard())
                    continue
                
                # Call OpenRouter API for text enhancement with specific model (no rate limiting for paid models)
                logger.info(f"Enhancing text with production model {model_id} ({model_name}): {text}")
                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model_no_rate_limit(text, system_prompt, model_id)
                
                # Convert markdown to HTML and add model info and processing time to the result
                formatted_text = convert_markdown_to_html(enhanced_text)
                logger.info(f"Successfully enhanced text with production model {model_id}, sending response")

                # Initialize UniversalAIProcessor for splitting long responses
                processor = UniversalAIProcessor(logger)
                await processor.send_split_response(
                    context.bot,
                    chat_id,
                    formatted_text,
                    reply_markup=BotKeyboards.reply_keyboard(),
                    parse_mode="HTML"
                )
                logger.info(f"Sent production mode response {i+1} as separate message")
                
            except Exception as e:
                # Reply with error and continue to next model
                logger.error(f"Error processing text with model {model_id}: {e}", exc_info=True)
                error_response = f"❌ Model ID {model_id}: Error - {str(e)}"
                logger.info(f"Continuing after error for model {model_id}")
                await context.bot.send_message(chat_id=chat_id, text=error_response, reply_markup=BotKeyboards.reply_keyboard())
        
    except Exception as e:
        logger.error(f"Error in process_media_group_production_mode_immediate: {e}", exc_info=True)
        error_message = f"❌ Error in production mode processing: {str(e)}"
        await context.bot.send_message(chat_id=chat_id, text=error_message, reply_markup=BotKeyboards.reply_keyboard())
    finally:
        # Clean up media group data to prevent reprocessing
        if media_group_id and 'media_groups' in context.bot_data and media_group_id in context.bot_data['media_groups']:
            del context.bot_data['media_groups'][media_group_id]
            logger.info(f"Cleaned up media group {media_group_id} from context in production mode")

async def process_user_text(text: str, user: User, is_forwarded: bool = False) -> str:
    """Process user text and return processed result"""
    try:
        # Check if text is too long
        if len(text) > 2000:
            return "❌ Сообщение слишком длинное. Пожалуйста, отправьте текст короче 2000 символов."
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check if test mode is enabled
        test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
        
        if test_mode:
            # Process text with multiple models in test mode
            return await process_user_text_test_mode(text, is_forwarded)
        
        # Check if PROD_MODELS is configured for production mode
        prod_models_str = os.getenv("PROD_MODELS")
        if prod_models_str:
            # Process text with multiple production models
            return await process_user_text_production_mode(text, is_forwarded)
        
        # Fallback to single model processing (original behavior)
        # Prepare the prompt for text enhancement (from environment)
        system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful assistant. Improve the text by adding reasonable formatting and emojis. Respond in the same language as the input text. Make the text more engaging and well-structured."
        )
        
        # Call OpenRouter API for text enhancement
        logger.info(f"Enhancing text: {text}")
        enhanced_text, model_name, processing_time = await enhance_text_with_openrouter(text, system_prompt)
        logger.info(f"Enhanced text: '{enhanced_text}'")
        
        # Convert markdown to HTML and add model name and processing time to the response
        formatted_text = convert_markdown_to_html(enhanced_text)

        return formatted_text
        
    except Exception as e:
        logger.error(f"Error in process_user_text: {e}", exc_info=True)
        # Return a friendly error message when API limit is exceeded
        if "402" in str(e) or "insufficient credits" in str(e).lower():
            return "⚡ Все ИИ жрут электричество. Бесплатный лимит на сегодня , увы, закончился:(. Решение - приходи завтра пораньше, пока шустрые конкуренты  спят:). Альтернатива - заходи в ТМА, там тоже халява есть:)"
        else:
            # For other errors, return a generic response with detailed error information
            error_type = type(e).__name__
            error_message = str(e)
            
            # Create a user-friendly error message with technical details
            user_message = "❌ ИИ не смог обработать ваш текст. Попробуйте еще раз или отправьте другой текст.\n\n"
            user_message += f"Технические детали ошибки:\n"
            user_message += f"• Тип ошибки: {error_type}\n"
            user_message += f"• Сообщение: {error_message}\n\n"
            
            if is_forwarded:
                user_message += f"Получено пересланное сообщение:\n{text[:200]}{'...' if len(text) > 200 else ''}\n\n"
            else:
                user_message += f"Получено сообщение:\n{text[:200]}{'...' if len(text) > 200 else ''}\n\n"
            
            user_message += "Если проблема повторяется, попробуйте:\n"
            user_message += "1. Отправить более короткий текст\n"
            user_message += "2. Проверить отсутствие специальных символов\n"
            user_message += "3. Попробовать позже\n\n"
            user_message += "Альтернатива - заходи в ТМА, там тоже халява есть :)"
            
            return user_message

async def process_user_text_test_mode_immediate(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE, is_forwarded: bool = False):
    """Process user text with multiple models in test mode and send responses immediately"""
    try:
        import os
        import asyncio
        from dotenv import load_dotenv
        from .keyboards import BotKeyboards
        load_dotenv()
        
        # Get test models from environment (support live reload and alias)
        test_models_str = os.getenv("TEST_MODELS") or os.getenv("TEST_MODEL") or ""
        if not test_models_str:
            error_message = "❌ TEST_MODELS not configured in environment"
            await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Parse test models
        try:
            test_model_ids = [int(model_id.strip()) for model_id in test_models_str.split(",")]
        except ValueError:
            error_message = "❌ Invalid TEST_MODELS format. Should be comma-separated integers."
            await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        if not test_model_ids:
            error_message = "❌ No test models configured"
            await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Prepare the prompt for text enhancement (from environment)
        system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful assistant. Improve the text by adding reasonable formatting and emojis. Respond in the same language as the input text. Make the text more engaging and well-structured."
        )
        
        # Get message object for media handling
        message = update.message
        
        # Store bot ID to prevent feedback loop
        bot_id = context.bot_data.get('bot_id') if context.bot_data else None
        
        # Initialize UniversalAIProcessor for splitting long responses
        from uni_text_processor.universal_processor import UniversalAIProcessor
        processor = UniversalAIProcessor(logger)
        
        # Get user language for processing messages
        from models import User
        from db import async_session
        from sqlalchemy import select
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(update.effective_user.id)))
            db_user = result.scalar_one_or_none()
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
        finally:
            await session.close()

        # Process text with each model and send response immediately
        logger.info(f"Starting test mode processing for {len(test_model_ids)} models: {test_model_ids}")
        for i, model_id in enumerate(test_model_ids):
            try:
                logger.info(f"Processing model {i+1}/{len(test_model_ids)}: Model ID {model_id}")

                # Send processing message before starting processing
                if i == 0:  # First model (Model #1)
                    processing_msg = await update.message.reply_text(
                        I18n.get(user_lang, "messages.processing_model_1"),
                        reply_markup=BotKeyboards.reply_keyboard(user_lang)
                    )
                else:  # Second model (Model #2)
                    processing_msg = await update.message.reply_text(
                        I18n.get(user_lang, "messages.processing_model_2"),
                        reply_markup=BotKeyboards.reply_keyboard(user_lang)
                    )

                # Fetch model name from database
                model_name = await get_model_name_from_db(model_id)
                if not model_name:
                    # Try to delete the processing message in case of error
                    try:
                        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                    except:
                        pass
                    error_response = f"❌ Model ID {model_id}: Model not found in database"
                    logger.warning(f"Model not found: {model_id}")
                    await update.message.reply_text(error_response, reply_markup=BotKeyboards.reply_keyboard(user_lang))
                    continue

                # Call OpenRouter API for text enhancement with specific model
                logger.info(f"Enhancing text with model {model_id} ({model_name}): {text}")
                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model(text, system_prompt, model_id)

                # Delete the processing message after processing is complete
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                except:
                    # If deletion fails, edit the message to clear it
                    try:
                        await processing_msg.edit_text(" ")
                    except:
                        pass  # If both fail, just continue
                
                # Convert markdown to HTML and add model info and processing time to the result
                formatted_text = convert_markdown_to_html(enhanced_text)
                caption_text = _truncate_caption(formatted_text)
                
                # Send the response immediately with HTML parsing, splitting long responses into multiple messages
                # Initialize UniversalAIProcessor for splitting long responses
                processor = UniversalAIProcessor(logger)
                
                full_response_text = formatted_text
                sent_message = None
                if message.photo:
                    photo = message.photo[-1]
                    if len(full_response_text) <= 1024:
                        sent_message = await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=photo.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=photo.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang)
                        )
                        sent_messages = await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                        sent_message = sent_messages[0] if sent_messages else None
                elif message.video:
                    if len(full_response_text) <= 1024:
                        sent_message = await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=message.video.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=message.video.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang)
                        )
                        sent_messages = await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                        sent_message = sent_messages[0] if sent_messages else None
                elif message.document:
                    if len(full_response_text) <= 1024:
                        sent_message = await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=message.document.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=message.document.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang)
                        )
                        sent_messages = await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                        sent_message = sent_messages[0] if sent_messages else None
                elif message.audio:
                    if len(full_response_text) <= 1024:
                        sent_message = await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=message.audio.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=message.audio.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang)
                        )
                        sent_messages = await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                        sent_message = sent_messages[0] if sent_messages else None
                elif message.animation:
                    if len(full_response_text) <= 1024:
                        sent_message = await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=message.animation.file_id,
                            caption=full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=message.animation.file_id,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang)
                        )
                        sent_messages = await processor.send_split_response(
                            context.bot,
                            update.effective_chat.id,
                            full_response_text,
                            reply_markup=BotKeyboards.reply_keyboard(user_lang),
                            parse_mode="HTML"
                        )
                        sent_message = sent_messages[0] if sent_messages else None
                else:
                    # Split and send long text responses as multiple messages
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        formatted_text,
                        reply_markup=BotKeyboards.reply_keyboard(user_lang),
                        parse_mode="HTML"
                    )
                    # Use the first message for tracking
                    sent_message = sent_messages[0] if sent_messages else None
                
                # Add the sent message ID to a list to prevent processing in feedback loop
                if hasattr(context, 'bot_data') and context.bot_data:
                    if 'sent_message_ids' not in context.bot_data:
                        context.bot_data['sent_message_ids'] = set()
                    if sent_message:
                        context.bot_data['sent_message_ids'].add(sent_message.message_id)
                
            except Exception as e:
                # Reply with error and continue to next model
                logger.error(f"Error processing text with model {model_id}: {e}", exc_info=True)
                error_response = f"❌ Model ID {model_id}: Error - {str(e)}"
                logger.info(f"Continuing after error for model {model_id}")
                await update.message.reply_text(error_response, reply_markup=BotKeyboards.reply_keyboard())
        
    except Exception as e:
        logger.error(f"Error in process_user_text_test_mode_immediate: {e}", exc_info=True)
        error_message = f"❌ Error in test mode processing: {str(e)}"
        await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())

async def process_user_text_test_mode(text: str, is_forwarded: bool = False) -> str:
    """Process user text with multiple models in test mode"""
    try:
        import os
        from dotenv import load_dotenv
        import asyncio
        load_dotenv()
        
        # Get test models from environment (support live reload and alias)
        test_models_str = os.getenv("TEST_MODELS") or os.getenv("TEST_MODEL") or ""
        if not test_models_str:
            return "❌ TEST_MODELS not configured in environment"
        
        # Parse test models
        try:
            test_model_ids = [int(model_id.strip()) for model_id in test_models_str.split(",")]
        except ValueError:
            return "❌ Invalid TEST_MODELS format. Should be comma-separated integers."
        
        if not test_model_ids:
            return "❌ No test models configured"
        
        # Prepare the prompt for text enhancement (from environment)
        system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful assistant. Improve the text by adding reasonable formatting and emojis. Respond in the same language as the input text. Make the text more engaging and well-structured."
        )
        
        # Process text with each model and collect results
        results = []
        for i, model_id in enumerate(test_model_ids):
            try:
                # Fetch model name from database
                model_name = await get_model_name_from_db(model_id)
                if not model_name:
                    results.append(f"❌ Model ID {model_id}: Model not found in database")
                    continue
                
                # Call OpenRouter API for text enhancement with specific model
                logger.info(f"Enhancing text with model {model_id} ({model_name}): {text}")
                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model(text, system_prompt, model_id)
                
                # Convert markdown to HTML and add model info and processing time to the result
                formatted_text = convert_markdown_to_html(enhanced_text)
                results.append(formatted_text)
                
            except Exception as e:
                logger.error(f"Error processing text with model {model_id}: {e}", exc_info=True)
                results.append(f"❌ Model ID {model_id}: Error - {str(e)}")
        
        # Combine all results
        if not results:
            return "❌ No results from any model"
        
        return "\n\n---\n\n".join(results)
        
    except Exception as e:
        logger.error(f"Error in process_user_text_test_mode: {e}", exc_info=True)
        return f"❌ Error in test mode processing: {str(e)}"

async def process_user_text_production_mode(text: str, is_forwarded: bool = False) -> str:
    """Process user text with multiple production models"""
    try:
        import os
        from dotenv import load_dotenv
        import asyncio
        load_dotenv()
        
        # Get production models from environment
        prod_models_str = os.getenv("PROD_MODELS") or ""
        if not prod_models_str:
            return "❌ PROD_MODELS not configured in environment"
        
        # Parse production models
        try:
            prod_model_ids = [int(model_id.strip()) for model_id in prod_models_str.split(",")]
        except ValueError:
            return "❌ Invalid PROD_MODELS format. Should be comma-separated integers."
        
        if not prod_model_ids:
            return "❌ No production models configured"
        
        # Prepare the prompt for text enhancement (from environment)
        system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful assistant. Improve the text by adding reasonable formatting and emojis. Respond in the same language as the input text. Make the text more engaging and well-structured."
        )
        
        # Process text with each model and collect results
        results = []
        for i, model_id in enumerate(prod_model_ids):
            try:
                # Fetch model name from database
                model_name = await get_model_name_from_db(model_id)
                if not model_name:
                    results.append(f"❌ Model ID {model_id}: Model not found in database")
                    continue
                
                # Call OpenRouter API for text enhancement with specific model
                # For production models (paid), we don't need rate limiting
                logger.info(f"Enhancing text with production model {model_id} ({model_name}): {text}")
                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model_no_rate_limit(text, system_prompt, model_id)
                
                # Convert markdown to HTML and add model info and processing time to the result
                formatted_text = convert_markdown_to_html(enhanced_text)
                results.append(formatted_text)
                
            except Exception as e:
                logger.error(f"Error processing text with model {model_id}: {e}", exc_info=True)
                results.append(f"❌ Model ID {model_id}: Error - {str(e)}")
        
        # Combine all results
        if not results:
            return "❌ No results from any model"
        
        return "\n\n---\n\n".join(results)
        
    except Exception as e:
        logger.error(f"Error in process_user_text_production_mode: {e}", exc_info=True)
        return f"❌ Error in production mode processing: {str(e)}"

async def process_user_text_production_mode_immediate(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE, is_forwarded: bool = False):
    """Process user text with multiple production models and send responses immediately"""
    try:
        import os
        import asyncio
        from dotenv import load_dotenv
        from .keyboards import BotKeyboards
        load_dotenv()
        
        # Get production models from environment
        prod_models_str = os.getenv("PROD_MODELS") or ""
        if not prod_models_str:
            error_message = "❌ PROD_MODELS not configured in environment"
            await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Parse production models
        try:
            prod_model_ids = [int(model_id.strip()) for model_id in prod_models_str.split(",")]
        except ValueError:
            error_message = "❌ Invalid PROD_MODELS format. Should be comma-separated integers."
            await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        if not prod_model_ids:
            error_message = "❌ No production models configured"
            await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())
            return
        
        # Prepare the prompt for text enhancement (from environment)
        system_prompt = os.getenv(
            "SYSTEM_PROMPT",
            "You are a helpful assistant. Improve the text by adding reasonable formatting and emojis. Respond in the same language as the input text. Make the text more engaging and well-structured."
        )
        
        # Get message object for media handling
        message = update.message
        
        # Store bot ID to prevent feedback loop
        bot_id = context.bot_data.get('bot_id') if context.bot_data else None
        
        # Initialize UniversalAIProcessor for splitting long responses
        from uni_text_processor.universal_processor import UniversalAIProcessor
        processor = UniversalAIProcessor(logger)
        
        # Get user language for processing messages
        from models import User
        from db import async_session
        from sqlalchemy import select
        session = async_session()
        try:
            result = await session.execute(select(User).where(User.telegram_id == int(update.effective_user.id)))
            db_user = result.scalar_one_or_none()
            user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
        finally:
            await session.close()

        # Process text with each model and send response immediately
        logger.info(f"Starting production mode processing for {len(prod_model_ids)} models: {prod_model_ids}")
        for i, model_id in enumerate(prod_model_ids):
            try:
                logger.info(f"Processing model {i+1}/{len(prod_model_ids)}: Model ID {model_id}")

                # Send processing message before starting processing
                if i == 0:  # First model (Model #1)
                    processing_msg = await update.message.reply_text(
                        I18n.get(user_lang, "messages.processing_model_1"),
                        reply_markup=BotKeyboards.reply_keyboard(user_lang)
                    )
                else:  # Second model (Model #2)
                    processing_msg = await update.message.reply_text(
                        I18n.get(user_lang, "messages.processing_model_2"),
                        reply_markup=BotKeyboards.reply_keyboard(user_lang)
                    )

                # Fetch model name from database
                model_name = await get_model_name_from_db(model_id)
                if not model_name:
                    # Try to delete the processing message in case of error
                    try:
                        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                    except:
                        pass
                    error_response = f"❌ Model ID {model_id}: Model not found in database"
                    logger.warning(f"Model not found: {model_id}")
                    await update.message.reply_text(error_response, reply_markup=BotKeyboards.reply_keyboard(user_lang))
                    continue

                # Call OpenRouter API for text enhancement with specific model (no rate limiting for paid models)
                logger.info(f"Enhancing text with production model {model_id} ({model_name}): {text}")
                enhanced_text, model_name, processing_time = await enhance_text_with_openrouter_for_model_no_rate_limit(text, system_prompt, model_id)

                # Delete the processing message after processing is complete
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                except:
                    # If deletion fails, edit the message to clear it
                    try:
                        await processing_msg.edit_text(" ")
                    except:
                        pass  # If both fail, just continue
                
                # Convert markdown to HTML and add model info and processing time to the result
                formatted_text = convert_markdown_to_html(enhanced_text)

                # Send the response immediately with HTML parsing, splitting long responses into multiple messages
                # Initialize UniversalAIProcessor for splitting long responses
                processor = UniversalAIProcessor(logger)

                if message.photo:
                    photo = message.photo[-1]
                    # Split and send long caption responses as multiple messages
                    caption_text = formatted_text
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        caption_text,
                        reply_markup=BotKeyboards.reply_keyboard(user_lang),
                        parse_mode="HTML"
                    )
                elif message.video:
                    # Split and send long caption responses as multiple messages
                    caption_text = formatted_text
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        caption_text,
                        reply_markup=BotKeyboards.reply_keyboard(user_lang),
                        parse_mode="HTML"
                    )
                elif message.document:
                    # Split and send long caption responses as multiple messages
                    caption_text = formatted_text
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        caption_text,
                        reply_markup=BotKeyboards.reply_keyboard(user_lang),
                        parse_mode="HTML"
                    )
                elif message.audio:
                    # Split and send long caption responses as multiple messages
                    caption_text = formatted_text
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        caption_text,
                        reply_markup=BotKeyboards.reply_keyboard(user_lang),
                        parse_mode="HTML"
                    )
                elif message.animation:
                    # Split and send long caption responses as multiple messages
                    caption_text = formatted_text
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        caption_text,
                        reply_markup=BotKeyboards.reply_keyboard(user_lang),
                        parse_mode="HTML"
                    )
                else:
                    # Split and send long text responses as multiple messages
                    sent_messages = await processor.send_split_response(
                        context.bot,
                        update.effective_chat.id,
                        formatted_text,
                        reply_markup=BotKeyboards.reply_keyboard(user_lang),
                        parse_mode="HTML"
                    )
                    logger.info(f"Processing text message")
            except Exception as e:
                logger.error(f"Error in process_user_text_production_mode_immediate: {e}", exc_info=True)
                await update.message.reply_text(f"❌ Error in production mode processing: {str(e)}", reply_markup=BotKeyboards.reply_keyboard())
    except Exception as e:
        logger.error(f"Error in process_user_text_production_mode_immediate: {e}", exc_info=True)
        error_message = f"❌ Error in production mode processing: {str(e)}"
        await update.message.reply_text(error_message, reply_markup=BotKeyboards.reply_keyboard())
        return
        
async def get_model_name_from_db(model_id: int) -> str:
    """Fetch model name from database based on model ID"""
    try:
        import sys
        import os
        # Add parent directory to path to import models and services
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from models import Model
        from db import async_session
        from sqlalchemy import select
        
        session = async_session()
        try:
            result = await session.execute(
                select(Model.model).where(Model.id == model_id)
            )
            model_name = result.scalar_one_or_none()
            return model_name
        finally:
            await session.close()
    except Exception as e:
        # If database connection fails, return None to use fallback
        logger.warning(f"Failed to connect to database to fetch model name: {e}")
        return None

async def enhance_text_with_openrouter_for_model(text: str, system_prompt: str, model_id: int) -> tuple:
    start_time = time.time()
    db_utils = DatabaseUtils(logger)
    model = await db_utils.get_model_by_id(model_id)
    if not model:
        model_name = os.getenv("FALLBACK_OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")
        provider_id = 1
    else:
        model_name = model["model"]
        provider_id = model.get("provider", 0)
    processor = UniversalAIProcessor(logger)
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        result = await processor.process_text_with_model(
            system_content=system_prompt,
            user_content=text,
            model_id=model_id,
            model_name=model_name,
            provider_id=provider_id,
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            http_session=session
        )
        if result["success"]:
            return (result["result"], model_name, result["processing_time"])
        raise Exception(result["result"]) 

async def enhance_text_with_openrouter(text: str, system_prompt: str) -> tuple:
    model_id = int(os.getenv("MODEL_ID", "19"))
    return await enhance_text_with_openrouter_for_model(text, system_prompt, model_id)

async def enhance_text_with_openrouter_for_model_no_rate_limit(text: str, system_prompt: str, model_id: int) -> tuple:
    return await enhance_text_with_openrouter_for_model(text, system_prompt, model_id)

def setup_handlers(application: Application):
    """Set up all command and callback handlers"""
    print("DEBUG: Setting up handlers")

    # Command handlers with explicit bot username to avoid initialization issues
    application.add_handler(CommandHandler("start", start_command))
    print("DEBUG: Added /start command handler")

    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("worker", worker_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("help", help_command))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Create button filter using centralized button texts
    button_texts = get_all_button_texts()
    button_filter = filters.Regex(f"^({'|'.join(map(re.escape, button_texts))})$")

    # Message handler for reply keyboard buttons (specific buttons only)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & button_filter,
        reply_keyboard_handler
    ), group=1)


    # Message handler for all other messages (text and media)
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL |
         filters.AUDIO | filters.ANIMATION | filters.CAPTION) & ~filters.COMMAND & ~button_filter,
        text_message_handler
    ), group=2)

    print("DEBUG: All handlers set up")
    logger.info("Bot handlers set up successfully")


async def pre_checkout_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query from Telegram Stars payment"""
    try:
        query = update.pre_checkout_query
        if not query:
            return
        
        payload = query.invoice_payload
        
        # Проверяем, существует ли платеж в БД
        session = async_session()
        try:
            result = await session.execute(
                select(Payment).where(Payment.telegram_pre_checkout_id == payload)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                await query.answer(ok=False, error_message="Payment not found")
                return
            
            # Проверяем статус платежа
            if payment.status != 'pending':
                await query.answer(ok=False, error_message="Payment already processed")
                return
            
            # Подтверждаем pre-checkout
            await query.answer(ok=True)
            
        finally:
            await session.close()
            
    except Exception as e:
        logger.error(f"Error in pre-checkout handler: {e}")
        await query.answer(ok=False, error_message="Payment verification failed")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment from Telegram Stars"""
    try:
        # Get the message from the successful payment update
        message = update.message
        if not message or not message.successful_payment:
            return
        
        successful_payment = message.successful_payment
        payload = successful_payment.invoice_payload
        
        # Находим платеж в БД
        session = async_session()
        try:
            result = await session.execute(
                select(Payment).where(Payment.telegram_pre_checkout_id == payload)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                logger.error(f"Payment not found for payload: {payload}")
                return
            
            # Проверяем, не был ли уже обработан
            if payment.status == 'completed':
                logger.info(f"Payment {payment.id} already completed")
                return
            
            # Получаем пользователя
            user_result = await session.execute(
                select(User).where(User.id == payment.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User not found for payment: {payment.id}")
                return
            
            # Обновляем баланс пользователя
            user.balance = (user.balance or 0.0) + payment.batteries_received
            
            # Обновляем статус платежа
            payment.status = 'completed'
            payment.telegram_invoice_id = successful_payment.telegram_payment_charge_id
            payment.completed_at = datetime.now(timezone.utc)
            
            await session.commit()
            await session.refresh(user)
            
            # Отправляем подтверждение пользователю
            user_lang = user.language_code if user.language_code in ['ru', 'en'] else 'en'
            success_message = I18n.get(
                user_lang,
                "messages.payment_success",
                batteries=payment.batteries_received,
                balance=user.balance
            )
            
            await update.message.reply_text(
                success_message,
                reply_markup=BotKeyboards.balance_menu(user_lang),
                parse_mode="HTML"
            )
            
            logger.info(f"Payment {payment.id} completed successfully. User {user.id} received {payment.batteries_received} batteries")
            
        finally:
            await session.close()
            
    except Exception as e:
        logger.error(f"Error in successful payment handler: {e}", exc_info=True)
