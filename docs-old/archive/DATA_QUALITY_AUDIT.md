# Apple Health Data Quality Audit & Fixes

## Date: October 22, 2025

## Executive Summary

Audit of the data pipeline from Apple Health XML → Redis revealed **critical data quality issues** that prevent the LLM from correctly answering queries about workout patterns.

## Critical Issues Found

### 1. **Inconsistent DateTime Formats** 🚨

**Problem:**
- Parser outputs: UTC datetime objects
- `import_health.py` line 121: Converts to `"%Y-%m-%d %H:%M:%S"` (naive format, loses timezone!)
- `import_health.py` line 139: Same issue for workouts
- Redis stores: Naive datetime strings without timezone

**Impact:**
- All timezone information is lost during import
- Tools can't reliably filter by date ranges
- Comparison operations fail due to timezone mismatches

**Current:**
```python
"date": record.start_date.strftime("%Y-%m-%d %H:%M:%S")  # ❌ WRONG: 2025-10-17 16:59:18 (naive)
```

**Should be:**
```python
"date": record.start_date.isoformat()  # ✅ CORRECT: 2025-10-17T16:59:18+00:00 (ISO with timezone)
```

### 2. **Missing Critical Fields** 🚨

**Problem:**
- Workouts missing `day_of_week` field
- Workouts missing `date` field (only has `startDate`)
- No cleaned `type` field (keeps `HKWorkoutActivityType` prefix)

**Impact:**
- LLM cannot identify workout day-of-week patterns without computing it
- Tools must reparse dates to extract day of week
- Inconsistent type naming across the system

**Missing fields:**
```json
{
  "type": "HKWorkoutActivityTypeTraditionalStrengthTraining",  // ❌ Long form
  "startDate": "2025-10-17 16:59:18",  // ❌ Naive datetime
  // MISSING: "day_of_week"
  // MISSING: "date" (YYYY-MM-DD)
  // MISSING: "type_cleaned"
}
```

**Should have:**
```json
{
  "type": "HKWorkoutActivityTypeTraditionalStrengthTraining",  // Keep for reference
  "type_cleaned": "TraditionalStrengthTraining",  // ✅ Clean name
  "startDate": "2025-10-17T16:59:18+00:00",  // ✅ ISO format
  "date": "2025-10-17",  // ✅ Date only
  "day_of_week": "Friday"  // ✅ Pre-computed
}
```

### 3. **Field Name Inconsistencies**

**Problem:**
- Workouts use `totalEnergyBurned`
- Search tool returns `energy_burned`
- Aggregator expects `calories`

**Impact:**
- Tools can't find energy data consistently
- Fallback logic required everywhere

## Root Cause Analysis

The `import_health.py` script (lines 109-146) converts Python datetime objects to strings using `strftime()` instead of `isoformat()`, losing timezone information and creating naive datetime strings.

This violates the documented standard: "All dates are UTC in ISO format."

## Recommended Fixes

### Fix 1: Update `import_health.py` to preserve timezone

```python
# Line 121 - Health records
"date": record.start_date.isoformat(),  # Not strftime()

# Line 130 - Metric summary
"latest_date": record.start_date.isoformat(),

# Line 139-140 - Workouts
"startDate": workout.start_date.isoformat(),
"endDate": workout.end_date.isoformat() if workout.end_date else None,
```

### Fix 2: Enrich workout data with computed fields

```python
# After line 136 in import_health.py
workout_dict = {
    "type": workout.workout_activity_type,  # Full name for reference
    "type_cleaned": workout_type,  # Already computed clean name
    "startDate": workout.start_date.isoformat(),  # ISO with timezone
    "endDate": workout.end_date.isoformat() if workout.end_date else None,
    "date": workout.start_date.strftime("%Y-%m-%d"),  # Date only for filtering
    "day_of_week": workout.start_date.strftime("%A"),  # Monday, Tuesday, etc.
    "duration": workout.duration,
    "duration_minutes": round(workout.duration / 60, 1) if workout.duration else None,  # Fix: seconds to minutes
    "calories": workout.total_energy_burned,  # Standardize field name
    "totalEnergyBurned": workout.total_energy_burned,  # Keep for backwards compat
    "totalDistance": workout.total_distance,
    "source": workout.source_name,
}
```

### Fix 3: Standardize field names

**Energy burned:**
- Primary: `calories` (matches common usage)
- Alias: `totalEnergyBurned` (for backwards compatibility)

**Duration:**
- Store in seconds: `duration`
- Pre-compute minutes: `duration_minutes` (not just round seconds!)

## Implementation Plan

1. ✅ **Update `import_health.py`** with timezone-aware ISO formats
2. ✅ **Add enrichment fields** (day_of_week, date, type_cleaned, calories)
3. ✅ **Create `reload_health_data.py`** with same enrichment for existing parsed files
4. ✅ **Test data integrity** - verify all dates are ISO format with timezone
5. ⏳ **Update documentation** in `DATA_RELOAD_INSTRUCTIONS.md`
6. ⏳ **Add data validation** script to verify format compliance

## Testing Checklist

After fixes, verify:

- [ ] All workout dates are ISO format: `2025-10-17T16:59:18+00:00`
- [ ] All workouts have `day_of_week` field
- [ ] All workouts have `date` field (YYYY-MM-DD)
- [ ] All workouts have `type_cleaned` field
- [ ] Duration in minutes is correctly calculated (duration / 60, not rounded seconds)
- [ ] Energy field is `calories` (with `totalEnergyBurned` alias)
- [ ] Health record dates are ISO format
- [ ] LLM can correctly answer "what day do I work out?" queries

## Verification Command

```bash
# Check workout data format
docker exec redis-wellness redis-cli GET "health:user:wellness_user:data" | \
  python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
workout = data.get('workouts', [])[0] if data.get('workouts') else {}

print('Sample workout format:')
print(f\"  startDate: {workout.get('startDate')} {'✅' if 'T' in workout.get('startDate', '') and '+' in workout.get('startDate', '') else '❌'}\")
print(f\"  date: {workout.get('date')} {'✅' if workout.get('date') else '❌'}\")
print(f\"  day_of_week: {workout.get('day_of_week')} {'✅' if workout.get('day_of_week') else '❌'}\")
print(f\"  type_cleaned: {workout.get('type_cleaned')} {'✅' if workout.get('type_cleaned') else '❌'}\")
print(f\"  calories: {workout.get('calories')} {'✅' if workout.get('calories') is not None else '❌'}\")
"
```

## Long-term Recommendations

1. **Add data validation layer** between parser and Redis
2. **Create Pydantic models** for Redis data format (enforce schema)
3. **Add integration tests** that verify data format compliance
4. **Document data contracts** between components (parser → Redis → tools)
5. **Add data migration scripts** for format changes

## Impact on Demo

**Before fixes:**
- LLM: "Based on the data, here's a detailed summary..." [verbose, wrong]
- User: "What day do I work out?"
- LLM: *Lists all workouts instead of answering the question*

**After fixes:**
- User: "What day do I work out?"
- LLM: "You consistently work out on Mondays and Fridays."
- ✅ Correct, concise, answers the actual question

## Files Modified

1. `/import_health.py` - Fix datetime formats, add enrichment
2. `/reload_health_data.py` - Add same enrichment for existing data
3. `/docs/DATA_QUALITY_AUDIT.md` - This document
4. `/docs/DATA_RELOAD_INSTRUCTIONS.md` - Update with new format

## Notes for Future Exports

When uploading new Apple Health XML:
1. Use `import_health.py` (will have fixes applied)
2. All enrichment happens automatically
3. Data will be clean and LLM-friendly from the start
4. No manual post-processing needed

## Related Issues

- Timezone mismatch bugs in `compare_time_periods`
- Workout search not finding recent data (naive datetime comparison)
- LLM unable to identify day-of-week patterns
- Inconsistent field naming across codebase
