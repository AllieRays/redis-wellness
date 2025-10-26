"""
Unit tests for consolidated health query tools.

Tests the 6 consolidated health tools without requiring real LLM or Redis.
Focuses on tool creation, parameter validation, and docstring quality.
"""

import pytest

from src.apple_health.query_tools import (
    create_get_activity_comparison_tool,
    create_get_health_metrics_tool,
    create_get_trends_tool,
    create_get_workout_patterns_tool,
    create_get_workout_progress_tool,
    create_get_workouts_tool,
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

    def test_create_get_workouts_tool(self):
        """Test get_workouts tool creation."""
        tool = create_get_workouts_tool(user_id="test_user")

        assert tool is not None
        assert tool.name == "get_workouts"
        assert callable(tool.func)

    def test_create_get_trends_tool(self):
        """Test get_trends tool creation."""
        tool = create_get_trends_tool(user_id="test_user")

        assert tool is not None
        assert tool.name == "get_trends"
        assert callable(tool.func)

    def test_create_get_activity_comparison_tool(self):
        """Test get_activity_comparison tool creation."""
        tool = create_get_activity_comparison_tool(user_id="test_user")

        assert tool is not None
        assert tool.name == "get_activity_comparison"
        assert callable(tool.func)

    def test_create_get_workout_patterns_tool(self):
        """Test get_workout_patterns tool creation."""
        tool = create_get_workout_patterns_tool(user_id="test_user")

        assert tool is not None
        assert tool.name == "get_workout_patterns"
        assert callable(tool.func)

    def test_create_get_workout_progress_tool(self):
        """Test get_workout_progress tool creation."""
        tool = create_get_workout_progress_tool(user_id="test_user")

        assert tool is not None
        assert tool.name == "get_workout_progress"
        assert callable(tool.func)


@pytest.mark.unit
class TestToolDocstrings:
    """Test that all tool docstrings follow the standard template for Qwen."""

    def test_get_health_metrics_docstring_structure(self):
        """Test get_health_metrics has proper docstring structure."""
        tool = create_get_health_metrics_tool(user_id="test_user")
        docstring = tool.description

        # Must have key sections for Qwen
        assert "USE WHEN" in docstring
        assert "DO NOT USE" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Examples:" in docstring

        # Must have clear alternatives
        assert "get_trends" in docstring  # Alternative tool mentioned

        # No emojis allowed
        assert "🎯" not in docstring
        assert "✅" not in docstring
        assert "⚠️" not in docstring

    def test_get_workouts_docstring_structure(self):
        """Test get_workouts has proper docstring structure."""
        tool = create_get_workouts_tool(user_id="test_user")
        docstring = tool.description

        assert "USE WHEN" in docstring
        assert "DO NOT USE" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Examples:" in docstring

        # No emojis
        assert "🎯" not in docstring
        assert "✅" not in docstring

    def test_get_trends_docstring_structure(self):
        """Test get_trends has proper docstring structure."""
        tool = create_get_trends_tool(user_id="test_user")
        docstring = tool.description

        assert "USE WHEN" in docstring
        assert "DO NOT USE" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Examples:" in docstring

        # No emojis
        assert "🎯" not in docstring

    def test_get_activity_comparison_docstring_structure(self):
        """Test get_activity_comparison has proper docstring structure."""
        tool = create_get_activity_comparison_tool(user_id="test_user")
        docstring = tool.description

        assert "USE WHEN" in docstring
        assert "DO NOT USE" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Examples:" in docstring

    def test_get_workout_patterns_docstring_structure(self):
        """Test get_workout_patterns has proper docstring structure."""
        tool = create_get_workout_patterns_tool(user_id="test_user")
        docstring = tool.description

        assert "USE WHEN" in docstring
        assert "DO NOT USE" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Examples:" in docstring

        # Must mention alternative tools
        assert "get_workouts" in docstring

    def test_get_workout_progress_docstring_structure(self):
        """Test get_workout_progress has proper docstring structure."""
        tool = create_get_workout_progress_tool(user_id="test_user")
        docstring = tool.description

        assert "USE WHEN" in docstring
        assert "DO NOT USE" in docstring
        assert "Args:" in docstring
        assert "Returns:" in docstring
        assert "Examples:" in docstring


@pytest.mark.unit
class TestToolSignatures:
    """Test that tool signatures match expected parameters."""

    def test_get_health_metrics_parameters(self):
        """Test get_health_metrics has correct parameters."""
        tool = create_get_health_metrics_tool(user_id="test_user")

        # Check function signature via args_schema if available
        # LangChain tools use Pydantic models for validation
        assert hasattr(tool, "args_schema") or hasattr(tool, "args")

    def test_get_trends_has_analysis_type_parameter(self):
        """Test get_trends supports analysis_type parameter for branching."""
        tool = create_get_trends_tool(user_id="test_user")
        docstring = tool.description

        # Must document the branching parameter
        assert "analysis_type" in docstring
        assert "trend" in docstring
        assert "comparison" in docstring

    def test_get_workout_patterns_has_analysis_type_parameter(self):
        """Test get_workout_patterns supports analysis_type parameter."""
        tool = create_get_workout_patterns_tool(user_id="test_user")
        docstring = tool.description

        # Must document the branching parameter
        assert "analysis_type" in docstring
        assert "schedule" in docstring
        assert "intensity" in docstring


@pytest.mark.unit
class TestToolConsolidation:
    """Test that consolidation achieved the goals."""

    def test_total_tool_count(self):
        """Test that we have exactly 6 health tools (reduced from 9)."""
        from src.apple_health.query_tools import create_user_bound_tools

        # Create tools WITHOUT memory (health only)
        health_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=False,
        )

        assert len(health_tools) == 6, "Should have exactly 6 health tools"

    def test_total_tool_count_with_memory(self):
        """Test that we have 8 total tools (6 health + 2 memory)."""
        from src.apple_health.query_tools import create_user_bound_tools

        # Create tools WITH memory
        all_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=True,
        )

        assert len(all_tools) == 8, "Should have 8 total tools (6 health + 2 memory)"

    def test_all_tool_names_use_get_verb(self):
        """Test that all tools use natural 'get_*' naming."""
        from src.apple_health.query_tools import create_user_bound_tools

        all_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=True,
        )

        for tool in all_tools:
            # All tools should start with "get_" or be memory tools
            assert (
                tool.name.startswith("get_") or tool.name == "store_user_goal"
            ), f"Tool {tool.name} doesn't follow get_* naming convention"

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
class TestDocstringQualityForQwen:
    """Test that docstrings are optimized for LLM understanding."""

    def test_all_tools_have_concrete_examples(self):
        """Test that all tools include concrete Query→Call examples."""
        from src.apple_health.query_tools import create_user_bound_tools

        health_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=False,
        )

        for tool in health_tools:
            docstring = tool.description

            # Must have example section
            assert "Examples:" in docstring, f"{tool.name} missing Examples section"

            # Must show query pattern
            assert "Query:" in docstring, f"{tool.name} missing Query examples"

            # Must show function call
            assert "Call:" in docstring, f"{tool.name} missing Call examples"

    def test_all_tools_document_alternatives(self):
        """Test that all tools clearly state when NOT to use them."""
        from src.apple_health.query_tools import create_user_bound_tools

        health_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=False,
        )

        for tool in health_tools:
            docstring = tool.description

            # Must have DO NOT USE section
            assert (
                "DO NOT USE" in docstring
            ), f"{tool.name} missing 'DO NOT USE' guidance"

            # Must mention at least one alternative with arrow
            assert (
                "→" in docstring or "->" in docstring
            ), f"{tool.name} doesn't point to alternatives"

    def test_no_emojis_in_any_docstrings(self):
        """Test that no tools use emojis in docstrings (Qwen clarity)."""
        from src.apple_health.query_tools import create_user_bound_tools

        all_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=True,
        )

        emoji_chars = ["🎯", "✅", "❌", "⚠️", "🔢", "📊", "🏃"]

        for tool in all_tools:
            docstring = tool.description
            for emoji in emoji_chars:
                assert (
                    emoji not in docstring
                ), f"{tool.name} contains emoji {emoji} in docstring"


@pytest.mark.unit
class TestStatelessAgentToolCount:
    """Test that stateless agent gets correct tool subset."""

    def test_stateless_has_no_memory_tools(self):
        """Test stateless agent receives 6 health tools only."""
        from src.apple_health.query_tools import create_user_bound_tools

        stateless_tools = create_user_bound_tools(
            user_id="test_user",
            include_memory_tools=False,  # Stateless baseline
        )

        assert len(stateless_tools) == 6

        tool_names = [t.name for t in stateless_tools]

        # Should NOT have memory tools
        assert "get_my_goals" not in tool_names
        assert "get_tool_suggestions" not in tool_names

        # Should have all health tools
        assert "get_health_metrics" in tool_names
        assert "get_workouts" in tool_names
        assert "get_trends" in tool_names
        assert "get_activity_comparison" in tool_names
        assert "get_workout_patterns" in tool_names
        assert "get_workout_progress" in tool_names
