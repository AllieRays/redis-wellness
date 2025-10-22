# Bug Fix: Timezone-Aware vs Timezone-Naive Datetime Comparison

**Date:** 2025-10-21
**Status:** ✅ FIXED
**Severity:** Critical (P0) - All health queries were failing

## Problem

All health data queries were returning "no data available" even though data existed in Redis.

### Root Cause

**TypeError: can't compare offset-naive and offset-aware datetimes**

The issue occurred in two places:
1. `search_health_records_by_metric()` in `/backend/src/tools/agent_tools.py` (line 236)
2. `aggregate_metrics()` in `/backend/src/tools/agent_tools.py` (line 578)

### Why It Happened

```python
# Time period parsing returns timezone-aware datetimes (UTC)
filter_start, filter_end, time_range_desc = _parse_time_period(time_period)
# filter_start = datetime(2025, 9, 21, tzinfo=timezone.utc)

# But stored health records have timezone-naive datetime strings
record_date = datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S")
# record_date = datetime(2025, 10, 21, 12, 53, 11)  # No tzinfo

# This comparison FAILS:
if filter_start <= record_date <= filter_end:  # ❌ TypeError
```

Python cannot compare timezone-aware and timezone-naive datetimes. When this comparison failed, it raised an exception that was caught, returning empty results to the user.

## Solution

Make the stored record dates timezone-aware before comparison by assuming UTC:

```python
# Parse the stored date string
record_date = datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S")

# Make it timezone-aware (assume UTC) if it isn't already
if record_date.tzinfo is None:
    record_date = record_date.replace(tzinfo=UTC)

# Now comparison works ✅
if filter_start <= record_date <= filter_end:
```

## Changes Made

### 1. Fixed `search_health_records_by_metric()` (line 228-239)

```python
# BEFORE (line 228-236):
filtered_records = []
for record in all_records:
    record_date = datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S")

    # Check if record is within date range
    if filter_start <= record_date <= filter_end:  # ❌ FAILS

# AFTER (line 228-239):
filtered_records = []
for record in all_records:
    record_date = datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S")
    # Make timezone-aware for comparison (assume UTC)
    if record_date.tzinfo is None:
        record_date = record_date.replace(tzinfo=UTC)

    # Check if record is within date range
    if filter_start <= record_date <= filter_end:  # ✅ WORKS
```

### 2. Fixed `aggregate_metrics()` (line 571-582)

```python
# BEFORE (line 571-578):
filtered_values = []
for record in all_records:
    record_date = datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S")

    if filter_start <= record_date <= filter_end:  # ❌ FAILS

# AFTER (line 571-582):
filtered_values = []
for record in all_records:
    record_date = datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S")
    # Make timezone-aware for comparison (assume UTC)
    if record_date.tzinfo is None:
        record_date = record_date.replace(tzinfo=UTC)

    if filter_start <= record_date <= filter_end:  # ✅ WORKS
```

## Verification

### Before Fix
```bash
$ curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "what is my latest weight?", "user_id": "your_user"}'

{
  "response": "It seems there is no recent data available for your latest weight.",
  "tools_used": [{"name": "search_health_records_by_metric"}],
  "tool_calls_made": 1
}
```

**Backend logs:**
```
📊 Found 39 total BodyMass records
❌ Error: TypeError: can't compare offset-naive and offset-aware datetimes
```

### After Fix
```bash
$ curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "what is my latest weight?", "user_id": "your_user"}'

{
  "response": "Your latest weight was recorded as 158.3 lbs on October 21st...",
  "tools_used": [{"name": "search_health_records_by_metric"}],
  "tool_calls_made": 1
}
```

**Backend logs:**
```
📊 Found 39 total BodyMass records
✅ Filtered to 39 BodyMass records (Last 30 days (recent))
```

## Test Coverage

Created comprehensive test suite (`test_health_queries_comprehensive.py`) covering:

1. ✅ **Basic weight query**: "what is my latest weight?"
2. ✅ **Average aggregation**: "what was my average heart rate last week?"
3. ✅ **Historical query**: "what was my BMI in September?"
4. ✅ **Follow-up with context**: "is that good?"
5. ✅ **Workout query**: "when was the last time I exercised?"
6. ✅ **Multi-metric query**: "show me my latest weight and heart rate"

All 6 tests pass ✅

### Test Results
```bash
$ uv run pytest tests/test_health_queries_comprehensive.py -v
===================== test session starts =====================
tests/test_health_queries_comprehensive.py::test_basic_weight_query PASSED
tests/test_health_queries_comprehensive.py::test_average_heart_rate PASSED
tests/test_health_queries_comprehensive.py::test_historical_bmi_query PASSED
tests/test_health_queries_comprehensive.py::test_follow_up_with_context PASSED
tests/test_health_queries_comprehensive.py::test_workout_query PASSED
tests/test_health_queries_comprehensive.py::test_multiple_metrics PASSED
===================== 6 passed in 49.50s ======================
```

## Prevention

### Why Didn't This Break Before?

This was likely introduced when:
1. Test data generator was updated to use `datetime.now(timezone.utc)` (timezone-aware)
2. But the stored date strings remained timezone-naive
3. Time parsing utility `_parse_time_period()` returns timezone-aware datetimes

### Best Practices Going Forward

1. **Always use timezone-aware datetimes** when working with dates
2. **Use `datetime.now(timezone.utc)`** instead of `datetime.now()`
3. **When parsing stored dates**, immediately make them timezone-aware:
   ```python
   record_date = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
   if record_date.tzinfo is None:
       record_date = record_date.replace(tzinfo=UTC)
   ```
4. **Add type hints** to catch this earlier:
   ```python
   from datetime import datetime, timezone

   def parse_date(date_str: str) -> datetime:
       """Always returns timezone-aware datetime."""
       dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
       return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
   ```

## Related Files

- `/backend/src/tools/agent_tools.py` (lines 228-239, 571-582) ← Fixed
- `/backend/src/utils/time_utils.py` (time period parsing)
- `/backend/tests/test_health_queries_comprehensive.py` ← New test suite
- `/backend/tests/fixtures/generate_test_data.py` (test data generation)

## Impact

**Queries Fixed:**
- ✅ All weight queries
- ✅ All BMI queries
- ✅ All heart rate queries
- ✅ Historical queries (e.g., "in September")
- ✅ Recent queries (e.g., "last week")
- ✅ Aggregation queries (average, min, max)
- ✅ Multi-metric queries

**User Experience:**
- Before: All queries returned "no data available" 😞
- After: All queries return correct health data 🎉

## Deployment

1. ✅ Code changes committed to `agent_tools.py`
2. ✅ Comprehensive test suite created
3. ✅ Backend container rebuilt: `docker-compose up -d --build backend`
4. ✅ All tests passing

**No database migration needed** - this was a code-only fix.
