"""
Unit tests for parse_health_record_date utility function.

Tests timezone handling, edge cases, and error conditions.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.utils.time_utils import parse_health_record_date


class TestParseHealthRecordDate:
    """Test suite for parse_health_record_date function."""

    def test_basic_parsing(self):
        """Test basic date parsing with UTC assumption."""
        result = parse_health_record_date("2025-10-21 12:53:11")

        assert result.year == 2025
        assert result.month == 10
        assert result.day == 21
        assert result.hour == 12
        assert result.minute == 53
        assert result.second == 11
        assert result.tzinfo == UTC

    def test_naive_datetime_converted_to_utc(self):
        """Naive datetime should be converted to UTC by default."""
        result = parse_health_record_date("2025-01-15 08:30:45")

        assert result.tzinfo is not None, "Datetime should be timezone-aware"
        assert result.tzinfo == UTC, "Timezone should be UTC"

    def test_midnight_datetime(self):
        """Test parsing datetime at midnight."""
        result = parse_health_record_date("2025-12-31 00:00:00")

        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == UTC

    def test_end_of_day_datetime(self):
        """Test parsing datetime at end of day."""
        result = parse_health_record_date("2025-06-30 23:59:59")

        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59
        assert result.tzinfo == UTC

    def test_leap_year_date(self):
        """Test parsing date in leap year."""
        result = parse_health_record_date("2024-02-29 15:20:00")

        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29
        assert result.tzinfo == UTC

    def test_assume_utc_false_with_strict_false(self):
        """With assume_utc=False and strict=False, datetime remains naive."""
        result = parse_health_record_date(
            "2025-10-21 12:53:11", assume_utc=False, strict=False
        )

        assert result.tzinfo is None, "Datetime should remain naive"

    def test_strict_mode_raises_for_naive_datetime(self):
        """Strict mode should raise ValueError for naive datetimes."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date(
                "2025-10-21 12:53:11", assume_utc=False, strict=True
            )

        assert "Naive datetime found" in str(exc_info.value)
        assert "timezone-aware" in str(exc_info.value)

    def test_invalid_date_format_raises_error(self):
        """Invalid date format should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025/10/21 12:53:11")  # Wrong separator

        assert "Invalid health record date format" in str(exc_info.value)
        assert "YYYY-MM-DD HH:MM:SS" in str(exc_info.value)

    def test_invalid_date_string_raises_error(self):
        """Completely invalid date string should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("not-a-date")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_missing_time_component_raises_error(self):
        """Date without time component should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-10-21")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_missing_seconds_raises_error(self):
        """Date without seconds should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-10-21 12:53")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_extra_components_raises_error(self):
        """Date with extra components should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-10-21 12:53:11.123456")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_invalid_month_raises_error(self):
        """Invalid month should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-13-21 12:53:11")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_invalid_day_raises_error(self):
        """Invalid day should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-02-30 12:53:11")  # Feb doesn't have 30 days

        assert "Invalid health record date format" in str(exc_info.value)

    def test_invalid_hour_raises_error(self):
        """Invalid hour should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-10-21 25:53:11")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_invalid_minute_raises_error(self):
        """Invalid minute should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-10-21 12:60:11")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_invalid_second_raises_error(self):
        """Invalid second should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("2025-10-21 12:53:61")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_comparison_with_timezone_aware_datetime(self):
        """Parsed datetime should be comparable with timezone-aware datetimes."""
        result = parse_health_record_date("2025-10-21 12:53:11")
        other = datetime(2025, 10, 21, 12, 53, 11, tzinfo=UTC)

        assert result == other
        assert result <= other
        assert result >= other

    def test_comparison_between_different_dates(self):
        """Test comparison between different parsed dates."""
        earlier = parse_health_record_date("2025-10-20 10:00:00")
        later = parse_health_record_date("2025-10-21 10:00:00")

        assert earlier < later
        assert later > earlier
        assert earlier != later

    def test_year_boundary_dates(self):
        """Test dates at year boundaries."""
        end_of_year = parse_health_record_date("2024-12-31 23:59:59")
        start_of_year = parse_health_record_date("2025-01-01 00:00:00")

        assert end_of_year < start_of_year
        assert (start_of_year - end_of_year) == timedelta(seconds=1)

    def test_idempotent_parsing(self):
        """Parsing the same date multiple times should yield same result."""
        date_str = "2025-10-21 12:53:11"
        result1 = parse_health_record_date(date_str)
        result2 = parse_health_record_date(date_str)

        assert result1 == result2
        assert result1.tzinfo == result2.tzinfo

    def test_empty_string_raises_error(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_whitespace_only_raises_error(self):
        """Whitespace-only string should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_health_record_date("   ")

        assert "Invalid health record date format" in str(exc_info.value)

    def test_date_with_leading_zeros(self):
        """Date with leading zeros should parse correctly."""
        result = parse_health_record_date("2025-01-05 08:09:07")

        assert result.month == 1
        assert result.day == 5
        assert result.hour == 8
        assert result.minute == 9
        assert result.second == 7

    def test_century_boundary(self):
        """Test dates at century boundary."""
        result = parse_health_record_date("2000-01-01 00:00:00")

        assert result.year == 2000
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo == UTC

    def test_documentation_example(self):
        """Test the example from function docstring."""
        result = parse_health_record_date("2025-10-21 12:53:11")
        expected = datetime(2025, 10, 21, 12, 53, 11, tzinfo=UTC)

        assert result == expected


class TestParseHealthRecordDateEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_maximum_valid_date(self):
        """Test maximum valid date (year 9999)."""
        result = parse_health_record_date("9999-12-31 23:59:59")

        assert result.year == 9999
        assert result.tzinfo == UTC

    def test_minimum_valid_date(self):
        """Test minimum valid date (year 1)."""
        result = parse_health_record_date("0001-01-01 00:00:00")

        assert result.year == 1
        assert result.tzinfo == UTC

    def test_dst_transition_dates(self):
        """Test dates during DST transitions (stored as UTC, so no ambiguity)."""
        # Spring forward date
        spring = parse_health_record_date("2025-03-09 10:00:00")
        assert spring.tzinfo == UTC

        # Fall back date
        fall = parse_health_record_date("2025-11-02 09:00:00")
        assert fall.tzinfo == UTC

    def test_historical_date(self):
        """Test parsing historical dates."""
        result = parse_health_record_date("1990-05-15 14:30:00")

        assert result.year == 1990
        assert result.month == 5
        assert result.day == 15
        assert result.tzinfo == UTC

    def test_future_date(self):
        """Test parsing future dates."""
        result = parse_health_record_date("2099-12-25 18:00:00")

        assert result.year == 2099
        assert result.month == 12
        assert result.day == 25
        assert result.tzinfo == UTC


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
