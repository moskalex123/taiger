#!/usr/bin/env python3
"""
Simple Model Test for Telegram Bot
This script sends a test message to the bot and collects responses from all models.
The bot is already configured to respond with answers from different models with their names and processing times.
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

class SimpleModelTester:
    def __init__(self):
        """Initialize the simple model tester."""
        # Test message
        self.test_message = "Привет! Это тестовое сообщение для проверки работы всех моделей ИИ."
        
        # Results storage
        self.responses = []
        self.test_timestamp = datetime.now().isoformat()
    
    async def run_test(self):
        """Run the simple test by sending one message and collecting all responses."""
        logger.info("🚀 Starting simple model test")
        logger.info(f"Test message: '{self.test_message}'")
        
        # Initialize client
        client = TelegramMicroClient()
        
        if not await client.initialize():
            logger.error("Failed to initialize client")
            return False
        
        try:
            # Send test message to bot
            logger.info("📤 Sending test message to bot...")
            await client.send_test_message(self.test_message)
            
            # Wait for responses (longer wait time since multiple models will respond)
            logger.info("⏳ Waiting for bot responses (up to 120 seconds)...")
            responses = await client.wait_for_responses(timeout=120)
            
            if responses:
                logger.info(f"✅ Received {len(responses)} responses from bot")
                self.responses = responses
                return True
            else:
                logger.warning("⚠️ No responses received from bot")
                return False
                
        except Exception as e:
            logger.error(f"Error during test: {e}")
            return False
        finally:
            await client.close()
    
    def parse_response_info(self, response_text):
        """Parse model name and processing time from response text."""
        # Look for pattern like: [Model: mistralai/mistral-7b-instruct:free (ID: 19) | Processing time: 2.34s]
        import re
        
        # Pattern to match model info
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
    
    def generate_report(self):
        """Generate a report from the collected responses."""
        logger.info("📝 Generating test report...")
        
        if not self.responses:
            logger.warning("No responses to generate report from")
            return None
        
        # Create reports directory if it doesn't exist
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Parse response information
        parsed_responses = []
        for i, response in enumerate(self.responses):
            response_text = response.text if response.text else ""
            info = self.parse_response_info(response_text)
            
            parsed_response = {
                "response_number": i + 1,
                "model_name": info["model_name"],
                "model_id": info["model_id"],
                "processing_time": info["processing_time"],
                "response_text": response_text,
                "response_length": len(response_text),
                "has_media": bool(response.photo or response.video or response.document),
                "timestamp": response.date.isoformat() if response.date else None
            }
            parsed_responses.append(parsed_response)
        
        # Generate JSON report
        json_report_path = os.path.join(reports_dir, f"simple_model_test_{timestamp}.json")
        report_data = {
            "test_timestamp": self.test_timestamp,
            "report_timestamp": datetime.now().isoformat(),
            "test_message": self.test_message,
            "total_responses": len(parsed_responses),
            "responses": parsed_responses
        }
        
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # Generate CSV report
        csv_report_path = os.path.join(reports_dir, f"simple_model_test_{timestamp}.csv")
        with open(csv_report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Response #', 'Model Name', 'Model ID', 'Processing Time (s)', 'Response Length', 'Has Media', 'Timestamp'])
            
            for response in parsed_responses:
                writer.writerow([
                    response["response_number"],
                    response["model_name"],
                    response["model_id"],
                    response["processing_time"],
                    response["response_length"],
                    response["has_media"],
                    response["timestamp"]
                ])
        
        # Generate summary report
        summary_report_path = os.path.join(reports_dir, f"simple_model_test_summary_{timestamp}.txt")
        with open(summary_report_path, 'w', encoding='utf-8') as f:
            f.write("SIMPLE MODEL TESTING REPORT\n")
            f.write("=" * 40 + "\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Test Message: {self.test_message}\n")
            f.write(f"Total Responses: {len(parsed_responses)}\n")
            f.write("=" * 40 + "\n\n")
            
            # Group by model
            model_stats = {}
            for response in parsed_responses:
                model_name = response["model_name"]
                if model_name not in model_stats:
                    model_stats[model_name] = {
                        "count": 0,
                        "total_time": 0,
                        "responses": []
                    }
                model_stats[model_name]["count"] += 1
                model_stats[model_name]["total_time"] += response["processing_time"]
                model_stats[model_name]["responses"].append(response)
            
            # Write model statistics
            for model_name, stats in model_stats.items():
                avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
                f.write(f"Model: {model_name}\n")
                f.write(f"  Responses: {stats['count']}\n")
                f.write(f"  Avg Processing Time: {avg_time:.2f}s\n")
                f.write("\n")
            
            # Write individual responses
            f.write("INDIVIDUAL RESPONSES\n")
            f.write("=" * 20 + "\n")
            for response in parsed_responses:
                f.write(f"Response #{response['response_number']}:\n")
                f.write(f"  Model: {response['model_name']} (ID: {response['model_id']})\n")
                f.write(f"  Processing Time: {response['processing_time']:.2f}s\n")
                f.write(f"  Response Length: {response['response_length']} characters\n")
                f.write(f"  Has Media: {response['has_media']}\n")
                f.write(f"  Preview: {response['response_text'][:100]}...\n")
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
    """Main function to run simple model testing."""
    logger.info("🚀 Simple Model Tester for Telegram Bot")
    logger.info("=" * 50)
    
    # Check if TEST_MODE is enabled in the main project
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    if not test_mode:
        logger.warning("⚠️  TEST_MODE is not enabled in the main project.")
        logger.warning("   Please set TEST_MODE=true in the main .env file and restart the backend.")
        logger.warning("   Without TEST_MODE, you will only get responses from the default model.")
    
    # Create tester
    tester = SimpleModelTester()
    
    try:
        # Run test
        success = await tester.run_test()
        
        if success:
            # Generate report
            reports = tester.generate_report()
            logger.info("✅ Simple model testing completed successfully!")
        else:
            logger.warning("⚠️ Model testing did not receive any responses")
            return False
            
    except Exception as e:
        logger.error(f"Error during model testing: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("✅ Simple model testing completed!")
            sys.exit(0)
        else:
            logger.info("❌ Simple model testing failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
        sys.exit(1)