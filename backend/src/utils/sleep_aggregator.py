"""Sleep data aggregation utilities.

Aggregate Apple Health sleep segments into daily sleep summaries.
Apple Health records sleep as multiple segments per night (InBed, Asleep, Awake, etc.),
so we need to aggregate them to get meaningful sleep metrics.
"""

from collections import defaultdict
from datetime import datetime

from ..apple_health.models import SleepSegment, SleepState, SleepSummary
from ..config import get_settings
from .time_utils import convert_utc_to_user_timezone


def aggregate_sleep_by_date(sleep_segments: list[SleepSegment]) -> list[SleepSummary]:
    """
    Aggregate sleep segments into daily summaries.

    Groups segments by date and calculates total sleep hours, in-bed time,
    and sleep efficiency for each day.

    Args:
        sleep_segments: List of SleepSegment objects with start/end times

    Returns:
        List of SleepSummary objects, one per day with sleep data

    Example:
        >>> segments = [
        ...     SleepSegment(
        ...         state="HKCategoryValueSleepAnalysisInBed",
        ...         start_date=datetime(2025, 10, 20, 1, 0, tzinfo=UTC),
        ...         end_date=datetime(2025, 10, 20, 8, 0, tzinfo=UTC),
        ...         duration_hours=7.0
        ...     ),
        ...     SleepSegment(
        ...         state="HKCategoryValueSleepAnalysisAsleepUnspecified",
        ...         start_date=datetime(2025, 10, 20, 1, 15, tzinfo=UTC),
        ...         end_date=datetime(2025, 10, 20, 7, 30, tzinfo=UTC),
        ...         duration_hours=6.25
        ...     )
        ... ]
        >>> summaries = aggregate_sleep_by_date(segments)
        >>> summaries[0].total_sleep_hours
        6.25
        >>> summaries[0].total_in_bed_hours
        7.0
    """
    # Group segments by date (use date of sleep end, as that's typically morning)
    daily_segments = defaultdict(list)

    for segment in sleep_segments:
        # Use end_date for grouping (when you wake up determines the "day")
        date_key = segment.end_date.date().isoformat()
        daily_segments[date_key].append(segment)

    # Create summaries for each date
    summaries = []

    for date_str in sorted(daily_segments.keys()):
        segments = daily_segments[date_str]
        summary = _create_daily_summary(date_str, segments)
        summaries.append(summary)

    return summaries


def _create_daily_summary(date_str: str, segments: list[SleepSegment]) -> SleepSummary:
    """
    Create a single daily sleep summary from segments.

    Calculates total sleep hours, in-bed time, and optional detailed breakdown.

    Args:
        date_str: Date string in YYYY-MM-DD format
        segments: All sleep segments for this date

    Returns:
        SleepSummary with aggregated metrics
    """
    # Initialize accumulators
    in_bed_segments = []
    total_asleep = 0.0
    total_deep = 0.0
    total_rem = 0.0
    total_core = 0.0
    total_awake = 0.0
    total_asleep_unspecified = 0.0

    first_sleep: datetime | None = None
    last_wake: datetime | None = None

    # First pass: collect segments by type
    has_detailed_stages = False
    for segment in segments:
        state = segment.state

        # Track time boundaries
        if first_sleep is None or segment.start_date < first_sleep:
            first_sleep = segment.start_date
        if last_wake is None or segment.end_date > last_wake:
            last_wake = segment.end_date

        # Check if we have detailed sleep stages
        if state in [
            SleepState.ASLEEP_CORE.value,
            SleepState.ASLEEP_DEEP.value,
            SleepState.ASLEEP_REM.value,
        ]:
            has_detailed_stages = True

        # Collect InBed segments separately
        if state == SleepState.IN_BED.value:
            in_bed_segments.append(segment)
        elif state == SleepState.ASLEEP_UNSPECIFIED.value:
            total_asleep_unspecified += segment.duration_hours
        elif state == SleepState.ASLEEP_DEEP.value:
            total_deep += segment.duration_hours
        elif state == SleepState.ASLEEP_REM.value:
            total_rem += segment.duration_hours
        elif state == SleepState.ASLEEP_CORE.value:
            total_core += segment.duration_hours
        elif state == SleepState.AWAKE.value:
            total_awake += segment.duration_hours

    # Calculate total in_bed time from InBed segments
    total_in_bed = sum(seg.duration_hours for seg in in_bed_segments)

    # Calculate total asleep time
    # If we have detailed stages, use them; otherwise use AsleepUnspecified
    if has_detailed_stages:
        total_asleep = total_deep + total_rem + total_core
    else:
        # No detailed stages, use AsleepUnspecified
        total_asleep = total_asleep_unspecified

    # Calculate sleep efficiency (if we have both metrics)
    sleep_efficiency = None
    if total_in_bed > 0:
        sleep_efficiency = round((total_asleep / total_in_bed) * 100, 1)

    # Format times in user's timezone (convert from UTC)
    settings = get_settings()
    first_sleep_time = None
    last_wake_time = None

    if first_sleep:
        local_first_sleep = convert_utc_to_user_timezone(
            first_sleep, settings.user_timezone
        )
        first_sleep_time = local_first_sleep.strftime("%H:%M")

    if last_wake:
        local_last_wake = convert_utc_to_user_timezone(
            last_wake, settings.user_timezone
        )
        last_wake_time = local_last_wake.strftime("%H:%M")

    return SleepSummary(
        date=date_str,
        total_sleep_hours=round(total_asleep, 2),
        total_in_bed_hours=round(total_in_bed, 2),
        sleep_efficiency=sleep_efficiency,
        deep_sleep_hours=round(total_deep, 2) if total_deep > 0 else None,
        rem_sleep_hours=round(total_rem, 2) if total_rem > 0 else None,
        core_sleep_hours=round(total_core, 2) if total_core > 0 else None,
        awake_hours=round(total_awake, 2) if total_awake > 0 else None,
        segment_count=len(segments),
        first_sleep_time=first_sleep_time,
        last_wake_time=last_wake_time,
    )


def parse_sleep_segments_from_records(records: list[dict]) -> list[SleepSegment]:
    """
    Parse sleep segments from raw health records.

    Converts raw sleep analysis records (with start/end dates and state)
    into SleepSegment objects.

    Args:
        records: List of health records with date, value (state), source

    Returns:
        List of SleepSegment objects

    Example:
        >>> records = [{
        ...     "date": "2025-10-20T08:00:00+00:00",
        ...     "value": "HKCategoryValueSleepAnalysisInBed",
        ...     "source": "Watch",
        ...     "start_date": "2025-10-20T01:00:00+00:00",
        ...     "end_date": "2025-10-20T08:00:00+00:00"
        ... }]
        >>> segments = parse_sleep_segments_from_records(records)
        >>> segments[0].duration_hours
        7.0
    """
    from ..utils.time_utils import parse_health_record_date

    segments = []

    for record in records:
        # Parse dates using time_utils to ensure proper UTC handling
        start_date = parse_health_record_date(record.get("start_date", record["date"]))
        end_date = parse_health_record_date(record.get("end_date", record["date"]))

        # Calculate duration
        duration_seconds = (end_date - start_date).total_seconds()
        duration_hours = duration_seconds / 3600

        segment = SleepSegment(
            state=record["value"],
            start_date=start_date,
            end_date=end_date,
            duration_hours=duration_hours,
            source_name=record.get("source"),
        )

        segments.append(segment)

    return segments
