"""
Workout Tool - Get workout details with heart rate zones.

Provides the get_workouts tool which returns comprehensive
workout information including heart rate zones and day_of_week tracking.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.time_utils import parse_health_record_date as _parse_health_record_date

logger = logging.getLogger(__name__)

# Constants for heart rate zone calculations
CONSERVATIVE_MAX_HR = 190  # Age-independent maximum heart rate estimate (fallback)
DEFAULT_WORKOUT_SEARCH_DAYS = 30  # Default days to search for workouts


def _calculate_max_hr(date_of_birth: str | None) -> int:
    """
    Calculate age-based maximum heart rate using standard formula.

    Uses 220 - age formula when date of birth is available,
    falls back to conservative estimate of 190 otherwise.

    Args:
        date_of_birth: ISO date string (YYYY-MM-DD) or None

    Returns:
        Estimated maximum heart rate in bpm
    """
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

            # Standard formula: 220 - age
            if 18 <= age <= 100:  # Reasonable age range
                return 220 - age
        except (ValueError, TypeError):
            pass

    # Fallback to conservative estimate
    return CONSERVATIVE_MAX_HR


def _get_heart_rate_during_workout(
    health_data: dict, workout_start_str: str, duration_minutes: float, user_max_hr: int
) -> dict[str, Any] | None:
    """
    Get heart rate statistics during a workout.

    Args:
        health_data: Full health data dict
        workout_start_str: Workout start time (ISO format)
        duration_minutes: Workout duration in minutes

    Returns:
        Dict with HR stats or None if no data
    """
    try:
        # Parse workout time window (workouts use ISO format from .isoformat())
        # Note: Workouts are stored in ISO format, not health record format
        workout_start = datetime.fromisoformat(workout_start_str.replace("Z", "+00:00"))
        workout_end = workout_start + timedelta(minutes=duration_minutes)

        # Get heart rate records
        hr_records = health_data.get("metrics_records", {}).get("HeartRate", [])
        if not hr_records:
            return None

        # Find HR readings during workout
        workout_hrs = []
        for record in hr_records:
            try:
                # Use centralized date parsing utility
                record_time = _parse_health_record_date(record["date"])

                if workout_start <= record_time <= workout_end:
                    hr_value = float(record["value"])
                    workout_hrs.append(hr_value)
            except (ValueError, KeyError):
                continue

        if not workout_hrs:
            return None

        # Calculate statistics
        avg_hr = sum(workout_hrs) / len(workout_hrs)
        min_hr = min(workout_hrs)
        max_hr = max(workout_hrs)

        # Calculate heart rate zones (based on % of max HR)
        max_hr_estimate = user_max_hr

        zones = {
            "zone1_easy": 0,  # 50-60% (95-114 bpm)
            "zone2_moderate": 0,  # 60-70% (114-133 bpm)
            "zone3_tempo": 0,  # 70-80% (133-152 bpm)
            "zone4_threshold": 0,  # 80-90% (152-171 bpm)
            "zone5_maximum": 0,  # 90-100% (171-190 bpm)
        }

        for hr in workout_hrs:
            hr_percent = (hr / max_hr_estimate) * 100
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

        # Find dominant zone
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
            "heart_rate_zone_distribution": {
                k.replace("_", " ").title(): v for k, v in zones.items() if v > 0
            },
        }
    except Exception as e:
        logger.debug(
            f"Failed to get heart rate data for workout: {type(e).__name__}: {e}"
        )
        return None


def _parse_workout_entry(
    workout: dict[str, Any],
    cutoff_date: datetime,
    health_data: dict[str, Any],
    user_max_hr: int,
) -> dict[str, Any] | None:
    """
    Parse a single workout entry from health data.

    Args:
        workout: Raw workout data dict
        cutoff_date: Only include workouts after this date
        health_data: Full health data for heart rate lookup

    Returns:
        Formatted workout info dict or None if parsing fails
    """
    # IMPORTANT: Use 'startDate' (full datetime) not 'date' (date string only)
    start_date_str = workout.get("startDate", "")
    if not start_date_str:
        return None

    try:
        # Parse ISO datetime from workout data (stored with .isoformat())
        workout_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))

        # If naive datetime, assume UTC
        if workout_date.tzinfo is None:
            workout_date = workout_date.replace(tzinfo=UTC)

        if workout_date < cutoff_date:
            return None

        # Format workout info
        workout_type = workout.get("type", "Unknown").replace(
            "HKWorkoutActivityType", ""
        )

        # Support both duration_minutes and duration (both in minutes)
        # NOTE: Apple Health XML stores duration in minutes, not seconds
        # Use explicit None check to handle 0-duration workouts correctly
        duration_min = workout.get("duration_minutes")
        if duration_min is None:
            duration_min = workout.get("duration", 0)

        # Validate duration before using in timedelta
        if duration_min and isinstance(duration_min, int | float) and duration_min > 0:
            # Get heart rate data during workout
            hr_data = _get_heart_rate_during_workout(
                health_data, start_date_str, duration_min, user_max_hr
            )
        else:
            hr_data = None
            if duration_min is None or duration_min < 0:
                logger.debug(
                    f"Invalid duration for workout on {start_date_str}: {duration_min}"
                )
                duration_min = 0

        # Format workout info (UTC, frontend handles timezone)
        day_of_week = workout_date.strftime("%A")

        # Basic workout info (always included)
        workout_info = {
            "date": workout_date.date().isoformat(),  # "2025-10-17"
            "datetime": workout_date.isoformat(),  # "2025-10-17T16:59:18+00:00"
            "day_of_week": day_of_week,
            "type": workout_type,
            "duration_minutes": (round(float(duration_min), 1) if duration_min else 0),
        }

        # Always include detailed info (calories, heart rate)
        # Use explicit None check to handle 0-calorie workouts correctly
        calories = workout.get("calories")
        if calories is None:
            calories = workout.get("totalEnergyBurned", 0)
        workout_info["energy_burned"] = calories

        # Add heart rate data if available
        if hr_data:
            workout_info.update(hr_data)

        return workout_info

    except Exception as e:
        logger.debug(f"Skipping workout due to parsing error: {type(e).__name__}: {e}")
        return None


def create_get_workouts_tool(user_id: str):
    """
    Create get_workouts tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def get_workouts(
        days_back: int = DEFAULT_WORKOUT_SEARCH_DAYS,
    ) -> dict[str, Any]:
        """
        Get workout details with heart rate zones and comprehensive metrics.

        USE WHEN user asks:
        - "Did I work out on October 17th?"
        - "When did I last work out?"
        - "Show me my recent workouts"
        - "What was my heart rate during workouts?"
        - "Show my workout history"

        DO NOT USE for:
        - Workout patterns by day → use get_workout_patterns instead
        - Progress tracking → use get_workout_progress instead

        Args:
            days_back: Days to search back (default: 90)
                      IMPORTANT: For specific dates like "October 17th", ALWAYS use default (90) or higher!
                      Only use days_back=1 if user explicitly says "today" or "in the past day".
                      For "recent" or "last week", use 7-30 days.

        Returns:
            Dict with:
            - workouts: List of workouts (sorted most recent first)
            - total_workouts: Count of workouts found
            - last_workout: Human-readable time since last workout

        Each workout includes:
        - date: "2025-10-22" (YYYY-MM-DD)
        - day_of_week: "Friday" (pre-calculated, use this!)
        - type: Workout type
        - duration_minutes: Duration
        - energy_burned: Calories
        - heart_rate_avg, heart_rate_min, heart_rate_max: HR stats (if available)
        - heart_rate_zone: Dominant zone (if available)

        Examples:
            Query: "Show me my recent workouts"
            Call: get_workouts()
            Returns: List of last 30 days of workouts with full details

            Query: "Did I work out last week?"
            Call: get_workouts(days_back=7)
            Returns: Workouts from last 7 days
        """
        logger.info(
            f"🔧 get_workouts called with days_back={days_back}, user_id={user_id}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found", "workouts": []}

                health_data = json.loads(health_data_json)

                # Calculate user-specific max HR from date of birth
                user_profile = health_data.get("user_profile", {})
                date_of_birth = user_profile.get("date_of_birth")
                user_max_hr = _calculate_max_hr(date_of_birth)
                logger.debug(
                    f"Using max HR {user_max_hr} bpm for user (age-based: {date_of_birth is not None})"
                )

                # Get actual workout records
                all_workouts = health_data.get("workouts", [])
                logger.info(
                    f"📊 Found {len(all_workouts)} total workouts in health data"
                )

                # Filter workouts by date range
                cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
                recent_workouts = []

                for workout in all_workouts:
                    workout_info = _parse_workout_entry(
                        workout, cutoff_date, health_data, user_max_hr
                    )
                    if workout_info:
                        recent_workouts.append(workout_info)

                # Sort by datetime (most recent first)
                recent_workouts.sort(key=lambda x: x["datetime"], reverse=True)
                logger.info(
                    f"✅ Filtered to {len(recent_workouts)} recent workouts (last {days_back} days)"
                )

                # Calculate time since last workout
                if recent_workouts:
                    try:
                        # Use datetime field to avoid re-parsing
                        last_workout_datetime = datetime.fromisoformat(
                            recent_workouts[0]["datetime"]
                        )
                        now = datetime.now(UTC)
                        days_ago = (now.date() - last_workout_datetime.date()).days
                        time_ago = f"{days_ago} days ago" if days_ago > 0 else "today"
                    except Exception as e:
                        logger.debug(
                            f"Failed to calculate time since last workout: {type(e).__name__}: {e}"
                        )
                        time_ago = "unknown"
                else:
                    time_ago = "no workouts found"

                result = {
                    "workouts": recent_workouts,
                    "total_workouts": len(recent_workouts),
                    "last_workout": time_ago,
                    "days_searched": days_back,
                    "summary": f"Found {len(recent_workouts)} workouts in the last {days_back} days. Last workout was {time_ago}.",
                }

                logger.info(f"📤 Returning: {result['summary']}")
                # Debug: Log first workout to verify data structure
                if recent_workouts:
                    logger.info(f"🔍 First workout sample: {recent_workouts[0]}")
                else:
                    logger.warning("⚠️ recent_workouts list is empty despite count!")
                return result

        except Exception as e:
            logger.error(
                f"❌ Error in get_workouts: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {
                "error": f"Failed to search workouts: {str(e)}",
                "error_type": type(e).__name__,
                "workouts": [],
            }

    return get_workouts
