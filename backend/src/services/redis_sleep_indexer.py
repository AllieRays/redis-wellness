"""
Redis Sleep Indexer - Fast sleep aggregations using Redis data structures.

Builds Redis indexes for instant sleep queries:
- Hashes for daily sleep summaries (hours, efficiency)
- Sorted sets for time-range queries
- Individual sleep nights as hashes

This provides 50-100x speedup over JSON parsing for sleep queries.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from ..utils.redis_keys import RedisKeys
from ..utils.sleep_aggregator import (
    aggregate_sleep_by_date,
    parse_sleep_segments_from_records,
)
from .redis_connection import get_redis_manager

logger = logging.getLogger(__name__)


class SleepIndexer:
    """Index sleep data in Redis for O(1) aggregation queries."""

    def __init__(self):
        self.redis_manager = get_redis_manager()
        # TTL: 7 months to match health data retention
        self.ttl_seconds = 210 * 24 * 60 * 60

    def index_sleep_data(
        self, user_id: str, sleep_records: list[dict[str, Any]]
    ) -> dict[str, int | str]:
        """
        Create Redis indexes for fast sleep queries.

        Indexes created:
        1. user:{user_id}:sleep:by_date - Sorted Set: date → timestamp
        2. user:{user_id}:sleep:{date} - Hash: Daily sleep summary

        Args:
            user_id: User identifier
            sleep_records: List of sleep record dictionaries

        Returns:
            Dict with index statistics
        """
        if not sleep_records:
            logger.info(f"No sleep data to index for user {user_id}")
            return {"nights_indexed": 0, "keys_created": 0}

        try:
            # Parse and aggregate sleep segments
            sleep_segments = parse_sleep_segments_from_records(sleep_records)
            sleep_summaries = aggregate_sleep_by_date(sleep_segments)

            if not sleep_summaries:
                logger.info(f"No sleep summaries generated for user {user_id}")
                return {"nights_indexed": 0, "keys_created": 0}

            with self.redis_manager.get_connection() as client:
                pipeline = client.pipeline()

                # Clear old indexes
                by_date_key = RedisKeys.sleep_by_date(user_id)
                pipeline.delete(by_date_key)

                keys_created = 1  # by_date key

                for summary in sleep_summaries:
                    try:
                        # 1. Index by date for range queries (Sorted Set)
                        date_obj = datetime.fromisoformat(summary.date).replace(
                            tzinfo=UTC
                        )
                        timestamp = date_obj.timestamp()
                        pipeline.zadd(by_date_key, {summary.date: timestamp})

                        # 2. Store daily sleep summary (Hash)
                        sleep_key = RedisKeys.sleep_detail(user_id, summary.date)
                        sleep_data = {
                            "date": summary.date,
                            "sleep_hours": str(summary.total_sleep_hours),
                            "in_bed_hours": str(summary.total_in_bed_hours),
                            "sleep_efficiency": str(summary.sleep_efficiency or 0),
                            "bedtime": summary.first_sleep_time or "",
                            "wake_time": summary.last_wake_time or "",
                            "deep_sleep_hours": str(summary.deep_sleep_hours or 0),
                            "rem_sleep_hours": str(summary.rem_sleep_hours or 0),
                            "core_sleep_hours": str(summary.core_sleep_hours or 0),
                            "awake_hours": str(summary.awake_hours or 0),
                            "segment_count": str(summary.segment_count),
                        }

                        pipeline.hset(sleep_key, mapping=sleep_data)
                        pipeline.expire(sleep_key, self.ttl_seconds)
                        keys_created += 1

                    except Exception as e:
                        logger.warning(f"Failed to index sleep for {summary.date}: {e}")
                        continue

                # Set TTL on sorted set
                pipeline.expire(by_date_key, self.ttl_seconds)

                # Execute all commands
                pipeline.execute()

                logger.info(
                    f"✅ Indexed {len(sleep_summaries)} nights of sleep for {user_id} ({keys_created} Redis keys)"
                )

                return {
                    "nights_indexed": len(sleep_summaries),
                    "keys_created": keys_created,
                    "ttl_days": self.ttl_seconds // (24 * 60 * 60),
                }

        except Exception as e:
            logger.error(f"Failed to index sleep data: {e}", exc_info=True)
            return {"error": str(e), "nights_indexed": 0}

    def get_sleep_in_date_range(
        self, user_id: str, start_timestamp: float, end_timestamp: float
    ) -> list[dict[str, Any]]:
        """
        Get sleep summaries in date range using Redis indexes.

        O(log N) operation - much faster than scanning all records.

        Args:
            user_id: User identifier
            start_timestamp: Start of range (Unix timestamp)
            end_timestamp: End of range (Unix timestamp)

        Returns:
            List of sleep summary dicts
        """
        try:
            with self.redis_manager.get_connection() as client:
                by_date_key = RedisKeys.sleep_by_date(user_id)

                # Get dates in range from sorted set
                date_strings = client.zrangebyscore(
                    by_date_key, start_timestamp, end_timestamp
                )

                # Fetch sleep details for each date
                sleep_nights = []
                for date_bytes in date_strings:
                    date_str = (
                        date_bytes.decode()
                        if isinstance(date_bytes, bytes)
                        else date_bytes
                    )
                    sleep_key = RedisKeys.sleep_detail(user_id, date_str)
                    sleep_data = client.hgetall(sleep_key)

                    if sleep_data:
                        # Convert bytes to strings and numeric types
                        night = {}
                        for k, v in sleep_data.items():
                            key = k.decode() if isinstance(k, bytes) else k
                            value = v.decode() if isinstance(v, bytes) else v

                            # Convert numeric fields
                            if key in [
                                "sleep_hours",
                                "in_bed_hours",
                                "sleep_efficiency",
                                "deep_sleep_hours",
                                "rem_sleep_hours",
                                "core_sleep_hours",
                                "awake_hours",
                            ]:
                                try:
                                    night[key] = float(value)
                                except (ValueError, TypeError):
                                    night[key] = 0.0
                            elif key == "segment_count":
                                try:
                                    night[key] = int(value)
                                except (ValueError, TypeError):
                                    night[key] = 0
                            else:
                                night[key] = value

                        sleep_nights.append(night)

                return sleep_nights

        except Exception as e:
            logger.error(f"Failed to get sleep in date range: {e}")
            return []

    def get_average_sleep_hours(self, user_id: str, days: int = 30) -> float:
        """
        Get average sleep hours over last N days.

        Fast aggregation using Redis indexes.

        Args:
            user_id: User identifier
            days: Number of days to average

        Returns:
            Average sleep hours
        """
        try:
            # Get sleep data for last N days
            now = datetime.now(UTC)
            start_timestamp = (now.timestamp()) - (days * 24 * 60 * 60)
            end_timestamp = now.timestamp()

            sleep_nights = self.get_sleep_in_date_range(
                user_id, start_timestamp, end_timestamp
            )

            if not sleep_nights:
                return 0.0

            total_hours = sum(night.get("sleep_hours", 0) for night in sleep_nights)
            return round(total_hours / len(sleep_nights), 2)

        except Exception as e:
            logger.error(f"Failed to calculate average sleep: {e}")
            return 0.0
