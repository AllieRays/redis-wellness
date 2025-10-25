"""
Unit tests for time_utils - Time parsing and UTC handling.

REAL TESTS - NO MOCKS: Tests real datetime parsing logic.
"""

from datetime import UTC, datetime

import pytest

from src.utils.time_utils import (
    format_date_utc,
    format_datetime_utc,
    get_utc_timestamp,
    parse_health_record_date,
    parse_time_period,
)


@pytest.mark.unit
class TestTimeParsingBasic:
    """Test basic time parsing functions."""

    def test_get_utc_timestamp(self):
        """Test UTC timestamp generation."""
        ts = get_utc_timestamp()

        assert isinstance(ts, int)
        assert ts > 0

    def test_format_datetime_utc(self):
        """Test datetime formatting."""
        dt = datetime(2024, 10, 22, 16, 30, 0, tzinfo=UTC)

        result = format_datetime_utc(dt)

        assert "2024-10-22" in result
        assert "16:30:00" in result

    def test_format_date_utc(self):
        """Test date-only formatting."""
        dt = datetime(2024, 10, 22, 16, 30, 0, tzinfo=UTC)

        result = format_date_utc(dt)

        assert result == "2024-10-22"

    def test_parse_health_record_date_iso(self):
        """Test parsing ISO 8601 health record dates."""
        date_str = "2024-10-22T16:30:00+00:00"

        result = parse_health_record_date(date_str)

        assert result.year == 2024
        assert result.month == 10
        assert result.day == 22
        assert result.tzinfo is not None

    def test_parse_health_record_date_z_suffix(self):
        """Test parsing dates with Z suffix."""
        date_str = "2024-10-22T16:30:00Z"

        result = parse_health_record_date(date_str)

        assert result.tzinfo is not None


@pytest.mark.unit
class TestTimePeriodParsing:
    """Test natural language time period parsing."""

    def test_parse_last_week(self):
        """Test parsing 'last week'."""
        start, end, desc = parse_time_period("last week")

        assert "week" in desc.lower()
        assert (end - start).days == 6  # Mon-Sun

    def test_parse_last_7_days(self):
        """Test parsing 'last 7 days'."""
        start, end, desc = parse_time_period("last 7 days")

        assert "7 day" in desc.lower()
        assert (end - start).days >= 6

    def test_parse_this_month(self):
        """Test parsing 'this month'."""
        start, end, desc = parse_time_period("this month")

        assert "month" in desc.lower()
        assert start.day == 1

    def test_parse_recent_default(self):
        """Test parsing 'recent' defaults to last N days."""
        start, end, desc = parse_time_period("recent")

        assert "recent" in desc.lower() or "day" in desc.lower()
        assert (end - start).days >= 28  # At least some days

    def test_parse_october_15(self):
        """Test parsing specific date."""
        start, end, desc = parse_time_period("October 15 2024")

        assert start.month == 10
        assert start.day == 15
        assert start.year == 2024
        assert start.date() == end.date()  # Same day
