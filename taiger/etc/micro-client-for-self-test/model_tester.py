#!/usr/bin/env python3
"""
Model Tester for Telegram Bot
This script tests different AI models through the Telegram bot and generates a report.
"""

import os
import sys
import asyncio
import logging
import json
import csv
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to path to import from telegram_bot
sys.path.append('..')

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from micro_client import TelegramMicroClient

class ModelTester:
    def __init__(self):
        """Initialize the model tester."""
        self.test_messages = [
            "Привет! Это тестовое сообщение для проверки работы ИИ модели.",
            "Напиши краткое описание преимуществ облачных технологий для бизнеса.",
            "Создай привлекательное описание для товара: умная кофеварка с голосовым управлением.",
            "Объясни простыми словами, что такое искусственный интеллект.",
            "Напиши короткий пост для социальной сети о важности экологии."
        ]
        
        # Test models configuration (should match what's in TEST_MODELS)
        self.test_models = [
            {"id": 17, "name": "Model 17"},
            {"id": 18, "name": "Model 18"},
            {"id": 19, "name": "Model 19"},
            {"id": 20, "name": "Model 20"},
            {"id": 21, "name": "Model 21"},
            {"id": 22, "name": "Model 22"},
            {"id": 23, "name": "Model 23"},
            {"id": 24, "name": "Model 24"},
            {"id": 25, "name": "Model 25"}
        ]
        
        self.results = []
    
    async def run_model_test(self, model_id, model_name):
        """Test a specific model with all test messages."""
        logger.info(f"🚀 Testing model {model_id} ({model_name})")
        
        # Initialize client
        client = TelegramMicroClient()
        
        if not await client.initialize():
            logger.error(f"Failed to initialize client for model {model_id}")
            return None
        
        model_results = {
            "model_id": model_id,
            "model_name": model_name,
            "timestamp": datetime.now().isoformat(),
            "messages": []
        }
        
        try:
            # Test each message
            for i, message in enumerate(self.test_messages):
                logger.info(f"  Testing message {i+1}/{len(self.test_messages)}: '{message[:50]}...'")
                
                # Send message to bot
                await client.send_test_message(message)
                
                # Wait for responses
                await asyncio.sleep(10)  # Increased wait time for model processing
                responses = await client.wait_for_responses(timeout=30)
                
                message_result = {
                    "message_id": i+1,
                    "input_text": message,
                    "responses": [],
                    "response_count": len(responses)
                }
                
                # Process responses
                for j, response in enumerate(responses):
                    response_data = {
                        "response_id": j+1,
                        "text": response.text if response.text else "",
                        "has_media": bool(response.photo or response.video or response.document),
                        "timestamp": response.date.isoformat() if response.date else None
                    }
                    message_result["responses"].append(response_data)
                
                model_results["messages"].append(message_result)
                
                # Wait between messages to avoid rate limiting
                if i < len(self.test_messages) - 1:
                    await asyncio.sleep(15)
            
            logger.info(f"✅ Completed testing model {model_id} ({model_name})")
            return model_results
            
        except Exception as e:
            logger.error(f"Error testing model {model_id}: {e}")
            return None
        finally:
            await client.close()
    
    async def run_all_tests(self):
        """Run tests for all models."""
        logger.info("🚀 Starting model testing for all models")
        
        for model in self.test_models:
            model_id = model["id"]
            model_name = model["name"]
            
            # Test the model
            result = await self.run_model_test(model_id, model_name)
            if result:
                self.results.append(result)
            
            # Wait between models to avoid rate limiting
            if model != self.test_models[-1]:
                logger.info("⏳ Waiting between models...")
                await asyncio.sleep(30)
        
        logger.info("✅ Completed testing all models")
    
    def generate_report(self):
        """Generate a comprehensive report of the test results."""
        logger.info("📝 Generating test report...")
        
        # Create reports directory if it doesn't exist
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate JSON report
        json_report_path = os.path.join(reports_dir, f"model_test_report_{timestamp}.json")
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # Generate CSV report
        csv_report_path = os.path.join(reports_dir, f"model_test_report_{timestamp}.csv")
        with open(csv_report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Model ID', 'Model Name', 'Message ID', 'Input Text', 'Response Count', 'Response Text', 'Has Media', 'Response Time'])
            
            for model_result in self.results:
                model_id = model_result["model_id"]
                model_name = model_result["model_name"]
                
                for message_result in model_result["messages"]:
                    message_id = message_result["message_id"]
                    input_text = message_result["input_text"]
                    response_count = message_result["response_count"]
                    
                    if message_result["responses"]:
                        for response in message_result["responses"]:
                            response_text = response["text"][:100] + "..." if len(response["text"]) > 100 else response["text"]
                            has_media = response["has_media"]
                            response_time = response["timestamp"]
                            writer.writerow([model_id, model_name, message_id, input_text, response_count, response_text, has_media, response_time])
                    else:
                        writer.writerow([model_id, model_name, message_id, input_text, response_count, "No response", False, ""])
        
        # Generate summary report
        summary_report_path = os.path.join(reports_dir, f"model_test_summary_{timestamp}.txt")
        with open(summary_report_path, 'w', encoding='utf-8') as f:
            f.write("MODEL TESTING REPORT SUMMARY\n")
            f.write("=" * 50 + "\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Models Tested: {len(self.results)}\n")
            f.write(f"Messages Per Model: {len(self.test_messages)}\n")
            f.write("=" * 50 + "\n\n")
            
            for model_result in self.results:
                model_id = model_result["model_id"]
                model_name = model_result["model_name"]
                total_responses = sum([msg["response_count"] for msg in model_result["messages"]])
                
                f.write(f"Model {model_id} ({model_name}):\n")
                f.write(f"  Total Responses: {total_responses}\n")
                f.write(f"  Success Rate: {total_responses}/{len(self.test_messages)} ({100*total_responses/len(self.test_messages):.1f}%)\n")
                
                # Calculate average response time
                response_times = []
                for message_result in model_result["messages"]:
                    for response in message_result["responses"]:
                        if response["timestamp"]:
                            response_times.append(response["timestamp"])
                
                if response_times:
                    f.write(f"  Responses Received: {len(response_times)}\n")
                f.write("\n")
        
        logger.info(f"✅ Reports generated:")
        logger.info(f"  JSON: {json_report_path}")
        logger.info(f"  CSV: {csv_report_path}")
        logger.info(f"  Summary: {summary_report_path}")
        
        return {
            "json": json_report_path,
            "csv": csv_report_path,
            "summary": summary_report_path
        }

async def main():
    """Main function to run model testing."""
    logger.info("🚀 Model Tester for Telegram Bot")
    logger.info("=" * 50)
    
    # Check if TEST_MODE is enabled in the main project
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    if not test_mode:
        logger.warning("⚠️  TEST_MODE is not enabled in the main project. Testing may not work as expected.")
        logger.warning("   Please set TEST_MODE=true in the main .env file and restart the backend.")
    
    # Create tester
    tester = ModelTester()
    
    try:
        # Run all tests
        await tester.run_all_tests()
        
        # Generate report
        if tester.results:
            reports = tester.generate_report()
            logger.info("✅ Model testing completed successfully!")
            logger.info(f"Generated {len(tester.results)} model test results")
        else:
            logger.warning("⚠️ No test results to report")
            
    except Exception as e:
        logger.error(f"Error during model testing: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("✅ Model testing completed!")
            sys.exit(0)
        else:
            logger.info("❌ Model testing failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)