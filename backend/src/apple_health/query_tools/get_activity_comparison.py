"""
Activity Comparison Tool - Get comprehensive activity comparison.

Compares all activity-related metrics between two time periods:
- Steps
- Active Energy
- Workouts
- Distance
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.exceptions import HealthDataNotFoundError, ToolExecutionError
from ...utils.metric_aggregators import aggregate_metric_values
from ...utils.time_utils import parse_time_period
from ...utils.user_config import get_user_health_data_key

logger = logging.getLogger(__name__)


def create_get_activity_comparison_tool(user_id: str):
    """
    Create get_activity_comparison tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_activity_comparison(period1: str, period2: str) -> dict[str, Any]:
        """
        Compare comprehensive activity levels (steps, energy, workouts, distance) between two periods.

        USE WHEN user asks:
        - "Compare my activity levels in October vs September"
        - "How does this month compare to last month for activity?"
        - "Compare my activity this week vs last week"
        - "Am I more active this month?"

        DO NOT USE for:
        - Single metric comparison → use get_trends instead
        - Raw data without comparison → use get_health_metrics instead

        Args:
            period1: First time period
                Examples: "October 2025", "this month", "last week"
            period2: Second time period
                Examples: "September 2025", "last month", "previous week"

        Returns:
            Dict with:
            - period1: {steps, active_energy, distance, workouts}
            - period2: {steps, active_energy, distance, workouts}
            - comparison: {differences, percent changes}

        Examples:
            Query: "Compare my activity in October vs September"
            Call: get_activity_comparison(period1="October 2025", period2="September 2025")
            Returns: Full activity breakdown with totals, averages, and comparisons

            Query: "This month vs last month activity"
            Call: get_activity_comparison(period1="this month", period2="last month")
            Returns: Activity comparison with percent changes
        """
        logger.info(
            f"🏃 get_activity_comparison called: period1='{period1}', period2='{period2}', user_id={user_id}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    raise HealthDataNotFoundError(user_id)

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})
                workouts = health_data.get("workouts", [])

                # Parse both time periods
                from ...utils.time_utils import parse_health_record_date

                start1, end1, desc1 = parse_time_period(period1)
                start2, end2, desc2 = parse_time_period(period2)

                logger.info(f"Period 1: {start1} to {end1} ({desc1})")
                logger.info(f"Period 2: {start2} to {end2} ({desc2})")

                # Collect all activity metrics
                result = {
                    "period1": {
                        "name": desc1,
                        "date_range": f"{start1.date()} to {end1.date()}",
                        "steps": {},
                        "active_energy": {},
                        "distance": {},
                        "workouts": {},
                    },
                    "period2": {
                        "name": desc2,
                        "date_range": f"{start2.date()} to {end2.date()}",
                        "steps": {},
                        "active_energy": {},
                        "distance": {},
                        "workouts": {},
                    },
                    "comparison": {},
                }

                # Process Steps (using proper daily aggregation)
                if "StepCount" in metrics_records:
                    step_records = metrics_records["StepCount"]

                    # Aggregate by day first (StepCount is cumulative)
                    period1_daily_steps = aggregate_metric_values(
                        step_records, "StepCount", (start1, end1)
                    )
                    period2_daily_steps = aggregate_metric_values(
                        step_records, "StepCount", (start2, end2)
                    )

                    if period1_daily_steps:
                        result["period1"]["steps"] = {
                            "total": sum(period1_daily_steps),
                            "average": sum(period1_daily_steps)
                            / len(period1_daily_steps),
                            "days": len(period1_daily_steps),
                        }

                    if period2_daily_steps:
                        result["period2"]["steps"] = {
                            "total": sum(period2_daily_steps),
                            "average": sum(period2_daily_steps)
                            / len(period2_daily_steps),
                            "days": len(period2_daily_steps),
                        }

                # Process Active Energy (using proper daily aggregation)
                if "ActiveEnergyBurned" in metrics_records:
                    energy_records = metrics_records["ActiveEnergyBurned"]

                    # Aggregate by day first (ActiveEnergyBurned is cumulative)
                    period1_daily_energy = aggregate_metric_values(
                        energy_records, "ActiveEnergyBurned", (start1, end1)
                    )
                    period2_daily_energy = aggregate_metric_values(
                        energy_records, "ActiveEnergyBurned", (start2, end2)
                    )

                    if period1_daily_energy:
                        result["period1"]["active_energy"] = {
                            "total": sum(period1_daily_energy),
                            "average": sum(period1_daily_energy)
                            / len(period1_daily_energy),
                            "days": len(period1_daily_energy),
                        }

                    if period2_daily_energy:
                        result["period2"]["active_energy"] = {
                            "total": sum(period2_daily_energy),
                            "average": sum(period2_daily_energy)
                            / len(period2_daily_energy),
                            "days": len(period2_daily_energy),
                        }

                # Process Distance (using proper daily aggregation)
                if "DistanceWalkingRunning" in metrics_records:
                    distance_records = metrics_records["DistanceWalkingRunning"]

                    # Aggregate by day first (DistanceWalkingRunning is cumulative)
                    period1_daily_distance = aggregate_metric_values(
                        distance_records, "DistanceWalkingRunning", (start1, end1)
                    )
                    period2_daily_distance = aggregate_metric_values(
                        distance_records, "DistanceWalkingRunning", (start2, end2)
                    )

                    if period1_daily_distance:
                        result["period1"]["distance"] = {
                            "total": sum(period1_daily_distance),
                            "average": sum(period1_daily_distance)
                            / len(period1_daily_distance),
                            "unit": distance_records[0].get("unit", "km"),
                            "days": len(period1_daily_distance),
                        }

                    if period2_daily_distance:
                        result["period2"]["distance"] = {
                            "total": sum(period2_daily_distance),
                            "average": sum(period2_daily_distance)
                            / len(period2_daily_distance),
                            "unit": distance_records[0].get("unit", "km"),
                            "days": len(period2_daily_distance),
                        }

                # Process Workouts
                period1_workouts = []
                period2_workouts = []

                for workout in workouts:
                    workout_date = parse_health_record_date(workout["startDate"])

                    if start1 <= workout_date <= end1:
                        period1_workouts.append(workout)
                    if start2 <= workout_date <= end2:
                        period2_workouts.append(workout)

                if period1_workouts:
                    workout_types = {}
                    for w in period1_workouts:
                        wtype = w.get("type", "Unknown")
                        workout_types[wtype] = workout_types.get(wtype, 0) + 1

                    result["period1"]["workouts"] = {
                        "total": len(period1_workouts),
                        "types": workout_types,
                        "total_duration": sum(
                            w.get("duration", 0) for w in period1_workouts
                        ),
                    }

                if period2_workouts:
                    workout_types = {}
                    for w in period2_workouts:
                        wtype = w.get("type", "Unknown")
                        workout_types[wtype] = workout_types.get(wtype, 0) + 1

                    result["period2"]["workouts"] = {
                        "total": len(period2_workouts),
                        "types": workout_types,
                        "total_duration": sum(
                            w.get("duration", 0) for w in period2_workouts
                        ),
                    }

                # Calculate comparisons
                comparison = {}

                # Steps comparison
                if result["period1"]["steps"] and result["period2"]["steps"]:
                    p1_avg = result["period1"]["steps"]["average"]
                    p2_avg = result["period2"]["steps"]["average"]
                    diff = p1_avg - p2_avg
                    pct_change = (diff / p2_avg * 100) if p2_avg > 0 else 0

                    comparison["steps"] = {
                        "difference": diff,
                        "percent_change": pct_change,
                        "direction": (
                            "increase"
                            if diff > 0
                            else "decrease"
                            if diff < 0
                            else "no change"
                        ),
                    }

                # Energy comparison
                if (
                    result["period1"]["active_energy"]
                    and result["period2"]["active_energy"]
                ):
                    p1_avg = result["period1"]["active_energy"]["average"]
                    p2_avg = result["period2"]["active_energy"]["average"]
                    diff = p1_avg - p2_avg
                    pct_change = (diff / p2_avg * 100) if p2_avg > 0 else 0

                    comparison["active_energy"] = {
                        "difference": diff,
                        "percent_change": pct_change,
                        "direction": (
                            "increase"
                            if diff > 0
                            else "decrease"
                            if diff < 0
                            else "no change"
                        ),
                    }

                # Workout comparison
                if result["period1"]["workouts"] and result["period2"]["workouts"]:
                    p1_count = result["period1"]["workouts"]["total"]
                    p2_count = result["period2"]["workouts"]["total"]
                    diff = p1_count - p2_count
                    pct_change = (diff / p2_count * 100) if p2_count > 0 else 0

                    comparison["workouts"] = {
                        "difference": diff,
                        "percent_change": pct_change,
                        "direction": (
                            "increase"
                            if diff > 0
                            else "decrease"
                            if diff < 0
                            else "no change"
                        ),
                    }

                result["comparison"] = comparison

                logger.info("✅ Activity comparison complete")
                return result

        except (HealthDataNotFoundError, ToolExecutionError):
            raise
        except Exception as e:
            raise ToolExecutionError("get_activity_comparison", str(e)) from e

    return get_activity_comparison
