"""
Shared workout helper functions.

Common utilities for workout data processing across tools:
- Heart rate calculations (max HR, zones)
- Workout parsing and validation
- Date/time handling for workouts
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from .time_utils import parse_health_record_date

logger = logging.getLogger(__name__)

# Constants
CONSERVATIVE_MAX_HR = 190  # Age-independent maximum heart rate estimate


def calculate_max_hr(date_of_birth: str | None) -> int:
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


def get_heart_rate_during_workout(
    health_data: dict, workout_start_str: str, duration_minutes: float, user_max_hr: int
) -> dict[str, Any] | None:
    """
    Get heart rate statistics during a workout.

    Args:
        health_data: Full health data dict
        workout_start_str: Workout start time (ISO format)
        duration_minutes: Workout duration in minutes
        user_max_hr: User's maximum heart rate for zone calculation

    Returns:
        Dict with HR stats and zones, or None if no data
    """
    try:
        # Parse workout time window
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
                record_time = parse_health_record_date(record["date"])
                if workout_start <= record_time <= workout_end:
                    workout_hrs.append(float(record["value"]))
            except (ValueError, KeyError):
                continue

        if not workout_hrs:
            return None

        # Calculate statistics
        avg_hr = sum(workout_hrs) / len(workout_hrs)
        min_hr = min(workout_hrs)
        max_hr = max(workout_hrs)

        # Calculate heart rate zones (based on % of max HR)
        zones = {
            "zone1_easy": 0,  # 50-60%
            "zone2_moderate": 0,  # 60-70%
            "zone3_tempo": 0,  # 70-80%
            "zone4_threshold": 0,  # 80-90%
            "zone5_maximum": 0,  # 90-100%
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


def parse_workout_safe(
    workout: dict, cutoff_date: datetime, health_data: dict, user_max_hr: int
) -> dict[str, Any] | None:
    """
    Parse a single workout entry with validation and heart rate enrichment.

    Args:
        workout: Raw workout data dict
        cutoff_date: Only include workouts after this date
        health_data: Full health data for heart rate lookup
        user_max_hr: User's maximum heart rate for zone calculation

    Returns:
        Formatted workout info dict or None if parsing fails
    """
    start_date_str = workout.get("startDate", "")
    if not start_date_str:
        return None

    try:
        # Parse ISO datetime from workout data
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
        duration_min = workout.get("duration_minutes") or workout.get("duration", 0)

        # Get heart rate data during workout
        hr_data = None
        if duration_min and isinstance(duration_min, int | float) and duration_min > 0:
            hr_data = get_heart_rate_during_workout(
                health_data, start_date_str, duration_min, user_max_hr
            )

        day_of_week = workout_date.strftime("%A")

        # Basic workout info (always included)
        workout_info = {
            "date": workout_date.date().isoformat(),  # "2025-10-17"
            "datetime": workout_date.isoformat(),  # "2025-10-17T16:59:18+00:00"
            "day_of_week": day_of_week,
            "type": workout_type,
            "duration_minutes": round(float(duration_min), 1) if duration_min else 0,
            "energy_burned": workout.get("calories")
            or workout.get("totalEnergyBurned", 0),
        }

        # Add heart rate data if available
        if hr_data:
            workout_info.update(hr_data)

        return workout_info

    except Exception as e:
        logger.debug(f"Skipping workout due to parsing error: {type(e).__name__}: {e}")
        return None
