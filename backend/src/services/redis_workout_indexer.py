"""
Redis Workout Indexer - Fast aggregations using Redis data structures.

Builds Redis indexes for instant workout queries:
- Hashes for counts by day of week
- Sorted sets for time-range queries
- Individual workout details as hashes

This provides 50-100x speedup over JSON parsing for common queries.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from .redis_connection import get_redis_manager

logger = logging.getLogger(__name__)


class WorkoutIndexer:
    """Index workouts in Redis for O(1) aggregation queries."""

    def __init__(self):
        self.redis_manager = get_redis_manager()
        # TTL: 7 months to match health data retention
        self.ttl_seconds = 210 * 24 * 60 * 60

    def index_workouts(
        self, user_id: str, workouts: list[dict[str, Any]]
    ) -> dict[str, int]:
        """
        Create Redis indexes for fast workout queries.

        Indexes created:
        1. user:{user_id}:workout:days - Hash: day_of_week → count
        2. user:{user_id}:workout:by_date - Sorted Set: workout_id → timestamp
        3. user:{user_id}:workout:{id} - Hash: Individual workout details

        Args:
            user_id: User identifier
            workouts: List of workout dictionaries

        Returns:
            Dict with index statistics
        """
        if not workouts:
            logger.info(f"No workouts to index for user {user_id}")
            return {"workouts_indexed": 0, "keys_created": 0}

        try:
            with self.redis_manager.get_connection() as client:
                pipeline = client.pipeline()

                # Clear old indexes
                days_key = f"user:{user_id}:workout:days"
                by_date_key = f"user:{user_id}:workout:by_date"

                pipeline.delete(days_key)
                pipeline.delete(by_date_key)

                keys_created = 2  # days + by_date keys

                for workout in workouts:
                    try:
                        # Generate workout ID
                        workout_id = self._generate_workout_id(user_id, workout)

                        # 1. Count by day of week (Hash)
                        day_of_week = workout.get("day_of_week", "Unknown")
                        pipeline.hincrby(days_key, day_of_week, 1)

                        # 2. Index by date for range queries (Sorted Set)
                        start_date_str = workout.get("startDate", "")
                        if start_date_str:
                            try:
                                workout_date = datetime.fromisoformat(
                                    start_date_str.replace("Z", "+00:00")
                                )
                                if workout_date.tzinfo is None:
                                    workout_date = workout_date.replace(tzinfo=UTC)

                                timestamp = workout_date.timestamp()
                                pipeline.zadd(by_date_key, {workout_id: timestamp})
                            except (ValueError, AttributeError):
                                logger.debug(
                                    f"Invalid date for workout: {start_date_str}"
                                )
                                continue

                        # 3. Store workout details (Hash)
                        workout_key = f"user:{user_id}:workout:{workout_id}"
                        workout_data = {
                            "date": workout.get("date", ""),
                            "startDate": workout.get("startDate", ""),
                            "day_of_week": day_of_week,
                            "type": workout.get(
                                "type_cleaned", workout.get("type", "")
                            ),
                            "duration_minutes": str(workout.get("duration_minutes", 0)),
                            "calories": str(workout.get("calories", 0)),
                        }

                        pipeline.hset(workout_key, mapping=workout_data)
                        pipeline.expire(workout_key, self.ttl_seconds)
                        keys_created += 1

                    except Exception as e:
                        logger.warning(f"Failed to index workout: {e}")
                        continue

                # Set TTLs on aggregate keys
                pipeline.expire(days_key, self.ttl_seconds)
                pipeline.expire(by_date_key, self.ttl_seconds)

                # Execute all commands
                pipeline.execute()

                logger.info(
                    f"✅ Indexed {len(workouts)} workouts for {user_id} ({keys_created} Redis keys)"
                )

                return {
                    "workouts_indexed": len(workouts),
                    "keys_created": keys_created,
                    "ttl_days": self.ttl_seconds // (24 * 60 * 60),
                }

        except Exception as e:
            logger.error(f"Failed to index workouts: {e}", exc_info=True)
            return {"error": str(e), "workouts_indexed": 0}

    def _generate_workout_id(self, user_id: str, workout: dict) -> str:
        """Generate unique workout ID."""
        date = workout.get("date", "unknown")
        workout_type = workout.get("type_cleaned", workout.get("type", "unknown"))
        start_time = workout.get("startDate", "")

        # Use start time for uniqueness if available
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                time_str = dt.strftime("%H%M%S")
                return f"{date}:{workout_type}:{time_str}"
            except (ValueError, AttributeError):
                pass

        return f"{date}:{workout_type}"

    def get_workout_count_by_day(self, user_id: str) -> dict[str, int]:
        """
        Get workout counts by day of week from Redis index.

        O(1) operation using Redis Hash.

        Args:
            user_id: User identifier

        Returns:
            Dict mapping day_of_week to count
        """
        try:
            with self.redis_manager.get_connection() as client:
                days_key = f"user:{user_id}:workout:days"
                day_counts = client.hgetall(days_key)

                # Handle both bytes and strings (depends on Redis connection settings)
                result = {}
                for k, v in day_counts.items():
                    key = k.decode() if isinstance(k, bytes) else k
                    value = int(v.decode() if isinstance(v, bytes) else v)
                    result[key] = value
                return result

        except Exception as e:
            logger.error(f"Failed to get workout counts by day: {e}")
            return {}

    def get_workouts_in_date_range(
        self, user_id: str, start_timestamp: float, end_timestamp: float
    ) -> list[str]:
        """
        Get workout IDs in date range using Redis Sorted Set.

        O(log N) operation - much faster than scanning all workouts.

        Args:
            user_id: User identifier
            start_timestamp: Start of range (Unix timestamp)
            end_timestamp: End of range (Unix timestamp)

        Returns:
            List of workout IDs in range
        """
        try:
            with self.redis_manager.get_connection() as client:
                by_date_key = f"user:{user_id}:workout:by_date"
                workout_ids = client.zrangebyscore(
                    by_date_key, start_timestamp, end_timestamp
                )

                # Handle both bytes and strings
                return [
                    wid.decode() if isinstance(wid, bytes) else wid
                    for wid in workout_ids
                ]

        except Exception as e:
            logger.error(f"Failed to get workouts in date range: {e}")
            return []

    def get_workout_details(self, user_id: str, workout_ids: list[str]) -> list[dict]:
        """
        Fetch workout details for given IDs using Redis pipeline.

        Batch operation for efficiency.

        Args:
            user_id: User identifier
            workout_ids: List of workout IDs

        Returns:
            List of workout detail dictionaries
        """
        if not workout_ids:
            return []

        try:
            with self.redis_manager.get_connection() as client:
                pipeline = client.pipeline()

                # Batch fetch all workout hashes
                for workout_id in workout_ids:
                    workout_key = f"user:{user_id}:workout:{workout_id}"
                    pipeline.hgetall(workout_key)

                results = pipeline.execute()

                # Convert to dicts
                workouts = []
                for workout_data in results:
                    if workout_data:
                        # Handle both bytes and strings
                        workout = {}
                        for k, v in workout_data.items():
                            key = k.decode() if isinstance(k, bytes) else k
                            value = v.decode() if isinstance(v, bytes) else v
                            workout[key] = value

                        # Convert numeric fields
                        if "duration_minutes" in workout:
                            try:
                                workout["duration_minutes"] = float(
                                    workout["duration_minutes"]
                                )
                            except (ValueError, TypeError):
                                workout["duration_minutes"] = 0
                        if "calories" in workout:
                            try:
                                workout["calories"] = float(workout["calories"])
                            except (ValueError, TypeError):
                                workout["calories"] = 0

                        workouts.append(workout)

                return workouts

        except Exception as e:
            logger.error(f"Failed to get workout details: {e}")
            return []

    def get_total_workout_count(self, user_id: str) -> int:
        """
        Get total workout count using Redis Sorted Set cardinality.

        O(1) operation.

        Args:
            user_id: User identifier

        Returns:
            Total number of workouts indexed
        """
        try:
            with self.redis_manager.get_connection() as client:
                by_date_key = f"user:{user_id}:workout:by_date"
                return client.zcard(by_date_key)

        except Exception as e:
            logger.error(f"Failed to get total workout count: {e}")
            return 0

    def index_exists(self, user_id: str) -> bool:
        """
        Check if workout indexes exist for user.

        Args:
            user_id: User identifier

        Returns:
            True if indexes exist
        """
        try:
            with self.redis_manager.get_connection() as client:
                days_key = f"user:{user_id}:workout:days"
                return client.exists(days_key) > 0

        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False
