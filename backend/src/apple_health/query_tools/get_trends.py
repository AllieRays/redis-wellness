"""
Trends Analysis Tool - Get trends and period comparisons for any metric.

Combines weight trend analysis and time period comparisons into a single tool.
Handles both trend analysis (linear regression, moving averages) and
period-over-period comparisons with statistical significance.
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.exceptions import HealthDataNotFoundError, ToolExecutionError
from ...utils.health_analytics import (
    calculate_weight_trends,
    compare_time_periods,
)
from ...utils.user_config import get_user_health_data_key

logger = logging.getLogger(__name__)


def create_get_trends_tool(user_id: str):
    """
    Create get_trends tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_trends(
        metric_type: str,
        analysis_type: str = "comparison",
        period1: str | None = None,
        period2: str | None = None,
        time_period: str = "last_90_days",
        trend_type: str = "both",
    ) -> dict[str, Any]:
        """
        Get trend analysis or period-over-period comparisons for any metric.

        USE WHEN user asks:
        - "Am I losing weight?" (trend analysis)
        - "Compare my weight this month vs last month" (period comparison)
        - "How does my heart rate compare to last week?" (period comparison)
        - "Show my weight trend" (trend analysis)

        DO NOT USE for:
        - Raw data points → use get_health_metrics instead
        - Statistics without comparison → use get_health_metrics instead

        Args:
            metric_type: Metric to analyze
                Valid: "BodyMass", "HeartRate", "StepCount", "BodyMassIndex", "ActiveEnergyBurned"
            analysis_type: Type of analysis (default: "comparison")
                Options: "trend", "comparison"
            period1: First time period for comparison (required if analysis_type="comparison")
                Examples: "this month", "October 2025", "this week"
            period2: Second time period for comparison (required if analysis_type="comparison")
                Examples: "last month", "September 2025", "last week"
            time_period: Time period for trend analysis (default: "last_90_days", used if analysis_type="trend")
                Options: "last_90_days", "last_30_days", "this_month", "last_month"
            trend_type: Type of trend analysis (default: "both", used if analysis_type="trend")
                Options: "linear_regression", "moving_average", "both"

        Returns:
            Dict with:
            - For "trend": slope, R², trend direction, statistical significance
            - For "comparison": period averages, difference, percent change, significance

        Examples:
            Query: "Am I losing weight?"
            Call: get_trends(metric_type="BodyMass", analysis_type="trend", time_period="last_30_days")
            Returns: {"slope": -0.5, "direction": "decreasing", "r_squared": 0.82}

            Query: "Compare my weight this month vs last month"
            Call: get_trends(metric_type="BodyMass", analysis_type="comparison", period1="this month", period2="last month")
            Returns: {"period1_avg": 155.2, "period2_avg": 157.8, "difference": -2.6, "percent_change": -1.6}

            Query: "Heart rate this week vs last week"
            Call: get_trends(metric_type="HeartRate", analysis_type="comparison", period1="this week", period2="last week")
            Returns: Comparison with statistical significance testing
        """
        logger.info(
            f"🔧 get_trends called: metric_type='{metric_type}', analysis_type='{analysis_type}', "
            f"period1='{period1}', period2='{period2}', user_id={user_id}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    raise HealthDataNotFoundError(user_id)

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                # Get records for the specified metric
                all_records = metrics_records.get(metric_type, [])

                if not all_records:
                    raise HealthDataNotFoundError(user_id, metric_types=[metric_type])

                # Branch based on analysis type
                if analysis_type == "trend":
                    # Trend analysis (linear regression, moving average)
                    result = calculate_weight_trends(
                        all_records, time_period, trend_type
                    )
                    logger.info("✅ Trend analysis complete")
                    return result

                elif analysis_type == "comparison":
                    # Period comparison
                    if not period1 or not period2:
                        raise ValueError(
                            "period1 and period2 are required for comparison analysis"
                        )

                    result = compare_time_periods(
                        all_records, metric_type, period1, period2
                    )
                    logger.info("✅ Period comparison complete")
                    return result

                else:
                    raise ValueError(
                        f"Invalid analysis_type: {analysis_type}. Must be 'trend' or 'comparison'"
                    )

        except (HealthDataNotFoundError, ToolExecutionError):
            raise
        except Exception as e:
            raise ToolExecutionError("get_trends", str(e)) from e

    return get_trends
