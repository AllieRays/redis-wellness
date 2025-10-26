"""
Unit tests for time_utils - Time parsing and UTC handling.

DETERMINISTIC TESTS WITH MOCKING: Uses fixed test dates and mocking for reproducibility.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.utils.time_utils import (
    format_date_utc,
    format_datetime_utc,
    get_utc_timestamp,
    parse_health_record_date,
    parse_time_period,
)

# Fixed test dates (update annually or use current year)
TEST_DATETIME = datetime(2025, 10, 22, 16, 30, 0, tzinfo=UTC)
TEST_DATE_STR_ISO = "2025-10-22T16:30:00+00:00"
TEST_DATE_STR_Z = "2025-10-22T16:30:00Z"


@pytest.mark.unit
class TestTimeParsingBasic:
    """Test basic time parsing functions."""

    @patch("src.utils.time_utils.datetime")
    def test_get_utc_timestamp(self, mock_datetime):
        """Test UTC timestamp generation with mocked time."""
        # Mock datetime.now(UTC) to return fixed time
        mock_datetime.now.return_value = TEST_DATETIME

        ts = get_utc_timestamp()

        # Verify correct timestamp
        expected = int(TEST_DATETIME.timestamp())
        assert ts == expected

        # Verify UTC was used
        mock_datetime.now.assert_called_once_with(UTC)

    def test_format_datetime_utc(self):
        """Test datetime formatting."""
        result = format_datetime_utc(TEST_DATETIME)

        assert "2025-10-22" in result
        assert "16:30:00" in result
        assert "+00:00" in result or "Z" in result

    def test_format_date_utc(self):
        """Test date-only formatting."""
        result = format_date_utc(TEST_DATETIME)

        assert result == "2025-10-22"

    def test_parse_health_record_date_iso(self):
        """Test parsing ISO 8601 health record dates."""
        result = parse_health_record_date(TEST_DATE_STR_ISO)

        assert result.year == 2025
        assert result.month == 10
        assert result.day == 22
        assert result.hour == 16
        assert result.minute == 30
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_parse_health_record_date_z_suffix(self):
        """Test parsing dates with Z suffix."""
        result = parse_health_record_date(TEST_DATE_STR_Z)

        assert result.tzinfo == UTC
        assert result.year == 2025


@pytest.mark.unit
class TestTimePeriodParsing:
    """Test natural language time period parsing with mocked current time."""

    @patch("src.utils.time_utils.datetime")
    def test_parse_last_week(self, mock_datetime):
        """Test parsing 'last week' with fixed current date."""
        # Mock "now" to Friday, Oct 25, 2025
        now = datetime(2025, 10, 25, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        start, end, desc = parse_time_period("last week")

        # Last week should be Monday Oct 13 to Sunday Oct 19
        assert "week" in desc.lower()
        assert (end - start).days == 6  # Mon-Sun
        assert start.tzinfo == UTC
        assert end.tzinfo == UTC

    @patch("src.utils.time_utils.datetime")
    def test_parse_last_7_days(self, mock_datetime):
        """Test parsing 'last 7 days' with fixed current date."""
        # Mock "now" to Oct 25, 2025
        now = datetime(2025, 10, 25, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        start, end, desc = parse_time_period("last 7 days")

        assert "7 day" in desc.lower()
        assert (end - start).days >= 6

    @patch("src.utils.time_utils.datetime")
    def test_parse_this_month(self, mock_datetime):
        """Test parsing 'this month' with fixed current date."""
        # Mock "now" to Oct 25, 2025
        now = datetime(2025, 10, 25, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        start, end, desc = parse_time_period("this month")

        # This month = Oct 1 to Oct 25 (current day)
        assert "month" in desc.lower()
        assert start.day == 1
        assert start.year == 2025
        assert start.month == 10
        assert end.year == 2025
        assert end.month == 10

    @patch("src.utils.time_utils.datetime")
    def test_parse_recent_default(self, mock_datetime):
        """Test parsing 'recent' defaults to last N days."""
        # Mock "now" to Oct 25, 2025
        now = datetime(2025, 10, 25, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        start, end, desc = parse_time_period("recent")

        assert "recent" in desc.lower() or "day" in desc.lower()
        assert (end - start).days >= 28  # At least some days

    def test_parse_october_15(self):
        """Test parsing specific date."""
        start, end, desc = parse_time_period("October 15 2025")

        assert start.month == 10
        assert start.day == 15
        assert start.year == 2025
        assert start.date() == end.date()  # Same day
