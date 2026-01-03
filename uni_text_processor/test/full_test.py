#!/usr/bin/env python3
"""
Full test script for Universal AI Text Processor
Tests all models without strict timeout restrictions
Outputs results to both console and JSON file
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

from uni_text_processor.universal_processor import UniversalAIProcessor
from uni_text_processor.db_utils import DatabaseUtils
import aiohttp


async def main():
    """Main test function without strict timeouts"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Initialize processor first
    processor = UniversalAIProcessor(logger)
    
    # Read test content files
    try:
        # Read system content
        system_content_path = Path(__file__).parent / "system_content_to_test_AI.txt"
        if system_content_path.exists():
            with open(system_content_path, 'r', encoding='utf-8') as f:
                system_content = f.read().strip()
            # Use default if file is empty
            if not system_content:
                system_content = processor.get_default_system_prompt()
                logger.info("System content file is empty, using default from processor")
        else:
            system_content = processor.get_default_system_prompt()
            logger.info("System content file not found, using default from processor")
        
        # Read user content
        user_content_path = Path(__file__).parent / "user_content_to_test_AI.txt"
        if user_content_path.exists():
            with open(user_content_path, 'r', encoding='utf-8') as f:
                user_content = f.read().strip()
        else:
            user_content = "Hello! This is a test message for AI processing. Please make it more engaging and add some emojis."
            logger.info(f"User content file not found, using default: {user_content}")
            
    except Exception as e:
        logger.error(f"Error reading test content files: {e}")
        return
    
    # Initialize components
    db_utils = DatabaseUtils(logger)
    
    # Fetch all models from database
    logger.info("Fetching models from database...")
    models = await db_utils.get_all_models()
    
    if not models:
        logger.error("No models found in database")
        return
    
    logger.info(f"Found {len(models)} models to test")
    
    # Create shared HTTP session for better performance
    # Use longer timeout for comprehensive testing
    timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes per request
    http_session = aiohttp.ClientSession(timeout=timeout)
    
    # Output file paths
    timestamp = datetime.now().strftime('%d%m_%H%M')
    output_file = Path(__file__).parent / f"full_test_{timestamp}.json"
    
    try:
        # Process text with each model
        results = []
        consecutive_timeouts = 0
        max_consecutive_timeouts = 3
        
        for i, model in enumerate(models):
            logger.info(f"Processing with model {model['id']}: {model['model']} (Provider: {model['provider']})")
            
            try:
                # Use longer timeout for comprehensive testing
                result = await processor.process_text_with_model(
                    system_content=system_content,
                    user_content=user_content,
                    model_id=model['id'],
                    model_name=model['model'],
                    provider_id=model['provider'],
                    temperature=model['temperature'],
                    top_p=model['top_p'],
                    max_tokens=model['max_tokens'],
                    http_session=http_session
                )
                
                results.append(result)
                logger.info(f"Completed processing with model {model['id']} in {result['processing_time']:.2f}s")
                
                # Reset consecutive timeout counter on successful response
                consecutive_timeouts = 0
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "result": f"Exception: {str(e)}",
                    "model_id": model['id'],
                    "model_name": model['model'],
                    "provider": processor.provider_factory.get_provider_name(model['provider']),
                    "processing_time": 0
                }
                results.append(error_result)
                logger.error(f"Error processing with model {model['id']}: {e}")
                
                # Check if this is a timeout error
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    # Increment consecutive timeout counter
                    consecutive_timeouts += 1
                    
                    # If we have 3 consecutive timeouts, log but continue testing
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        logger.warning(f"Detected {max_consecutive_timeouts} consecutive timeouts - this may indicate a processor issue")
                else:
                    # Reset consecutive timeout counter on non-timeout errors
                    consecutive_timeouts = 0
            
            # Save intermediate results after each model
            intermediate_output = {
                "test_summary": {
                    "total_models": len(models),
                    "models_tested": i + 1,
                    "successful_processing": len([r for r in results if r["success"]]),
                    "failed_processing": len([r for r in results if not r["success"]]),
                    "consecutive_timeouts": consecutive_timeouts,
                    "timestamp": datetime.now().isoformat(),
                    "system_content": system_content,
                    "user_content": user_content
                },
                "results": [{k: v for k, v in r.items() if k != "success"} for r in results]
            }
            
            # Write results to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(intermediate_output, f, ensure_ascii=False, indent=2)
        
        # Output final results as JSON
        print("\n" + "="*50)
        print("FULL TEST RESULTS")
        print("="*50)
        
        final_output = {
            "test_summary": {
                "total_models": len(models),
                "models_tested": len(results),
                "successful_processing": len([r for r in results if r["success"]]),
                "failed_processing": len([r for r in results if not r["success"]]),
                "consecutive_timeouts": consecutive_timeouts,
                "completed_at": datetime.now().isoformat(),
                "system_content": system_content,
                "user_content": user_content
            },
            "results": [{k: v for k, v in r.items() if k != "success"} for r in results]
        }
        
        # Print to console
        print(json.dumps(final_output, ensure_ascii=False, indent=2))
        
        # Write final results to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to: {output_file}")
    
    finally:
        # Close the HTTP session
        if http_session and not http_session.closed:
            await http_session.close()


if __name__ == "__main__":
    asyncio.run(main())