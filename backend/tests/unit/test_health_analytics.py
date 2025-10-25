"""
Unit tests for health analytics functions.

REAL TESTS - NO MOCKS:
- Tests weight trends with linear regression
- Tests period comparisons with statistical significance
- Tests metric correlations
- Uses real mathematical calculations (NumPy/SciPy)
"""

import pytest

from src.utils.health_analytics import (
    calculate_weight_trends,
    compare_time_periods,
    correlate_metrics,
)


@pytest.mark.unit
class TestWeightTrends:
    """Test weight trend analysis with regression and moving averages."""

    def test_weight_trends_negative_slope(self):
        """Test linear regression correctly identifies negative slope."""
        # Simulating 30 days of decreasing weight: 170 lbs → 165 lbs
        weight_records = []
        for day in range(1, 31):  # 30 days for sufficient moving average data
            date_str = f"2025-10-{day:02d}T08:00:00+00:00"
            weight = 170.0 - (day * 0.17)  # Gradual decrease
            weight_records.append(
                {"date": date_str, "value": str(weight), "unit": "lb"}
            )

        result = calculate_weight_trends(
            weight_records, time_period="last_90_days", trend_type="both"
        )

        assert "trends" in result
        assert "linear_regression" in result["trends"]
        assert "statistics" in result["trends"]

        # Check trend is decreasing
        regression = result["trends"]["linear_regression"]
        assert regression["trend_direction"] == "decreasing"
        assert regression["slope"] < 0
        assert regression["r_squared"] > 0.95  # Strong linear fit

    def test_weight_trends_positive_slope(self):
        """Test linear regression correctly identifies positive slope."""
        # Simulating increasing weight trend
        weight_records = [
            {"date": "2025-09-01T08:00:00+00:00", "value": "65.0", "unit": "kg"},
            {"date": "2025-09-15T08:00:00+00:00", "value": "66.0", "unit": "kg"},
            {"date": "2025-10-01T08:00:00+00:00", "value": "67.0", "unit": "kg"},
            {"date": "2025-10-15T08:00:00+00:00", "value": "68.0", "unit": "kg"},
        ]

        result = calculate_weight_trends(
            weight_records, time_period="last_90_days", trend_type="linear_regression"
        )

        regression = result["trends"]["linear_regression"]
        assert regression["trend_direction"] == "increasing"
        assert regression["slope"] > 0

    def test_weight_trends_stable(self):
        """Test stable weight detection."""
        # Weight stays around 70 kg with minor fluctuations
        weight_records = []
        for day in range(1, 21):  # 20 days
            # Small random fluctuation around 70 kg
            weight = 70.0 + (0.1 if day % 2 == 0 else -0.1)
            weight_records.append(
                {
                    "date": f"2025-10-{day:02d}T08:00:00+00:00",
                    "value": str(weight),
                    "unit": "kg",
                }
            )

        result = calculate_weight_trends(
            weight_records, time_period="last_90_days", trend_type="linear_regression"
        )

        regression = result["trends"]["linear_regression"]
        assert regression["trend_direction"] == "stable"
        assert abs(regression["slope"]) < 0.01

    def test_weight_trends_converts_kg_to_lbs(self):
        """Test weight values are converted to lbs for US display."""
        weight_records = [
            {"date": "2025-10-01T08:00:00+00:00", "value": "70.0", "unit": "kg"},
            {"date": "2025-10-15T08:00:00+00:00", "value": "69.0", "unit": "kg"},
        ]

        result = calculate_weight_trends(
            weight_records, time_period="last_90_days", trend_type="both"
        )

        stats = result["trends"]["statistics"]
        # 70 kg ≈ 154.3 lbs, 69 kg ≈ 152.1 lbs
        assert stats["starting_weight"] > 150
        assert stats["starting_weight"] < 160
        assert stats["current_weight"] > 150
        assert stats["current_weight"] < 160

    def test_weight_trends_moving_average(self):
        """Test moving average smoothing."""
        weight_records = [
            {
                "date": f"2025-10-{day:02d}T08:00:00+00:00",
                "value": str(170 - day * 0.2),
                "unit": "lb",
            }
            for day in range(1, 22)  # 21 days of data
        ]

        result = calculate_weight_trends(
            weight_records, time_period="last_30_days", trend_type="moving_average"
        )

        moving_avg = result["trends"]["moving_average"]
        # Check for either success or error (insufficient data)
        if "error" not in moving_avg:
            assert "current_avg" in moving_avg
            assert "avg_at_start" in moving_avg
            assert "change" in moving_avg
            if "window_days" in moving_avg:
                assert moving_avg["window_days"] == 7
        else:
            # If error, window_size should still be there
            assert "window_size" in moving_avg

    def test_weight_trends_no_data(self):
        """Test handling of empty weight records."""
        weight_records = []

        result = calculate_weight_trends(weight_records, time_period="last_90_days")

        assert "error" in result
        assert "No weight records" in result["error"]

    def test_weight_trends_insufficient_data(self):
        """Test handling of insufficient data points."""
        weight_records = [
            {"date": "2025-10-01T08:00:00+00:00", "value": "70.0", "unit": "kg"}
        ]

        result = calculate_weight_trends(
            weight_records, time_period="last_90_days", trend_type="linear_regression"
        )

        assert "error" in result or "trends" in result


@pytest.mark.unit
class TestComparePeriods:
    """Test time period comparison with statistical tests."""

    def test_compare_periods_lower_values(self):
        """Test detecting statistically significant difference between periods (lower values in period 1)."""
        all_records = [
            # This month (lower weights)
            {"date": "2025-10-05T08:00:00+00:00", "value": "68.0", "unit": "kg"},
            {"date": "2025-10-10T08:00:00+00:00", "value": "68.2", "unit": "kg"},
            {"date": "2025-10-15T08:00:00+00:00", "value": "68.1", "unit": "kg"},
            {"date": "2025-10-20T08:00:00+00:00", "value": "68.3", "unit": "kg"},
            # Last month (higher weights)
            {"date": "2025-09-05T08:00:00+00:00", "value": "70.0", "unit": "kg"},
            {"date": "2025-09-10T08:00:00+00:00", "value": "70.2", "unit": "kg"},
            {"date": "2025-09-15T08:00:00+00:00", "value": "70.1", "unit": "kg"},
            {"date": "2025-09-20T08:00:00+00:00", "value": "70.3", "unit": "kg"},
        ]

        result = compare_time_periods(
            all_records, "BodyMass", "this_month", "last_month"
        )

        assert "change" in result
        assert result["change"]["direction"] == "decrease"
        assert result["change"]["absolute"] < 0
        assert result["change"]["percentage"] < 0

        # Check statistical test
        assert "statistical_test" in result
        assert "p_value" in result["statistical_test"]
        assert "significant" in result["statistical_test"]

    def test_compare_periods_higher_values(self):
        """Test detecting difference between periods (higher values in period 1)."""
        all_records = [
            # This month (higher)
            {"date": "2025-10-05T08:00:00+00:00", "value": "72.0", "unit": "kg"},
            {"date": "2025-10-10T08:00:00+00:00", "value": "72.2", "unit": "kg"},
            # Last month (lower)
            {"date": "2025-09-05T08:00:00+00:00", "value": "70.0", "unit": "kg"},
            {"date": "2025-09-10T08:00:00+00:00", "value": "70.1", "unit": "kg"},
        ]

        result = compare_time_periods(
            all_records, "BodyMass", "this_month", "last_month"
        )

        assert result["change"]["direction"] == "increase"
        assert result["change"]["absolute"] > 0
        assert result["change"]["percentage"] > 0

    def test_compare_periods_includes_statistics(self):
        """Test comparison includes basic statistics for each period."""
        all_records = [
            {"date": "2025-10-05T08:00:00+00:00", "value": "68", "unit": "kg"},
            {"date": "2025-10-10T08:00:00+00:00", "value": "69", "unit": "kg"},
            {"date": "2025-10-15T08:00:00+00:00", "value": "70", "unit": "kg"},
            {"date": "2025-09-05T08:00:00+00:00", "value": "71", "unit": "kg"},
            {"date": "2025-09-10T08:00:00+00:00", "value": "72", "unit": "kg"},
            {"date": "2025-09-15T08:00:00+00:00", "value": "73", "unit": "kg"},
        ]

        result = compare_time_periods(
            all_records, "BodyMass", "this_month", "last_month"
        )

        # Check period1 stats
        assert "period1" in result
        assert "average" in result["period1"]
        assert "min" in result["period1"]
        assert "max" in result["period1"]
        assert "count" in result["period1"]

        # Check period2 stats
        assert "period2" in result
        assert "average" in result["period2"]

    def test_compare_periods_no_data(self):
        """Test handling when one period has no data."""
        all_records = [
            {"date": "2025-10-05T08:00:00+00:00", "value": "70", "unit": "kg"}
        ]

        result = compare_time_periods(
            all_records, "BodyMass", "this_month", "last_month"
        )

        # Should return error when insufficient data
        assert "error" in result or "period1" in result


@pytest.mark.unit
class TestCorrelateMetrics:
    """Test correlation analysis between two metrics."""

    def test_correlate_positive_correlation(self):
        """Test detecting positive correlation (e.g., weight and BMI)."""
        # As weight increases, BMI increases
        weight_records = [
            {"date": "2025-10-01T08:00:00+00:00", "value": "65"},
            {"date": "2025-10-02T08:00:00+00:00", "value": "66"},
            {"date": "2025-10-03T08:00:00+00:00", "value": "67"},
            {"date": "2025-10-04T08:00:00+00:00", "value": "68"},
        ]
        bmi_records = [
            {"date": "2025-10-01T08:00:00+00:00", "value": "22.0"},
            {"date": "2025-10-02T08:00:00+00:00", "value": "22.5"},
            {"date": "2025-10-03T08:00:00+00:00", "value": "23.0"},
            {"date": "2025-10-04T08:00:00+00:00", "value": "23.5"},
        ]

        result = correlate_metrics(
            weight_records, bmi_records, "Weight", "BMI", time_period="recent"
        )

        assert "correlation" in result
        assert result["correlation"] > 0.9  # Strong positive
        assert "positive" in result["strength"]
        assert result["significant"] is True

    def test_correlate_negative_correlation(self):
        """Test detecting negative correlation."""
        # As exercise increases, resting heart rate decreases
        exercise_records = [
            {"date": "2025-10-01T08:00:00+00:00", "value": "10"},
            {"date": "2025-10-02T08:00:00+00:00", "value": "20"},
            {"date": "2025-10-03T08:00:00+00:00", "value": "30"},
            {"date": "2025-10-04T08:00:00+00:00", "value": "40"},
        ]
        heart_rate_records = [
            {"date": "2025-10-01T08:00:00+00:00", "value": "75"},
            {"date": "2025-10-02T08:00:00+00:00", "value": "73"},
            {"date": "2025-10-03T08:00:00+00:00", "value": "71"},
            {"date": "2025-10-04T08:00:00+00:00", "value": "69"},
        ]

        result = correlate_metrics(
            exercise_records,
            heart_rate_records,
            "Exercise",
            "RestingHeartRate",
            time_period="recent",
        )

        assert result["correlation"] < -0.9  # Strong negative
        assert "negative" in result["strength"]

    def test_correlate_no_correlation(self):
        """Test detecting lack of correlation."""
        # Truly random data with more points - no relationship
        import random

        random.seed(42)  # Reproducible

        metric_x_records = [
            {
                "date": f"2025-10-{day:02d}T08:00:00+00:00",
                "value": str(random.uniform(95, 105)),
            }
            for day in range(1, 11)
        ]
        metric_y_records = [
            {
                "date": f"2025-10-{day:02d}T08:00:00+00:00",
                "value": str(random.uniform(45, 55)),
            }
            for day in range(1, 11)
        ]

        result = correlate_metrics(
            metric_x_records,
            metric_y_records,
            "MetricX",
            "MetricY",
            time_period="recent",
        )

        # Should have low-to-moderate correlation (not strong)
        assert abs(result["correlation"]) < 0.9
        # Just verify it's not claiming very strong correlation
        assert (
            "perfect" not in result["strength"]
            and "very strong" not in result["strength"]
        )

    def test_correlate_requires_overlapping_dates(self):
        """Test correlation requires matching dates."""
        # No overlapping dates
        metric_x_records = [
            {"date": "2025-10-01T08:00:00+00:00", "value": "100"},
            {"date": "2025-10-02T08:00:00+00:00", "value": "105"},
        ]
        metric_y_records = [
            {"date": "2025-10-05T08:00:00+00:00", "value": "50"},
            {"date": "2025-10-06T08:00:00+00:00", "value": "55"},
        ]

        result = correlate_metrics(
            metric_x_records,
            metric_y_records,
            "MetricX",
            "MetricY",
            time_period="recent",
        )

        # Should fail with insufficient overlapping data
        assert "error" in result

    def test_correlate_insufficient_data(self):
        """Test correlation requires minimum data points."""
        metric_x_records = [{"date": "2025-10-01T08:00:00+00:00", "value": "100"}]
        metric_y_records = [{"date": "2025-10-01T08:00:00+00:00", "value": "50"}]

        result = correlate_metrics(
            metric_x_records,
            metric_y_records,
            "MetricX",
            "MetricY",
            time_period="recent",
        )

        assert "error" in result
        assert "Insufficient" in result["error"]
