"""
Test for Apple Health workout parsing.

Verifies that strength training workouts from October 2025 are correctly extracted.
"""

import pytest
from backend.src.tools.health_parser_tool import parse_health_file


def test_parse_workouts_from_apple_health():
    """Test that workouts are correctly parsed from Apple Health export."""
    # Parse the actual Apple Health export
    result = parse_health_file("apple_health_export/export.xml", anonymize=False)

    # Verify parsing succeeded
    assert result.success is True, f"Parsing failed: {result.message}"

    # Extract data
    data = result.data

    # Verify workouts were extracted
    assert "workouts" in data, "Workouts not found in parsed data"
    assert "workout_count" in data, "Workout count not found in parsed data"

    # Verify we have workouts
    workouts = data["workouts"]
    workout_count = data["workout_count"]

    assert workout_count > 0, f"Expected workouts but found {workout_count}"
    assert len(workouts) > 0, "Workouts list is empty"

    print(f"\n✅ Found {workout_count} total workouts")
    print(f"✅ Recent workouts (last 10): {len(workouts)}")

    # Verify October 2025 workouts exist
    oct_2025_workouts = [w for w in workouts if w["date"].startswith("2025-10")]
    assert len(oct_2025_workouts) > 0, "No October 2025 workouts found"

    print(f"✅ Found {len(oct_2025_workouts)} October 2025 workouts")

    # Verify the October 17, 2025 workout exists
    oct_17_workouts = [w for w in workouts if "2025-10-17" in w["date"]]
    assert len(oct_17_workouts) > 0, "October 17, 2025 workout not found"

    # Get the Oct 17 workout
    oct_17_workout = oct_17_workouts[0]

    # Verify workout details
    assert (
        oct_17_workout["type"] == "TraditionalStrengthTraining"
    ), f"Expected TraditionalStrengthTraining, got {oct_17_workout['type']}"

    assert oct_17_workout["duration_minutes"] is not None, "Duration is missing"
    assert oct_17_workout["duration_minutes"] > 0, "Duration should be positive"

    assert oct_17_workout["calories"] is not None, "Calories are missing"
    assert oct_17_workout["calories"] > 0, "Calories should be positive"

    assert (
        oct_17_workout["source"] == "Connect"
    ), f"Expected source 'Connect' (Garmin), got {oct_17_workout['source']}"

    print("\n✅ October 17, 2025 Workout Details:")
    print(f"   Type: {oct_17_workout['type']}")
    print(f"   Duration: {oct_17_workout['duration_minutes']} minutes")
    print(f"   Calories: {oct_17_workout['calories']} Cal")
    print(f"   Source: {oct_17_workout['source']}")

    # Verify all October 2025 workouts are strength training
    for workout in oct_2025_workouts:
        assert (
            "Strength" in workout["type"]
        ), f"Expected strength training workout, got {workout['type']}"
        assert (
            workout["source"] == "Connect"
        ), f"Expected Garmin source, got {workout['source']}"

    print("\n✅ All October 2025 workouts are strength training from Garmin")

    # Print summary of all October workouts
    print("\n📊 October 2025 Workouts Summary:")
    for workout in sorted(oct_2025_workouts, key=lambda w: w["date"]):
        date_str = workout["date"][:10]  # Extract just the date part
        print(
            f"   {date_str}: {workout['duration_minutes']}min, {workout['calories']}Cal"
        )


def test_workout_data_structure():
    """Test that workout data has the expected structure."""
    result = parse_health_file("apple_health_export/export.xml", anonymize=False)

    assert result.success is True
    workouts = result.data["workouts"]

    if len(workouts) > 0:
        workout = workouts[0]

        # Verify required fields
        required_fields = ["type", "date", "duration_minutes", "calories", "source"]
        for field in required_fields:
            assert field in workout, f"Missing required field: {field}"

        # Verify data types
        assert isinstance(workout["type"], str), "Type should be string"
        assert isinstance(workout["date"], str), "Date should be ISO format string"
        assert isinstance(
            workout["duration_minutes"], int | type(None)
        ), "Duration should be int or None"
        assert isinstance(
            workout["calories"], int | type(None)
        ), "Calories should be int or None"
        assert isinstance(workout["source"], str), "Source should be string"

        print("\n✅ Workout data structure is valid")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
