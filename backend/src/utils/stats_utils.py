"""Statistical utilities for health data analysis (pure functions with NumPy/SciPy)."""

from datetime import datetime
from typing import Any

import numpy as np
from scipy import stats


def calculate_basic_stats(values: list[float]) -> dict[str, float]:
    """
    Calculate basic statistics for a list of values.

    Args:
        values: List of numeric values

    Returns:
        Dictionary with avg, min, max, std_dev, count

    Examples:
        calculate_basic_stats([1, 2, 3, 4, 5]) →
        {
            "average": 3.0,
            "min": 1.0,
            "max": 5.0,
            "std_dev": 1.41,
            "count": 5
        }
    """
    if not values:
        return {"average": 0.0, "min": 0.0, "max": 0.0, "std_dev": 0.0, "count": 0}

    values_array = np.array(values)

    return {
        "average": float(np.mean(values_array)),
        "min": float(np.min(values_array)),
        "max": float(np.max(values_array)),
        "std_dev": float(np.std(values_array)),
        "count": len(values),
    }


def calculate_linear_regression(
    dates: list[datetime], values: list[float]
) -> dict[str, Any]:
    """
    Calculate linear regression for trend analysis.

    Args:
        dates: List of datetime objects
        values: List of corresponding values

    Returns:
        Dictionary with regression statistics

    Examples:
        calculate_linear_regression(dates, weights) →
        {
            "slope": -0.05,  # lbs/day
            "slope_per_week": -0.35,
            "slope_per_month": -1.5,
            "intercept": 172.5,
            "r_squared": 0.78,
            "p_value": 0.001,
            "std_err": 0.01,
            "trend_direction": "decreasing",
            "significance": "significant"
        }
    """
    if not dates or not values or len(dates) != len(values) or len(dates) < 2:
        return {
            "error": "Insufficient data for regression",
            "slope": 0.0,
            "r_squared": 0.0,
        }

    # Convert dates to days from start
    start_date = min(dates)
    days_from_start = [(d - start_date).days for d in dates]

    # Perform linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        days_from_start, values
    )

    # Determine trend direction
    if abs(slope) < 0.01:  # Nearly flat
        trend_direction = "stable"
    elif slope < 0:
        trend_direction = "decreasing"
    else:
        trend_direction = "increasing"

    # Determine statistical significance
    significance = "significant" if p_value < 0.05 else "not_significant"

    return {
        "slope": float(slope),  # per day
        "slope_per_week": float(slope * 7),
        "slope_per_month": float(slope * 30),
        "intercept": float(intercept),
        "r_squared": float(r_value**2),
        "p_value": float(p_value),
        "std_err": float(std_err),
        "trend_direction": trend_direction,
        "significance": significance,
    }


def calculate_moving_average(
    values: list[float], window_size: int = 7
) -> dict[str, Any]:
    """
    Calculate moving average for smoothing trends.

    Args:
        values: List of values
        window_size: Size of moving window (default: 7 days)

    Returns:
        Dictionary with moving average data

    Examples:
        calculate_moving_average([170, 171, 169, 168, 167], window_size=3) →
        {
            "window_size": 3,
            "values": [170.0, 169.33, 168.0],
            "current_avg": 168.0,
            "avg_at_start": 170.0,
            "change": -2.0
        }
    """
    if not values or len(values) < window_size:
        return {
            "error": "Insufficient data for moving average",
            "window_size": window_size,
        }

    values_array = np.array(values)
    moving_avg = np.convolve(
        values_array, np.ones(window_size) / window_size, mode="valid"
    )

    return {
        "window_size": window_size,
        "values": [float(v) for v in moving_avg],
        "current_avg": float(moving_avg[-1]),
        "avg_at_start": float(moving_avg[0]),
        "change": float(moving_avg[-1] - moving_avg[0]),
    }


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.

    Args:
        old_value: Original value
        new_value: New value

    Returns:
        Percentage change

    Examples:
        calculate_percentage_change(100, 110) → 10.0
        calculate_percentage_change(110, 100) → -9.09
    """
    if old_value == 0:
        return 0.0

    return ((new_value - old_value) / old_value) * 100


def calculate_pearson_correlation(
    values_x: list[float], values_y: list[float]
) -> dict[str, float]:
    """
    Calculate Pearson correlation coefficient between two variables.

    Args:
        values_x: First variable values
        values_y: Second variable values

    Returns:
        Dictionary with correlation coefficient and p-value

    Examples:
        calculate_pearson_correlation([1,2,3,4], [2,4,6,8]) →
        {
            "correlation": 1.0,
            "p_value": 0.0,
            "strength": "perfect positive"
        }
    """
    if (
        not values_x
        or not values_y
        or len(values_x) != len(values_y)
        or len(values_x) < 2
    ):
        return {
            "error": "Insufficient data for correlation",
            "correlation": 0.0,
            "p_value": 1.0,
        }

    correlation, p_value = stats.pearsonr(values_x, values_y)

    # Determine correlation strength
    abs_corr = abs(correlation)
    if abs_corr >= 0.9:
        strength = "perfect" if abs_corr == 1.0 else "very strong"
    elif abs_corr >= 0.7:
        strength = "strong"
    elif abs_corr >= 0.5:
        strength = "moderate"
    elif abs_corr >= 0.3:
        strength = "weak"
    else:
        strength = "very weak"

    direction = (
        "positive" if correlation > 0 else "negative" if correlation < 0 else "none"
    )
    strength_description = (
        f"{strength} {direction}" if direction != "none" else "no correlation"
    )

    return {
        "correlation": float(correlation),
        "p_value": float(p_value),
        "strength": strength_description,
        "significant": bool(float(p_value) < 0.05),
    }


def compare_periods(
    period1_values: list[float],
    period2_values: list[float],
    period1_name: str = "Period 1",
    period2_name: str = "Period 2",
) -> dict[str, Any]:
    """
    Compare statistics between two time periods.

    Args:
        period1_values: Values from first period
        period2_values: Values from second period
        period1_name: Name of first period
        period2_name: Name of second period

    Returns:
        Dictionary with comparison statistics

    Examples:
        compare_periods([100, 102, 101], [95, 97, 96], "This Month", "Last Month") →
        {
            "period1": {"average": 101.0, "count": 3, "name": "This Month"},
            "period2": {"average": 96.0, "count": 3, "name": "Last Month"},
            "change": {
                "absolute": -5.0,
                "percentage": -4.95,
                "direction": "decrease"
            }
        }
    """
    if not period1_values or not period2_values:
        return {"error": "Insufficient data for comparison"}

    stats1 = calculate_basic_stats(period1_values)
    stats2 = calculate_basic_stats(period2_values)

    # Calculate changes
    avg_change = stats1["average"] - stats2["average"]
    pct_change = calculate_percentage_change(stats2["average"], stats1["average"])

    # Determine direction
    if abs(avg_change) < 0.01:
        direction = "no change"
    elif avg_change > 0:
        direction = "increase"
    else:
        direction = "decrease"

    # Perform t-test for statistical significance
    t_statistic, t_p_value = stats.ttest_ind(period1_values, period2_values)

    return {
        "period1": {**stats1, "name": period1_name},
        "period2": {**stats2, "name": period2_name},
        "change": {
            "absolute": float(avg_change),
            "percentage": float(pct_change),
            "direction": direction,
        },
        "statistical_test": {
            "t_statistic": float(t_statistic),
            "p_value": float(t_p_value),
            "significant": bool(float(t_p_value) < 0.05),
        },
    }
