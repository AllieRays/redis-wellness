"""
Test mathematical accuracy of health analysis tools.

Ensures that all calculations are correct and produce expected results.
Tests pure functions with known inputs/outputs.
"""

from datetime import datetime, timedelta

import pytest

from src.utils.conversion_utils import kg_to_lbs, lbs_to_kg
from src.utils.health_analytics import (
    calculate_weight_trends,
    compare_time_periods,
)
from src.utils.stats_utils import (
    calculate_basic_stats,
    calculate_linear_regression,
    calculate_moving_average,
    calculate_pearson_correlation,
    calculate_percentage_change,
    compare_periods,
)
from src.utils.time_utils import parse_time_period


class TestConversionUtils:
    """Test unit conversion accuracy."""

    def test_kg_to_lbs_conversion(self):
        """Test kilograms to pounds conversion."""
        assert abs(kg_to_lbs(72.5) - 159.83) < 0.01
        assert abs(kg_to_lbs(100) - 220.46) < 0.01
        assert abs(kg_to_lbs(50) - 110.23) < 0.01

    def test_lbs_to_kg_conversion(self):
        """Test pounds to kilograms conversion."""
        assert abs(lbs_to_kg(160) - 72.57) < 0.01
        assert abs(lbs_to_kg(220.46) - 100.0) < 0.01
        assert abs(lbs_to_kg(110.23) - 50.0) < 0.01

    def test_round_trip_conversion(self):
        """Test that converting kg→lbs→kg gives original value."""
        original = 75.0
        converted = kg_to_lbs(original)
        back = lbs_to_kg(converted)
        assert abs(original - back) < 0.001


class TestStatsUtils:
    """Test statistical utility functions."""

    def test_calculate_basic_stats(self):
        """Test basic statistics calculation."""
        values = [1, 2, 3, 4, 5]
        stats = calculate_basic_stats(values)

        assert stats["average"] == 3.0
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["count"] == 5
        assert abs(stats["std_dev"] - 1.414) < 0.01

    def test_calculate_basic_stats_empty(self):
        """Test basic statistics with empty list."""
        stats = calculate_basic_stats([])
        assert stats["count"] == 0
        assert stats["average"] == 0.0

    def test_calculate_linear_regression(self):
        """Test linear regression with perfect linear data."""
        # Perfect linear relationship: y = 2x + 1
        dates = [datetime(2025, 1, i) for i in range(1, 11)]
        values = [2 * i + 1 for i in range(1, 11)]

        regression = calculate_linear_regression(dates, values)

        # Slope should be 2.0 (2 units per day)
        assert abs(regression["slope"] - 2.0) < 0.01
        # R² should be 1.0 (perfect fit)
        assert abs(regression["r_squared"] - 1.0) < 0.01
        assert regression["trend_direction"] == "increasing"

    def test_calculate_moving_average(self):
        """Test moving average calculation."""
        values = [10, 12, 11, 13, 12, 14, 13]
        result = calculate_moving_average(values, window_size=3)

        assert result["window_size"] == 3
        assert len(result["values"]) == 5  # 7 - 3 + 1
        # First value should be average of [10, 12, 11]
        assert abs(result["values"][0] - 11.0) < 0.01

    def test_calculate_percentage_change(self):
        """Test percentage change calculation."""
        assert abs(calculate_percentage_change(100, 110) - 10.0) < 0.01
        assert abs(calculate_percentage_change(110, 100) - (-9.09)) < 0.01
        assert calculate_percentage_change(0, 10) == 0.0  # Handle zero

    def test_calculate_pearson_correlation(self):
        """Test Pearson correlation calculation."""
        # Perfect positive correlation
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        result = calculate_pearson_correlation(x, y)

        assert abs(result["correlation"] - 1.0) < 0.01
        assert result["significant"]
        assert "positive" in result["strength"]

        # Perfect negative correlation
        y_neg = [10, 8, 6, 4, 2]
        result_neg = calculate_pearson_correlation(x, y_neg)

        assert abs(result_neg["correlation"] - (-1.0)) < 0.01
        assert "negative" in result_neg["strength"]

    def test_compare_periods(self):
        """Test period comparison."""
        period1 = [100, 102, 101, 103, 102]  # avg: 101.6
        period2 = [95, 97, 96, 98, 97]  # avg: 96.6

        result = compare_periods(period1, period2, "This Month", "Last Month")

        assert abs(result["period1"]["average"] - 101.6) < 0.1
        assert abs(result["period2"]["average"] - 96.6) < 0.1
        assert result["change"]["direction"] == "increase"
        assert abs(result["change"]["absolute"] - 5.0) < 0.1


class TestTimeUtils:
    """Test time parsing utilities."""

    def test_parse_time_period_month(self):
        """Test parsing month names."""
        start, end, desc = parse_time_period("September")
        assert start.month == 9
        assert start.day == 1
        assert end.month == 9
        assert end.day == 30

    def test_parse_time_period_month_with_year(self):
        """Test parsing month with year."""
        start, end, desc = parse_time_period("September 2024")
        assert start.year == 2024
        assert start.month == 9

    def test_parse_time_period_early_month(self):
        """Test parsing early month qualifier."""
        start, end, desc = parse_time_period("early September")
        assert start.day == 1
        assert end.day == 10

    def test_parse_time_period_last_n_days(self):
        """Test parsing 'last N days'."""
        start, end, desc = parse_time_period("last 7 days")
        now = datetime.now()
        days_diff = (now - start).days
        assert 6 <= days_diff <= 7  # Account for partial days

    def test_parse_time_period_this_month(self):
        """Test parsing 'this month'."""
        start, end, desc = parse_time_period("this month")
        now = datetime.now()
        assert start.year == now.year
        assert start.month == now.month
        assert start.day == 1


class TestWeightTrends:
    """Test weight trend analysis with realistic data."""

    def create_sample_weight_records(
        self, num_days=90, start_weight=172.5, daily_change=-0.05
    ):
        """Create sample weight records for testing."""
        records = []
        current_date = datetime.now() - timedelta(days=num_days)

        for i in range(num_days):
            date_str = current_date.strftime("%Y-%m-%d %H:%M:%S")
            weight_kg = (
                start_weight + (i * daily_change)
            ) / 2.20462  # Convert lbs to kg

            records.append(
                {"date": date_str, "value": f"{weight_kg:.2f}", "unit": "kg"}
            )

            current_date += timedelta(days=1)

        return records

    def test_calculate_weight_trends_linear_regression(self):
        """Test weight trend calculation with decreasing trend."""
        # Create data: starting at 172.5 lbs, decreasing 0.05 lbs/day
        records = self.create_sample_weight_records(
            num_days=90, start_weight=172.5, daily_change=-0.05
        )

        result = calculate_weight_trends(records, "last_90_days", "linear_regression")

        assert "trends" in result
        assert "linear_regression" in result["trends"]

        regression = result["trends"]["linear_regression"]

        # Should show decreasing trend
        assert regression["trend_direction"] == "decreasing"
        # Slope should be approximately -0.05 lbs/day
        assert abs(regression["slope"] - (-0.05)) < 0.02
        # Should be statistically significant
        assert regression["significance"] == "significant"
        assert regression["r_squared"] > 0.9  # Very high correlation for linear data

    def test_calculate_weight_trends_statistics(self):
        """Test that statistics are calculated correctly."""
        records = self.create_sample_weight_records(
            num_days=90, start_weight=172.5, daily_change=-0.05
        )

        result = calculate_weight_trends(records, "last_90_days", "both")

        stats = result["trends"]["statistics"]

        # Check that we have all required statistics
        assert "current_weight" in stats
        assert "starting_weight" in stats
        assert "total_change" in stats
        assert "average_weight" in stats

        # Starting weight should be approximately 172.5 lbs
        assert abs(stats["starting_weight"] - 172.5) < 1.0
        # Total change should be approximately -4.5 lbs (90 days * -0.05)
        assert abs(stats["total_change"] - (-4.5)) < 1.0

    def test_calculate_weight_trends_empty_data(self):
        """Test weight trends with empty data."""
        result = calculate_weight_trends([], "last_90_days", "both")
        assert "error" in result


class TestComparePeriods:
    """Test period comparison functionality."""

    def create_sample_metric_records(self, num_days=60, base_value=100, variation=5):
        """Create sample metric records."""
        import random

        records = []
        current_date = datetime.now() - timedelta(days=num_days)

        for _i in range(num_days):
            date_str = current_date.strftime("%Y-%m-%d %H:%M:%S")
            # Add some random variation
            value = base_value + random.uniform(-variation, variation)

            records.append({"date": date_str, "value": f"{value:.2f}", "unit": "count"})

            current_date += timedelta(days=1)

        return records

    def test_compare_time_periods_different_averages(self):
        """Test comparing periods with different averages."""
        # Create records where second half has higher values
        records = self.create_sample_metric_records(num_days=60, base_value=100)

        # Manually adjust second half to be higher
        for i in range(30, 60):
            old_value = float(records[i]["value"])
            records[i]["value"] = f"{old_value + 10:.2f}"

        result = compare_time_periods(
            records, "HeartRate", "last_30_days", "previous_30_days"
        )

        assert "period1" in result
        assert "period2" in result
        assert "change" in result

        # Period 1 (recent) should have higher average
        assert result["period1"]["average"] > result["period2"]["average"]
        assert result["change"]["direction"] in ["increase", "decrease"]


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_weight_trend_analysis_workflow(self):
        """Test complete workflow from raw data to insights."""
        # Create realistic weight loss data
        records = []
        start_date = datetime(2025, 7, 22)

        for i in range(90):
            date = start_date + timedelta(days=i)
            # Simulate weight loss with some noise
            daily_loss_lbs = -0.05
            noise = (-1 if i % 2 == 0 else 1) * 0.2  # Small random variation
            weight_lbs = 172.5 + (i * daily_loss_lbs) + noise
            weight_kg = weight_lbs / 2.20462

            records.append(
                {
                    "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "value": f"{weight_kg:.2f}",
                    "unit": "kg",
                }
            )

        # Calculate trends
        result = calculate_weight_trends(records, "last_90_days", "both")

        # Verify result structure
        assert "time_period" in result
        assert "trends" in result

        # Verify all analysis types completed
        assert "linear_regression" in result["trends"]
        assert "moving_average" in result["trends"]
        assert "statistics" in result["trends"]

        # Verify meaningful results
        regression = result["trends"]["linear_regression"]
        assert regression["trend_direction"] == "decreasing"
        assert regression["slope"] < 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
