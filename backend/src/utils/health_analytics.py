"""Mathematical analysis for health data using NumPy/SciPy (pure functions)."""

from typing import Any

from .conversion_utils import kg_to_lbs
from .stats_utils import (
    calculate_basic_stats,
    calculate_linear_regression,
    calculate_moving_average,
    calculate_pearson_correlation,
)
from .stats_utils import compare_periods as stats_compare_periods
from .time_utils import parse_health_record_date, parse_time_period


def calculate_weight_trends(
    weight_records: list[dict[str, Any]],
    time_period: str = "last_90_days",
    trend_type: str = "both",
) -> dict[str, Any]:
    """
    Calculate weight trends with linear regression and moving averages.

    PURE FUNCTION - Data passed in, no Redis access.

    Args:
        weight_records: List of weight records [{"date": "YYYY-MM-DD HH:MM:SS", "value": "72.5", "unit": "kg"}, ...]
        time_period: Time period to analyze ("last_90_days", "last_30_days", "this_month", "last_month")
        trend_type: Type of trend analysis ("linear_regression", "moving_average", "both")

    Returns:
        Dictionary with trend analysis results

    Examples:
        calculate_weight_trends(records, "last_90_days", "both") →
        {
            "time_period": "last_90_days",
            "date_range": "2025-07-22 to 2025-10-20",
            "trends": {
                "linear_regression": {
                    "slope": -0.05,  # lbs/day
                    "slope_per_week": -0.35,
                    "slope_per_month": -1.5,
                    "r_squared": 0.78,
                    "p_value": 0.001,
                    "trend_direction": "decreasing",
                    "significance": "significant"
                },
                "moving_average": {
                    "window_days": 7,
                    "current_avg": 168.2,
                    "avg_at_start": 172.1,
                    "change": -3.9
                },
                "statistics": {
                    "current_weight": 167.8,
                    "starting_weight": 172.5,
                    "total_change": -4.7,
                    "average_weight": 170.2,
                    "std_dev": 2.1,
                    "min_weight": 166.5,
                    "max_weight": 174.0,
                    "measurements_count": 77
                }
            }
        }
    """
    if not weight_records:
        return {"error": "No weight records provided", "trends": {}}

    try:
        # Parse time period
        filter_start, filter_end, time_range_desc = parse_time_period(time_period)

        # Filter records by time period
        filtered_records = []
        for record in weight_records:
            record_date = parse_health_record_date(record["date"])
            if filter_start <= record_date <= filter_end:
                filtered_records.append(record)

        if not filtered_records:
            return {
                "error": "No weight records found in time period",
                "time_period": time_period,
                "date_range": f"{filter_start.date()} to {filter_end.date()}",
                "trends": {},
            }

        # Sort by date
        filtered_records.sort(key=lambda x: x["date"])

        # Extract dates and values
        dates = [parse_health_record_date(r["date"]) for r in filtered_records]

        # Convert values to lbs
        values_lbs = []
        for record in filtered_records:
            value_str = record["value"]
            unit = record.get("unit", "kg")

            # Parse numeric value
            try:
                value_float = float(value_str)
                # Convert to lbs if in kg
                if "kg" in unit.lower():
                    value_lbs = kg_to_lbs(value_float)
                else:
                    value_lbs = value_float
                values_lbs.append(value_lbs)
            except (ValueError, TypeError):
                continue

        if not values_lbs or len(values_lbs) < 2:
            return {
                "error": "Insufficient data points for trend analysis",
                "time_period": time_period,
                "trends": {},
            }

        results = {}

        # Linear regression
        if trend_type in ["linear_regression", "both"]:
            regression_results = calculate_linear_regression(dates, values_lbs)
            results["linear_regression"] = regression_results

        # Moving average
        if trend_type in ["moving_average", "both"]:
            moving_avg_results = calculate_moving_average(values_lbs, window_size=7)
            results["moving_average"] = moving_avg_results

        # Overall statistics
        basic_stats = calculate_basic_stats(values_lbs)
        results["statistics"] = {
            "current_weight": float(values_lbs[-1]),
            "starting_weight": float(values_lbs[0]),
            "total_change": float(values_lbs[-1] - values_lbs[0]),
            "average_weight": basic_stats["average"],
            "std_dev": basic_stats["std_dev"],
            "min_weight": basic_stats["min"],
            "max_weight": basic_stats["max"],
            "measurements_count": basic_stats["count"],
        }

        return {
            "time_period": time_period,
            "date_range": f"{dates[0].date()} to {dates[-1].date()}",
            "trends": results,
        }

    except Exception as e:
        return {
            "error": f"Weight trend calculation failed: {str(e)}",
            "time_period": time_period,
            "trends": {},
        }


def compare_time_periods(
    all_records: list[dict[str, Any]], metric_type: str, period1: str, period2: str
) -> dict[str, Any]:
    """
    Compare metrics between two time periods with statistical significance.

    PURE FUNCTION - Data passed in, no Redis access.

    Args:
        all_records: List of all metric records [{"date": "...", "value": "...", "unit": "..."}, ...]
        metric_type: Type of metric ("BodyMass", "HeartRate", "StepCount", etc.)
        period1: First time period ("this_month", "last_30_days", etc.)
        period2: Second time period ("last_month", "previous_30_days", etc.)

    Returns:
        Dictionary with comparison results

    Examples:
        compare_time_periods(records, "BodyMass", "this_month", "last_month") →
        {
            "metric_type": "BodyMass",
            "period1": {
                "name": "this_month",
                "average": 168.5,
                "min": 167.0,
                "max": 170.0,
                "count": 25
            },
            "period2": {
                "name": "last_month",
                "average": 170.2,
                "min": 168.5,
                "max": 172.5,
                "count": 30
            },
            "change": {
                "absolute": -1.7,
                "percentage": -1.0,
                "direction": "decrease"
            },
            "statistical_test": {
                "t_statistic": -2.45,
                "p_value": 0.018,
                "significant": true
            }
        }
    """
    if not all_records:
        return {"error": "No records provided"}

    try:
        # Parse both time periods
        start1, end1, desc1 = parse_time_period(period1)
        start2, end2, desc2 = parse_time_period(period2)

        # Filter records for each period
        period1_records = []
        period2_records = []

        for record in all_records:
            # Parse date using canonical function (ensures UTC timezone)
            record_date = parse_health_record_date(record["date"])

            # Parse value
            try:
                value_float = float(record["value"])

                # Convert weight to lbs if needed
                if metric_type == "BodyMass":
                    unit = record.get("unit", "kg")
                    if "kg" in unit.lower():
                        value_float = kg_to_lbs(value_float)

                # Assign to appropriate period
                if start1 <= record_date <= end1:
                    period1_records.append(value_float)
                if start2 <= record_date <= end2:
                    period2_records.append(value_float)
            except (ValueError, TypeError):
                continue

        if not period1_records or not period2_records:
            return {
                "error": "Insufficient data in one or both periods",
                "period1": desc1,
                "period2": desc2,
            }

        # Use stats utility to compare
        comparison = stats_compare_periods(
            period1_records, period2_records, desc1, desc2
        )

        # Add metric type to result
        comparison["metric_type"] = metric_type

        return comparison

    except Exception as e:
        return {
            "error": f"Period comparison failed: {str(e)}",
            "metric_type": metric_type,
        }


def correlate_metrics(
    records_x: list[dict[str, Any]],
    records_y: list[dict[str, Any]],
    metric_x_name: str,
    metric_y_name: str,
    time_period: str = "recent",
) -> dict[str, Any]:
    """
    Calculate correlation between two metrics.

    PURE FUNCTION - Data passed in, no Redis access.

    Args:
        records_x: First metric records
        records_y: Second metric records
        metric_x_name: Name of first metric (e.g., "BodyMass")
        metric_y_name: Name of second metric (e.g., "HeartRate")
        time_period: Time period to analyze

    Returns:
        Dictionary with correlation analysis

    Examples:
        correlate_metrics(weight_records, heart_rate_records, "Weight", "Heart Rate") →
        {
            "metric_x": "Weight",
            "metric_y": "Heart Rate",
            "correlation": -0.65,
            "p_value": 0.002,
            "strength": "moderate negative",
            "significant": true,
            "interpretation": "As weight decreases, heart rate tends to increase"
        }
    """
    if not records_x or not records_y:
        return {"error": "Insufficient records for correlation"}

    try:
        # Parse time period
        filter_start, filter_end, time_range_desc = parse_time_period(time_period)

        # Create date-indexed dictionaries for matching
        x_by_date = {}
        for record in records_x:
            record_date = parse_health_record_date(record["date"])
            if filter_start <= record_date <= filter_end:
                try:
                    value = float(record["value"])
                    date_key = record_date.date()
                    if date_key not in x_by_date:
                        x_by_date[date_key] = []
                    x_by_date[date_key].append(value)
                except (ValueError, TypeError):
                    continue

        y_by_date = {}
        for record in records_y:
            record_date = parse_health_record_date(record["date"])
            if filter_start <= record_date <= filter_end:
                try:
                    value = float(record["value"])
                    date_key = record_date.date()
                    if date_key not in y_by_date:
                        y_by_date[date_key] = []
                    y_by_date[date_key].append(value)
                except (ValueError, TypeError):
                    continue

        # Find common dates and average values
        x_values = []
        y_values = []

        for date_key in x_by_date:
            if date_key in y_by_date:
                x_avg = sum(x_by_date[date_key]) / len(x_by_date[date_key])
                y_avg = sum(y_by_date[date_key]) / len(y_by_date[date_key])
                x_values.append(x_avg)
                y_values.append(y_avg)

        if len(x_values) < 3:
            return {
                "error": "Insufficient overlapping data points for correlation",
                "metric_x": metric_x_name,
                "metric_y": metric_y_name,
            }

        # Calculate correlation
        correlation_result = calculate_pearson_correlation(x_values, y_values)

        # Add interpretation
        correlation_result["correlation"]
        if correlation_result.get("significant"):
            if "positive" in correlation_result["strength"]:
                interpretation = (
                    f"As {metric_x_name} increases, {metric_y_name} tends to increase"
                )
            elif "negative" in correlation_result["strength"]:
                interpretation = (
                    f"As {metric_x_name} decreases, {metric_y_name} tends to increase"
                )
            else:
                interpretation = (
                    f"No clear relationship between {metric_x_name} and {metric_y_name}"
                )
        else:
            interpretation = f"No statistically significant relationship between {metric_x_name} and {metric_y_name}"

        return {
            "metric_x": metric_x_name,
            "metric_y": metric_y_name,
            "time_period": time_range_desc,
            "correlation": correlation_result["correlation"],
            "p_value": correlation_result["p_value"],
            "strength": correlation_result["strength"],
            "significant": correlation_result["significant"],
            "data_points": len(x_values),
            "interpretation": interpretation,
        }

    except Exception as e:
        return {
            "error": f"Correlation calculation failed: {str(e)}",
            "metric_x": metric_x_name,
            "metric_y": metric_y_name,
        }
