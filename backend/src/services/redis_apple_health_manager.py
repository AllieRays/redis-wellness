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
                main_key = f"health:user:{user_id}:data"
                redis_client.set(main_key, json.dumps(health_data))

                # Store quick lookup indices with TTL
                indices_stored = self._create_indices(
                    redis_client, user_id, health_data, ttl_seconds
                )

                # Store conversation context WITHOUT TTL (permanent)
                context_key = f"health:user:{user_id}:context"
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
            key = f"health:user:{user_id}:metric:{metric_type}"
            redis_client.setex(key, ttl_seconds, json.dumps(data))
            indices_count += 1

        # Index recent insights with TTL (key Redis advantage)
        recent_key = f"health:user:{user_id}:recent_insights"
        recent_insights = {
            "record_count": health_data.get("record_count", 0),
            "data_categories": health_data.get("data_categories", []),
            "date_range": health_data.get("date_range", {}),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        redis_client.setex(recent_key, ttl_seconds, json.dumps(recent_insights))
        indices_count += 1

        return indices_count

    def query_health_metrics(
        self, user_id: str, metric_types: list[str]
    ) -> dict[str, Any]:
        """Fast Redis-based metric queries (O(1) vs O(n) file parsing)."""
        try:
            results = {}
            cache_hits = 0

            for metric_type in metric_types:
                key = f"health:user:{user_id}:metric:{metric_type}"
                data = self.redis.get(key)

                if data:
                    results[metric_type] = json.loads(data)
                    cache_hits += 1
                else:
                    results[metric_type] = {"error": "No data found or expired"}

            # Get TTL info to show memory management
            ttl_info = {}
            for metric_type in metric_types:
                key = f"health:user:{user_id}:metric:{metric_type}"
                ttl = self.redis.ttl(key)
                ttl_info[metric_type] = {
                    "ttl_seconds": ttl,
                    "expires_at": (
                        (datetime.now(UTC) + timedelta(seconds=ttl)).isoformat()
                        if ttl > 0
                        else None
                    ),
                }

            return {
                "metrics": results,
                "cache_hits": cache_hits,
                "total_requested": len(metric_types),
                "cache_hit_ratio": (
                    cache_hits / len(metric_types) if metric_types else 0
                ),
                "ttl_info": ttl_info,
            }

        except redis.RedisError as e:
            raise ToolError(f"Redis query failed: {str(e)}", "REDIS_ERROR") from e

    def get_conversation_context(self, user_id: str) -> str | None:
        """Get health-aware conversation context from Redis."""
        try:
            context_key = f"health:user:{user_id}:context"
            context = self.redis.get(context_key)

            # Also get TTL for context expiration info
            ttl = self.redis.ttl(context_key)

            return {
                "context": context,
                "ttl_seconds": ttl,
                "expires_at": (
                    (datetime.now(UTC) + timedelta(seconds=ttl)).isoformat()
                    if ttl > 0
                    else None
                ),
            }

        except redis.RedisError:
            return None

    def cleanup_expired_data(self, user_id: str) -> dict[str, Any]:
        """Manual cleanup demo (Redis TTL makes this unnecessary)."""
        try:
            # Find all user keys (for demo purposes)
            pattern = f"health:user:{user_id}:*"
            keys = self.redis.keys(pattern)

            expired_keys = []
            active_keys = []

            for key in keys:
                ttl = self.redis.ttl(key)
                if ttl <= 0:  # Expired or no TTL
                    expired_keys.append(key)
                else:
                    active_keys.append(key)

            return {
                "total_keys": len(keys),
                "active_keys": len(active_keys),
                "expired_keys": len(expired_keys),
                "redis_auto_cleanup": "TTL handles expiration automatically",
                "manual_cleanup_needed": False,
            }

        except redis.RedisError as e:
            raise ToolError(
                f"Redis cleanup check failed: {str(e)}", "REDIS_ERROR"
            ) from e


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


@measure_execution_time
def query_health_metrics(
    user_id: str, metric_types: list[str], days_back: int = 30
) -> ToolResult:
    """
    Query specific health metrics from Redis for conversation context.

    Demonstrates Redis's O(1) lookup speed vs O(n) file parsing for
    providing immediate health context in AI conversations.

    Args:
        user_id: Unique user identifier
        metric_types: List of metric types to query (e.g., ['BodyMassIndex', 'DietaryWater'])
        days_back: Number of days to look back (for future enhancement)

    Returns:
        ToolResult with requested metrics and performance info
    """
    try:
        # Validate inputs
        if not HealthDataValidator.validate_user_id(user_id):
            return create_error_result("Invalid user ID format", "INVALID_USER_ID")

        if not HealthDataValidator.validate_metric_types(metric_types):
            return create_error_result(
                "Invalid metric types requested", "INVALID_METRICS"
            )

        # Start performance tracking
        performance_tracker.start_operation("query_metrics", "redis")

        # Query Redis for metrics
        query_results = redis_manager.query_health_metrics(user_id, metric_types)

        # End performance tracking
        performance_tracker.end_operation("query_metrics", "redis", success=True)

        # Add Redis advantages info for demo
        demo_info = {
            "redis_advantages": {
                "lookup_speed": "O(1) constant time",
                "automatic_ttl": "7-month expiration without manual cleanup",
                "cache_hit_ratio": query_results["cache_hit_ratio"],
                "memory_efficient": "Only active data in memory",
            }
        }

        query_results.update(demo_info)

        return create_success_result(
            query_results,
            f"Retrieved {query_results['cache_hits']}/{len(metric_types)} metrics from Redis cache",
        )

    except ToolError:
        performance_tracker.end_operation("query_metrics", "redis", success=False)
        raise
    except Exception:
        performance_tracker.end_operation("query_metrics", "redis", success=False)
        return create_error_result("Failed to query health metrics", "QUERY_ERROR")


@measure_execution_time
def get_health_conversation_context(user_id: str) -> ToolResult:
    """
    Get health-aware conversation context from Redis short-term memory.

    This tool provides AI agents with relevant health context that persists
    across conversation sessions, demonstrating Redis's memory advantages.

    Args:
        user_id: Unique user identifier

    Returns:
        ToolResult with conversation context and TTL information
    """
    try:
        if not HealthDataValidator.validate_user_id(user_id):
            return create_error_result("Invalid user ID format", "INVALID_USER_ID")

        # Get conversation context from Redis
        context_info = redis_manager.get_conversation_context(user_id)

        if not context_info or not context_info.get("context"):
            return create_error_result(
                "No conversation context found or expired", "NO_CONTEXT"
            )

        return create_success_result(
            context_info, "Retrieved health conversation context from Redis memory"
        )

    except Exception:
        return create_error_result(
            "Failed to retrieve conversation context", "CONTEXT_ERROR"
        )
