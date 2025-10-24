#!/usr/bin/env python3
"""
Rebuild Redis Workout Indexes from JSON Data.

This script rebuilds the Redis workout indexes from the existing health data JSON.
Run this after loading health data to enable fast workout queries.

Usage:
    python rebuild_workout_indexes.py
"""

import json
import logging
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from src.services.redis_connection import get_redis_manager
from src.services.redis_workout_indexer import WorkoutIndexer
from src.utils.user_config import get_user_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def rebuild_indexes():
    """Rebuild workout indexes from JSON data in Redis."""
    try:
        user_id = get_user_id()
        redis_manager = get_redis_manager()
        indexer = WorkoutIndexer()

        logger.info(f"Rebuilding workout indexes for user: {user_id}")

        # Get health data from Redis
        with redis_manager.get_connection() as client:
            main_key = f"health:user:{user_id}:data"
            health_data_json = client.get(main_key)

            if not health_data_json:
                logger.error(f"No health data found for user {user_id}")
                logger.error("Please run load_real_health.py or load_health_data.py first")
                return False

            health_data = json.loads(health_data_json)
            workouts = health_data.get("workouts", [])

            if not workouts:
                logger.warning("No workouts found in health data")
                return False

            logger.info(f"Found {len(workouts)} workouts in JSON data")

        # Build indexes
        logger.info("Building Redis indexes...")
        stats = indexer.index_workouts(user_id, workouts)

        logger.info(f"✅ Successfully indexed {stats['workouts_indexed']} workouts")
        logger.info(f"Created {stats['keys_created']} Redis keys")

        # Verify indexes
        total_count = indexer.get_total_workout_count(user_id)
        day_counts = indexer.get_workout_count_by_day(user_id)

        logger.info(f"\nVerification:")
        logger.info(f"  Total workouts indexed: {total_count}")
        logger.info(f"  Workouts by day: {day_counts}")

        return True

    except Exception as e:
        logger.error(f"Failed to rebuild indexes: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = rebuild_indexes()
    sys.exit(0 if success else 1)
