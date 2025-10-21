#!/usr/bin/env python3
"""
Test Redis Chat with actual health data loaded.

This test:
1. Populates Redis with test health data
2. Tests exercise query
3. Verifies tools retrieve the data
"""

import json
from datetime import datetime, timedelta

import redis
import requests


def setup_test_health_data():
    """Populate Redis with test health data."""
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    user_id = "your_user"

    # Create sample workout records
    workouts = [
        {
            "type": "HKWorkoutActivityTypeRunning",
            "startDate": (datetime.now() - timedelta(days=2)).isoformat(),
            "endDate": (
                datetime.now() - timedelta(days=2) + timedelta(minutes=30)
            ).isoformat(),
            "duration": 1800,
            "totalDistance": 5.2,
            "totalEnergyBurned": 350,
        },
        {
            "type": "HKWorkoutActivityTypeCycling",
            "startDate": (datetime.now() - timedelta(days=5)).isoformat(),
            "endDate": (
                datetime.now() - timedelta(days=5) + timedelta(minutes=45)
            ).isoformat(),
            "duration": 2700,
            "totalDistance": 15.5,
            "totalEnergyBurned": 420,
        },
    ]

    # Store workout data
    for i, workout in enumerate(workouts):
        key = f"health:user:{user_id}:workout:{i}"
        r.set(key, json.dumps(workout))

    # Create weight records
    weight_data = {
        "latest_value": "72.5",
        "unit": "kg",
        "count": 45,
        "latest_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "data_points": [
            {
                "value": "72.5",
                "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            },
            {
                "value": "73.0",
                "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            },
        ],
    }

    r.set(f"health:user:{user_id}:metric:BodyMass", json.dumps(weight_data))

    # Create main health data with workouts
    main_health_data = {
        "user_id": user_id,
        "record_count": 2567,
        "export_date": datetime.now().isoformat(),
        "data_categories": ["HKQuantityTypeIdentifierBodyMass", "HKWorkoutTypeRunning"],
        "date_range": {
            "start_date": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "span_days": 90,
        },
        "metrics_summary": {
            "BodyMass": weight_data,
            "ActiveEnergyBurned": {
                "latest_value": str(workouts[0]["totalEnergyBurned"]),
                "unit": "kcal",
                "count": 45,
                "latest_date": workouts[0]["startDate"][:10],
            },
            "workouts": {
                "count": len(workouts),
                "latest_date": workouts[0]["startDate"][:10],
                "types": ["Running", "Cycling"],
            },
        },
        "workouts": workouts,
    }

    r.set(f"health:user:{user_id}:data", json.dumps(main_health_data))

    print("✅ Created test health data in Redis")
    print(f"   • {len(workouts)} workout records")
    print(f"   • Weight data with {weight_data['count']} records")
    print(f"   • Latest workout: {workouts[0]['startDate'][:10]}")

    return user_id


def test_exercise_query_with_data():
    """Test exercise query with actual data."""
    print("\n" + "=" * 80)
    print("TEST: Exercise Query with Real Data")
    print("=" * 80)

    # Setup data
    setup_test_health_data()

    # Query
    message = "when was the last time I worked out"
    session_id = f"test_real_data_{int(datetime.now().timestamp())}"

    print(f"\nQuery: {message}")
    print(f"Session: {session_id}")

    # Send request
    response = requests.post(
        "http://localhost:8000/api/chat/redis",
        json={"message": message, "session_id": session_id},
        timeout=60,
    )

    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        return False

    result = response.json()

    print("\n📊 Response:")
    print(f"   Tools called: {result['tool_calls_made']}")
    print(f"   Tool names: {[t['name'] for t in result['tools_used']]}")
    print(f"\n💬 Answer:\n   {result['response']}\n")

    # Verify response contains date info
    response_lower = result["response"].lower()

    # Check if response mentions recent dates or "2 days ago" type info
    has_date_info = any(
        word in response_lower
        for word in ["ago", "days", "yesterday", "recent", "2025", "2024", "last"]
    )

    # Check if tools were called
    tools_called = result["tool_calls_made"] > 0

    # Check if it's not an error response
    not_error = not any(
        err in response_lower for err in ["no data", "couldn't find", "unable"]
    )

    print(f"✓ Tools called: {tools_called}")
    print(f"✓ Has date info: {has_date_info}")
    print(f"✓ Not error response: {not_error}")

    # Cleanup
    requests.delete(f"http://localhost:8000/api/chat/session/{session_id}")

    success = tools_called and (has_date_info or not_error)

    if success:
        print(f"\n{'=' * 80}")
        print("✅ TEST PASSED")
        print(f"{'=' * 80}\n")
    else:
        print(f"\n{'=' * 80}")
        print("❌ TEST FAILED")
        print("   Response should mention dates or workout info")
        print(f"{'=' * 80}\n")

    assert success, "Exercise query should call tools and provide date information"


if __name__ == "__main__":
    try:
        success = test_exercise_query_with_data()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
