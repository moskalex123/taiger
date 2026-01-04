#!/usr/bin/env python3
"""
Console Micro-Client for Testing Telegram Bot Localization with user 16
This client uses user session 16 to test the @taiger_pro_bot localization.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
import tempfile
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.types import Message

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import S3SessionManager
sys.path.append('/opt/taiger')
from s3_session_manager import S3SessionManager

class TelegramMicroClient:
    def __init__(self):
        """Initialize the Telegram micro client."""
        self.api_id = int(os.getenv('TELEGRAM_API_ID', '21118124'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH', '491b6a7118ccbf3738bebc959ea14e4d')
        self.session_name = os.getenv('SESSION_NAME', 'micro_client')
        self.bot_username = os.getenv('BOT_USERNAME', '@taiger_pro_bot')
        self.test_user_id = int(os.getenv('TEST_USER_ID', '16'))  # Updated to user 16

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
                logger.error("Session 16 is not authorized. Please check the session file.")
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
                        logger.info(f"Found bot response: {message.text[:100] if message.text else 'No text'}...")

                        # Check if message has media
                        if message.photo:
                            logger.info("Response contains photo")
                        elif message.video or message.document:
                            logger.info("Response contains document/video")

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

    async def test_localization(self):
        """Test the localization functionality"""
        logger.info("🌍 Starting localization test...")

        # Test 1: Send /start command to trigger initial welcome message
        logger.info("\n--- Testing /start command ---")
        await self.send_test_message("/start")
        
        # Wait for responses
        await asyncio.sleep(10)
        start_responses = await self.wait_for_responses()

        if start_responses:
            logger.info(f"✅ Received {len(start_responses)} responses to /start")
            for i, response in enumerate(start_responses):
                text = response.text if response.text else "No text"
                logger.info(f"Response {i+1}: {text[:200]}...")
        else:
            logger.warning("⚠️ No responses received to /start")

        # Test 2: Test profile button (Russian text) to see if localized UI works
        logger.info("\n--- Testing profile command ---")
        await self.send_test_message("👤 Профиль")  # Russian profile button text
        await asyncio.sleep(5)
        profile_responses = await self.wait_for_responses()

        if profile_responses:
            logger.info(f"✅ Received {len(profile_responses)} responses to profile command")
            for i, response in enumerate(profile_responses):
                text = response.text if response.text else "No text"
                logger.info(f"Response {i+1}: {text[:200]}...")
        else:
            logger.warning("⚠️ No responses received to profile command")

        # Test 3: Test language toggle via inline keyboard (if possible)
        logger.info("\n--- Testing language toggle functionality ---")
        # For this we would need to interact with inline keyboards, which is more complex
        # For now, let's just check if language-specific responses are in place

        # Test 4: Send a message in Russian to see if bot responds appropriately
        logger.info("\n--- Testing Russian language response ---")
        await self.send_test_message("Привет! Это тест локализации. Как дела?")
        await asyncio.sleep(10)
        russian_responses = await self.wait_for_responses()

        if russian_responses:
            logger.info(f"✅ Received {len(russian_responses)} responses to Russian message")
            for i, response in enumerate(russian_responses):
                text = response.text if response.text else "No text"
                logger.info(f"Response {i+1}: {text[:200]}...")
        else:
            logger.warning("⚠️ No responses received to Russian message")

        # Combine all responses for analysis
        all_responses = start_responses + profile_responses + russian_responses
        return all_responses

    async def interactive_mode(self):
        """Interactive mode for manual testing"""
        logger.info("🎯 Entering interactive mode...")
        logger.info("Type your messages and press Enter. Type 'quit' to exit.")

        while True:
            try:
                user_input = input("\n💬 Your message: ").strip()

                if user_input.lower() == 'quit':
                    logger.info("Exiting interactive mode...")
                    break

                if not user_input:
                    continue

                # Send message to bot
                await self.send_test_message(user_input)

                # Wait for response
                await asyncio.sleep(3)
                responses = await self.wait_for_responses(timeout=10)

                if responses:
                    logger.info(f"📨 Bot responses ({len(responses)}):")
                    for i, response in enumerate(responses):
                        text = response.text if response.text else "No text"
                        logger.info(f"  {i+1}. {text[:150]}...")
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
    logger.info("🚀 Telegram Micro-Client for Localization Testing (User 16)")
    logger.info("=" * 60)

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

        # Run localization tests
        logger.info("\n" + "="*60)
        logger.info("RUNNING LOCALIZATION TESTS")
        logger.info("="*60)

        responses = await client.test_localization()

        # Analyze localization results
        logger.info("\n" + "="*60)
        logger.info("ANALYSIS RESULTS")
        logger.info("="*60)

        localized_responses = 0
        total_responses = len(responses)
        
        for i, response in enumerate(responses):
            text = response.text if response.text else ""
            if text:
                # Check for localization indicators
                has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in text)
                has_localized_elements = any([
                    'Профиль' in text,
                    'Баланс' in text,
                    'Воркер' in text,
                    'ID:' in text,
                    'Статус воркера' in text,
                    'Пользователь не найден' in text
                ])
                
                if has_cyrillic or has_localized_elements:
                    logger.info(f"  Response {i+1} appears to be localized: {text[:100]}...")
                    localized_responses += 1
                else:
                    logger.info(f"  Response {i+1}: {text[:100]}...")

        logger.info(f"\n📊 Localization Results:")
        logger.info(f"  Total responses: {total_responses}")
        logger.info(f"  Localized responses: {localized_responses}")
        logger.info(f"  Localization rate: {localized_responses/total_responses*100 if total_responses > 0 else 0:.1f}%")

        if total_responses > 0:
            if localized_responses > 0:
                logger.info("✅ Localization functionality appears to be working!")
            else:
                logger.info("⚠️ No localized responses detected - localization may not be working properly")

        # Interactive mode
        logger.info("\n" + "="*60)
        logger.info("INTERACTIVE MODE")
        logger.info("="*60)

        await client.interactive_mode()

    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()
        logger.info("\n✅ Testing completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")