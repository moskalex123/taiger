#!/usr/bin/env python3
"""
Comprehensive Model Testing Script
Runs all test texts from the methodology through the Telegram bot
and collects responses in a single JSON file with average response times.
"""

import os
import sys
import json
import time
import asyncio
import csv
import re
from datetime import datetime
from dotenv import load_dotenv
import logging

# Add parent directory to path to import micro_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from micro_client import TelegramMicroClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test texts extracted from the methodology
TEST_TEXTS = [
    {
        "id": 1,
        "category": "Короткие и простые посты (Базовый уровень)",
        "subcategory": "Новость/Объявление",
        "text": "Завтра в нашем магазине скидка 20% на все.",
        "what_to_test": [
            "Умение создать заголовок",
            "Добавление эмодзи для привлечения внимания",
            "Форматирование в более читаемый вид",
            "Добавление призыва к действию (CTA)"
        ]
    },
    {
        "id": 2,
        "category": "Короткие и простые посты (Базовый уровень)",
        "subcategory": "Вопрос",
        "text": "Ребята, какой ноутбук посоветуете для учебы? Бюджет до 50к.",
        "what_to_test": [
            "Структурирование вопроса (например, список критериев)",
            "Добавление хештегов для охвата (#учеба #ноутбук #совет)",
            "Умение перефразировать вопрос, чтобы он звучал более привлекательно"
        ]
    },
    {
        "id": 3,
        "category": "Длинные и \"стеновые\" посты (Проверка работы с информационным шумом)",
        "subcategory": "Эмоциональный рассказ",
        "text": "В общем, такая ситуация, пришел я сегодня на работу, а там мой начальник опять с утра не в духе, начал всем раздавать указания, которые сами себе противоречат, я пытался ему вежливо сказать, что так нельзя, но он как начал орать, в общем, еле сдержался, чтобы не нагрубить в ответ, думаю, может уже пора искать новую работу, хотя зарплата тут нормальная, но нервы дороже.",
        "what_to_test": [
            "Суммаризация: Умение выделить суть (\"Сотрудник столкнулся с неадекватным поведением начальника и рассматривает смену работы\")",
            "Структурирование: Превращение потока сознания в список тезисов или краткий абзац",
            "Тон: Сможет ли ИИ сохранить эмоциональную окраску, но убрать ненужную драму"
        ]
    },
    {
        "id": 4,
        "category": "Длинные и \"стеновые\" посты (Проверка работы с информационным шумом)",
        "subcategory": "Инструкция с \"водой\"",
        "text": "Чтобы настроить программу, вам нужно сначала открыть ее, потом найти в левом верхнем углу меню, там будет много пунктов, но вам нужен именно \"Настройки\", кликните на него, откроется окно, не пугайтесь, там много всего, но ищите вкладку \"Подключения\", а потом уже там будет поле для ввода вашего ключа API.",
        "what_to_test": [
            "Удаление лишних слов и создание четкой, пошаговой инструкции",
            "Добавление форматирования (например, списка или жирного шрифта для ключевых пунктов)",
            "Улучшение читабельности"
        ]
    },
    {
        "id": 5,
        "category": "Специфические типы контента (Проверка креативности и шаблонов)",
        "subcategory": "Анонс мероприятия",
        "text": "Митап по маркетингу в субботу, 15 числа. Будет несколько спикеров. Начало в 12:00. Адрес: ул. Пушкина, 10.",
        "what_to_test": [
            "Создание интригующего заголовка (\"Раскрываем секреты маркетинга: приходите на митап!\")",
            "Структурирование информации (Дата, Время, Место, Спикеры, Что будет)",
            "Генерация убедительного CTA (\"Зарегистрируйтесь по ссылке...\", \"Количество мест ограничено!\")"
        ]
    },
    {
        "id": 6,
        "category": "Специфические типы контента (Проверка креативности и шаблонов)",
        "subcategory": "Описание продукта/услуги",
        "text": "Мы делаем сайты под ключ. Качественно и недорого. Используем современные технологии.",
        "what_to_test": [
            "Умение расписать выгоды, а не фичи. Не \"используем современные технологии\", а \"ваш сайт будет быстрым и безопасным\"",
            "Создание убедительного USP (Уникальное торговое предложение)",
            "Добавление структуры и призыва к действию (\"?? Напишите нам для бесплатной консультации!\")"
        ]
    },
    {
        "id": 7,
        "category": "Посты с ошибками и странной стилистикой",
        "subcategory": "С ошибками и CAPS LOCK",
        "text": "ВАЩЕ КЛАССНАЯ АКЦИЯ У НАС ВСЕ ТОВАРЫ СО СКИДКОЙ 50 ПРОЦЕНТОВ ТОРОПИТЕСЬ ПРЕДЛОЖЕНИЕ ОГРАНИЧЕНО",
        "what_to_test": [
            "Исправление регистра и пунктуации",
            "Сохранение энергичности сообщения, но в более цивилизованной форме",
            "Добавление структуры"
        ]
    },
    {
        "id": 8,
        "category": "Посты с ошибками и странной стилистикой",
        "subcategory": "Слишком формальный или канцелярит",
        "text": "Настоящим уведомляем о проведении технических работ, в результате которых возможно временное отсутствие доступа к сервису. Приносим извинения за доставленные неудобства.",
        "what_to_test": [
            "Упрощение языка и перевод на человеческий",
            "Сохранение сути, но с более дружелюбным тоном (\"Друзья, завтра утром будут техработы. Сервис может быть недоступен около часа. Спасибо за понимание!\")"
        ]
    },
    {
        "id": 9,
        "category": "Креативные и вовлекающие посты",
        "subcategory": "Скучный опрос",
        "text": "Что вы думаете о новой функции?",
        "what_to_test": [
            "Умение создать интригующий вопрос",
            "Добавление вариантов ответа с эмодзи",
            "Формулировку, которая провоцирует дискуссию"
        ]
    },
    {
        "id": 10,
        "category": "Креативные и вовлекающие посты",
        "subcategory": "Заготовка для \"вирального\" поста",
        "text": "Сегодня видел, как ворона каталась на скейте. Было смешно.",
        "what_to_test": [
            "Креативность: Может ли ИИ развить эту мысль в забавный мини-рассказ?",
            "Создание харизмы: Добавление шуток, риторических вопросов (\"Вы видели что-нибудь подобное?\")",
            "Генерация хештегов: #ПриродаУдивляет #ВоронаСкейтер #ЖизньПрекрасна"
        ]
    }
]

class ComprehensiveMethodologyTester:
    def __init__(self):
        self.all_responses = []
        self.test_timestamp = datetime.now().isoformat()
    
    def parse_response_info(self, response_text):
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
    
    async def wait_for_all_model_responses(self, client, timeout=180):
        """Wait for responses from all models, specifically waiting for model 33"""
        logger.info("⏳ Waiting for bot responses from all models (including model 33)...")
        responses = []
        start_time = asyncio.get_event_loop().time()
        model_33_received = False
        last_check_time = start_time
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Check for new responses every 10 seconds
            current_time = asyncio.get_event_loop().time()
            if (current_time - last_check_time) >= 10:
                # Get recent responses
                recent_responses = await client.wait_for_responses(timeout=30)
                
                # Add new responses to our collection
                for response in recent_responses:
                    response_text = response.text if response.text else ""
                    info = self.parse_response_info(response_text)
                    
                    # Check if this is a new response we haven't seen before
                    is_new_response = True
                    for existing_response in responses:
                        if (existing_response.text == response_text and 
                            existing_response.date == response.date):
                            is_new_response = False
                            break
                    
                    if is_new_response:
                        responses.append(response)
                        logger.info(f"Found bot response from model {info['model_id']}: {response_text[:100]}...")
                        
                        # Check if we've received a response from model 33
                        if info["model_id"] == 33:
                            model_33_received = True
                            logger.info("✅ Received response from model 33")
                
                last_check_time = current_time
            
            # If we've received a response from model 33, we can move on
            if model_33_received:
                break
            
            # Wait a bit before checking again
            await asyncio.sleep(5)
        
        if not model_33_received:
            logger.warning("⚠️ Did not receive response from model 33 within timeout")
        
        logger.info(f"✅ Collected {len(responses)} responses from bot")
        return responses
    
    async def run_single_test(self, test_text):
        """Run a single test with a fresh client instance"""
        logger.info(f"Running test for text ID {test_text['id']}: {test_text['subcategory']}")
        
        # Create a new client instance for each test to avoid database locking
        client = TelegramMicroClient()
        
        try:
            # Initialize the client
            success = await client.initialize()
            if not success:
                logger.error(f"Failed to initialize client for test {test_text['id']}")
                return False
            
            # Send the test message
            logger.info(f"📤 Sending test message: '{test_text['text']}'")
            await client.send_test_message(test_text['text'])
            
            # Wait for responses from all models, specifically waiting for model 33
            responses = await self.wait_for_all_model_responses(client, timeout=180)
            
            if responses:
                logger.info(f"✅ Received {len(responses)} responses from bot")
                # Store responses with test text metadata
                for response in responses:
                    response_text = response.text if response.text else ""
                    info = self.parse_response_info(response_text)
                    
                    enriched_response = {
                        "test_text_id": test_text["id"],
                        "model_name": info["model_name"],
                        "model_id": info["model_id"],
                        "processing_time": info["processing_time"],
                        "response_text": response_text
                    }
                    self.all_responses.append(enriched_response)
                return True
            else:
                logger.warning("⚠️ No responses received from bot")
                return False
                
        except Exception as e:
            logger.error(f"Error during test {test_text['id']}: {e}")
            return False
        finally:
            # Clean up client
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"Error closing client: {e}")
            # Small delay between tests to avoid rate limiting
            await asyncio.sleep(20)
    
    async def run_all_tests(self):
        """Run tests for all texts and collect results"""
        logger.info(f"🚀 Starting comprehensive testing of {len(TEST_TEXTS)} test texts")
        
        successful_tests = 0
        failed_tests = 0
        
        for i, test_text in enumerate(TEST_TEXTS):
            logger.info(f"Processing test {i+1}/{len(TEST_TEXTS)}")
            try:
                success = await self.run_single_test(test_text)
                if success:
                    successful_tests += 1
                else:
                    failed_tests += 1
            except Exception as e:
                logger.error(f"Failed to run test {test_text['id']}: {e}")
                failed_tests += 1
        
        logger.info(f"✅ Tests completed. Successful: {successful_tests}, Failed: {failed_tests}")
        return successful_tests > 0
    
    def save_responses_to_json(self):
        """Save all responses to a single JSON file"""
        logger.info("📝 Saving responses to messages.json...")
        
        # Create reports directory if it doesn't exist
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Save to messages.json
        json_report_path = os.path.join(reports_dir, "messages.json")
        report_data = {
            "test_run_timestamp": self.test_timestamp,
            "total_responses": len(self.all_responses),
            "responses": self.all_responses
        }
        
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Responses saved to: {json_report_path}")
        return json_report_path

async def main():
    """Main function to run comprehensive methodology testing."""
    logger.info("🚀 Comprehensive Methodology Tester for Telegram Bot")
    logger.info("=" * 60)
    
    # Check if TEST_MODE is enabled in the main project
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    if not test_mode:
        logger.warning("⚠️  TEST_MODE is not enabled in the main project.")
        logger.warning("   Please set TEST_MODE=true in the main .env file and restart the backend.")
        logger.warning("   Without TEST_MODE, you will only get responses from the default model.")
    
    # Create tester
    tester = ComprehensiveMethodologyTester()
    
    try:
        # Run all tests
        success = await tester.run_all_tests()
        
        if success:
            # Save all responses to a single JSON file
            json_path = tester.save_responses_to_json()
            if json_path:
                logger.info("✅ Comprehensive methodology testing completed successfully!")
                print(f"\n✅ Comprehensive testing completed!")
                print(f"📄 Responses saved to: {json_path}")
            else:
                logger.warning("⚠️ Testing completed but responses were not saved")
                print("\n⚠️ Testing completed but responses were not saved")
        else:
            logger.error("Comprehensive testing failed")
            print("\n❌ Comprehensive testing failed. Check logs for details.")
            
    except Exception as e:
        logger.error(f"Error during comprehensive testing: {e}")
        print(f"\n❌ Error during testing: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("✅ Comprehensive methodology testing completed!")
            sys.exit(0)
        else:
            logger.info("❌ Comprehensive methodology testing failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)