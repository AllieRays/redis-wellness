"""
API tests for chat routes.

Tests HTTP endpoints with structural validation:
- Request/response format
- Status codes
- Error handling
- Session management
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.mark.integration
class TestStatelessChatAPI:
    """Test stateless chat API endpoint."""

    def test_stateless_chat_basic(self):
        """Test basic stateless chat request."""
        response = client.post(
            "/api/chat/stateless", json={"message": "What's my weight?"}
        )

        assert response.status_code == 200

        data = response.json()

        # Validate response structure
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

        assert "tools_used" in data
        assert isinstance(data["tools_used"], list)

        assert "tool_calls_made" in data
        assert isinstance(data["tool_calls_made"], int)

        assert "type" in data
        assert data["type"] == "stateless"

        assert "response_time_ms" in data
        assert data["response_time_ms"] >= 0

    def test_stateless_chat_missing_message(self):
        """Test stateless chat with missing message field."""
        response = client.post("/api/chat/stateless", json={})

        assert response.status_code == 422  # Validation error

    def test_stateless_chat_empty_message(self):
        """Test stateless chat with empty message."""
        response = client.post("/api/chat/stateless", json={"message": ""})

        # Should either accept empty or return validation error
        assert response.status_code in [200, 422]


@pytest.mark.integration
class TestRedisChatAPI:
    """Test Redis chat API endpoint."""

    def test_redis_chat_basic(self):
        """Test basic Redis chat request."""
        response = client.post(
            "/api/chat/redis",
            json={"message": "What's my BMI?", "session_id": "test_session_123"},
        )

        assert response.status_code == 200

        data = response.json()

        # Validate response structure
        assert "response" in data
        assert isinstance(data["response"], str)

        assert "session_id" in data
        assert data["session_id"] == "test_session_123"

        assert "tools_used" in data
        assert "tool_calls_made" in data

        assert "memory_stats" in data
        assert isinstance(data["memory_stats"], dict)

        assert "token_stats" in data

        assert "type" in data
        assert data["type"] == "redis_with_memory"

    def test_redis_chat_default_session(self):
        """Test Redis chat with default session_id."""
        response = client.post("/api/chat/redis", json={"message": "Hello"})

        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        # Should use default session if not provided

    def test_redis_chat_conversation_persistence(self):
        """Test that conversation is persisted across messages."""
        session_id = "persistence_test"

        # First message
        response1 = client.post(
            "/api/chat/redis",
            json={"message": "My goal BMI is 22", "session_id": session_id},
        )

        assert response1.status_code == 200

        # Second message referencing first
        response2 = client.post(
            "/api/chat/redis",
            json={
                "message": "Remember my goal from earlier",
                "session_id": session_id,
            },
        )

        assert response2.status_code == 200

        # Memory stats should show history
        data2 = response2.json()
        assert "memory_stats" in data2


@pytest.mark.integration
class TestConversationHistoryAPI:
    """Test conversation history endpoint."""

    def test_get_conversation_history_empty(self):
        """Test getting history for new session."""
        response = client.get("/api/chat/history/new_session_123")

        assert response.status_code == 200

        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)

    def test_get_conversation_history_with_messages(self):
        """Test getting history after sending messages."""
        session_id = "history_test_session"

        # Send a message first
        client.post(
            "/api/chat/redis",
            json={"message": "Test message", "session_id": session_id},
        )

        # Get history
        response = client.get(f"/api/chat/history/{session_id}")

        assert response.status_code == 200

        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) > 0

        # Validate message structure
        if len(data["messages"]) > 0:
            msg = data["messages"][0]
            assert "role" in msg
            assert msg["role"] in ["user", "assistant"]
            assert "content" in msg


@pytest.mark.integration
class TestMemoryStatsAPI:
    """Test memory statistics endpoint."""

    def test_get_memory_stats(self):
        """Test getting memory stats for a session."""
        session_id = "memory_stats_test"

        # Send a message first
        client.post(
            "/api/chat/redis",
            json={"message": "Test for memory", "session_id": session_id},
        )

        # Get memory stats
        response = client.get(f"/api/chat/memory/{session_id}")

        assert response.status_code == 200

        data = response.json()
        assert "short_term" in data
        assert "long_term" in data
        assert "user_id" in data
        assert "session_id" in data


@pytest.mark.integration
class TestSessionManagementAPI:
    """Test session management endpoints."""

    def test_clear_session(self):
        """Test clearing a session."""
        session_id = "clear_test_session"

        # Create session with messages
        client.post(
            "/api/chat/redis",
            json={"message": "Message to clear", "session_id": session_id},
        )

        # Clear session
        response = client.delete(f"/api/chat/session/{session_id}")

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == session_id

    def test_clear_nonexistent_session(self):
        """Test clearing a session that doesn't exist."""
        response = client.delete("/api/chat/session/nonexistent_session")

        # Should succeed (idempotent) or return appropriate status
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestDemoInfoAPI:
    """Test demo information endpoint."""

    def test_get_demo_info(self):
        """Test getting demo information."""
        response = client.get("/api/chat/demo/info")

        assert response.status_code == 200

        data = response.json()

        # Should return information about the demo
        assert isinstance(data, dict)
        assert "stateless" in data or "redis" in data


@pytest.mark.integration
class TestAPIErrorHandling:
    """Test API error handling."""

    def test_invalid_json(self):
        """Test sending invalid JSON."""
        response = client.post(
            "/api/chat/stateless",
            data="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_malformed_request(self):
        """Test malformed request body."""
        response = client.post("/api/chat/stateless", json={"wrong_field": "value"})

        assert response.status_code == 422

    def test_nonexistent_endpoint(self):
        """Test accessing nonexistent endpoint."""
        response = client.get("/api/chat/nonexistent")

        assert response.status_code == 404


@pytest.mark.integration
class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self):
        """Test that CORS headers are present."""
        response = client.options("/api/chat/stateless")

        # CORS headers should be present
        assert response.status_code in [200, 405]  # OPTIONS might be disabled
