"""Unit tests for Apple Health models."""

from datetime import UTC, datetime

from src.apple_health.models import (
    HealthMetricType,
    HealthRecord,
)


class TestHealthMetricType:
    """Tests for HealthMetricType enum."""

    def test_resting_heart_rate_exists(self):
        """Verify RestingHeartRate is a recognized metric type."""
        assert hasattr(HealthMetricType, "RESTING_HEART_RATE")
        assert (
            HealthMetricType.RESTING_HEART_RATE.value
            == "HKQuantityTypeIdentifierRestingHeartRate"
        )

    def test_heart_rate_exists(self):
        """Verify HeartRate is a recognized metric type."""
        assert hasattr(HealthMetricType, "HEART_RATE")
        assert HealthMetricType.HEART_RATE.value == "HKQuantityTypeIdentifierHeartRate"

    def test_resting_heart_rate_distinct_from_heart_rate(self):
        """Verify RestingHeartRate and HeartRate are different types."""
        assert HealthMetricType.RESTING_HEART_RATE != HealthMetricType.HEART_RATE


class TestHealthRecord:
    """Tests for HealthRecord model."""

    def test_parse_resting_heart_rate_record(self):
        """Verify RestingHeartRate records are parsed correctly."""
        record = HealthRecord(
            record_type="HKQuantityTypeIdentifierRestingHeartRate",
            unit="count/min",
            value="73",
            start_date=datetime(2023, 10, 17, 1, 0, 0, tzinfo=UTC),
            end_date=datetime(2023, 10, 17, 1, 0, 0, tzinfo=UTC),
            source_name="Apple Watch",
            creation_date=datetime(2023, 10, 17, 2, 0, 0, tzinfo=UTC),
        )

        assert record.record_type == HealthMetricType.RESTING_HEART_RATE
        assert record.value == "73"
        assert record.unit == "count/min"

    def test_parse_heart_rate_record(self):
        """Verify HeartRate records are parsed correctly."""
        record = HealthRecord(
            record_type="HKQuantityTypeIdentifierHeartRate",
            unit="count/min",
            value="120",
            start_date=datetime(2023, 10, 17, 14, 30, 0, tzinfo=UTC),
            end_date=datetime(2023, 10, 17, 14, 30, 0, tzinfo=UTC),
            source_name="Apple Watch",
            creation_date=datetime(2023, 10, 17, 14, 35, 0, tzinfo=UTC),
        )

        assert record.record_type == HealthMetricType.HEART_RATE
        assert record.value == "120"

    def test_normalize_unknown_type_to_other(self):
        """Verify unknown metric types fall back to OTHER."""
        record = HealthRecord(
            record_type="HKQuantityTypeIdentifierUnknownMetric",
            unit="unknown",
            value="42",
            start_date=datetime(2023, 10, 17, 1, 0, 0, tzinfo=UTC),
            end_date=datetime(2023, 10, 17, 1, 0, 0, tzinfo=UTC),
        )

        assert record.record_type == HealthMetricType.OTHER

    def test_resting_heart_rate_not_classified_as_other(self):
        """
        Regression test: Ensure RestingHeartRate is not classified as OTHER.

        This was a bug where RestingHeartRate wasn't in the enum,
        causing all 258 records to be misclassified as OTHER.
        """
        record = HealthRecord(
            record_type="HKQuantityTypeIdentifierRestingHeartRate",
            unit="count/min",
            value="73",
            start_date=datetime(2023, 10, 17, 1, 0, 0, tzinfo=UTC),
            end_date=datetime(2023, 10, 17, 1, 0, 0, tzinfo=UTC),
        )

        # Critical assertion: should NOT be OTHER
        assert record.record_type != HealthMetricType.OTHER
        assert record.record_type == HealthMetricType.RESTING_HEART_RATE
