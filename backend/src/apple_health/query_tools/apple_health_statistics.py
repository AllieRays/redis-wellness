"""
Metrics Aggregation Tool - LangChain tool for computing health statistics.

Provides the aggregate_metrics tool which performs mathematical aggregation
on health metric data (average, min, max, sum, count).
"""

import json
import logging
from statistics import mean
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.conversion_utils import (
    kg_to_lbs as _kg_to_lbs,
)
from ...utils.exceptions import HealthDataNotFoundError, ToolExecutionError
from ...utils.metric_aggregators import aggregate_metric_values, get_aggregation_summary
from ...utils.metric_classifier import (
    get_aggregation_strategy,
    get_expected_unit_format,
)
from ...utils.time_utils import parse_time_period as _parse_time_period

logger = logging.getLogger(__name__)


def create_aggregate_metrics_tool(user_id: str):
    """
    Create aggregate_metrics tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def aggregate_metrics(
        metric_types: list[str],
        time_period: str = "recent",
        aggregations: list[str] = None,
    ) -> dict[str, Any]:
        """
        🔢 CALCULATE STATISTICS - Use for mathematical aggregation: average, min, max, sum, count.

        ⚠️ USE THIS TOOL WHEN USER ASKS FOR:
        - AVERAGE/MEAN: "average heart rate", "mean weight", "avg BMI"
        - MIN/MAX: "minimum", "lowest", "highest", "maximum", "best", "worst"
        - TOTAL/SUM: "total steps", "sum of calories", "how many total"
        - STATISTICS: "stats on", "statistics", "give me numbers", "calculate"
        - COMPUTATION: "compute", "calculate my", "what's my avg"

        ❌ DO NOT USE THIS TOOL FOR:
        - Individual data points → use search_health_records_by_metric instead
        - Viewing trends over time → use search_health_records_by_metric instead
        - Listing all values → use search_health_records_by_metric instead
        - Workouts → use search_workouts_and_activity instead

        This tool performs MATHEMATICAL AGGREGATION on health metric data.
        It returns COMPUTED STATISTICS (single numbers), NOT raw data lists.

        Args:
            metric_types: List of metric types ["HeartRate", "BodyMass", "BodyMassIndex", "StepCount", "ActiveEnergyBurned"]
            time_period: Natural language time ("last week", "September", "this month", "last 30 days", "recent")
            aggregations: Statistics to compute ["average", "min", "max", "sum", "count"] (defaults to all if not specified)

        Example Queries and Tool Calls (illustrative):
            Query: "What was my average heart rate last week?"
            → aggregate_metrics(metric_types=["HeartRate"], time_period="last week", aggregations=["average"])
            Returns: {"average": "<number> bpm", "sample_size": <count>}

            Query: "Give me stats on my weight in September"
            → aggregate_metrics(metric_types=["BodyMass"], time_period="September", aggregations=["average", "min", "max"])
            Returns: {"average": "<number> lbs", "min": "<number> lbs", "max": "<number> lbs"}

            Query: "How many total steps did I take this month?"
            → aggregate_metrics(metric_types=["StepCount"], time_period="this month", aggregations=["sum"])
            Returns: {"sum": "<number>", "count": <days>}

        Returns:
            Dict with computed statistics for each metric type
        """
        logger.info(
            f"🔧 aggregate_metrics called: metrics={metric_types}, time_period='{time_period}', aggregations={aggregations}, user_id={user_id}"
        )

        try:
            # Default aggregations if not provided
            if not aggregations:
                aggregations = ["average", "min", "max", "count"]

            # Parse time period into date range
            filter_start, filter_end, time_range_desc = _parse_time_period(time_period)
            logger.info(
                f"📅 Parsed '{time_period}' → {filter_start.strftime('%Y-%m-%d')} to {filter_end.strftime('%Y-%m-%d')} ({time_range_desc})"
            )

            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found for user", "results": []}

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                results = []
                for metric_type in metric_types:
                    if metric_type not in metrics_records:
                        logger.warning(f"⚠️ Metric {metric_type} not found in records")
                        continue

                    all_records = metrics_records[metric_type]
                    logger.info(
                        f"📊 Found {len(all_records)} total {metric_type} records"
                    )

                    # METRIC-SPECIFIC AGGREGATION using new utilities
                    # Apply metric-specific aggregation strategy
                    date_range = (filter_start, filter_end)
                    aggregated_values = aggregate_metric_values(
                        all_records, metric_type, date_range
                    )

                    if not aggregated_values:
                        logger.warning(
                            f"⚠️ No {metric_type} records found in time range"
                        )
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
                    summary = get_aggregation_summary(
                        all_records, metric_type, date_range
                    )
                    strategy = get_aggregation_strategy(metric_type)

                    logger.info(
                        f"✅ {metric_type} aggregation: {summary['strategy']} strategy, "
                        f"{summary['original_records']} → {summary['aggregated_values']} values "
                        f"(reduction: {summary['reduction_ratio']:.1f}x)"
                    )

                    # Calculate statistics on properly aggregated values
                    statistics = {}

                    # Get appropriate unit format for this metric
                    unit = (
                        get_expected_unit_format(metric_type)
                        or all_records[0].get("unit", "")
                        if all_records
                        else ""
                    )

                    # Normalize BodyMass values to lbs for statistics
                    values_for_stats = aggregated_values
                    if metric_type == "BodyMass":
                        original_unit = (
                            all_records[0].get("unit", "kg") if all_records else "kg"
                        ).lower()
                        if "kg" in original_unit:
                            values_for_stats = [
                                _kg_to_lbs(v) for v in aggregated_values
                            ]
                        unit = "lbs"

                    if "average" in aggregations or "avg" in aggregations:
                        avg_value = mean(values_for_stats)
                        # Format based on metric type
                        if metric_type == "StepCount":
                            statistics["average"] = f"{avg_value:.0f} steps/day"
                        elif metric_type == "HeartRate":
                            statistics["average"] = f"{avg_value:.1f} bpm (daily avg)"
                        elif metric_type == "BodyMass":
                            statistics["average"] = f"{avg_value:.1f} lbs"
                        else:
                            statistics["average"] = (
                                f"{avg_value:.1f} {unit}"
                                if unit
                                else f"{avg_value:.1f}"
                            )

                    if "min" in aggregations or "minimum" in aggregations:
                        min_value = min(values_for_stats)
                        if metric_type == "StepCount":
                            statistics["min"] = f"{min_value:.0f} steps (lowest day)"
                        elif metric_type == "HeartRate":
                            statistics["min"] = (
                                f"{min_value:.1f} bpm (lowest daily avg)"
                            )
                        elif metric_type == "BodyMass":
                            statistics["min"] = f"{min_value:.1f} lbs"
                        else:
                            statistics["min"] = (
                                f"{min_value:.1f} {unit}"
                                if unit
                                else f"{min_value:.1f}"
                            )

                    if "max" in aggregations or "maximum" in aggregations:
                        max_value = max(values_for_stats)
                        if metric_type == "StepCount":
                            statistics["max"] = (
                                f"{max_value:.0f} steps (most active day)"
                            )
                        elif metric_type == "HeartRate":
                            statistics["max"] = (
                                f"{max_value:.1f} bpm (highest daily avg)"
                            )
                        elif metric_type == "BodyMass":
                            statistics["max"] = f"{max_value:.1f} lbs"
                        else:
                            statistics["max"] = (
                                f"{max_value:.1f} {unit}"
                                if unit
                                else f"{max_value:.1f}"
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
                            # Sum of weights makes no sense - skip this aggregation
                            logger.warning(
                                f"⚠️ Skipping sum aggregation for {metric_type} (not meaningful)"
                            )
                        else:
                            statistics["sum"] = (
                                f"{sum_value:.1f} {unit}"
                                if unit
                                else f"{sum_value:.1f}"
                            )

                    if "count" in aggregations:
                        if strategy.value in [
                            "cumulative",
                            "daily_average",
                            "latest_value",
                        ]:
                            statistics["count"] = (
                                f"{len(aggregated_values)} days with data"
                            )
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
                }

        except HealthDataNotFoundError:
            raise
        except Exception as e:
            raise ToolExecutionError("aggregate_metrics", str(e)) from e

    return aggregate_metrics
