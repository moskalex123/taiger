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
from datetime import datetime
import logging

# Add parent directory to path to import micro_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from micro_client import TelegramMicroClient

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

class ComprehensiveModelTester:
    def __init__(self):
        self.client = None
        self.results = {
            "test_run_timestamp": datetime.now().isoformat(),
            "test_texts": TEST_TEXTS,
            "model_responses": [],
            "summary": {}
        }
    
    async def initialize_client(self):
        """Initialize the Telegram micro-client"""
        try:
            self.client = TelegramMicroClient()
            success = await self.client.initialize()
            if success:
                logger.info("Micro-client initialized successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to initialize micro-client: {e}")
            return False
    
    def enrich_response_with_metadata(self, response, test_text):
        """Enrich a response with metadata and parse model information."""
        import re
        
        # Extract text from response
        response_text = response.text if response.text else ""
        
        # Parse model info from response text
        # Look for pattern like: [Model: mistralai/mistral-7b-instruct:free (ID: 19) | Processing time: 2.34s]
        pattern = r'\[Model: ([^(]+) \(ID: (\d+)\) \| Processing time: ([\d.]+)s\]'
        match = re.search(pattern, response_text)
        
        if match:
            model_name = match.group(1).strip()
            model_id = int(match.group(2))
            processing_time = float(match.group(3))
        else:
            # If no pattern found, mark as unknown/error
            model_name = "Unknown"
            model_id = -1
            processing_time = -1
        
        # Create enriched response
        enriched_response = {
            "test_text_id": test_text["id"],
            "category": test_text["category"],
            "subcategory": test_text["subcategory"],
            "model_name": model_name,
            "model_id": model_id,
            "processing_time": processing_time,
            "response_text": response_text,
            "response_length": len(response_text),
            "has_media": bool(response.photo or response.video or response.document),
            "timestamp": response.date.isoformat() if response.date else None,
            "message_id": response.id
        }
        
        return enriched_response
    
    async def run_test_for_text(self, test_text):
        """Run test for a single text and collect all model responses"""
        logger.info(f"Running test for text ID {test_text['id']}: {test_text['subcategory']}")
        
        try:
            # Send the test message
            await self.client.send_test_message(test_text['text'])
            logger.info(f"Test message sent for text ID {test_text['id']}")
            
            # Wait for responses (increased timeout for multiple models)
            # Add extra delay to ensure all models respond
            await asyncio.sleep(5)  # Give time for initial responses
            responses = await self.client.wait_for_responses(timeout=180)
            logger.info(f"Received {len(responses)} responses for text ID {test_text['id']}")
            
            # Add metadata to responses
            enriched_responses = []
            for response in responses:
                enriched_response = self.enrich_response_with_metadata(response, test_text)
                enriched_responses.append(enriched_response)
            
            return enriched_responses
        except Exception as e:
            logger.error(f"Error running test for text ID {test_text['id']}: {e}")
            return []
    
    async def run_all_tests(self):
        """Run tests for all texts and collect results"""
        if not await self.initialize_client():
            logger.error("Failed to initialize client, cannot run tests")
            return False
        
        try:
            all_responses = []
            
            for test_text in TEST_TEXTS:
                logger.info(f"Processing test text {test_text['id']}/{len(TEST_TEXTS)}")
                
                # Run test for this text
                responses = await self.run_test_for_text(test_text)
                
                # Responses are already enriched, just extend the list
                all_responses.extend(responses)
                
                all_responses.extend(responses)
                
                # Small delay between tests to avoid overwhelming the bot
                await asyncio.sleep(2)
            
            # Store all responses
            self.results['model_responses'] = all_responses
            
            # Calculate summary statistics
            await self.calculate_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Error running all tests: {e}")
            return False
        finally:
            # Clean up client
            if self.client:
                await self.client.stop()
    
    async def calculate_summary(self):
        """Calculate summary statistics for the test run"""
        summary = {
            "total_test_texts": len(TEST_TEXTS),
            "total_responses": len(self.results['model_responses']),
            "models": {},
            "average_processing_times": {},
            "responses_per_model": {}
        }
        
        # Group responses by model
        model_responses = {}
        for response in self.results['model_responses']:
            model_name = response.get('model_name', 'Unknown')
            if model_name not in model_responses:
                model_responses[model_name] = []
            model_responses[model_name].append(response)
        
        # Calculate statistics for each model
        for model_name, responses in model_responses.items():
            summary['responses_per_model'][model_name] = len(responses)
            
            # Calculate average processing time
            valid_times = [r.get('processing_time', 0) for r in responses if r.get('processing_time', -1) > 0]
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                summary['average_processing_times'][model_name] = round(avg_time, 2)
            else:
                summary['average_processing_times'][model_name] = -1  # Indicates errors
        
        summary['models'] = list(model_responses.keys())
        self.results['summary'] = summary
    
    def save_results(self, filename=None):
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_model_test_results_{timestamp}.json"
        
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", filename)
        
        # Ensure reports directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Add completion timestamp
        self.results['completion_timestamp'] = datetime.now().isoformat()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to {filepath}")
        return filepath

async def main():
    """Main function to run comprehensive model testing"""
    logger.info("Starting comprehensive model testing")
    
    tester = ComprehensiveModelTester()
    
    try:
        success = await tester.run_all_tests()
        
        if success:
            filepath = tester.save_results()
            logger.info(f"Comprehensive testing completed successfully. Results saved to {filepath}")
            print(f"\n✅ Comprehensive testing completed!")
            print(f"📄 Results saved to: {filepath}")
            print(f"📊 Total responses collected: {tester.results['summary']['total_responses']}")
            print(f"🤖 Models tested: {len(tester.results['summary']['models'])}")
        else:
            logger.error("Comprehensive testing failed")
            print("\n❌ Comprehensive testing failed. Check logs for details.")
            
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        print(f"\n❌ Error during testing: {e}")

if __name__ == "__main__":
    asyncio.run(main())