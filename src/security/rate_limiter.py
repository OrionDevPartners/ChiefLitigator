"""4-layer rate limiting for the Cyphergy platform.

Architecture (from V2 spec):
  Layer 1: Per-IP        -- Blocks IP-level abuse (brute force, scraping)
  Layer 2: Per-User      -- Limits authenticated user request volume
  Layer 3: Per-Tenant    -- Aggregate cap across all users in an organization
  Layer 4: Global        -- Circuit breaker protecting the entire service

All limits are configurable via environment variables (CPAA-compliant).
Redis is the primary backend; in-memory fallback engages automatically
when Redis is unavailable (graceful degradation).

Justification: Legal AI platforms process high-value, sensitive data.
Rate limiting is defense-in-depth against:
  - Credential stuffing / brute force
  - Denial-of-service (volumetric and application-layer)
  - Cost explosion from runaway LLM API calls
  - Data exfiltration via high-frequency enumeration
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

logger = logging.getLogger("cyphergy.security.rate_limiter")


# ---------------------------------------------------------------------------
# Configuration (CPAA -- all from environment variables)
# ---------------------------------------------------------------------------

def _env_int(name: str, default: int) -> int:
    """Read an integer from env with a safe default."""
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float from env with a safe default."""
    try:
        return float(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting thresholds. All values sourced from env vars.

    Justification for defaults:
      - 100 req/min per IP: Standard API rate limit, prevents scraping
      - 300 req/min per user: Higher than IP because authenticated users
        may legitimately make burst requests (e.g., batch document analysis)
      - 1000 req/min per tenant: Aggregate cap prevents one firm from
        monopolizing capacity
      - 5000 req/min global: Circuit breaker threshold protects downstream
        services (LLM APIs, databases) from cascading failure
      - 60s windows: Standard sliding window for rate limiting
    """

    # Layer 1: Per-IP
    ip_max_requests: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_IP_MAX", 100)
    )
    ip_window_seconds: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_IP_WINDOW", 60)
    )

    # Layer 2: Per-User (after authentication)
    user_max_requests: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_USER_MAX", 300)
    )
    user_window_seconds: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_USER_WINDOW", 60)
    )

    # Layer 3: Per-Tenant (aggregate across all users in a tenant)
    tenant_max_requests: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_TENANT_MAX", 1000)
    )
    tenant_window_seconds: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_TENANT_WINDOW", 60)
    )

    # Layer 4: Global circuit breaker
    global_max_requests: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_GLOBAL_MAX", 5000)
    )
    global_window_seconds: int = field(
        default_factory=lambda: _env_int("RATE_LIMIT_GLOBAL_WINDOW", 60)
    )

    # Circuit breaker recovery time (seconds before retrying after trip)
    circuit_breaker_cooldown: float = field(
        default_factory=lambda: _env_float("RATE_LIMIT_CB_COOLDOWN", 30.0)
    )


# ---------------------------------------------------------------------------
# Rate Limit Result
# ---------------------------------------------------------------------------

@dataclass
class RateLimitResult:
    """Result of a rate limit check.

    Attributes:
        allowed: Whether the request should proceed.
        layer: Which layer denied the request (None if allowed).
        remaining: Approximate remaining requests in the current window.
        retry_after: Seconds until the client should retry (0 if allowed).
        message: Human-readable explanation for the client.
    """
    allowed: bool
    layer: Optional[str] = None
    remaining: int = 0
    retry_after: float = 0.0
    message: str = ""


# ---------------------------------------------------------------------------
# In-Memory Sliding Window Counter
# ---------------------------------------------------------------------------

class _SlidingWindowCounter:
    """Thread-safe sliding window rate counter.

    Justification for in-memory implementation: Redis is preferred in
    production for multi-instance deployments, but a single-process
    in-memory fallback ensures the service never runs without rate
    limiting -- even during Redis outages.

    Uses a simple sliding window approach: timestamps of recent requests
    are stored per key, and expired entries are pruned on each check.
    """

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Check if key is within limits and record the request.

        Returns:
            (allowed, remaining) -- whether the request is allowed and
            approximate remaining quota.
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            # Prune expired timestamps
            timestamps = self._windows[key]
            self._windows[key] = [t for t in timestamps if t > cutoff]
            timestamps = self._windows[key]

            current_count = len(timestamps)

            if current_count >= max_requests:
                remaining = 0
                return False, remaining

            # Record this request
            self._windows[key].append(now)
            remaining = max(0, max_requests - current_count - 1)
            return True, remaining

    def get_retry_after(self, key: str, window_seconds: int) -> float:
        """Calculate seconds until the oldest entry in the window expires.

        Justification: Giving clients an accurate Retry-After header
        prevents thundering herd retries and reduces unnecessary load.
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._windows.get(key, [])
            active = [t for t in timestamps if t > cutoff]
            if not active:
                return 0.0
            # Time until the oldest active entry expires
            oldest = min(active)
            return max(0.0, (oldest + window_seconds) - now)

    def reset(self, key: str) -> None:
        """Clear all entries for a key. Used in tests."""
        with self._lock:
            self._windows.pop(key, None)

    def reset_all(self) -> None:
        """Clear all rate limit state. Used in tests."""
        with self._lock:
            self._windows.clear()


# ---------------------------------------------------------------------------
# Redis Backend (optional, preferred in production)
# ---------------------------------------------------------------------------

class _RedisBackend:
    """Redis-backed sliding window using sorted sets.

    Justification: In multi-instance deployments (Kubernetes, ECS),
    in-memory counters are per-process and cannot enforce global limits.
    Redis provides a shared counter that works across all instances.

    Falls back to in-memory if Redis is unavailable.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: Optional[object] = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Redis. Fail silently for graceful degradation."""
        try:
            import redis
            self._client = redis.from_url(
                self._redis_url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                retry_on_timeout=False,
            )
            # Verify connection
            self._client.ping()  # type: ignore[union-attr]
            self._available = True
            logger.info("redis_connected | url=%s", _mask_url(self._redis_url))
        except Exception as exc:
            self._available = False
            logger.warning(
                "redis_unavailable | url=%s error=%s | falling back to in-memory",
                _mask_url(self._redis_url),
                type(exc).__name__,
            )

    @property
    def is_available(self) -> bool:
        return self._available

    def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Sorted-set sliding window in Redis.

        Each request is stored as a member with its timestamp as the score.
        Expired entries are removed via ZREMRANGEBYSCORE.
        """
        if not self._available or self._client is None:
            raise ConnectionError("Redis not available")

        import time as _time

        now = _time.time()
        window_start = now - window_seconds
        pipe_key = f"cyphergy:ratelimit:{key}"

        try:
            pipe = self._client.pipeline()  # type: ignore[union-attr]
            # Remove expired entries
            pipe.zremrangebyscore(pipe_key, 0, window_start)
            # Count current entries
            pipe.zcard(pipe_key)
            # Add current request
            pipe.zadd(pipe_key, {str(now): now})
            # Set expiry on the key to auto-cleanup
            pipe.expire(pipe_key, window_seconds + 1)
            results = pipe.execute()

            current_count = results[1]  # zcard result

            if current_count >= max_requests:
                return False, 0

            remaining = max(0, max_requests - current_count - 1)
            return True, remaining

        except Exception as exc:
            logger.warning(
                "redis_command_failed | key=%s error=%s | degrading to in-memory",
                key,
                type(exc).__name__,
            )
            self._available = False
            raise ConnectionError("Redis command failed") from exc


def _mask_url(url: str) -> str:
    """Mask credentials in a Redis URL for safe logging.

    Justification (@M:010): Never log secrets. Redis URLs may contain
    passwords (redis://:password@host:6379). We replace the password
    portion with [REDACTED].
    """
    if "@" in url:
        # Format: redis://:password@host:port or redis://user:password@host:port
        prefix, suffix = url.rsplit("@", 1)
        # Find the scheme
        if "://" in prefix:
            scheme, _ = prefix.split("://", 1)
            return f"{scheme}://[REDACTED]@{suffix}"
    return url


# ---------------------------------------------------------------------------
# Circuit Breaker (Layer 4)
# ---------------------------------------------------------------------------

class _CircuitBreaker:
    """Global circuit breaker to protect downstream services.

    Justification: If total request volume exceeds capacity, continuing
    to process requests risks cascading failure in LLM APIs, databases,
    and external legal data sources. The circuit breaker returns 503
    immediately, preserving system stability for requests already in flight.

    States:
      CLOSED  -- Normal operation, requests flow through.
      OPEN    -- Tripped, all requests rejected with 503.
      (Recovery is automatic after cooldown period.)
    """

    def __init__(self, max_requests: int, window_seconds: int, cooldown: float) -> None:
        self._counter = _SlidingWindowCounter()
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._cooldown = cooldown
        self._tripped_at: Optional[float] = None
        self._lock = Lock()

    @property
    def is_open(self) -> bool:
        """Check if the circuit breaker is currently open (rejecting requests)."""
        with self._lock:
            if self._tripped_at is None:
                return False
            elapsed = time.monotonic() - self._tripped_at
            if elapsed >= self._cooldown:
                # Cooldown expired -- close the circuit
                self._tripped_at = None
                self._counter.reset("global")
                logger.info("circuit_breaker_recovered | cooldown=%.1fs", self._cooldown)
                return False
            return True

    def check(self) -> tuple[bool, float]:
        """Check if a request can proceed through the circuit breaker.

        Returns:
            (allowed, retry_after)
        """
        if self.is_open:
            with self._lock:
                if self._tripped_at is not None:
                    remaining_cooldown = max(
                        0.0,
                        self._cooldown - (time.monotonic() - self._tripped_at),
                    )
                    return False, remaining_cooldown
                # Circuit recovered between is_open check and here
                pass

        allowed, _ = self._counter.check_and_increment(
            "global", self._max_requests, self._window_seconds
        )

        if not allowed:
            with self._lock:
                self._tripped_at = time.monotonic()
            logger.warning(
                "circuit_breaker_tripped | max=%d window=%ds cooldown=%.1fs",
                self._max_requests,
                self._window_seconds,
                self._cooldown,
            )
            return False, self._cooldown

        return True, 0.0

    def reset(self) -> None:
        """Reset the circuit breaker. Used in tests."""
        with self._lock:
            self._tripped_at = None
        self._counter.reset("global")


# ---------------------------------------------------------------------------
# RateLimiter (public API)
# ---------------------------------------------------------------------------

class RateLimiter:
    """4-layer rate limiter for the Cyphergy platform.

    Usage:
        limiter = RateLimiter()

        # In middleware or route handler:
        result = limiter.check_request(
            ip="203.0.113.42",
            user_id="usr_abc123",      # None if not authenticated
            tenant_id="tenant_xyz",     # None if not authenticated
        )

        if not result.allowed:
            return JSONResponse(
                status_code=429 if result.layer != "global" else 503,
                content={"error": result.message},
                headers={"Retry-After": str(int(result.retry_after))},
            )
    """

    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self._config = config or RateLimitConfig()

        # Try Redis first, fall back to in-memory
        redis_url = os.getenv("REDIS_URL", "")
        self._redis: Optional[_RedisBackend] = None
        if redis_url:
            self._redis = _RedisBackend(redis_url)

        # In-memory fallback (always initialized)
        self._memory = _SlidingWindowCounter()

        # Global circuit breaker (Layer 4)
        self._circuit_breaker = _CircuitBreaker(
            max_requests=self._config.global_max_requests,
            window_seconds=self._config.global_window_seconds,
            cooldown=self._config.circuit_breaker_cooldown,
        )

        logger.info(
            "rate_limiter_initialized | backend=%s ip_limit=%d/%ds "
            "user_limit=%d/%ds tenant_limit=%d/%ds global_limit=%d/%ds",
            "redis" if (self._redis and self._redis.is_available) else "in-memory",
            self._config.ip_max_requests,
            self._config.ip_window_seconds,
            self._config.user_max_requests,
            self._config.user_window_seconds,
            self._config.tenant_max_requests,
            self._config.tenant_window_seconds,
            self._config.global_max_requests,
            self._config.global_window_seconds,
        )

    def _check_layer(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Check a single rate limit layer, using Redis or in-memory.

        Justification for dual-backend: Redis provides cross-instance
        consistency but may be unavailable. In-memory ensures rate
        limiting is NEVER disabled -- defense must not have gaps.
        """
        if self._redis and self._redis.is_available:
            try:
                return self._redis.check_and_increment(key, max_requests, window_seconds)
            except ConnectionError:
                # Redis failed mid-request -- fall through to in-memory
                pass

        return self._memory.check_and_increment(key, max_requests, window_seconds)

    def check_request(
        self,
        ip: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> RateLimitResult:
        """Run all 4 rate limit layers in order.

        Layer evaluation order matters:
          1. Global circuit breaker first (cheapest check, protects everything)
          2. Per-IP (catches unauthenticated abuse)
          3. Per-User (prevents single-account abuse)
          4. Per-Tenant (prevents org-level resource monopolization)

        Returns a RateLimitResult with details about the decision.
        """
        # --- Layer 4: Global Circuit Breaker (checked first for efficiency) ---
        cb_allowed, cb_retry = self._circuit_breaker.check()
        if not cb_allowed:
            logger.warning("rate_limit_denied | layer=global ip=%s", ip)
            return RateLimitResult(
                allowed=False,
                layer="global",
                remaining=0,
                retry_after=cb_retry,
                message="Service temporarily unavailable. Please retry later.",
            )

        # --- Layer 1: Per-IP ---
        ip_key = f"ip:{ip}"
        ip_allowed, ip_remaining = self._check_layer(
            ip_key,
            self._config.ip_max_requests,
            self._config.ip_window_seconds,
        )
        if not ip_allowed:
            retry = self._memory.get_retry_after(
                ip_key, self._config.ip_window_seconds
            )
            logger.warning("rate_limit_denied | layer=ip ip=%s", ip)
            return RateLimitResult(
                allowed=False,
                layer="ip",
                remaining=0,
                retry_after=retry,
                message="Too many requests from this IP address.",
            )

        # --- Layer 2: Per-User (only if authenticated) ---
        user_remaining = self._config.user_max_requests
        if user_id:
            user_key = f"user:{user_id}"
            user_allowed, user_remaining = self._check_layer(
                user_key,
                self._config.user_max_requests,
                self._config.user_window_seconds,
            )
            if not user_allowed:
                retry = self._memory.get_retry_after(
                    user_key, self._config.user_window_seconds
                )
                logger.warning(
                    "rate_limit_denied | layer=user user_id=%s ip=%s",
                    user_id, ip,
                )
                return RateLimitResult(
                    allowed=False,
                    layer="user",
                    remaining=0,
                    retry_after=retry,
                    message="Too many requests for this user account.",
                )

        # --- Layer 3: Per-Tenant (only if tenant context is available) ---
        tenant_remaining = self._config.tenant_max_requests
        if tenant_id:
            tenant_key = f"tenant:{tenant_id}"
            tenant_allowed, tenant_remaining = self._check_layer(
                tenant_key,
                self._config.tenant_max_requests,
                self._config.tenant_window_seconds,
            )
            if not tenant_allowed:
                retry = self._memory.get_retry_after(
                    tenant_key, self._config.tenant_window_seconds
                )
                logger.warning(
                    "rate_limit_denied | layer=tenant tenant_id=%s ip=%s",
                    tenant_id, ip,
                )
                return RateLimitResult(
                    allowed=False,
                    layer="tenant",
                    remaining=0,
                    retry_after=retry,
                    message="Your organization has exceeded its request quota.",
                )

        # --- All layers passed ---
        # Return the minimum remaining across all applicable layers
        remaining = min(ip_remaining, user_remaining, tenant_remaining)
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            message="OK",
        )

    def reset_all(self) -> None:
        """Reset all rate limit state. Used in tests only."""
        self._memory.reset_all()
        self._circuit_breaker.reset()
