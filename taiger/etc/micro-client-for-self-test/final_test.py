#!/usr/bin/env python3
"""
Final test script to process all methodology texts and collect responses
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

async def process_single_text(client, text, text_index):
    """Process a single text and collect responses"""
    logger.info(f"Processing text {text_index + 1}/{len(TEST_TEXTS)}: '{text[:50]}...'")
    
    try:
        # Send the test message
        await client.send_test_message(text)
        
        # Wait for responses with a reasonable timeout
        await asyncio.sleep(45)  # Give time for processing
        responses = await client.wait_for_responses(timeout=75)
        
        if responses:
            logger.info(f"✅ Received {len(responses)} responses for text {text_index + 1}")
            
            # Parse responses
            parsed_responses = []
            for response in responses:
                response_text = response.text if response.text else ""
                info = parse_response_info(response_text)
                
                parsed_response = {
                    "test_text_index": text_index,
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

async def main():
    """Main function to process all texts"""
    logger.info("🚀 Final Test for Telegram Bot - Processing All Methodology Texts")
    logger.info("=" * 70)
    
    all_responses = []
    
    # Process each text one by one
    for i, text in enumerate(TEST_TEXTS):
        # Create a new client for each text to avoid session issues
        client = TelegramMicroClient()
        
        try:
            # Initialize the client
            success = await client.initialize()
            if not success:
                logger.error(f"Failed to initialize client for text {i + 1}")
                continue
            
            # Process the text
            responses = await process_single_text(client, text, i)
            all_responses.extend(responses)
            
        except Exception as e:
            logger.error(f"Error with client for text {i + 1}: {e}")
        finally:
            # Clean up client
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"Error closing client: {e}")
            
            # Wait between texts to avoid rate limiting
            if i < len(TEST_TEXTS) - 1:  # Don't wait after the last text
                logger.info("⏳ Waiting 30 seconds before next text...")
                await asyncio.sleep(30)
    
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
        model_ids = sorted(set([r["model_id"] for r in all_responses]))
        print(f"🤖 Models that responded: {model_ids}")
        return True
    else:
        logger.warning("⚠️ No responses collected from any texts")
        print("\n⚠️ No responses collected from any texts")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("✅ Final test completed!")
            sys.exit(0)
        else:
            logger.info("❌ Final test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)