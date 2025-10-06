"""Factory for creating vision model providers."""

import logging
from typing import Dict, Any, Optional

from ..providers import (
    VisionModelProvider,
    OllamaProvider,
    LMStudioProvider,
    MLXVLMProvider
)

logger = logging.getLogger(__name__)


PROVIDER_CLASSES = {
    'ollama': OllamaProvider,
    'lm_studio': LMStudioProvider,
    'lmstudio': LMStudioProvider,  # Alias
    'mlx_vlm': MLXVLMProvider,
    'mlx': MLXVLMProvider,  # Alias
}


def create_provider(provider_config: Dict[str, Any]) -> VisionModelProvider:
    """Create a vision model provider from configuration.
    
    Args:
        provider_config: Provider configuration dictionary with 'type' and 'settings'
        
    Returns:
        Configured provider instance
        
    Raises:
        ValueError: If provider type is unknown
        RuntimeError: If provider server is not available
    """
    provider_type = provider_config.get('type', '').lower()
    settings = provider_config.get('settings', {})
    
    if provider_type not in PROVIDER_CLASSES:
        available = ', '.join(PROVIDER_CLASSES.keys())
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Available providers: {available}"
        )
    
    # Create provider instance
    provider_class = PROVIDER_CLASSES[provider_type]
    
    # Extract common settings
    model_name = settings.get('model')
    api_url = settings.get('api_url')
    
    # Get provider-specific config
    provider_config = {
        k: v for k, v in settings.items() 
        if k not in ['model', 'api_url', 'max_retries', 'timeout']
    }
    
    logger.info(f"Creating {provider_type} provider with model: {model_name}")
    
    # Create provider
    provider = provider_class(
        model_name=model_name,
        api_url=api_url,
        config=provider_config
    )
    
    # Check if server is available
    if not provider.check_server():
        raise RuntimeError(
            f"{provider_type} server is not available. "
            f"Please ensure the server is running and the model is loaded."
        )
    
    return provider


def list_available_providers() -> Dict[str, str]:
    """Get list of available provider types.
    
    Returns:
        Dictionary mapping provider names to descriptions
    """
    return {
        'ollama': 'Ollama local AI server',
        'lm_studio': 'LM Studio with OpenAI-compatible API',
        'mlx_vlm': 'MLX Vision Language Models for Apple Silicon'
    }