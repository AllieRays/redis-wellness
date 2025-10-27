"""
Privacy-first health data models for Apple Health XML parsing.

This module defines Pydantic models for parsing Apple Health data with
built-in privacy protections and data minimization principles.
"""

import hashlib
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PrivacyLevel(str, Enum):
    """Privacy classification for health data fields."""

    PUBLIC = "public"  # Safe to display (e.g., metric type)
    SENSITIVE = "sensitive"  # Health values (e.g., BMI, weight)
    PERSONAL = "personal"  # Identifying info (e.g., device name)
    PRIVATE = "private"  # Internal processing only


class HealthMetricType(str, Enum):
    """Common Apple Health metric types for wellness focus."""

    # Physical metrics
    BODY_MASS_INDEX = "HKQuantityTypeIdentifierBodyMassIndex"
    BODY_MASS = "HKQuantityTypeIdentifierBodyMass"
    HEIGHT = "HKQuantityTypeIdentifierHeight"

    # Activity metrics
    STEPS = "HKQuantityTypeIdentifierStepCount"
    DISTANCE_WALKING = "HKQuantityTypeIdentifierDistanceWalkingRunning"
    ACTIVE_ENERGY = "HKQuantityTypeIdentifierActiveEnergyBurned"

    # Nutrition
    DIETARY_WATER = "HKQuantityTypeIdentifierDietaryWater"
    DIETARY_ENERGY = "HKQuantityTypeIdentifierDietaryEnergyConsumed"

    # Sleep & Recovery
    SLEEP_ANALYSIS = "HKCategoryTypeIdentifierSleepAnalysis"
    HEART_RATE = "HKQuantityTypeIdentifierHeartRate"
    RESTING_HEART_RATE = "HKQuantityTypeIdentifierRestingHeartRate"

    # Other metrics (fallback)
    OTHER = "other"


class HealthRecord(BaseModel):
    """
    Individual health record with privacy protection.

    Maps to Apple Health <Record> XML elements.
    Privacy: Contains sensitive health data.
    """

    # Public fields - safe to display
    record_type: HealthMetricType = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )
    unit: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )

    # Sensitive fields - health data
    value: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    start_date: datetime = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    end_date: datetime = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )

    # Personal fields - can be anonymized
    source_name: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PERSONAL}
    )
    source_version: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PERSONAL}
    )
    device: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PERSONAL}
    )
    creation_date: datetime | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PERSONAL}
    )

    # Private fields - internal use only
    raw_metadata: dict[str, Any] | None = Field(
        default_factory=dict, json_schema_extra={"privacy_level": PrivacyLevel.PRIVATE}
    )

    @field_validator("record_type", mode="before")
    @classmethod
    def normalize_record_type(cls, v):
        """Normalize record type to enum, fallback to OTHER for unknown types."""
        if isinstance(v, str):
            try:
                return HealthMetricType(v)
            except ValueError:
                return HealthMetricType.OTHER
        return v

    def anonymize(self) -> "HealthRecord":
        """
        Create anonymized version by hashing/removing personal data.

        Returns:
            New HealthRecord with personal fields anonymized
        """
        anonymized_data = self.dict()

        # Hash personal identifiers
        if self.source_name:
            anonymized_data["source_name"] = self._hash_field(self.source_name)
        if self.device:
            anonymized_data["device"] = self._hash_field(self.device)

        # Remove precise timestamps (keep date only)
        anonymized_data["start_date"] = self.start_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        anonymized_data["end_date"] = self.end_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Clear private metadata
        anonymized_data["raw_metadata"] = {}

        return HealthRecord(**anonymized_data)

    def _hash_field(self, value: str) -> str:
        """Create consistent hash of sensitive field."""
        return hashlib.sha256(value.encode()).hexdigest()[:8]

    def to_conversation_context(self) -> str:
        """
        Safe representation for AI conversation context.
        Excludes personal/private data.
        """
        context_parts = []

        # Include metric type and value (core health data)
        metric_name = self.record_type.value.replace("HKQuantityTypeIdentifier", "")
        if self.value and self.unit:
            context_parts.append(f"{metric_name}: {self.value} {self.unit}")

        # Include date (anonymized to day level)
        date_str = self.start_date.strftime("%Y-%m-%d")
        context_parts.append(f"Date: {date_str}")

        return " | ".join(context_parts)


class SleepState(str, Enum):
    """Sleep states from Apple Health sleep analysis."""

    IN_BED = "HKCategoryValueSleepAnalysisInBed"
    ASLEEP_UNSPECIFIED = "HKCategoryValueSleepAnalysisAsleepUnspecified"
    ASLEEP_CORE = "HKCategoryValueSleepAnalysisAsleepCore"
    ASLEEP_DEEP = "HKCategoryValueSleepAnalysisAsleepDeep"
    ASLEEP_REM = "HKCategoryValueSleepAnalysisAsleepREM"
    AWAKE = "HKCategoryValueSleepAnalysisAwake"


class SleepSegment(BaseModel):
    """
    Individual sleep segment with start/end times and sleep state.

    Apple Health records sleep as multiple segments per night.
    Each segment has a sleep state (InBed, Asleep, Awake, etc.).
    """

    # Public fields
    state: str = Field(..., json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC})

    # Sensitive fields - sleep timing data
    start_date: datetime = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    end_date: datetime = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    duration_hours: float = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )

    # Personal fields
    source_name: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PERSONAL}
    )

    @field_validator("duration_hours", mode="before")
    @classmethod
    def calculate_duration(cls, v, info):
        """Calculate duration from start/end dates if not provided."""
        if v is not None:
            return v
        if info.data.get("start_date") and info.data.get("end_date"):
            start = info.data["start_date"]
            end = info.data["end_date"]
            duration_seconds = (end - start).total_seconds()
            return duration_seconds / 3600  # Convert to hours
        return 0.0


class SleepSummary(BaseModel):
    """
    Daily sleep summary aggregated from multiple segments.

    Provides a consolidated view of sleep for a single night/day.
    """

    # Public fields
    date: str = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )  # YYYY-MM-DD format

    # Sensitive sleep metrics
    total_sleep_hours: float = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    total_in_bed_hours: float = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    sleep_efficiency: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )  # Sleep / InBed ratio

    # Optional detailed breakdown
    deep_sleep_hours: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    rem_sleep_hours: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    core_sleep_hours: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    awake_hours: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )

    # Metadata
    segment_count: int = Field(
        0, json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )
    first_sleep_time: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )  # HH:MM format
    last_wake_time: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )  # HH:MM format

    @field_validator("sleep_efficiency", mode="before")
    @classmethod
    def calculate_efficiency(cls, v, info):
        """Calculate sleep efficiency from sleep/in_bed hours."""
        if v is not None:
            return v
        if (
            info.data.get("total_sleep_hours") is not None
            and info.data.get("total_in_bed_hours") is not None
        ):
            in_bed = info.data["total_in_bed_hours"]
            if in_bed > 0:
                sleep = info.data["total_sleep_hours"]
                return round((sleep / in_bed) * 100, 1)
        return None


class WorkoutSummary(BaseModel):
    """
    Workout data with privacy protection.

    Maps to Apple Health <Workout> XML elements.
    """

    # Public fields
    workout_activity_type: str = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )
    duration_unit: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )

    # Sensitive fields
    duration: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    total_distance: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    total_energy_burned: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    start_date: datetime = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    end_date: datetime = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )

    # Personal fields
    source_name: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PERSONAL}
    )
    device: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PERSONAL}
    )


class ActivitySummary(BaseModel):
    """
    Daily activity summary with privacy protection.

    Maps to Apple Health <ActivitySummary> XML elements.
    """

    # Public fields
    date_components: date = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )

    # Sensitive activity data
    active_energy_burned: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    active_energy_burned_goal: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    apple_exercise_time: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    apple_exercise_time_goal: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    apple_stand_hours: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )
    apple_stand_hours_goal: float | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE}
    )


class UserProfile(BaseModel):
    """
    Basic user profile derived from Apple Health Me element.
    Highly privacy-sensitive.
    """

    # All fields are personal/private - no public health profile data
    date_of_birth: date | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PRIVATE}
    )
    biological_sex: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PRIVATE}
    )
    blood_type: str | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PRIVATE}
    )

    def anonymize(self) -> "UserProfile":
        """Create fully anonymized profile (removes all personal data)."""
        return UserProfile()


class HealthDataCollection(BaseModel):
    """
    Complete parsed health data collection with privacy controls.

    Main container for all parsed Apple Health data.
    """

    # Export metadata
    export_date: datetime = Field(
        ..., json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )
    record_count: int = Field(
        0, json_schema_extra={"privacy_level": PrivacyLevel.PUBLIC}
    )

    # User data (highly sensitive)
    user_profile: UserProfile | None = Field(
        None, json_schema_extra={"privacy_level": PrivacyLevel.PRIVATE}
    )

    # Health records (sensitive)
    records: list[HealthRecord] = Field(
        default_factory=list,
        json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE},
    )
    workouts: list[WorkoutSummary] = Field(
        default_factory=list,
        json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE},
    )
    sleep_summaries: list[SleepSummary] = Field(
        default_factory=list,
        json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE},
    )
    activity_summaries: list[ActivitySummary] = Field(
        default_factory=list,
        json_schema_extra={"privacy_level": PrivacyLevel.SENSITIVE},
    )

    def get_records_by_type(self, metric_type: HealthMetricType) -> list[HealthRecord]:
        """Get all records of a specific type."""
        return [r for r in self.records if r.record_type == metric_type]

    def get_recent_records(self, days: int = 30) -> list[HealthRecord]:
        """
        Get records from last N days.

        Note: Parser normalizes all datetimes to UTC, so we use UTC for comparison.
        """

        cutoff = datetime.now(UTC) - timedelta(days=days)
        return [r for r in self.records if r.start_date >= cutoff]

    def anonymize_all(self) -> "HealthDataCollection":
        """Create fully anonymized version of health data."""
        anonymized_records = [record.anonymize() for record in self.records]
        anonymized_profile = (
            self.user_profile.anonymize() if self.user_profile else None
        )

        return HealthDataCollection(
            export_date=self.export_date,
            record_count=len(anonymized_records),
            user_profile=anonymized_profile,
            records=anonymized_records,
            workouts=self.workouts,  # Workouts keep device info but could be anonymized too
            sleep_summaries=self.sleep_summaries,
            activity_summaries=self.activity_summaries,
        )

    def to_conversation_summary(self, limit: int = 10) -> str:
        """
        Create safe summary for AI conversation context.
        Only includes essential health metrics, no personal data.
        """
        if not self.records:
            return "No health data available"

        # Get diverse recent records for context
        recent_records = self.get_recent_records(days=30)
        context_records = recent_records[:limit]

        summaries = [record.to_conversation_context() for record in context_records]
        return f"Recent health data ({len(summaries)} records): " + " || ".join(
            summaries
        )


# Import protection
__all__ = [
    "PrivacyLevel",
    "HealthMetricType",
    "HealthRecord",
    "SleepState",
    "SleepSegment",
    "SleepSummary",
    "WorkoutSummary",
    "ActivitySummary",
    "UserProfile",
    "HealthDataCollection",
]
