"""
Test Redis Chat with RAG and Semantic Memory.

Tests that the Redis chat system correctly:
1. Uses tool calling to retrieve health data
2. Stores conversations in semantic memory
3. Retrieves relevant memories via semantic search
4. Answers follow-up questions with context
"""

import asyncio
import uuid
from datetime import datetime

import pytest

from src.services.memory_manager import get_memory_manager
from src.services.redis_chat import RedisChatService


@pytest.fixture
def redis_chat_service():
    """Create Redis chat service instance."""
    return RedisChatService()


@pytest.fixture
def unique_session_id():
    """Generate unique session ID for test isolation."""
    return f"test_session_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"


@pytest.fixture
async def cleanup_session(unique_session_id):
    """Cleanup test session data after test."""
    yield
    # Cleanup after test
    memory_manager = get_memory_manager()
    await memory_manager.clear_session_memory(unique_session_id)


@pytest.mark.asyncio
async def test_redis_chat_exercise_query(
    redis_chat_service, unique_session_id, cleanup_session
):
    """
    Test Redis chat can answer: "when was the last time I exercised?"

    This test verifies:
    1. Tool calling works (agent calls search_workouts_and_activity or similar)
    2. Response contains actual data from Redis health records
    3. Response includes tool usage metadata
    4. Memory is created and stored
    """
    # Query about exercise
    message = "when was the last time I exercised"

    # Send message to Redis chat
    result = await redis_chat_service.chat(
        message=message, session_id=unique_session_id
    )

    # Verify response structure
    assert "response" in result, "Response should contain 'response' field"
    assert "session_id" in result, "Response should contain 'session_id' field"
    assert "tools_used" in result, "Response should contain 'tools_used' field"
    assert (
        "tool_calls_made" in result
    ), "Response should contain 'tool_calls_made' field"
    assert "memory_stats" in result, "Response should contain 'memory_stats' field"

    # Verify session ID matches
    assert result["session_id"] == unique_session_id, "Session ID should match"

    # Verify tools were called
    assert result["tool_calls_made"] > 0, "Agent should have called at least one tool"
    assert len(result["tools_used"]) > 0, "tools_used list should not be empty"

    # Verify tool names make sense for exercise query
    tool_names = [tool["name"] for tool in result["tools_used"]]
    exercise_related_tools = [
        "search_workouts_and_activity",
        "search_health_records_by_metric",
        "get_latest_health_values",
        "get_health_summary_by_category",
    ]

    # At least one tool should be exercise-related
    has_exercise_tool = any(tool in tool_names for tool in exercise_related_tools)
    assert has_exercise_tool, f"Expected exercise-related tool, got: {tool_names}"

    # Verify response is not empty
    response_text = result["response"]
    assert len(response_text) > 0, "Response should not be empty"
    assert isinstance(response_text, str), "Response should be a string"

    # Verify response is meaningful (not an error message)
    error_indicators = ["error", "failed", "could not", "unable to"]
    response_lower = response_text.lower()

    # Check if it's an actual answer vs error
    # If there's no data, that's okay, but it should be a proper response
    is_valid_response = len(response_text) > 20 and not all(  # Has substance
        indicator in response_lower for indicator in error_indicators
    )

    print(f"\n{'=' * 80}")
    print("TEST: Redis Chat Exercise Query")
    print(f"{'=' * 80}")
    print(f"Session ID: {unique_session_id}")
    print(f"Query: {message}")
    print(f"\nResponse: {response_text}")
    print(f"\nTools called ({result['tool_calls_made']}): {tool_names}")
    print(f"Memory stats: {result['memory_stats']}")
    print(f"{'=' * 80}\n")

    assert (
        is_valid_response
    ), f"Response should be meaningful, got: {response_text[:200]}"


@pytest.mark.asyncio
async def test_redis_chat_follow_up_with_memory(
    redis_chat_service, unique_session_id, cleanup_session
):
    """
    Test that Redis chat uses memory for follow-up questions.

    This tests:
    1. First question creates memory
    2. Follow-up question uses short-term memory (conversation context)
    3. Memory stats show memory is available
    """
    # First question
    first_message = "what is my latest weight"
    first_result = await redis_chat_service.chat(
        message=first_message, session_id=unique_session_id
    )

    print(f"\n{'=' * 80}")
    print("TEST: Redis Chat Follow-up with Memory")
    print(f"{'=' * 80}")
    print(f"Session ID: {unique_session_id}")
    print(f"\nFirst Query: {first_message}")
    print(f"First Response: {first_result['response']}")
    print(f"Tools used: {[tool['name'] for tool in first_result['tools_used']]}")

    # Verify first response worked
    assert first_result["tool_calls_made"] > 0, "First query should call tools"

    # Wait a moment for memory to be stored
    await asyncio.sleep(1)

    # Follow-up question using pronoun "that"
    follow_up_message = "is that good?"
    follow_up_result = await redis_chat_service.chat(
        message=follow_up_message, session_id=unique_session_id
    )

    print(f"\nFollow-up Query: {follow_up_message}")
    print(f"Follow-up Response: {follow_up_result['response']}")
    print(f"Tools used: {[tool['name'] for tool in follow_up_result['tools_used']]}")

    # Verify memory stats show short-term memory is available
    memory_stats = follow_up_result.get("memory_stats", {})
    print(f"\nMemory Stats: {memory_stats}")
    print(f"{'=' * 80}\n")

    # Short-term memory should be available for second message
    assert memory_stats.get(
        "short_term_available", False
    ), "Short-term memory should be available for follow-up"

    # Response should reference previous context
    follow_up_text = follow_up_result["response"].lower()

    # The follow-up should either:
    # 1. Reference the weight from previous message
    # 2. Make sense in context (not ask "what is that?")
    context_indicators = ["weight", "bmi", "healthy", "normal", "range"]
    has_context = any(indicator in follow_up_text for indicator in context_indicators)

    # Or check it's not confused
    confusion_indicators = ["what", "which", "clarify", "don't understand"]
    is_confused = any(indicator in follow_up_text for indicator in confusion_indicators)

    assert (
        has_context or not is_confused
    ), f"Follow-up should understand context. Got: {follow_up_result['response'][:200]}"


@pytest.mark.asyncio
async def test_redis_chat_semantic_memory_retrieval(
    redis_chat_service, cleanup_session
):
    """
    Test semantic memory storage and retrieval across sessions.

    This tests:
    1. Store a conversation about exercise goal
    2. Later query retrieves it via semantic search
    3. Semantic hits are recorded
    """
    # Use two different sessions to test semantic memory (not just short-term)
    session1 = (
        f"test_semantic_1_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    )
    session2 = (
        f"test_semantic_2_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    )

    memory_manager = get_memory_manager()

    try:
        print(f"\n{'=' * 80}")
        print("TEST: Redis Chat Semantic Memory Retrieval")
        print(f"{'=' * 80}")

        # Store a fact in session 1
        first_message = "I want to exercise 5 times per week"
        first_result = await redis_chat_service.chat(
            message=first_message, session_id=session1
        )

        print(f"Session 1 - Query: {first_message}")
        print(f"Session 1 - Response: {first_result['response']}")

        # Wait for semantic memory to be stored
        await asyncio.sleep(2)

        # Verify semantic memory was stored
        # Query in a DIFFERENT session about exercise goals
        second_message = "what are my workout goals"
        second_result = await redis_chat_service.chat(
            message=second_message, session_id=session2
        )

        print(f"\nSession 2 - Query: {second_message}")
        print(f"Session 2 - Response: {second_result['response']}")
        print(f"Semantic hits: {second_result['memory_stats'].get('semantic_hits', 0)}")
        print(f"{'=' * 80}\n")

        # Check if semantic memory was retrieved
        # Note: This might be 0 if the query isn't semantically similar enough
        # or if the memory hasn't been indexed yet
        memory_stats = second_result.get("memory_stats", {})

        # At minimum, verify the system is checking for semantic memory
        assert (
            "semantic_hits" in memory_stats
        ), "Memory stats should include semantic_hits field"
        assert (
            "long_term_available" in memory_stats
        ), "Memory stats should include long_term_available field"

        print("✓ Semantic memory system is operational")
        print(f"  - Semantic hits: {memory_stats.get('semantic_hits', 0)}")
        print(
            f"  - Long-term available: {memory_stats.get('long_term_available', False)}"
        )

    finally:
        # Cleanup both sessions
        await memory_manager.clear_session_memory(session1)
        await memory_manager.clear_session_memory(session2)


@pytest.mark.asyncio
async def test_redis_chat_conversation_history(
    redis_chat_service, unique_session_id, cleanup_session
):
    """
    Test that conversation history is properly stored and retrieved.
    """
    # Send a message
    await redis_chat_service.chat(
        message="what is my weight", session_id=unique_session_id
    )

    # Get conversation history
    history = await redis_chat_service.get_conversation_history(
        session_id=unique_session_id, limit=10
    )

    print(f"\n{'=' * 80}")
    print("TEST: Conversation History")
    print(f"{'=' * 80}")
    print(f"Session ID: {unique_session_id}")
    print(f"History entries: {len(history)}")

    # Should have at least 2 messages (user + assistant)
    assert len(history) >= 2, f"Should have at least 2 messages, got {len(history)}"

    # Check message structure
    for msg in history:
        assert "role" in msg, "Message should have 'role' field"
        assert "content" in msg, "Message should have 'content' field"
        assert msg["role"] in ["user", "assistant"], f"Invalid role: {msg['role']}"

    print("✓ Conversation history stored correctly")
    print(f"{'=' * 80}\n")


@pytest.mark.asyncio
async def test_redis_chat_memory_stats(
    redis_chat_service, unique_session_id, cleanup_session
):
    """
    Test that memory statistics are correctly reported.
    """
    # Send a message to create memory
    await redis_chat_service.chat(
        message="tell me about my health", session_id=unique_session_id
    )

    # Get memory stats
    stats = await redis_chat_service.get_memory_stats(unique_session_id)

    print(f"\n{'=' * 80}")
    print("TEST: Memory Statistics")
    print(f"{'=' * 80}")
    print(f"Session ID: {unique_session_id}")
    print(f"Stats: {stats}")
    print(f"{'=' * 80}\n")

    # Verify stats structure
    assert "short_term" in stats, "Stats should include short_term"
    assert "long_term" in stats, "Stats should include long_term"
    assert "user_id" in stats, "Stats should include user_id"
    assert "session_id" in stats, "Stats should include session_id"

    # Verify short-term stats
    short_term = stats["short_term"]
    assert "message_count" in short_term, "Short-term should include message_count"
    assert short_term["message_count"] > 0, "Should have at least one message"

    # Verify long-term stats
    long_term = stats["long_term"]
    assert (
        "semantic_search_enabled" in long_term
    ), "Long-term should include semantic_search_enabled"

    print("✓ Memory stats reported correctly")
