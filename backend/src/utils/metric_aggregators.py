"""Daily aggregation strategies for health metrics before statistical analysis."""

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .metric_classifier import AggregationStrategy, get_aggregation_strategy
from .time_utils import parse_health_record_date as _parse_health_record_date_tz


def _parse_health_record_date_naive(date_str: str) -> datetime:
    """
    Parse health record date to naive datetime for aggregation comparisons.

    Uses the canonical parse_health_record_date from time_utils but converts
    to naive datetime for comparison with normalized date ranges.

    Args:
        date_str: Date string in format "YYYY-MM-DD HH:MM:SS"

    Returns:
        Naive datetime object for comparison
    """
    dt = _parse_health_record_date_tz(date_str, assume_utc=True)
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _normalize_date_range(
    date_range: tuple[datetime, datetime],
) -> tuple[datetime, datetime]:
    """
    Convert timezone-aware datetime range to naive for health record comparison.

    Args:
        date_range: (start_date, end_date) tuple, potentially timezone-aware

    Returns:
        (start_date, end_date) tuple with naive datetimes
    """
    filter_start, filter_end = date_range

    # Convert timezone-aware datetimes to naive for comparison with health records
    # Use the canonical parse_health_record_date for consistent handling
    if filter_start.tzinfo is not None:
        filter_start = filter_start.replace(tzinfo=None)
    if filter_end.tzinfo is not None:
        filter_end = filter_end.replace(tzinfo=None)

    return filter_start, filter_end


def aggregate_daily_sums(
    records: list[dict[str, Any]], date_range: tuple[datetime, datetime]
) -> dict[date, float]:
    """
    Aggregate records by summing all values per day.

    Used for cumulative metrics like StepCount, DistanceWalkingRunning.

    Args:
        records: List of health records
        date_range: (start_date, end_date) tuple

    Returns:
        Dictionary mapping date to daily total

    Example:
        # StepCount records: [250, 488, 686] steps on 2025-10-17
        # Returns: {date(2025, 10, 17): 1424.0}
    """
    filter_start, filter_end = _normalize_date_range(date_range)
    daily_totals = defaultdict(float)

    for record in records:
        try:
            record_date = _parse_health_record_date_naive(record["date"])
            if filter_start <= record_date <= filter_end:
                value = float(record["value"])
                date_key = record_date.date()
                daily_totals[date_key] += value
        except (ValueError, TypeError, KeyError):
            continue

    return dict(daily_totals)


def aggregate_daily_averages(
    records: list[dict[str, Any]], date_range: tuple[datetime, datetime]
) -> dict[date, float]:
    """
    Aggregate records by averaging all values per day.

    Used for high-frequency point metrics like HeartRate.

    Args:
        records: List of health records
        date_range: (start_date, end_date) tuple

    Returns:
        Dictionary mapping date to daily average

    Example:
        # HeartRate records: [81, 87, 77, 77, 77] bpm on 2025-10-17
        # Returns: {date(2025, 10, 17): 79.8}
    """
    filter_start, filter_end = _normalize_date_range(date_range)
    daily_values = defaultdict(list)

    for record in records:
        try:
            record_date = _parse_health_record_date_naive(record["date"])
            if filter_start <= record_date <= filter_end:
                value = float(record["value"])
                date_key = record_date.date()
                daily_values[date_key].append(value)
        except (ValueError, TypeError, KeyError):
            continue

    # Calculate averages
    daily_averages = {}
    for date_key, values in daily_values.items():
        if values:
            daily_averages[date_key] = sum(values) / len(values)

    return daily_averages


def aggregate_daily_latest(
    records: list[dict[str, Any]], date_range: tuple[datetime, datetime]
) -> dict[date, float]:
    """
    Aggregate records by taking the latest value per day.

    Used for measurements like BodyMass where multiple readings per day
    should use the most recent (latest) value.

    Args:
        records: List of health records
        date_range: (start_date, end_date) tuple

    Returns:
        Dictionary mapping date to latest daily value

    Example:
        # BodyMass records: [138.6, 137.2, 137.6] lbs on 2025-10-17
        # Returns: {date(2025, 10, 17): 137.6} (latest reading)
    """
    filter_start, filter_end = _normalize_date_range(date_range)
    daily_values = defaultdict(list)

    # Collect all values with timestamps per day
    for record in records:
        try:
            record_date = _parse_health_record_date_naive(record["date"])
            if filter_start <= record_date <= filter_end:
                value = float(record["value"])
                date_key = record_date.date()
                daily_values[date_key].append((record_date.time(), value))
        except (ValueError, TypeError, KeyError):
            continue

    # Take latest value per day
    daily_latest = {}
    for date_key, time_value_pairs in daily_values.items():
        if time_value_pairs:
            # Sort by time and take the latest (last) value
            time_value_pairs.sort(key=lambda x: x[0])
            latest_value = time_value_pairs[-1][1]
            daily_latest[date_key] = latest_value

    return daily_latest


def get_individual_values(
    records: list[dict[str, Any]], date_range: tuple[datetime, datetime]
) -> list[float]:
    """
    Extract individual values directly without daily aggregation.

    Used for metrics like BodyMassIndex, ActiveEnergyBurned where each
    reading is a complete measurement.

    Args:
        records: List of health records
        date_range: (start_date, end_date) tuple

    Returns:
        List of individual values

    Example:
        # BMI records: [23.9, 23.7, 23.8, 24.2] BMI values
        # Returns: [23.9, 23.7, 23.8, 24.2]
    """
    filter_start, filter_end = _normalize_date_range(date_range)
    values = []

    for record in records:
        try:
            record_date = _parse_health_record_date_naive(record["date"])
            if filter_start <= record_date <= filter_end:
                value = float(record["value"])
                values.append(value)
        except (ValueError, TypeError, KeyError):
            continue

    return values


def aggregate_metric_values(
    records: list[dict[str, Any]],
    metric_type: str,
    date_range: tuple[datetime, datetime],
) -> list[float]:
    """
    Apply metric-specific aggregation strategy and return values for statistics.

    This is the main entry point that automatically selects the appropriate
    aggregation method based on the metric type.

    Args:
        records: List of health records
        metric_type: Type of metric (e.g., "StepCount", "BodyMass")
        date_range: (start_date, end_date) tuple

    Returns:
        List of aggregated values ready for statistical calculations

    Examples:
        # StepCount: Returns daily totals [20646, 6918, 2980]
        # HeartRate: Returns daily averages [79.8, 82.1, 75.4]
        # BodyMass: Returns daily latest values [137.6, 138.2, 137.1]
        # BodyMassIndex: Returns individual readings [23.9, 23.7, 23.8]
    """
    strategy = get_aggregation_strategy(metric_type)

    if strategy == AggregationStrategy.CUMULATIVE:
        daily_totals = aggregate_daily_sums(records, date_range)
        return list(daily_totals.values())

    elif strategy == AggregationStrategy.DAILY_AVERAGE:
        daily_averages = aggregate_daily_averages(records, date_range)
        return list(daily_averages.values())

    elif strategy == AggregationStrategy.LATEST_VALUE:
        daily_latest = aggregate_daily_latest(records, date_range)
        return list(daily_latest.values())

    elif strategy == AggregationStrategy.INDIVIDUAL:
        return get_individual_values(records, date_range)

    else:
        # Fallback to individual values for unknown strategies
        return get_individual_values(records, date_range)


def get_aggregation_summary(
    records: list[dict[str, Any]],
    metric_type: str,
    date_range: tuple[datetime, datetime],
) -> dict[str, Any]:
    """
    Get aggregation summary with metadata for logging and debugging.

    Args:
        records: List of health records
        metric_type: Type of metric
        date_range: Date range tuple

    Returns:
        Dictionary with aggregation metadata
    """
    strategy = get_aggregation_strategy(metric_type)
    aggregated_values = aggregate_metric_values(records, metric_type, date_range)

    filter_start, filter_end = _normalize_date_range(date_range)

    # Count original records in date range
    original_count = 0
    for record in records:
        try:
            record_date = _parse_health_record_date_naive(record["date"])
            if filter_start <= record_date <= filter_end:
                original_count += 1
        except (ValueError, TypeError, KeyError):
            continue

    return {
        "metric_type": metric_type,
        "strategy": strategy.value,
        "original_records": original_count,
        "aggregated_values": len(aggregated_values),
        "date_range": f"{filter_start.date()} to {filter_end.date()}",
        "sample_values": aggregated_values[:3] if aggregated_values else [],
        "reduction_ratio": (
            original_count / len(aggregated_values) if aggregated_values else 0
        ),
    }
