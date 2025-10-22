"""
Integration test for workout data flow: XML -> Parser -> Redis.

This test ensures workouts are correctly parsed from Apple Health XML
and stored in Redis without data loss.
"""

import json
import sys
from pathlib import Path

import pytest
import redis

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from parsers.apple_health_parser import AppleHealthParser


@pytest.fixture
def redis_client():
    """Redis client for testing."""
    client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield client
    # Cleanup test data
    client.delete("health:user:test_user:data")


def test_workout_parsing_from_sample_xml(tmp_path):
    """Test that workouts are correctly parsed from XML."""
    # Create sample Apple Health XML with workouts
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData [
<!ELEMENT HealthData (ExportDate,Me,(Record|Workout|ActivitySummary)*)>
<!ATTLIST HealthData locale CDATA #REQUIRED>
]>
<HealthData locale="en_US">
 <ExportDate value="2025-10-22 00:00:00 -0700"/>
 <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01"
     HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale"
     HKCharacteristicTypeIdentifierBloodType="HKBloodTypeNotSet"/>
 <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
          duration="30.5"
          durationUnit="min"
          sourceName="TestApp"
          creationDate="2025-10-21 10:00:00 -0700"
          startDate="2025-10-21 09:00:00 -0700"
          endDate="2025-10-21 09:30:30 -0700">
  <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned"
                     sum="250.5"
                     unit="kcal"/>
  <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning"
                     sum="5.2"
                     unit="km"/>
 </Workout>
 <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
          duration="45.0"
          durationUnit="min"
          sourceName="TestApp"
          creationDate="2025-10-20 14:00:00 -0700"
          startDate="2025-10-20 13:00:00 -0700"
          endDate="2025-10-20 13:45:00 -0700">
  <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned"
                     sum="400.0"
                     unit="kcal"/>
 </Workout>
</HealthData>
"""

    # Write sample XML
    xml_file = tmp_path / "test_export.xml"
    xml_file.write_text(sample_xml)

    # Parse with AppleHealthParser
    parser = AppleHealthParser(allowed_directories=[str(tmp_path)])
    health_data = parser.parse_file(str(xml_file))

    # Verify workouts were parsed
    assert len(health_data.workouts) == 2, "Should parse 2 workouts"

    # Verify first workout details
    workout1 = health_data.workouts[0]
    assert workout1.workout_activity_type == "HKWorkoutActivityTypeRunning"
    assert workout1.duration == 30.5
    assert workout1.total_energy_burned == 250.5
    assert workout1.total_distance == 5.2

    # Verify second workout
    workout2 = health_data.workouts[1]
    assert workout2.workout_activity_type == "HKWorkoutActivityTypeCycling"
    assert workout2.duration == 45.0
    assert workout2.total_energy_burned == 400.0


def test_workout_storage_in_redis(redis_client, tmp_path):
    """Test that parsed workouts are correctly stored in Redis."""
    # Create minimal XML with one workout
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData [
<!ELEMENT HealthData (ExportDate,Me,(Record|Workout)*)>
]>
<HealthData locale="en_US">
 <ExportDate value="2025-10-22 00:00:00 -0700"/>
 <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01"/>
 <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
          duration="20.0"
          durationUnit="min"
          startDate="2025-10-21 09:00:00 -0700"
          endDate="2025-10-21 09:20:00 -0700">
  <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned"
                     sum="150.0"
                     unit="kcal"/>
 </Workout>
</HealthData>
"""

    xml_file = tmp_path / "test_export.xml"
    xml_file.write_text(sample_xml)

    # Parse
    parser = AppleHealthParser(allowed_directories=[str(tmp_path)])
    health_data = parser.parse_file(str(xml_file))

    # Convert to JSON structure (simulate scripts/parse_apple_health.py)
    workouts = []
    for workout in health_data.workouts:
        workout_dict = {
            "type": workout.workout_activity_type,
            "date": workout.start_date.strftime("%Y-%m-%d"),
            "startDate": workout.start_date.isoformat(),
            "endDate": workout.end_date.isoformat(),
            "duration": workout.duration * 60 if workout.duration else None,
            "duration_minutes": workout.duration,
            "totalEnergyBurned": workout.total_energy_burned,
            "calories": workout.total_energy_burned,
        }
        workouts.append(workout_dict)

    health_json = {
        "user_id": "test_user",
        "record_count": len(health_data.records),
        "export_date": health_data.export_date.isoformat(),
        "workouts": workouts,
    }

    # Store in Redis (simulate scripts/load_health_to_redis.py)
    redis_client.set("health:user:test_user:data", json.dumps(health_json))

    # Verify data in Redis
    stored_data = redis_client.get("health:user:test_user:data")
    assert stored_data is not None, "Data should be stored in Redis"

    parsed_data = json.loads(stored_data)
    assert "workouts" in parsed_data, "Workouts field should exist"
    assert len(parsed_data["workouts"]) == 1, "Should have 1 workout"

    stored_workout = parsed_data["workouts"][0]
    assert stored_workout["type"] == "HKWorkoutActivityTypeRunning"
    assert stored_workout["duration_minutes"] == 20.0
    assert stored_workout["totalEnergyBurned"] == 150.0


def test_redis_data_integrity():
    """
    Test that verifies current Redis data has workouts.

    This is a smoke test that fails if workout data is missing,
    alerting developers to reload the data.
    """
    client = redis.Redis(host="localhost", port=6379, decode_responses=True)

    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis not available")

    # Check if health data exists
    data = client.get("health:user:wellness_user:data")
    if not data:
        pytest.skip("No health data loaded in Redis")

    health_data = json.loads(data)

    # Verify workouts exist
    assert "workouts" in health_data, "Health data should have 'workouts' field"

    workouts = health_data.get("workouts", [])
    if len(workouts) == 0:
        pytest.fail(
            "⚠️  WARNING: No workouts found in Redis!\n"
            "Run: python3 scripts/load_health_to_redis.py\n"
            "This will reload the parsed health data with all workouts."
        )

    print(f"✅ Redis data integrity check passed: {len(workouts)} workouts found")
