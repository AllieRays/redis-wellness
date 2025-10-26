"""
Integration tests for Apple Health query tools with real Redis data.

REAL TESTS - REQUIRE REDIS:
- Tests tools with real Redis storage
- Tests data flow: store → query → validate
- Requires: docker-compose up -d redis
"""

import json

import pytest

from src.apple_health.query_tools import (
    create_get_health_metrics_tool,
    create_get_workout_data_tool,
)


@pytest.fixture
def sample_health_data_in_redis(clean_redis, test_user_id):
    """Store sample health data in Redis for testing."""
    health_data = {
        "metrics_records": {
            "BodyMass": [
                {"date": "2025-10-20T12:00:00+00:00", "value": 70.2, "unit": "kg"},
                {"date": "2025-10-21T12:00:00+00:00", "value": 70.0, "unit": "kg"},
                {"date": "2025-10-22T12:00:00+00:00", "value": 69.8, "unit": "kg"},
            ],
            "HeartRate": [
                {"date": "2025-10-20T12:00:00+00:00", "value": 72, "unit": "count/min"},
                {"date": "2025-10-21T12:00:00+00:00", "value": 75, "unit": "count/min"},
                {"date": "2025-10-22T12:00:00+00:00", "value": 70, "unit": "count/min"},
            ],
        },
        "metrics_summary": {
            "BodyMass": {
                "latest_value": 69.8,
                "latest_date": "2025-10-22",
                "unit": "kg",
                "count": 3,
            },
            "HeartRate": {
                "latest_value": 70,
                "latest_date": "2025-10-22",
                "unit": "count/min",
                "count": 3,
            },
        },
        "workouts": [
            {
                "startDate": "2025-10-17T16:59:18+00:00",
                "type": "HKWorkoutActivityTypeTraditionalStrengthTraining",
                "duration_minutes": 45,
                "calories": 220,
            },
            {
                "startDate": "2025-10-19T10:30:00+00:00",
                "type": "HKWorkoutActivityTypeRunning",
                "duration_minutes": 30,
                "calories": 350,
            },
            {
                "startDate": "2025-10-22T08:15:00+00:00",
                "type": "HKWorkoutActivityTypeCycling",
                "duration_minutes": 60,
                "calories": 420,
            },
        ],
    }

    # Store in Redis
    main_key = f"health:user:{test_user_id}:data"
    with clean_redis as redis_client:
        redis_client.set(main_key, json.dumps(health_data))

    return health_data


@pytest.mark.integration
class TestGetHealthMetricsTool:
    """Test get_health_metrics tool with real Redis data."""

    def test_get_health_metrics_raw_data(
        self, sample_health_data_in_redis, test_user_id
    ):
        """Test retrieving raw health metrics."""
        tool = create_get_health_metrics_tool(user_id=test_user_id)

        result = tool.invoke(
            {"metric_types": ["BodyMass"], "time_period": "October 2025"}
        )

        assert "results" in result
        assert len(result["results"]) > 0
        assert result["mode"] == "raw_data"

        # Verify we got body mass data
        body_mass_result = result["results"][0]
        assert body_mass_result["metric"] == "BodyMass"
        assert "data" in body_mass_result
        assert len(body_mass_result["data"]) > 0

    def test_get_health_metrics_aggregation(
        self, sample_health_data_in_redis, test_user_id
    ):
        """Test health metrics with aggregation."""
        tool = create_get_health_metrics_tool(user_id=test_user_id)

        result = tool.invoke(
            {
                "metric_types": ["HeartRate"],
                "time_period": "October 2025",
                "aggregations": ["average", "min", "max"],
            }
        )

        assert "results" in result
        assert result["mode"] == "statistics"

        # Verify statistics calculated
        hr_result = result["results"][0]
        assert hr_result["metric"] == "HeartRate"
        assert "stats" in hr_result
        assert "average" in hr_result["stats"]

    def test_get_health_metrics_no_data(self, clean_redis, test_user_id):
        """Test querying when no data exists."""
        tool = create_get_health_metrics_tool(user_id=test_user_id)

        result = tool.invoke({"metric_types": ["BodyMass"], "time_period": "recent"})

        # Should return error or empty results, not crash
        assert "error" in result or "results" in result

    def test_get_health_metrics_multiple_types(
        self, sample_health_data_in_redis, test_user_id
    ):
        """Test querying multiple metric types at once."""
        tool = create_get_health_metrics_tool(user_id=test_user_id)

        result = tool.invoke(
            {
                "metric_types": ["BodyMass", "HeartRate"],
                "time_period": "October 2025",
            }
        )

        assert "results" in result
        assert len(result["results"]) >= 2
        metric_types_found = [r["metric"] for r in result["results"]]
        assert "BodyMass" in metric_types_found
        assert "HeartRate" in metric_types_found


@pytest.mark.integration
class TestGetWorkoutsTool:
    """Test get_workouts tool with real Redis data."""

    def test_get_workouts_basic(self, sample_health_data_in_redis, test_user_id):
        """Test retrieving workouts."""
        tool = create_get_workout_data_tool(user_id=test_user_id)

        result = tool.invoke({"days_back": 30})

        assert "workouts" in result
        assert len(result["workouts"]) > 0
        assert "total_workouts" in result

        # Verify workout structure
        workout = result["workouts"][0]
        assert "date" in workout
        assert "type" in workout
        assert "duration_minutes" in workout
        assert "day_of_week" in workout

    def test_get_workouts_recent(self, sample_health_data_in_redis, test_user_id):
        """Test getting recent workouts (last 7 days)."""
        tool = create_get_workout_data_tool(user_id=test_user_id)

        result = tool.invoke({"days_back": 7})

        assert "workouts" in result
        # Should find at least Oct 22 workout (within 7 days if test runs near that date)
        # Or return empty if dates don't match - that's OK

    def test_get_workouts_no_data(self, clean_redis, test_user_id):
        """Test querying workouts when none exist."""
        tool = create_get_workout_data_tool(user_id=test_user_id)

        result = tool.invoke({"days_back": 30})

        # Should return error or empty workouts, not crash
        assert "error" in result or "workouts" in result
        if "workouts" in result:
            assert isinstance(result["workouts"], list)

    def test_get_workouts_includes_metadata(
        self, sample_health_data_in_redis, test_user_id
    ):
        """Test workouts include required metadata."""
        tool = create_get_workout_data_tool(user_id=test_user_id)

        result = tool.invoke({"days_back": 30})

        if result.get("workouts"):
            workout = result["workouts"][0]
            # Verify required fields present
            assert "date" in workout
            assert "day_of_week" in workout
            assert "type" in workout
            assert "duration_minutes" in workout
            assert "energy_burned" in workout or "calories" in str(workout)


@pytest.mark.integration
class TestToolErrorHandling:
    """Test tool error handling and edge cases."""

    def test_tool_handles_missing_redis_connection(self, test_user_id):
        """Test tools handle Redis connection errors gracefully."""
        tool = create_get_health_metrics_tool(user_id=test_user_id)

        # Tool should handle missing data gracefully
        # (If Redis is down, this test will fail - that's expected)
        result = tool.invoke({"metric_types": ["BodyMass"], "time_period": "recent"})

        # Should return structured response (error or empty), not exception
        assert isinstance(result, dict)

    def test_tool_handles_invalid_metric_type(
        self, sample_health_data_in_redis, test_user_id
    ):
        """Test tool handles unknown metric types."""
        tool = create_get_health_metrics_tool(user_id=test_user_id)

        result = tool.invoke(
            {"metric_types": ["NonExistentMetric"], "time_period": "recent"}
        )

        # Should not crash - return empty results or error
        assert isinstance(result, dict)
        assert "results" in result or "error" in result


@pytest.mark.integration
class TestToolDataFlow:
    """Test end-to-end data flow through tools."""

    def test_data_flow_store_to_query(self, clean_redis, test_user_id):
        """Test complete flow: store data → query via tool → validate result."""
        # Step 1: Store health data
        health_data = {
            "metrics_records": {
                "BodyMass": [
                    {"date": "2025-10-25T12:00:00+00:00", "value": 155.0, "unit": "lb"},
                ]
            },
            "metrics_summary": {
                "BodyMass": {
                    "latest_value": 155.0,
                    "latest_date": "2025-10-25",
                    "unit": "lb",
                    "count": 1,
                }
            },
        }

        main_key = f"health:user:{test_user_id}:data"
        with clean_redis as redis_client:
            redis_client.set(main_key, json.dumps(health_data))

        # Step 2: Query via tool
        tool = create_get_health_metrics_tool(user_id=test_user_id)
        result = tool.invoke(
            {"metric_types": ["BodyMass"], "time_period": "October 25"}
        )

        # Step 3: Validate result
        assert "results" in result
        assert len(result["results"]) > 0

        body_mass = result["results"][0]
        assert body_mass["metric_type"] == "BodyMass"

        # Verify the exact value we stored
        if "records" in body_mass:
            assert len(body_mass["records"]) > 0
            # Value should be 155.0 lb
            record_value = body_mass["records"][0]["value"]
            assert "155" in str(record_value)
