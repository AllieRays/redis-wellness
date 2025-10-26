"""
Unit tests for goal_tools.py.

Tests goal component extraction and validation logic without Redis.
"""

import pytest

from src.apple_health.query_tools.goal_tools import _extract_goal_components


class TestGoalComponentExtraction:
    """Test goal component extraction from natural language."""

    def test_weight_goal_lbs(self):
        """Extract weight goal in pounds."""
        result = _extract_goal_components("reach 150 lbs")
        assert result["metric"] == "weight"
        assert result["value"] == 150.0
        assert result["unit"] == "lbs"
        assert "150 lbs" in result["goal_text"]

    def test_weight_goal_kg(self):
        """Extract weight goal in kilograms."""
        result = _extract_goal_components("get to 68 kg")
        assert result["metric"] == "weight"
        assert result["value"] == 68.0
        assert result["unit"] == "kg"

    def test_weight_goal_decimal(self):
        """Extract weight goal with decimal value."""
        result = _extract_goal_components("weigh 145.5 pounds")
        assert result["metric"] == "weight"
        assert result["value"] == 145.5
        assert result["unit"] == "lbs"

    def test_distance_goal_miles(self):
        """Extract distance goal in miles."""
        result = _extract_goal_components("run 5 miles")
        assert result["metric"] == "distance"
        assert result["value"] == 5.0
        assert result["unit"] == "mi"

    def test_distance_goal_km(self):
        """Extract distance goal in kilometers."""
        result = _extract_goal_components("bike 10 km")
        assert result["metric"] == "distance"
        assert result["value"] == 10.0
        assert result["unit"] == "km"

    def test_steps_goal(self):
        """Extract steps goal."""
        result = _extract_goal_components("walk 10000 steps")
        assert result["metric"] == "steps"
        assert result["value"] == 10000
        assert result["unit"] == "count"

    def test_steps_goal_with_comma(self):
        """Extract steps goal with comma separator."""
        result = _extract_goal_components("hit 10,000 steps daily")
        assert result["metric"] == "steps"
        assert result["value"] == 10000
        assert result["unit"] == "count"

    def test_workout_frequency_goal(self):
        """Extract workout frequency goal."""
        result = _extract_goal_components("workout 4 times per week")
        assert result["metric"] == "workout_frequency"
        assert result["value"] == 4
        assert result["unit"] == "per_week"

    def test_workout_frequency_days(self):
        """Extract workout frequency with 'days' instead of 'times'."""
        result = _extract_goal_components("exercise 5 days a week")
        assert result["metric"] == "workout_frequency"
        assert result["value"] == 5
        assert result["unit"] == "per_week"

    def test_text_only_goal(self):
        """Handle text-only goals without structured data."""
        result = _extract_goal_components("never skip leg day")
        assert "goal_text" in result
        assert result["goal_text"] == "never skip leg day"
        assert "metric" not in result

    def test_complex_text_goal(self):
        """Handle complex text goal."""
        result = _extract_goal_components("improve my cardio endurance")
        assert "goal_text" in result
        assert "improve" in result["goal_text"]
        assert "metric" not in result

    def test_empty_goal(self):
        """Handle empty goal description."""
        result = _extract_goal_components("")
        assert result["goal_text"] == ""

    def test_number_without_context(self):
        """Don't extract number without proper context."""
        result = _extract_goal_components("goal is 150")
        # Should be text-only since no metric keyword
        assert "goal_text" in result
        # Should NOT extract as weight without context
        assert "metric" not in result or result.get("metric") != "weight"


class TestGoalToolValidation:
    """Test goal tool input validation."""

    def test_extract_preserves_original_text(self):
        """Ensure original text is preserved in goal_text."""
        original = "reach 150 lbs by summer"
        result = _extract_goal_components(original)
        assert result["goal_text"] == original

    def test_case_insensitive_extraction(self):
        """Extraction should be case-insensitive."""
        result1 = _extract_goal_components("REACH 150 LBS")
        result2 = _extract_goal_components("reach 150 lbs")
        assert result1["metric"] == result2["metric"]
        assert result1["value"] == result2["value"]

    def test_multiple_numbers_first_match(self):
        """With multiple numbers, extract the most relevant one."""
        result = _extract_goal_components("lose 10 lbs to reach 150 lbs")
        # Should extract the weight goal (either 10 or 150 is valid)
        assert result["metric"] == "weight"
        assert result["value"] in [10.0, 150.0]

    def test_whitespace_handling(self):
        """Handle extra whitespace gracefully."""
        result = _extract_goal_components("  reach   150   lbs  ")
        assert result["metric"] == "weight"
        assert result["value"] == 150.0


@pytest.mark.asyncio
class TestGoalStorageErrors:
    """Test error handling in goal storage."""

    async def test_empty_description_validation(self):
        """Empty descriptions should be rejected."""
        import json

        from src.apple_health.query_tools.goal_tools import store_user_goal

        # Test empty string
        result_str = await store_user_goal.ainvoke(
            {"goal_description": "", "user_id": "test_user"}
        )
        result = json.loads(result_str)
        assert result["status"] == "error"
        assert result["stored"] is False

    async def test_whitespace_only_description(self):
        """Whitespace-only descriptions should be rejected."""
        import json

        from src.apple_health.query_tools.goal_tools import store_user_goal

        result_str = await store_user_goal.ainvoke(
            {"goal_description": "   ", "user_id": "test_user"}
        )
        result = json.loads(result_str)
        assert result["status"] == "error"
        assert result["stored"] is False


class TestGoalExtractionEdgeCases:
    """Test edge cases in goal extraction."""

    def test_mixed_units(self):
        """Handle mixed units (should pick first match)."""
        result = _extract_goal_components("lose 5 kg and reach 150 lbs")
        assert result["metric"] == "weight"
        # Should match first weight pattern
        assert result["value"] in [5.0, 150.0]

    def test_no_keyword_with_unit(self):
        """Number with unit but no context keyword."""
        result = _extract_goal_components("my target is 150 lbs")
        # "target" isn't in our weight keywords, may or may not match
        if "metric" in result:
            assert result["metric"] == "weight"

    def test_workout_without_frequency(self):
        """Workout goal without numeric frequency."""
        result = _extract_goal_components("workout more consistently")
        # Should be text-only
        assert "goal_text" in result
        assert "metric" not in result

    def test_distance_without_activity_verb(self):
        """Distance with unit but no activity verb."""
        result = _extract_goal_components("cover 5 miles daily")
        # "cover" isn't in our distance keywords
        # Should still extract if pattern matches
        if "metric" in result:
            assert result["metric"] == "distance"
