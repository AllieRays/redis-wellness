"""Unit tests for timezone conversion functionality.

Tests the convert_utc_to_user_timezone function and its integration
with sleep data aggregation.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from src.apple_health.models import SleepSegment, SleepState
from src.utils.sleep_aggregator import aggregate_sleep_by_date
from src.utils.time_utils import convert_utc_to_user_timezone


class TestTimezoneConversion:
    """Test UTC to user timezone conversion."""

    def test_utc_to_pst_conversion(self):
        """Test conversion from UTC to Pacific time."""
        # September 1st, 8:10 AM UTC should be 1:10 AM PDT (daylight saving time)
        utc_time = datetime(2025, 9, 1, 8, 10, 0, tzinfo=UTC)
        pst_time = convert_utc_to_user_timezone(utc_time, "America/Los_Angeles")

        assert pst_time.hour == 1
        assert pst_time.minute == 10
        assert pst_time.tzinfo == ZoneInfo("America/Los_Angeles")

    def test_utc_to_est_conversion(self):
        """Test conversion from UTC to Eastern time."""
        # 12:00 PM UTC should be 8:00 AM EDT (daylight saving time)
        utc_time = datetime(2025, 9, 1, 12, 0, 0, tzinfo=UTC)
        est_time = convert_utc_to_user_timezone(utc_time, "America/New_York")

        assert est_time.hour == 8
        assert est_time.minute == 0
        assert est_time.tzinfo == ZoneInfo("America/New_York")

    def test_utc_to_utc_conversion(self):
        """Test conversion when timezone is UTC (no change)."""
        utc_time = datetime(2025, 9, 1, 8, 10, 0, tzinfo=UTC)
        same_time = convert_utc_to_user_timezone(utc_time, "UTC")

        assert same_time.hour == 8
        assert same_time.minute == 10
        assert same_time.tzinfo == ZoneInfo("UTC")

    def test_naive_datetime_conversion(self):
        """Test conversion with naive datetime (should assume UTC)."""
        naive_time = datetime(2025, 9, 1, 8, 10, 0)
        pst_time = convert_utc_to_user_timezone(naive_time, "America/Los_Angeles")

        # Should assume UTC and convert to PST
        assert pst_time.hour == 1
        assert pst_time.minute == 10

    def test_winter_vs_summer_time(self):
        """Test daylight saving time handling."""
        # Summer (PDT = UTC-7)
        summer_utc = datetime(2025, 7, 1, 8, 0, 0, tzinfo=UTC)
        summer_pst = convert_utc_to_user_timezone(summer_utc, "America/Los_Angeles")
        assert summer_pst.hour == 1  # 8 - 7 = 1 AM PDT

        # Winter (PST = UTC-8)
        winter_utc = datetime(2025, 1, 1, 8, 0, 0, tzinfo=UTC)
        winter_pst = convert_utc_to_user_timezone(winter_utc, "America/Los_Angeles")
        assert winter_pst.hour == 0  # 8 - 8 = 0 AM PST (midnight)


class TestSleepAggregationWithTimezone:
    """Test sleep aggregation with timezone conversion."""

    @pytest.fixture
    def mock_settings(self, monkeypatch):
        """Mock settings to use America/Los_Angeles timezone."""
        from src.config import Settings

        def mock_get_settings():
            settings = Settings()
            settings.user_timezone = "America/Los_Angeles"
            return settings

        # Monkeypatch where it's imported in sleep_aggregator
        monkeypatch.setattr(
            "src.utils.sleep_aggregator.get_settings", mock_get_settings
        )

    def test_sleep_times_converted_to_local_timezone(self, mock_settings):
        """Test that sleep times are converted from UTC to local timezone."""
        # Create sleep segments in UTC
        # 8:10 AM UTC = 1:10 AM PDT (bedtime)
        # 3:25 PM UTC = 8:25 AM PDT (wake time)
        segments = [
            SleepSegment(
                state=SleepState.IN_BED.value,
                start_date=datetime(2025, 9, 1, 8, 10, 0, tzinfo=UTC),
                end_date=datetime(2025, 9, 1, 15, 25, 0, tzinfo=UTC),
                duration_hours=7.25,
                source_name="Test",
            ),
            SleepSegment(
                state=SleepState.ASLEEP_UNSPECIFIED.value,
                start_date=datetime(2025, 9, 1, 8, 15, 0, tzinfo=UTC),
                end_date=datetime(2025, 9, 1, 15, 24, 0, tzinfo=UTC),
                duration_hours=7.15,
                source_name="Test",
            ),
        ]

        # Aggregate sleep data
        summaries = aggregate_sleep_by_date(segments)

        # Verify times are in local timezone (PDT)
        assert len(summaries) == 1
        summary = summaries[0]

        assert summary.date == "2025-09-01"
        assert summary.total_sleep_hours == 7.15
        assert summary.total_in_bed_hours == 7.25
        assert summary.sleep_efficiency == 98.6

        # Critical: Times should be in local timezone (PDT), not UTC
        assert summary.first_sleep_time == "01:10"  # Not "08:10" (UTC)
        assert summary.last_wake_time == "08:25"  # Not "15:25" (UTC)

    def test_sleep_times_with_different_timezone(self, monkeypatch):
        """Test sleep times with a different timezone (EST)."""
        from src.config import Settings

        def mock_get_settings():
            settings = Settings()
            settings.user_timezone = "America/New_York"
            return settings

        monkeypatch.setattr(
            "src.utils.sleep_aggregator.get_settings", mock_get_settings
        )

        segments = [
            SleepSegment(
                state=SleepState.IN_BED.value,
                start_date=datetime(2025, 9, 1, 8, 10, 0, tzinfo=UTC),
                end_date=datetime(2025, 9, 1, 15, 25, 0, tzinfo=UTC),
                duration_hours=7.25,
                source_name="Test",
            ),
        ]

        summaries = aggregate_sleep_by_date(segments)
        summary = summaries[0]

        # EST is UTC-4 during daylight saving time
        # 8:10 AM UTC = 4:10 AM EDT
        # 3:25 PM UTC = 11:25 AM EDT
        assert summary.first_sleep_time == "04:10"
        assert summary.last_wake_time == "11:25"

    def test_sleep_times_utc_timezone(self, monkeypatch):
        """Test that UTC timezone shows times without conversion."""
        from src.config import Settings

        def mock_get_settings():
            settings = Settings()
            settings.user_timezone = "UTC"
            return settings

        monkeypatch.setattr(
            "src.utils.sleep_aggregator.get_settings", mock_get_settings
        )

        segments = [
            SleepSegment(
                state=SleepState.IN_BED.value,
                start_date=datetime(2025, 9, 1, 8, 10, 0, tzinfo=UTC),
                end_date=datetime(2025, 9, 1, 15, 25, 0, tzinfo=UTC),
                duration_hours=7.25,
                source_name="Test",
            ),
        ]

        summaries = aggregate_sleep_by_date(segments)
        summary = summaries[0]

        # UTC should show original times
        assert summary.first_sleep_time == "08:10"
        assert summary.last_wake_time == "15:25"

    def test_multiple_nights_timezone_conversion(self, mock_settings):
        """Test timezone conversion across multiple nights."""
        segments = [
            # Night 1: Sept 1
            SleepSegment(
                state=SleepState.ASLEEP_UNSPECIFIED.value,
                start_date=datetime(2025, 9, 1, 8, 0, 0, tzinfo=UTC),
                end_date=datetime(2025, 9, 1, 15, 0, 0, tzinfo=UTC),
                duration_hours=7.0,
                source_name="Test",
            ),
            # Night 2: Sept 2
            SleepSegment(
                state=SleepState.ASLEEP_UNSPECIFIED.value,
                start_date=datetime(2025, 9, 2, 9, 0, 0, tzinfo=UTC),
                end_date=datetime(2025, 9, 2, 16, 0, 0, tzinfo=UTC),
                duration_hours=7.0,
                source_name="Test",
            ),
        ]

        summaries = aggregate_sleep_by_date(segments)

        assert len(summaries) == 2
        # Sept 1: 8:00 UTC = 1:00 AM PDT, 15:00 UTC = 8:00 AM PDT
        assert summaries[0].first_sleep_time == "01:00"
        assert summaries[0].last_wake_time == "08:00"

        # Sept 2: 9:00 UTC = 2:00 AM PDT, 16:00 UTC = 9:00 AM PDT
        assert summaries[1].first_sleep_time == "02:00"
        assert summaries[1].last_wake_time == "09:00"
