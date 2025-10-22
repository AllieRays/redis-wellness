"""
Time parsing utilities for natural language date/time descriptions.

All datetime operations use UTC. Frontend is responsible for timezone
conversion and display to support global users.
"""

import re
from datetime import UTC, datetime, timedelta

# Default timeframe for "recent" queries
DEFAULT_RECENT_DAYS = 30


def parse_time_period(time_period: str) -> tuple[datetime, datetime, str]:
    """
    Parse natural language time descriptions into UTC date ranges.

    Args:
        time_period: Natural language time description (e.g., "last week", "September")

    Returns:
        Tuple of (start_date_utc, end_date_utc, description)

    Examples:
        >>> parse_time_period("last week")
        (datetime(2025, 10, 14, tzinfo=UTC), datetime(2025, 10, 21, tzinfo=UTC), 'Last 7 days')
    """
    # Get current time in UTC (timezone-agnostic backend)
    now_utc = datetime.now(UTC)
    time_period_lower = time_period.lower().strip()

    # Month names mapping
    months = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sept": 9,
        "sep": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    # Pattern 1: "September" or "September 2025"
    month_year_pattern = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dec)\s*(\d{4})?"
    match = re.search(month_year_pattern, time_period_lower)

    if match:
        month_name = match.group(1)
        year_str = match.group(2)

        month_num = months[month_name]
        year = int(year_str) if year_str else now_utc.year

        # Create dates in UTC (timezone-agnostic)
        # Check for qualifiers (early, mid, late)
        if "early" in time_period_lower:
            start_date = datetime(year, month_num, 1, tzinfo=UTC)
            end_date = datetime(year, month_num, 10, 23, 59, 59, tzinfo=UTC)
            desc = f"Early {month_name.capitalize()} {year}"
        elif "mid" in time_period_lower or "middle" in time_period_lower:
            start_date = datetime(year, month_num, 11, tzinfo=UTC)
            end_date = datetime(year, month_num, 20, 23, 59, 59, tzinfo=UTC)
            desc = f"Mid {month_name.capitalize()} {year}"
        elif "late" in time_period_lower or "end" in time_period_lower:
            start_date = datetime(year, month_num, 21, tzinfo=UTC)
            # Last day of month
            if month_num == 12:
                end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=UTC)
            else:
                end_date = datetime(year, month_num + 1, 1, tzinfo=UTC) - timedelta(
                    seconds=1
                )
            desc = f"Late {month_name.capitalize()} {year}"
        else:
            # Full month
            start_date = datetime(year, month_num, 1, tzinfo=UTC)
            if month_num == 12:
                end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=UTC)
            else:
                end_date = datetime(year, month_num + 1, 1, tzinfo=UTC) - timedelta(
                    seconds=1
                )
            desc = f"{month_name.capitalize()} {year}"

        return start_date, end_date, desc

    # Pattern 2: "last N days/weeks/months"
    relative_pattern = r"last\s+(\d+)\s+(day|week|month)s?"
    match = re.search(relative_pattern, time_period_lower)

    if match:
        num = int(match.group(1))
        unit = match.group(2)

        if unit == "day":
            start_date = now_utc - timedelta(days=num)
            desc = f"Last {num} day{'s' if num > 1 else ''}"
        elif unit == "week":
            start_date = now_utc - timedelta(weeks=num)
            desc = f"Last {num} week{'s' if num > 1 else ''}"
        elif unit == "month":
            start_date = now_utc - timedelta(days=num * 30)  # Approximate
            desc = f"Last {num} month{'s' if num > 1 else ''}"

        return start_date, now_utc, desc

    # Pattern 3: "this week/month/year"
    if "this week" in time_period_lower:
        start_date = now_utc - timedelta(days=now_utc.weekday())  # Monday
        return start_date, now_utc, "This week"

    if "this month" in time_period_lower:
        start_date = datetime(now_utc.year, now_utc.month, 1, tzinfo=UTC)
        return start_date, now_utc, f"This month ({now_utc.strftime('%B %Y')})"

    if "this year" in time_period_lower:
        start_date = datetime(now_utc.year, 1, 1, tzinfo=UTC)
        return start_date, now_utc, f"This year ({now_utc.year})"

    # Pattern 4: "last week/month/year"
    if "last week" in time_period_lower:
        # Start from last Monday in UTC
        days_since_monday = now_utc.weekday()
        last_monday = now_utc - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        return last_monday, last_sunday, "Last week"

    if "last month" in time_period_lower:
        # Previous month in UTC
        if now_utc.month == 1:
            prev_month = 12
            prev_year = now_utc.year - 1
        else:
            prev_month = now_utc.month - 1
            prev_year = now_utc.year

        start_date = datetime(prev_year, prev_month, 1, tzinfo=UTC)
        if prev_month == 12:
            end_date = datetime(prev_year, 12, 31, 23, 59, 59, tzinfo=UTC)
        else:
            end_date = datetime(prev_year, prev_month + 1, 1, tzinfo=UTC) - timedelta(
                seconds=1
            )

        month_name = datetime(prev_year, prev_month, 1, tzinfo=UTC).strftime("%B %Y")
        return start_date, end_date, f"Last month ({month_name})"

    # Default: "recent" or anything else → last N days
    start_date = now_utc - timedelta(days=DEFAULT_RECENT_DAYS)
    return start_date, now_utc, f"Last {DEFAULT_RECENT_DAYS} days (recent)"


def format_datetime_utc(utc_datetime: datetime) -> str:
    """
    Format datetime as ISO 8601 UTC string.

    Args:
        utc_datetime: Datetime in UTC timezone

    Returns:
        ISO 8601 string in UTC

    Examples:
        >>> format_datetime_utc(datetime(2025, 10, 17, 16, 59, 18, tzinfo=timezone.utc))
        '2025-10-17T16:59:18Z'
    """
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=UTC)
    return utc_datetime.isoformat()


def format_date_utc(utc_datetime: datetime) -> str:
    """
    Format datetime as ISO 8601 date string (UTC).

    Args:
        utc_datetime: Datetime in UTC timezone

    Returns:
        ISO 8601 date string (YYYY-MM-DD)

    Examples:
        >>> format_date_utc(datetime(2025, 10, 17, 16, 59, 18, tzinfo=timezone.utc))
        '2025-10-17'
    """
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=UTC)
    return utc_datetime.date().isoformat()


def parse_health_record_date(
    date_str: str, assume_utc: bool = True, strict: bool = False
) -> datetime:
    """
    Parse health record date string to timezone-aware datetime.

    All stored health records use format "%Y-%m-%d %H:%M:%S" and are
    assumed to be in UTC timezone unless otherwise specified.

    This is the canonical way to parse dates from Redis health data.
    Use this instead of datetime.strptime() to ensure timezone consistency.

    Args:
        date_str: Date string in format "YYYY-MM-DD HH:MM:SS"
        assume_utc: If True, naive datetimes are assumed UTC (default: True)
        strict: If True, raises ValueError for naive datetimes when assume_utc=False

    Returns:
        Timezone-aware datetime in UTC

    Raises:
        ValueError: If date format is invalid or if datetime is naive and strict=True

    Examples:
        >>> parse_health_record_date("2025-10-21 12:53:11")
        datetime.datetime(2025, 10, 21, 12, 53, 11, tzinfo=datetime.timezone.utc)

        >>> parse_health_record_date("2025-10-21 12:53:11", assume_utc=False, strict=True)
        ValueError: Naive datetime found...

    Note:
        This function centralizes timezone handling for all health record dates.
        Any changes to date storage format should be reflected here.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        raise ValueError(
            f"Invalid health record date format: '{date_str}'. "
            f"Expected format: 'YYYY-MM-DD HH:MM:SS'. Error: {e}"
        ) from e

    # Handle timezone awareness
    if dt.tzinfo is None:
        if strict and not assume_utc:
            raise ValueError(
                f"Naive datetime found: '{date_str}'. "
                "All health records must be timezone-aware. "
                "Set assume_utc=True to convert to UTC, or ensure data is stored with timezone."
            )
        if assume_utc:
            dt = dt.replace(tzinfo=UTC)

    return dt
