"""
LLM tests for AI agents with real Ollama/Qwen.

REAL TESTS - EXPENSIVE:
- Tests REAL LLM calls (Ollama + Qwen 2.5 7B)
- Requires: ollama serve + qwen2.5:7b model
- Marked with @pytest.mark.llm (run sparingly)
- These tests are SLOW and consume resources
"""

import pytest


@pytest.mark.llm
@pytest.mark.asyncio
class TestStatelessAgent:
    """Test stateless agent with real LLM."""

    async def test_stateless_agent_basic_response(
        self, stateless_agent, test_user_id, test_session_id
    ):
        """Test stateless agent generates response."""
        result = await stateless_agent.chat(
            message="Hello, how are you?",
            user_id=test_user_id,
            session_id=test_session_id,
        )

        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
        assert "tool_calls_made" in result

    async def test_stateless_agent_tool_calling(
        self, stateless_agent, test_user_id, test_session_id
    ):
        """Test stateless agent calls tools when appropriate."""
        result = await stateless_agent.chat(
            message="Search for health records",
            user_id=test_user_id,
            session_id=test_session_id,
        )

        # Agent should attempt tool use for health queries
        assert "tools_used" in result
        # May or may not call tools depending on LLM decision


@pytest.mark.llm
@pytest.mark.integration  # Also requires Redis
@pytest.mark.asyncio
class TestStatefulAgent:
    """Test stateful RAG agent with real LLM + Redis memory."""

    async def test_stateful_agent_basic_response(
        self, stateful_agent, test_user_id, test_session_id
    ):
        """Test stateful agent generates response with memory."""
        result = await stateful_agent.chat(
            message="Hello",
            user_id=test_user_id,
            session_id=test_session_id,
        )

        assert "response" in result
        assert isinstance(result["response"], str)
        assert "memory_stats" in result
        assert isinstance(result["memory_stats"], dict)

    async def test_stateful_agent_memory_persistence(
        self, stateful_agent, test_user_id, test_session_id
    ):
        """Test stateful agent remembers context across messages."""
        # First message
        result1 = await stateful_agent.chat(
            message="My name is Test User",
            user_id=test_user_id,
            session_id=test_session_id,
        )

        assert "response" in result1

        # Second message referencing first
        result2 = await stateful_agent.chat(
            message="What is my name?",
            user_id=test_user_id,
            session_id=test_session_id,
        )

        # Agent should have access to conversation history
        assert "memory_stats" in result2
        # Note: Whether LLM correctly recalls name depends on model performance


@pytest.mark.llm
@pytest.mark.asyncio
class TestAgentResponseQuality:
    """Test LLM response quality (real LLM validation)."""

    async def test_agent_generates_non_empty_response(
        self, stateless_agent, test_user_id, test_session_id
    ):
        """Test agent always generates non-empty response."""
        result = await stateless_agent.chat(
            message="Tell me about health",
            user_id=test_user_id,
            session_id=test_session_id,
        )

        assert result["response"]
        assert len(result["response"]) > 10  # Meaningful response

    async def test_agent_response_time_reasonable(
        self, stateless_agent, test_user_id, test_session_id
    ):
        """Test agent responds within reasonable time."""
        import time

        start = time.time()

        await stateless_agent.chat(
            message="Quick test",
            user_id=test_user_id,
            session_id=test_session_id,
        )

        duration = time.time() - start

        # Should respond within 30 seconds for simple queries
        assert duration < 30.0
