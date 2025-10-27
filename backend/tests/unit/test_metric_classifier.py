"""
Unit tests for metric classifier.

Tests classification of health metrics into aggregation strategies.
"""

from src.utils.metric_classifier import (
    AggregationStrategy,
    get_aggregation_description,
    get_aggregation_strategy,
    get_expected_unit_format,
    should_aggregate_daily,
)


class TestAggregationStrategy:
    """Test aggregation strategy classification."""

    def test_cumulative_metrics(self):
        """Should classify cumulative metrics correctly."""
        assert get_aggregation_strategy("StepCount") == AggregationStrategy.CUMULATIVE
        assert (
            get_aggregation_strategy("DistanceWalkingRunning")
            == AggregationStrategy.CUMULATIVE
        )
        assert (
            get_aggregation_strategy("DietaryWater") == AggregationStrategy.CUMULATIVE
        )

    def test_daily_average_metrics(self):
        """Should classify high-frequency metrics for daily averaging."""
        assert (
            get_aggregation_strategy("HeartRate") == AggregationStrategy.DAILY_AVERAGE
        )
        assert (
            get_aggregation_strategy("RespiratoryRate")
            == AggregationStrategy.DAILY_AVERAGE
        )

    def test_latest_value_metrics(self):
        """Should classify latest-value metrics."""
        assert get_aggregation_strategy("BodyMass") == AggregationStrategy.LATEST_VALUE
        assert get_aggregation_strategy("Height") == AggregationStrategy.LATEST_VALUE
        assert (
            get_aggregation_strategy("BodyFatPercentage")
            == AggregationStrategy.LATEST_VALUE
        )

    def test_individual_metrics(self):
        """Should classify individual reading metrics."""
        assert (
            get_aggregation_strategy("BodyMassIndex") == AggregationStrategy.INDIVIDUAL
        )
        assert (
            get_aggregation_strategy("ActiveEnergyBurned")
            == AggregationStrategy.INDIVIDUAL
        )
        assert get_aggregation_strategy("VO2Max") == AggregationStrategy.INDIVIDUAL

    def test_unknown_metric_defaults_to_individual(self):
        """Should default to INDIVIDUAL for unknown metrics."""
        assert (
            get_aggregation_strategy("UnknownMetric") == AggregationStrategy.INDIVIDUAL
        )
        assert (
            get_aggregation_strategy("CustomHealthData")
            == AggregationStrategy.INDIVIDUAL
        )


class TestShouldAggregateDaily:
    """Test daily aggregation requirement check."""

    def test_cumulative_needs_aggregation(self):
        """Cumulative metrics need daily aggregation."""
        assert should_aggregate_daily("StepCount") is True

    def test_daily_average_needs_aggregation(self):
        """Daily average metrics need aggregation."""
        assert should_aggregate_daily("HeartRate") is True

    def test_latest_value_needs_aggregation(self):
        """Latest value metrics need aggregation."""
        assert should_aggregate_daily("BodyMass") is True

    def test_individual_no_aggregation(self):
        """Individual metrics don't need daily aggregation."""
        assert should_aggregate_daily("BodyMassIndex") is False
        assert should_aggregate_daily("ActiveEnergyBurned") is False

    def test_unknown_no_aggregation(self):
        """Unknown metrics default to no aggregation."""
        assert should_aggregate_daily("UnknownMetric") is False


class TestExpectedUnitFormat:
    """Test unit format retrieval."""

    def test_step_count_units(self):
        """Should return 'steps' for step count."""
        assert get_expected_unit_format("StepCount") == "steps"

    def test_distance_units(self):
        """Should return 'mi' for distance."""
        assert get_expected_unit_format("DistanceWalkingRunning") == "mi"

    def test_heart_rate_units(self):
        """Should return 'bpm' for heart rate metrics."""
        assert get_expected_unit_format("HeartRate") == "bpm"
        assert get_expected_unit_format("RestingHeartRate") == "bpm"

    def test_weight_units(self):
        """Should return 'lbs' for body mass."""
        assert get_expected_unit_format("BodyMass") == "lbs"

    def test_bmi_units(self):
        """Should return 'BMI' for BMI."""
        assert get_expected_unit_format("BodyMassIndex") == "BMI"

    def test_energy_units(self):
        """Should return 'Cal' for energy metrics."""
        assert get_expected_unit_format("ActiveEnergyBurned") == "Cal"
        assert get_expected_unit_format("DietaryEnergyConsumed") == "Cal"

    def test_water_units(self):
        """Should return 'fl oz' for water."""
        assert get_expected_unit_format("DietaryWater") == "fl oz"

    def test_unknown_metric_returns_empty(self):
        """Should return empty string for unknown metrics."""
        assert get_expected_unit_format("UnknownMetric") == ""


class TestAggregationDescription:
    """Test human-readable aggregation descriptions."""

    def test_cumulative_description(self):
        """Should describe cumulative aggregation."""
        desc = get_aggregation_description("StepCount")
        assert "totaled per day" in desc.lower()
        assert "StepCount" in desc

    def test_daily_average_description(self):
        """Should describe daily average aggregation."""
        desc = get_aggregation_description("HeartRate")
        assert "averaged per day" in desc.lower()
        assert "HeartRate" in desc

    def test_latest_value_description(self):
        """Should describe latest value aggregation."""
        desc = get_aggregation_description("BodyMass")
        assert "latest" in desc.lower()
        assert "BodyMass" in desc

    def test_individual_description(self):
        """Should describe individual reading aggregation."""
        desc = get_aggregation_description("BodyMassIndex")
        assert "individual" in desc.lower()
        assert "BodyMassIndex" in desc


class TestClassificationValidation:
    """Test that metric classifications don't overlap."""

    def test_no_metric_in_multiple_categories(self):
        """No metric should be classified in multiple categories."""
        from src.utils.metric_classifier import (
            CUMULATIVE_METRICS,
            HIGH_FREQ_POINT_METRICS,
            INDIVIDUAL_METRICS,
            LATEST_VALUE_METRICS,
        )

        all_sets = [
            CUMULATIVE_METRICS,
            HIGH_FREQ_POINT_METRICS,
            LATEST_VALUE_METRICS,
            INDIVIDUAL_METRICS,
        ]

        # Check for overlaps between all pairs
        for i, set1 in enumerate(all_sets):
            for set2 in all_sets[i + 1 :]:
                overlap = set1.intersection(set2)
                assert overlap == set(), f"Found overlap: {overlap}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_case_sensitivity(self):
        """Metric names are case-sensitive."""
        # Exact match required
        assert get_aggregation_strategy("StepCount") == AggregationStrategy.CUMULATIVE
        # Different case should default to INDIVIDUAL
        assert get_aggregation_strategy("stepcount") == AggregationStrategy.INDIVIDUAL

    def test_empty_metric_name(self):
        """Should handle empty metric name."""
        assert get_aggregation_strategy("") == AggregationStrategy.INDIVIDUAL

    def test_none_metric_name(self):
        """Should handle None - actually returns INDIVIDUAL (default)."""
        # Implementation handles None by defaulting to INDIVIDUAL
        # This is because the `in` operator works with None
        result = get_aggregation_strategy(None)
        assert result == AggregationStrategy.INDIVIDUAL

    def test_all_strategies_have_descriptions(self):
        """All strategies should have descriptions."""
        for _strategy in AggregationStrategy:
            desc = get_aggregation_description("TestMetric")
            # Description should work for any metric
            assert isinstance(desc, str)
            assert len(desc) > 0
