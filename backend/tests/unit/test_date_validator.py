"""
Unit tests for date validator.

Tests date extraction and validation logic to detect LLM hallucinations.
"""

import pytest

from src.utils.date_validator import DateValidator, get_date_validator


@pytest.fixture
def date_validator():
    """Create date validator instance."""
    return DateValidator()


class TestDateExtraction:
    """Test extraction of dates from text."""

    def test_extracts_month_day(self, date_validator):
        """Should extract month and day from common formats."""
        dates = date_validator.extract_specific_dates("October 15th")
        assert len(dates) == 1
        assert dates[0]["month"] == 10
        assert dates[0]["day"] == 15
        assert dates[0]["year"] is None

    def test_extracts_month_day_with_year(self, date_validator):
        """Should extract full date with year."""
        dates = date_validator.extract_specific_dates("Oct 15, 2025")
        assert len(dates) == 1
        assert dates[0]["month"] == 10
        assert dates[0]["day"] == 15
        assert dates[0]["year"] == 2025

    def test_extracts_month_abbreviations(self, date_validator):
        """Should handle month abbreviations."""
        dates = date_validator.extract_specific_dates("Sep 3rd")
        assert len(dates) == 1
        assert dates[0]["month"] == 9
        assert dates[0]["day"] == 3

    def test_extracts_ordinal_suffixes(self, date_validator):
        """Should handle st, nd, rd, th suffixes."""
        assert date_validator.extract_specific_dates("January 1st")[0]["day"] == 1
        assert date_validator.extract_specific_dates("January 2nd")[0]["day"] == 2
        assert date_validator.extract_specific_dates("January 3rd")[0]["day"] == 3
        assert date_validator.extract_specific_dates("January 4th")[0]["day"] == 4

    def test_extracts_multiple_dates(self, date_validator):
        """Should extract multiple dates from text."""
        text = "Between October 1st and October 31st"
        dates = date_validator.extract_specific_dates(text)
        assert len(dates) == 2
        assert dates[0]["day"] == 1
        assert dates[1]["day"] == 31

    def test_case_insensitive(self, date_validator):
        """Should work regardless of case."""
        assert date_validator.extract_specific_dates("OCTOBER 15TH")[0]["month"] == 10
        assert date_validator.extract_specific_dates("october 15th")[0]["month"] == 10
        assert date_validator.extract_specific_dates("October 15th")[0]["month"] == 10

    def test_handles_sept_abbreviation(self, date_validator):
        """Should handle both 'sept' and 'sep' for September."""
        assert date_validator.extract_specific_dates("Sept 15")[0]["month"] == 9
        assert date_validator.extract_specific_dates("Sep 15")[0]["month"] == 9

    def test_returns_empty_for_no_dates(self, date_validator):
        """Should return empty list if no dates found."""
        dates = date_validator.extract_specific_dates("No dates here")
        assert dates == []

    def test_stores_raw_match(self, date_validator):
        """Should store the raw matched text."""
        dates = date_validator.extract_specific_dates("October 15th, 2025")
        assert dates[0]["raw_match"] == "october 15th, 2025"


class TestDateMatching:
    """Test date comparison logic."""

    def test_matches_same_month_day(self, date_validator):
        """Should match dates with same month and day."""
        date1 = {"month": 10, "day": 15, "year": None}
        date2 = {"month": 10, "day": 15, "year": None}
        assert date_validator.dates_match(date1, date2) is True

    def test_does_not_match_different_month(self, date_validator):
        """Should not match dates with different months."""
        date1 = {"month": 10, "day": 15, "year": None}
        date2 = {"month": 11, "day": 15, "year": None}
        assert date_validator.dates_match(date1, date2) is False

    def test_does_not_match_different_day(self, date_validator):
        """Should not match dates with different days."""
        date1 = {"month": 10, "day": 15, "year": None}
        date2 = {"month": 10, "day": 16, "year": None}
        assert date_validator.dates_match(date1, date2) is False

    def test_matches_with_one_year_missing(self, date_validator):
        """Should match if one date lacks year."""
        date1 = {"month": 10, "day": 15, "year": 2025}
        date2 = {"month": 10, "day": 15, "year": None}
        assert date_validator.dates_match(date1, date2) is True

    def test_matches_with_both_years_matching(self, date_validator):
        """Should match if both years are same."""
        date1 = {"month": 10, "day": 15, "year": 2025}
        date2 = {"month": 10, "day": 15, "year": 2025}
        assert date_validator.dates_match(date1, date2) is True

    def test_does_not_match_different_years(self, date_validator):
        """Should not match if years are different."""
        date1 = {"month": 10, "day": 15, "year": 2025}
        date2 = {"month": 10, "day": 15, "year": 2024}
        assert date_validator.dates_match(date1, date2) is False


class TestResponseValidation:
    """Test full response validation logic."""

    def test_valid_when_dates_match(self, date_validator):
        """Should pass validation when dates match."""
        query = "What was my heart rate on October 15th?"
        response = "Your heart rate on October 15th was 72 bpm."

        result = date_validator.validate_response(query, response)
        assert result["valid"] is True
        assert result["date_mismatches"] == []
        assert result["warnings"] == []

    def test_invalid_when_dates_mismatch(self, date_validator):
        """Should fail validation when dates don't match."""
        query = "What was my heart rate on October 15th?"
        response = "Your heart rate on October 11th was 72 bpm."

        result = date_validator.validate_response(query, response)
        assert result["valid"] is False
        assert len(result["date_mismatches"]) == 1
        assert len(result["warnings"]) == 1
        assert "october 11th" in result["warnings"][0].lower()

    def test_valid_when_no_query_dates(self, date_validator):
        """Should pass if query has no specific dates."""
        query = "What was my heart rate recently?"
        response = "Your heart rate on October 15th was 72 bpm."

        result = date_validator.validate_response(query, response)
        assert result["valid"] is True

    def test_valid_when_no_response_dates(self, date_validator):
        """Should pass if response has no dates."""
        query = "What was my heart rate on October 15th?"
        response = "Your heart rate was 72 bpm."

        result = date_validator.validate_response(query, response)
        assert result["valid"] is True

    def test_returns_extracted_dates(self, date_validator):
        """Should return both query and response dates."""
        query = "What was my heart rate on October 15th?"
        response = "Your heart rate on October 15th was 72 bpm."

        result = date_validator.validate_response(query, response)
        assert len(result["query_dates"]) == 1
        assert len(result["response_dates"]) == 1
        assert result["query_dates"][0]["month"] == 10
        assert result["response_dates"][0]["month"] == 10

    def test_ignores_year_if_not_in_query(self, date_validator):
        """Should ignore year in response if query didn't specify it."""
        query = "What was my heart rate on October 15th?"
        response = "Your heart rate on October 15th, 2025 was 72 bpm."

        result = date_validator.validate_response(query, response)
        assert result["valid"] is True

    def test_fails_if_year_mismatches(self, date_validator):
        """Should fail if both specify year and they differ."""
        query = "What was my heart rate on October 15th, 2025?"
        response = "Your heart rate on October 15th, 2024 was 72 bpm."

        result = date_validator.validate_response(query, response)
        assert result["valid"] is False


class TestGetDateValidator:
    """Test singleton factory function."""

    def test_returns_date_validator(self):
        """Should return DateValidator instance."""
        validator = get_date_validator()
        assert isinstance(validator, DateValidator)

    def test_returns_same_instance(self):
        """Should return singleton instance."""
        validator1 = get_date_validator()
        validator2 = get_date_validator()
        assert validator1 is validator2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_handles_multiple_dates_in_query(self, date_validator):
        """Should handle queries with date ranges."""
        query = "Between October 1st and October 31st"
        response = "During October 15th you had..."

        result = date_validator.validate_response(query, response)
        # October 15th does NOT match October 1st or 31st
        # So validation fails (which is correct behavior)
        assert result["valid"] is False
        assert len(result["date_mismatches"]) == 1

    def test_handles_empty_query(self, date_validator):
        """Should handle empty query."""
        result = date_validator.validate_response("", "October 15th")
        assert result["valid"] is True

    def test_handles_empty_response(self, date_validator):
        """Should handle empty response."""
        result = date_validator.validate_response("October 15th", "")
        assert result["valid"] is True

    def test_handles_unicode(self, date_validator):
        """Should handle unicode characters."""
        query = "October 15th 😊"
        response = "October 15th 🎉"
        result = date_validator.validate_response(query, response)
        assert result["valid"] is True

    def test_day_at_month_boundaries(self, date_validator):
        """Should handle edge days like 1st and 31st."""
        dates = date_validator.extract_specific_dates("January 1st and December 31st")
        assert len(dates) == 2
        assert dates[0]["day"] == 1
        assert dates[1]["day"] == 31

    def test_february_29th(self, date_validator):
        """Should extract February 29th (leap year)."""
        dates = date_validator.extract_specific_dates("February 29th")
        assert len(dates) == 1
        assert dates[0]["month"] == 2
        assert dates[0]["day"] == 29

    def test_invalid_day_still_extracted(self, date_validator):
        """Should extract but not validate impossible dates like February 30."""
        # Note: We extract, validation of calendar validity is separate concern
        dates = date_validator.extract_specific_dates("February 30th")
        assert len(dates) == 1
        assert dates[0]["day"] == 30

    def test_all_month_names(self, date_validator):
        """Should handle all 12 months."""
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        for i, month in enumerate(months, start=1):
            dates = date_validator.extract_specific_dates(f"{month} 15")
            assert dates[0]["month"] == i

    def test_all_month_abbreviations(self, date_validator):
        """Should handle all month abbreviations."""
        abbrevs = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sept",
            "Oct",
            "Nov",
            "Dec",
        ]
        for i, abbrev in enumerate(abbrevs, start=1):
            dates = date_validator.extract_specific_dates(f"{abbrev} 15")
            assert dates[0]["month"] == i
