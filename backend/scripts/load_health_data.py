#!/usr/bin/env python3
"""
Load parsed Apple Health data into Redis.

This script loads health data from a JSON file into Redis, ensuring
data integrity and proper formatting.

Usage:
    python scripts/load_health_data.py <json_file> [--user-id USER_ID]
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


import redis


def validate_health_data(data: dict) -> tuple[bool, str]:
    """
    Validate health data structure.

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["export_date", "record_count"]

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate metrics_records structure
    if "metrics_records" in data:
        if not isinstance(data["metrics_records"], dict):
            return False, "metrics_records must be a dict"

        # Validate each metric has proper structure
        for metric_type, records in data["metrics_records"].items():
            if not isinstance(records, list):
                return False, f"Metric {metric_type} records must be a list"

            for i, record in enumerate(records):
                if not isinstance(record, dict):
                    return False, f"Metric {metric_type} record {i} must be a dict"

                if "date" not in record:
                    return (
                        False,
                        f"Metric {metric_type} record {i} missing 'date' field",
                    )

                if "value" not in record:
                    return (
                        False,
                        f"Metric {metric_type} record {i} missing 'value' field",
                    )

    # Validate workouts structure
    if "workouts" in data:
        if not isinstance(data["workouts"], list):
            return False, "workouts must be a list"

        for i, workout in enumerate(data["workouts"]):
            if not isinstance(workout, dict):
                return False, f"Workout {i} must be a dict"

            # Check for either format (workoutActivityType or type)
            if "workoutActivityType" not in workout and "type" not in workout:
                return (
                    False,
                    f"Workout {i} missing 'workoutActivityType' or 'type' field",
                )

            if "startDate" not in workout:
                return False, f"Workout {i} missing 'startDate' field"

            if "duration" not in workout and "duration_minutes" not in workout:
                return (
                    False,
                    f"Workout {i} missing 'duration' or 'duration_minutes' field",
                )

    return True, ""


def load_health_data_to_redis(
    json_file: str,
    user_id: str = "wellness_user",
    redis_host: str = "localhost",
    redis_port: int = 6379,
) -> bool:
    """
    Load health data from JSON file into Redis.

    Args:
        json_file: Path to parsed health data JSON file
        user_id: User ID to store data under
        redis_host: Redis host
        redis_port: Redis port

    Returns:
        True if successful, False otherwise
    """
    print(f"🔄 Loading health data from: {json_file}")
    print(f"👤 User ID: {user_id}")
    print(f"🔌 Redis: {redis_host}:{redis_port}")
    print()

    # Load JSON file
    try:
        with open(json_file) as f:
            health_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON: {e}")
        return False

    print(f"✅ Loaded JSON file ({len(json.dumps(health_data))} bytes)")

    # Validate data structure
    is_valid, error_msg = validate_health_data(health_data)
    if not is_valid:
        print(f"❌ Error: Invalid health data structure: {error_msg}")
        return False

    print("✅ Validated health data structure")

    # Display data summary
    print("\n📊 Data Summary:")
    print(f"   - Total records: {health_data.get('record_count', 0)}")
    print(f"   - Export date: {health_data.get('export_date', 'N/A')}")

    if "metrics_records" in health_data:
        print(f"   - Metric types: {len(health_data['metrics_records'])}")
        for metric_type, records in health_data["metrics_records"].items():
            print(f"     • {metric_type}: {len(records)} records")

    if "workouts" in health_data:
        print(f"   - Workouts: {len(health_data['workouts'])}")

    # Connect to Redis
    try:
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            decode_responses=False,  # Store as bytes for consistency
        )
        redis_client.ping()
        print("\n✅ Connected to Redis")
    except redis.ConnectionError as e:
        print(f"\n❌ Error: Cannot connect to Redis: {e}")
        return False

    # Store in Redis
    try:
        main_key = f"health:user:{user_id}:data"

        # Store main health data
        redis_client.set(main_key, json.dumps(health_data))
        print(f"✅ Stored main health data at: {main_key}")

        # Create indices for fast metric queries
        if "metrics_summary" in health_data:
            for metric_type, summary in health_data["metrics_summary"].items():
                index_key = f"health:user:{user_id}:metric:{metric_type}"
                redis_client.setex(
                    index_key,
                    210 * 24 * 60 * 60,  # 7 months TTL
                    json.dumps(summary),
                )
            print(f"✅ Created {len(health_data['metrics_summary'])} metric indices")

        # Verify data was stored correctly
        stored_data = redis_client.get(main_key)
        if stored_data:
            stored_json = json.loads(stored_data)
            if stored_json.get("record_count") == health_data.get("record_count"):
                print("✅ Verified data integrity")
            else:
                print("⚠️  Warning: Stored data may be incomplete")

        print("\n🎉 Successfully loaded health data into Redis!")
        print("\n💡 Test with:")
        print("   curl -X POST http://localhost:8000/api/chat/redis \\")
        print('     -H "Content-Type: application/json" \\')
        print(
            f'     -d \'{{"message": "what is my latest weight?", "user_id": "{user_id}"}}\''
        )

        return True

    except Exception as e:
        print(f"\n❌ Error storing data in Redis: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Load parsed Apple Health data into Redis"
    )
    parser.add_argument("json_file", help="Path to parsed health data JSON file")
    parser.add_argument(
        "--user-id",
        default="wellness_user",
        help="User ID to store data under (default: wellness_user)",
    )
    parser.add_argument(
        "--redis-host", default="localhost", help="Redis host (default: localhost)"
    )
    parser.add_argument(
        "--redis-port", type=int, default=6379, help="Redis port (default: 6379)"
    )

    args = parser.parse_args()

    success = load_health_data_to_redis(
        json_file=args.json_file,
        user_id=args.user_id,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
