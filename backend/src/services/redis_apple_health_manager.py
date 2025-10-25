"""
Redis Health Tool for AI Agents.

Provides Redis-powered health data storage and retrieval with TTL-based
short-term memory, demonstrating advantages over stateless approaches.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import redis

from ..config import get_settings
from ..utils.base import (
    HealthDataValidator,
    ToolError,
    ToolResult,
    create_error_result,
    create_success_result,
    measure_execution_time,
    performance_tracker,
)
from ..utils.redis_keys import RedisKeys
from .redis_connection import get_redis_manager


class RedisHealthManager:
    """
    Manages health data in Redis with TTL-based memory management.

    Demonstrates Redis advantages:
    - Automatic TTL expiration (7 months default)
    - Fast O(1) lookups vs O(n) file parsing
    - Conversational memory persistence
    - Real-time aggregations
    """

    def __init__(self):
        # Use production-ready connection manager
        self.redis_manager = get_redis_manager()

        # Get settings for TTL configuration
        self.settings = get_settings()

        # TTL settings (7 months for long-term memory)
        self.default_ttl_seconds = self.settings.redis_health_data_ttl_seconds

    def store_health_data(
        self, user_id: str, health_data: dict[str, Any], ttl_days: int = 210
    ) -> dict[str, Any]:
        """Store parsed health data permanently with optional TTL for indices."""
        try:
            ttl_seconds = ttl_days * 24 * 60 * 60

            with self.redis_manager.get_connection() as redis_client:
                # Store main health data collection WITHOUT TTL (permanent)
                main_key = RedisKeys.health_data(user_id)
                redis_client.set(main_key, json.dumps(health_data))

                # Store quick lookup indices with TTL
                indices_stored = self._create_indices(
                    redis_client, user_id, health_data, ttl_seconds
                )

                # Store conversation context WITHOUT TTL (permanent)
                context_key = RedisKeys.health_context(user_id)
                conversation_context = health_data.get("conversation_context", "")
                redis_client.set(context_key, conversation_context)

                # Track storage metrics
                storage_info = {
                    "user_id": user_id,
                    "main_key": main_key,
                    "indices_count": indices_stored,
                    "health_data_ttl": "permanent",
                    "indices_ttl_days": ttl_days,
                    "indices_expire_at": (
                        datetime.now(UTC) + timedelta(days=ttl_days)
                    ).isoformat(),
                    "redis_keys_created": indices_stored
                    + 2,  # main + context + indices
                }

                return storage_info

        except redis.RedisError as e:
            raise ToolError(f"Redis storage failed: {str(e)}", "REDIS_ERROR") from e

    def _create_indices(
        self, redis_client, user_id: str, health_data: dict[str, Any], ttl_seconds: int
    ) -> int:
        """Create Redis indices for fast metric queries."""
        indices_count = 0

        # Index by metric type for fast queries
        metrics_summary = health_data.get("metrics_summary", {})
        for metric_type, data in metrics_summary.items():
            key = RedisKeys.health_metric(user_id, metric_type)
            redis_client.setex(key, ttl_seconds, json.dumps(data))
            indices_count += 1

        # Index recent insights with TTL (key Redis advantage)
        recent_key = RedisKeys.health_recent_insights(user_id)
        recent_insights = {
            "record_count": health_data.get("record_count", 0),
            "data_categories": health_data.get("data_categories", []),
            "date_range": health_data.get("date_range", {}),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        redis_client.setex(recent_key, ttl_seconds, json.dumps(recent_insights))
        indices_count += 1

        return indices_count


# Global Redis manager instance
redis_manager = RedisHealthManager()


@measure_execution_time
def store_health_data(
    user_id: str, health_data: dict[str, Any], ttl_days: int = 210
) -> ToolResult:
    """
    Store parsed health data in Redis permanently with temporary indices.

    Health data (BMI, weight, etc.) is stored permanently for reliable access.
    Only temporary indices have TTL for long-term memory management.

    Args:
        user_id: Unique user identifier
        health_data: Parsed health data from parse_health_file tool
        ttl_days: TTL for temporary indices only (1-365, default: 210 = 7 months)

    Returns:
        ToolResult with storage information and TTL details for indices
    """
    try:
        # Validate inputs
        if not HealthDataValidator.validate_user_id(user_id):
            return create_error_result("Invalid user ID format", "INVALID_USER_ID")

        if ttl_days < 1 or ttl_days > 365:
            return create_error_result(
                "TTL must be between 1 and 365 days", "INVALID_TTL"
            )

        # Start performance tracking
        performance_tracker.start_operation("store_data", "redis")

        # Store data with TTL
        storage_info = redis_manager.store_health_data(user_id, health_data, ttl_days)

        # End performance tracking
        performance_tracker.end_operation("store_data", "redis", success=True)

        return create_success_result(
            storage_info,
            f"Health data stored permanently (indices expire in {ttl_days} days / ~{ttl_days // 30} months)",
        )

    except ToolError:
        performance_tracker.end_operation("store_data", "redis", success=False)
        raise
    except Exception:
        performance_tracker.end_operation("store_data", "redis", success=False)
        return create_error_result("Failed to store health data", "STORAGE_ERROR")
