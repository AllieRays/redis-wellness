"""
Health Analytics Tools - LangChain tools for advanced health data analysis.

Provides analytical tools for:
- Weight trend analysis with linear regression
- Time period comparisons with statistical significance
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


def create_weight_trends_tool(user_id: str):
    """
    Create calculate_weight_trends_tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def calculate_weight_trends_tool(
        time_period: str = "last_90_days", trend_type: str = "both"
    ) -> dict[str, Any]:
        """
        Calculate weight trends with linear regression and moving averages.

        Use this when the user asks about:
        - Weight trends over time
        - "Am I losing or gaining weight?"
        - "Calculate my weight trend"
        - "Show me my weight progress"
        - Statistical analysis of weight changes

        Args:
            time_period: Time period to analyze ("last_90_days", "last_30_days", "this_month", "last_month")
            trend_type: Type of analysis ("linear_regression", "moving_average", "both")

        Returns:
            Dict with trend analysis including slope, R², statistical significance

        Examples:
            - "Calculate my weight trend over 3 months" → time_period="last_90_days", trend_type="both"
            - "Am I losing weight?" → time_period="last_30_days", trend_type="linear_regression"
        """
        logger.info(
            f"🔧 calculate_weight_trends_tool called: time_period='{time_period}', trend_type='{trend_type}', user_id={user_id}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    raise HealthDataNotFoundError(user_id)

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                # Get weight records
                weight_records = metrics_records.get("BodyMass", [])

                if not weight_records:
                    raise HealthDataNotFoundError(user_id, metric_types=["BodyMass"])

                # Call pure function with data
                result = calculate_weight_trends(
                    weight_records, time_period, trend_type
                )

                logger.info("✅ Weight trend analysis complete")
                return result

        except (HealthDataNotFoundError, ToolExecutionError):
            raise
        except Exception as e:
            raise ToolExecutionError("calculate_weight_trends_tool", str(e)) from e

    return calculate_weight_trends_tool


def create_compare_periods_tool(user_id: str):
    """
    Create compare_time_periods_tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def compare_time_periods_tool(
        metric_type: str, period1: str, period2: str
    ) -> dict[str, Any]:
        """
        Compare metrics between two time periods with statistical significance.

        Use this when the user asks to compare:
        - "Compare my weight this month vs last month"
        - "How does my heart rate this week compare to last week?"
        - "Compare my activity levels"
        - Period-over-period analysis

        Args:
            metric_type: Type of metric ("BodyMass", "HeartRate", "StepCount", "BodyMassIndex", "ActiveEnergyBurned")
            period1: First time period ("this_month", "last_30_days", etc.)
            period2: Second time period ("last_month", "previous_30_days", etc.)

        Returns:
            Dict with comparison statistics and significance testing

        Examples:
            - "Compare my weight this month vs last month" → metric_type="BodyMass", period1="this_month", period2="last_month"
            - "How does my heart rate compare?" → metric_type="HeartRate", period1="last_week", period2="previous_week"
        """
        logger.info(
            f"🔧 compare_time_periods_tool called: metric_type='{metric_type}', period1='{period1}', period2='{period2}', user_id={user_id}"
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

                # Call pure function with data
                result = compare_time_periods(
                    all_records, metric_type, period1, period2
                )

                logger.info("✅ Period comparison complete")
                return result

        except (HealthDataNotFoundError, ToolExecutionError):
            raise
        except Exception as e:
            raise ToolExecutionError("compare_time_periods_tool", str(e)) from e

    return compare_time_periods_tool
