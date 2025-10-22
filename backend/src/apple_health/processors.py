"""Apple Health Data Processors - Parse and transform health data.

Provides data processing functions for:
1. Parsing Apple Health XML exports into structured data
2. Generating health insights from Redis-cached data

These processors return ToolResult objects and are used by REST API endpoints.
For LangChain agent tools, see query_tools/ package.
"""

import json
import os
from datetime import datetime
from typing import Any

from ..services.redis_apple_health_manager import redis_manager
from ..utils.base import (
    HealthDataValidator,
    ToolResult,
    create_error_result,
    create_success_result,
    measure_execution_time,
)
from .models import HealthDataCollection
from .parser import AppleHealthParser, ParsingError

# ========== PARSING TOOL ==========


@measure_execution_time
def parse_health_file(file_path: str, anonymize: bool = True) -> ToolResult:
    """
    Parse Apple Health XML file and extract structured health data.

    Args:
        file_path: Path to Apple Health export XML file
        anonymize: Whether to anonymize personal data (recommended: True)

    Returns:
        ToolResult containing parsed health data or error information
    """
    try:
        if not HealthDataValidator.validate_file_path(file_path):
            return create_error_result(
                "Invalid file path format or security violation", "INVALID_FILE_PATH"
            )

        allowed_dirs = [
            os.getcwd(),
            os.path.join(os.getcwd(), "apple_health_export"),
        ]

        parser = AppleHealthParser(allowed_directories=allowed_dirs)

        if not parser.validate_xml_structure(file_path):
            return create_error_result(
                "File is not a valid Apple Health export", "INVALID_HEALTH_FILE"
            )

        health_data: HealthDataCollection = parser.parse_file(file_path)

        if anonymize:
            health_data = health_data.anonymize_all()

        ai_summary = _prepare_ai_summary(health_data)

        result_data = {
            "record_count": health_data.record_count,
            "export_date": health_data.export_date.isoformat(),
            "metrics_summary": ai_summary["metrics_summary"],
            "data_categories": ai_summary["data_categories"],
            "date_range": ai_summary["date_range"],
            "workouts": ai_summary.get("workouts", []),
            "workout_count": len(health_data.workouts),
            "conversation_context": health_data.to_conversation_summary(limit=10),
            "anonymized": anonymize,
        }

        return create_success_result(
            result_data,
            f"Successfully parsed {health_data.record_count} health records",
        )

    except ParsingError as e:
        return create_error_result(
            f"Health data parsing failed: {str(e)}", "PARSING_ERROR"
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in parse_health_file: {type(e).__name__}")

        return create_error_result(
            "An unexpected error occurred during parsing", "UNEXPECTED_ERROR"
        )


def _prepare_ai_summary(health_data: HealthDataCollection) -> dict[str, Any]:
    """Prepare AI-friendly summary of health data."""
    metrics_summary = {}
    data_categories = set()
    earliest_date = None
    latest_date = None

    for record in health_data.records:
        category = record.record_type.value.replace("HKQuantityTypeIdentifier", "")
        data_categories.add(category)

        if category not in metrics_summary:
            metrics_summary[category] = {
                "count": 0,
                "latest_value": None,
                "latest_date": None,
            }

        metrics_summary[category]["count"] += 1

        current_latest = metrics_summary[category]["latest_date"]
        if current_latest is None or record.start_date > current_latest:
            if record.value:
                metrics_summary[category][
                    "latest_value"
                ] = f"{record.value} {record.unit}"
            metrics_summary[category]["latest_date"] = record.start_date

        if earliest_date is None or record.start_date < earliest_date:
            earliest_date = record.start_date
        if latest_date is None or record.start_date > latest_date:
            latest_date = record.start_date

    date_range = {
        "earliest": earliest_date.isoformat() if earliest_date else None,
        "latest": latest_date.isoformat() if latest_date else None,
        "span_days": (
            (latest_date - earliest_date).days if earliest_date and latest_date else 0
        ),
    }

    for category in metrics_summary:
        if metrics_summary[category]["latest_date"]:
            metrics_summary[category]["latest_date"] = metrics_summary[category][
                "latest_date"
            ].isoformat()

    workouts_summary = []
    for workout in sorted(
        health_data.workouts, key=lambda w: w.start_date, reverse=True
    )[:10]:
        workout_type = workout.workout_activity_type.replace(
            "HKWorkoutActivityType", ""
        )
        workouts_summary.append(
            {
                "type": workout_type,
                "date": workout.start_date.isoformat(),
                "duration_minutes": round(workout.duration)
                if workout.duration
                else None,
                "calories": round(workout.total_energy_burned)
                if workout.total_energy_burned
                else None,
                "source": workout.source_name,
            }
        )

    return {
        "metrics_summary": metrics_summary,
        "data_categories": list(data_categories),
        "date_range": date_range,
        "workouts": workouts_summary,
    }


# ========== INSIGHTS TOOL ==========


def generate_health_insights(
    user_id: str, focus_area: str = "overall", include_trends: bool = True
) -> ToolResult:
    """
    Generate AI-ready health insights from Redis-cached data.

    Args:
        user_id: User identifier
        focus_area: Area to focus on ("weight", "activity", "nutrition", "overall")
        include_trends: Whether to include trend analysis

    Returns:
        ToolResult with comprehensive health insights
    """
    try:
        if not HealthDataValidator.validate_user_id(user_id):
            return create_error_result("Invalid user ID", "INVALID_USER_ID")

        with redis_manager.redis_manager.get_connection() as redis_client:
            main_key = f"health:user:{user_id}:data"
            health_data_json = redis_client.get(main_key)

            if not health_data_json:
                return create_error_result(
                    "No health data found - please parse your health file first",
                    "NO_HEALTH_DATA",
                )

            health_data = json.loads(health_data_json)

            if focus_area == "weight":
                insights = _generate_weight_insights(health_data, include_trends)
            elif focus_area == "activity":
                insights = _generate_activity_insights(health_data, include_trends)
            elif focus_area == "nutrition":
                insights = _generate_nutrition_insights(health_data, include_trends)
            else:
                insights = _generate_overall_insights(health_data, include_trends)

            insights["redis_advantages"] = {
                "instant_analysis": "Generated from O(1) Redis lookups",
                "conversation_memory": "Insights persist across chat sessions",
                "ttl_management": "Automatic cleanup after 7 days",
                "real_time_updates": "Always reflects latest health data",
            }

            return create_success_result(
                insights,
                f"Generated {focus_area} health insights from {health_data.get('record_count', 0)} records",
            )

    except Exception as e:
        return create_error_result(
            f"Failed to generate insights: {str(e)}", "INSIGHT_GENERATION_ERROR"
        )


def _generate_overall_insights(
    health_data: dict[str, Any], include_trends: bool
) -> dict[str, Any]:
    """Generate overall health insights."""
    insights = {
        "summary": "Comprehensive health analysis from your Apple Health data",
        "data_overview": {
            "total_records": health_data.get("record_count", 0),
            "data_span_days": health_data.get("date_range", {}).get("span_days", 0),
            "categories_tracked": len(health_data.get("data_categories", [])),
            "export_date": health_data.get("export_date"),
        },
    }

    metrics = health_data.get("metrics_summary", {})
    key_metrics = {}

    if "BodyMassIndex" in metrics:
        bmi_data = metrics["BodyMassIndex"]
        key_metrics["bmi"] = {
            "category": "Weight Management",
            "records": bmi_data["count"],
            "latest_value": bmi_data.get("latest_value", "N/A"),
            "latest_date": _format_date(bmi_data.get("latest_date")),
            "insight": _get_bmi_insight(bmi_data.get("latest_value", "")),
        }

    if "BodyMass" in metrics:
        weight_data = metrics["BodyMass"]
        key_metrics["weight"] = {
            "category": "Weight Management",
            "records": weight_data["count"],
            "latest_value": weight_data.get("latest_value", "N/A"),
            "latest_date": _format_date(weight_data.get("latest_date")),
            "insight": f"Current weight based on {weight_data['count']} measurements",
        }

    if "StepCount" in metrics:
        steps_data = metrics["StepCount"]
        key_metrics["steps"] = {
            "category": "Physical Activity",
            "records": steps_data["count"],
            "latest_value": steps_data.get("latest_value", "N/A"),
            "latest_date": _format_date(steps_data.get("latest_date")),
            "insight": f"Tracking {steps_data['count']} step measurements",
        }

    if "ActiveEnergyBurned" in metrics:
        energy_data = metrics["ActiveEnergyBurned"]
        key_metrics["active_energy"] = {
            "category": "Physical Activity",
            "records": energy_data["count"],
            "latest_value": energy_data.get("latest_value", "N/A"),
            "latest_date": _format_date(energy_data.get("latest_date")),
            "insight": f"Last workout tracked {_format_date(energy_data.get('latest_date'))}",
        }

    if "HeartRate" in metrics:
        hr_data = metrics["HeartRate"]
        key_metrics["heart_rate"] = {
            "category": "Cardiovascular Health",
            "records": hr_data["count"],
            "latest_value": hr_data.get("latest_value", "N/A"),
            "latest_date": _format_date(hr_data.get("latest_date")),
            "insight": f"Comprehensive heart rate monitoring with {hr_data['count']} measurements",
        }

    insights["key_metrics"] = key_metrics

    data_completeness = len(key_metrics) / 4.0 * 100
    insights["health_data_score"] = {
        "completeness_percentage": min(100, data_completeness),
        "message": (
            "Excellent data coverage"
            if data_completeness > 80
            else "Good data foundation"
        ),
    }

    return insights


def _generate_weight_insights(
    health_data: dict[str, Any], include_trends: bool
) -> dict[str, Any]:
    """Generate weight-focused insights."""
    metrics = health_data.get("metrics_summary", {})

    insights = {
        "focus_area": "Weight Management",
        "summary": "Analysis of your weight and BMI data",
    }

    if "BodyMassIndex" in metrics:
        bmi_data = metrics["BodyMassIndex"]
        latest_bmi = bmi_data.get("latest_value", "")

        insights["bmi_analysis"] = {
            "total_records": bmi_data["count"],
            "latest_value": latest_bmi,
            "health_category": _get_bmi_category(latest_bmi),
            "insight": _get_bmi_insight(latest_bmi),
            "data_frequency": f"Tracked {bmi_data['count']} times",
        }

    if "BodyMass" in metrics:
        weight_data = metrics["BodyMass"]
        insights["weight_tracking"] = {
            "total_records": weight_data["count"],
            "latest_value": weight_data.get("latest_value", "N/A"),
            "consistency": (
                "Regular tracking"
                if weight_data["count"] > 10
                else "Occasional tracking"
            ),
        }

    return insights


def _generate_activity_insights(
    health_data: dict[str, Any], include_trends: bool
) -> dict[str, Any]:
    """Generate activity-focused insights."""
    metrics = health_data.get("metrics_summary", {})

    insights = {
        "focus_area": "Physical Activity",
        "summary": "Analysis of your movement and exercise patterns",
    }

    if "StepCount" in metrics:
        steps_data = metrics["StepCount"]
        insights["step_analysis"] = {
            "total_records": steps_data["count"],
            "latest_value": steps_data.get("latest_value", "N/A"),
            "tracking_consistency": (
                "Excellent" if steps_data["count"] > 100 else "Good"
            ),
        }

    activity_metrics = {}
    if "DistanceWalkingRunning" in metrics:
        activity_metrics["distance"] = metrics["DistanceWalkingRunning"]
    if "ActiveEnergyBurned" in metrics:
        activity_metrics["energy"] = metrics["ActiveEnergyBurned"]

    if activity_metrics:
        insights["activity_metrics"] = activity_metrics

    return insights


def _generate_nutrition_insights(
    health_data: dict[str, Any], include_trends: bool
) -> dict[str, Any]:
    """Generate nutrition-focused insights."""
    metrics = health_data.get("metrics_summary", {})

    insights = {
        "focus_area": "Nutrition & Hydration",
        "summary": "Analysis of your dietary tracking data",
    }

    if "DietaryWater" in metrics:
        water_data = metrics["DietaryWater"]
        insights["hydration_analysis"] = {
            "total_records": water_data["count"],
            "latest_value": water_data.get("latest_value", "N/A"),
            "tracking_pattern": "Regular hydration tracking",
        }

    return insights


# ========== HELPER FUNCTIONS ==========


def _get_bmi_category(bmi_value: str) -> str:
    """Get BMI category from value."""
    try:
        if not bmi_value:
            return "Unknown"

        bmi = float(bmi_value.split()[0]) if " " in bmi_value else float(bmi_value)

        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal weight"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"
    except Exception:
        return "Unable to determine"


def _get_bmi_insight(bmi_value: str) -> str:
    """Get health insight from BMI value."""
    category = _get_bmi_category(bmi_value)

    insights_map = {
        "Normal weight": "Your BMI is within the healthy range",
        "Overweight": "Your BMI suggests focusing on gradual weight management",
        "Underweight": "Your BMI suggests considering weight gain strategies",
        "Obese": "Your BMI indicates significant weight management may be beneficial",
        "Unknown": "Unable to assess BMI category",
        "Unable to determine": "BMI data needs review",
    }

    return insights_map.get(category, "BMI tracking is valuable for health monitoring")


def _format_date(date_str: str | None) -> str:
    """Format ISO date string to human-readable format."""
    if not date_str:
        return "N/A"

    try:
        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(date_obj.tzinfo) if date_obj.tzinfo else datetime.now()
        delta = now - date_obj

        if delta.days == 0:
            return "today"
        elif delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
    except Exception:
        return date_str
