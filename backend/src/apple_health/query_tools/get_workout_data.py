"""
Consolidated Workout Data Tool - ONE tool for ALL workout queries.

This tool handles:
- Listing workouts ("show my recent workouts")
- Patterns ("what days do I work out")
- Progress ("am I improving")
- Comparisons ("how do I compare to last month")

The tool does the heavy lifting so the LLM just needs to ask for workout data.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.time_utils import parse_health_record_date

logger = logging.getLogger(__name__)

# Constants
CONSERVATIVE_MAX_HR = 190
DEFAULT_DAYS_BACK = 30


def _calculate_max_hr(date_of_birth: str | None) -> int:
    """Calculate age-based maximum heart rate."""
    if date_of_birth:
        try:
            from datetime import date

            dob = date.fromisoformat(date_of_birth)
            today = date.today()
            age = (
                today.year
                - dob.year
                - ((today.month, today.day) < (dob.month, dob.day))
            )
            if 18 <= age <= 100:
                return 220 - age
        except (ValueError, TypeError):
            pass
    return CONSERVATIVE_MAX_HR


def _get_heart_rate_during_workout(
    health_data: dict, workout_start_str: str, duration_minutes: float, user_max_hr: int
) -> dict[str, Any] | None:
    """Get heart rate statistics during a workout."""
    try:
        workout_start = datetime.fromisoformat(workout_start_str.replace("Z", "+00:00"))
        workout_end = workout_start + timedelta(minutes=duration_minutes)

        hr_records = health_data.get("metrics_records", {}).get("HeartRate", [])
        if not hr_records:
            return None

        workout_hrs = []
        for record in hr_records:
            try:
                record_time = parse_health_record_date(record["date"])
                if workout_start <= record_time <= workout_end:
                    workout_hrs.append(float(record["value"]))
            except (ValueError, KeyError):
                continue

        if not workout_hrs:
            return None

        avg_hr = sum(workout_hrs) / len(workout_hrs)
        min_hr = min(workout_hrs)
        max_hr = max(workout_hrs)

        # Calculate heart rate zones
        zones = {
            "zone1_easy": 0,
            "zone2_moderate": 0,
            "zone3_tempo": 0,
            "zone4_threshold": 0,
            "zone5_maximum": 0,
        }

        for hr in workout_hrs:
            hr_percent = (hr / user_max_hr) * 100
            if hr_percent < 60:
                zones["zone1_easy"] += 1
            elif hr_percent < 70:
                zones["zone2_moderate"] += 1
            elif hr_percent < 80:
                zones["zone3_tempo"] += 1
            elif hr_percent < 90:
                zones["zone4_threshold"] += 1
            else:
                zones["zone5_maximum"] += 1

        dominant_zone = max(zones.items(), key=lambda x: x[1])[0]
        zone_names = {
            "zone1_easy": "Easy (50-60% max HR)",
            "zone2_moderate": "Moderate (60-70% max HR)",
            "zone3_tempo": "Tempo (70-80% max HR)",
            "zone4_threshold": "Threshold (80-90% max HR)",
            "zone5_maximum": "Maximum (90-100% max HR)",
        }

        return {
            "heart_rate_avg": f"{round(avg_hr)} bpm",
            "heart_rate_min": f"{round(min_hr)} bpm",
            "heart_rate_max": f"{round(max_hr)} bpm",
            "heart_rate_samples": len(workout_hrs),
            "heart_rate_zone": zone_names[dominant_zone],
        }
    except Exception as e:
        logger.debug(f"Failed to get heart rate data: {type(e).__name__}: {e}")
        return None


def _parse_workout(
    workout: dict, cutoff_date: datetime, health_data: dict, user_max_hr: int
) -> dict[str, Any] | None:
    """Parse a single workout entry."""
    start_date_str = workout.get("startDate", "")
    if not start_date_str:
        return None

    try:
        workout_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        if workout_date.tzinfo is None:
            workout_date = workout_date.replace(tzinfo=UTC)

        if workout_date < cutoff_date:
            return None

        workout_type = workout.get("type", "Unknown").replace(
            "HKWorkoutActivityType", ""
        )
        duration_min = workout.get("duration_minutes") or workout.get("duration", 0)

        hr_data = None
        if duration_min and isinstance(duration_min, int | float) and duration_min > 0:
            hr_data = _get_heart_rate_during_workout(
                health_data, start_date_str, duration_min, user_max_hr
            )

        day_of_week = workout_date.strftime("%A")

        workout_info = {
            "date": workout_date.date().isoformat(),
            "datetime": workout_date.isoformat(),
            "day_of_week": day_of_week,
            "type": workout_type,
            "duration_minutes": round(float(duration_min), 1) if duration_min else 0,
            "energy_burned": workout.get("calories")
            or workout.get("totalEnergyBurned", 0),
        }

        if hr_data:
            workout_info.update(hr_data)

        return workout_info

    except Exception as e:
        logger.debug(f"Skipping workout due to parsing error: {type(e).__name__}: {e}")
        return None


def _analyze_patterns(workouts: list[dict]) -> dict[str, Any]:
    """Analyze workout patterns by day of week."""
    if not workouts:
        return {"error": "No workouts to analyze"}

    # Group by day of week
    by_day = {}
    for workout in workouts:
        day = workout["day_of_week"]
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(workout)

    # Calculate stats per day
    day_stats = {}
    for day, day_workouts in by_day.items():
        day_stats[day] = {
            "count": len(day_workouts),
            "avg_duration": round(
                mean([w["duration_minutes"] for w in day_workouts]), 1
            ),
            "types": list({w["type"] for w in day_workouts}),
        }

    # Find most common day
    most_common_day = max(by_day.items(), key=lambda x: len(x[1]))[0]

    return {
        "by_day": day_stats,
        "most_common_day": most_common_day,
        "days_active": len(by_day),
        "summary": f"You typically work out on {most_common_day}s ({len(by_day[most_common_day])} times). Active {len(by_day)} days per week.",
    }


def _analyze_progress(
    workouts: list[dict], period1_days: int, period2_days: int
) -> dict[str, Any]:
    """Compare recent period vs previous period."""
    if not workouts:
        return {"error": "No workouts for progress analysis"}

    now = datetime.now(UTC)
    period1_start = now - timedelta(days=period1_days)
    period2_start = now - timedelta(days=period2_days)

    # Split workouts into two periods
    period1_workouts = []
    period2_workouts = []

    for workout in workouts:
        workout_dt = datetime.fromisoformat(workout["datetime"])
        if workout_dt >= period1_start:
            period1_workouts.append(workout)
        elif workout_dt >= period2_start:
            period2_workouts.append(workout)

    if not period1_workouts or not period2_workouts:
        return {"error": "Not enough data for comparison"}

    # Calculate metrics for each period
    def calc_metrics(ws, days):
        return {
            "count": len(ws),
            "avg_duration": round(mean([w["duration_minutes"] for w in ws]), 1),
            "workouts_per_week": round(len(ws) / (days / 7), 1),
        }

    recent = calc_metrics(period1_workouts, period1_days)
    previous = calc_metrics(period2_workouts, period2_days - period1_days)

    # Calculate changes
    changes = {}
    for key in ["count", "avg_duration", "workouts_per_week"]:
        if previous[key] > 0:
            pct_change = ((recent[key] - previous[key]) / previous[key]) * 100
            changes[key] = f"{pct_change:+.0f}%"
        else:
            changes[key] = "N/A"

    # Determine trend
    improving_count = sum(1 for v in changes.values() if v.startswith("+"))
    if improving_count >= 2:
        trend = "improving"
    elif improving_count == 0:
        trend = "declining"
    else:
        trend = "maintaining"

    return {
        "recent_period": recent,
        "previous_period": previous,
        "changes": changes,
        "trend": trend,
        "summary": f"You're {trend}! Frequency {changes['workouts_per_week']}, duration {changes['avg_duration']}.",
    }


def create_get_workout_data_tool(user_id: str):
    """Create the consolidated workout data tool."""

    @tool
    def get_workout_data(
        days_back: int = DEFAULT_DAYS_BACK,
        include_patterns: bool = False,
        include_progress: bool = False,
    ) -> dict[str, Any]:
        """
        Get comprehensive workout data - ONE tool for ALL workout questions.

        This tool handles EVERYTHING about workouts:
        - "Tell me about my recent workouts" → Returns workout list
        - "What days do I work out?" → Returns patterns (sets include_patterns=True automatically)
        - "Am I improving?" → Returns progress comparison (sets include_progress=True automatically)

        ⚠️ THIS IS THE ONLY WORKOUT TOOL - use it for ALL workout queries!

        Args:
            days_back: How many days back to search (default: 30)
                      - For "recent workouts" use default (30)
                      - For specific dates like "October 17" use 90+
                      - For "this week" use 7
            include_patterns: Set to True if user asks about patterns, days, or schedule
            include_progress: Set to True if user asks about improvement, progress, or trends

        Returns:
            Dict with:
            - workouts: List of workouts (always included)
            - total_workouts: Count
            - last_workout: Time since last workout
            - patterns: Day-of-week analysis (if include_patterns=True)
            - progress: Recent vs previous comparison (if include_progress=True)

        Examples:
            "Tell me about my recent workouts" → get_workout_data()
            "What days do I work out?" → get_workout_data(include_patterns=True)
            "Am I getting stronger?" → get_workout_data(include_progress=True)
            "Show all my workout info" → get_workout_data(include_patterns=True, include_progress=True)
        """
        logger.info(
            f"🔧 get_workout_data: days_back={days_back}, patterns={include_patterns}, progress={include_progress}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found", "workouts": []}

                health_data = json.loads(health_data_json)

                # Get user max HR
                user_profile = health_data.get("user_profile", {})
                date_of_birth = user_profile.get("date_of_birth")
                user_max_hr = _calculate_max_hr(date_of_birth)

                # Get workouts
                all_workouts = health_data.get("workouts", [])
                logger.info(f"📊 Found {len(all_workouts)} total workouts")

                # Filter by date range
                cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
                recent_workouts = []

                for workout in all_workouts:
                    workout_info = _parse_workout(
                        workout, cutoff_date, health_data, user_max_hr
                    )
                    if workout_info:
                        recent_workouts.append(workout_info)

                # Sort by date (most recent first)
                recent_workouts.sort(key=lambda x: x["datetime"], reverse=True)
                logger.info(
                    f"✅ Filtered to {len(recent_workouts)} workouts (last {days_back} days)"
                )

                # Build response
                result = {
                    "workouts": recent_workouts,
                    "total_workouts": len(recent_workouts),
                    "days_searched": days_back,
                }

                # Calculate time since last workout
                if recent_workouts:
                    last_workout_dt = datetime.fromisoformat(
                        recent_workouts[0]["datetime"]
                    )
                    days_ago = (datetime.now(UTC).date() - last_workout_dt.date()).days
                    result["last_workout"] = (
                        f"{days_ago} days ago" if days_ago > 0 else "today"
                    )
                else:
                    result["last_workout"] = "no workouts found"

                # Add patterns if requested
                if include_patterns:
                    logger.info("📊 Including pattern analysis")
                    result["patterns"] = _analyze_patterns(recent_workouts)

                # Add progress if requested
                if include_progress:
                    logger.info("📈 Including progress analysis")
                    # Use half of days_back as the comparison period
                    result["progress"] = _analyze_progress(
                        recent_workouts,
                        period1_days=days_back // 2,
                        period2_days=days_back,
                    )

                result["summary"] = (
                    f"Found {len(recent_workouts)} workouts in the last {days_back} days. Last workout was {result['last_workout']}."
                )

                return result

        except Exception as e:
            logger.error(
                f"❌ Error in get_workout_data: {type(e).__name__}: {e}", exc_info=True
            )
            return {
                "error": f"Failed to get workout data: {str(e)}",
                "error_type": type(e).__name__,
                "workouts": [],
            }

    return get_workout_data
