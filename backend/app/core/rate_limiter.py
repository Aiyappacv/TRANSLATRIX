"""
Rate Limiter
Redis-based rate limiting for API endpoints
"""
from typing import Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Redis-based rate limiter"""

    def __init__(self, redis_client=None):
        """
        Initialize rate limiter

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit

        Args:
            key: Rate limit key (e.g., user_id, ip_address)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not self.redis:
            # If Redis not available, allow request
            return True, None

        try:
            current_time = datetime.utcnow()
            window_key = f"rate_limit:{key}:{window_seconds}"

            # Get current count
            current_count = self.redis.get(window_key)

            if current_count is None:
                # First request in this window
                self.redis.setex(window_key, window_seconds, 1)
                return True, None

            current_count = int(current_count)

            if current_count >= max_requests:
                # Rate limit exceeded
                ttl = self.redis.ttl(window_key)
                logger.warning(
                    "rate_limit_exceeded",
                    key=key,
                    max_requests=max_requests,
                    window=window_seconds
                )
                return False, ttl

            # Increment counter
            self.redis.incr(window_key)
            return True, None

        except Exception as e:
            logger.error("rate_limit_check_failed", error=str(e))
            # On error, allow request
            return True, None

    def check_tenant_rate_limit(
        self,
        tenant_id: str,
        max_requests_per_minute: int = 60,
        max_requests_per_hour: int = 1000
    ) -> tuple[bool, Optional[int]]:
        """
        Check tenant-level rate limits

        Args:
            tenant_id: Tenant ID
            max_requests_per_minute: Max requests per minute
            max_requests_per_hour: Max requests per hour

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        # Check minute limit
        allowed, retry_after = self.check_rate_limit(
            key=f"tenant:{tenant_id}",
            max_requests=max_requests_per_minute,
            window_seconds=60
        )

        if not allowed:
            return False, retry_after

        # Check hour limit
        allowed, retry_after = self.check_rate_limit(
            key=f"tenant:{tenant_id}",
            max_requests=max_requests_per_hour,
            window_seconds=3600
        )

        return allowed, retry_after

    def check_user_rate_limit(
        self,
        user_id: str,
        max_requests_per_minute: int = 30
    ) -> tuple[bool, Optional[int]]:
        """
        Check user-level rate limits

        Args:
            user_id: User ID
            max_requests_per_minute: Max requests per minute

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        return self.check_rate_limit(
            key=f"user:{user_id}",
            max_requests=max_requests_per_minute,
            window_seconds=60
        )


# Global rate limiter instance (initialized in main.py)
rate_limiter = RateLimiter()
