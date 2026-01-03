import os
import logging
from dotenv import load_dotenv
from telegram import Update, Bot, BotCommand
from telegram.ext import Application, ContextTypes
from fastapi import HTTPException
from typing import Optional
import asyncio
import time
from .update_tracker import update_tracker

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")
        
        self.webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        self.webhook_secret = os.getenv("TELEGRAM_BOT_SECRET", "")
        
        # Create bot instance
        self.bot = Bot(token=self.token)
        self.application: Optional[Application] = None
        
    async def initialize(self, start_polling=False):
        """Initialize the bot application"""
        try:
            # Create application
            if not self.token:
                raise ValueError("TELEGRAM_BOT_TOKEN is required")
            self.application = Application.builder().token(self.token).build()
            
            # Initialize the bot properly
            await self.bot.initialize()
            
            # Get bot info and store bot ID in bot_data for use in handlers
            bot_info = await self.bot.get_me()
            if self.application:
                self.application.bot_data['bot_id'] = bot_info.id
                self.application.bot_data['bot_username'] = bot_info.username
                # Clear any existing media group data to prevent reprocessing after restart
                self.application.bot_data['media_groups'] = {}
                # Initialize sent_message_ids set to track messages sent by bot
                self.application.bot_data['sent_message_ids'] = set()
                logger.info(f"Bot ID stored in bot_data: {bot_info.id}")
                logger.info(f"Bot username stored in bot_data: {bot_info.username}")
                logger.info("Cleared media_groups data to prevent reprocessing")
                logger.info("Initialized sent_message_ids set to track bot messages")
            
            # Set up commands
            await self.setup_commands()
            
            # Set up handlers
            from .handlers import setup_handlers
            setup_handlers(self.application)
            
            # Initialize application
            await self.application.initialize()
            
            # Start polling if requested
            if start_polling:
                await self.start_polling()
            
            logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def setup_commands(self):
        """Set up bot commands menu"""
        commands = [
            BotCommand("start", "Main dashboard and balance"),
            BotCommand("balance", "Check current balance"),
            BotCommand("worker", "Worker control panel"),
            BotCommand("logs", "View recent activity"),
            BotCommand("help", "Show help message")
        ]
        
        try:
            if self.application:
                await self.application.bot.set_my_commands(commands)
            else:
                async with self.bot:
                    await self.bot.set_my_commands(commands)  # type: ignore
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
    
    async def set_webhook(self, webhook_url: str):
        """Set webhook for the bot"""
        try:
            if self.application:
                await self.application.bot.set_webhook(
                    url=webhook_url,
                    secret_token=self.webhook_secret,
                    drop_pending_updates=True
                )
            else:
                async with self.bot:
                    await self.bot.set_webhook(  # type: ignore
                        url=webhook_url,
                        secret_token=self.webhook_secret,
                        drop_pending_updates=True
                    )
            logger.info(f"Webhook set to: {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            raise
    
    async def remove_webhook(self):
        """Remove webhook and switch to polling"""
        try:
            if self.application:
                await self.application.bot.delete_webhook(drop_pending_updates=True)
            else:
                async with self.bot:
                    await self.bot.delete_webhook(drop_pending_updates=True)  # type: ignore
            logger.info("Webhook removed and pending updates dropped")
        except Exception as e:
            logger.error(f"Failed to remove webhook: {e}")
    
    async def process_update(self, update_data: dict) -> dict:
        """Process webhook update"""
        try:
            print(f"DEBUG: Received update: {update_data}")
            if not self.application:
                raise HTTPException(status_code=500, detail="Bot not initialized")
            
            # Create Update object from webhook data
            update = Update.de_json(update_data, self.bot)
            print(f"DEBUG: Created update object: {update}")
            
            # Process the update
            print("DEBUG: Processing update...")
            await self.application.process_update(update)
            print("DEBUG: Update processed successfully")
            
            return {"status": "ok"}
            
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            raise HTTPException(status_code=500, detail=f"Update processing failed: {str(e)}")
    
    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Send message to user"""
        try:
            # Используем parse_mode из kwargs или по умолчанию None
            parse_mode = kwargs.pop('parse_mode', None)
            
            if self.application:
                return await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    **kwargs
                )
            async with self.bot:
                return await self.bot.send_message(  # type: ignore
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    **kwargs
                )
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            # Log the exact error type and message for better debugging
            logger.error(f"Error type: {type(e).__name__}, Error args: {e.args}")
            raise
    
    async def edit_message(self, chat_id: int, message_id: int, text: str, **kwargs):
        """Edit existing message"""
        try:
            # Используем parse_mode из kwargs или по умолчанию None
            parse_mode = kwargs.pop('parse_mode', None)
            
            if self.application:
                return await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode=parse_mode,
                    **kwargs
                )
            async with self.bot:
                return await self.bot.edit_message_text(  # type: ignore
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="HTML",
                    **kwargs
                )
        except Exception as e:
            logger.error(f"Failed to edit message {message_id} in {chat_id}: {e}")
            # Log the exact error type and message for better debugging
            logger.error(f"Error type: {type(e).__name__}, Error args: {e.args}")
            raise

    async def delete_message(self, chat_id: int, message_id: int):
        """Delete message if possible"""
        try:
            if self.application:
                await self.application.bot.delete_message(chat_id=chat_id, message_id=message_id)
                return
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Failed to delete message {message_id} in {chat_id}: {e}")
            logger.error(f"Error type: {type(e).__name__}, Error args: {e.args}")
            raise
    
    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None, show_alert: bool = False):
        """Answer callback query"""
        try:
            if self.application:
                await self.application.bot.answer_callback_query(
                    callback_query_id=callback_query_id,
                    text=text,
                    show_alert=show_alert
                )
            else:
                async with self.bot:
                    await self.bot.answer_callback_query(  # type: ignore
                        callback_query_id=callback_query_id,
                        text=text,
                        show_alert=show_alert
                    )
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}")

    async def start_polling(self):
        """Start polling for updates (alternative to webhook)"""
        try:
            if not self.application:
                raise ValueError("Application not initialized")
            
            # Start the application
            await self.application.start()
            
            # Start polling
            await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
            logger.info("Telegram bot started polling for updates")
            
        except Exception as e:
            logger.error(f"Failed to start polling: {e}")
            raise

    async def stop_polling(self):
        """Stop polling for updates"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                logger.info("Telegram bot stopped polling")
            
        except Exception as e:
            logger.error(f"Failed to stop polling: {e}")
            raise

# Global bot instance
# Lazy initialization to ensure environment variables are loaded
_telegram_bot_instance = None

def get_telegram_bot():
    """Get or create telegram bot instance with lazy initialization"""
    global _telegram_bot_instance
    if _telegram_bot_instance is None:
        _telegram_bot_instance = TelegramBot()
    return _telegram_bot_instance

# For backward compatibility
telegram_bot = get_telegram_bot()
