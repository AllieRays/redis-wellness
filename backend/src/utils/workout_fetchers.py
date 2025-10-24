"""
Workout Data Fetching Utilities.

Pure functions for fetching and filtering workout data from Redis.
These eliminate duplication across query tools by providing a centralized
workout fetching interface.

Similar to metric_aggregators.py for health records, this module provides
workout-specific data fetching with flexible filtering options.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ..services.redis_apple_health_manager import redis_manager
from ..services.redis_workout_indexer import WorkoutIndexer

logger = logging.getLogger(__name__)

# Global indexer instance
_indexer = None


def get_indexer() -> WorkoutIndexer:
    """Get or create workout indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = WorkoutIndexer()
    return _indexer


def fetch_workouts_from_redis(
    user_id: str,
    days_back: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    use_indexes: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch and filter workouts from Redis.

    Automatically uses Redis indexes when available for 50-100x speedup.
    Falls back to JSON parsing if indexes don't exist.

    Provides flexible filtering by either days_back or explicit date ranges.
    All datetime comparisons are done in UTC.

    Args:
        user_id: User identifier
        days_back: Filter to last N days from now (if provided)
        start_date: Filter from this date (inclusive, if provided)
        end_date: Filter to this date (exclusive, if provided)
        use_indexes: Try Redis indexes first (default: True)

    Returns:
        List of workout dictionaries matching filters. Empty list if no data found.

    Examples:
        # Last 60 days (uses Redis indexes if available)
        workouts = fetch_workouts_from_redis(user_id, days_back=60)

        # Specific date range
        workouts = fetch_workouts_from_redis(
            user_id,
            start_date=datetime(2025, 9, 1, tzinfo=UTC),
            end_date=datetime(2025, 10, 1, tzinfo=UTC)
        )

        # All workouts (no filtering)
        workouts = fetch_workouts_from_redis(user_id)
    """
    try:
        indexer = get_indexer()

        # Try fast path with Redis indexes first
        if use_indexes and indexer.index_exists(user_id):
            logger.debug(f"Using Redis indexes for {user_id}")

            # Calculate time range
            if days_back is not None:
                start_timestamp = (
                    datetime.now(UTC) - timedelta(days=days_back)
                ).timestamp()
                end_timestamp = datetime.now(UTC).timestamp()
            elif start_date is not None:
                start_timestamp = start_date.timestamp()
                end_timestamp = (
                    end_date.timestamp() if end_date else datetime.now(UTC).timestamp()
                )
            else:
                # No filtering - get all workouts
                # This is slower with indexes, so fall back to JSON
                logger.debug("No filtering requested, using JSON")
                use_indexes = False

            if use_indexes:
                # Get workout IDs from sorted set (O(log N))
                workout_ids = indexer.get_workouts_in_date_range(
                    user_id, start_timestamp, end_timestamp
                )

                # Fetch details from hashes (batch operation)
                workouts = indexer.get_workout_details(user_id, workout_ids)

                logger.debug(f"Redis indexes returned {len(workouts)} workouts")

                # If indexes returned 0 results, fall back to JSON to verify
                # (indexes might be stale or not fully built)
                if len(workouts) == 0:
                    logger.warning(
                        "Redis indexes returned 0 workouts. "
                        "Falling back to JSON parsing to verify."
                    )
                    use_indexes = False  # Force fallback to JSON below
                else:
                    return workouts

        # Fallback: Parse JSON (slower but always works)
        logger.debug(f"Using JSON parsing for {user_id}")

        with redis_manager.redis_manager.get_connection() as redis_client:
            main_key = f"health:user:{user_id}:data"
            health_data_json = redis_client.get(main_key)

            if not health_data_json:
                logger.debug(f"No health data found for user {user_id}")
                return []

            health_data = json.loads(health_data_json)
            all_workouts = health_data.get("workouts", [])

            # No filtering requested - return all
            if days_back is None and start_date is None and end_date is None:
                return all_workouts

            # Calculate cutoff date if days_back provided
            cutoff_date = None
            if days_back is not None:
                cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
            elif start_date is not None:
                cutoff_date = start_date

            # Filter workouts by date range
            filtered_workouts = []
            for workout in all_workouts:
                start_date_str = workout.get("startDate", "")
                if not start_date_str:
                    continue

                try:
                    # Parse workout date (ISO format with timezone)
                    workout_date = datetime.fromisoformat(
                        start_date_str.replace("Z", "+00:00")
                    )

                    # Ensure UTC for comparison
                    if workout_date.tzinfo is None:
                        workout_date = workout_date.replace(tzinfo=UTC)

                    # Apply filters
                    if cutoff_date and workout_date < cutoff_date:
                        continue
                    if end_date and workout_date >= end_date:
                        continue

                    filtered_workouts.append(workout)

                except (ValueError, AttributeError) as e:
                    logger.debug(f"Skipping workout with invalid date: {e}")
                    continue

            return filtered_workouts

    except Exception as e:
        logger.error(f"Error fetching workouts from Redis: {e}", exc_info=True)
        return []


def fetch_workouts_in_range(
    user_id: str, start_date: datetime, end_date: datetime
) -> list[dict[str, Any]]:
    """
    Fetch workouts within a specific date range.

    Convenience wrapper around fetch_workouts_from_redis for explicit ranges.

    Args:
        user_id: User identifier
        start_date: Start of range (inclusive)
        end_date: End of range (exclusive)

    Returns:
        List of workout dictionaries in the date range

    Example:
        # Get September 2025 workouts
        workouts = fetch_workouts_in_range(
            user_id,
            datetime(2025, 9, 1, tzinfo=UTC),
            datetime(2025, 10, 1, tzinfo=UTC)
        )
    """
    return fetch_workouts_from_redis(
        user_id=user_id, start_date=start_date, end_date=end_date
    )


def fetch_recent_workouts(user_id: str, days: int = 30) -> list[dict[str, Any]]:
    """
    Fetch workouts from the last N days.

    Convenience wrapper around fetch_workouts_from_redis for recent queries.
    Uses Redis indexes for 50-100x speedup when available.

    Args:
        user_id: User identifier
        days: Number of days to look back (default 30)

    Returns:
        List of workout dictionaries from the last N days

    Example:
        # Get last 60 days of workouts
        workouts = fetch_recent_workouts(user_id, days=60)
    """
    return fetch_workouts_from_redis(user_id=user_id, days_back=days)


def get_workout_count(
    user_id: str,
    days_back: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """
    Get count of workouts matching filter criteria.

    Convenience function that fetches and counts in one call.

    Args:
        user_id: User identifier
        days_back: Filter to last N days (if provided)
        start_date: Filter from this date (if provided)
        end_date: Filter to this date (if provided)

    Returns:
        Number of workouts matching criteria

    Example:
        # How many workouts in last 30 days?
        count = get_workout_count(user_id, days_back=30)
    """
    workouts = fetch_workouts_from_redis(
        user_id=user_id, days_back=days_back, start_date=start_date, end_date=end_date
    )
    return len(workouts)
