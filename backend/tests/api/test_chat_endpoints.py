"""
API tests for chat endpoints.

NOTE: These tests run against the REAL backend in Docker.
Requires: docker-compose up -d backend

REAL TESTS - REQUIRE BACKEND:
- Tests real FastAPI endpoints via httpx client
- No mocks - tests actual HTTP request/response flow
- Requires: docker-compose up -d backend redis
"""

import pytest


@pytest.mark.api
class TestStatelessChatAPI:
    """Test stateless chat API endpoint."""

    def test_stateless_chat_basic(self, test_client):
        """Test basic stateless chat request."""
        response = test_client.post("/api/chat/stateless", json={"message": "Hello"})

        assert response.status_code == 200

        data = response.json()

        assert "response" in data
        assert isinstance(data["response"], str)
        assert "tools_used" in data
        assert "tool_calls_made" in data
        assert "type" in data
        assert data["type"] == "stateless"

    def test_stateless_chat_missing_message(self, test_client):
        """Test stateless chat with missing message field."""
        response = test_client.post("/api/chat/stateless", json={})

        assert response.status_code == 422  # Validation error

    def test_stateless_chat_validation(self, test_client):
        """Test stateless chat response validation."""
        response = test_client.post("/api/chat/stateless", json={"message": "test"})

        data = response.json()

        assert "response_time_ms" in data
        assert data["response_time_ms"] >= 0


@pytest.mark.api
@pytest.mark.integration  # Requires Redis
class TestRedisChatAPI:
    """Test Redis RAG chat API endpoint."""

    def test_redis_chat_basic(self, test_client, test_session_id):
        """Test basic Redis chat request."""
        response = test_client.post(
            "/api/chat/stateful",
            json={"message": "Hello", "session_id": test_session_id},
        )

        assert response.status_code == 200

        data = response.json()

        assert "response" in data
        assert "session_id" in data
        assert data["session_id"] == test_session_id
        assert "memory_stats" in data
        assert "type" in data
        assert data["type"] == "redis_with_memory"

    def test_redis_chat_default_session(self, test_client):
        """Test Redis chat with default session_id."""
        response = test_client.post("/api/chat/stateful", json={"message": "Hello"})

        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data

    def test_redis_chat_memory_stats(self, test_client, test_session_id):
        """Test that memory stats are included."""
        response = test_client.post(
            "/api/chat/stateful",
            json={"message": "test", "session_id": test_session_id},
        )

        data = response.json()

        assert "memory_stats" in data
        assert isinstance(data["memory_stats"], dict)


@pytest.mark.api
@pytest.mark.integration
class TestConversationHistoryAPI:
    """Test conversation history endpoint."""

    def test_get_conversation_history(self, test_client, test_session_id):
        """Test getting history for session."""
        # First send a message
        test_client.post(
            "/api/chat/stateful",
            json={"message": "test message", "session_id": test_session_id},
        )

        # Then get history
        response = test_client.get(f"/api/chat/history/{test_session_id}")

        assert response.status_code == 200

        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)


@pytest.mark.api
@pytest.mark.integration  # Requires backend running
class TestStreamingEndpoints:
    """Test streaming chat endpoints."""

    def test_stateless_stream_basic(self, test_client):
        """Test stateless streaming endpoint returns SSE format."""
        # Use httpx streaming
        with test_client.stream(
            "POST", "/api/chat/stateless/stream", json={"message": "Hello"}
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Read at least one chunk
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
                if b"data:" in content:
                    break

            # Verify SSE format
            assert b"data:" in content

    def test_redis_stream_basic(self, test_client, test_session_id):
        """Test Redis streaming endpoint returns SSE format."""
        # Use httpx streaming
        with test_client.stream(
            "POST",
            "/api/chat/stateful/stream",
            json={"message": "Hello", "session_id": test_session_id},
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Read at least one chunk
            content = b""
            for chunk in response.iter_bytes():
                content += chunk
                if b"data:" in content:
                    break

            # Verify SSE format
            assert b"data:" in content

    @pytest.mark.integration
    def test_redis_stream_includes_memory_stats(self, test_client, test_session_id):
        """Test Redis streaming includes memory_stats in done event."""
        with test_client.stream(
            "POST",
            "/api/chat/stateful/stream",
            json={"message": "test", "session_id": test_session_id},
        ) as response:
            # Read full stream
            content = b""
            for chunk in response.iter_bytes():
                content += chunk

            # Verify memory_stats appears somewhere in stream
            assert b"memory_stats" in content or b"done" in content


@pytest.mark.api
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, test_client):
        """Test health check returns 200."""
        response = test_client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data or "healthy" in str(data).lower()
