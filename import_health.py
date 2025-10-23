#!/usr/bin/env python3
"""
Apple Health Data Importer

Parses Apple Health XML exports and loads them into Redis.
This is the single entry point for importing health data.

Usage:
    # From project root
    cd /Users/allierays/Sites/redis-wellness
    uv run python import_health.py apple_health_export/export.xml

    # Or with custom options
    uv run python import_health.py /path/to/export.xml --user-id myuser --redis-port 6379
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend/src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

import redis
from apple_health.parser import AppleHealthParser


def import_health_data(
    xml_file: str,
    user_id: str = "wellness_user",
    redis_host: str = "localhost",
    redis_port: int = 6379,
) -> bool:
    """
    Parse Apple Health XML and store in Redis.

    Args:
        xml_file: Path to export.xml file
        user_id: User ID for storage (default: wellness_user)
        redis_host: Redis hostname (default: localhost)
        redis_port: Redis port (default: 6379)

    Returns:
        True if successful, False otherwise
    """
    print("=" * 80)
    print("  Apple Health Data Import")
    print("=" * 80)

    xml_path = Path(xml_file).resolve()

    # Validate file
    if not xml_path.exists():
        print(f"\n❌ Error: File not found: {xml_path}")
        return False

    file_size_mb = xml_path.stat().st_size / 1024 / 1024
    print(f"\n📱 XML File: {xml_path}")
    print(f"   Size: {file_size_mb:.1f} MB")
    print(f"👤 User ID: {user_id}")
    print(f"🔌 Redis: {redis_host}:{redis_port}")

    # Parse XML
    print("\n" + "-" * 80)
    print("Step 1/3: Parsing Apple Health XML")
    print("-" * 80)
    print("Please wait, this may take several minutes for large files...")

    try:
        parser = AppleHealthParser(allowed_directories=[str(xml_path.parent)])

        if not parser.validate_xml_structure(str(xml_path)):
            print("\n❌ Error: Not a valid Apple Health export file")
            print("   Expected: export.xml from Apple Health app")
            return False

        health_data = parser.parse_file(str(xml_path))

        if not health_data or health_data.record_count == 0:
            print("\n❌ Error: No health records found")
            return False

        print(f"✅ Parsed {health_data.record_count:,} health records")
        print(f"   Export date: {health_data.export_date}")

    except Exception as e:
        print(f"\n❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Convert to Redis format
    print("\n" + "-" * 80)
    print("Step 2/3: Converting to storage format")
    print("-" * 80)

    try:
        data = {
            "record_count": health_data.record_count,
            "export_date": health_data.export_date.isoformat(),
            "metrics_records": {},
            "metrics_summary": {},
            "workouts": [],
        }

        # Process health records
        print("Processing health metrics...")
        for record in health_data.records:
            metric_type = record.record_type.value.replace("HKQuantityTypeIdentifier", "")

            if metric_type not in data["metrics_records"]:
                data["metrics_records"][metric_type] = []
                data["metrics_summary"][metric_type] = {
                    "count": 0,
                    "latest_value": None,
                    "latest_date": None,
                }

            data["metrics_records"][metric_type].append({
                "date": record.start_date.isoformat(),  # ISO format with timezone
                "value": str(record.value),
                "unit": record.unit,
                "source": record.source_name,
            })

            data["metrics_summary"][metric_type]["count"] += 1
            if record.value:
                data["metrics_summary"][metric_type]["latest_value"] = f"{record.value} {record.unit}"
                data["metrics_summary"][metric_type]["latest_date"] = record.start_date.isoformat()  # Already correct

        # Process workouts with enrichment
        print("Processing workouts...")
        for workout in health_data.workouts:
            workout_type = workout.workout_activity_type.replace("HKWorkoutActivityType", "")

            # Enrich with computed fields for LLM-friendly access
            workout_dict = {
                # Original fields
                "type": workout.workout_activity_type,  # Keep full name
                "workoutActivityType": workout.workout_activity_type,  # Backwards compat

                # Dates in ISO format with timezone
                "startDate": workout.start_date.isoformat(),
                "endDate": workout.end_date.isoformat() if workout.end_date else None,

                # Computed fields for easy filtering and display
                "date": workout.start_date.strftime("%Y-%m-%d"),  # Date only
                "day_of_week": workout.start_date.strftime("%A"),  # Monday, Tuesday, etc.
                "type_cleaned": workout_type,  # Clean type name

                # Duration
                "duration": workout.duration,  # Seconds
                "duration_minutes": round(workout.duration / 60, 1) if workout.duration else None,  # Convert to minutes

                # Energy with standardized field name
                "calories": workout.total_energy_burned,  # Primary field
                "totalEnergyBurned": workout.total_energy_burned,  # Backwards compat

                # Other fields
                "totalDistance": workout.total_distance,
                "source": workout.source_name,
            }

            data["workouts"].append(workout_dict)

        print(f"✅ Converted successfully")

    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Display summary
    print("\n📊 Data Summary:")
    print(f"   Total records: {data['record_count']:,}")
    print(f"   Metric types: {len(data['metrics_records'])}")

    if data["metrics_records"]:
        sorted_metrics = sorted(
            data["metrics_records"].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        print("\n   Top metrics:")
        for metric_type, records in sorted_metrics[:8]:
            print(f"     • {metric_type}: {len(records):,} records")

    if data["workouts"]:
        print(f"\n   Workouts: {len(data['workouts']):,}")

    # Store in Redis
    print("\n" + "-" * 80)
    print("Step 3/3: Storing in Redis")
    print("-" * 80)

    try:
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            decode_responses=False,
        )
        client.ping()
        print("✅ Connected to Redis")

    except redis.ConnectionError as e:
        print(f"❌ Cannot connect to Redis: {e}")
        print("\nMake sure Redis is running:")
        print("  docker-compose ps")
        return False

    try:
        main_key = f"health:user:{user_id}:data"

        # Store main data
        client.set(main_key, json.dumps(data))
        print(f"✅ Stored data: {main_key}")

        # Create metric indices
        for metric_type, summary in data["metrics_summary"].items():
            index_key = f"health:user:{user_id}:metric:{metric_type}"
            client.setex(
                index_key,
                210 * 24 * 60 * 60,  # 7 months
                json.dumps(summary),
            )
        print(f"✅ Created {len(data['metrics_summary'])} metric indices")

        # Build Redis workout indexes for fast queries
        print("\n📊 Building Redis workout indexes...")
        try:
            # Import inside function to avoid circular dependency
            import sys
            sys.path.insert(0, 'backend/src')
            from services.redis_workout_indexer import WorkoutIndexer

            indexer = WorkoutIndexer()
            index_stats = indexer.index_workouts(user_id, data["workouts"])

            if "error" in index_stats:
                print(f"⚠️  Workout indexing failed: {index_stats['error']}")
            else:
                print(f"✅ Indexed {index_stats['workouts_indexed']} workouts ({index_stats['keys_created']} Redis keys)")
                print(f"   TTL: {index_stats['ttl_days']} days (7 months)")
        except Exception as e:
            print(f"⚠️  Workout indexing failed: {e}")
            print("   (Workouts still accessible via JSON, but queries will be slower)")

        # Clear semantic memory to prevent stale cached answers
        print("\n🧹 Clearing semantic memory cache...")
        try:
            import asyncio
            from services.memory_manager import get_memory_manager

            memory_manager = get_memory_manager()
            result = asyncio.run(memory_manager.clear_factual_memory(user_id))

            if "error" in result:
                print(f"⚠️  Memory clearing failed: {result['error']}")
            else:
                deleted = result.get('deleted_count', 0)
                if deleted > 0:
                    print(f"✅ Cleared {deleted} cached memories (fresh data will be used)")
                else:
                    print(f"✅ No stale memories found")
        except Exception as e:
            print(f"⚠️  Memory clearing failed: {e}")
            print("   (Existing semantic memories may contain outdated information)")

        # Verify
        stored = client.get(main_key)
        if stored:
            stored_data = json.loads(stored)
            if stored_data.get("record_count") == data.get("record_count"):
                print("✅ Verified data integrity")
            else:
                print("⚠️  Warning: Record count mismatch")

        print("\n" + "=" * 80)
        print("✅ Import completed successfully!")
        print("=" * 80)
        print("\n💡 Test your data:")
        print(f'   curl -X POST http://localhost:8000/api/chat/redis \\')
        print(f'     -H "Content-Type: application/json" \\')
        print(f'     -d \'{{"message": "What health data do you have for me?", "user_id": "{user_id}"}}\'')
        print()

        return True

    except Exception as e:
        print(f"\n❌ Storage failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Import Apple Health data into Redis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic import
  uv run python import_health.py apple_health_export/export.xml

  # Custom user
  uv run python import_health.py export.xml --user-id john

  # Different Redis
  uv run python import_health.py export.xml --redis-host redis.local --redis-port 6380
        """
    )

    parser.add_argument(
        "xml_file",
        help="Path to Apple Health export.xml file"
    )
    parser.add_argument(
        "--user-id",
        default="wellness_user",
        help="User ID for storage (default: wellness_user)"
    )
    parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redis hostname (default: localhost)"
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redis port (default: 6379)"
    )

    args = parser.parse_args()

    success = import_health_data(
        xml_file=args.xml_file,
        user_id=args.user_id,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
