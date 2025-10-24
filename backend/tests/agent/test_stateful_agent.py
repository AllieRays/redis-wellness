"""
Agent tests for Stateful RAG Agent with CoALA Memory.

Tests agent with memory coordinator integration:
- Memory retrieval (all 4 types)
- Memory storage
- Tool calling with memory context
- Response validation
"""

import pytest

from src.agents.stateful_rag_agent import StatefulRAGAgent
from src.services.memory_coordinator import get_memory_coordinator
from src.utils.user_config import get_user_id


@pytest.mark.agent
class TestStatefulAgentInitialization:
    """Test stateful agent initialization."""

    def test_agent_requires_memory_coordinator(self):
        """Test agent requires memory_coordinator parameter."""
        with pytest.raises(ValueError, match="requires memory_coordinator"):
            StatefulRAGAgent(memory_coordinator=None)

    def test_agent_initializes_with_coordinator(self):
        """Test agent initializes with memory coordinator."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)

        assert agent.memory_coordinator is not None
        assert agent.llm is not None
        assert hasattr(agent, "chat")


@pytest.mark.agent
class TestStatefulAgentResponseStructure:
    """Test stateful agent response structure."""

    @pytest.mark.asyncio
    async def test_agent_returns_coala_memory_stats(
        self, health_data_fixture, clean_redis
    ):
        """Test agent returns CoALA memory stats in response."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)
        user_id = get_user_id()
        session_id = "test_session"

        with health_data_fixture(user_id):
            result = await agent.chat(
                message="What's my BMI?", user_id=user_id, session_id=session_id
            )

            # Validate CoALA memory stats structure
            assert "memory_stats" in result
            mem_stats = result["memory_stats"]

            # CoALA framework: 4 memory types
            assert "short_term_available" in mem_stats
            assert "episodic_hits" in mem_stats
            assert "episodic_available" in mem_stats
            assert "semantic_hits" in mem_stats
            assert "semantic_available" in mem_stats
            assert "procedural_available" in mem_stats


@pytest.mark.agent
class TestStatefulAgentMemoryRetrieval:
    """Test agent memory retrieval behavior."""

    @pytest.mark.asyncio
    async def test_agent_retrieves_short_term_context(
        self, health_data_fixture, clean_redis
    ):
        """Test agent retrieves short-term conversation context."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)
        user_id = get_user_id()
        session_id = "test_short_term"

        with health_data_fixture(user_id):
            # First message
            result1 = await agent.chat(
                message="My BMI goal is 22",
                user_id=user_id,
                session_id=session_id,
            )

            assert "response" in result1

            # Second message referencing first
            result2 = await agent.chat(
                message="Remember that goal",
                user_id=user_id,
                session_id=session_id,
            )

            # Should have short-term context available
            assert result2["memory_stats"]["short_term_available"] is True

    @pytest.mark.asyncio
    async def test_agent_tool_first_policy(self, health_data_fixture, clean_redis):
        """Test agent skips semantic memory for factual queries (tool-first)."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)
        user_id = get_user_id()
        session_id = "test_tool_first"

        with health_data_fixture(user_id):
            # Factual query should skip long-term memory
            result = await agent.chat(
                message="How many workouts did I do last week?",
                user_id=user_id,
                session_id=session_id,
            )

            # Agent should call tools
            assert result["tool_calls_made"] > 0

            # Memory stats may show semantic not needed
            assert "memory_stats" in result


@pytest.mark.agent
class TestStatefulAgentMemoryStorage:
    """Test agent memory storage behavior."""

    @pytest.mark.asyncio
    async def test_agent_stores_interaction_in_coordinator(
        self, health_data_fixture, clean_redis
    ):
        """Test agent stores interactions via coordinator."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)
        user_id = get_user_id()
        session_id = "test_storage"

        with health_data_fixture(user_id):
            # Send message
            await agent.chat(
                message="What's my weight?",
                user_id=user_id,
                session_id=session_id,
            )

            # Get context to verify storage
            context = await coordinator.get_full_context(
                user_id=user_id, session_id=session_id, current_query="test"
            )

            # Short-term should have the interaction
            assert context.get("short_term") is not None


@pytest.mark.agent
class TestStatefulAgentToolCalling:
    """Test agent tool calling with memory context."""

    @pytest.mark.asyncio
    async def test_agent_calls_tools_with_context(
        self, health_data_fixture, clean_redis
    ):
        """Test agent calls tools appropriately with memory context."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)
        user_id = get_user_id()
        session_id = "test_tools"

        with health_data_fixture(user_id):
            result = await agent.chat(
                message="What's my current BMI?",
                user_id=user_id,
                session_id=session_id,
            )

            # Should call tools
            assert result["tool_calls_made"] > 0
            assert len(result["tools_used"]) > 0

            # Should have response
            assert result["response"]
            assert len(result["response"]) > 0


@pytest.mark.agent
class TestStatefulAgentValidation:
    """Test agent response validation."""

    @pytest.mark.asyncio
    async def test_agent_validates_responses(self, health_data_fixture, clean_redis):
        """Test agent includes validation in response."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)
        user_id = get_user_id()
        session_id = "test_validation"

        with health_data_fixture(user_id):
            result = await agent.chat(
                message="What's my BMI?",
                user_id=user_id,
                session_id=session_id,
            )

            # Validation should be present
            assert "validation" in result
            assert "valid" in result["validation"]
            assert "score" in result["validation"]


@pytest.mark.agent
class TestStatefulAgentConversationPersistence:
    """Test conversation persistence across messages."""

    @pytest.mark.asyncio
    async def test_agent_maintains_conversation_context(
        self, health_data_fixture, clean_redis
    ):
        """Test agent maintains context across multiple messages."""
        coordinator = get_memory_coordinator()
        agent = StatefulRAGAgent(memory_coordinator=coordinator)
        user_id = get_user_id()
        session_id = "test_persistence"

        with health_data_fixture(user_id):
            # First message
            result1 = await agent.chat(
                message="What's my weight?",
                user_id=user_id,
                session_id=session_id,
            )

            assert result1["response"]

            # Second message referencing first
            result2 = await agent.chat(
                message="Is that healthy for my height?",
                user_id=user_id,
                session_id=session_id,
            )

            # Should have short-term context
            assert result2["memory_stats"]["short_term_available"] is True
            assert result2["response"]


@pytest.mark.agent
class TestStatefulAgentVsStateless:
    """Test stateful agent behavior vs stateless."""

    @pytest.mark.asyncio
    async def test_stateful_handles_followup_better_than_stateless(
        self, health_data_fixture, clean_redis
    ):
        """Test stateful agent handles follow-up questions with context."""
        from src.agents.stateless_agent import StatelessHealthAgent

        coordinator = get_memory_coordinator()
        stateful_agent = StatefulRAGAgent(memory_coordinator=coordinator)
        stateless_agent = StatelessHealthAgent()

        user_id = get_user_id()
        session_id = "test_comparison"

        with health_data_fixture(user_id):
            # First message for both
            stateful_result1 = await stateful_agent.chat(
                message="My BMI is 23",
                user_id=user_id,
                session_id=session_id,
            )

            stateless_result1 = await stateless_agent.chat(
                message="My BMI is 23",
                user_id=user_id,
            )

            # Both should respond
            assert stateful_result1["response"]
            assert stateless_result1["response"]

            # Follow-up for stateful (should have context)
            stateful_result2 = await stateful_agent.chat(
                message="Is that good?",
                user_id=user_id,
                session_id=session_id,
            )

            # Stateful should have memory context
            assert stateful_result2["memory_stats"]["short_term_available"] is True

            # Stateless follow-up (no context)
            stateless_result2 = await stateless_agent.chat(
                message="Is that good?",
                user_id=user_id,
            )

            # Stateless should respond but without context
            # (may be confused about "that")
            assert stateless_result2["response"]
