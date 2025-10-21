#!/usr/bin/env python3
"""
Load Apple Health XML data into Redis.

This script:
1. Parses the Apple Health export.xml file
2. Structures the data for Redis storage
3. Loads it into Redis with proper indexing
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import redis

# Add backend/src to path
project_root = Path(__file__).parent.parent
backend_src = project_root / "backend" / "src"
sys.path.insert(0, str(backend_src))

# Import with absolute path to avoid relative import issues
import importlib.util

parser_path = project_root / "backend" / "src" / "parsers" / "apple_health_parser.py"
spec = importlib.util.spec_from_file_location("apple_health_parser", parser_path)
parser_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser_module)
AppleHealthParser = parser_module.AppleHealthParser


def load_health_data_to_redis():
    """Parse Apple Health XML and load into Redis."""
    print("=" * 80)
    print("LOADING APPLE HEALTH DATA INTO REDIS")
    print("=" * 80)

    # Initialize parser
    parser = AppleHealthParser()
    xml_path = project_root / "apple_health_export" / "export.xml"

    # Parse XML
    print(f"\n📄 Parsing {xml_path}...")
    try:
        health_data_collection = parser.parse_file(str(xml_path))
    except Exception as e:
        print(f"❌ Failed to parse XML: {e}")
        return False

    print(f"✅ Parsed {len(health_data_collection.records)} health records")
    print(f"✅ Parsed {len(health_data_collection.workouts)} workouts")

    # Structure data for Redis
    print("\n📦 Structuring data for Redis...")

    # Group metrics by type
    metrics_records = {}
    metrics_summary = {}

    for record in health_data_collection.records:
        record_type = record.record_type.replace("HKQuantityTypeIdentifier", "")

        if record_type not in metrics_records:
            metrics_records[record_type] = []
            metrics_summary[record_type] = {
                "latest_value": None,
                "unit": record.unit,
                "count": 0,
                "latest_date": None,
            }

        # Add to records
        metrics_records[record_type].append(
            {
                "date": record.start_date.strftime("%Y-%m-%d %H:%M:%S"),
                "value": record.value,
                "unit": record.unit,
                "source": record.source_name,
            }
        )

        # Update summary
        metrics_summary[record_type]["count"] += 1
        if (
            not metrics_summary[record_type]["latest_date"]
            or record.start_date.strftime("%Y-%m-%d")
            > metrics_summary[record_type]["latest_date"]
        ):
            metrics_summary[record_type]["latest_date"] = record.start_date.strftime(
                "%Y-%m-%d"
            )
            metrics_summary[record_type]["latest_value"] = record.value

    # Structure workouts
    workouts = []
    for workout in health_data_collection.workouts:
        workout_dict = {
            "type": workout.workout_activity_type,
            "date": workout.start_date.strftime("%Y-%m-%d"),
            "startDate": workout.start_date.isoformat(),
            "endDate": workout.end_date.isoformat(),
            "duration": workout.duration * 60,  # Convert to seconds
            "duration_minutes": workout.duration,
            "totalDistance": workout.total_distance,
            "totalEnergyBurned": workout.total_energy_burned,
            "calories": workout.total_energy_burned,  # Alias for compatibility
            "source": workout.source_name,
        }
        workouts.append(workout_dict)

    # Sort workouts by date (most recent first)
    workouts.sort(key=lambda x: x["date"], reverse=True)

    # Create main health data structure
    main_health_data = {
        "user_id": "your_user",
        "record_count": len(health_data_collection.records),
        "export_date": health_data_collection.export_date.isoformat(),
        "data_categories": list(metrics_records.keys()),
        "date_range": {
            "start_date": (
                min((r.start_date for r in health_data_collection.records)).strftime(
                    "%Y-%m-%d"
                )
                if health_data_collection.records
                else None
            ),
            "end_date": (
                max((r.start_date for r in health_data_collection.records)).strftime(
                    "%Y-%m-%d"
                )
                if health_data_collection.records
                else None
            ),
        },
        "metrics_summary": metrics_summary,
        "metrics_records": metrics_records,
        "workouts": workouts,
        "conversation_context": f"Health data export from {health_data_collection.export_date.strftime('%Y-%m-%d')} with {len(health_data_collection.records)} records and {len(workouts)} workouts.",
    }

    # Connect to Redis
    print("\n🔌 Connecting to Redis...")
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return False

    print("✅ Connected to Redis")

    # Store data
    print("\n💾 Storing data in Redis...")
    user_id = "your_user"

    # Store main health data
    main_key = f"health:user:{user_id}:data"
    r.set(main_key, json.dumps(main_health_data))
    print(f"✅ Stored main health data at {main_key}")

    # Store conversation context
    context_key = f"health:user:{user_id}:context"
    r.set(context_key, main_health_data["conversation_context"])
    print(f"✅ Stored conversation context at {context_key}")

    # Store metric indices
    for metric_type, data in metrics_summary.items():
        key = f"health:user:{user_id}:metric:{metric_type}"
        r.set(key, json.dumps(data))
    print(f"✅ Stored {len(metrics_summary)} metric indices")

    # Store individual workout records (for compatibility with tests)
    for i, workout in enumerate(workouts[:10]):  # Store first 10 workouts
        key = f"health:user:{user_id}:workout:{i}"
        r.set(key, json.dumps(workout))
    print(f"✅ Stored {min(10, len(workouts))} individual workout records")

    # Print summary
    print("\n" + "=" * 80)
    print("✅ DATA LOADING COMPLETE")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   • Total records: {len(health_data_collection.records)}")
    print(f"   • Total workouts: {len(workouts)}")
    print(f"   • Metric types: {len(metrics_records)}")
    print(f"   • Most recent workout: {workouts[0]['date'] if workouts else 'None'}")

    # Show October 17 workout if it exists
    oct_17_workouts = [w for w in workouts if "2025-10-17" in w["date"]]
    if oct_17_workouts:
        print(f"\n📅 October 17, 2025 workout found:")
        workout = oct_17_workouts[0]
        print(f"   • Type: {workout['type'].replace('HKWorkoutActivityType', '')}")
        print(f"   • Duration: {workout['duration_minutes']} minutes")
        print(f"   • Calories: {workout['totalEnergyBurned']} Cal")
        print(f"   • Distance: {workout['totalDistance']} mi")

    return True


if __name__ == "__main__":
    success = load_health_data_to_redis()
    sys.exit(0 if success else 1)
