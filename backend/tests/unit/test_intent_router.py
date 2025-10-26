"""
Unit tests for intent router - goal detection and pre-routing logic.

Tests the pre-router that detects goal-setting statements and bypasses
tool calling for instant responses.
"""

import pytest

from src.utils.intent_router import (
    extract_goal_from_statement,
    is_goal_retrieval_question,
    is_goal_setting_statement,
    should_bypass_tools,
)


class TestGoalSettingDetection:
    """Test detection of goal-setting statements."""

    def test_detects_my_goal_is(self):
        """Should detect 'my goal is' pattern."""
        assert is_goal_setting_statement("my goal is to lose weight")
        assert is_goal_setting_statement("My goal is to work out 3x per week")
        assert is_goal_setting_statement("MY GOAL IS to never skip leg day")

    def test_detects_i_want_to(self):
        """Should detect 'I want to' pattern."""
        assert is_goal_setting_statement("i want to run a marathon")
        assert is_goal_setting_statement("I want to get stronger")

    def test_detects_i_plan_to(self):
        """Should detect 'I plan to' pattern."""
        assert is_goal_setting_statement("i plan to exercise daily")

    def test_detects_my_target_is(self):
        """Should detect 'my target is' pattern."""
        assert is_goal_setting_statement("my target is 150 lbs")

    def test_does_not_detect_questions(self):
        """Should NOT detect questions as goal-setting."""
        assert not is_goal_setting_statement("did I work out?")
        assert not is_goal_setting_statement("what is my goal?")
        assert not is_goal_setting_statement("how am I doing with my goal?")

    def test_does_not_detect_factual_queries(self):
        """Should NOT detect factual queries as goal-setting."""
        assert not is_goal_setting_statement("tell me about my workouts")
        assert not is_goal_setting_statement("show me my heart rate")

    def test_case_insensitive(self):
        """Should work regardless of case."""
        assert is_goal_setting_statement("MY GOAL IS to run")
        assert is_goal_setting_statement("My Goal Is to run")
        assert is_goal_setting_statement("my goal is to run")


class TestGoalRetrievalDetection:
    """Test detection of goal retrieval questions."""

    def test_detects_what_is_my_goal(self):
        """Should detect 'what is my goal' pattern."""
        assert is_goal_retrieval_question("what is my goal")
        assert is_goal_retrieval_question("what is my goal?")
        assert is_goal_retrieval_question("What is my goal?")

    def test_detects_whats_my_goal(self):
        """Should detect 'what's my goal' contraction."""
        assert is_goal_retrieval_question("what's my goal")
        assert is_goal_retrieval_question("What's my goal?")

    def test_detects_tell_me_my_goal(self):
        """Should detect 'tell me my goal' pattern."""
        assert is_goal_retrieval_question("tell me my goal")

    def test_detects_remind_me(self):
        """Should detect 'remind me of my goal' pattern."""
        assert is_goal_retrieval_question("remind me of my goal")

    def test_does_not_detect_goal_setting(self):
        """Should NOT detect goal-setting as retrieval."""
        assert not is_goal_retrieval_question("my goal is to exercise")

    def test_does_not_detect_goal_progress(self):
        """Should NOT detect goal progress queries as simple retrieval."""
        assert not is_goal_retrieval_question("how am I doing with my goal")
        assert not is_goal_retrieval_question("am I meeting my goal")


class TestGoalExtraction:
    """Test extraction of goal text from statements."""

    def test_extracts_after_my_goal_is(self):
        """Should extract text after 'my goal is'."""
        goal = extract_goal_from_statement("my goal is to lose 10 pounds")
        assert goal == "to lose 10 pounds"

    def test_extracts_after_i_want_to(self):
        """Should extract text after 'I want to'."""
        goal = extract_goal_from_statement("I want to run 5k every week")
        assert goal == "run 5k every week"

    def test_preserves_original_case(self):
        """Should preserve the original text case."""
        goal = extract_goal_from_statement("My goal is to Never Skip Leg Day")
        assert "Never Skip Leg Day" in goal

    def test_handles_extra_whitespace(self):
        """Should handle extra whitespace."""
        goal = extract_goal_from_statement("my goal is   to exercise daily")
        assert goal == "to exercise daily"

    def test_fallback_returns_full_message(self):
        """Should return full message if no pattern matches."""
        message = "random text without pattern"
        goal = extract_goal_from_statement(message)
        assert goal == message


class TestShouldBypassTools:
    """Test the main pre-router decision logic."""

    @pytest.mark.asyncio
    async def test_bypasses_for_goal_setting(self):
        """Should bypass tools for goal-setting statements."""
        should_bypass, response, intent = await should_bypass_tools(
            "my goal is to never skip leg day"
        )

        assert should_bypass is True
        assert intent == "goal_setting"
        assert "never skip leg day" in response
        assert "saved" in response.lower() or "got it" in response.lower()

    @pytest.mark.asyncio
    async def test_bypasses_for_goal_retrieval(self):
        """Should bypass tools for goal retrieval (even if empty)."""
        should_bypass, response, intent = await should_bypass_tools("what is my goal")

        assert should_bypass is True
        assert intent == "goal_retrieval"
        # Response should either have goal or say "no goal set"

    @pytest.mark.asyncio
    async def test_does_not_bypass_for_factual_queries(self):
        """Should NOT bypass tools for factual health queries."""
        should_bypass, response, intent = await should_bypass_tools(
            "did I work out on Friday"
        )

        assert should_bypass is False
        assert response is None
        assert intent is None

    @pytest.mark.asyncio
    async def test_does_not_bypass_for_workout_queries(self):
        """Should NOT bypass tools for workout questions."""
        should_bypass, response, intent = await should_bypass_tools(
            "tell me about my recent workouts"
        )

        assert should_bypass is False
        assert response is None
        assert intent is None

    @pytest.mark.asyncio
    async def test_extracts_goal_in_response(self):
        """Goal-setting response should include the extracted goal."""
        message = "my goal is to run a marathon"
        should_bypass, response, intent = await should_bypass_tools(message)

        assert should_bypass is True
        assert "marathon" in response

    @pytest.mark.asyncio
    async def test_handles_empty_message(self):
        """Should handle empty message gracefully."""
        should_bypass, response, intent = await should_bypass_tools("")

        assert should_bypass is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_goal_with_special_characters(self):
        """Should handle goals with special characters."""
        assert is_goal_setting_statement("my goal is to lose 10% body fat")
        goal = extract_goal_from_statement("my goal is to lose 10% body fat")
        assert "10% body fat" in goal

    def test_multiline_goal(self):
        """Should handle multiline goal statements."""
        message = "my goal is to exercise daily\nand eat healthy"
        assert is_goal_setting_statement(message)

    def test_goal_with_numbers(self):
        """Should handle goals with numeric values."""
        assert is_goal_setting_statement("my goal is to reach 125 lbs")
        goal = extract_goal_from_statement("my goal is to reach 125 lbs")
        assert "125 lbs" in goal

    @pytest.mark.asyncio
    async def test_very_long_goal(self):
        """Should handle very long goal statements."""
        long_goal = "my goal is " + "to exercise " * 100
        should_bypass, response, intent = await should_bypass_tools(long_goal)

        assert should_bypass is True
        assert intent == "goal_setting"
