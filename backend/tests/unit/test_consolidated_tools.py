"""
Unit tests for consolidated health query tools.

Tests the 2 consolidated health tools without requiring real LLM or Redis.
Focuses on tool creation, parameter validation, and docstring quality.
"""

import pytest

from src.apple_health.query_tools import (
    create_get_health_metrics_tool,
    create_get_workout_data_tool,
)


@pytest.mark.unit
class TestToolCreation:
    """Test that all tools can be created successfully."""

    def test_create_get_health_metrics_tool(self):
        """Test get_health_metrics tool creation."""
        tool = create_get_health_metrics_tool(user_id="test_user")

        assert tool is not None
        assert tool.name == "get_health_metrics"
        assert callable(tool.func)

    def test_create_get_workout_data_tool(self):
        """Test get_workout_data tool creation (consolidated workout tool)."""
        tool = create_get_workout_data_tool(user_id="test_user")

        assert tool is not None
        assert tool.name == "get_workout_data"
        assert callable(tool.func)
        # Verify it has the consolidated parameters
        assert "include_patterns" in tool.description
        assert "include_progress" in tool.description


@pytest.mark.unit
class TestToolDocstrings:
    """Test that all tool docstrings follow the standard template."""

    def test_get_health_metrics_docstring_structure(self):
        """Test get_health_metrics has proper docstring structure."""
        tool = create_get_health_metrics_tool(user_id="test_user")
        docstring = tool.description

        # Must have key sections
        assert "USE" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring

    def test_get_workout_data_docstring_structure(self):
        """Test get_workout_data has proper docstring structure."""
        tool = create_get_workout_data_tool(user_id="test_user")
        docstring = tool.description

        # New consolidated tool has different structure (no "USE" section)
        assert "ONE tool for ALL workout" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Examples:" in docstring


@pytest.mark.unit
class TestToolConsolidation:
    """Test that consolidation achieved the goals."""

    def test_total_tool_count(self):
        """Test that we have exactly 3 health tools (metrics, sleep, workouts)."""
        from src.apple_health.query_tools import create_user_bound_tools

        # Create tools WITHOUT memory (health only)
        health_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=False,
        )

        assert len(health_tools) == 3, "Should have exactly 3 health tools"

    def test_total_tool_count_with_memory(self):
        """Test that we have 5 total tools (3 health + 2 memory)."""
        from src.apple_health.query_tools import create_user_bound_tools

        # Create tools WITH memory
        all_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=True,
        )

        assert len(all_tools) == 5, "Should have 5 total tools (3 health + 2 memory)"

    def test_all_tool_names_use_get_verb(self):
        """Test that all tools use natural 'get_*' naming."""
        from src.apple_health.query_tools import create_user_bound_tools

        all_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=True,
        )

        for tool in all_tools:
            # All tools should start with "get_"
            assert tool.name.startswith("get_"), (
                f"Tool {tool.name} doesn't follow get_* naming convention"
            )

    def test_no_duplicate_tool_names(self):
        """Test that all tool names are unique."""
        from src.apple_health.query_tools import create_user_bound_tools

        all_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=True,
        )

        tool_names = [tool.name for tool in all_tools]
        assert len(tool_names) == len(set(tool_names)), "Tool names must be unique"


@pytest.mark.unit
class TestStatelessAgentToolCount:
    """Test that stateless agent gets correct tool subset."""

    def test_stateless_has_no_memory_tools(self):
        """Test stateless agent receives 3 health tools only."""
        from src.apple_health.query_tools import create_user_bound_tools

        stateless_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=False,  # Stateless baseline
        )

        assert len(stateless_tools) == 3

        tool_names = [t.name for t in stateless_tools]

        # Should NOT have memory tools
        assert "get_my_goals" not in tool_names
        assert "get_tool_suggestions" not in tool_names

        # Should have all health tools
        assert "get_health_metrics" in tool_names
        assert "get_sleep_analysis" in tool_names
        assert "get_workout_data" in tool_names
