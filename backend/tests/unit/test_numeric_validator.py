"""
Unit tests for numeric validator.

Tests:
- Number extraction from text
- Tool result parsing
- Response validation
- Hallucination detection
- Fuzzy matching tolerance
"""

import pytest

from src.utils.numeric_validator import NumericValidator, get_numeric_validator


class TestNumericValidator:
    """Test suite for NumericValidator."""

    def test_extract_numbers_basic(self):
        """Test basic number extraction."""
        validator = NumericValidator()

        text = "Your weight is 136.8 lb and BMI is 23.6"
        numbers = validator.extract_numbers_with_context(text)

        assert len(numbers) == 2
        assert numbers[0]["value"] == 136.8
        assert numbers[0]["unit"] == "lb"
        assert numbers[1]["value"] == 23.6
        assert numbers[1]["unit"] is None

    def test_extract_numbers_with_units(self):
        """Test extraction with various units."""
        validator = NumericValidator()

        text = "Heart rate: 70 bpm, Steps: 10000 count, Workout: 45 minutes"
        numbers = validator.extract_numbers_with_context(text)

        assert len(numbers) == 3
        assert numbers[0]["value"] == 70
        assert numbers[0]["unit"] == "bpm"
        assert numbers[1]["value"] == 10000
        assert numbers[1]["unit"] == "count"
        assert numbers[2]["value"] == 45
        assert numbers[2]["unit"] in ["min", "mins", "minutes"]

    def test_values_match_exact(self):
        """Test exact value matching."""
        validator = NumericValidator()

        assert validator.values_match(136.8, 136.8) is True
        assert validator.values_match(70.0, 70.0) is True

    def test_values_match_rounding(self):
        """Test fuzzy matching for rounding."""
        validator = NumericValidator()

        # Within 1.0 difference
        assert validator.values_match(70.2, 70.0) is True
        assert validator.values_match(136.8, 137.0) is True

    def test_values_match_percentage_tolerance(self):
        """Test percentage tolerance matching."""
        validator = NumericValidator(tolerance=0.1)  # 10%

        # 70 vs 72 = 2.8% difference
        assert validator.values_match(70.0, 72.0) is True

        # 70 vs 80 = 14.3% difference
        assert validator.values_match(70.0, 80.0) is False

    def test_extract_tool_numbers(self):
        """Test extracting numbers from tool results."""
        validator = NumericValidator()

        tool_results = [
            {
                "name": "search_health_records",
                "content": "Found 3 records: BodyMass 136.8 lb on Oct 17, "
                "HeartRate 70 bpm, BMI 23.6 count",
            }
        ]

        numbers = validator.extract_tool_numbers(tool_results)

        assert len(numbers) >= 3
        assert any(n["value"] == 136.8 and n["unit"] == "lb" for n in numbers)
        assert any(n["value"] == 70 and n["unit"] == "bpm" for n in numbers)
        assert any(n["value"] == 23.6 and n["unit"] == "count" for n in numbers)

    def test_validate_response_valid(self):
        """Test validation of correct response."""
        validator = NumericValidator()

        tool_results = [
            {
                "name": "aggregate_metrics",
                "content": "Average: 87.5 bpm, Min: 60 bpm, Max: 110 bpm",
            }
        ]

        response = "Your average heart rate was 87.5 bpm (min: 60 bpm, max: 110 bpm)"

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is True
        assert result["score"] == 1.0
        assert len(result["hallucinations"]) == 0
        assert len(result["matched"]) == 3

    def test_validate_response_hallucination(self):
        """Test detection of hallucinated numbers."""
        validator = NumericValidator()

        tool_results = [
            {"name": "search_health_records", "content": "BodyMass: 136.8 lb"}
        ]

        # Response with hallucinated number
        response = "Your weight is 140 lb (not in tool data)"

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is False
        assert len(result["hallucinations"]) > 0
        assert result["score"] < 1.0

    def test_validate_response_fuzzy_match(self):
        """Test fuzzy matching for rounded numbers."""
        validator = NumericValidator()

        tool_results = [{"name": "aggregate_metrics", "content": "Average: 87.5 bpm"}]

        # Response with rounded number (should pass with fuzzy matching)
        response = "Your average heart rate was 88 bpm"

        result = validator.validate_response(response, tool_results, strict=False)

        # Should pass with fuzzy matching
        assert result["valid"] is True or result["score"] >= 0.8

    def test_validate_response_no_numbers(self):
        """Test validation when response has no numbers."""
        validator = NumericValidator()

        tool_results = [{"name": "search_workouts", "content": "No workouts found"}]

        response = "No workout data available for the requested period."

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is True
        assert result["score"] == 1.0
        assert len(result["hallucinations"]) == 0

    def test_validate_response_numbers_but_no_tools(self):
        """Test when response has numbers but tools returned nothing."""
        validator = NumericValidator()

        tool_results = []  # No tool data

        response = "Your weight is 140 lb"

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is False
        assert len(result["hallucinations"]) > 0
        assert "no tool data available" in result["warnings"][0].lower()

    def test_correct_hallucinations(self):
        """Test correction of hallucinated numbers."""
        validator = NumericValidator()

        tool_results = [
            {"name": "search_health_records", "content": "BodyMass: 136.8 lb"}
        ]

        response = "Your weight is 140 lb and you weigh 150 pounds"

        validation_result = validator.validate_response(response, tool_results)
        corrected = validator.correct_hallucinations(response, validation_result)

        # Should contain replacement markers
        assert "[DATA NOT VERIFIED]" in corrected
        # Should not contain the hallucinated numbers
        assert "140" not in corrected or "[DATA NOT VERIFIED]" in corrected

    def test_mixed_valid_and_invalid_numbers(self):
        """Test response with both valid and hallucinated numbers."""
        validator = NumericValidator()

        tool_results = [
            {
                "name": "search_health_records",
                "content": "BodyMass: 136.8 lb, HeartRate: 70 bpm",
            }
        ]

        # Mix of valid and hallucinated
        response = "Your weight is 136.8 lb and heart rate is 90 bpm"

        result = validator.validate_response(response, tool_results)

        # Should detect partial validation
        assert len(result["matched"]) == 1  # 136.8 lb is correct
        assert len(result["hallucinations"]) == 1  # 90 bpm is wrong
        assert result["score"] == 0.5  # 50% valid

    def test_get_numeric_validator_singleton(self):
        """Test global validator singleton."""
        validator1 = get_numeric_validator()
        validator2 = get_numeric_validator()

        assert validator1 is validator2

    def test_validation_stats(self):
        """Test validation statistics in result."""
        validator = NumericValidator()

        tool_results = [
            {
                "name": "aggregate_metrics",
                "content": "Average: 87.5 bpm, Count: 100 readings",
            }
        ]

        response = "Average: 87.5 bpm from 100 readings"

        result = validator.validate_response(response, tool_results)

        assert "stats" in result
        assert result["stats"]["total_numbers"] == 2
        assert result["stats"]["matched"] == 2
        assert result["stats"]["hallucinated"] == 0
        assert result["stats"]["tool_numbers_available"] >= 2


class TestValidatorIntegration:
    """Integration tests for validator with realistic scenarios."""

    def test_realistic_weight_query(self):
        """Test realistic weight query scenario."""
        validator = NumericValidator()

        tool_results = [
            {
                "name": "search_health_records_by_metric",
                "content": """Found 5 records for BodyMass:
                - 2025-10-17: 136.8 lb
                - 2025-10-16: 137.2 lb
                - 2025-10-15: 136.5 lb
                - 2025-10-14: 137.0 lb
                - 2025-10-13: 136.9 lb""",
            }
        ]

        response = "Your weight on October 17 was 136.8 lb"

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is True
        assert result["score"] == 1.0

    def test_realistic_aggregate_query(self):
        """Test realistic aggregation scenario."""
        validator = NumericValidator()

        tool_results = [
            {
                "name": "aggregate_metrics",
                "content": "HeartRate statistics: average=87.5 bpm, min=65 bpm, max=110 bpm, count=150",
            }
        ]

        response = (
            "Over the last week, your average heart rate was 87.5 bpm. "
            "It ranged from 65 bpm to 110 bpm across 150 readings."
        )

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is True
        assert len(result["matched"]) == 4

    def test_realistic_hallucination_scenario(self):
        """Test realistic hallucination detection."""
        validator = NumericValidator()

        tool_results = [
            {
                "name": "search_health_records_by_metric",
                "content": "BodyMass: 136.8 lb, BMI: 23.6 count",
            }
        ]

        # LLM invents a "normal BMI range"
        response = (
            "Your weight is 136.8 lb and BMI is 23.6, "
            "which is within the normal range of 18.5-24.9"
        )

        result = validator.validate_response(response, tool_results)

        # Should flag the 18.5 and 24.9 as hallucinations
        assert len(result["hallucinations"]) >= 2
        assert result["score"] < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
