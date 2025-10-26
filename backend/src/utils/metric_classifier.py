"""Metric classification for health data aggregation strategies."""

from enum import Enum


class AggregationStrategy(str, Enum):
    """Aggregation strategies for different metric types."""

    CUMULATIVE = "cumulative"  # Sum per day (StepCount, Distance)
    DAILY_AVERAGE = "daily_average"  # Average per day (HeartRate)
    LATEST_VALUE = "latest_value"  # Latest reading per day (BodyMass)
    INDIVIDUAL = "individual"  # Use readings directly (BMI, ActiveEnergy)


# Metric classification based on data analysis
CUMULATIVE_METRICS: set[str] = {
    "StepCount",  # Sum incremental step readings throughout day
    "DistanceWalkingRunning",  # Sum distance segments throughout day
    "DietaryWater",  # Sum water intake throughout day
    "DietaryEnergyConsumed",  # Sum calories consumed throughout day
    "AppleExerciseTime",  # Sum exercise minutes throughout day
    "AppleStandHours",  # Sum stand hours throughout day
}

HIGH_FREQ_POINT_METRICS: set[str] = {
    "HeartRate",  # Average ~239 readings per day
    "RespiratoryRate",  # Average multiple readings per day
    "BloodPressureSystolic",  # Average multiple readings per day
    "BloodPressureDiastolic",  # Average multiple readings per day
}

LATEST_VALUE_METRICS: set[str] = {
    "BodyMass",  # Latest weight reading per day (scale readings)
    "Height",  # Latest height (rarely changes)
    "BodyFatPercentage",  # Latest body fat reading per day
    "LeanBodyMass",  # Latest lean mass reading per day
}

INDIVIDUAL_METRICS: set[str] = {
    "BodyMassIndex",  # Each BMI calculation is complete
    "ActiveEnergyBurned",  # Each workout energy burn is complete
    "BasalEnergyBurned",  # Each basal metabolic reading is complete
    "VO2Max",  # Each VO2 max test is complete
    "RestingHeartRate",  # Each daily resting HR is complete
}


def get_aggregation_strategy(metric_type: str) -> AggregationStrategy:
    """
    Determine the appropriate aggregation strategy for a metric type.

    Args:
        metric_type: Health metric type (e.g., "StepCount", "BodyMass")

    Returns:
        AggregationStrategy enum value

    Examples:
        get_aggregation_strategy("StepCount") → AggregationStrategy.CUMULATIVE
        get_aggregation_strategy("BodyMass") → AggregationStrategy.LATEST_VALUE
        get_aggregation_strategy("HeartRate") → AggregationStrategy.DAILY_AVERAGE
    """
    if metric_type in CUMULATIVE_METRICS:
        return AggregationStrategy.CUMULATIVE
    elif metric_type in HIGH_FREQ_POINT_METRICS:
        return AggregationStrategy.DAILY_AVERAGE
    elif metric_type in LATEST_VALUE_METRICS:
        return AggregationStrategy.LATEST_VALUE
    elif metric_type in INDIVIDUAL_METRICS:
        return AggregationStrategy.INDIVIDUAL
    else:
        # Default fallback: treat unknown metrics as individual readings
        # This is the safest approach for unknown metric types
        return AggregationStrategy.INDIVIDUAL


def should_aggregate_daily(metric_type: str) -> bool:
    """
    Check if a metric type requires daily pre-aggregation.

    Args:
        metric_type: Health metric type

    Returns:
        True if metric needs daily aggregation before statistics

    Examples:
        should_aggregate_daily("StepCount") → True (sum per day first)
        should_aggregate_daily("BodyMassIndex") → False (use readings directly)
    """
    strategy = get_aggregation_strategy(metric_type)
    return strategy in {
        AggregationStrategy.CUMULATIVE,
        AggregationStrategy.DAILY_AVERAGE,
        AggregationStrategy.LATEST_VALUE,
    }


def get_expected_unit_format(metric_type: str) -> str:
    """
    Get the expected unit format for display.

    Args:
        metric_type: Health metric type

    Returns:
        Expected unit format for user display
    """
    unit_formats = {
        "StepCount": "steps",
        "DistanceWalkingRunning": "mi",
        "HeartRate": "bpm",
        "RestingHeartRate": "bpm",
        "BodyMass": "lbs",
        "BodyMassIndex": "BMI",
        "ActiveEnergyBurned": "Cal",
        "DietaryEnergyConsumed": "Cal",
        "DietaryWater": "fl oz",
    }
    return unit_formats.get(metric_type, "")


def get_aggregation_description(metric_type: str) -> str:
    """
    Get human-readable description of how a metric is aggregated.

    Args:
        metric_type: Health metric type

    Returns:
        Description of aggregation method
    """
    strategy = get_aggregation_strategy(metric_type)

    descriptions = {
        AggregationStrategy.CUMULATIVE: f"{metric_type} totaled per day, then statistics on daily totals",
        AggregationStrategy.DAILY_AVERAGE: f"{metric_type} averaged per day, then statistics on daily averages",
        AggregationStrategy.LATEST_VALUE: f"Latest {metric_type} reading per day, then statistics on daily values",
        AggregationStrategy.INDIVIDUAL: f"Statistics calculated on individual {metric_type} readings",
    }

    return descriptions[strategy]


# Validation - ensure no metric is classified in multiple categories
def _validate_classifications():
    """Validate that metric classifications don't overlap."""
    all_sets = [
        CUMULATIVE_METRICS,
        HIGH_FREQ_POINT_METRICS,
        LATEST_VALUE_METRICS,
        INDIVIDUAL_METRICS,
    ]

    # Check for overlaps
    all_metrics = set()
    for metric_set in all_sets:
        overlap = all_metrics.intersection(metric_set)
        if overlap:
            raise ValueError(f"Metric classification overlap found: {overlap}")
        all_metrics.update(metric_set)


# Run validation on import
_validate_classifications()
