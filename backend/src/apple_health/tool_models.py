"""
Pydantic models for structured tool return types.

These models provide type safety and validation for all health query tool responses,
replacing dict returns with strongly-typed models.

Benefits:
- Type checking and IDE autocomplete
- Runtime validation
- Self-documenting API
- Consistent response structure
- Easy to serialize to JSON

Usage:
    from apple_health.tool_models import HealthRecordResult

    result = HealthRecordResult(
        metric_type="BodyMass",
        records=[{"value": "150 lbs", "date": "2025-10-22"}],
        total_found=1,
        time_range="recent"
    )

    return result.model_dump()  # Convert to dict for LangChain tool
"""

from typing import Any

from pydantic import BaseModel, Field

# ========== Base Models ==========


class ToolError(BaseModel):
    """Standard error response for tool failures."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(default="ToolError", description="Error type/category")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional error context"
    )


class ToolSuccess(BaseModel):
    """Base class for successful tool responses."""

    success: bool = Field(
        default=True, description="Always true for successful responses"
    )


# ========== Health Record Models ==========


class HealthRecordItem(BaseModel):
    """Single health record entry."""

    value: str | float = Field(
        ..., description="Metric value with unit (e.g., '150 lbs', '72 bpm')"
    )
    date: str = Field(..., description="Date in YYYY-MM-DD format")


class HealthRecordResult(BaseModel):
    """Result for a single metric type search."""

    metric_type: str = Field(
        ..., description="Metric type (e.g., 'BodyMass', 'HeartRate')"
    )
    records: list[HealthRecordItem] = Field(
        default_factory=list, description="Matching health records"
    )
    total_found: int = Field(default=0, description="Number of records found")
    time_range: str = Field(..., description="Human-readable time range description")
    latest_value: str | None = Field(
        None, description="Latest value (for summary-only results)"
    )
    latest_date: str | None = Field(
        None, description="Latest date (for summary-only results)"
    )
    total_records: int | None = Field(
        None, description="Total records in database (for summary)"
    )


class HealthRecordsResponse(BaseModel):
    """Complete response for health records search tool."""

    results: list[HealthRecordResult] = Field(
        default_factory=list, description="Results per metric type"
    )
    total_metrics: int = Field(default=0, description="Number of metric types returned")
    searched_metrics: list[str] = Field(
        default_factory=list, description="Metric types that were searched"
    )
    error: str | None = Field(None, description="Error message if search failed")
    error_type: str | None = Field(None, description="Error type if search failed")


# ========== Workout Models ==========


class HeartRateStats(BaseModel):
    """Heart rate statistics during workout."""

    heart_rate_avg: str = Field(..., description="Average HR (e.g., '145 bpm')")
    heart_rate_min: str = Field(..., description="Minimum HR (e.g., '120 bpm')")
    heart_rate_max: str = Field(..., description="Maximum HR (e.g., '165 bpm')")
    heart_rate_samples: int = Field(..., description="Number of HR measurements")
    heart_rate_zone: str = Field(
        ..., description="Dominant HR zone (e.g., 'Moderate (60-70% max HR)')"
    )
    heart_rate_zone_distribution: dict[str, int] = Field(
        default_factory=dict, description="Time in each zone"
    )


class WorkoutItem(BaseModel):
    """Single workout entry with full details."""

    workout_type: str = Field(
        ..., description="Type of workout (e.g., 'Running', 'Cycling')"
    )
    date: str = Field(..., description="Workout date in YYYY-MM-DD format")
    day_of_week: str = Field(
        ..., description="Day name (e.g., 'Friday') - use this, don't calculate!"
    )
    start_time: str | None = Field(None, description="Start time in HH:MM format")
    duration_minutes: float = Field(..., description="Duration in minutes")
    duration_str: str = Field(
        ..., description="Human-readable duration (e.g., '45 min')"
    )
    calories: float | None = Field(None, description="Calories burned")
    heart_rate_avg: str | None = Field(None, description="Average HR (e.g., '145 bpm')")
    heart_rate_min: str | None = Field(None, description="Min HR")
    heart_rate_max: str | None = Field(None, description="Max HR")
    heart_rate_zone: str | None = Field(None, description="Dominant HR zone")
    heart_rate_samples: int | None = Field(
        None, description="Number of HR measurements"
    )
    heart_rate_zone_distribution: dict[str, int] | None = Field(
        None, description="Time in each zone"
    )
    last_workout: str | None = Field(
        None, description="Human-readable time since workout (e.g., '3 days ago')"
    )


class WorkoutStatsItem(BaseModel):
    """Aggregated workout statistics."""

    workout_type: str = Field(..., description="Workout type")
    total_count: int = Field(..., description="Number of workouts")
    total_duration_minutes: float = Field(..., description="Total minutes")
    total_calories: float = Field(..., description="Total calories burned")
    avg_duration_minutes: float = Field(..., description="Average workout duration")
    avg_calories: float = Field(..., description="Average calories per workout")


class WorkoutsResponse(BaseModel):
    """Complete response for workout search tool."""

    workouts: list[WorkoutItem] = Field(
        default_factory=list, description="Recent workouts (most recent first)"
    )
    workout_stats: list[WorkoutStatsItem] = Field(
        default_factory=list, description="Aggregated stats by type"
    )
    total_workouts: int = Field(default=0, description="Total workouts found")
    days_searched: int = Field(default=7, description="Days back searched")
    date_range: str = Field(..., description="Search date range description")
    error: str | None = Field(None, description="Error message if search failed")


# ========== Trend and Comparison Models ==========


class TrendResult(BaseModel):
    """Trend analysis for a metric over time."""

    metric_type: str = Field(..., description="Metric being analyzed")
    trend_direction: str = Field(
        ..., description="'increasing', 'decreasing', or 'stable'"
    )
    change_amount: float | None = Field(None, description="Numeric change value")
    change_percent: float | None = Field(None, description="Percent change")
    period: str = Field(..., description="Time period analyzed")
    data_points: int = Field(default=0, description="Number of data points")
    confidence: str = Field(
        default="medium", description="Confidence level: 'high', 'medium', 'low'"
    )


class ComparisonResult(BaseModel):
    """Comparison between two time periods."""

    metric_type: str = Field(..., description="Metric being compared")
    period1_avg: float = Field(..., description="Average for first period")
    period2_avg: float = Field(..., description="Average for second period")
    difference: float = Field(..., description="Absolute difference")
    percent_change: float = Field(..., description="Percent change")
    period1_label: str = Field(
        ..., description="First period label (e.g., 'Last 7 days')"
    )
    period2_label: str = Field(..., description="Second period label")


class TrendsResponse(BaseModel):
    """Response for trends and comparisons tool."""

    trends: list[TrendResult] = Field(
        default_factory=list, description="Trend analyses"
    )
    comparisons: list[ComparisonResult] = Field(
        default_factory=list, description="Period comparisons"
    )
    summary: str | None = Field(None, description="Human-readable summary")
    error: str | None = Field(None, description="Error message if analysis failed")


# ========== Progress Tracking Models ==========


class ProgressGoal(BaseModel):
    """Goal definition and current status."""

    metric_type: str = Field(..., description="Metric being tracked")
    goal_value: float = Field(..., description="Target value")
    current_value: float = Field(..., description="Current value")
    start_value: float | None = Field(None, description="Starting value")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    remaining: float = Field(..., description="Amount remaining to goal")
    on_track: bool = Field(..., description="Whether on track to meet goal")
    estimated_completion: str | None = Field(
        None, description="Estimated completion date"
    )


class ProgressResponse(BaseModel):
    """Response for progress tracking tool."""

    goals: list[ProgressGoal] = Field(default_factory=list, description="Goal progress")
    summary: str | None = Field(None, description="Overall progress summary")
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations for progress"
    )
    error: str | None = Field(None, description="Error message if tracking failed")


# ========== Statistics Models ==========


class StatisticResult(BaseModel):
    """Statistical calculation result."""

    metric_type: str = Field(..., description="Metric type")
    statistic: str = Field(
        ..., description="Statistic name (e.g., 'average', 'max', 'min')"
    )
    value: float | str = Field(..., description="Calculated value")
    unit: str | None = Field(None, description="Unit of measurement")
    period: str = Field(..., description="Time period")
    sample_count: int = Field(default=0, description="Number of data points")


class StatisticsResponse(BaseModel):
    """Response for statistics tool."""

    statistics: list[StatisticResult] = Field(
        default_factory=list, description="Calculated statistics"
    )
    summary: str | None = Field(None, description="Statistical summary")
    error: str | None = Field(None, description="Error message if calculation failed")


# ========== Workout Pattern Models ==========


class WorkoutPattern(BaseModel):
    """Identified workout pattern."""

    pattern_type: str = Field(
        ..., description="Pattern type (e.g., 'weekly_frequency', 'preferred_days')"
    )
    description: str = Field(..., description="Human-readable pattern description")
    frequency: float | None = Field(None, description="Frequency metric")
    days: list[str] | None = Field(None, description="Days involved in pattern")
    confidence: str = Field(default="medium", description="Pattern confidence")


class WorkoutPatternsResponse(BaseModel):
    """Response for workout patterns tool."""

    patterns: list[WorkoutPattern] = Field(
        default_factory=list, description="Identified patterns"
    )
    total_workouts_analyzed: int = Field(
        default=0, description="Total workouts analyzed"
    )
    analysis_period: str = Field(..., description="Time period analyzed")
    summary: str | None = Field(None, description="Pattern summary")
    error: str | None = Field(None, description="Error message if analysis failed")


# ========== Convenience Functions ==========


def create_error_response(
    error_message: str, error_type: str = "ToolError"
) -> dict[str, Any]:
    """
    Create standardized error response dict.

    Args:
        error_message: Error description
        error_type: Error category

    Returns:
        Dict with error structure
    """
    return ToolError(error=error_message, error_type=error_type).model_dump()


def create_empty_response(model_class: type[BaseModel]) -> dict[str, Any]:
    """
    Create empty response for a given model class.

    Args:
        model_class: Pydantic model class

    Returns:
        Dict with empty/default values
    """
    return model_class().model_dump()


# Export all models
__all__ = [
    # Base
    "ToolError",
    "ToolSuccess",
    # Health Records
    "HealthRecordItem",
    "HealthRecordResult",
    "HealthRecordsResponse",
    # Workouts
    "HeartRateStats",
    "WorkoutItem",
    "WorkoutStatsItem",
    "WorkoutsResponse",
    # Trends
    "TrendResult",
    "ComparisonResult",
    "TrendsResponse",
    # Progress
    "ProgressGoal",
    "ProgressResponse",
    # Statistics
    "StatisticResult",
    "StatisticsResponse",
    # Patterns
    "WorkoutPattern",
    "WorkoutPatternsResponse",
    # Utilities
    "create_error_response",
    "create_empty_response",
]
