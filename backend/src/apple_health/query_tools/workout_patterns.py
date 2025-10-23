"""
Workout Pattern Analysis Tools - Dynamic analysis of workout schedules and intensity.

These tools analyze workout data from Redis to answer pattern questions like:
- "What days do I work out?"
- "What day do I work out harder?"
- "How consistent am I?"

The tools perform data analysis so Qwen doesn't have to count or calculate patterns.
"""

import logging
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from langchain_core.tools import tool

from ...utils.workout_fetchers import fetch_recent_workouts

logger = logging.getLogger(__name__)


def create_workout_schedule_tool(user_id: str):
    """
    Create get_workout_schedule_analysis tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_workout_schedule_analysis(days_back: int = 210) -> dict[str, Any]:
        """
        Analyze workout schedule patterns from actual data.

        Returns comprehensive schedule analysis:
        - Which days user actually works out (by frequency)
        - Workout consistency metrics
        - Weekly averages
        - Regular days (days appearing in >40% of weeks)

        Use this when user asks:
        - "What days do I work out?"
        - "How often do I exercise?"
        - "What's my workout schedule?"
        - "Am I consistent with workouts?"

        This tool analyzes the data for you - don't try to count manually!

        IMPORTANT: Use the default days_back (210 days = 7 months) unless the user explicitly
        requests a different timeframe. The default covers the full data retention period.

        Args:
            days_back: How many days back to analyze (default 210 = 7 months).
                      DO NOT override unless user explicitly specifies a different timeframe.

        Returns:
            Dict with schedule analysis including day frequency and consistency
        """
        logger.info(
            f"🔧 get_workout_schedule_analysis called with days_back={days_back}, user_id={user_id}"
        )

        try:
            # Fetch workouts using centralized utility
            recent_workouts = fetch_recent_workouts(user_id, days=days_back)

            if not recent_workouts:
                return {
                    "period": f"last {days_back} days",
                    "total_workouts": 0,
                    "message": "No workouts found in this period",
                }

            # Count by day_of_week (uses enriched field)
            day_counts = Counter([w["day_of_week"] for w in recent_workouts])

            # Calculate consistency (appeared in X% of weeks)
            weeks = days_back / 7
            regular_threshold = weeks * 0.4  # 40% of weeks = "regular"

            # Sort days by count (descending)
            sorted_days = day_counts.most_common()

            # Determine regular days
            regular_days = [
                day for day, count in day_counts.items() if count >= regular_threshold
            ]

            return {
                "period": f"last {days_back} days",
                "total_workouts": len(recent_workouts),
                "workouts_per_week_avg": round(len(recent_workouts) / weeks, 1),
                "day_frequency": dict(sorted_days),
                "regular_days": regular_days,
                "most_common_day": sorted_days[0] if sorted_days else None,
                "analysis": {
                    "weeks_analyzed": round(weeks, 1),
                    "consistency_threshold": f"{int(regular_threshold)} workouts = regular day",
                    "unique_days_used": len(day_counts),
                },
            }

        except Exception as e:
            logger.error(f"❌ Error in get_workout_schedule_analysis: {str(e)}")
            return {"error": f"Failed to analyze schedule: {str(e)}"}

    return get_workout_schedule_analysis


def create_intensity_analysis_tool(user_id: str):
    """
    Create analyze_workout_intensity_by_day tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def analyze_workout_intensity_by_day(days_back: int = 210) -> dict[str, Any]:
        """
        Compare workout intensity across different days of the week.

        Returns average duration and calories burned per day, sorted by intensity.

        Use this when user asks:
        - "What day do I work out harder?"
        - "Which day has my longest workouts?"
        - "When do I push myself the most?"
        - "What's my hardest workout day?"

        This tool analyzes the data for you - don't try to calculate manually!

        IMPORTANT: Use the default days_back (210 days = 7 months) unless the user explicitly
        requests a different timeframe. The default covers the full data retention period.

        Args:
            days_back: How many days back to analyze (default 210 = 7 months).
                      DO NOT override unless user explicitly specifies a different timeframe.

        Returns:
            Dict with intensity analysis by day of week
        """
        logger.info(
            f"🔧 analyze_workout_intensity_by_day called with days_back={days_back}, user_id={user_id}"
        )

        try:
            # Fetch workouts using centralized utility
            recent_workouts = fetch_recent_workouts(user_id, days=days_back)

            if not recent_workouts:
                return {
                    "period": f"last {days_back} days",
                    "message": "No workouts found in this period",
                }

            # Group by day_of_week
            by_day = defaultdict(list)
            for w in recent_workouts:
                by_day[w["day_of_week"]].append(w)

            # Calculate averages per day
            intensity = {}
            for day, day_workouts in by_day.items():
                durations = [
                    w["duration_minutes"]
                    for w in day_workouts
                    if w.get("duration_minutes")
                ]
                calories = [w["calories"] for w in day_workouts if w.get("calories")]

                intensity[day] = {
                    "count": len(day_workouts),
                    "avg_duration_minutes": (
                        round(mean(durations), 1) if durations else 0
                    ),
                    "avg_calories": round(mean(calories), 1) if calories else 0,
                    "total_duration_minutes": (
                        round(sum(durations), 1) if durations else 0
                    ),
                }

            # Sort by intensity (total duration is best proxy)
            sorted_days = sorted(
                intensity.items(),
                key=lambda x: x[1]["total_duration_minutes"],
                reverse=True,
            )

            return {
                "period": f"last {days_back} days",
                "intensity_by_day": dict(sorted_days),
                "hardest_day": sorted_days[0][0] if sorted_days else None,
                "easiest_day": sorted_days[-1][0] if sorted_days else None,
                "analysis": {
                    "ranking": [day for day, _ in sorted_days],
                    "metric_used": "total_duration_minutes (best intensity proxy)",
                },
            }

        except Exception as e:
            logger.error(f"❌ Error in analyze_workout_intensity_by_day: {str(e)}")
            return {"error": f"Failed to analyze intensity: {str(e)}"}

    return analyze_workout_intensity_by_day
