"""
Redis Connection Manager with pooling and circuit breaker pattern.

Provides production-ready Redis connections with:
- Connection pooling for performance
- Circuit breaker for resilience
- Automatic retry logic
- Health monitoring
"""

import logging
import os
import time
from contextlib import contextmanager
from enum import Enum

import redis
from redis.connection import ConnectionPool

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class RedisCircuitBreaker:
    """Circuit breaker for Redis operations."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        # HALF_OPEN state - allow one attempt
        return True

    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.info("Redis circuit breaker reset to CLOSED")

    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Redis circuit breaker OPEN after {self.failure_count} failures"
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout


class RedisConnectionManager:
    """
    Production-ready Redis connection manager.

    Features:
    - Connection pooling for performance
    - Circuit breaker for resilience
    - Health monitoring
    - Automatic retry logic
    """

    def __init__(self):
        self._pool: ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self.circuit_breaker = RedisCircuitBreaker()
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize Redis connection pool."""
        try:
            # Connection pool configuration
            pool_config = {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", 6379)),
                "db": int(os.getenv("REDIS_DB", 0)),
                "decode_responses": True,
                "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", 20)),
                "retry_on_timeout": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "health_check_interval": 30,
            }

            # Add password if provided
            redis_password = os.getenv("REDIS_PASSWORD")
            if redis_password:
                pool_config["password"] = redis_password

            # Create connection pool
            self._pool = ConnectionPool(**pool_config)
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            self._client.ping()
            logger.info("Redis connection pool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {str(e)}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for getting Redis connections with circuit breaker.

        Usage:
            with redis_manager.get_connection() as redis_client:
                redis_client.set("key", "value")
        """
        if not self.circuit_breaker.can_execute():
            raise redis.ConnectionError("Redis circuit breaker is OPEN")

        try:
            if not self._client:
                self._initialize_connection()

            yield self._client
            self.circuit_breaker.record_success()

        except redis.RedisError as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Redis operation failed: {str(e)}")
            raise
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Unexpected Redis error: {str(e)}")
            raise

    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if not self.circuit_breaker.can_execute():
                return False

            with self.get_connection() as redis_client:
                redis_client.ping()
                return True

        except Exception:
            return False

    def get_pool_info(self) -> dict:
        """Get connection pool information for monitoring."""
        if not self._pool:
            return {"error": "Pool not initialized"}

        return {
            "created_connections": self._pool.created_connections,
            "available_connections": len(self._pool._available_connections),
            "in_use_connections": len(self._pool._in_use_connections),
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
        }

    def close(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection pool closed")


# Global connection manager instance
redis_connection_manager = RedisConnectionManager()


def get_redis_manager() -> RedisConnectionManager:
    """Get the global Redis connection manager."""
    return redis_connection_manager
