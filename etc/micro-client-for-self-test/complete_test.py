#!/usr/bin/env python3
"""
Complete test script to process all methodology texts and collect all responses
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

# Test texts from the methodology
TEST_TEXTS = [
    "Завтра в нашем магазине скидка 20% на все.",
    "Ребята, какой ноутбук посоветуете для учебы? Бюджет до 50к.",
    "В общем, такая ситуация, пришел я сегодня на работу, а там мой начальник опять с утра не в духе, начал всем раздавать указания, которые сами себе противоречат, я пытался ему вежливо сказать, что так нельзя, но он как начал орать, в общем, еле сдержался, чтобы не нагрубить в ответ, думаю, может уже пора искать новую работу, хотя зарплата тут нормальная, но нервы дороже.",
    "Чтобы настроить программу, вам нужно сначала открыть ее, потом найти в левом верхнем углу меню, там будет много пунктов, но вам нужен именно \"Настройки\", кликните на него, откроется окно, не пугайтесь, там много всего, но ищите вкладку \"Подключения\", а потом уже там будет поле для ввода вашего ключа API.",
    "Митап по маркетингу в субботу, 15 числа. Будет несколько спикеров. Начало в 12:00. Адрес: ул. Пушкина, 10.",
    "Мы делаем сайты под ключ. Качественно и недорого. Используем современные технологии.",
    "ВАЩЕ КЛАССНАЯ АКЦИЯ У НАС ВСЕ ТОВАРЫ СО СКИДКОЙ 50 ПРОЦЕНТОВ ТОРОПИТЕСЬ ПРЕДЛОЖЕНИЕ ОГРАНИЧЕНО",
    "Настоящим уведомляем о проведении технических работ, в результате которых возможно временное отсутствие доступа к сервису. Приносим извинения за доставленные неудобства.",
    "Что вы думаете о новой функции?",
    "Сегодня видел, как ворона каталась на скейте. Было смешно."
]

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

async def wait_for_responses_with_patience(client, timeout=120):
    """Wait for responses with patience, checking multiple times"""
    logger.info(f"⏳ Waiting for bot responses (up to {timeout} seconds)...")
    all_responses = []
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            # Get recent responses
            recent_responses = await client.wait_for_responses(timeout=30)
            
            # Add new responses to our collection
            for response in recent_responses:
                response_text = response.text if response.text else ""
                # Check if this is a new response we haven't seen before
                is_new = True
                for existing in all_responses:
                    if existing.text == response_text and existing.date == response.date:
                        is_new = False
                        break
                
                if is_new:
                    all_responses.append(response)
                    info = parse_response_info(response_text)
                    logger.info(f"Found response from model {info['model_id']}: {response_text[:100]}...")
            
            # If we have some responses, log progress
            if all_responses:
                logger.info(f"Collected {len(all_responses)} responses so far...")
            
            # Wait before checking again
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"Error collecting responses: {e}")
            break
    
    return all_responses

async def process_single_text(text, text_index):
    """Process a single text and collect responses"""
    logger.info(f"Processing text {text_index + 1}/{len(TEST_TEXTS)}: '{text[:50]}...'")
    
    # Create a new client for each text to avoid session issues
    client = TelegramMicroClient()
    
    try:
        # Initialize the client
        success = await client.initialize()
        if not success:
            logger.error(f"Failed to initialize client for text {text_index + 1}")
            return []
        
        # Send the test message
        await client.send_test_message(text)
        
        # Wait for responses with patience
        responses = await wait_for_responses_with_patience(client, timeout=120)
        
        if responses:
            logger.info(f"✅ Received {len(responses)} responses for text {text_index + 1}")
            
            # Parse responses
            parsed_responses = []
            for response in responses:
                response_text = response.text if response.text else ""
                info = parse_response_info(response_text)
                
                parsed_response = {
                    "test_text_index": text_index,
                    "test_text": text,
                    "model_name": info["model_name"],
                    "model_id": info["model_id"],
                    "processing_time": info["processing_time"],
                    "response_text": response_text
                }
                parsed_responses.append(parsed_response)
            
            return parsed_responses
        else:
            logger.warning(f"⚠️ No responses received for text {text_index + 1}")
            return []
            
    except Exception as e:
        logger.error(f"Error processing text {text_index + 1}: {e}")
        return []
    finally:
        # Clean up client
        try:
            await client.close()
        except Exception as e:
            logger.warning(f"Error closing client: {e}")

async def main():
    """Main function to process all texts"""
    logger.info("🚀 Complete Test for Telegram Bot - Processing All Methodology Texts")
    logger.info("=" * 70)
    
    all_responses = []
    
    # Process each text one by one
    for i, text in enumerate(TEST_TEXTS):
        responses = await process_single_text(text, i)
        all_responses.extend(responses)
        
        # Wait between texts to avoid rate limiting
        if i < len(TEST_TEXTS) - 1:  # Don't wait after the last text
            logger.info("⏳ Waiting 60 seconds before next text...")
            await asyncio.sleep(60)
    
    # Save all responses to JSON file
    if all_responses:
        output_data = {
            "test_run_timestamp": datetime.now().isoformat(),
            "total_texts_processed": len(TEST_TEXTS),
            "total_responses": len(all_responses),
            "responses": all_responses
        }
        
        with open("messages.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info("✅ All responses saved to messages.json")
        print(f"\n✅ Processed {len(TEST_TEXTS)} texts")
        print(f"📄 Collected {len(all_responses)} responses")
        print("💾 Responses saved to messages.json")
        
        # Show summary
        model_ids = sorted(set([r["model_id"] for r in all_responses if r["model_id"] != -1]))
        print(f"🤖 Models that responded: {model_ids}")
        
        # Show responses per text
        print("\n📊 Responses per text:")
        for i in range(len(TEST_TEXTS)):
            count = len([r for r in all_responses if r["test_text_index"] == i])
            print(f"  Text {i+1}: {count} responses")
        
        return True
    else:
        logger.warning("⚠️ No responses collected from any texts")
        print("\n⚠️ No responses collected from any texts")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("✅ Complete test completed!")
            sys.exit(0)
        else:
            logger.info("❌ Complete test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)