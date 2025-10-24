"""
Integration tests for workout data queries.

Validates that both stateless and Redis chat agents can successfully
retrieve and respond with actual workout data instead of "no workouts" messages.

NOTE: These tests require:
- Ollama running locally (http://localhost:11434)
- Redis running locally (localhost:6379)
- Health data imported into Redis

Set OLLAMA_BASE_URL=http://localhost:11434 if running tests outside Docker.
"""

import os

import pytest
from fastapi.testclient import TestClient

from src.main import app

# Override Ollama URL for local testing (outside Docker)
os.environ["OLLAMA_BASE_URL"] = os.environ.get(
    "OLLAMA_BASE_URL", "http://localhost:11434"
)

client = TestClient(app)


@pytest.mark.integration
class TestWorkoutDataRetrieval:
    """Test that workout queries return real data, not 'no workouts' messages."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup test session IDs."""
        self.stateless_test_query = "tell me about my recent workouts"
        self.redis_test_session = "workout_test_session"

    def test_stateless_chat_returns_workout_data(self):
        """Test stateless chat handles workout queries correctly."""
        response = client.post(
            "/api/chat/stateless",
            json={"message": self.stateless_test_query},
        )

        assert response.status_code == 200

        data = response.json()

        # Validate response structure
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

        # Should have called workout-related tools
        assert "tools_used" in data
        assert isinstance(data["tools_used"], list)
        assert (
            len(data["tools_used"]) > 0
        ), "Expected tools to be called for workout query"

        response_lower = data["response"].lower()

        # CRITICAL TEST: If agent says "no workouts", tool results MUST confirm it
        if "haven't worked out" in response_lower or "no workout" in response_lower:
            pytest.fail(
                f"Agent returned 'no workouts' message but this indicates missing or stale data.\n"
                f"Response: {data['response']}\n"
                f"Tools used: {data['tools_used']}\n"
                f"\nEither:\n"
                f"1. Import recent workout data into Redis\n"
                f"2. Check if workout data is being filtered incorrectly (check dates)\n"
                f"3. Verify health data import worked correctly"
            )

    def test_redis_chat_returns_workout_data(self):
        """Test Redis chat handles workout queries correctly."""
        response = client.post(
            "/api/chat/redis",
            json={
                "message": self.stateless_test_query,
                "session_id": self.redis_test_session,
            },
        )

        assert response.status_code == 200

        data = response.json()

        # Validate response structure
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

        # Should have called workout-related tools
        assert "tools_used" in data
        assert isinstance(data["tools_used"], list)
        assert (
            len(data["tools_used"]) > 0
        ), "Expected tools to be called for workout query"

        # Redis chat should have memory stats
        assert "memory_stats" in data
        assert isinstance(data["memory_stats"], dict)

        response_lower = data["response"].lower()

        # CRITICAL TEST: If agent says "no workouts", tool results MUST confirm it
        if "haven't worked out" in response_lower or "no workout" in response_lower:
            pytest.fail(
                f"Agent returned 'no workouts' message but this indicates missing or stale data.\n"
                f"Response: {data['response']}\n"
                f"Tools used: {data['tools_used']}\n"
                f"\nEither:\n"
                f"1. Import recent workout data into Redis\n"
                f"2. Check if workout data is being filtered incorrectly (check dates)\n"
                f"3. Verify health data import worked correctly"
            )

    def test_stateless_chat_workout_tools_called(self):
        """Verify that workout-related tools are being invoked."""
        response = client.post(
            "/api/chat/stateless",
            json={"message": "what workouts did I do this week?"},
        )

        assert response.status_code == 200

        data = response.json()

        # Check that workout tools were called
        tools_used = data.get("tools_used", [])
        tool_names = [
            tool["name"] if isinstance(tool, dict) else tool for tool in tools_used
        ]

        # Should use workout-related tools
        workout_tool_keywords = [
            "workout",
            "activity",
            "exercise",
            "search_workouts",
            "get_workout",
        ]

        has_workout_tool = any(
            any(keyword in tool_name.lower() for keyword in workout_tool_keywords)
            for tool_name in tool_names
        )

        assert (
            has_workout_tool
        ), f"Expected workout-related tools to be called, but got: {tool_names}"

    def test_redis_chat_workout_tools_called(self):
        """Verify that Redis chat invokes workout-related tools."""
        response = client.post(
            "/api/chat/redis",
            json={
                "message": "show me my recent exercise activities",
                "session_id": "workout_tools_test",
            },
        )

        assert response.status_code == 200

        data = response.json()

        # Check that workout tools were called
        tools_used = data.get("tools_used", [])
        tool_names = [
            tool["name"] if isinstance(tool, dict) else tool for tool in tools_used
        ]

        # Should use workout-related tools
        workout_tool_keywords = [
            "workout",
            "activity",
            "exercise",
            "search_workouts",
            "get_workout",
        ]

        has_workout_tool = any(
            any(keyword in tool_name.lower() for keyword in workout_tool_keywords)
            for tool_name in tool_names
        )

        assert (
            has_workout_tool
        ), f"Expected workout-related tools to be called, but got: {tool_names}"

    def test_comparison_both_agents_return_workout_data(self):
        """Compare both agents to ensure they handle workout queries consistently."""
        query = "tell me about my recent workouts"

        # Test stateless
        stateless_response = client.post(
            "/api/chat/stateless",
            json={"message": query},
        )

        # Test Redis
        redis_response = client.post(
            "/api/chat/redis",
            json={"message": query, "session_id": "comparison_test"},
        )

        assert stateless_response.status_code == 200
        assert redis_response.status_code == 200

        stateless_data = stateless_response.json()
        redis_data = redis_response.json()

        # Both should have called tools
        assert len(stateless_data.get("tools_used", [])) > 0
        assert len(redis_data.get("tools_used", [])) > 0

        # Check if either agent says "no workouts"
        stateless_lower = stateless_data["response"].lower()
        redis_lower = redis_data["response"].lower()

        no_workout_phrases = ["haven't worked out", "no workout"]
        stateless_has_no_workout = any(
            phrase in stateless_lower for phrase in no_workout_phrases
        )
        redis_has_no_workout = any(
            phrase in redis_lower for phrase in no_workout_phrases
        )

        if stateless_has_no_workout or redis_has_no_workout:
            error_parts = []
            if stateless_has_no_workout:
                error_parts.append(f"Stateless: {stateless_data['response']}")
            if redis_has_no_workout:
                error_parts.append(f"Redis: {redis_data['response']}")

            pytest.fail(
                "One or both agents returned 'no workouts' message:\n\n"
                + "\n\n".join(error_parts)
                + "\n\nThis indicates missing or stale workout data. Check import status."
            )
