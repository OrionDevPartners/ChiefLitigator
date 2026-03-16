"""CPAA-compliant LLM provider abstraction.

Provides a unified interface for LLM calls that works identically with:
- Direct Anthropic API (development)
- AWS Bedrock Runtime (production)

The factory function ``get_provider()`` reads LLM_PROVIDER from the
environment and returns the appropriate implementation. Agents never
know which provider they are using.

Environment Variables
---------------------
LLM_PROVIDER : str
    "anthropic" (default) or "bedrock".

Anthropic-specific:
    ANTHROPIC_API_KEY : str

Bedrock-specific:
    AWS_ACCESS_KEY_ID : str
    AWS_SECRET_ACCESS_KEY : str
    AWS_DEFAULT_REGION : str (defaults to "us-east-1")
    AWS_SESSION_TOKEN : str (optional, for assumed-role credentials)
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response envelope — unified across providers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LLMProviderResponse:
    """Normalized response returned by every provider implementation.

    Attributes
    ----------
    text : str
        Concatenated text content from the model response.
    input_tokens : int
        Token count consumed by the prompt.
    output_tokens : int
        Token count generated in the response.
    stop_reason : str
        Why the model stopped (e.g. "end_turn", "max_tokens").
    raw : Any
        Provider-specific raw response object for advanced introspection.
        Callers should NOT depend on the shape of this field.
    """

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    raw: Any = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract interface for LLM providers.

    All providers expose a single ``create_message`` coroutine with the
    same signature. Agents call this method and receive an
    ``LLMProviderResponse`` regardless of the backend.
    """

    @abstractmethod
    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        system: str,
        messages: list[dict[str, Any]],
    ) -> LLMProviderResponse:
        """Send a prompt to the LLM and return a normalized response.

        Parameters
        ----------
        model:
            Model identifier. Anthropic format for AnthropicProvider
            (e.g. "claude-opus-4-6"), Bedrock format for BedrockProvider
            (e.g. "anthropic.claude-opus-4-6-20250514-v1:0").
        max_tokens:
            Maximum tokens to generate.
        temperature:
            Sampling temperature (0.0 - 1.0).
        system:
            System prompt.
        messages:
            Conversation messages in OpenAI/Anthropic format
            (list of {"role": str, "content": str} dicts).

        Returns
        -------
        LLMProviderResponse
        """
        ...


# ---------------------------------------------------------------------------
# Anthropic (direct API) — development
# ---------------------------------------------------------------------------

class AnthropicProvider(LLMProvider):
    """Direct Anthropic API provider for development environments.

    Reads ANTHROPIC_API_KEY from the environment. Uses the official
    ``anthropic`` Python SDK with async support.
    """

    def __init__(self) -> None:
        try:
            import anthropic  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicProvider. "
                "Install it with: pip install anthropic"
            ) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for "
                "AnthropicProvider but was not set or is empty."
            )

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        logger.info("AnthropicProvider initialized (direct API)")

    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        system: str,
        messages: list[dict[str, Any]],
    ) -> LLMProviderResponse:
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )

        text_parts: list[str] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        return LLMProviderResponse(
            text="\n".join(text_parts),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason or "",
            raw=response,
        )


# ---------------------------------------------------------------------------
# Model ID mapping — Anthropic shorthand to Bedrock ARN-style IDs
# ---------------------------------------------------------------------------

_BEDROCK_MODEL_MAP: dict[str, str] = {
    # Opus 4.6 — orchestrator + all legal agents in production
    # Uses inference profile (us. prefix) as required by Bedrock on-demand
    "claude-opus-4-6": "us.anthropic.claude-opus-4-6-v1",
    "claude-opus-4-6-20250514": "us.anthropic.claude-opus-4-6-v1",
    # Sonnet 4.6
    "claude-sonnet-4-6": "us.anthropic.claude-sonnet-4-6",
    "claude-sonnet-4-6-20250514": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    # Haiku 4.5
    "claude-haiku-4-5": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "claude-haiku-4-5-20251001": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    # Opus 4.5 / 4.1
    "claude-opus-4-5": "us.anthropic.claude-opus-4-5-20251101-v1:0",
    "claude-opus-4-1": "us.anthropic.claude-opus-4-1-20250805-v1:0",
    # Older models
    "claude-sonnet-4-20250514": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "claude-3-5-sonnet-20241022": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3-5-haiku-20241022": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
}


def _resolve_bedrock_model_id(model: str) -> str:
    """Convert an Anthropic model name to its Bedrock equivalent.

    If the model string is already in Bedrock format (contains a dot),
    it is returned unchanged. Otherwise the mapping table is consulted.
    Falls back to the original string if no mapping exists, so that
    newly released models can be used by passing the full Bedrock ID
    directly via the LLM_MODEL env var.
    """
    if "." in model:
        return model
    resolved = _BEDROCK_MODEL_MAP.get(model, model)
    if resolved == model:
        logger.warning(
            "No Bedrock model mapping found for '%s'. "
            "Passing it through unchanged — set LLM_MODEL to a valid "
            "Bedrock model ID if this fails.",
            model,
        )
    return resolved


# ---------------------------------------------------------------------------
# AWS Bedrock — production
# ---------------------------------------------------------------------------

class BedrockProvider(LLMProvider):
    """AWS Bedrock Runtime provider for production environments.

    Uses boto3's ``bedrock-runtime`` client with the Anthropic Messages
    API format (``invoke_model`` with ``anthropic_version``).

    Credentials are resolved through the standard boto3 chain:
    environment variables, shared credentials file, IAM role, or
    ECS task role.

    Environment Variables
    ---------------------
    AWS_DEFAULT_REGION : str
        AWS region for the Bedrock endpoint (default: "us-east-1").
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY : str
        Explicit credentials (optional if using IAM/ECS role).
    AWS_SESSION_TOKEN : str
        Session token for temporary credentials (optional).
    """

    def __init__(self) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "The 'boto3' package is required for BedrockProvider. "
                "Install it with: pip install boto3"
            ) from exc

        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
        )
        self._region = region
        logger.info(
            "BedrockProvider initialized (region=%s)",
            region,
        )

    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        system: str,
        messages: list[dict[str, Any]],
    ) -> LLMProviderResponse:
        """Invoke a model through AWS Bedrock Runtime using the Converse API.

        The Converse API is the recommended interface for newer Bedrock models
        (Opus 4.6, Sonnet 4.6, etc.). It provides a unified format across all
        model providers on Bedrock.

        Bedrock's API is synchronous. This method wraps it in
        ``asyncio.to_thread`` so it integrates cleanly with async
        agent code without blocking the event loop.
        """
        import asyncio

        bedrock_model_id = _resolve_bedrock_model_id(model)

        # Convert messages from Anthropic format to Bedrock Converse format
        converse_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                converse_messages.append({
                    "role": role,
                    "content": [{"text": content}],
                })
            elif isinstance(content, list):
                # Already in block format
                converse_messages.append({
                    "role": role,
                    "content": content if all(isinstance(b, dict) for b in content) else [{"text": str(content)}],
                })

        # Build system prompt in Converse format
        system_blocks = [{"text": system}] if system else []

        raw_response = await asyncio.to_thread(
            self._client.converse,
            modelId=bedrock_model_id,
            messages=converse_messages,
            system=system_blocks,
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        )

        # Extract text from Converse response format
        output_message = raw_response.get("output", {}).get("message", {})
        text_parts: list[str] = []
        for block in output_message.get("content", []):
            if "text" in block:
                text_parts.append(block["text"])

        usage = raw_response.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        stop_reason = raw_response.get("stopReason", "")

        return LLMProviderResponse(
            text="\n".join(text_parts),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=stop_reason,
            raw=raw_response,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_provider_instance: LLMProvider | None = None


def get_provider(*, force_new: bool = False) -> LLMProvider:
    """Return the LLM provider based on the LLM_PROVIDER env var.

    Parameters
    ----------
    force_new:
        If True, discard the cached singleton and create a fresh
        provider instance. Used in tests.

    Returns
    -------
    LLMProvider
        An AnthropicProvider (default) or BedrockProvider instance.

    Raises
    ------
    ValueError
        If LLM_PROVIDER is set to an unsupported value.
    """
    global _provider_instance

    if _provider_instance is not None and not force_new:
        return _provider_instance

    provider_name = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    if provider_name == "bedrock":
        _provider_instance = BedrockProvider()
    elif provider_name == "anthropic":
        _provider_instance = AnthropicProvider()
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER value: '{provider_name}'. "
            f"Expected 'anthropic' or 'bedrock'."
        )

    logger.info("LLM provider resolved: %s", provider_name)
    return _provider_instance


def reset_provider() -> None:
    """Clear the cached provider singleton. Used in tests."""
    global _provider_instance
    _provider_instance = None
