"""
Sleep Analysis Tool - Query sleep data with daily aggregation.

Provides LLM with access to sleep metrics including total sleep hours,
in-bed time, sleep efficiency, and detailed sleep stage breakdown.
"""

import json
import logging
from statistics import mean
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.exceptions import HealthDataNotFoundError, ToolExecutionError
from ...utils.sleep_aggregator import (
    aggregate_sleep_by_date,
    parse_sleep_segments_from_records,
)
from ...utils.time_utils import parse_time_period
from ...utils.user_config import get_user_health_data_key

logger = logging.getLogger(__name__)


def create_get_sleep_analysis_tool(user_id: str):
    """
    Create get_sleep_analysis tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_sleep_analysis(
        time_period: str = "last 7 days",
        include_details: bool = False,
    ) -> dict[str, Any]:
        """
        Get sleep analysis with daily aggregated metrics.

        USE WHEN user asks about:
        - "How much sleep do I get?" (average over time)
        - "Did I sleep well last night?" (recent single day)
        - "What's my sleep pattern this week?" (trend over days)
        - "When do I usually go to bed?" (sleep timing)
        - "What's my sleep efficiency?" (quality metric)

        DO NOT USE for:
        - Workout data → use get_workouts instead
        - Activity metrics → use get_health_metrics instead

        Args:
            time_period: Natural language time period (default: "last 7 days")
                Examples: "last night", "this week", "October", "last 30 days"
            include_details: Include detailed sleep stage breakdown (default: False)
                Set to True for: "deep sleep", "REM sleep", "sleep stages"

        Returns:
            Dict with:
            - sleep_nights: List of daily sleep summaries
            - average_sleep_hours: Mean sleep duration
            - average_efficiency: Mean sleep efficiency percentage
            - total_nights: Number of nights with data
            - time_range: Human-readable time description

        Examples:
            Query: "How much sleep do I get regularly?"
            Call: get_sleep_analysis(time_period="last 30 days")
            Returns: Average sleep hours over 30 days with nightly breakdown

            Query: "Did I sleep well last night?"
            Call: get_sleep_analysis(time_period="last night")
            Returns: Single night summary with hours and efficiency

            Query: "What's my deep sleep like this week?"
            Call: get_sleep_analysis(time_period="this week", include_details=True)
            Returns: Week of sleep with deep/REM/core breakdown
        """
        logger.info(
            f"get_sleep_analysis called: time_period='{time_period}', "
            f"include_details={include_details}, user_id={user_id}"
        )

        try:
            # Parse time period into date range
            filter_start, filter_end, time_range_desc = parse_time_period(time_period)
            logger.debug(
                f"Parsed '{time_period}' → {filter_start.strftime('%Y-%m-%d')} to "
                f"{filter_end.strftime('%Y-%m-%d')}"
            )

            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {
                        "error": "No health data found for user",
                        "sleep_nights": [],
                    }

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                # Get sleep analysis records
                sleep_records = metrics_records.get(
                    "HKCategoryTypeIdentifierSleepAnalysis", []
                )

                if not sleep_records:
                    return {
                        "error": "No sleep data found",
                        "sleep_nights": [],
                        "message": "No sleep analysis data in your Apple Health records. "
                        "Make sure your device is tracking sleep.",
                    }

                logger.info(f"Found {len(sleep_records)} sleep record segments")

                # Parse segments and aggregate by date
                sleep_segments = parse_sleep_segments_from_records(sleep_records)

                # Filter by date range
                filtered_segments = [
                    seg
                    for seg in sleep_segments
                    if filter_start <= seg.end_date <= filter_end
                ]

                if not filtered_segments:
                    return {
                        "sleep_nights": [],
                        "total_nights": 0,
                        "time_range": time_range_desc,
                        "message": f"No sleep data found for {time_range_desc}",
                    }

                logger.info(
                    f"Filtered to {len(filtered_segments)} segments in {time_range_desc}"
                )

                # Aggregate into daily summaries
                sleep_summaries = aggregate_sleep_by_date(filtered_segments)

                # Calculate averages
                if sleep_summaries:
                    avg_sleep = mean([s.total_sleep_hours for s in sleep_summaries])
                    efficiencies = [
                        s.sleep_efficiency
                        for s in sleep_summaries
                        if s.sleep_efficiency is not None
                    ]
                    avg_efficiency = mean(efficiencies) if efficiencies else None
                else:
                    avg_sleep = 0.0
                    avg_efficiency = None

                # Format for LLM consumption
                sleep_nights = []
                for summary in sleep_summaries:
                    night_data = {
                        "date": summary.date,
                        "sleep_hours": summary.total_sleep_hours,
                        "in_bed_hours": summary.total_in_bed_hours,
                        "sleep_efficiency": summary.sleep_efficiency,
                        "bedtime": summary.first_sleep_time,
                        "wake_time": summary.last_wake_time,
                    }

                    # Add detailed breakdown if requested
                    if include_details:
                        night_data["details"] = {
                            "deep_sleep_hours": summary.deep_sleep_hours,
                            "rem_sleep_hours": summary.rem_sleep_hours,
                            "core_sleep_hours": summary.core_sleep_hours,
                            "awake_hours": summary.awake_hours,
                            "segment_count": summary.segment_count,
                        }

                    sleep_nights.append(night_data)

                logger.info(
                    f"Returning {len(sleep_nights)} nights of sleep data "
                    f"(avg: {avg_sleep:.1f}h)"
                )

                return {
                    "sleep_nights": sleep_nights,
                    "average_sleep_hours": round(avg_sleep, 2),
                    "average_efficiency": round(avg_efficiency, 1)
                    if avg_efficiency
                    else None,
                    "total_nights": len(sleep_nights),
                    "time_range": time_range_desc,
                }

        except HealthDataNotFoundError:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid health data format: {e}", exc_info=True)
            raise ToolExecutionError(
                "get_sleep_analysis", f"Invalid health data format: {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Error in get_sleep_analysis: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise ToolExecutionError("get_sleep_analysis", str(e)) from e

    return get_sleep_analysis
