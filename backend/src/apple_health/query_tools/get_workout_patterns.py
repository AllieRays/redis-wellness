"""
Workout Pattern Analysis Tool - Get workout patterns by day of week.

Combines schedule analysis (frequency, consistency) and intensity analysis
(duration, calories by day) into a single tool.
"""

import logging
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from langchain_core.tools import tool

from ...utils.exceptions import ToolExecutionError
from ...utils.workout_fetchers import fetch_recent_workouts

logger = logging.getLogger(__name__)

# Constants
REGULAR_DAY_THRESHOLD = 0.4  # 40% of weeks = regular attendance


def create_get_workout_patterns_tool(user_id: str):
    """
    Create get_workout_patterns tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_workout_patterns(
        analysis_type: str = "schedule",
        days_back: int = 210,
    ) -> dict[str, Any]:
        """
        Get workout patterns by day of week (schedule frequency OR intensity comparison).

        USE WHEN user asks:
        - "What days do I usually work out?" (schedule)
        - "Am I consistent with workouts?" (schedule)
        - "What day do I work out harder?" (intensity)
        - "Which day has my longest workouts?" (intensity)
        - "How many times per week do I work out?" (schedule)

        DO NOT USE for:
        - Recent workout details → use get_workouts instead
        - Specific workout dates/times → use get_workouts instead
        - Workout progress tracking → use get_workout_progress instead

        Args:
            analysis_type: Type of pattern analysis (default: "schedule")
                Options: "schedule", "intensity"
            days_back: Days to analyze (default: 210 = 7 months)
                DO NOT override unless user explicitly requests different timeframe

        Returns:
            Dict with:
            - For "schedule": day_frequency, regular_days, most_common_day, workouts_per_week_avg, consistency_pct
            - For "intensity": intensity_by_day, hardest_day, easiest_day, day_ranking, intensity_difference_pct

        Examples:
            Query: "What days do I usually work out?"
            Call: get_workout_patterns(analysis_type="schedule")
            Returns: {
                "most_common_day": "Monday",
                "most_common_day_consistency_pct": 75.0,
                "workouts_per_week_avg": 2.5,
                "day_frequency": {"Monday": 25, "Wednesday": 22},
                "regular_days": ["Monday", "Wednesday"]
            }

            Query: "What day do I work out harder?"
            Call: get_workout_patterns(analysis_type="intensity")
            Returns: {
                "hardest_day": "Monday",
                "easiest_day": "Friday",
                "intensity_difference_pct": 45.2,
                "day_ranking": ["Monday", "Wednesday", "Friday"],
                "intensity_by_day": {
                    "Monday": {"workout_count": 10, "avg_duration_minutes": 52.3, "avg_calories": 420},
                    "Friday": {"workout_count": 5, "avg_duration_minutes": 36.0, "avg_calories": 280}
                }
            }
        """
        logger.info(
            f"🔧 get_workout_patterns called: analysis_type='{analysis_type}', "
            f"days_back={days_back}, user_id={user_id}"
        )

        try:
            # Fetch workouts using centralized utility
            recent_workouts = fetch_recent_workouts(user_id, days=days_back)

            logger.info(
                f"📊 fetch_recent_workouts returned {len(recent_workouts)} workouts"
            )

            if not recent_workouts:
                logger.warning(f"⚠️ No workouts found for last {days_back} days!")
                return {
                    "period": f"last {days_back} days",
                    "total_workouts": 0,
                    "message": "No workouts found in this period",
                }

            # Branch based on analysis type
            if analysis_type == "schedule":
                return _analyze_schedule(recent_workouts, days_back)
            elif analysis_type == "intensity":
                return _analyze_intensity(recent_workouts, days_back)
            else:
                raise ValueError(
                    f"Invalid analysis_type: {analysis_type}. Must be 'schedule' or 'intensity'"
                )

        except Exception as e:
            logger.error(
                f"❌ Error in get_workout_patterns: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise ToolExecutionError("get_workout_patterns", str(e)) from e

    return get_workout_patterns


def _analyze_schedule(recent_workouts: list, days_back: int) -> dict[str, Any]:
    """Analyze workout schedule frequency and consistency."""
    # Count by day_of_week
    day_counts = Counter([w["day_of_week"] for w in recent_workouts])

    # Calculate consistency (appeared in X% of weeks)
    weeks = days_back / 7
    regular_threshold = weeks * REGULAR_DAY_THRESHOLD

    # Sort days by count (descending)
    sorted_days = day_counts.most_common()

    # Determine regular days
    regular_days = [
        day for day, count in day_counts.items() if count >= regular_threshold
    ]

    # Calculate consistency percentage for top day
    consistency_pct = None
    if sorted_days:
        consistency_pct = round((sorted_days[0][1] / weeks) * 100, 1)

    return {
        "period": f"last {days_back} days",
        "total_workouts": len(recent_workouts),
        "workouts_per_week_avg": round(len(recent_workouts) / weeks, 1),
        "day_frequency": dict(sorted_days),
        "regular_days": regular_days,
        "most_common_day": sorted_days[0][0] if sorted_days else None,
        "most_common_day_consistency_pct": consistency_pct,
        "analysis_type": "schedule",
    }


def _analyze_intensity(recent_workouts: list, days_back: int) -> dict[str, Any]:
    """Analyze workout intensity by day of week."""
    # Group by day_of_week
    by_day = defaultdict(list)
    for w in recent_workouts:
        by_day[w["day_of_week"]].append(w)

    # Calculate averages per day
    intensity = {}
    for day, day_workouts in by_day.items():
        durations = [
            w["duration_minutes"] for w in day_workouts if w.get("duration_minutes")
        ]
        calories = [w["calories"] for w in day_workouts if w.get("calories")]

        # Primary metric: avg duration (most reliable intensity indicator)
        avg_duration = round(mean(durations), 1) if durations else 0
        avg_calories = round(mean(calories), 1) if calories else 0

        intensity[day] = {
            "workout_count": len(day_workouts),
            "avg_duration_minutes": avg_duration,
            "avg_calories": avg_calories,
        }

    # Sort by avg duration (better than total for intensity comparison)
    sorted_days = sorted(
        intensity.items(),
        key=lambda x: x[1]["avg_duration_minutes"],
        reverse=True,
    )

    # Calculate relative intensity (% difference from easiest day)
    hardest_day_data = sorted_days[0][1] if sorted_days else None
    easiest_day_data = sorted_days[-1][1] if sorted_days else None
    intensity_difference_pct = None

    if (
        hardest_day_data
        and easiest_day_data
        and easiest_day_data["avg_duration_minutes"] > 0
    ):
        intensity_difference_pct = round(
            (
                (
                    hardest_day_data["avg_duration_minutes"]
                    - easiest_day_data["avg_duration_minutes"]
                )
                / easiest_day_data["avg_duration_minutes"]
            )
            * 100,
            1,
        )

    return {
        "period": f"last {days_back} days",
        "intensity_by_day": dict(sorted_days),
        "hardest_day": sorted_days[0][0] if sorted_days else None,
        "easiest_day": sorted_days[-1][0] if sorted_days else None,
        "intensity_difference_pct": intensity_difference_pct,
        "day_ranking": [day for day, _ in sorted_days],
        "analysis_type": "intensity",
    }
