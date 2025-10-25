"""
Unit tests for NumericValidator - LLM hallucination detection.

REAL TESTS - NO MOCKS:
- Tests pure validation logic with real tool results
- Tests extraction of numbers with units
- Tests hallucination detection accuracy
"""

import pytest

from src.utils.numeric_validator import NumericValidator, get_numeric_validator


@pytest.mark.unit
class TestNumericValidatorExtraction:
    """Test number extraction with context."""

    def test_extract_simple_numbers(self):
        """Test extracting plain numbers."""
        validator = NumericValidator()
        text = "Your weight is 70.2 and your BMI is 23.6"

        numbers = validator.extract_numbers_with_context(text)

        assert len(numbers) == 2
        assert numbers[0]["value"] == 70.2
        assert numbers[1]["value"] == 23.6

    def test_extract_numbers_with_units(self):
        """Test extracting numbers with health units."""
        validator = NumericValidator()
        text = "Weight: 136.8 lb, Heart rate: 72 bpm, BMI: 23.6 count"

        numbers = validator.extract_numbers_with_context(text)

        assert len(numbers) == 3
        assert numbers[0]["value"] == 136.8
        assert numbers[0]["unit"] == "lb"
        assert numbers[1]["value"] == 72
        assert numbers[1]["unit"] == "bpm"
        assert numbers[2]["value"] == 23.6
        assert numbers[2]["unit"] == "count"

    def test_extract_numbers_with_context(self):
        """Test context extraction around numbers."""
        validator = NumericValidator()
        text = "Your current weight is 70 kg which is healthy"

        numbers = validator.extract_numbers_with_context(text)

        assert len(numbers) == 1
        assert "current weight" in numbers[0]["context"].lower()
        assert numbers[0]["position"] >= 0

    def test_extract_from_tool_results(self):
        """Test extracting numbers from tool results."""
        validator = NumericValidator()
        tool_results = [
            {
                "name": "get_weight",
                "content": "Your weight is 70.2 kg",
            },
            {
                "name": "get_bmi",
                "content": "Your BMI is 23.6",
            },
        ]

        numbers = validator.extract_tool_numbers(tool_results)

        assert len(numbers) == 2
        assert numbers[0]["source"] == "tool"
        assert numbers[0]["tool_name"] == "get_weight"
        assert numbers[0]["value"] == 70.2
        assert numbers[1]["tool_name"] == "get_bmi"
        assert numbers[1]["value"] == 23.6


@pytest.mark.unit
class TestNumericValidatorMatching:
    """Test value matching with tolerance."""

    def test_exact_match(self):
        """Test exact value matches."""
        validator = NumericValidator()

        assert validator.values_match(70.0, 70.0)
        assert validator.values_match(23.6, 23.6)

    def test_rounding_match(self):
        """Test rounding tolerance (< 1.0 difference)."""
        validator = NumericValidator()

        # Common rounding scenarios
        assert validator.values_match(70.2, 70.0)  # Round down
        assert validator.values_match(70.0, 70.2)  # Round up
        assert validator.values_match(72.8, 73.0)  # Round to nearest

    def test_percentage_tolerance(self):
        """Test percentage tolerance matching."""
        validator = NumericValidator(tolerance=0.1)  # 10%

        # Within 10% tolerance
        assert validator.values_match(100.0, 105.0)
        assert validator.values_match(100.0, 95.0)

        # Outside 10% tolerance
        assert not validator.values_match(100.0, 120.0)
        assert not validator.values_match(100.0, 80.0)

    def test_strict_mode(self):
        """Test strict mode (no tolerance)."""
        validator = NumericValidator()

        # Exact match required in strict mode
        assert validator.values_match(70.0, 70.0, tolerance=0.0)

        # Rounding still allowed (< 1.0 difference)
        assert validator.values_match(70.2, 70.0, tolerance=0.0)

        # Percentage differences rejected
        assert not validator.values_match(70.0, 73.0, tolerance=0.0)


@pytest.mark.unit
class TestNumericValidatorValidation:
    """Test response validation against tool results."""

    def test_valid_response_all_matched(self):
        """Test response where all numbers match tool results."""
        validator = NumericValidator()

        tool_results = [{"name": "get_health", "content": "Weight: 70.2 kg, BMI: 23.6"}]

        response = "Your weight is 70 kg and your BMI is 23.6"

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is True
        assert result["score"] == 1.0
        assert len(result["hallucinations"]) == 0
        assert len(result["matched"]) == 2
        assert result["stats"]["matched"] == 2
        assert result["stats"]["hallucinated"] == 0

    def test_hallucinated_numbers_detected(self):
        """Test detection of hallucinated numbers."""
        validator = NumericValidator()

        tool_results = [{"name": "get_health", "content": "Weight: 70 kg"}]

        # Response includes number NOT in tool results (outside tolerance)
        response = "Your weight is 80 kg"  # 80 is hallucinated (>10% diff)

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is False
        assert result["score"] == 0.0
        assert len(result["hallucinations"]) == 1
        assert result["hallucinations"][0]["value"] == 80.0
        assert len(result["warnings"]) > 0

    def test_partial_hallucination(self):
        """Test response with some correct and some hallucinated numbers."""
        validator = NumericValidator()

        tool_results = [{"name": "get_health", "content": "Weight: 70 kg, BMI: 23.6"}]

        # One correct (70), one hallucinated (30.0 - >10% diff from 23.6)
        response = "Your weight is 70 kg and BMI is 30.0"

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is False
        assert result["score"] == 0.5  # 1 out of 2 matched
        assert len(result["matched"]) == 1
        assert len(result["hallucinations"]) == 1
        assert result["hallucinations"][0]["value"] == 30.0

    def test_no_numbers_in_response(self):
        """Test response with no numbers (safe case)."""
        validator = NumericValidator()

        tool_results = [{"name": "get_health", "content": "Weight: 70 kg"}]

        response = "You're doing great! Keep up the good work."

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is True
        assert result["score"] == 1.0
        assert len(result["hallucinations"]) == 0
        assert result["stats"]["total_numbers"] == 0

    def test_numbers_but_no_tool_data(self):
        """Test response with numbers but no tool data (likely hallucination)."""
        validator = NumericValidator()

        tool_results = []  # No tool data

        response = "Your weight is 70 kg"

        result = validator.validate_response(response, tool_results)

        assert result["valid"] is False
        assert result["score"] == 0.0
        assert len(result["hallucinations"]) == 1
        assert "no tool data available" in result["warnings"][0].lower()

    def test_unit_matching(self):
        """Test that units must match when both present."""
        validator = NumericValidator()

        tool_results = [{"name": "get_health", "content": "Weight: 70 kg"}]

        # Same value, different unit → should not match
        response = "Your weight is 70 lb"

        result = validator.validate_response(response, tool_results)

        # Note: This might match if units are ignored, or not match if enforced
        # Current implementation: units must match when both present
        assert result["score"] < 1.0  # Not a perfect match


@pytest.mark.unit
class TestNumericValidatorCorrection:
    """Test hallucination correction."""

    def test_correct_hallucinations(self):
        """Test replacing hallucinated numbers with warnings."""
        validator = NumericValidator()

        response = "Your weight is 75 kg"

        validation_result = {
            "hallucinations": [
                {
                    "value": 75.0,
                    "unit": "kg",
                    "raw_match": "75 kg",
                    "position": response.index("75"),
                }
            ]
        }

        corrected = validator.correct_hallucinations(response, validation_result)

        assert "75 kg" not in corrected
        assert "[DATA NOT VERIFIED]" in corrected

    def test_correct_multiple_hallucinations(self):
        """Test correcting multiple hallucinated numbers."""
        validator = NumericValidator()

        response = "Weight: 75 kg, BMI: 25.0"

        validation_result = {
            "hallucinations": [
                {
                    "value": 75.0,
                    "raw_match": "75",
                    "position": response.index("75"),
                },
                {
                    "value": 25.0,
                    "raw_match": "25.0",
                    "position": response.index("25.0"),
                },
            ]
        }

        corrected = validator.correct_hallucinations(response, validation_result)

        assert "75" not in corrected or "[DATA NOT VERIFIED]" in corrected
        assert "25.0" not in corrected or "[DATA NOT VERIFIED]" in corrected


@pytest.mark.unit
class TestNumericValidatorSingleton:
    """Test global validator instance."""

    def test_get_numeric_validator(self):
        """Test get_numeric_validator returns consistent instance."""
        validator1 = get_numeric_validator()
        validator2 = get_numeric_validator()

        assert validator1 is validator2  # Same instance
        assert isinstance(validator1, NumericValidator)
