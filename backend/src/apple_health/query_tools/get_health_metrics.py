"""
Health Metrics Tool - Get health data with optional statistics.

Combines raw data retrieval and statistical aggregation into a single tool.
Handles all health metric queries (weight, BMI, heart rate, steps, etc.)
"""

import json
import logging
from datetime import datetime
from statistics import mean
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.conversion_utils import kg_to_lbs
from ...utils.exceptions import HealthDataNotFoundError, ToolExecutionError
from ...utils.metric_aggregators import aggregate_metric_values, get_aggregation_summary
from ...utils.metric_classifier import (
    get_aggregation_strategy,
    get_expected_unit_format,
)
from ...utils.time_utils import parse_health_record_date, parse_time_period
from ...utils.user_config import get_user_health_data_key

logger = logging.getLogger(__name__)


def create_get_health_metrics_tool(user_id: str):
    """
    Create get_health_metrics tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_health_metrics(
        metric_types: list[str],
        time_period: str = "recent",
        aggregations: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get health metrics with optional statistics (raw data OR aggregated).

        USE WHEN user asks:
        - "What was my weight in September?" (raw data)
        - "What was my average heart rate last week?" (statistics)
        - "Show me my BMI trend" (raw data over time)
        - "Total steps this month" (statistics)
        - "Minimum/maximum values" (statistics)

        DO NOT USE for:
        - Trend analysis → use get_trends instead
        - Period comparisons → use get_trends instead
        - Workout data → use get_workouts instead

        Args:
            metric_types: List of metric types
                Examples: ["BodyMass"], ["RestingHeartRate"], ["StepCount"], ["BodyMassIndex"]
                Valid: "BodyMass", "BodyMassIndex", "HeartRate", "RestingHeartRate", "StepCount", "ActiveEnergyBurned"
                IMPORTANT: Use "RestingHeartRate" for resting HR (measured at rest), "HeartRate" for all HR measurements
            time_period: Natural language time period (default: "recent")
                Examples: "October 15th", "September", "last 2 weeks", "this month", "recent"
            aggregations: Optional statistics to compute (default: None = raw data)
                Options: ["average"], ["min", "max"], ["sum"], ["count"], or combinations
                If None: returns raw data points
                If provided: returns computed statistics

        Returns:
            Dict with:
            - results: List of metric data (raw records OR statistics)
            - total_metrics: Number of metrics returned
            - mode: "raw_data" or "statistics"

        Examples:
            Query: "What was my weight in September?"
            Call: get_health_metrics(metric_types=["BodyMass"], time_period="September")
            Returns: List of weight values with dates

            Query: "What was my average heart rate last week?"
            Call: get_health_metrics(metric_types=["HeartRate"], time_period="last week", aggregations=["average"])
            Returns: {"average": "87.5 bpm", "sample_size": 7}

            Query: "What was my average resting heart rate last week?"
            Call: get_health_metrics(metric_types=["RestingHeartRate"], time_period="last week", aggregations=["average"])
            Returns: {"average": "73.4 bpm", "sample_size": 7}

            Query: "Total steps this month"
            Call: get_health_metrics(metric_types=["StepCount"], time_period="this month", aggregations=["sum"])
            Returns: {"sum": "150000 total steps (30 days)"}
        """
        logger.info(
            f"🔧 get_health_metrics called: metrics={metric_types}, time_period='{time_period}', "
            f"aggregations={aggregations}, user_id={user_id}"
        )

        try:
            # Parse time period into date range
            filter_start, filter_end, time_range_desc = parse_time_period(time_period)
            logger.debug(
                f"Parsed '{time_period}' → {filter_start.strftime('%Y-%m-%d')} to "
                f"{filter_end.strftime('%Y-%m-%d')} ({time_range_desc})"
            )

            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {
                        "mode": "error",
                        "error": "No health data found for user",
                        "results": [],
                    }

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})
                metrics_summary = health_data.get("metrics_summary", {})

                # BRANCH: Statistics mode vs Raw data mode
                if aggregations:
                    return _calculate_statistics(
                        metrics_records,
                        metric_types,
                        filter_start,
                        filter_end,
                        time_range_desc,
                        aggregations,
                    )
                else:
                    return _get_raw_data(
                        metrics_records,
                        metrics_summary,
                        metric_types,
                        filter_start,
                        filter_end,
                        time_range_desc,
                    )

        except HealthDataNotFoundError:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid health data format: {e}", exc_info=True)
            raise ToolExecutionError(
                "get_health_metrics", f"Invalid health data format: {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Error in get_health_metrics: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise ToolExecutionError("get_health_metrics", str(e)) from e

    return get_health_metrics


def _get_raw_data(
    metrics_records: dict,
    metrics_summary: dict,
    metric_types: list[str],
    filter_start: datetime,
    filter_end: datetime,
    time_range_desc: str,
) -> dict[str, Any]:
    """Get raw health metric data points without aggregation."""
    results = []

    for metric_type in metric_types:
        # Get unit format for this metric type
        unit = get_expected_unit_format(metric_type) or ""

        # Try to get historical records first
        if metric_type in metrics_records:
            all_records = metrics_records[metric_type]
            logger.debug(f"Found {len(all_records)} total {metric_type} records")

            # Filter by date range and normalize values
            data = []
            for record in all_records:
                record_date = parse_health_record_date(record["date"])

                if filter_start <= record_date <= filter_end:
                    raw_value = record["value"]
                    raw_unit = record.get("unit", "")

                    # Normalize weight to lbs
                    if metric_type == "BodyMass":
                        numeric_value = (
                            kg_to_lbs(raw_value)
                            if "kg" in raw_unit.lower()
                            else float(raw_value)
                        )
                        unit = "lbs"
                    else:
                        numeric_value = float(raw_value)

                    data.append(
                        {
                            "date": record_date.date().isoformat(),
                            "value": numeric_value,
                        }
                    )

            logger.info(
                f"Filtered to {len(data)} {metric_type} records in {time_range_desc}"
            )

            results.append(
                {
                    "metric": metric_type,
                    "unit": unit,
                    "count": len(data),
                    "data": data,
                    "data_source": "historical",
                }
            )

        # Fall back to summary if no detailed records
        elif metric_type in metrics_summary:
            metric_info = metrics_summary[metric_type]
            latest_value = metric_info.get("latest_value")
            raw_unit = metric_info.get("unit", "")

            # Normalize value
            if latest_value is not None:
                if metric_type == "BodyMass" and "kg" in raw_unit.lower():
                    numeric_value = kg_to_lbs(latest_value)
                    unit = "lbs"
                else:
                    numeric_value = float(latest_value)
                    unit = raw_unit or unit

                # Create single data point from summary
                data = [
                    {
                        "date": metric_info.get("latest_date", "N/A"),
                        "value": numeric_value,
                    }
                ]
            else:
                data = []

            results.append(
                {
                    "metric": metric_type,
                    "unit": unit,
                    "count": len(data),
                    "data": data,
                    "data_source": "summary_fallback",
                }
            )
        else:
            # No data found for this metric
            results.append(
                {
                    "metric": metric_type,
                    "unit": unit,
                    "count": 0,
                    "data": [],
                    "data_source": "none",
                }
            )

    logger.info(f"Returning {len(results)} metric types (raw data)")
    return {
        "mode": "raw_data",
        "time_range": time_range_desc,
        "total_metrics": len(results),
        "results": results,
    }


def _format_stat_value(
    metric_type: str, stat_type: str, value: float, unit: str, sample_size: int = 0
) -> dict[str, Any]:
    """Format statistic value with metric-specific context.

    Returns dict with 'value' (numeric) and 'formatted' (human-readable string).
    """
    # Metric-specific formatters
    formatters = {
        "StepCount": {
            "average": lambda v: f"{v:.0f} steps/day",
            "min": lambda v: f"{v:.0f} steps (lowest day)",
            "max": lambda v: f"{v:.0f} steps (most active day)",
            "sum": lambda v: f"{v:.0f} total steps ({sample_size} days)",
        },
        "HeartRate": {
            "average": lambda v: f"{v:.1f} bpm (daily avg)",
            "min": lambda v: f"{v:.1f} bpm (lowest daily avg)",
            "max": lambda v: f"{v:.1f} bpm (highest daily avg)",
        },
        "BodyMass": {
            "average": lambda v: f"{v:.1f} lbs",
            "min": lambda v: f"{v:.1f} lbs",
            "max": lambda v: f"{v:.1f} lbs",
        },
        "DistanceWalkingRunning": {
            "sum": lambda v: f"{v:.1f} total miles ({sample_size} days)",
        },
    }

    # Get formatter or use default
    formatter = formatters.get(metric_type, {}).get(stat_type)
    if formatter:
        formatted = formatter(value)
    else:
        # Default formatting
        if stat_type == "sum":
            formatted = (
                f"{value:.1f} {unit} ({sample_size} days)" if unit else f"{value:.1f}"
            )
        else:
            formatted = f"{value:.1f} {unit}" if unit else f"{value:.1f}"

    return {"value": round(value, 2), "formatted": formatted}


def _calculate_statistics(
    metrics_records: dict,
    metric_types: list[str],
    filter_start: datetime,
    filter_end: datetime,
    time_range_desc: str,
    aggregations: list[str],
) -> dict[str, Any]:
    """Calculate statistics on health metric data with metric-specific aggregation strategies."""
    results = []

    for metric_type in metric_types:
        if metric_type not in metrics_records:
            logger.warning(f"Metric {metric_type} not found in records")
            continue

        all_records = metrics_records[metric_type]
        logger.debug(f"Found {len(all_records)} total {metric_type} records")

        # Apply metric-specific aggregation strategy
        date_range = (filter_start, filter_end)
        aggregated_values = aggregate_metric_values(
            all_records, metric_type, date_range
        )

        if not aggregated_values:
            logger.warning(f"No {metric_type} records found in time range")
            results.append(
                {
                    "metric": metric_type,
                    "unit": get_expected_unit_format(metric_type) or "",
                    "sample_size": 0,
                    "stats": {},
                    "message": f"No {metric_type} data found for {time_range_desc}",
                }
            )
            continue

        # Get aggregation summary for logging
        summary = get_aggregation_summary(all_records, metric_type, date_range)
        strategy = get_aggregation_strategy(metric_type)

        logger.info(
            f"{metric_type} aggregation: {summary['strategy']} strategy, "
            f"{summary['original_records']} → {summary['aggregated_values']} values "
            f"(reduction: {summary['reduction_ratio']:.1f}x)"
        )

        # Get appropriate unit format
        unit = (
            get_expected_unit_format(metric_type) or all_records[0].get("unit", "")
            if all_records
            else ""
        )

        # Normalize BodyMass values to lbs
        values_for_stats = aggregated_values
        if metric_type == "BodyMass":
            original_unit = (
                all_records[0].get("unit", "kg") if all_records else "kg"
            ).lower()
            if "kg" in original_unit:
                values_for_stats = [kg_to_lbs(v) for v in aggregated_values]
            unit = "lbs"

        # Compute requested statistics using helper
        stats = {}
        sample_size = len(aggregated_values)
        logger.info(
            f"📊 Stats calculation for {metric_type}: sample_size={sample_size}, "
            f"aggregated_values={aggregated_values[:5] if len(aggregated_values) <= 5 else aggregated_values[:3]} (showing first few)"
        )

        if "average" in aggregations or "avg" in aggregations:
            avg_value = mean(values_for_stats)
            stats["average"] = _format_stat_value(
                metric_type, "average", avg_value, unit, sample_size
            )

        if "min" in aggregations or "minimum" in aggregations:
            min_value = min(values_for_stats)
            stats["min"] = _format_stat_value(
                metric_type, "min", min_value, unit, sample_size
            )

        if "max" in aggregations or "maximum" in aggregations:
            max_value = max(values_for_stats)
            stats["max"] = _format_stat_value(
                metric_type, "max", max_value, unit, sample_size
            )

        if "sum" in aggregations or "total" in aggregations:
            # Skip sum for BodyMass (not meaningful)
            if metric_type == "BodyMass":
                logger.debug(
                    f"Skipping sum aggregation for {metric_type} (not meaningful)"
                )
            else:
                sum_value = sum(aggregated_values)
                stats["sum"] = _format_stat_value(
                    metric_type, "sum", sum_value, unit, sample_size
                )

        if "count" in aggregations:
            if strategy.value in ["cumulative", "daily_average", "latest_value"]:
                count_formatted = f"{sample_size} days with data"
            else:
                count_formatted = f"{sample_size} readings"
            stats["count"] = {"value": sample_size, "formatted": count_formatted}

        results.append(
            {
                "metric": metric_type,
                "unit": unit,
                "sample_size": sample_size,
                "aggregation_strategy": strategy.value,
                "original_records": summary["original_records"],
                "stats": stats,
            }
        )

    logger.info(f"Returning statistics for {len(results)} metrics")
    return {
        "mode": "statistics",
        "time_range": time_range_desc,
        "total_metrics": len(results),
        "results": results,
    }
