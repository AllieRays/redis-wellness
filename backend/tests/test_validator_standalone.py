"""
Standalone test for numeric validator without complex dependencies.

Run with: python tests/test_validator_standalone.py
"""

import importlib.util
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

spec = importlib.util.spec_from_file_location(
    "numeric_validator", backend_path / "src" / "agents" / "numeric_validator.py"
)
validator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator_module)
NumericValidator = validator_module.NumericValidator


def test_basic_extraction():
    """Test basic number extraction."""
    validator = NumericValidator()

    text = "Your weight is 136.8 lb and BMI is 23.6"
    numbers = validator.extract_numbers_with_context(text)

    assert len(numbers) == 2, f"Expected 2 numbers, got {len(numbers)}"
    assert numbers[0]["value"] == 136.8
    assert numbers[0]["unit"] == "lb"
    print("✅ test_basic_extraction PASSED")


def test_validation_with_tool_data():
    """Test validation against tool results."""
    validator = NumericValidator()

    tool_results = [
        {
            "name": "aggregate_metrics",
            "content": "Average: 87.5 bpm, Min: 60 bpm, Max: 110 bpm",
        }
    ]

    response = "Your average heart rate was 87.5 bpm (min: 60 bpm, max: 110 bpm)"

    result = validator.validate_response(response, tool_results)

    assert result["valid"] is True, f"Expected valid, got {result}"
    assert result["score"] == 1.0
    assert len(result["hallucinations"]) == 0
    print("✅ test_validation_with_tool_data PASSED")


def test_hallucination_detection():
    """Test detection of hallucinated numbers."""
    validator = NumericValidator(tolerance=0.01)  # 1% tolerance, stricter

    tool_results = [{"name": "search_health_records", "content": "BodyMass: 136.8 lb"}]

    # Response with significantly different number (150 vs 136.8 = 9.7% diff)
    response = "Your weight is 150 lb"

    result = validator.validate_response(response, tool_results, strict=False)

    assert result["valid"] is False, f"Expected invalid, got {result}"
    assert len(result["hallucinations"]) > 0
    print("✅ test_hallucination_detection PASSED")


def test_fuzzy_matching():
    """Test fuzzy matching for rounded numbers."""
    validator = NumericValidator()

    tool_results = [{"name": "aggregate_metrics", "content": "Average: 87.5 bpm"}]

    # Response with rounded number
    response = "Your average heart rate was 88 bpm"

    result = validator.validate_response(response, tool_results, strict=False)

    # Should pass with fuzzy matching (within 1.0 difference)
    assert result["score"] >= 0.8, f"Expected high score, got {result['score']}"
    print("✅ test_fuzzy_matching PASSED")


def test_realistic_weight_query():
    """Test realistic weight query scenario."""
    validator = NumericValidator()

    tool_results = [
        {
            "name": "search_health_records_by_metric",
            "content": """Found 5 records for BodyMass:
            - 2025-10-17: 136.8 lb
            - 2025-10-16: 137.2 lb
            - 2025-10-15: 136.5 lb""",
        }
    ]

    response = "Your weight on October 17 was 136.8 lb"

    result = validator.validate_response(response, tool_results)

    assert result["valid"] is True
    assert result["score"] == 1.0
    print("✅ test_realistic_weight_query PASSED")


def test_hallucination_with_context():
    """Test realistic hallucination detection with medical context."""
    validator = NumericValidator(tolerance=0.01)  # Strict 1% tolerance

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

    result = validator.validate_response(response, tool_results, strict=False)

    # Should flag at least one hallucination (18.5 is definitely wrong)
    # Note: 24.9 might match 23.6 with fuzzy matching
    assert (
        len(result["hallucinations"]) >= 1
    ), f"Expected at least 1 hallucination, got {result}"
    assert result["score"] < 1.0
    print("✅ test_hallucination_with_context PASSED")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Running Numeric Validator Tests")
    print("=" * 60 + "\n")

    tests = [
        test_basic_extraction,
        test_validation_with_tool_data,
        test_hallucination_detection,
        test_fuzzy_matching,
        test_realistic_weight_query,
        test_hallucination_with_context,
    ]

    failed = 0
    for test_func in tests:
        try:
            test_func()
        except AssertionError as e:
            print(f"❌ {test_func.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test_func.__name__} ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"✅ All {len(tests)} tests PASSED!")
    else:
        print(f"❌ {failed}/{len(tests)} tests FAILED")
    print("=" * 60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
