"""
Workout Search Tool - LangChain tool for querying workout and activity data.

Provides the search_workouts_and_activity tool which returns comprehensive
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
CONSERVATIVE_MAX_HR = 190  # Age-independent maximum heart rate estimate
DEFAULT_WORKOUT_SEARCH_DAYS = 7  # Default days to search for workouts
EXTENDED_WORKOUT_SEARCH_DAYS = 30  # Extended search for "last workout" queries


def _get_heart_rate_during_workout(
    health_data: dict, workout_start_str: str, duration_minutes: float
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
        max_hr_estimate = CONSERVATIVE_MAX_HR

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
    except Exception:
        return None


def create_search_workouts_tool(user_id: str):
    """
    Create search_workouts_and_activity tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def search_workouts_and_activity(
        days_back: int = DEFAULT_WORKOUT_SEARCH_DAYS,
    ) -> dict[str, Any]:
        """
        Search for recent workout and activity data with detailed metrics.

        Returns comprehensive workout information including:
        - Workout type, date, DAY_OF_WEEK (e.g., Friday), time, and duration
        - Calories burned during workout
        - Heart rate statistics (avg, min, max) during workout
        - Heart rate zones and zone distribution

        IMPORTANT: Each workout includes 'day_of_week' field - USE IT! Don't calculate days yourself.

        CRITICAL: Workouts are returned sorted MOST RECENT FIRST. When presenting to users,
        ALWAYS list them in the order provided (most recent → oldest) for clarity.

        DATE FORMAT: All dates are in UTC and formatted as:
        - "date": "2025-10-22" (YYYY-MM-DD, date only)
        - "day_of_week": "Friday" (use this, don't calculate!)
        - "last_workout": "3 days ago" (human-readable, use this exact text)

        Use this when the user asks:
        - "When did I last work out?"
        - "Show me my recent workouts"
        - "How active have I been?"
        - "What was my heart rate during my workout?"
        - "Which day of the week do I work out?"

        IMPORTANT: For "last workout" queries, use days_back=30 to ensure finding it!

        Args:
            days_back: How many days back to search (default 7, recommend 30 for 'last workout')

        Returns:
            Dict with workout data including day_of_week field for each workout
        """
        logger.info(
            f"🔧 search_workouts_and_activity called with days_back={days_back}, user_id={user_id}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found", "workouts": []}

                health_data = json.loads(health_data_json)

                # Get actual workout records
                all_workouts = health_data.get("workouts", [])
                logger.info(
                    f"📊 Found {len(all_workouts)} total workouts in health data"
                )

                # Filter workouts by date range
                cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
                recent_workouts = []

                for workout in all_workouts:
                    # IMPORTANT: Use 'startDate' (full datetime) not 'date' (date string only)
                    start_date_str = workout.get("startDate", "")
                    if start_date_str:
                        try:
                            # Parse ISO datetime from workout data (stored with .isoformat())
                            # Note: Workouts use ISO format, not health record format
                            workout_date = datetime.fromisoformat(
                                start_date_str.replace("Z", "+00:00")
                            )

                            # If naive datetime, assume UTC
                            if workout_date.tzinfo is None:
                                workout_date = workout_date.replace(tzinfo=UTC)

                            if workout_date >= cutoff_date:
                                # Format workout info
                                workout_type = workout.get("type", "Unknown").replace(
                                    "HKWorkoutActivityType", ""
                                )
                                # Support both duration_minutes and duration (in seconds)
                                duration_min = (
                                    workout.get("duration_minutes")
                                    or workout.get("duration", 0) / 60
                                )

                                # Get heart rate data during workout
                                hr_data = _get_heart_rate_during_workout(
                                    health_data, start_date_str, duration_min
                                )

                                # Format workout info (UTC, frontend handles timezone)
                                day_of_week = workout_date.strftime("%A")

                                # Basic workout info (always included)
                                workout_info = {
                                    "date": workout_date.date().isoformat(),  # "2025-10-17"
                                    "datetime": workout_date.isoformat(),  # "2025-10-17T16:59:18+00:00"
                                    "day_of_week": day_of_week,
                                    "type": workout_type,
                                    "duration_minutes": (
                                        round(duration_min, 1)
                                        if isinstance(duration_min, int | float)
                                        else duration_min
                                    ),
                                }

                                # Always include detailed info (calories, heart rate)
                                # LLM will decide what to mention based on user query
                                workout_info["energy_burned"] = workout.get(
                                    "calories"
                                ) or workout.get("totalEnergyBurned", 0)
                                # Add heart rate data if available
                                if hr_data:
                                    workout_info.update(hr_data)

                                recent_workouts.append(workout_info)
                        except Exception as e:
                            logger.debug(
                                f"Skipping workout due to parsing error: {type(e).__name__}: {e}"
                            )
                            continue

                # Sort by date (most recent first)
                recent_workouts.sort(key=lambda x: x["date"], reverse=True)
                logger.info(
                    f"✅ Filtered to {len(recent_workouts)} recent workouts (last {days_back} days)"
                )

                # Calculate time since last workout
                if recent_workouts:
                    last_workout_date = recent_workouts[0]["date"]
                    try:
                        # Parse date string (YYYY-MM-DD format)
                        date_obj = datetime.fromisoformat(last_workout_date)
                        # CRITICAL: Use UTC for consistent timezone handling
                        now = datetime.now(UTC)
                        days_ago = (now.date() - date_obj.date()).days
                        time_ago = f"{days_ago} days ago" if days_ago > 0 else "today"
                    except Exception:
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
                return result

        except Exception as e:
            logger.error(
                f"❌ Error in search_workouts_and_activity: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {
                "error": f"Failed to search workouts: {str(e)}",
                "error_type": type(e).__name__,
                "workouts": [],
            }

    return search_workouts_and_activity
