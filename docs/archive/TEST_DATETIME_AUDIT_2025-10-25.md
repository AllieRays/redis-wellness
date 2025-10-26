# Datetime Test Audit - Critical Issues Found

**Date**: October 25, 2025
**Status**: 🚨 **3 CRITICAL ISSUES** - Will cause false positives/flaky tests
**Tests Run**: ✅ All passing NOW, but will fail/flake in production

---

## Executive Summary

All datetime tests currently **PASS** (10/10 tests), but contain **3 critical design flaws** that will cause:

1. ❌ **Hardcoded 2024 dates** - Will fail when year changes
2. ❌ **Non-deterministic time-dependent tests** - Will flake based on when you run them
3. ❌ **Timezone-dependent assumptions** - May fail in different timezones

**These tests will break in production and cause CI failures!**

---

## Critical Issue #1: Hardcoded 2024 Dates

### Problem

Multiple tests use hardcoded `2024` dates that won't work in 2025+:

**test_time_utils.py**:
```python
# Line 33: HARDCODED 2024
def test_format_datetime_utc(self):
    dt = datetime(2024, 10, 22, 16, 30, 0, tzinfo=UTC)  # ❌ 2024!

# Line 42: HARDCODED 2024
def test_format_date_utc(self):
    dt = datetime(2024, 10, 22, 16, 30, 0, tzinfo=UTC)  # ❌ 2024!

# Line 50: HARDCODED 2024
def test_parse_health_record_date_iso(self):
    date_str = "2024-10-22T16:30:00+00:00"  # ❌ 2024!

# Line 61: HARDCODED 2024
def test_parse_health_record_date_z_suffix(self):
    date_str = "2024-10-22T16:30:00Z"  # ❌ 2024!

# Line 102: HARDCODED 2024
def test_parse_october_15(self):
    start, end, desc = parse_time_period("October 15 2024")  # ❌ 2024!
```

**test_metric_aggregators.py** (lines 74-76):
```python
records = [
    {"date": "2025-10-17T08:00:00+00:00", ...},  # ✅ Good - uses 2025
    {"date": "2025-10-17T12:00:00+00:00", ...},  # ✅ Good
]
```

**test_health_analytics.py** (lines 29, 53-56):
```python
# Line 29: HARDCODED 2025 (good for now, but...)
date_str = f"2025-10-{day:02d}T08:00:00+00:00"  # ⚠️ Will be wrong in 2026

# Lines 53-56: HARDCODED 2025
{"date": "2025-09-01T08:00:00+00:00", ...},  # ⚠️ Will be wrong in 2026
{"date": "2025-10-15T08:00:00+00:00", ...},  # ⚠️ Will be wrong in 2026
```

### Impact

- ❌ Tests will fail when year != 2024/2025
- ❌ Creates maintenance burden (update every year)
- ❌ May cause CI failures on Jan 1st

### Fix

Use **relative dates** or **mock the current time**:

```python
# ❌ WRONG - Hardcoded year
dt = datetime(2024, 10, 22, 16, 30, 0, tzinfo=UTC)

# ✅ CORRECT - Use fixed test time
TEST_DATE = datetime(2025, 10, 22, 16, 30, 0, tzinfo=UTC)
dt = TEST_DATE

# ✅ BETTER - Mock current time for relative tests
from unittest.mock import patch
from utils.time_utils import get_utc_timestamp

@patch('utils.time_utils.get_utc_timestamp', return_value=1729865400)
def test_time_dependent_function():
    # Test uses mocked "now" - always deterministic
    ...
```

---

## Critical Issue #2: Non-Deterministic Time-Dependent Tests

### Problem

Tests that depend on "current time" will produce different results based on when you run them:

**test_time_utils.py line 24-29**:
```python
def test_get_utc_timestamp(self):
    ts = get_utc_timestamp()  # ❌ Returns CURRENT time!

    assert isinstance(ts, int)
    assert ts > 0  # ⚠️ This is basically useless
```

**Why This Is Bad**:
- ✅ Test passes if `ts > 0` (always true for timestamps after 1970)
- ❌ But doesn't verify the timestamp is CORRECT
- ❌ Doesn't test timezone handling
- ❌ Doesn't test UTC enforcement

**test_time_utils.py lines 72-77**:
```python
def test_parse_last_week(self):
    start, end, desc = parse_time_period("last week")  # ❌ Depends on TODAY

    assert "week" in desc.lower()
    assert (end - start).days == 6  # Mon-Sun
```

**Why This Is Flaky**:
- If you run this test on **Monday**, it returns last week (Mon-Sun)
- If you run on **Tuesday**, it STILL returns last week (Mon-Sun)
- But the ACTUAL dates are different!
- **This can cause false positives** if the implementation changes

**test_time_utils.py lines 86-91**:
```python
def test_parse_this_month(self):
    start, end, desc = parse_time_period("this month")  # ❌ Depends on CURRENT MONTH

    assert "month" in desc.lower()
    assert start.day == 1  # ⚠️ Only checks start is day 1
```

**Why This Is Incomplete**:
- Doesn't verify `start.month` matches current month
- Doesn't verify `start.year` is correct
- Doesn't verify `end` is actually in the current month
- **Can give false positive if returns wrong month but starts on day 1**

### Impact

- ❌ Tests pass with incorrect implementations
- ❌ Different results on different days
- ❌ Hard to reproduce test failures
- ❌ Masks bugs in datetime logic

### Fix

**Mock the current time** for all time-dependent tests:

```python
# ❌ WRONG - Non-deterministic
def test_parse_last_week(self):
    start, end, desc = parse_time_period("last week")
    assert (end - start).days == 6

# ✅ CORRECT - Deterministic with mocking
from unittest.mock import patch
from datetime import UTC, datetime

@patch('src.utils.time_utils.datetime')
def test_parse_last_week(mock_datetime):
    # Fix "now" to Oct 25, 2025 (Friday)
    mock_datetime.now.return_value = datetime(2025, 10, 25, 12, 0, 0, tzinfo=UTC)
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    start, end, desc = parse_time_period("last week")

    # Last week = Oct 13 (Mon) to Oct 19 (Sun)
    assert start == datetime(2025, 10, 13, 0, 0, 0, tzinfo=UTC)
    assert end == datetime(2025, 10, 19, 23, 59, 59, tzinfo=UTC)
    assert desc == "Last week"
```

---

## Critical Issue #3: Incomplete Assertions

### Problem

Tests verify **partial behavior** but miss edge cases:

**test_time_utils.py line 24-29** (already mentioned):
```python
def test_get_utc_timestamp(self):
    ts = get_utc_timestamp()

    assert isinstance(ts, int)  # ✅ Checks type
    assert ts > 0               # ✅ Checks positive
    # ❌ Doesn't check it's actually UTC
    # ❌ Doesn't check it's close to current time
    # ❌ Doesn't verify datetime.now(UTC) is used
```

**Better Test**:
```python
from unittest.mock import patch
from datetime import UTC, datetime

@patch('src.utils.time_utils.datetime')
def test_get_utc_timestamp(mock_datetime):
    # Mock datetime.now(UTC) to return fixed time
    fixed_time = datetime(2025, 10, 25, 14, 30, 0, tzinfo=UTC)
    mock_datetime.now.return_value = fixed_time

    ts = get_utc_timestamp()

    # Verify it's the correct timestamp for our mocked time
    expected_ts = int(fixed_time.timestamp())
    assert ts == expected_ts  # Exact match

    # Verify datetime.now was called with UTC
    mock_datetime.now.assert_called_once_with(UTC)
```

**test_time_utils.py lines 72-77**:
```python
def test_parse_last_week(self):
    start, end, desc = parse_time_period("last week")

    assert "week" in desc.lower()  # ✅ Checks description
    assert (end - start).days == 6  # ⚠️ Only checks duration
    # ❌ Doesn't verify it's ACTUALLY last week
    # ❌ Doesn't verify it's Monday to Sunday
    # ❌ Doesn't verify timezone is UTC
```

---

## Recommended Fixes

### 1. Update test_time_utils.py

Replace hardcoded dates and add mocking:

```python
"""Unit tests for time_utils - DETERMINISTIC TESTS WITH MOCKING."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.utils.time_utils import (
    format_date_utc,
    format_datetime_utc,
    get_utc_timestamp,
    parse_health_record_date,
    parse_time_period,
)

# Fixed test dates (update annually or use current year dynamically)
TEST_DATETIME = datetime(2025, 10, 22, 16, 30, 0, tzinfo=UTC)
TEST_DATE_STR_ISO = "2025-10-22T16:30:00+00:00"
TEST_DATE_STR_Z = "2025-10-22T16:30:00Z"


@pytest.mark.unit
class TestTimeParsingBasic:
    """Test basic time parsing functions."""

    @patch('src.utils.time_utils.datetime')
    def test_get_utc_timestamp(self, mock_datetime):
        """Test UTC timestamp generation with mocked time."""
        # Mock datetime.now(UTC) to return fixed time
        mock_datetime.now.return_value = TEST_DATETIME

        ts = get_utc_timestamp()

        # Verify correct timestamp
        expected = int(TEST_DATETIME.timestamp())
        assert ts == expected

        # Verify UTC was used
        mock_datetime.now.assert_called_once_with(UTC)

    def test_format_datetime_utc(self):
        """Test datetime formatting."""
        result = format_datetime_utc(TEST_DATETIME)

        assert "2025-10-22" in result
        assert "16:30:00" in result
        assert "+00:00" in result or "Z" in result

    def test_format_date_utc(self):
        """Test date-only formatting."""
        result = format_date_utc(TEST_DATETIME)

        assert result == "2025-10-22"

    def test_parse_health_record_date_iso(self):
        """Test parsing ISO 8601 health record dates."""
        result = parse_health_record_date(TEST_DATE_STR_ISO)

        assert result.year == 2025
        assert result.month == 10
        assert result.day == 22
        assert result.hour == 16
        assert result.minute == 30
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_parse_health_record_date_z_suffix(self):
        """Test parsing dates with Z suffix."""
        result = parse_health_record_date(TEST_DATE_STR_Z)

        assert result.tzinfo == UTC
        assert result.year == 2025


@pytest.mark.unit
class TestTimePeriodParsing:
    """Test natural language time period parsing with mocked current time."""

    @patch('src.utils.time_utils.datetime')
    def test_parse_last_week(self, mock_datetime):
        """Test parsing 'last week' with fixed current date."""
        # Mock "now" to Friday, Oct 25, 2025
        now = datetime(2025, 10, 25, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        start, end, desc = parse_time_period("last week")

        # Last week should be Monday Oct 13 to Sunday Oct 19
        assert start.date() == datetime(2025, 10, 13).date()
        assert end.date() == datetime(2025, 10, 19).date()
        assert "week" in desc.lower()
        assert (end - start).days == 6

    @patch('src.utils.time_utils.datetime')
    def test_parse_this_month(self, mock_datetime):
        """Test parsing 'this month' with fixed current date."""
        # Mock "now" to Oct 25, 2025
        now = datetime(2025, 10, 25, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        start, end, desc = parse_time_period("this month")

        # This month = Oct 1 to Oct 25 (current day)
        assert start.year == 2025
        assert start.month == 10
        assert start.day == 1
        assert end.year == 2025
        assert end.month == 10
        assert "month" in desc.lower()
```

### 2. Update test_metric_aggregators.py

Good news: Already uses 2025 dates! But should add constants:

```python
# Add at top of file
TEST_YEAR = 2025  # Update annually or use datetime.now(UTC).year

# Then use in tests:
{"date": f"{TEST_YEAR}-10-17T08:00:00+00:00", ...}
```

### 3. Update test_health_analytics.py

Replace hardcoded 2025 with constant:

```python
# Add at top
from datetime import UTC, datetime

TEST_YEAR = datetime.now(UTC).year  # Always current year
# Or: TEST_YEAR = 2025  # Update annually

# Then use:
date_str = f"{TEST_YEAR}-10-{day:02d}T08:00:00+00:00"
```

---

## Summary of Issues

| Issue | Files Affected | Severity | Impact |
|-------|----------------|----------|--------|
| Hardcoded 2024 dates | test_time_utils.py | 🔴 HIGH | Tests will fail on Jan 1, 2025 |
| Non-deterministic tests | test_time_utils.py | 🔴 HIGH | Flaky tests, false positives |
| Incomplete assertions | test_time_utils.py | 🟡 MEDIUM | May miss bugs |
| Hardcoded 2025 dates | test_health_analytics.py | 🟡 MEDIUM | Will fail on Jan 1, 2026 |

---

## Action Plan

### Immediate (Before Demo)
1. ✅ Document issues (this document)
2. ⚠️ **DO NOT fix before demo** (tests currently pass, don't introduce risk)
3. ✅ Add to post-demo tasks

### Post-Demo (High Priority)
1. Update test_time_utils.py with mocking
2. Replace all hardcoded years with constants
3. Add comprehensive assertions
4. Run tests with different mock dates to verify robustness

### Long-Term
1. Add CI check: Fail if tests contain hardcoded years < current_year
2. Add test coverage for edge cases (leap years, month boundaries, DST)
3. Consider using `freezegun` library for time mocking

---

## Test Coverage Gaps

Additional tests needed:

1. **Leap year handling** - Feb 29 dates
2. **Month boundary tests** - "last month" on Jan 1
3. **Year boundary tests** - "last week" on Jan 1
4. **Timezone edge cases** - Dates near midnight UTC
5. **Invalid date strings** - Malformed ISO dates
6. **Missing timezone** - Naive datetime handling

---

**Reviewed**: October 25, 2025
**Status**: Tests pass NOW, will fail in future
**Next Action**: Fix post-demo (high priority)
