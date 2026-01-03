"""
AI процессор для интеграции с UniversalAIProcessor (UniTextProcessor)
"""
import os
import sys
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Optional
from uni_text_processor.universal_processor import UniversalAIProcessor
from uni_text_processor.db_utils import DatabaseUtils

class AIProcessor:
    """Обработчик AI запросов через UniversalAIProcessor (UniTextProcessor)"""
    
    def __init__(self, logger, log_worker_status_callback=None):
        self.logger = logger
        self._log_worker_status = log_worker_status_callback
        
        self.db_utils = DatabaseUtils(self.logger)
        self.universal_processor = UniversalAIProcessor(self.logger)
    
    async def process_with_hyperbolic(self, system_content: str, user_content: str,
                                    model_name: str, temperature: float,
                                    top_p: float, max_tokens: int,
                                    http_session: aiohttp.ClientSession) -> Optional[str]:
        """Process text with UniversalAIProcessor (UniTextProcessor)."""
        
        self.logger.info(f"Processing with UniversalAIProcessor. Model: {model_name}")
        self.logger.info(f"Request parameters: temperature={temperature}, top_p={top_p}, max_tokens={max_tokens}")
        self.logger.info(f"Input text length: {len(user_content)} chars")
        
        request_start_time = datetime.now()
        
        try:
            # Получить информацию о модели из БД
            models = await self.db_utils.get_all_models()
            model_data = next((m for m in models if m['model'] == model_name), None)
            if not model_data:
                error = f"Model '{model_name}' not found in database"
                self.logger.error(error)
                return error
            
            model_id = model_data['id']
            provider_id = model_data.get('provider', 0)
            
            self.logger.info(f"Found model_id={model_id}, provider_id={provider_id} ({self.universal_processor.provider_factory.get_provider_name(provider_id) if hasattr(self.universal_processor.provider_factory, 'get_provider_name') else 'unknown'})")
            
            # Обработать текст через UniversalAIProcessor
            result = await self.universal_processor.process_text_with_model(
                system_content=system_content,
                user_content=user_content,
                model_id=model_id,
                model_name=model_name,
                provider_id=provider_id,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                http_session=http_session
            )
            
            processing_time = (datetime.now() - request_start_time).total_seconds()
            
            if result['success']:
                processed_text = result['result']
                self.logger.info(f"✅ Processed successfully: {len(processed_text)} chars output")
                self.logger.info(f"⏱️ Processing time: {result['processing_time']:.2f}s")
                return processed_text
            else:
                self.logger.error(f"❌ Processing failed: {result['result']}")
                # Логирование в статус воркера
                if self._log_worker_status:
                    await self._log_worker_status("ai_processor_error", 
                        "log_ai_processor_error", "error", error=result['result'][:100])
                return result['result']
                
        except Exception as e:
            processing_time = (datetime.now() - request_start_time).total_seconds()
            error_msg = f"UniversalAIProcessor error after {processing_time:.2f}s: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            if self._log_worker_status:
                await self._log_worker_status("ai_processor_exception", 
                    "log_ai_processor_exception", "error", error=str(e))
            return f"{type(e).__name__}: {str(e)[:150]}"