"""
Tool wrappers that inject user context automatically.

This solves the problem of passing user_id to tools without requiring
the LLM to know or provide it.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.tools import tool

from ..services.redis_health_tool import redis_manager
from ..utils.conversion_utils import convert_weight_to_lbs as _convert_weight_to_lbs
from ..utils.time_utils import parse_time_period as _parse_time_period

# Note: _parse_time_period and _convert_weight_to_lbs are now imported from utils modules


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
        from datetime import datetime, timedelta

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
                record_time = datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S")
                # Make timezone aware for comparison
                if record_time.tzinfo is None and workout_start.tzinfo is not None:
                    record_time = record_time.replace(tzinfo=workout_start.tzinfo)

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
        # Using simplified age-based max HR: 220 - age (assume age 30 for now)
        max_hr_estimate = 190  # Conservative estimate

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


def create_user_bound_tools(user_id: str, conversation_history=None):
    """
    Create tool instances bound to a specific user.

    This is the correct way to handle user context - the tools are
    created for each chat session with the user_id baked in.

    Args:
        user_id: The user identifier to bind to these tools
        conversation_history: Recent conversation messages to detect follow-ups

    Returns:
        List of LangChain tools with user_id injected
    """

    # Check if this is a follow-up query (for tiered responses)
    import logging

    logger = logging.getLogger(__name__)

    is_followup = False
    if conversation_history and len(conversation_history) >= 2:
        # Check if we already discussed workouts in PREVIOUS messages (exclude last/current message)
        # Look at assistant responses to see if we already talked about workouts
        from langchain_core.messages import AIMessage

        recent_assistant_messages = [
            msg for msg in conversation_history[-5:-1] if isinstance(msg, AIMessage)
        ]
        if recent_assistant_messages:
            recent_text = " ".join(
                [msg.content.lower() for msg in recent_assistant_messages]
            )
            is_followup = "workout" in recent_text or "exercise" in recent_text
            logger.info(
                f"🔍 Tiered response: is_followup={is_followup} (checked {len(recent_assistant_messages)} prev messages)"
            )
    else:
        logger.info(
            f"🔍 Tiered response: is_followup=False (conv_history={len(conversation_history) if conversation_history else 0} messages)"
        )

    @tool
    def search_health_records_by_metric(
        metric_types: list[str], time_period: str = "recent"
    ) -> dict[str, Any]:
        """
        Search for specific health metrics within a time period.

        Use this when the user asks about specific health metrics like:
        - BMI, weight, steps, heart rate, active energy
        - Recent values or trends
        - Historical data ("what was my weight in September?")

        Args:
            metric_types: List of metric types (e.g., ["BodyMassIndex", "BodyMass"])
            time_period: Natural language time description (default: "recent")
                Examples:
                - "September" → all of September in current year
                - "September 2024" → all of September 2024
                - "early September" → first 10 days of September
                - "late August" → last 10 days of August
                - "last 2 weeks" → past 14 days
                - "this month" → current month so far
                - "recent" → last 30 days (default)

        Examples:
            - "What was my weight in September?" → time_period="September"
            - "What's my current weight?" → time_period="recent"
            - "Show my BMI in early August" → time_period="early August"
            - "Weight trend last 2 weeks" → time_period="last 2 weeks"

        Returns:
            Dict with matching records and metadata
        """
        import json
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"🔧 search_health_records_by_metric called: metrics={metric_types}, time_period='{time_period}', user_id={user_id}"
        )

        try:
            # Parse time period into date range
            filter_start, filter_end, time_range_desc = _parse_time_period(time_period)
            logger.info(
                f"📅 Parsed '{time_period}' → {filter_start.strftime('%Y-%m-%d')} to {filter_end.strftime('%Y-%m-%d')} ({time_range_desc})"
            )

            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found for user", "records": []}

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})
                metrics_summary = health_data.get("metrics_summary", {})

                results = []
                for metric_type in metric_types:
                    # Try to get historical records first
                    if metric_type in metrics_records:
                        all_records = metrics_records[metric_type]
                        logger.info(
                            f"📊 Found {len(all_records)} total {metric_type} records"
                        )

                        # Filter by date range and limit
                        filtered_records = []
                        for record in all_records:  # Keep chronological order
                            record_date = datetime.strptime(
                                record["date"], "%Y-%m-%d %H:%M:%S"
                            )

                            # Check if record is within date range
                            if filter_start <= record_date <= filter_end:
                                value = record["value"]
                                unit = record["unit"]

                                # Convert weight from kg/lb to lbs
                                if metric_type == "BodyMass":
                                    value = _convert_weight_to_lbs(value, unit)
                                elif unit:
                                    value = f"{value} {unit}"

                                filtered_records.append(
                                    {
                                        "value": value,
                                        "date": record["date"][:10],  # Just YYYY-MM-DD
                                    }
                                )

                        logger.info(
                            f"✅ Filtered to {len(filtered_records)} {metric_type} records ({time_range_desc})"
                        )

                        results.append(
                            {
                                "metric_type": metric_type,
                                "records": filtered_records,
                                "total_found": len(filtered_records),
                                "time_range": time_range_desc,
                            }
                        )

                    # Fall back to summary if no detailed records
                    elif metric_type in metrics_summary:
                        metric_info = metrics_summary[metric_type]
                        latest_value = metric_info.get("latest_value", "N/A")
                        unit = metric_info.get("unit", "")

                        if metric_type == "BodyMass" and latest_value != "N/A":
                            latest_value = _convert_weight_to_lbs(latest_value, unit)
                        elif latest_value != "N/A" and unit:
                            latest_value = f"{latest_value} {unit}"

                        results.append(
                            {
                                "metric_type": metric_type,
                                "latest_value": latest_value,
                                "latest_date": metric_info.get("latest_date", "N/A"),
                                "total_records": metric_info.get("count", 0),
                                "time_range": time_range_desc,
                            }
                        )

                logger.info(f"📤 Returning {len(results)} metric types")
                return {
                    "results": results,
                    "total_metrics": len(results),
                    "searched_metrics": metric_types,
                }
        except Exception as e:
            logger.error(f"❌ Error in search_health_records_by_metric: {e}")
            return {"error": str(e), "results": []}

    @tool
    def search_workouts_and_activity(days_back: int = 7) -> dict[str, Any]:
        """
        Search for recent workout and activity data with detailed metrics.

        Returns comprehensive workout information including:
        - Workout type, date, DAY_OF_WEEK (e.g., Friday), time, and duration
        - Calories burned during workout
        - Heart rate statistics (avg, min, max) during workout
        - Heart rate zones and zone distribution

        IMPORTANT: Each workout includes 'day_of_week' field - USE IT! Don't calculate days yourself.

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
        import json
        import logging
        from datetime import datetime

        logger = logging.getLogger(__name__)
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
                # Note: Parser normalizes all datetimes to UTC, so we can compare directly

                cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
                recent_workouts = []

                for workout in all_workouts:
                    # Support both 'date' and 'startDate' field names
                    start_date_str = workout.get("date") or workout.get("startDate", "")
                    if start_date_str:
                        try:
                            # Parser already normalized to UTC, just parse the ISO string
                            workout_date = datetime.fromisoformat(
                                start_date_str.replace("Z", "+00:00")
                            )

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

                                # Format datetime in PST for display
                                # Calculate day of week in PST
                                from zoneinfo import ZoneInfo

                                from backend.src.utils.time_utils import (
                                    format_date_pst,
                                    format_datetime_pst,
                                )

                                workout_date_pst = workout_date.astimezone(
                                    ZoneInfo("America/Los_Angeles")
                                )
                                day_of_week = workout_date_pst.strftime("%A")

                                # Basic workout info (always included)
                                workout_info = {
                                    "date": format_date_pst(
                                        workout_date
                                    ),  # "Oct 17, 2025"
                                    "datetime": format_datetime_pst(
                                        workout_date
                                    ),  # "Oct 17, 2025 at 9:59 AM PDT"
                                    "day_of_week": day_of_week,
                                    "type": workout_type,
                                    "duration_minutes": (
                                        round(duration_min, 1)
                                        if isinstance(duration_min, (int, float))
                                        else duration_min
                                    ),
                                }

                                # Detailed info (only on follow-ups for tiered response)
                                if is_followup:
                                    workout_info["energy_burned"] = workout.get(
                                        "calories"
                                    ) or workout.get("totalEnergyBurned", 0)
                                    # Add heart rate data if available
                                    if hr_data:
                                        workout_info.update(hr_data)

                                recent_workouts.append(workout_info)
                        except Exception as e:
                            logger.debug(f"Skipping workout due to parsing error: {e}")
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
                        date_obj = datetime.fromisoformat(last_workout_date)
                        now = datetime.now()
                        days_ago = (now - date_obj).days
                        time_ago = f"{days_ago} days ago" if days_ago > 0 else "today"
                    except:
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
            logger.error(f"❌ Error in search_workouts_and_activity: {e}")
            return {"error": str(e), "workouts": []}

    @tool
    def aggregate_metrics(
        metric_types: list[str],
        time_period: str = "recent",
        aggregations: list[str] = None,
    ) -> dict[str, Any]:
        """
        🔢 CALCULATE STATISTICS - Use for mathematical aggregation: average, min, max, sum, count.

        ⚠️ USE THIS TOOL WHEN USER ASKS FOR:
        - AVERAGE/MEAN: "average heart rate", "mean weight", "avg BMI"
        - MIN/MAX: "minimum", "lowest", "highest", "maximum", "best", "worst"
        - TOTAL/SUM: "total steps", "sum of calories", "how many total"
        - STATISTICS: "stats on", "statistics", "give me numbers", "calculate"
        - COMPUTATION: "compute", "calculate my", "what's my avg"

        ❌ DO NOT USE THIS TOOL FOR:
        - Individual data points → use search_health_records_by_metric instead
        - Viewing trends over time → use search_health_records_by_metric instead
        - Listing all values → use search_health_records_by_metric instead
        - Workouts → use search_workouts_and_activity instead

        This tool performs MATHEMATICAL AGGREGATION on health metric data.
        It returns COMPUTED STATISTICS (single numbers), NOT raw data lists.

        Args:
            metric_types: List of metric types ["HeartRate", "BodyMass", "BodyMassIndex", "StepCount", "ActiveEnergyBurned"]
            time_period: Natural language time ("last week", "September", "this month", "last 30 days", "recent")
            aggregations: Statistics to compute ["average", "min", "max", "sum", "count"] (defaults to all if not specified)

        Example Queries and Tool Calls:
            Query: "What was my average heart rate last week?"
            → aggregate_metrics(metric_types=["HeartRate"], time_period="last week", aggregations=["average"])
            Returns: {"average": "72.5 bpm", "sample_size": 1250}

            Query: "Give me stats on my weight in September"
            → aggregate_metrics(metric_types=["BodyMass"], time_period="September", aggregations=["average", "min", "max"])
            Returns: {"average": "160.2 lbs", "min": "158.1 lbs", "max": "162.5 lbs"}

            Query: "How many total steps did I take this month?"
            → aggregate_metrics(metric_types=["StepCount"], time_period="this month", aggregations=["sum"])
            Returns: {"sum": "125000", "count": 30}

        Returns:
            Dict with computed statistics for each metric type
        """
        import json
        import logging
        from statistics import mean

        logger = logging.getLogger(__name__)
        logger.info(
            f"🔧 aggregate_metrics called: metrics={metric_types}, time_period='{time_period}', aggregations={aggregations}, user_id={user_id}"
        )

        try:
            # Default aggregations if not provided
            if not aggregations:
                aggregations = ["average", "min", "max", "count"]

            # Parse time period into date range
            filter_start, filter_end, time_range_desc = _parse_time_period(time_period)
            logger.info(
                f"📅 Parsed '{time_period}' → {filter_start.strftime('%Y-%m-%d')} to {filter_end.strftime('%Y-%m-%d')} ({time_range_desc})"
            )

            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found for user", "results": []}

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                results = []
                for metric_type in metric_types:
                    if metric_type not in metrics_records:
                        logger.warning(f"⚠️ Metric {metric_type} not found in records")
                        continue

                    all_records = metrics_records[metric_type]
                    logger.info(
                        f"📊 Found {len(all_records)} total {metric_type} records"
                    )

                    # Filter by date range
                    filtered_values = []
                    for record in all_records:
                        record_date = datetime.strptime(
                            record["date"], "%Y-%m-%d %H:%M:%S"
                        )

                        if filter_start <= record_date <= filter_end:
                            try:
                                value = float(record["value"])
                                filtered_values.append(value)
                            except (ValueError, TypeError):
                                continue

                    if not filtered_values:
                        logger.warning(
                            f"⚠️ No {metric_type} records found in time range"
                        )
                        results.append(
                            {
                                "metric_type": metric_type,
                                "time_range": time_range_desc,
                                "statistics": {},
                                "message": f"No {metric_type} data found for {time_range_desc}",
                            }
                        )
                        continue

                    logger.info(
                        f"✅ Filtered to {len(filtered_values)} {metric_type} values ({time_range_desc})"
                    )

                    # Calculate statistics
                    statistics = {}
                    unit = all_records[0].get("unit", "") if all_records else ""

                    if "average" in aggregations or "avg" in aggregations:
                        avg_value = mean(filtered_values)
                        # Convert weight to lbs if needed
                        if metric_type == "BodyMass":
                            statistics["average"] = _convert_weight_to_lbs(
                                str(avg_value), unit
                            )
                        else:
                            statistics["average"] = (
                                f"{avg_value:.1f} {unit}"
                                if unit
                                else f"{avg_value:.1f}"
                            )

                    if "min" in aggregations or "minimum" in aggregations:
                        min_value = min(filtered_values)
                        if metric_type == "BodyMass":
                            statistics["min"] = _convert_weight_to_lbs(
                                str(min_value), unit
                            )
                        else:
                            statistics["min"] = (
                                f"{min_value:.1f} {unit}"
                                if unit
                                else f"{min_value:.1f}"
                            )

                    if "max" in aggregations or "maximum" in aggregations:
                        max_value = max(filtered_values)
                        if metric_type == "BodyMass":
                            statistics["max"] = _convert_weight_to_lbs(
                                str(max_value), unit
                            )
                        else:
                            statistics["max"] = (
                                f"{max_value:.1f} {unit}"
                                if unit
                                else f"{max_value:.1f}"
                            )

                    if "sum" in aggregations or "total" in aggregations:
                        sum_value = sum(filtered_values)
                        if metric_type == "BodyMass":
                            statistics["sum"] = _convert_weight_to_lbs(
                                str(sum_value), unit
                            )
                        else:
                            statistics["sum"] = (
                                f"{sum_value:.1f} {unit}"
                                if unit
                                else f"{sum_value:.1f}"
                            )

                    if "count" in aggregations:
                        statistics["count"] = len(filtered_values)

                    results.append(
                        {
                            "metric_type": metric_type,
                            "time_range": time_range_desc,
                            "statistics": statistics,
                            "sample_size": len(filtered_values),
                        }
                    )

                logger.info(f"📤 Returning statistics for {len(results)} metrics")
                return {
                    "results": results,
                    "total_metrics": len(results),
                    "time_range": time_range_desc,
                }

        except Exception as e:
            logger.error(f"❌ Error in aggregate_metrics: {e}")
            return {"error": str(e), "results": []}

    @tool
    def calculate_weight_trends_tool(
        time_period: str = "last_90_days", trend_type: str = "both"
    ) -> dict[str, Any]:
        """
        Calculate weight trends with linear regression and moving averages.

        Use this when the user asks about:
        - Weight trends over time
        - "Am I losing or gaining weight?"
        - "Calculate my weight trend"
        - "Show me my weight progress"
        - Statistical analysis of weight changes

        Args:
            time_period: Time period to analyze ("last_90_days", "last_30_days", "this_month", "last_month")
            trend_type: Type of analysis ("linear_regression", "moving_average", "both")

        Returns:
            Dict with trend analysis including slope, R², statistical significance

        Examples:
            - "Calculate my weight trend over 3 months" → time_period="last_90_days", trend_type="both"
            - "Am I losing weight?" → time_period="last_30_days", trend_type="linear_regression"
        """
        import json
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"🔧 calculate_weight_trends_tool called: time_period='{time_period}', trend_type='{trend_type}', user_id={user_id}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found for user"}

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                # Get weight records
                weight_records = metrics_records.get("BodyMass", [])

                if not weight_records:
                    return {"error": "No weight records found"}

                # Call pure function with data
                from ..utils.math_tools import calculate_weight_trends

                result = calculate_weight_trends(
                    weight_records, time_period, trend_type
                )

                logger.info("✅ Weight trend analysis complete")
                return result

        except Exception as e:
            logger.error(f"❌ Error in calculate_weight_trends_tool: {e}")
            return {"error": str(e)}

    @tool
    def compare_time_periods_tool(
        metric_type: str, period1: str, period2: str
    ) -> dict[str, Any]:
        """
        Compare metrics between two time periods with statistical significance.

        Use this when the user asks to compare:
        - "Compare my weight this month vs last month"
        - "How does my heart rate this week compare to last week?"
        - "Compare my activity levels"
        - Period-over-period analysis

        Args:
            metric_type: Type of metric ("BodyMass", "HeartRate", "StepCount", "BodyMassIndex", "ActiveEnergyBurned")
            period1: First time period ("this_month", "last_30_days", etc.)
            period2: Second time period ("last_month", "previous_30_days", etc.)

        Returns:
            Dict with comparison statistics and significance testing

        Examples:
            - "Compare my weight this month vs last month" → metric_type="BodyMass", period1="this_month", period2="last_month"
            - "How does my heart rate compare?" → metric_type="HeartRate", period1="last_week", period2="previous_week"
        """
        import json
        import logging

        # Import moved to top level

        logger = logging.getLogger(__name__)
        logger.info(
            f"🔧 compare_time_periods_tool called: metric_type='{metric_type}', period1='{period1}', period2='{period2}', user_id={user_id}"
        )

        try:
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found for user"}

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                # Get records for the specified metric
                all_records = metrics_records.get(metric_type, [])

                if not all_records:
                    return {"error": f"No {metric_type} records found"}

                # Call pure function with data
                from ..utils.math_tools import compare_time_periods

                result = compare_time_periods(
                    all_records, metric_type, period1, period2
                )

                logger.info("✅ Period comparison complete")
                return result

        except Exception as e:
            logger.error(f"❌ Error in compare_time_periods_tool: {e}")
            return {"error": str(e)}

    return [
        search_health_records_by_metric,  # All metric queries (weight, BMI, heart rate, steps, etc.)
        search_workouts_and_activity,  # All workout queries
        aggregate_metrics,  # Statistics and aggregations
        calculate_weight_trends_tool,  # Weight trend analysis with regression
        compare_time_periods_tool,  # Period-over-period comparisons
    ]
