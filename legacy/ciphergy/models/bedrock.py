"""
AWS Bedrock integration for Ciphergy Pipeline.

Provides a production-grade client for invoking Anthropic foundation models
via AWS Bedrock, with streaming, tool use, retry logic, and token tracking.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Sequence

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model catalog — inference-profile IDs required by Bedrock cross-region
# ---------------------------------------------------------------------------

SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
    "claude-sonnet-4-6": {
        "model_id": "us.anthropic.claude-sonnet-4-6-20250514",
        "display_name": "Claude Sonnet 4.6",
        "max_tokens": 1_000_000,
        "capabilities": ["messages", "tools", "streaming", "vision"],
        "priority": 1,  # lower = preferred for cost
    },
    "claude-opus-4-6": {
        "model_id": "us.anthropic.claude-opus-4-6-20250514",
        "display_name": "Claude Opus 4.6",
        "max_tokens": 1_000_000,
        "capabilities": ["messages", "tools", "streaming", "vision"],
        "priority": 2,
    },
}

DEFAULT_MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TokenUsage:
    """Tracks token consumption for a single invocation."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class BedrockResponse:
    """Structured response from a Bedrock invocation."""

    content: str
    stop_reason: str
    model_id: str
    usage: TokenUsage
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

_THROTTLE_CODES = {"ThrottlingException", "TooManyRequestsException", "ServiceUnavailableException"}
_MAX_RETRIES = 5
_BASE_DELAY = 1.0  # seconds


def _should_retry(error: ClientError) -> bool:
    code = error.response.get("Error", {}).get("Code", "")
    return code in _THROTTLE_CODES


def _backoff_delay(attempt: int) -> float:
    return min(_BASE_DELAY * (2 ** attempt), 30.0)


# ---------------------------------------------------------------------------
# BedrockClient
# ---------------------------------------------------------------------------


class BedrockClient:
    """Production client for AWS Bedrock Anthropic models.

    Supports the Messages API, tool use, streaming, and automatic retry
    with exponential backoff on throttling errors.

    Parameters
    ----------
    region : str, optional
        AWS region.  Resolved in order: explicit arg -> CIPHERGY_AWS_REGION
        -> AWS_DEFAULT_REGION -> AWS_REGION -> us-east-1.
    profile : str, optional
        Named AWS profile (for local dev).  In production, use IAM roles.
    preferred_model : str, optional
        Key into SUPPORTED_MODELS.  Defaults to ``claude-sonnet-4-6``.
    max_retries : int
        Maximum retry attempts on throttling.
    """

    def __init__(
        self,
        region: Optional[str] = None,
        profile: Optional[str] = None,
        preferred_model: str = DEFAULT_MODEL,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self.region = region or self._resolve_region()
        self.preferred_model = preferred_model
        self.max_retries = max_retries

        # Cumulative token tracking across calls
        self._cumulative_usage = TokenUsage()

        session_kwargs: Dict[str, Any] = {"region_name": self.region}
        if profile:
            session_kwargs["profile_name"] = profile

        session = boto3.Session(**session_kwargs)
        boto_config = BotoConfig(
            retries={"max_attempts": 0},  # we handle retries ourselves
            read_timeout=300,
            connect_timeout=10,
        )
        self._client = session.client("bedrock-runtime", config=boto_config)
        self._bedrock_mgmt = session.client("bedrock", config=boto_config)
        logger.info("BedrockClient initialized: region=%s, model=%s", self.region, self.preferred_model)

    # ------------------------------------------------------------------
    # Region resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_region() -> str:
        for var in ("CIPHERGY_AWS_REGION", "AWS_DEFAULT_REGION", "AWS_REGION"):
            val = os.environ.get(var)
            if val:
                return val
        return "us-east-1"

    # ------------------------------------------------------------------
    # Model helpers
    # ------------------------------------------------------------------

    def _resolve_model_id(self, model_key: Optional[str] = None) -> str:
        """Return the Bedrock model ID for the given key, with fallback."""
        key = model_key or self.preferred_model
        if key in SUPPORTED_MODELS:
            return SUPPORTED_MODELS[key]["model_id"]

        # Fallback chain: try all models in priority order
        for k in sorted(SUPPORTED_MODELS, key=lambda k: SUPPORTED_MODELS[k]["priority"]):
            logger.warning("Model '%s' not found, falling back to '%s'", key, k)
            return SUPPORTED_MODELS[k]["model_id"]

        raise ValueError(f"No supported models available. Requested: {key}")

    def get_available_models(self) -> List[Dict[str, Any]]:
        """List Bedrock foundation models matching 'anthropic'.

        Returns a list of dicts with modelId, modelName, and providerName.
        """
        try:
            paginator = self._bedrock_mgmt.get_paginator("list_foundation_models")
            results: List[Dict[str, Any]] = []
            for page in paginator.paginate(byProvider="Anthropic"):
                for summary in page.get("modelSummaries", []):
                    results.append({
                        "modelId": summary.get("modelId"),
                        "modelName": summary.get("modelName"),
                        "providerName": summary.get("providerName"),
                        "inputModalities": summary.get("inputModalities", []),
                        "outputModalities": summary.get("outputModalities", []),
                    })
            logger.info("Found %d Anthropic models on Bedrock", len(results))
            return results
        except ClientError as exc:
            logger.error("Failed to list foundation models: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Core invocation (Messages API)
    # ------------------------------------------------------------------

    def _build_body(
        self,
        messages: List[Dict[str, Any]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.95,
        tools: Optional[List[Dict[str, Any]]] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = tools
        if stop_sequences:
            body["stop_sequences"] = stop_sequences
        return body

    def _invoke_with_retry(
        self,
        model_id: str,
        body: Dict[str, Any],
        *,
        stream: bool = False,
    ) -> Any:
        """Low-level invoke with exponential backoff on throttle."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if stream:
                    resp = self._client.invoke_model_with_response_stream(
                        modelId=model_id,
                        contentType="application/json",
                        accept="application/json",
                        body=json.dumps(body),
                    )
                else:
                    resp = self._client.invoke_model(
                        modelId=model_id,
                        contentType="application/json",
                        accept="application/json",
                        body=json.dumps(body),
                    )
                return resp
            except ClientError as exc:
                last_exc = exc
                if _should_retry(exc) and attempt < self.max_retries:
                    delay = _backoff_delay(attempt)
                    logger.warning(
                        "Bedrock throttled (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, self.max_retries, delay, exc,
                    )
                    time.sleep(delay)
                else:
                    raise
        raise last_exc  # type: ignore[misc]

    def _parse_response(self, raw_bytes: bytes, model_id: str) -> BedrockResponse:
        """Parse the JSON body returned by invoke_model."""
        data = json.loads(raw_bytes)
        content_blocks = data.get("content", [])

        text_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input", {}),
                })

        usage_data = data.get("usage", {})
        usage = TokenUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
        )
        self._cumulative_usage.input_tokens += usage.input_tokens
        self._cumulative_usage.output_tokens += usage.output_tokens

        return BedrockResponse(
            content="\n".join(text_parts),
            stop_reason=data.get("stop_reason", "unknown"),
            model_id=model_id,
            usage=usage,
            tool_calls=tool_calls,
            raw=data,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke_model(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.95,
        stop_sequences: Optional[List[str]] = None,
    ) -> BedrockResponse:
        """Invoke a Bedrock model using the Messages API.

        Parameters
        ----------
        messages : list
            Conversation messages in ``[{"role": "user", "content": "..."}]`` format.
        model : str, optional
            Model key (e.g. ``claude-sonnet-4-6``).  Falls back to preferred.
        system : str, optional
            System prompt.
        max_tokens : int
            Maximum output tokens.  Up to 1M for context window.
        temperature : float
            Sampling temperature.
        top_p : float
            Nucleus sampling.
        stop_sequences : list, optional
            Custom stop sequences.

        Returns
        -------
        BedrockResponse
        """
        model_id = self._resolve_model_id(model)
        body = self._build_body(
            messages, system=system, max_tokens=max_tokens,
            temperature=temperature, top_p=top_p, stop_sequences=stop_sequences,
        )
        logger.debug("invoke_model: model=%s, messages=%d, max_tokens=%d", model_id, len(messages), max_tokens)
        resp = self._invoke_with_retry(model_id, body)
        raw_bytes = resp["body"].read()
        return self._parse_response(raw_bytes, model_id)

    def invoke_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> BedrockResponse:
        """Invoke a model with tool-use definitions.

        Parameters
        ----------
        messages : list
            Conversation messages.
        tools : list
            Tool definitions per the Anthropic tool-use schema::

                [{"name": "get_weather", "description": "...",
                  "input_schema": {"type": "object", "properties": {...}}}]
        model : str, optional
            Model key.
        system : str, optional
            System prompt.
        max_tokens : int
            Maximum output tokens.
        temperature : float
            Sampling temperature.

        Returns
        -------
        BedrockResponse
            Check ``response.tool_calls`` for any tool invocations requested
            by the model.
        """
        model_id = self._resolve_model_id(model)
        body = self._build_body(
            messages, system=system, max_tokens=max_tokens,
            temperature=temperature, tools=tools,
        )
        logger.debug("invoke_with_tools: model=%s, tools=%d", model_id, len(tools))
        resp = self._invoke_with_retry(model_id, body)
        raw_bytes = resp["body"].read()
        return self._parse_response(raw_bytes, model_id)

    def stream_model(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Generator[str, None, BedrockResponse]:
        """Stream a model response, yielding text chunks.

        Yields
        ------
        str
            Text delta chunks as they arrive.

        Returns
        -------
        BedrockResponse
            Final aggregated response (accessible via generator .value after
            StopIteration, or use the ``stream_model_full`` helper).
        """
        model_id = self._resolve_model_id(model)
        body = self._build_body(
            messages, system=system, max_tokens=max_tokens, temperature=temperature,
        )
        logger.debug("stream_model: model=%s", model_id)
        resp = self._invoke_with_retry(model_id, body, stream=True)

        stream = resp.get("body")
        if stream is None:
            raise RuntimeError("No streaming body returned from Bedrock")

        full_text: List[str] = []
        usage = TokenUsage()
        stop_reason = "unknown"

        for event in stream:
            chunk = event.get("chunk")
            if not chunk:
                continue
            data = json.loads(chunk["bytes"])
            event_type = data.get("type", "")

            if event_type == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    full_text.append(text)
                    yield text

            elif event_type == "message_delta":
                stop_reason = data.get("delta", {}).get("stop_reason", stop_reason)
                msg_usage = data.get("usage", {})
                usage.output_tokens = msg_usage.get("output_tokens", usage.output_tokens)

            elif event_type == "message_start":
                msg = data.get("message", {})
                msg_usage = msg.get("usage", {})
                usage.input_tokens = msg_usage.get("input_tokens", 0)

        self._cumulative_usage.input_tokens += usage.input_tokens
        self._cumulative_usage.output_tokens += usage.output_tokens

        return BedrockResponse(
            content="".join(full_text),
            stop_reason=stop_reason,
            model_id=model_id,
            usage=usage,
        )

    def stream_model_full(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        on_chunk: Optional[Any] = None,
    ) -> BedrockResponse:
        """Stream a model and collect the full response.

        Parameters
        ----------
        on_chunk : callable, optional
            Called with each text chunk as ``on_chunk(text: str)``.

        Returns
        -------
        BedrockResponse
        """
        gen = self.stream_model(
            messages, model=model, system=system,
            max_tokens=max_tokens, temperature=temperature,
        )
        try:
            while True:
                chunk = next(gen)
                if on_chunk:
                    on_chunk(chunk)
        except StopIteration as stop:
            return stop.value  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------

    @property
    def cumulative_usage(self) -> TokenUsage:
        """Return cumulative token usage across all invocations."""
        return self._cumulative_usage

    def reset_usage(self) -> None:
        """Reset cumulative token counters."""
        self._cumulative_usage = TokenUsage()
