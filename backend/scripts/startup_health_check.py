#!/usr/bin/env python3
"""
Startup Health Check - Auto-import health data if Redis is empty.

This script runs on container startup and:
1. Checks if health data exists in Redis
2. If missing, automatically imports from available source files
3. Ensures the application is always ready with data

Called by docker-entrypoint.sh before starting the main application.
"""

import logging
import sys
from pathlib import Path

import redis

# Add src to path BEFORE importing local modules
src_dir = str(Path(__file__).parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from utils.redis_keys import RedisKeys  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_redis_health_data(redis_client, user_id: str = "wellness_user") -> bool:
    """Check if health data exists in Redis."""
    try:
        main_key = RedisKeys.health_data(user_id)
        data = redis_client.get(main_key)

        if not data:
            return False

        # Parse and validate
        import json

        parsed = json.loads(data)
        record_count = parsed.get("record_count", 0)

        if record_count == 0:
            logger.warning("Health data exists but has 0 records")
            return False

        logger.info(f"✅ Health data found in Redis: {record_count:,} records")
        return True

    except Exception as e:
        logger.error(f"Failed to check Redis health data: {e}")
        return False


def auto_import_health_data():
    """Automatically import health data if Redis is empty."""
    logger.info("=" * 80)
    logger.info("STARTUP HEALTH CHECK")
    logger.info("=" * 80)

    # Connect to Redis
    logger.info("Connecting to Redis...")
    try:
        redis_client = redis.Redis(
            host="redis",  # Docker service name
            port=6379,
            db=0,
            decode_responses=False,
        )
        redis_client.ping()
        logger.info("✅ Redis connected")
    except redis.ConnectionError as e:
        logger.error(f"❌ Cannot connect to Redis: {e}")
        logger.error("   Application will start but health queries will fail")
        return False

    # Check if data exists
    user_id = "wellness_user"
    if check_redis_health_data(redis_client, user_id):
        logger.info("✅ Health data already loaded - skipping import")
        logger.info("=" * 80)
        return True

    logger.info("⚠️  No health data found in Redis")
    logger.info("🔍 Checking for data files to import...")

    # Look for data files (in order of preference)
    # Files are mounted at root level in Docker
    data_files = [
        Path("/parsed_health_data.json"),  # Fast (if exists)
        Path("/apple_health_export/export.xml"),  # Slow
    ]

    source_file = None
    for file in data_files:
        if file.exists() and file.is_file():
            source_file = file
            logger.info(f"✅ Found data file: {file.name}")
            break

    if not source_file:
        logger.warning("⚠️  No health data files found")
        logger.warning(
            "   Expected: parsed_health_data.json or apple_health_export/export.xml"
        )
        logger.warning(
            "   Application will start but health queries will return no data"
        )
        logger.info("=" * 80)
        return False

    # Run import
    logger.info(f"📥 Auto-importing health data from {source_file.name}...")
    logger.info("   This may take a few minutes for large files...")

    try:
        # Import the import script as a module
        from import_health_data import import_from_json, import_from_xml

        if source_file.suffix == ".json":
            success = import_from_json(source_file, user_id, redis_client)
        elif source_file.suffix == ".xml":
            success = import_from_xml(source_file, user_id, redis_client)
        else:
            logger.error(f"❌ Unsupported file type: {source_file.suffix}")
            return False

        if success:
            logger.info("=" * 80)
            logger.info("✅ AUTO-IMPORT SUCCESSFUL")
            logger.info("=" * 80)
            return True
        else:
            logger.error("❌ Auto-import failed")
            return False

    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        logger.error("   Application will start but health queries will return no data")
        return False


def main():
    """Main entry point."""
    auto_import_health_data()

    # Always exit 0 - we want the app to start even if import fails
    # The app will just return "no data" for health queries
    sys.exit(0)


if __name__ == "__main__":
    main()
