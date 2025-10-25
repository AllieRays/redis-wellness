"""
Unit tests for metric aggregation strategies.

REAL TESTS - NO MOCKS:
- Tests pure aggregation functions with real health data
- Tests metric classification and strategy selection
- No external dependencies
"""

from datetime import UTC, date, datetime

import pytest

from src.utils.metric_aggregators import (
    aggregate_daily_averages,
    aggregate_daily_latest,
    aggregate_daily_sums,
    aggregate_metric_values,
    get_aggregation_summary,
    get_individual_values,
)
from src.utils.metric_classifier import (
    AggregationStrategy,
    get_aggregation_strategy,
    should_aggregate_daily,
)


@pytest.mark.unit
class TestAggregationStrategyClassification:
    """Test metric type classification."""

    def test_cumulative_metrics_classified_correctly(self):
        """Test StepCount uses cumulative strategy."""
        strategy = get_aggregation_strategy("StepCount")
        assert strategy == AggregationStrategy.CUMULATIVE

    def test_high_freq_metrics_classified_correctly(self):
        """Test HeartRate uses daily average strategy."""
        strategy = get_aggregation_strategy("HeartRate")
        assert strategy == AggregationStrategy.DAILY_AVERAGE

    def test_latest_value_metrics_classified_correctly(self):
        """Test BodyMass uses latest value strategy."""
        strategy = get_aggregation_strategy("BodyMass")
        assert strategy == AggregationStrategy.LATEST_VALUE

    def test_individual_metrics_classified_correctly(self):
        """Test BodyMassIndex uses individual strategy."""
        strategy = get_aggregation_strategy("BodyMassIndex")
        assert strategy == AggregationStrategy.INDIVIDUAL

    def test_unknown_metric_defaults_to_individual(self):
        """Test unknown metrics default to individual readings."""
        strategy = get_aggregation_strategy("UnknownMetric")
        assert strategy == AggregationStrategy.INDIVIDUAL

    def test_should_aggregate_daily_for_cumulative(self):
        """Test cumulative metrics require daily aggregation."""
        assert should_aggregate_daily("StepCount") is True

    def test_should_not_aggregate_daily_for_individual(self):
        """Test individual metrics don't require daily aggregation."""
        assert should_aggregate_daily("BodyMassIndex") is False


@pytest.mark.unit
class TestDailySums:
    """Test daily sum aggregation (for cumulative metrics like StepCount)."""

    def test_step_count_sums_per_day(self):
        """Test StepCount incremental readings sum per day."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "250"},
            {"date": "2025-10-17T12:00:00+00:00", "value": "488"},
            {"date": "2025-10-17T18:00:00+00:00", "value": "686"},
            {"date": "2025-10-18T08:00:00+00:00", "value": "300"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 19, tzinfo=UTC),
        )

        daily_totals = aggregate_daily_sums(records, date_range)

        assert daily_totals[date(2025, 10, 17)] == 1424.0  # 250 + 488 + 686
        assert daily_totals[date(2025, 10, 18)] == 300.0

    def test_daily_sums_filters_by_date_range(self):
        """Test daily sums respects date range filtering."""
        records = [
            {"date": "2025-10-15T12:00:00+00:00", "value": "100"},  # Before range
            {"date": "2025-10-17T12:00:00+00:00", "value": "200"},  # In range
            {"date": "2025-10-20T12:00:00+00:00", "value": "300"},  # After range
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        daily_totals = aggregate_daily_sums(records, date_range)

        assert date(2025, 10, 15) not in daily_totals
        assert date(2025, 10, 17) in daily_totals
        assert daily_totals[date(2025, 10, 17)] == 200.0
        assert date(2025, 10, 20) not in daily_totals

    def test_daily_sums_handles_invalid_values(self):
        """Test daily sums skips invalid numeric values."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "100"},
            {"date": "2025-10-17T12:00:00+00:00", "value": "invalid"},  # Skip
            {"date": "2025-10-17T18:00:00+00:00", "value": "200"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        daily_totals = aggregate_daily_sums(records, date_range)

        assert daily_totals[date(2025, 10, 17)] == 300.0  # Only valid values


@pytest.mark.unit
class TestDailyAverages:
    """Test daily average aggregation (for high-frequency metrics like HeartRate)."""

    def test_heart_rate_averages_per_day(self):
        """Test HeartRate multiple readings average per day."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "81"},
            {"date": "2025-10-17T12:00:00+00:00", "value": "87"},
            {"date": "2025-10-17T16:00:00+00:00", "value": "77"},
            {"date": "2025-10-17T20:00:00+00:00", "value": "77"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        daily_averages = aggregate_daily_averages(records, date_range)

        # (81 + 87 + 77 + 77) / 4 = 80.5
        assert daily_averages[date(2025, 10, 17)] == pytest.approx(80.5, abs=0.1)

    def test_daily_averages_multiple_days(self):
        """Test daily averages across multiple days."""
        records = [
            {"date": "2025-10-17T12:00:00+00:00", "value": "80"},
            {"date": "2025-10-17T18:00:00+00:00", "value": "90"},
            {"date": "2025-10-18T12:00:00+00:00", "value": "70"},
            {"date": "2025-10-18T18:00:00+00:00", "value": "80"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 19, tzinfo=UTC),
        )

        daily_averages = aggregate_daily_averages(records, date_range)

        assert daily_averages[date(2025, 10, 17)] == pytest.approx(85.0, abs=0.1)
        assert daily_averages[date(2025, 10, 18)] == pytest.approx(75.0, abs=0.1)


@pytest.mark.unit
class TestDailyLatest:
    """Test latest value aggregation (for measurements like BodyMass)."""

    def test_body_mass_uses_latest_per_day(self):
        """Test BodyMass uses latest reading when multiple per day."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "138.6"},  # Morning
            {"date": "2025-10-17T12:00:00+00:00", "value": "137.2"},  # Midday
            {"date": "2025-10-17T20:00:00+00:00", "value": "137.6"},  # Evening (latest)
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        daily_latest = aggregate_daily_latest(records, date_range)

        # Should use 137.6 (latest reading at 20:00)
        assert daily_latest[date(2025, 10, 17)] == 137.6

    def test_daily_latest_multiple_days(self):
        """Test latest value across multiple days."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "70.0"},
            {"date": "2025-10-17T20:00:00+00:00", "value": "69.8"},  # Latest day 1
            {"date": "2025-10-18T08:00:00+00:00", "value": "69.9"},
            {"date": "2025-10-18T20:00:00+00:00", "value": "69.7"},  # Latest day 2
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 19, tzinfo=UTC),
        )

        daily_latest = aggregate_daily_latest(records, date_range)

        assert daily_latest[date(2025, 10, 17)] == 69.8
        assert daily_latest[date(2025, 10, 18)] == 69.7


@pytest.mark.unit
class TestIndividualValues:
    """Test individual value extraction (for complete metrics like BodyMassIndex)."""

    def test_body_mass_index_uses_individual_readings(self):
        """Test BMI uses each reading directly."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "23.9"},
            {"date": "2025-10-17T20:00:00+00:00", "value": "23.7"},
            {"date": "2025-10-18T08:00:00+00:00", "value": "23.8"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 19, tzinfo=UTC),
        )

        values = get_individual_values(records, date_range)

        assert len(values) == 3
        assert values == [23.9, 23.7, 23.8]


@pytest.mark.unit
class TestAggregateMetricValues:
    """Test main aggregation entry point that selects strategy automatically."""

    def test_aggregate_step_count_sums(self):
        """Test StepCount automatically uses sum strategy."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "100"},
            {"date": "2025-10-17T12:00:00+00:00", "value": "200"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        values = aggregate_metric_values(records, "StepCount", date_range)

        assert len(values) == 1
        assert values[0] == 300.0  # Sum per day

    def test_aggregate_heart_rate_averages(self):
        """Test HeartRate automatically uses average strategy."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "80"},
            {"date": "2025-10-17T12:00:00+00:00", "value": "90"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        values = aggregate_metric_values(records, "HeartRate", date_range)

        assert len(values) == 1
        assert values[0] == pytest.approx(85.0, abs=0.1)  # Average per day

    def test_aggregate_body_mass_latest(self):
        """Test BodyMass automatically uses latest value strategy."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "70.0"},
            {"date": "2025-10-17T20:00:00+00:00", "value": "69.8"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        values = aggregate_metric_values(records, "BodyMass", date_range)

        assert len(values) == 1
        assert values[0] == 69.8  # Latest value

    def test_aggregate_bmi_individual(self):
        """Test BodyMassIndex automatically uses individual strategy."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "23.9"},
            {"date": "2025-10-17T20:00:00+00:00", "value": "23.7"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        values = aggregate_metric_values(records, "BodyMassIndex", date_range)

        assert len(values) == 2  # All individual readings
        assert values == [23.9, 23.7]


@pytest.mark.unit
class TestAggregationSummary:
    """Test aggregation metadata and debugging info."""

    def test_aggregation_summary_includes_strategy(self):
        """Test summary includes strategy used."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "100"},
            {"date": "2025-10-17T12:00:00+00:00", "value": "200"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        summary = get_aggregation_summary(records, "StepCount", date_range)

        assert summary["metric_type"] == "StepCount"
        assert summary["strategy"] == "cumulative"
        assert summary["original_records"] == 2
        assert summary["aggregated_values"] == 1  # 2 records → 1 daily total

    def test_aggregation_summary_shows_reduction_ratio(self):
        """Test summary calculates reduction ratio."""
        records = [
            {"date": "2025-10-17T08:00:00+00:00", "value": "80"},
            {"date": "2025-10-17T12:00:00+00:00", "value": "85"},
            {"date": "2025-10-17T16:00:00+00:00", "value": "90"},
            {"date": "2025-10-17T20:00:00+00:00", "value": "75"},
        ]
        date_range = (
            datetime(2025, 10, 17, tzinfo=UTC),
            datetime(2025, 10, 18, tzinfo=UTC),
        )

        summary = get_aggregation_summary(records, "HeartRate", date_range)

        # 4 records aggregated to 1 daily average
        assert summary["original_records"] == 4
        assert summary["aggregated_values"] == 1
        assert summary["reduction_ratio"] == pytest.approx(4.0, abs=0.1)
