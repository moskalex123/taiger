"""
Provider Factory for Universal AI Text Processor
"""
from typing import Optional, Dict, Any
from .provider_interface import AIProviderInterface
from .hyperbolic_provider import HyperbolicProvider
from .openrouter_provider import OpenRouterProvider


class ProviderFactory:
    """Factory class to create provider instances based on provider ID"""
    
    # Provider ID mapping
    PROVIDER_HYPERBOLIC = 0
    PROVIDER_OPENROUTER = 1
    
    # Provider class mapping
    _provider_classes = {
        PROVIDER_HYPERBOLIC: HyperbolicProvider,
        PROVIDER_OPENROUTER: OpenRouterProvider
    }
    
    @classmethod
    def create_provider(cls, provider_id: int, logger=None) -> Optional[AIProviderInterface]:
        """
        Create a provider instance based on provider ID.
        
        Args:
            provider_id: Integer ID of the provider (0=Hyperbolic, 1=OpenRouter)
            logger: Optional logger instance
            
        Returns:
            Provider instance or None if provider ID is not supported
        """
        provider_class = cls._provider_classes.get(provider_id)
        if provider_class:
            return provider_class(logger)
        return None
    
    @classmethod
    def get_provider_name(cls, provider_id: int) -> str:
        """
        Get the name of a provider based on its ID.
        
        Args:
            provider_id: Integer ID of the provider
            
        Returns:
            Provider name as string
        """
        if provider_id == cls.PROVIDER_HYPERBOLIC:
            return "Hyperbolic"
        elif provider_id == cls.PROVIDER_OPENROUTER:
            return "OpenRouter"
        else:
            return f"Unknown Provider ({provider_id})"
    
    @classmethod
    def get_supported_providers(cls) -> Dict[int, str]:
        """
        Get a dictionary of supported providers.
        
        Returns:
            Dictionary mapping provider IDs to provider names
        """
        return {
            cls.PROVIDER_HYPERBOLIC: "Hyperbolic",
            cls.PROVIDER_OPENROUTER: "OpenRouter"
        }
    
    @classmethod
    def is_provider_supported(cls, provider_id: int) -> bool:
        """
        Check if a provider ID is supported.
        
        Args:
            provider_id: Integer ID of the provider
            
        Returns:
            True if provider is supported, False otherwise
        """
        return provider_id in cls._provider_classes