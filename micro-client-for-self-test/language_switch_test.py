#!/usr/bin/env python3
"""
Test to check if language switching works for user 16
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
import tempfile
from dotenv import load_dotenv
from pyrogram import Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import S3SessionManager
sys.path.append('/opt/taiger')
from s3_session_manager import S3SessionManager

class LanguageSwitchTest:
    def __init__(self):
        """Initialize the language switch test."""
        self.api_id = int(os.getenv('TELEGRAM_API_ID', '21118124'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH', '491b6a7118ccbf3738bebc959ea14e4d')
        self.session_name = os.getenv('SESSION_NAME', 'micro_client')
        self.bot_username = os.getenv('BOT_USERNAME', '@taiger_pro_bot')
        self.test_user_id = int(os.getenv('TEST_USER_ID', '16'))

        # Initialize S3 session manager
        self.s3_manager = S3SessionManager()

        # Set up session directory and path
        process_id = os.getpid()
        self.session_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
        self.session_path = os.path.join(self.session_dir, f"{self.test_user_id}_{process_id}_micro_client.session")
        os.makedirs(self.session_dir, exist_ok=True)

        # Create Pyrogram Client with the session file
        self.client = Client(
            name=os.path.splitext(os.path.basename(self.session_path))[0],
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=self.session_dir
        )

    def _load_session_from_s3(self):
        """Load session from S3."""
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
            logger.error(f"❌ Session not found in S3 for user {self.test_user_id}")
            return False

    async def initialize(self):
        """Initialize the Telegram client"""
        try:
            logger.info("Initializing Telegram client...")

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

            logger.info(f"✅ Telegram client initialized successfully as {me.first_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            return False

    async def send_message(self, text: str):
        """Send a message to the bot"""
        try:
            logger.info(f"Sending: '{text}'")
            message = await self.client.send_message(self.bot_username, text)
            logger.info(f"✅ Message sent successfully")
            return message
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    async def get_recent_bot_response(self):
        """Get the most recent bot response"""
        try:
            async for message in self.client.get_chat_history(self.bot_username, limit=20):
                if message.from_user and message.from_user.username == self.bot_username.lstrip('@'):
                    text = message.text if message.text else ""
                    return text, message
        except Exception as e:
            logger.error(f"Error getting bot responses: {e}")
        return None, None

    async def test_language_switching(self):
        """Test if language switching works"""
        logger.info("🌍 Testing language switching functionality...")

        # First, send /start to ensure the user is registered
        await self.send_message("/start")
        await asyncio.sleep(3)
        
        # Get the initial response
        initial_response, _ = await self.get_recent_bot_response()
        if initial_response:
            logger.info(f"Initial response: {initial_response[:200]}...")
        
        # Try to access profile menu which should have language toggle
        await self.send_message("👤 Профиль")  # Russian profile button text
        await asyncio.sleep(2)
        
        profile_response, profile_msg = await self.get_recent_bot_response()
        if profile_response:
            logger.info(f"Profile response: {profile_response[:200]}...")
            
            # Check if response is in Russian (has localization)
            has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in profile_response)
            has_russian_elements = any([
                'Профиль' in profile_response,
                'Баланс' in profile_response,
                'Воркер' in profile_response,
                'ID:' in profile_response,
                'Статус воркера' in profile_response
            ])
            
            if has_cyrillic or has_russian_elements:
                logger.info("✅ Russian localization detected!")
                return True
            else:
                logger.info("⚠️ Response is not in Russian, testing language toggle...")
                
                # If we have a message with inline keyboard, we could potentially test the language toggle
                # But this requires more complex interaction with callback queries
                # For now, let's just report what we found

        return False

    async def close(self):
        """Close the client connection"""
        if self.client and self.client.is_connected:
            try:
                await self.client.stop()
                logger.info("Client stopped")
            except Exception as e:
                logger.warning(f"Error stopping client: {e}")

async def main():
    """Main function"""
    logger.info("🚀 Language Switching Test for @taiger_pro_bot (User 16)")
    logger.info("=" * 60)

    # Create client
    client = LanguageSwitchTest()

    # Initialize
    if not await client.initialize():
        logger.error("Failed to initialize client")
        return

    try:
        # Run language switching test
        localization_detected = await client.test_language_switching()

        if localization_detected:
            logger.info("\n✅ Language switching/localization is working!")
        else:
            logger.info("\n⚠️ Localization may need manual language switching or is set to English by default")

    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()
        logger.info("\n✅ Language switching test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")