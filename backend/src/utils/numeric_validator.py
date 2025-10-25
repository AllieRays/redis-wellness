"""Numeric validation to detect and prevent LLM hallucinations in health data."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class NumericValidator:
    """Detect hallucinated numbers by comparing LLM responses against tool outputs."""

    def __init__(self, tolerance: float = 0.1):
        """
        Initialize validator.

        Args:
            tolerance: Percentage tolerance for numeric differences (0.1 = 10%)
        """
        self.tolerance = tolerance

        # Common health metric units
        self.unit_patterns = [
            r"lb",
            r"lbs",
            r"kg",
            r"count",
            r"bpm",
            r"cal",
            r"kcal",
            r"min",
            r"mins",
            r"minutes",
            r"count/min",
            r"steps",
            r"BMI",
        ]

    def extract_numbers_with_context(self, text: str) -> list[dict[str, Any]]:
        """
        Extract numbers with surrounding context from text.

        Returns list of: {
            "value": float,
            "unit": str or None,
            "raw_match": str,
            "context": str (5 words before/after)
        }
        """
        numbers = []

        # Pattern to match numbers with optional units
        # Matches: "136.8", "136.8 lb", "70 count/min", "23.6 BMI"
        pattern = r"(\d+\.?\d*)\s*(" + "|".join(self.unit_patterns) + r")?"

        for match in re.finditer(pattern, text, re.IGNORECASE):
            value_str = match.group(1)
            unit = match.group(2)

            try:
                value = float(value_str)

                # Extract context (5 words before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()

                numbers.append(
                    {
                        "value": value,
                        "unit": unit.lower() if unit else None,
                        "raw_match": match.group(0),
                        "context": context,
                        "position": match.start(),
                    }
                )
            except ValueError:
                continue

        return numbers

    def extract_tool_numbers(self, tool_results: list[dict]) -> list[dict[str, Any]]:
        """
        Extract all numeric values from tool results (ground truth).

        Args:
            tool_results: List of tool outputs from message history

        Returns:
            List of extracted numbers with context
        """
        all_numbers = []

        for tool_result in tool_results:
            # Tool results can be in various formats
            content = str(tool_result.get("content", ""))

            numbers = self.extract_numbers_with_context(content)

            for num in numbers:
                num["source"] = "tool"
                num["tool_name"] = tool_result.get("name", "unknown")

            all_numbers.extend(numbers)

        return all_numbers

    def values_match(self, val1: float, val2: float, tolerance: float = None) -> bool:
        """
        Check if two values match within tolerance.

        Args:
            val1, val2: Values to compare
            tolerance: Percentage tolerance (None = use instance default)

        Returns:
            True if values match within tolerance
        """
        if tolerance is None:
            tolerance = self.tolerance

        # Handle exact matches
        if val1 == val2:
            return True

        # Handle rounding (e.g., 70.2 → 70)
        if abs(val1 - val2) < 1.0:
            return True

        # Percentage tolerance
        if val1 > 0:
            percent_diff = abs(val1 - val2) / val1
            return percent_diff <= tolerance

        return False

    def validate_response(
        self, response_text: str, tool_results: list[dict], strict: bool = False
    ) -> dict[str, Any]:
        """
        Validate LLM response against tool results.

        Args:
            response_text: LLM's generated response
            tool_results: Tool outputs from message history
            strict: If True, require exact matches (no tolerance)

        Returns:
            {
                "valid": bool,
                "hallucinations": list of flagged numbers,
                "matched": list of validated numbers,
                "warnings": list of warning messages,
                "score": float (0.0-1.0, percentage of numbers validated)
            }
        """
        # Extract ground truth from tools
        tool_numbers = self.extract_tool_numbers(tool_results)

        # Extract numbers from response
        response_numbers = self.extract_numbers_with_context(response_text)

        if not response_numbers:
            # No numbers in response - probably safe
            return {
                "valid": True,
                "hallucinations": [],
                "matched": [],
                "warnings": [],
                "score": 1.0,
                "stats": {
                    "total_numbers": 0,
                    "matched": 0,
                    "hallucinated": 0,
                    "tool_numbers_available": len(tool_numbers),
                },
            }

        if not tool_numbers:
            # Response has numbers but tools returned none - likely hallucination
            logger.warning(
                f"Response contains {len(response_numbers)} numbers but tools returned none"
            )
            return {
                "valid": False,
                "hallucinations": response_numbers,
                "matched": [],
                "warnings": ["Response contains numbers but no tool data available"],
                "score": 0.0,
                "stats": {
                    "total_numbers": len(response_numbers),
                    "matched": 0,
                    "hallucinated": len(response_numbers),
                    "tool_numbers_available": 0,
                },
            }

        # Match each response number against tool numbers
        matched = []
        hallucinations = []
        warnings = []

        for resp_num in response_numbers:
            found_match = False

            for tool_num in tool_numbers:
                # Check if values match
                values_match = self.values_match(
                    resp_num["value"],
                    tool_num["value"],
                    tolerance=0.0 if strict else self.tolerance,
                )

                # Check if units match (if both present)
                units_match = True
                if resp_num["unit"] and tool_num["unit"]:
                    units_match = resp_num["unit"] == tool_num["unit"]

                if values_match and units_match:
                    matched.append(
                        {
                            "response": resp_num,
                            "tool": tool_num,
                            "confidence": (
                                "exact"
                                if resp_num["value"] == tool_num["value"]
                                else "fuzzy"
                            ),
                        }
                    )
                    found_match = True
                    break

            if not found_match:
                hallucinations.append(resp_num)
                warnings.append(
                    f"Unverified number: {resp_num['raw_match']} "
                    f"(context: ...{resp_num['context'][:50]}...)"
                )

        # Calculate validation score
        total_numbers = len(response_numbers)
        matched_count = len(matched)
        score = matched_count / total_numbers if total_numbers > 0 else 1.0

        # Consider valid if score > 0.8 (80% of numbers verified)
        is_valid = score >= 0.8 and len(hallucinations) == 0

        result = {
            "valid": is_valid,
            "hallucinations": hallucinations,
            "matched": matched,
            "warnings": warnings,
            "score": score,
            "stats": {
                "total_numbers": total_numbers,
                "matched": matched_count,
                "hallucinated": len(hallucinations),
                "tool_numbers_available": len(tool_numbers),
            },
        }

        if not is_valid:
            logger.warning(
                f"❌ Response validation failed: score={score:.2f}, "
                f"hallucinations={len(hallucinations)}, "
                f"warnings={warnings}"
            )
        else:
            logger.info(
                f"✅ Response validation passed: score={score:.2f}, "
                f"matched={matched_count}/{total_numbers}"
            )

        return result

    def correct_hallucinations(
        self, response_text: str, validation_result: dict
    ) -> str:
        """
        Attempt to correct hallucinated numbers in response.

        Strategy: Replace hallucinated numbers with "[DATA NOT AVAILABLE]"

        Args:
            response_text: Original response
            validation_result: Result from validate_response()

        Returns:
            Corrected response text
        """
        corrected = response_text

        # Sort hallucinations by position (reverse order for string replacement)
        hallucinations = sorted(
            validation_result["hallucinations"],
            key=lambda x: x["position"],
            reverse=True,
        )

        for halluc in hallucinations:
            # Replace the hallucinated number
            start = halluc["position"]
            end = start + len(halluc["raw_match"])

            corrected = corrected[:start] + "[DATA NOT VERIFIED]" + corrected[end:]

        return corrected


# Global validator instance
_numeric_validator: NumericValidator | None = None


def get_numeric_validator() -> NumericValidator:
    """Get or create global numeric validator."""
    global _numeric_validator

    if _numeric_validator is None:
        _numeric_validator = NumericValidator(tolerance=0.1)

    return _numeric_validator
