#!/usr/bin/env python3
"""
Simple workout parsing test that doesn't require complex imports.
Tests that October 2025 strength training workouts can be extracted from Apple Health XML.
"""

import xml.etree.ElementTree as ET
from datetime import datetime


def parse_workouts_from_xml(file_path):
    """Parse workouts from Apple Health XML file."""
    workouts = []

    # Parse XML file
    context = ET.iterparse(file_path, events=("start", "end"))
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end" and elem.tag == "Workout":
            # Extract workout attributes
            workout_type = elem.get("workoutActivityType", "").replace(
                "HKWorkoutActivityType", ""
            )
            start_date_str = elem.get("startDate", "")
            duration = float(elem.get("duration", 0))
            duration_unit = elem.get("durationUnit", "")
            source = elem.get("sourceName", "")

            # Parse date
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S %z")
            except Exception:
                start_date = None

            # Find energy burned (if available)
            calories = None
            for stat in elem.findall("WorkoutStatistics"):
                if "ActiveEnergyBurned" in stat.get("type", ""):
                    calories = float(stat.get("sum", 0))
                    break

            workouts.append(
                {
                    "type": workout_type,
                    "date": start_date,
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "calories": calories,
                    "source": source,
                }
            )

            # Clear element to save memory
            elem.clear()

    return workouts


def test_october_2025_workouts():
    """Test that October 2025 workouts are correctly parsed."""

    print("🏋️ Testing Workout Parsing")
    print("=" * 60)

    # Parse workouts
    file_path = "apple_health_export/export.xml"
    print(f"\n📁 Parsing workouts from: {file_path}")

    workouts = parse_workouts_from_xml(file_path)

    print(f"\n✅ Total workouts found: {len(workouts)}")

    # Filter October 2025 workouts
    oct_2025_workouts = [
        w
        for w in workouts
        if w["date"] and w["date"].year == 2025 and w["date"].month == 10
    ]

    print(f"✅ October 2025 workouts: {len(oct_2025_workouts)}")

    if len(oct_2025_workouts) == 0:
        print("\n❌ ERROR: No October 2025 workouts found!")
        return False

    # Find the October 17 workout
    oct_17_workouts = [w for w in oct_2025_workouts if w["date"].day == 17]

    if len(oct_17_workouts) == 0:
        print("\n❌ ERROR: October 17, 2025 workout not found!")
        return False

    oct_17_workout = oct_17_workouts[0]

    print("\n✅ Found October 17, 2025 workout:")
    print(f"   Type: {oct_17_workout['type']}")
    print(f"   Date: {oct_17_workout['date'].strftime('%Y-%m-%d %H:%M')}")
    print(
        f"   Duration: {oct_17_workout['duration']:.1f} {oct_17_workout['duration_unit']}"
    )
    print(f"   Calories: {oct_17_workout['calories']:.0f} Cal")
    print(f"   Source: {oct_17_workout['source']}")

    # Verify expected values
    assert (
        oct_17_workout["type"] == "TraditionalStrengthTraining"
    ), f"Expected TraditionalStrengthTraining, got {oct_17_workout['type']}"

    assert (
        oct_17_workout["source"] == "Connect"
    ), f"Expected source 'Connect' (Garmin), got {oct_17_workout['source']}"

    assert (
        oct_17_workout["duration"] > 20
    ), f"Expected duration > 20 minutes, got {oct_17_workout['duration']}"

    assert (
        oct_17_workout["calories"] > 100
    ), f"Expected calories > 100, got {oct_17_workout['calories']}"

    print("\n✅ All validations passed!")

    # Print summary of all October workouts
    print("\n📊 October 2025 Workouts Summary:")
    print("   Date       | Duration | Calories | Type")
    print("   " + "-" * 50)

    for workout in sorted(oct_2025_workouts, key=lambda w: w["date"]):
        date_str = workout["date"].strftime("%Y-%m-%d")
        duration_str = f"{workout['duration']:.0f} min"
        calories_str = (
            f"{workout['calories']:.0f} Cal" if workout["calories"] else "N/A"
        )
        type_short = workout["type"].replace("StrengthTraining", "Strength")
        print(f"   {date_str} | {duration_str:8} | {calories_str:8} | {type_short}")

    # Verify all are strength training from Garmin
    for workout in oct_2025_workouts:
        assert (
            "Strength" in workout["type"]
        ), f"Expected strength training, got {workout['type']}"
        assert (
            workout["source"] == "Connect"
        ), f"Expected Garmin source, got {workout['source']}"

    print(
        f"\n✅ All {len(oct_2025_workouts)} workouts are strength training from Garmin"
    )
    print(f"\n{'=' * 60}")
    print("🎉 ALL TESTS PASSED!")
    print(f"{'=' * 60}")

    return True


if __name__ == "__main__":
    success = test_october_2025_workouts()
    exit(0 if success else 1)
