# Datetime Handling Guidelines

## Critical Principles

**ALWAYS use UTC for all datetime operations in this codebase.**

### Why UTC?

1. **Consistency**: All stored data uses UTC timezone
2. **Apple Health Data**: Parser normalizes all timestamps to UTC
3. **Comparison Safety**: Prevents timezone-aware vs naive datetime bugs
4. **Redis Storage**: All timestamps stored as ISO format with UTC offset

## Correct Usage

### ✅ CORRECT - Use UTC explicitly

```python
from datetime import UTC, datetime

# Getting current time
now = datetime.now(UTC)

# Parsing ISO datetimes
workout_date = datetime.fromisoformat("2025-10-17T16:59:18+00:00")

# Ensure datetime is UTC-aware
if workout_date.tzinfo is None:
    workout_date = workout_date.replace(tzinfo=UTC)
```

### ❌ WRONG - Naive datetimes

```python
# DON'T DO THIS - creates naive datetime
now = datetime.now()  # ❌ No timezone info

# DON'T DO THIS - comparison will fail
cutoff = datetime.now() - timedelta(days=30)  # ❌ Naive
if workout_date >= cutoff:  # ❌ TypeError if workout_date is aware
    ...
```

## Fixed Issues (October 2025)

### Files Updated

1. **`backend/src/parsers/apple_health_parser.py`**
   - Line 178: `datetime.now()` → `datetime.now(UTC)`
   - Lines 267, 270: Fallback dates now use UTC

2. **`backend/src/tools/agent_tools.py`**
   - Line 413: Already correct ✅
   - Line 491: `datetime.now()` → `datetime.now(UTC)`
   - Line 419: Fixed to use `startDate` (full datetime) instead of `date` (string)

3. **`backend/src/utils/base.py`**
   - Lines 30, 57: ToolResult and ToolError timestamps now use UTC

4. **`backend/src/services/redis_health_tool.py`**
   - Lines 78, 108, 141, 173: All `datetime.now()` → `datetime.now(UTC)`

5. **`backend/src/services/memory_manager.py`**
   - Line 308: Semantic memory timestamps now use UTC

## Data Structure Standards

### Workout Data Format

Workouts in Redis have both `date` and `startDate` fields:

```json
{
  "type": "HKWorkoutActivityTypeTraditionalStrengthTraining",
  "date": "2025-10-17",  // Simple date string (YYYY-MM-DD)
  "startDate": "2025-10-17T16:59:18+00:00",  // Full ISO datetime with UTC
  "endDate": "2025-10-17T17:26:17+00:00",
  "duration": 1619.83,
  "duration_minutes": 26.997,
  "calories": 116.0
}
```

**Always use `startDate` for datetime comparisons**, not `date`.

## Testing

### Integration Test

Run `backend/tests/integration/test_workout_data_flow.py` to verify:
- Workouts are parsed with correct timezone
- Data flows from XML → Parser → Redis without timezone loss
- Current Redis data has workouts (prevents regression)

```bash
cd backend
uv run pytest tests/integration/test_workout_data_flow.py -v
```

### Smoke Test

```python
# Quick check that workouts exist and have correct dates
import redis
import json
from datetime import UTC, datetime, timedelta

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
data = json.loads(r.get("health:user:wellness_user:data"))

# Verify workouts exist
assert len(data["workouts"]) > 0, "No workouts found"

# Verify recent workouts are findable
cutoff = datetime.now(UTC) - timedelta(days=30)
recent = [w for w in data["workouts"]
          if datetime.fromisoformat(w["startDate"]) >= cutoff]
print(f"Found {len(recent)} workouts in last 30 days")
```

## Common Pitfalls

### 1. Using `date` field instead of `startDate`

```python
# ❌ WRONG - 'date' is just YYYY-MM-DD string
start_date_str = workout.get("date")  # "2025-10-17"
workout_date = datetime.fromisoformat(start_date_str)  # Naive datetime at midnight

# ✅ CORRECT - 'startDate' is full ISO with timezone
start_date_str = workout.get("startDate")  # "2025-10-17T16:59:18+00:00"
workout_date = datetime.fromisoformat(start_date_str)  # Aware datetime
```

### 2. Comparing dates without timezone consistency

```python
# ❌ WRONG
cutoff = datetime.now() - timedelta(days=30)  # Naive
if workout_date >= cutoff:  # TypeError if workout_date is aware
    ...

# ✅ CORRECT
cutoff = datetime.now(UTC) - timedelta(days=30)  # UTC-aware
if workout_date >= cutoff:  # Works correctly
    ...
```

### 3. Storing naive datetimes in Redis

```python
# ❌ WRONG
redis_client.set(key, datetime.now().isoformat())  # No timezone info

# ✅ CORRECT
redis_client.set(key, datetime.now(UTC).isoformat())  # "2025-10-22T05:15:00+00:00"
```

## Future Development

When adding new datetime code:

1. **Always import UTC**: `from datetime import UTC, datetime`
2. **Use `datetime.now(UTC)`** not `datetime.now()`
3. **Ensure parsed datetimes are UTC-aware** before comparisons
4. **Use `startDate` field** for workouts, not `date`
5. **Test with timezone-aware data** from Apple Health exports

## Audit Checklist

Run this to find any remaining issues:

```bash
cd backend
grep -rn "datetime.now()" src/ --include="*.py" | grep -v "datetime.now(UTC)"
```

If any results appear, they need to be fixed.

## Related Documentation

- `backend/tests/integration/test_workout_data_flow.py` - Integration tests
- `backend/src/parsers/apple_health_parser.py` - XML parsing with UTC normalization
- `scripts/parse_apple_health.py` - Conversion to JSON format
- `scripts/load_health_to_redis.py` - Loading data with correct user_id
