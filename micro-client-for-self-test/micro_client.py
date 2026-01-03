#!/usr/bin/env python3
"""
Console Micro-Client for Testing Telegram Bot Promo Mode
This client uses user session 7 to test the @taiger_pro_bot in promo mode.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import tempfile
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import S3SessionManager
sys.path.append('..')
from s3_session_manager import S3SessionManager

class TelegramMicroClient:
    def __init__(self):
        """Initialize the Telegram micro client."""
        self.api_id = int(os.getenv('TELEGRAM_API_ID', '21118124'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH', '491b6a7118ccbf3738bebc959ea14e4d')
        self.session_name = os.getenv('SESSION_NAME', 'micro_client')
        self.bot_username = os.getenv('BOT_USERNAME', '@taiger_pro_bot')
        self.test_user_id = int(os.getenv('TEST_USER_ID', '7'))
        
        if not self.api_id or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env file")
        
        # Initialize S3 session manager
        self.s3_manager = S3SessionManager()
        
        # Set up session directory and path (following worker approach with PID)
        process_id = os.getpid()
        self.session_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
        self.session_path = os.path.join(self.session_dir, f"{self.test_user_id}_{process_id}_micro_client.session")
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Store the last sent message ID and send time
        self.last_message_id = None
        self.last_message_time = None
        
        # Create Pyrogram Client with the session file
        self.client = Client(
            name=os.path.splitext(os.path.basename(self.session_path))[0],
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=self.session_dir
        )
        self.connected = False
    
    def _load_session_from_s3(self):
        """Load session from S3 or create new one."""
        logger.info(f"📦 Checking for session in S3 for user {self.test_user_id}...")
        
        # Check if session exists in S3
        if self.s3_manager.session_exists(self.test_user_id):
            logger.info("📥 Session found in S3, downloading...")
            if self.s3_manager.download_session(self.test_user_id, self.session_path):
                logger.info("✅ Session successfully downloaded from S3")
                return True
            else:
                logger.error("❌ Failed to download session from S3")
                return False
        else:
            logger.warning(f"⚠️ Session not found in S3 for user {self.test_user_id}")
            return False
    
    async def initialize(self):
        """Initialize the Telegram client"""
        try:
            logger.info("Initializing Telegram micro-client...")
            
            # Download session from S3
            if not self._load_session_from_s3():
                logger.error("Failed to load session from S3")
                return False
            
            # Check if session file exists
            if not os.path.exists(self.session_path):
                logger.error(f"Session file not found: {self.session_path}")
                return False
            
            await self.client.start()
            
            # Verify authorization
            me = await self.client.get_me()
            if not me:
                logger.error("Session 7 is not authorized. Please check the session file.")
                return False
                
            logger.info(f"✅ Telegram micro-client initialized successfully as {me.first_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            return False
    
    async def get_bot_info(self):
        """Get information about the bot"""
        try:
            bot_entity = await self.client.get_chat(self.bot_username)
            logger.info(f"Bot info: {bot_entity}")
            return bot_entity
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return None
    
    async def send_test_message(self, text: str):
        """Send a test message to the bot"""
        try:
            logger.info(f"Sending test message: '{text}'")
            message = await self.client.send_message(self.bot_username, text)
            self.last_message_id = message.id
            self.last_message_time = datetime.now()
            logger.info(f"✅ Test message sent successfully with ID: {self.last_message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            return False

    def get_buttons(self, message: Message):
        """Get all buttons from a message"""
        buttons = {'inline': [], 'reply': []}
        if message.reply_markup:
            if isinstance(message.reply_markup, InlineKeyboardMarkup):
                for row in message.reply_markup.inline_keyboard:
                    for button in row:
                        buttons['inline'].append({
                            'text': button.text,
                            'callback_data': button.callback_data
                        })
            elif isinstance(message.reply_markup, ReplyKeyboardMarkup):
                for row in message.reply_markup.keyboard:
                    for button in row:
                        buttons['reply'].append({
                            'text': button.text
                        })
        return buttons

    async def press_button(self, message: Message, button_index: int, button_type: str = 'inline'):
        """Simulate pressing a button on the message"""
        try:
            buttons = self.get_buttons(message)
            if button_type == 'inline' and button_index < len(buttons['inline']):
                button = buttons['inline'][button_index]
                callback_data = button['callback_data']
                logger.info(f"Simulating press of inline button '{button['text']}' with callback_data: {callback_data}")
                # Send as "CALLBACK:<callback_data>" to trigger bot's callback handler
                await self.send_test_message(f"CALLBACK:{callback_data}")
                return True
            elif button_type == 'reply' and button_index < len(buttons['reply']):
                button = buttons['reply'][button_index]
                text = button['text']
                logger.info(f"Simulating press of reply button '{text}'")
                await self.send_test_message(text)
                return True
            else:
                logger.error(f"Button index {button_index} out of range for {button_type} buttons")
                return False
        except Exception as e:
            logger.error(f"Failed to press button: {e}")
            return False
    
    async def wait_for_responses(self, timeout: int = 120):
        """Wait for bot responses to the last sent message"""
        if not self.last_message_id or not self.last_message_time:
            logger.warning("No message ID or time to wait for responses to")
            return []

        logger.info(f"Waiting for bot responses sent after message ID {self.last_message_id} (timeout: {timeout}s)...")
        responses = []
        start_time = asyncio.get_event_loop().time()

        try:
            # Get the bot entity
            bot_entity = await self.client.get_chat(self.bot_username)
            bot_id = bot_entity.id

            # Look for messages from the bot that were sent after our message
            async for message in self.client.get_chat_history(self.bot_username, limit=100):
                # Check if this is a response from the bot
                if message.from_user and message.from_user.id == bot_id:
                    # Check if the message was sent after our test message
                    if message.date > self.last_message_time:
                        responses.append(message)
                        logger.info(f"Found bot response: {message.text[:100]}...")

                        # Check if message has media
                        if message.photo:
                            logger.info("Response contains photo")
                        elif message.video or message.document:
                            logger.info("Response contains document/video")

                        # Check if message has buttons
                        buttons = self.get_buttons(message)
                        if buttons['inline'] or buttons['reply']:
                            logger.info(f"Response has buttons: {len(buttons['inline'])} inline, {len(buttons['reply'])} reply")

                    # Stop if we've found enough recent responses (increased from 5 to 20 for test mode)
                    if len(responses) >= 20:
                        break

                # Check timeout
                if (asyncio.get_event_loop().time() - start_time) > timeout:
                    logger.warning("Timeout reached while waiting for responses")
                    break

        except Exception as e:
            logger.error(f"Error while waiting for responses: {e}")

        return responses
    
    async def test_promo_mode(self):
        """Test the promo mode functionality"""
        logger.info("🚀 Starting promo mode test...")
        
        # Test 1: Send a simple text message
        test_text = "Привет! Это тестовое сообщение для проверки промо-режима бота."
        await self.send_test_message(test_text)
        
        # Wait for responses (increased from 5 to 15 seconds for multiple model responses)
        await asyncio.sleep(15)
        responses = await self.wait_for_responses()
        
        if responses:
            logger.info(f"✅ Received {len(responses)} bot responses")
            for i, response in enumerate(responses):
                logger.info(f"Response {i+1}: {response.text[:200]}...")
        else:
            logger.warning("⚠️ No bot responses received")
        
        return responses
    
    async def test_with_media(self):
        """Test with media messages"""
        logger.info("📸 Testing with media...")
        
        # For now, just test text with media description
        test_text = "Посмотрите на этот красивый закат! 🌅 Фото сделано вечером на берегу моря."
        await self.send_test_message(test_text)
        
        await asyncio.sleep(15)
        responses = await self.wait_for_responses()
        
        return responses
    
    async def interactive_mode(self):
        """Interactive mode for manual testing"""
        logger.info("🎯 Entering interactive mode...")
        logger.info("Type your messages and press Enter. Type 'quit' to exit.")
        logger.info("To press buttons, use 'press <response_index> <button_index> [inline|reply]'")

        while True:
            try:
                user_input = input("\n💬 Your message: ").strip()

                if user_input.lower() == 'quit':
                    logger.info("Exiting interactive mode...")
                    break

                if not user_input:
                    continue

                # Check if it's a button press command
                if user_input.startswith('press '):
                    parts = user_input.split()
                    if len(parts) >= 3:
                        try:
                            response_index = int(parts[1]) - 1  # Convert to 0-based
                            button_index = int(parts[2])
                            button_type = parts[3] if len(parts) > 3 else 'inline'

                            # Get recent responses
                            responses = await self.wait_for_responses(timeout=1)  # Short timeout to get cached
                            if 0 <= response_index < len(responses):
                                message = responses[response_index]
                                success = await self.press_button(message, button_index, button_type)
                                if success:
                                    logger.info("✅ Button pressed successfully")
                                    # Wait for response to button press
                                    await asyncio.sleep(3)
                                    new_responses = await self.wait_for_responses(timeout=10)
                                    if new_responses:
                                        logger.info(f"📨 New responses after button press ({len(new_responses)}):")
                                        for i, resp in enumerate(new_responses):
                                            logger.info(f"  {i+1}. {resp.text[:150]}...")
                                            buttons = self.get_buttons(resp)
                                            if buttons['inline'] or buttons['reply']:
                                                logger.info(f"    Has buttons: {len(buttons['inline'])} inline, {len(buttons['reply'])} reply")
                                else:
                                    logger.error("❌ Failed to press button")
                            else:
                                logger.error(f"Invalid response index: {response_index + 1}")
                        except ValueError as e:
                            logger.error(f"Invalid button press command: {e}")
                    else:
                        logger.error("Invalid button press command format")
                    continue

                # Send message to bot
                await self.send_test_message(user_input)

                # Wait for response
                await asyncio.sleep(3)
                responses = await self.wait_for_responses(timeout=10)

                if responses:
                    logger.info(f"📨 Bot responses ({len(responses)}):")
                    for i, response in enumerate(responses):
                        logger.info(f"  {i+1}. {response.text[:150]}...")
                        buttons = self.get_buttons(response)
                        if buttons['inline'] or buttons['reply']:
                            logger.info(f"    Has buttons: {len(buttons['inline'])} inline, {len(buttons['reply'])} reply")
                            # List buttons
                            for j, btn in enumerate(buttons['inline']):
                                logger.info(f"      Inline {j}: {btn['text']}")
                            for j, btn in enumerate(buttons['reply']):
                                logger.info(f"      Reply {j}: {btn['text']}")
                else:
                    logger.warning("⚠️ No response received")

            except KeyboardInterrupt:
                logger.info("\n🛑 Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
    
    async def close(self):
        """Close the client connection"""
        if self.client and self.client.is_connected:
            try:
                await self.client.stop()
                logger.info("Client stopped")
            except Exception as e:
                logger.warning(f"Error stopping client: {e}")
        else:
            logger.info("Client was not connected")

async def main():
    """Main function"""
    logger.info("🚀 Telegram Micro-Client for Promo Mode Testing")
    logger.info("=" * 50)
    
    # Create client
    client = TelegramMicroClient()
    
    # Initialize
    if not await client.initialize():
        logger.error("Failed to initialize client")
        return
    
    try:
        # Get bot info
        bot_info = await client.get_bot_info()
        if bot_info:
            logger.info(f"Connected to bot: {bot_info.title} (@{bot_info.username})")
        
        # Test promo mode
        logger.info("\n" + "="*50)
        logger.info("TESTING PROMO MODE")
        logger.info("="*50)
        
        # Run automated tests
        responses = await client.test_promo_mode()
        
        if responses:
            logger.info("\n✅ Promo mode test completed successfully!")
            logger.info(f"Received {len(responses)} responses from bot")
        else:
            logger.warning("\n⚠️ No responses received from bot")
        
        # Test with media
        logger.info("\n" + "="*50)
        logger.info("TESTING WITH MEDIA DESCRIPTIONS")
        logger.info("="*50)
        
        media_responses = await client.test_with_media()
        
        # Interactive mode
        logger.info("\n" + "="*50)
        logger.info("INTERACTIVE MODE")
        logger.info("="*50)
        
        await client.interactive_mode()
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
    finally:
        await client.close()
        logger.info("\n✅ Testing completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")