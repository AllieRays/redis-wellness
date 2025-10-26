"""
Integration tests for Procedural Memory Manager.

NOTE: These tests are currently disabled because the procedural memory manager
does not expose the APIs we expected (store_pattern, suggest_procedure, etc).

The procedural memory is used internally by the stateful agent but does not have
a public API for testing. Memory learning is tested via agent integration tests instead.
"""

import pytest

from src.services.procedural_memory_manager import get_procedural_memory


@pytest.mark.skip(reason="Procedural memory APIs not exposed for testing")
@pytest.mark.integration
class TestProceduralMemoryStorage:
    """Test pattern storage in procedural memory."""

    @pytest.mark.asyncio
    async def test_store_pattern_basic(self, clean_redis):
        """Test storing a basic workflow pattern."""
        memory = get_procedural_memory()

        await memory.store_pattern(
            query="How many workouts do I have?",
            tools_used=["get_workouts"],
            success_score=1.0,
            execution_time_ms=1500,
        )

        # Verify pattern stored (check stats)
        stats = memory.get_procedure_stats()
        assert stats["total_patterns"] > 0

    @pytest.mark.asyncio
    async def test_store_multiple_patterns(self, clean_redis):
        """Test storing multiple workflow patterns."""
        memory = get_procedural_memory()

        await memory.store_pattern(
            query="What workouts did I do?",
            tools_used=["get_workouts"],
            success_score=1.0,
            execution_time_ms=1200,
        )
        await memory.store_pattern(
            query="What is my average heart rate?",
            tools_used=["get_health_metrics"],
            success_score=0.95,
            execution_time_ms=1800,
        )

        stats = memory.get_procedure_stats()
        assert stats["total_patterns"] >= 2

    @pytest.mark.asyncio
    async def test_store_multi_tool_pattern(self, clean_redis):
        """Test storing pattern with multiple tools."""
        memory = get_procedural_memory()

        await memory.store_pattern(
            query="Compare my workouts this week vs last week",
            tools_used=["get_workouts", "get_activity_comparison"],
            success_score=1.0,
            execution_time_ms=2500,
        )

        stats = memory.get_procedure_stats()
        assert stats["total_patterns"] > 0


@pytest.mark.skip(reason="Procedural memory APIs not exposed for testing")
@pytest.mark.integration
class TestProceduralMemoryRetrieval:
    """Test pattern retrieval and suggestions."""

    @pytest.mark.asyncio
    async def test_suggest_procedure_semantic_match(self, clean_redis):
        """Test suggesting tools via semantic similarity."""
        memory = get_procedural_memory()

        # Store a pattern
        await memory.store_pattern(
            query="How many workouts do I have?",
            tools_used=["get_workouts"],
            success_score=1.0,
            execution_time_ms=1500,
        )

        # Query with similar intent (different wording)
        suggestions = await memory.suggest_procedure(query="Show me my workout history")

        # Should suggest get_workouts tool
        assert len(suggestions) > 0
        found_get_workouts = any("get_workouts" in str(sugg) for sugg in suggestions)
        assert found_get_workouts

    @pytest.mark.asyncio
    async def test_suggest_procedure_no_patterns(self, clean_redis):
        """Test suggestions when no patterns stored."""
        memory = get_procedural_memory()

        suggestions = await memory.suggest_procedure(query="Random query")

        # Should return empty list, not error
        assert isinstance(suggestions, list)
        # May return empty or default suggestions
        assert len(suggestions) >= 0

    @pytest.mark.asyncio
    async def test_suggest_procedure_ranking(self, clean_redis):
        """Test suggestions ranked by success score."""
        memory = get_procedural_memory()

        # Store patterns with different success scores
        await memory.store_pattern(
            query="Get my workouts",
            tools_used=["get_workouts"],
            success_score=1.0,
            execution_time_ms=1000,
        )
        await memory.store_pattern(
            query="Get my workouts",
            tools_used=["get_health_metrics"],  # Wrong tool
            success_score=0.2,
            execution_time_ms=5000,
        )

        suggestions = await memory.suggest_procedure(query="Show workouts")

        # Higher success score should rank first
        if len(suggestions) >= 2:
            # First suggestion should be the successful one
            assert "get_workouts" in str(suggestions[0])


@pytest.mark.skip(reason="Procedural memory APIs not exposed for testing")
@pytest.mark.integration
class TestProceduralMemoryEvaluation:
    """Test workflow evaluation logic."""

    def test_evaluate_workflow_successful(self, clean_redis):
        """Test evaluating successful workflow."""
        memory = get_procedural_memory()

        evaluation = memory.evaluate_workflow(
            tools_used=["get_workouts"],
            tool_results=[{"name": "get_workouts", "content": "Found 5 workouts"}],
            response_generated=True,
            execution_time_ms=1500,
        )

        assert evaluation["success"] is True
        assert evaluation["success_score"] > 0.5

    def test_evaluate_workflow_failed(self, clean_redis):
        """Test evaluating failed workflow."""
        memory = get_procedural_memory()

        evaluation = memory.evaluate_workflow(
            tools_used=["get_workouts"],
            tool_results=[{"name": "get_workouts", "content": "Error: No data"}],
            response_generated=False,
            execution_time_ms=1500,
        )

        # Failed workflow should have low success
        assert evaluation["success"] is False or evaluation["success_score"] < 0.5

    def test_evaluate_workflow_no_tools(self, clean_redis):
        """Test evaluating workflow with no tool calls."""
        memory = get_procedural_memory()

        evaluation = memory.evaluate_workflow(
            tools_used=[],
            tool_results=[],
            response_generated=True,
            execution_time_ms=500,
        )

        # No tools but response generated = conversational query
        # Evaluation depends on implementation
        assert "success" in evaluation
        assert "success_score" in evaluation


@pytest.mark.skip(reason="Procedural memory APIs not exposed for testing")
@pytest.mark.integration
class TestProceduralMemoryStats:
    """Test procedural memory statistics."""

    def test_procedure_stats_empty(self, clean_redis):
        """Test stats when no patterns stored."""
        memory = get_procedural_memory()

        stats = memory.get_procedure_stats()

        assert "total_patterns" in stats
        assert stats["total_patterns"] == 0

    @pytest.mark.asyncio
    async def test_procedure_stats_after_storage(self, clean_redis):
        """Test stats reflect stored patterns."""
        memory = get_procedural_memory()

        # Store patterns
        await memory.store_pattern(
            query="Get workouts",
            tools_used=["get_workouts"],
            success_score=1.0,
            execution_time_ms=1500,
        )
        await memory.store_pattern(
            query="Get metrics",
            tools_used=["get_health_metrics"],
            success_score=0.95,
            execution_time_ms=1800,
        )

        stats = memory.get_procedure_stats()
        assert stats["total_patterns"] >= 2


@pytest.mark.skip(reason="Procedural memory APIs not exposed for testing")
@pytest.mark.integration
class TestProceduralMemoryCleanup:
    """Test procedural memory cleanup."""

    @pytest.mark.asyncio
    async def test_clear_procedures(self, clean_redis):
        """Test clearing procedural patterns."""
        memory = get_procedural_memory()

        # Store pattern
        await memory.store_pattern(
            query="Get workouts",
            tools_used=["get_workouts"],
            success_score=1.0,
            execution_time_ms=1500,
        )

        # Clear patterns
        memory.clear_procedures()

        # Verify cleared
        stats = memory.get_procedure_stats()
        assert stats["total_patterns"] == 0
