"""
Progress Tracking Tool - Compare workout metrics between time periods.

This tool helps answer questions like:
- "Am I getting stronger?"
- "How's my progress?"
- "Have I improved since my injury?"

The tool performs time-based comparisons so Qwen doesn't have to.
"""

import logging
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Any

from langchain_core.tools import tool

from ...utils.workout_fetchers import fetch_workouts_in_range

logger = logging.getLogger(__name__)


def create_progress_tracking_tool(user_id: str):
    """
    Create get_workout_progress tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_workout_progress(
        period1_days: int = 30, period2_days: int = 60
    ) -> dict[str, Any]:
        """
        Compare workout metrics between two time periods to show progress.

        Compares recent period (period1) vs previous period (period2) to show if user is improving.

        Metrics compared:
        - Workout count
        - Average duration
        - Total duration
        - Average calories
        - Workout frequency (workouts per week)

        Use this when user asks:
        - "Am I getting stronger?"
        - "How's my progress?"
        - "Am I improving?"
        - "Have I been more active lately?"
        - "How do I compare to last month?"

        This tool performs the comparison for you - don't try to calculate manually!

        Args:
            period1_days: Recent period to analyze (default 30 = last month)
            period2_days: Total period including both recent and previous (default 60 = last 2 months)
                         Previous period is calculated as: period2_days - period1_days

        Returns:
            Dict with metrics for both periods and percentage changes
        """
        logger.info(
            f"🔧 get_workout_progress called with period1={period1_days}, period2={period2_days}, user_id={user_id}"
        )

        try:
            # Define time periods
            now = datetime.now(UTC)
            period1_start = now - timedelta(days=period1_days)
            period2_start = now - timedelta(days=period2_days)
            period1_end = now

            # Period 2 (previous) is the gap between period2_start and period1_start
            period2_end = period1_start

            # Fetch workouts for each period using centralized utility
            period1_workouts = fetch_workouts_in_range(
                user_id, period1_start, period1_end
            )
            period2_workouts = fetch_workouts_in_range(
                user_id, period2_start, period2_end
            )

            # Calculate metrics for each period
            def calc_metrics(workouts, period_days):
                if not workouts:
                    return {
                        "count": 0,
                        "total_duration": 0,
                        "avg_duration": 0,
                        "total_calories": 0,
                        "avg_calories": 0,
                        "workouts_per_week": 0,
                    }

                durations = [
                    w["duration_minutes"] for w in workouts if w.get("duration_minutes")
                ]
                calories = [w["calories"] for w in workouts if w.get("calories")]

                return {
                    "count": len(workouts),
                    "total_duration": round(sum(durations), 1) if durations else 0,
                    "avg_duration": round(mean(durations), 1) if durations else 0,
                    "total_calories": round(sum(calories), 1) if calories else 0,
                    "avg_calories": round(mean(calories), 1) if calories else 0,
                    "workouts_per_week": round(len(workouts) / (period_days / 7), 1),
                }

            metrics1 = calc_metrics(period1_workouts, period1_days)
            metrics2 = calc_metrics(period2_workouts, period2_days - period1_days)

            # Calculate percentage changes
            def calc_change(new, old):
                if old == 0:
                    return "N/A" if new == 0 else "+100%"
                change = round(((new - old) / old) * 100, 1)
                return f"+{change}%" if change > 0 else f"{change}%"

            # Determine overall trend
            def determine_trend():
                # Consider improving if either avg_duration OR frequency increased
                duration_improved = metrics1["avg_duration"] > metrics2["avg_duration"]
                frequency_improved = (
                    metrics1["workouts_per_week"] > metrics2["workouts_per_week"]
                )

                if duration_improved and frequency_improved:
                    return "strongly improving"
                elif duration_improved or frequency_improved:
                    return "improving"
                elif (
                    metrics1["avg_duration"] == metrics2["avg_duration"]
                    and metrics1["workouts_per_week"] == metrics2["workouts_per_week"]
                ):
                    return "maintaining"
                else:
                    return "declining"

            return {
                "period1": {
                    "name": f"Recent {period1_days} days",
                    "date_range": f"{period1_start.strftime('%Y-%m-%d')} to {period1_end.strftime('%Y-%m-%d')}",
                    **metrics1,
                },
                "period2": {
                    "name": f"Previous {period2_days - period1_days} days",
                    "date_range": f"{period2_start.strftime('%Y-%m-%d')} to {period2_end.strftime('%Y-%m-%d')}",
                    **metrics2,
                },
                "changes": {
                    "workout_count": calc_change(metrics1["count"], metrics2["count"]),
                    "avg_duration": calc_change(
                        metrics1["avg_duration"], metrics2["avg_duration"]
                    ),
                    "workouts_per_week": calc_change(
                        metrics1["workouts_per_week"], metrics2["workouts_per_week"]
                    ),
                    "total_duration": calc_change(
                        metrics1["total_duration"], metrics2["total_duration"]
                    ),
                },
                "trend": determine_trend(),
                "interpretation": {
                    "improving_if": "avg_duration or workouts_per_week increased",
                    "maintaining_if": "metrics stayed roughly the same",
                    "declining_if": "both avg_duration and frequency decreased",
                },
            }

        except Exception as e:
            logger.error(f"❌ Error in get_workout_progress: {str(e)}")
            return {"error": f"Failed to analyze progress: {str(e)}"}

    return get_workout_progress
