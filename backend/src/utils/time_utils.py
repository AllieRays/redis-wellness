"""
Time parsing utilities for natural language date/time descriptions.

All datetime operations use UTC. Frontend is responsible for timezone
conversion and display to support global users.

==========================================================================
📅 DATETIME STANDARDS FOR LLM INTERACTIONS
==========================================================================

This module handles all datetime parsing and formatting for the application.
When interacting with LLMs, follow these critical standards:

**STORAGE FORMAT (Internal):**
- All datetimes stored in ISO 8601 format: "2025-10-22T16:22:02+00:00"
- All datetimes are UTC (no timezone conversion in backend)
- Use `.isoformat()` for serialization to Redis/JSON

**LLM INPUT FORMAT (What tools return to LLM):**
- Health records: Date-only "YYYY-MM-DD" (e.g., "2025-10-22")
- Workouts: Date-only "YYYY-MM-DD" + "day_of_week" field (e.g., "Friday")
- Relative times: Human-readable strings (e.g., "3 days ago", "today")
- NEVER send full ISO timestamps to LLM (too technical, causes confusion)

**LLM OUTPUT FORMAT (How LLM should present to users):**
- Natural language: "October 22", "last Friday", "3 days ago"
- Avoid technical formats: NO "2025-10-22T16:22:02+00:00" in user responses
- Use day_of_week from tool data instead of calculating
- Use time_ago from tool data instead of calculating

**PARSING FUNCTIONS:**
- `parse_health_record_date()` - Parse any datetime from Redis (ISO or legacy)
- `parse_time_period()` - Convert natural language to UTC date ranges
- `format_datetime_utc()` - Format datetime to ISO 8601 string
- `format_date_utc()` - Format datetime to date-only string (YYYY-MM-DD)

**CRITICAL RULES FOR TOOL DEVELOPERS:**
1. Parse stored datetimes with `parse_health_record_date()`
2. Return dates to LLM as date-only strings: `.date().isoformat()`
3. Include helper fields: day_of_week, time_ago, last_workout
4. Document date formats in tool docstrings
5. Never send full ISO timestamps to LLM

**WHY THIS MATTERS:**
LLMs struggle with ISO 8601 timestamps and timezone calculations.
Providing clean, simple date strings with helper fields prevents:
- Incorrect day-of-week calculations
- Timezone confusion
- Hallucinated relative time statements
- Technical datetime strings in user responses

==========================================================================
"""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

# Default timeframe for "recent" queries
DEFAULT_RECENT_DAYS = 30


def get_utc_timestamp() -> int:
    """
    Get current UTC timestamp.

    Returns:
        int: Current UTC timestamp in seconds since epoch

    Example:
        >>> ts = get_utc_timestamp()
        >>> print(ts)
        1729737600

    Note:
        Use this instead of generating timestamps manually to ensure
        consistency across the codebase. All timestamps should be UTC.
    """
    return int(datetime.now(UTC).timestamp())


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
    # Normalize input: replace underscores with spaces
    time_period_lower = time_period.lower().strip().replace("_", " ")

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

    # Pattern 0: Specific date - "October 15th", "Oct 15", "October 15, 2024"
    # This must come BEFORE month-only pattern to avoid matching just the month
    specific_date_pattern = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?"
    match = re.search(specific_date_pattern, time_period_lower)

    if match:
        month_name = match.group(1)
        day = int(match.group(2))
        year_str = match.group(3)

        month_num = months[month_name]
        year = int(year_str) if year_str else now_utc.year

        # Single day range (start of day to end of day in UTC)
        start_date = datetime(year, month_num, day, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(year, month_num, day, 23, 59, 59, tzinfo=UTC)
        desc = f"{month_name.capitalize()} {day}, {year}"

        return start_date, end_date, desc

    # Pattern 1: "September" or "September 2025" (month only, no day)
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


def convert_utc_to_user_timezone(
    utc_datetime: datetime, user_timezone: str
) -> datetime:
    """
    Convert UTC datetime to user's local timezone.

    Args:
        utc_datetime: Datetime in UTC timezone
        user_timezone: IANA timezone name (e.g., "America/Los_Angeles", "America/New_York")

    Returns:
        Datetime converted to user's timezone

    Examples:
        >>> dt = datetime(2025, 9, 1, 8, 10, 0, tzinfo=UTC)  # 8:10 AM UTC
        >>> convert_utc_to_user_timezone(dt, "America/Los_Angeles")
        datetime.datetime(2025, 9, 1, 1, 10, 0, tzinfo=ZoneInfo(key='America/Los_Angeles'))  # 1:10 AM PST

    Note:
        This is used for display purposes only (e.g., sleep times).
        All internal storage and calculations remain in UTC.
    """
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=UTC)

    user_tz = ZoneInfo(user_timezone)
    return utc_datetime.astimezone(user_tz)


def parse_health_record_date(
    date_str: str, assume_utc: bool = True, strict: bool = False
) -> datetime:
    """
    Parse health record date string to timezone-aware datetime.

    Expects ISO 8601 format:
    - "2025-10-21T12:53:11+00:00" (with timezone)
    - "2025-10-21T12:53:11Z" (UTC shorthand)
    - "2025-10-21T12:53:11" (assumes UTC if assume_utc=True)

    This is the canonical way to parse dates from Redis health data.

    Args:
        date_str: Date string in ISO 8601 format
        assume_utc: If True, naive datetimes are assumed UTC (default: True)
        strict: If True, raises ValueError for naive datetimes when assume_utc=False

    Returns:
        Timezone-aware datetime in UTC

    Raises:
        ValueError: If date format is invalid or if datetime is naive and strict=True

    Examples:
        >>> parse_health_record_date("2025-10-21T12:53:11+00:00")
        datetime.datetime(2025, 10, 21, 12, 53, 11, tzinfo=datetime.timezone.utc)

        >>> parse_health_record_date("2025-10-21T12:53:11Z")
        datetime.datetime(2025, 10, 21, 12, 53, 11, tzinfo=datetime.timezone.utc)

    Note:
        All health record dates must be in ISO 8601 format.
        This ensures consistent timezone handling across the application.
    """
    try:
        # Parse ISO 8601 format
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(
            f"Invalid health record date format: '{date_str}'. "
            f"Expected ISO 8601 format (e.g., '2025-10-21T12:53:11+00:00' or '2025-10-21T12:53:11Z'). "
            f"Error: {e}"
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
