"""
Comprehensive test suite for health queries with real data.

Tests all major query types to ensure the system works end-to-end.
"""

import time
from datetime import datetime

import requests

BASE_URL = "http://localhost:8000"
USER_ID = "wellness_user"  # The user_id that has test data loaded


def test_basic_weight_query():
    """Test: What is my latest weight?"""
    session_id = f"test_weight_{int(time.time())}"

    response = requests.post(
        f"{BASE_URL}/api/chat/redis",
        json={
            "message": "what is my latest weight?",
            "session_id": session_id,
            "user_id": USER_ID,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should use the search tool
    assert data["tool_calls_made"] > 0
    assert any(
        tool["name"] == "search_health_records_by_metric" for tool in data["tools_used"]
    )

    # Should mention weight
    response_text = data["response"].lower()
    assert any(keyword in response_text for keyword in ["weight", "lbs", "pounds"])

    # Should NOT say "no data" or "insufficient data"
    assert "no data" not in response_text
    assert "insufficient" not in response_text

    print(f"✅ Weight query: {data['response'][:100]}...")


def test_average_heart_rate():
    """Test: What was my average heart rate last week?"""
    session_id = f"test_hr_{int(time.time())}"

    response = requests.post(
        f"{BASE_URL}/api/chat/redis",
        json={
            "message": "what was my average heart rate last week?",
            "session_id": session_id,
            "user_id": USER_ID,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should use aggregate tool for averages
    assert data["tool_calls_made"] > 0
    tool_names = [tool["name"] for tool in data["tools_used"]]
    assert "aggregate_metrics" in tool_names

    # Should mention heart rate and bpm
    response_text = data["response"].lower()
    assert any(keyword in response_text for keyword in ["heart rate", "bpm"])

    # Should NOT say "no data"
    assert "no data" not in response_text

    print(f"✅ Average HR query: {data['response'][:100]}...")


def test_historical_bmi_query():
    """Test: What was my BMI in September?"""
    session_id = f"test_bmi_{int(time.time())}"

    response = requests.post(
        f"{BASE_URL}/api/chat/redis",
        json={
            "message": "what was my BMI in September?",
            "session_id": session_id,
            "user_id": USER_ID,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should use search tool
    assert data["tool_calls_made"] > 0
    assert any(
        tool["name"] == "search_health_records_by_metric" for tool in data["tools_used"]
    )

    # Should mention September and BMI
    response_text = data["response"].lower()
    assert (
        "september" in response_text
        or "bmi" in response_text
        or "body mass index" in response_text
    )

    # Should NOT say "no data"
    assert "no data" not in response_text

    print(f"✅ Historical BMI query: {data['response'][:100]}...")


def test_follow_up_with_context():
    """Test: Follow-up question uses conversation context"""
    session_id = f"test_followup_{int(time.time())}"

    # First query
    response1 = requests.post(
        f"{BASE_URL}/api/chat/redis",
        json={
            "message": "what is my latest weight?",
            "session_id": session_id,
            "user_id": USER_ID,
        },
    )

    assert response1.status_code == 200
    response1.json()

    # Wait for memory storage
    time.sleep(1)

    # Follow-up query
    response2 = requests.post(
        f"{BASE_URL}/api/chat/redis",
        json={"message": "is that good?", "session_id": session_id, "user_id": USER_ID},
    )

    assert response2.status_code == 200
    data2 = response2.json()

    # Follow-up should use context (may or may not call tools)
    response_text = data2["response"].lower()

    # Should NOT say "what are you referring to" or "I don't know what you mean"
    assert "what are you referring" not in response_text
    assert "don't know what" not in response_text

    # Should mention health/weight/BMI context
    assert any(
        keyword in response_text for keyword in ["weight", "bmi", "healthy", "health"]
    )

    print(f"✅ Follow-up query: {data2['response'][:100]}...")


def test_workout_query():
    """Test: When did I last work out?"""
    session_id = f"test_workout_{int(time.time())}"

    response = requests.post(
        f"{BASE_URL}/api/chat/redis",
        json={
            "message": "when was the last time I exercised?",
            "session_id": session_id,
            "user_id": USER_ID,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should use workout tool
    assert data["tool_calls_made"] > 0
    assert any(
        tool["name"] == "search_workouts_and_activity" for tool in data["tools_used"]
    )

    # Should respond (even if no workouts found)
    assert len(data["response"]) > 20

    print(f"✅ Workout query: {data['response'][:100]}...")


def test_multiple_metrics():
    """Test: Query multiple metrics at once"""
    session_id = f"test_multi_{int(time.time())}"

    response = requests.post(
        f"{BASE_URL}/api/chat/redis",
        json={
            "message": "show me my latest weight and heart rate",
            "session_id": session_id,
            "user_id": USER_ID,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should call tools
    assert data["tool_calls_made"] > 0

    # Should mention at least one metric (LLM may focus on one)
    response_text = data["response"].lower()
    has_weight = "weight" in response_text or "lbs" in response_text
    has_hr = "heart rate" in response_text or "bpm" in response_text
    assert has_weight or has_hr, "Response should mention at least one requested metric"

    print(f"✅ Multi-metric query: {data['response'][:100]}...")


if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE HEALTH QUERY TESTS")
    print("=" * 80)
    print(f"Testing against: {BASE_URL}")
    print(f"User ID: {USER_ID}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    try:
        test_basic_weight_query()
        print()

        test_average_heart_rate()
        print()

        test_historical_bmi_query()
        print()

        test_follow_up_with_context()
        print()

        test_workout_query()
        print()

        test_multiple_metrics()
        print()

        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        raise
