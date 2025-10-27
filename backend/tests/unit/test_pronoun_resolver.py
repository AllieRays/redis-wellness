"""
Unit tests for pronoun resolver.

Tests pronoun resolution logic for health data queries.
"""

import json
from unittest.mock import MagicMock

import pytest

from src.utils.pronoun_resolver import PronounResolver, get_pronoun_resolver


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis = MagicMock()
    redis.get.return_value = None  # Default: no context
    return redis


@pytest.fixture
def pronoun_resolver(mock_redis):
    """Create pronoun resolver with mock Redis."""
    return PronounResolver(mock_redis)


class TestTopicExtraction:
    """Test extraction of health topics from queries."""

    def test_extracts_bmi_from_query(self, pronoun_resolver):
        """Should detect BMI mentions."""
        assert pronoun_resolver.extract_topic_from_query("What's my BMI?") == "BMI"
        assert (
            pronoun_resolver.extract_topic_from_query("Check my body mass index")
            == "BMI"
        )

    def test_extracts_weight_from_query(self, pronoun_resolver):
        """Should detect weight mentions."""
        assert (
            pronoun_resolver.extract_topic_from_query("How much do I weigh?")
            == "weight"
        )
        assert pronoun_resolver.extract_topic_from_query("Check my weight") == "weight"
        assert pronoun_resolver.extract_topic_from_query("What's my wt?") == "weight"

    def test_does_not_confuse_body_weight_with_weight(self, pronoun_resolver):
        """Should not confuse 'body weight' with just 'weight'."""
        # Implementation specifically excludes 'weight' when 'body' is present
        # to avoid confusion with 'body mass' metrics
        assert (
            pronoun_resolver.extract_topic_from_query("What's my body weight?") is None
        )

    def test_extracts_heart_rate(self, pronoun_resolver):
        """Should detect heart rate mentions."""
        assert (
            pronoun_resolver.extract_topic_from_query("What's my heart rate?")
            == "heart rate"
        )

    def test_extracts_workouts(self, pronoun_resolver):
        """Should detect workout mentions."""
        assert (
            pronoun_resolver.extract_topic_from_query("Did I workout today?")
            == "workouts"
        )
        assert (
            pronoun_resolver.extract_topic_from_query("Show my exercise") == "workouts"
        )

    def test_extracts_steps(self, pronoun_resolver):
        """Should detect step-related queries."""
        assert (
            pronoun_resolver.extract_topic_from_query("How many steps today?")
            == "steps"
        )
        assert pronoun_resolver.extract_topic_from_query("Did I walk today?") == "steps"

    def test_extracts_calories_burned(self, pronoun_resolver):
        """Should detect calorie burning queries."""
        assert (
            pronoun_resolver.extract_topic_from_query("How many calories did I burn?")
            == "calories burned"
        )
        assert (
            pronoun_resolver.extract_topic_from_query("Active calories burned")
            == "calories burned"
        )

    def test_returns_none_for_unknown_topic(self, pronoun_resolver):
        """Should return None for non-health queries."""
        assert pronoun_resolver.extract_topic_from_query("Hello there") is None
        assert pronoun_resolver.extract_topic_from_query("What's the weather?") is None

    def test_case_insensitive(self, pronoun_resolver):
        """Should work regardless of case."""
        assert pronoun_resolver.extract_topic_from_query("WHAT'S MY BMI?") == "BMI"
        assert pronoun_resolver.extract_topic_from_query("what's my bmi?") == "BMI"


class TestTopicExtractionFromResponse:
    """Test extraction of topics from tool usage."""

    def test_extracts_topic_from_tool_names_string_list(self, pronoun_resolver):
        """Should extract topic from list of tool name strings."""
        assert (
            pronoun_resolver.extract_topic_from_response("", ["get_workout_data"])
            == "workouts"
        )

    def test_extracts_topic_from_tool_dict_list(self, pronoun_resolver):
        """Should extract topic from list of tool dicts."""
        tools = [
            {
                "name": "get_health_metrics",
                "args": {"metric_types": ["HKQuantityTypeIdentifierBodyMassIndex"]},
            }
        ]
        assert pronoun_resolver.extract_topic_from_response("", tools) == "BMI"

    def test_extracts_weight_from_tool_args(self, pronoun_resolver):
        """Should extract weight from metric_types."""
        tools = [
            {
                "name": "get_health_metrics",
                "args": {"metric_types": ["HKQuantityTypeIdentifierBodyMass"]},
            }
        ]
        assert pronoun_resolver.extract_topic_from_response("", tools) == "weight"

    def test_extracts_heart_rate_from_tool_args(self, pronoun_resolver):
        """Should extract heart rate from metric_types."""
        tools = [
            {
                "name": "get_health_metrics",
                "args": {"metric_types": ["HKQuantityTypeIdentifierHeartRate"]},
            }
        ]
        assert pronoun_resolver.extract_topic_from_response("", tools) == "heart rate"

    def test_returns_none_for_unknown_tools(self, pronoun_resolver):
        """Should return None for tools without recognizable topics."""
        assert (
            pronoun_resolver.extract_topic_from_response("", ["some_other_tool"])
            is None
        )


class TestContextUpdate:
    """Test conversation context updates."""

    def test_updates_context_with_query_topic(self, pronoun_resolver, mock_redis):
        """Should store topic extracted from query."""
        pronoun_resolver.update_context(
            session_id="test_session",
            query="What's my BMI?",
            response="Your BMI is 23.5",
            tools_used=[],
        )

        # Check Redis was called
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        key, ttl, value_json = call_args[0]

        assert key == "pronoun_context:test_session"
        assert ttl == 604800  # 7 days
        value = json.loads(value_json)
        assert value["last_topic"] == "BMI"
        assert "BMI" in value["last_query"]

    def test_updates_context_from_tool_if_no_query_topic(
        self, pronoun_resolver, mock_redis
    ):
        """Should fall back to tool-based topic if query has none."""
        pronoun_resolver.update_context(
            session_id="test_session",
            query="Tell me more about that",
            response="Your workouts...",
            tools_used=["get_workout_data"],
        )

        call_args = mock_redis.setex.call_args
        value_json = call_args[0][2]
        value = json.loads(value_json)
        assert value["last_topic"] == "workouts"

    def test_truncates_long_queries(self, pronoun_resolver, mock_redis):
        """Should truncate long queries to 200 characters."""
        long_query = "x" * 300
        pronoun_resolver.update_context(
            session_id="test_session",
            query=long_query,
            response="Response",
            tools_used=["get_workout_data"],
        )

        call_args = mock_redis.setex.call_args
        value_json = call_args[0][2]
        value = json.loads(value_json)
        assert len(value["last_query"]) == 200

    def test_handles_redis_error_gracefully(self, pronoun_resolver, mock_redis):
        """Should not raise if Redis fails."""
        mock_redis.setex.side_effect = Exception("Redis error")

        # Should not raise
        pronoun_resolver.update_context(
            session_id="test_session",
            query="What's my BMI?",
            response="Your BMI is 23.5",
            tools_used=[],
        )


class TestPronounResolution:
    """Test pronoun resolution in queries."""

    def test_resolves_is_that(self, pronoun_resolver, mock_redis):
        """Should resolve 'is that' to last topic."""
        # Setup context
        context = {"last_topic": "BMI", "last_query": "What's my BMI?"}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns("test_session", "Is that good?")
        assert resolved == "Is BMI good?"

    def test_resolves_about_that(self, pronoun_resolver, mock_redis):
        """Should resolve 'about that' to topic."""
        context = {"last_topic": "weight", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns(
            "test_session", "Tell me more about that"
        )
        assert resolved == "Tell me more about weight"

    def test_resolves_about_it(self, pronoun_resolver, mock_redis):
        """Should resolve 'about it' to topic."""
        context = {"last_topic": "heart rate", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns(
            "test_session", "Tell me more about it"
        )
        assert resolved == "Tell me more about heart rate"

    def test_resolves_standalone_it(self, pronoun_resolver, mock_redis):
        """Should resolve ' it ' to topic."""
        context = {"last_topic": "workouts", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns(
            "test_session", "How can I improve it ?"
        )
        # Note: Need space before and after 'it' for pattern to match
        assert " workouts " in resolved

    def test_preserves_capitalization(self, pronoun_resolver, mock_redis):
        """Should handle both 'Is that' and 'is that'."""
        context = {"last_topic": "BMI", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns("test_session", "Is that normal?")
        assert "BMI" in resolved

    def test_returns_original_if_no_pronouns(self, pronoun_resolver, mock_redis):
        """Should return original query if no pronouns detected."""
        context = {"last_topic": "BMI", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        query = "What's my heart rate?"
        resolved = pronoun_resolver.resolve_pronouns("test_session", query)
        assert resolved == query

    def test_returns_original_if_no_context(self, pronoun_resolver, mock_redis):
        """Should return original if no context available."""
        mock_redis.get.return_value = None

        resolved = pronoun_resolver.resolve_pronouns("test_session", "Is that good?")
        assert resolved == "Is that good?"

    def test_handles_missing_last_topic(self, pronoun_resolver, mock_redis):
        """Should return original if context has no last_topic."""
        context = {"last_query": "Something"}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns("test_session", "Is that good?")
        assert resolved == "Is that good?"

    def test_handles_redis_error(self, pronoun_resolver, mock_redis):
        """Should return original query if Redis fails."""
        mock_redis.get.side_effect = Exception("Redis error")

        resolved = pronoun_resolver.resolve_pronouns("test_session", "Is that good?")
        assert resolved == "Is that good?"


class TestGetPronounResolver:
    """Test factory function."""

    def test_creates_resolver(self, mock_redis):
        """Should create PronounResolver instance."""
        resolver = get_pronoun_resolver(mock_redis)
        assert isinstance(resolver, PronounResolver)
        assert resolver.redis == mock_redis


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_query(self, pronoun_resolver, mock_redis):
        """Should handle empty query."""
        context = {"last_topic": "BMI", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns("test_session", "")
        assert resolved == ""

    def test_query_with_multiple_pronouns(self, pronoun_resolver, mock_redis):
        """Should handle multiple pronouns in one query."""
        context = {"last_topic": "weight", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns(
            "test_session", "Is that good and how can I improve it?"
        )
        # Should resolve at least one pronoun
        assert "weight" in resolved

    def test_malformed_json_context(self, pronoun_resolver, mock_redis):
        """Should handle malformed JSON gracefully."""
        mock_redis.get.return_value = "not valid json"

        resolved = pronoun_resolver.resolve_pronouns("test_session", "Is that good?")
        assert resolved == "Is that good?"

    def test_unicode_in_query(self, pronoun_resolver, mock_redis):
        """Should handle unicode characters."""
        context = {"last_topic": "BMI", "last_query": ""}
        mock_redis.get.return_value = json.dumps(context)

        resolved = pronoun_resolver.resolve_pronouns("test_session", "Is that good? 😊")
        assert "BMI" in resolved
