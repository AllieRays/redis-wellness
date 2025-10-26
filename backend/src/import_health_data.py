#!/usr/bin/env python3
"""
Apple Health Data Importer - Single Script

Handles both:
1. XML import from Apple Health export
2. JSON import from pre-parsed data

Usage:
    # From XML (slow, full parse)
    uv run python import_health_data.py apple_health_export/export.xml

    # From pre-parsed JSON (fast)
    uv run python import_health_data.py parsed_health_data.json

    # Auto-detect
    uv run python import_health_data.py
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import redis

logger = logging.getLogger(__name__)


def import_from_json(
    json_file: Path | None, user_id: str, redis_client, data_dict: dict | None = None
) -> bool:
    """Import from pre-parsed JSON (fast path)."""
    from src.utils.redis_keys import RedisKeys

    # If data_dict provided (from XML parsing), use it directly
    if data_dict is not None:
        data = data_dict
    else:
        # Load from JSON file
        if json_file is None:
            logger.error("❌ No JSON file or data provided")
            return False

        logger.info(
            f"\n📄 Loading JSON: {json_file.name} ({json_file.stat().st_size / 1024 / 1024:.1f} MB)"
        )

        try:
            with open(json_file) as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to read JSON: {e}")
            return False

    # CRITICAL: Enrich workout data - REQUIRED for tools to work
    enriched_count = 0
    failed_count = 0

    for workout in data.get("workouts", []):
        # REQUIRED: day_of_week field (used by workout analysis tools)
        start_date_str = workout.get("startDate", "")
        if not start_date_str:
            logger.warning(
                f"⚠️  Workout missing startDate: {workout.get('type', 'unknown')}"
            )
            failed_count += 1
            continue

        try:
            dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))

            # GUARANTEE these fields exist
            if "day_of_week" not in workout:
                workout["day_of_week"] = dt.strftime("%A")
                enriched_count += 1

            if "date" not in workout:
                workout["date"] = dt.strftime("%Y-%m-%d")

        except Exception as e:
            logger.warning(f"⚠️  Failed to parse date '{start_date_str}': {e}")
            # Fallback to prevent "Unknown"
            workout["day_of_week"] = workout.get("day_of_week", "Monday")
            workout["date"] = workout.get("date", "2020-01-01")
            failed_count += 1

        # REQUIRED: type_cleaned field (used by workout search)
        if "type_cleaned" not in workout:
            workout_type = workout.get("type", "")
            workout["type_cleaned"] = workout_type.replace("HKWorkoutActivityType", "")

        # REQUIRED: calories field (used by energy analysis)
        if "totalEnergyBurned" in workout and "calories" not in workout:
            workout["calories"] = workout["totalEnergyBurned"]

    if enriched_count > 0:
        logger.info(f"✅ Enriched {enriched_count} workouts with computed fields")
    if failed_count > 0:
        logger.warning(f"⚠️  {failed_count} workouts had date parsing issues")

    logger.info(f"✅ Parsed {data.get('record_count', 0):,} records")

    # Store in Redis
    logger.info("\n💾 Storing in Redis...")
    try:
        # Main data
        main_key = RedisKeys.health_data(user_id)
        redis_client.set(main_key, json.dumps(data))
        logger.info(f"✅ Stored: {main_key}")

        # Metric indexes
        if "metrics_summary" in data:
            for metric_type, summary in data["metrics_summary"].items():
                index_key = RedisKeys.health_metric(user_id, metric_type)
                redis_client.setex(index_key, 210 * 24 * 60 * 60, json.dumps(summary))
            logger.info(f"✅ Created {len(data['metrics_summary'])} metric indices")

        # Workout indexes - Create Redis hash sets for fast queries and deduplication
        if "workouts" in data and data["workouts"]:
            logger.info(f"\n📊 Indexing {len(data['workouts'])} workouts...")
            logger.info("   (Creating Redis hashes for O(1) lookups + deduplication)")

            try:
                from src.services.redis_workout_indexer import WorkoutIndexer

                indexer = WorkoutIndexer()

                stats = indexer.index_workouts(user_id, data["workouts"])

                if "error" in stats:
                    logger.warning(f"⚠️  Indexing had issues: {stats['error']}")
                    logger.warning(
                        "   Workouts are still in JSON, queries will work (just slower)"
                    )
                else:
                    logger.info(
                        f"✅ Created {stats['workouts_indexed']} workout hashes ({stats['keys_created']} Redis keys)"
                    )
                    logger.info(f"   TTL: {stats['ttl_days']} days")

            except Exception as e:
                logger.warning(f"⚠️  Warning: Could not create workout indexes: {e}")
                logger.warning(
                    "   Workouts are in JSON, queries will work (just slower)"
                )

        # Sleep indexes - Create Redis hash sets for fast queries
        if "metrics_records" in data:
            sleep_records = data["metrics_records"].get(
                "HKCategoryTypeIdentifierSleepAnalysis", []
            )
            if sleep_records:
                logger.info(f"\n🛌 Indexing {len(sleep_records)} sleep records...")
                logger.info("   (Creating Redis hashes for O(1) lookups)")

                try:
                    from src.services.redis_sleep_indexer import SleepIndexer

                    indexer = SleepIndexer()

                    stats = indexer.index_sleep_data(user_id, sleep_records)

                    if "error" in stats:
                        logger.warning(f"⚠️  Indexing had issues: {stats['error']}")
                        logger.warning(
                            "   Sleep data is still in JSON, queries will work (just slower)"
                        )
                    else:
                        logger.info(
                            f"✅ Created {stats['nights_indexed']} sleep summaries ({stats['keys_created']} Redis keys)"
                        )
                        logger.info(f"   TTL: {stats['ttl_days']} days")

                except Exception as e:
                    logger.warning(f"⚠️  Warning: Could not create sleep indexes: {e}")
                    logger.warning(
                        "   Sleep data is in JSON, queries will work (just slower)"
                    )

        return True

    except Exception as e:
        logger.error(f"❌ Storage failed: {e}", exc_info=True)
        return False


def import_from_xml(xml_file: Path, user_id: str, redis_client) -> bool:
    """Import from Apple Health XML export (slow path)."""
    try:
        from src.apple_health.parser import AppleHealthParser
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error(
            "   Make sure you're running from the project root with backend/src in PYTHONPATH"
        )
        return False

    logger.info(
        f"\n📱 Parsing XML: {xml_file.name} ({xml_file.stat().st_size / 1024 / 1024:.1f} MB)"
    )
    logger.info("⏳ This may take several minutes for large files...")

    try:
        parser = AppleHealthParser(allowed_directories=[str(xml_file.parent)])

        if not parser.validate_xml_structure(str(xml_file)):
            logger.error("❌ Not a valid Apple Health export file")
            return False

        health_data = parser.parse_file(str(xml_file))

        if not health_data or health_data.record_count == 0:
            logger.error("❌ No health records found")
            return False

        logger.info(f"✅ Parsed {health_data.record_count:,} health records")

    except Exception as e:
        logger.error(f"❌ Parsing failed: {e}", exc_info=True)
        return False

    # Convert to JSON format
    logger.info("\n🔄 Converting to storage format...")
    data = {
        "record_count": health_data.record_count,
        "export_date": health_data.export_date.isoformat(),
        "metrics_records": {},
        "metrics_summary": {},
        "workouts": [],
    }

    for record in health_data.records:
        metric_type = record.record_type.value.replace("HKQuantityTypeIdentifier", "")

        if metric_type not in data["metrics_records"]:
            data["metrics_records"][metric_type] = []
            data["metrics_summary"][metric_type] = {
                "count": 0,
                "latest_value": None,
                "latest_date": None,
                "unit": None,
            }

        # For sleep records, we need both start and end dates (duration matters)
        record_data = {
            "date": record.start_date.isoformat(),
            "value": str(record.value),
            "unit": record.unit,
            "source": record.source_name,
        }

        # Sleep records need start/end dates for duration calculation
        if "Sleep" in metric_type:
            record_data["start_date"] = record.start_date.isoformat()
            record_data["end_date"] = record.end_date.isoformat()

        data["metrics_records"][metric_type].append(record_data)

        data["metrics_summary"][metric_type]["count"] += 1
        if record.value:
            data["metrics_summary"][metric_type]["latest_value"] = str(record.value)
            data["metrics_summary"][metric_type]["latest_date"] = (
                record.start_date.isoformat()
            )
            data["metrics_summary"][metric_type]["unit"] = record.unit

    for workout in health_data.workouts:
        workout_type = workout.workout_activity_type.replace(
            "HKWorkoutActivityType", ""
        )

        data["workouts"].append(
            {
                "type": workout.workout_activity_type,
                "workoutActivityType": workout.workout_activity_type,
                "startDate": workout.start_date.isoformat(),
                "endDate": workout.end_date.isoformat() if workout.end_date else None,
                "date": workout.start_date.strftime("%Y-%m-%d"),
                "day_of_week": workout.start_date.strftime("%A"),
                "type_cleaned": workout_type,
                "duration": workout.duration,
                # IMPORTANT: workout.duration is ALREADY in minutes (durationUnit="min" in Apple Health XML)
                # DO NOT divide by 60 - that would convert minutes to hours!
                "duration_minutes": round(workout.duration, 1)
                if workout.duration
                else None,
                "calories": workout.total_energy_burned,
                "totalEnergyBurned": workout.total_energy_burned,
                "totalDistance": workout.total_distance,
                "source": workout.source_name,
            }
        )

    logger.info("✅ Conversion complete")

    # Now store using same logic as JSON import
    return import_from_json(None, user_id, redis_client, data_dict=data)


def main():
    parser = argparse.ArgumentParser(
        description="Import Apple Health data into Redis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From XML export (slow, full parse)
  uv run python import_health_data.py apple_health_export/export.xml

  # From pre-parsed JSON (fast)
  uv run python import_health_data.py parsed_health_data.json

  # Auto-detect best source
  uv run python import_health_data.py
        """,
    )

    parser.add_argument(
        "file", nargs="?", help="Path to export.xml or parsed_health_data.json"
    )
    parser.add_argument("--user-id", default="wellness_user", help="User ID")
    parser.add_argument(
        "--redis-host",
        default=None,
        help="Redis host (default: REDIS_HOST env or localhost)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=None,
        help="Redis port (default: REDIS_PORT env or 6379)",
    )

    args = parser.parse_args()

    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Use environment variables if args not provided
    import os

    if args.redis_host is None:
        args.redis_host = os.getenv("REDIS_HOST", "localhost")
    if args.redis_port is None:
        args.redis_port = int(os.getenv("REDIS_PORT", "6379"))

    print("=" * 80)
    print("  Apple Health Data Import")
    print("=" * 80)
    print(f"\n👤 User ID: {args.user_id}")
    print(f"🔌 Redis: {args.redis_host}:{args.redis_port}")

    # Auto-detect file if not provided
    if not args.file:
        if Path("parsed_health_data.json").exists():
            args.file = "parsed_health_data.json"
            print("📄 Auto-detected: parsed_health_data.json")
        elif Path("apple_health_export/export.xml").exists():
            args.file = "apple_health_export/export.xml"
            print("📱 Auto-detected: apple_health_export/export.xml")
        else:
            print("\n❌ No health data file found")
            print(
                "   Looked for: parsed_health_data.json or apple_health_export/export.xml"
            )
            sys.exit(1)

    file_path = Path(args.file).resolve()

    if not file_path.exists():
        print(f"\n❌ File not found: {file_path}")
        sys.exit(1)

    # Connect to Redis
    print("\n🔌 Connecting to Redis...")
    try:
        client = redis.Redis(
            host=args.redis_host, port=args.redis_port, db=0, decode_responses=False
        )
        client.ping()
        print("✅ Connected")
    except redis.ConnectionError as e:
        print(f"❌ Cannot connect: {e}")
        print("\nMake sure Redis is running: docker-compose ps")
        sys.exit(1)

    # Import based on file type
    print("\n" + "-" * 80)
    if file_path.suffix == ".json":
        success = import_from_json(file_path, args.user_id, client)
    elif file_path.suffix == ".xml":
        success = import_from_xml(file_path, args.user_id, client)
    else:
        print(f"❌ Unsupported file type: {file_path.suffix}")
        print("   Expected: .xml or .json")
        sys.exit(1)

    if success:
        # Validate critical metrics were imported correctly
        print("\n" + "-" * 80)
        print("🔍 Validating import...")

        try:
            from src.utils.redis_keys import RedisKeys

            # Check for RestingHeartRate data (regression test for parser bug)
            main_key = RedisKeys.health_data(args.user_id)
            health_data_json = client.get(main_key)

            if health_data_json:
                health_data = json.loads(health_data_json)
                metrics = health_data.get("metrics_summary", {})

                # Check if RestingHeartRate exists
                if "RestingHeartRate" in metrics:
                    count = metrics["RestingHeartRate"].get("count", 0)
                    print(f"✅ RestingHeartRate: {count:,} records imported")
                else:
                    print("⚠️  RestingHeartRate: No records found")
                    print(
                        "   (Check if your Apple Health export contains resting heart rate data)"
                    )

                # Show other key metrics
                key_metrics = ["HeartRate", "StepCount", "BodyMass"]
                for metric in key_metrics:
                    if metric in metrics:
                        count = metrics[metric].get("count", 0)
                        print(f"✅ {metric}: {count:,} records")

                # Show sleep data
                sleep_records = health_data.get("metrics_records", {}).get(
                    "HKCategoryTypeIdentifierSleepAnalysis", []
                )
                if sleep_records:
                    print(
                        f"✅ Sleep: {len(sleep_records):,} records ({len(sleep_records) // 6} nights estimated)"
                    )

                # Show workout data with corrected duration
                workouts = health_data.get("workouts", [])
                if workouts:
                    total_minutes = sum(w.get("duration_minutes", 0) for w in workouts)
                    total_hours = total_minutes / 60
                    total_calories = sum(
                        w.get("calories", 0) for w in workouts if w.get("calories")
                    )
                    print(
                        f"✅ Workouts: {len(workouts):,} workouts ({total_hours:.1f} hours, {total_calories:,.0f} Cal)"
                    )

        except Exception as e:
            print(f"⚠️  Validation check failed: {e}")

        print("\n" + "=" * 80)
        print("✅ Import completed successfully!")
        print("=" * 80)
        print("\n💡 Test it:")
        print("   Frontend: http://localhost:3000")
        print("   API: http://localhost:8000/docs")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
