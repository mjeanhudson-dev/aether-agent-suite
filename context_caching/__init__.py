"""
Aether Sovereign Agent Suite - Universal Gemini Context Caching Module
=====================================================================
Provides dual-mode Gemini Explicit Context Caching for heavy blueprints (MyAssistance, KPPC routing)
reducing input token consumption by 75% across AI coding harnesses.
"""

from .context_cache import (
    DEFAULT_ADC_LOCATION,
    DEFAULT_ADC_PROJECT,
    DEFAULT_MODEL,
    create_context_cache,
    get_genai_client,
    list_context_caches,
    query_cached_content,
)

__all__ = [
    "DEFAULT_ADC_PROJECT",
    "DEFAULT_ADC_LOCATION",
    "DEFAULT_MODEL",
    "get_genai_client",
    "create_context_cache",
    "query_cached_content",
    "list_context_caches",
]
