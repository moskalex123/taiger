#!/usr/bin/env python3
"""
Patient test script to send one message and collect responses
"""

import os
import sys
import json
import asyncio
import re
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

# Single test message
TEST_MESSAGE = "Завтра в нашем магазине скидка 20% на все."

def parse_response_info(response_text):
    """Parse model name and processing time from response text."""
    # Look for pattern like: [Model: mistralai/mistral-7b-instruct:free (ID: 19) | Processing time: 2.34s]
    pattern = r'\[Model: ([^(]+) \(ID: (\d+)\) \| Processing time: ([\d.]+)s\]'
    match = re.search(pattern, response_text)
    
    if match:
        model_name = match.group(1).strip()
        model_id = int(match.group(2))
        processing_time = float(match.group(3))
        return {
            "model_name": model_name,
            "model_id": model_id,
            "processing_time": processing_time
        }
    else:
        # If no pattern found, return unknown
        return {
            "model_name": "Unknown",
            "model_id": -1,
            "processing_time": -1
        }

async def collect_responses(client, timeout=300):
    """Patiently collect responses from the bot"""
    logger.info("⏳ Patiently collecting bot responses...")
    responses = []
    start_time = asyncio.get_event_loop().time()
    
    # Wait a bit for processing to start
    await asyncio.sleep(30)
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            # Get recent responses
            recent_responses = await client.wait_for_responses(timeout=30)
            
            # Add new responses to our collection
            for response in recent_responses:
                response_text = response.text if response.text else ""
                # Check if this is a new response we haven't seen before
                is_new = True
                for existing in responses:
                    if existing.text == response_text and existing.date == response.date:
                        is_new = False
                        break
                
                if is_new:
                    responses.append(response)
                    info = parse_response_info(response_text)
                    logger.info(f"Found response from model {info['model_id']}: {response_text[:100]}...")
            
            # If we have some responses, check if we should continue waiting
            if responses:
                logger.info(f"Collected {len(responses)} responses so far...")
                
            # Wait before checking again
            await asyncio.sleep(15)
            
        except Exception as e:
            logger.error(f"Error collecting responses: {e}")
            break
    
    return responses

async def main():
    """Main function to run a patient test"""
    logger.info("🚀 Patient Test for Telegram Bot")
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
        
        # Patiently collect responses
        responses = await collect_responses(client, timeout=300)
        
        if responses:
            logger.info(f"✅ Received {len(responses)} responses from bot")
            
            # Parse and save responses
            parsed_responses = []
            for response in responses:
                response_text = response.text if response.text else ""
                info = parse_response_info(response_text)
                
                parsed_response = {
                    "model_name": info["model_name"],
                    "model_id": info["model_id"],
                    "processing_time": info["processing_time"],
                    "response_text": response_text
                }
                parsed_responses.append(parsed_response)
            
            # Save to JSON file
            output_data = {
                "test_run_timestamp": datetime.now().isoformat(),
                "test_message": TEST_MESSAGE,
                "total_responses": len(parsed_responses),
                "responses": parsed_responses
            }
            
            with open("messages.json", "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info("✅ Responses saved to messages.json")
            print(f"\n✅ Received {len(responses)} responses from bot")
            print("📄 Responses saved to messages.json")
            
            # Show summary
            model_ids = [r["model_id"] for r in parsed_responses]
            print(f"🤖 Models that responded: {sorted(set(model_ids))}")
            return True
        else:
            logger.warning("⚠️ No responses received from bot")
            print("\n⚠️ No responses received from bot")
            return False
            
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
            logger.info("✅ Patient test completed!")
            sys.exit(0)
        else:
            logger.info("❌ Patient test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)