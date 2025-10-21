#!/usr/bin/env python3
"""
Test script for health insights functionality with mock data.
"""

from src.services.redis_health_tool import store_health_data
from src.tools.health_insights_tool import generate_health_insights

# Create mock health data similar to real parsed Apple Health data
mock_health_data = {
    "record_count": 255672,
    "export_date": "2024-01-01",
    "date_range": {
        "span_days": 1095,  # 3 years of data
        "start_date": "2021-01-01",
        "end_date": "2024-01-01",
    },
    "data_categories": [
        "BodyMassIndex",
        "StepCount",
        "HeartRate",
        "BodyMass",
        "DietaryWater",
        "ActiveEnergyBurned",
        "DistanceWalkingRunning",
    ],
    "metrics_summary": {
        "BodyMassIndex": {
            "count": 245,
            "latest_value": "22.5 kg/m^2",
            "first_date": "2021-01-15",
            "last_date": "2023-12-28",
        },
        "StepCount": {
            "count": 985,
            "latest_value": "8547 count",
            "first_date": "2021-01-01",
            "last_date": "2023-12-31",
        },
        "HeartRate": {
            "count": 45823,
            "latest_value": "72 count/min",
            "first_date": "2021-01-01",
            "last_date": "2023-12-31",
        },
        "BodyMass": {
            "count": 123,
            "latest_value": "68.5 kg",
            "first_date": "2021-01-15",
            "last_date": "2023-12-28",
        },
        "DietaryWater": {
            "count": 156,
            "latest_value": "2.1 L",
            "first_date": "2021-03-01",
            "last_date": "2023-11-15",
        },
    },
    "conversation_context": "User has comprehensive Apple Health data with weight, activity, and hydration tracking over 3 years.",
}


def test_health_insights():
    print("=== Testing Health Insights Tool ===")

    print("Storing mock health data...")
    store_result = store_health_data("test_user", mock_health_data)
    print(f"Store result: success={store_result.success}")

    if not store_result.success:
        print(f"Store failed: {store_result.data}")
        return

    print("\n=== Overall Health Insights ===")
    insights_result = generate_health_insights("test_user", focus_area="overall")

    if insights_result.success:
        print("✅ SUCCESS: Health insights generated!")
        print(f"Message: {insights_result.message}")

        # Display key insights
        data = insights_result.data
        print(f"\nSummary: {data.get('summary', 'N/A')}")

        # Data overview
        overview = data.get("data_overview", {})
        print(f"Total Records: {overview.get('total_records', 'N/A')}")
        print(f"Data Span: {overview.get('data_span_days', 'N/A')} days")
        print(f"Categories: {overview.get('categories_tracked', 'N/A')}")

        # Key health metrics insights
        metrics = data.get("key_metrics", {})
        if metrics:
            print("\nHealth Insights:")
            for metric_name, metric_info in metrics.items():
                insight = metric_info.get("insight", "No insight available")
                records = metric_info.get("records", "Unknown")
                print(f"- {metric_name.upper()}: {insight} ({records} records)")

        # Health score
        score = data.get("health_data_score", {})
        if score:
            print(
                f"\nHealth Data Score: {score.get('completeness_percentage', 0)}% - {score.get('message', 'N/A')}"
            )

    else:
        print(f"❌ Insights generation failed: {insights_result.data}")
        return

    print("\n=== Weight-focused Insights ===")
    weight_insights = generate_health_insights("test_user", focus_area="weight")
    if weight_insights.success:
        weight_data = weight_insights.data
        print(f"Focus Area: {weight_data.get('focus_area', 'Unknown')}")
        print(f"Summary: {weight_data.get('summary', 'N/A')}")

        if "bmi_analysis" in weight_data:
            bmi = weight_data["bmi_analysis"]
            print(f"BMI Category: {bmi.get('health_category', 'Unknown')}")
            print(f"BMI Insight: {bmi.get('insight', 'No insight')}")
            print(f"BMI Records: {bmi.get('total_records', 'Unknown')}")
    else:
        print(f"❌ Weight insights failed: {weight_insights.data}")

    print("\n=== Activity-focused Insights ===")
    activity_insights = generate_health_insights("test_user", focus_area="activity")
    if activity_insights.success:
        activity_data = activity_insights.data
        print(f"Focus Area: {activity_data.get('focus_area', 'Unknown')}")
        print(f"Summary: {activity_data.get('summary', 'N/A')}")

        if "step_analysis" in activity_data:
            steps = activity_data["step_analysis"]
            print(
                f"Step Tracking: {steps.get('tracking_consistency', 'Unknown')} ({steps.get('total_records', 'Unknown')} records)"
            )
    else:
        print(f"❌ Activity insights failed: {activity_insights.data}")

    print("\n=== Redis Advantages Demo ===")
    redis_advantages = insights_result.data.get("redis_advantages", {})
    if redis_advantages:
        print("Redis-powered features:")
        for advantage, desc in redis_advantages.items():
            print(f"- {advantage}: {desc}")


if __name__ == "__main__":
    test_health_insights()
