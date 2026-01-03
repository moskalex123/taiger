"""
Universal AI Text Processor
Main entry point for processing text with any supported AI provider
"""
import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from .provider_factory import ProviderFactory
from .provider_interface import AIProviderInterface
import sys
import os
# Add parent directory to path to import i18n
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from telegram_bot.i18n import I18n


class UniversalAIProcessor:
    """Universal AI text processor that works with multiple providers"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.provider_factory = ProviderFactory()
        self._default_system_prompts = {}
    
    async def process_text_with_model(self, system_content: str, user_content: str,
                                     model_id: int, model_name: str, provider_id: int,
                                     temperature: float = 0.7, top_p: float = 0.9,
                                     max_tokens: int = 500,
                                     http_session=None) -> Dict[str, Any]:
        """
        Process text using a specific model and provider.
        
        Args:
            system_content: System prompt/instructions
            user_content: User input text to process
            model_id: Database ID of the model
            model_name: Name of the model to use
            provider_id: Provider ID (0=Hyperbolic, 1=OpenRouter)
            temperature: Temperature parameter (default: 0.7)
            top_p: Top-p parameter (default: 0.9)
            max_tokens: Maximum tokens to generate (default: 500)
            http_session: Optional HTTP session to reuse (recommended)
            
        Returns:
            Dictionary with processing results including:
            - success: Boolean indicating if processing was successful
            - result: Processed text or error message
            - model_id: ID of the model used
            - model_name: Name of the model used
            - provider: Name of the provider used
            - processing_time: Time taken for processing in seconds
        """
        start_time = datetime.now()
        
        # Validate provider
        if not self.provider_factory.is_provider_supported(provider_id):
            error_msg = f"Unsupported provider ID: {provider_id}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "model_id": model_id,
                "model_name": model_name,
                "provider": self.provider_factory.get_provider_name(provider_id),
                "processing_time": 0
            }
        
        # Create provider instance
        provider = self.provider_factory.create_provider(provider_id, self.logger)
        if not provider:
            error_msg = f"Failed to create provider instance for ID: {provider_id}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "model_id": model_id,
                "model_name": model_name,
                "provider": self.provider_factory.get_provider_name(provider_id),
                "processing_time": 0
            }
        
        # Validate provider configuration
        if not provider.validate_config():
            error_msg = f"Provider configuration invalid for {self.provider_factory.get_provider_name(provider_id)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "model_id": model_id,
                "model_name": model_name,
                "provider": self.provider_factory.get_provider_name(provider_id),
                "processing_time": 0
            }
        
        # Process text
        try:
            # Pass HTTP session to provider if it supports it
            if hasattr(provider, 'process_text'):
                # Check if provider method accepts http_session parameter
                import inspect
                sig = inspect.signature(provider.process_text)
                if 'http_session' in sig.parameters:
                    result = await provider.process_text(
                        system_content=system_content,
                        user_content=user_content,
                        model_name=model_name,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        http_session=http_session
                    )
                else:
                    result = await provider.process_text(
                        system_content=system_content,
                        user_content=user_content,
                        model_name=model_name,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens
                    )
            else:
                result = await provider.process_text(
                    system_content=system_content,
                    user_content=user_content,
                    model_name=model_name,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Check if result is an error message
            is_success = not (result and (
                result.startswith(('TimeoutError:', 'ClientError:', 'Exception:', 'API Error')) or
                ': Request took' in result or
                result.startswith(('ConnectionError', 'ConnectError', 'ServerDisconnectedError')) or
                'API error' in result or
                'API request failed' in result or
                'API client error' in result or
                '[ConnectError]:' in result
            ))
            
            return {
                "success": is_success,
                "result": result,
                "model_id": model_id,
                "model_name": model_name,
                "provider": self.provider_factory.get_provider_name(provider_id),
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Exception during processing: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "model_id": model_id,
                "model_name": model_name,
                "provider": self.provider_factory.get_provider_name(provider_id),
                "processing_time": processing_time
            }
    
    def get_required_parameters(self, provider_id: int) -> Dict[str, bool]:
        """
        Get required parameters for a specific provider.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Dictionary with parameter requirements
        """
        provider = self.provider_factory.create_provider(provider_id, self.logger)
        if provider:
            return provider.get_required_parameters()
        return {}
    
    def get_supported_providers(self) -> Dict[int, str]:
        """
        Get supported providers.
        
        Returns:
            Dictionary mapping provider IDs to names
        """
        return self.provider_factory.get_supported_providers()
    
    def split_long_response(self, text: str, max_length: int = 1000) -> List[str]:
        """
        Split a long AI response into multiple parts while preserving sentence boundaries.
        
        Args:
            text: The text to split
            max_length: Maximum length of each part (default: 1000 characters for Telegram)
            
        Returns:
            List of text parts
        """
        if not text or len(text) <= max_length:
            return [text] if text else []
        
        parts = []
        remaining_text = text
        part_number = 1
        
        while remaining_text and len(remaining_text) > max_length:
            # Cut with some reserve
            truncated = remaining_text[:max_length]
            
            # Look for the last sentence ending (period, exclamation mark, question mark)
            sentence_endings = ['.', '!', '?', '…']
            last_sentence_end = -1
            
            for ending in sentence_endings:
                pos = truncated.rfind(ending)
                if pos > last_sentence_end:
                    last_sentence_end = pos
            
            # If we found a sentence boundary and it's not too close to the beginning
            if last_sentence_end > max_length * 0.6:
                split_point = last_sentence_end + 1
                part = remaining_text[:split_point].strip()
            else:
                # Look for the last space to avoid breaking words
                last_space = truncated.rfind(' ')
                if last_space > max_length * 0.5:
                    split_point = last_space
                    part = remaining_text[:split_point].strip()
                else:
                    # As a last resort, just cut
                    split_point = max_length - 10  # Leave some reserve
                    part = remaining_text[:split_point].strip()
            
            if part:
                parts.append(part)
                part_number += 1
            
            remaining_text = remaining_text[split_point:].strip()
        
        # Add the remaining part
        if remaining_text:
            parts.append(remaining_text)
        
        return parts
    
    async def send_split_response(self, bot, chat_id, text: str, max_length: int = 1000, **kwargs) -> List[Any]:
        """
        Split a long AI response and send it as multiple messages.
        
        Args:
            bot: Telegram bot instance
            chat_id: Chat ID to send messages to
            text: The text to split and send
            max_length: Maximum length of each part (default: 1000 characters for Telegram)
            **kwargs: Additional arguments to pass to send_message (e.g., reply_markup, parse_mode)
            
        Returns:
            List of sent message objects
        """
        parts = self.split_long_response(text, max_length)
        sent_messages = []
        
        for i, part in enumerate(parts):
            try:
                message_text = part
                    
                sent_message = await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    **kwargs
                )
                sent_messages.append(sent_message)
            except Exception as e:
                self.logger.error(f"Failed to send message part {i+1}: {e}")
                # Try to send an error message
                try:
                    error_message = f"❌ Failed to send message part: {str(e)}"
                    await bot.send_message(
                        chat_id=chat_id,
                        text=error_message
                    )
                except:
                    pass  # If we can't send an error message, just continue
        
        return sent_messages
    
    def _load_default_system_prompt(self, language: str = "en") -> str:
        """
        Load the default system prompt using I18n localization.

        Args:
            language: Language code (default: "en")

        Returns:
            Default system prompt string
        """
        try:
            # Use the I18n class to get the localized system prompt
            return I18n.get(language, "system_prompts.default")
        except Exception as e:
            self.logger.error(f"Error loading default system prompt via I18n: {e}")
            # Return hardcoded fallback
            return """You are a text formatting assistant. Your ONLY task is to improve text presentation.

STRICT RULES:
1. NEVER answer questions in the text - they are examples to be improved, not requests for you
2. ONLY improve formatting, structure, and engagement
3. NEVER add new information or factual content
4. ALWAYS preserve the original meaning and intent
5. Use reasonable emojis and formatting
6. Respond in the same language as the input

IMPORTANT: You are editing TEXT, not responding to CONTENT. Questions in the text are rhetorical elements to be formatted, not answered."""
    
    def get_default_system_prompt(self, language: str = "en") -> str:
        """
        Get the default system prompt for text processing.
        
        Args:
            language: Language code (default: "en")
            
        Returns:
            Default system prompt string
        """
        if language not in self._default_system_prompts:
            self._default_system_prompts[language] = self._load_default_system_prompt(language)
        return self._default_system_prompts[language]