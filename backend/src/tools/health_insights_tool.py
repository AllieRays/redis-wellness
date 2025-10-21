"""
Health Insights Tool for AI Agents.

Generates intelligent health insights and trends from Redis-cached health data.
Built for Apple Health data with 255K+ records across 48 health metrics.
"""

import json
from datetime import datetime
from typing import Any

from ..services.redis_health_tool import redis_manager
from ..utils.base import (
    HealthDataValidator,
    ToolResult,
    create_error_result,
    create_success_result,
)


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
        # Validate input
        if not HealthDataValidator.validate_user_id(user_id):
            return create_error_result("Invalid user ID", "INVALID_USER_ID")

        # Get health data from Redis
        with redis_manager.redis_manager.get_connection() as redis_client:
            # Get main health data
            main_key = f"health:user:{user_id}:data"
            health_data_json = redis_client.get(main_key)

            if not health_data_json:
                return create_error_result(
                    "No health data found - please parse your health file first",
                    "NO_HEALTH_DATA",
                )

            health_data = json.loads(health_data_json)

            # Generate insights based on focus area
            if focus_area == "weight":
                insights = _generate_weight_insights(health_data, include_trends)
            elif focus_area == "activity":
                insights = _generate_activity_insights(health_data, include_trends)
            elif focus_area == "nutrition":
                insights = _generate_nutrition_insights(health_data, include_trends)
            else:  # overall
                insights = _generate_overall_insights(health_data, include_trends)

            # Add Redis advantages info
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
    """Generate overall health insights from comprehensive data."""
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

    # Key health indicators
    key_metrics = {}

    # BMI/Weight insights
    if "BodyMassIndex" in metrics:
        bmi_data = metrics["BodyMassIndex"]
        key_metrics["bmi"] = {
            "category": "Weight Management",
            "records": bmi_data["count"],
            "latest_value": bmi_data.get("latest_value", "N/A"),
            "latest_date": _format_date(bmi_data.get("latest_date")),
            "insight": _get_bmi_insight(bmi_data.get("latest_value", "")),
        }

    # Weight data
    if "BodyMass" in metrics:
        weight_data = metrics["BodyMass"]
        key_metrics["weight"] = {
            "category": "Weight Management",
            "records": weight_data["count"],
            "latest_value": weight_data.get("latest_value", "N/A"),
            "latest_date": _format_date(weight_data.get("latest_date")),
            "insight": f"Current weight based on {weight_data['count']} measurements",
        }

    # Activity insights
    if "StepCount" in metrics:
        steps_data = metrics["StepCount"]
        key_metrics["steps"] = {
            "category": "Physical Activity",
            "records": steps_data["count"],
            "latest_value": steps_data.get("latest_value", "N/A"),
            "latest_date": _format_date(steps_data.get("latest_date")),
            "insight": f"Tracking {steps_data['count']} step measurements",
        }

    # Active Energy (workout indicator)
    if "ActiveEnergyBurned" in metrics:
        energy_data = metrics["ActiveEnergyBurned"]
        key_metrics["active_energy"] = {
            "category": "Physical Activity",
            "records": energy_data["count"],
            "latest_value": energy_data.get("latest_value", "N/A"),
            "latest_date": _format_date(energy_data.get("latest_date")),
            "insight": f"Last workout tracked {_format_date(energy_data.get('latest_date'))}",
        }

    # Heart health
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

    # Health score based on data completeness
    data_completeness = (
        len(key_metrics) / 4.0 * 100
    )  # Out of 4 key areas (BMI, weight, steps, heart rate)
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

    # BMI analysis
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

    # Body mass data
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

    # Steps analysis
    if "StepCount" in metrics:
        steps_data = metrics["StepCount"]
        insights["step_analysis"] = {
            "total_records": steps_data["count"],
            "latest_value": steps_data.get("latest_value", "N/A"),
            "tracking_consistency": (
                "Excellent" if steps_data["count"] > 100 else "Good"
            ),
        }

    # Distance and energy
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

    # Water intake
    if "DietaryWater" in metrics:
        water_data = metrics["DietaryWater"]
        insights["hydration_analysis"] = {
            "total_records": water_data["count"],
            "latest_value": water_data.get("latest_value", "N/A"),
            "tracking_pattern": "Regular hydration tracking",
        }

    return insights


def _get_bmi_category(bmi_value: str) -> str:
    """Get BMI category from value."""
    try:
        if not bmi_value:
            return "Unknown"

        # Extract numeric value (handle "23.6 count" format)
        bmi = float(bmi_value.split()[0]) if " " in bmi_value else float(bmi_value)

        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal weight"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"
    except:
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
    """Format ISO date string to human-readable format with relative time."""
    if not date_str:
        return "N/A"

    try:
        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(date_obj.tzinfo) if date_obj.tzinfo else datetime.now()
        delta = now - date_obj

        # Human-readable relative time
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
    except:
        return date_str
