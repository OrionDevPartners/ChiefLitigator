"""
Ciphergy Pipeline — Base Connector

Abstract base class and configuration for all Ciphergy connectors.
Every connector must implement connect(), disconnect(), health_check(),
fetch(), and push(). The message bus protocol is defined here as well.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConnectorConfig:
    """Configuration for a Ciphergy connector."""

    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: str = "bearer"  # bearer, api_key, oauth2, none
    rate_limit: int = 100  # requests per minute
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageBusMessage:
    """Standard message format for the Ciphergy inter-connector message bus."""

    source: str
    destination: str
    msg_type: str  # STATUS, ALERT, QUESTION, ANSWER, DIRECTIVE, CASCADE, SYNC, DATA
    payload: Dict[str, Any]
    priority: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    timestamp: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BaseConnector(ABC):
    """
    Base class for all Ciphergy connectors.

    Provides rate limiting, retry logic, connection lifecycle management,
    and the Ciphergy message bus protocol. Subclasses must implement the
    five abstract methods.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self._connected: bool = False
        self._request_timestamps: List[float] = []
        self._logger = logging.getLogger(f"ciphergy.connectors.{config.name}")

    @property
    def is_connected(self) -> bool:
        """Whether the connector is currently connected."""
        return self._connected

    @property
    def name(self) -> str:
        """Connector name from config."""
        return self.config.name

    # ── Abstract interface ──────────────────────────────────────────

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the external service.

        Returns:
            True if connection was successful, False otherwise.
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully close the connection."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the service is reachable and authenticated.

        Returns:
            True if healthy, False otherwise.
        """
        ...

    @abstractmethod
    def fetch(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Fetch data from the external service.

        Args:
            query: Query string or resource identifier.
            **kwargs: Additional parameters specific to the connector.

        Returns:
            Dict containing the fetched data under a "data" key,
            plus "status" and "connector" metadata.
        """
        ...

    @abstractmethod
    def push(self, data: Dict[str, Any], **kwargs: Any) -> bool:
        """
        Push data to the external service.

        Args:
            data: The data payload to send.
            **kwargs: Additional parameters specific to the connector.

        Returns:
            True if the push succeeded, False otherwise.
        """
        ...

    # ── Rate limiting ───────────────────────────────────────────────

    def _check_rate_limit(self) -> None:
        """
        Block if the per-minute rate limit has been reached.

        Raises:
            RuntimeError: If rate limit cannot be satisfied within timeout.
        """
        now = time.monotonic()
        window = 60.0  # 1 minute window

        # Prune timestamps older than the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps if now - ts < window
        ]

        if len(self._request_timestamps) >= self.config.rate_limit:
            oldest = self._request_timestamps[0]
            wait_time = window - (now - oldest) + 0.1
            if wait_time > self.config.timeout:
                raise RuntimeError(
                    f"Rate limit ({self.config.rate_limit}/min) exceeded and "
                    f"wait time ({wait_time:.1f}s) exceeds timeout ({self.config.timeout}s)"
                )
            self._logger.warning("Rate limit reached. Waiting %.1fs", wait_time)
            time.sleep(wait_time)

        self._request_timestamps.append(time.monotonic())

    # ── Retry wrapper ───────────────────────────────────────────────

    def _with_retry(self, operation: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function with retry logic and rate limiting.

        Args:
            operation: Human-readable description for logging.
            func: The callable to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            The return value of func.

        Raises:
            RuntimeError: After all retries exhausted.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                self._check_rate_limit()
                return func(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                self._logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    operation,
                    attempt,
                    self.config.max_retries,
                    exc,
                )
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** (attempt - 1))
                    time.sleep(delay)

        raise RuntimeError(
            f"{operation} failed after {self.config.max_retries} retries: {last_error}"
        )

    # ── Message bus protocol ────────────────────────────────────────

    def send_message(self, message: MessageBusMessage) -> bool:
        """
        Send a message via the Ciphergy message bus protocol.

        The default implementation uses push() to deliver the message.
        Connectors can override for custom delivery.

        Args:
            message: The message to send.

        Returns:
            True if delivered successfully.
        """
        payload = {
            "ciphergy_message": True,
            "source": message.source,
            "destination": message.destination,
            "type": message.msg_type,
            "priority": message.priority,
            "timestamp": message.timestamp,
            "correlation_id": message.correlation_id,
            "payload": message.payload,
        }
        return self.push(payload, message_bus=True)

    def receive_messages(self, **kwargs: Any) -> List[MessageBusMessage]:
        """
        Receive pending messages from the message bus.

        The default implementation uses fetch() with a bus query.
        Connectors can override for custom reception.

        Args:
            **kwargs: Filter parameters.

        Returns:
            List of pending messages.
        """
        result = self.fetch("__ciphergy_bus__", **kwargs)
        messages: List[MessageBusMessage] = []

        for item in result.get("data", []):
            if isinstance(item, dict) and item.get("ciphergy_message"):
                messages.append(
                    MessageBusMessage(
                        source=item.get("source", ""),
                        destination=item.get("destination", ""),
                        msg_type=item.get("type", "INFO"),
                        payload=item.get("payload", {}),
                        priority=item.get("priority", "MEDIUM"),
                        timestamp=item.get("timestamp", ""),
                        correlation_id=item.get("correlation_id", ""),
                    )
                )

        return messages

    # ── Lifecycle helpers ───────────────────────────────────────────

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"<{self.__class__.__name__} name={self.config.name!r} status={status}>"
