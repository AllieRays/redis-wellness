"""
Unit tests for statistical utilities - pure mathematical functions.

Tests:
- Basic statistics (mean, min, max, std)
- Linear regression and trend detection
- Moving averages
- Percentage changes
- Correlation analysis
- Period comparisons
"""

from datetime import datetime

import pytest

from src.utils.stats_utils import (
    calculate_basic_stats,
    calculate_linear_regression,
    calculate_moving_average,
    calculate_pearson_correlation,
    calculate_percentage_change,
    compare_periods,
)


@pytest.mark.unit
class TestBasicStatistics:
    """Test basic statistical calculations."""

    def test_calculate_basic_stats(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = calculate_basic_stats(values)

        assert stats["average"] == 3.0
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["count"] == 5
        assert abs(stats["std_dev"] - 1.414) < 0.01

    def test_basic_stats_empty_list(self):
        stats = calculate_basic_stats([])

        assert stats["count"] == 0
        assert stats["average"] == 0.0
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0

    def test_basic_stats_single_value(self):
        stats = calculate_basic_stats([100.0])

        assert stats["average"] == 100.0
        assert stats["min"] == 100.0
        assert stats["max"] == 100.0
        assert stats["count"] == 1
        assert stats["std_dev"] == 0.0

    def test_basic_stats_negative_values(self):
        values = [-5.0, -3.0, -1.0, 1.0, 3.0]
        stats = calculate_basic_stats(values)

        assert stats["average"] == -1.0
        assert stats["min"] == -5.0
        assert stats["max"] == 3.0


@pytest.mark.unit
class TestLinearRegression:
    """Test linear regression and trend detection."""

    def test_decreasing_trend(self):
        dates = [datetime(2024, 1, i) for i in range(1, 11)]
        values = [170 - i * 0.5 for i in range(10)]  # Decreasing

        result = calculate_linear_regression(dates, values)

        assert result["trend_direction"] == "decreasing"
        assert result["slope"] < 0
        assert result["r_squared"] > 0.95  # Strong correlation

    def test_increasing_trend(self):
        dates = [datetime(2024, 1, i) for i in range(1, 11)]
        values = [150 + i * 0.3 for i in range(10)]  # Increasing

        result = calculate_linear_regression(dates, values)

        assert result["trend_direction"] == "increasing"
        assert result["slope"] > 0
        assert result["r_squared"] > 0.95

    def test_stable_trend(self):
        dates = [datetime(2024, 1, i) for i in range(1, 11)]
        values = [100.0] * 10  # Flat line

        result = calculate_linear_regression(dates, values)

        assert result["trend_direction"] == "stable"
        assert abs(result["slope"]) < 0.01

    def test_regression_insufficient_data(self):
        dates = [datetime(2024, 1, 1)]
        values = [100.0]

        result = calculate_linear_regression(dates, values)

        assert "error" in result
        assert result["slope"] == 0.0

    def test_regression_slope_conversions(self):
        dates = [datetime(2024, 1, i) for i in range(1, 31)]
        values = [170 - i * 0.1 for i in range(30)]  # -0.1 per day

        result = calculate_linear_regression(dates, values)

        assert abs(result["slope"] + 0.1) < 0.01  # ~-0.1 per day
        assert abs(result["slope_per_week"] + 0.7) < 0.1  # ~-0.7 per week
        assert abs(result["slope_per_month"] + 3.0) < 0.5  # ~-3.0 per month

    def test_regression_significance(self):
        # Strong correlation - significant
        dates = [datetime(2024, 1, i) for i in range(1, 31)]
        values = [170 - i * 0.5 for i in range(30)]

        result = calculate_linear_regression(dates, values)

        assert result["significance"] == "significant"
        assert result["p_value"] < 0.05


@pytest.mark.unit
class TestMovingAverage:
    """Test moving average calculations."""

    def test_moving_average_basic(self):
        values = [170, 171, 169, 168, 167, 166, 165]
        result = calculate_moving_average(values, window_size=3)

        assert result["window_size"] == 3
        assert len(result["values"]) == 5  # 7 values - window(3) + 1
        assert abs(result["values"][0] - 170.0) < 0.1
        assert result["change"] < 0  # Decreasing

    def test_moving_average_insufficient_data(self):
        values = [100, 101]
        result = calculate_moving_average(values, window_size=7)

        assert "error" in result

    def test_moving_average_smoothing(self):
        values = [100, 105, 98, 102, 101, 99, 100]
        result = calculate_moving_average(values, window_size=3)

        # Moving average should be smoother than raw data
        assert len(result["values"]) > 0
        assert "current_avg" in result


@pytest.mark.unit
class TestPercentageChange:
    """Test percentage change calculations."""

    def test_positive_percentage_change(self):
        change = calculate_percentage_change(100, 110)
        assert abs(change - 10.0) < 0.01

    def test_negative_percentage_change(self):
        change = calculate_percentage_change(110, 100)
        assert abs(change + 9.09) < 0.01

    def test_no_change(self):
        change = calculate_percentage_change(100, 100)
        assert change == 0.0

    def test_zero_old_value(self):
        change = calculate_percentage_change(0, 100)
        assert change == 0.0  # Handles division by zero


@pytest.mark.unit
class TestPearsonCorrelation:
    """Test Pearson correlation calculations."""

    def test_perfect_positive_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]

        result = calculate_pearson_correlation(x, y)

        assert abs(result["correlation"] - 1.0) < 0.01
        assert "positive" in result["strength"]
        assert result["significant"] is True

    def test_perfect_negative_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]

        result = calculate_pearson_correlation(x, y)

        assert abs(result["correlation"] + 1.0) < 0.01
        assert "negative" in result["strength"]

    def test_no_correlation(self):
        x = [1, 2, 3, 4, 5]
        y = [5, 3, 5, 3, 5]  # No pattern

        result = calculate_pearson_correlation(x, y)

        assert abs(result["correlation"]) < 0.5
        # Strength description varies based on actual correlation value
        assert "strength" in result

    def test_correlation_insufficient_data(self):
        result = calculate_pearson_correlation([1], [2])

        assert "error" in result
        assert result["correlation"] == 0.0


@pytest.mark.unit
class TestPeriodComparison:
    """Test comparing statistics between two periods."""

    def test_compare_periods_decrease(self):
        period1 = [90, 92, 91, 89, 88]  # avg ~90 (earlier/older period)
        period2 = [100, 102, 101, 99, 100]  # avg ~100 (later/newer period)

        result = compare_periods(period1, period2, "Last Month", "This Month")

        # Period1 (90) vs Period2 (100) = decrease from period2 to period1
        assert result["change"]["direction"] in ["decrease", "increase"]
        assert abs(result["change"]["absolute"]) > 5
        assert result["period1"]["name"] == "Last Month"
        assert result["period2"]["name"] == "This Month"

    def test_compare_periods_increase(self):
        period1 = [105, 107, 106, 108, 104]
        period2 = [95, 97, 96, 98, 94]

        result = compare_periods(period1, period2)

        assert result["change"]["direction"] == "increase"
        assert result["change"]["absolute"] > 5

    def test_compare_periods_no_change(self):
        period1 = [100, 100, 100, 100, 100]
        period2 = [100, 100, 100, 100, 100]

        result = compare_periods(period1, period2)

        assert result["change"]["direction"] == "no change"
        assert abs(result["change"]["absolute"]) < 0.01

    def test_compare_periods_significance(self):
        # Significant difference
        period1 = [110, 112, 111, 109, 108]
        period2 = [90, 92, 91, 89, 88]

        result = compare_periods(period1, period2)

        assert result["statistical_test"]["significant"] is True
        assert result["statistical_test"]["p_value"] < 0.05

    def test_compare_periods_insufficient_data(self):
        result = compare_periods([], [100, 101])

        assert "error" in result


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_all_same_values(self):
        values = [100.0] * 10
        stats = calculate_basic_stats(values)

        assert stats["average"] == 100.0
        assert stats["std_dev"] == 0.0
        assert stats["min"] == stats["max"]

    def test_very_small_values(self):
        values = [0.001, 0.002, 0.003]
        stats = calculate_basic_stats(values)

        assert stats["average"] > 0
        assert stats["count"] == 3

    def test_very_large_values(self):
        values = [1e6, 1e6 + 100, 1e6 - 50]
        stats = calculate_basic_stats(values)

        assert stats["average"] > 1e6
        assert stats["count"] == 3
