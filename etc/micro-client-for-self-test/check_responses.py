#!/usr/bin/env python3
"""
Check recent responses from the bot
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import logging

# Add parent directory to path to import micro_client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from micro_client import TelegramMicroClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to check recent bot responses"""
    logger.info("🔍 Checking recent bot responses")
    logger.info("=" * 40)
    
    # Create client
    client = TelegramMicroClient()
    
    try:
        # Initialize the client
        success = await client.initialize()
        if not success:
            logger.error("Failed to initialize client")
            return False
        
        # Get bot info
        bot_entity = await client.get_bot_info()
        if not bot_entity:
            logger.error("Failed to get bot info")
            return False
        
        bot_id = bot_entity.id
        logger.info(f"Connected to bot: {bot_entity.username} (ID: {bot_id})")
        
        # Check recent messages from the bot
        logger.info("📥 Checking recent messages from bot...")
        recent_messages = []
        
        async for message in client.client.get_chat_history("@taiger_pro_bot", limit=50):
            if message.from_user and message.from_user.id == bot_id:
                # Check if message is recent (within last 30 minutes)
                message_age = (datetime.now().timestamp() - message.date.timestamp()) / 60
                if message_age <= 30:
                    recent_messages.append(message)
                    logger.info(f"Recent message ({message_age:.1f} min ago): {message.text[:100]}...")
                else:
                    break  # Stop if we've gone beyond recent messages
        
        logger.info(f"Found {len(recent_messages)} recent messages from bot")
        
        if recent_messages:
            print(f"\n📥 Found {len(recent_messages)} recent messages from bot:")
            for i, message in enumerate(recent_messages):
                age = (datetime.now().timestamp() - message.date.timestamp()) / 60
                print(f"{i+1}. [{age:.1f} min ago] {message.text[:150]}...")
        else:
            print("\n📭 No recent messages from bot found")
            
        return True
            
    except Exception as e:
        logger.error(f"Error checking bot responses: {e}")
        print(f"\n❌ Error checking bot responses: {e}")
        return False
    finally:
        # Clean up client
        try:
            await client.close()
        except Exception as e:
            logger.warning(f"Error closing client: {e}")

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("✅ Bot response check completed!")
            sys.exit(0)
        else:
            logger.info("❌ Bot response check failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)