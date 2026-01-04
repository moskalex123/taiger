#!/usr/bin/env python3
"""
Basic test script to send one message and see if we get any response
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

# Simple test message
TEST_MESSAGE = "Тестовое сообщение для проверки бота."

async def main():
    """Main function to run a basic test"""
    logger.info("🚀 Basic Test for Telegram Bot")
    logger.info("=" * 40)
    
    # Create client
    client = TelegramMicroClient()
    
    try:
        # Initialize the client
        success = await client.initialize()
        if not success:
            logger.error("Failed to initialize client")
            return False
        
        # Send the test message
        logger.info(f"📤 Sending test message: '{TEST_MESSAGE}'")
        await client.send_test_message(TEST_MESSAGE)
        
        # Wait a bit and then check for responses
        logger.info("⏳ Waiting 60 seconds for any bot responses...")
        await asyncio.sleep(60)
        
        # Try to get responses
        responses = await client.wait_for_responses(timeout=30)
        
        logger.info(f"Found {len(responses)} responses")
        
        if responses:
            print(f"\n✅ Received {len(responses)} responses from bot:")
            for i, response in enumerate(responses):
                age = (datetime.now().timestamp() - response.date.timestamp()) / 60
                text_preview = response.text[:150] if response.text else "(no text)"
                print(f"{i+1}. [{age:.1f} min ago] {text_preview}...")
        else:
            print("\n📭 No responses received from bot")
            
        return True
            
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        print(f"\n❌ Error during testing: {e}")
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
            logger.info("✅ Basic test completed!")
            sys.exit(0)
        else:
            logger.info("❌ Basic test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)