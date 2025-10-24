"""
Date Validator for Health Data Responses.

Prevents LLM date hallucinations by:
1. Extracting dates from user query
2. Extracting dates from LLM response
3. Comparing and flagging mismatches

This catches cases like:
- User asks: "What was my heart rate on October 15th?"
- LLM responds: "Your heart rate on October 11, 2025 was..."
  ↑ HALLUCINATION: Wrong date!
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class DateValidator:
    """
    Validator to detect hallucinated dates in LLM responses.

    Strategy:
    - Extract dates from user query (expected dates)
    - Extract dates from LLM response (claimed dates)
    - Flag dates in response that don't match the query
    """

    def __init__(self):
        """Initialize date validator."""
        # Month names for extraction
        self.months = {
            "january": 1,
            "jan": 1,
            "february": 2,
            "feb": 2,
            "march": 3,
            "mar": 3,
            "april": 4,
            "apr": 4,
            "may": 5,
            "june": 6,
            "jun": 6,
            "july": 7,
            "jul": 7,
            "august": 8,
            "aug": 8,
            "september": 9,
            "sept": 9,
            "sep": 9,
            "october": 10,
            "oct": 10,
            "november": 11,
            "nov": 11,
            "december": 12,
            "dec": 12,
        }

    def extract_specific_dates(self, text: str) -> list[dict[str, Any]]:
        """
        Extract specific dates from text.

        Examples:
        - "October 15th" → {month: 10, day: 15}
        - "Oct 15, 2025" → {month: 10, day: 15, year: 2025}
        - "September 3rd" → {month: 9, day: 3}

        Returns:
            List of date dictionaries with month/day/year
        """
        dates = []
        text_lower = text.lower()

        # Pattern: "October 15th", "Oct 15, 2025"
        pattern = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?"

        for match in re.finditer(pattern, text_lower):
            month_name = match.group(1)
            day = int(match.group(2))
            year_str = match.group(3)

            month_num = self.months.get(month_name)
            if month_num:
                date_dict = {
                    "month": month_num,
                    "day": day,
                    "year": int(year_str) if year_str else None,
                    "raw_match": match.group(0),
                }
                dates.append(date_dict)

        return dates

    def dates_match(self, date1: dict, date2: dict) -> bool:
        """
        Check if two dates match (ignoring year if not specified).

        Args:
            date1, date2: Date dicts with month/day/year

        Returns:
            True if dates match
        """
        # Month and day must always match
        if date1["month"] != date2["month"] or date1["day"] != date2["day"]:
            return False

        # If both have years, they must match
        if date1.get("year") and date2.get("year"):
            return date1["year"] == date2["year"]

        # If only one has year, ignore year comparison
        return True

    def validate_response(self, user_query: str, response_text: str) -> dict[str, Any]:
        """
        Validate that LLM response uses the same dates as user query.

        Args:
            user_query: User's original question
            response_text: LLM's generated response

        Returns:
            {
                "valid": bool,
                "date_mismatches": list of mismatched dates,
                "warnings": list of warning messages,
            }
        """
        # Extract dates from query and response
        query_dates = self.extract_specific_dates(user_query)
        response_dates = self.extract_specific_dates(response_text)

        if not query_dates:
            # No specific dates in query - skip validation
            return {
                "valid": True,
                "date_mismatches": [],
                "warnings": [],
            }

        if not response_dates:
            # Query has dates but response doesn't mention any - acceptable
            return {
                "valid": True,
                "date_mismatches": [],
                "warnings": [],
            }

        # Check if response dates match query dates
        mismatches = []
        warnings = []

        for resp_date in response_dates:
            found_match = False

            for query_date in query_dates:
                if self.dates_match(resp_date, query_date):
                    found_match = True
                    break

            if not found_match:
                mismatches.append(resp_date)
                warnings.append(
                    f"⚠️ DATE MISMATCH: Response mentions {resp_date['raw_match']}, "
                    f"but user asked about {query_dates[0]['raw_match']}"
                )

        is_valid = len(mismatches) == 0

        return {
            "valid": is_valid,
            "date_mismatches": mismatches,
            "warnings": warnings,
            "query_dates": query_dates,
            "response_dates": response_dates,
        }


# Singleton instance
_date_validator = None


def get_date_validator() -> DateValidator:
    """Get singleton date validator instance."""
    global _date_validator
    if _date_validator is None:
        _date_validator = DateValidator()
    return _date_validator
