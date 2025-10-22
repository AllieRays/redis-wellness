"""
Generate comprehensive test health data.

Creates BMI, weight, and heart rate data for testing.
Fixes Bug #3: Insufficient test data causing "no data" responses.
"""

import random
from datetime import UTC, datetime, timedelta


def generate_comprehensive_health_data(user_id: str = "wellness_user"):
    """
    Generate 90 days of comprehensive health data.

    Returns:
        Dict with health data in the format expected by Redis storage
    """
    data = {
        "user_id": user_id,
        "export_date": datetime.now().isoformat(),
        "record_count": 0,
        "workouts": [],  # Keep existing workouts
        "metrics_summary": {},
        "metrics_records": {},
    }

    end_date = datetime.now(UTC)

    # Generate BMI data (daily readings for 90 days)
    print("Generating BMI data...")
    bmi_records = []
    base_bmi = 23.5  # Healthy BMI
    for days_ago in range(90, 0, -1):
        date = end_date - timedelta(days=days_ago)
        # Add some natural variation
        bmi = base_bmi + random.uniform(-0.5, 0.5)

        # Make September slightly different for testing
        if date.month == 9:
            bmi = base_bmi + random.uniform(-0.3, 0.3)

        bmi_records.append(
            {
                "value": round(bmi, 2),
                "unit": "count",
                "date": date.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    data["metrics_records"]["BodyMassIndex"] = bmi_records

    # Generate weight data (3x per week for 13 weeks)
    print("Generating weight data...")
    weight_records = []
    base_weight = 160  # lbs
    for week in range(13):
        for day in [0, 2, 5]:  # Mon, Wed, Sat
            days_ago = (12 - week) * 7 + (5 - day)
            if days_ago < 0 or days_ago > 90:
                continue
            date = end_date - timedelta(days=days_ago)
            weight = base_weight + random.uniform(-2, 2)
            weight_records.append(
                {
                    "value": round(weight, 1),
                    "unit": "lb",
                    "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    data["metrics_records"]["BodyMass"] = weight_records

    # Generate heart rate data (5-10 readings per day)
    print("Generating heart rate data...")
    hr_records = []
    for days_ago in range(90, 0, -1):
        readings_today = random.randint(5, 10)
        for _ in range(readings_today):
            date = end_date - timedelta(
                days=days_ago,
                hours=random.randint(6, 22),  # Between 6am and 10pm
                minutes=random.randint(0, 59),
            )
            # Resting heart rate varies throughout day
            base_hr = random.randint(65, 85)
            hr = base_hr + random.randint(-5, 5)
            hr_records.append(
                {
                    "value": hr,
                    "unit": "count/min",
                    "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    data["metrics_records"]["HeartRate"] = hr_records

    # Generate workout data (2-3 workouts per week)
    print("Generating workout data...")
    workouts = []
    workout_types = [
        "HKWorkoutActivityTypeRunning",
        "HKWorkoutActivityTypeCycling",
        "HKWorkoutActivityTypeTraditionalStrengthTraining",
        "HKWorkoutActivityTypeYoga",
        "HKWorkoutActivityTypeElliptical",
    ]

    for week in range(13):  # 13 weeks
        workouts_this_week = random.randint(2, 3)
        for _ in range(workouts_this_week):
            days_ago = (12 - week) * 7 + random.randint(0, 6)
            if days_ago < 0 or days_ago > 90:
                continue

            workout_date = end_date - timedelta(days=days_ago)
            workout_start = workout_date.replace(
                hour=random.randint(6, 19),
                minute=random.randint(0, 59),
                second=0,
                microsecond=0,
            )

            # Workout duration between 20-60 minutes
            duration_minutes = random.randint(20, 60)
            workout_end = workout_start + timedelta(minutes=duration_minutes)

            # Calories burned (rough estimate based on duration)
            calories = duration_minutes * random.uniform(6, 10)

            workout = {
                "workoutActivityType": random.choice(workout_types),
                "startDate": workout_start.isoformat(),
                "endDate": workout_end.isoformat(),
                "duration": duration_minutes * 60,  # in seconds
                "durationUnit": "s",
                "totalEnergyBurned": round(calories, 1),
                "totalEnergyBurnedUnit": "Cal",
                "sourceName": "Test Health App",
                "creationDate": workout_end.isoformat(),
            }
            workouts.append(workout)

    # Sort workouts by date (oldest first)
    workouts.sort(key=lambda x: x["startDate"])
    data["workouts"] = workouts

    # Calculate summaries
    data["metrics_summary"]["BodyMassIndex"] = {
        "count": len(bmi_records),
        "latest_value": f"{bmi_records[-1]['value']} count",
        "latest_date": bmi_records[-1]["date"],
    }

    data["metrics_summary"]["BodyMass"] = {
        "count": len(weight_records),
        "latest_value": f"{weight_records[-1]['value']} lb",
        "latest_date": weight_records[-1]["date"],
    }

    data["metrics_summary"]["HeartRate"] = {
        "count": len(hr_records),
        "latest_value": f"{hr_records[-1]['value']} count/min",
        "latest_date": hr_records[-1]["date"],
    }

    data["record_count"] = len(bmi_records) + len(weight_records) + len(hr_records)

    print(f"\n✅ Generated {data['record_count']} health records:")
    print(f"   - BMI: {len(bmi_records)} records")
    print(f"   - Weight: {len(weight_records)} records")
    print(f"   - Heart Rate: {len(hr_records)} records")

    return data


if __name__ == "__main__":
    # Generate and save data
    data = generate_comprehensive_health_data()

    # Save to JSON for manual review
    import json

    with open("test_health_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print("\n📝 Data saved to test_health_data.json")
