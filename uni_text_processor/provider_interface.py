"""
AI Provider Interface for Universal Text Processor
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio


class AIProviderInterface(ABC):
    """Abstract base class for all AI providers"""
    
    def __init__(self, logger=None):
        self.logger = logger or self._get_default_logger()
    
    @abstractmethod
    async def process_text(self, system_content: str, user_content: str,
                          model_name: str, temperature: float,
                          top_p: float, max_tokens: int) -> Optional[str]:
        """
        Process text with the AI provider.
        
        Args:
            system_content: System prompt/instructions
            user_content: User input text to process
            model_name: Name of the model to use
            temperature: Temperature parameter for the model
            top_p: Top-p parameter for the model
            max_tokens: Maximum tokens to generate
            
        Returns:
            Processed text or None if failed
        """
        pass
    
    @abstractmethod
    def get_required_parameters(self) -> Dict[str, bool]:
        """
        Get required parameters for this provider.
        
        Returns:
            Dictionary with parameter names as keys and whether they're required as values
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the provider is properly configured.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
    
    def _get_default_logger(self):
        """Get a default logger if none provided"""
        import logging
        return logging.getLogger(__name__)
    
    def log_info(self, message: str):
        """Log info message"""
        if self.logger:
            self.logger.info(message)
    
    def log_error(self, message: str):
        """Log error message"""
        if self.logger:
            self.logger.error(message)
    
    def log_warning(self, message: str):
        """Log warning message"""
        if self.logger:
            self.logger.warning(message)