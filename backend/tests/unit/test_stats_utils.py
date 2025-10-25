"""
Unit tests for stats_utils - Statistical calculations for health data.

REAL TESTS - NO MOCKS:
- Tests pure mathematical functions with numpy/scipy
- Tests real statistical calculations
- No LLM, no external dependencies
"""

from datetime import UTC, datetime

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
class TestBasicStats:
    """Test basic statistical calculations."""

    def test_calculate_basic_stats_normal(self):
        """Test basic stats with normal data."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]

        result = calculate_basic_stats(values)

        assert result["average"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["std_dev"] == pytest.approx(1.41, abs=0.01)
        assert result["count"] == 5

    def test_calculate_basic_stats_empty(self):
        """Test basic stats with empty list."""
        values = []

        result = calculate_basic_stats(values)

        assert result["average"] == 0.0
        assert result["min"] == 0.0
        assert result["max"] == 0.0
        assert result["count"] == 0

    def test_calculate_basic_stats_single_value(self):
        """Test basic stats with single value."""
        values = [42.0]

        result = calculate_basic_stats(values)

        assert result["average"] == 42.0
        assert result["min"] == 42.0
        assert result["max"] == 42.0
        assert result["std_dev"] == 0.0
        assert result["count"] == 1

    def test_calculate_basic_stats_real_health_data(self):
        """Test with real-world health data (weights in kg)."""
        weights = [70.2, 70.0, 69.8, 69.5, 69.3]

        result = calculate_basic_stats(weights)

        assert result["average"] == pytest.approx(69.76, abs=0.01)
        assert result["min"] == 69.3
        assert result["max"] == 70.2
        assert result["count"] == 5


@pytest.mark.unit
class TestLinearRegression:
    """Test linear regression for trend analysis."""

    def test_linear_regression_decreasing_trend(self):
        """Test regression with decreasing trend."""
        dates = [
            datetime(2024, 10, 1, tzinfo=UTC),
            datetime(2024, 10, 8, tzinfo=UTC),
            datetime(2024, 10, 15, tzinfo=UTC),
            datetime(2024, 10, 22, tzinfo=UTC),
        ]
        values = [70.0, 69.5, 69.0, 68.5]  # Losing 0.5 kg/week

        result = calculate_linear_regression(dates, values)

        assert result["trend_direction"] == "decreasing"
        assert result["slope"] < 0
        assert result["slope_per_week"] == pytest.approx(-0.5, abs=0.1)
        assert result["r_squared"] > 0.9  # Strong correlation

    def test_linear_regression_increasing_trend(self):
        """Test regression with increasing trend."""
        dates = [
            datetime(2024, 10, 1, tzinfo=UTC),
            datetime(2024, 10, 8, tzinfo=UTC),
            datetime(2024, 10, 15, tzinfo=UTC),
        ]
        values = [100.0, 105.0, 110.0]

        result = calculate_linear_regression(dates, values)

        assert result["trend_direction"] == "increasing"
        assert result["slope"] > 0
        assert result["r_squared"] > 0.9

    def test_linear_regression_stable(self):
        """Test regression with stable values."""
        dates = [
            datetime(2024, 10, 1, tzinfo=UTC),
            datetime(2024, 10, 2, tzinfo=UTC),
            datetime(2024, 10, 3, tzinfo=UTC),
            datetime(2024, 10, 4, tzinfo=UTC),
        ]
        values = [70.0, 70.0, 70.0, 70.0]  # Completely flat

        result = calculate_linear_regression(dates, values)

        assert result["trend_direction"] == "stable"
        assert abs(result["slope"]) < 0.01

    def test_linear_regression_insufficient_data(self):
        """Test regression with insufficient data."""
        dates = [datetime(2024, 10, 1, tzinfo=UTC)]
        values = [70.0]

        result = calculate_linear_regression(dates, values)

        assert "error" in result
        assert result["slope"] == 0.0


@pytest.mark.unit
class TestMovingAverage:
    """Test moving average calculations."""

    def test_moving_average_window_3(self):
        """Test 3-day moving average."""
        values = [170.0, 171.0, 169.0, 168.0, 167.0]

        result = calculate_moving_average(values, window_size=3)

        assert result["window_size"] == 3
        assert len(result["values"]) == 3  # 5 - 3 + 1
        assert result["current_avg"] == pytest.approx(168.0, abs=0.1)

    def test_moving_average_window_7(self):
        """Test 7-day moving average."""
        values = [70.0] * 10  # Stable weight

        result = calculate_moving_average(values, window_size=7)

        assert result["window_size"] == 7
        assert all(v == pytest.approx(70.0, abs=0.1) for v in result["values"])
        assert result["change"] == pytest.approx(0.0, abs=0.1)

    def test_moving_average_insufficient_data(self):
        """Test moving average with too few values."""
        values = [70.0, 71.0]

        result = calculate_moving_average(values, window_size=7)

        assert "error" in result


@pytest.mark.unit
class TestPercentageChange:
    """Test percentage change calculations."""

    def test_percentage_increase(self):
        """Test percentage increase."""
        change = calculate_percentage_change(100.0, 110.0)

        assert change == pytest.approx(10.0, abs=0.01)

    def test_percentage_decrease(self):
        """Test percentage decrease."""
        change = calculate_percentage_change(110.0, 100.0)

        assert change == pytest.approx(-9.09, abs=0.01)

    def test_percentage_no_change(self):
        """Test zero percentage change."""
        change = calculate_percentage_change(100.0, 100.0)

        assert change == 0.0

    def test_percentage_from_zero(self):
        """Test percentage change from zero (edge case)."""
        change = calculate_percentage_change(0.0, 100.0)

        assert change == 0.0  # Returns 0 when old_value is 0


@pytest.mark.unit
class TestPearsonCorrelation:
    """Test correlation calculations."""

    def test_perfect_positive_correlation(self):
        """Test perfect positive correlation."""
        x = [1.0, 2.0, 3.0, 4.0]
        y = [2.0, 4.0, 6.0, 8.0]

        result = calculate_pearson_correlation(x, y)

        assert result["correlation"] == pytest.approx(1.0, abs=0.001)
        assert "positive" in result["strength"]
        assert result["significant"] is True

    def test_perfect_negative_correlation(self):
        """Test perfect negative correlation."""
        x = [1.0, 2.0, 3.0, 4.0]
        y = [8.0, 6.0, 4.0, 2.0]

        result = calculate_pearson_correlation(x, y)

        assert result["correlation"] == pytest.approx(-1.0, abs=0.001)
        assert "negative" in result["strength"]

    def test_no_correlation(self):
        """Test no correlation."""
        x = [1.0, 2.0, 3.0, 4.0]
        y = [5.0, 5.0, 5.0, 5.0]  # Constant

        result = calculate_pearson_correlation(x, y)

        # Note: Constant y will have undefined correlation (NaN)
        # Implementation may handle this differently
        assert "correlation" in result

    def test_insufficient_data_correlation(self):
        """Test correlation with insufficient data."""
        x = [1.0]
        y = [2.0]

        result = calculate_pearson_correlation(x, y)

        assert "error" in result


@pytest.mark.unit
class TestComparePeriods:
    """Test period comparison."""

    def test_compare_periods_decrease(self):
        """Test comparison showing decrease."""
        period1 = [95.0, 96.0, 97.0]  # Current period (lower)
        period2 = [100.0, 101.0, 102.0]  # Previous period (higher)

        result = compare_periods(period1, period2, "This Month", "Last Month")

        assert result["change"]["direction"] == "decrease"
        assert result["change"]["absolute"] < 0
        assert result["change"]["percentage"] < 0
        assert result["period1"]["average"] == pytest.approx(96.0, abs=0.1)
        assert result["period2"]["average"] == pytest.approx(101.0, abs=0.1)

    def test_compare_periods_increase(self):
        """Test comparison showing increase."""
        period1 = [105.0, 106.0, 107.0]
        period2 = [100.0, 101.0, 102.0]

        result = compare_periods(period1, period2)

        assert result["change"]["direction"] == "increase"
        assert result["change"]["absolute"] > 0
        assert result["change"]["percentage"] > 0

    def test_compare_periods_statistical_test(self):
        """Test that statistical significance is calculated."""
        period1 = [100.0, 101.0, 102.0, 103.0, 104.0]
        period2 = [90.0, 91.0, 92.0, 93.0, 94.0]

        result = compare_periods(period1, period2)

        assert "statistical_test" in result
        assert "t_statistic" in result["statistical_test"]
        assert "p_value" in result["statistical_test"]
        assert "significant" in result["statistical_test"]

    def test_compare_periods_insufficient_data(self):
        """Test comparison with empty periods."""
        period1 = []
        period2 = [100.0]

        result = compare_periods(period1, period2)

        assert "error" in result
