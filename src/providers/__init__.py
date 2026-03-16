"""LLM provider abstraction layer for CPAA-compliant provider switching.

The LLM_PROVIDER environment variable controls which backend is used:
- "anthropic" (default): Direct Anthropic API via anthropic.AsyncAnthropic.
- "bedrock": AWS Bedrock Runtime via boto3.

Agents import ``get_provider()`` and receive a provider instance that
implements ``LLMProvider``. Zero code changes between dev and prod --
only the environment variable changes.
"""

from src.providers.llm_provider import (
    AnthropicProvider,
    BedrockProvider,
    LLMProvider,
    LLMProviderResponse,
    get_provider,
)

__all__ = [
    "AnthropicProvider",
    "BedrockProvider",
    "LLMProvider",
    "LLMProviderResponse",
    "get_provider",
]
