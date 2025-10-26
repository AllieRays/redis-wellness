"""
Workout Progress Tool - Get workout progress comparison between periods.

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

from ...utils.exceptions import ToolExecutionError
from ...utils.workout_fetchers import fetch_workouts_in_range

logger = logging.getLogger(__name__)


def create_get_workout_progress_tool(user_id: str):
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
        Compare workout metrics between recent and previous periods to track progress.

        USE WHEN user asks:
        - "Am I getting stronger?"
        - "How's my progress?"
        - "Am I improving?"
        - "Have I been more active lately?"
        - "How do I compare to last month?"

        DO NOT USE for:
        - Day-of-week patterns → use get_workout_patterns instead
        - Single period stats → use get_workouts instead

        Args:
            period1_days: Recent period in days (default: 30 = last month)
            period2_days: Total period including both (default: 60 = last 2 months)
                Previous period = period2_days - period1_days

        Returns:
            Dict with:
            - period1: Recent metrics (count, avg_duration, workouts_per_week)
            - period2: Previous metrics
            - changes: Percent changes for all metrics
            - trend: "improving", "maintaining", or "declining"

        Examples:
            Query: "Am I improving?"
            Call: get_workout_progress()
            Returns: {"trend": "improving", "changes": {"+15%" duration, "+20%" frequency}}

            Query: "Progress over last 3 months"
            Call: get_workout_progress(period1_days=45, period2_days=90)
            Returns: Comparison of last 45 days vs previous 45 days
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
            logger.error(
                f"❌ Error in get_workout_progress: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise ToolExecutionError("get_workout_progress", str(e)) from e

    return get_workout_progress
