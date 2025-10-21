"""
Time parsing utilities for natural language date/time descriptions.

SHARED MODULE - Used by both stateless and stateful chats.
Pure functions with no side effects.

Datetimes are interpreted in Pacific timezone (user's local time)
but converted to UTC for consistent storage and comparison.
"""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

# User's timezone - Pacific Time
USER_TIMEZONE = ZoneInfo("America/Los_Angeles")


def parse_time_period(time_period: str) -> tuple[datetime, datetime, str]:
    """
    Parse natural language time descriptions into date ranges.

    Interprets user input in Pacific timezone, returns UTC for comparison with stored data.

    Args:
        time_period: Natural language time description

    Returns:
        Tuple of (start_date_utc, end_date_utc, description)

    Examples:
        "September" → (2025-09-01 00:00 PST as UTC, 2025-09-30 23:59 PST as UTC, "September 2025")
        "last week" → (7 days ago PST as UTC, now PST as UTC, "Last 7 days")
        "this month" → (first day of month PST as UTC, now PST as UTC, "This month")
    """
    # Get current time in Pacific timezone
    now_pst = datetime.now(USER_TIMEZONE)
    now_utc = now_pst.astimezone(UTC)
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
        year = int(year_str) if year_str else now_pst.year

        # Create dates in PST, then convert to UTC
        # Check for qualifiers (early, mid, late)
        if "early" in time_period_lower:
            start_date_pst = datetime(year, month_num, 1, tzinfo=USER_TIMEZONE)
            end_date_pst = datetime(
                year, month_num, 10, 23, 59, 59, tzinfo=USER_TIMEZONE
            )
            desc = f"Early {month_name.capitalize()} {year}"
        elif "mid" in time_period_lower or "middle" in time_period_lower:
            start_date_pst = datetime(year, month_num, 11, tzinfo=USER_TIMEZONE)
            end_date_pst = datetime(
                year, month_num, 20, 23, 59, 59, tzinfo=USER_TIMEZONE
            )
            desc = f"Mid {month_name.capitalize()} {year}"
        elif "late" in time_period_lower or "end" in time_period_lower:
            start_date_pst = datetime(year, month_num, 21, tzinfo=USER_TIMEZONE)
            # Last day of month
            if month_num == 12:
                end_date_pst = datetime(year, 12, 31, 23, 59, 59, tzinfo=USER_TIMEZONE)
            else:
                end_date_pst = datetime(
                    year, month_num + 1, 1, tzinfo=USER_TIMEZONE
                ) - timedelta(seconds=1)
            desc = f"Late {month_name.capitalize()} {year}"
        else:
            # Full month
            start_date_pst = datetime(year, month_num, 1, tzinfo=USER_TIMEZONE)
            if month_num == 12:
                end_date_pst = datetime(year, 12, 31, 23, 59, 59, tzinfo=USER_TIMEZONE)
            else:
                end_date_pst = datetime(
                    year, month_num + 1, 1, tzinfo=USER_TIMEZONE
                ) - timedelta(seconds=1)
            desc = f"{month_name.capitalize()} {year}"

        # Convert to UTC for comparison with stored data
        return start_date_pst.astimezone(UTC), end_date_pst.astimezone(UTC), desc

    # Pattern 2: "last N days/weeks/months"
    relative_pattern = r"last\s+(\d+)\s+(day|week|month)s?"
    match = re.search(relative_pattern, time_period_lower)

    if match:
        num = int(match.group(1))
        unit = match.group(2)

        if unit == "day":
            start_date_pst = now_pst - timedelta(days=num)
            desc = f"Last {num} day{'s' if num > 1 else ''}"
        elif unit == "week":
            start_date_pst = now_pst - timedelta(weeks=num)
            desc = f"Last {num} week{'s' if num > 1 else ''}"
        elif unit == "month":
            start_date_pst = now_pst - timedelta(days=num * 30)  # Approximate
            desc = f"Last {num} month{'s' if num > 1 else ''}"

        return start_date_pst.astimezone(UTC), now_utc, desc

    # Pattern 3: "this week/month/year"
    if "this week" in time_period_lower:
        start_date_pst = now_pst - timedelta(days=now_pst.weekday())  # Monday
        return start_date_pst.astimezone(UTC), now_utc, "This week"

    if "this month" in time_period_lower:
        start_date_pst = datetime(now_pst.year, now_pst.month, 1, tzinfo=USER_TIMEZONE)
        return (
            start_date_pst.astimezone(UTC),
            now_utc,
            f"This month ({now_pst.strftime('%B %Y')})",
        )

    if "this year" in time_period_lower:
        start_date_pst = datetime(now_pst.year, 1, 1, tzinfo=USER_TIMEZONE)
        return start_date_pst.astimezone(UTC), now_utc, f"This year ({now_pst.year})"

    # Pattern 4: "last week/month/year"
    if "last week" in time_period_lower:
        # Start from last Monday in PST
        days_since_monday = now_pst.weekday()
        last_monday_pst = now_pst - timedelta(days=days_since_monday + 7)
        last_sunday_pst = last_monday_pst + timedelta(
            days=6, hours=23, minutes=59, seconds=59
        )
        return (
            last_monday_pst.astimezone(UTC),
            last_sunday_pst.astimezone(UTC),
            "Last week",
        )

    if "last month" in time_period_lower:
        # Previous month in PST
        if now_pst.month == 1:
            prev_month = 12
            prev_year = now_pst.year - 1
        else:
            prev_month = now_pst.month - 1
            prev_year = now_pst.year

        start_date_pst = datetime(prev_year, prev_month, 1, tzinfo=USER_TIMEZONE)
        if prev_month == 12:
            end_date_pst = datetime(prev_year, 12, 31, 23, 59, 59, tzinfo=USER_TIMEZONE)
        else:
            end_date_pst = datetime(
                prev_year, prev_month + 1, 1, tzinfo=USER_TIMEZONE
            ) - timedelta(seconds=1)

        month_name = datetime(prev_year, prev_month, 1, tzinfo=USER_TIMEZONE).strftime(
            "%B %Y"
        )
        return (
            start_date_pst.astimezone(UTC),
            end_date_pst.astimezone(UTC),
            f"Last month ({month_name})",
        )

    # Default: "recent" or anything else → last 30 days
    start_date_pst = now_pst - timedelta(days=30)
    return start_date_pst.astimezone(UTC), now_utc, "Last 30 days (recent)"


def format_datetime_pst(utc_datetime: datetime) -> str:
    """
    Convert UTC datetime to user-friendly PST display format.

    Args:
        utc_datetime: Datetime in UTC timezone

    Returns:
        Formatted string in PST (e.g., "Oct 17, 2025 at 9:59 AM PDT")

    Examples:
        format_datetime_pst(datetime(2025, 10, 17, 16, 59, 18, tzinfo=timezone.utc))
        → "Oct 17, 2025 at 9:59 AM PDT"
    """
    if utc_datetime.tzinfo is None:
        # Assume UTC if naive
        utc_datetime = utc_datetime.replace(tzinfo=UTC)

    # Convert to Pacific time
    pst_time = utc_datetime.astimezone(USER_TIMEZONE)

    # Format with timezone abbreviation (PDT/PST)
    return pst_time.strftime("%b %d, %Y at %I:%M %p %Z")


def format_date_pst(utc_datetime: datetime) -> str:
    """
    Convert UTC datetime to user-friendly PST date format (no time).

    Args:
        utc_datetime: Datetime in UTC timezone

    Returns:
        Formatted string in PST (e.g., "Oct 17, 2025")

    Examples:
        format_date_pst(datetime(2025, 10, 17, 16, 59, 18, tzinfo=timezone.utc))
        → "Oct 17, 2025"
    """
    if utc_datetime.tzinfo is None:
        # Assume UTC if naive
        utc_datetime = utc_datetime.replace(tzinfo=UTC)

    # Convert to Pacific time
    pst_time = utc_datetime.astimezone(USER_TIMEZONE)

    # Format date only
    return pst_time.strftime("%b %d, %Y")
