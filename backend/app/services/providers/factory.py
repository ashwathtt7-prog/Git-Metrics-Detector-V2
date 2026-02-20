from __future__ import annotations

import logging
from .base import LLMProvider

logger = logging.getLogger(__name__)

_provider_instance: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Create and cache the LLM provider based on settings.

    Reads LLM_PROVIDER from config and instantiates the appropriate provider.
    Supported values: ollama (default), gemini, openai, anthropic.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    from ...config import settings

    provider_name = settings.llm_provider.lower().strip()

    if provider_name == "gemini":
        if not settings.gemini_api_key and not settings.gemini_service_account_file:
            raise ValueError("Either GEMINI_API_KEY or GEMINI_SERVICE_ACCOUNT_FILE is required when LLM_PROVIDER=gemini")
        
        from .gemini_provider import GeminiProvider
        _provider_instance = GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            service_account_file=settings.gemini_service_account_file
        )

    elif provider_name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        from .openai_provider import OpenAIProvider
        _provider_instance = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    elif provider_name == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        from .anthropic_provider import AnthropicProvider
        _provider_instance = AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    elif provider_name == "ollama":
        from .ollama_provider import OllamaProvider
        _provider_instance = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider_name}'. "
            f"Supported: ollama, gemini, openai, anthropic"
        )

    logger.info(f"[LLM] Using provider: {_provider_instance.name} ({provider_name})")
    return _provider_instance
