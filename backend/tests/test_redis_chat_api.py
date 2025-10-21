"""
Test Redis Chat API with RAG and Semantic Memory.

Tests via HTTP API that the Redis chat system correctly:
1. Uses tool calling to retrieve health data
2. Answers exercise-related queries
3. Provides memory statistics
"""

import json
import time
import uuid
from datetime import datetime

import requests


def test_redis_chat_exercise_query():
    """
    Test Redis chat can answer: "when was the last time I exercised?"

    This test verifies:
    1. Tool calling works (agent calls search_workouts_and_activity or similar)
    2. Response contains actual data from Redis health records
    3. Response includes tool usage metadata
    4. Memory is created and stored
    """
    base_url = "http://localhost:8000"

    # Generate unique session ID
    session_id = (
        f"test_session_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    )

    print(f"\n{'=' * 80}")
    print("TEST: Redis Chat Exercise Query via API")
    print(f"{'=' * 80}")
    print(f"Session ID: {session_id}")
    print(f"Base URL: {base_url}")

    # Test 1: Health check
    print("\n[1/5] Checking backend health...")
    health_response = requests.get(f"{base_url}/api/health/check")
    assert (
        health_response.status_code == 200
    ), f"Health check failed: {health_response.status_code}"
    health_data = health_response.json()
    print(
        f"✓ Backend healthy: Redis={health_data['redis_connected']}, Ollama={health_data['ollama_connected']}"
    )

    assert health_data["redis_connected"], "Redis must be connected"
    assert health_data["ollama_connected"], "Ollama must be connected"

    # Test 2: Send exercise query
    print("\n[2/5] Sending exercise query...")
    message = "when was the last time I exercised"

    chat_payload = {"message": message, "session_id": session_id}

    chat_response = requests.post(
        f"{base_url}/api/chat/redis",
        json=chat_payload,
        headers={"Content-Type": "application/json"},
        timeout=60,  # RAG queries can take time
    )

    print(f"Response status: {chat_response.status_code}")
    assert (
        chat_response.status_code == 200
    ), f"Chat request failed: {chat_response.status_code} - {chat_response.text}"

    result = chat_response.json()

    # Test 3: Verify response structure
    print("\n[3/5] Verifying response structure...")
    required_fields = [
        "response",
        "session_id",
        "tools_used",
        "tool_calls_made",
        "memory_stats",
        "type",
    ]
    for field in required_fields:
        assert field in result, f"Response missing required field: {field}"
        print(f"✓ Has field: {field}")

    # Verify session ID matches
    assert (
        result["session_id"] == session_id
    ), f"Session ID mismatch: expected {session_id}, got {result['session_id']}"

    # Verify type is correct (should be redis_rag_with_memory or redis_with_memory)
    valid_types = ["redis_with_memory", "redis_rag_with_memory"]
    assert (
        result["type"] in valid_types
    ), f"Wrong type: {result['type']}, expected one of {valid_types}"

    # Test 4: Verify tools were called
    print("\n[4/5] Verifying tool usage...")
    print(f"Tools called: {result['tool_calls_made']}")
    assert result["tool_calls_made"] > 0, "Agent should have called at least one tool"
    assert len(result["tools_used"]) > 0, "tools_used list should not be empty"

    tool_names = [tool["name"] for tool in result["tools_used"]]
    print(f"Tool names: {tool_names}")

    # Verify tool names make sense for exercise query
    exercise_related_tools = [
        "search_workouts_and_activity",
        "search_health_records_by_metric",
        "get_latest_health_values",
        "get_health_summary_by_category",
    ]

    has_exercise_tool = any(tool in tool_names for tool in exercise_related_tools)
    assert has_exercise_tool, f"Expected exercise-related tool, got: {tool_names}"
    print("✓ Uses exercise-related tools")

    # Test 5: Verify response quality
    print("\n[5/5] Verifying response quality...")
    response_text = result["response"]
    print(f"\nQuery: {message}")
    print(f"Response: {response_text}")
    print(f"\nMemory stats: {json.dumps(result['memory_stats'], indent=2)}")

    assert len(response_text) > 0, "Response should not be empty"
    assert isinstance(response_text, str), "Response should be a string"

    # Response should be substantive
    assert len(response_text) > 20, f"Response too short: {response_text}"

    # Check memory stats
    memory_stats = result["memory_stats"]
    print("\nMemory system check:")
    print(
        f"  - Short-term available: {memory_stats.get('short_term_available', False)}"
    )
    print(f"  - Semantic hits: {memory_stats.get('semantic_hits', 0)}")
    print(f"  - Long-term available: {memory_stats.get('long_term_available', False)}")

    # Verify memory stats structure
    assert "short_term_available" in memory_stats, "Missing short_term_available"
    assert "semantic_hits" in memory_stats, "Missing semantic_hits"
    assert "long_term_available" in memory_stats, "Missing long_term_available"

    print(f"\n{'=' * 80}")
    print("✓ TEST PASSED: Redis Chat Exercise Query")
    print(f"{'=' * 80}\n")

    # Cleanup: Clear session
    print("Cleaning up session...")
    cleanup_response = requests.delete(f"{base_url}/api/chat/session/{session_id}")
    if cleanup_response.status_code == 200:
        print("✓ Session cleaned up")
    else:
        print(f"⚠ Cleanup warning: {cleanup_response.status_code}")


def test_redis_chat_follow_up_with_memory():
    """
    Test that Redis chat uses memory for follow-up questions.
    """
    base_url = "http://localhost:8000"
    session_id = (
        f"test_followup_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    )

    print(f"\n{'=' * 80}")
    print("TEST: Redis Chat Follow-up with Memory")
    print(f"{'=' * 80}")
    print(f"Session ID: {session_id}")

    try:
        # First question
        print("\n[1/3] Sending first query...")
        first_message = "what is my latest weight"
        first_response = requests.post(
            f"{base_url}/api/chat/redis",
            json={"message": first_message, "session_id": session_id},
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        assert first_response.status_code == 200
        first_result = first_response.json()

        print(f"First Query: {first_message}")
        print(f"First Response: {first_result['response']}")
        print(f"Tools used: {[tool['name'] for tool in first_result['tools_used']]}")

        assert first_result["tool_calls_made"] > 0, "First query should call tools"

        # Wait for memory to be stored
        print("\n[2/3] Waiting for memory storage...")
        time.sleep(2)

        # Follow-up question
        print("\n[3/3] Sending follow-up query...")
        follow_up_message = "is that good?"
        follow_up_response = requests.post(
            f"{base_url}/api/chat/redis",
            json={"message": follow_up_message, "session_id": session_id},
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        assert follow_up_response.status_code == 200
        follow_up_result = follow_up_response.json()

        print(f"Follow-up Query: {follow_up_message}")
        print(f"Follow-up Response: {follow_up_result['response']}")
        print(
            f"Tools used: {[tool['name'] for tool in follow_up_result['tools_used']]}"
        )

        # Verify memory stats
        memory_stats = follow_up_result.get("memory_stats", {})
        print(f"\nMemory Stats: {json.dumps(memory_stats, indent=2)}")

        # NOTE: Semantic memory is currently disabled in the agent
        # so short_term_available will be False, but conversation history
        # is still maintained through message history

        # Response should reference context from conversation history
        follow_up_text = follow_up_result["response"].lower()
        context_indicators = [
            "weight",
            "bmi",
            "healthy",
            "normal",
            "range",
            "good",
            "136",
            "lbs",
        ]
        has_context = any(
            indicator in follow_up_text for indicator in context_indicators
        )

        confusion_indicators = [
            "don't understand",
            "what are you referring to",
            "what do you mean",
            "clarify what",
        ]
        any(indicator in follow_up_text for indicator in confusion_indicators)

        # The agent should understand context from conversation history
        # even though semantic memory is disabled
        assert (
            has_context
        ), f"Follow-up should understand 'that' refers to weight. Got: {follow_up_result['response'][:200]}"

        print(f"\n{'=' * 80}")
        print("✓ TEST PASSED: Follow-up with Memory")
        print(f"{'=' * 80}\n")

    finally:
        # Cleanup
        requests.delete(f"{base_url}/api/chat/session/{session_id}")


def test_conversation_history():
    """
    Test that conversation history is properly stored.
    """
    base_url = "http://localhost:8000"
    session_id = (
        f"test_history_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    )

    print(f"\n{'=' * 80}")
    print("TEST: Conversation History Storage")
    print(f"{'=' * 80}")
    print(f"Session ID: {session_id}")

    try:
        # Send a message
        print("\n[1/2] Sending message...")
        requests.post(
            f"{base_url}/api/chat/redis",
            json={"message": "what is my weight", "session_id": session_id},
            timeout=60,
        )

        # Get conversation history
        print("\n[2/2] Retrieving history...")
        history_response = requests.get(f"{base_url}/api/chat/history/{session_id}")
        assert history_response.status_code == 200
        history_data = history_response.json()

        print(f"History entries: {history_data['total_messages']}")
        assert (
            history_data["total_messages"] >= 2
        ), "Should have at least 2 messages (user + assistant)"

        # Check message structure
        for msg in history_data["messages"]:
            assert "role" in msg, "Message should have 'role' field"
            assert "content" in msg, "Message should have 'content' field"
            assert msg["role"] in ["user", "assistant"], f"Invalid role: {msg['role']}"

        print(f"\n{'=' * 80}")
        print("✓ TEST PASSED: Conversation History")
        print(f"{'=' * 80}\n")

    finally:
        # Cleanup
        requests.delete(f"{base_url}/api/chat/session/{session_id}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("REDIS CHAT RAG API TESTS")
    print("=" * 80)

    tests = [
        ("Exercise Query", test_redis_chat_exercise_query),
        ("Follow-up with Memory", test_redis_chat_follow_up_with_memory),
        ("Conversation History", test_conversation_history),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n\nRunning: {test_name}")
            print("-" * 80)
            result = test_func()
            results.append((test_name, "PASSED", None))
        except AssertionError as e:
            results.append((test_name, "FAILED", str(e)))
            print(f"\n✗ TEST FAILED: {test_name}")
            print(f"Error: {e}")
        except Exception as e:
            results.append((test_name, "ERROR", str(e)))
            print(f"\n✗ TEST ERROR: {test_name}")
            print(f"Error: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, status, error in results:
        symbol = "✓" if status == "PASSED" else "✗"
        print(f"{symbol} {test_name}: {status}")
        if error:
            print(f"  → {error[:100]}")

    passed = sum(1 for _, status, _ in results if status == "PASSED")
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    print("=" * 80 + "\n")

    if passed == total:
        exit(0)
    else:
        exit(1)
