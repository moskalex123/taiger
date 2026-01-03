#!/usr/bin/env python3
"""
Test script to verify localization of @taiger_pro_bot using micro-client
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

class LocalizationTestClient:
    def __init__(self):
        """Initialize the localization test client."""
        self.api_id = int(os.getenv('TELEGRAM_API_ID', '21118124'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH', '491b6a7118ccbf3738bebc959ea14e4d')
        self.session_name = os.getenv('SESSION_NAME', 'micro_client')
        self.bot_username = os.getenv('BOT_USERNAME', '@taiger_pro_bot')
        self.test_user_id = int(os.getenv('TEST_USER_ID', '7'))

        if not self.api_id or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env file")

        # Initialize S3 session manager
        self.s3_manager = S3SessionManager()

        # Set up session directory and path
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
            # Try to copy from local file if S3 fails
            local_session = f"/opt/taiger/micro-client-for-self-test/{self.test_user_id}_micro_client.session"
            if os.path.exists(local_session):
                import shutil
                shutil.copy2(local_session, self.session_path)
                logger.info(f"📋 Copied local session from {local_session}")
                return True
            return False

    async def initialize(self):
        """Initialize the Telegram client"""
        try:
            logger.info("Initializing Telegram localization test client...")

            # Download session from S3 or local
            if not self._load_session_from_s3():
                logger.error("Failed to load session from S3 or local")
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

            logger.info(f"✅ Telegram localization test client initialized successfully as {me.first_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            return False

    async def send_command(self, command: str):
        """Send a command to the bot"""
        try:
            logger.info(f"Sending command: '{command}'")
            message = await self.client.send_message(self.bot_username, command)
            self.last_message_id = message.id
            self.last_message_time = datetime.now()
            logger.info(f"✅ Command sent successfully with ID: {self.last_message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False

    async def wait_for_responses(self, timeout: int = 30):
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
            async for message in self.client.get_chat_history(self.bot_username, limit=50):
                # Check if this is a response from the bot
                if message.from_user and message.from_user.id == bot_id:
                    # Check if the message was sent after our test message
                    if message.date > self.last_message_time:
                        responses.append(message)
                        logger.info(f"Found bot response: {message.text[:100] if message.text else 'No text'}...")

                    # Stop if we've found enough responses
                    if len(responses) >= 10:
                        break

                # Check timeout
                if (asyncio.get_event_loop().time() - start_time) > timeout:
                    logger.warning("Timeout reached while waiting for responses")
                    break

        except Exception as e:
            logger.error(f"Error while waiting for responses: {e}")

        return responses

    async def test_localization(self):
        """Test localization by checking if bot responds in appropriate language"""
        logger.info("🌍 Starting localization test...")
        
        # First, send /start command to ensure user is registered
        await self.send_command("/start")
        await asyncio.sleep(5)
        start_responses = await self.wait_for_responses()
        
        logger.info("Start command responses:")
        for i, response in enumerate(start_responses):
            text = response.text if response.text else "No text"
            logger.info(f"  {i+1}. {text[:200]}...")
        
        # Test profile command to see if language-specific responses work
        await self.send_command("👤 Профиль")  # Russian profile button text
        await asyncio.sleep(3)
        profile_responses = await self.wait_for_responses()
        
        logger.info("Profile command responses:")
        for i, response in enumerate(profile_responses):
            text = response.text if response.text else "No text"
            logger.info(f"  {i+1}. {text[:200]}...")
        
        # Test language toggle if available
        # We need to find the callback query for language toggle
        # For this, we'll need to interact with inline keyboards
        # which is more complex, so let's try sending a message that might trigger localized response
        
        # Test with a simple message
        await self.send_command("Привет! Это тест локализации.")
        await asyncio.sleep(5)
        hello_responses = await self.wait_for_responses()
        
        logger.info("Hello command responses:")
        for i, response in enumerate(hello_responses):
            text = response.text if response.text else "No text"
            logger.info(f"  {i+1}. {text[:200]}...")
        
        # Combine all responses for analysis
        all_responses = start_responses + profile_responses + hello_responses
        return all_responses

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
    """Main function for localization testing"""
    logger.info("🌍 Telegram Bot Localization Test")
    logger.info("=" * 50)

    # Create client
    client = LocalizationTestClient()

    # Initialize
    if not await client.initialize():
        logger.error("Failed to initialize client")
        return

    try:
        # Get bot info
        bot_info = await client.get_bot_info()
        if bot_info:
            logger.info(f"Connected to bot: {bot_info.title} (@{bot_info.username})")

        # Run localization test
        logger.info("\n" + "="*50)
        logger.info("RUNNING LOCALIZATION TEST")
        logger.info("="*50)

        responses = await client.test_localization()

        logger.info(f"\n✅ Localization test completed!")
        logger.info(f"Total responses received: {len(responses)}")

        # Analyze responses for localization
        logger.info("\n" + "="*50)
        logger.info("ANALYSIS")
        logger.info("="*50)
        
        localized_responses = 0
        for i, response in enumerate(responses):
            text = response.text if response.text else ""
            if text:
                # Check for Cyrillic characters (Russian) or other localization indicators
                has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in text)
                has_localized_elements = 'Профиль' in text or 'Баланс' in text or 'Воркер' in text or 'ID:' in text
                
                if has_cyrillic or has_localized_elements:
                    logger.info(f"  Response {i+1} appears to be localized: {text[:100]}...")
                    localized_responses += 1
                else:
                    logger.info(f"  Response {i+1}: {text[:100]}...")

        logger.info(f"\nLocalized responses: {localized_responses}/{len(responses)}")

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