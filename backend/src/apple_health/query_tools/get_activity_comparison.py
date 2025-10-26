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
from collections import Counter
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.exceptions import HealthDataNotFoundError, ToolExecutionError
from ...utils.metric_aggregators import aggregate_metric_values
from ...utils.time_utils import parse_time_period
from ...utils.user_config import get_user_health_data_key

logger = logging.getLogger(__name__)


def _calculate_comparison(
    p1_value: float, p2_value: float, unit: str | None = None
) -> dict[str, Any]:
    """
    Calculate comparison metrics between two values.

    Args:
        p1_value: Value from period 1
        p2_value: Value from period 2
        unit: Optional unit for the metric

    Returns:
        Dict with difference, percent change, direction, and optional unit
    """
    diff = p1_value - p2_value
    pct_change = (diff / p2_value * 100) if p2_value > 0 else 0

    result = {
        "diff": round(diff, 1),
        "pct": round(pct_change, 1),
        "direction": "up" if diff > 0 else "down" if diff < 0 else "same",
    }

    if unit:
        result["unit"] = unit

    return result


def _generate_insight(comparison: dict[str, Any]) -> str:
    """
    Generate human-readable summary for LLM consumption.

    Args:
        comparison: Comparison dict with metric changes

    Returns:
        Natural language summary of key changes
    """
    insights = []

    if "steps" in comparison and comparison["steps"]["pct"] != 0:
        pct = comparison["steps"]["pct"]
        direction = "more" if pct > 0 else "fewer"
        insights.append(f"{abs(pct):.1f}% {direction} daily steps")

    if "active_energy" in comparison and comparison["active_energy"]["pct"] != 0:
        pct = comparison["active_energy"]["pct"]
        direction = "more" if pct > 0 else "less"
        insights.append(f"{abs(pct):.1f}% {direction} energy burned")

    if "distance" in comparison and comparison["distance"]["pct"] != 0:
        pct = comparison["distance"]["pct"]
        direction = "more" if pct > 0 else "less"
        insights.append(f"{abs(pct):.1f}% {direction} distance")

    if "workouts" in comparison and comparison["workouts"]["diff"] != 0:
        diff = int(comparison["workouts"]["diff"])
        direction = "more" if diff > 0 else "fewer"
        insights.append(
            f"{abs(diff)} {direction} workout{'s' if abs(diff) != 1 else ''}"
        )

    return "; ".join(insights) if insights else "No significant changes"


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
            Dict with optimized structure for LLM:
            - periods.p1/p2: {period, dates, steps, energy, distance, workouts}
            - comparison: {steps, active_energy, distance, workouts} with diff/pct/direction
            - summary: Natural language insight of key changes

        Examples:
            Query: "Compare my activity in October vs September"
            Call: get_activity_comparison(period1="October 2025", period2="September 2025")
            Returns: {
                "periods": {
                    "p1": {"period": "October 2025", "steps": {"total": 245000, "avg": 7903, "days": 31}},
                    "p2": {"period": "September 2025", "steps": {"total": 216000, "avg": 7200, "days": 30}}
                },
                "comparison": {"steps": {"diff": 703, "pct": 9.8, "direction": "up"}},
                "summary": "9.8% more daily steps; 2 more workouts"
            }

            Query: "This month vs last month activity"
            Call: get_activity_comparison(period1="this month", period2="last month")
            Returns: Flattened structure with rounded values and natural language summary
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

                # Initialize result with flattened structure
                result = {
                    "periods": {
                        "p1": {
                            "period": desc1,
                            "dates": f"{start1.date()} to {end1.date()}",
                        },
                        "p2": {
                            "period": desc2,
                            "dates": f"{start2.date()} to {end2.date()}",
                        },
                    },
                    "comparison": {},
                    "summary": "",
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
                        total = sum(period1_daily_steps)
                        avg = total / len(period1_daily_steps)
                        result["periods"]["p1"]["steps"] = {
                            "total": int(total),
                            "avg": round(avg, 1),
                            "days": len(period1_daily_steps),
                        }

                    if period2_daily_steps:
                        total = sum(period2_daily_steps)
                        avg = total / len(period2_daily_steps)
                        result["periods"]["p2"]["steps"] = {
                            "total": int(total),
                            "avg": round(avg, 1),
                            "days": len(period2_daily_steps),
                        }

                # Process Active Energy (using proper daily aggregation)
                energy_unit = "kcal"
                if "ActiveEnergyBurned" in metrics_records:
                    energy_records = metrics_records["ActiveEnergyBurned"]
                    if energy_records:
                        energy_unit = energy_records[0].get("unit", "kcal")

                    # Aggregate by day first (ActiveEnergyBurned is cumulative)
                    period1_daily_energy = aggregate_metric_values(
                        energy_records, "ActiveEnergyBurned", (start1, end1)
                    )
                    period2_daily_energy = aggregate_metric_values(
                        energy_records, "ActiveEnergyBurned", (start2, end2)
                    )

                    if period1_daily_energy:
                        total = sum(period1_daily_energy)
                        avg = total / len(period1_daily_energy)
                        result["periods"]["p1"]["energy"] = {
                            "total": round(total, 1),
                            "avg": round(avg, 1),
                            "days": len(period1_daily_energy),
                            "unit": energy_unit,
                        }

                    if period2_daily_energy:
                        total = sum(period2_daily_energy)
                        avg = total / len(period2_daily_energy)
                        result["periods"]["p2"]["energy"] = {
                            "total": round(total, 1),
                            "avg": round(avg, 1),
                            "days": len(period2_daily_energy),
                            "unit": energy_unit,
                        }

                # Process Distance (using proper daily aggregation)
                distance_unit = "km"
                if "DistanceWalkingRunning" in metrics_records:
                    distance_records = metrics_records["DistanceWalkingRunning"]
                    if distance_records:
                        distance_unit = distance_records[0].get("unit", "km")

                    # Aggregate by day first (DistanceWalkingRunning is cumulative)
                    period1_daily_distance = aggregate_metric_values(
                        distance_records, "DistanceWalkingRunning", (start1, end1)
                    )
                    period2_daily_distance = aggregate_metric_values(
                        distance_records, "DistanceWalkingRunning", (start2, end2)
                    )

                    if period1_daily_distance:
                        total = sum(period1_daily_distance)
                        avg = total / len(period1_daily_distance)
                        result["periods"]["p1"]["distance"] = {
                            "total": round(total, 1),
                            "avg": round(avg, 1),
                            "days": len(period1_daily_distance),
                            "unit": distance_unit,
                        }

                    if period2_daily_distance:
                        total = sum(period2_daily_distance)
                        avg = total / len(period2_daily_distance)
                        result["periods"]["p2"]["distance"] = {
                            "total": round(total, 1),
                            "avg": round(avg, 1),
                            "days": len(period2_daily_distance),
                            "unit": distance_unit,
                        }

                # Process Workouts (single-pass with Counter)
                period1_workouts = []
                period2_workouts = []
                period1_types = Counter()
                period2_types = Counter()

                for workout in workouts:
                    workout_date = parse_health_record_date(workout["startDate"])
                    wtype = workout.get("type", "Unknown")

                    if start1 <= workout_date <= end1:
                        period1_workouts.append(workout)
                        period1_types[wtype] += 1
                    if start2 <= workout_date <= end2:
                        period2_workouts.append(workout)
                        period2_types[wtype] += 1

                if period1_workouts:
                    total_duration = sum(w.get("duration", 0) for w in period1_workouts)
                    result["periods"]["p1"]["workouts"] = {
                        "count": len(period1_workouts),
                        "types": dict(period1_types),
                        "duration_mins": round(total_duration, 1),
                    }

                if period2_workouts:
                    total_duration = sum(w.get("duration", 0) for w in period2_workouts)
                    result["periods"]["p2"]["workouts"] = {
                        "count": len(period2_workouts),
                        "types": dict(period2_types),
                        "duration_mins": round(total_duration, 1),
                    }

                # Calculate comparisons using DRY helper function
                comparison = {}

                # Steps comparison
                p1_steps = result["periods"]["p1"].get("steps")
                p2_steps = result["periods"]["p2"].get("steps")
                if p1_steps and p2_steps:
                    comparison["steps"] = _calculate_comparison(
                        p1_steps["avg"], p2_steps["avg"]
                    )

                # Energy comparison
                p1_energy = result["periods"]["p1"].get("energy")
                p2_energy = result["periods"]["p2"].get("energy")
                if p1_energy and p2_energy:
                    comparison["active_energy"] = _calculate_comparison(
                        p1_energy["avg"], p2_energy["avg"], unit=energy_unit
                    )

                # Distance comparison
                p1_distance = result["periods"]["p1"].get("distance")
                p2_distance = result["periods"]["p2"].get("distance")
                if p1_distance and p2_distance:
                    comparison["distance"] = _calculate_comparison(
                        p1_distance["avg"], p2_distance["avg"], unit=distance_unit
                    )

                # Workout comparison
                p1_workouts = result["periods"]["p1"].get("workouts")
                p2_workouts = result["periods"]["p2"].get("workouts")
                if p1_workouts and p2_workouts:
                    comparison["workouts"] = _calculate_comparison(
                        float(p1_workouts["count"]), float(p2_workouts["count"])
                    )

                result["comparison"] = comparison
                result["summary"] = _generate_insight(comparison)

                logger.info("✅ Activity comparison complete")
                return result

        except (HealthDataNotFoundError, ToolExecutionError):
            raise
        except Exception as e:
            raise ToolExecutionError("get_activity_comparison", str(e)) from e

    return get_activity_comparison
