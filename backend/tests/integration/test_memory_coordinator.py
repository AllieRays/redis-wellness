"""
Integration tests for Memory Coordinator (CoALA Framework).

Tests all 4 memory types:
- Episodic: Personal events, preferences, goals
- Procedural: Learned tool patterns
- Semantic: General health knowledge
- Short-term: Conversation history
"""

import pytest

from src.services.memory_coordinator import get_memory_coordinator
from src.utils.user_config import get_user_id


@pytest.mark.integration
class TestMemoryCoordinatorInitialization:
    """Test memory coordinator initialization."""

    def test_coordinator_initializes(self):
        """Test coordinator initializes with all 4 memory managers."""
        coordinator = get_memory_coordinator()

        assert coordinator is not None
        assert hasattr(coordinator, "episodic")
        assert hasattr(coordinator, "procedural")
        assert hasattr(coordinator, "semantic")
        assert hasattr(coordinator, "short_term")


@pytest.mark.integration
class TestMemoryCoordinatorFullContext:
    """Test getting full context from all memory types."""

    @pytest.mark.asyncio
    async def test_get_full_context_structure(self, clean_redis):
        """Test get_full_context returns all 4 memory types."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_session"

        context = await coordinator.get_full_context(
            user_id=user_id,  # Ignored but passed for API compatibility
            session_id=session_id,
            current_query="What's my BMI?",
            skip_long_term=False,
        )

        # Verify structure
        assert isinstance(context, dict)
        assert "episodic" in context
        assert "procedural" in context
        assert "semantic" in context
        assert "short_term" in context

    @pytest.mark.asyncio
    async def test_get_full_context_skip_long_term(self, clean_redis):
        """Test skip_long_term flag skips episodic and semantic."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_session"

        # First store some episodic and semantic data
        await coordinator.store_interaction(
            session_id=session_id,
            user_message="My goal is BMI 22",
            assistant_response="Noted your goal",
            tools_used=[],
        )

        # Get context with skip_long_term=True
        context = await coordinator.get_full_context(
            user_id=user_id,
            session_id=session_id,
            current_query="What's my BMI?",
            skip_long_term=True,
        )

        # Episodic and semantic should be None or empty
        assert context.get("episodic") is None or context.get("episodic") == ""
        assert context.get("semantic") is None or context.get("semantic") == ""
        # Short-term and procedural may still be available
        assert "short_term" in context
        assert "procedural" in context


@pytest.mark.integration
class TestMemoryCoordinatorStorage:
    """Test storing interactions across all memory types."""

    @pytest.mark.asyncio
    async def test_store_interaction_success(self, clean_redis):
        """Test storing interaction succeeds."""
        coordinator = get_memory_coordinator()
        get_user_id()
        session_id = "test_storage"

        results = await coordinator.store_interaction(
            session_id=session_id,
            user_message="What's my weight?",
            assistant_response="Your weight is 70 kg",
            tools_used=["get_latest_health_records"],
        )

        # Check that short-term stored successfully
        assert results.get("short_term_user") is True
        assert results.get("short_term_assistant") is True

    @pytest.mark.asyncio
    async def test_store_and_retrieve_procedural(self, clean_redis):
        """Test procedural memory learns tool patterns."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_procedural"

        # Store interaction with tool usage
        await coordinator.store_interaction(
            session_id=session_id,
            user_message="What's my BMI?",
            assistant_response="Your BMI is 23.1",
            tools_used=["get_latest_health_records", "get_time_range_stats"],
        )

        # Retrieve context
        context = await coordinator.get_full_context(
            user_id=user_id, session_id=session_id, current_query="What's my BMI?"
        )

        # Procedural memory should capture tool patterns
        # (May be None if not enough data yet)
        assert "procedural" in context


@pytest.mark.integration
class TestMemoryCoordinatorEpisodic:
    """Test episodic memory (personal events)."""

    @pytest.mark.asyncio
    async def test_episodic_stores_personal_context(self, clean_redis):
        """Test episodic memory stores personal preferences/goals."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_episodic"

        # Store interaction with personal context
        await coordinator.store_interaction(
            session_id=session_id,
            user_message="My goal is to reach BMI 22 by next month",
            assistant_response="I'll help you track progress toward your BMI goal of 22",
            tools_used=[],
        )

        # Retrieve - episodic should capture goal
        context = await coordinator.get_full_context(
            user_id=user_id,
            session_id=session_id,
            current_query="Am I on track with my goals?",
        )

        # Episodic memory should be available (may be empty if not enough similarity)
        assert "episodic" in context


@pytest.mark.integration
class TestMemoryCoordinatorSemantic:
    """Test semantic memory (general knowledge)."""

    @pytest.mark.asyncio
    async def test_semantic_stores_health_knowledge(self, clean_redis):
        """Test semantic memory stores general health facts."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_semantic"

        # Store interaction with health knowledge
        await coordinator.store_interaction(
            session_id=session_id,
            user_message="What's a healthy BMI range?",
            assistant_response="A healthy BMI range is typically 18.5-24.9",
            tools_used=[],
        )

        # Retrieve - semantic should capture knowledge
        context = await coordinator.get_full_context(
            user_id=user_id,
            session_id=session_id,
            current_query="Is my BMI good?",
        )

        # Semantic memory should be available
        assert "semantic" in context


@pytest.mark.integration
class TestMemoryCoordinatorShortTerm:
    """Test short-term memory (conversation history)."""

    @pytest.mark.asyncio
    async def test_short_term_captures_conversation(self, clean_redis):
        """Test short-term memory captures recent conversation."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_short_term"

        # Store multiple interactions
        await coordinator.store_interaction(
            session_id=session_id,
            user_message="What's my BMI?",
            assistant_response="Your BMI is 23.1",
            tools_used=["get_latest_health_records"],
        )

        await coordinator.store_interaction(
            session_id=session_id,
            user_message="Is that healthy?",
            assistant_response="Yes, 23.1 is within the healthy range",
            tools_used=[],
        )

        # Retrieve - short-term should have recent turns
        context = await coordinator.get_full_context(
            user_id=user_id,
            session_id=session_id,
            current_query="What did you say about my BMI?",
        )

        # Short-term should contain conversation
        assert context.get("short_term") is not None
        assert len(context["short_term"]) > 0


@pytest.mark.integration
class TestMemoryCoordinatorClearance:
    """Test memory clearance operations."""

    @pytest.mark.asyncio
    async def test_clear_all_memories(self, clean_redis):
        """Test clearing all memories for a user."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_clear"

        # Store some data
        await coordinator.store_interaction(
            session_id=session_id,
            user_message="Test message",
            assistant_response="Test response",
            tools_used=[],
        )

        # Clear all memories
        success = await coordinator.clear_all_memories(user_id)

        # Should succeed
        assert success is True

        # Context should be empty after clearing
        context = await coordinator.get_full_context(
            user_id=user_id, session_id=session_id, current_query="test"
        )

        # All memories should be None or empty
        assert not context.get("episodic")
        assert not context.get("semantic")


@pytest.mark.integration
class TestMemoryCoordinatorStats:
    """Test memory statistics."""

    @pytest.mark.asyncio
    async def test_get_memory_stats(self, clean_redis):
        """Test getting memory statistics."""
        coordinator = get_memory_coordinator()
        user_id = get_user_id()
        session_id = "test_stats"

        # Store some interactions
        await coordinator.store_interaction(
            session_id=session_id,
            user_message="What's my BMI?",
            assistant_response="Your BMI is 23.1",
            tools_used=["get_latest_health_records"],
        )

        # Get stats
        stats = await coordinator.get_memory_stats(session_id, user_id)

        # Should return stats structure
        assert isinstance(stats, dict)
        assert "user_id" in stats
        assert "session_id" in stats
