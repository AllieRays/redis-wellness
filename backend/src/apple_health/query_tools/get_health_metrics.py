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
from ...utils.conversion_utils import (
    convert_weight_to_lbs as _convert_weight_to_lbs,
)
from ...utils.conversion_utils import (
    kg_to_lbs as _kg_to_lbs,
)
from ...utils.exceptions import HealthDataNotFoundError, ToolExecutionError
from ...utils.metric_aggregators import aggregate_metric_values, get_aggregation_summary
from ...utils.metric_classifier import (
    get_aggregation_strategy,
    get_expected_unit_format,
)
from ...utils.time_utils import (
    parse_health_record_date as _parse_health_record_date,
)
from ...utils.time_utils import (
    parse_time_period as _parse_time_period,
)
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
                Examples: ["BodyMass"], ["HeartRate", "StepCount"], ["BodyMassIndex"]
                Valid: "BodyMass", "BodyMassIndex", "HeartRate", "StepCount", "ActiveEnergyBurned"
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
            filter_start, filter_end, time_range_desc = _parse_time_period(time_period)
            logger.info(
                f"📅 Parsed '{time_period}' → {filter_start.strftime('%Y-%m-%d')} to "
                f"{filter_end.strftime('%Y-%m-%d')} ({time_range_desc})"
            )

            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found for user", "results": []}

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
        except Exception as e:
            logger.error(
                f"❌ Error in get_health_metrics: {type(e).__name__}: {e}",
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
        # Try to get historical records first
        if metric_type in metrics_records:
            all_records = metrics_records[metric_type]
            logger.info(f"📊 Found {len(all_records)} total {metric_type} records")

            # Filter by date range
            filtered_records = []
            for record in all_records:
                record_date = _parse_health_record_date(record["date"])

                if filter_start <= record_date <= filter_end:
                    value = record["value"]
                    unit = record["unit"]

                    # Convert weight from kg/lb to lbs
                    if metric_type == "BodyMass":
                        value = _convert_weight_to_lbs(value, unit)
                    elif unit:
                        value = f"{value} {unit}"

                    filtered_records.append(
                        {
                            "value": value,
                            "date": record_date.date().isoformat(),
                        }
                    )

            logger.info(
                f"✅ Filtered to {len(filtered_records)} {metric_type} records ({time_range_desc})"
            )

            results.append(
                {
                    "metric_type": metric_type,
                    "records": filtered_records,
                    "total_found": len(filtered_records),
                    "time_range": time_range_desc,
                }
            )

        # Fall back to summary if no detailed records
        elif metric_type in metrics_summary:
            metric_info = metrics_summary[metric_type]
            latest_value = metric_info.get("latest_value", "N/A")
            unit = metric_info.get("unit", "")

            if metric_type == "BodyMass" and latest_value != "N/A":
                latest_value = _convert_weight_to_lbs(latest_value, unit)
            elif latest_value != "N/A" and unit:
                latest_value = f"{latest_value} {unit}"

            results.append(
                {
                    "metric_type": metric_type,
                    "latest_value": latest_value,
                    "latest_date": metric_info.get("latest_date", "N/A"),
                    "total_records": metric_info.get("count", 0),
                    "time_range": time_range_desc,
                }
            )

    logger.info(f"📤 Returning {len(results)} metric types (raw data)")
    return {
        "results": results,
        "total_metrics": len(results),
        "searched_metrics": metric_types,
        "mode": "raw_data",
    }


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
            logger.warning(f"⚠️ Metric {metric_type} not found in records")
            continue

        all_records = metrics_records[metric_type]
        logger.info(f"📊 Found {len(all_records)} total {metric_type} records")

        # Apply metric-specific aggregation strategy
        date_range = (filter_start, filter_end)
        aggregated_values = aggregate_metric_values(
            all_records, metric_type, date_range
        )

        if not aggregated_values:
            logger.warning(f"⚠️ No {metric_type} records found in time range")
            results.append(
                {
                    "metric_type": metric_type,
                    "time_range": time_range_desc,
                    "statistics": {},
                    "message": f"No {metric_type} data found for {time_range_desc}",
                }
            )
            continue

        # Get aggregation summary for logging
        summary = get_aggregation_summary(all_records, metric_type, date_range)
        strategy = get_aggregation_strategy(metric_type)

        logger.info(
            f"✅ {metric_type} aggregation: {summary['strategy']} strategy, "
            f"{summary['original_records']} → {summary['aggregated_values']} values "
            f"(reduction: {summary['reduction_ratio']:.1f}x)"
        )

        # Calculate statistics
        statistics = {}

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
                values_for_stats = [_kg_to_lbs(v) for v in aggregated_values]
            unit = "lbs"

        # Compute requested statistics
        if "average" in aggregations or "avg" in aggregations:
            avg_value = mean(values_for_stats)
            if metric_type == "StepCount":
                statistics["average"] = f"{avg_value:.0f} steps/day"
            elif metric_type == "HeartRate":
                statistics["average"] = f"{avg_value:.1f} bpm (daily avg)"
            elif metric_type == "BodyMass":
                statistics["average"] = f"{avg_value:.1f} lbs"
            else:
                statistics["average"] = (
                    f"{avg_value:.1f} {unit}" if unit else f"{avg_value:.1f}"
                )

        if "min" in aggregations or "minimum" in aggregations:
            min_value = min(values_for_stats)
            if metric_type == "StepCount":
                statistics["min"] = f"{min_value:.0f} steps (lowest day)"
            elif metric_type == "HeartRate":
                statistics["min"] = f"{min_value:.1f} bpm (lowest daily avg)"
            elif metric_type == "BodyMass":
                statistics["min"] = f"{min_value:.1f} lbs"
            else:
                statistics["min"] = (
                    f"{min_value:.1f} {unit}" if unit else f"{min_value:.1f}"
                )

        if "max" in aggregations or "maximum" in aggregations:
            max_value = max(values_for_stats)
            if metric_type == "StepCount":
                statistics["max"] = f"{max_value:.0f} steps (most active day)"
            elif metric_type == "HeartRate":
                statistics["max"] = f"{max_value:.1f} bpm (highest daily avg)"
            elif metric_type == "BodyMass":
                statistics["max"] = f"{max_value:.1f} lbs"
            else:
                statistics["max"] = (
                    f"{max_value:.1f} {unit}" if unit else f"{max_value:.1f}"
                )

        if "sum" in aggregations or "total" in aggregations:
            sum_value = sum(aggregated_values)
            if metric_type == "StepCount":
                statistics["sum"] = (
                    f"{sum_value:.0f} total steps ({len(aggregated_values)} days)"
                )
            elif metric_type == "DistanceWalkingRunning":
                statistics["sum"] = (
                    f"{sum_value:.1f} total miles ({len(aggregated_values)} days)"
                )
            elif metric_type == "BodyMass":
                logger.warning(
                    f"⚠️ Skipping sum aggregation for {metric_type} (not meaningful)"
                )
            else:
                statistics["sum"] = (
                    f"{sum_value:.1f} {unit}" if unit else f"{sum_value:.1f}"
                )

        if "count" in aggregations:
            if strategy.value in ["cumulative", "daily_average", "latest_value"]:
                statistics["count"] = f"{len(aggregated_values)} days with data"
            else:
                statistics["count"] = f"{len(aggregated_values)} readings"

        results.append(
            {
                "metric_type": metric_type,
                "time_range": time_range_desc,
                "statistics": statistics,
                "aggregation_strategy": strategy.value,
                "sample_size": len(aggregated_values),
                "original_records": summary["original_records"],
            }
        )

    logger.info(f"📤 Returning statistics for {len(results)} metrics")
    return {
        "results": results,
        "total_metrics": len(results),
        "time_range": time_range_desc,
        "mode": "statistics",
    }
